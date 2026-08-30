from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlparse

from ..economic_releases import build_release_row
from ..provider_contracts import (
    ContextProvider,
    HONG_KONG,
    ProviderResult,
    ProviderSpec,
    target_sunday_cutoff,
)
from .census_release_common import (
    SOURCE,
    latest_release,
    month_period,
    release_timestamp,
    require_census_pdf,
    signed,
    space,
)


CENSUS_HOUSING_RELEASES = "https://www.census.gov/construction/nrc/data/releases.html"
HOUSING_PATH = "/construction/nrc/"


def parse_housing_release(text: str, source_url: str, as_of_date: date) -> list[dict]:
    source_period = _source_period(source_url)
    normalized = space(text)
    released = release_timestamp(normalized)
    if released.astimezone(HONG_KONG) > target_sunday_cutoff(as_of_date):
        return []
    titles = re.findall(
        r"NEW RESIDENTIAL CONSTRUCTION,\s*([A-Z]+\s+\d{4})",
        normalized,
        flags=re.IGNORECASE,
    )
    if len(titles) != 1 or (period := month_period(titles[0])) is None:
        raise ValueError("Census housing release requires one observation-month title")
    if source_period != period:
        raise ValueError(
            "Census housing filename conflicts with the PDF observation period"
        )

    specs = (
        (
            "HOUSING_PERMITS_SAAR",
            "Privately-owned housing units authorized by building permits",
            r"housing units authorized by building permits in ([A-Za-z]+) were at a seasonally adjusted annual rate of ([\d,]+)\. This is ([\d.]+) percent(?: \([^)]*\)\*?)? (above|below) the revised ([A-Za-z]+) rate of ([\d,]+)",
        ),
        (
            "HOUSING_STARTS_SAAR",
            "Privately-owned housing starts",
            r"housing starts in ([A-Za-z]+) were at a seasonally adjusted annual rate of ([\d,]+)\. This is ([\d.]+) percent(?: \([^)]*\)\*?)? (above|below) the revised ([A-Za-z]+) estimate of ([\d,]+)",
        ),
        (
            "HOUSING_COMPLETIONS_SAAR",
            "Privately-owned housing completions",
            r"housing completions in ([A-Za-z]+) were at a seasonally adjusted annual rate of ([\d,]+)\. This is ([\d.]+) percent(?: \([^)]*\)\*?)? (above|below) the revised ([A-Za-z]+) estimate of ([\d,]+)",
        ),
    )
    common = {
        "release_at_bjt": released.astimezone(HONG_KONG).isoformat(),
        "frequency": "monthly",
        "source": SOURCE,
        "source_url": source_url,
        "known_as_of": released.isoformat(),
        "vintage_date": released.date().isoformat(),
        "as_of_date": as_of_date,
        "seasonal_adjustment": "seasonally adjusted annual rate",
    }
    rows = []
    for code, name, pattern in specs:
        matches = re.findall(pattern, normalized, flags=re.IGNORECASE)
        if len(matches) != 1:
            raise ValueError(
                f"Census housing release requires exactly one {code} headline"
            )
        (
            observed_month,
            current,
            published_change,
            direction,
            revised_month,
            previous,
        ) = matches[0]
        if not period.endswith(f"-{_month_number(observed_month):02d}"):
            raise ValueError(f"Census housing {code} month conflicts with release title")
        if _month_number(revised_month) != _previous_month_number(period):
            raise ValueError(
                f"Census housing {code} revised value must describe the previous month"
            )
        current_value = float(current.replace(",", ""))
        previous_value = float(previous.replace(",", ""))
        calculated = (current_value / previous_value - 1.0) * 100.0
        if abs(calculated - signed(direction, published_change)) > 0.11:
            raise ValueError(
                f"Census housing {code} level conflicts with published change"
            )
        rows.append(
            build_release_row(
                indicator_code=code,
                indicator_name=name,
                observation_period=period,
                value=current_value,
                previous_value=previous_value,
                unit="units_saar",
                **common,
            )
        )
    return rows


def build_census_housing_provider(start: date, end: date, session) -> ContextProvider:
    if end < start:
        raise ValueError("Report end must not precede start")

    def fetch() -> ProviderResult:
        rows, content, selected_url = latest_release(
            session,
            index_url=CENSUS_HOUSING_RELEASES,
            path_fragment=HOUSING_PATH,
            description="housing",
            as_of_date=end,
            parser=parse_housing_release,
        )
        required = {
            "HOUSING_PERMITS_SAAR",
            "HOUSING_STARTS_SAAR",
            "HOUSING_COMPLETIONS_SAAR",
        }
        present = {str(row["indicator_code"]) for row in rows}
        if required != present:
            raise ValueError("Archived Census housing provider is incomplete")
        return ProviderResult(
            category="economic_releases",
            rows=rows,
            raw_text=content,
            source=SOURCE,
            source_url=CENSUS_HOUSING_RELEASES,
            notes=f"selected artifact: {selected_url}",
        )

    return ContextProvider(
        spec=ProviderSpec(
            name="census_housing",
            category="economic_releases",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="monthly",
            freshness_days=60,
        ),
        fetch=fetch,
    )


def _month_number(value: str) -> int:
    period = month_period(f"{value} 2000")
    if period is None:
        raise ValueError(f"Unsupported Census housing month: {value}")
    return int(period[-2:])


def _previous_month_number(period: str) -> int:
    month = int(period[-2:])
    return 12 if month == 1 else month - 1


def _source_period(source_url: str) -> str:
    require_census_pdf(
        source_url,
        path_fragment=HOUSING_PATH,
        description="housing",
    )
    match = re.fullmatch(
        r"/construction/nrc/pdf/newresconst_(\d{4})(\d{2})\.pdf",
        urlparse(source_url).path,
        flags=re.IGNORECASE,
    )
    if match is None or not 1 <= int(match.group(2)) <= 12:
        raise ValueError("Census housing archive filename is not release-specific")
    return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"


__all__ = [
    "CENSUS_HOUSING_RELEASES",
    "build_census_housing_provider",
    "parse_housing_release",
]
