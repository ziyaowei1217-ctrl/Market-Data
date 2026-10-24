"""Official / free data providers.

Each provider turns a list of ``SeriesDef`` into observations. Series codes are
documented next to each class; ``catalog/series.csv`` holds the concrete list.
"""

from __future__ import annotations

import io
import json
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Sequence

import numpy as np
import pandas as pd

from ..db.store import Observation
from .base import FetchResult, Provider, ProviderError, SeriesDef, obs_from_pairs, register, to_float


def _today() -> date:
    return datetime.now(timezone.utc).date()


# --------------------------------------------------------------------------- FRED / ALFRED


@register
class Fred(Provider):
    """code = FRED series id. With FRED_API_KEY uses the API (and ALFRED vintages
    when the series is flagged ``vintages``); without a key falls back to the
    public fredgraph CSV (latest values only)."""

    name = "FRED"
    API = "https://api.stlouisfed.org/fred/series/observations"
    CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        key = self.env.get("FRED_API_KEY")
        if not key:
            frame = self.get_csv(self.CSV, {"id": d.code, "cosd": start.isoformat()})
            date_col, value_col = frame.columns[0], frame.columns[1]
            return obs_from_pairs(zip(frame[date_col], frame[value_col]), start)
        params = {
            "series_id": d.code, "api_key": key, "file_type": "json",
            "observation_start": start.isoformat(), "limit": 100000,
        }
        if d.vintages:
            params.update({"realtime_start": "1776-07-04", "realtime_end": "9999-12-31"})
        payload = self.get_json(self.API, params)
        time.sleep(0.5)  # FRED allows 120 requests/minute
        out = []
        for row in payload.get("observations", []):
            value = to_float(row.get("value"))
            if value is None:
                continue
            realtime = date.fromisoformat(row["realtime_start"]) if d.vintages else None
            out.append(Observation(date.fromisoformat(row["date"]), value, realtime))
        return out


# --------------------------------------------------------------------------- U.S. Treasury


@register
class TreasuryFiscal(Provider):
    """Fiscal Data API. code = free label; params:
    endpoint, filter, date_field, value_field, [scale], [agg=sum|last]."""

    name = "TSY"
    BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        p = d.params
        date_field = p.get("date_field", "record_date")
        filters = [f"{date_field}:gte:{start.isoformat()}"]
        if p.get("filter"):
            filters.append(p["filter"])
        fields = sorted({date_field, *str(p["value_field"]).split("+")})
        rows: list[dict] = []
        page = 1
        while True:
            payload = self.get_json(
                self.BASE + p["endpoint"],
                {"filter": ",".join(filters), "fields": ",".join(fields), "sort": date_field,
                 "page[size]": 10000, "page[number]": page, "format": "json"},
            )
            rows.extend(payload.get("data", []))
            total_pages = int(payload.get("meta", {}).get("total-pages", 1) or 1)
            if page >= total_pages:
                break
            page += 1
        scale = float(p.get("scale", 1.0))
        grouped: dict[date, list[float]] = defaultdict(list)
        for row in rows:
            parts = [to_float(row.get(f)) for f in str(p["value_field"]).split("+")]
            if any(v is None for v in parts):
                continue
            grouped[date.fromisoformat(row[date_field][:10])].append(sum(parts) * scale)  # type: ignore[arg-type]
        if p.get("align") == "month_start":
            aligned: dict[date, list[float]] = defaultdict(list)
            for k, v in grouped.items():
                aligned[k.replace(day=1)].extend(v)
            grouped = aligned
        agg = p.get("agg", "last")
        return [
            Observation(k, (sum(v) if agg == "sum" else v[-1]))
            for k, v in sorted(grouped.items())
        ]


@register
class TreasuryCurve(Provider):
    """home.treasury.gov daily curves. code = column label, e.g. "10 Yr";
    params.type = daily_treasury_yield_curve | daily_treasury_real_yield_curve."""

    name = "TSYCURVE"
    batch = True
    URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        by_type: dict[str, list[SeriesDef]] = defaultdict(list)
        for d in defs:
            by_type[d.params.get("type", "daily_treasury_yield_curve")].append(d)
        results = []
        for curve_type, items in by_type.items():
            frames = []
            for year in range(start.year, _today().year + 1):
                body = self.get(
                    self.URL.format(year=year),
                    {"type": curve_type, "field_tdr_date_value": year, "page": "", "_format": "csv"},
                )
                if body.strip():
                    frames.append(pd.read_csv(io.BytesIO(body)))
            frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            for d in items:
                if frame.empty or d.code not in frame.columns:
                    results.append(FetchResult(d.key, [], "error", f"column {d.code!r} not in curve file"))
                    continue
                obs = obs_from_pairs(zip(pd.to_datetime(frame["Date"]), frame[d.code]), start)
                results.append(FetchResult(d.key, obs, "ok" if obs else "empty"))
        return results


