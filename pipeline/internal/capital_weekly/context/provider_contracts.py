from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Callable, Iterable
from zoneinfo import ZoneInfo


HONG_KONG = ZoneInfo("Asia/Hong_Kong")
SOURCE_TIERS = frozenset({"public", "licensed"})
REQUIREDNESS_VALUES = frozenset({"required", "optional"})
PROVIDER_PHASES = frozenset(
    {
        "config",
        "metadata",
        "retrieve",
        "raw",
        "parse",
        "point_in_time",
        "freshness",
        "coverage",
        "normalized",
    }
)


class PointInTimeUnavailable(RuntimeError):
    """Raised when no source artifact can prove its target-week vintage."""


class ProviderPhaseError(RuntimeError):
    """A provider failure with a stable, credential-safe diagnostic contract."""

    def __init__(
        self,
        error_code: str,
        failure_phase: str,
        safe_message: str,
        attempts: int = 1,
    ) -> None:
        self.error_code = error_code
        self.failure_phase = failure_phase
        self.safe_message = safe_message
        self.attempts = attempts
        super().__init__(safe_message)


@dataclass(frozen=True)
class ProviderResult:
    category: str
    rows: list[dict]
    raw_text: str | bytes
    source: str
    source_url: str
    status: str = "OK"
    notes: str = ""
    raw_is_diagnostic: bool = False
    attempts: int = 1
    completed_phase: str = "normalized"


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
    "HONG_KONG",
    "PointInTimeUnavailable",
    "PROVIDER_PHASES",
    "ProviderPhaseError",
    "ProviderResult",
    "ProviderSpec",
    "filter_known_as_of",
    "select_capture_at_or_before",
    "target_sunday_cutoff",
]
