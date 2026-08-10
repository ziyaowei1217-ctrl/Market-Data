from datetime import date
from pathlib import Path
import tempfile
import unittest

from capital_weekly.context.providers import (
    build_default_providers,
    metric_rows,
    not_configured_result,
)
from capital_weekly.context.common import METRIC_FIELDS


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
                "hkex_microstructure",
                "sse_microstructure",
                "szse_microstructure",
            }.issubset(providers)
        )


if __name__ == "__main__":
    unittest.main()
