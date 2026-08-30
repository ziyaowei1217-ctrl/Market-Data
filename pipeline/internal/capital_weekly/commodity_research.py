from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date, datetime, timezone
import hashlib
import json
import math
from typing import Any
from urllib.parse import urlparse

from .context.common import (
    MEASUREMENT_KIND_VALUES,
    METRIC_ROLE_VALUES,
    PARTICIPANT_CLASS_VALUES,
)
from .context.provider_contracts import target_sunday_cutoff


HISTORY_FREQUENCIES = (
    "daily",
    "weekly",
    "monthly",
    "annual",
    "marketing_year",
)
COMMODITY_FAMILIES = frozenset(
    {
        "natural_gas",
        "refined_products",
        "copper",
        "gold",
        "grains_oilseeds",
        "softs",
        "livestock",
    }
)
PRICE_KINDS = frozenset({"official_cash", "official_monthly_benchmark"})
PRICE_PROVIDERS = frozenset({"eia_v2", "world_bank_pink_sheet"})

PRICE_HISTORY_FIELDS = (
    "record_id",
    "as_of_date",
    "commodity_code",
    "commodity_family",
    "series_code",
    "price_kind",
    "observation_date",
    "known_as_of",
    "value",
    "unit",
    "source",
    "source_url",
    "qc_flag",
)
METRIC_HISTORY_FIELDS = (
    "record_id",
    "as_of_date",
    "commodity_code",
    "commodity_family",
    "metric_code",
    "metric_role",
    "measurement_kind",
    "participant_class",
    "observation_date",
    "known_as_of",
    "reference_period",
    "value",
    "unit",
    "source",
    "source_url",
    "qc_flag",
)


