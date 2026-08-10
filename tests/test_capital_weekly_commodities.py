import json
import unittest

from capital_weekly.context.commodities import (
    calculate_weekly_change,
    eia_not_configured_result,
    parse_eia_series,
)


class CommodityFundamentalTests(unittest.TestCase):
    def test_eia_parser_validates_units_and_orders_periods(self):
        payload = {
            "response": {
                "data": [
                    {
                        "period": "2026-07-24",
                        "value": "425000",
                        "series-description": "U.S. Ending Stocks of Crude Oil",
                        "unit": "Thousand Barrels",
                    },
                    {
                        "period": "2026-07-17",
                        "value": "420000",
                        "series-description": "U.S. Ending Stocks of Crude Oil",
                        "unit": "Thousand Barrels",
                    },
                ]
            }
        }

        rows = parse_eia_series(
            json.dumps(payload),
            metric_code="eia_crude_stocks",
            expected_unit="Thousand Barrels",
        )

        self.assertEqual([row["period"] for row in rows], ["2026-07-17", "2026-07-24"])
        self.assertEqual(rows[-1]["value"], 425000.0)
        self.assertEqual(rows[-1]["unit"], "Thousand Barrels")

    def test_eia_parser_rejects_unexpected_units_and_duplicate_periods(self):
        wrong_unit = {
            "response": {
                "data": [
                    {"period": "2026-07-24", "value": "1", "unit": "Percent"}
                ]
            }
        }
        with self.assertRaisesRegex(ValueError, "unit"):
            parse_eia_series(
                json.dumps(wrong_unit),
                metric_code="stocks",
                expected_unit="Thousand Barrels",
            )

        duplicate = {
            "response": {
                "data": [
                    {"period": "2026-07-24", "value": "1", "unit": "Barrels"},
                    {"period": "2026-07-24", "value": "2", "unit": "Barrels"},
                ]
            }
        }
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            parse_eia_series(
                json.dumps(duplicate),
                metric_code="stocks",
                expected_unit="Barrels",
            )

    def test_weekly_change_uses_latest_two_observations(self):
        rows = [
            {"period": "2026-07-10", "value": 100.0},
            {"period": "2026-07-17", "value": 110.0},
            {"period": "2026-07-24", "value": 107.0},
        ]

        result = calculate_weekly_change(rows)

        self.assertEqual(result["period"], "2026-07-24")
        self.assertEqual(result["change"], -3.0)
        self.assertAlmostEqual(result["change_pct"], -3 / 110)

    def test_missing_eia_key_is_visible_not_configured_status(self):
        result = eia_not_configured_result()

        self.assertEqual(result.category, "commodity_fundamentals")
        self.assertEqual(result.status, "NOT_CONFIGURED")
        self.assertEqual(result.rows, [])
        self.assertIn("EIA_API_KEY", result.notes)


if __name__ == "__main__":
    unittest.main()
