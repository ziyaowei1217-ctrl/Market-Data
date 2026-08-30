from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import csv
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pipeline.internal.capital_weekly import macro_assets as macro_assets_module
from pipeline.internal.capital_weekly.context.provider_contracts import (
    ContextProvider,
    ProviderResult,
    ProviderSpec,
)
from pipeline.internal.capital_weekly.commodity_research import (
    METRIC_HISTORY_FIELDS,
    PRICE_HISTORY_FIELDS,
    FormulaSpec,
    bounded_metric_history,
    bounded_price_history,
    build_research_facts,
    load_formula_specs,
    stable_record_id,
)
from pipeline.internal.capital_weekly.weekly_context import (
    CATEGORY_FIELDS,
    CATEGORY_FILES,
    publish_weekly_context_bundle,
    run_weekly_context,
)


LIMITS = {
    "daily": 400,
    "weekly": 160,
    "monthly": 84,
    "annual": 12,
    "marketing_year": 12,
}
REGISTRY = {
    "NATGAS_HH": "natural_gas",
    "WTI": "refined_products",
}


def _price_config(
    series_code: str,
    frequency: str,
    *,
    provider: str = "eia_v2",
    commodity_code: str | None = None,
) -> dict:
    code = commodity_code or series_code
    return {
        "series_code": series_code,
        "provider": provider,
        "frequency": frequency,
        "level_unit": f"native-{frequency}",
        "source": "Official fixture",
        "source_url": "https://official.example.test/prices",
        "commodity_code": code,
        "commodity_family": "refined_products",
        "price_kind": (
            "official_cash"
            if provider == "eia_v2"
            else "official_monthly_benchmark"
        ),
    }


def _price_points(
    as_of: date,
    *,
    count: int,
    step_days: int,
) -> list[dict]:
    first = as_of - timedelta(days=(count - 1) * step_days)
    return [
        {
            "date": first + timedelta(days=index * step_days),
            "known_as_of": datetime.combine(
                first + timedelta(days=index * step_days),
                datetime.min.time(),
                tzinfo=timezone.utc,
            ).isoformat(),
            "value": float(index + 1),
        }
        for index in range(count)
    ]


def _metric_row(
    observation_date: date,
    *,
    frequency: str = "weekly",
    value: float = 10.0,
    known_as_of: str | None = None,
    qc_flag: str = "OK",
    source_url: str = "https://official.example.test/metric",
    metric_role: str = "physical_fundamental",
    measurement_kind: str = "inventory",
) -> dict:
    return {
        "as_of_date": observation_date,
        "category": "commodity_fundamentals",
        "metric_code": "stocks",
        "metric_name": "Official stocks",
        "value": value,
        "unit": "native-bcf",
        "frequency": frequency,
        "market": "US",
        "source": "Official fixture",
        "source_url": source_url,
        "qc_flag": qc_flag,
        "commodity_code": "NATGAS_HH",
        "commodity_family": "natural_gas",
        "metric_role": metric_role,
        "measurement_kind": measurement_kind,
        "participant_class": None,
        "known_as_of": known_as_of
        or datetime.combine(
            observation_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        ).isoformat(),
        "reference_period": observation_date.isoformat(),
    }


class StableRecordIdTests(unittest.TestCase):
    def test_canonical_utf8_json_produces_stable_sha256_identity(self):
        left = {
            "series": "WTI",
            "code": "WTI",
            "observation_date": "2026-08-28",
            "known_as_of": "2026-08-28T12:00:00+00:00",
        }
        right = dict(reversed(tuple(left.items())))

        self.assertEqual(
            stable_record_id("commodity_price_history", left),
            "1032a8342a32869a1608b8537e74986d71878dee362d61a2587ec513d1707c44",
        )
        self.assertEqual(
            stable_record_id("commodity_price_history", left),
            stable_record_id("commodity_price_history", right),
        )