# --------------------------------------------------------------------------- New York Fed


@register
class NyFedRates(Provider):
    """markets.newyorkfed.org reference rates. code = "<path>:<field>", e.g.
    "secured/sofr:percentRate", "unsecured/effr:volumeInBillions"."""

    name = "NYFED"
    batch = True
    URL = "https://markets.newyorkfed.org/api/rates/{path}/search.json"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        by_path: dict[str, list[SeriesDef]] = defaultdict(list)
        for d in defs:
            by_path[d.code.split(":")[0]].append(d)
        results = []
        for path, items in by_path.items():
            payload = self.get_json(
                self.URL.format(path=path), {"startDate": start.isoformat(), "endDate": _today().isoformat()}
            )
            rows = payload.get("refRates", [])
            for d in items:
                field = d.code.split(":")[1]
                obs = obs_from_pairs(((r["effectiveDate"], r.get(field)) for r in rows), start)
                results.append(FetchResult(d.key, sorted(obs, key=lambda o: o.obs_date), "ok" if obs else "empty"))
        return results


@register
class NyFedAcm(Provider):
    """ACM term premia workbook. code = column (ACMTP10, ACMRNY05, ACMY02 ...)."""

    name = "ACM"
    batch = True
    URL = "https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        body = self.get(self.URL)
        frame = None
        for sheet in pd.read_excel(io.BytesIO(body), sheet_name=None).values():
            cols = [str(c).strip().upper() for c in sheet.columns]
            if "DATE" in cols and any(c.startswith("ACMTP") for c in cols):
                sheet.columns = cols
                frame = sheet
                break
        if frame is None:
            raise ProviderError("ACM workbook layout changed: no sheet with DATE and ACMTP columns")
        dates = pd.to_datetime(frame["DATE"], format="mixed", dayfirst=True)
        results = []
        for d in defs:
            col = d.code.upper()
            if col not in frame.columns:
                results.append(FetchResult(d.key, [], "error", f"{col} missing from ACM workbook"))
                continue
            obs = obs_from_pairs(zip(dates, frame[col]), start)
            results.append(FetchResult(d.key, obs, "ok" if obs else "empty"))
        return results


# --------------------------------------------------------------------------- CFTC


@register
class Cftc(Provider):
    """CFTC public reporting (Socrata). code = "<dataset>:<contract code>:<field>".
    Datasets: gpe5-46if (TFF futures only), 72hh-3qpy (Disaggregated futures only)."""

    name = "CFTC"
    batch = True
    URL = "https://publicreporting.cftc.gov/resource/{dataset}.json"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        groups: dict[tuple[str, str], list[SeriesDef]] = defaultdict(list)
        for d in defs:
            dataset, contract, _ = d.code.split(":")
            groups[(dataset, contract)].append(d)
        results = []
        for (dataset, contract), items in groups.items():
            rows = self.get_json(
                self.URL.format(dataset=dataset),
                {
                    "$where": f"cftc_contract_market_code='{contract}' AND report_date_as_yyyy_mm_dd >= '{start.isoformat()}T00:00:00'",
                    "$order": "report_date_as_yyyy_mm_dd",
                    "$limit": 50000,
                },
            )
            for d in items:
                field = d.code.split(":")[2]
                obs = obs_from_pairs(((r["report_date_as_yyyy_mm_dd"][:10], r.get(field)) for r in rows), start)
                status = "ok" if obs else ("error" if rows and field not in rows[0] else "empty")
                results.append(FetchResult(d.key, obs, status, "" if obs else f"field {field} not found"))
        return results


# --------------------------------------------------------------------------- BLS


