"""Headline numbers parsed from official press releases (checked against real
pages saved by inspect_sources.py): National Bureau of Statistics of China."""

from __future__ import annotations

import re
import time
from collections import defaultdict
from datetime import date, timedelta
from typing import Sequence
from urllib.parse import urljoin

from ..db.store import Observation
from .base import FetchResult, Provider, ProviderError, SeriesDef, register
from .documents import BROWSER_UA, html_text

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
        if url in seen or "/PressRelease/" not in url:
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
        failures: list[str] = []
        for i in range(pages):
            url = self.LIST + ("" if i == 0 else f"index_{i}.html")
            items = None
            for attempt in range(2):
                try:
                    items = parse_nbs_listing(self._get(url).decode("utf-8", errors="replace"), url)
                    break
                except ProviderError as error:
                    if i == 0 and attempt == 1:
                        raise
                    failures.append(f"listing page {i}: {error}")
                    time.sleep(3)
            if items is not None and not items:
                failures.append(f"listing page {i}: no release links")
            if not items:
                break
            listing.extend(items)
            if min(d for _, d, _ in items) < start - timedelta(days=40):
                break
            time.sleep(0.5)
        values: dict[str, dict[date, float]] = defaultdict(dict)
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
            note = f"{len(obs)} releases from {len(listing)} listed; {len(failures)} problems" + (f" (e.g. {failures[0][:120]})" if failures else "")
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


# --------------------------------------------------------------------------- S&P Global PMI

SPG_REGIONS = {"US": "US", "Eurozone": "EZ", "UK": "UK", "Japan": "JP"}
_SPG_TITLE = re.compile(r"^(?:S&P Global|HCOB|au Jibun Bank) (Flash )?(US|Eurozone|UK|Japan) (?:(Manufacturing|Services|Composite) )?PMI$")
_DECIMAL = re.compile(r"(?<![\d.])\d{2}\.\d(?![\d.])")


def _embargo_month(text: str) -> date | None:
    m = re.search(rf"Embargoed until .{{0,60}}?(\d{{1,2}}) ({_MONTH_RE}) (\d{{4}})", text)
    return date(int(m.group(3)), MONTHS.index(m.group(2).lower()) + 1, 1) if m else None


def _prev_month(m: date) -> date:
    return (m - timedelta(days=1)).replace(day=1)


def parse_spg_flash(text: str) -> dict[str, dict[date, float]]:
    """Bullets like 'Flash US Composite PMI Output Index: 57.6 (September: 58.4).' — chart axis
    integers are interleaved in the PDF text, so only one-decimal numbers count."""
    flat = re.sub(r"\s+", " ", text)
    month = _embargo_month(flat)
    if month is None:
        return {}
    out: dict[str, dict[date, float]] = defaultdict(dict)
    for m in re.finditer(r"Flash (?:US|Eurozone|UK|Japan) ([^:()]{3,70}?):([^()]{0,60})\(([A-Z][a-z]+):([^()]{0,40})\)", flat):
        label = m.group(1)
        if "Composite" in label:
            kind = "comp"
        elif "Services" in label:
            kind = "serv"
        elif "Manufacturing" in label and "Output" not in label:
            kind = "mfg"
        else:
            continue
        current, previous = _DECIMAL.findall(m.group(2)), _DECIMAL.findall(m.group(4))
        if current:
            out[kind][month] = float(current[0])
        if previous and m.group(3).lower() in MONTHS:
            prev = _prev_month(month)
            if MONTHS[prev.month - 1] == m.group(3).lower():
                out[kind][prev] = float(previous[0])
    return dict(out)


def parse_spg_final(kind: str, text: str) -> dict[str, dict[date, float]]:
    """Final releases (first working days of the next month). The index value is the first
    one-decimal number after the index name that is not the previous month's value
    ('from 53.9') or the 50.0 no-change mark; the PDF's two columns are interleaved, so the
    name itself may be split ('Purchasing Global Market Intelligence Managers' Index')."""
    flat = re.sub(r"\s+", " ", text).replace("’", "'")
    month = _embargo_month(flat)
    if month is None:
        return {}
    data_month = _prev_month(month)
    anchors = {"mfg": [r"headline [^.]{0,120}?Manufacturing (?:Purchasing|PMI)", r"Purchasing Managers' Index",
                       r"Manufacturing PMI(?:®)?"],
               "serv": [r"Services PMI(?:®)? Business Activity Index", r"Services Business Activity Index", r"Business Activity Index"],
               "comp": [r"Composite PMI(?:®)? Output Index", r"Composite Output Index", r"Composite PMI"]}
    kinds = ["mfg"] if kind == "Manufacturing" else ["serv", "comp"]
    out: dict[str, dict[date, float]] = {}
    for k in kinds:
        for pattern in anchors[k]:
            hit = re.search(pattern, flat[flat.find("Embargoed"):] if "Embargoed" in flat else flat)
            if not hit:
                continue
            offset = flat.find("Embargoed") if "Embargoed" in flat else 0
            window = flat[offset + hit.end(): offset + hit.end() + 500]
            picks = []
            for m in _DECIMAL.finditer(window):
                before, after = window[max(0, m.start() - 14): m.start()], window[m.end(): m.end() + 30]
                if re.search(r"\bfrom\s*$", before) or re.match(r"\s*(?:\S+\s+){0,1}(?:no-change|neutral|threshold|mark|level\b)", after):
                    continue
                picks.append(float(m.group(0)))
            if picks:
                out[k] = {data_month: picks[0]}
                break
    return out


