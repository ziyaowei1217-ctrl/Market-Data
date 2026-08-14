from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from ..economic_releases import build_release_row, derive_price_index_rows
from ..provider_contracts import (
    ContextProvider,
    HONG_KONG,
    PointInTimeUnavailable,
    ProviderResult,
    ProviderSpec,
    target_sunday_cutoff,
)


CPI_ARCHIVE = "https://www.bls.gov/bls/news-release/cpi.htm"
EMPLOYMENT_ARCHIVE = "https://www.bls.gov/bls/news-release/empsit.htm"
ALLOWED_RELEASE_PREFIX = "https://www.bls.gov/news.release/archives/"
SOURCE = "U.S. Bureau of Labor Statistics"
EASTERN = ZoneInfo("America/New_York")

_MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}
@dataclass(frozen=True)
class _Cell:
    text: str
    rowspan: int
    colspan: int
    header: bool


@dataclass(frozen=True)
class _RawRow:
    cells: tuple[_Cell, ...]
    section: str


@dataclass(frozen=True)
class _Table:
    caption: str
    rows: tuple[_RawRow, ...]

    def grid(self) -> tuple[tuple[str, ...], ...]:
        return _expand_rows(self.rows)


class _ArchiveParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.tables: list[_Table] = []
        self.text_parts: list[str] = []
        self._rows: list[_RawRow] | None = None
        self._row: list[_Cell] | None = None
        self._cell_parts: list[str] | None = None
        self._cell_attrs: dict[str, str | None] = {}
        self._cell_header = False
        self._caption_parts: list[str] | None = None
        self._caption = ""
        self._section = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and attributes.get("href"):
            self.links.append(str(attributes["href"]))
        elif tag == "table":
            if self._rows is not None:
                raise ValueError("Nested BLS tables are not supported")
            self._rows = []
            self._caption = ""
            self._section = ""
        elif tag in {"thead", "tbody", "tfoot"} and self._rows is not None:
            self._section = tag
        elif tag == "caption" and self._rows is not None:
            self._caption_parts = []
        elif tag == "tr" and self._rows is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell_parts = []
            self._cell_attrs = attributes
            self._cell_header = tag == "th"

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        if self._caption_parts is not None:
            self._caption_parts.append(data)
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell_parts is not None:
            if self._row is None:
                raise ValueError("BLS table cell appears outside a row")
            self._row.append(
                _Cell(
                    text=_space(" ".join(self._cell_parts)),
                    rowspan=_span(self._cell_attrs.get("rowspan"), "rowspan"),
                    colspan=_span(self._cell_attrs.get("colspan"), "colspan"),
                    header=self._cell_header,
                )
            )
            self._cell_parts = None
        elif tag == "caption" and self._caption_parts is not None:
            self._caption = _space(" ".join(self._caption_parts))
            self._caption_parts = None
        elif tag == "tr" and self._row is not None:
            if self._rows is None:
                raise ValueError("BLS table row appears outside a table")
            if self._row:
                self._rows.append(_RawRow(tuple(self._row), self._section))
            self._row = None
        elif tag in {"thead", "tbody", "tfoot"} and self._rows is not None:
            self._section = ""
        elif tag == "table" and self._rows is not None:
            self.tables.append(_Table(self._caption, tuple(self._rows)))
            self._rows = None

    @property
    def text(self) -> str:
        return _space(" ".join(self.text_parts))