@register
class Bls(Provider):
    """BLS Public Data API v2 (BLS_API_KEY recommended; v1 without key is limited
    to 25 requests/day). code = BLS series id."""

    name = "BLS"
    batch = True

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        key = self.env.get("BLS_API_KEY")
        url = "https://api.bls.gov/publicAPI/v2/timeseries/data/" if key else "https://api.bls.gov/publicAPI/v1/timeseries/data/"
        chunk = 50 if key else 25
        span = 20 if key else 10
        results: dict[str, list[Observation]] = defaultdict(list)
        messages: dict[str, str] = {}
        codes = [d.code for d in defs]
        end_year = _today().year
        for i in range(0, len(codes), chunk):
            for y0 in range(start.year, end_year + 1, span):
                body = {"seriesid": codes[i:i + chunk], "startyear": str(y0), "endyear": str(min(y0 + span - 1, end_year))}
                if key:
                    body["registrationkey"] = key
                payload = _post_json(self, url, body)
                if payload.get("status") != "REQUEST_SUCCEEDED":
                    raise ProviderError(f"BLS: {payload.get('status')} {payload.get('message')}")
                for series in payload.get("Results", {}).get("series", []):
                    for row in series.get("data", []):
                        period = row.get("period", "")
                        obs_date = _bls_period(row.get("year"), period)
                        value = to_float(row.get("value"))
                        if obs_date and value is not None and obs_date >= start:
                            results[series["seriesID"]].append(Observation(obs_date, value))
                for msg in payload.get("message", []) or []:
                    for code in codes[i:i + chunk]:
                        if code in msg:
                            messages[code] = msg
        out = []
        for d in defs:
            obs = sorted({o.obs_date: o for o in results.get(d.code, [])}.values(), key=lambda o: o.obs_date)
            out.append(FetchResult(d.key, obs, "ok" if obs else "error", messages.get(d.code, "" if obs else "no data")))
        return out


def _bls_period(year: Any, period: str) -> date | None:
    if not year or not period:
        return None
    y = int(year)
    if period.startswith("M") and period != "M13":
        return date(y, int(period[1:]), 1)
    if period.startswith("Q") and period != "Q05":
        return date(y, 3 * (int(period[1:]) - 1) + 1, 1)
    if period == "A01":
        return date(y, 1, 1)
    return None


def _post_json(provider: Provider, url: str, body: dict, attempts: int = 4) -> Any:
    delay = 2.0
    for attempt in range(1, attempts + 1):
        try:
            response = provider.session.post(url, json=body, timeout=(15, 120))
            if response.status_code in (429, 500, 502, 503, 504) and attempt < attempts:
                time.sleep(delay)
                delay *= 2.5
                continue
            response.raise_for_status()
            return response.json()
        except (ValueError, OSError) as error:
            if attempt >= attempts:
                raise ProviderError(f"POST failed: {type(error).__name__}") from None
            time.sleep(delay)
            delay *= 2.5
    raise ProviderError("POST failed")


# --------------------------------------------------------------------------- BEA


@register
class Bea(Provider):
    """BEA API (BEA_API_KEY). code = "<dataset>:<table>:<SeriesCode>", e.g.
    "NIUnderlyingDetail:U20404:DHSGRG" (monthly PCE housing price index).
    Series codes are BEA's stable identifiers (FRED ids are built from them)."""

    name = "BEA"
    env_keys = ("BEA_API_KEY",)
    batch = True
    URL = "https://apps.bea.gov/api/data"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        groups: dict[tuple[str, str, str], list[SeriesDef]] = defaultdict(list)
        for d in defs:
            dataset, table, _ = d.code.split(":")
            groups[(dataset, table, d.frequency or "M")].append(d)
        out = []
        years = ",".join(str(y) for y in range(start.year, _today().year + 1))
        for (dataset, table, freq), items in groups.items():
            payload = self.get_json(self.URL, {
                "UserID": self.env["BEA_API_KEY"], "method": "GetData", "DataSetName": dataset,
                "TableName": table, "Frequency": freq, "Year": years, "ResultFormat": "JSON",
            })
            results = payload.get("BEAAPI", {}).get("Results", {})
            if isinstance(results, list):
                results = results[0] if results else {}
            if "Error" in results or "Error" in payload.get("BEAAPI", {}):
                err = results.get("Error") or payload["BEAAPI"]["Error"]
                raise ProviderError(f"BEA: {str(err)[:200]}")
            rows = results.get("Data", [])
            for d in items:
                code = d.code.split(":")[2]
                obs = []
                for r in rows:
                    if code.startswith("line="):
                        if str(r.get("LineNumber")) != code[5:]:
                            continue
                    elif r.get("SeriesCode") != code:
                        continue
                    obs_date = _period_to_date(str(r.get("TimePeriod", "")))
                    value = to_float(r.get("DataValue"))
                    if obs_date and value is not None and obs_date >= start:
                        obs.append(Observation(obs_date, value))
                obs = sorted({o.obs_date: o for o in obs}.values(), key=lambda o: o.obs_date)
                out.append(FetchResult(d.key, obs, "ok" if obs else "error", "" if obs else f"SeriesCode {code} not in {table}"))
        return out


