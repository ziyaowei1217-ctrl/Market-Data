from datetime import date
import math
import unittest

from pipeline.internal.capital_weekly.context.economic_releases import (
    ECONOMIC_RELEASE_FIELDS,
    annualized_three_month_change,
    build_release_row,
    derive_ism_rows,
    derive_price_index_rows,
    derive_real_gdp_rows,
    derive_retail_sales_rows,
    normalize_economic_release_rows,
    percent_change,
    select_latest_vintages,
)


def release_row(
    indicator_code: str,
    observation_period: str,
    value: float,
    known_as_of: str,
    vintage_date: str = "initial",
) -> dict:
    return build_release_row(
        indicator_code=indicator_code,
        observation_period=observation_period,
        release_at_bjt="2026-08-07T20:30:00+08:00",
        value=value,
        unit="index",
        frequency="monthly",
        source="Official fixture",
        source_url="https://example.test/economic-release",
        known_as_of=known_as_of,
        as_of_date=date(2026, 8, 9),
        vintage_date=vintage_date,
    )


class EconomicReleaseTests(unittest.TestCase):
    def test_schema_has_the_public_release_contract_columns(self):
        self.assertEqual(
            ECONOMIC_RELEASE_FIELDS,
            (
                "record_id", "indicator_code", "indicator_name", "observation_period",
                "release_at_bjt", "vintage_date", "as_of_date", "known_as_of",
                "value", "previous_value", "revised_previous", "consensus_value",
                "surprise_value", "unit", "frequency", "seasonal_adjustment",
                "calculation_id", "formula_version", "input_record_ids", "source",
                "source_url", "source_tier", "qc_flag",
            ),
        )

    def test_revision_after_sunday_cannot_replace_the_eligible_vintage(self):
        rows = [
            release_row("CPI_INDEX_SA", "2026-06", 326.1, "2026-07-14T08:30:00-04:00", "v1"),
            release_row("CPI_INDEX_SA", "2026-06", 326.4, "2026-08-10T08:30:00-04:00", "v2"),
        ]

        selected = select_latest_vintages(rows, date(2026, 8, 9))

        self.assertEqual(selected[0]["value"], 326.1)
        self.assertEqual(selected[0]["vintage_date"], "v1")

    def test_absent_consensus_keeps_consensus_and_surprise_null(self):
        row = build_release_row(
            indicator_code="NFP_CHANGE",
            observation_period="2026-07",
            release_at_bjt="2026-08-07T20:30:00+08:00",
            value=125000.0,
            unit="persons",
            frequency="monthly",
            source="U.S. Bureau of Labor Statistics",
            source_url="https://www.bls.gov/news.release/",
            known_as_of="2026-08-07T08:30:00-04:00",
            as_of_date=date(2026, 8, 9),
        )

        self.assertIsNone(row["consensus_value"])
        self.assertIsNone(row["surprise_value"])

    def test_price_index_calculations_use_literal_monthly_bases(self):
        rows = [
            release_row("CPI_INDEX_SA", "2025-06", 300.0, "2026-07-14T08:30:00-04:00"),
            release_row("CPI_INDEX_SA", "2026-03", 318.0, "2026-07-14T08:30:00-04:00"),
            release_row("CPI_INDEX_SA", "2026-05", 324.0, "2026-07-14T08:30:00-04:00"),
            release_row("CPI_INDEX_SA", "2026-06", 326.1, "2026-07-14T08:30:00-04:00"),
        ]

        derived = derive_price_index_rows(rows, "CPI_INDEX_SA")
        values = {row["indicator_code"]: row["value"] for row in derived}

        self.assertAlmostEqual(values["CPI_INDEX_SA_MOM_PCT"], 0.648148148148, places=10)
        self.assertAlmostEqual(values["CPI_INDEX_SA_YOY_PCT"], 8.7, places=10)
        self.assertAlmostEqual(values["CPI_INDEX_SA_3M_ANN_PCT"], 10.584616273789, places=10)
        self._assert_derived_metadata(derived)

    def test_price_index_calculations_apply_equally_to_pce(self):
        rows = [
            release_row("PCE_PRICE_INDEX", "2025-06", 120.0, "2026-07-31T08:30:00-04:00"),
            release_row("PCE_PRICE_INDEX", "2026-03", 124.0, "2026-07-31T08:30:00-04:00"),
            release_row("PCE_PRICE_INDEX", "2026-05", 125.0, "2026-07-31T08:30:00-04:00"),
            release_row("PCE_PRICE_INDEX", "2026-06", 126.0, "2026-07-31T08:30:00-04:00"),
        ]

        derived = derive_price_index_rows(rows, "PCE_PRICE_INDEX")
        values = {row["indicator_code"]: row["value"] for row in derived}

        self.assertAlmostEqual(values["PCE_PRICE_INDEX_MOM_PCT"], 0.8, places=10)
        self.assertAlmostEqual(values["PCE_PRICE_INDEX_YOY_PCT"], 5.0, places=10)
        self.assertAlmostEqual(values["PCE_PRICE_INDEX_3M_ANN_PCT"], 6.609385438988, places=10)
        self._assert_derived_metadata(derived)

    def test_post_sunday_base_cannot_contribute_to_an_eligible_price_derived_row(self):
        rows = [
            release_row("CPI_INDEX_SA", "2026-05", 324.0, "2026-08-10T08:30:00-04:00"),
            release_row("CPI_INDEX_SA", "2026-06", 326.1, "2026-07-14T08:30:00-04:00"),
        ]

        derived = derive_price_index_rows(rows, "CPI_INDEX_SA")

        self.assertEqual(select_latest_vintages(derived, date(2026, 8, 9)), [])


    def test_real_gdp_calculations_use_literal_quarterly_bases(self):
        rows = [
            release_row("REAL_GDP_INDEX_SAAR", "2025-Q2", 22000.0, "2026-07-30T08:30:00-04:00"),
            release_row("REAL_GDP_INDEX_SAAR", "2026-Q1", 23000.0, "2026-07-30T08:30:00-04:00"),
            release_row("REAL_GDP_INDEX_SAAR", "2026-Q2", 23230.0, "2026-07-30T08:30:00-04:00"),
        ]

        derived = derive_real_gdp_rows(rows)
        values = {row["indicator_code"]: row["value"] for row in derived}

        self.assertAlmostEqual(values["REAL_GDP_QOQ_SAAR"], 4.060401, places=6)
        self.assertAlmostEqual(values["REAL_GDP_YOY_PCT"], 5.590909090909, places=10)
        self._assert_derived_metadata(derived)

    def test_ism_distance_is_reported_without_regime_commentary(self):
        rows = derive_ism_rows(
            build_release_row(
                indicator_code="ISM_MANUFACTURING_PMI",
                observation_period="2026-07",
                release_at_bjt="2026-08-03T22:00:00+08:00",
                value=48.7,
                unit="index",
                frequency="monthly",
                source="Institute for Supply Management",
                source_url="https://www.ismworld.org/",
                known_as_of="2026-08-03T10:00:00-04:00",
                as_of_date=date(2026, 8, 9),
            )
        )

        self.assertEqual(
            {row["indicator_code"]: row["value"] for row in rows},
            {"ISM_MANUFACTURING_PMI": 48.7, "ISM_MANUFACTURING_DISTANCE_50": -1.3},
        )
        self._assert_derived_metadata([rows[1]])

    def test_retail_sales_yoy_uses_release_specific_level_inputs(self):
        rows = [
            release_row("RETAIL_SALES_LEVEL_SA", "2025-06", 700000.0, "2026-07-15T08:30:00-04:00"),
            release_row("RETAIL_SALES_LEVEL_SA", "2026-06", 735000.0, "2026-07-15T08:30:00-04:00"),
        ]

        derived = derive_retail_sales_rows(rows)

        self.assertEqual(len(derived), 1)
        self.assertEqual(derived[0]["indicator_code"], "RETAIL_SALES_YOY_PCT")
        self.assertAlmostEqual(derived[0]["value"], 5.0, places=12)
        self._assert_derived_metadata(derived)

    def test_validator_rejects_forged_or_mutated_record_ids(self):
        row = release_row("CPI_INDEX_SA", "2026-06", 326.1, "2026-07-14T08:30:00-04:00")

        with self.assertRaisesRegex(ValueError, "record_id does not match"):
            normalize_economic_release_rows([{**row, "record_id": "forged"}])
        with self.assertRaisesRegex(ValueError, "record_id does not match"):
            normalize_economic_release_rows([{**row, "observation_period": "2026-07"}])

    def test_validator_enforces_observed_and_calculated_provenance_contracts(self):
        observed = release_row("CPI_INDEX_SA", "2026-06", 326.1, "2026-07-14T08:30:00-04:00")
        derived = derive_price_index_rows(
            [
                release_row("CPI_INDEX_SA", "2026-05", 324.0, "2026-07-14T08:30:00-04:00"),
                observed,
            ],
            "CPI_INDEX_SA",
        )[0]

        with self.assertRaisesRegex(ValueError, "observed rows must use source-v1"):
            normalize_economic_release_rows([{**observed, "formula_version": "economic-v1"}])
        with self.assertRaisesRegex(ValueError, "observed rows must not declare input_record_ids"):
            normalize_economic_release_rows([{**observed, "input_record_ids": "input"}])
        with self.assertRaisesRegex(ValueError, "economic-v1"):
            normalize_economic_release_rows([{**derived, "formula_version": "source-v1"}])
        with self.assertRaisesRegex(ValueError, "exactly 2 input_record_ids"):
            normalize_economic_release_rows([{**derived, "input_record_ids": "one"}])
        with self.assertRaisesRegex(ValueError, "consensus_value must be null"):
            normalize_economic_release_rows([{**observed, "consensus_value": 3.0}])
        with self.assertRaisesRegex(ValueError, "surprise_value must be null"):
            normalize_economic_release_rows([{**observed, "surprise_value": 1.0}])

    def test_validator_rejects_nonfinite_duplicate_unknown_naive_and_nonpublic_rows(self):
        row = release_row("CPI_INDEX_SA", "2026-06", 326.1, "2026-07-14T08:30:00-04:00")

        with self.assertRaisesRegex(ValueError, "non-finite"):
            normalize_economic_release_rows([{**row, "value": math.inf}])
        with self.assertRaisesRegex(ValueError, "Duplicate economic release record_id"):
            normalize_economic_release_rows([row, dict(row)])
        with self.assertRaisesRegex(ValueError, "Unknown economic calculation_id"):
            normalize_economic_release_rows([{**row, "calculation_id": "unregistered"}])
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            normalize_economic_release_rows(
                [{**row, "known_as_of": "2026-07-14T08:30:00"}]
            )
        with self.assertRaisesRegex(ValueError, "public"):
            normalize_economic_release_rows([{**row, "source_tier": "licensed"}])

    def test_percent_helpers_reject_invalid_bases(self):
        self.assertAlmostEqual(percent_change(126.0, 120.0), 5.0, places=12)
        self.assertAlmostEqual(
            annualized_three_month_change(126.0, 120.0), 21.550625, places=12
        )
        with self.assertRaisesRegex(ValueError, "base cannot be zero"):
            percent_change(1.0, 0.0)
        with self.assertRaisesRegex(ValueError, "must be positive"):
            annualized_three_month_change(0.0, 1.0)

    def _assert_derived_metadata(self, rows: list[dict]) -> None:
        for row in rows:
            self.assertNotEqual(row["calculation_id"], "observed")
            self.assertEqual(row["formula_version"], "economic-v1")
            self.assertIn("|", row["input_record_ids"])


if __name__ == "__main__":
    unittest.main()
