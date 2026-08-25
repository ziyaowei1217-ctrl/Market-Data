from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import pandas as pd

from ..economic_releases import (
    build_release_row,
    derive_price_index_rows,
    derive_real_gdp_rows,
)
from ..provider_contracts import (
    ContextProvider,
    HONG_KONG,
    PointInTimeUnavailable,
    ProviderResult,
    ProviderSpec,
    target_sunday_cutoff,
)


BEA_ARCHIVE = "https://www.bea.gov/news/archive"
SOURCE = "U.S. Bureau of Economic Analysis"
EASTERN = ZoneInfo("America/New_York")
ALLOWED_RELEASE_HOSTS = frozenset({"bea.gov", "www.bea.gov"})

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

    @property
    def searchable_title(self) -> str:
        if self.caption:
            return self.caption
        grid = self.grid()
        header_rows = _header_row_indexes(self)
        parts: list[str] = []
        for row_index in header_rows:
            for value in grid[row_index]:
                if value and value not in parts:
                    parts.append(value)
        return " ".join(parts)


@dataclass(frozen=True)
class _ArchiveEntry:
    title: str
    url: str
    published: datetime


@dataclass(frozen=True)
class _ReleaseMetadata:
    family: str
    released: datetime
    title: str
    observation_period: str
    vintage_date: str