# --------------------------------------------------------------------------- EIA


@register
class Eia(Provider):
    """EIA Open Data v2 via the legacy series-id route. code = e.g. PET.WCESTUS1.W."""

    name = "EIA"
    env_keys = ("EIA_API_KEY",)
    URL = "https://api.eia.gov/v2/seriesid/{code}"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        payload = self.get_json(
            self.URL.format(code=d.code), {"api_key": self.env["EIA_API_KEY"], "start": start.isoformat(), "length": 5000}
        )
        rows = payload.get("response", {}).get("data", [])
        out = []
        for row in rows:
            period = str(row.get("period"))
            obs_date = _period_to_date(period)
            value = to_float(row.get("value"))
            if obs_date and value is not None and obs_date >= start:
                out.append(Observation(obs_date, value))
        return sorted(out, key=lambda o: o.obs_date)


def _period_to_date(period: str) -> date | None:
    """2026-10-17 | 2026-09 | 2026-Q3 | 2026Q3 | 2026-M09 | 2026M09 | 2026."""
    p = period.strip().replace(" ", "")
    try:
        if len(p) == 10:
            return date.fromisoformat(p)
        if len(p) == 7 and p[4] == "-" and p[5:].isdigit():
            return date(int(p[:4]), int(p[5:]), 1)
        if "Q" in p:
            y, q = p.replace("-", "").split("Q")
            return date(int(y), 3 * (int(q) - 1) + 1, 1)
        if "M" in p:
            y, m = p.replace("-", "").split("M")
            return date(int(y), int(m), 1)
        if len(p) == 4 and p.isdigit():
            return date(int(p), 1, 1)
    except ValueError:
        return None
    return None


# --------------------------------------------------------------------------- ECB / Eurostat


@register
class Ecb(Provider):
    """ECB Data Portal. code = "<flow>/<key>", e.g. "EXR/D.USD.EUR.SP00.A"."""

    name = "ECB"
    URL = "https://data-api.ecb.europa.eu/service/data/{code}"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        frame = self.get_csv(self.URL.format(code=d.code), {"startPeriod": start.isoformat(), "format": "csvdata"})
        return [o for o in (
            Observation(dt, v) for dt, v in (
                (_period_to_date(str(p)), to_float(x)) for p, x in zip(frame["TIME_PERIOD"], frame["OBS_VALUE"])
            ) if dt and v is not None
        ) if o.obs_date >= start]


@register
class Eurostat(Provider):
    """Eurostat dissemination API (JSON-stat). code = dataset; params = dimension filters."""

    name = "EUROSTAT"
    URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        dataset = d.params.get("dataset", d.code)
        params = {"format": "JSON", "lang": "EN", **{k: v for k, v in d.params.items() if k != "dataset"}}
        payload = self.get_json(self.URL.format(dataset=dataset), params)
        dims = payload["id"]
        sizes = payload["size"]
        for dim, size in zip(dims, sizes):
            if dim != "time" and size != 1:
                raise ProviderError(f"Eurostat filter leaves {size} values for dimension {dim}")
        time_index = payload["dimension"]["time"]["category"]["index"]
        values = payload.get("value", {})
        out = []
        for period, pos in time_index.items():
            v = values.get(str(pos))
            obs_date = _period_to_date(period)
            if v is not None and obs_date and obs_date >= start:
                out.append(Observation(obs_date, float(v)))
        return sorted(out, key=lambda o: o.obs_date)


# --------------------------------------------------------------------------- national sources


@register
class Ons(Provider):
    """UK ONS time series. code = CDID; params.uri = timeseries uri; params.period = months|quarters|years."""

    name = "ONS"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        payload = self.get_json("https://www.ons.gov.uk" + d.params["uri"] + "/data")
        period = d.params.get("period", "months")
        out = []
        for row in payload.get(period, []):
            obs_date = _ons_date(row.get("date", ""), period)
            value = to_float(row.get("value"))
            if obs_date and value is not None and obs_date >= start:
                out.append(Observation(obs_date, value))
        return out


