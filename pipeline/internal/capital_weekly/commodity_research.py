from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
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
RESEARCH_FACT_FIELDS = (
    "record_id",
    "as_of_date",
    "commodity_code",
    "commodity_family",
    "fact_code",
    "fact_kind",
    "value",
    "unit",
    "observation_date",
    "known_as_of",
    "reference_period",
    "formula_id",
    "formula_version",
    "input_record_ids",
    "source_urls",
    "qc_flag",
)


@dataclass(frozen=True)
class FormulaSpec:
    formula_id: str
    version: str
    fact_kind: str
    output_unit: str
    required_inputs: tuple[Mapping[str, object], ...]


_FORMULA_VERSIONS = {
    "absolute_change_v1": "1.0.0",
    "coverage_count_v1": "1.0.0",
    "freshness_age_days_v1": "1.0.0",
    "percentage_change_v1": "1.0.0",
    "seasonal_deviation_v1": "1.0.0",
    "stock_to_use_v1": "1.0.0",
    "trailing_percentile_v1": "1.0.0",
    "year_over_year_change_v1": "1.0.0",
}


def load_formula_specs(path: str | Path | None = None) -> dict[str, FormulaSpec]:
    config_path = (
        Path(path)
        if path is not None
        else Path(__file__).resolve().parents[2] / "config.json"
    )
    document = json.loads(config_path.read_text(encoding="utf-8"))
    try:
        research = document["commodity_research"]
        raw_facts = research["facts"]
        raw_universe = research["universe"]
    except (KeyError, TypeError) as error:
        raise ValueError(
            "commodity_research facts and universe must be configured"
        ) from error
    if not isinstance(raw_universe, list):
        raise ValueError("commodity_research.universe must be a row list")
    registry = validate_commodity_registry(
        {
            row.get("commodity_code"): row.get("commodity_family")
            for row in raw_universe
            if isinstance(row, Mapping)
        }
    )
    if not isinstance(raw_facts, list) or not raw_facts:
        raise ValueError("commodity_research.facts must be a nonempty row list")
    fact_fields = {
        "fact_code",
        "commodity_code",
        "commodity_family",
        "formula_id",
        "version",
        "fact_kind",
        "output_unit",
        "required_inputs",
    }
    specs: dict[str, FormulaSpec] = {}
    for raw in raw_facts:
        if not isinstance(raw, Mapping) or set(raw) != fact_fields:
            raise ValueError(
                "commodity_research fact must declare exact registered fields"
            )
        fact_code = _required_text(raw["fact_code"], "fact_code")
        if fact_code in specs:
            raise ValueError(f"Duplicate configured fact_code: {fact_code}")
        commodity_code = _required_text(raw["commodity_code"], "commodity_code")
        commodity_family = _validate_family(raw["commodity_family"])
        _validate_code_family(commodity_code, commodity_family, registry)
        raw_inputs = raw["required_inputs"]
        if not isinstance(raw_inputs, list) or not raw_inputs or not all(
            isinstance(selector, Mapping) for selector in raw_inputs
        ):
            raise ValueError("required_inputs must be a nonempty row list")
        for selector in raw_inputs:
            if selector.get("commodity_code") != commodity_code:
                raise ValueError(
                    f"Configured fact {fact_code} input commodity_code mismatch"
                )
        spec = FormulaSpec(
            formula_id=_required_text(raw["formula_id"], "formula_id"),
            version=_required_text(raw["version"], "formula_version"),
            fact_kind=_required_text(raw["fact_kind"], "fact_kind"),
            output_unit=_required_text(raw["output_unit"], "output_unit"),
            required_inputs=tuple(dict(selector) for selector in raw_inputs),
        )
        specs[fact_code] = _validated_formula_spec(spec)
    build_research_facts([], [], specs, date(2000, 1, 2))
    return specs


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