class _DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[_Table] = []
        self.text_parts: list[str] = []
        self.headings: list[str] = []
        self.archive_entries: list[tuple[str, str, str]] = []
        self.links: list[tuple[str, str, str]] = []
        self._rows: list[_RawRow] | None = None
        self._row: list[_Cell] | None = None
        self._cell_parts: list[str] | None = None
        self._cell_attrs: dict[str, str | None] = {}
        self._cell_header = False
        self._caption_parts: list[str] | None = None
        self._caption = ""
        self._section = ""
        self._heading_parts: list[str] | None = None
        self._row_links: list[tuple[str, list[str]]] = []
        self._active_link: tuple[str, list[str], str] | None = None
        self._row_time = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table":
            if self._rows is not None:
                raise ValueError("Nested BEA tables are not supported")
            self._rows = []
            self._caption = ""
            self._section = ""
        elif tag in {"thead", "tbody", "tfoot"} and self._rows is not None:
            self._section = tag
        elif tag == "caption" and self._rows is not None:
            self._caption_parts = []
        elif tag == "tr" and self._rows is not None:
            self._row = []
            self._row_links = []
            self._row_time = ""
        elif tag in {"td", "th"} and self._row is not None:
            self._cell_parts = []
            self._cell_attrs = attributes
            self._cell_header = tag == "th"
        elif tag == "a" and attributes.get("href"):
            self._active_link = (
                str(attributes["href"]),
                [],
                str(attributes.get("rel") or ""),
            )
        elif tag == "time" and self._row is not None and attributes.get("datetime"):
            self._row_time = str(attributes["datetime"])
        elif tag in {"h1", "h2"}:
            self._heading_parts = []

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        if self._caption_parts is not None:
            self._caption_parts.append(data)
        if self._cell_parts is not None:
            self._cell_parts.append(data)
        if self._heading_parts is not None:
            self._heading_parts.append(data)
        if self._active_link is not None:
            self._active_link[1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._active_link is not None:
            href, parts, rel = self._active_link
            self.links.append((href, _space(" ".join(parts)), rel))
            if self._row is not None:
                self._row_links.append((href, parts))
            self._active_link = None
        elif tag in {"td", "th"} and self._cell_parts is not None:
            if self._row is None:
                raise ValueError("BEA table cell appears outside a row")
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
                raise ValueError("BEA table row appears outside a table")
            if self._row:
                self._rows.append(_RawRow(tuple(self._row), self._section))
            if self._row_time:
                for href, parts in self._row_links:
                    self.archive_entries.append(
                        (href, _space(" ".join(parts)), self._row_time)
                    )
            self._row = None
            self._row_links = []
            self._row_time = ""
        elif tag in {"thead", "tbody", "tfoot"} and self._rows is not None:
            self._section = ""
        elif tag == "table" and self._rows is not None:
            self.tables.append(_Table(self._caption, tuple(self._rows)))
            self._rows = None
        elif tag in {"h1", "h2"} and self._heading_parts is not None:
            heading = _space(" ".join(self._heading_parts))
            if heading:
                self.headings.append(heading)
            self._heading_parts = None

    @property
    def text(self) -> str:
        return _space(" ".join(self.text_parts))


def parse_gdp_release(text: str, source_url: str, as_of_date: date) -> list[dict]:
    metadata = _gdp_release_metadata(text)
    return _parse_gdp_artifact(text, source_url, as_of_date, metadata)


def _parse_gdp_artifact(
    text: str,
    source_url: str,
    as_of_date: date,
    metadata: _ReleaseMetadata,
) -> list[dict]:
    _require_release_url(source_url)
    document = _parse_document(text)
    released = metadata.released
    vintage = metadata.vintage_date
    observation_period = metadata.observation_period
    if released.astimezone(HONG_KONG) > target_sunday_cutoff(as_of_date):
        return []

    level_tables = [
        table
        for table in document.tables
        if (
            "real gross domestic product" in _label(table.searchable_title)
            or _label(table.searchable_title).startswith(
                "table 3. gross domestic product: level"
            )
        )
        and re.search(
            r"chained(?:\s*\([^)]*\))?\s+dollars",
            _label(table.searchable_title + " " + _table_text(table)),
        )
    ]
    if len(level_tables) != 1:
        raise ValueError(
            "Archived BEA GDP release requires exactly one real-GDP chained-dollar table"
        )
    table = level_tables[0]
    table_text = _label(_table_text(table))
    if "seasonally adjusted at annual rates" not in table_text:
        raise ValueError("BEA real-GDP table must be seasonally adjusted at annual rates")
    periods = _quarter_columns(table)
    levels = _series_for_label(
        table,
        periods,
        frozenset({"gross domestic product", "gross domestic product (gdp)"}),
        required_section=None,
        series_name="real GDP",
    )
    if not levels:
        raise ValueError("Archived BEA GDP release is missing real GDP levels")
    if max(levels) != observation_period:
        raise ValueError("BEA GDP table latest quarter conflicts with the release title")

    common = _release_common(
        released=released,
        source_url=source_url,
        as_of_date=as_of_date,
        vintage_date=vintage,
        frequency="quarterly",
        seasonal_adjustment="seasonally adjusted at annual rates",
    )
    observed: list[dict] = []
    for period in sorted(levels):
        observed.append(
            build_release_row(
                indicator_code="REAL_GDP_LEVEL_SAAR",
                indicator_name="Real gross domestic product",
                observation_period=period,
                value=levels[period],
                previous_value=levels.get(_previous_quarter(period)),
                unit="billions_chained_dollars",
                **common,
            )
        )
    derived = derive_real_gdp_rows(observed)
    required_codes = {"REAL_GDP_QOQ_SAAR", "REAL_GDP_YOY_PCT"}
    current_codes = {
        str(row["indicator_code"])
        for row in derived
        if row["observation_period"] == observation_period
    }
    if not required_codes <= current_codes:
        raise ValueError("Archived BEA GDP table lacks quarterly or year-ago bases")
    return observed + derived


def parse_pio_release(text: str, source_url: str, as_of_date: date) -> list[dict]:
    metadata = _pio_release_metadata(text)
    return _parse_pio_artifact(text, source_url, as_of_date, metadata)


def _parse_pio_artifact(
    text: str,
    source_url: str,
    as_of_date: date,
    metadata: _ReleaseMetadata,
) -> list[dict]:
    _require_release_url(source_url)
    document = _parse_document(text)
    released = metadata.released
    observation_period = metadata.observation_period
    vintage = metadata.vintage_date
    if released.astimezone(HONG_KONG) > target_sunday_cutoff(as_of_date):
        return []

    level_table = _one_table(
        document.tables,
        lambda table: _label(table.searchable_title).startswith(
            "table 5. price indexes for personal consumption expenditures: level"
        ),
        "PIO Table 5 price-index table",
    )
    periods = _month_columns(level_table)
    headline = _series_for_label(
        level_table,
        periods,
        frozenset({"personal consumption expenditures (pce)"}),
        required_section="chain-type price indexes",
        series_name="PCE price index",
    )
    core = _series_for_label(
        level_table,
        periods,
        frozenset({"pce excluding food and energy"}),
        required_section="chain-type price indexes",
        series_name="Core PCE price index",
    )
    if not headline or not core:
        raise ValueError("Archived BEA PIO release is missing headline or Core PCE levels")
    if max(headline) != observation_period or max(core) != observation_period:
        raise ValueError("BEA PCE table latest month conflicts with the release title")

    common = _release_common(
        released=released,
        source_url=source_url,
        as_of_date=as_of_date,
        vintage_date=vintage,
        frequency="monthly",
        seasonal_adjustment="seasonally adjusted",
    )
    observed: list[dict] = []
    for code, name, series in (
        ("PCE_PRICE_INDEX", "PCE price index", headline),
        (
            "CORE_PCE_PRICE_INDEX",
            "PCE price index excluding food and energy",
            core,
        ),
    ):
        for period in sorted(series):
            observed.append(
                build_release_row(
                    indicator_code=code,
                    indicator_name=name,
                    observation_period=period,
                    value=series[period],
                    previous_value=series.get(_previous_month(period)),
                    unit="index",
                    **common,
                )
            )

    derived: list[dict] = []
    for code in ("PCE_PRICE_INDEX", "CORE_PCE_PRICE_INDEX"):
        derived.extend(derive_price_index_rows(observed, code))
    _validate_published_pce_yoy(document.tables, derived, observation_period)
    required_codes = {
        "PCE_PRICE_INDEX_MOM_PCT",
        "PCE_PRICE_INDEX_YOY_PCT",
        "PCE_PRICE_INDEX_3M_ANN_PCT",
        "CORE_PCE_PRICE_INDEX_MOM_PCT",
        "CORE_PCE_PRICE_INDEX_YOY_PCT",
        "CORE_PCE_PRICE_INDEX_3M_ANN_PCT",
    }
    current_codes = {
        str(row["indicator_code"])
        for row in derived
        if row["observation_period"] == observation_period
    }
    if not required_codes <= current_codes:
        raise ValueError("Archived BEA PIO table lacks required monthly calculation bases")
    return observed + derived


def build_bea_provider(start: date, end: date, session) -> ContextProvider:
    if end < start:
        raise ValueError("Report end must not precede start")

    def fetch() -> ProviderResult:
        entries = _collect_archive_entries(session, end)
        gdp_rows, gdp_text, gdp_url = _latest_release(
            session,
            entries,
            lambda entry: _is_gdp_title(entry.title),
            end,
            "GDP",
            "gdp",
        )
        pio_rows, pio_text, pio_url = _latest_release(
            session,
            entries,
            lambda entry: _is_pio_title(entry.title),
            end,
            "Personal Income and Outlays",
            "pio",
        )
        rows = gdp_rows + pio_rows
        required = {
            "REAL_GDP_QOQ_SAAR",
            "REAL_GDP_YOY_PCT",
            "PCE_PRICE_INDEX_MOM_PCT",
            "PCE_PRICE_INDEX_YOY_PCT",
            "PCE_PRICE_INDEX_3M_ANN_PCT",
            "CORE_PCE_PRICE_INDEX_MOM_PCT",
            "CORE_PCE_PRICE_INDEX_YOY_PCT",
            "CORE_PCE_PRICE_INDEX_3M_ANN_PCT",
        }
        present = {str(row["indicator_code"]) for row in rows}
        missing = sorted(required - present)
        if missing:
            raise ValueError("Archived BEA provider is missing: " + ", ".join(missing))
        return ProviderResult(
            category="economic_releases",
            rows=rows,
            raw_text=(
                f"SOURCE {gdp_url}\n{gdp_text}\n"
                f"SOURCE {pio_url}\n{pio_text}"
            ),
            source=SOURCE,
            source_url=BEA_ARCHIVE,
        )

    return ContextProvider(
        spec=ProviderSpec(
            name="bea_economic_releases",
            category="economic_releases",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="monthly_and_quarterly",
            freshness_days=100,
        ),
        fetch=fetch,
    )


def _latest_release(
    session,
    entries: list[_ArchiveEntry],
    predicate: Callable[[_ArchiveEntry], bool],
    as_of_date: date,
    description: str,
    family: str,
) -> tuple[list[dict], str, str]:
    cutoff = target_sunday_cutoff(as_of_date)
    eligible = [
        entry
        for entry in entries
        if predicate(entry) and entry.published.astimezone(HONG_KONG) <= cutoff
    ]
    if not eligible:
        raise PointInTimeUnavailable(
            f"No official BEA {description} release existed by {as_of_date.isoformat()}"
        )
    latest_published = max(entry.published for entry in eligible)
    candidates = sorted(
        (entry for entry in eligible if entry.published == latest_published),
        key=lambda entry: entry.url,
    )
    parsed: list[tuple[list[dict], str, str]] = []
    for entry in candidates:
        release_page = _get_text(session, entry.url)
        metadata = (
            _gdp_release_metadata(release_page)
            if family == "gdp"
            else _pio_release_metadata(release_page)
        )
        artifact, artifact_url = _release_artifact(
            session,
            entry.url,
            release_page,
            family,
            metadata,
        )
        rows = (
            _parse_gdp_artifact(artifact, artifact_url, as_of_date, metadata)
            if family == "gdp"
            else _parse_pio_artifact(artifact, artifact_url, as_of_date, metadata)
        )
        if not rows:
            raise ValueError(
                "BEA archive timestamp is eligible but artifact timestamp is not: "
                f"{artifact_url}"
            )
        parsed.append((rows, artifact, artifact_url))
    _reject_conflicting_artifacts(parsed, description)
    return parsed[0]


def _collect_archive_entries(session, as_of_date: date) -> list[_ArchiveEntry]:
    current_url = BEA_ARCHIVE
    visited: set[str] = set()
    entries: list[_ArchiveEntry] = []
    seen_entries: set[tuple[str, datetime]] = set()
    cutoff = target_sunday_cutoff(as_of_date)

    while True:
        if current_url in visited:
            raise ValueError("BEA archive pagination cycle detected")
        visited.add(current_url)
        archive_text = _get_text(session, current_url)
        document = _parse_document(archive_text)
        for entry in _archive_release_entries(document, current_url):
            key = (entry.url, entry.published)
            if key not in seen_entries:
                seen_entries.add(key)
                entries.append(entry)

        eligible = [
            entry
            for entry in entries
            if entry.published.astimezone(HONG_KONG) <= cutoff
        ]
        if any(_is_gdp_title(entry.title) for entry in eligible) and any(
            _is_pio_title(entry.title) for entry in eligible
        ):
            break

        next_url = _archive_next_url(document, current_url)
        if next_url is None:
            break
        current_url = next_url

    if not entries:
        raise PointInTimeUnavailable("No official BEA archived release links found")
    return entries


def _archive_release_entries(
    document: _DocumentParser, archive_url: str
) -> list[_ArchiveEntry]:
    entries: list[_ArchiveEntry] = []
    seen: set[tuple[str, datetime]] = set()
    for href, title, raw_published in document.archive_entries:
        url = urljoin(archive_url, href)
        _require_news_url(url)
        published = datetime.fromisoformat(raw_published)
        if published.tzinfo is None:
            raise ValueError("BEA archive publication time must include a UTC offset")
        key = (url, published)
        if key in seen:
            continue
        seen.add(key)
        entries.append(_ArchiveEntry(title=title, url=url, published=published))
    return entries


def _archive_next_url(document: _DocumentParser, current_url: str) -> str | None:
    next_links = [href for href, _, rel in document.links if "next" in rel.split()]
    if not next_links:
        return None
    if len(next_links) != 1:
        raise ValueError("BEA archive page has ambiguous next links")
    next_url = urljoin(current_url, next_links[0])
    _require_archive_url(next_url)
    return next_url


def _reject_conflicting_artifacts(
    candidates: list[tuple[list[dict], str, str]], description: str
) -> None:
    if len(candidates) < 2:
        return
    baseline = _semantic_rows(candidates[0][0])
    for rows, _, url in candidates[1:]:
        if _semantic_rows(rows) != baseline:
            raise ValueError(
                f"Conflicting BEA {description} artifacts for the same publication time: {url}"
            )


def _semantic_rows(rows: list[dict]) -> dict[tuple[str, str, str], tuple[object, ...]]:
    return {
        (
            str(row["indicator_code"]),
            str(row["observation_period"]),
            str(row["calculation_id"]),
        ): (
            row["value"],
            row["unit"],
            row["seasonal_adjustment"],
            row["vintage_date"],
            row["known_as_of"],
        )
        for row in rows
    }


def _validate_published_pce_yoy(
    tables: list[_Table], derived: list[dict], observation_period: str
) -> None:
    matches = [
        table
        for table in tables
        if _label(table.searchable_title).startswith(
            "table 7. price indexes for personal consumption expenditures: "
            "percent change from month one year ago"
        )
    ]
    if not matches:
        return
    if len(matches) != 1:
        raise ValueError("Archived BEA PIO release requires at most one PIO Table 7")
    periods = _month_columns(matches[0])
    published = {
        "PCE_PRICE_INDEX_YOY_PCT": _series_for_label(
            matches[0],
            periods,
            frozenset({"personal consumption expenditures (pce)"}),
            required_section=None,
            series_name="PCE published YoY",
        ),
        "CORE_PCE_PRICE_INDEX_YOY_PCT": _series_for_label(
            matches[0],
            periods,
            frozenset({"pce excluding food and energy"}),
            required_section=None,
            series_name="Core PCE published YoY",
        ),
    }
    calculated = {
        str(row["indicator_code"]): float(row["value"])
        for row in derived
        if row["observation_period"] == observation_period
    }
    for code, series in published.items():
        if observation_period not in series:
            raise ValueError(f"Archived BEA PIO Table 7 is missing {code}")
        if (
            code in calculated
            and abs(calculated[code] - series[observation_period]) > 0.0500000001
        ):
            raise ValueError(f"BEA PCE level history conflicts with published {code}")


def _release_common(
    *,
    released: datetime,
    source_url: str,
    as_of_date: date,
    vintage_date: str,
    frequency: str,
    seasonal_adjustment: str,
) -> dict:
    return {
        "release_at_bjt": released.astimezone(HONG_KONG).isoformat(),
        "frequency": frequency,
        "source": SOURCE,
        "source_url": source_url,
        "known_as_of": released.isoformat(),
        "vintage_date": vintage_date,
        "as_of_date": as_of_date,
        "seasonal_adjustment": seasonal_adjustment,
    }


def _release_artifact(
    session,
    release_url: str,
    release_page: str,
    family: str,
    metadata: _ReleaseMetadata,
) -> tuple[str, str]:
    document = _parse_document(release_page)
    table_links = [
        (href, label)
        for href, label, _ in document.links
        if "tables only" in _label(label)
    ]
    if table_links:
        if len(table_links) != 1:
            raise ValueError("BEA release has ambiguous Tables Only attachments")
        artifact_url = urljoin(release_url, table_links[0][0])
        try:
            kind = _require_artifact_url(artifact_url, machine_readable=True)
        except ValueError as error:
            raise ValueError(
                f"BEA Tables Only link is not an official BEA attachment: {artifact_url}"
            ) from error
    else:
        pdf_links = [
            (href, label)
            for href, label, _ in document.links
            if "full release" in _label(label) and "table" in _label(label)
        ]
        if len(pdf_links) != 1:
            raise ValueError(
                "BEA release has no trustworthy release-specific artifact"
            )
        artifact_url = urljoin(release_url, pdf_links[0][0])
        try:
            kind = _require_artifact_url(artifact_url, machine_readable=False)
        except ValueError as error:
            raise ValueError(
                f"BEA Full Release link is not an official BEA attachment: {artifact_url}"
            ) from error
        if kind != "pdf":
            raise ValueError("BEA release has no trustworthy release-specific artifact")

    _require_family_artifact_identity(artifact_url, family)

    response = _get_response(session, artifact_url)
    content = _response_content(response)
    content_type = str(getattr(response, "headers", {}).get("Content-Type", ""))
    media_type = content_type.split(";", 1)[0].strip().lower()
    if kind == "xlsx":
        expected = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        if media_type != expected:
            raise ValueError("BEA XLSX attachment has an invalid content type")
        if not content.startswith(b"PK"):
            raise ValueError("BEA XLSX signature is invalid")
        tables = _xlsx_tables_html(content, family)
    elif kind == "html":
        if media_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError("BEA HTML attachment has an invalid content type")
        tables = content.decode("utf-8", errors="strict")
        _validate_artifact_tables(tables, family)
    else:
        if media_type != "application/pdf":
            raise ValueError("BEA PDF attachment has an invalid content type")
        if not content.startswith(b"%PDF"):
            raise ValueError("BEA PDF signature is invalid")
        tables = _pdf_tables_html(content, metadata)
        _validate_artifact_tables(tables, family)
    return tables, artifact_url


def _xlsx_tables_html(content: bytes, family: str) -> str:
    sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, header=None)
    tables: list[str] = []
    for frame in sheets.values():
        matrix = [
            [_excel_cell(value) for value in row]
            for row in frame.itertuples(index=False, name=None)
        ]
        title_position = next(
            (
                (row_index, value)
                for row_index, row in enumerate(matrix)
                for value in row
                if _label(value).startswith("table ")
            ),
            None,
        )
        if title_position is None:
            continue
        title_row, title = title_position
        if not re.match(r"table (3|5|7)\.", _label(title)):
            continue
        body = matrix[title_row + 1 :]
        while body and not any(body[0]):
            body.pop(0)
        while body and not any(body[-1]):
            body.pop()
        if not body:
            raise ValueError(f"BEA workbook table is empty: {title}")
        header_count = _workbook_header_count(body)
        if header_count == 0:
            raise ValueError(f"BEA workbook table has no headers: {title}")
        tables.append(_matrix_table_html(title, body, header_count))
    if not tables:
        raise ValueError("BEA workbook contains no supported release tables")
    output = "".join(tables)
    _validate_artifact_tables(output, family)
    return output


