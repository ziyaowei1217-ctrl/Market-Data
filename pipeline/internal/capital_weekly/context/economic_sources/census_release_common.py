from __future__ import annotations

import io
import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from pypdf import PdfReader

from ..provider_contracts import PointInTimeUnavailable


SOURCE = "U.S. Census Bureau"
EASTERN = ZoneInfo("America/New_York")
MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._active: tuple[str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self._active = (str(attributes["href"]), [])

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._active[1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._active is not None:
            href, parts = self._active
            self.links.append((href, space(" ".join(parts))))
            self._active = None


def archive_pdf_links(
    text: str,
    index_url: str,
    *,
    path_fragment: str,
    description: str,
    as_of_date: date,
) -> list[tuple[str, str]]:
    parser = _LinkParser()
    parser.feed(text)
    parser.close()
    by_period: dict[str, str] = {}
    target_month = f"{as_of_date.year:04d}-{as_of_date.month:02d}"
    for href, label in parser.links:
        period = month_period(label)
        if period is None or period > target_month:
            continue
        url = urljoin(index_url, href)
        existing = by_period.get(period)
        if existing is not None and existing != url:
            raise ValueError(f"Census {description} archive has ambiguous {period} PDFs")
        by_period[period] = url
    if not by_period:
        raise PointInTimeUnavailable(
            f"No official Census {description} archive PDFs were found"
        )
    return sorted(by_period.items(), reverse=True)


def fetch_index(session, url: str) -> str:
    response = session.get(url, timeout=30, allow_redirects=False)
    reject_redirect(response, url)
    response.raise_for_status()
    return str(response.text)


def fetch_pdf_text(
    session,
    url: str,
    *,
    path_fragment: str,
    description: str,
) -> tuple[str, bytes]:
    require_census_pdf(url, path_fragment=path_fragment, description=description)
    response = session.get(url, timeout=30, allow_redirects=False)
    reject_redirect(response, url)
    response.raise_for_status()
    media_type = str(response.headers.get("Content-Type", "")).split(";", 1)[0].lower()
    if media_type != "application/pdf":
        raise ValueError(f"Census {description} artifact must be an official PDF")
    content = bytes(response.content)
    if not content.startswith(b"%PDF"):
        raise ValueError(f"Census {description} PDF signature is invalid")
    reader = PdfReader(io.BytesIO(content))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    if not space(text):
        raise ValueError(f"Census {description} PDF contains no extractable text")
    return text, content


def latest_release(
    session,
    *,
    index_url: str,
    path_fragment: str,
    description: str,
    as_of_date: date,
    parser: Callable[[str, str, date], list[dict]],
) -> tuple[list[dict], bytes, str]:
    index = fetch_index(session, index_url)
    links = archive_pdf_links(
        index,
        index_url,
        path_fragment=path_fragment,
        description=description,
        as_of_date=as_of_date,
    )
    for archive_period, url in links:
        text, content = fetch_pdf_text(
            session,
            url,
            path_fragment=path_fragment,
            description=description,
        )
        rows = parser(text, url, as_of_date)
        if rows:
            observation_periods = {
                str(row.get("observation_period") or "") for row in rows
            }
            if observation_periods != {archive_period}:
                raise ValueError(
                    f"Census {description} archive label {archive_period} conflicts "
                    "with the PDF observation period"
                )
            return rows, content, url
    raise PointInTimeUnavailable(
        f"No official Census {description} release existed by {as_of_date.isoformat()}"
    )


def require_census_pdf(url: str, *, path_fragment: str, description: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"www.census.gov", "www2.census.gov"}
        or path_fragment not in parsed.path
        or not parsed.path.lower().endswith(".pdf")
    ):
        raise ValueError(
            f"URL is outside the official Census {description} archive: {url}"
        )


def reject_redirect(response, requested_url: str) -> None:
    status = int(getattr(response, "status_code", 200))
    if getattr(response, "history", None) or 300 <= status < 400:
        raise ValueError(f"Census request must not redirect: {requested_url}")
    final_url = str(getattr(response, "url", requested_url))
    if final_url != requested_url:
        raise ValueError(f"Census response URL changed unexpectedly: {requested_url}")


def release_timestamp(text: str) -> datetime:
    matches = re.findall(
        r"FOR RELEASE AT (\d{1,2}):(\d{2})\s*(AM|PM)\s*"
        r"(EDT|EST),\s*(?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY),\s*"
        r"([A-Z]+)\s+(\d{1,2}),\s+(\d{4})",
        space(text),
        flags=re.IGNORECASE,
    )
    if len(matches) != 1:
        raise ValueError("Census release requires exactly one embargo timestamp")
    raw_hour, raw_minute, meridiem, zone, month_name, raw_day, raw_year = matches[0]
    month = MONTHS.get(month_name.lower())
    if month is None:
        raise ValueError(f"Unsupported Census release month: {month_name}")
    hour = int(raw_hour) % 12 + (12 if meridiem.upper() == "PM" else 0)
    released = datetime(
        int(raw_year), month, int(raw_day), hour, int(raw_minute), tzinfo=EASTERN
    )
    expected = "EDT" if released.dst() else "EST"
    if zone.upper() != expected:
        raise ValueError("Census release timezone abbreviation conflicts with its date")
    return released


def month_period(value: str) -> str | None:
    match = re.fullmatch(r"([A-Za-z]+)\s+(\d{4})", space(value))
    if match is None or match.group(1).lower() not in MONTHS:
        return None
    return f"{int(match.group(2)):04d}-{MONTHS[match.group(1).lower()]:02d}"


def signed(direction: str, value: str) -> float:
    number = float(value.replace(",", ""))
    return -number if direction.lower() in {"decreased", "decrease", "below"} else number


def space(value: str) -> str:
    return " ".join(value.split())
