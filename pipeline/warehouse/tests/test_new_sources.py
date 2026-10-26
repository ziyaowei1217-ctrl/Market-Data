"""Sources added on 2026-10-26 to fill macro, fund-flow and energy gaps (no network)."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from pipeline.warehouse.providers.base import SeriesDef


def sdef(provider: str, code: str, frequency: str = "M", **params) -> SeriesDef:
    return SeriesDef(key=f"{provider}:{code}", provider=provider, code=code, params=params, frequency=frequency)


class ManualTableTests(unittest.TestCase):
    def test_reads_rows_by_series_key_and_ignores_blank_values(self):
        from pipeline.warehouse.providers.manual import ManualTable

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "elections.csv").write_text(
                "series_key,obs_date,value,source_url,note\n"
                "MANUAL:election:EE,2026-10-26,20270307,https://www.valimised.ee/en/riigikogu-elections-2027,fixed\n"
                "MANUAL:election:FR,2026-07-01,20270418,https://example.org/fr,first round\n"
                "MANUAL:election:ES,2026-10-26,,https://example.org/es,not announced\n",
                encoding="utf-8")
            provider = ManualTable(env={"MANUAL_DIR": tmp})
            results = {r.key: r for r in provider.fetch([sdef("MANUAL", "election:EE", "A"), sdef("MANUAL", "election:FR", "A"),
                                                         sdef("MANUAL", "election:ES", "A")], date(2020, 1, 1))}
        self.assertEqual([(o.obs_date, o.value) for o in results["MANUAL:election:EE"].observations], [(date(2026, 10, 26), 20270307.0)])
        self.assertEqual(results["MANUAL:election:FR"].observations[0].obs_date, date(2026, 7, 1))
        self.assertEqual(results["MANUAL:election:ES"].status, "empty")

    def test_checked_in_tables_parse(self):
        from pipeline.warehouse.catalog.mapping import load_series
        from pipeline.warehouse.providers.manual import ManualTable

        defs = [SeriesDef(key=s["key"], provider=s["provider"], code=s["code"], frequency=s["frequency"])
                for s in load_series() if s["provider"] == "MANUAL"]
        self.assertTrue(defs)
        results = ManualTable(env={}).fetch(defs, date(2020, 1, 1))
        self.assertTrue(all(r.status in ("ok", "empty") for r in results), [(r.key, r.message) for r in results])


ISM_SERVICES_SAMPLE = """
      Services at a Glance                               with a reading of 50.1 percent, a
      INDEX        Sep  Aug % Point Direction Rate of Trend* the 47.8 percent recorded in August.
                   Index Index Change       Change (months)
      Services PMI® 54.9 55.4 -0.5 Growing  Slower  27   tered 53.2 percent, 1.9 percentage
      Business Activity 56.5 61.7 -5.2 Growing Slower 27 points higher than the 51.3 percent
      New Orders   59.8 60.9 -1.1  Growing  Slower  16   recorded in August. This is the 22nd
      Employment   50.1 47.8 +2.3  Growing From Contracting 1
      Supplier Deliveries 53.2 51.3 +1.9 Slowing Faster 22
      Inventories  51.0 49.6 +1.4  Growing From Contracting 1
      Prices       69.4 68.1 +1.3  Increasing Faster 112
      New Export Orders 48.3 50.2 -1.9 Contracting From Growing 1
      Inventory Sentiment 55.0 54.1 +0.9 Too High Faster 3