def _workbook_header_count(rows: list[list[str]]) -> int:
    for index, row in enumerate(rows):
        first = row[0].strip() if row else ""
        joined = _label(" ".join(row))
        if re.fullmatch(r"\d+(?:\.0+)?", first) or (
            "chain-type price indexes" in joined and index > 0
        ):
            return index
    return 0


def _matrix_table_html(
    caption: str,
    rows: list[list[str]],
    header_count: int,
) -> str:
    width = max(len(row) for row in rows)

    def rendered_row(row: list[str], tag: str) -> str:
        padded = row + [""] * (width - len(row))
        return "<tr>" + "".join(
            f"<{tag}>{escape(value)}</{tag}>" for value in padded
        ) + "</tr>"

    return (
        f"<table><caption>{escape(caption)}</caption><thead>"
        + "".join(rendered_row(row, "th") for row in rows[:header_count])
        + "</thead><tbody>"
        + "".join(rendered_row(row, "td") for row in rows[header_count:])
        + "</tbody></table>"
    )


def _excel_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return _space(str(value))


def _validate_artifact_tables(text: str, family: str) -> None:
    document = _parse_document(text)
    titles = [_label(table.searchable_title) for table in document.tables]
    gdp = [
        title
        for title in titles
        if title.startswith("table 3. gross domestic product: level")
    ]
    pio_5 = [
        title
        for title in titles
        if title.startswith(
            "table 5. price indexes for personal consumption expenditures: level"
        )
    ]
    pio_7 = [
        title
        for title in titles
        if title.startswith(
            "table 7. price indexes for personal consumption expenditures: "
            "percent change from month one year ago"
        )
    ]
    if family == "gdp":
        if len(gdp) != 1 or pio_5 or pio_7:
            raise ValueError(
                "BEA GDP artifact must contain exactly one GDP Table 3 and no PIO tables"
            )
    elif family == "pio":
        if len(pio_5) != 1 or len(pio_7) != 1 or gdp:
            raise ValueError(
                "BEA PIO artifact must contain exactly one Table 5 and one Table 7"
            )
    else:
        raise ValueError(f"Unsupported BEA release family: {family}")


