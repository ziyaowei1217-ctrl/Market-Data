from __future__ import annotations

import math
import csv
import io
import statistics
from datetime import date, datetime
from typing import Any, Iterable


def _date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def calculate_financial_conditions(
    components: Iterable[dict[str, Any]],
    *,
    expected_components: int,
    expected_end: date,
    minimum_coverage: float = 0.75,
    max_lag_days: int = 7,
    tightening_threshold: float = 0.5,
) -> dict[str, Any]:
    if expected_components <= 0:
        raise ValueError("expected_components must be positive")
    if not 0 <= minimum_coverage <= 1:
        raise ValueError("minimum_coverage must be between zero and one")

    included = []
    excluded: dict[str, str] = {}
    seen = set()
    for component in components:
        code = str(component["metric_code"])
        if code in seen:
            raise ValueError(f"Duplicate financial-condition component: {code}")
        seen.add(code)
        observed = _date(component["as_of_date"])
        lag = (expected_end - observed).days
        if lag > max_lag_days or lag < 0:
            excluded[code] = "STALE" if lag > max_lag_days else "FUTURE_DATE"
            continue
        try:
            value = float(component["value"])
            mean = float(component["mean"])
            std = float(component["std"])
            direction = int(component["risk_direction"])
        except (KeyError, TypeError, ValueError):
            excluded[code] = "INVALID_VALUE"
            continue
        if not all(math.isfinite(item) for item in (value, mean, std)):
            excluded[code] = "INVALID_VALUE"
            continue
        if std <= 0:
            excluded[code] = "INVALID_STD"
            continue
        if direction not in {-1, 1}:
            excluded[code] = "INVALID_DIRECTION"
            continue
        included.append(
            {
                "metric_code": code,
                "z_score": (value - mean) / std * direction,
                "as_of_date": observed,
            }
        )

    coverage = len(included) / expected_components
    if coverage < minimum_coverage:
        return {
            "as_of_date": expected_end,
            "score": None,
            "coverage": coverage,
            "regime": "insufficient_data",
            "qc_flag": "INSUFFICIENT_DATA",
            "components": included,
            "excluded": excluded,
        }

    score = sum(row["z_score"] for row in included) / len(included)
    if score >= tightening_threshold:
        regime = "tightening"
    elif score <= -tightening_threshold:
        regime = "easing"
    else:
        regime = "neutral"
    return {
        "as_of_date": expected_end,
        "score": score,
        "coverage": coverage,
        "regime": regime,
        "qc_flag": "OK",
        "components": included,
        "excluded": excluded,
    }


def parse_fred_components_csv(
    text: str,
    config: Iterable[dict[str, Any]],
    *,
    expected_end: date,
    minimum_observations: int = 60,
) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    fieldnames = reader.fieldnames or []
    date_column = next(
        (name for name in ("DATE", "observation_date") if name in fieldnames),
        None,
    )
    if date_column is None:
        raise ValueError("FRED response is missing DATE")
    configured = [dict(row) for row in config]
    missing = [
        row["series_id"]
        for row in configured
        if row["series_id"] not in reader.fieldnames
    ]
    if missing:
        raise ValueError(f"FRED response missing series: {', '.join(missing)}")
    observations = {row["metric_code"]: [] for row in configured}
    for raw in reader:
        observation_date = date.fromisoformat(raw[date_column])
        if observation_date > expected_end:
            continue
        for item in configured:
            value = str(raw[item["series_id"]]).strip()
            if value in {"", ".", "NA"}:
                continue
            try:
                number = float(value)
            except ValueError:
                continue
            if math.isfinite(number):
                observations[item["metric_code"]].append(
                    (observation_date, number)
                )
    rows = []
    for item in configured:
        values = observations[item["metric_code"]]
        if len(values) < minimum_observations:
            continue
        numeric = [value for _, value in values]
        rows.append(
            {
                "metric_code": item["metric_code"],
                "series_id": item["series_id"],
                "value": numeric[-1],
                "mean": statistics.mean(numeric),
                "std": statistics.stdev(numeric),
                "risk_direction": int(item["risk_direction"]),
                "as_of_date": values[-1][0],
            }
        )
    return rows


__all__ = ["calculate_financial_conditions", "parse_fred_components_csv"]
