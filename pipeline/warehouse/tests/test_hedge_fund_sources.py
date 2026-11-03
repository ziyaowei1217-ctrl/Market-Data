"""Hedge fund leverage and financing sources added on 2026-11-03 (no network):
OFR Hedge Fund Monitor (Form PF, CFTC TFF in 10-year equivalents, FICC sponsored repo,
SCOOS), Fed Z.1 hedge fund lines via FRED, TIC Cayman Islands and FINRA margin balances."""

from __future__ import annotations

import io
import unittest
from datetime import date

import openpyxl
import pandas as pd

from pipeline.warehouse.engine.formula import Context, RawSeries, evaluate
from pipeline.warehouse.tests.test_pipeline import FakeSession, sd

FINRA_HEADER = ["Year-Month", "Debit Balances in Customers' Securities Margin Accounts",
                "Free Credit Balances in Customers' Cash Accounts",
                "Free Credit Balances in Customers' Securities Margin Accounts"]


def finra_workbook(rows, header=FINRA_HEADER, title="Customer Margin Balances") -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title
    ws.append(header)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class OfrHedgeFundMonitorTests(unittest.TestCase):
    def test_timeseries_skips_nulls_and_rows_before_start(self):
        from pipeline.warehouse.providers.official import OfrHedgeFundMonitor

        rows = [["2025-12-31", 39148000000000.0], ["2026-03-31", None], ["2026-06-30", 45193000000000.0]]
        session = FakeSession({"hf/v1/series/timeseries": rows})
        [res] = OfrHedgeFundMonitor(session, env={}).fetch([sd("OFR", "FPF-ALLQHF_GNE_SUM", frequency="Q")],
                                                            date(2026, 1, 1))
        self.assertEqual(res.status, "ok")
        self.assertEqual([(o.obs_date, o.value) for o in res.observations], [(date(2026, 6, 30), 45193000000000.0)])
        url, params = session.calls[0]
        self.assertIn("data.financialresearch.gov/hf/v1/series/timeseries", url)
        self.assertEqual(params["mnemonic"], "FPF-ALLQHF_GNE_SUM")
        self.assertEqual(params["start_date"], "2026-01-01")

    def test_unexpected_payload_is_an_error(self):
        from pipeline.warehouse.providers.official import OfrHedgeFundMonitor

        session = FakeSession({"hf/v1/series/timeseries": {"error": "unknown mnemonic"}})
        [res] = OfrHedgeFundMonitor(session, env={}).fetch([sd("OFR", "FPF-NOPE")], date(2026, 1, 1))
        self.assertEqual(res.status, "error")
        self.assertIn("FPF-NOPE", res.message)


class FinraMarginTests(unittest.TestCase):
    def test_columns_by_code_sorted_by_month(self):
        from pipeline.warehouse.providers.files import FinraMargin

        body = finra_workbook([["2026-09", 1480054, 215328, 218581], ["2026-08", "1,453,832", 207641, 217499],
                               ["1997-01", 103337, 68856, None]])
        session = FakeSession({"margin-statistics.xlsx": body})
        res = {r.key: r for r in FinraMargin(session, env={}).fetch(
            [sd("FINRA", "debit_margin", frequency="M"), sd("FINRA", "free_credit_margin", frequency="M")],
            date(2026, 1, 1))}
        self.assertEqual([(o.obs_date, o.value) for o in res["FINRA:debit_margin"].observations],
                         [(date(2026, 8, 1), 1453832.0), (date(2026, 9, 1), 1480054.0)])
        self.assertEqual(res["FINRA:free_credit_margin"].observations[-1].value, 218581.0)

    def test_changed_layout_is_reported(self):
        from pipeline.warehouse.providers.files import FinraMargin

        body = finra_workbook([["2026-09", 1480054, 215328, 218581]], header=["Month", "Debit", "Cash", "Margin"])
        session = FakeSession({"margin-statistics.xlsx": body})
        [res] = FinraMargin(session, env={}).fetch([sd("FINRA", "debit_margin", frequency="M")], date(2026, 1, 1))
        self.assertEqual(res.status, "error")
        self.assertIn("layout", res.message)


