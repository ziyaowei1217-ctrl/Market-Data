"""Weekly institution reports: download, archive page text, (later) parse tables.

The reports are free to read but copyrighted, so their text is stored only in
the private ``report_pages`` table (no anon/authenticated read policy). Parsed
numbers become ordinary observations with ``vintage_source='report'``.
"""

from __future__ import annotations

import html
import io
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Callable, Iterable
from urllib.parse import urljoin

import requests

from .base import USER_AGENT

BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


@dataclass
class ReportSource:
    name: str
    title: str
    candidates: Callable[[date], Iterable[tuple[date, str]]]  # (report date guess, url)


def _recent_days(today: date, days: int = 14) -> list[date]:
    return [today - timedelta(days=k) for k in range(days)]


def _jpm(today: date):
    yield today, "https://am.jpmorgan.com/content/dam/jpm-am-aem/americas/us/en/insights/market-insights/wmr/weekly_market_recap.pdf"


def _gs(today: date):
    for d in _recent_days(today):
        yield d, f"https://am.gs.com/cms-assets/gsam-app/documents/insights/en/{d.year}/market_monitor_{d:%m%d%y}.pdf"


def _factset(today: date):
    base = "https://advantage.factset.com/hubfs/Website/Resources%20Section/Research%20Desk/Earnings%20Insight/"
    for d in _recent_days(today):
        yield d, f"{base}EarningsInsight_{d:%m%d%y}.pdf"


def _hsbc_uk(today: date):
    for d in _recent_days(today):
        yield d, (
            "https://www.assetmanagement.hsbc.co.uk/en/intermediary/news-and-insights/"
            f"investment-weekly-{d.day}-{d:%B}-{d.year}".lower()
        )


def _hsbc_au(today: date):
    for d in _recent_days(today):
        yield d, (
            "https://www.assetmanagement.hsbc.com.au/en/institutional-investor/news-and-insights/-/media/files/"
            f"attachments/common/news-and-articles/articles/am-investment-weekly-{d:%d-%m-%y}"
        )


SOURCES = [
    ReportSource("JPM_WMR", "J.P. Morgan Weekly Market Recap", _jpm),
    ReportSource("GS_MM", "Goldman Sachs AM Market Monitor", _gs),
    ReportSource("FACTSET_EI", "FactSet Earnings Insight", _factset),
    ReportSource("HSBC_UK", "HSBC AM Investment Weekly (UK)", _hsbc_uk),
    ReportSource("HSBC_AU", "HSBC AM Investment Weekly (AU)", _hsbc_au),
]


class _TextAndLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.links: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if ".pdf" in href.lower() or "/media/files/" in href.lower():
                self.links.append(href)
        if tag in ("tr", "p", "br", "li", "h1", "h2", "h3", "h4", "table", "div"):
            self.parts.append("\n")
        if tag in ("td", "th"):
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def pdf_pages(body: bytes) -> list[str]:
    import pdfplumber

    pages = []
    with pdfplumber.open(io.BytesIO(body)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text(layout=True) or "")
    return pages


def html_text(body: bytes) -> tuple[str, list[str]]:
    parser = _TextAndLinks()
    parser.feed(body.decode("utf-8", errors="replace"))
    text = re.sub(r"[ \t]+", " ", html.unescape("".join(parser.parts)))
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return text, parser.links


_DATE_PATTERNS = [
    (re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})"), "%B %d %Y"),
    (re.compile(r"(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})"), "%d %B %Y"),
]


def find_report_date(text: str) -> date | None:
    for pattern, fmt in _DATE_PATTERNS:
        m = pattern.search(text[:4000])
        if m:
            try:
                return datetime.strptime(" ".join(m.groups()), fmt).date()
            except ValueError:
                continue
    return None


@dataclass
class ArchivedReport:
    source: str
    report_date: date
    url: str
    pages: list[str]


def download(source: ReportSource, session: requests.Session, today: date | None = None, log=print) -> ArchivedReport | None:
    today = today or datetime.now(timezone.utc).date()
    for guess, url in source.candidates(today):
        try:
            response = session.get(url, timeout=(15, 90), headers={"User-Agent": BROWSER_UA}, allow_redirects=True)
        except requests.RequestException as error:
            log(f"  {source.name}: {type(error).__name__} for {url}")
            continue
        if response.status_code != 200 or not response.content:
            continue
        body = response.content
        if body[:5] == b"%PDF-":
            pages = pdf_pages(body)
        else:
            text, links = html_text(body)
            pages = [text]
            for link in links[:3]:
                target = urljoin(response.url, link)
                try:
                    sub = session.get(target, timeout=(15, 90), headers={"User-Agent": BROWSER_UA})
                except requests.RequestException:
                    continue
                if sub.status_code == 200 and sub.content[:5] == b"%PDF-":
                    pages.extend(pdf_pages(sub.content))
                    url = target
                    break
            if len(text) < 500 and len(pages) == 1:
                continue  # error/landing page
        found = find_report_date("\n".join(pages)) or guess
        log(f"  {source.name}: {len(pages)} pages, report date {found}, {url}")
        return ArchivedReport(source.name, found, url, pages)
    log(f"  {source.name}: no report found in the last 14 days")
    return None


def archive_all(store, session: requests.Session | None = None, log=print) -> int:
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", USER_AGENT)
    stored = 0
    for source in SOURCES:
        report = download(source, session, log=log)
        if report is None:
            store.log("reports", "cloud", "REPORT", source.name, "empty", 0, "no report found")
            continue
        n = store.upsert_report_pages(report.source, report.report_date, report.url, report.pages)
        store.log("reports", "cloud", "REPORT", source.name, "ok", n, f"{report.report_date} {report.url}")
        stored += n
    return stored