def _pdf_tables_html(content: bytes, metadata: _ReleaseMetadata) -> str:
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
    if metadata.family == "pio":
        return _pio_pdf_tables_html(text, metadata.observation_period)
    raise ValueError("BEA GDP PDF fallback has no supported machine-readable layout")


def _pio_pdf_tables_html(text: str, observation_period: str) -> str:
    year, observation_month = (int(value) for value in observation_period.split("-"))
    table_5, table_7 = _pio_pdf_sections(text)

    level_months = _pdf_month_headers(table_5)
    yoy_months = _pdf_month_headers(table_7)
    level_years = _years_for_months(level_months, year, observation_month)
    yoy_years = _years_for_months(yoy_months, year, observation_month)
    headline_levels = _pdf_series_values(
        table_5, 1, "Personal consumption expenditures (PCE)", len(level_months)
    )
    core_levels = _pdf_series_values(
        table_5, 6, "PCE excluding food and energy", len(level_months)
    )
    headline_yoy = _pdf_series_values(
        table_7, 1, "Personal consumption expenditures (PCE)", len(yoy_months)
    )
    core_yoy = _pdf_series_values(
        table_7, 6, "PCE excluding food and energy", len(yoy_months)
    )

    table_5_rows = [
        ["Line", ""] + [str(value) for value in level_years],
        ["Line", ""] + level_months,
        ["", "Chain-type price indexes (2017=100), seasonally adjusted"],
        ["1", "Personal consumption expenditures (PCE)"]
        + [str(value) for value in headline_levels],
        ["6", "PCE excluding food and energy"]
        + [str(value) for value in core_levels],
    ]
    table_7_rows = [
        ["Line", ""] + [str(value) for value in yoy_years],
        ["Line", ""] + yoy_months,
        ["1", "Personal consumption expenditures (PCE)"]
        + [str(value) for value in headline_yoy],
        ["6", "PCE excluding food and energy"]
        + [str(value) for value in core_yoy],
    ]
    return _matrix_table_html(
        "Table 5. Price Indexes for Personal Consumption Expenditures: "
        "Level and Percent Change from Preceding Period (Months)",
        table_5_rows,
        2,
    ) + _matrix_table_html(
        "Table 7. Price Indexes for Personal Consumption Expenditures: "
        "Percent Change from Month One Year Ago",
        table_7_rows,
        2,
    )


