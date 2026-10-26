"""Parsers for published files whose layouts were checked against real samples
(see inspect_sources.py): Treasury TIC, Japan CPI, NY Fed SCE, ISM, and the
Forex Factory weekly calendar (consensus forecasts)."""

from __future__ import annotations

import csv
import io
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Sequence

import pandas as pd

from ..db.store import Observation
from .base import FetchResult, Provider, ProviderError, SeriesDef, register, to_float
from .documents import BROWSER_UA, pdf_pages


def _today() -> date:
    return datetime.now(timezone.utc).date()


@register
class TicTable5(Provider):
    """Treasury TIC SLT table 5 (major foreign holders, $bn, 13 months).
    code = row label: "Grand Total" | "Of Which: Foreign Official"."""

    name = "TIC"
    batch = True
    URL = "https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.txt"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        text = self.get(self.URL).decode("utf-8", errors="replace")
        rows = [line.rstrip("\r").split("\t") for line in text.splitlines()]
        header = next((r for r in rows if r and r[0].strip() == "Country"), None)
        if header is None:
            raise ProviderError("TIC table 5 layout changed: no Country header")
        months = [date.fromisoformat(h.strip() + "-01") if re.fullmatch(r"\d{4}-\d{2}", h.strip()) else None for h in header[1:]]
        table = {r[0].strip(): r[1:] for r in rows if r and r[0].strip()}
        out = []
        for d in defs:
            values = table.get(d.code)
            obs = []
            if values:
                for m, v in zip(months, values):
                    x = to_float(v)
                    if m and x is not None and m >= start:
                        obs.append(Observation(m, x))
            out.append(FetchResult(d.key, sorted(obs, key=lambda o: o.obs_date), "ok" if obs else "error",
                                   "" if obs else f"row {d.code!r} not found"))
        return out


@register
class JapanCpi(Provider):
    """Statistics Bureau of Japan CPI CSVs (national, monthly indices). Year-over-year
    is computed within one base (2020 base file, then 2025 base file from 2026).
    code = headline_yoy | ex_fresh_yoy."""

    name = "JPCPI"
    batch = True
    FILES = ("https://www.stat.go.jp/data/cpi/2020/csv/zmi2020aa.csv", "https://www.stat.go.jp/data/cpi/2025/csv/zmi2025aa.csv")
    COLUMNS = {"headline_yoy": "総合", "ex_fresh_yoy": "生鮮食品を除く総合"}

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        merged: dict[str, dict[date, float]] = defaultdict(dict)
        errors = []
        for url in self.FILES:
            try:
                body = self.get(url)
            except ProviderError as error:
                errors.append(str(error))
                continue
            for enc in ("utf-8-sig", "cp932"):
                try:
                    text = body.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            rows = list(csv.reader(io.StringIO(text)))
            names = rows[0]
            for code, label in self.COLUMNS.items():
                if label not in names:
                    continue
                col = names.index(label)
                levels = {}
                for r in rows:
                    if r and re.fullmatch(r"\d{6}", r[0].strip()) and len(r) > col:
                        v = to_float(r[col])
                        if v is not None:
                            levels[date(int(r[0][:4]), int(r[0][4:6]), 1)] = v
                for m, v in levels.items():
                    prev = levels.get(date(m.year - 1, m.month, 1))
                    if prev:
                        merged[code][m] = round((v / prev - 1) * 100, 4)  # later (newer base) file overwrites
        out = []
        for d in defs:
            obs = [Observation(m, v) for m, v in sorted(merged.get(d.code, {}).items()) if m >= start]
            out.append(FetchResult(d.key, obs, "ok" if obs else "error", "" if obs else "; ".join(errors)[:200]))
        return out


