from datetime import date
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from pipeline.internal.capital_weekly.context.providers import (
    build_default_providers,
    metric_rows,
    not_configured_result,
)
from pipeline.internal.capital_weekly.context.common import METRIC_FIELDS
from pipeline.internal.capital_weekly.context.provider_contracts import (
    ContextProvider,
    ProviderResult,
    ProviderSpec,
)
from pipeline.internal.capital_weekly.weekly_context import run_weekly_context


YAHOO_CONFIG = (
    "metric_code,metric_name,ticker,unit,role\n"
    "vix_9d_level,Cboe S&P 500 9-Day Volatility Index,^VIX9D,index_points,vix_9d\n"
    "vix_1m_level,Cboe VIX 30-Day Volatility Index,^VIX,index_points,vix_1m\n"
    "vix_3m_level,Cboe S&P 500 3-Month Volatility Index,^VIX3M,index_points,vix_3m\n"
    "vix_6m_level,Cboe S&P 500 6-Month Volatility Index,^VIX6M,index_points,vix_6m\n"
    "cboe_skew_level,Cboe SKEW Index,^SKEW,index_points,skew\n"
)


def write_provider_configs(data_dir):
    (data_dir / "capital_weekly_company_watchlist.csv").write_text(
        "ticker,cik,company_name,enabled\n", encoding="utf-8"
    )
    (data_dir / "capital_weekly_cftc_contracts.csv").write_text(
        "contract_code,metric_code,report_type\n"
        "13874A,sp500,tff\n"
        "088691,gold,disaggregated\n",
        encoding="utf-8",
    )
    (data_dir / "capital_weekly_breadth_universe.csv").write_text(
        "symbol,name,enabled\n"
        "XLC,Communication Services,1\n"
        "XLY,Consumer Discretionary,1\n",
        encoding="utf-8",
    )
    (data_dir / "capital_weekly_eia_series.csv").write_text(
        "metric_code,metric_name,route,frequency,series,expected_unit\n",
        encoding="utf-8",
    )
    (data_dir / "capital_weekly_financial_conditions.csv").write_text(
        "metric_code,metric_name,series_id,risk_direction\n"
        "vix,VIX,VIXCLS,1\n",
        encoding="utf-8",
    )
    (data_dir / "capital_weekly_yahoo_volatility.csv").write_text(
        YAHOO_CONFIG, encoding="utf-8"
    )