def _pio_pdf_sections(text: str) -> tuple[str, str]:
    table_5_markers = list(re.finditer(r"(?m)^Table 5\.", text))
    table_7_markers = list(re.finditer(r"(?m)^Table 7\.", text))
    if len(table_5_markers) != 1 or len(table_7_markers) != 1:
        raise ValueError(
            "BEA PIO PDF requires unique Table 5 and Table 7 markers"
        )
    table_5_start = table_5_markers[0].start()
    table_7_start = table_7_markers[0].start()
    if table_5_start >= table_7_start:
        raise ValueError("BEA PIO PDF Table 5 must precede Table 7")
    table_5 = text[table_5_start:table_7_start]
    next_marker = re.search(r"(?m)^Table \d+\.", text[table_7_start + 1 :])
    table_7_end = (
        len(text)
        if next_marker is None
        else table_7_start + 1 + next_marker.start()
    )
    table_7 = text[table_7_start:table_7_end]
    expected_5 = (
        "Table 5. Price Indexes for Personal Consumption Expenditures: "
        "Level and Percent Change from Preceding Period (Months)"
    )
    expected_7 = (
        "Table 7. Price Indexes for Personal Consumption Expenditures: "
        "Percent Change from Month One Year Ago"
    )
    if expected_5 not in _space(table_5) or expected_7 not in _space(table_7):
        raise ValueError("BEA PIO PDF has ambiguous Table 5 or Table 7 identity")
    return table_5, table_7


