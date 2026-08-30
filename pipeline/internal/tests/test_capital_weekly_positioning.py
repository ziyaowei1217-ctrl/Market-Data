from datetime import date
import unittest

from pipeline.internal.capital_weekly.context.positioning import (
    calculate_positioning_percentile,
    cftc_known_as_of,
    parse_cftc_disaggregated_csv,
    parse_cftc_tff_csv,
    parse_finra_margin_table,
)
from pipeline.internal.capital_weekly.context.provider_contracts import filter_known_as_of


DISAGGREGATED_COLUMNS = (
    "Market_and_Exchange_Names,CFTC_Contract_Market_Code,"
    "Report_Date_as_YYYY-MM-DD,Open_Interest_All,"
    "Prod_Merc_Positions_Long_All,Prod_Merc_Positions_Short_All,"
    "Swap_Positions_Long_All,Swap__Positions_Short_All,"
    "M_Money_Positions_Long_All,M_Money_Positions_Short_All,"
    "Other_Rept_Positions_Long_All,Other_Rept_Positions_Short_All\n"
)


def gold_contract(**overrides):
    contract = {
        "contract_code": "088691",
        "commodity_code": "GOLD_COMEX",
        "commodity_family": "gold",
        "market_name": "GOLD - COMMODITY EXCHANGE INC.",
        "percentile_window": "3",
        "percentile_min_observations": "2",
    }
    contract.update(overrides)
    return contract