class ContextProviderTests(unittest.TestCase):
    def test_default_registry_rejects_duplicate_breadth_symbols(self):
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            (data_dir / "capital_weekly_breadth_universe.csv").write_text(
                "symbol,name,enabled\nXLC,First,1\nXLC,Duplicate,1\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "breadth symbols"):
                build_default_providers(
                    start=date(2026, 7, 20),
                    end=date(2026, 7, 26),
                    data_dir=data_dir,
                    environ={},
                )

    def test_default_registry_rejects_unknown_cftc_report_type(self):
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            (data_dir / "capital_weekly_cftc_contracts.csv").write_text(
                "contract_code,metric_code,report_type\n"
                "13874A,sp500,legacy\n"
                "088691,gold,disaggregated\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unsupported report types"):
                build_default_providers(
                    start=date(2026, 7, 20),
                    end=date(2026, 7, 26),
                    data_dir=data_dir,
                    environ={},
                )

    def test_provider_failure_provenance_is_typed(self):
        spec = ProviderSpec(
            name="optional",
            category="market_internals",
            source_tier="public",
            requiredness="optional",
            provider_version="1.0.0",
            schema_version="context-metric-v1",
            frequency="daily",
            freshness_days=7,
            failure_source="Official Source",
            failure_source_url="https://example.gov/data",
        )

        self.assertEqual(spec.failure_source, "Official Source")
        self.assertEqual(spec.failure_source_url, "https://example.gov/data")

    def test_metric_rows_emit_shared_contract(self):
        rows = metric_rows(
            as_of_date=date(2026, 7, 24),
            category="market_internals",
            market="HKEX",
            source="HKEX",
            source_url="https://www.hkex.com.hk/",
            frequency="daily",
            values={"turnover": 100.0, "advance_ratio": 0.55},
            units={"turnover": "HKD", "advance_ratio": "ratio"},
        )

        self.assertEqual(len(rows), 2)
        self.assertTrue(set(METRIC_FIELDS).issubset(rows[0]))
        self.assertEqual(rows[0]["category"], "market_internals")

    def test_not_configured_provider_keeps_status_visible(self):
        result = not_configured_result(
            category="company_events",
            source="SEC",
            source_url="https://data.sec.gov/",
            notes="watchlist is empty",
        )

        self.assertEqual(result.status, "NOT_CONFIGURED")
        self.assertEqual(result.rows, [])
        self.assertIn("watchlist", result.notes)

    def test_default_registry_includes_both_stable_and_dynamic_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)

            providers = build_default_providers(
                start=date(2026, 7, 20),
                end=date(2026, 7, 26),
                data_dir=data_dir,
                environ={},
            )

        self.assertTrue(
            {
                "bls_calendar",
                "bls_economic_releases",
                "bea_economic_releases",
                "census_retail_sales",
                "census_housing",
                "census_durable_goods",
                "ism_manufacturing_pmi",
                "federal_reserve_calendar",
                "fomc_calendar",
                "census_calendar",
                "nasdaq_market_summary",
                "cftc_tff",
                "cftc_disaggregated",
                "finra_margin",
                "sec_company_events",
                "eia_commodities",
                "fred_financial_conditions",
                "yahoo_volatility_signals",
                "yahoo_market_state",
                "ishares_ivv_fund",
                "hkex_stock_connect_flows",
                "hkex_microstructure",
                "sse_microstructure",
                "szse_microstructure",
            }.issubset(providers)
        )
        self.assertTrue(all(isinstance(provider, ContextProvider) for provider in providers.values()))
        self.assertEqual(providers["sec_company_events"].spec.requiredness, "optional")
        self.assertEqual(providers["eia_commodities"].spec.requiredness, "optional")
        self.assertEqual(
            providers["fred_financial_conditions"].spec.requiredness, "optional"
        )
        self.assertEqual(
            providers["yahoo_volatility_signals"].spec.requiredness, "optional"
        )
        self.assertEqual(providers["yahoo_market_state"].spec.requiredness, "optional")
        self.assertEqual(providers["ishares_ivv_fund"].spec.category, "fund_flows")
        self.assertEqual(
            providers["hkex_stock_connect_flows"].spec.category,
            "fund_flows",
        )
        self.assertEqual(providers["bls_calendar"].spec.requiredness, "required")
        self.assertEqual(
            providers["bls_economic_releases"].spec.category,
            "economic_releases",
        )
        self.assertEqual(
            providers["bea_economic_releases"].spec.requiredness,
            "required",
        )
        self.assertEqual(providers["census_housing"].spec.requiredness, "required")
        self.assertEqual(
            providers["census_durable_goods"].spec.requiredness,
            "required",
        )
        self.assertEqual(providers["fomc_calendar"].spec.category, "events")
        self.assertEqual(
            providers["ism_manufacturing_pmi"].spec.source_tier,
            "licensed",
        )
        licensed_gap = providers["ism_manufacturing_pmi"].fetch()
        self.assertEqual(licensed_gap.status, "UNAVAILABLE_LICENSED")
        self.assertEqual(licensed_gap.rows, [])
        self.assertEqual(providers["nasdaq_market_summary"].spec.source_tier, "public")
        self.assertEqual(providers["nasdaq_market_summary"].spec.provider_version, "1.0.0")
        self.assertEqual(
            providers["nasdaq_market_summary"].spec.schema_version,
            "context-metric-v1",
        )

    def test_fomc_provider_enriches_only_completed_window_decisions(self):
        calendar_url = (
            "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
        )
        statement_url = (
            "https://www.federalreserve.gov/newsevents/pressreleases/"
            "monetary20260729a.htm"
        )
        calendar = """
        <div class="panel-heading"><h4><a>2026 FOMC Meetings</a></h4></div>
        <div class="row fomc-meeting">
          <div class="fomc-meeting__month col-xs-5">July</div>
          <div class="fomc-meeting__date col-xs-4">28-29</div>
        </div>
        <div class="row fomc-meeting">
          <div class="fomc-meeting__month col-xs-5">September</div>
          <div class="fomc-meeting__date col-xs-4">15-16</div>
        </div>
        """
        statement = """
        <p>July 29, 2026</p><p>For release at 2:00 p.m. EDT</p>
        <p>The Committee decided to maintain the target range for the federal
        funds rate at 3-1/2 to 3-3/4 percent.</p>
        """

        class Response:
            encoding = "utf-8"
            apparent_encoding = "utf-8"

            def __init__(self, text):
                self.text = text

            def raise_for_status(self):
                return None

        class Session:
            def __init__(self):
                self.calls = []

            def get(self, url, **kwargs):
                self.calls.append((url, kwargs))
                return Response({calendar_url: calendar, statement_url: statement}[url])

        session = Session()
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            provider = build_default_providers(
                start=date(2026, 7, 27),
                end=date(2026, 8, 2),
                data_dir=data_dir,
                environ={},
                session=session,
            )["fomc_calendar"]
            result = provider.fetch()

        self.assertEqual(
            [url for url, _ in session.calls],
            [calendar_url, statement_url],
        )
        self.assertEqual(len(result.rows), 1)
        decision = result.rows[0]
        self.assertEqual(decision["event_type"], "fomc_policy_decision")
        self.assertEqual(decision["actual"], "maintain 3.5%-3.75%")
        self.assertEqual(decision["previous"], None)
        self.assertEqual(decision["source_url"], statement_url)

    def test_yahoo_market_state_provider_emits_registered_proxy_breadth(self):
        calls = []
        dates = pd.bdate_range("2025-10-24", periods=205)

        def fake_download(**kwargs):
            calls.append(kwargs)
            return pd.DataFrame(
                {
                    ("XLC", "Close"): [100.0 + index for index in range(205)],
                    ("XLY", "Close"): [200.0 - index * 0.2 for index in range(205)],
                    ("RSP", "Close"): [100.0 + index * 0.4 for index in range(205)],
                    ("SPY", "Close"): [100.0 + index * 0.3 for index in range(205)],
                },
                index=dates,
            )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            provider = build_default_providers(
                start=dates[-5].date(),
                end=dates[-1].date(),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=fake_download,
            )["yahoo_market_state"]
            result = provider.fetch()

        codes = {row["metric_code"] for row in result.rows}
        self.assertEqual(result.status, "OK")
        self.assertTrue(
            {
                "us_sector_etf_proxy_pct_above_20d_ma",
                "us_sector_etf_proxy_pct_above_50d_ma",
                "us_sector_etf_proxy_pct_above_200d_ma",
                "us_sector_etf_proxy_advancers",
                "us_sector_etf_proxy_decliners",
                "rsp_spy_relative_return_5d",
                "rsp_spy_relative_return_20d",
            }.issubset(codes)
        )
        self.assertTrue(all(row["market"] == "US_PROXY" for row in result.rows))
        self.assertIn("registered 2-instrument sector ETF proxy universe", result.notes)
        self.assertEqual(calls[0]["tickers"], ["XLC", "XLY", "RSP", "SPY"])

    def test_yahoo_volatility_provider_uses_bounded_deterministic_download(self):
        calls = []

        def fake_download(**kwargs):
            calls.append(kwargs)
            return pd.DataFrame(
                {
                    ("^VIX9D", "Close"): [14.0, 99.0],
                    ("^VIX", "Close"): [16.0, 99.0],
                    ("^VIX3M", "Close"): [20.0, 99.0],
                    ("^VIX6M", "Close"): [22.0, 99.0],
                    ("^SKEW", "Close"): [145.0, 199.0],
                },
                index=pd.to_datetime(["2026-08-07", "2026-08-10"]),
            )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            providers = build_default_providers(
                start=date(2026, 8, 3),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=fake_download,
            )
            provider = providers["yahoo_volatility_signals"]
            result = provider.fetch()

        self.assertEqual(provider.spec.category, "financial_conditions")
        self.assertEqual(provider.spec.requiredness, "optional")
        self.assertEqual(provider.spec.source_tier, "public")
        self.assertEqual(provider.spec.freshness_days, 7)
        self.assertEqual(result.status, "OK")
        self.assertEqual(len(result.rows), 8)
        self.assertEqual(
            [row["metric_code"] for row in result.rows],
            [
                "vix_9d_level",
                "vix_1m_level",
                "vix_3m_level",
                "vix_6m_level",
                "cboe_skew_level",
                "vix_1m_3m_spread",
                "vix_1m_3m_ratio",
                "vix_9d_1m_spread",
            ],
        )
        self.assertTrue(all(set(METRIC_FIELDS).issubset(row) for row in result.rows))
        self.assertTrue(all(row["qc_flag"] == "OK" for row in result.rows))
        self.assertEqual(
            calls,
            [
                {
                    "tickers": ["^VIX9D", "^VIX", "^VIX3M", "^VIX6M", "^SKEW"],
                    "start": "2025-02-05",
                    "end": "2026-08-10",
                    "interval": "1d",
                    "auto_adjust": False,
                    "actions": False,
                    "group_by": "ticker",
                    "threads": False,
                    "progress": False,
                }
            ],
        )
        self.assertIn("date,ticker,close", result.raw_text)
        self.assertNotIn("2026-08-10", result.raw_text)
        self.assertEqual(result.source, "Yahoo Finance (Cboe indices)")
        self.assertEqual(result.source_url, "https://finance.yahoo.com/")

    def test_yahoo_volatility_provider_keeps_fresh_independent_series(self):
        def partial_download(**_kwargs):
            return pd.DataFrame(
                {
                    ("^VIX9D", "Close"): [float("nan")],
                    ("^VIX", "Close"): [16.0],
                    ("^VIX3M", "Close"): [float("nan")],
                    ("^VIX6M", "Close"): [float("nan")],
                    ("^SKEW", "Close"): [145.0],
                },
                index=pd.to_datetime(["2026-08-07"]),
            )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            result = build_default_providers(
                start=date(2026, 8, 3),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=partial_download,
            )["yahoo_volatility_signals"].fetch()

        self.assertEqual(result.status, "OK")
        self.assertEqual(
            [row["metric_code"] for row in result.rows],
            ["vix_1m_level", "cboe_skew_level"],
        )
        self.assertIn("vix_9d", result.notes)
        self.assertIn("vix_3m", result.notes)
        self.assertIn("vix_6m", result.notes)

    def test_yahoo_volatility_provider_audits_omitted_pair_calculations(self):
        def disjoint_download(**_kwargs):
            return pd.DataFrame(
                {
                    ("^VIX9D", "Close"): [14.0, None, None, None, None],
                    ("^VIX", "Close"): [None, 16.0, None, None, None],
                    ("^VIX3M", "Close"): [None, None, 20.0, None, None],
                    ("^VIX6M", "Close"): [None, None, None, 22.0, None],
                    ("^SKEW", "Close"): [None, None, None, None, 145.0],
                },
                index=pd.to_datetime(
                    [
                        "2026-08-03", "2026-08-04", "2026-08-05",
                        "2026-08-06", "2026-08-07",
                    ]
                ),
            )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            result = build_default_providers(
                start=date(2026, 8, 3),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=disjoint_download,
            )["yahoo_volatility_signals"].fetch()

        self.assertEqual(result.status, "OK")
        self.assertEqual(len(result.rows), 5)
        self.assertIn("vix_1m_3m_spread", result.notes)
        self.assertIn("vix_1m_3m_ratio", result.notes)
        self.assertIn("vix_9d_1m_spread", result.notes)
        self.assertIn("no fresh common date", result.notes)

    def test_yahoo_failure_returns_auditable_optional_result(self):
        def unavailable(**_kwargs):
            raise RuntimeError("Yahoo unavailable")

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            provider = build_default_providers(
                start=date(2026, 8, 3),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=unavailable,
            )["yahoo_volatility_signals"]

            result = provider.fetch()

        self.assertEqual(result.status, "FETCH_FAILED")
        self.assertEqual(result.rows, [])
        self.assertEqual(result.source, "Yahoo Finance (Cboe indices)")
        self.assertEqual(result.source_url, "https://finance.yahoo.com/")
        self.assertIn("Yahoo unavailable", result.notes)

    def test_yahoo_stale_legs_preserve_fresh_rows_and_normalized_raw_history(self):
        def stale_download(**_kwargs):
            return pd.DataFrame(
                {
                    ("^VIX9D", "Close"): [14.0, float("nan")],
                    ("^VIX", "Close"): [16.0, 15.0],
                    ("^VIX3M", "Close"): [20.0, float("nan")],
                    ("^VIX6M", "Close"): [22.0, float("nan")],
                    ("^SKEW", "Close"): [144.0, 145.0],
                },
                index=pd.to_datetime(["2026-07-17", "2026-08-07"]),
            )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            provider = build_default_providers(
                start=date(2026, 8, 3),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=stale_download,
            )["yahoo_volatility_signals"]

            result = provider.fetch()

        self.assertEqual(result.status, "OK")
        self.assertEqual(
            [row["metric_code"] for row in result.rows],
            ["vix_1m_level", "cboe_skew_level"],
        )
        self.assertIn("2026-07-17,^VIX9D,14.0", result.raw_text)
        self.assertIn("2026-08-07,^SKEW,145.0", result.raw_text)
        self.assertIn("vix_9d", result.notes)
        self.assertIn("vix_3m", result.notes)
        self.assertIn("vix_6m", result.notes)

    def test_yahoo_failure_preserves_unrelated_context_rows_and_audit(self):
        def unavailable(**_kwargs):
            raise RuntimeError("Yahoo unavailable")

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            yahoo = build_default_providers(
                start=date(2026, 8, 3),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=unavailable,
            )["yahoo_volatility_signals"]

            required = ContextProvider(
                spec=ProviderSpec(
                    name="required_fixture",
                    category="financial_conditions",
                    source_tier="public",
                    requiredness="required",
                    provider_version="fixture-v1",
                    schema_version="context-metric-v1",
                    frequency="daily",
                    freshness_days=None,
                ),
                fetch=lambda: ProviderResult(
                    category="financial_conditions",
                    rows=metric_rows(
                        as_of_date=date(2026, 8, 8),
                        category="financial_conditions",
                        market="US",
                        source="Fixture",
                        source_url="https://example.test/fixture",
                        frequency="daily",
                        values={"fixture_metric": 1.0},
                        units={"fixture_metric": "ratio"},
                    ),
                    raw_text="fixture",
                    source="Fixture",
                    source_url="https://example.test/fixture",
                ),
            )

            tables = run_weekly_context(
                {
                    "required_fixture": required,
                    "yahoo_volatility_signals": yahoo,
                },
                as_of_date=date(2026, 8, 9),
            )

        self.assertEqual(
            [row["metric_code"] for row in tables["financial_conditions"]],
            ["fixture_metric"],
        )
        self.assertEqual(
            {row["provider"]: row["status"] for row in tables["source_log"]},
            {
                "required_fixture": "OK",
                "yahoo_volatility_signals": "FETCH_FAILED",
            },
        )
        yahoo_audit = next(
            row
            for row in tables["source_log"]
            if row["provider"] == "yahoo_volatility_signals"
        )
        self.assertEqual(yahoo_audit["observations"], 0)
        self.assertEqual(yahoo_audit["requiredness"], "optional")
        self.assertEqual(yahoo_audit["source_url"], "https://finance.yahoo.com/")


if __name__ == "__main__":
    unittest.main()
