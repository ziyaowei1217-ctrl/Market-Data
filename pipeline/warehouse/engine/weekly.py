"""Compute weekly indicator values at Friday cut-offs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Iterable, Mapping

import pandas as pd

from .formula import Context, FormulaError, RawSeries, evaluate, parse

# Knowledge cut-off for historical weeks: data published by the Sunday after the
# Friday cut-off counts as known (mirrors the existing pipeline's "最近一个已结束周日").
KNOWLEDGE_GRACE = pd.Timedelta(days=2)

# Bump when calculation rules change; the weekly job then recomputes all history.
ENGINE_VERSION = "2026-10-24.2"


@dataclass(frozen=True)
class WeeklyValue:
    indicator_id: str
    week_cutoff: date
    value: float | None
    obs_date: date | None
    status: str
    detail: str


def week_cutoffs(start: date, end: date) -> list[pd.Timestamp]:
    """Fridays in [start, end]."""
    return list(pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="W-FRI"))


def last_completed_friday(now: datetime | None = None) -> pd.Timestamp:
    now = now or datetime.now(timezone.utc)
    today = pd.Timestamp(now.date())
    # Friday's close is complete once Saturday starts (UTC).
    offset = (today.weekday() - 4) % 7
    if offset == 0:
        offset = 7
    return today - pd.Timedelta(days=offset)


def compute(
    formulas: Mapping[str, str],
    raw: Mapping[str, pd.DataFrame],
    cutoffs: Iterable[pd.Timestamp],
    *,
    known_now: pd.Timestamp | None = None,
    fast: bool = False,
    max_age_days: Mapping[str, int] | None = None,
) -> list[WeeklyValue]:
    """Evaluate every formula at every cut-off.

    ``known_now`` (forward mode): evaluate the latest week with everything stored
    so far. Otherwise each historical week sees what was knowable by its Sunday.
    ``fast`` evaluates history from the latest stored versions (backfill mode).
    """
    parsed = {}
    results: list[WeeklyValue] = []
    for indicator_id, text in formulas.items():
        try:
            parsed[indicator_id] = parse(text)
        except FormulaError as error:
            for cutoff in cutoffs:
                results.append(WeeklyValue(indicator_id, cutoff.date(), None, None, "error", str(error)[:300]))
    raw_series = {key: RawSeries.from_frame(frame) for key, frame in raw.items() if not frame.empty}
    shared: dict = {}
    for cutoff in cutoffs:
        known = known_now if known_now is not None else cutoff + KNOWLEDGE_GRACE
        ctx = Context(raw_series, cutoff, known, fast=fast, shared_cache=shared)
        for indicator_id, formula in parsed.items():
            scalar = evaluate(formula, ctx)
            limit = (max_age_days or {}).get(indicator_id)
            if (scalar.status == "ok" and limit is not None and scalar.obs_date is not None
                    and (cutoff - scalar.obs_date).days > limit):
                scalar.status = "stale"
                scalar.detail = f"latest observation {scalar.obs_date.date()} older than {limit} days; {scalar.detail}"
            results.append(
                WeeklyValue(
                    indicator_id,
                    cutoff.date(),
                    scalar.value,
                    scalar.obs_date.date() if scalar.obs_date is not None else None,
                    scalar.status,
                    scalar.detail[:300],
                )
            )
    return results
