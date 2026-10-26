import json
import unittest
from datetime import date

import pandas as pd

from pipeline.warehouse.db.store import Observation, SQLiteStore, plan_new_rows
from pipeline.warehouse.engine.weekly import compute
from pipeline.warehouse.providers import official
from pipeline.warehouse.providers.base import SeriesDef
from pipeline.warehouse import runner


class FakeResponse:
    def __init__(self, body: bytes, url: str, status: int = 200):
        self.content = body
        self.url = url
        self.status_code = status
        self.headers = {"Content-Type": "application/octet-stream"}

    def json(self):
        return json.loads(self.content)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise OSError(self.status_code)


class FakeSession:
    """Routes requests by URL substring to canned bodies; records calls."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []
        self.headers = {}

    def _route(self, url, params):
        self.calls.append((url, params))
        for needle, body in self.routes.items():
            if needle in url:
                payload = body(params) if callable(body) else body
                if isinstance(payload, (dict, list)):
                    payload = json.dumps(payload)
                if isinstance(payload, str):
                    payload = payload.encode()
                return FakeResponse(payload, url)
        return FakeResponse(b"not found", url, 404)

    def get(self, url, params=None, **kwargs):
        return self._route(url, params)

    def post(self, url, json=None, **kwargs):
        return self._route(url, json)


def sd(provider, code, **kw):
    return SeriesDef(key=f"{provider}:{code}", provider=provider, code=code, **kw)


START = date(2026, 1, 1)


class ProviderParsingTests(unittest.TestCase):
    def test_fred_csv_without_key(self):
        session = FakeSession({"fredgraph.csv": "observation_date,DGS10\n2026-10-22,4.01\n2026-10-23,.\n"})
        [res] = official.Fred(session, env={}).fetch([sd("FRED", "DGS10")], START)
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.observations, [Observation(date(2026, 10, 22), 4.01)])

    def test_fred_api_with_vintages(self):
        payload = {"observations": [
            {"realtime_start": "2026-09-05", "realtime_end": "2026-10-02", "date": "2026-08-01", "value": "159000"},
            {"realtime_start": "2026-10-03", "realtime_end": "9999-12-31", "date": "2026-08-01", "value": "159050"},
        ]}
        session = FakeSession({"api.stlouisfed.org": payload})
        provider = official.Fred(session, env={"FRED_API_KEY": "k"})
        official.time.sleep = lambda s: None
        [res] = provider.fetch([sd("FRED", "PAYEMS", vintages=True)], START)
        self.assertEqual([o.realtime_start for o in res.observations], [date(2026, 9, 5), date(2026, 10, 3)])
        self.assertEqual(session.calls[0][1]["realtime_start"], "1776-07-04")

    def test_nyfed_rates(self):
        payload = {"refRates": [
            {"effectiveDate": "2026-10-23", "type": "SOFR", "percentRate": 4.02, "volumeInBillions": 2900},
            {"effectiveDate": "2026-10-22", "type": "SOFR", "percentRate": 4.01, "volumeInBillions": 2850},
        ]}
        session = FakeSession({"markets.newyorkfed.org": payload})
        res = official.NyFedRates(session, env={}).fetch(
            [sd("NYFED", "secured/sofr:percentRate"), sd("NYFED", "secured/sofr:volumeInBillions")], START
        )
        self.assertEqual(res[0].observations[-1], Observation(date(2026, 10, 23), 4.02))
        self.assertEqual(res[1].observations[0].value, 2850)

    def test_cftc_groups_by_contract(self):
        rows = [{"report_date_as_yyyy_mm_dd": "2026-10-20T00:00:00.000", "asset_mgr_positions_long": "1000",
                 "asset_mgr_positions_short": "400", "open_interest_all": "5000"}]
        session = FakeSession({"publicreporting.cftc.gov": rows})
        res = official.Cftc(session, env={}).fetch(
            [sd("CFTC", "gpe5-46if:13874A:asset_mgr_positions_long"), sd("CFTC", "gpe5-46if:13874A:open_interest_all")], START
        )
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(res[0].observations, [Observation(date(2026, 10, 20), 1000.0)])

    def test_bls_post(self):
        payload = {"status": "REQUEST_SUCCEEDED", "message": [], "Results": {"series": [
            {"seriesID": "CUSR0000SA0", "data": [
                {"year": "2026", "period": "M09", "value": "330.1"},
                {"year": "2026", "period": "M13", "value": "329.0"},
            ]}]}}
        session = FakeSession({"api.bls.gov": payload})
        [res] = official.Bls(session, env={"BLS_API_KEY": "k"}).fetch([sd("BLS", "CUSR0000SA0")], START)
        self.assertEqual(res.observations, [Observation(date(2026, 9, 1), 330.1)])

    def test_ecb_csv(self):
        csv = "KEY,FREQ,TIME_PERIOD,OBS_VALUE\nEXR.D.USD.EUR.SP00.A,D,2026-10-22,1.1612\nEXR.D.USD.EUR.SP00.A,D,2026-10-23,1.1655\n"
        session = FakeSession({"data-api.ecb.europa.eu": csv})
        [res] = official.Ecb(session, env={}).fetch([sd("ECB", "EXR/D.USD.EUR.SP00.A")], START)
        self.assertEqual(res.observations[-1], Observation(date(2026, 10, 23), 1.1655))

    def test_eurostat_jsonstat(self):
        payload = {"id": ["freq", "unit", "geo", "time"], "size": [1, 1, 1, 2],
                   "dimension": {"time": {"category": {"index": {"2026-Q1": 0, "2026-Q2": 1}}}},
                   "value": {"0": 0.4, "1": 0.2}}
        session = FakeSession({"ec.europa.eu/eurostat": payload})
        d = sd("EUROSTAT", "namq_10_gdp:qoq", params={"dataset": "namq_10_gdp", "geo": "EA"})
        [res] = official.Eurostat(session, env={}).fetch([d], START)
        self.assertEqual(res.observations[-1], Observation(date(2026, 4, 1), 0.2))
        self.assertIn("/namq_10_gdp", session.calls[0][0])
        self.assertNotIn("dataset", session.calls[0][1])

    def test_treasury_fiscal_pagination_and_scale(self):
        def page(params):
            n = params["page[number]"]
            rows = [{"auction_date": f"2026-10-0{n}", "offering_amt": "69000000000"}]
            return {"data": rows, "meta": {"total-pages": 2}}
        session = FakeSession({"api.fiscaldata.treasury.gov": page})
        d = sd("TSY", "auction:2-Year:offering_amt", params={
            "endpoint": "v1/accounting/od/auctions_query", "date_field": "auction_date",
            "value_field": "offering_amt", "scale": 1e-6, "filter": "security_term:eq:2-Year"})
        [res] = official.TreasuryFiscal(session, env={}).fetch([d], START)
        self.assertEqual([o.value for o in res.observations], [69000.0, 69000.0])

    def test_yahoo_chart(self):
        payload = {"chart": {"result": [{"meta": {"gmtoffset": -14400, "currentTradingPeriod": {"regular": {"end": 1}}},
                                         "timestamp": [1792929600], "indicators": {"quote": [{"close": [5800.5]}]}}]}}
        session = FakeSession({"query2.finance.yahoo.com": payload})
        official.time.sleep = lambda s: None
        [res] = official.Yahoo(session, env={}).fetch([sd("YAHOO", "^RUT")], START)
        self.assertEqual(res.observations[0].value, 5800.5)

    def test_missing_credentials(self):
        [res] = official.Eia(FakeSession({}), env={}).fetch([sd("EIA", "PET.WCESTUS1.W")], START)
        self.assertEqual(res.status, "not_configured")

    def test_http_error_becomes_status(self):
        [res] = official.Cboe(FakeSession({}), env={}).fetch([sd("CBOE", "VIX")], START)
        self.assertEqual(res.status, "error")


class StoreVersioningTests(unittest.TestCase):
    def test_initial_load_estimates_then_revision_first_seen(self):
        rows = plan_new_rows({}, False, [Observation(date(2026, 8, 1), 1.0)], fetch_day=date(2026, 10, 24), release_lag_days=45)
        self.assertEqual(rows, [(date(2026, 8, 1), date(2026, 9, 15), 1.0, "backfill_estimate")])
        rows = plan_new_rows({date(2026, 8, 1): 1.0}, True,
                             [Observation(date(2026, 8, 1), 1.1), Observation(date(2026, 9, 1), 2.0)],
                             fetch_day=date(2026, 10, 24), release_lag_days=45)
        self.assertEqual([r[3] for r in rows], ["first_seen", "first_seen"])

    def test_unchanged_values_are_not_rewritten(self):
        rows = plan_new_rows({date(2026, 8, 1): 1.0}, True, [Observation(date(2026, 8, 1), 1.0)],
                             fetch_day=date(2026, 10, 24), release_lag_days=45)
        self.assertEqual(rows, [])


class EndToEndTests(unittest.TestCase):
    def test_fetch_store_derive(self):
        days = pd.bdate_range("2025-09-01", "2026-10-23")
        csv = "observation_date,SP500\n" + "".join(f"{d.date()},{5000 + i}\n" for i, d in enumerate(days))
        session = FakeSession({"fredgraph.csv": csv})
        store = SQLiteStore()
        store.init_schema()
        store.upsert_series([{"series_key": "FRED:SP500", "provider": "FRED", "code": "SP500", "params": {},
                              "title": "S&P 500", "frequency": "D", "unit": "点", "source_url": "", "release_lag_days": 1,
                              "vintages": False}])
        defs = [sd("FRED", "SP500", release_lag_days=1)]
        summary = runner.fetch(store, defs, start=date(2025, 9, 1), session=session, env={}, log=lambda *_: None)
        self.assertEqual(summary["FRED"].ok, 1)
        self.assertEqual(summary["FRED"].rows, len(days))
        raw = store.load_observations(["FRED:SP500"])
        values = compute({"01-002": 'ret({FRED:SP500}, "W")'}, raw, [pd.Timestamp("2026-10-23")], fast=True)
        self.assertEqual(values[0].status, "ok")
        self.assertAlmostEqual(values[0].value, ((5000 + len(days) - 1) / (5000 + len(days) - 6) - 1) * 100)
        # A second fetch with identical data writes nothing.
        summary = runner.fetch(store, defs, start=date(2025, 9, 1), session=session, env={}, log=lambda *_: None)
        self.assertEqual(summary["FRED"].rows, 0)


class MappingTests(unittest.TestCase):
    def test_every_formula_parses_and_references_registered_series(self):
        from pipeline.warehouse.catalog.mapping import load_mapping, load_series
        from pipeline.warehouse.engine.formula import parse

        keys = {s["key"] for s in load_series()}
        providers = {s["provider"] for s in load_series()}
        from pipeline.warehouse.providers.base import REGISTRY
        self.assertTrue(providers <= set(REGISTRY), providers - set(REGISTRY))
        mapping = load_mapping()
        self.assertEqual(len(mapping), 1959)
        for iid, m in mapping.items():
            if m["method"] == "api":
                formula = parse(m["formula"])
                self.assertTrue(formula.series, iid)
                self.assertTrue(set(formula.series) <= keys, (iid, set(formula.series) - keys))

    def test_forecast_modules_excluded(self):
        import csv
        from pipeline.warehouse.catalog.build_catalog import INDICATORS_CSV
        from pipeline.warehouse.catalog.mapping import load_mapping

        mapping = load_mapping()
        with INDICATORS_CSV.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["module"] in ("分机构年度增长预测", "长期资本市场假设"):
                    self.assertEqual(mapping[r["indicator_id"]]["method"], "excluded")


if __name__ == "__main__":
    unittest.main()


class ReportArchiveTests(unittest.TestCase):
    def test_html_text_keeps_table_cells_and_pdf_links(self):
        from pipeline.warehouse.providers.reports import html_text

        text, links = html_text(b"<html><script>x=1</script><table><tr><td>S&amp;P 500</td><td>1.2</td></tr></table>"
                                b"<a href='/files/report.pdf'>pdf</a></html>")
        self.assertIn("S&P 500 | 1.2", text)
        self.assertEqual(links, ["/files/report.pdf"])

    def test_report_date(self):
        from pipeline.warehouse.providers.reports import find_report_date

        self.assertEqual(find_report_date("U.S. | October 19, 2026 ..."), date(2026, 10, 19))
        self.assertEqual(find_report_date("Investment Weekly 16 October 2026"), date(2026, 10, 16))

    def test_download_tries_dated_candidates(self):
        from pipeline.warehouse.providers import reports

        body = b"<html>" + b"<p>Investment Weekly 16 October 2026</p>" * 40 + b"</html>"
        session = FakeSession({"investment-weekly-16-october-2026": body})
        got = reports.download(reports.SOURCES[3], session, today=date(2026, 10, 18), log=lambda *_: None)
        self.assertEqual(got.report_date, date(2026, 10, 16))
        store = SQLiteStore()
        store.init_schema()
        self.assertEqual(store.upsert_report_pages(got.source, got.report_date, got.url, got.pages), 1)


class BreadthTests(unittest.TestCase):
    def test_breadth_metrics(self):
        import numpy as np
        from pipeline.warehouse.providers.breadth import compute, constituents

        html = ("<table><tr><th>Symbol</th><th>Security</th><th>GICS Sector</th></tr>"
                "<tr><td>BRK.B</td><td>Berkshire</td><td>Financials</td></tr></table>")
        self.assertEqual(constituents(html)["Symbol"].tolist(), ["BRK-B"])
        idx = pd.bdate_range("2024-10-01", "2026-10-23")
        rising = pd.DataFrame({f"T{i}": np.linspace(100, 200, len(idx)) for i in range(10)}, index=idx)
        m = compute(rising, {f"T{i}": "Energy" for i in range(10)}, date(2026, 1, 1))
        self.assertEqual(m["pct_above_200dma"].iloc[-1], 100.0)
        self.assertEqual(m["advancers"].iloc[-1], 10)
        self.assertAlmostEqual(m["median_drawdown_52w"].iloc[-1], 0.0)


class FileParserTests(unittest.TestCase):
    def test_tic_table5(self):
        from pipeline.warehouse.providers.files import TicTable5

        txt = ("Table 5\r\nCountry\t2026-08\t2026-07\r\nJapan\t1068.3\t1103.9\r\nGrand Total\t9331.7\t9248.4\r\n"
               "Of Which: Foreign Official\t3755.6\t3773.1\r\n")
        session = FakeSession({"slt_table5.txt": txt})
        [res] = TicTable5(session, env={}).fetch([sd("TIC", "Grand Total")], date(2026, 1, 1))
        self.assertEqual(res.observations[-1], Observation(date(2026, 8, 1), 9331.7))

    def test_ism_glance_rows(self):
        from pipeline.warehouse.providers.files import parse_ism

        text = ("Manufacturing PMI® 54.5 54.6 -0.1 Growing Slower 9\n New Orders   55.3 53.7 +1.6  Growing\n"
                " Employment 52.7 51.2 +1.5 Growing\n Inventories  48.6 50.6 -2.0 Contracting\n Customers’ Inventories 41.6 42.8 -1.2\n"
                " Prices 77.9 71.1 +6.8 Increasing\n New Export Orders 50.9 53.2 -2.3")
        got = parse_ism(text)
        self.assertEqual(got["pmi"], (54.5, 54.6))
        self.assertEqual(got["new_orders"], (55.3, 53.7))
        self.assertEqual(got["inventories"], (48.6, 50.6))
        self.assertEqual(got["prices"], (77.9, 71.1))

    def test_ff_numbers_and_calendar(self):
        from pipeline.warehouse.providers.files import ForexFactoryCalendar, _ff_number

        self.assertEqual(_ff_number("150K"), 150000)
        self.assertEqual(_ff_number("0.3%"), 0.3)
        self.assertEqual(_ff_number("95.2B"), 95.2e9)
        self.assertIsNone(_ff_number(""))
        events = [{"title": "CPI y/y", "country": "USD", "date": "2026-10-14T08:30:00-04:00", "forecast": "3.7%", "previous": "3.5%"}]
        session = FakeSession({"ff_calendar_thisweek.json": events})
        [res] = ForexFactoryCalendar(session, env={}).fetch([sd("FFCAL", "USD|CPI y/y|forecast")], date(2026, 1, 1))
        self.assertEqual(res.observations, [Observation(date(2026, 10, 14), 3.7)])


class SurpriseTests(unittest.TestCase):
    def test_first_print_minus_consensus(self):
        from pipeline.warehouse.engine.formula import Context, RawSeries, evaluate

        actual = pd.DataFrame({"obs_date": pd.to_datetime(["2026-08-01", "2026-09-01"]),
                               "realtime_start": pd.to_datetime(["2026-09-12", "2026-10-17"]),
                               "value": [3.5, 3.9], "vintage_source": ["first_seen", "first_seen"]})
        cons = pd.DataFrame({"obs_date": pd.to_datetime(["2026-09-10", "2026-10-14"]), "realtime_start": pd.to_datetime(["2026-09-08", "2026-10-12"]),
                             "value": [3.4, 3.7], "vintage_source": ["first_seen", "first_seen"]})
        ctx = Context({"A:X": RawSeries.from_frame(actual), "C:Y": RawSeries.from_frame(cons)},
                      pd.Timestamp("2026-10-23"), pd.Timestamp("2026-10-25"))
        result = evaluate("surprise({A:X}, {C:Y})", ctx)
        self.assertAlmostEqual(result.value, 0.2)


class BundesbankTests(unittest.TestCase):
    def test_decimal_comma(self):
        csv = "Date;BBSSY.D.REN.EUR.A630.000000WT1010.A;Flags\n2026-10-22;3,31;\n2026-10-23;3,33;\n"
        session = FakeSession({"api.statistiken.bundesbank.de": csv})
        [res] = official.Bundesbank(session, env={}).fetch([sd("BBK", "BBSSY/D.REN.EUR.A630.000000WT1010.A")], date(2026, 1, 1))
        self.assertEqual(res.observations[-1], Observation(date(2026, 10, 23), 3.33))


class SeriesResetTests(unittest.TestCase):
    def test_reset_runs_once(self):
        from unittest import mock

        store = SQLiteStore()
        store.init_schema()
        key = "BBK:BBSSY/D.REN.EUR.A630.000000WT1010.A"
        store.write_observations(key, [Observation(date(2026, 10, 23), 333.0)], release_lag_days=1)
        with mock.patch.object(runner, "SERIES_RESETS", {"t1": (key,)}):
            self.assertEqual(runner.apply_series_resets(store), [key])
            self.assertEqual(store.latest_values(key)[1], False)
            store.write_observations(key, [Observation(date(2026, 10, 23), 3.33)], release_lag_days=1)
            self.assertEqual(runner.apply_series_resets(store), [])
        self.assertEqual(store.latest_values(key)[1], True)
        store.close()


class CodeVersionGuardTests(unittest.TestCase):
    def test_older_checkout_refuses(self):
        from unittest import mock

        store = SQLiteStore()
        store.init_schema()
        with mock.patch.object(runner, "code_version", return_value="2026-10-25T00:00:00Z bbb"):
            runner.guard_code_version(store)
        with mock.patch.object(runner, "code_version", return_value="2026-10-23T00:00:00Z aaa"):
            with self.assertRaises(runner.StaleCodeError):
                runner.guard_code_version(store)
        with mock.patch.object(runner, "code_version", return_value="2026-10-26T00:00:00Z ccc"):
            runner.guard_code_version(store)
        self.assertEqual(store.get_meta("code_version"), "2026-10-26T00:00:00Z ccc")
        store.close()


class SnbTests(unittest.TestCase):
    def test_two_dimension_cube(self):
        csv = ('"CubeId";"rendeiduebd"\n"PublishingDate";"2026-10-24 09:00"\n\n"Date";"D0";"D1";"Value"\n'
               '"2026-10-22";"CHF";"10J";"0.50"\n"2026-10-23";"CHF";"10J";"0.491"\n"2026-10-23";"CHF";"2J";"0.1"\n')
        session = FakeSession({"data.snb.ch": csv})
        [res] = official.Snb(session, env={}).fetch_many([sd("SNB", "rendeiduebd:CHF.10J")], date(2026, 1, 1))
        self.assertEqual([o.value for o in res.observations], [0.50, 0.491])


class ObsOrderingTests(unittest.TestCase):
    def test_sorted_newest_first_input(self):
        from pipeline.warehouse.providers.base import obs_from_pairs

        obs = obs_from_pairs([("2026-10-22", "4.1"), ("2026-01-02", "4.5"), ("2025-12-31", "4.6")])
        self.assertEqual([o.obs_date for o in obs], [date(2025, 12, 31), date(2026, 1, 2), date(2026, 10, 22)])


NBS_HEAD = "Chinese(GB)\nRSS\nHome > Latest Releases\n{title}\n 2026-10-15 09:30\n Print|\n Large|\n"


class NbsTests(unittest.TestCase):
    def parse(self, kind, title, body):
        from pipeline.warehouse.providers.releases import parse_nbs

        return parse_nbs(kind, title, f"{title}\n" + NBS_HEAD.format(title=title) + body)

    def test_cpi_current_and_older_wording(self):
        t = "Consumer Price Index in September 2026"
        self.assertEqual(self.parse("cpi_yoy", t, "In September 2026, China’s Consumer Price Index (CPI) increased by 0.9% year on year. Specifically, urban decreased by 0.2%."),
                         (date(2026, 9, 1), 0.9))
        t = "Consumer Price Index for March 2025"
        self.assertEqual(self.parse("cpi_yoy", t, "In March 2025, the national consumer price index (CPI) decreased by 0.1 percent year-on-year."),
                         (date(2025, 3, 1), -0.1))

    def test_ppi(self):
        t = "Producer Price Index in the Industrial Sector for March 2025"
        self.assertEqual(self.parse("ppi_yoy", t, "In March, the national producer prices for industrial products decreased by 2.5 percent year on year"),
                         (date(2025, 3, 1), -2.5))

    def test_ip_and_retail_use_single_month(self):
        t = "Industrial Production Operation in September 2026"
        body = ("In September, the total value added of industrial enterprises above the designated size increased by 5.5% year on year "
                "in real terms. From January to September, the total value added ... increased by 5.3% year on year.")
        self.assertEqual(self.parse("ip_yoy", t, body), (date(2026, 9, 1), 5.5))
        t = "Total Retail Sales of Consumer Goods from January to September 2026"
        body = ("From January to September 2026, the total retail sales of consumer goods reached 37,000.1 billion yuan, up by 1.1% year on year. "
                "In September, the total retail sales of consumer goods reached 4,243.3 billion yuan, up by 1.3% year on year.")
        self.assertEqual(self.parse("retail_yoy", t, body), (date(2026, 9, 1), 1.3))
        t = "Total Retail Sales of Consumer Goods from January to February 2025"
        body = "From January to February 2025, the total retail sales of consumer goods reached 8,373.1 billion yuan, up by 4.0 percent year on year."
        self.assertEqual(self.parse("retail_yoy", t, body), (date(2025, 2, 1), 4.0))

    def test_gdp_table_and_pmi(self):
        t = "Preliminary Accounting Results of GDP for the Third Quarter of 2026"
        body = ("results of the preliminary accounting of China’s GDP in the third quarter of 2026 are as follows.\nTable 1\n | \n | \n"
                "Absolute Value (100 million yuan)\n | \nGrowth Rate Y/Y (%)\n | \nQ3\n | \nFirst Three Quarters of 2026\n | \nQ3\n | \n"
                "First Three Quarters of 2026\n | \nGDP\n | \n375367\n | \n1071071\n | \n4.5\n | \n4.6\n | \nPrimary industry\n | \n27472\n")
        self.assertEqual(self.parse("gdp_yoy", t, body), (date(2026, 7, 1), 4.5))
        t = "Purchasing Managers' Index for March 2025"
        body = "In March, the purchasing managers' index (PMI) of China's manufacturing industry came in at 50.5 percent, up 0.3 percentage points"
        self.assertEqual(self.parse("mfg_pmi", t, body), (date(2025, 3, 1), 50.5))

    def test_listing(self):
        from pipeline.warehouse.providers.releases import nbs_kind, parse_nbs_listing

        html = ('<li><a href="./202610/t20261015_1965500.html" title="Consumer Price Index in September 2026">13.Consumer Price Index in September 2026</a>'
                '<span>2026-10-15</span></li><li><a href="./202504/t20250408_1959247.html">Purchasing Managers’ Index for March 2025</a></li>')
        items = parse_nbs_listing(html, "https://www.stats.gov.cn/english/PressRelease/index_1.html")
        self.assertEqual(items[0], ("Consumer Price Index in September 2026", date(2026, 10, 15),
                                    "https://www.stats.gov.cn/english/PressRelease/202610/t20261015_1965500.html"))
        self.assertEqual([nbs_kind(t) for t, _, _ in items], ["cpi_yoy", "mfg_pmi"])


class TotalReturnTests(unittest.TestCase):
    def test_dividend_on_ex_date(self):
        from pipeline.warehouse.providers.official import total_return_index

        closes = [Observation(date(2026, 1, d), v) for d, v in [(2, 100.0), (5, 99.0), (6, 99.0)]]
        out = total_return_index(closes, {date(2026, 1, 5): 1.0})
        self.assertEqual([o.value for o in out], [100.0, 100.0, 100.0])

    def test_lbma(self):
        body = json.dumps([{"is_cms_locked": 0, "d": "2026-10-22", "v": [4100.5, 3080.1, 3500.2]},
                           {"is_cms_locked": 0, "d": "2026-10-23", "v": [4120.0, 3090.0, 3510.0]}])
        session = FakeSession({"prices.lbma.org.uk": body})
        [res] = official.Lbma(session, env={}).fetch([sd("LBMA", "gold_pm")], date(2026, 1, 1))
        self.assertEqual(res.observations[-1], Observation(date(2026, 10, 23), 4120.0))
