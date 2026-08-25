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
        "contract_code,metric_code\n13874A,sp500\n", encoding="utf-8"
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
                "federal_reserve_calendar",
                "census_calendar",
                "nasdaq_market_summary",
                "cftc_tff",
                "finra_margin",
                "sec_company_events",
                "eia_commodities",
                "fred_financial_conditions",
                "yahoo_volatility_signals",
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
        self.assertEqual(providers["bls_calendar"].spec.requiredness, "required")
        self.assertEqual(providers["nasdaq_market_summary"].spec.source_tier, "public")
        self.assertEqual(providers["nasdaq_market_summary"].spec.provider_version, "1.0.0")
        self.assertEqual(
            providers["nasdaq_market_summary"].spec.schema_version,
            "context-metric-v1",
        )

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
