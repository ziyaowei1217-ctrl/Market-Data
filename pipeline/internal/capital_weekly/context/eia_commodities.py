from __future__ import annotations

import calendar
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from pipeline.internal.capital_weekly.official_http import OfficialHttpPolicy
from pipeline.internal.common import DEFAULT_CONFIG_PATH


HONG_KONG = ZoneInfo("Asia/Hong_Kong")
EIA_PROVIDERS = frozenset({"eia_natural_gas", "eia_refined_products"})
EIA_FAMILIES = {
    "eia_natural_gas": "natural_gas",
    "eia_refined_products": "refined_products",
}
EIA_MEASUREMENT_KINDS = frozenset(
    {"inventory", "supply", "demand", "trade", "utilization"}
)
EIA_FREQUENCY_PATTERNS = {
    "weekly": r"\d{4}-\d{2}-\d{2}",
    "monthly": r"\d{4}-\d{2}",
    "annual": r"\d{4}",
}
EIA_SPEC_FIELDS = frozenset(
    {
        "provider",
        "commodity_code",
        "commodity_family",
        "route",
        "frequency",
        "facets",
        "metric_code",
        "metric_name",
        "measurement_kind",
        "source_description",
        "expected_unit",
        "freshness_days",
    }
)
LEGACY_EIA_UNIT_CODES = {"MBBL": "Thousand Barrels"}
COMMODITY_HTTP_FIELDS = frozenset(
    {
        "provider",
        "connect_timeout",
        "read_timeout",
        "total_timeout",
        "max_attempts",
        "retry_backoff_seconds",
        "retry_after_cap",
    }
)


@dataclass(frozen=True)
class CommodityHttpSpec:
    policy: OfficialHttpPolicy
    request_batch_size: int | None = None
    page_length: int | None = None


@dataclass(frozen=True)
class EiaBatchSpec:
    route: str
    facets: Mapping[str, tuple[str, ...]]
    frequency: str
    start: str
    end: str
    page_length: int

    def __post_init__(self) -> None:
        route = str(self.route).strip("/")
        if not route or not re.fullmatch(r"[a-z0-9][a-z0-9/_-]*", route):
            raise ValueError(f"Invalid EIA batch route: {self.route!r}")
        if not str(self.frequency).strip():
            raise ValueError("EIA batch frequency cannot be blank")
        if self.page_length <= 0:
            raise ValueError("EIA page_length must be positive")
        normalized: dict[str, tuple[str, ...]] = {}
        for raw_name, raw_values in self.facets.items():
            name = str(raw_name).strip()
            values = tuple(str(value).strip() for value in raw_values)
            if not name or not values or any(not value for value in values):
                raise ValueError("EIA batch facets cannot contain blanks")
            if len(values) != len(set(values)):
                raise ValueError(f"EIA batch facet {name} contains duplicates")
            normalized[name] = values
        if "series" not in normalized:
            raise ValueError("EIA batch requires a series facet")
        object.__setattr__(self, "route", route)
        object.__setattr__(self, "facets", normalized)


class EiaBatchError(ValueError):
    """A post-transport EIA validation failure with a provider phase."""

    def __init__(self, phase: str, message: str) -> None:
        self.phase = phase
        super().__init__(message)


def _positive_number(value: Any, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"commodity HTTP {field} must be positive") from error
    if not math.isfinite(parsed) or parsed <= 0:
        raise ValueError(f"commodity HTTP {field} must be positive")
    return parsed


def _positive_integer(value: Any, field: str) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as error:
        raise ValueError(f"commodity HTTP {field} must be a positive integer") from error
    if parsed <= 0:
        raise ValueError(f"commodity HTTP {field} must be a positive integer")
    return parsed


def _backoff_values(value: Any) -> tuple[float, ...]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError("commodity HTTP retry_backoff_seconds must be a JSON array") from error
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError("commodity HTTP retry_backoff_seconds must be a non-empty array")
    values = tuple(float(item) for item in value)
    if any(not math.isfinite(item) or item < 0 for item in values):
        raise ValueError("commodity HTTP retry_backoff_seconds must be finite and nonnegative")
    return values