@register
class NyFedSce(Provider):
    """NY Fed Survey of Consumer Expectations chart data (sheet "Inflation expectations").
    code = exact column header, or "<header A> - <header B>" for a spread."""

    name = "SCE"
    batch = True
    URL = "https://www.newyorkfed.org/medialibrary/interactives/sce/sce/downloads/data/frbny-sce-data.xlsx"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        sheet = pd.read_excel(io.BytesIO(self.get(self.URL)), sheet_name="Inflation expectations", header=None)
        header_row = next(i for i in range(min(15, len(sheet)))
                          if any(str(c).startswith("Median one-year ahead") for c in sheet.iloc[i]))
        headers = [str(c).strip() for c in sheet.iloc[header_row]]
        data = sheet.iloc[header_row + 1:]
        dates = [date(int(str(x)[:4]), int(str(x)[4:6]), 1) if re.fullmatch(r"\d{6}(\.0)?", str(x)) else None for x in data.iloc[:, 0]]

        def column(name: str) -> dict[date, float]:
            if name not in headers:
                raise ProviderError(f"SCE column {name!r} missing")
            values = data.iloc[:, headers.index(name)]
            return {d: float(v) for d, v in zip(dates, values) if d and to_float(v) is not None}

        out = []
        for d in defs:
            try:
                if " - " in d.code:
                    a, b = (column(x.strip()) for x in d.code.split(" - "))
                    series = {k: a[k] - b[k] for k in a if k in b}
                else:
                    series = column(d.code)
            except ProviderError as error:
                out.append(FetchResult(d.key, [], "error", str(error)))
                continue
            obs = [Observation(k, v) for k, v in sorted(series.items()) if k >= start]
            out.append(FetchResult(d.key, obs, "ok" if obs else "empty"))
        return out


ISM_ROWS = {
    "pmi": r"Manufacturing PMI®?",
    "new_orders": r"(?<!Export )New Orders",
    "employment": r"Employment",
    "prices": r"Prices",
    "inventories": r"(?<!Customers’ )(?<!Customers' )Inventories",
}


ISM_SERVICES_ROWS = {**ISM_ROWS, "pmi": r"Services PMI®?"}


def parse_ism(text: str, rows: dict[str, str] = ISM_ROWS) -> dict[str, tuple[float, float]]:
    """'at a Glance' rows: label, current index, previous index, change."""
    out = {}
    for key, label in rows.items():
        m = re.search(label + r"\s+(\d{2}\.\d)\s+(\d{2}\.\d)\s+[+\-]?\d+\.\d", text)
        if m:
            out[key] = (float(m.group(1)), float(m.group(2)))
    return out


@register
class Ism(Provider):
    """ISM Manufacturing Report On Business PDF. code = pmi | new_orders | employment |
    prices | inventories. Normal runs read the last 3 monthly reports; a first load
    (env BACKFILL=1) walks back to ``start``."""

    name = "ISM"
    batch = True
    supports_backfill = True
    URL = "https://www.ismworld.org/globalassets/pub/research-and-surveys/rob/pmi/baby{ym}pmi.pdf"
    ROWS = ISM_ROWS

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        today = _today()
        months = []
        m = date(today.year, today.month, 1)
        limit = start if self.env.get("BACKFILL") else (m - timedelta(days=100))
        while m >= max(limit.replace(day=1), date(2019, 1, 1)):
            months.append(m)
            m = (m - timedelta(days=1)).replace(day=1)
        values: dict[str, dict[date, float]] = defaultdict(dict)
        for report_month in months:
            data_month = (report_month - timedelta(days=1)).replace(day=1)
            try:
                r = self.session.get(self.URL.format(ym=f"{data_month:%Y%m}"), timeout=(15, 60), headers={"User-Agent": BROWSER_UA})
            except Exception:  # noqa: BLE001
                continue
            if r.status_code != 200 or r.content[:5] != b"%PDF-":
                continue
            parsed = parse_ism("\n".join(pdf_pages(r.content)[:3]), self.ROWS)
            prev_month = (data_month - timedelta(days=1)).replace(day=1)
            for key, (cur, prev) in parsed.items():
                values[key][data_month] = cur
                values[key].setdefault(prev_month, prev)
        out = []
        for d in defs:
            obs = [Observation(k, v) for k, v in sorted(values.get(d.code, {}).items()) if k >= start]
            out.append(FetchResult(d.key, obs, "ok" if obs else "empty", f"{len(values.get(d.code, {}))} months"))
        return out


@register
class IsmServices(Ism):
    """ISM Services Report On Business PDF (same 'at a Glance' layout). code = pmi |
    new_orders | employment | prices | inventories."""

    name = "ISMS"
    URL = "https://www.ismworld.org/globalassets/pub/research-and-surveys/rob/nmi/rain{ym}svcs.pdf"
    ROWS = ISM_SERVICES_ROWS