class HistoryLimitConfigTests(unittest.TestCase):
    def _write_config(self, root: Path, limits: dict) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        path = root / "config.json"
        path.write_text(
            json.dumps(
                {
                    "commodity_research": {
                        "history_limits": limits,
                        "universe": [
                            {
                                "commodity_code": code,
                                "commodity_family": family,
                            }
                            for code, family in REGISTRY.items()
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_loads_all_explicit_positive_frequency_limits(self):
        with TemporaryDirectory() as directory:
            path = self._write_config(Path(directory), LIMITS)

            self.assertEqual(
                macro_assets_module.load_commodity_research_config(
                    path
                ).history_limits,
                LIMITS,
            )

    def test_missing_or_nonpositive_limit_fails_without_a_default(self):
        invalid_limits = [
            {key: value for key, value in LIMITS.items() if key != "weekly"},
            {**LIMITS, "daily": 0},
            {**LIMITS, "monthly": -1},
            {**LIMITS, "annual": 1.5},
            {**LIMITS, "marketing_year": True},
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for index, limits in enumerate(invalid_limits):
                with self.subTest(limits=limits):
                    path = self._write_config(root / str(index), limits)
                    with self.assertRaisesRegex(ValueError, "history_limits"):
                        macro_assets_module.load_commodity_research_config(path)

    def test_production_config_declares_the_exact_code_family_registry(self):
        loader = getattr(
            macro_assets_module,
            "load_commodity_research_config",
            None,
        )
        self.assertIsNotNone(loader)

        config = loader()

        self.assertEqual(
            config.commodity_registry,
            {
                "NATGAS_HH": "natural_gas",
                "WTI": "refined_products",
                "BRENT": "refined_products",
                "RBOB_US": "refined_products",
                "ULSD_US": "refined_products",
                "JET_US": "refined_products",
                "PROPANE_US": "refined_products",
                "COPPER_COMEX": "copper",
                "GOLD_COMEX": "gold",
                "CORN": "grains_oilseeds",
                "SOYBEANS": "grains_oilseeds",
                "WHEAT": "grains_oilseeds",
                "RICE": "grains_oilseeds",
                "COTTON": "softs",
                "SUGAR": "softs",
                "COFFEE": "softs",
                "COCOA": "softs",
                "CATTLE": "livestock",
                "HOGS": "livestock",
            },
        )
        for price_config in macro_assets_module.load_macro_asset_universe():
            if price_config.provider not in {
                "eia_v2",
                "world_bank_pink_sheet",
            }:
                continue
            with self.subTest(series_code=price_config.series_code):
                self.assertEqual(
                    config.commodity_registry.get(price_config.commodity_code),
                    price_config.commodity_family,
                )


class BoundedPriceHistoryTests(unittest.TestCase):
    def test_point_in_time_selection_precedes_exact_frequency_windows(self):
        as_of = date(2026, 8, 30)
        definitions = (
            ("DAILY", "daily", 402, 1, 400, "eia_v2"),
            ("WEEKLY", "weekly", 162, 7, 160, "eia_v2"),
            ("MONTHLY", "monthly", 86, 28, 84, "world_bank_pink_sheet"),
            ("ANNUAL", "annual", 14, 365, 12, "world_bank_pink_sheet"),
        )
        universe = []
        histories = {}
        expected_oldest = {}
        for series, frequency, count, step, limit, provider in definitions:
            universe.append(_price_config(series, frequency, provider=provider))
            points = _price_points(as_of, count=count, step_days=step)
            expected_oldest[series] = points[-limit]["date"].isoformat()
            histories[series] = points

        rows = bounded_price_history(
            histories,
            universe,
            as_of,
            LIMITS,
            {
                config["commodity_code"]: config["commodity_family"]
                for config in universe
            },
        )

        self.assertTrue(all(tuple(row) == PRICE_HISTORY_FIELDS for row in rows))
        for series, _frequency, _count, _step, limit, _provider in definitions:
            with self.subTest(series=series):
                selected = [row for row in rows if row["series_code"] == series]
                self.assertEqual(len(selected), limit)
                self.assertEqual(selected[0]["observation_date"], expected_oldest[series])
                self.assertEqual(
                    [row["observation_date"] for row in selected],
                    sorted(row["observation_date"] for row in selected),
                )
                self.assertEqual(selected[-1]["unit"], f"native-{_frequency}")

    def test_future_price_observation_or_vintage_is_rejected(self):
        as_of = date(2026, 8, 30)
        invalid = (
            (
                {
                    "date": as_of + timedelta(days=1),
                    "known_as_of": "2026-08-30T12:00:00Z",
                    "value": 99.0,
                },
                "observation_date exceeds as_of_date",
            ),
            (
                {
                    "date": as_of,
                    "known_as_of": "2026-08-31T00:00:00Z",
                    "value": 99.0,
                },
                "known_as_of exceeds target Sunday",
            ),
        )

        for point, message in invalid:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    bounded_price_history(
                        {"WTI": [point]},
                        [_price_config("WTI", "daily")],
                        as_of,
                        LIMITS,
                        REGISTRY,
                    )

    def test_duplicate_semantic_identity_fails_even_when_values_match(self):
        as_of = date(2026, 8, 30)
        point = {
            "date": as_of,
            "known_as_of": "2026-08-30T00:00:00+00:00",
            "value": 78.5,
        }

        with self.assertRaisesRegex(ValueError, "Duplicate.*identity"):
            bounded_price_history(
                {"WTI": [point, dict(point)]},
                [_price_config("WTI", "daily")],
                as_of,
                LIMITS,
                REGISTRY,
            )

    def test_equivalent_known_as_of_offsets_are_one_semantic_identity(self):
        as_of = date(2026, 8, 30)
        points = [
            {
                "date": as_of,
                "known_as_of": "2026-08-30T08:00:00Z",
                "value": 78.5,
            },
            {
                "date": as_of,
                "known_as_of": "2026-08-30T16:00:00+08:00",
                "value": 78.5,
            },
        ]

        with self.assertRaisesRegex(ValueError, "Duplicate.*identity"):
            bounded_price_history(
                {"WTI": points},
                [_price_config("WTI", "daily")],
                as_of,
                LIMITS,
                REGISTRY,
            )

    def test_nonfinite_price_is_omitted_and_never_coerced_to_zero(self):
        rows = bounded_price_history(
            {
                "WTI": [
                    {
                        "date": date(2026, 8, 29),
                        "known_as_of": "2026-08-29T00:00:00+00:00",
                        "value": float("nan"),
                    },
                    {
                        "date": date(2026, 8, 30),
                        "known_as_of": "2026-08-30T00:00:00+00:00",
                        "value": 78.5,
                    },
                ]
            },
            [_price_config("WTI", "daily")],
            date(2026, 8, 30),
            LIMITS,
            REGISTRY,
        )

        self.assertEqual([row["value"] for row in rows], [78.5])
        self.assertNotIn(0, [row["value"] for row in rows])

    def test_nonofficial_price_provider_is_not_a_commodity_research_history(self):
        rows = bounded_price_history(
            {"BTC_USD": _price_points(date(2026, 8, 30), count=2, step_days=1)},
            [
                _price_config(
                    "BTC_USD",
                    "daily",
                    provider="yahoo_chart",
                    commodity_code="BTC_USD",
                )
            ],
            date(2026, 8, 30),
            LIMITS,
            REGISTRY,
        )

        self.assertEqual(rows, [])

    def test_price_history_rejects_unconfigured_and_mismatched_code_family(self):
        as_of = date(2026, 8, 30)
        point = {
            "date": as_of,
            "known_as_of": "2026-08-30T12:00:00Z",
            "value": 78.5,
        }
        invalid = (
            (
                _price_config(
                    "MADE_UP",
                    "daily",
                    commodity_code="MADE_UP",
                ),
                "commodity_code",
            ),
            (
                {
                    **_price_config("WTI", "daily"),
                    "commodity_family": "gold",
                },
                "code-family",
            ),
        )

        for config, message in invalid:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    bounded_price_history(
                        {config["series_code"]: [point]},
                        [config],
                        as_of,
                        LIMITS,
                        REGISTRY,
                    )


class BoundedMetricHistoryTests(unittest.TestCase):
    def test_metric_history_is_bounded_sorted_and_preserves_native_units(self):
        as_of = date(2026, 8, 30)
        first = as_of - timedelta(days=161 * 7)
        inputs = [
            _metric_row(first + timedelta(days=index * 7), value=float(index + 1))
            for index in range(162)
        ]

        rows = bounded_metric_history(inputs, as_of, LIMITS, REGISTRY)

        self.assertEqual(len(rows), 160)
        self.assertTrue(all(tuple(row) == METRIC_HISTORY_FIELDS for row in rows))
        self.assertEqual(rows[0]["observation_date"], inputs[2]["as_of_date"].isoformat())
        self.assertEqual(rows[-1]["unit"], "native-bcf")
        self.assertEqual(
            [row["observation_date"] for row in rows],
            sorted(row["observation_date"] for row in rows),
        )

    def test_duplicate_metric_identity_fails_and_nonfinite_row_is_omitted(self):
        as_of = date(2026, 8, 30)
        row = _metric_row(as_of)
        with self.assertRaisesRegex(ValueError, "Duplicate.*identity"):
            bounded_metric_history([row, dict(row)], as_of, LIMITS, REGISTRY)

        selected = bounded_metric_history(
            [
                _metric_row(as_of - timedelta(days=7), value=-math.inf),
                _metric_row(as_of, value=12.0),
            ],
            as_of,
            LIMITS,
            REGISTRY,
        )
        self.assertEqual([item["value"] for item in selected], [12.0])

    def test_metric_trimming_orders_vintages_by_aware_timestamp(self):
        as_of = date(2026, 8, 30)
        observation = date(2026, 8, 29)
        nine_utc = _metric_row(
            observation,
            value=9.0,
            known_as_of="2026-08-30T09:00:00Z",
        )
        ten_utc = _metric_row(
            observation,
            value=10.0,
            known_as_of="2026-08-30T02:00:00-08:00",
        )

        rows = bounded_metric_history(
            [nine_utc, ten_utc],
            as_of,
            {**LIMITS, "weekly": 1},
            REGISTRY,
        )

        self.assertEqual([row["value"] for row in rows], [10.0])
        self.assertEqual(rows[0]["known_as_of"], "2026-08-30T10:00:00Z")

    def test_invalid_source_qc_taxonomy_or_timestamp_fails_closed(self):
        as_of = date(2026, 8, 30)
        invalid = (
            (_metric_row(as_of, source_url=""), "source_url"),
            (_metric_row(as_of, qc_flag="FETCH_FAILED"), "qc_flag"),
            (_metric_row(as_of, metric_role="fundamental"), "metric_role"),
            (_metric_row(as_of, measurement_kind="physical_level"), "measurement_kind"),
            (_metric_row(as_of, known_as_of="2026-08-30T12:00:00"), "UTC offset"),
        )
        for row, message in invalid:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    bounded_metric_history([row], as_of, LIMITS, REGISTRY)

    def test_future_metric_observation_or_vintage_is_rejected(self):
        as_of = date(2026, 8, 30)
        invalid = (
            (
                _metric_row(
                    as_of + timedelta(days=1),
                    known_as_of="2026-08-30T12:00:00Z",
                ),
                "observation_date exceeds as_of_date",
            ),
            (
                _metric_row(
                    as_of,
                    known_as_of="2026-08-31T00:00:00Z",
                ),
                "known_as_of exceeds target Sunday",
            ),
        )

        for row, message in invalid:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    bounded_metric_history(
                        [row],
                        as_of,
                        LIMITS,
                        REGISTRY,
                    )

    def test_metric_history_rejects_unconfigured_and_mismatched_code_family(self):
        as_of = date(2026, 8, 30)
        made_up = {
            **_metric_row(as_of),
            "commodity_code": "MADE_UP",
            "commodity_family": "gold",
        }
        mismatched = {
            **_metric_row(as_of),
            "commodity_family": "gold",
        }

        for row, message in (
            (made_up, "commodity_code"),
            (mismatched, "code-family"),
        ):
            with self.subTest(row=row):
                with self.assertRaisesRegex(ValueError, message):
                    bounded_metric_history(
                        [row],
                        as_of,
                        LIMITS,
                        commodity_registry=REGISTRY,
                    )


def _research_price(
    record_id: str,
    observation_date: str,
    value: float,
    *,
    unit: str = "USD/BBL",
    known_as_of: str | None = None,
    source_url: str = "https://official.example.test/prices",
) -> dict:
    return {
        "record_id": record_id,
        "as_of_date": "2026-08-30",
        "commodity_code": "WTI",
        "commodity_family": "refined_products",
        "series_code": "WTI_CASH",
        "price_kind": "official_cash",
        "observation_date": observation_date,
        "known_as_of": known_as_of or f"{observation_date}T12:00:00Z",
        "value": value,
        "unit": unit,
        "source": "Official price fixture",
        "source_url": source_url,
        "qc_flag": "OK",
    }


def _price_selector(**parameters) -> dict:
    return {
        "role": "series",
        "dataset": "price_history",
        "commodity_code": "WTI",
        "series_code": "WTI_CASH",
        **parameters,
    }


def _research_metric(
    record_id: str,
    observation_date: str,
    value: float,
    *,
    commodity_code: str = "NATGAS_HH",
    commodity_family: str = "natural_gas",
    metric_code: str = "eia_ng_storage_lower48",
    metric_role: str = "physical_fundamental",
    measurement_kind: str = "inventory",
    participant_class: str | None = None,
    unit: str = "BCF",
    known_as_of: str | None = None,
    reference_period: str | None = None,
    source_url: str = "https://official.example.test/metrics",
) -> dict:
    return {
        "record_id": record_id,
        "as_of_date": "2026-08-30",
        "commodity_code": commodity_code,
        "commodity_family": commodity_family,
        "metric_code": metric_code,
        "metric_role": metric_role,
        "measurement_kind": measurement_kind,
        "participant_class": participant_class,
        "observation_date": observation_date,
        "known_as_of": known_as_of or f"{observation_date}T12:00:00Z",
        "reference_period": reference_period or observation_date,
        "value": value,
        "unit": unit,
        "source": "Official metric fixture",
        "source_url": source_url,
        "qc_flag": "OK",
    }


def _metric_selector(**parameters) -> dict:
    return {
        "role": "series",
        "dataset": "metric_history",
        "commodity_code": "NATGAS_HH",
        "metric_code": "eia_ng_storage_lower48",
        "metric_role": "physical_fundamental",
        "measurement_kind": "inventory",
        "participant_class": None,
        **parameters,
    }


def _stock_to_use_specs() -> dict:
    return {
        "corn_stock_to_use": FormulaSpec(
            formula_id="stock_to_use_v1",
            version="1.0.0",
            fact_kind="stock_to_use",
            output_unit="ratio",
            required_inputs=(
                {
                    "role": "numerator",
                    "dataset": "metric_history",
                    "commodity_code": "CORN",
                    "metric_code": "usda_psd_ending_stocks",
                    "metric_role": "physical_fundamental",
                    "measurement_kind": "inventory",
                    "participant_class": None,
                },
                {
                    "role": "denominator",
                    "dataset": "metric_history",
                    "commodity_code": "CORN",
                    "metric_code": "usda_psd_domestic_use",
                    "metric_role": "physical_fundamental",
                    "measurement_kind": "demand",
                    "participant_class": None,
                },
            ),
        )
    }


class RegisteredResearchFactTests(unittest.TestCase):
    def test_production_config_registers_all_formulas_with_exact_inputs(self):
        specs = load_formula_specs()

        self.assertEqual(
            {spec.formula_id for spec in specs.values()},
            {
                "absolute_change_v1",
                "percentage_change_v1",
                "year_over_year_change_v1",
                "trailing_percentile_v1",
                "seasonal_deviation_v1",
                "stock_to_use_v1",
                "coverage_count_v1",
                "freshness_age_days_v1",
            },
        )
        self.assertTrue(specs)
        for fact_code, spec in specs.items():
            with self.subTest(fact_code=fact_code):
                self.assertEqual(fact_code, fact_code.strip())
                self.assertTrue(spec.required_inputs)
                for selector in spec.required_inputs:
                    self.assertIn(
                        selector["dataset"],
                        {"price_history", "metric_history"},
                    )
                    self.assertIn("commodity_code", selector)
                    self.assertNotIn("prefix", selector)
                    self.assertNotIn("label", selector)

    def test_absolute_change_has_registered_formula_and_exact_provenance(self):
        specs = {
            "wti_absolute_change": FormulaSpec(
                formula_id="absolute_change_v1",
                version="1.0.0",
                fact_kind="absolute_change",
                output_unit="USD/BBL",
                required_inputs=(_price_selector(observation_count=2),),
            )
        }
        price_history = [
            _research_price(
                "price-new",
                "2026-08-29",
                78.0,
                source_url="https://official.example.test/shared",
            ),
            _research_price(
                "price-old",
                "2026-08-22",
                75.0,
                source_url="https://official.example.test/shared",
            ),
        ]

        facts = build_research_facts(
            price_history,
            [],
            specs,
            date(2026, 8, 30),
        )

        self.assertEqual(len(facts), 1)
        fact = facts[0]
        self.assertEqual(fact["value"], 3.0)
        self.assertEqual(fact["unit"], "USD/BBL")
        self.assertEqual(fact["observation_date"], "2026-08-29")
        self.assertEqual(fact["known_as_of"], "2026-08-29T12:00:00Z")
        self.assertEqual(fact["reference_period"], "2026-08-22 to 2026-08-29")
        self.assertEqual(fact["formula_id"], "absolute_change_v1")
        self.assertEqual(fact["formula_version"], "1.0.0")
        self.assertEqual(fact["input_record_ids"], ["price-new", "price-old"])
        self.assertEqual(
            fact["source_urls"],
            ["https://official.example.test/shared"],
        )
        self.assertNotIn("bullish", json.dumps(fact).lower())
        self.assertNotIn("bearish", json.dumps(fact).lower())
        self.assertNotIn("prediction", json.dumps(fact).lower())

    def test_percentage_change_is_percent_with_exact_inputs(self):
        specs = {
            "wti_percentage_change": FormulaSpec(
                formula_id="percentage_change_v1",
                version="1.0.0",
                fact_kind="percentage_change",
                output_unit="percent",
                required_inputs=(_price_selector(observation_count=2),),
            )
        }

        facts = build_research_facts(
            [
                _research_price("price-old", "2026-08-22", 80.0),
                _research_price("price-new", "2026-08-29", 84.0),
            ],
            [],
            specs,
            date(2026, 8, 30),
        )

        self.assertEqual(len(facts), 1)
        fact = facts[0]
        self.assertEqual(fact["value"], 5.0)
        self.assertEqual(fact["unit"], "percent")
        self.assertEqual(fact["observation_date"], "2026-08-29")
        self.assertEqual(fact["known_as_of"], "2026-08-29T12:00:00Z")
        self.assertEqual(fact["formula_id"], "percentage_change_v1")
        self.assertEqual(fact["formula_version"], "1.0.0")
        self.assertEqual(fact["input_record_ids"], ["price-new", "price-old"])
        self.assertEqual(
            fact["source_urls"],
            ["https://official.example.test/prices"],
        )

    def test_percentage_change_zero_denominator_is_factually_unavailable(self):
        specs = {
            "wti_percentage_change": FormulaSpec(
                formula_id="percentage_change_v1",
                version="1.0.0",
                fact_kind="percentage_change",
                output_unit="percent",
                required_inputs=(_price_selector(observation_count=2),),
            )
        }

        self.assertEqual(
            build_research_facts(
                [
                    _research_price("price-old", "2026-08-22", 0.0),
                    _research_price("price-new", "2026-08-29", 84.0),
                ],
                [],
                specs,
                date(2026, 8, 30),
            ),
            [],
        )

    def test_year_over_year_change_uses_exact_configured_year_alignment(self):
        specs = {
            "wti_year_over_year_change": FormulaSpec(
                formula_id="year_over_year_change_v1",
                version="1.0.0",
                fact_kind="year_over_year_change",
                output_unit="USD/BBL",
                required_inputs=(
                    _price_selector(observation_count=2, comparison_years=1),
                ),
            )
        }

        facts = build_research_facts(
            [
                _research_price("prior-year", "2025-08-29", 70.0),
                _research_price("current-year", "2026-08-29", 76.0),
            ],
            [],
            specs,
            date(2026, 8, 30),
        )

        self.assertEqual(len(facts), 1)
        fact = facts[0]
        self.assertEqual(fact["value"], 6.0)
        self.assertEqual(fact["unit"], "USD/BBL")
        self.assertEqual(fact["observation_date"], "2026-08-29")
        self.assertEqual(fact["known_as_of"], "2026-08-29T12:00:00Z")
        self.assertEqual(fact["reference_period"], "2025-08-29 to 2026-08-29")
        self.assertEqual(fact["formula_id"], "year_over_year_change_v1")
        self.assertEqual(fact["formula_version"], "1.0.0")
        self.assertEqual(
            fact["input_record_ids"],
            ["current-year", "prior-year"],
        )
        self.assertEqual(
            fact["source_urls"],
            ["https://official.example.test/prices"],
        )

    def test_trailing_percentile_uses_configured_inclusive_rank(self):
        specs = {
            "natgas_storage_percentile": FormulaSpec(
                formula_id="trailing_percentile_v1",
                version="1.0.0",
                fact_kind="trailing_percentile",
                output_unit="percentile",
                required_inputs=(
                    _metric_selector(
                        trailing_observations=4,
                        minimum_observations=4,
                    ),
                ),
            )
        }
        history = [
            _research_metric("storage-1", "2026-08-08", 10.0),
            _research_metric("storage-2", "2026-08-15", 40.0),
            _research_metric("storage-3", "2026-08-22", 20.0),
            _research_metric("storage-4", "2026-08-29", 30.0),
        ]

        facts = build_research_facts([], history, specs, date(2026, 8, 30))

        self.assertEqual(len(facts), 1)
        fact = facts[0]
        self.assertEqual(fact["value"], 75.0)
        self.assertEqual(fact["unit"], "percentile")
        self.assertEqual(fact["observation_date"], "2026-08-29")
        self.assertEqual(fact["known_as_of"], "2026-08-29T12:00:00Z")
        self.assertEqual(fact["reference_period"], "2026-08-08 to 2026-08-29")
        self.assertEqual(fact["formula_id"], "trailing_percentile_v1")
        self.assertEqual(fact["formula_version"], "1.0.0")
        self.assertEqual(
            fact["input_record_ids"],
            ["storage-1", "storage-2", "storage-3", "storage-4"],
        )
        self.assertEqual(
            fact["source_urls"],
            ["https://official.example.test/metrics"],
        )

    def test_seasonal_deviation_uses_aligned_iso_week_history(self):
        specs = {
            "natgas_storage_seasonal_deviation": FormulaSpec(
                formula_id="seasonal_deviation_v1",
                version="1.0.0",
                fact_kind="seasonal_deviation",
                output_unit="BCF",
                required_inputs=(
                    _metric_selector(prior_years=3, minimum_observations=3),
                ),
            )
        }
        history = [
            _research_metric("season-2023", "2023-08-25", 100.0),
            _research_metric("season-2024", "2024-08-23", 110.0),
            _research_metric("season-2025", "2025-08-22", 120.0),
            _research_metric("season-2026", "2026-08-21", 150.0),
        ]

        facts = build_research_facts([], history, specs, date(2026, 8, 30))

        self.assertEqual(len(facts), 1)
        fact = facts[0]
        self.assertEqual(fact["value"], 40.0)
        self.assertEqual(fact["unit"], "BCF")
        self.assertEqual(fact["observation_date"], "2026-08-21")
        self.assertEqual(fact["known_as_of"], "2026-08-21T12:00:00Z")
        self.assertEqual(
            fact["reference_period"],
            "ISO week 34: 2023-08-25, 2024-08-23, 2025-08-22 to 2026-08-21",
        )
        self.assertEqual(fact["formula_id"], "seasonal_deviation_v1")
        self.assertEqual(fact["formula_version"], "1.0.0")
        self.assertEqual(
            fact["input_record_ids"],
            ["season-2023", "season-2024", "season-2025", "season-2026"],
        )
        self.assertEqual(
            fact["source_urls"],
            ["https://official.example.test/metrics"],
        )

    def test_seasonal_deviation_requires_configured_week_coverage(self):
        specs = {
            "natgas_storage_seasonal_deviation": FormulaSpec(
                formula_id="seasonal_deviation_v1",
                version="1.0.0",
                fact_kind="seasonal_deviation",
                output_unit="BCF",
                required_inputs=(
                    _metric_selector(prior_years=3, minimum_observations=3),
                ),
            )
        }

        facts = build_research_facts(
            [],
            [
                _research_metric("season-2024", "2024-08-23", 110.0),
                _research_metric("season-2025", "2025-08-22", 120.0),
                _research_metric("season-2026", "2026-08-21", 150.0),
            ],
            specs,
            date(2026, 8, 30),
        )

        self.assertEqual(facts, [])

    def test_seasonal_deviation_uses_latest_revision_per_distinct_iso_year(self):
        specs = {
            "natgas_storage_seasonal_deviation": FormulaSpec(
                formula_id="seasonal_deviation_v1",
                version="1.0.0",
                fact_kind="seasonal_deviation",
                output_unit="BCF",
                required_inputs=(
                    _metric_selector(prior_years=3, minimum_observations=3),
                ),
            )
        }
        history = [
            _research_metric("season-2023", "2023-08-25", 100.0),
            _research_metric(
                "season-2024-original",
                "2024-08-23",
                110.0,
                known_as_of="2024-08-23T12:00:00Z",
            ),
            _research_metric(
                "season-2024-revision",
                "2024-08-23",
                130.0,
                known_as_of="2024-08-24T12:00:00Z",
            ),
            _research_metric("season-2025", "2025-08-22", 140.0),
            _research_metric("season-2026", "2026-08-21", 170.0),
        ]

        facts = build_research_facts([], history, specs, date(2026, 8, 30))

        self.assertEqual(len(facts), 1)
        self.assertAlmostEqual(facts[0]["value"], 170.0 - (370.0 / 3.0))
        self.assertEqual(
            facts[0]["input_record_ids"],
            [
                "season-2023",
                "season-2024-revision",
                "season-2025",
                "season-2026",
            ],
        )
        self.assertNotIn("season-2024-original", facts[0]["input_record_ids"])

    def test_seasonal_minimum_counts_distinct_prior_iso_years(self):
        specs = {
            "natgas_storage_seasonal_deviation": FormulaSpec(
                formula_id="seasonal_deviation_v1",
                version="1.0.0",
                fact_kind="seasonal_deviation",
                output_unit="BCF",
                required_inputs=(
                    _metric_selector(prior_years=3, minimum_observations=3),
                ),
            )
        }
        history = [
            _research_metric(
                "season-2024-original",
                "2024-08-23",
                110.0,
                known_as_of="2024-08-23T12:00:00Z",
            ),
            _research_metric(
                "season-2024-revision",
                "2024-08-23",
                130.0,
                known_as_of="2024-08-24T12:00:00Z",
            ),
            _research_metric("season-2025", "2025-08-22", 140.0),
            _research_metric("season-2026", "2026-08-21", 170.0),
        ]

        self.assertEqual(
            build_research_facts([], history, specs, date(2026, 8, 30)),
            [],
        )

    def test_stock_to_use_requires_exact_same_vintage_usda_inputs(self):
        specs = {
            "corn_stock_to_use": FormulaSpec(
                formula_id="stock_to_use_v1",
                version="1.0.0",
                fact_kind="stock_to_use",
                output_unit="ratio",
                required_inputs=(
                    {
                        "role": "numerator",
                        "dataset": "metric_history",
                        "commodity_code": "CORN",
                        "metric_code": "usda_psd_ending_stocks",
                        "metric_role": "physical_fundamental",
                        "measurement_kind": "inventory",
                        "participant_class": None,
                    },
                    {
                        "role": "denominator",
                        "dataset": "metric_history",
                        "commodity_code": "CORN",
                        "metric_code": "usda_psd_domestic_use",
                        "metric_role": "physical_fundamental",
                        "measurement_kind": "demand",
                        "participant_class": None,
                    },
                ),
            )
        }
        history = [
            _research_metric(
                "corn-ending",
                "2026-08-12",
                200.0,
                commodity_code="CORN",
                commodity_family="grains_oilseeds",
                metric_code="usda_psd_ending_stocks",
                measurement_kind="inventory",
                unit="1000 MT",
                known_as_of="2026-08-12T16:00:00Z",
                reference_period="2026/27",
                source_url="https://official.example.test/usda/ending",
            ),
            _research_metric(
                "corn-use",
                "2026-08-12",
                1000.0,
                commodity_code="CORN",
                commodity_family="grains_oilseeds",
                metric_code="usda_psd_domestic_use",
                measurement_kind="demand",
                unit="1000 MT",
                known_as_of="2026-08-12T16:00:00Z",
                reference_period="2026/27",
                source_url="https://official.example.test/usda/use",
            ),
        ]

        facts = build_research_facts([], history, specs, date(2026, 8, 30))

        self.assertEqual(len(facts), 1)
        fact = facts[0]
        self.assertEqual(fact["value"], 0.2)
        self.assertEqual(fact["unit"], "ratio")
        self.assertEqual(fact["observation_date"], "2026-08-12")
        self.assertEqual(fact["known_as_of"], "2026-08-12T16:00:00Z")
        self.assertEqual(fact["reference_period"], "2026/27")
        self.assertEqual(fact["formula_id"], "stock_to_use_v1")
        self.assertEqual(fact["formula_version"], "1.0.0")
        self.assertEqual(
            fact["input_record_ids"],
            ["corn-ending", "corn-use"],
        )
        self.assertEqual(
            fact["source_urls"],
            [
                "https://official.example.test/usda/ending",
                "https://official.example.test/usda/use",
            ],
        )

    def test_stock_to_use_zero_denominator_is_factually_unavailable(self):
        specs = {
            "corn_stock_to_use": FormulaSpec(
                formula_id="stock_to_use_v1",
                version="1.0.0",
                fact_kind="stock_to_use",
                output_unit="ratio",
                required_inputs=(
                    {
                        "role": "numerator",
                        "dataset": "metric_history",
                        "commodity_code": "CORN",
                        "metric_code": "usda_psd_ending_stocks",
                        "metric_role": "physical_fundamental",
                        "measurement_kind": "inventory",
                        "participant_class": None,
                    },
                    {
                        "role": "denominator",
                        "dataset": "metric_history",
                        "commodity_code": "CORN",
                        "metric_code": "usda_psd_domestic_use",
                        "metric_role": "physical_fundamental",
                        "measurement_kind": "demand",
                        "participant_class": None,
                    },
                ),
            )
        }
        common = {
            "commodity_code": "CORN",
            "commodity_family": "grains_oilseeds",
            "unit": "1000 MT",
            "known_as_of": "2026-08-12T16:00:00Z",
            "reference_period": "2026/27",
        }
        history = [
            _research_metric(
                "corn-ending",
                "2026-08-12",
                200.0,
                metric_code="usda_psd_ending_stocks",
                measurement_kind="inventory",
                **common,
            ),
            _research_metric(
                "corn-use",
                "2026-08-12",
                0.0,
                metric_code="usda_psd_domestic_use",
                measurement_kind="demand",
                **common,
            ),
        ]

        self.assertEqual(
            build_research_facts([], history, specs, date(2026, 8, 30)),
            [],
        )

    def test_stock_to_use_rejects_mixed_unit_and_mixed_usda_vintage(self):
        common = {
            "commodity_code": "CORN",
            "commodity_family": "grains_oilseeds",
            "known_as_of": "2026-08-12T16:00:00Z",
            "reference_period": "2026/27",
        }
        numerator = _research_metric(
            "corn-ending",
            "2026-08-12",
            200.0,
            metric_code="usda_psd_ending_stocks",
            measurement_kind="inventory",
            unit="1000 MT",
            **common,
        )
        denominator = _research_metric(
            "corn-use",
            "2026-08-12",
            1000.0,
            metric_code="usda_psd_domestic_use",
            measurement_kind="demand",
            unit="1000 MT",
            **common,
        )
        invalid = (
            ({**denominator, "unit": "MT"}, "mixed units"),
            (
                {
                    **denominator,
                    "known_as_of": "2026-08-19T16:00:00Z",
                },
                "USDA vintage",
            ),
        )

        for changed_denominator, message in invalid:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    build_research_facts(
                        [],
                        [numerator, changed_denominator],
                        _stock_to_use_specs(),
                        date(2026, 8, 30),
                    )

    def test_stock_to_use_requires_nonblank_usda_vintage_fields(self):
        common = {
            "commodity_code": "CORN",
            "commodity_family": "grains_oilseeds",
            "known_as_of": "2026-08-12T16:00:00Z",
            "reference_period": "2026/27",
            "unit": "1000 MT",
        }
        numerator = _research_metric(
            "corn-ending",
            "2026-08-12",
            200.0,
            metric_code="usda_psd_ending_stocks",
            measurement_kind="inventory",
            **common,
        )
        denominator = _research_metric(
            "corn-use",
            "2026-08-12",
            1000.0,
            metric_code="usda_psd_domestic_use",
            measurement_kind="demand",
            **common,
        )
        invalid = (
            (
                {**numerator, "known_as_of": None},
                {**denominator, "known_as_of": None},
            ),
            (
                {**numerator, "reference_period": ""},
                {**denominator, "reference_period": ""},
            ),
        )

        for invalid_numerator, invalid_denominator in invalid:
            with self.subTest(
                known_as_of=invalid_numerator.get("known_as_of"),
                reference_period=invalid_numerator.get("reference_period"),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "nonblank USDA vintage",
                ):
                    build_research_facts(
                        [],
                        [invalid_numerator, invalid_denominator],
                        _stock_to_use_specs(),
                        date(2026, 8, 30),
                    )

    def test_coverage_count_counts_only_configured_exact_series_window(self):
        specs = {
            "natgas_storage_coverage": FormulaSpec(
                formula_id="coverage_count_v1",
                version="1.0.0",
                fact_kind="coverage_count",
                output_unit="count",
                required_inputs=(
                    _metric_selector(trailing_observations=3),
                ),
            )
        }
        history = [
            _research_metric("storage-1", "2026-08-01", 10.0),
            _research_metric("storage-2", "2026-08-08", 20.0),
            _research_metric("storage-3", "2026-08-15", 30.0),
            _research_metric("storage-4", "2026-08-22", 40.0),
        ]

        facts = build_research_facts([], history, specs, date(2026, 8, 30))

        self.assertEqual(len(facts), 1)
        fact = facts[0]
        self.assertEqual(fact["value"], 3)
        self.assertEqual(fact["unit"], "count")
        self.assertEqual(fact["observation_date"], "2026-08-22")
        self.assertEqual(fact["known_as_of"], "2026-08-22T12:00:00Z")
        self.assertEqual(fact["reference_period"], "2026-08-08 to 2026-08-22")
        self.assertEqual(fact["formula_id"], "coverage_count_v1")
        self.assertEqual(fact["formula_version"], "1.0.0")
        self.assertEqual(
            fact["input_record_ids"],
            ["storage-2", "storage-3", "storage-4"],
        )
        self.assertEqual(
            fact["source_urls"],
            ["https://official.example.test/metrics"],
        )

    def test_freshness_age_days_uses_as_of_date_and_latest_exact_input(self):
        specs = {
            "natgas_storage_freshness": FormulaSpec(
                formula_id="freshness_age_days_v1",
                version="1.0.0",
                fact_kind="freshness_age_days",
                output_unit="days",
                required_inputs=(
                    _metric_selector(observation_count=1),
                ),
            )
        }
        history = [
            _research_metric("storage-old", "2026-08-16", 20.0),
            _research_metric("storage-latest", "2026-08-23", 25.0),
        ]

        facts = build_research_facts([], history, specs, date(2026, 8, 30))

        self.assertEqual(len(facts), 1)
        fact = facts[0]
        self.assertEqual(fact["value"], 7)
        self.assertEqual(fact["unit"], "days")
        self.assertEqual(fact["observation_date"], "2026-08-23")
        self.assertEqual(fact["known_as_of"], "2026-08-23T12:00:00Z")
        self.assertEqual(fact["reference_period"], "2026-08-23 to 2026-08-30")
        self.assertEqual(fact["formula_id"], "freshness_age_days_v1")
        self.assertEqual(fact["formula_version"], "1.0.0")
        self.assertEqual(fact["input_record_ids"], ["storage-latest"])
        self.assertEqual(
            fact["source_urls"],
            ["https://official.example.test/metrics"],
        )

    def test_fractional_second_known_as_of_orders_by_aware_instant(self):
        specs = {
            "natgas_storage_freshness": FormulaSpec(
                formula_id="freshness_age_days_v1",
                version="1.0.0",
                fact_kind="freshness_age_days",
                output_unit="days",
                required_inputs=(
                    _metric_selector(observation_count=1),
                ),
            )
        }
        history = [
            _research_metric(
                "whole-second-vintage",
                "2026-08-23",
                20.0,
                known_as_of="2026-08-29T12:00:00Z",
            ),
            _research_metric(
                "fractional-later-vintage",
                "2026-08-23",
                21.0,
                known_as_of="2026-08-29T12:00:00.900000+00:00",
            ),
        ]

        facts = build_research_facts([], history, specs, date(2026, 8, 30))

        self.assertEqual(len(facts), 1)
        self.assertEqual(
            facts[0]["input_record_ids"],
            ["fractional-later-vintage"],
        )
        self.assertEqual(
            facts[0]["known_as_of"],
            "2026-08-29T12:00:00.900000Z",
        )

    def test_missing_input_record_id_is_rejected_before_fact_emission(self):
        specs = {
            "wti_absolute_change": FormulaSpec(
                formula_id="absolute_change_v1",
                version="1.0.0",
                fact_kind="absolute_change",
                output_unit="USD/BBL",
                required_inputs=(_price_selector(observation_count=2),),
            )
        }
        orphan = _research_price("orphan", "2026-08-29", 78.0)
        del orphan["record_id"]

        with self.assertRaisesRegex(ValueError, "record_id"):
            build_research_facts(
                [
                    _research_price("price-old", "2026-08-22", 75.0),
                    orphan,
                ],
                [],
                specs,
                date(2026, 8, 30),
            )

    def test_future_input_observation_or_vintage_is_rejected(self):
        specs = {
            "wti_absolute_change": FormulaSpec(
                formula_id="absolute_change_v1",
                version="1.0.0",
                fact_kind="absolute_change",
                output_unit="USD/BBL",
                required_inputs=(_price_selector(observation_count=2),),
            )
        }
        invalid = (
            (
                _research_price("future-observation", "2026-08-31", 78.0),
                "observation_date exceeds as_of_date",
            ),
            (
                _research_price(
                    "future-vintage",
                    "2026-08-29",
                    78.0,
                    known_as_of="2026-08-31T00:00:00Z",
                ),
                "known_as_of exceeds target Sunday cutoff",
            ),
        )
        for row, message in invalid:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    build_research_facts(
                        [_research_price("price-old", "2026-08-22", 75.0), row],
                        [],
                        specs,
                        date(2026, 8, 30),
                    )

    def test_nonfinite_formula_result_is_factually_unavailable(self):
        specs = {
            "wti_absolute_change": FormulaSpec(
                formula_id="absolute_change_v1",
                version="1.0.0",
                fact_kind="absolute_change",
                output_unit="USD/BBL",
                required_inputs=(_price_selector(observation_count=2),),
            )
        }

        self.assertEqual(
            build_research_facts(
                [
                    _research_price("price-old", "2026-08-22", -1e308),
                    _research_price("price-new", "2026-08-29", 1e308),
                ],
                [],
                specs,
                date(2026, 8, 30),
            ),
            [],
        )

    def test_nonfinite_inputs_never_create_coverage_or_freshness_facts(self):
        specs = {
            "storage_coverage": FormulaSpec(
                formula_id="coverage_count_v1",
                version="1.0.0",
                fact_kind="coverage_count",
                output_unit="count",
                required_inputs=(
                    _metric_selector(trailing_observations=160),
                ),
            ),
            "storage_freshness": FormulaSpec(
                formula_id="freshness_age_days_v1",
                version="1.0.0",
                fact_kind="freshness_age_days",
                output_unit="days",
                required_inputs=(
                    _metric_selector(observation_count=1),
                ),
            ),
        }

        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value):
                self.assertEqual(
                    build_research_facts(
                        [],
                        [_research_metric("nonfinite", "2026-08-23", value)],
                        specs,
                        date(2026, 8, 30),
                    ),
                    [],
                )

    def test_nonnumeric_input_is_a_schema_violation(self):
        specs = {
            "storage_coverage": FormulaSpec(
                formula_id="coverage_count_v1",
                version="1.0.0",
                fact_kind="coverage_count",
                output_unit="count",
                required_inputs=(
                    _metric_selector(trailing_observations=160),
                ),
            )
        }

        with self.assertRaisesRegex(ValueError, "value must be numeric"):
            build_research_facts(
                [],
                [_research_metric("not-numeric", "2026-08-23", "missing")],
                specs,
                date(2026, 8, 30),
            )

    def test_duplicate_normalized_fact_identity_is_rejected(self):
        spec = FormulaSpec(
            formula_id="absolute_change_v1",
            version="1.0.0",
            fact_kind="absolute_change",
            output_unit="USD/BBL",
            required_inputs=(_price_selector(observation_count=2),),
        )

        with self.assertRaisesRegex(
            ValueError,
            "Duplicate commodity research fact identity",
        ):
            build_research_facts(
                [
                    _research_price("price-old", "2026-08-22", 75.0),
                    _research_price("price-new", "2026-08-29", 78.0),
                ],
                [],
                {"duplicate_fact": spec, " duplicate_fact ": spec},
                date(2026, 8, 30),
            )

    def test_unregistered_formula_or_version_is_rejected(self):
        invalid = (
            FormulaSpec(
                formula_id="bullish_composite_v1",
                version="1.0.0",
                fact_kind="composite",
                output_unit="score",
                required_inputs=(_price_selector(observation_count=2),),
            ),
            FormulaSpec(
                formula_id="absolute_change_v1",
                version="2.0.0",
                fact_kind="absolute_change",
                output_unit="USD/BBL",
                required_inputs=(_price_selector(observation_count=2),),
            ),
        )
        for spec in invalid:
            with self.subTest(formula_id=spec.formula_id, version=spec.version):
                with self.assertRaisesRegex(ValueError, "Unregistered formula"):
                    build_research_facts(
                        [],
                        [],
                        {"invalid": spec},
                        date(2026, 8, 30),
                    )

    def test_dispatch_rejects_prefix_label_and_hidden_defaults(self):
        base = {
            "role": "series",
            "dataset": "price_history",
            "commodity_code": "WTI",
            "series_code": "WTI",
            "observation_count": 2,
        }
        prefix_spec = FormulaSpec(
            formula_id="absolute_change_v1",
            version="1.0.0",
            fact_kind="absolute_change",
            output_unit="USD/BBL",
            required_inputs=(base,),
        )
        history = [
            _research_price("price-old", "2026-08-22", 75.0),
            _research_price("price-new", "2026-08-29", 78.0),
        ]
        self.assertEqual(
            build_research_facts(
                history,
                [],
                {"prefix_not_selected": prefix_spec},
                date(2026, 8, 30),
            ),
            [],
        )

        invalid_selectors = (
            {**base, "series_code": "WTI_CASH", "label": "WTI cash"},
            {key: value for key, value in base.items() if key != "observation_count"},
        )
        for selector in invalid_selectors:
            with self.subTest(selector=selector):
                spec = FormulaSpec(
                    formula_id="absolute_change_v1",
                    version="1.0.0",
                    fact_kind="absolute_change",
                    output_unit="USD/BBL",
                    required_inputs=(selector,),
                )
                with self.assertRaisesRegex(ValueError, "exact price identity"):
                    build_research_facts(
                        history,
                        [],
                        {"invalid_dispatch": spec},
                        date(2026, 8, 30),
                    )


class WeeklyContextResearchFactTests(unittest.TestCase):
    def test_context_cli_uses_current_staged_macro_price_history_for_wti_facts(self):
        from pipeline.internal.scripts import fetch_weekly_context as fetch_module

        with TemporaryDirectory() as directory:
            root = Path(directory)
            context_output = root / "capital_weekly_context_20260830"
            macro_output = root / "capital_weekly_macro_assets_python_20260830"
            macro_output.mkdir()
            rows = [
                {
                    **_research_price("wti-prior-year", "2025-08-29", 70.0),
                    "series_code": "WTI",
                    "unit": "$/BBL",
                },
                {
                    **_research_price("wti-prior", "2026-08-22", 75.0),
                    "series_code": "WTI",
                    "unit": "$/BBL",
                },
                {
                    **_research_price("wti-current", "2026-08-29", 78.0),
                    "series_code": "WTI",
                    "unit": "$/BBL",
                },
            ]
            with (macro_output / "commodity_price_history.csv").open(
                "w", newline="", encoding="utf-8"
            ) as file:
                writer = csv.DictWriter(file, fieldnames=PRICE_HISTORY_FIELDS)
                writer.writeheader()
                writer.writerows(rows)

            argv = [
                "fetch_weekly_context.py",
                "--output-dir",
                str(context_output),
                "--start-date",
                "2026-08-24",
                "--end-date",
                "2026-08-30",
                "--no-raw-cache",
            ]
            with patch.object(fetch_module, "build_default_providers", return_value={}), patch(
                "sys.argv", argv
            ):
                fetch_module.main()

            snapshot = json.loads(
                (context_output / "weekly_context_snapshot.json").read_text(
                    encoding="utf-8"
                )
            )
            facts = snapshot["commodity_research_facts"]
            self.assertEqual(
                [fact["fact_code"] for fact in facts],
                [
                    "wti_absolute_change",
                    "wti_percentage_change",
                    "wti_year_over_year_change",
                ],
            )
            self.assertEqual(
                [fact["value"] for fact in facts],
                [3.0, 4.0, 8.0],
            )
            self.assertEqual(
                facts[0]["input_record_ids"],
                ["wti-current", "wti-prior"],
            )

    def test_runner_and_publisher_add_registered_research_facts_csv(self):
        as_of = date(2026, 8, 30)
        raw_row = _metric_row(
            date(2026, 8, 23),
            value=100.0,
            known_as_of="2026-08-23T12:00:00+00:00",
        )
        provider = ContextProvider(
            ProviderSpec(
                name="official_storage",
                category="commodity_fundamentals",
                source_tier="public",
                requiredness="required",
                provider_version="1.0.0",
                schema_version="commodity-v2",
                frequency="weekly",
                freshness_days=10,
            ),
            lambda: ProviderResult(
                category="commodity_fundamentals",
                rows=[raw_row],
                raw_text="official fixture",
                source="Official fixture",
                source_url="https://official.example.test/metric",
            ),
        )
        formula_specs = {
            "storage_coverage": FormulaSpec(
                formula_id="coverage_count_v1",
                version="1.0.0",
                fact_kind="coverage_count",
                output_unit="count",
                required_inputs=(
                    {
                        "role": "series",
                        "dataset": "metric_history",
                        "commodity_code": "NATGAS_HH",
                        "metric_code": "stocks",
                        "metric_role": "physical_fundamental",
                        "measurement_kind": "inventory",
                        "participant_class": None,
                        "trailing_observations": 160,
                    },
                ),
            ),
            "storage_freshness": FormulaSpec(
                formula_id="freshness_age_days_v1",
                version="1.0.0",
                fact_kind="freshness_age_days",
                output_unit="days",
                required_inputs=(
                    {
                        "role": "series",
                        "dataset": "metric_history",
                        "commodity_code": "NATGAS_HH",
                        "metric_code": "stocks",
                        "metric_role": "physical_fundamental",
                        "measurement_kind": "inventory",
                        "participant_class": None,
                        "observation_count": 1,
                    },
                ),
            ),
        }

        tables = run_weekly_context(
            {"official_storage": provider},
            as_of_date=as_of,
            history_limits=LIMITS,
            commodity_registry=REGISTRY,
            formula_specs=formula_specs,
        )

        self.assertEqual(
            [row["fact_code"] for row in tables["commodity_research_facts"]],
            ["storage_coverage", "storage_freshness"],
        )
        self.assertEqual(
            [row["value"] for row in tables["commodity_research_facts"]],
            [1, 7],
        )
        self.assertEqual(
            CATEGORY_FILES["commodity_research_facts"],
            "commodity_research_facts.csv",
        )

        with TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            publish_weekly_context_bundle(tables, output)

            with (output / "commodity_research_facts.csv").open(
                newline="", encoding="utf-8"
            ) as file:
                self.assertEqual(
                    next(csv.reader(file)),
                    list(CATEGORY_FIELDS["commodity_research_facts"]),
                )
            snapshot = json.loads(
                (output / "weekly_context_snapshot.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                len(snapshot["commodity_research_facts"]),
                2,
            )


if __name__ == "__main__":
    unittest.main()
