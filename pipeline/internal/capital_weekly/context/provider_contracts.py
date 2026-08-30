from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Callable, Iterable
from zoneinfo import ZoneInfo


HONG_KONG = ZoneInfo("Asia/Hong_Kong")
SOURCE_TIERS = frozenset({"public", "licensed"})
REQUIREDNESS_VALUES = frozenset({"required", "optional"})
FIXED_REQUIRED_CONTEXT_IDENTITIES = frozenset(
    {
        ("bls_calendar", "events"),
        ("federal_reserve_calendar", "events"),
        ("fomc_calendar", "events"),
        ("census_calendar", "events"),
        ("nasdaq_market_summary", "market_internals"),
        ("cftc_tff", "positioning_flows"),
        ("cftc_disaggregated", "positioning_flows"),
        ("finra_margin", "positioning_flows"),
        ("hkex_microstructure", "market_internals"),
        ("sse_microstructure", "market_internals"),
        ("szse_microstructure", "market_internals"),
        ("bls_economic_releases", "economic_releases"),
        ("bea_economic_releases", "economic_releases"),
        ("census_retail_sales", "economic_releases"),
        ("census_housing", "economic_releases"),
        ("census_durable_goods", "economic_releases"),
    }
)


class PointInTimeUnavailable(RuntimeError):
    """Raised when no source artifact can prove its target-week vintage."""


@dataclass(frozen=True)
class ProviderResult:
    category: str
    rows: list[dict]
    raw_text: str | bytes
    source: str
    source_url: str
    status: str = "OK"
    notes: str = ""


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    category: str
    source_tier: str
    requiredness: str
    provider_version: str
    schema_version: str
    frequency: str
    freshness_days: int | None
    failure_source: str = ""
    failure_source_url: str = ""

    def __post_init__(self) -> None:
        if self.source_tier not in SOURCE_TIERS:
            raise ValueError(f"Unsupported source tier: {self.source_tier}")
        if self.requiredness not in REQUIREDNESS_VALUES:
            raise ValueError(f"Unsupported requiredness: {self.requiredness}")


@dataclass(frozen=True)
class ContextProvider:
    spec: ProviderSpec
    fetch: Callable[[], ProviderResult]


@dataclass(frozen=True)
class CaptureMetadata:
    provider: str
    captured_at: str
    path: Path
    sha256: str
    source_url: str


def target_sunday_cutoff(as_of_date: date) -> datetime:
    return datetime.combine(as_of_date, time.max, tzinfo=HONG_KONG)


def filter_known_as_of(rows: Iterable[dict], as_of_date: date) -> list[dict]:
    cutoff = target_sunday_cutoff(as_of_date)
    accepted = []
    for row in rows:
        raw = str(row.get("known_as_of") or "")
        known = datetime.fromisoformat(raw)
        if known.tzinfo is None:
            raise ValueError("known_as_of must include a UTC offset")
        if known.astimezone(HONG_KONG) <= cutoff:
            accepted.append(dict(row))
    return accepted


def select_capture_at_or_before(
    captures: Iterable[CaptureMetadata], as_of_date: date
) -> CaptureMetadata:
    cutoff = target_sunday_cutoff(as_of_date)
    eligible: list[tuple[datetime, CaptureMetadata]] = []
    for capture in captures:
        captured_at = datetime.fromisoformat(capture.captured_at)
        if captured_at.tzinfo is None:
            raise ValueError("captured_at must include a UTC offset")
        captured_hkt = captured_at.astimezone(HONG_KONG)
        if captured_hkt <= cutoff:
            eligible.append((captured_hkt, capture))
    if not eligible:
        raise PointInTimeUnavailable(
            f"No capture is available on or before {as_of_date.isoformat()}"
        )
    return max(eligible, key=lambda item: item[0])[1]


__all__ = [
    "CaptureMetadata",
    "ContextProvider",
    "FIXED_REQUIRED_CONTEXT_IDENTITIES",
    "HONG_KONG",
    "PointInTimeUnavailable",
    "ProviderResult",
    "ProviderSpec",
    "filter_known_as_of",
    "select_capture_at_or_before",
    "target_sunday_cutoff",
]
