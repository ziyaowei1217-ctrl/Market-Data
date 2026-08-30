from __future__ import annotations

import math
from datetime import date, datetime, time
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo


HONG_KONG = ZoneInfo("Asia/Hong_Kong")


def _payload_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, Mapping):
        candidates = [
            payload[key]
            for key in ("data", "results", "records")
            if key in payload
        ]
        if len(candidates) != 1 or not isinstance(candidates[0], list):
            raise ValueError("USDA payload must contain one records collection")
        records = candidates[0]
    else:
        raise ValueError("USDA payload must be a list or object")
    if not all(isinstance(record, Mapping) for record in records):
        raise ValueError("USDA payload records must be objects")
    return [dict(record) for record in records]


def _cutoff_datetime(cutoff: date | datetime) -> datetime:
    if isinstance(cutoff, datetime):
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("USDA cutoff must include a UTC offset")
        return cutoff
    return datetime.combine(cutoff, time.max, tzinfo=HONG_KONG)


def _timestamp(value: Any, field: str) -> datetime:
    raw = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"USDA {field} must be an ISO timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"USDA {field} must include a UTC offset")
    return parsed


def _finite_number(value: Any, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"USDA {field} must be numeric")
    if not math.isfinite(float(value)):
        raise ValueError(f"USDA {field} must be finite")
    return value


def parse_usda_lookup(
    payload: Any,
    key_fields: Sequence[str],
) -> dict[str, str]:
    """Return an exact official display-name -> code mapping."""
    if len(key_fields) != 2:
        raise ValueError("USDA lookup key_fields must contain display and code fields")
    display_field, code_field = key_fields
    resolved: dict[str, str] = {}
    for record in _payload_records(payload):
        missing = [field for field in key_fields if field not in record]
        if missing:
            raise ValueError(f"USDA missing lookup field: {', '.join(missing)}")
        display = str(record[display_field] if record[display_field] is not None else "").strip()
        code = str(record[code_field] if record[code_field] is not None else "").strip()
        if not display or not code:
            raise ValueError("USDA blank lookup identity")
        if display in resolved:
            raise ValueError(f"USDA duplicate official display name: {display}")
        resolved[display] = code
    return resolved


def _required_spec_value(spec: Mapping[str, Any], field: str) -> str:
    value = str(spec.get(field) or "").strip()
    if not value:
        raise ValueError(f"USDA spec missing {field}")
    return value