def _validated_formula_spec(value: object) -> FormulaSpec:
    if not isinstance(value, FormulaSpec):
        raise ValueError("formula_specs values must be FormulaSpec instances")
    formula_id = _required_text(value.formula_id, "formula_id")
    version = _required_text(value.version, "formula_version")
    expected_version = _FORMULA_VERSIONS.get(formula_id)
    if expected_version is None:
        raise ValueError(f"Unregistered formula_id: {formula_id}")
    if version != expected_version:
        raise ValueError(
            f"Unregistered formula version: {formula_id} {version}"
        )
    _required_text(value.fact_kind, "fact_kind")
    _required_text(value.output_unit, "output_unit")
    if not isinstance(value.required_inputs, tuple) or not value.required_inputs:
        raise ValueError("required_inputs must be a nonempty tuple")
    return value


def _validate_fact_inputs(
    price_history: Iterable[dict],
    metric_history: Iterable[dict],
    as_of_date: date,
) -> dict[str, tuple[dict, ...]]:
    if isinstance(as_of_date, datetime) or not isinstance(as_of_date, date):
        raise ValueError("as_of_date must be a date")
    cutoff = target_sunday_cutoff(as_of_date)
    normalized: dict[str, list[dict]] = {
        "price_history": [],
        "metric_history": [],
    }
    seen_record_ids: set[str] = set()
    for dataset, rows in (
        ("price_history", price_history),
        ("metric_history", metric_history),
    ):
        for raw in rows:
            if not isinstance(raw, Mapping):
                raise ValueError(f"{dataset} rows must be mappings")
            row = dict(raw)
            record_id = _required_text(row.get("record_id"), "record_id")
            if record_id in seen_record_ids:
                raise ValueError(f"Duplicate input record_id: {record_id}")
            seen_record_ids.add(record_id)
            observation = _observation_date(row.get("observation_date"))
            known, known_text = _known_as_of(row.get("known_as_of"))
            if observation > as_of_date:
                raise ValueError(
                    "input observation_date exceeds as_of_date: "
                    f"{observation.isoformat()} > {as_of_date.isoformat()}"
                )
            if known is not None and known > cutoff:
                raise ValueError(
                    "input known_as_of exceeds target Sunday cutoff: "
                    f"{known_text} > {cutoff.isoformat()}"
                )
            if str(row.get("qc_flag") or "").strip() != "OK":
                raise ValueError("research fact inputs must have qc_flag OK")
            row["record_id"] = record_id
            row["observation_date"] = observation.isoformat()
            row["known_as_of"] = known_text
            row["source_url"] = _source_url(row.get("source_url"))
            row["unit"] = _required_text(row.get("unit"), "unit")
            normalized[dataset].append(row)
    return {key: tuple(value) for key, value in normalized.items()}


def _select_two_observation_price_inputs(
    datasets: Mapping[str, tuple[dict, ...]],
    selector: Mapping[str, object],
    formula_id: str,
) -> tuple[dict, dict]:
    expected_keys = {
        "role",
        "dataset",
        "commodity_code",
        "series_code",
        "observation_count",
    }
    if not isinstance(selector, Mapping) or set(selector) != expected_keys:
        raise ValueError(
            f"{formula_id} input must declare exact price identity and "
            "observation_count"
        )
    if selector["role"] != "series" or selector["dataset"] != "price_history":
        raise ValueError(f"{formula_id} requires the series price input")
    if selector["observation_count"] != 2:
        raise ValueError(f"{formula_id} observation_count must be 2")
    commodity_code = _required_text(selector["commodity_code"], "commodity_code")
    series_code = _required_text(selector["series_code"], "series_code")
    selected = sorted(
        (
            row
            for row in datasets["price_history"]
            if row.get("commodity_code") == commodity_code
            and row.get("series_code") == series_code
        ),
        key=lambda row: (row["observation_date"], row["known_as_of"] or "", row["record_id"]),
    )
    if len(selected) < 2:
        return ()  # type: ignore[return-value]
    return selected[-2], selected[-1]


