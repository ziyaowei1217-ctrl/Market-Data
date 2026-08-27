from __future__ import annotations

import json
import math
from typing import Any

from ..weekly_context import ProviderResult


EIA_SOURCE_URL = "https://api.eia.gov/v2/"
EIA_UNIT_CODES = {"MBBL": "Thousand Barrels"}


def parse_eia_series(
    text: str,
    *,
    metric_code: str,
    expected_unit: str,
) -> list[dict[str, Any]]:
    payload = json.loads(text)
    data = payload.get("response", {}).get("data")
    if not isinstance(data, list):
        raise ValueError("EIA response has no data array")
    rows = []
    seen = set()
    for raw in data:
        period = str(raw.get("period", "")).strip()
        if not period:
            raise ValueError("EIA observation is missing period")
        if period in seen:
            raise ValueError(f"Duplicate EIA period: {period}")
        seen.add(period)
        raw_unit = str(raw.get("unit") or raw.get("units") or "").strip()
        unit = EIA_UNIT_CODES.get(raw_unit, raw_unit)
        if unit != expected_unit:
            raise ValueError(
                f"Unexpected EIA unit for {metric_code}: {unit!r}; "
                f"expected {expected_unit!r}"
            )
        try:
            value = float(raw["value"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid EIA value for {period}") from error
        if not math.isfinite(value):
            raise ValueError(f"Invalid EIA value for {period}")
        rows.append(
            {
                "period": period,
                "metric_code": metric_code,
                "metric_name": str(
                    raw.get("series-description") or metric_code
                ).strip(),
                "value": value,
                "unit": unit,
            }
        )
    rows.sort(key=lambda row: row["period"])
    return rows


def calculate_weekly_change(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) < 2:
        raise ValueError("At least two observations are required for a weekly change")
    ordered = sorted(rows, key=lambda row: row["period"])
    previous, current = ordered[-2:]
    prior_value = float(previous["value"])
    current_value = float(current["value"])
    return {
        "period": current["period"],
        "change": current_value - prior_value,
        "change_pct": (
            (current_value - prior_value) / prior_value
            if prior_value != 0
            else None
        ),
    }


def eia_not_configured_result() -> ProviderResult:
    return ProviderResult(
        category="commodity_fundamentals",
        rows=[],
        raw_text="",
        source="U.S. Energy Information Administration",
        source_url=EIA_SOURCE_URL,
        status="NOT_CONFIGURED",
        notes="Set EIA_API_KEY to enable the free EIA Open Data provider.",
    )


__all__ = [
    "calculate_weekly_change",
    "eia_not_configured_result",
    "parse_eia_series",
]
