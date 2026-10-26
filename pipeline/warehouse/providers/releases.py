"""Headline numbers parsed from official press releases (checked against real
pages saved by inspect_sources.py): National Bureau of Statistics of China."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, timedelta
from typing import Sequence
from urllib.parse import urljoin

from ..db.store import Observation
from .base import FetchResult, Provider, ProviderError, SeriesDef, register
from .reports import BROWSER_UA, html_text

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
          "october", "november", "december"]
_MONTH_RE = "|".join(m.capitalize() for m in MONTHS)
QUARTERS = {"first": 1, "second": 2, "third": 3, "fourth": 4}

_UP = r"increased|rose|grew|went up|up|expanded|climbed"
_DOWN = r"decreased|declined|fell|dropped|went down|down|contracted"
_PCT = r"(?:%|percent|per cent)"
_YOY = re.compile(
    rf"(?P<verb>{_UP}|{_DOWN})\s+(?:by\s+)?(?P<num>\d+(?:\.\d+)?)\s*{_PCT}\s*(?:,\s*)?(?:year[- ]on[- ]year|y/y)"
    rf"|(?P<flat>remained (?:flat|unchanged)|was flat|unchanged|the same)\s+(?:as\s+)?(?:the same (?:period|month) )?(?:last year|year[- ]on[- ]year)",
    re.I,
)


def signed_yoy(text: str) -> float | None:
    """First 'rose/fell by X% year on year' (or 'remained flat') in ``text``."""
    m = _YOY.search(text)
    if not m:
        return None
    if m.group("flat"):
        return 0.0
    value = float(m.group("num"))
    return -value if re.fullmatch(_DOWN, m.group("verb"), re.I) else value


def title_month(title: str) -> date | None:
    """'Consumer Price Index in September 2026', '... from January to February 2025' → that (last) month."""
    hits = re.findall(rf"({_MONTH_RE})\b(?:\s+in)?\s*(\d{{4}})?", title)
    year = re.findall(r"(\d{4})", title)
    if not hits or not year:
        return None
    return date(int(year[-1]), MONTHS.index(hits[-1][0].lower()) + 1, 1)


def title_quarter(title: str) -> date | None:
    m = re.search(r"(First|Second|Third|Fourth) Quarter", title, re.I)
    y = re.search(r"(\d{4})", title)
    if not m or not y:
        return None
    return date(int(y.group(1)), 3 * (QUARTERS[m.group(1).lower()] - 1) + 1, 1)


def _body(text: str, title: str) -> str:
    """Release text after the dateline (skips the site header and repeated title)."""
    m = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", text)
    return text[m.end():] if m else text[text.find(title) + len(title):] if title in text else text


def _single_month(body: str, month: date) -> str:
    """Text from the sentence about the single month ('In September, ...'); for China's combined
    January–February releases, the 'From January to February' sentence."""
    name = MONTHS[month.month - 1].capitalize()
    pat = (rf"From January to February(?:\s+\d{{4}})?," if month.month == 2 else rf"In {name}(?:\s+\d{{4}})?,")
    hits = [m.start() for m in re.finditer(pat, body)]
    return body[hits[0]:] if hits else ""


def parse_nbs(kind: str, title: str, text: str) -> tuple[date, float] | None:
    body = _body(text, title)
    if kind == "gdp_yoy":
        period = title_quarter(title)
        m = re.search(r"\nGDP\s*\n((?:\s*\|\s*\n\s*-?[\d,.]+\s*\n)+)", body)
        if not period or not m:
            return None
        nums = re.findall(r"-?[\d,]+(?:\.\d+)?", m.group(1))
        if len(nums) < 2:
            return None
        return period, float(nums[len(nums) // 2].replace(",", ""))
    period = title_month(title)
    if period is None:
        return None
    if kind == "mfg_pmi":
        m = re.search(rf"(?:came in at|was|stood at|registered|reached|recorded)\s+(\d{{2}}(?:\.\d)?)\s*{_PCT}", body[:1500])
        return (period, float(m.group(1))) if m else None
    if kind in ("ip_yoy", "retail_yoy"):
        section = _single_month(body, period)
        if kind == "ip_yoy":
            m = re.search(r"value added of (?:the )?industrial enterprises", section[:600], re.I)
            section = section[m.start():] if m else ""
        value = signed_yoy(section[:600]) if section else None
        return (period, value) if value is not None else None
    value = signed_yoy(body[:800])  # CPI / PPI: the headline is the first y/y figure
    return (period, value) if value is not None else None


NBS_KINDS = {  # title prefix → series code
    "Consumer Price Index": "cpi_yoy",
    "Industrial Producer Price Ind": "ppi_yoy",
    "Producer Price Index": "ppi_yoy",
    "Industrial Production Operation": "ip_yoy",
    "Total Retail Sales of Consumer Goods": "retail_yoy",
    "Preliminary Accounting Results of GDP": "gdp_yoy",
    "Purchasing Managers' Index": "mfg_pmi",
    "Purchasing Managers Index": "mfg_pmi",
}


def nbs_kind(title: str) -> str | None:
    t = title.replace("’", "'").strip()
    return next((code for prefix, code in NBS_KINDS.items() if t.startswith(prefix)), None)


def parse_nbs_listing(html: str, base: str) -> list[tuple[str, date, str]]:
    """(title, url-date, absolute url) for each release link on a listing page."""
    out, seen = [], set()
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, flags=re.S | re.I):
        attrs = m.group(1)
        href = re.search(r"href=[\"']([^\"']*t(\d{8})_\d+\.html?)[\"']", attrs)
        if not href:
            continue
        title_attr = re.search(r"title=[\"']([^\"']+)[\"']", attrs)
        title = (title_attr.group(1) if title_attr else re.sub(r"<[^>]+>", "", m.group(2))).strip()
        title = re.sub(r"^\d+\.\s*", "", re.sub(r"\s+", " ", title))
        url = urljoin(base, href.group(1))
        if url in seen:
            continue
        seen.add(url)
        d = href.group(2)
        out.append((title, date(int(d[:4]), int(d[4:6]), int(d[6:])), url))
    return out


@register
class NbsReleases(Provider):
    """National Bureau of Statistics of China English press releases. code = cpi_yoy |
    ppi_yoy | ip_yoy | retail_yoy | gdp_yoy | mfg_pmi. Normal runs read the first two
    listing pages; a first load (env BACKFILL=1) walks the listing back (the site keeps
    about 34 pages, i.e. from early 2024)."""

    name = "NBS"
    batch = True
    supports_backfill = True
    LIST = "https://www.stats.gov.cn/english/PressRelease/"
    MAX_PAGES = 40

    def _get(self, url: str) -> bytes:
        return self.get(url, headers={"User-Agent": BROWSER_UA})

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        wanted = {d.code for d in defs}
        pages = self.MAX_PAGES if self.env.get("BACKFILL") else 2
        listing: list[tuple[str, date, str]] = []
        for i in range(pages):
            url = self.LIST + ("" if i == 0 else f"index_{i}.html")
            try:
                items = parse_nbs_listing(self._get(url).decode("utf-8", errors="replace"), url)
            except ProviderError:
                if i == 0:
                    raise
                break
            if not items:
                break
            listing.extend(items)
            if min(d for _, d, _ in items) < start - timedelta(days=40):
                break
        values: dict[str, dict[date, float]] = defaultdict(dict)
        failures = []
        for title, _, url in sorted(listing, key=lambda x: x[1]):  # oldest first: later releases overwrite
            kind = nbs_kind(title)
            if kind not in wanted:
                continue
            try:
                text, _ = html_text(self._get(url))
            except ProviderError as error:
                failures.append(f"{title}: {error}")
                continue
            parsed = parse_nbs(kind, title, text)
            if parsed is None:
                failures.append(f"unparsed: {title}")
                continue
            values[kind][parsed[0]] = parsed[1]
        out = []
        for d in defs:
            obs = [Observation(k, v) for k, v in sorted(values.get(d.code, {}).items()) if k >= start]
            note = f"{len(obs)} releases; {len(failures)} not parsed" + (f" (e.g. {failures[0][:80]})" if failures else "")
            out.append(FetchResult(d.key, obs, "ok" if obs else "empty", note))
        return out


def parse_aaii(text: str, today: date) -> dict[date, tuple[float, float, float]]:
    """'Reported Date | Bullish | Neutral | Bearish' table without years: the first row is
    the latest survey (on or before today); years roll back as months go back."""
    rows = re.findall(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s*\|\s*(\d+(?:\.\d+)?)%\s*\|\s*(\d+(?:\.\d+)?)%\s*\|\s*(\d+(?:\.\d+)?)%",
                      re.sub(r"\s*\r?\n\s*", " ", text))
    out: dict[date, tuple[float, float, float]] = {}
    year, prev_month = today.year, None
    for mon, day, bull, neutral, bear in rows:
        month = [m[:3] for m in MONTHS].index(mon.lower()) + 1
        if prev_month is None:
            year = today.year if (month, int(day)) <= (today.month, today.day) else today.year - 1
        elif month > prev_month:
            year -= 1
        prev_month = month
        out[date(year, month, int(day))] = (float(bull), float(neutral), float(bear))
    return out


@register
class AaiiSentiment(Provider):
    """AAII Sentiment Survey past-results table (about the latest 22 weeks; the warehouse
    accumulates). code = bullish | neutral | bearish | spread (bullish − bearish)."""

    name = "AAII"
    batch = True
    URL = "https://www.aaii.com/sentimentsurvey/sent_results"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        text, _ = html_text(self.get(self.URL, headers={"User-Agent": BROWSER_UA}))
        table = parse_aaii(text, date.today())
        if not table:
            raise ProviderError("AAII table not found")
        pick = {"bullish": lambda r: r[0], "neutral": lambda r: r[1], "bearish": lambda r: r[2],
                "spread": lambda r: round(r[0] - r[2], 4)}
        out = []
        for d in defs:
            obs = [Observation(k, pick[d.code](v)) for k, v in sorted(table.items()) if k >= start]
            out.append(FetchResult(d.key, obs, "ok" if obs else "empty"))
        return out