def _ons_date(text: str, period: str) -> date | None:
    try:
        if period == "months":
            return datetime.strptime(text.title(), "%Y %b").date()
        if period == "quarters":
            y, q = text.split(" Q")
            return date(int(y), 3 * (int(q) - 1) + 1, 1)
        return date(int(text), 1, 1)
    except (ValueError, TypeError):
        return None


@register
class StatCan(Provider):
    """Statistics Canada WDS. code = vector id (digits, without the leading v)."""

    name = "STATCAN"
    batch = True
    URL = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        months = (_today().year - start.year + 1) * 12
        payload = _post_json(self, self.URL, [{"vectorId": int(d.code), "latestN": months} for d in defs])
        by_vector = {}
        for item in payload:
            obj = item.get("object") or {}
            by_vector[str(obj.get("vectorId"))] = obj.get("vectorDataPoint", [])
        out = []
        for d in defs:
            points = by_vector.get(d.code, [])
            obs = obs_from_pairs(((p["refPer"], p.get("value")) for p in points), start)
            out.append(FetchResult(d.key, obs, "ok" if obs else "error", "" if obs else "vector not returned"))
        return out


@register
class Bcb(Provider):
    """Banco Central do Brasil SGS. code = series number (432 Selic target, 13522 IPCA 12m)."""

    name = "BCB"
    URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        rows = self.get_json(
            self.URL.format(code=d.code),
            {"formato": "json", "dataInicial": start.strftime("%d/%m/%Y"), "dataFinal": _today().strftime("%d/%m/%Y")},
        )
        return obs_from_pairs(((datetime.strptime(r["data"], "%d/%m/%Y"), r["valor"]) for r in rows), start)


@register
class BankOfCanada(Provider):
    """Bank of Canada Valet. code = series name (V39079 target overnight rate)."""

    name = "BOC"
    URL = "https://www.bankofcanada.ca/valet/observations/{code}/json"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        payload = self.get_json(self.URL.format(code=d.code), {"start_date": start.isoformat()})
        return obs_from_pairs(((r["d"], (r.get(d.code) or {}).get("v")) for r in payload.get("observations", [])), start)


@register
class BankOfEngland(Provider):
    """Bank of England IADB. code = series code (IUDBEDR Bank Rate)."""

    name = "BOE"
    URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        body = self.get(
            self.URL,
            {"csv.x": "yes", "Datefrom": start.strftime("%d/%b/%Y"), "Dateto": "now", "SeriesCodes": d.code,
             "CSVF": "TN", "UsingCodes": "Y", "VPD": "Y", "VFD": "N"},
            headers={"User-Agent": "Mozilla/5.0 (compatible; CapitalWeekly-Warehouse/1.0)"},
        )
        frame = pd.read_csv(io.BytesIO(body))
        return obs_from_pairs(zip(pd.to_datetime(frame.iloc[:, 0], format="%d %b %Y"), frame.iloc[:, 1]), start)


@register
class MofJapan(Provider):
    """Japan MOF JGB yields (daily). code = column label, e.g. "10Y"."""

    name = "MOFJP"
    batch = True
    URLS = (
        "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv",
        "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv",
    )

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        frames = []
        for url in self.URLS:
            text = self.get(url).decode("cp932", errors="replace")
            lines = text.splitlines()
            header = next((i for i, line in enumerate(lines) if line.split(",")[0].strip() in ("Date", "基準日")), None)
            if header is None:
                raise ProviderError(f"MOF CSV layout changed: no Date header in {url}")
            frame = pd.read_csv(io.StringIO("\n".join(lines[header:])))
            frame.columns = [str(c).strip() for c in frame.columns]
            frame = frame.rename(columns={frame.columns[0]: "Date"})
            frames.append(frame)
        frame = pd.concat(frames, ignore_index=True)
        dates = pd.to_datetime(frame["Date"].map(_jp_date), errors="coerce")
        out = []
        for d in defs:
            if d.code not in frame.columns:
                out.append(FetchResult(d.key, [], "error", f"column {d.code} missing"))
                continue
            obs = obs_from_pairs(((dt, v) for dt, v in zip(dates, frame[d.code]) if pd.notna(dt)), start)
            dedup = sorted({o.obs_date: o for o in obs}.values(), key=lambda o: o.obs_date)
            out.append(FetchResult(d.key, dedup, "ok" if dedup else "empty"))
        return out


