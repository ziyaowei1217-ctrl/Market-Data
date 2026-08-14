from __future__ import annotations

import hashlib
import math
from datetime import date, datetime
from typing import Any, Iterable

from .provider_contracts import filter_known_as_of


ECONOMIC_RELEASE_FIELDS = (
    "record_id", "indicator_code", "indicator_name", "observation_period",
    "release_at_bjt", "vintage_date", "as_of_date", "known_as_of",
    "value", "previous_value", "revised_previous", "consensus_value",
    "surprise_value", "unit", "frequency", "seasonal_adjustment",
    "calculation_id", "formula_version", "input_record_ids", "source",
    "source_url", "source_tier", "qc_flag",
)

OBSERVED_CALCULATION_ID = "observed"
PRICE_INDEX_MOM_CALCULATION_ID = "price_index_mom_pct"
PRICE_INDEX_YOY_CALCULATION_ID = "price_index_yoy_pct"
PRICE_INDEX_THREE_MONTH_CALCULATION_ID = "price_index_3m_annualized_pct"
REAL_GDP_QOQ_SAAR_CALCULATION_ID = "real_gdp_qoq_saar_pct"
REAL_GDP_YOY_CALCULATION_ID = "real_gdp_yoy_pct"
ISM_DISTANCE_50_CALCULATION_ID = "ism_distance_from_50"
RETAIL_SALES_YOY_CALCULATION_ID = "retail_sales_yoy_pct"

REGISTERED_CALCULATION_IDS = frozenset(
    {
        OBSERVED_CALCULATION_ID,
        PRICE_INDEX_MOM_CALCULATION_ID,
        PRICE_INDEX_YOY_CALCULATION_ID,
        PRICE_INDEX_THREE_MONTH_CALCULATION_ID,
        REAL_GDP_QOQ_SAAR_CALCULATION_ID,
        REAL_GDP_YOY_CALCULATION_ID,
        ISM_DISTANCE_50_CALCULATION_ID,
        RETAIL_SALES_YOY_CALCULATION_ID,
    }
)
CALCULATION_INPUT_ARITY = {
    PRICE_INDEX_MOM_CALCULATION_ID: 2,
    PRICE_INDEX_YOY_CALCULATION_ID: 2,
    PRICE_INDEX_THREE_MONTH_CALCULATION_ID: 2,
    REAL_GDP_QOQ_SAAR_CALCULATION_ID: 2,
    REAL_GDP_YOY_CALCULATION_ID: 2,
    ISM_DISTANCE_50_CALCULATION_ID: 2,
    RETAIL_SALES_YOY_CALCULATION_ID: 2,
}


def percent_change(current: float, base: float) -> float:
    if base == 0:
        raise ValueError("Percent change base cannot be zero")
    return (current / base - 1.0) * 100.0


def annualized_three_month_change(current: float, three_month_base: float) -> float:
    if three_month_base <= 0 or current <= 0:
        raise ValueError("Annualized price-index inputs must be positive")
    return ((current / three_month_base) ** 4 - 1.0) * 100.0


def build_release_row(
    indicator_code: str,
    observation_period: str,
    release_at_bjt: str,
    value: float,
    unit: str,
    frequency: str,
    source: str,
    source_url: str,
    known_as_of: str,
    as_of_date: date,
    *,
    indicator_name: str | None = None,
    vintage_date: str = "initial",
    previous_value: float | None = None,
    revised_previous: float | None = None,
    seasonal_adjustment: str = "",
    calculation_id: str = OBSERVED_CALCULATION_ID,
    formula_version: str = "source-v1",
    input_record_ids: tuple[str, ...] = (),
) -> dict:
    normalized_inputs = _input_record_ids(input_record_ids)
    row = {
        "indicator_code": indicator_code,
        "indicator_name": indicator_name or indicator_code,
        "observation_period": observation_period,
        "release_at_bjt": release_at_bjt,
        "vintage_date": vintage_date,
        "as_of_date": as_of_date.isoformat(),
        "known_as_of": known_as_of,
        "value": value,
        "previous_value": previous_value,
        "revised_previous": revised_previous,
        "consensus_value": None,
        "surprise_value": None,
        "unit": unit,
        "frequency": frequency,
        "seasonal_adjustment": seasonal_adjustment,
        "calculation_id": calculation_id,
        "formula_version": formula_version,
        "input_record_ids": normalized_inputs,
        "source": source,
        "source_url": source_url,
        "source_tier": "public",
        "qc_flag": "OK",
    }
    row["record_id"] = _record_id(row)
    return normalize_economic_release_rows([row])[0]


