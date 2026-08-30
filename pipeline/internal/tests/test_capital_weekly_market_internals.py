from datetime import date
import math
import unittest

import pandas as pd

from pipeline.internal.capital_weekly.context.market_internals import (
    calculate_breadth,
    calculate_liquidity_metrics,
    calculate_registered_universe_state,
    calculate_style_relative_return,
    parse_nasdaq_market_summary,
)


class MarketInternalsTests(unittest.TestCase):
    def test_liquidity_metrics_calculate_volatility_drawdown_turnover_and_amihud(self):
        history = pd.DataFrame(
            {
                "date": [date(2026, 7, 22), date(2026, 7, 23), date(2026, 7, 24)],
                "close": [100.0, 110.0, 99.0],
                "volume": [100.0, 200.0, 400.0],
                "turnover_value": [100.0, 200.0, 400.0],
            }
        )

        metrics = calculate_liquidity_metrics(history, window=3)

        self.assertAlmostEqual(metrics["realized_volatility"], math.sqrt(0.02) * math.sqrt(252))
        self.assertAlmostEqual(metrics["drawdown"], -0.10)
        self.assertAlmostEqual(metrics["relative_turnover"], 400 / (700 / 3))
        self.assertAlmostEqual(metrics["amihud"], 0.000375)

    def test_breadth_calculates_participation_median_and_moving_average_share(self):
        rows = []
        closes = {
            "A": [90.0, 100.0, 110.0],
            "B": [110.0, 100.0, 90.0],
            "C": [100.0, 100.0, 100.0],
        }
        days = [date(2026, 7, 22), date(2026, 7, 23), date(2026, 7, 24)]
        for symbol, values in closes.items():
            rows.extend(
                {"symbol": symbol, "date": day, "close": value}
                for day, value in zip(days, values)
            )

        metrics = calculate_breadth(pd.DataFrame(rows), moving_average_windows=(2,))

        self.assertEqual(metrics["advancers"], 1)
        self.assertEqual(metrics["decliners"], 1)
        self.assertEqual(metrics["unchanged"], 1)
        self.assertAlmostEqual(metrics["advance_ratio"], 0.5)
        self.assertAlmostEqual(metrics["advance_decline_ratio"], 1.0)
        self.assertEqual(metrics["net_advances"], 0)
        self.assertAlmostEqual(metrics["median_return"], 0.0)
        self.assertAlmostEqual(metrics["pct_above_2d_ma"], 1 / 3)
        self.assertEqual(metrics["new_highs"], 1)
        self.assertEqual(metrics["new_lows"], 1)

    def test_style_relative_return_subtracts_benchmark_return(self):
        style = pd.Series([100.0, 110.0])
        benchmark = pd.Series([100.0, 105.0])

        self.assertAlmostEqual(
            calculate_style_relative_return(style, benchmark),
            0.05,
        )

    def test_registered_universe_applies_cutoff_before_breadth_calculation(self):
        days = pd.bdate_range("2025-10-27", periods=205)
        rows = []
        for symbol, step in (("XLK", 1.0), ("XLF", -0.2)):
            rows.extend(
                {
                    "symbol": symbol,
                    "date": observation.date(),
                    "close": 100.0 + index * step,
                }
                for index, observation in enumerate(days)
            )
        cutoff = days[-2].date()
        rows.append(
            {
                "symbol": "XLF",
                "date": days[-1].date(),
                "close": 500.0,
            }
        )

        result = calculate_registered_universe_state(
            pd.DataFrame(rows),
            as_of_date=cutoff,
        )

        self.assertEqual(result["as_of_date"], cutoff)
        self.assertEqual(result["constituent_count"], 2)
        self.assertEqual(result["advancers"], 1)
        self.assertEqual(result["decliners"], 1)
        self.assertAlmostEqual(result["pct_above_20d_ma"], 0.5)
        self.assertAlmostEqual(result["pct_above_50d_ma"], 0.5)
        self.assertAlmostEqual(result["pct_above_200d_ma"], 0.5)
        self.assertEqual(result["coverage_above_200d_ma"], 2)

    def test_breadth_excludes_symbols_without_required_moving_average_history(self):
        dates = pd.bdate_range("2026-01-02", periods=22)
        rows = [
            {"symbol": "FULL", "date": day.date(), "close": 100 + index}
            for index, day in enumerate(dates)
        ]
        rows.extend(
            {"symbol": "SHORT", "date": day.date(), "close": 200 + index}
            for index, day in enumerate(dates[-5:])
        )

        metrics = calculate_breadth(
            pd.DataFrame(rows), moving_average_windows=(20,)
        )

        self.assertEqual(metrics["coverage_above_20d_ma"], 1)
        self.assertEqual(metrics["pct_above_20d_ma"], 1.0)

    def test_new_high_low_counts_use_a_252_session_lookback(self):
        dates = pd.bdate_range("2025-08-01", periods=260)
        values = [1_000.0, *([100.0] * 258), 200.0]
        history = pd.DataFrame(
            {
                "symbol": "A",
                "date": [day.date() for day in dates],
                "close": values,
            }
        )

        metrics = calculate_breadth(history, moving_average_windows=(20,))

        self.assertEqual(metrics["new_highs"], 1)
        self.assertEqual(metrics["new_lows"], 0)

    def test_nasdaq_summary_parser_extracts_public_volume_and_trade_fields(self):
        html = """
        <h2>For Jul 23, 2026</h2>
        <table>
        <tr><td>Total Volume:</td><td>7,756,125,617</td><td>$522,416,199,518</td></tr>
        <tr><td>Block Volume:</td><td>1,537,010,039</td></tr>
        <tr><td>Number of Issues:</td><td>5,745</td></tr>
        <tr><td>Total Trades:</td><td>66,453,432</td></tr>
        <tr><td>Block Trades:</td><td>40,990</td></tr>
        </table>
        """

        rows = parse_nasdaq_market_summary(html)

        self.assertEqual(rows[0]["date"], date(2026, 7, 23))
        self.assertEqual(rows[0]["share_volume"], 7_756_125_617)
        self.assertEqual(rows[0]["dollar_volume"], 522_416_199_518)
        self.assertEqual(rows[0]["trade_count"], 66_453_432)
        self.assertAlmostEqual(
            rows[0]["block_volume_ratio"], 1_537_010_039 / 7_756_125_617
        )


if __name__ == "__main__":
    unittest.main()