class TicCaymanTests(unittest.TestCase):
    def test_cayman_row(self):
        from pipeline.warehouse.providers.files import TicTable5

        txt = ("Table 5\r\nCountry\t2026-08\t2026-07\r\nCayman Islands\t463.0\t460.1\r\nGrand Total\t9331.7\t9248.4\r\n")
        session = FakeSession({"slt_table5.txt": txt})
        [res] = TicTable5(session, env={}).fetch([sd("TIC", "Cayman Islands")], date(2026, 1, 1))
        self.assertEqual([(o.obs_date, o.value) for o in res.observations],
                         [(date(2026, 7, 1), 460.1), (date(2026, 8, 1), 463.0)])


class HedgeFundMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pipeline.warehouse.catalog.build_catalog import load_catalog
        from pipeline.warehouse.catalog.mapping import load_mapping, load_series

        cls.catalog = {r["indicator_id"]: r for r in load_catalog()}
        cls.mapping = load_mapping()
        cls.series = {s["key"]: s for s in load_series()}

    def test_block_46_is_in_the_catalog_and_computed(self):
        block = sorted(i for i in self.catalog if i.startswith("46-"))
        self.assertEqual(block, [f"46-{i:03d}" for i in range(1, 38)])
        for iid in block:
            self.assertEqual(self.catalog[iid]["module"], "资金流仓位", iid)
            self.assertTrue(self.catalog[iid]["unit"], iid)
            self.assertEqual(self.mapping[iid]["method"], "api", iid)
            self.assertTrue(self.mapping[iid]["coverage_note"], iid)

    def test_key_formulas(self):
        self.assertEqual(self.mapping["46-004"]["formula"], "{OFR:FPF-ALLQHF_GNE_SUM} / {OFR:FPF-ALLQHF_NAV_SUM}")
        self.assertEqual(self.mapping["46-020"]["formula"], "{OFR:TFF-LF_TREAS_NET_POS10YREQV} / 1e9")
        self.assertEqual(self.mapping["46-022"]["formula"], "ma({OFR:FICC-SPONSORED_REPO_VOL}, 20) / 1e9")
        self.assertEqual(self.mapping["46-032"]["formula"], "{TIC:Cayman Islands}")
        self.assertEqual(self.mapping["46-034"]["formula"], "{FINRA:debit_margin} / 1000")

    def test_series_registry(self):
        for key, freq in [("OFR:FPF-ALLQHF_GNE_SUM", "Q"), ("OFR:TFF-LF_TREAS_NET_POS10YREQV", "W"),
                          ("OFR:FICC-SPONSORED_REPO_VOL", "D"), ("OFR:SCOOS-NET_HF_LEVERAGEUSE", "Q"),
                          ("FRED:BOGZ1FL622000623Q", "Q"), ("TIC:Cayman Islands", "M"), ("FINRA:debit_margin", "M")]:
            self.assertIn(key, self.series)
            self.assertEqual(self.series[key]["frequency"], freq, key)
        self.assertGreaterEqual(self.series["OFR:FPF-ALLQHF_GNE_SUM"]["release_lag_days"], 120)

    def test_gross_leverage_from_form_pf(self):
        dates = pd.to_datetime(["2026-03-31", "2026-06-30"])
        known = pd.to_datetime(["2026-08-01", "2026-11-01"])

        def raw(values):
            return pd.DataFrame({"obs_date": dates, "realtime_start": known, "value": values,
                                 "vintage_source": "backfill_estimate"})

        series = {"OFR:FPF-ALLQHF_GNE_SUM": raw([42291e9, 45193e9]), "OFR:FPF-ALLQHF_NAV_SUM": raw([4994e9, 5511e9])}
        ctx = Context({k: RawSeries.from_frame(v) for k, v in series.items()}, pd.Timestamp("2026-10-30"),
                      pd.Timestamp("2026-11-03"))
        result = evaluate(self.mapping["46-004"]["formula"], ctx)
        self.assertEqual(result.obs_date, pd.Timestamp("2026-06-30"))
        self.assertAlmostEqual(result.value, 45193 / 5511, places=6)


if __name__ == "__main__":
    unittest.main()