def _pdf_month_headers(text: str) -> list[str]:
    matches = list(re.finditer(r"(?m)^Line\s+(.+)$", text))
    if len(matches) != 1:
        raise ValueError(
            "BEA PIO PDF table requires one unique Line month header"
        )
    match = matches[0]
    months = re.findall(
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?(?:\s+[rpe])?",
        match.group(1),
        flags=re.IGNORECASE,
    )
    if not months:
        raise ValueError("BEA PIO PDF table has no month columns")
    return [_space(month) for month in months]


def _years_for_months(
    month_headers: list[str], observation_year: int, observation_month: int
) -> list[int]:
    months = [
        _MONTHS[re.sub(r"\s+[rpe]$", "", value.lower()).rstrip(".")]
        for value in month_headers
    ]
    if months[-1] != observation_month:
        raise ValueError("BEA PIO PDF latest month conflicts with the release title")
    years = [observation_year] * len(months)
    current_year = observation_year
    later_month = months[-1]
    for index in range(len(months) - 2, -1, -1):
        if months[index] > later_month:
            current_year -= 1
        years[index] = current_year
        later_month = months[index]
    return years


def _pdf_series_values(
    text: str, line_number: int, label: str, expected_count: int
) -> list[float]:
    matches = list(re.finditer(
        rf"(?m)^\s*{line_number}\s+{re.escape(label)}\s+(.+?)\s+{line_number}\s*$",
        text,
    ))
    if len(matches) != 1:
        raise ValueError(f"BEA PIO PDF has duplicate or ambiguous rows for {label}")
    match = matches[0]
    values = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", match.group(1))]
    if len(values) != expected_count:
        raise ValueError(f"BEA PIO PDF has ambiguous values for {label}")
    return values


def _get_text(session, url: str) -> str:
    response = _get_response(session, url)
    return str(response.text)


def _get_response(session, url: str):
    response = session.get(url, timeout=30, allow_redirects=False)
    status = int(getattr(response, "status_code", 200))
    history = getattr(response, "history", ())
    final_url = str(getattr(response, "url", url))
    if history or 300 <= status < 400 or final_url != url:
        raise ValueError(f"BEA request must not redirect: {url}")
    response.raise_for_status()
    return response


def _response_content(response) -> bytes:
    content = getattr(response, "content", None)
    if isinstance(content, bytes):
        return content
    return str(getattr(response, "text", "")).encode("utf-8")


def _require_release_url(url: str) -> None:
    try:
        _require_news_url(url)
    except ValueError:
        try:
            _require_artifact_url(url, machine_readable=None)
        except ValueError as error:
            raise ValueError(f"URL is outside an official BEA release: {url}") from error


def _require_news_url(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_RELEASE_HOSTS
        or re.fullmatch(r"/news/\d{4}/[a-z0-9][a-z0-9-]*", parsed.path) is None
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"URL is outside an official BEA release: {url}")


def _require_archive_url(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_RELEASE_HOSTS
        or parsed.path != "/news/archive"
        or parsed.params
        or (parsed.query and re.fullmatch(r"page=\d+", parsed.query) is None)
        or parsed.fragment
    ):
        raise ValueError(f"URL is outside the official BEA archive: {url}")


def _require_artifact_url(
    url: str, machine_readable: bool | None
) -> str:
    parsed = urlparse(url)
    match = re.fullmatch(
        r"/sites/default/files/\d{4}-\d{2}/[A-Za-z0-9][A-Za-z0-9._-]*\.(xlsx|html?|pdf)",
        parsed.path,
        flags=re.IGNORECASE,
    )
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_RELEASE_HOSTS
        or match is None
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"URL is outside an official BEA attachment: {url}")
    extension = match.group(1).lower()
    kind = "html" if extension in {"htm", "html"} else extension
    if machine_readable is True and kind not in {"xlsx", "html"}:
        raise ValueError(f"BEA Tables Only attachment is not machine readable: {url}")
    return kind


def _require_family_artifact_identity(url: str, family: str) -> None:
    filename = urlparse(url).path.rsplit("/", 1)[-1].lower()
    if family == "gdp":
        matches = filename.startswith("gdp")
    elif family == "pio":
        matches = re.match(r"pi\d", filename) is not None
    else:
        raise ValueError(f"Unsupported BEA release family: {family}")
    if not matches:
        raise ValueError(
            f"BEA {family.upper()} attachment identity conflicts with its release: {url}"
        )


