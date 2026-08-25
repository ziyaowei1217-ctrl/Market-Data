from datetime import date, datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pandas as pd

from pipeline.internal.capital_weekly import equity_indices
from pipeline.internal.capital_weekly.equity_indices import (
    IndexConfig,
    _drop_unfinished_current_day,
    _parse_eastmoney_kline,
    load_index_universe,
    source_url,
)


class EquityIndexFetcherTests(unittest.TestCase):
    def test_fetcher_applies_as_of_cutoff_before_snapshot_calculation(self):
        with tempfile.TemporaryDirectory() as directory:
            universe_path = Path(directory) / "universe.csv"
            universe_path.write_text(
                "region,index_name_cn,index_name_en,ticker,currency,provider,"
                "provider_symbol,source,notes\n"
                "US,测试指数,Test Index,TEST,USD,sina_us,.TEST,Sina Finance,\n",
                encoding="utf-8",
            )
            history = pd.DataFrame(
                {
                    "date": [date(2025, 12, 31), date(2026, 8, 7), date(2026, 8, 10)],
                    "open": [100.0, 105.0, 110.0],
                    "high": [100.0, 105.0, 110.0],
                    "low": [100.0, 105.0, 110.0],
                    "close": [100.0, 105.0, 110.0],
                    "volume": [1, 1, 1],
                }
            )

            with patch(
                "pipeline.internal.capital_weekly.equity_indices.fetch_history",
                return_value=(history, "fake history"),
            ):
                data, source_log = equity_indices.fetch_equity_indices(
                    universe_path,
                    as_of_date=date(2026, 8, 9),
                )

        self.assertEqual(data.loc[0, "latest_date"], "2026-08-07")
        self.assertEqual(source_log.loc[0, "latest_date"], "2026-08-07")

    def test_parse_yahoo_chart_ohlcv_normalizes_daily_rows(self):
        payload = {
            "chart": {
                "result": [
                    {
                        "timestamp": [1784505600, 1784592000],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [2900.0, 2910.0],
                                    "high": [2920.0, 2930.0],
                                    "low": [2890.0, 2900.0],
                                    "close": [2915.0, 2925.0],
                                    "volume": [100, 200],
                                }
                            ]
                        },
                    }
                ],
                "error": None,
            }
        }

        history = equity_indices._parse_yahoo_chart_ohlcv(json.dumps(payload))

        self.assertEqual(
            history["date"].tolist(),
            [datetime(2026, 7, 20).date(), datetime(2026, 7, 21).date()],
        )
        self.assertEqual(history["close"].tolist(), [2915.0, 2925.0])

    def test_parse_ftse_russell_csv_uses_price_index_column(self):
        text = (
            "\ufeffIndex_Name,Date,Value_Without_Dividends__USD_,"
            "Value_With_Dividends__USD_\n"
            "Russell 2000®,07/24/2026,7281.785036,16160.757634\n"
            "Russell 2000®,07/23/2026,7307.045182,16216.160176\n"
        )

        history = equity_indices._parse_ftse_russell_csv(text)

        self.assertEqual(
            history["date"].tolist(),
            [datetime(2026, 7, 23).date(), datetime(2026, 7, 24).date()],
        )
        self.assertEqual(history["close"].tolist(), [7307.045182, 7281.785036])

    def test_merge_rut_history_extends_yahoo_scale_with_ftse_latest_date(self):
        yahoo = pd.DataFrame(
            {
                "date": [
                    datetime(2026, 7, 20).date(),
                    datetime(2026, 7, 21).date(),
                    datetime(2026, 7, 22).date(),
                    datetime(2026, 7, 23).date(),
                ],
                "open": [2900.0, 2910.0, 2920.0, 2930.0],
                "high": [2900.0, 2910.0, 2920.0, 2930.0],
                "low": [2900.0, 2910.0, 2920.0, 2930.0],
                "close": [2900.0, 2910.0, 2920.0, 2930.0],
                "volume": [0, 0, 0, 0],
            }
        )
        ftse = pd.DataFrame(
            {
                "date": [
                    datetime(2026, 7, 20).date(),
                    datetime(2026, 7, 21).date(),
                    datetime(2026, 7, 22).date(),
                    datetime(2026, 7, 23).date(),
                    datetime(2026, 7, 24).date(),
                ],
                "open": [7250.0, 7275.0, 7300.0, 7325.0, 7350.0],
                "high": [7250.0, 7275.0, 7300.0, 7325.0, 7350.0],
                "low": [7250.0, 7275.0, 7300.0, 7325.0, 7350.0],
                "close": [7250.0, 7275.0, 7300.0, 7325.0, 7350.0],
                "volume": [0, 0, 0, 0, 0],
            }
        )

        merged = equity_indices._merge_rut_history(yahoo, ftse)

        self.assertEqual(merged.iloc[-1]["date"], datetime(2026, 7, 24).date())
        self.assertAlmostEqual(merged.iloc[-1]["close"], 2940.0)
        self.assertEqual(len(merged), 5)

    def test_merge_rut_history_rejects_unstable_recent_scale_ratio(self):
        yahoo = pd.DataFrame(
            {
                "date": [
                    datetime(2026, 7, 20).date(),
                    datetime(2026, 7, 21).date(),
                ],
                "open": [100.0, 100.0],
                "high": [100.0, 100.0],
                "low": [100.0, 100.0],
                "close": [100.0, 100.0],
                "volume": [0, 0],
            }
        )
        ftse = pd.DataFrame(
            {
                "date": [
                    datetime(2026, 7, 20).date(),
                    datetime(2026, 7, 21).date(),
                ],
                "open": [250.0, 300.0],
                "high": [250.0, 300.0],
                "low": [250.0, 300.0],
                "close": [250.0, 300.0],
                "volume": [0, 0],
            }
        )

        with self.assertRaisesRegex(ValueError, "scale ratio"):
            equity_indices._merge_rut_history(yahoo, ftse)

    def test_load_index_universe_rejects_duplicate_tickers(self):
        header = (
            "region,index_name_cn,index_name_en,ticker,currency,provider,"
            "provider_symbol,source,notes\n"
        )
        row = "US,罗素2000,Russell 2000,RUT,USD,sina_us,.RUT,Sina Finance,\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "indices.csv"
            path.write_text(header + row + row, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate index ticker: RUT"):
                load_index_universe(path)

    def test_universe_contains_real_russell_2000_and_sox_without_nasdaq_proxy_note(self):
        universe = load_index_universe()
        by_ticker = {config.ticker: config for config in universe}

        self.assertIn("RUT", by_ticker)
        self.assertEqual(by_ticker["RUT"].index_name_en, "Russell 2000")
        self.assertEqual(by_ticker["RUT"].provider, "yahoo_ftse_russell")
        self.assertEqual(by_ticker["RUT"].provider_symbol, "^RUT")
        self.assertEqual(by_ticker["RUT"].source, "Yahoo Finance + FTSE Russell")
        self.assertIn("SOX", by_ticker)
        self.assertEqual(by_ticker["SOX"].index_name_en, "PHLX Semiconductor Index")
        self.assertEqual(by_ticker["SOX"].provider, "sina_us")
        self.assertEqual(by_ticker["SOX"].provider_symbol, ".SOX")
        self.assertEqual(by_ticker["SOX"].source, "Sina Finance US Index")

        nasdaq_100 = by_ticker[".NDX"]
        self.assertNotIn("Russell", nasdaq_100.notes)

    def test_parse_hsi_chart_normalizes_one_year_close_series(self):
        text = json.dumps(
            {
                "indexCode": "00011.01",
                "indexName": "Hang Seng Composite Industry Index - Energy",
                "indexLevels-1y": [
                    [1767139200000, 100.0],
                    [1784822400000, 110.0],
                ],
            }
        )

        history = equity_indices._parse_hsi_chart(text, "00011.01")

        self.assertEqual(
            history["date"].tolist(),
            [datetime(2025, 12, 31).date(), datetime(2026, 7, 24).date()],
        )
        self.assertEqual(history["close"].tolist(), [100.0, 110.0])
        self.assertEqual(history["open"].tolist(), [100.0, 110.0])

    def test_parse_hsi_chart_rejects_wrong_index_code(self):
        text = json.dumps(
            {
                "indexCode": "00011.02",
                "indexLevels-1y": [[1784822400000, 110.0]],
            }
        )

        with self.assertRaisesRegex(ValueError, "index code"):
            equity_indices._parse_hsi_chart(text, "00011.01")

    def legacy_parse_investing_page_rejects_non_object_history_record(self):
        state = {
            "historicalDataStore": {"historicalData": {"data": [None]}},
            "indexStore": {"priceChanges": {"pct_ytd": 10}},
        }
        text = (
            '<script id="__NEXT_DATA__" type="application/json">'
            f'{json.dumps({"props": {"pageProps": {"state": state}}})}</script>'
        )

        with self.assertRaisesRegex(ValueError, "Investing.com"):
            equity_indices._parse_investing_page(text)

    def legacy_parse_investing_page_ignores_invalid_optional_price_change_shapes(self):
        record = {
            "rowDateTimestamp": "2026-07-10T00:00:00Z",
            "last_openRaw": "109",
            "last_closeRaw": "110",
            "last_maxRaw": "111",
            "last_minRaw": "108",
            "volumeRaw": 20,
        }
        index_stores = (
            None,
            [],
            {"priceChanges": None},
            {"priceChanges": []},
        )

        for index_store in index_stores:
            with self.subTest(index_store=index_store):
                state = {
                    "historicalDataStore": {"historicalData": {"data": [record]}},
                    "indexStore": index_store,
                }
                text = (
                    '<script id="__NEXT_DATA__" type="application/json">'
                    f'{json.dumps({"props": {"pageProps": {"state": state}}})}</script>'
                )

                history = equity_indices._parse_investing_page(text)

                self.assertEqual(history["close"].tolist(), [110.0])

    def legacy_parse_investing_page_accepts_reordered_script_attributes(self):
        text = (
            '<script nonce="test-nonce" type = "application/json" '
            'data-page="history" id = "__NEXT_DATA__" >\n'
            '{"props":{"pageProps":{"state":{'
            '"historicalDataStore":{"historicalData":{"data":['
            '{"rowDateTimestamp":"2025-12-31T00:00:00Z",'
            '"last_openRaw":"99","last_closeRaw":"100",'
            '"last_maxRaw":"101","last_minRaw":"98","volumeRaw":10}'
            ']}},"indexStore":{"priceChanges":{"pct_ytd":0}}'
            '}}}}\n</script>'
        )

        try:
            history = equity_indices._parse_investing_page(text)
        except ValueError:
            history = None

        self.assertIsNotNone(history)
        self.assertEqual(history.iloc[-1]["close"], 100.0)

    def legacy_parse_investing_page_wraps_malformed_json(self):
        text = (
            '<script id="__NEXT_DATA__" type="application/json">'
            '{not valid json}</script>'
        )

        with self.assertRaisesRegex(ValueError, "Investing.com"):
            equity_indices._parse_investing_page(text)

    def legacy_parse_investing_page_rejects_invalid_json_shape_with_provider_error(self):
        payloads = ("null", "[]", '{"props":{"pageProps":{}}}')

        for payload in payloads:
            with self.subTest(payload=payload):
                text = (
                    '<script id="__NEXT_DATA__" type="application/json">'
                    f"{payload}</script>"
                )

                with self.assertRaisesRegex(ValueError, "Investing.com"):
                    equity_indices._parse_investing_page(text)

    def legacy_investing_page_url_uses_historical_data_slug(self):
        config = IndexConfig(
            region="HK",
            index_name_cn="恒生能源业指数",
            index_name_en="Hang Seng Composite Industry Index - Energy",
            ticker="HSCIEN",
            currency="HKD",
            provider="investing_page",
            provider_symbol="hsci-energy",
            source="Investing.com Historical Data",
        )

        try:
            url = source_url(config)
        except ValueError:
            url = None

        self.assertEqual(
            url,
            "https://www.investing.com/indices/hsci-energy-historical-data",
        )

    def legacy_parse_investing_page_normalizes_rows_and_appends_ytd_baseline(self):
        text = (
            '<script id="__NEXT_DATA__" type="application/json">'
            '{"props":{"pageProps":{"state":{'
            '"historicalDataStore":{"historicalData":{"data":['
            '{"rowDateTimestamp":"2026-07-10T00:00:00Z",'
            '"last_openRaw":"109","last_closeRaw":"110",'
            '"last_maxRaw":"111","last_minRaw":"108","volumeRaw":20},'
            '{"rowDateTimestamp":"2026-07-09T00:00:00Z",'
            '"last_openRaw":"107","last_closeRaw":"109",'
            '"last_maxRaw":"110","last_minRaw":"106","volumeRaw":10}'
            ']}},"indexStore":{"priceChanges":{"pct_ytd":10}}'
            '}}}}</script>'
        )
        parser = getattr(equity_indices, "_parse_investing_page", None)
        self.assertTrue(callable(parser), "investing_page parser is missing")

        history = equity_indices._append_investing_ytd_baseline(parser(text))

        self.assertEqual(
            history["date"].tolist(),
            [
                datetime(2025, 12, 31).date(),
                datetime(2026, 7, 9).date(),
                datetime(2026, 7, 10).date(),
            ],
        )
        self.assertEqual(history["close"].tolist(), [100.0, 109.0, 110.0])
        self.assertEqual(history.iloc[0].to_dict(), {
            "date": datetime(2025, 12, 31).date(),
            "open": 100.0,
            "high": 100.0,
            "low": 100.0,
            "close": 100.0,
            "volume": 0.0,
        })

    def legacy_parse_investing_page_reads_currency_store_ytd_baseline(self):
        state = {
            "historicalDataStore": {"historicalData": {"data": [{
                "rowDateTimestamp": "2026-07-10T00:00:00Z",
                "last_openRaw": 6.79, "last_closeRaw": 6.78,
                "last_maxRaw": 6.80, "last_minRaw": 6.77, "volumeRaw": 0,
            }]}},
            "currencyStore": {"priceChanges": {"pct_ytd": -2.7683}},
        }
        text = (
            '<script id="__NEXT_DATA__" type="application/json">'
            f'{json.dumps({"props": {"pageProps": {"state": state}}})}</script>'
        )

        history = equity_indices._append_investing_ytd_baseline(
            equity_indices._parse_investing_page(text)
        )

        self.assertEqual(history.iloc[0]["date"], datetime(2025, 12, 31).date())
        self.assertAlmostEqual(history.iloc[-1]["close"], 6.78)

    def legacy_parse_investing_page_rejects_missing_next_data(self):
        parser = getattr(equity_indices, "_parse_investing_page", None)
        self.assertTrue(callable(parser), "investing_page parser is missing")

        with self.assertRaisesRegex(ValueError, "Investing.com"):
            parser("<html><body>No Next data</body></html>")

    def legacy_investing_current_day_row_respects_hk_close_buffer(self):
        config = IndexConfig(
            region="HK",
            index_name_cn="恒生能源业指数",
            index_name_en="Hang Seng Composite Industry Index - Energy",
            ticker="HSCIEN",
            currency="HKD",
            provider="investing_page",
            provider_symbol="hsci-energy",
            source="Investing.com Historical Data",
        )
        history = pd.DataFrame(
            {
                "date": [datetime(2026, 7, 9).date(), datetime(2026, 7, 10).date()],
                "close": [12970.76, 12965.51],
            }
        )

        before_close = _drop_unfinished_current_day(
            history,
            config,
            now_hkt=datetime(2026, 7, 10, 15, 30, tzinfo=ZoneInfo("Asia/Hong_Kong")),
        )
        after_close = _drop_unfinished_current_day(
            history,
            config,
            now_hkt=datetime(2026, 7, 10, 16, 30, tzinfo=ZoneInfo("Asia/Hong_Kong")),
        )

        self.assertEqual(before_close["date"].tolist(), [datetime(2026, 7, 9).date()])
        self.assertEqual(after_close["date"].tolist(), history["date"].tolist())

    def legacy_us_investing_current_day_row_respects_new_york_close_buffer(self):
        config = IndexConfig(
            region="US",
            index_name_cn="罗素2000",
            index_name_en="Russell 2000",
            ticker="RUT",
            currency="USD",
            provider="investing_page",
            provider_symbol="smallcap-2000",
            source="Investing.com Historical Data",
        )
        history = pd.DataFrame(
            {
                "date": [datetime(2026, 7, 10).date(), datetime(2026, 7, 13).date()],
                "close": [2977.81, 2990.0],
            }
        )

        before_close = _drop_unfinished_current_day(
            history,
            config,
            now_hkt=datetime(2026, 7, 14, 3, 30, tzinfo=ZoneInfo("Asia/Hong_Kong")),
        )
        after_close = _drop_unfinished_current_day(
            history,
            config,
            now_hkt=datetime(2026, 7, 14, 4, 30, tzinfo=ZoneInfo("Asia/Hong_Kong")),
        )

        self.assertEqual(before_close["date"].tolist(), [datetime(2026, 7, 10).date()])
        self.assertEqual(after_close["date"].tolist(), history["date"].tolist())

    def legacy_investing_intraday_ytd_baseline_is_not_kept_after_today_is_dropped(self):
        config = IndexConfig(
            region="HK",
            index_name_cn="恒生能源业指数",
            index_name_en="Hang Seng Composite Industry Index - Energy",
            ticker="HSCIEN",
            currency="HKD",
            provider="investing_page",
            provider_symbol="hsci-energy",
            source="Investing.com Historical Data",
        )
        state = {
            "historicalDataStore": {
                "historicalData": {
                    "data": [
                        {
                            "rowDateTimestamp": "2026-07-10T00:00:00Z",
                            "last_openRaw": 109,
                            "last_closeRaw": 110,
                            "last_maxRaw": 111,
                            "last_minRaw": 108,
                            "volumeRaw": 20,
                        },
                        {
                            "rowDateTimestamp": "2026-07-09T00:00:00Z",
                            "last_openRaw": 107,
                            "last_closeRaw": 109,
                            "last_maxRaw": 110,
                            "last_minRaw": 106,
                            "volumeRaw": 10,
                        },
                    ]
                }
            },
            "indexStore": {"priceChanges": {"pct_ytd": 10}},
        }
        text = (
            '<script id="__NEXT_DATA__" type="application/json">'
            f'{json.dumps({"props": {"pageProps": {"state": state}}})}</script>'
        )

        history = equity_indices._parse_investing_page(text)
        before_close = _drop_unfinished_current_day(
            history,
            config,
            now_hkt=datetime(2026, 7, 10, 15, 30, tzinfo=ZoneInfo("Asia/Hong_Kong")),
        )
        before_close = equity_indices._append_investing_ytd_baseline(before_close)

        self.assertEqual(before_close["date"].tolist(), [datetime(2026, 7, 9).date()])

    def test_parse_eastmoney_kline_normalizes_daily_rows(self):
        text = (
            '{"data":{"klines":['
            '"2026-07-08,100.00,102.00,103.00,99.00,12345,0,0,0,0,0",'
            '"2026-07-09,102.00,101.00,104.00,100.00,23456,0,0,0,0,0"]}}'
        )

        history = _parse_eastmoney_kline(text)

        self.assertEqual(
            history["date"].tolist(),
            [datetime(2026, 7, 8).date(), datetime(2026, 7, 9).date()],
        )
        self.assertEqual(history["close"].tolist(), [102.0, 101.0])

    def test_eastmoney_hk_intraday_row_is_dropped_before_close(self):
        config = IndexConfig(
            region="HK",
            index_name_cn="恒生能源业指数",
            index_name_en="Hang Seng Composite Industry Index - Energy",
            ticker="HSCIEN",
            currency="HKD",
            provider="eastmoney_kline",
            provider_symbol="124.HSCIEN",
            source="Eastmoney Kline",
        )
        history = pd.DataFrame(
            {
                "date": [datetime(2026, 7, 9).date(), datetime(2026, 7, 10).date()],
                "close": [12970.76, 12965.51],
            }
        )

        filtered = _drop_unfinished_current_day(
            history,
            config,
            now_hkt=datetime(2026, 7, 10, 15, 30, tzinfo=ZoneInfo("Asia/Hong_Kong")),
        )

        self.assertEqual(filtered["date"].tolist(), [datetime(2026, 7, 9).date()])

    def test_eastmoney_hk_today_row_is_kept_after_close_buffer(self):
        config = IndexConfig(
            region="HK",
            index_name_cn="恒生能源业指数",
            index_name_en="Hang Seng Composite Industry Index - Energy",
            ticker="HSCIEN",
            currency="HKD",
            provider="eastmoney_kline",
            provider_symbol="124.HSCIEN",
            source="Eastmoney Kline",
        )
        history = pd.DataFrame(
            {
                "date": [datetime(2026, 7, 9).date(), datetime(2026, 7, 10).date()],
                "close": [12970.76, 12965.51],
            }
        )

        filtered = _drop_unfinished_current_day(
            history,
            config,
            now_hkt=datetime(2026, 7, 10, 16, 30, tzinfo=ZoneInfo("Asia/Hong_Kong")),
        )

        self.assertEqual(
            filtered["date"].tolist(),
            [datetime(2026, 7, 9).date(), datetime(2026, 7, 10).date()],
        )

    def test_tencent_hk_intraday_row_is_dropped_before_close(self):
        config = IndexConfig(
            region="HK",
            index_name_cn="恒生指数",
            index_name_en="Hang Seng Index",
            ticker="hkHSI",
            currency="HKD",
            provider="tencent_kline",
            provider_symbol="hkHSI",
            source="Tencent Finance Kline",
        )
        history = pd.DataFrame(
            {
                "date": [
                    datetime(2026, 7, 9).date(),
                    datetime(2026, 7, 10).date(),
                ],
                "close": [24030.18, 24423.22],
            }
        )

        filtered = _drop_unfinished_current_day(
            history,
            config,
            now_hkt=datetime(2026, 7, 10, 10, 30, tzinfo=ZoneInfo("Asia/Hong_Kong")),
        )

        self.assertEqual(filtered["date"].tolist(), [datetime(2026, 7, 9).date()])

    def test_tencent_hk_today_row_is_kept_after_close_buffer(self):
        config = IndexConfig(
            region="HK",
            index_name_cn="恒生指数",
            index_name_en="Hang Seng Index",
            ticker="hkHSI",
            currency="HKD",
            provider="tencent_kline",
            provider_symbol="hkHSI",
            source="Tencent Finance Kline",
        )
        history = pd.DataFrame(
            {
                "date": [
                    datetime(2026, 7, 9).date(),
                    datetime(2026, 7, 10).date(),
                ],
                "close": [24030.18, 24423.22],
            }
        )

        filtered = _drop_unfinished_current_day(
            history,
            config,
            now_hkt=datetime(2026, 7, 10, 16, 30, tzinfo=ZoneInfo("Asia/Hong_Kong")),
        )

        self.assertEqual(
            filtered["date"].tolist(),
            [datetime(2026, 7, 9).date(), datetime(2026, 7, 10).date()],
        )


if __name__ == "__main__":
    unittest.main()
