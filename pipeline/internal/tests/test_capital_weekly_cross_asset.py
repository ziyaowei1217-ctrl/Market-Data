from datetime import date, timedelta
import math
import unittest

from pipeline.internal.capital_weekly.cross_asset import rolling_correlation_history


class CrossAssetCorrelationTests(unittest.TestCase):
    @staticmethod
    def _history(values, *, start=date(2026, 8, 1)):
        return [
            {"date": start + timedelta(days=index), "value": value}
            for index, value in enumerate(values)
        ]

    def test_mixed_price_return_and_level_change_produce_matched_correlation(self):
        histories = {
            "LEFT": self._history([100.0, 110.0, 99.0, 108.9, 98.01, 107.811]),
            "RIGHT": self._history([4.0, 4.1, 4.0, 4.1, 4.0, 4.1]),
        }

        result = rolling_correlation_history(
            histories,
            "LEFT",
            "RIGHT",
            "pct_return",
            "level_change",
            window=5,
            minimum_observations=4,
        )

        self.assertEqual(result[-1]["date"], date(2026, 8, 6))
        self.assertAlmostEqual(result[-1]["value"], 1.0)
        self.assertEqual(result[-1]["observations"], 5)

    def test_inner_join_excludes_a_transformed_date_missing_from_one_input(self):
        histories = {
            "LEFT": self._history([100.0, 110.0, 99.0, 108.9, 98.01, 107.811]),
            "RIGHT": [
                point
                for point in self._history([4.0, 4.1, 4.0, 4.1, 4.0, 4.1])
                if point["date"] != date(2026, 8, 4)
            ],
        }

        result = rolling_correlation_history(
            histories,
            "LEFT",
            "RIGHT",
            "pct_return",
            "level_change",
            window=4,
            minimum_observations=3,
        )

        self.assertNotIn(date(2026, 8, 4), [point["date"] for point in result])
        self.assertEqual(result[-1]["observations"], 4)

    def test_no_output_is_emitted_before_minimum_observation_count(self):
        histories = {
            "LEFT": self._history([100.0, 101.0, 99.0, 102.0]),
            "RIGHT": self._history([4.0, 4.1, 4.0, 4.2]),
        }

        result = rolling_correlation_history(
            histories,
            "LEFT",
            "RIGHT",
            "pct_return",
            "level_change",
            window=5,
            minimum_observations=4,
        )

        self.assertEqual(result, [])

    def test_non_finite_input_is_rejected(self):
        histories = {
            "LEFT": self._history([100.0, math.inf, 102.0]),
            "RIGHT": self._history([4.0, 4.1, 4.2]),
        }

        with self.assertRaisesRegex(ValueError, "finite"):
            rolling_correlation_history(
                histories,
                "LEFT",
                "RIGHT",
                "pct_return",
                "level_change",
                window=2,
                minimum_observations=2,
            )

    def test_zero_variance_eligible_window_is_rejected(self):
        histories = {
            "LEFT": self._history([100.0, 110.0, 121.0, 133.1]),
            "RIGHT": self._history([4.0, 4.1, 4.0, 4.2]),
        }

        with self.assertRaisesRegex(ValueError, "zero variance"):
            rolling_correlation_history(
                histories,
                "LEFT",
                "RIGHT",
                "pct_return",
                "level_change",
                window=3,
                minimum_observations=3,
            )


if __name__ == "__main__":
    unittest.main()
