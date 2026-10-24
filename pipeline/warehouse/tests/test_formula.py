import math
import unittest

import numpy as np
import pandas as pd

from pipeline.warehouse.engine.formula import Context, FormulaError, RawSeries, evaluate, parse
from pipeline.warehouse.engine.weekly import compute, last_completed_friday


def frame(dates, values, realtime=None, source="backfill_estimate"):
    dates = pd.to_datetime(dates)
    realtime = dates if realtime is None else pd.to_datetime(realtime)
    return pd.DataFrame(
        {"obs_date": dates, "realtime_start": realtime, "value": values, "vintage_source": source}
    )


def daily(start, end, fn):
    dates = pd.bdate_range(start, end)
    return frame(dates, [fn(i, d) for i, d in enumerate(dates)])


def ctx(raw, cutoff, known=None, fast=False):
    cutoff = pd.Timestamp(cutoff)
    return Context(
        {k: RawSeries.from_frame(v) for k, v in raw.items()},
        cutoff,
        pd.Timestamp(known) if known else cutoff + pd.Timedelta(days=2),
        fast=fast,
    )


class WindowTests(unittest.TestCase):
    def setUp(self):
        # Price index growing 0.1% per business day from 100.
        self.raw = {"T:PX": daily("2024-01-01", "2026-10-30", lambda i, d: 100 * 1.001**i)}

    def test_level_respects_obs_cutoff(self):
        result = evaluate("{T:PX}", ctx(self.raw, "2026-10-23"))
        self.assertEqual(result.obs_date, pd.Timestamp("2026-10-23"))

    def test_weekly_return(self):
        result = evaluate('ret({T:PX}, "W")', ctx(self.raw, "2026-10-23"))
        self.assertAlmostEqual(result.value, (1.001**5 - 1) * 100, places=8)

    def test_ytd_uses_previous_year_end(self):
        c = ctx(self.raw, "2026-10-23")
        result = evaluate('ret({T:PX}, "YTD")', c)
        px = self.raw["T:PX"].set_index("obs_date")["value"]
        expected = (px["2026-10-23"] / px["2025-12-31"] - 1) * 100
        self.assertAlmostEqual(result.value, expected, places=8)

    def test_mtd_anchor_is_previous_month_end(self):
        result = evaluate('ret({T:PX}, "MTD")', ctx(self.raw, "2026-10-02"))
        self.assertIn("2026-09-30", result.detail)

    def test_change_in_bp(self):
        raw = {"T:Y": frame(["2026-10-16", "2026-10-23"], [4.10, 4.235])}
        result = evaluate('chg({T:Y}, "W") * 100', ctx(raw, "2026-10-23"))
        self.assertAlmostEqual(result.value, 13.5, places=8)

    def test_snapshot_previous_month_end(self):
        result = evaluate('snap({T:PX}, "ME")', ctx(self.raw, "2026-10-23"))
        self.assertEqual(result.obs_date, pd.Timestamp("2026-09-30"))

    def test_insufficient_history_is_explicit(self):
        raw = {"T:Y": frame(["2026-10-16", "2026-10-23"], [1.0, 2.0])}
        result = evaluate('pctile({T:Y}, "3Y")', ctx(raw, "2026-10-23"))
        self.assertIsNone(result.value)
        self.assertEqual(result.status, "insufficient_history")

    def test_percentile_of_maximum_is_100(self):
        result = evaluate('pctile({T:PX}, "1Y")', ctx(self.raw, "2026-10-23"))
        self.assertAlmostEqual(result.value, 100.0)

    def test_volatility_of_constant_growth_is_zero(self):
        result = evaluate('vol({T:PX}, "52W")', ctx(self.raw, "2026-10-23"))
        self.assertLess(result.value, 0.01)

    def test_drawdown(self):
        raw = {"T:P": frame(["2026-01-02", "2026-01-09", "2026-01-16"], [100.0, 120.0, 90.0])}
        result = evaluate("drawdown({T:P})", ctx(raw, "2026-01-16"))
        self.assertAlmostEqual(result.value, -25.0)


class SeriesTransformTests(unittest.TestCase):
    def setUp(self):
        months = pd.date_range("2023-01-01", "2026-09-01", freq="MS")
        values = [100 * 1.002**i for i in range(len(months))]
        # Monthly CPI published ~45 days after the reference month.
        self.raw = {"T:CPI": frame(months, values, realtime=months + pd.Timedelta(days=45))}

    def test_yoy_monthly(self):
        result = evaluate("yoy({T:CPI})", ctx(self.raw, "2026-10-23"))
        self.assertAlmostEqual(result.value, (1.002**12 - 1) * 100, places=8)

    def test_known_cutoff_hides_unpublished_month(self):
        # On 2026-10-09 the September print (known 10-16) is not yet out.
        result = evaluate("yoy({T:CPI})", ctx(self.raw, "2026-10-09"))
        self.assertEqual(result.obs_date, pd.Timestamp("2026-08-01"))

    def test_annualized_three_month(self):
        result = evaluate("ann({T:CPI}, 3)", ctx(self.raw, "2026-10-23"))
        self.assertAlmostEqual(result.value, (1.002**12 - 1) * 100, places=8)

    def test_fiscal_year_to_date_sum(self):
        months = pd.date_range("2025-08-01", "2026-01-01", freq="MS")
        raw = {"T:DEF": frame(months, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])}
        # FY2026 starts Oct 2025: Oct+Nov+Dec+Jan = 3+4+5+6
        result = evaluate("fytd({T:DEF})", ctx(raw, "2026-03-06"))
        self.assertAlmostEqual(result.value, 18.0)

    def test_spread_uses_same_dates(self):
        raw = {
            "T:A": frame(["2026-10-21", "2026-10-22", "2026-10-23"], [5.0, 5.1, 5.2]),
            "T:B": frame(["2026-10-21", "2026-10-22"], [4.0, 4.0]),
        }
        result = evaluate("({T:A} - {T:B}) * 100", ctx(raw, "2026-10-23"))
        self.assertEqual(result.obs_date, pd.Timestamp("2026-10-22"))
        self.assertAlmostEqual(result.value, 110.0)

    def test_moving_sum(self):
        weeks = pd.date_range("2026-09-04", periods=6, freq="W-FRI")
        raw = {"T:F": frame(weeks, [1, 2, 3, 4, 5, 6])}
        result = evaluate("msum({T:F}, 4)", ctx(raw, "2026-10-09"))
        self.assertAlmostEqual(result.value, 3 + 4 + 5 + 6)


