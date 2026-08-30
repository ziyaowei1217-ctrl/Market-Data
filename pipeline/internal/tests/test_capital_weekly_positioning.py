from datetime import date
import unittest

from pipeline.internal.capital_weekly.context.positioning import (
    calculate_positioning_percentile,
    parse_cftc_disaggregated_csv,
    parse_cftc_tff_csv,
    parse_finra_margin_table,
    select_released_cftc_rows,
)


class PositioningTests(unittest.TestCase):
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
        self.assertAlmostEqual(rows[-1]["asset_manager_percentile"], 1.0)
        self.assertAlmostEqual(rows[-1]["leveraged_fund_percentile"], 0.5)
        self.assertEqual(rows[-1]["release_lag_days"], 3)

    def test_disaggregated_parser_uses_managed_money_and_swap_dealer_columns(self):
        text = (
            "Market_and_Exchange_Names,Report_Date_as_YYYY-MM-DD,"
            "CFTC_Contract_Market_Code,Open_Interest_All,"
            "M_Money_Positions_Long_All,M_Money_Positions_Short_All,"
            "Swap_Positions_Long_All,Swap__Positions_Short_All\n"
            "GOLD,2026-07-14,088691,500000,120000,80000,90000,100000\n"
            "GOLD,2026-07-21,088691,510000,110000,95000,105000,95000\n"
        )

        rows = parse_cftc_disaggregated_csv(text, {"088691": "GOLD_COT"})

        self.assertEqual(rows[-1]["managed_money_net"], 15_000)
        self.assertEqual(rows[-1]["managed_money_net_change"], -25_000)
        self.assertAlmostEqual(rows[-1]["managed_money_percentile"], 0.5)
        self.assertEqual(rows[-1]["swap_dealer_net"], 10_000)
        self.assertAlmostEqual(rows[-1]["swap_dealer_percentile"], 1.0)

    def test_cftc_release_cutoff_excludes_not_yet_public_report(self):
        rows = [
            {
                "report_date": date(2026, 8, 4),
                "expected_release_date": date(2026, 8, 7),
            },
            {
                "report_date": date(2026, 8, 11),
                "expected_release_date": date(2026, 8, 14),
            },
        ]

        selected = select_released_cftc_rows(
            rows,
            start=date(2026, 8, 3),
            end=date(2026, 8, 9),
        )

        self.assertEqual([row["report_date"] for row in selected], [date(2026, 8, 4)])

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