_JP_ERAS = {"M": 1867, "T": 1911, "S": 1925, "H": 1988, "R": 2018}


def _jp_date(text: Any) -> str | None:
    """'2026/10/23', '2026-10-23' or Japanese era 'R8.10.23' -> ISO date."""
    s = str(text).strip()
    if s and s[0] in _JP_ERAS and "." in s:
        try:
            y, m, d = s[1:].split(".")
            return f"{_JP_ERAS[s[0]] + int(y):04d}-{int(m):02d}-{int(d):02d}"
        except ValueError:
            return None
    return s.replace("/", "-") if s else None


# --------------------------------------------------------------------------- market data (free)


@register
class Cboe(Provider):
    """Cboe daily index history CSV. code = index symbol (VIX, VIX9D, VVIX, OVX ...)."""

    name = "CBOE"
    URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{code}_History.csv"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        frame = self.get_csv(self.URL.format(code=d.code))
        frame.columns = [str(c).strip().upper() for c in frame.columns]
        value_col = "CLOSE" if "CLOSE" in frame.columns else frame.columns[-1]
        return obs_from_pairs(zip(pd.to_datetime(frame["DATE"], format="mixed"), frame[value_col]), start)


@register
class Yahoo(Provider):
    """Yahoo Finance chart API (free, delayed, unofficial). code = ticker.
    Used only for index levels that have no free official feed; every value
    is labelled with this source in the catalog."""

    name = "YAHOO"
    URL = "https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        period1 = int(datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp())
        period2 = int(datetime.now(timezone.utc).timestamp()) + 86400
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko)"}
        payload = self.get_json(
            self.URL.format(ticker=d.code),
            {"period1": period1, "period2": period2, "interval": "1d", "events": "history", "includeAdjustedClose": "false"},
            headers=headers,
        )
        time.sleep(1.0)
        result = (payload.get("chart", {}).get("result") or [None])[0]
        if result and len(result.get("timestamp") or []) < 10:
            # Some index tickers only return history for range= queries.
            for host in ("query1", "query2"):
                try:
                    retry = self.get_json(
                        self.URL.format(ticker=d.code).replace("query2", host),
                        {"range": "10y", "interval": "1d"}, headers=headers,
                    )
                except ProviderError:
                    continue
                time.sleep(1.0)
                candidate = (retry.get("chart", {}).get("result") or [None])[0]
                if candidate and len(candidate.get("timestamp") or []) > len(result.get("timestamp") or []):
                    result = candidate
                    break
        if not result:
            raise ProviderError(f"Yahoo: {payload.get('chart', {}).get('error')}")
        meta = result.get("meta", {})
        offset = int(meta.get("gmtoffset", 0))
        stamps = result.get("timestamp") or []
        closes = (result.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
        out = {}
        for ts, close in zip(stamps, closes):
            if close is None:
                continue
            local = datetime.fromtimestamp(ts + offset, tz=timezone.utc).date()
            if local >= start:
                out[local] = Observation(local, float(close))
        # Drop today's intraday bar if the market has not closed.
        regular = meta.get("currentTradingPeriod", {}).get("regular", {})
        end = regular.get("end")
        if end and datetime.now(timezone.utc).timestamp() < end:
            out.pop(datetime.fromtimestamp(end + offset, tz=timezone.utc).date(), None)
        return [out[k] for k in sorted(out)]


# --------------------------------------------------------------------------- index publishers


@register
class Msci(Provider):
    """MSCI end-of-day index levels (endpoint behind msci.com charts; MSCI terms:
    internal, non-commercial use). code = "<index code>:<STRD|NETR|GRTR>:<currency>",
    params.frequency = DAILY (default) or END_OF_MONTH, params.start = YYYY-MM-DD override."""

    name = "MSCI"
    URL = "https://app2.msci.com/products/service/index/indexmaster/getLevelDataForGraph"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        code, variant, currency = d.code.split(":")
        begin = date.fromisoformat(d.params["start"]) if d.params.get("start") else start
        begin = max(begin, date(1997, 1, 1))
        payload = self.get_json(self.URL, {
            "currency_symbol": currency, "index_variant": variant,
            "start_date": begin.strftime("%Y%m%d"), "end_date": _today().strftime("%Y%m%d"),
            "data_frequency": d.params.get("frequency", "DAILY"), "baseValue": "false", "index_codes": code,
        })
        if payload.get("error_code"):
            raise ProviderError(f"MSCI error {payload.get('error_code')}: {str(payload.get('error_message'))[:120]}")
        rows = (payload.get("indexes") or {}).get("INDEX_LEVELS") or []
        time.sleep(0.5)
        return obs_from_pairs(((datetime.strptime(str(r["calc_date"]), "%Y%m%d"), r.get("level_eod")) for r in rows), begin)


@register
class SpDji(Provider):
    """S&P Dow Jones Indices data widget JSON. code = "<indexId>:levels" (≈10y daily
    levels) or "<indexId>:<field>" for month-end characteristics:
    topNConstituentWeight | marketCap."""

    name = "SPDJI"
    batch = True
    URL = "https://www.spglobal.com/spdji/en/util/redesign/index-data/get-performance-data-for-datawidget-redesign.dot"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        by_id: dict[str, list[SeriesDef]] = defaultdict(list)
        for d in defs:
            by_id[d.code.split(":")[0]].append(d)
        out = []
        for index_id, items in by_id.items():
            payload = self.get_json(self.URL, {"indexId": index_id, "language_id": 1},
                                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0)", "Referer": "https://www.spglobal.com/spdji/en/"})
            for d in items:
                field = d.code.split(":", 1)[1]
                obs: list[Observation] = []
                if field == "levels":
                    for row in (payload.get("indexLevelsHolder") or {}).get("indexLevels") or []:
                        when = datetime.fromtimestamp(int(row["effectiveDate"]) / 1000, tz=timezone.utc).date()
                        value = to_float(row.get("indexValue"))
                        if value is not None and when >= start:
                            obs.append(Observation(when, value))
                else:
                    value, as_of = _spdji_field(payload, field)
                    if value is not None and as_of is not None:
                        obs.append(Observation(as_of, value))
                obs = sorted({o.obs_date: o for o in obs}.values(), key=lambda o: o.obs_date)
                out.append(FetchResult(d.key, obs, "ok" if obs else "error", "" if obs else f"field {field} not found"))
        return out


def _spdji_field(payload: dict, field: str) -> tuple[float | None, date | None]:
    chars = payload.get("indexCharacteristics") or {}
    as_of = None
    for key in ("asOfDate", "asOfDateValue", "effectiveDate"):
        if chars.get(key):
            raw = chars[key]
            try:
                as_of = (datetime.fromtimestamp(int(raw) / 1000, tz=timezone.utc).date() if str(raw).isdigit()
                         else pd.Timestamp(raw).date())
            except (ValueError, TypeError):
                as_of = None
            break
    if field == "marketCap":
        rows = (payload.get("idsIndexCountryBreakdownHolder") or {}).get("idsIndexCountryBreakdown") or []
        total = sum(to_float(r.get("marketCap")) or 0.0 for r in rows) if rows else None
        return (total / 1e9 if total else None), as_of
    return to_float(chars.get(field)), as_of


@register
class Stoxx(Provider):
    """STOXX guest history files (rolling 3 months; the warehouse accumulates).
    code = symbol, e.g. sx5p (STOXX Europe 50 price, EUR)."""

    name = "STOXX"
    URL = "https://www.stoxx.com/documents/stoxxnet/Documents/Indices/Current/HistoricalData/h_3m{symbol}.txt"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        text = self.get(self.URL.format(symbol=d.code.lower())).decode("utf-8", errors="replace")
        pairs = []
        for line in text.splitlines():
            parts = [p.strip() for p in line.split(";")]
            if len(parts) >= 3 and parts[0][:2].isdigit():
                try:
                    pairs.append((datetime.strptime(parts[0], "%d.%m.%Y"), parts[2]))
                except ValueError:
                    continue
        return obs_from_pairs(pairs, start)


@register
class JpxTopix(Provider):
    """JPX daily index snapshot (no date field: stamped with the last Tokyo trading
    day on or before the fetch). code = TOPIX | TOPIX_TR."""

    name = "JPX"
    batch = True
    URL = "https://www.jpx.co.jp/market/indices/e_indices_stock_price3.txt"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        payload = json.loads(self.get(self.URL).decode("utf-8-sig", errors="replace"))
        flat: dict[str, Any] = {}

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                name = str(node.get("name") or node.get("indexName") or "")
                if name and "currentPrice" in node:
                    flat[name.upper()] = node
                for key, value in node.items():
                    if isinstance(value, dict) and "currentPrice" in value:
                        flat[str(key).upper()] = value
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(payload)
        tokyo_today = (datetime.now(timezone.utc) + timedelta(hours=9)).date()
        stamp = tokyo_today if tokyo_today.weekday() < 5 else tokyo_today - timedelta(days=tokyo_today.weekday() - 4)
        wanted = {"TOPIX": ("TOPIX",), "TOPIX_TR": ("TOPIX TOTAL RETURN INDEX", "TOPIX TOTAL RETURN", "TOPIXTR")}
        out = []
        for d in defs:
            node = next((flat[k] for k in wanted.get(d.code, (d.code,)) if k in flat), None)
            value = to_float(node.get("currentPrice")) if node else None
            obs = [Observation(stamp, value)] if value is not None else []
            out.append(FetchResult(d.key, obs, "ok" if obs else "error", "" if obs else f"{d.code} not in snapshot"))
        return out



# --------------------------------------------------------------------------- central banks (SDMX)


def _sdmx_csv_pairs(text: str) -> list[tuple[str, str]]:
    """Extract (period, value) from SDMX-CSV or simple 'date;value' text."""
    import csv as _csv

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    delimiter = ";" if lines[0].count(";") > lines[0].count(",") else ","
    rows = list(_csv.reader(lines, delimiter=delimiter))
    header = [h.strip().upper() for h in rows[0]]
    if "TIME_PERIOD" in header and "OBS_VALUE" in header:
        t, v = header.index("TIME_PERIOD"), header.index("OBS_VALUE")
        return [(r[t], r[v]) for r in rows[1:] if len(r) > max(t, v)]
    out = []
    for r in rows:
        if len(r) >= 2 and len(r[0]) >= 7 and r[0][:4].isdigit() and r[0][4] in "-/":
            out.append((r[0], r[1]))
    return out


@register
class Bundesbank(Provider):
    """Deutsche Bundesbank time-series API. code = "<flow>/<key>",
    e.g. "BBSSY/D.REN.EUR.A630.000000WT1010.A" (current 10Y Bund yield)."""

    name = "BBK"
    URL = "https://api.statistiken.bundesbank.de/rest/data/{code}"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        body = self.get(self.URL.format(code=d.code), {"format": "csv", "startPeriod": start.isoformat()},
                        headers={"Accept": "text/csv, application/vnd.sdmx.data+csv, */*"})
        pairs = _sdmx_csv_pairs(body.decode("utf-8-sig", errors="replace"))
        # Bundesbank CSV uses a decimal comma ("3,33"); never treat it as a thousands separator.
        return obs_from_pairs(((_period_to_date(p) or p, v.replace(".", "").replace(",", ".") if "," in v else v)
                               for p, v in pairs), start)


@register
class Bis(Provider):
    """BIS statistics API. code = "<dataflow>/<key>", e.g. "WS_CBPOL/D.JP" (policy rate)."""

    name = "BIS"
    URL = "https://stats.bis.org/api/v1/data/{code}/all"

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        body = self.get(self.URL.format(code=d.code), {"format": "csv", "startPeriod": start.isoformat()})
        pairs = _sdmx_csv_pairs(body.decode("utf-8-sig", errors="replace"))
        return obs_from_pairs(((_period_to_date(p) or p, v) for p, v in pairs), start)


@register
class Snb(Provider):
    """Swiss National Bank data portal cube (long CSV: "Date";"D0";"Value").
    code = "<cube>:<D0 code>", e.g. "rendoblid:10J0" (10-year Confederation bond yield)."""

    name = "SNB"
    batch = True
    URL = "https://data.snb.ch/api/cube/{cube}/data/csv/en"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        by_cube: dict[str, list[SeriesDef]] = defaultdict(list)
        for d in defs:
            by_cube[d.code.split(":")[0]].append(d)
        out = []
        for cube, items in by_cube.items():
            text = self.get(self.URL.format(cube=cube), {"fromDate": start.isoformat()}).decode("utf-8-sig", errors="replace")
            values: dict[str, list[tuple[str, str]]] = defaultdict(list)
            for line in text.splitlines():
                parts = [p.strip().strip('"') for p in line.split(";")]
                if len(parts) >= 3 and len(parts[0]) == 10 and parts[0][:4].isdigit():
                    values[parts[1]].append((parts[0], parts[2]))
            for d in items:
                obs = obs_from_pairs(values.get(d.code.split(":")[1], []), start)
                out.append(FetchResult(d.key, obs, "ok" if obs else "error", "" if obs else "dimension not found"))
        return out