def load_commodity_http_policies(
    path: str | Path | None = None,
) -> dict[str, CommodityHttpSpec]:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    document = json.loads(config_path.read_text(encoding="utf-8"))
    try:
        rows = document["context"]["commodity_http"]
    except (KeyError, TypeError) as error:
        raise ValueError("config missing context.commodity_http") from error
    if not isinstance(rows, list) or not rows or not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("context.commodity_http must be a non-empty row list")
    result: dict[str, CommodityHttpSpec] = {}
    for raw in rows:
        missing = sorted(COMMODITY_HTTP_FIELDS - set(raw))
        if missing:
            raise ValueError("commodity HTTP config missing: " + ", ".join(missing))
        provider = str(raw["provider"]).strip()
        if not provider or provider in result:
            raise ValueError(f"duplicate or blank commodity HTTP provider: {provider!r}")
        max_attempts = _positive_integer(raw["max_attempts"], "max_attempts")
        retry_after_cap = float(raw["retry_after_cap"])
        if not math.isfinite(retry_after_cap) or retry_after_cap < 0:
            raise ValueError("commodity HTTP retry_after_cap must be finite and nonnegative")
        policy = OfficialHttpPolicy(
            connect_timeout=_positive_number(raw["connect_timeout"], "connect_timeout"),
            read_timeout=_positive_number(raw["read_timeout"], "read_timeout"),
            total_timeout=_positive_number(raw["total_timeout"], "total_timeout"),
            max_attempts=max_attempts,
            backoff_seconds=_backoff_values(raw["retry_backoff_seconds"]),
            retry_after_cap=retry_after_cap,
        )
        request_batch_size = None
        page_length = None
        if provider == "eia":
            missing_eia = [
                field for field in ("request_batch_size", "page_length") if field not in raw
            ]
            if missing_eia:
                raise ValueError("EIA commodity HTTP config missing: " + ", ".join(missing_eia))
            request_batch_size = _positive_integer(raw["request_batch_size"], "request_batch_size")
            page_length = _positive_integer(raw["page_length"], "page_length")
        result[provider] = CommodityHttpSpec(policy, request_batch_size, page_length)
    return result


def build_eia_batch_specs(
    rows: Sequence[Mapping[str, Any]],
    *,
    request_batch_size: int,
    page_length: int,
    start: str,
    end: str,
) -> list[EiaBatchSpec]:
    batch_size = _positive_integer(request_batch_size, "request_batch_size")
    page_size = _positive_integer(page_length, "page_length")
    grouped: dict[tuple[str, str], list[str]] = {}
    seen: set[str] = set()
    for row in rows:
        route = str(row.get("route") or "").strip("/")
        frequency = str(row.get("frequency") or "").strip()
        facets = parse_facets(row.get("facets"))
        series = facets.get("series", "")
        if not series:
            raise ValueError("EIA configured series requires facets.series")
        if series in seen:
            raise ValueError(f"EIA duplicate configured series: {series}")
        seen.add(series)
        grouped.setdefault((route, frequency), []).append(series)
    specs: list[EiaBatchSpec] = []
    for (route, frequency), series_values in sorted(grouped.items()):
        for offset in range(0, len(series_values), batch_size):
            specs.append(
                EiaBatchSpec(
                    route=route,
                    facets={"series": tuple(series_values[offset : offset + batch_size])},
                    frequency=frequency,
                    start=str(start),
                    end=str(end),
                    page_length=page_size,
                )
            )
    return specs


def _eia_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError("EIA batch response is not valid JSON") from error
        if isinstance(payload, Mapping):
            return dict(payload)
    raise ValueError("EIA batch response must be a JSON object")


def eia_response_total(
    response: Mapping[str, Any],
    *,
    offset: int,
    page_count: int,
    requested_length: int,
    prior_total: int | None = None,
) -> int:
    if "total" not in response:
        raise ValueError("EIA response total is required")
    total = response["total"]
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ValueError("EIA response total must be a non-negative integer")
    if offset < 0 or page_count < 0 or requested_length <= 0:
        raise ValueError("EIA pagination offset and page size are invalid")
    if page_count > requested_length:
        raise ValueError("EIA page contains more rows than requested length")
    if offset + page_count > total:
        raise ValueError("EIA page exceeds response total")
    if prior_total is not None and total != prior_total:
        raise ValueError("EIA response total changed across pages")
    return total