def stable_record_id(namespace: str, identity: Mapping[str, object]) -> str:
    normalized_namespace = str(namespace).strip()
    if not normalized_namespace:
        raise ValueError("record identity namespace must not be blank")
    if not isinstance(identity, Mapping):
        raise TypeError("record identity must be a mapping")
    try:
        canonical = json.dumps(
            {
                "identity": dict(identity),
                "namespace": normalized_namespace,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("record identity must be canonical JSON data") from error
    return hashlib.sha256(canonical).hexdigest()


def validate_history_limits(limits: Mapping[str, object]) -> dict[str, int]:
    if not isinstance(limits, Mapping):
        raise ValueError("history_limits must be a mapping")
    if set(limits) != set(HISTORY_FREQUENCIES):
        missing = sorted(set(HISTORY_FREQUENCIES) - set(limits))
        extra = sorted(set(limits) - set(HISTORY_FREQUENCIES))
        detail = "; ".join(
            value
            for value in (
                f"missing {', '.join(missing)}" if missing else "",
                f"unsupported {', '.join(extra)}" if extra else "",
            )
            if value
        )
        raise ValueError(f"history_limits must declare exact frequencies: {detail}")
    normalized: dict[str, int] = {}
    for frequency in HISTORY_FREQUENCIES:
        value = limits[frequency]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(
                f"history_limits.{frequency} must be a positive integer"
            )
        normalized[frequency] = value
    return normalized


def validate_commodity_registry(
    registry: Mapping[str, object],
) -> dict[str, str]:
    if not isinstance(registry, Mapping) or not registry:
        raise ValueError("commodity_registry must be a nonempty mapping")
    normalized: dict[str, str] = {}
    for raw_code, raw_family in registry.items():
        code = _required_text(raw_code, "commodity_code")
        family = _validate_family(raw_family)
        if code in normalized:
            raise ValueError(f"Duplicate commodity_code in registry: {code}")
        normalized[code] = family
    return normalized


def _validate_code_family(
    commodity_code: str,
    commodity_family: str,
    registry: Mapping[str, str],
) -> None:
    expected_family = registry.get(commodity_code)
    if expected_family is None:
        raise ValueError(
            f"Unsupported commodity_code in commodity registry: {commodity_code}"
        )
    if expected_family != commodity_family:
        raise ValueError(
            "Commodity code-family mismatch: "
            f"{commodity_code} requires {expected_family}, got {commodity_family}"
        )


def _field(record: object, name: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(name, default)
    return getattr(record, name, default)


def _required_text(value: object, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field} must not be blank")
    return normalized


def _source_url(value: object) -> str:
    normalized = _required_text(value, "source_url")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an absolute HTTP(S) URL")
    return normalized


def _observation_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError) as error:
        raise ValueError("observation_date must be an ISO date") from error


def _known_as_of(value: object) -> tuple[datetime | None, str | None]:
    if value is None or not str(value).strip():
        return None, None
    raw = str(value).strip()
    try:
        known = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("known_as_of must be an ISO timestamp with a UTC offset") from error
    if known.tzinfo is None or known.utcoffset() is None:
        raise ValueError("known_as_of must include a UTC offset")
    canonical = known.astimezone(timezone.utc)
    return canonical, canonical.isoformat().replace("+00:00", "Z")


def _finite_value(value: object) -> int | float | None:
    if isinstance(value, bool):
        raise ValueError("value must be numeric")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("value must be numeric") from error
    if not math.isfinite(numeric):
        return None
    if isinstance(value, (int, float)):
        return value
    return numeric


def _validate_family(value: object) -> str:
    family = _required_text(value, "commodity_family")
    if family not in COMMODITY_FAMILIES:
        raise ValueError(f"Unsupported commodity_family: {family}")
    return family


def _ordered_row(fields: tuple[str, ...], values: Mapping[str, object]) -> dict:
    return {field: values[field] for field in fields}


def bounded_price_history(
    histories: Mapping[str, Iterable[dict]],
    universe: Iterable[object],
    as_of_date: date,
    limits: Mapping[str, object],
    commodity_registry: Mapping[str, object],
) -> list[dict]:
    normalized_limits = validate_history_limits(limits)
    normalized_registry = validate_commodity_registry(commodity_registry)
    if isinstance(as_of_date, datetime) or not isinstance(as_of_date, date):
        raise ValueError("as_of_date must be a date")
    if not isinstance(histories, Mapping):
        raise TypeError("histories must be a mapping")
    universe_rows = list(universe)
    cutoff = target_sunday_cutoff(as_of_date)
    grouped: dict[
        tuple[str, str],
        list[tuple[date, datetime | None, dict]],
    ] = defaultdict(list)
    frequencies: dict[str, str] = {}
    seen_ids: set[str] = set()
    seen_series: set[str] = set()

    for config in universe_rows:
        provider = str(_field(config, "provider") or "").strip()
        if provider not in PRICE_PROVIDERS:
            continue
        series_code = _required_text(_field(config, "series_code"), "series_code")
        if series_code in seen_series:
            raise ValueError(f"Duplicate configured price series: {series_code}")
        seen_series.add(series_code)
        frequency = _required_text(_field(config, "frequency"), "frequency")
        if frequency not in normalized_limits:
            raise ValueError(f"Unsupported history frequency: {frequency}")
        frequencies[series_code] = frequency
        commodity_code = _required_text(
            _field(config, "commodity_code"), "commodity_code"
        )
        commodity_family = _validate_family(_field(config, "commodity_family"))
        _validate_code_family(
            commodity_code,
            commodity_family,
            normalized_registry,
        )
        price_kind = _required_text(_field(config, "price_kind"), "price_kind")
        if price_kind not in PRICE_KINDS:
            raise ValueError(f"Unsupported price_kind: {price_kind}")
        source = _required_text(_field(config, "source"), "source")
        default_url = _source_url(_field(config, "source_url"))
        default_unit = _required_text(_field(config, "level_unit"), "unit")
        config_known = _field(config, "known_as_of")

        for raw in histories.get(series_code, ()):
            observation = _observation_date(
                raw.get("observation_date", raw.get("date"))
            )
            known, known_text = _known_as_of(
                raw.get("known_as_of", config_known)
            )
            if observation > as_of_date:
                raise ValueError(
                    "observation_date exceeds as_of_date: "
                    f"{observation.isoformat()} > {as_of_date.isoformat()}"
                )
            if known is not None and known > cutoff:
                raise ValueError(
                    "known_as_of exceeds target Sunday cutoff: "
                    f"{known_text} > {cutoff.isoformat()}"
                )
            qc_flag = str(raw.get("qc_flag", "OK") or "").strip()
            if qc_flag != "OK":
                raise ValueError(f"qc_flag must be OK, got {qc_flag or 'blank'}")
            value = _finite_value(raw.get("value"))
            if value is None:
                continue
            unit = _required_text(raw.get("unit", default_unit), "unit")
            row_source = _required_text(raw.get("source", source), "source")
            row_url = _source_url(raw.get("source_url", default_url))
            identity = {
                "code": commodity_code,
                "known_as_of": known_text,
                "observation_date": observation.isoformat(),
                "series": series_code,
            }
            record_id = stable_record_id("commodity_price_history", identity)
            if record_id in seen_ids:
                raise ValueError(
                    f"Duplicate commodity price history identity: {record_id}"
                )
            seen_ids.add(record_id)
            row = _ordered_row(
                PRICE_HISTORY_FIELDS,
                {
                    "record_id": record_id,
                    "as_of_date": as_of_date.isoformat(),
                    "commodity_code": commodity_code,
                    "commodity_family": commodity_family,
                    "series_code": series_code,
                    "price_kind": price_kind,
                    "observation_date": observation.isoformat(),
                    "known_as_of": known_text,
                    "value": value,
                    "unit": unit,
                    "source": row_source,
                    "source_url": row_url,
                    "qc_flag": "OK",
                },
            )
            grouped[(commodity_code, series_code)].append(
                (observation, known, row)
            )

    selected: list[dict] = []
    for key in sorted(grouped):
        rows = sorted(
            grouped[key],
            key=lambda item: (
                item[0],
                item[1] or datetime.min.replace(tzinfo=timezone.utc),
                item[2]["record_id"],
            ),
        )
        series_code = key[1]
        selected.extend(
            item[2] for item in rows[-normalized_limits[frequencies[series_code]] :]
        )
    return selected


def bounded_metric_history(
    rows: Iterable[dict],
    as_of_date: date,
    limits: Mapping[str, object],
    commodity_registry: Mapping[str, object],
) -> list[dict]:
    normalized_limits = validate_history_limits(limits)
    normalized_registry = validate_commodity_registry(commodity_registry)
    if isinstance(as_of_date, datetime) or not isinstance(as_of_date, date):
        raise ValueError("as_of_date must be a date")
    cutoff = target_sunday_cutoff(as_of_date)
    grouped: dict[
        tuple[str, str, str, str, str | None],
        list[tuple[date, datetime | None, dict]],
    ] = defaultdict(list)
    frequencies: dict[tuple[str, str, str, str, str | None], str] = {}
    seen_ids: set[str] = set()

    for raw in rows:
        frequency = _required_text(raw.get("frequency"), "frequency")
        if frequency not in normalized_limits:
            raise ValueError(f"Unsupported history frequency: {frequency}")
        observation = _observation_date(
            raw.get("observation_date", raw.get("as_of_date"))
        )
        known, known_text = _known_as_of(raw.get("known_as_of"))
        if observation > as_of_date:
            raise ValueError(
                "observation_date exceeds as_of_date: "
                f"{observation.isoformat()} > {as_of_date.isoformat()}"
            )
        if known is not None and known > cutoff:
            raise ValueError(
                "known_as_of exceeds target Sunday cutoff: "
                f"{known_text} > {cutoff.isoformat()}"
            )
        qc_flag = str(raw.get("qc_flag") or "").strip()
        if qc_flag != "OK":
            raise ValueError(f"qc_flag must be OK, got {qc_flag or 'blank'}")
        value = _finite_value(raw.get("value"))
        if value is None:
            continue
        commodity_code = _required_text(raw.get("commodity_code"), "commodity_code")
        commodity_family = _validate_family(raw.get("commodity_family"))
        _validate_code_family(
            commodity_code,
            commodity_family,
            normalized_registry,
        )
        metric_code = _required_text(raw.get("metric_code"), "metric_code")
        metric_role = _required_text(raw.get("metric_role"), "metric_role")
        if metric_role not in METRIC_ROLE_VALUES:
            raise ValueError(f"Unsupported metric_role: {metric_role}")
        measurement_kind = _required_text(
            raw.get("measurement_kind"), "measurement_kind"
        )
        if measurement_kind not in MEASUREMENT_KIND_VALUES:
            raise ValueError(f"Unsupported measurement_kind: {measurement_kind}")
        participant = raw.get("participant_class")
        participant_class = (
            None if participant is None or not str(participant).strip() else str(participant).strip()
        )
        if (
            participant_class is not None
            and participant_class not in PARTICIPANT_CLASS_VALUES
        ):
            raise ValueError(
                f"Unsupported participant_class: {participant_class}"
            )
        reference = raw.get("reference_period")
        reference_period = (
            None if reference is None or not str(reference).strip() else str(reference).strip()
        )
        source = _required_text(raw.get("source"), "source")
        source_url = _source_url(raw.get("source_url"))
        unit = _required_text(raw.get("unit"), "unit")
        identity = {
            "code": commodity_code,
            "known_as_of": known_text,
            "measurement": measurement_kind,
            "metric": metric_code,
            "observation_date": observation.isoformat(),
            "participant": participant_class,
            "reference_period": reference_period,
            "role": metric_role,
        }
        record_id = stable_record_id("commodity_metric_history", identity)
        if record_id in seen_ids:
            raise ValueError(
                f"Duplicate commodity metric history identity: {record_id}"
            )
        seen_ids.add(record_id)
        row = _ordered_row(
            METRIC_HISTORY_FIELDS,
            {
                "record_id": record_id,
                "as_of_date": as_of_date.isoformat(),
                "commodity_code": commodity_code,
                "commodity_family": commodity_family,
                "metric_code": metric_code,
                "metric_role": metric_role,
                "measurement_kind": measurement_kind,
                "participant_class": participant_class,
                "observation_date": observation.isoformat(),
                "known_as_of": known_text,
                "reference_period": reference_period,
                "value": value,
                "unit": unit,
                "source": source,
                "source_url": source_url,
                "qc_flag": "OK",
            },
        )
        group = (
            commodity_code,
            metric_code,
            metric_role,
            measurement_kind,
            participant_class,
        )
        existing_frequency = frequencies.setdefault(group, frequency)
        if existing_frequency != frequency:
            raise ValueError(
                f"Metric history identity has mixed frequencies: {metric_code}"
            )
        grouped[group].append((observation, known, row))

    selected: list[dict] = []
    for group in sorted(grouped, key=lambda item: tuple(value or "" for value in item)):
        history = sorted(
            grouped[group],
            key=lambda item: (
                item[0],
                item[1] or datetime.min.replace(tzinfo=timezone.utc),
                item[2]["record_id"],
            ),
        )
        selected.extend(
            item[2]
            for item in history[-normalized_limits[frequencies[group]] :]
        )
    return selected


__all__ = [
    "METRIC_HISTORY_FIELDS",
    "PRICE_HISTORY_FIELDS",
    "bounded_metric_history",
    "bounded_price_history",
    "stable_record_id",
    "validate_commodity_registry",
    "validate_history_limits",
]