# --------------------------------------------------------------------------- Japan MHLW Monthly Labour Survey


def mhlw_url(data_month: date) -> str:
    """Preliminary release workbook for a data month (folders by Reiwa year: 2019 = r01)."""
    reiwa = data_month.year - 2018
    ym = f"{data_month.year % 100:02d}{data_month.month:02d}"
    return f"https://www.mhlw.go.jp/toukei/itiran/roudou/monthly/r{reiwa:02d}/{ym}p/xls/{ym}p.xlsx"


def parse_mhlw_real_wages(sheet: pd.DataFrame) -> dict[date, float]:
    """Sheet 賃金指数, first block (establishments with 5+ employees): column 4 is the real
    year-on-year change of total cash earnings (deflated by CPI excluding imputed rent).
    Month rows read "2025年７月", then "８月" ... until the first note line."""
    import unicodedata

    out: dict[date, float] = {}
    year = None
    for _, row in sheet.iterrows():
        cells = [unicodedata.normalize("NFKC", str(c)).strip() for c in row.tolist()]
        label = cells[0] or (cells[1] if len(cells) > 1 else "")
        if label.startswith("注") or (out and re.fullmatch(r"\d{4}年", label)):
            break  # the next block (other establishment sizes / worker types) starts with annual rows again
        m = re.match(r"(\d{4})年\s*(\d{1,2})\s*月", label)
        if m:
            year, month = int(m.group(1)), int(m.group(2))
        else:
            m = re.match(r"(\d{1,2})\s*月", label)
            if not (m and year):
                continue
            month = int(m.group(1))
        value = to_float(cells[4]) if len(cells) > 4 else None
        if value is not None:
            out[date(year, month, 1)] = value
    return out


@register
class MhlwRealWages(Provider):
    """MHLW Monthly Labour Survey preliminary workbook (xlsx). code = real_total_yoy. Each
    workbook carries the latest 13 months, so a first load (BACKFILL=1) also reads one
    workbook per earlier year."""

    name = "MHLW"
    batch = True
    supports_backfill = True

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        today = _today()
        month = date(today.year, today.month, 1)
        values: dict[date, float] = {}
        latest = None
        for back in range(1, 5):  # the newest preliminary release (data month m is published early in m+2)
            data_month = (month - timedelta(days=28 * back)).replace(day=1)
            parsed = self._read(data_month)
            if parsed:
                latest = data_month
                values.update(parsed)
                break
        if latest and self.env.get("BACKFILL"):
            d = date(latest.year - 1, latest.month, 1)
            while d >= start.replace(day=1) and d.year >= 2019:
                for k, v in self._read(d).items():
                    values.setdefault(k, v)  # newer workbooks carry revised values
                d = date(d.year - 1, d.month, 1)
        out = []
        for d in defs:
            obs = [Observation(k, v) for k, v in sorted(values.items()) if k >= start]
            out.append(FetchResult(d.key, obs, "ok" if obs else "error", "" if obs else "no MHLW workbook found"))
        return out

    def _read(self, data_month: date) -> dict[date, float]:
        try:
            r = self.session.get(mhlw_url(data_month), timeout=(15, 60), headers={"User-Agent": BROWSER_UA})
        except Exception:  # noqa: BLE001
            return {}
        if r.status_code != 200 or r.content[:2] != b"PK":
            return {}
        sheets = pd.read_excel(io.BytesIO(r.content), sheet_name=None, header=None, dtype=str)
        sheet = sheets.get("賃金指数")
        return parse_mhlw_real_wages(sheet.fillna("")) if sheet is not None else {}


# --------------------------------------------------------------------------- Bank of England Decision Maker Panel

MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
               "november", "december"]


def dmp_url(release_month: date) -> str:
    return ("https://www.bankofengland.co.uk/-/media/boe/files/decision-maker-panel-survey/"
            f"{release_month.year}/monthly-dmp-data-{MONTH_NAMES[release_month.month - 1]}-{release_month.year}.xlsx")