def _parse_document(text: str) -> _DocumentParser:
    parser = _DocumentParser()
    parser.feed(text)
    parser.close()
    return parser


def _gdp_release_metadata(text: str) -> _ReleaseMetadata:
    document = _parse_document(text)
    title = _release_title(document, "GDP")
    return _ReleaseMetadata(
        family="gdp",
        released=_release_timestamp(document.text),
        title=title,
        observation_period=_gdp_observation_period(title),
        vintage_date=_gdp_estimate_label(title),
    )


def _pio_release_metadata(text: str) -> _ReleaseMetadata:
    document = _parse_document(text)
    title = _release_title(document, "Personal Income and Outlays")
    return _ReleaseMetadata(
        family="pio",
        released=_release_timestamp(document.text),
        title=title,
        observation_period=_pio_observation_period(title),
        vintage_date=_pio_vintage_label(document.text),
    )


def _release_title(document: _DocumentParser, expected: str) -> str:
    matches = [
        title
        for title in document.headings
        if (
            _is_gdp_release_heading(title)
            if expected == "GDP"
            else expected.lower() in title.lower()
        )
    ]
    if len(matches) != 1:
        raise ValueError(f"Archived BEA release requires exactly one {expected} title")
    return matches[0]


def _gdp_estimate_label(title: str) -> str:
    normalized = _label(title)
    if "annual update" in normalized:
        return "annual_update"
    labels = [
        label
        for phrase, label in (
            ("advance estimate", "advance"),
            ("second estimate", "second"),
            ("third estimate", "third"),
        )
        if phrase in normalized
    ]
    if len(labels) != 1:
        raise ValueError("Archived BEA GDP release is missing an unambiguous estimate label")
    return labels[0]


