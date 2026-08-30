from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from ..economic_releases import build_release_row, derive_retail_sales_rows
from ..provider_contracts import (
    ContextProvider,
    HONG_KONG,
    PointInTimeUnavailable,
    ProviderResult,
    ProviderSpec,
    target_sunday_cutoff,
)


CENSUS_DATA_PAGE = "https://www.census.gov/retail/data.html"
CENSUS_SALES_PAGE = "https://www.census.gov/retail/sales.html"
CENSUS_HISTORICAL_RELEASES = (
    "https://www.census.gov/retail/marts/historic_releases.html"
)
CURRENT_RELEASE_PDF = "https://www.census.gov/retail/marts/www/marts_current.pdf"
ARCHIVED_RELEASE_PREFIX = (
    "https://www2.census.gov/retail/releases/historical/marts/"
)
SOURCE = "U.S. Census Bureau"
EASTERN = ZoneInfo("America/New_York")

_MONTHS = {
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
_NUMBER = r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"


@dataclass(frozen=True)
class _ReleaseMetadata:
    released: datetime
    observation_period: str


@dataclass(frozen=True)
class _Candidate:
    rows: list[dict]
    text: str
    content: bytes
    url: str

    @property
    def known_as_of(self) -> datetime:
        return datetime.fromisoformat(str(self.rows[0]["known_as_of"]))


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._active: tuple[str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self._active = (str(attributes["href"]), [])

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._active[1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._active is not None:
            href, parts = self._active
            self.links.append((href, _space(" ".join(parts))))
            self._active = None


def parse_retail_sales_release(
    text: str, source_url: str, as_of_date: date
) -> list[dict]:
    """Parse one official MARTS full-release PDF after text extraction."""
    _require_release_pdf_url(source_url)
    normalized = _space(text)
    metadata = _release_metadata(normalized)
    if metadata.released.astimezone(HONG_KONG) > target_sunday_cutoff(as_of_date):
        return []

    table_1 = _table_section(normalized, 1, 2)
    table_2 = _table_section(normalized, 2, 3)
    if "millions of dollars" not in table_1.lower() or not re.search(
        r"not\s+(?:adjusted\s+)?for price changes", normalized, re.IGNORECASE
    ):
        raise ValueError(
            "Census retail Table 1 must report millions of current dollars"
        )
    if "not adjusted" not in table_1.lower() or "adjusted" not in table_1.lower():
        raise ValueError("Census retail Table 1 is missing adjusted-sales headers")
    if not all(marker in table_1.lower() for marker in ("(a)", "(p)", "(r)")):
        raise ValueError("Census retail Table 1 is missing estimate-status headers")

    table_1_values = _unique_total_row(table_1, 12, "Table 1")
    adjusted_values = table_1_values[-5:]
    table_2_values = _unique_total_row(table_2, 6, "Table 2")
    current_mom, published_yoy, revised_prior_mom = table_2_values[:3]

    current_period = metadata.observation_period
    previous_period = _shift_month(current_period, -1)
    two_month_base = _shift_month(current_period, -2)
    year_ago_period = _shift_month(current_period, -12)
    year_ago_previous = _shift_month(current_period, -13)
    original_prior_mom, disclosed_revised_mom = _revision_values(
        normalized,
        expected_start=two_month_base,
        expected_end=previous_period,
    )
    if abs(disclosed_revised_mom - revised_prior_mom) > 1e-12:
        raise ValueError(
            "Census Table 2 conflicts with the published prior-month revision"
        )

    series = {
        current_period: adjusted_values[0],
        previous_period: adjusted_values[1],
        two_month_base: adjusted_values[2],
        year_ago_period: adjusted_values[3],
        year_ago_previous: adjusted_values[4],
    }
    calculated_mom = (series[current_period] / series[previous_period] - 1.0) * 100.0
    calculated_prior_mom = (
        series[previous_period] / series[two_month_base] - 1.0
    ) * 100.0
    calculated_yoy = (
        series[current_period] / series[year_ago_period] - 1.0
    ) * 100.0
    for calculated, published, description in (
        (calculated_mom, current_mom, "current month change"),
        (calculated_prior_mom, revised_prior_mom, "revised prior-month change"),
        (calculated_yoy, published_yoy, "current year-over-year change"),
    ):
        if abs(calculated - published) > 0.0500000001:
            raise ValueError(
                f"Census adjusted levels conflict with the published {description}"
            )

    common = {
        "release_at_bjt": metadata.released.astimezone(HONG_KONG).isoformat(),
        "frequency": "monthly",
        "source": SOURCE,
        "source_url": source_url,
        "known_as_of": metadata.released.isoformat(),
        "vintage_date": metadata.released.date().isoformat(),
        "as_of_date": as_of_date,
        "seasonal_adjustment": "seasonally adjusted",
    }
    rows = [
        build_release_row(
            indicator_code="RETAIL_SALES_MOM",
            indicator_name="Retail and food services sales MoM",
            observation_period=current_period,
            value=current_mom,
            previous_value=original_prior_mom,
            revised_previous=disclosed_revised_mom,
            unit="percent",
            **common,
        )
    ]
    level_rows: list[dict] = []
    for period in sorted(series):
        level_rows.append(
            build_release_row(
                indicator_code="RETAIL_SALES_LEVEL_SA",
                indicator_name="Retail and food services sales",
                observation_period=period,
                value=series[period],
                previous_value=series.get(_shift_month(period, -1)),
                unit="millions_current_dollars",
                **common,
            )
        )
    derived = derive_retail_sales_rows(level_rows)
    if not any(
        row["indicator_code"] == "RETAIL_SALES_YOY_PCT"
        and row["observation_period"] == current_period
        for row in derived
    ):
        raise ValueError("Census release lacks a same-month year-ago adjusted level")
    return rows + level_rows + derived


def build_census_provider(start: date, end: date, session) -> ContextProvider:
    if end < start:
        raise ValueError("Report end must not precede start")

    def fetch() -> ProviderResult:
        data_page = _get_html(session, CENSUS_DATA_PAGE)
        historical_url = _historical_index_url(data_page)
        sales_page = _get_html(session, CENSUS_SALES_PAGE)
        current_url = _current_release_url(sales_page)
        historical_page = _get_html(session, historical_url)
        archived_urls = _archived_release_urls(historical_page, historical_url)

        current = _fetch_candidate(session, current_url, end)
        selected: _Candidate | None = None
        if current is not None:
            current_period = _latest_period(current.rows)
            same_period_urls = [
                url
                for url in archived_urls
                if _archive_observation_period(url) == current_period
            ]
            candidates = [current]
            candidates.extend(
                candidate
                for url in same_period_urls
                if (candidate := _fetch_candidate(session, url, end)) is not None
            )
            selected = _select_latest_candidate(candidates)
        else:
            groups: dict[str, list[str]] = {}
            for url in archived_urls:
                groups.setdefault(_archive_observation_period(url), []).append(url)
            for period in sorted(groups, reverse=True):
                candidates = [
                    candidate
                    for url in sorted(groups[period])
                    if (candidate := _fetch_candidate(session, url, end)) is not None
                ]
                if candidates:
                    selected = _select_latest_candidate(candidates)
                    break

        if selected is None:
            raise PointInTimeUnavailable(
                f"No official Census retail release existed by {end.isoformat()}"
            )
        required = {"RETAIL_SALES_MOM", "RETAIL_SALES_YOY_PCT"}
        present = {str(row["indicator_code"]) for row in selected.rows}
        if not required <= present:
            raise ValueError(
                "Archived Census provider is missing: "
                + ", ".join(sorted(required - present))
            )
        return ProviderResult(
            category="economic_releases",
            rows=selected.rows,
            raw_text=selected.content,
            source=SOURCE,
            source_url=CENSUS_DATA_PAGE,
            notes=(
                f"Sales page: {CENSUS_SALES_PAGE}; historical index: "
                f"{CENSUS_HISTORICAL_RELEASES}; selected artifact: {selected.url}"
            ),
        )

    return ContextProvider(
        spec=ProviderSpec(
            name="census_retail_sales",
            category="economic_releases",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="monthly",
            freshness_days=45,
        ),
        fetch=fetch,
    )


def _release_metadata(text: str) -> _ReleaseMetadata:
    embargoes = re.findall(
        r"FOR RELEASE AT 8:30 AM (EDT|EST),\s*[A-Z]+,\s*"
        r"([A-Z]+\s+\d{1,2},\s+\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if len(embargoes) != 1:
        raise ValueError("Census release requires exactly one 8:30 AM embargo timestamp")
    abbreviation, raw_date = embargoes[0]
    released = datetime.strptime(raw_date.title(), "%B %d, %Y").replace(
        hour=8, minute=30, tzinfo=EASTERN
    )
    if released.tzname() != abbreviation.upper():
        raise ValueError("Census release timezone abbreviation conflicts with its date")

    titles = re.findall(
        r"ADVANCE MONTHLY SALES FOR RETAIL AND FOOD SERVICES,\s*"
        r"([A-Z]+\s+\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if len(titles) != 1:
        raise ValueError("Census release requires exactly one observation-month title")
    return _ReleaseMetadata(
        released=released,
        observation_period=_month_period(titles[0]),
    )


def _table_section(text: str, number: int, next_number: int) -> str:
    starts = list(re.finditer(rf"Table\s+{number}\.\s", text, re.IGNORECASE))
    ends = list(re.finditer(rf"Table\s+{next_number}\.\s", text, re.IGNORECASE))
    if len(starts) != 1 or len(ends) != 1 or ends[0].start() <= starts[0].start():
        raise ValueError(
            f"Census release requires exactly one ordered Table {number}"
        )
    return text[starts[0].start() : ends[0].start()]


def _unique_total_row(section: str, value_count: int, table_name: str) -> list[float]:
    pattern = re.compile(
        r"Retail\s*&\s*food services,\s*total(?:[\s.…⋯·•]+)"
        + rf"({_NUMBER}(?:\s+{_NUMBER}){{{value_count - 1}}})",
        re.IGNORECASE,
    )
    matches = pattern.findall(section)
    if len(matches) != 1:
        raise ValueError(
            f"Census retail release requires exactly one {table_name} total row"
        )
    return [_number(value) for value in matches[0].split()]


def _revision_values(
    text: str, *, expected_start: str, expected_end: str
) -> tuple[float, float]:
    revised = re.findall(
        r"The\s+([A-Za-z]+\s+\d{4})\s+to\s+([A-Za-z]+\s+\d{4})\s+"
        r"percent change was revised from\s+(up|down)\s+([\d.]+)\s+percent"
        r"(?:\s*\([^)]*\))?\s+to\s+(up|down)\s+([\d.]+)\s+percent",
        text,
        flags=re.IGNORECASE,
    )
    unrevised = re.findall(
        r"The\s+([A-Za-z]+\s+\d{4})\s+to\s+([A-Za-z]+\s+\d{4})\s+"
        r"percent change was unrevised from\s+(up|down)\s+([\d.]+)\s+percent",
        text,
        flags=re.IGNORECASE,
    )
    if len(revised) + len(unrevised) != 1:
        raise ValueError("Census release requires exactly one prior-month revision")
    if revised:
        start, end, old_direction, old_value, new_direction, new_value = revised[0]
        original = _directed_number(old_direction, old_value)
        replacement = _directed_number(new_direction, new_value)
    else:
        start, end, direction, value = unrevised[0]
        original = replacement = _directed_number(direction, value)
    if _month_period(start) != expected_start or _month_period(end) != expected_end:
        raise ValueError("Census revision periods conflict with the release month")
    return original, replacement


def _fetch_candidate(session, url: str, as_of_date: date) -> _Candidate | None:
    text, content = _get_pdf_text(session, url)
    rows = parse_retail_sales_release(text, url, as_of_date)
    if not rows:
        return None
    return _Candidate(rows=rows, text=text, content=content, url=url)


def _select_latest_candidate(candidates: Iterable[_Candidate]) -> _Candidate:
    materialized = list(candidates)
    if not materialized:
        raise PointInTimeUnavailable("No eligible Census release candidates")
    latest_known = max(candidate.known_as_of for candidate in materialized)
    latest = [
        candidate for candidate in materialized if candidate.known_as_of == latest_known
    ]
    baseline = _semantic_rows(latest[0].rows)
    for candidate in latest[1:]:
        if _semantic_rows(candidate.rows) != baseline:
            raise ValueError(
                "Conflicting Census artifacts for the same publication time: "
                + candidate.url
            )
    return min(latest, key=lambda candidate: (candidate.url == CURRENT_RELEASE_PDF, candidate.url))


def _semantic_rows(rows: list[dict]) -> dict[tuple[str, str, str], tuple[object, ...]]:
    return {
        (
            str(row["indicator_code"]),
            str(row["observation_period"]),
            str(row["calculation_id"]),
        ): (
            row["value"],
            row["previous_value"],
            row["revised_previous"],
            row["unit"],
            row["seasonal_adjustment"],
            row["known_as_of"],
        )
        for row in rows
    }


def _historical_index_url(data_page: str) -> str:
    document = _parse_links(data_page)
    candidates = [
        urljoin(CENSUS_DATA_PAGE, href)
        for href, label in document.links
        if "advance monthly retail trade reports" in label.lower()
    ]
    if len(candidates) != 1:
        raise ValueError("Census data page requires one official Census historical index")
    try:
        _require_exact_page_url(candidates[0], CENSUS_HISTORICAL_RELEASES)
    except ValueError as error:
        raise ValueError("Census data page has no official Census historical index") from error
    return candidates[0]


def _current_release_url(sales_page: str) -> str:
    document = _parse_links(sales_page)
    candidates = [
        urljoin(CENSUS_SALES_PAGE, href)
        for href, _ in document.links
        if urlparse(urljoin(CENSUS_SALES_PAGE, href)).path
        == "/retail/marts/www/marts_current.pdf"
    ]
    candidates = list(dict.fromkeys(candidates))
    if len(candidates) != 1:
        raise ValueError("Census sales page requires one official current release PDF")
    _require_release_pdf_url(candidates[0])
    return candidates[0]


def _archived_release_urls(index_page: str, index_url: str) -> list[str]:
    document = _parse_links(index_page)
    candidates: list[str] = []
    for href, _ in document.links:
        url = urljoin(index_url, href)
        filename = urlparse(url).path.rsplit("/", 1)[-1]
        if re.fullmatch(r"adv\d{4}(?:r)?\.pdf", filename, re.IGNORECASE):
            _require_release_pdf_url(url)
            if url not in candidates:
                candidates.append(url)
    if not candidates:
        raise PointInTimeUnavailable("No official Census archived retail PDFs found")
    return candidates


def _archive_observation_period(url: str) -> str:
    filename = urlparse(url).path.rsplit("/", 1)[-1]
    match = re.fullmatch(r"adv(\d{2})(\d{2})(?:r)?\.pdf", filename, re.IGNORECASE)
    if match is None:
        raise ValueError(f"Census archive filename lacks an observation month: {url}")
    year = 2000 + int(match.group(1))
    month = int(match.group(2))
    return date(year, month, 1).strftime("%Y-%m")


def _latest_period(rows: list[dict]) -> str:
    periods = [
        str(row["observation_period"])
        for row in rows
        if row["indicator_code"] == "RETAIL_SALES_MOM"
    ]
    if len(periods) != 1:
        raise ValueError("Census artifact must contain exactly one current MoM row")
    return periods[0]


def _get_html(session, url: str) -> str:
    response = _get_response(session, url)
    media_type = _media_type(response)
    if media_type not in {"text/html", "application/xhtml+xml"}:
        raise ValueError("Census page has an invalid content type")
    return str(response.text)


def _get_pdf_text(session, url: str) -> tuple[str, bytes]:
    _require_release_pdf_url(url)
    response = _get_response(session, url)
    if _media_type(response) != "application/pdf":
        raise ValueError("Census release PDF has an invalid content type")
    content = bytes(response.content)
    if not content.startswith(b"%PDF"):
        raise ValueError("Census release PDF signature is invalid")
    from pypdf import PdfReader

    text = "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages
    )
    if not text.strip():
        raise ValueError("Census release PDF contains no extractable text")
    return text, content


def _get_response(session, url: str):
    response = session.get(url, timeout=30, allow_redirects=False)
    status = int(getattr(response, "status_code", 200))
    history = getattr(response, "history", ())
    final_url = str(getattr(response, "url", url))
    if history or 300 <= status < 400 or final_url != url:
        raise ValueError(f"Census request must not redirect: {url}")
    response.raise_for_status()
    return response


def _media_type(response) -> str:
    return str(getattr(response, "headers", {}).get("Content-Type", "")).split(
        ";", 1
    )[0].strip().lower()


def _require_exact_page_url(url: str, expected: str) -> None:
    parsed = urlparse(url)
    if (
        url != expected
        or parsed.scheme != "https"
        or parsed.hostname != "www.census.gov"
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"URL is outside the official Census page: {url}")


def _require_release_pdf_url(url: str) -> None:
    parsed = urlparse(url)
    is_current = url == CURRENT_RELEASE_PDF
    is_archive = (
        parsed.scheme == "https"
        and parsed.hostname == "www2.census.gov"
        and url.startswith(ARCHIVED_RELEASE_PREFIX)
        and re.fullmatch(
            r"/retail/releases/historical/marts/adv\d{4}(?:r)?\.pdf",
            parsed.path,
            re.IGNORECASE,
        )
        is not None
    )
    if (
        not (is_current or is_archive)
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"URL is outside an official Census retail release: {url}")


def _parse_links(text: str) -> _LinkParser:
    parser = _LinkParser()
    parser.feed(text)
    parser.close()
    return parser


def _month_period(value: str) -> str:
    match = re.fullmatch(r"\s*([A-Za-z]+)\s+(\d{4})\s*", value)
    if match is None or match.group(1).lower() not in _MONTHS:
        raise ValueError(f"Unsupported Census month: {value}")
    return f"{int(match.group(2)):04d}-{_MONTHS[match.group(1).lower()]:02d}"


def _shift_month(period: str, offset: int) -> str:
    year, month = (int(value) for value in period.split("-"))
    absolute = year * 12 + month - 1 + offset
    return f"{absolute // 12:04d}-{absolute % 12 + 1:02d}"


def _number(value: str) -> float:
    return float(value.replace(",", ""))


def _directed_number(direction: str, value: str) -> float:
    number = float(value)
    return number if direction.lower() == "up" else -number


def _space(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


__all__ = [
    "ARCHIVED_RELEASE_PREFIX",
    "CENSUS_DATA_PAGE",
    "CENSUS_HISTORICAL_RELEASES",
    "CENSUS_SALES_PAGE",
    "CURRENT_RELEASE_PDF",
    "build_census_provider",
    "parse_retail_sales_release",
]
