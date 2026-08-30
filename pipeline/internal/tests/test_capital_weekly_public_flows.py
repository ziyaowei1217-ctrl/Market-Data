from datetime import date
import unittest

from pipeline.internal.capital_weekly.context.public_flows import (
    calculate_etf_implied_flow,
    parse_hkex_stock_connect_daily,
    parse_ishares_fund_page,
)


class PublicFlowTests(unittest.TestCase):
    def test_ishares_parser_reads_dated_nav_assets_and_shares(self):
        html = """
        <script type="application/ld+json">
        {"additionalProperty":[
          {"name":"NAV as of","value":"769.23","unitText":"USD",
           "valueReference":{"name":"As of Dates","value":"Aug 21, 2026"}},
          {"name":"Net Assets of Fund","value":"$891,841,317,999","unitText":"USD",
           "valueReference":{"name":"As of Dates","value":"Aug 21, 2026"}}
        ]}
        </script>
        &quot;sharesOutstanding&quot;:{&quot;formattedValue&quot;:&quot;1,159,400,000&quot;,
        &quot;formattedAsOfDate&quot;:&quot;Aug 21, 2026&quot;}
        """

        observation = parse_ishares_fund_page(html, ticker="IVV")

        self.assertEqual(observation["date"], date(2026, 8, 21))
        self.assertEqual(observation["ticker"], "IVV")
        self.assertEqual(observation["net_assets"], 891_841_317_999)
        self.assertEqual(observation["shares_outstanding"], 1_159_400_000)
        self.assertAlmostEqual(observation["nav"], 769.23)

    def test_etf_implied_flow_requires_two_ordered_issuer_observations(self):
        previous = {
            "date": date(2026, 8, 14),
            "shares_outstanding": 1_150_000_000,
            "nav": 760.0,
        }
        current = {
            "date": date(2026, 8, 21),
            "shares_outstanding": 1_159_400_000,
            "nav": 769.23,
        }

        flow = calculate_etf_implied_flow(current, previous)

        self.assertAlmostEqual(flow, 9_400_000 * 769.23)
        with self.assertRaisesRegex(ValueError, "prior"):
            calculate_etf_implied_flow(current, current)

    def test_hkex_parser_aggregates_official_southbound_and_northbound_turnover(self):
        text = r'''tabData = [
          {"date":"2026-08-21","market":"SSE Northbound","tradingDay":1,
           "content":[{"style":1,"table":{"schema":[["Total Turnover","Total Trade Count","DQB","ETF Turnover"]],
           "tr":[{"td":[["125,846.52"]]},{"td":[["6,347,299"]]},{"td":[["999,999,999"]]},{"td":[["2,587.42"]]}]}}]},
          {"date":"2026-08-21","market":"SSE Southbound","tradingDay":1,
           "content":[{"style":1,"table":{"schema":[["Total Turnover","Buy Turnover","Sell Turnover","Total Trade Count","Buy Trade Count","Sell Trade Count","ETF Turnover"]],
           "tr":[{"td":[["64,769.85"]]},{"td":[["29,818.19"]]},{"td":[["34,951.66"]]},{"td":[["1,259,694"]]},{"td":[["595,886"]]},{"td":[["663,808"]]},{"td":[["241.63"]]}]}}]},
          {"date":"2026-08-21","market":"SZSE Northbound","tradingDay":1,
           "content":[{"style":1,"table":{"schema":[["Total Turnover","Total Trade Count","DQB","ETF Turnover"]],
           "tr":[{"td":[["142,241.02"]]},{"td":[["7,181,858"]]},{"td":[["999,999,999"]]},{"td":[["2,610.95"]]}]}}]},
          {"date":"2026-08-21","market":"SZSE Southbound","tradingDay":1,
           "content":[{"style":1,"table":{"schema":[["Total Turnover","Buy Turnover","Sell Turnover","Total Trade Count","Buy Trade Count","Sell Trade Count","ETF Turnover"]],
           "tr":[{"td":[["35,642.81"]]},{"td":[["16,573.32"]]},{"td":[["19,069.49"]]},{"td":[["721,425"]]},{"td":[["339,643"]]},{"td":[["381,782"]]},{"td":[["44.81"]]}]}}]}
        ];'''

        observation = parse_hkex_stock_connect_daily(text)

        self.assertEqual(observation["date"], date(2026, 8, 21))
        self.assertAlmostEqual(observation["southbound_buy_turnover"], 46_391.51)
        self.assertAlmostEqual(observation["southbound_sell_turnover"], 54_021.15)
        self.assertAlmostEqual(observation["southbound_net_buy"], -7_629.64)
        self.assertAlmostEqual(observation["southbound_total_turnover"], 100_412.66)
        self.assertAlmostEqual(observation["northbound_total_turnover"], 268_087.54)
        self.assertNotIn("northbound_net_buy", observation)


if __name__ == "__main__":
    unittest.main()
