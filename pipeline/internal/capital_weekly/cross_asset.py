from __future__ import annotations

import math
from datetime import date
from typing import Iterable, Literal, Mapping

from .returns import parse_date


DailyTransform = Literal["pct_return", "level_change"]


def _dated_values(history: Iterable[dict]) -> list[tuple[date, float]]:
    values: dict[date, float] = {}
    for point in history:
        observation_date = parse_date(point["date"])
        value = float(point["value"])
        if not math.isfinite(value):
            raise ValueError("Correlation inputs must be finite")
        if observation_date in values:
            raise ValueError(
                f"Correlation input contains duplicate date: {observation_date}"
            )
        values[observation_date] = value
    return sorted(values.items())


def _daily_transform(
    history: Iterable[dict],
    transform: DailyTransform,
) -> dict[date, float]:
    points = _dated_values(history)
    transformed: dict[date, float] = {}
    for (previous_date, previous), (current_date, current) in zip(
        points,
        points[1:],
    ):
        del previous_date
        if transform == "pct_return":
            if previous == 0:
                raise ValueError("Percentage-return input must have a non-zero base")
            value = current / previous - 1.0
        elif transform == "level_change":
            value = current - previous
        else:
            raise ValueError(f"Unsupported daily transform: {transform}")
        if not math.isfinite(value):
            raise ValueError("Correlation transformations must be finite")
        transformed[current_date] = value
    return transformed


def _pearson(left: list[float], right: list[float]) -> float:
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    left_ss = math.fsum(value * value for value in left_centered)
    right_ss = math.fsum(value * value for value in right_centered)
    if left_ss <= 1e-24 or right_ss <= 1e-24:
        raise ValueError("Correlation window has zero variance")
    value = math.fsum(
        left_value * right_value
        for left_value, right_value in zip(left_centered, right_centered)
    ) / math.sqrt(left_ss * right_ss)
    if not math.isfinite(value):
        raise ValueError("Correlation calculation produced a non-finite value")
    return max(-1.0, min(1.0, value))


def rolling_correlation_history(
    histories: Mapping[str, Iterable[dict]],
    left_code: str,
    right_code: str,
    left_transform: DailyTransform,
    right_transform: DailyTransform,
    *,
    window: int,
    minimum_observations: int,
) -> list[dict[str, date | float | int]]:
    if window < 2:
        raise ValueError("Correlation window must contain at least two observations")
    if minimum_observations < 2 or minimum_observations > window:
        raise ValueError(
            "Correlation minimum observations must be between two and the window"
        )
    try:
        left = _daily_transform(histories[left_code], left_transform)
        right = _daily_transform(histories[right_code], right_transform)
    except KeyError as error:
        raise ValueError(f"Correlation is missing input: {error.args[0]}") from error

    shared_dates = sorted(set(left).intersection(right))
    result: list[dict[str, date | float | int]] = []
    for end_index, observation_date in enumerate(shared_dates):
        start_index = max(0, end_index - window + 1)
        window_dates = shared_dates[start_index : end_index + 1]
        if len(window_dates) < minimum_observations:
            continue
        result.append(
            {
                "date": observation_date,
                "value": _pearson(
                    [left[day] for day in window_dates],
                    [right[day] for day in window_dates],
                ),
                "observations": len(window_dates),
            }
        )
    return result


__all__ = ["DailyTransform", "rolling_correlation_history"]