def normalize_economic_release_rows(rows: Iterable[dict[str, Any]]) -> list[dict]:
    normalized: list[dict] = []
    seen_record_ids: set[str] = set()
    for raw in rows:
        missing = [field for field in ECONOMIC_RELEASE_FIELDS if field not in raw]
        if missing:
            raise ValueError(
                "Economic release row missing required fields: " + ", ".join(missing)
            )
        row = dict(raw)
        calculation_id = str(row["calculation_id"])
        if calculation_id not in REGISTERED_CALCULATION_IDS:
            raise ValueError(f"Unknown economic calculation_id: {calculation_id}")
        row["calculation_id"] = calculation_id
        row["input_record_ids"] = _input_record_ids(row["input_record_ids"])
        row["as_of_date"] = _iso_date(row["as_of_date"])
        _aware_timestamp(row["release_at_bjt"], "release_at_bjt")
        _aware_timestamp(row["known_as_of"], "known_as_of")
        if row["source_tier"] != "public":
            raise ValueError("Economic release source_tier must be public")
        if row["consensus_value"] is not None:
            raise ValueError("Economic release consensus_value must be null for public rows")
        if row["surprise_value"] is not None:
            raise ValueError("Economic release surprise_value must be null for public rows")
        _validate_calculation_contract(row)
        for field in (
            "value",
            "previous_value",
            "revised_previous",
            "consensus_value",
            "surprise_value",
        ):
            value = row[field]
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Economic release {field} must be numeric or null")
            if not math.isfinite(float(value)):
                raise ValueError(f"Economic release {field} is non-finite")
            row[field] = float(value)
        record_id = str(row["record_id"])
        if not record_id:
            raise ValueError("Economic release record_id must not be blank")
        if record_id != _record_id(row):
            raise ValueError("Economic release record_id does not match row identity")
        if record_id in seen_record_ids:
            raise ValueError(f"Duplicate economic release record_id: {record_id}")
        seen_record_ids.add(record_id)
        normalized.append(row)
    return normalized


def validate_economic_release_input_references(rows: Iterable[dict]) -> None:
    table = list(rows)
    record_ids = {str(row["record_id"]) for row in table}
    for row in table:
        if row["calculation_id"] == OBSERVED_CALCULATION_ID:
            continue
        for input_record_id in str(row["input_record_ids"]).split("|"):
            if input_record_id not in record_ids:
                raise ValueError(
                    "Economic release input_record_id does not resolve: "
                    f"{input_record_id}"
                )


def select_latest_vintages(rows: Iterable[dict], as_of_date: date) -> list[dict]:
    eligible = filter_known_as_of(rows, as_of_date)
    latest: dict[tuple[str, str, str], tuple[datetime, dict]] = {}
    for raw in eligible:
        row = dict(raw)
        key = (
            str(row["indicator_code"]),
            str(row["observation_period"]),
            str(row["calculation_id"]),
        )
        known = _aware_timestamp(row["known_as_of"], "known_as_of")
        current = latest.get(key)
        if current is None or known > current[0]:
            latest[key] = (known, row)
    return [latest[key][1] for key in sorted(latest)]


def derive_price_index_rows(rows: Iterable[dict], indicator_code: str) -> list[dict]:
    source_rows = [dict(row) for row in rows if row["indicator_code"] == indicator_code]
    output: list[dict] = []
    for artifact_rows in _rows_by_artifact(source_rows).values():
        periods = {_month_period(row["observation_period"]): row for row in artifact_rows}
        for period in sorted(periods):
            current = periods[period]
            for suffix, calculation_id, months, calculator in (
                ("MOM_PCT", PRICE_INDEX_MOM_CALCULATION_ID, 1, percent_change),
                ("YOY_PCT", PRICE_INDEX_YOY_CALCULATION_ID, 12, percent_change),
                (
                    "3M_ANN_PCT",
                    PRICE_INDEX_THREE_MONTH_CALCULATION_ID,
                    3,
                    annualized_three_month_change,
                ),
            ):
                base = periods.get(_shift_month(period, -months))
                if base is None:
                    continue
                output.append(
                    _derived_row(
                        current,
                        indicator_code=f"{indicator_code}_{suffix}",
                        indicator_name=f"{current['indicator_name']} {suffix}",
                        value=calculator(float(current["value"]), float(base["value"])),
                        calculation_id=calculation_id,
                        input_rows=(current, base),
                    )
                )
    return output


