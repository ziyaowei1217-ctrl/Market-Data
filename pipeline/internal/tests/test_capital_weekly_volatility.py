from datetime import date
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from pipeline.internal.capital_weekly.context.volatility import (
    YahooVolatilitySeries,
    calculate_yahoo_volatility_metrics,
    extract_yahoo_close_histories,
    load_yahoo_volatility_config,
    serialize_yahoo_close_histories,
)


CONFIG = (
    (
        "vix_9d_level",
        "Cboe S&P 500 9-Day Volatility Index",
        "^VIX9D",
        "index_points",
        "vix_9d",
    ),
    (
        "vix_1m_level",
        "Cboe VIX 30-Day Volatility Index",
        "^VIX",
        "index_points",
        "vix_1m",
    ),
    (
        "vix_3m_level",
        "Cboe S&P 500 3-Month Volatility Index",
        "^VIX3M",
        "index_points",
        "vix_3m",
    ),
    (
        "vix_6m_level",
        "Cboe S&P 500 6-Month Volatility Index",
        "^VIX6M",
        "index_points",
        "vix_6m",
    ),
    (
        "cboe_skew_level",
        "Cboe SKEW Index",
        "^SKEW",
        "index_points",
        "skew",
    ),
)


def config_rows():
    return tuple(YahooVolatilitySeries(*row) for row in CONFIG)


def yahoo_frame():
    index = pd.to_datetime(["2026-08-06", "2026-08-07", "2026-08-10"])
    values = {
        ("^VIX9D", "Close"): [15.0, 14.0, 99.0],
        ("^VIX", "Close"): [17.0, 16.0, 99.0],
        ("^VIX3M", "Close"): [21.0, 20.0, 99.0],
        ("^VIX6M", "Close"): [23.0, 22.0, 99.0],
        ("^SKEW", "Close"): [145.0, float("nan"), 199.0],
    }
    return pd.DataFrame(values, index=index)


