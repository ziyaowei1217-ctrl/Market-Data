import unittest

import pandas as pd

from pipeline.internal.capital_weekly.macro_divergence import add_macro_ranks, build_macro_divergence


def _frame(group, changes, names=None, codes=None, asset_class="fixed_income", unit="bp",
           level_units=None):
    count = len(changes)
    names = names or [f"指标{i}" for i in range(1, count + 1)]
    codes = codes or [f"S{i}" for i in range(1, count + 1)]
    return pd.DataFrame(
        {
            "asset_class": [asset_class] * count,
            "group": [group] * count,
            "series_code": codes,
            "name_cn": names,
            "level_unit": level_units or ["percent"] * count,
            "change_unit": [unit] * count,
            "qc_flag": ["OK"] * count,
            "daily_change": changes,
            "weekly_change": changes,
            "mtd_change": changes,
            "ytd_change": changes,
        }
    )


class MacroDivergenceTests(unittest.TestCase):
    def test_dense_ranks_are_within_group_and_exclude_failed_rows(self):
        frame = pd.concat(
            [
                _frame("credit_spreads", [5.0, 5.0, -2.0]),
                _frame("commodities", [0.03, -0.01], asset_class="commodity", unit="pct"),
            ],
            ignore_index=True,
        )
        frame.loc[2, "qc_flag"] = "FETCH_FAILED"

        ranked = add_macro_ranks(frame)

        self.assertEqual(ranked.loc[:1, "weekly_rank"].tolist(), [1, 1])
        self.assertTrue(pd.isna(ranked.loc[2, "weekly_rank"]))
        self.assertEqual(ranked.loc[3:, "weekly_rank"].tolist(), [1, 2])

    def test_ok_row_with_null_horizon_change_is_excluded_and_unranked(self):
        frame = _frame("credit_spreads", [3.0, None, -1.0])
        frame["daily_change"] = [None, 9.0, -1.0]

        ranked = add_macro_ranks(frame)
        summary = build_macro_divergence(frame)
        weekly = summary.query("horizon == 'weekly'").iloc[0]
        daily = summary.query("horizon == 'daily'").iloc[0]

        self.assertEqual(ranked.loc[[0, 2], "weekly_rank"].tolist(), [1, 2])
        self.assertTrue(pd.isna(ranked.loc[1, "weekly_rank"]))
        self.assertEqual(ranked.loc[[1, 2], "daily_rank"].tolist(), [1, 2])
        self.assertTrue(pd.isna(ranked.loc[0, "daily_rank"]))
        self.assertEqual(weekly["valid_count"], 2)
        self.assertEqual(daily["valid_count"], 2)

    def test_summary_calculates_counts_and_population_statistics(self):
        frame = _frame(
            "credit_spreads",
            [4.0, 1.0, 0.0, -3.0],
            names=["高收益", "投资级", "持平", "收窄项"],
        )

        weekly = build_macro_divergence(frame).query("horizon == 'weekly'").iloc[0]

        self.assertEqual(weekly["valid_count"], 4)
        self.assertEqual(weekly["up_count"], 2)
        self.assertEqual(weekly["flat_count"], 1)
        self.assertEqual(weekly["down_count"], 1)
        self.assertAlmostEqual(weekly["median_change"], 0.5)
        self.assertAlmostEqual(weekly["change_range"], 7.0)
        self.assertAlmostEqual(weekly["dispersion"], frame["weekly_change"].std(ddof=0))
        self.assertEqual(weekly["top_movers"], "高收益 +4.00bp; 投资级 +1.00bp; 持平 0.00bp")
        self.assertEqual(weekly["bottom_movers"], "收窄项 -3.00bp; 持平 0.00bp; 投资级 +1.00bp")

    def test_insufficient_and_failed_values_are_excluded(self):
        frame = _frame("credit_spreads", [99.0, 2.0])
        frame.loc[0, "qc_flag"] = "FETCH_FAILED"

        weekly = build_macro_divergence(frame).query("horizon == 'weekly'").iloc[0]

        self.assertEqual(weekly["valid_count"], 1)
        self.assertEqual(weekly["qc_flag"], "INSUFFICIENT_DATA")
        self.assertTrue(pd.isna(weekly["median_change"]))
        self.assertEqual(weekly["top_movers"], "")
        self.assertEqual(weekly["commentary_cn"], "")

    def test_commentary_uses_sovereign_yield_and_curve_wording(self):
        frame = _frame(
            "sovereign_curve",
            [3.0, -2.0, 5.0],
            names=["美国10年期收益率", "中国10年期收益率", "美国10年-2年期限利差"],
            codes=["UST10Y", "CGB10Y", "UST10Y2Y"],
            level_units=["percent", "percent", "percentage_points"],
        )

        text = build_macro_divergence(frame).query("horizon == 'weekly'").iloc[0]["commentary_cn"]

        self.assertIn("美国10年期收益率（收益率上行）", text)
        self.assertIn("中国10年期收益率（收益率下行）", text)
        self.assertIn("美国10年-2年期限利差（曲线走陡）", text)

    def test_curve_wording_uses_level_unit_for_any_series_code_and_neutral_direction(self):
        frame = _frame(
            "sovereign_curve",
            [-4.0, 1.0],
            names=["中国10年-2年期限利差", "美国2年期收益率"],
            codes=["CGB10Y2Y_CUSTOM", "UST2Y"],
            level_units=["percentage_points", "percent"],
        )

        text = build_macro_divergence(frame).query("horizon == 'weekly'").iloc[0]["commentary_cn"]

        self.assertIn("中国10年-2年期限利差（曲线趋平）", text)
        self.assertNotIn("倒挂", text)

    def test_commentary_uses_credit_and_commodity_wording_by_sign(self):
        credit = _frame("credit_spreads", [4.0, -3.0], names=["高收益利差", "投资级利差"])
        commodity = _frame(
            "commodities", [0.02, -0.01], names=["原油", "黄金"],
            asset_class="commodity", unit="pct",
        )

        summary = build_macro_divergence(pd.concat([credit, commodity], ignore_index=True))
        credit_text = summary.query("group == 'credit_spreads' and horizon == 'weekly'").iloc[0]["commentary_cn"]
        commodity_text = summary.query("group == 'commodities' and horizon == 'weekly'").iloc[0]["commentary_cn"]

        self.assertIn("高收益利差（信用利差走阔）", credit_text)
        self.assertIn("投资级利差（信用利差收窄）", credit_text)
        self.assertIn("原油（商品上涨）", commodity_text)
        self.assertIn("黄金（商品下跌）", commodity_text)
        self.assertNotIn("高收益利差信用利差", credit_text)
        self.assertNotIn("原油商品上涨", commodity_text)

    def test_commentary_magnitudes_are_absolute_and_movers_remain_signed(self):
        commodity = _frame(
            "commodities", [-0.0038, 0.002], names=["WTI原油", "黄金"],
            asset_class="commodity", unit="pct",
        )
        rates = _frame(
            "policy_money_market", [-5.79, 1.25], names=["3个月HIBOR", "1年期LPR"],
        )

        summary = build_macro_divergence(pd.concat([commodity, rates], ignore_index=True))
        commodity_row = summary.query("group == 'commodities' and horizon == 'weekly'").iloc[0]
        rates_row = summary.query("group == 'policy_money_market' and horizon == 'weekly'").iloc[0]

        self.assertIn("WTI原油（商品下跌）0.38%", commodity_row["commentary_cn"])
        self.assertIn("3个月HIBOR（利率下行）5.79bp", rates_row["commentary_cn"])
        self.assertNotIn("（商品下跌）+", commodity_row["commentary_cn"])
        self.assertNotIn("（商品下跌）-", commodity_row["commentary_cn"])
        self.assertNotIn("（利率下行）+", rates_row["commentary_cn"])
        self.assertNotIn("（利率下行）-", rates_row["commentary_cn"])
        self.assertIn("黄金 +0.20%", commodity_row["top_movers"])
        self.assertIn("WTI原油 -0.38%", commodity_row["bottom_movers"])
        self.assertIn("1年期LPR +1.25bp", rates_row["top_movers"])
        self.assertIn("3个月HIBOR -5.79bp", rates_row["bottom_movers"])

    def test_policy_money_market_wording_uses_rate_direction(self):
        frame = _frame("policy_money_market", [2.0, -1.0], names=["1年期LPR", "3个月HIBOR"])

        text = build_macro_divergence(frame).query("horizon == 'weekly'").iloc[0]["commentary_cn"]

        self.assertIn("1年期LPR（利率上行）", text)
        self.assertIn("3个月HIBOR（利率下行）", text)

    def test_policy_rate_commentary_distinguishes_tightening_and_easing(self):
        frame = _frame(
            "policy_rates",
            [25.0, -10.0],
            names=["美联储目标利率上限", "新西兰官方现金利率"],
            asset_class="policy_rate",
        )

        weekly = build_macro_divergence(frame).query("horizon == 'weekly'").iloc[0]

        self.assertEqual(weekly["group_cn"], "政策利率")
        self.assertIn("美联储目标利率上限（政策收紧、政策利率上调）25.00bp", weekly["commentary_cn"])
        self.assertIn("新西兰官方现金利率（政策宽松、政策利率下调）10.00bp", weekly["commentary_cn"])
        self.assertNotIn("）+", weekly["commentary_cn"])
        self.assertNotIn("）-", weekly["commentary_cn"])
        self.assertIn("美联储目标利率上限 +25.00bp", weekly["top_movers"])
        self.assertIn("新西兰官方现金利率 -10.00bp", weekly["bottom_movers"])

    def test_money_market_commentary_distinguishes_funding_rate_direction(self):
        frame = _frame(
            "money_market",
            [3.5, -2.25],
            names=["美元SOFR", "欧元短期利率"],
            asset_class="money_market",
        )

        weekly = build_macro_divergence(frame).query("horizon == 'weekly'").iloc[0]

        self.assertEqual(weekly["group_cn"], "货币市场利率")
        self.assertIn("美元SOFR（资金利率上行、政策传导趋紧）3.50bp", weekly["commentary_cn"])
        self.assertIn("欧元短期利率（资金利率下行、政策传导趋松）2.25bp", weekly["commentary_cn"])
        self.assertNotIn("）+", weekly["commentary_cn"])
        self.assertNotIn("）-", weekly["commentary_cn"])
        self.assertIn("美元SOFR +3.50bp", weekly["top_movers"])
        self.assertIn("欧元短期利率 -2.25bp", weekly["bottom_movers"])

    def test_foreign_exchange_commentary_uses_currency_wording(self):
        frame = _frame(
            "foreign_exchange",
            [0.004, -0.003],
            names=["美元指数", "美元兑人民币"],
            asset_class="foreign_exchange",
            unit="pct",
        )

        weekly = build_macro_divergence(frame).query("horizon == 'weekly'").iloc[0]

        self.assertEqual(weekly["group_cn"], "外汇")
        self.assertIn("美元指数（汇率上涨）0.40%", weekly["commentary_cn"])
        self.assertIn("美元兑人民币（汇率下跌）0.30%", weekly["commentary_cn"])
        self.assertNotIn("收益率", weekly["commentary_cn"])


if __name__ == "__main__":
    unittest.main()