def _select_year_over_year_inputs(
    datasets: Mapping[str, tuple[dict, ...]],
    selector: Mapping[str, object],
) -> tuple[dict, dict]:
    expected_keys = {
        "role",
        "dataset",
        "commodity_code",
        "series_code",
        "observation_count",
        "comparison_years",
    }
    if not isinstance(selector, Mapping) or set(selector) != expected_keys:
        raise ValueError(
            "year_over_year_change_v1 input must declare exact price identity, "
            "observation_count, and comparison_years"
        )
    if selector["role"] != "series" or selector["dataset"] != "price_history":
        raise ValueError("year_over_year_change_v1 requires the series price input")
    if selector["observation_count"] != 2:
        raise ValueError("year_over_year_change_v1 observation_count must be 2")
    years = selector["comparison_years"]
    if isinstance(years, bool) or not isinstance(years, int) or years <= 0:
        raise ValueError("comparison_years must be a positive integer")
    commodity_code = _required_text(selector["commodity_code"], "commodity_code")
    series_code = _required_text(selector["series_code"], "series_code")
    selected = sorted(
        (
            row
            for row in datasets["price_history"]
            if row.get("commodity_code") == commodity_code
            and row.get("series_code") == series_code
        ),
        key=lambda row: (row["observation_date"], row["known_as_of"] or "", row["record_id"]),
    )
    if not selected:
        return ()  # type: ignore[return-value]
    current = selected[-1]
    current_date = date.fromisoformat(current["observation_date"])
    try:
        comparison_date = current_date.replace(year=current_date.year - years)
    except ValueError:
        return ()  # type: ignore[return-value]
    prior = [
        row for row in selected[:-1]
        if row["observation_date"] == comparison_date.isoformat()
    ]
    if len(prior) != 1:
        return ()  # type: ignore[return-value]
    return prior[0], current


def _select_metric_series(
    datasets: Mapping[str, tuple[dict, ...]],
    selector: Mapping[str, object],
    *,
    parameter_keys: set[str],
    formula_id: str,
) -> list[dict]:
    identity_keys = {
        "role",
        "dataset",
        "commodity_code",
        "metric_code",
        "metric_role",
        "measurement_kind",
        "participant_class",
    }
    if not isinstance(selector, Mapping) or set(selector) != identity_keys | parameter_keys:
        raise ValueError(
            f"{formula_id} input must declare exact metric identity and parameters"
        )
    if selector["role"] != "series" or selector["dataset"] != "metric_history":
        raise ValueError(f"{formula_id} requires the series metric input")
    commodity_code = _required_text(selector["commodity_code"], "commodity_code")
    metric_code = _required_text(selector["metric_code"], "metric_code")
    metric_role = _required_text(selector["metric_role"], "metric_role")
    measurement_kind = _required_text(
        selector["measurement_kind"], "measurement_kind"
    )
    participant_class = selector["participant_class"]
    if participant_class is not None:
        participant_class = _required_text(participant_class, "participant_class")
    return sorted(
        (
            row
            for row in datasets["metric_history"]
            if row.get("commodity_code") == commodity_code
            and row.get("metric_code") == metric_code
            and row.get("metric_role") == metric_role
            and row.get("measurement_kind") == measurement_kind
            and row.get("participant_class") == participant_class
        ),
        key=lambda row: (row["observation_date"], row["known_as_of"] or "", row["record_id"]),
    )