def parse_spg_listing(html: str) -> list[tuple[str, str]]:
    """(title, url) pairs from the PMI releases page: each release title with the first
    press-release link that follows it (markup between the two varies)."""
    import html as _html

    out = []
    chunks = re.split(r'class="releaseTitle"[^>]*>', html)
    for chunk in chunks[1:]:
        title = _html.unescape(re.sub(r"<[^>]+>", "", chunk.split("</span>", 1)[0]))
        link = re.search(r'href="([^"]*PressRelease[^"]*)"', chunk)
        if link:
            out.append((re.sub(r"\s+", " ", title).strip(), _html.unescape(link.group(1))))
    return out


@register
class SpGlobalPmi(Provider):
    """S&P Global PMI press releases (headline indices only; the site keeps about one month
    of releases, so history accumulates). code = "<US|EZ|UK|JP>:<mfg|serv|comp>". Flash
    releases give the current month and the final value of the previous month; final
    releases give the final value."""

    name = "SPGPMI"
    batch = True
    PAUSE = 6  # seconds between PDF downloads
    LIST = "https://www.pmi.spglobal.com/Public/Release/PressReleases?language=en"

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        from .documents import pdf_pages

        listing = parse_spg_listing(self.get(self.LIST, headers={"User-Agent": BROWSER_UA}).decode("utf-8", errors="replace"))
        if not listing:
            raise ProviderError("PMI release list layout changed")
        wanted = {d.code.split(":")[0] for d in defs}
        values: dict[str, dict[date, float]] = defaultdict(dict)
        problems: list[str] = []
        done: list[str] = []
        wanted_items = []
        for position, (title, url) in enumerate(listing):  # the page lists newest first
            m = _SPG_TITLE.match(title)
            if not m or SPG_REGIONS[m.group(2)] not in wanted:
                continue
            region, flash, kind = SPG_REGIONS[m.group(2)], bool(m.group(1)), m.group(3)
            if flash or kind is not None:
                wanted_items.append((position, title, url, region, flash, kind))
        # The site starts answering with empty pages after about five downloads, so go slowly and
        # fetch the newest releases first (flash releases also carry the previous month's final
        # value); results are applied oldest first.
        parsed_items = []
        for position, title, url, region, flash, kind in sorted(wanted_items, key=lambda x: x[0]):
            text = None
            for wait in (0, 15, 40):
                time.sleep(wait or self.PAUSE)
                try:
                    body = self.get(url, headers={"User-Agent": BROWSER_UA, "Accept": "application/pdf,*/*"})
                except Exception:  # noqa: BLE001 - retried, then reported as "no PDF"
                    continue
                if body[:5] == b"%PDF-":
                    text = "\n".join(pdf_pages(body)[:2])
                    break
            if text is None:
                problems.append(f"no PDF: {title}")
                continue
            parsed = parse_spg_flash(text) if flash else parse_spg_final(kind, text)
            if not parsed:
                problems.append(f"unparsed: {title}")
                continue
            done.append(title.replace("S&P Global ", ""))
            parsed_items.append((position, region, parsed))
        for _, region, parsed in sorted(parsed_items, key=lambda x: -x[0]):  # oldest release first
            for k, by_month in parsed.items():
                values[f"{region}:{k}"].update(by_month)
        out = []
        for d in defs:
            obs = [Observation(k, v) for k, v in sorted(values.get(d.code, {}).items()) if k >= start]
            note = (f"{len(obs)} months; parsed {', '.join(done)[:300]}; " +
                    (f"{len(problems)} problems: {'; '.join(x[:60] for x in problems)[:400]}" if problems else "no problems"))
            out.append(FetchResult(d.key, obs, "ok" if obs else "empty", note))
        return out