def parse_cpi_release(text: str, source_url: str, as_of_date: date) -> list[dict]:
    _require_release_url(source_url, "cpi_")
    document = _parse_document(text)
    released = _embargo_timestamp(document.text)
    if released.astimezone(HONG_KONG) > target_sunday_cutoff(as_of_date):
        return []

    table = _one_table(
        document.tables,
        lambda caption: caption.startswith(
            "table 1. consumer price index for all urban consumers (cpi-u):"
        )
        and "[1982-84=100" in caption,
        "CPI Table 1 index table",
    )
    values = _cpi_index_series(table)
    headline = values.get("CPI_INDEX_NSA")
    core = values.get("CORE_CPI_INDEX_NSA")
    if not headline:
        raise ValueError("Archived BLS CPI release is missing all-items CPI")
    if not core:
        raise ValueError("Archived BLS CPI release is missing Core CPI")
    latest_headline = max(headline)
    latest_core = max(core)
    if latest_headline != latest_core:
        raise ValueError(
            "Archived BLS CPI and Core CPI must share the same latest observation period"
        )

    observed: list[dict] = []
    for code in ("CPI_INDEX_NSA", "CORE_CPI_INDEX_NSA"):
        series = values[code]
        for period in sorted(series, reverse=True):
            observed.append(
                build_release_row(
                    indicator_code=code,
                    indicator_name=(
                        "Consumer Price Index"
                        if code == "CPI_INDEX_NSA"
                        else "Consumer Price Index less food and energy"
                    ),
                    observation_period=period,
                    release_at_bjt=released.astimezone(HONG_KONG).isoformat(),
                    value=series[period],
                    previous_value=series.get(_previous_month(period)),
                    unit="index",
                    frequency="monthly",
                    seasonal_adjustment="not seasonally adjusted",
                    source=SOURCE,
                    source_url=source_url,
                    known_as_of=released.isoformat(),
                    vintage_date=released.date().isoformat(),
                    as_of_date=as_of_date,
                )
            )
    derived: list[dict] = []
    for code in ("CPI_INDEX_NSA", "CORE_CPI_INDEX_NSA"):
        derived.extend(derive_price_index_rows(observed, code))
    return observed + derived


def parse_employment_release(
    text: str, source_url: str, as_of_date: date
) -> list[dict]:
    _require_release_url(source_url, "empsit_")
    document = _parse_document(text)
    released = _embargo_timestamp(document.text)
    if released.astimezone(HONG_KONG) > target_sunday_cutoff(as_of_date):
        return []

    household = _one_table(
        document.tables,
        lambda caption: caption.startswith(
            "summary table a. household data, seasonally adjusted"
        ),
        "Employment Summary table A",
    )
    establishment = _one_table(
        document.tables,
        lambda caption: caption.startswith(
            "summary table b. establishment data, seasonally adjusted"
        ),
        "Employment Summary table B",
    )
    unemployment = _employment_series(
        household, "unemployment rate", required_section="employment status"
    )
    payroll = _employment_series(
        establishment,
        "total nonfarm",
        required_section="over-the-month change, in thousands",
    )
    if not unemployment:
        raise ValueError("Archived BLS employment release is missing unemployment")
    if not payroll:
        raise ValueError("Archived BLS employment release is missing NFP")
    current_period = max(payroll)
    if max(unemployment) != current_period:
        raise ValueError("BLS NFP and unemployment must share the release observation period")

    revisions = _nfp_revisions(document.text, current_period)
    required_revision_periods = (
        _previous_month(current_period),
        _previous_month(_previous_month(current_period)),
    )
    if set(revisions) != set(required_revision_periods):
        raise ValueError("Archived BLS employment release must contain two prior NFP revisions")
    prior_period = required_revision_periods[0]
    prior_original, prior_revised = revisions[prior_period]
    table_prior = payroll.get(prior_period)
    if table_prior is None or table_prior * 1000.0 != prior_revised:
        raise ValueError("BLS NFP table conflicts with the published revision disclosure")

    common = {
        "release_at_bjt": released.astimezone(HONG_KONG).isoformat(),
        "frequency": "monthly",
        "source": SOURCE,
        "source_url": source_url,
        "known_as_of": released.isoformat(),
        "vintage_date": released.date().isoformat(),
        "as_of_date": as_of_date,
        "seasonal_adjustment": "seasonally adjusted",
    }
    rows = [
        build_release_row(
            indicator_code="NFP_CHANGE",
            indicator_name="Total nonfarm payroll employment change",
            observation_period=current_period,
            value=payroll[current_period] * 1000.0,
            previous_value=prior_original,
            revised_previous=prior_revised,
            unit="persons",
            **common,
        )
    ]
    for period in required_revision_periods:
        original, revised = revisions[period]
        rows.append(
            build_release_row(
                indicator_code="NFP_CHANGE",
                indicator_name="Total nonfarm payroll employment change revision",
                observation_period=period,
                value=revised,
                previous_value=original,
                revised_previous=None,
                unit="persons",
                **common,
            )
        )
    rows.append(
        build_release_row(
            indicator_code="UNEMPLOYMENT_RATE",
            indicator_name="Unemployment rate",
            observation_period=current_period,
            value=unemployment[current_period],
            previous_value=unemployment.get(prior_period),
            unit="percent",
            **common,
        )
    )
    return rows