def parse_psd_records(
    payload: Any,
    spec: Mapping[str, Any],
    cutoff: date | datetime,
) -> list[dict[str, Any]]:
    records = _payload_records(payload)
    cutoff_at = _cutoff_datetime(cutoff)
    commodity_api_code = _required_spec_value(spec, "commodity_api_code")
    country_code = _required_spec_value(spec, "country_code")
    commodity_code = _required_spec_value(spec, "commodity_code")
    commodity_family = _required_spec_value(spec, "commodity_family")
    country_name = _required_spec_value(spec, "country_name")
    try:
        market_year = int(spec["market_year"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("USDA PSD spec market_year must be an integer") from error
    raw_attributes = spec.get("attributes")
    raw_units = spec.get("units")
    if not isinstance(raw_attributes, Mapping) or not raw_attributes:
        raise ValueError("USDA PSD spec attributes must be a non-empty object")
    if not isinstance(raw_units, Mapping) or not raw_units:
        raise ValueError("USDA PSD spec units must be a non-empty object")
    attributes = {str(name): str(code) for name, code in raw_attributes.items()}
    units = {str(code): str(name) for code, name in raw_units.items()}

    candidates: list[tuple[datetime, dict[str, Any]]] = []
    for record in records:
        if (
            str(record.get("commodityCode") or "") != commodity_api_code
            or str(record.get("countryCode") if record.get("countryCode") is not None else "")
            != country_code
        ):
            continue
        try:
            record_year = int(record.get("marketYear"))
        except (TypeError, ValueError) as error:
            raise ValueError("USDA PSD marketYear must be an integer") from error
        if record_year != market_year:
            continue
        released_at = _timestamp(record.get("releaseDate"), "releaseDate")
        if released_at.astimezone(HONG_KONG) <= cutoff_at.astimezone(HONG_KONG):
            candidates.append((released_at, record))
    if not candidates:
        return []
    selected_release = max(released_at for released_at, _record in candidates)
    selected = [
        record
        for released_at, record in candidates
        if released_at == selected_release
    ]

    code_to_name = {code: name for name, code in attributes.items()}
    if len(code_to_name) != len(attributes):
        raise ValueError("USDA PSD spec contains duplicate attribute codes")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in selected:
        attribute_code = str(
            record.get("attributeId") if record.get("attributeId") is not None else ""
        )
        if attribute_code not in code_to_name:
            continue
        if attribute_code in seen:
            raise ValueError(
                f"USDA PSD duplicate attribute for selected release: {attribute_code}"
            )
        unit_code = str(record.get("unitId") if record.get("unitId") is not None else "")
        if unit_code not in units:
            raise ValueError(
                f"USDA PSD unexpected native unit {unit_code or 'blank'}"
            )
        seen.add(attribute_code)
        normalized.append(
            {
                "commodity_code": commodity_code,
                "commodity_family": commodity_family,
                "commodity_api_code": commodity_api_code,
                "country_code": country_code,
                "country_name": country_name,
                "market_year": market_year,
                "attribute": code_to_name[attribute_code],
                "attribute_code": attribute_code,
                "value": _finite_number(record.get("value"), "PSD value"),
                "unit_code": unit_code,
                "unit": units[unit_code],
                "release_date": selected_release.isoformat(),
            }
        )
    missing = sorted(set(attributes.values()) - seen)
    if missing:
        raise ValueError(
            "USDA PSD selected release missing configured attributes: "
            + ", ".join(missing)
        )
    return sorted(normalized, key=lambda row: list(attributes).index(row["attribute"]))


def calculate_stock_to_use(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any] | None:
    copied = [dict(record) for record in records]
    ending = [record for record in copied if record.get("attribute") == "ending_stocks"]
    use = [record for record in copied if record.get("attribute") == "domestic_use"]
    if len(ending) != 1 or len(use) != 1:
        return None
    numerator, denominator = ending[0], use[0]
    identity_fields = (
        "commodity_code",
        "commodity_family",
        "commodity_api_code",
        "country_code",
        "country_name",
        "market_year",
        "release_date",
        "unit_code",
        "unit",
    )
    if any(numerator.get(field) != denominator.get(field) for field in identity_fields):
        return None
    denominator_value = denominator.get("value")
    numerator_value = numerator.get("value")
    if (
        isinstance(denominator_value, bool)
        or not isinstance(denominator_value, (int, float))
        or not math.isfinite(float(denominator_value))
        or denominator_value == 0
        or isinstance(numerator_value, bool)
        or not isinstance(numerator_value, (int, float))
        or not math.isfinite(float(numerator_value))
    ):
        return None
    result = dict(numerator)
    result.update(
        {
            "attribute": "stock_to_use",
            "attribute_code": None,
            "value": numerator_value / denominator_value,
            "unit_code": None,
            "unit": "ratio",
        }
    )
    return result


def parse_esr_records(
    payload: Any,
    spec: Mapping[str, Any],
    cutoff: date | datetime,
) -> list[dict[str, Any]]:
    cutoff_at = _cutoff_datetime(cutoff)
    commodity_api_code = _required_spec_value(spec, "commodity_api_code")
    aggregate_all_countries = spec.get("aggregate_all_countries") is True
    country_code = (
        "ALL"
        if aggregate_all_countries
        else _required_spec_value(spec, "country_code")
    )
    commodity_code = _required_spec_value(spec, "commodity_code")
    commodity_family = _required_spec_value(spec, "commodity_family")
    country_name = _required_spec_value(spec, "country_name")
    unit_code = _required_spec_value(spec, "unit_code")
    unit = _required_spec_value(spec, "unit")
    try:
        market_year = int(spec["market_year"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("USDA ESR spec market_year must be an integer") from error

    candidates: list[tuple[datetime, date, dict[str, Any]]] = []
    for record in _payload_records(payload):
        if (
            str(record.get("commodityCode") if record.get("commodityCode") is not None else "")
            != commodity_api_code
            or (
                not aggregate_all_countries
                and str(
                    record.get("countryCode")
                    if record.get("countryCode") is not None
                    else ""
                )
                != country_code
            )
        ):
            continue
        try:
            record_year = int(record.get("marketYear"))
        except (TypeError, ValueError) as error:
            raise ValueError("USDA ESR marketYear must be an integer") from error
        if record_year != market_year:
            continue
        record_unit = str(record.get("unitId") if record.get("unitId") is not None else "")
        if record_unit != unit_code:
            raise ValueError(f"USDA ESR unexpected native unit {record_unit or 'blank'}")
        released_at = _timestamp(record.get("releaseDate"), "releaseDate")
        try:
            week_ending = date.fromisoformat(
                str(record.get("weekEndingDate") or "").split("T", 1)[0]
            )
        except ValueError as error:
            raise ValueError("USDA ESR weekEndingDate must be YYYY-MM-DD") from error
        if released_at.astimezone(HONG_KONG) <= cutoff_at.astimezone(HONG_KONG):
            candidates.append((released_at, week_ending, record))
    if not candidates:
        return []
    selected_release = max(item[0] for item in candidates)
    selected_week = max(
        item[1] for item in candidates if item[0] == selected_release
    )
    selected = [
        record
        for released_at, week_ending, record in candidates
        if released_at == selected_release and week_ending == selected_week
    ]
    if not selected:
        return []
    selected_country_codes = [
        str(
            record.get("countryCode")
            if record.get("countryCode") is not None
            else ""
        )
        for record in selected
    ]
    if (
        any(not code for code in selected_country_codes)
        or len(set(selected_country_codes)) != len(selected_country_codes)
    ):
        raise ValueError("USDA ESR selected release has duplicate country records")
    if not aggregate_all_countries and len(selected) != 1:
        raise ValueError("USDA ESR selected release has duplicate country records")
    metrics = (
        ("net_sales", "currentMYNetSales"),
        ("weekly_exports", "weeklyExports"),
        ("outstanding_sales", "outstandingSales"),
    )
    return [
        {
            "commodity_code": commodity_code,
            "commodity_family": commodity_family,
            "commodity_api_code": commodity_api_code,
            "country_code": country_code,
            "country_name": country_name,
            "market_year": market_year,
            "week_ending_date": selected_week.isoformat(),
            "metric": metric,
            "value": sum(
                _finite_number(record.get(field), f"ESR {field}")
                for record in selected
            ),
            "unit_code": unit_code,
            "unit": unit,
            "release_date": selected_release.isoformat(),
        }
        for metric, field in metrics
    ]


__all__ = [
    "calculate_stock_to_use",
    "parse_esr_records",
    "parse_psd_records",
    "parse_usda_lookup",
]
