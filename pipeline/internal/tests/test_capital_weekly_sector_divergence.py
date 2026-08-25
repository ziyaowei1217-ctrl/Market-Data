import unittest

import pandas as pd

from pipeline.internal.capital_weekly.sector_divergence import add_return_ranks, build_divergence_summary


def _frame(weekly_returns):
    names = ["信息技术", "医药卫生", "工业", "能源"]
    return pd.DataFrame(
        {
            "market": ["US"] * len(weekly_returns),
            "sector_name_cn": names[: len(weekly_returns)],
            "sort_order": list(range(1, len(weekly_returns) + 1)),
            "daily_change": weekly_returns,
            "weekly_change": weekly_returns,
            "mtd_change": weekly_returns,
            "ytd_change": weekly_returns,
        }
    )


class SectorDivergenceTests(unittest.TestCase):
    def test_summary_calculates_weekly_divergence_metrics_and_commentary(self):
        frame = _frame([0.04, 0.01, 0.00, -0.02])

        ranked = add_return_ranks(frame)
        summary = build_divergence_summary(ranked)
        weekly = summary.loc[summary["horizon"] == "weekly"].iloc[0]

        self.assertEqual(ranked["weekly_rank"].tolist(), [1, 2, 3, 4])
        self.assertEqual(weekly["positive_count"], 2)
        self.assertEqual(weekly["flat_count"], 1)
        self.assertEqual(weekly["negative_count"], 1)
        self.assertAlmostEqual(weekly["breadth_ratio"], 0.5)
        self.assertAlmostEqual(weekly["leader_laggard_spread"], 0.06)
        self.assertAlmostEqual(weekly["dispersion"], frame["weekly_change"].std(ddof=0))
        self.assertEqual(weekly["top_3"], "信息技术 4.00%; 医药卫生 1.00%; 工业 0.00%")
        self.assertIn("4个行业中2个上涨", weekly["commentary_cn"])

    def test_add_return_ranks_uses_dense_ranks_for_ties(self):
        ranked = add_return_ranks(_frame([0.02, 0.02, -0.01]))

        self.assertEqual(ranked["weekly_rank"].tolist(), [1, 1, 2])

    def test_summary_flags_all_missing_horizon_as_insufficient_data(self):
        frame = _frame([0.01, 0.00, -0.01])
        frame["mtd_change"] = None

        summary = build_divergence_summary(add_return_ranks(frame))
        mtd = summary.loc[summary["horizon"] == "mtd"].iloc[0]

        self.assertEqual(mtd["qc_flag"], "INSUFFICIENT_DATA")
        self.assertTrue(pd.isna(mtd["breadth_ratio"]))
        self.assertTrue(pd.isna(mtd["leader_laggard_spread"]))
        self.assertTrue(pd.isna(mtd["dispersion"]))

    def test_failed_rows_with_numeric_returns_are_excluded_from_ranks_and_summary(self):
        frame = _frame([0.04, 0.01, 0.00, 0.99])
        frame["qc_flag"] = ["OK", "OK", "OK", "FETCH_FAILED"]

        ranked = add_return_ranks(frame)
        summary = build_divergence_summary(ranked)
        weekly = summary.loc[summary["horizon"] == "weekly"].iloc[0]

        self.assertEqual(ranked["weekly_rank"].iloc[:3].tolist(), [1, 2, 3])
        self.assertTrue(pd.isna(ranked["weekly_rank"].iloc[3]))
        self.assertEqual(weekly["valid_count"], 3)
        self.assertEqual(weekly["positive_count"], 2)
        self.assertEqual(weekly["flat_count"], 1)
        self.assertEqual(weekly["negative_count"], 0)
        self.assertAlmostEqual(weekly["leader_laggard_spread"], 0.04)
        self.assertNotIn("能源", weekly["top_3"])
        self.assertNotIn("能源", weekly["commentary_cn"])


if __name__ == "__main__":
    unittest.main()
