import json
from datetime import date
import unittest

from capital_weekly.context.microstructure import (
    ensure_fresh_market_date,
    parse_hkex_market_highlights,
    parse_hkex_short_selling,
    parse_sse_daily_overview,
    parse_szse_daily_overview,
)


class MicrostructureTests(unittest.TestCase):
    def test_hkex_highlights_parse_volume_turnover_trades_and_breadth(self):
        text = """
        Trading Date: 24/07/2026
        Shares Traded: 25,000,000,000
        Turnover (HK$): 210,500,000,000
        Number of Trades: 2,300,000
        Advanced: 1,120
        Declined: 810
        Unchanged: 190
        """

        result = parse_hkex_market_highlights(text)

        self.assertEqual(result["as_of_date"], date(2026, 7, 24))
        self.assertEqual(result["turnover"], 210_500_000_000)
        self.assertEqual(result["advancers"], 1120)
        self.assertAlmostEqual(result["advance_ratio"], 1120 / 1930)

    def test_hkex_short_selling_calculates_market_ratio(self):
        text = """
        Date: 24/07/2026
        Total Short Selling Turnover: HK$ 28,000,000,000
        Total Market Turnover: HK$ 200,000,000,000
        """

        result = parse_hkex_short_selling(text)

        self.assertEqual(result["short_turnover"], 28_000_000_000)
        self.assertAlmostEqual(result["short_turnover_ratio"], 0.14)

    def test_hkex_official_daily_quotation_layout_is_supported(self):
        text = """
        DATE: 24 JUL 2026 (FRIDAY)
        Advanced   : 1120
        Declined   : 810
        Unchanged  : 190
        Today's Turnover:
        (HK$):    210,500,000,000
        (Shares): 25,000,000,000
        (Deals):       2,300,000
        Overseas Turnover (HK$): 2,900,000,000
        Short Selling Turnover Total Value ($) : HKD 28,000,000,000
        Total market turnover                  : HKD 200,000,000,000
        """

        highlights = parse_hkex_market_highlights(text)
        short = parse_hkex_short_selling(text)

        self.assertEqual(highlights["as_of_date"], date(2026, 7, 24))
        self.assertEqual(highlights["turnover"], 210_500_000_000)
        self.assertEqual(highlights["volume"], 25_000_000_000)
        self.assertAlmostEqual(short["short_turnover_ratio"], 0.14)

    def test_sse_and_szse_json_normalize_public_daily_overviews(self):
        sse = {
            "result": [
                {
                    "tradeDate": "20260724",
                    "turnover": "745000000000",
                    "volume": "52800000000",
                    "up": "1260",
                    "down": "980",
                    "flat": "110",
                    "limitUp": "45",
                    "limitDown": "8",
                }
            ]
        }
        szse = {
            "data": [
                {
                    "date": "2026-07-24",
                    "amount": "820000000000",
                    "volume": "61000000000",
                    "riseCount": "1680",
                    "fallCount": "920",
                    "unchangedCount": "85",
                    "limitUpCount": "62",
                    "limitDownCount": "11",
                }
            ]
        }

        sh = parse_sse_daily_overview(json.dumps(sse))
        sz = parse_szse_daily_overview(json.dumps(szse))

        self.assertEqual(sh["market"], "SSE")
        self.assertEqual(sh["advancers"], 1260)
        self.assertEqual(sz["market"], "SZSE")
        self.assertEqual(sz["limit_up"], 62)
        self.assertAlmostEqual(sz["advance_ratio"], 1680 / 2600)

    def test_sse_official_jsonp_daily_overview_uses_stock_total_row(self):
        text = (
            'jsonpCallback({"result":['
            '{"TRADE_DATE":"20260724","PRODUCT_CODE":"01",'
            '"TRADE_AMT":"6267.15","TRADE_VOL":"465.15",'
            '"TOTAL_TO_RATE":"1.2415","LIST_NUM":"1698"},'
            '{"TRADE_DATE":"20260724","PRODUCT_CODE":"17",'
            '"TRADE_AMT":"9163.02","TRADE_VOL":"508.58",'
            '"TOTAL_TO_RATE":"1.4407","LIST_NUM":"2350"}]})'
        )

        result = parse_sse_daily_overview(text)

        self.assertEqual(result["as_of_date"], date(2026, 7, 24))
        self.assertEqual(result["turnover"], 9163.02 * 100_000_000)
        self.assertEqual(result["volume"], 508.58 * 100_000_000)
        self.assertAlmostEqual(result["turnover_rate"], 0.014407)
        self.assertEqual(result["listed_count"], 2350)

    def test_szse_official_report_normalizes_market_overview(self):
        text = json.dumps(
            [
                {
                    "metadata": {
                        "name": "深圳市场",
                        "subname": "2026-07-24",
                        "tabkey": "tab1",
                    },
                    "data": [
                        {"zbmc": "上市公司数", "brsz": "2,896"},
                        {"zbmc": "上市证券数", "brsz": "23,419"},
                        {"zbmc": "股票成交金额（亿元）", "brsz": "10,168.80"},
                        {"zbmc": "股票平均换手率", "brsz": "2.32"},
                    ],
                }
            ],
            ensure_ascii=False,
        )

        result = parse_szse_daily_overview(text)

        self.assertEqual(result["as_of_date"], date(2026, 7, 24))
        self.assertEqual(result["turnover"], 1_016_880_000_000)
        self.assertAlmostEqual(result["turnover_rate"], 0.0232)
        self.assertEqual(result["listed_companies"], 2896)
        self.assertEqual(result["listed_securities"], 23419)

    def test_stale_market_date_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "stale"):
            ensure_fresh_market_date(
                date(2026, 7, 17),
                expected_end=date(2026, 7, 26),
                max_lag_days=3,
            )


if __name__ == "__main__":
    unittest.main()