def _select_exact_metric_input(
    datasets: Mapping[str, tuple[dict, ...]],
    selector: Mapping[str, object],
    *,
    role: str,
    formula_id: str,
) -> dict | None:
    identity_keys = {
        "role",
        "dataset",
        "commodity_code",
        "metric_code",
        "metric_role",
        "measurement_kind",
        "participant_class",
    }
    if not isinstance(selector, Mapping) or set(selector) != identity_keys:
        raise ValueError(f"{formula_id} {role} must declare exact metric identity")
    if selector["role"] != role or selector["dataset"] != "metric_history":
        raise ValueError(f"{formula_id} requires the {role} metric input")
    commodity_code = _required_text(selector["commodity_code"], "commodity_code")
    metric_code = _required_text(selector["metric_code"], "metric_code")
    metric_role = _required_text(selector["metric_role"], "metric_role")
    measurement_kind = _required_text(
        selector["measurement_kind"], "measurement_kind"
    )
    participant_class = selector["participant_class"]
    if participant_class is not None:
        participant_class = _required_text(participant_class, "participant_class")
    selected = sorted(
        (
            row
            for row in datasets["metric_history"]
            if row.get("commodity_code") == commodity_code
            and row.get("metric_code") == metric_code
            and row.get("metric_role") == metric_role
            and row.get("measurement_kind") == measurement_kind
            and row.get("participant_class") == participant_class
        ),
        key=lambda row: (row["observation_date"], row["known_as_of"] or "", row["record_id"]),
    )
    return selected[-1] if selected else None


def _fact_from_inputs(
    *,
    fact_code: str,
    spec: FormulaSpec,
    rows: tuple[dict, ...],
    value: float,
    reference_period: str,
    as_of_date: date,
) -> dict:
    latest = max(rows, key=lambda row: row["observation_date"])
    known_values = [row["known_as_of"] for row in rows if row["known_as_of"]]
    known_as_of = max(known_values) if known_values else None
    commodity_code = _required_text(latest.get("commodity_code"), "commodity_code")
    commodity_family = _validate_family(latest.get("commodity_family"))
    if any(
        row.get("commodity_code") != commodity_code
        or row.get("commodity_family") != commodity_family
        for row in rows
    ):
        raise ValueError("Formula inputs have mixed commodity identities")
    input_record_ids = sorted(row["record_id"] for row in rows)
    source_urls = sorted({row["source_url"] for row in rows})
    observation_date = latest["observation_date"]
    identity = {
        "commodity_code": commodity_code,
        "fact_code": fact_code,
        "formula_id": spec.formula_id,
        "formula_version": spec.version,
        "known_as_of": known_as_of,
        "observation_date": observation_date,
        "reference_period": reference_period,
    }
    return _ordered_row(
        RESEARCH_FACT_FIELDS,
        {
            "record_id": stable_record_id("commodity_research_facts", identity),
            "as_of_date": as_of_date.isoformat(),
            "commodity_code": commodity_code,
            "commodity_family": commodity_family,
            "fact_code": fact_code,
            "fact_kind": spec.fact_kind,
            "value": value,
            "unit": spec.output_unit,
            "observation_date": observation_date,
            "known_as_of": known_as_of,
            "reference_period": reference_period,
            "formula_id": spec.formula_id,
            "formula_version": spec.version,
            "input_record_ids": input_record_ids,
            "source_urls": source_urls,
            "qc_flag": "OK",
        },
    )


