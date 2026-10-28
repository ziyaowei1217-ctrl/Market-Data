"""Text helpers for providers that read numbers out of published HTML pages and PDFs.

Only the parsed numbers are stored (as observations); page text is never kept.
"""

from __future__ import annotations

import html
import io
import re
from datetime import date, datetime
from html.parser import HTMLParser

BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


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
    """First English long-form date in the opening text of a release ("October 19, 2026" / "16 October 2026")."""
    for pattern, fmt in _DATE_PATTERNS:
        m = pattern.search(text[:4000])
        if m:
            try:
                return datetime.strptime(" ".join(m.groups()), fmt).date()
            except ValueError:
                continue
    return None