def derive_real_gdp_rows(rows: Iterable[dict]) -> list[dict]:
    source_rows = [
        dict(row)
        for row in rows
        if row["indicator_code"] in {"REAL_GDP_INDEX_SAAR", "REAL_GDP_LEVEL_SAAR"}
    ]
    output: list[dict] = []
    for artifact_rows in _rows_by_artifact(source_rows).values():
        periods = {_quarter_period(row["observation_period"]): row for row in artifact_rows}
        for period in sorted(periods):
            current = periods[period]
            prior_quarter = periods.get(_shift_quarter(period, -1))
            if prior_quarter is not None:
                output.append(
                    _derived_row(
                        current,
                        indicator_code="REAL_GDP_QOQ_SAAR",
                        indicator_name="Real GDP QoQ SAAR",
                        value=annualized_three_month_change(
                            float(current["value"]), float(prior_quarter["value"])
                        ),
                        calculation_id=REAL_GDP_QOQ_SAAR_CALCULATION_ID,
                        input_rows=(current, prior_quarter),
                    )
                )
            prior_year = periods.get(_shift_quarter(period, -4))
            if prior_year is not None:
                output.append(
                    _derived_row(
                        current,
                        indicator_code="REAL_GDP_YOY_PCT",
                        indicator_name="Real GDP YoY",
                        value=percent_change(
                            float(current["value"]), float(prior_year["value"])
                        ),
                        calculation_id=REAL_GDP_YOY_CALCULATION_ID,
                        input_rows=(current, prior_year),
                    )
                )
    return output


def derive_retail_sales_rows(rows: Iterable[dict]) -> list[dict]:
    source_rows = [
        dict(row)
        for row in rows
        if row["indicator_code"] == "RETAIL_SALES_LEVEL_SA"
    ]
    output: list[dict] = []
    for artifact_rows in _rows_by_artifact(source_rows).values():
        periods = {_month_period(row["observation_period"]): row for row in artifact_rows}
        for period in sorted(periods):
            current = periods[period]
            prior_year = periods.get(_shift_month(period, -12))
            if prior_year is None:
                continue
            output.append(
                _derived_row(
                    current,
                    indicator_code="RETAIL_SALES_YOY_PCT",
                    indicator_name="Retail sales YoY",
                    value=percent_change(
                        float(current["value"]), float(prior_year["value"])
                    ),
                    calculation_id=RETAIL_SALES_YOY_CALCULATION_ID,
                    input_rows=(current, prior_year),
                )
            )
    return output


def derive_ism_rows(row: dict) -> list[dict]:
    observed = dict(row)
    if observed["indicator_code"] != "ISM_MANUFACTURING_PMI":
        raise ValueError("ISM derivation requires ISM_MANUFACTURING_PMI")
    return [
        observed,
        _derived_row(
            observed,
            indicator_code="ISM_MANUFACTURING_DISTANCE_50",
            indicator_name="ISM Manufacturing PMI distance from 50",
            value=round(float(observed["value"]) - 50.0, 10),
            calculation_id=ISM_DISTANCE_50_CALCULATION_ID,
            input_rows=(observed, observed),
        ),
    ]


def _derived_row(
    current: dict,
    *,
    indicator_code: str,
    indicator_name: str,
    value: float,
    calculation_id: str,
    input_rows: tuple[dict, dict],
) -> dict:
    return build_release_row(
        indicator_code=indicator_code,
        indicator_name=indicator_name,
        observation_period=str(current["observation_period"]),
        release_at_bjt=str(current["release_at_bjt"]),
        value=value,
        unit="percent" if calculation_id != ISM_DISTANCE_50_CALCULATION_ID else "index_points",
        frequency=str(current["frequency"]),
        source=str(current["source"]),
        source_url=str(current["source_url"]),
        known_as_of=_latest_input_timestamp(input_rows, "known_as_of"),
        as_of_date=date.fromisoformat(_iso_date(current["as_of_date"])),
        vintage_date=str(current["vintage_date"]),
        seasonal_adjustment=str(current["seasonal_adjustment"]),
        calculation_id=calculation_id,
        formula_version="economic-v1",
        input_record_ids=tuple(str(row["record_id"]) for row in input_rows),
    )