def build_research_facts(
    price_history: Iterable[dict],
    metric_history: Iterable[dict],
    formula_specs: Mapping[str, FormulaSpec],
    as_of_date: date,
) -> list[dict]:
    if not isinstance(formula_specs, Mapping):
        raise ValueError("formula_specs must map fact_code to FormulaSpec")
    datasets = _validate_fact_inputs(price_history, metric_history, as_of_date)
    facts: list[dict] = []
    for raw_fact_code in sorted(formula_specs):
        fact_code = _required_text(raw_fact_code, "fact_code")
        spec = _validated_formula_spec(formula_specs[raw_fact_code])
        if spec.formula_id == "absolute_change_v1":
            if spec.fact_kind != "absolute_change":
                raise ValueError("absolute_change_v1 requires fact_kind absolute_change")
            if len(spec.required_inputs) != 1:
                raise ValueError("absolute_change_v1 requires one input selector")
            selected = _select_two_observation_price_inputs(
                datasets,
                spec.required_inputs[0],
                spec.formula_id,
            )
            if not selected:
                continue
            previous, current = selected
            if previous["unit"] != current["unit"] or spec.output_unit != current["unit"]:
                raise ValueError("absolute_change_v1 inputs and output have mixed units")
            value = float(current["value"]) - float(previous["value"])
            if not math.isfinite(value):
                continue
            facts.append(
                _fact_from_inputs(
                    fact_code=fact_code,
                    spec=spec,
                    rows=selected,
                    value=value,
                    reference_period=(
                        f"{previous['observation_date']} to {current['observation_date']}"
                    ),
                    as_of_date=as_of_date,
                )
            )
        elif spec.formula_id == "percentage_change_v1":
            if spec.fact_kind != "percentage_change":
                raise ValueError(
                    "percentage_change_v1 requires fact_kind percentage_change"
                )
            if spec.output_unit != "percent":
                raise ValueError("percentage_change_v1 output_unit must be percent")
            if len(spec.required_inputs) != 1:
                raise ValueError("percentage_change_v1 requires one input selector")
            selected = _select_two_observation_price_inputs(
                datasets,
                spec.required_inputs[0],
                spec.formula_id,
            )
            if not selected:
                continue
            previous, current = selected
            if previous["unit"] != current["unit"]:
                raise ValueError("percentage_change_v1 inputs have mixed units")
            if float(previous["value"]) == 0.0:
                continue
            value = (
                (float(current["value"]) - float(previous["value"]))
                / float(previous["value"])
            ) * 100.0
            if not math.isfinite(value):
                continue
            facts.append(
                _fact_from_inputs(
                    fact_code=fact_code,
                    spec=spec,
                    rows=selected,
                    value=value,
                    reference_period=(
                        f"{previous['observation_date']} to {current['observation_date']}"
                    ),
                    as_of_date=as_of_date,
                )
            )
        elif spec.formula_id == "year_over_year_change_v1":
            if spec.fact_kind != "year_over_year_change":
                raise ValueError(
                    "year_over_year_change_v1 requires fact_kind "
                    "year_over_year_change"
                )
            if len(spec.required_inputs) != 1:
                raise ValueError(
                    "year_over_year_change_v1 requires one input selector"
                )
            selected = _select_year_over_year_inputs(
                datasets,
                spec.required_inputs[0],
            )
            if not selected:
                continue
            previous, current = selected
            if previous["unit"] != current["unit"] or spec.output_unit != current["unit"]:
                raise ValueError(
                    "year_over_year_change_v1 inputs and output have mixed units"
                )
            value = float(current["value"]) - float(previous["value"])
            if not math.isfinite(value):
                continue
            facts.append(
                _fact_from_inputs(
                    fact_code=fact_code,
                    spec=spec,
                    rows=selected,
                    value=value,
                    reference_period=(
                        f"{previous['observation_date']} to {current['observation_date']}"
                    ),
                    as_of_date=as_of_date,
                )
            )
        elif spec.formula_id == "trailing_percentile_v1":
            if spec.fact_kind != "trailing_percentile":
                raise ValueError(
                    "trailing_percentile_v1 requires fact_kind trailing_percentile"
                )
            if spec.output_unit != "percentile":
                raise ValueError(
                    "trailing_percentile_v1 output_unit must be percentile"
                )
            if len(spec.required_inputs) != 1:
                raise ValueError(
                    "trailing_percentile_v1 requires one input selector"
                )
            selector = spec.required_inputs[0]
            selected = _select_metric_series(
                datasets,
                selector,
                parameter_keys={"trailing_observations", "minimum_observations"},
                formula_id=spec.formula_id,
            )
            window = selector["trailing_observations"]
            minimum = selector["minimum_observations"]
            if (
                isinstance(window, bool)
                or not isinstance(window, int)
                or window <= 0
                or isinstance(minimum, bool)
                or not isinstance(minimum, int)
                or minimum <= 0
                or minimum > window
            ):
                raise ValueError(
                    "trailing percentile window and minimum must be positive "
                    "integers with minimum no greater than window"
                )
            selected = selected[-window:]
            if len(selected) < minimum:
                continue
            if len({row["unit"] for row in selected}) != 1:
                raise ValueError("trailing_percentile_v1 inputs have mixed units")
            values = [float(row["value"]) for row in selected]
            current_value = values[-1]
            value = (
                sum(observation <= current_value for observation in values)
                / len(values)
            ) * 100.0
            if not math.isfinite(value):
                continue
            facts.append(
                _fact_from_inputs(
                    fact_code=fact_code,
                    spec=spec,
                    rows=tuple(selected),
                    value=value,
                    reference_period=(
                        f"{selected[0]['observation_date']} to "
                        f"{selected[-1]['observation_date']}"
                    ),
                    as_of_date=as_of_date,
                )
            )
        elif spec.formula_id == "seasonal_deviation_v1":
            if spec.fact_kind != "seasonal_deviation":
                raise ValueError(
                    "seasonal_deviation_v1 requires fact_kind seasonal_deviation"
                )
            if len(spec.required_inputs) != 1:
                raise ValueError(
                    "seasonal_deviation_v1 requires one input selector"
                )
            selector = spec.required_inputs[0]
            selected = _select_metric_series(
                datasets,
                selector,
                parameter_keys={"prior_years", "minimum_observations"},
                formula_id=spec.formula_id,
            )
            prior_years = selector["prior_years"]
            minimum = selector["minimum_observations"]
            if (
                isinstance(prior_years, bool)
                or not isinstance(prior_years, int)
                or prior_years <= 0
                or isinstance(minimum, bool)
                or not isinstance(minimum, int)
                or minimum <= 0
                or minimum > prior_years
            ):
                raise ValueError(
                    "seasonal prior_years and minimum must be positive integers "
                    "with minimum no greater than prior_years"
                )
            if len(selected) < 2:
                continue
            current = selected[-1]
            current_date = date.fromisoformat(current["observation_date"])
            current_week = current_date.isocalendar()[1]
            aligned = [
                row
                for row in selected[:-1]
                if date.fromisoformat(row["observation_date"]).isocalendar()[1]
                == current_week
            ][-prior_years:]
            if len(aligned) < minimum:
                continue
            used = tuple(aligned + [current])
            if len({row["unit"] for row in used}) != 1 or spec.output_unit != current["unit"]:
                raise ValueError(
                    "seasonal_deviation_v1 inputs and output have mixed units"
                )
            seasonal_mean = sum(float(row["value"]) for row in aligned) / len(aligned)
            value = float(current["value"]) - seasonal_mean
            if not math.isfinite(value):
                continue
            facts.append(
                _fact_from_inputs(
                    fact_code=fact_code,
                    spec=spec,
                    rows=used,
                    value=value,
                    reference_period=(
                        f"ISO week {current_week}: "
                        + ", ".join(row["observation_date"] for row in aligned)
                        + f" to {current['observation_date']}"
                    ),
                    as_of_date=as_of_date,
                )
            )
        elif spec.formula_id == "stock_to_use_v1":
            if spec.fact_kind != "stock_to_use":
                raise ValueError("stock_to_use_v1 requires fact_kind stock_to_use")
            if spec.output_unit != "ratio":
                raise ValueError("stock_to_use_v1 output_unit must be ratio")
            if len(spec.required_inputs) != 2:
                raise ValueError("stock_to_use_v1 requires two input selectors")
            numerator = _select_exact_metric_input(
                datasets,
                spec.required_inputs[0],
                role="numerator",
                formula_id=spec.formula_id,
            )
            denominator = _select_exact_metric_input(
                datasets,
                spec.required_inputs[1],
                role="denominator",
                formula_id=spec.formula_id,
            )
            if numerator is None or denominator is None:
                continue
            selected = (numerator, denominator)
            if numerator["unit"] != denominator["unit"]:
                raise ValueError("stock_to_use_v1 inputs have mixed units")
            if (
                numerator.get("known_as_of") != denominator.get("known_as_of")
                or numerator.get("reference_period")
                != denominator.get("reference_period")
            ):
                raise ValueError("stock_to_use_v1 inputs have mixed USDA vintage")
            if float(denominator["value"]) == 0.0:
                continue
            value = float(numerator["value"]) / float(denominator["value"])
            if not math.isfinite(value):
                continue
            facts.append(
                _fact_from_inputs(
                    fact_code=fact_code,
                    spec=spec,
                    rows=selected,
                    value=value,
                    reference_period=str(numerator.get("reference_period") or ""),
                    as_of_date=as_of_date,
                )
            )
        elif spec.formula_id == "coverage_count_v1":
            if spec.fact_kind != "coverage_count":
                raise ValueError(
                    "coverage_count_v1 requires fact_kind coverage_count"
                )
            if spec.output_unit != "count":
                raise ValueError("coverage_count_v1 output_unit must be count")
            if len(spec.required_inputs) != 1:
                raise ValueError("coverage_count_v1 requires one input selector")
            selector = spec.required_inputs[0]
            selected = _select_metric_series(
                datasets,
                selector,
                parameter_keys={"trailing_observations"},
                formula_id=spec.formula_id,
            )
            window = selector["trailing_observations"]
            if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
                raise ValueError(
                    "coverage_count_v1 trailing_observations must be a positive integer"
                )
            selected = selected[-window:]
            if not selected:
                continue
            facts.append(
                _fact_from_inputs(
                    fact_code=fact_code,
                    spec=spec,
                    rows=tuple(selected),
                    value=len(selected),
                    reference_period=(
                        f"{selected[0]['observation_date']} to "
                        f"{selected[-1]['observation_date']}"
                    ),
                    as_of_date=as_of_date,
                )
            )
        elif spec.formula_id == "freshness_age_days_v1":
            if spec.fact_kind != "freshness_age_days":
                raise ValueError(
                    "freshness_age_days_v1 requires fact_kind freshness_age_days"
                )
            if spec.output_unit != "days":
                raise ValueError("freshness_age_days_v1 output_unit must be days")
            if len(spec.required_inputs) != 1:
                raise ValueError(
                    "freshness_age_days_v1 requires one input selector"
                )
            selector = spec.required_inputs[0]
            selected = _select_metric_series(
                datasets,
                selector,
                parameter_keys={"observation_count"},
                formula_id=spec.formula_id,
            )
            observation_count = selector["observation_count"]
            if observation_count != 1:
                raise ValueError(
                    "freshness_age_days_v1 observation_count must be 1"
                )
            if not selected:
                continue
            latest = selected[-1]
            value = (
                as_of_date - date.fromisoformat(latest["observation_date"])
            ).days
            facts.append(
                _fact_from_inputs(
                    fact_code=fact_code,
                    spec=spec,
                    rows=(latest,),
                    value=value,
                    reference_period=(
                        f"{latest['observation_date']} to {as_of_date.isoformat()}"
                    ),
                    as_of_date=as_of_date,
                )
            )
    seen_fact_ids: set[str] = set()
    input_ids = {
        row["record_id"]
        for rows in datasets.values()
        for row in rows
    }
    for fact in facts:
        if fact["record_id"] in seen_fact_ids:
            raise ValueError(
                "Duplicate commodity research fact identity: "
                f"{fact['record_id']}"
            )
        seen_fact_ids.add(fact["record_id"])
        orphan_ids = sorted(set(fact["input_record_ids"]) - input_ids)
        if orphan_ids:
            raise ValueError(
                "Commodity research fact references missing input record: "
                + ", ".join(orphan_ids)
            )
    return facts


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
    "RESEARCH_FACT_FIELDS",
    "FormulaSpec",
    "bounded_metric_history",
    "bounded_price_history",
    "build_research_facts",
    "load_formula_specs",
    "stable_record_id",
    "validate_commodity_registry",
    "validate_history_limits",
]
