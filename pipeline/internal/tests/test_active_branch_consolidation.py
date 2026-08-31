import json
from pathlib import Path
import unittest

from pipeline.internal.capital_weekly.weekly_release import (
    DATASET_CONTRACT_VERSION,
    OUTPUT_BUSINESS_FILES,
    SUPPORTED_DATASET_CONTRACT_VERSIONS,
    release_datasets_for_contract,
)


CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"
COMMODITY_TABLES = {
    ("macro_assets", "commodity_price_history.csv"),
    ("weekly_context", "commodity_metric_history.csv"),
    ("weekly_context", "commodity_research_facts.csv"),
}


class UnifiedReleaseContractTests(unittest.TestCase):
    def test_contract_six_is_additive_and_preserves_contract_five(self):
        contract_one = {
            ('equity_indices', '02_equity_indices.csv'),
            ('equity_indices', 'source_log.csv'),
            ('equity_sectors', '03_equity_sectors.csv'),
            ('equity_sectors', 'sector_divergence.csv'),
            ('equity_sectors', 'source_log.csv'),
            ('gics_sectors', '03_gics_sectors.csv'),
            ('gics_sectors', 'source_log.csv'),
            ('macro_assets', 'commodities.csv'),
            ('macro_assets', 'fixed_income.csv'),
            ('macro_assets', 'foreign_exchange.csv'),
            ('macro_assets', 'macro_divergence.csv'),
            ('macro_assets', 'money_market.csv'),
            ('macro_assets', 'policy_rates.csv'),
            ('macro_assets', 'source_log.csv'),
            ('weekly_context', 'commodity_fundamentals.csv'),
            ('weekly_context', 'company_events.csv'),
            ('weekly_context', 'events.csv'),
            ('weekly_context', 'financial_conditions.csv'),
            ('weekly_context', 'market_internals.csv'),
            ('weekly_context', 'positioning_flows.csv'),
            ('weekly_context', 'source_log.csv'),
        }
        expected_contracts = {
            1: contract_one,
            2: contract_one | {('weekly_context', 'economic_releases.csv')},
            3: contract_one
            | {('weekly_context', 'economic_releases.csv')}
            | {
                ('macro_assets', 'cross_asset.csv'),
                ('macro_assets', 'liquidity.csv'),
            },
            4: contract_one
            | {('weekly_context', 'economic_releases.csv')}
            | {
                ('macro_assets', 'cross_asset.csv'),
                ('macro_assets', 'liquidity.csv'),
            }
            | {('weekly_context', 'fund_flows.csv')},
            5: contract_one
            | {('weekly_context', 'economic_releases.csv')}
            | {
                ('macro_assets', 'cross_asset.csv'),
                ('macro_assets', 'liquidity.csv'),
            }
            | {('weekly_context', 'fund_flows.csv')}
            | {
                ('weekly_context', 'capital_markets.csv'),
                ('weekly_context', 'company_fundamentals.csv'),
            },
        }
        for version in range(1, 6):
            historic = {
                (item.pipeline, item.filename)
                for item in release_datasets_for_contract(version)
            }
            self.assertTrue(historic, f"contract {version} must resolve datasets")
            self.assertEqual(historic, expected_contracts[version])
            self.assertTrue(
                COMMODITY_TABLES.isdisjoint(historic),
                f"contract {version} must exclude commodity tables",
            )
        self.assertEqual(DATASET_CONTRACT_VERSION, 6)
        self.assertEqual(SUPPORTED_DATASET_CONTRACT_VERSIONS, frozenset(range(1, 7)))
        contract_five = {
            (item.pipeline, item.filename)
            for item in release_datasets_for_contract(5)
        }
        contract_six = {
            (item.pipeline, item.filename)
            for item in release_datasets_for_contract(6)
        }
        self.assertTrue(COMMODITY_TABLES.isdisjoint(contract_five))
        self.assertTrue(COMMODITY_TABLES.issubset(contract_six))
        self.assertEqual(
            OUTPUT_BUSINESS_FILES,
            ("indices.json", "sectors.json", "gics.json", "macro.json", "context.json"),
        )

    def test_production_config_is_the_exact_semantic_union(self):
        document = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            set(document),
            {"schema_version", "indices", "sectors", "gics", "macro", "context", "commodity_research"},
        )
        self.assertEqual(len(document["indices"]), 20)
        self.assertEqual(len(document["sectors"]), 34)
        self.assertEqual(len(document["gics"]), 11)
        self.assertEqual(len(document["macro"]), 81)
        self.assertEqual(set(document["context"]), {
            "breadth_universe", "cftc_contracts", "commodity_http",
            "company_watchlist", "eia_series", "financial_conditions",
            "metals", "usda_esr", "usda_psd", "yahoo_volatility",
        })
        self.assertEqual(len(document["context"]["cftc_contracts"]), 18)
        self.assertEqual(len(document["context"]["eia_series"]), 33)
        self.assertEqual(document["context"]["company_watchlist"], [])
        by_code = {row["series_code"]: row for row in document["macro"]}
        self.assertEqual(len(by_code), 81)
        self.assertEqual(by_code["WTI"]["provider"], "eia_v2")
        self.assertEqual(by_code["BRENT"]["provider"], "eia_v2")
        self.assertEqual(by_code["COMEX_GOLD"]["provider"], "world_bank_pink_sheet")
        self.assertEqual(by_code["BTC_USD"]["price_kind"], "vendor_proxy")
        cftc_by_family = {}
        for row in document["context"]["cftc_contracts"]:
            cftc_by_family.setdefault(row["report_family"], set()).add(
                row["contract_code"]
            )
        self.assertEqual(len(cftc_by_family["tff"]), 2)
        self.assertEqual(len(cftc_by_family["disaggregated"]), 16)
        eia_by_provider = {}
        for row in document["context"]["eia_series"]:
            eia_by_provider.setdefault(row["provider"], []).append(row)
        self.assertEqual(
            {name: len(rows) for name, rows in eia_by_provider.items()},
            {
                "eia_natural_gas": 13,
                "eia_refined_products": 19,
                "eia_commodities": 1,
            },
        )
        self.assertEqual(
            eia_by_provider["eia_commodities"],
            [
                {
                    "metric_code": "eia_weekly_petroleum_wtestus1",
                    "metric_name": "EIA weekly petroleum series WTESTUS1",
                    "route": "petroleum/sum/sndw",
                    "frequency": "weekly",
                    "series": "WTESTUS1",
                    "expected_unit": "Thousand Barrels",
                    "provider": "eia_commodities",
                    "freshness_days": "10",
                }
            ],
        )
        research_codes = {
            row["commodity_code"]
            for row in document["commodity_research"]["universe"]
        }
        self.assertNotIn("BTC_USD", research_codes)


if __name__ == "__main__":
    unittest.main()