def _record_id(row: dict) -> str:
    payload = "|".join(
        str(row[field])
        for field in (
            "indicator_code",
            "observation_period",
            "vintage_date",
            "calculation_id",
            "input_record_ids",
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _input_record_ids(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (tuple, list)):
        return "|".join(str(item) for item in value)
    raise ValueError("input_record_ids must be a tuple, list, or pipe-delimited string")


def _validate_calculation_contract(row: dict) -> None:
    calculation_id = row["calculation_id"]
    input_record_ids = row["input_record_ids"]
    formula_version = str(row["formula_version"])
    if calculation_id == OBSERVED_CALCULATION_ID:
        if formula_version != "source-v1":
            raise ValueError("Economic release observed rows must use source-v1")
        if input_record_ids:
            raise ValueError(
                "Economic release observed rows must not declare input_record_ids"
            )
        return
    if formula_version != "economic-v1":
        raise ValueError("Economic release calculated rows must use economic-v1")
    record_ids = input_record_ids.split("|") if input_record_ids else []
    expected_arity = CALCULATION_INPUT_ARITY[calculation_id]
    if len(record_ids) != expected_arity:
        raise ValueError(
            "Economic release calculated rows require exactly "
            f"{expected_arity} input_record_ids"
        )
    for record_id in record_ids:
        if not record_id or len(record_id) != 64 or any(
            character not in "0123456789abcdef" for character in record_id
        ):
            raise ValueError("Economic release input_record_ids must contain record IDs")


def _iso_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return date.fromisoformat(str(value)).isoformat()


def _aware_timestamp(value: Any, field: str) -> datetime:
    timestamp = datetime.fromisoformat(str(value))
    if timestamp.tzinfo is None:
        raise ValueError(f"{field} must include a UTC offset")
    return timestamp


def _rows_by_artifact(rows: Iterable[dict]) -> dict[tuple[str, ...], list[dict]]:
    grouped: dict[tuple[str, ...], list[dict]] = {}
    for row in rows:
        key = (
            str(row["vintage_date"]),
            str(row["known_as_of"]),
            str(row["release_at_bjt"]),
            str(row["source"]),
            str(row["source_url"]),
        )
        grouped.setdefault(key, []).append(row)
    return grouped


def _latest_input_timestamp(input_rows: tuple[dict, dict], field: str) -> str:
    return max(
        ((
            _aware_timestamp(row[field], field),
            str(row[field]),
        ) for row in input_rows),
        key=lambda item: item[0],
    )[1]


def _month_period(value: Any) -> tuple[int, int]:
    year, month = str(value).split("-", maxsplit=1)
    result = int(year), int(month)
    if result[1] not in range(1, 13):
        raise ValueError(f"Invalid monthly observation period: {value}")
    return result


def _shift_month(period: tuple[int, int], months: int) -> tuple[int, int]:
    absolute_month = period[0] * 12 + period[1] - 1 + months
    return absolute_month // 12, absolute_month % 12 + 1


def _quarter_period(value: Any) -> tuple[int, int]:
    year, quarter = str(value).split("-Q", maxsplit=1)
    result = int(year), int(quarter)
    if result[1] not in range(1, 5):
        raise ValueError(f"Invalid quarterly observation period: {value}")
    return result


def _shift_quarter(period: tuple[int, int], quarters: int) -> tuple[int, int]:
    absolute_quarter = period[0] * 4 + period[1] - 1 + quarters
    return absolute_quarter // 4, absolute_quarter % 4 + 1


__all__ = [
    "ECONOMIC_RELEASE_FIELDS",
    "REGISTERED_CALCULATION_IDS",
    "annualized_three_month_change",
    "build_release_row",
    "derive_ism_rows",
    "derive_price_index_rows",
    "derive_real_gdp_rows",
    "derive_retail_sales_rows",
    "normalize_economic_release_rows",
    "percent_change",
    "select_latest_vintages",
    "validate_economic_release_input_references",
]