def parse_dmp_sheet(sheet: pd.DataFrame, group: str) -> dict[date, float]:
    """'Quarterly average' column of the Realised or Expected group (three-month average of
    the mean). Rows are dated by survey month, e.g. "Sep-25"."""
    import unicodedata

    rows = [[unicodedata.normalize("NFKC", str(c)).strip() for c in r] for r in sheet.fillna("").values.tolist()]

    def is_avg(cell: str) -> bool:
        c = " ".join(cell.lower().replace("-", " ").split())
        return "quarterly average" in c or "3 month average" in c or "three month average" in c

    group_row = next((r for r in rows if any(c.lower().startswith("realised") for c in r)
                      and any(c.lower().startswith("expected") for c in r)), None)
    sub_row = next((r for r in rows if any(is_avg(c) for c in r)), None)
    if group_row is None or sub_row is None:
        found = [c for r in rows[:12] for c in r if c][:12]
        raise ProviderError(f"DMP sheet layout changed: no Realised/Expected header or average column; top cells {found}")
    starts = sorted((i, c.lower().split()[0]) for i, c in enumerate(group_row) if c.lower().startswith(("realised", "expected")))
    bounds = {name: (i, starts[k + 1][0] if k + 1 < len(starts) else len(sub_row)) for k, (i, name) in enumerate(starts)}
    lo, hi = bounds[group]
    col = next((i for i in range(lo, min(hi, len(sub_row))) if is_avg(sub_row[i])), None)
    if col is None:
        raise ProviderError(f"DMP: no average column under {group!r}")
    out = {}
    for r in rows:
        try:
            when = datetime.strptime(r[0], "%b-%y").date()
        except ValueError:
            continue
        v = to_float(r[col]) if col < len(r) else None
        if v is not None:
            out[when] = v
    return out


@register
class BoeDmp(Provider):
    """Bank of England Decision Maker Panel monthly data workbook. code = "<sheet>|<group>",
    e.g. "Price growth|expected" or "Wage growth|realised" (three-month averages)."""

    name = "DMP"
    batch = True

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        today = _today()
        body = None
        for back in range(0, 4):
            month = (date(today.year, today.month, 1) - timedelta(days=28 * back)).replace(day=1)
            try:
                r = self.session.get(dmp_url(month), timeout=(15, 90), headers={"User-Agent": BROWSER_UA})
            except Exception:  # noqa: BLE001
                continue
            if r.status_code == 200 and r.content[:2] == b"PK":
                body = r.content
                break
        if body is None:
            raise ProviderError("no DMP monthly workbook found for the last 4 months")
        sheets = pd.read_excel(io.BytesIO(body), sheet_name=None, header=None, dtype=str)
        by_name = {name.strip(): frame for name, frame in sheets.items()}
        out = []
        for d in defs:
            sheet_name, group = d.code.split("|")
            frame = by_name.get(sheet_name)
            if frame is None:
                out.append(FetchResult(d.key, [], "error", f"sheet {sheet_name!r} missing"))
                continue
            series = parse_dmp_sheet(frame, group)
            obs = [Observation(k, v) for k, v in sorted(series.items()) if k >= start]
            out.append(FetchResult(d.key, obs, "ok" if obs else "empty"))
        return out


def _ff_number(text: str) -> float | None:
    s = (text or "").strip().replace(",", "")
    if not s:
        return None
    mult = 1.0
    if s[-1:] in "KMBT" and s[:-1]:
        mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[s[-1]]
        s = s[:-1]
    s = s.rstrip("%")
    v = to_float(s)
    return None if v is None else v * mult


@register
class ForexFactoryCalendar(Provider):
    """Forex Factory weekly calendar (third-party compiled consensus; current week
    only, so the warehouse accumulates snapshots). code = "<country>|<title>|forecast"
    or "...|previous". obs_date = event date (US Eastern); values as published
    (K suffix → thousands × 1000, % stripped)."""

    name = "FFCAL"
    batch = True
    URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        events = json.loads(self.get(self.URL, headers={"User-Agent": BROWSER_UA}).decode("utf-8"))
        index: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for e in events:
            index[(e.get("country", ""), e.get("title", ""))].append(e)
        out = []
        for d in defs:
            country, title, field = d.code.split("|")
            obs = []
            for e in index.get((country, title), []):
                when = datetime.fromisoformat(e["date"]).date()
                v = _ff_number(e.get(field, ""))
                if v is not None:
                    obs.append(Observation(when, v / float(d.params.get("scale", 1))))
            out.append(FetchResult(d.key, obs, "ok" if obs else "empty", "" if obs else "not on this week's calendar"))
        return out