def _validate_eia_batch_rows(
    payload: Mapping[str, Any],
    expected: Mapping[str, Mapping[str, Any]],
) -> set[str]:
    data = payload.get("response", {}).get("data")
    if not isinstance(data, list):
        raise ValueError("EIA batch response has no data array")
    observed: set[str] = set()
    for row in data:
        if not isinstance(row, Mapping):
            raise ValueError("EIA batch data rows must be objects")
        series = str(row.get("series") or "").strip()
        if series not in expected:
            raise ValueError(f"EIA batch returned unexpected series: {series or 'blank'}")
        metadata = expected[series]
        facets = parse_facets(metadata.get("facets"))
        for facet, selected in facets.items():
            if str(row.get(facet) or "").strip() != selected:
                raise ValueError(f"Unexpected EIA facet {facet} for {series}")
        description = str(row.get("series-description") or "").strip()
        if description != str(metadata.get("source_description") or "").strip():
            raise ValueError(f"Unexpected EIA source description for {series}")
        units = {
            str(row[field]).strip()
            for field in ("unit", "units")
            if row.get(field) not in (None, "")
        }
        if units != {str(metadata.get("expected_unit") or "").strip()}:
            raise ValueError(f"Unexpected EIA unit for {series}")
        observed.add(series)
    return observed


def fetch_eia_batches(
    client: Any,
    specs: Sequence[EiaBatchSpec],
    *,
    expected_metadata: Mapping[str, Mapping[str, Any]],
) -> list[dict]:
    owners: dict[str, int] = {}
    for index, spec in enumerate(specs):
        for series in spec.facets["series"]:
            if series in owners:
                raise ValueError(f"EIA duplicate batch series: {series}")
            owners[series] = index
            if series not in expected_metadata:
                raise ValueError(f"EIA metadata missing configured series: {series}")
    expected_keys = set(expected_metadata)
    if set(owners) != expected_keys:
        missing = sorted(expected_keys - set(owners))
        extra = sorted(set(owners) - expected_keys)
        raise ValueError(f"EIA batch coverage mismatch; missing={missing}; extra={extra}")

    for spec in specs:
        selected = {series: expected_metadata[series] for series in spec.facets["series"]}
        try:
            client.fetch_metadata(spec, selected)
        except ValueError as error:
            raise EiaBatchError("metadata", str(error)) from error

    pages: list[dict] = []
    observed: set[str] = set()
    for spec in specs:
        selected = {series: expected_metadata[series] for series in spec.facets["series"]}
        offset = 0
        expected_total: int | None = None
        while True:
            try:
                payload = _eia_payload(
                    client.fetch_page(spec, offset=offset, length=spec.page_length)
                )
                observed.update(_validate_eia_batch_rows(payload, selected))
            except ValueError as error:
                raise EiaBatchError("parse", str(error)) from error
            pages.append(payload)
            response = payload.get("response", {})
            data = response.get("data", [])
            try:
                total = eia_response_total(
                    response,
                    offset=offset,
                    page_count=len(data),
                    requested_length=spec.page_length,
                    prior_total=expected_total,
                )
            except ValueError as error:
                raise EiaBatchError("coverage", str(error)) from error
            expected_total = total
            offset += len(data)
            if offset >= total:
                break
            if not data:
                raise EiaBatchError(
                    "coverage", "EIA pagination stopped before total coverage"
                )
    missing = sorted(expected_keys - observed)
    if missing:
        raise EiaBatchError(
            "coverage", "EIA batch missing configured series: " + ", ".join(missing)
        )
    return pages


def parse_explicit_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    raise ValueError(f"EIA {field} must be true or false")


