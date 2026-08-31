from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Literal


ChangeUnit = Literal["pct", "bp", "usd_billions", "correlation_points"]
WeeklyMode = Literal["iso_week", "trailing_7d"]


@dataclass(frozen=True)
class TimePoint:
    date: date
    value: float


@dataclass(frozen=True)
class ReturnSnapshot:
    latest_date: date
    latest_value: float
    daily_base_value: float | None
    daily_change: float | None
    weekly_base_value: float | None
    weekly_change: float | None
    mtd_base_value: float | None
    mtd_change: float | None
    ytd_base_value: float | None
    ytd_change: float | None
    change_unit: ChangeUnit
    daily_base_date: date | None
    weekly_base_date: date | None
    mtd_base_date: date | None
    ytd_base_date: date | None
    qc_flag: str


def parse_date(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _clean_series(points: Iterable[TimePoint | dict]) -> list[TimePoint]:
    clean: list[TimePoint] = []
    for point in points:
        if isinstance(point, TimePoint):
            dt = point.date
            value = point.value
        else:
            dt = parse_date(point["date"])
            value = float(point["value"])
        clean.append(TimePoint(dt, value))
    deduped = {point.date: point for point in clean}
    return sorted(deduped.values(), key=lambda item: item.date)


def _last_before(series: list[TimePoint], cutoff: date) -> TimePoint | None:
    result = None
    for point in series:
        if point.date < cutoff:
            result = point
        else:
            break
    return result


def _last_on_or_before(series: list[TimePoint], cutoff: date) -> TimePoint | None:
    result = None
    for point in series:
        if point.date <= cutoff:
            result = point
        else:
            break
    return result


def _change(latest: float, base: float, unit: ChangeUnit) -> float | None:
    if unit == "pct":
        if base == 0:
            return None
        return latest / base - 1
    if unit == "bp":
        return (latest - base) * 100
    if unit in {"usd_billions", "correlation_points"}:
        return latest - base
    raise ValueError(f"Unsupported change unit: {unit}")


def calculate_return_snapshot(
    points: Iterable[TimePoint | dict],
    change_unit: ChangeUnit = "pct",
    weekly_mode: WeeklyMode = "iso_week",
) -> ReturnSnapshot:
    """Calculate daily, weekly, MTD, and YTD changes from dated observations.

    By default, weekly means latest value versus the last observation before
    the latest observation's ISO-week Monday. ``trailing_7d`` instead selects
    the last observation on or before seven calendar days earlier. MTD/YTD use
    the last observation before the first calendar day of the month/year.
    """
    series = _clean_series(points)
    if len(series) < 2:
        raise ValueError("At least two valid observations are required")

    latest = series[-1]
    previous = series[-2]
    start_of_week = latest.date - timedelta(days=latest.date.weekday())
    start_of_month = latest.date.replace(day=1)
    start_of_year = latest.date.replace(month=1, day=1)

    if weekly_mode == "iso_week":
        weekly_base = _last_before(series, start_of_week)
    elif weekly_mode == "trailing_7d":
        weekly_base = _last_on_or_before(series, latest.date - timedelta(days=7))
    else:
        raise ValueError(f"Unsupported weekly mode: {weekly_mode}")
    mtd_base = _last_before(series, start_of_month)
    ytd_base = _last_before(series, start_of_year)

    missing = []
    if weekly_base is None:
        missing.append("missing_weekly_base")
    if mtd_base is None:
        missing.append("missing_mtd_base")
    if ytd_base is None:
        missing.append("missing_ytd_base")

    return ReturnSnapshot(
        latest_date=latest.date,
        latest_value=latest.value,
        daily_base_value=previous.value,
        daily_change=_change(latest.value, previous.value, change_unit),
        weekly_base_value=weekly_base.value if weekly_base else None,
        weekly_change=_change(latest.value, weekly_base.value, change_unit)
        if weekly_base
        else None,
        mtd_base_value=mtd_base.value if mtd_base else None,
        mtd_change=_change(latest.value, mtd_base.value, change_unit) if mtd_base else None,
        ytd_base_value=ytd_base.value if ytd_base else None,
        ytd_change=_change(latest.value, ytd_base.value, change_unit) if ytd_base else None,
        change_unit=change_unit,
        daily_base_date=previous.date,
        weekly_base_date=weekly_base.date if weekly_base else None,
        mtd_base_date=mtd_base.date if mtd_base else None,
        ytd_base_date=ytd_base.date if ytd_base else None,
        qc_flag="OK" if not missing else ";".join(missing),
    )


def calculate_macro_snapshot(
    history: Iterable[TimePoint | dict],
    change_unit: ChangeUnit,
) -> ReturnSnapshot:
    """Calculate a macro snapshot using a trailing-seven-calendar-day week."""
    return calculate_return_snapshot(history, change_unit, weekly_mode="trailing_7d")