def build_bls_provider(start: date, end: date, session) -> ContextProvider:
    if end < start:
        raise ValueError("Report end must not precede start")

    def fetch() -> ProviderResult:
        cpi_rows, cpi_text, cpi_url = _latest_release(
            session, CPI_ARCHIVE, "cpi_", parse_cpi_release, end
        )
        employment_rows, employment_text, employment_url = _latest_release(
            session,
            EMPLOYMENT_ARCHIVE,
            "empsit_",
            parse_employment_release,
            end,
        )
        rows = cpi_rows + employment_rows
        required = {
            "CPI_INDEX_NSA": "CPI",
            "CORE_CPI_INDEX_NSA": "Core CPI",
            "NFP_CHANGE": "NFP",
            "UNEMPLOYMENT_RATE": "unemployment",
        }
        present = {str(row["indicator_code"]) for row in rows}
        missing = [label for code, label in required.items() if code not in present]
        if missing:
            raise ValueError("Archived BLS provider is missing: " + ", ".join(missing))
        return ProviderResult(
            category="economic_releases",
            rows=rows,
            raw_text=(
                f"SOURCE {cpi_url}\n{cpi_text}\n"
                f"SOURCE {employment_url}\n{employment_text}"
            ),
            source=SOURCE,
            source_url=CPI_ARCHIVE,
            notes=f"Employment archive index: {EMPLOYMENT_ARCHIVE}",
        )

    return ContextProvider(
        spec=ProviderSpec(
            name="bls_economic_releases",
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


def _latest_release(
    session,
    archive_url: str,
    expected_stem: str,
    parser: Callable[[str, str, date], list[dict]],
    as_of_date: date,
) -> tuple[list[dict], str, str]:
    index_text = _get_text(session, archive_url)
    document = _parse_document(index_text)
    dated_links = _archive_links(document.links, archive_url, expected_stem)
    eligible = [(stamp, url) for stamp, url in dated_links if stamp <= as_of_date]
    if not eligible:
        raise PointInTimeUnavailable(
            f"No official BLS {expected_stem} release existed by {as_of_date.isoformat()}"
        )
    latest_filename_date = max(stamp for stamp, _ in eligible)
    candidate_urls = sorted(
        url for stamp, url in eligible if stamp == latest_filename_date
    )
    parsed: list[tuple[datetime, list[dict], str, str]] = []
    for url in candidate_urls:
        artifact = _get_text(session, url)
        rows = parser(artifact, url, as_of_date)
        if not rows:
            raise ValueError(
                f"BLS filename date is eligible but artifact timestamp is not: {url}"
            )
        known = datetime.fromisoformat(str(rows[0]["known_as_of"]))
        parsed.append((known, rows, artifact, url))
    latest_known = max(known for known, _, _, _ in parsed)
    equal_latest = [candidate for candidate in parsed if candidate[0] == latest_known]
    _reject_conflicting_artifacts(equal_latest)
    _, rows, artifact, url = min(equal_latest, key=lambda candidate: candidate[3])
    return rows, artifact, url


def _reject_conflicting_artifacts(
    candidates: list[tuple[datetime, list[dict], str, str]]
) -> None:
    if len(candidates) < 2:
        return
    baseline = _semantic_rows(candidates[0][1])
    for _, rows, _, url in candidates[1:]:
        if _semantic_rows(rows) != baseline:
            raise ValueError(f"Conflicting BLS artifacts for the same vintage: {url}")


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
            row["frequency"],
            row["seasonal_adjustment"],
            row["known_as_of"],
        )
        for row in rows
    }


