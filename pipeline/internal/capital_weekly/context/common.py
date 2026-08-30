from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Iterable


BASE_METRIC_FIELDS = (
    "as_of_date",
    "category",
    "metric_code",
    "metric_name",
    "value",
    "unit",
    "frequency",
    "market",
    "source",
    "source_url",
    "qc_flag",
)
COMMODITY_METRIC_FIELDS = (
    "commodity_code",
    "commodity_family",
    "metric_role",
    "measurement_kind",
    "participant_class",
    "known_as_of",
    "reference_period",
)
METRIC_ROLE_VALUES = frozenset({"physical_fundamental", "positioning"})
MEASUREMENT_KIND_VALUES = frozenset(
    {
        "inventory",
        "supply",
        "demand",
        "trade",
        "utilization",
        "price",
        "open_interest",
        "net_position",
        "percentile",
        "structural",
    }
)
PARTICIPANT_CLASS_VALUES = frozenset(
    {
        "producer",
        "swap_dealer",
        "managed_money",
        "other_reportable",
        "index_trader",
    }
)
METRIC_FIELDS = BASE_METRIC_FIELDS + COMMODITY_METRIC_FIELDS


def iso_date(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    return str(value)


def normalize_metric_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    seen = set()
    for raw in rows:
        missing = [field for field in BASE_METRIC_FIELDS if field not in raw]
        if missing:
            raise ValueError(f"Metric row missing required fields: {', '.join(missing)}")
        row = dict(raw)
        for field in COMMODITY_METRIC_FIELDS:
            row.setdefault(field, None)
        for field, allowed in (
            ("metric_role", METRIC_ROLE_VALUES),
            ("measurement_kind", MEASUREMENT_KIND_VALUES),
            ("participant_class", PARTICIPANT_CLASS_VALUES),
        ):
            value = row.get(field)
            if value not in (None, "") and value not in allowed:
                raise ValueError(f"Unsupported {field}: {value}")
        row["as_of_date"] = iso_date(row["as_of_date"])
        key = (
            row["as_of_date"],
            row["category"],
            row["metric_code"],
            row["market"],
        )
        if key in seen:
            raise ValueError(f"Duplicate metric key: {key}")
        seen.add(key)
        value = row["value"]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if not math.isfinite(float(value)):
                row["value"] = None
                row["qc_flag"] = "INVALID_VALUE"
        normalized.append(row)
    return normalized