"""


class IsmServicesTests(unittest.TestCase):
    def test_glance_rows(self):
        from pipeline.warehouse.providers.files import ISM_SERVICES_ROWS, parse_ism

        rows = parse_ism(ISM_SERVICES_SAMPLE, ISM_SERVICES_ROWS)
        self.assertEqual(rows, {"pmi": (54.9, 55.4), "new_orders": (59.8, 60.9), "employment": (50.1, 47.8),
                                "prices": (69.4, 68.1), "inventories": (51.0, 49.6)})

    def test_mapping_uses_services_report(self):
        from pipeline.warehouse.catalog.mapping import load_mapping

        m = load_mapping()
        self.assertEqual(m["36-006"]["formula"], "{ISMS:pmi}")
        self.assertEqual(m["36-012"]["formula"], "{ISMS:new_orders} - {ISMS:inventories}")


class SteoHistoryTests(unittest.TestCase):
    def test_forecast_months_are_dropped(self):
        from unittest import mock

        from pipeline.warehouse.providers import official
        from pipeline.warehouse.tests.test_pipeline import FakeSession

        payload = {"response": {"data": [{"period": p, "value": v} for p, v in
                                         [("2027-01", 2.4), ("2026-10", 0.02), ("2026-09", 0.03), ("2026-08", 0.02)]]}}
        provider = official.Eia(session=FakeSession({"seriesid/STEO.COPS_OPEC.M": payload}), env={"EIA_API_KEY": "k"})
        d = SeriesDef(key="EIA:STEO.COPS_OPEC.M", provider="EIA", code="STEO.COPS_OPEC.M", params={"history_only": True}, frequency="M")
        with mock.patch.object(official, "_today", return_value=date(2026, 10, 26)):
            obs = provider.fetch([d], date(2026, 1, 1))[0].observations
        self.assertEqual([o.obs_date for o in obs], [date(2026, 8, 1), date(2026, 9, 1)])


class OecdTests(unittest.TestCase):
    def test_sdmx_csv(self):
        from pipeline.warehouse.providers.official import Oecd
        from pipeline.warehouse.tests.test_pipeline import FakeSession

        csv_body = ("STRUCTURE,STRUCTURE_ID,REF_AREA,Reference area,TIME_PERIOD,Time period,OBS_VALUE,Observation value\n"
                    "DATAFLOW,X,IND,India,2026-08,,4.96261,\n"
                    "DATAFLOW,X,IND,India,2025-04,,2.941176,\n")
        code = "OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,1.0/IND.M.N.CPI.PA._T.N.GY"
        provider = Oecd(session=FakeSession({"sdmx.oecd.org": csv_body}))
        r = provider.fetch([SeriesDef(key="OECD:" + code, provider="OECD", code=code, frequency="M")], date(2025, 1, 1))[0]
        self.assertEqual([(o.obs_date, o.value) for o in r.observations], [(date(2025, 4, 1), 2.941176), (date(2026, 8, 1), 4.96261)])


class FuturesCurveTests(unittest.TestCase):
    def test_expiry_rules(self):
        from pipeline.warehouse.providers.futures import expiry

        # WTI: 3 business days before the 25th of the prior month (25 Nov 2026 is a Wednesday)
        self.assertEqual(expiry("CL", 2026, 12), date(2026, 11, 20))
        # 25 Oct 2026 is a Sunday: count back from Friday 23 Oct
        self.assertEqual(expiry("CL", 2026, 11), date(2026, 10, 20))
        # Brent (BZ / ICE): last business day of the second month before delivery
        self.assertEqual(expiry("BZ", 2027, 1), date(2026, 11, 30))
        self.assertEqual(expiry("BZ", 2026, 12), date(2026, 10, 30))

    def test_nth_nearby_picks_unexpired_contracts_in_order(self):
        from pipeline.warehouse.providers.futures import nth_nearby

        closes = {
            ("CL", 2026, 11): {date(2026, 10, 19): 60.0, date(2026, 10, 20): 61.0},
            ("CL", 2026, 12): {date(2026, 10, 19): 60.5, date(2026, 10, 20): 61.5, date(2026, 10, 21): 62.0},
            ("CL", 2027, 1): {date(2026, 10, 19): 61.0, date(2026, 10, 20): 62.0, date(2026, 10, 21): 62.4},
        }
        first = nth_nearby("CL", closes, 1)
        second = nth_nearby("CL", closes, 2)
        self.assertEqual(first[date(2026, 10, 20)], 61.0)   # Nov contract still trades on its last day
        self.assertEqual(first[date(2026, 10, 21)], 62.0)   # then Dec is the front month
        self.assertEqual(second[date(2026, 10, 21)], 62.4)
        self.assertNotIn(date(2026, 10, 21), nth_nearby("CL", closes, 3))  # Feb 2027 not loaded: no value

    def test_yahoo_ticker(self):
        from pipeline.warehouse.providers.futures import ticker

        self.assertEqual(ticker("CL", 2026, 12), "CLZ26.NYM")
        self.assertEqual(ticker("BZ", 2027, 1), "BZF27.NYM")


class BeaDirectInvestmentTests(unittest.TestCase):
    def test_rows_by_series_and_country(self):
        from pipeline.warehouse.providers.official import BeaDirectInvestment
        from pipeline.warehouse.tests.test_pipeline import FakeSession

        rows = [{"Year": "2024", "SeriesID": "23", "RowCode": "000", "DataValueUnformatted": "270004"},
                {"Year": "2024", "SeriesID": "22", "RowCode": "000", "DataValueUnformatted": "5598455"},
                {"Year": "2023", "SeriesID": "22", "RowCode": "399", "DataValueUnformatted": "3000000"},
                {"Year": "2024", "SeriesID": "22", "RowCode": "399", "DataValueUnformatted": "(D)"}]
        session = FakeSession({"apps.bea.gov/api/data": {"BEAAPI": {"Results": {"Data": rows}}}})
        provider = BeaDirectInvestment(session=session, env={"BEA_API_KEY": "k"})
        defs = [SeriesDef(key=f"BEADI:{c}", provider="BEADI", code=c, frequency="A") for c in ("23:000", "22:000", "22:399")]
        out = {r.key: r for r in provider.fetch(defs, date(2015, 1, 1))}
        self.assertEqual([(o.obs_date, o.value) for o in out["BEADI:22:000"].observations], [(date(2024, 1, 1), 5598455.0)])
        self.assertEqual([(o.obs_date, o.value) for o in out["BEADI:22:399"].observations], [(date(2023, 1, 1), 3000000.0)])
        params = session.calls[0][1]
        self.assertEqual((params["DataSetName"], params["DirectionOfInvestment"], params["Classification"]), ("MNE", "inward", "Country"))
        self.assertEqual(set(params["SeriesID"].split(",")), {"22", "23"})
        self.assertEqual(set(params["Country"].split(",")), {"000", "399"})


def frame(csv_text: str):
    import io

    import pandas as pd

    return pd.read_csv(io.StringIO(csv_text), header=None, dtype=str, keep_default_na=False)


class MhlwRealWageTests(unittest.TestCase):
    # first rows of sheet 賃金指数 in 2608p.xlsx (August 2026 preliminary); month rows after the first are synthetic
    SHEET = (",,,前年比,実質前年比,,前年比,実質前年比\n"
             "2022年,,102.3,2,-1,102.8,2.3,-0.7\n"
             "2025年７月,,130.9,3.4,-0.2,132.3,4,0.5\n"
             "８月,,99.0,3.0,0.4,99.1,3.1,0.6\n"
             "2026年１月,,94.2,2.5,0.7,92.9,2.9,1.1\n"
             ",７月,131.5,4.3,2.0,132.0,3.8,1.5\n"
             "2022年,,101.9,1.4,-1.6,102.3,1.6,-1.4\n"
             "2025年７月,,110.5,2.1,-1.4,109.8,2.5,-1\n"
             "注：実質前年比は、名目賃金指数を消費者物価指数で除して算出\n")

    def test_first_block_real_yoy_by_month(self):
        from pipeline.warehouse.providers.files import parse_mhlw_real_wages

        out = parse_mhlw_real_wages(frame(self.SHEET))
        self.assertEqual(out, {date(2025, 7, 1): -0.2, date(2025, 8, 1): 0.4, date(2026, 1, 1): 0.7, date(2026, 7, 1): 2.0})

    def test_japanese_era_labels(self):
        from pipeline.warehouse.providers.files import parse_mhlw_real_wages

        sheet = (",,,前年比,実質前年比\n令和３年,,100.0,0.3,-0.1\n令和６年８月,,93,2.8,-0.8\n９月,,91.6,2.5,-0.4\n"
                 "令和７年１月,,90.0,2.0,-1.8\n８月(速報),,94.4,1.5,-1.4\n令和３年,,99.0,0.1,-0.3\n")
        self.assertEqual(parse_mhlw_real_wages(frame(sheet)), {date(2024, 8, 1): -0.8, date(2024, 9, 1): -0.4,
                                                               date(2025, 1, 1): -1.8, date(2025, 8, 1): -1.4})

    def test_urls_use_reiwa_year_folders(self):
        from pipeline.warehouse.providers.files import mhlw_url

        self.assertEqual(mhlw_url(date(2026, 8, 1)), "https://www.mhlw.go.jp/toukei/itiran/roudou/monthly/r08/2608p/xls/2608p.xlsx")
        self.assertEqual(mhlw_url(date(2019, 6, 1)), "https://www.mhlw.go.jp/toukei/itiran/roudou/monthly/r01/1906p/xls/1906p.xlsx")


class DmpTests(unittest.TestCase):
    PRICE = (",Realised price growth over the past year (%),,,,,Expected price growth over the next year (%),,\n"
             "Survey date,Mean realised price growth (%),,,Distribution,,Mean expected price growth (%),,\n"
             ",Single month,Quarterly average,,5th percentile,,Single month,Quarterly average,\n"
             "Sep-25,3.9,4.0,,-1,,3.6,3.7,\n"
             "Oct-25,3.8,3.9,,-1,,3.5,3.6,\n")

    def test_quarterly_average_of_each_group(self):
        from pipeline.warehouse.providers.files import parse_dmp_sheet

        self.assertEqual(parse_dmp_sheet(frame(self.PRICE), "expected"), {date(2025, 9, 1): 3.7, date(2025, 10, 1): 3.6})
        self.assertEqual(parse_dmp_sheet(frame(self.PRICE), "realised"), {date(2025, 9, 1): 4.0, date(2025, 10, 1): 3.9})

    def test_release_url(self):
        from pipeline.warehouse.providers.files import dmp_url

        self.assertEqual(dmp_url(date(2026, 9, 1)),
                         "https://www.bankofengland.co.uk/-/media/boe/files/decision-maker-panel-survey/2026/monthly-dmp-data-september-2026.xlsx")


class ComputedMethodsTests(unittest.TestCase):
    def test_manual_indicators_with_a_formula_are_computed(self):
        from pipeline.warehouse.runner import formulas_for

        formulas = formulas_for()
        self.assertIn("108-008", formulas)   # Estonia election date (official, fixed)
        self.assertNotIn("108-001", formulas)  # Spain: no date announced yet


if __name__ == "__main__":
    unittest.main()
