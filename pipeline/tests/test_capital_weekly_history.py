from datetime import date
import unittest

import pandas as pd

from pipeline.capital_weekly.history import truncate_history_as_of


class HistoryCutoffTests(unittest.TestCase):
    def test_truncates_rows_after_as_of_and_preserves_attributes(self):
        history = pd.DataFrame(
            {
                "date": [date(2026, 8, 7), date(2026, 8, 10)],
                "close": [100.0, 110.0],
            }
        )
        history.attrs["provider_note"] = "kept"

        result = truncate_history_as_of(history, date(2026, 8, 9))

        self.assertEqual(result["date"].tolist(), [date(2026, 8, 7)])
        self.assertEqual(result.attrs["provider_note"], "kept")

    def test_none_cutoff_returns_an_independent_copy(self):
        history = pd.DataFrame({"date": [date(2026, 8, 10)], "close": [110.0]})

        result = truncate_history_as_of(history, None)

        self.assertIsNot(result, history)
        self.assertEqual(result.to_dict("records"), history.to_dict("records"))


if __name__ == "__main__":
    unittest.main()