def _get_text(session, url: str) -> str:
    response = session.get(url, timeout=30, allow_redirects=False)
    status = int(getattr(response, "status_code", 200))
    history = getattr(response, "history", ())
    final_url = str(getattr(response, "url", url))
    if history or 300 <= status < 400 or final_url != url:
        raise ValueError(f"BLS request must not redirect: {url}")
    response.raise_for_status()
    return str(response.text)


def _archive_links(
    hrefs: list[str], archive_url: str, expected_stem: str
) -> list[tuple[date, str]]:
    accepted: list[tuple[date, str]] = []
    for href in hrefs:
        if "/news.release/archives/" not in href:
            continue
        url = urljoin(archive_url, href)
        _require_release_url(url, expected_stem)
        filename = urlparse(url).path.rsplit("/", 1)[-1]
        match = re.fullmatch(re.escape(expected_stem) + r"(\d{8})\.htm", filename)
        if match is None:
            raise ValueError(f"BLS archive filename lacks a release date: {url}")
        stamp = datetime.strptime(match.group(1), "%m%d%Y").date()
        candidate = (stamp, url)
        if candidate not in accepted:
            accepted.append(candidate)
    if not accepted:
        raise PointInTimeUnavailable(f"No official BLS {expected_stem} archives found")
    return accepted


def _require_release_url(url: str, expected_stem: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "www.bls.gov"
        or not url.startswith(ALLOWED_RELEASE_PREFIX)
        or not parsed.path.rsplit("/", 1)[-1].startswith(expected_stem)
    ):
        raise ValueError(f"URL is outside the official BLS archive: {url}")


def _parse_document(text: str) -> _ArchiveParser:
    parser = _ArchiveParser()
    parser.feed(text)
    parser.close()
    return parser


def _one_table(
    tables: list[_Table], predicate: Callable[[str], bool], description: str
) -> _Table:
    matches = [table for table in tables if predicate(_label(table.caption))]
    if len(matches) != 1:
        raise ValueError(f"Archived BLS release requires exactly one {description}")
    return matches[0]


def _cpi_index_series(table: _Table) -> dict[str, dict[str, float]]:
    grid = table.grid()
    header_rows = _header_row_indexes(table)
    if not header_rows:
        raise ValueError("BLS CPI Table 1 is missing headers")
    headers = _column_headers(grid, header_rows)
    period_columns: dict[int, str] = {}
    for column, parts in headers.items():
        normalized = [_label(part) for part in parts]
        period = _first_month_period(parts)
        if period and "unadjusted indexes" in normalized:
            period_columns[column] = period
    if not period_columns:
        raise ValueError("BLS CPI Table 1 has no unadjusted index columns")
    return _labeled_series(
        table,
        period_columns,
        {
            "all items": "CPI_INDEX_NSA",
            "all items less food and energy": "CORE_CPI_INDEX_NSA",
        },
    )


def _employment_series(
    table: _Table, row_label: str, *, required_section: str
) -> dict[str, float]:
    grid = table.grid()
    header_rows = _header_row_indexes(table)
    headers = _column_headers(grid, header_rows)
    period_columns = {
        column: period
        for column, parts in headers.items()
        if (period := _first_month_period(parts)) is not None
        and not any("change from" in _label(part) for part in parts)
    }
    section = ""
    output: dict[str, float] = {}
    for row_index, row in enumerate(grid):
        if row_index in header_rows or not row:
            continue
        first = _label(row[0])
        unique = {_label(value) for value in row if value}
        if len(unique) == 1 and first:
            section = first
            continue
        if first != _label(row_label) or required_section not in section:
            continue
        for column, period in period_columns.items():
            if column >= len(row) or _missing(row[column]):
                continue
            _store_value(output, period, _number(row[column]), row_label)
    return output