def parse_facets(value: Any) -> dict[str, str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError("EIA facets must be a JSON object") from error
    if not isinstance(value, Mapping) or not value:
        raise ValueError("EIA facets must be a non-empty object")
    facets: dict[str, str] = {}
    for key, raw_value in value.items():
        facet = str(key).strip()
        selected = str(raw_value).strip()
        if not facet or not selected:
            raise ValueError("EIA facets cannot contain blank names or values")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", facet):
            raise ValueError(f"Invalid EIA facet name: {facet!r}")
        facets[facet] = selected
    return facets


def validate_eia_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    missing = sorted(field for field in EIA_SPEC_FIELDS if field not in spec)
    if missing:
        raise ValueError("EIA config missing fields: " + ", ".join(missing))
    normalized = dict(spec)
    for field in EIA_SPEC_FIELDS - {"facets"}:
        normalized[field] = str(normalized[field]).strip()
        if not normalized[field]:
            raise ValueError(f"EIA config field cannot be blank: {field}")
    provider = normalized["provider"]
    if provider not in EIA_PROVIDERS:
        raise ValueError(f"Unsupported EIA provider: {provider}")
    if normalized["commodity_family"] != EIA_FAMILIES[provider]:
        raise ValueError(
            f"EIA provider {provider} cannot emit family "
            f"{normalized['commodity_family']}"
        )
    if normalized["frequency"] not in EIA_FREQUENCY_PATTERNS:
        raise ValueError(
            f"Unsupported EIA frequency: {normalized['frequency']}"
        )
    if normalized["measurement_kind"] not in EIA_MEASUREMENT_KINDS:
        raise ValueError(
            "Unsupported EIA measurement_kind: "
            f"{normalized['measurement_kind']}"
        )
    route = normalized["route"].strip("/")
    if not route or not re.fullmatch(r"[a-z0-9][a-z0-9/-]*", route):
        raise ValueError(f"Invalid EIA route: {route!r}")
    normalized["route"] = route
    normalized["facets"] = parse_facets(normalized["facets"])
    try:
        freshness_days = int(normalized["freshness_days"])
    except ValueError as error:
        raise ValueError("EIA freshness_days must be a positive integer") from error
    if freshness_days <= 0:
        raise ValueError("EIA freshness_days must be a positive integer")
    normalized["freshness_days"] = freshness_days
    normalized["seasonal_deviation"] = parse_explicit_bool(
        spec.get("seasonal_deviation", False),
        field="seasonal_deviation",
    )
    return normalized


def period_date(period: str) -> date:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", period):
        return date.fromisoformat(period)
    if re.fullmatch(r"\d{4}-\d{2}", period):
        year, month = (int(part) for part in period.split("-"))
        return date(year, month, calendar.monthrange(year, month)[1])
    if re.fullmatch(r"\d{4}", period):
        return date(int(period), 12, 31)
    raise ValueError(f"Unsupported EIA period: {period!r}")


def parse_eia_metric_series(
    text: str,
    spec: Mapping[str, Any],
) -> list[dict[str, Any]]:
    configured = validate_eia_spec(spec)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("EIA response is not valid JSON") from error
    data = payload.get("response", {}).get("data")
    if not isinstance(data, list) or not data:
        raise ValueError(
            f"EIA series {configured['metric_code']} has no data array"
        )
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in data:
        if not isinstance(raw, Mapping):
            raise ValueError("EIA data rows must be objects")
        period = str(raw.get("period") or "").strip()
        if not re.fullmatch(
            EIA_FREQUENCY_PATTERNS[configured["frequency"]],
            period,
        ):
            raise ValueError(
                f"EIA period {period!r} does not match configured "
                f"frequency {configured['frequency']}"
            )
        observation_date = period_date(period)
        if period in seen:
            raise ValueError(f"Duplicate EIA period: {period}")
        seen.add(period)
        for facet, expected in configured["facets"].items():
            actual = str(raw.get(facet) or "").strip()
            if actual != expected:
                raise ValueError(
                    f"Unexpected EIA facet {facet} for "
                    f"{configured['metric_code']}: {actual!r}; expected {expected!r}"
                )
        description = str(raw.get("series-description") or "").strip()
        if description != configured["source_description"]:
            raise ValueError(
                f"Unexpected EIA source description for "
                f"{configured['metric_code']}: {description!r}; expected "
                f"{configured['source_description']!r}"
            )
        provided_units = {
            str(raw[field]).strip()
            for field in ("unit", "units")
            if raw.get(field) not in (None, "")
        }
        if provided_units != {configured["expected_unit"]}:
            raise ValueError(
                f"Unexpected EIA unit for {configured['metric_code']}: "
                f"{sorted(provided_units)!r}; expected "
                f"{configured['expected_unit']!r}"
            )
        try:
            value = float(raw["value"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"EIA value for {period} must be finite") from error
        if not math.isfinite(value):
            raise ValueError(f"EIA value for {period} must be finite")
        known_as_of = raw.get("known_as_of") or raw.get("known-as-of")
        if known_as_of is not None:
            known_as_of = str(known_as_of).strip()
            known = datetime.fromisoformat(known_as_of)
            if known.tzinfo is None or known.utcoffset() is None:
                raise ValueError("EIA known_as_of must include a UTC offset")
        rows.append(
            {
                "period": period,
                "observation_date": observation_date,
                "known_as_of": known_as_of,
                "metric_code": configured["metric_code"],
                "metric_name": configured["metric_name"],
                "measurement_kind": configured["measurement_kind"],
                "value": value,
                "unit": configured["expected_unit"],
                "frequency": configured["frequency"],
                "commodity_code": configured["commodity_code"],
                "commodity_family": configured["commodity_family"],
                "freshness_days": configured["freshness_days"],
                "seasonal_deviation": configured["seasonal_deviation"],
            }
        )
    rows.sort(key=lambda row: row["observation_date"])
    return rows


def _eligible(row: Mapping[str, Any], cutoff: date) -> bool:
    observation = row.get("observation_date")
    if not isinstance(observation, date):
        observation = period_date(str(row.get("period") or ""))
    if observation > cutoff:
        return False
    known_raw = row.get("known_as_of")
    if not known_raw:
        return True
    known = datetime.fromisoformat(str(known_raw))
    if known.tzinfo is None or known.utcoffset() is None:
        raise ValueError("EIA known_as_of must include a UTC offset")
    cutoff_at = datetime.combine(cutoff, datetime.max.time(), tzinfo=HONG_KONG)
    return known.astimezone(HONG_KONG) <= cutoff_at


def latest_and_changes(
    rows: list[dict[str, Any]],
    cutoff: date,
) -> list[dict[str, Any]]:
    eligible = sorted(
        (dict(row) for row in rows if _eligible(row, cutoff)),
        key=lambda row: period_date(str(row["period"])),
    )
    if len(eligible) < 2:
        metric = rows[0].get("metric_code") if rows else "unknown"
        raise ValueError(f"EIA series {metric} has fewer than two eligible observations")
    previous, current = eligible[-2:]
    difference = float(current["value"]) - float(previous["value"])
    prior = float(previous["value"])
    base = {
        key: value
        for key, value in current.items()
        if key not in {"observation_date", "freshness_days"}
    }
    level = dict(base)
    change = {
        **base,
        "metric_code": f"{current['metric_code']}_change",
        "metric_name": f"{current['metric_name']} change",
        "measurement_kind": current["measurement_kind"],
        "value": difference,
        "reference_period": f"{previous['period']} to {current['period']}",
    }
    change_pct = {
        **base,
        "metric_code": f"{current['metric_code']}_change_pct",
        "metric_name": f"{current['metric_name']} change percent",
        "measurement_kind": current["measurement_kind"],
        "value": difference / prior if prior else None,
        "unit": "ratio",
        "reference_period": f"{previous['period']} to {current['period']}",
    }
    level.setdefault("reference_period", current["period"])
    metrics = [level, change, change_pct]
    if current.get("seasonal_deviation"):
        current_week = period_date(str(current["period"])).isocalendar()[1]
        prior_same_week = [
            row
            for row in eligible[:-1]
            if period_date(str(row["period"])).isocalendar()[1] == current_week
        ][-5:]
        if len(prior_same_week) == 5:
            seasonal_mean = sum(float(row["value"]) for row in prior_same_week) / 5
            metrics.append(
                {
                    **base,
                    "metric_code": f"{current['metric_code']}_seasonal_deviation",
                    "metric_name": f"{current['metric_name']} seasonal deviation",
                    "measurement_kind": current["measurement_kind"],
                    "value": float(current["value"]) - seasonal_mean,
                    "reference_period": (
                        "formula_version=eia-seasonal-v1; "
                        + ",".join(str(row["period"]) for row in prior_same_week)
                    ),
                }
            )
    return metrics


def parse_eia_series(
    text: str,
    *,
    metric_code: str,
    expected_unit: str,
) -> list[dict[str, Any]]:
    """Compatibility parser for the original single-series EIA contract."""
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
        unit = LEGACY_EIA_UNIT_CODES.get(raw_unit, raw_unit)
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
    """Compatibility calculator for callers of the original context module."""
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


def validate_facet_metadata(
    text: str,
    *,
    route: str,
    facet: str,
    expected_value: str,
) -> None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"EIA facet metadata is invalid for {route}/{facet}") from error
    values = payload.get("response", {}).get("facets")
    if not isinstance(values, list):
        raise ValueError(f"EIA facet metadata is missing for {route}/{facet}")
    identifiers = {
        str(item.get("id") or "").strip()
        for item in values
        if isinstance(item, Mapping)
    }
    if expected_value not in identifiers:
        raise ValueError(
            f"EIA configured facet is unavailable for {route}/{facet}: "
            f"{expected_value}"
        )


__all__ = [
    "CommodityHttpSpec",
    "EiaBatchError",
    "EiaBatchSpec",
    "EIA_FAMILIES",
    "EIA_PROVIDERS",
    "build_eia_batch_specs",
    "eia_response_total",
    "calculate_weekly_change",
    "fetch_eia_batches",
    "latest_and_changes",
    "load_commodity_http_policies",
    "parse_eia_metric_series",
    "parse_eia_series",
    "parse_facets",
    "period_date",
    "validate_eia_spec",
    "validate_facet_metadata",
]