class VintageTests(unittest.TestCase):
    def setUp(self):
        # Two releases: Aug value first printed 1.0 (2026-09-10), revised to 1.2 on 2026-10-10
        # when Sep was first printed at 2.0.
        self.raw = {
            "T:M": frame(
                ["2026-07-01", "2026-08-01", "2026-08-01", "2026-09-01"],
                [0.5, 1.0, 1.2, 2.0],
                realtime=["2026-08-10", "2026-09-10", "2026-10-10", "2026-10-10"],
                source="provider",
            )
        }

    def test_prior_as_listed_in_latest_release(self):
        result = evaluate("prior({T:M})", ctx(self.raw, "2026-10-16"))
        self.assertAlmostEqual(result.value, 1.2)

    def test_first_release(self):
        result = evaluate("first({T:M})", ctx(self.raw, "2026-10-16"))
        self.assertAlmostEqual(result.value, 2.0)

    def test_revision_to_previous_period(self):
        result = evaluate("rev({T:M}, 1)", ctx(self.raw, "2026-10-16"))
        self.assertAlmostEqual(result.value, 0.2)

    def test_point_in_time_before_revision(self):
        result = evaluate("{T:M}", ctx(self.raw, "2026-09-18"))
        self.assertAlmostEqual(result.value, 1.0)

    def test_backfilled_series_has_no_vintage(self):
        raw = {"T:X": frame(["2026-08-01", "2026-09-01"], [1.0, 2.0])}
        result = evaluate("prior({T:X})", ctx(raw, "2026-10-16"))
        self.assertEqual(result.status, "no_vintage")


class ParserTests(unittest.TestCase):
    def test_rejects_unknown_functions(self):
        with self.assertRaises(FormulaError):
            parse("__import__('os')")

    def test_collects_series(self):
        self.assertEqual(parse('ret({FRED:SP500}, "W") - ret({FRED:DJIA}, "W")').series, ("FRED:SP500", "FRED:DJIA"))


class WeeklyComputeTests(unittest.TestCase):
    def test_fast_and_exact_agree_without_revisions(self):
        raw = {"T:PX": daily("2025-01-01", "2026-10-30", lambda i, d: 50 + math.sin(i / 7.0))}
        formulas = {"a": 'ret({T:PX}, "W")', "b": 'pctile({T:PX}, "1Y")', "c": "{T:PX}"}
        cutoffs = list(pd.date_range("2026-06-05", "2026-10-23", freq="W-FRI"))
        fast = compute(formulas, raw, cutoffs, fast=True)
        exact = compute(formulas, raw, cutoffs, fast=False)
        for f, e in zip(fast, exact):
            self.assertEqual((f.indicator_id, f.week_cutoff, f.status), (e.indicator_id, e.week_cutoff, e.status))
            self.assertTrue(np.isclose(f.value, e.value))

    def test_last_completed_friday(self):
        from datetime import datetime, timezone

        self.assertEqual(
            last_completed_friday(datetime(2026, 10, 24, 12, tzinfo=timezone.utc)), pd.Timestamp("2026-10-23")
        )
        self.assertEqual(
            last_completed_friday(datetime(2026, 10, 23, 12, tzinfo=timezone.utc)), pd.Timestamp("2026-10-16")
        )


if __name__ == "__main__":
    unittest.main()


class StalenessTests(unittest.TestCase):
    def test_old_observation_is_flagged_stale(self):
        raw = {"T:F": frame(["2024-04-05"], [86.9])}
        [v] = compute({"x": "{T:F}"}, raw, [pd.Timestamp("2026-10-23")], fast=True, max_age_days={"x": 14})
        self.assertEqual(v.status, "stale")
        self.assertEqual(v.value, 86.9)


class ParBondTests(unittest.TestCase):
    def test_flat_curve_unchanged_scenario_earns_coupon(self):
        from pipeline.warehouse.engine.formula import PAR_KEYS

        raw = {key: frame(["2026-10-22", "2026-10-23"], [4.0, 4.0]) for key in PAR_KEYS.values()}
        self.assertEqual(set(parse('parbond("tr", 10, 0)').series), set(PAR_KEYS.values()))
        tr = evaluate('parbond("tr", 10, 0)', ctx(raw, "2026-10-23"))
        down = evaluate('parbond("tr", 10, -50)', ctx(raw, "2026-10-23"))
        dur = evaluate('parbond("duration", 10, 0)', ctx(raw, "2026-10-23"))
        self.assertAlmostEqual(tr.value, 4.04, places=2)
        self.assertGreater(down.value, tr.value)
        self.assertAlmostEqual(dur.value, 8.18, places=2)
