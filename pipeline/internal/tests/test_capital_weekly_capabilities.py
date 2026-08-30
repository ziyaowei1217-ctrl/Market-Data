import csv
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pipeline.internal.capital_weekly.capabilities import CAPABILITY_SPECS, build_capability_manifest


EXPECTED_CAPABILITY_IDS = {
    "liquidity.fed_balance_sheet", "liquidity.tga", "liquidity.on_rrp",
    "liquidity.net_liquidity", "rates.ust_curve", "rates.curve_spreads",
    "rates.real_yields", "rates.breakeven_inflation",
    "rates.fed_funds_sofr", "macro.public_actuals",
    "macro.cpi", "macro.employment", "macro.wages",
    "macro.unemployment", "macro.gdp", "macro.pce_inflation",
    "macro.personal_income", "macro.personal_spending",
    "macro.retail_sales", "macro.housing", "macro.durable_goods",
    "macro.surprise_proxy", "positioning.cftc_cot",
    "positioning.cftc_percentile", "positioning.cta",
    "positioning.dealer_gamma", "volatility.vix", "volatility.vvix",
    "volatility.vix_term_structure", "volatility.put_call_ratio",
    "volatility.move", "credit.hy_oas", "credit.ig_oas",
    "credit.hy_ig_spread", "credit.cdx", "internals.above_20dma",
    "internals.above_50dma", "internals.above_200dma",
    "internals.advance_decline", "internals.new_high_low",
    "internals.equal_cap_weight", "fund_flow.etf_implied_flow",
    "fund_flow.etf_aum", "fund_flow.epfr", "fund_flow.mutual_fund",
    "china_flow.southbound", "china_flow.northbound",
    "earnings.reported_eps", "earnings.revenue_margin_fcf",
    "earnings.beat_miss", "earnings.forward_eps_consensus",
    "earnings.eps_revision_breadth", "earnings.sales_revision_breadth",
    "earnings.guidance_proxy", "fundamentals.sec_filings",
    "fundamentals.xbrl_company_facts", "valuation.trailing_pe",
    "valuation.price_to_book", "valuation.ev_ebitda",
    "valuation.forward_pe", "valuation.historical_percentiles",
    "cross_asset.stock_bond", "cross_asset.equity_usd",
    "cross_asset.gold_real_yield", "cross_asset.oil_breakeven",
    "commodities.gold_oil_copper", "fx.dxy", "fx.major",
    "events.fomc", "events.fomc_decisions", "events.economic_calendar",
    "events.earnings_calendar", "capital_markets.ipo_filings",
    "capital_markets.ipo_issuance_volume",
    "capital_markets.ma_announcements", "capital_markets.ecm_dcm",
    "alternative.google_trends", "alternative.app_downloads",
    "alternative.web_traffic",
}


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class CapabilityManifestTests(unittest.TestCase):
    def test_registry_covers_every_approved_matrix_row_with_unique_ids(self):
        ids = [spec.capability_id for spec in CAPABILITY_SPECS]

        self.assertEqual(len(ids), 79)
        self.assertEqual(set(ids), EXPECTED_CAPABILITY_IDS)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(spec.module and spec.label for spec in CAPABILITY_SPECS))

    def test_manifest_uses_cutoff_evidence_and_never_emits_placeholder_values(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            macro = root / "capital_weekly_macro_assets_python_20260809"
            context = root / "capital_weekly_context_20260809"
            write_csv(
                macro / "liquidity.csv",
                ["series_code", "latest_date", "qc_flag"],
                [
                    {"series_code": code, "latest_date": "2026-08-07", "qc_flag": "OK"}
                    for code in (
                        "FED_TOTAL_ASSETS", "TGA_BALANCE", "ON_RRP_TAKE_UP",
                        "FED_NET_LIQUIDITY",
                    )
                ],
            )
            write_csv(
                context / "economic_releases.csv",
                ["indicator_code", "as_of_date", "qc_flag"],
                [{
                    "indicator_code": "CORE_CPI_MOMENTUM_GAP_PROXY",
                    "as_of_date": "2026-08-09",
                    "qc_flag": "OK",
                }],
            )
            write_csv(
                context / "financial_conditions.csv",
                ["metric_code", "as_of_date", "qc_flag"],
                [{
                    "metric_code": "vix_1m_level",
                    "as_of_date": "2026-08-10",
                    "qc_flag": "OK",
                }],
            )
            write_csv(
                context / "source_log.csv",
                ["provider", "status", "category"],
                [
                    {
                        "provider": "sec_company_fundamentals",
                        "status": "NOT_CONFIGURED",
                        "category": "company_fundamentals",
                    },
                    {
                        "provider": "ism_manufacturing_pmi",
                        "status": "UNAVAILABLE_LICENSED",
                        "category": "economic_releases",
                    },
                ],
            )

            capabilities = build_capability_manifest(root, date(2026, 8, 9))

        by_id = {item["capability_id"]: item for item in capabilities}
        for capability_id in (
            "liquidity.fed_balance_sheet", "liquidity.tga",
            "liquidity.on_rrp", "liquidity.net_liquidity",
        ):
            self.assertEqual(by_id[capability_id]["status"], "available")
            self.assertEqual(
                by_id[capability_id]["evidence_files"],
                ["capital_weekly_macro_assets_python_20260809/liquidity.csv"],
            )
        self.assertEqual(by_id["macro.surprise_proxy"]["status"], "available")
        self.assertTrue(by_id["macro.surprise_proxy"]["proxy"])
        self.assertEqual(by_id["volatility.vix"]["status"], "failed")
        self.assertEqual(
            by_id["fundamentals.xbrl_company_facts"]["status"],
            "not_configured",
        )
        self.assertEqual(
            by_id["positioning.cta"]["status"], "unavailable_licensed"
        )
        self.assertEqual(
            by_id["alternative.google_trends"]["status"], "not_configured"
        )
        self.assertEqual(
            by_id["alternative.app_downloads"]["status"],
            "unavailable_licensed",
        )
        self.assertTrue(all(item["reason"] for item in capabilities))
        self.assertTrue(
            all(
                set(item) == {
                    "capability_id", "module", "label", "status", "reason",
                    "proxy", "evidence_files",
                }
                for item in capabilities
            )
        )
        self.assertFalse(any("value" in item for item in capabilities))

    def test_each_public_macro_module_requires_its_own_exact_evidence(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = root / "capital_weekly_context_20260809"
            write_csv(
                context / "economic_releases.csv",
                ["indicator_code", "as_of_date", "qc_flag"],
                [
                    {
                        "indicator_code": code,
                        "as_of_date": "2026-08-09",
                        "qc_flag": "OK",
                    }
                    for code in (
                        "CPI_INDEX_NSA", "CORE_CPI_INDEX_NSA", "NFP_CHANGE",
                        "UNEMPLOYMENT_RATE", "REAL_GDP_QOQ_SAAR",
                        "REAL_GDP_YOY_PCT", "PCE_PRICE_INDEX_YOY_PCT",
                        "CORE_PCE_PRICE_INDEX_YOY_PCT", "RETAIL_SALES_MOM",
                        "RETAIL_SALES_YOY_PCT",
                    )
                ],
            )
            write_csv(
                context / "events.csv",
                ["event_name", "event_type", "event_date", "qc_flag"],
                [{
                    "event_name": "FOMC policy decision",
                    "event_type": "central_bank",
                    "event_date": "2026-07-29",
                    "qc_flag": "OK",
                }],
            )

            capabilities = build_capability_manifest(root, date(2026, 8, 9))

        by_id = {item["capability_id"]: item for item in capabilities}
        for capability_id in (
            "macro.cpi", "macro.employment", "macro.unemployment",
            "macro.gdp", "macro.pce_inflation", "macro.retail_sales",
            "events.fomc",
        ):
            self.assertEqual(by_id[capability_id]["status"], "available")
        for capability_id in (
            "macro.wages", "macro.personal_income", "macro.personal_spending",
            "macro.housing", "macro.durable_goods", "events.fomc_decisions",
        ):
            self.assertEqual(by_id[capability_id]["status"], "failed")

    def test_implemented_optional_provider_status_maps_without_inventing_rows(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = root / "capital_weekly_context_20260809"
            write_csv(
                context / "source_log.csv",
                ["provider", "status", "category"],
                [{
                    "provider": "ishares_ivv_fund",
                    "status": "POINT_IN_TIME_UNAVAILABLE",
                    "category": "fund_flows",
                }],
            )
            write_csv(
                context / "fund_flows.csv",
                ["metric_code", "as_of_date", "qc_flag"],
                [],
            )

            capabilities = build_capability_manifest(root, date(2026, 8, 9))

        by_id = {item["capability_id"]: item for item in capabilities}
        self.assertEqual(by_id["fund_flow.etf_aum"]["status"], "failed")
        self.assertEqual(by_id["fund_flow.etf_aum"]["evidence_files"], [])
        self.assertIn("POINT_IN_TIME_UNAVAILABLE", by_id["fund_flow.etf_aum"]["reason"])

    def test_raw_cache_filename_cannot_shadow_the_registered_business_table(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            macro = root / "capital_weekly_macro_assets_python_20260809"
            write_csv(
                macro / "liquidity.csv",
                ["series_code", "latest_date", "qc_flag"],
                [{
                    "series_code": "FED_TOTAL_ASSETS",
                    "latest_date": "2026-08-07",
                    "qc_flag": "OK",
                }],
            )
            write_csv(
                macro / "raw" / "liquidity.csv",
                ["untrusted"],
                [{"untrusted": "raw cache"}],
            )

            capabilities = build_capability_manifest(root, date(2026, 8, 9))

        by_id = {item["capability_id"]: item for item in capabilities}
        self.assertEqual(
            by_id["liquidity.fed_balance_sheet"]["status"], "available"
        )
        self.assertEqual(
            by_id["liquidity.fed_balance_sheet"]["evidence_files"],
            ["capital_weekly_macro_assets_python_20260809/liquidity.csv"],
        )


if __name__ == "__main__":
    unittest.main()