def _gdp_observation_period(title: str) -> str:
    normalized = _space(title)
    match = re.search(
        r"(?:\b([1-4])(?:st|nd|rd|th)|\b(first|second|third|fourth))\s+quarter"
        r"(?:\s+and\s+year)?\s+(\d{4})",
        normalized,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise ValueError("Archived BEA GDP release is missing its observation quarter")
    words = {"first": 1, "second": 2, "third": 3, "fourth": 4}
    quarter = int(match.group(1)) if match.group(1) else words[match.group(2).lower()]
    return f"{int(match.group(3)):04d}-Q{quarter}"


def _pio_observation_period(title: str) -> str:
    matches = list(
        re.finditer(
            r"\b(" + "|".join(_MONTHS) + r")\.?\s+(\d{4})\b",
            title,
            flags=re.IGNORECASE,
        )
    )
    if not matches:
        raise ValueError("Archived BEA PIO release is missing its observation month")
    match = matches[-1]
    return f"{int(match.group(2)):04d}-{_MONTHS[match.group(1).lower()]:02d}"


def _pio_vintage_label(text: str) -> str:
    normalized = _label(text)
    if "annual update" in normalized or "data update" in normalized:
        return "annual_update"
    return "initial"


def _release_timestamp(text: str) -> datetime:
    match = re.search(
        r"embargoed\s+until\s+release\s+at\s+(\d{1,2}):(\d{2})\s*"
        r"([ap])\.?m\.?\s+(EST|EDT|ET)[,]?\s*"
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?[,]?\s*"
        r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise ValueError("Archived BEA release is missing an embargo timestamp")
    month = _MONTHS.get(match.group(5).lower().rstrip("."))
    if month is None:
        raise ValueError(f"Unsupported BEA release month: {match.group(5)}")
    hour = int(match.group(1)) % 12
    if match.group(3).lower() == "p":
        hour += 12
    timestamp = datetime(
        int(match.group(7)),
        month,
        int(match.group(6)),
        hour,
        int(match.group(2)),
        tzinfo=EASTERN,
    )
    zone_label = match.group(4).upper()
    expected = "EDT" if timestamp.dst() else "EST"
    if zone_label in {"EST", "EDT"} and zone_label != expected:
        raise ValueError("BEA embargo timezone label conflicts with the release date")
    return timestamp


def _one_table(
    tables: list[_Table], predicate: Callable[[_Table], bool], description: str
) -> _Table:
    matches = [table for table in tables if predicate(table)]
    if len(matches) != 1:
        raise ValueError(f"Archived BEA release requires exactly one {description}")
    return matches[0]


def _quarter_columns(table: _Table) -> dict[int, str]:
    return _period_columns(table, _quarter_from_header, "quarterly")


def _month_columns(table: _Table) -> dict[int, str]:
    return _period_columns(table, _month_from_header, "monthly")


def _period_columns(
    table: _Table,
    parser: Callable[[tuple[str, ...]], str | None],
    frequency: str,
) -> dict[int, str]:
    grid = table.grid()
    header_rows = _header_row_indexes(table)
    if not header_rows:
        raise ValueError(f"BEA {frequency} table is missing headers")
    headers = _column_headers(grid, header_rows)
    output = {
        column: period
        for column, parts in headers.items()
        if (period := parser(parts)) is not None
    }
    if not output:
        raise ValueError(f"BEA {frequency} table has no observation-period columns")
    if len(set(output.values())) != len(output):
        raise ValueError(f"BEA {frequency} table has duplicate period columns")
    return output


def _quarter_from_header(parts: tuple[str, ...]) -> str | None:
    for part in reversed(parts):
        match = re.fullmatch(r"(\d{4})\s*[: -]?\s*Q([1-4])(?:\s*[a-z])?", _space(part), re.I)
        if match:
            return f"{int(match.group(1)):04d}-Q{int(match.group(2))}"
    years = [int(part) for part in parts if re.fullmatch(r"\d{4}", part)]
    quarters = [
        int(match.group(1))
        for part in parts
        if (match := re.fullmatch(r"Q([1-4])(?:\s*[a-z])?", _space(part), re.I))
    ]
    if years and quarters:
        return f"{years[-1]:04d}-Q{quarters[-1]}"
    return None


def _month_from_header(parts: tuple[str, ...]) -> str | None:
    year: int | None = None
    month: int | None = None
    for part in parts:
        normalized = _space(part).lower()
        normalized = re.sub(r"\s+[rpe]$", "", normalized).rstrip(".")
        combined = re.fullmatch(r"([a-z]+)\.?\s+(\d{4})(?:\s+[rpe])?", _space(part), re.I)
        if combined and combined.group(1).lower() in _MONTHS:
            month = _MONTHS[combined.group(1).lower()]
            year = int(combined.group(2))
            continue
        year_first = re.fullmatch(
            r"(\d{4})\s+([a-z]+)\.?(?:\s+[rpe])?", _space(part), re.I
        )
        if year_first and year_first.group(2).lower() in _MONTHS:
            year = int(year_first.group(1))
            month = _MONTHS[year_first.group(2).lower()]
            continue
        if re.fullmatch(r"\d{4}", normalized):
            year = int(normalized)
        elif normalized in _MONTHS:
            month = _MONTHS[normalized]
    if year is None or month is None:
        return None
    return f"{year:04d}-{month:02d}"


def _series_for_label(
    table: _Table,
    period_columns: dict[int, str],
    accepted_labels: frozenset[str],
    *,
    required_section: str | None,
    series_name: str,
) -> dict[str, float]:
    header_rows = set(_header_row_indexes(table))
    section = ""
    output: dict[str, float] = {}
    for row_index, row in enumerate(table.grid()):
        if row_index in header_rows or not row:
            continue
        unique = {_label(value) for value in row if value}
        if len(unique) == 1:
            candidate = next(iter(unique))
            if candidate and candidate != "addenda":
                section = candidate
            continue
        label = next(
            (_label(value) for value in row if _label(value) in accepted_labels),
            None,
        )
        if label is None:
            continue
        if required_section and required_section not in section:
            continue
        for column, period in period_columns.items():
            if column >= len(row) or _missing(row[column]):
                continue
            _store_value(output, period, _number(row[column]), series_name)
    return output


def _store_value(series: dict[str, float], period: str, value: float, label: str) -> None:
    if period in series:
        raise ValueError(f"Duplicate BEA table value for {label} {period}")
    series[period] = value


def _header_row_indexes(table: _Table) -> tuple[int, ...]:
    explicit = tuple(index for index, row in enumerate(table.rows) if row.section == "thead")
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
        current = {column: value for column, (value, _) in active.items()}
        new_spans: dict[int, tuple[str, int]] = {}
        column = 0
        for cell in raw.cells:
            while column in current:
                column += 1
            for offset in range(cell.colspan):
                target = column + offset
                if target in current:
                    raise ValueError("Overlapping BEA table spans")
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


def _previous_month(period: str) -> str:
    year, month = (int(value) for value in period.split("-"))
    return f"{year - 1:04d}-12" if month == 1 else f"{year:04d}-{month - 1:02d}"


def _previous_quarter(period: str) -> str:
    year, quarter = period.split("-Q")
    numeric_year, numeric_quarter = int(year), int(quarter)
    if numeric_quarter == 1:
        return f"{numeric_year - 1:04d}-Q4"
    return f"{numeric_year:04d}-Q{numeric_quarter - 1}"


def _number(value: str) -> float:
    normalized = value.strip().replace(",", "").replace("−", "-")
    normalized = re.sub(r"[*†‡]+$", "", normalized).strip()
    try:
        return float(normalized)
    except ValueError as error:
        raise ValueError(f"Invalid numeric value in BEA table: {value!r}") from error


def _missing(value: str) -> bool:
    return value.strip().lower() in {"", "-", "--", "—", "...", "…", "na", "n/a"}


def _table_text(table: _Table) -> str:
    return " ".join(value for row in table.grid() for value in row if value)


def _span(raw: str | None, field: str) -> int:
    if raw is None:
        return 1
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"BEA table {field} must be an integer") from error
    if value < 1:
        raise ValueError(f"BEA table {field} must be positive")
    return value


def _is_gdp_title(title: str) -> bool:
    normalized = _label(title)
    return (
        (normalized.startswith("gdp (") or normalized.startswith("gross domestic product"))
        and "quarter" in normalized
        and " by state" not in normalized
    )


def _is_gdp_release_heading(title: str) -> bool:
    normalized = _label(title)
    return (
        (normalized.startswith("gdp") or normalized.startswith("gross domestic product"))
        and "quarter" in normalized
    )


def _is_pio_title(title: str) -> bool:
    return _label(title).startswith("personal income and outlays")


def _label(value: str) -> str:
    return _space(value).lower().rstrip(".: ")


def _space(value: str) -> str:
    return " ".join(value.split())


__all__ = [
    "ALLOWED_RELEASE_HOSTS",
    "BEA_ARCHIVE",
    "build_bea_provider",
    "parse_gdp_release",
    "parse_pio_release",
]
