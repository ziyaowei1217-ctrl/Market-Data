from datetime import date
import unittest

from capital_weekly.context.financial_conditions import (
    calculate_financial_conditions,
    parse_fred_components_csv,
)


class FinancialConditionTests(unittest.TestCase):
    def test_composite_standardizes_direction_and_classifies_tightening(self):
        components = [
            {
                "metric_code": "vix",
                "value": 30.0,
                "mean": 20.0,
                "std": 5.0,
                "risk_direction": 1,
                "as_of_date": date(2026, 7, 24),
            },
            {
                "metric_code": "equity",
                "value": 90.0,
                "mean": 100.0,
                "std": 10.0,
                "risk_direction": -1,
                "as_of_date": date(2026, 7, 24),
            },
        ]

        result = calculate_financial_conditions(
            components,
            expected_components=2,
            expected_end=date(2026, 7, 26),
        )

        self.assertEqual(result["coverage"], 1.0)
        self.assertEqual(result["score"], 1.5)
        self.assertEqual(result["regime"], "tightening")
        self.assertEqual(result["qc_flag"], "OK")

    def test_low_coverage_is_insufficient_instead_of_silent_renormalization(self):
        components = [
            {
                "metric_code": "vix",
                "value": 20,
                "mean": 20,
                "std": 5,
                "risk_direction": 1,
                "as_of_date": date(2026, 7, 24),
            }
        ]

        result = calculate_financial_conditions(
            components,
            expected_components=4,
            minimum_coverage=0.75,
            expected_end=date(2026, 7, 26),
        )

        self.assertIsNone(result["score"])
        self.assertEqual(result["coverage"], 0.25)
        self.assertEqual(result["regime"], "insufficient_data")
        self.assertEqual(result["qc_flag"], "INSUFFICIENT_DATA")

    def test_stale_components_are_excluded_from_coverage(self):
        components = [
            {
                "metric_code": "vix",
                "value": 20,
                "mean": 20,
                "std": 5,
                "risk_direction": 1,
                "as_of_date": date(2026, 7, 10),
            }
        ]

        result = calculate_financial_conditions(
            components,
            expected_components=1,
            expected_end=date(2026, 7, 26),
            max_lag_days=5,
        )

        self.assertEqual(result["excluded"]["vix"], "STALE")
        self.assertEqual(result["qc_flag"], "INSUFFICIENT_DATA")

    def test_zero_standard_deviation_component_is_excluded(self):
        components = [
            {
                "metric_code": "flat",
                "value": 20,
                "mean": 20,
                "std": 0,
                "risk_direction": 1,
                "as_of_date": date(2026, 7, 24),
            }
        ]

        result = calculate_financial_conditions(
            components,
            expected_components=1,
            expected_end=date(2026, 7, 26),
        )

        self.assertEqual(result["excluded"]["flat"], "INVALID_STD")
        self.assertEqual(result["coverage"], 0.0)

    def test_fred_csv_builds_observed_component_statistics(self):
        text = (
            "DATE,VIXCLS,SP500\n"
            "2026-07-20,20,100\n"
            "2026-07-21,22,110\n"
            "2026-07-24,24,121\n"
        )
        config = [
            {"metric_code": "vix", "series_id": "VIXCLS", "risk_direction": 1},
            {"metric_code": "equity", "series_id": "SP500", "risk_direction": -1},
        ]

        rows = parse_fred_components_csv(
            text,
            config,
            expected_end=date(2026, 7, 26),
            minimum_observations=3,
        )

        self.assertEqual(rows[0]["as_of_date"], date(2026, 7, 24))
        self.assertEqual(rows[0]["value"], 24.0)
        self.assertEqual(rows[0]["mean"], 22.0)
        self.assertEqual(rows[0]["std"], 2.0)
        self.assertEqual(rows[1]["risk_direction"], -1)

    def test_fred_csv_accepts_current_observation_date_header(self):
        text = (
            "observation_date,VIXCLS\n"
            "2026-07-20,20\n"
            "2026-07-21,22\n"
            "2026-07-24,24\n"
        )

        rows = parse_fred_components_csv(
            text,
            [{"metric_code": "vix", "series_id": "VIXCLS", "risk_direction": 1}],
            expected_end=date(2026, 7, 26),
            minimum_observations=3,
        )

        self.assertEqual(rows[0]["value"], 24.0)


if __name__ == "__main__":
    unittest.main()