def write_config(path, rows):
    lines = ["metric_code,metric_name,ticker,unit,role"]
    lines.extend(",".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class YahooVolatilityTests(unittest.TestCase):
    def test_truncates_future_rows_and_calculates_only_on_matched_dates(self):
        config = config_rows()
        histories = extract_yahoo_close_histories(
            yahoo_frame(), config, date(2026, 8, 9)
        )
        metrics = calculate_yahoo_volatility_metrics(
            histories, config, date(2026, 8, 9)
        )
        by_code = {row["metric_code"]: row for row in metrics}

        self.assertEqual(len(metrics), 8)
        self.assertEqual(
            {
                code: by_code[code]["value"]
                for code in (
                    "vix_9d_level",
                    "vix_1m_level",
                    "vix_3m_level",
                    "vix_6m_level",
                    "cboe_skew_level",
                )
            },
            {
                "vix_9d_level": 14.0,
                "vix_1m_level": 16.0,
                "vix_3m_level": 20.0,
                "vix_6m_level": 22.0,
                "cboe_skew_level": 145.0,
            },
        )
        self.assertEqual(by_code["vix_1m_level"]["value"], 16.0)
        self.assertEqual(
            by_code["cboe_skew_level"]["as_of_date"], date(2026, 8, 6)
        )
        self.assertEqual(by_code["vix_1m_3m_spread"]["value"], -4.0)
        self.assertEqual(by_code["vix_1m_3m_ratio"]["value"], 0.8)
        self.assertEqual(by_code["vix_9d_1m_spread"]["value"], -2.0)
        self.assertNotIn(date(2026, 8, 10), histories["vix_1m"].index)
        self.assertTrue(
            all(row["source_url"].startswith("https://") for row in metrics)
        )

    def test_uses_the_latest_common_term_date_when_one_series_lacks_friday(self):
        frame = yahoo_frame().iloc[:2].copy()
        frame.loc[pd.Timestamp("2026-08-07"), ("^VIX3M", "Close")] = float("nan")
        frame.loc[pd.Timestamp("2026-08-07"), ("^SKEW", "Close")] = 146.0

        histories = extract_yahoo_close_histories(
            frame, config_rows(), date(2026, 8, 9)
        )
        metrics = calculate_yahoo_volatility_metrics(
            histories, config_rows(), date(2026, 8, 9)
        )
        by_code = {row["metric_code"]: row for row in metrics}

        self.assertEqual(
            by_code["vix_1m_3m_spread"]["as_of_date"],
            date(2026, 8, 6),
        )
        self.assertEqual(by_code["vix_1m_3m_spread"]["value"], -4.0)
        self.assertEqual(
            by_code["cboe_skew_level"]["as_of_date"],
            date(2026, 8, 7),
        )

    def test_loads_the_exact_five_roles_in_file_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "volatility.csv"
            write_config(path, CONFIG)

            loaded = load_yahoo_volatility_config(path)

        self.assertEqual(tuple(item.role for item in loaded), (
            "vix_9d",
            "vix_1m",
            "vix_3m",
            "vix_6m",
            "skew",
        ))

    def test_rejects_duplicate_missing_and_unknown_config_roles(self):
        invalid_rows = {
            "duplicate role": (*CONFIG[:-1], CONFIG[0]),
            "missing skew": CONFIG[:-1],
            "unknown role": (*CONFIG[:-1], (*CONFIG[-1][:-1], "unknown")),
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "volatility.csv"
            for label, rows in invalid_rows.items():
                with self.subTest(label=label):
                    write_config(path, rows)
                    with self.assertRaises(ValueError):
                        load_yahoo_volatility_config(path)

    def test_rejects_duplicate_tickers_and_metric_codes(self):
        duplicate_ticker = list(CONFIG)
        duplicate_ticker[-1] = (
            *duplicate_ticker[-1][:2],
            CONFIG[0][2],
            *duplicate_ticker[-1][3:],
        )
        duplicate_metric = list(CONFIG)
        duplicate_metric[-1] = (CONFIG[0][0], *duplicate_metric[-1][1:])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "volatility.csv"
            for label, rows in (
                ("ticker", duplicate_ticker),
                ("metric code", duplicate_metric),
            ):
                with self.subTest(label=label):
                    write_config(path, rows)
                    with self.assertRaises(ValueError):
                        load_yahoo_volatility_config(path)

    def test_rejects_blank_fields_and_non_index_point_units(self):
        blank_name = list(CONFIG)
        blank_name[0] = (blank_name[0][0], " ", *blank_name[0][2:])
        wrong_unit = list(CONFIG)
        wrong_unit[0] = (*wrong_unit[0][:3], "ratio", wrong_unit[0][4])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "volatility.csv"
            for label, rows in (
                ("blank", blank_name),
                ("unit", wrong_unit),
            ):
                with self.subTest(label=label):
                    write_config(path, rows)
                    with self.assertRaises(ValueError):
                        load_yahoo_volatility_config(path)

    def test_disjoint_unrelated_term_dates_do_not_block_available_pairs(self):
        histories = extract_yahoo_close_histories(
            yahoo_frame(), config_rows(), date(2026, 8, 9)
        )
        histories["vix_6m"] = histories["vix_6m"].loc[
            histories["vix_6m"].index == date(2026, 8, 6)
        ]
        histories["vix_9d"] = histories["vix_9d"].loc[
            histories["vix_9d"].index == date(2026, 8, 7)
        ]

        metrics = calculate_yahoo_volatility_metrics(
            histories, config_rows(), date(2026, 8, 9)
        )

        by_code = {row["metric_code"]: row for row in metrics}
        self.assertEqual(by_code["vix_1m_3m_spread"]["value"], -4.0)
        self.assertEqual(by_code["vix_9d_1m_spread"]["value"], -2.0)

    def test_stale_skew_does_not_block_fresh_vix_rows(self):
        frame = pd.DataFrame(
            {
                ("^VIX9D", "Close"): [14.0, 13.0],
                ("^VIX", "Close"): [16.0, 15.0],
                ("^VIX3M", "Close"): [20.0, 19.0],
                ("^VIX6M", "Close"): [22.0, 21.0],
                ("^SKEW", "Close"): [145.0, float("nan")],
            },
            index=pd.to_datetime(["2026-08-06", "2026-08-15"]),
        )
        histories = extract_yahoo_close_histories(
            frame, config_rows(), date(2026, 8, 16)
        )

        metrics = calculate_yahoo_volatility_metrics(
            histories, config_rows(), date(2026, 8, 16)
        )

        self.assertNotIn(
            "cboe_skew_level", {row["metric_code"] for row in metrics}
        )
        self.assertIn("vix_1m_level", {row["metric_code"] for row in metrics})

    def test_stale_term_structure_does_not_block_fresh_skew(self):
        frame = pd.DataFrame(
            {
                ("^VIX9D", "Close"): [14.0, float("nan")],
                ("^VIX", "Close"): [16.0, float("nan")],
                ("^VIX3M", "Close"): [20.0, float("nan")],
                ("^VIX6M", "Close"): [22.0, float("nan")],
                ("^SKEW", "Close"): [145.0, 144.0],
            },
            index=pd.to_datetime(["2026-08-07", "2026-08-19"]),
        )
        histories = extract_yahoo_close_histories(
            frame, config_rows(), date(2026, 8, 20)
        )

        metrics = calculate_yahoo_volatility_metrics(
            histories, config_rows(), date(2026, 8, 20)
        )

        self.assertEqual(
            [row["metric_code"] for row in metrics], ["cboe_skew_level"]
        )

    def test_rejects_zero_vix3m_denominator(self):
        frame = yahoo_frame()
        frame.loc[pd.Timestamp("2026-08-07"), ("^VIX3M", "Close")] = 0.0
        histories = extract_yahoo_close_histories(
            frame, config_rows(), date(2026, 8, 9)
        )

        with self.assertRaisesRegex(ValueError, "denominator"):
            calculate_yahoo_volatility_metrics(
                histories, config_rows(), date(2026, 8, 9)
            )

    def test_rejects_non_finite_history(self):
        frame = yahoo_frame()
        frame.loc[pd.Timestamp("2026-08-07"), ("^VIX", "Close")] = float("inf")

        with self.assertRaisesRegex(ValueError, "non-finite"):
            extract_yahoo_close_histories(
                frame, config_rows(), date(2026, 8, 9)
            )

    def test_rejects_duplicate_normalized_dates(self):
        frame = yahoo_frame().iloc[:2].copy()
        frame.index = pd.to_datetime(["2026-08-07 09:00", "2026-08-07 16:00"])

        with self.assertRaisesRegex(ValueError, "duplicate dates"):
            extract_yahoo_close_histories(
                frame, config_rows(), date(2026, 8, 9)
            )

    def test_rejects_empty_and_future_only_histories(self):
        columns = yahoo_frame().columns
        invalid_frames = {
            "empty": pd.DataFrame(columns=columns),
            "future only": yahoo_frame().iloc[[-1]],
        }
        for label, frame in invalid_frames.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    extract_yahoo_close_histories(
                        frame, config_rows(), date(2026, 8, 9)
                    )

    def test_missing_tickers_preserve_available_histories_and_metrics(self):
        frame = yahoo_frame().drop(
            columns=[
                ("^VIX9D", "Close"),
                ("^VIX3M", "Close"),
                ("^VIX6M", "Close"),
            ]
        )

        histories = extract_yahoo_close_histories(
            frame, config_rows(), date(2026, 8, 9)
        )
        metrics = calculate_yahoo_volatility_metrics(
            histories, config_rows(), date(2026, 8, 9)
        )

        self.assertEqual(set(histories), {"vix_1m", "skew"})
        self.assertEqual(
            [row["metric_code"] for row in metrics],
            ["vix_1m_level", "cboe_skew_level"],
        )

    def test_extracts_field_first_multi_level_columns(self):
        frame = yahoo_frame()
        frame.columns = pd.MultiIndex.from_tuples(
            [(field, ticker) for ticker, field in frame.columns]
        )

        histories = extract_yahoo_close_histories(
            frame, config_rows(), date(2026, 8, 9)
        )

        self.assertEqual(histories["vix_3m"].to_dict(), {
            date(2026, 8, 6): 21.0,
            date(2026, 8, 7): 20.0,
        })

    def test_extracts_a_single_level_close_column_for_one_series(self):
        item = YahooVolatilitySeries(*CONFIG[1])
        frame = pd.DataFrame(
            {"Close": [17.0, 16.0]},
            index=pd.to_datetime(["2026-08-06", "2026-08-07"]),
        )

        histories = extract_yahoo_close_histories(
            frame, (item,), date(2026, 8, 9)
        )

        self.assertEqual(histories["vix_1m"].to_dict(), {
            date(2026, 8, 6): 17.0,
            date(2026, 8, 7): 16.0,
        })

    def test_serializes_histories_in_configured_ticker_and_date_order(self):
        histories = extract_yahoo_close_histories(
            yahoo_frame(), config_rows(), date(2026, 8, 9)
        )

        raw = serialize_yahoo_close_histories(histories, config_rows())

        self.assertEqual(
            raw,
            "date,ticker,close\n"
            "2026-08-06,^VIX9D,15.0\n"
            "2026-08-07,^VIX9D,14.0\n"
            "2026-08-06,^VIX,17.0\n"
            "2026-08-07,^VIX,16.0\n"
            "2026-08-06,^VIX3M,21.0\n"
            "2026-08-07,^VIX3M,20.0\n"
            "2026-08-06,^VIX6M,23.0\n"
            "2026-08-07,^VIX6M,22.0\n"
            "2026-08-06,^SKEW,145.0\n",
        )


if __name__ == "__main__":
    unittest.main()