class PositioningTests(unittest.TestCase):
    def test_disaggregated_parser_uses_physical_commodity_participant_classes(self):
        text = DISAGGREGATED_COLUMNS + (
            "GOLD - COMMODITY EXCHANGE INC.,088691,2026-08-18,500000,"
            "100000,200000,120000,70000,250000,100000,30000,20000\n"
        )

        rows = parse_cftc_disaggregated_csv(text, [gold_contract()])

        self.assertEqual(rows[0]["commodity_code"], "GOLD_COMEX")
        self.assertEqual(rows[0]["open_interest"], 500_000)
        self.assertEqual(rows[0]["producer_net"], -100_000)
        self.assertEqual(rows[0]["swap_dealer_net"], 50_000)
        self.assertEqual(rows[0]["managed_money_net"], 150_000)
        self.assertEqual(rows[0]["other_reportable_net"], 10_000)
        self.assertEqual(rows[0]["known_as_of"], "2026-08-21T15:30:00-04:00")
        self.assertNotIn("asset_manager_net", rows[0])

    def test_disaggregated_parser_calculates_same_contract_changes_and_windowed_percentiles(self):
        text = DISAGGREGATED_COLUMNS + (
            "GOLD - COMMODITY EXCHANGE INC.,088691,2026-08-04,500000,"
            "100,200,120,70,100,80,30,20\n"
            "GOLD - COMMODITY EXCHANGE INC.,088691,2026-08-11,510000,"
            "110,190,130,60,120,70,35,20\n"
            "GOLD - COMMODITY EXCHANGE INC.,088691,2026-08-18,520000,"
            "120,180,140,50,90,80,40,20\n"
        )

        rows = parse_cftc_disaggregated_csv(text, [gold_contract(percentile_window="2")])

        self.assertIsNone(rows[0]["managed_money_net_change"])
        self.assertIsNone(rows[0]["managed_money_percentile"])
        self.assertEqual(rows[1]["managed_money_net_change"], 30)
        self.assertEqual(rows[1]["managed_money_percentile"], 1.0)
        self.assertEqual(rows[2]["managed_money_net_change"], -40)
        self.assertEqual(rows[2]["managed_money_percentile"], 0.5)

    def test_disaggregated_rows_observe_the_friday_known_as_of_cutoff(self):
        row = {
            "report_date": date(2026, 8, 18),
            "known_as_of": cftc_known_as_of(date(2026, 8, 18)),
        }

        self.assertEqual(filter_known_as_of([row], date(2026, 8, 20)), [])
        self.assertEqual(filter_known_as_of([row], date(2026, 8, 23)), [row])

    def test_disaggregated_parser_rejects_absent_configured_code(self):
        text = DISAGGREGATED_COLUMNS + (
            "SILVER - COMMODITY EXCHANGE INC.,084691,2026-08-18,1000,"
            "100,200,120,70,250,100,30,20\n"
        )

        with self.assertRaisesRegex(
            ValueError, "^CFTC response contained no configured contracts$"
        ):
            parse_cftc_disaggregated_csv(text, [gold_contract()])

    def test_disaggregated_parser_rejects_partial_contract_coverage(self):
        text = DISAGGREGATED_COLUMNS + (
            "GOLD - COMMODITY EXCHANGE INC.,088691,2026-08-18,1000,"
            "100,200,120,70,250,100,30,20\n"
        )
        wti = gold_contract(
            contract_code="067651",
            commodity_code="WTI",
            commodity_family="refined_products",
            market_name="WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE",
        )

        with self.assertRaisesRegex(
            ValueError, "^CFTC response missing configured contracts: 067651$"
        ):
            parse_cftc_disaggregated_csv(text, [gold_contract(), wti])

    def test_disaggregated_parser_rejects_configured_code_market_name_mismatch(self):
        text = DISAGGREGATED_COLUMNS + (
            "NOT GOLD,088691,2026-08-18,1000,100,200,120,70,250,100,30,20\n"
        )

        with self.assertRaisesRegex(ValueError, "market name mismatch.*088691"):
            parse_cftc_disaggregated_csv(text, [gold_contract()])

    def test_cftc_parser_calculates_asset_manager_and_leveraged_fund_net(self):
        text = (
            "Market_and_Exchange_Names,Report_Date_as_MM_DD_YYYY,"
            "CFTC_Contract_Market_Code,Open_Interest_All,"
            "Asset_Mgr_Positions_Long_All,Asset_Mgr_Positions_Short_All,"
            "Lev_Money_Positions_Long_All,Lev_Money_Positions_Short_All\n"
            "S&P 500 Consolidated,07/21/2026,13874A,100000,"
            "60000,20000,15000,45000\n"
            "S&P 500 Consolidated,07/14/2026,13874A,90000,"
            "55000,25000,18000,40000\n"
        )

        rows = parse_cftc_tff_csv(text, {"13874A": "SP500"})

        self.assertEqual(rows[-1]["report_date"], date(2026, 7, 21))
        self.assertEqual(rows[-1]["asset_manager_net"], 40_000)
        self.assertEqual(rows[-1]["leveraged_fund_net"], -30_000)
        self.assertEqual(rows[-1]["asset_manager_net_change"], 10_000)
        self.assertEqual(rows[-1]["release_lag_days"], 3)

    def test_positioning_percentile_uses_observed_history(self):
        self.assertAlmostEqual(
            calculate_positioning_percentile([-20, 0, 10, 30], 10),
            0.75,
        )

    def test_finra_margin_parser_reads_public_monthly_balances(self):
        html = """
        <table><tr><th>Month/Year</th>
        <th>Debit Balances in Customers' Securities Margin Accounts</th>
        <th>Free Credit Balances in Customers' Cash Accounts</th>
        <th>Free Credit Balances in Customers' Securities Margin Accounts</th></tr>
        <tr><td>Jun-26</td><td>1,300,000</td><td>210,000</td><td>200,000</td></tr>
        </table>
        """

        rows = parse_finra_margin_table(html)

        self.assertEqual(rows[0]["date"], date(2026, 6, 1))
        self.assertEqual(rows[0]["margin_debit_millions"], 1_300_000)
        self.assertEqual(rows[0]["free_credit_total_millions"], 410_000)

    def test_cftc_parser_rejects_missing_position_columns(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            parse_cftc_tff_csv(
                "Market_and_Exchange_Names,Report_Date_as_MM_DD_YYYY\n"
                "S&P 500,07/21/2026\n",
                {},
            )

    def test_cftc_parser_accepts_current_iso_report_date_column(self):
        text = (
            "Market_and_Exchange_Names,Report_Date_as_YYYY-MM-DD,"
            "CFTC_Contract_Market_Code,Open_Interest_All,"
            "Asset_Mgr_Positions_Long_All,Asset_Mgr_Positions_Short_All,"
            "Lev_Money_Positions_Long_All,Lev_Money_Positions_Short_All\n"
            "S&P 500,2026-07-21,13874A,1000,600,200,300,500\n"
        )

        rows = parse_cftc_tff_csv(text, {"13874A": "SP500"})

        self.assertEqual(rows[0]["report_date"], date(2026, 7, 21))


if __name__ == "__main__":
    unittest.main()