def _labeled_series(
    table: _Table,
    period_columns: dict[int, str],
    labels: dict[str, str],
) -> dict[str, dict[str, float]]:
    header_rows = set(_header_row_indexes(table))
    output: dict[str, dict[str, float]] = {}
    for row_index, row in enumerate(table.grid()):
        if row_index in header_rows or not row:
            continue
        code = labels.get(_label(row[0]))
        if code is None:
            continue
        series = output.setdefault(code, {})
        for column, period in period_columns.items():
            if column >= len(row) or _missing(row[column]):
                continue
            _store_value(series, period, _number(row[column]), code)
    return output


def _store_value(series: dict[str, float], period: str, value: float, label: str) -> None:
    existing = series.get(period)
    if existing is not None and existing != value:
        raise ValueError(f"Conflicting duplicate BLS table row for {label} {period}")
    series[period] = value


def _header_row_indexes(table: _Table) -> tuple[int, ...]:
    explicit = tuple(
        index for index, row in enumerate(table.rows) if row.section == "thead"
    )
    if explicit:
        return explicit
    inferred: list[int] = []
    for index, row in enumerate(table.rows):
        if row.cells and all(cell.header for cell in row.cells):
            inferred.append(index)
        else:
            break
    return tuple(inferred)


def _column_headers(
    grid: tuple[tuple[str, ...], ...], header_rows: tuple[int, ...]
) -> dict[int, tuple[str, ...]]:
    width = max((len(row) for row in grid), default=0)
    output: dict[int, tuple[str, ...]] = {}
    for column in range(width):
        parts: list[str] = []
        for row_index in header_rows:
            value = grid[row_index][column]
            if value and (not parts or value != parts[-1]):
                parts.append(value)
        output[column] = tuple(parts)
    return output


def _expand_rows(rows: tuple[_RawRow, ...]) -> tuple[tuple[str, ...], ...]:
    active: dict[int, tuple[str, int]] = {}
    expanded: list[tuple[str, ...]] = []
    for raw in rows:
        current: dict[int, str] = {
            column: value for column, (value, _) in active.items()
        }
        new_spans: dict[int, tuple[str, int]] = {}
        column = 0
        for cell in raw.cells:
            while column in current:
                column += 1
            for offset in range(cell.colspan):
                target = column + offset
                if target in current:
                    raise ValueError("Overlapping BLS table spans")
                current[target] = cell.text
                if cell.rowspan > 1:
                    new_spans[target] = (cell.text, cell.rowspan - 1)
            column += cell.colspan
        width = max(current, default=-1) + 1
        expanded.append(tuple(current.get(index, "") for index in range(width)))
        next_active: dict[int, tuple[str, int]] = {}
        for target, (value, remaining) in active.items():
            if remaining > 1:
                next_active[target] = (value, remaining - 1)
        next_active.update(new_spans)
        active = next_active
    width = max((len(row) for row in expanded), default=0)
    return tuple(row + ("",) * (width - len(row)) for row in expanded)


