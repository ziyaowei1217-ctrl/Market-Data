from datetime import date
import unittest

from pipeline.capital_weekly.returns import (
    TimePoint,
    calculate_macro_snapshot,
    calculate_return_snapshot,
)


class ReturnSnapshotTests(unittest.TestCase):
    def test_bp_change_allows_zero_base_yield(self):
        history = [
            {"date": "2025-12-31", "value": 0.00},
            {"date": "2026-07-07", "value": 0.15},
        ]

        result = calculate_macro_snapshot(history, "bp")

        self.assertAlmostEqual(result.daily_change, 15.0)
        self.assertAlmostEqual(result.weekly_change, 15.0)
        self.assertAlmostEqual(result.mtd_change, 15.0)
        self.assertAlmostEqual(result.ytd_change, 15.0)

    def test_macro_snapshot_rejects_unknown_change_unit(self):
        history = [
            {"date": "2025-12-31", "value": 100.0},
            {"date": "2026-07-07", "value": 105.0},
        ]

        with self.assertRaisesRegex(ValueError, "Unsupported change unit"):
            calculate_macro_snapshot(history, "points")  # type: ignore[arg-type]

    def test_macro_snapshot_reports_same_base_yield_move_in_basis_points(self):
        history = [
            {"date": "2025-12-31", "value": 4.10},
            {"date": "2026-07-07", "value": 4.25},
        ]

        result = calculate_macro_snapshot(history, "bp")

        self.assertAlmostEqual(result.daily_change, 15.0)
        self.assertAlmostEqual(result.weekly_change, 15.0)
        self.assertAlmostEqual(result.mtd_change, 15.0)
        self.assertAlmostEqual(result.ytd_change, 15.0)

    def test_macro_snapshot_reports_commodity_move_as_decimal_percent_return(self):
        history = [
            {"date": "2025-12-31", "value": 100.0},
            {"date": "2026-07-07", "value": 105.0},
        ]

        result = calculate_macro_snapshot(history, "pct")

        self.assertAlmostEqual(result.daily_change, 0.05)

    def test_macro_weekly_base_is_last_observation_on_or_before_seven_days_ago(self):
        history = [
            {"date": "2025-12-31", "value": 90.0},
            {"date": "2026-07-01", "value": 100.0},
            {"date": "2026-07-03", "value": 102.0},
            {"date": "2026-07-08", "value": 105.0},
        ]

        macro = calculate_macro_snapshot(history, "pct")
        default = calculate_return_snapshot(history, "pct")

        self.assertEqual(macro.weekly_base_date, date(2026, 7, 1))
        self.assertAlmostEqual(macro.weekly_change, 0.05)
        self.assertEqual(default.weekly_base_date, date(2026, 7, 3))

    def test_calculates_daily_weekly_mtd_and_ytd_percent_changes(self):
        points = [
            TimePoint(date(2025, 12, 31), 80.0),
            TimePoint(date(2026, 6, 30), 90.0),
            TimePoint(date(2026, 7, 3), 100.0),
            TimePoint(date(2026, 7, 6), 102.0),
            TimePoint(date(2026, 7, 7), 105.0),
        ]

        result = calculate_return_snapshot(points, "pct")

        self.assertEqual(result.latest_date, date(2026, 7, 7))
        self.assertAlmostEqual(result.daily_change, 105.0 / 102.0 - 1)
        self.assertAlmostEqual(result.weekly_change, 105.0 / 100.0 - 1)
        self.assertAlmostEqual(result.mtd_change, 105.0 / 90.0 - 1)
        self.assertAlmostEqual(result.ytd_change, 105.0 / 80.0 - 1)
        self.assertEqual(result.daily_base_value, 102.0)
        self.assertEqual(result.weekly_base_value, 100.0)
        self.assertEqual(result.mtd_base_value, 90.0)
        self.assertEqual(result.ytd_base_value, 80.0)
        self.assertEqual(result.daily_base_date, date(2026, 7, 6))
        self.assertEqual(result.weekly_base_date, date(2026, 7, 3))
        self.assertEqual(result.mtd_base_date, date(2026, 6, 30))
        self.assertEqual(result.ytd_base_date, date(2025, 12, 31))
        self.assertEqual(result.qc_flag, "OK")

    def test_bp_change_mode_assumes_percent_point_inputs(self):
        points = [
            TimePoint(date(2025, 12, 31), 4.0),
            TimePoint(date(2026, 6, 30), 4.1),
            TimePoint(date(2026, 7, 3), 4.2),
            TimePoint(date(2026, 7, 6), 4.25),
            TimePoint(date(2026, 7, 7), 4.3),
        ]

        result = calculate_return_snapshot(points, "bp")

        self.assertAlmostEqual(result.daily_change, 5.0)
        self.assertAlmostEqual(result.weekly_change, 10.0)
        self.assertAlmostEqual(result.mtd_change, 20.0)
        self.assertAlmostEqual(result.ytd_change, 30.0)
        self.assertEqual(result.change_unit, "bp")
        self.assertEqual(result.weekly_base_value, 4.2)
        self.assertEqual(result.mtd_base_value, 4.1)
        self.assertEqual(result.ytd_base_value, 4.0)

    def test_missing_base_dates_are_flagged(self):
        points = [
            TimePoint(date(2026, 7, 6), 100.0),
            TimePoint(date(2026, 7, 7), 101.0),
        ]

        result = calculate_return_snapshot(points, "pct")

        self.assertEqual(
            result.qc_flag,
            "missing_weekly_base;missing_mtd_base;missing_ytd_base",
        )
        self.assertIsNone(result.weekly_change)
        self.assertIsNone(result.mtd_change)
        self.assertIsNone(result.ytd_change)
        self.assertIsNone(result.weekly_base_value)
        self.assertIsNone(result.mtd_base_value)
        self.assertIsNone(result.ytd_base_value)


if __name__ == "__main__":
    unittest.main()