def _nfp_revisions(text: str, current_period: str) -> dict[str, tuple[float, float]]:
    pattern = re.compile(
        r"(?:the\s+change\s+(?:in\s+total\s+nonfarm\s+payroll\s+employment\s+)?for\s+|"
        r"and\s+the\s+change\s+for\s+)"
        r"([A-Za-z]+)\s+was\s+revised\s+(?:up|down)\s+by\s+"
        r"[+\-]?\d[\d,]*,\s+from\s+([+\-]?\d[\d,]*)\s+to\s+([+\-]?\d[\d,]*)",
        flags=re.IGNORECASE,
    )
    revisions: dict[str, tuple[float, float]] = {}
    for match in pattern.finditer(text):
        period = _revision_period(match.group(1), current_period)
        values = (
            _number(match.group(2)),
            _number(match.group(3)),
        )
        existing = revisions.get(period)
        if existing is not None and existing != values:
            raise ValueError(f"Conflicting duplicate BLS NFP revision for {period}")
        revisions[period] = values
    return revisions


def _revision_period(month_name: str, current_period: str) -> str:
    month = _MONTHS.get(month_name.lower().rstrip("."))
    if month is None:
        raise ValueError(f"Unsupported BLS revision month: {month_name}")
    current_year, current_month = (int(value) for value in current_period.split("-"))
    year = current_year if month < current_month else current_year - 1
    return f"{year:04d}-{month:02d}"


def _embargo_timestamp(text: str) -> datetime:
    match = re.search(
        r"embargoed\s+until\s+(\d{1,2}):(\d{2})\s*"
        r"([ap])\.?m\.?\s*\((ET|EST|EDT)\)\s*"
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?[,]?\s*"
        r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise ValueError("Archived BLS release is missing an embargo timestamp")
    hour = int(match.group(1)) % 12
    if match.group(3).lower() == "p":
        hour += 12
    month_name = match.group(5).lower().rstrip(".")
    if month_name not in _MONTHS:
        raise ValueError(f"Unsupported BLS release month: {match.group(5)}")
    timestamp = datetime(
        int(match.group(7)),
        _MONTHS[month_name],
        int(match.group(6)),
        hour,
        int(match.group(2)),
        tzinfo=EASTERN,
    )
    if timestamp.utcoffset() is None:
        raise ValueError("BLS embargo timestamp must include a UTC offset")
    zone_label = match.group(4).upper()
    expected = "EDT" if timestamp.dst() else "EST"
    if zone_label in {"EST", "EDT"} and zone_label != expected:
        raise ValueError("BLS embargo timezone label conflicts with the release date")
    return timestamp


def _span(raw: str | None, field: str) -> int:
    if raw is None:
        return 1
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"BLS table {field} must be an integer") from error
    if value < 1:
        raise ValueError(f"BLS table {field} must be positive")
    return value


def _first_month_period(parts: tuple[str, ...]) -> str | None:
    periods = [period for part in parts if (period := _month_period(part)) is not None]
    if not periods:
        return None
    return periods[-1]


def _month_period(value: str) -> str | None:
    match = re.fullmatch(
        r"([A-Za-z]+)\.?\s+(\d{4})(?:\s*\(?[pP]\)?)?", _space(value)
    )
    if match is None:
        return None
    month = _MONTHS.get(match.group(1).lower())
    if month is None:
        return None
    return f"{int(match.group(2)):04d}-{month:02d}"


def _previous_month(period: str) -> str:
    year, month = (int(value) for value in period.split("-"))
    if month == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{month - 1:02d}"


def _number(value: str) -> float:
    normalized = value.strip().replace(",", "").replace("−", "-")
    normalized = re.sub(r"[*†‡]+$", "", normalized).strip()
    try:
        return float(normalized)
    except ValueError as error:
        raise ValueError(f"Invalid numeric value in BLS table: {value!r}") from error


def _missing(value: str) -> bool:
    return value.strip().lower() in {"", "-", "--", "—", "na", "n/a"}


def _label(value: str) -> str:
    return _space(value).lower().rstrip(".: ")


def _space(value: str) -> str:
    return " ".join(value.split())


__all__ = [
    "ALLOWED_RELEASE_PREFIX",
    "CPI_ARCHIVE",
    "EMPLOYMENT_ARCHIVE",
    "build_bls_provider",
    "parse_cpi_release",
    "parse_employment_release",
]
