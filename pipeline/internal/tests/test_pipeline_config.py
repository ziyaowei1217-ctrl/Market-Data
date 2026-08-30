from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pipeline.internal.capital_weekly.context.eia_commodities import validate_eia_spec
from pipeline.internal.capital_weekly.context.providers import build_default_providers
from pipeline.internal.capital_weekly.equity_indices import load_index_universe
from pipeline.internal.capital_weekly.equity_sectors import load_sector_universe as load_equity_sectors
from pipeline.internal.capital_weekly.gics_sectors import load_sector_universe as load_gics_sectors
from pipeline.internal.capital_weekly.macro_assets import load_macro_asset_universe
from pipeline.internal.common import DEFAULT_CONFIG_PATH, load_config_rows


EXPECTED_SECTION_HASHES = {
    "indices": "52d1af58519dc5d542eb220f108b3242052c5cb9312eeb1ac7ded0ccbc0bc146",
    "sectors": "34c7c2a4d59d19983b9f5ef6af147a9678f494da0e2d8f10f0be779ba41785c5",
    "gics": "5ded3da3ad2789ea91b917038f9e813181a1a5d2b719aa066b0257b9c2649449",
    "macro": "d8142cb57de706af5a1af2e623a7fca9c5af12acca12f9b38a0c72caf9d03e32",
    "context.cftc_contracts": "50504af5344ca4c71b9f0e740ba62f1c160be3aa5cc2dd6141ea613ba0e097e8",
    "context.company_watchlist": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "context.eia_series": "b1c1378337686d8389c25d39d01126a292a26638d633cb9b513b48ddd979fdc0",
    "context.financial_conditions": "f2c336e5c72e7a86a870cb5f07a8fce7d6855464c6587efde50bccff6f7ea3e7",
    "context.yahoo_volatility": "76ab154498b2c96c4f30e38cae6e0817d43b7a4c63e38dd6f4487d3ec179a8dc",
}


def rows_hash(rows: list[dict[str, str]]) -> str:
    encoded = json.dumps(
        rows,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class PipelineConfigTests(unittest.TestCase):
    def test_eia_config_covers_independent_physical_fundamental_families(self):
        rows = load_config_rows("context.eia_series")
        required_fields = {
            "provider", "commodity_code", "commodity_family", "route",
            "frequency", "facets", "metric_code", "metric_name",
            "measurement_kind", "source_description", "expected_unit",
            "freshness_days",
        }
        self.assertTrue(all(required_fields <= set(row) for row in rows))
        by_provider = {}
        for row in rows:
            by_provider.setdefault(row["provider"], set()).add(row["metric_code"])
        self.assertEqual(set(by_provider), {
            "eia_natural_gas", "eia_refined_products",
        })
        self.assertEqual(
            by_provider["eia_natural_gas"],
            {
                "eia_ng_storage_lower48", "eia_ng_storage_east",
                "eia_ng_storage_midwest", "eia_ng_storage_mountain",
                "eia_ng_storage_pacific", "eia_ng_storage_south_central",
                "eia_ng_dry_production", "eia_ng_consumption_residential",
                "eia_ng_consumption_commercial", "eia_ng_consumption_industrial",
                "eia_ng_consumption_electric_power", "eia_ng_lng_imports",
                "eia_ng_lng_exports",
            },
        )
        self.assertEqual(
            by_provider["eia_refined_products"],
            {
                "eia_crude_stocks_ex_spr", "eia_gasoline_stocks",
                "eia_distillate_stocks", "eia_jet_fuel_stocks",
                "eia_propane_stocks", "eia_refinery_utilization",
                "eia_refinery_crude_inputs", "eia_gasoline_production",
                "eia_distillate_production", "eia_jet_fuel_production",
                "eia_gasoline_product_supplied",
                "eia_distillate_product_supplied",
                "eia_jet_fuel_product_supplied", "eia_gasoline_imports",
                "eia_distillate_imports", "eia_jet_fuel_imports",
                "eia_gasoline_exports", "eia_distillate_exports",
                "eia_jet_fuel_exports",
            },
        )
        for row in rows:
            validate_eia_spec(row)
            self.assertIsInstance(row["facets"], dict)
            self.assertTrue(row["facets"])
            self.assertNotIn(row["measurement_kind"], {"price", "return"})

    def test_cftc_contracts_split_financial_and_physical_report_families(self):
        rows = load_config_rows("context.cftc_contracts")
        tff_codes = {
            row["contract_code"] for row in rows if row["report_family"] == "tff"
        }
        commodity_map = {
            row["contract_code"]: (
                row["commodity_code"],
                row["commodity_family"],
            )
            for row in rows
            if row["report_family"] == "disaggregated"
        }

        self.assertEqual(tff_codes, {"13874A", "098662"})
        self.assertEqual(
            commodity_map,
            {
                "023651": ("NATGAS_HH", "natural_gas"),
                "067651": ("WTI", "refined_products"),
                "111659": ("RBOB_US", "refined_products"),
                "022651": ("ULSD_US", "refined_products"),
                "085692": ("COPPER_COMEX", "copper"),
                "088691": ("GOLD_COMEX", "gold"),
                "002602": ("CORN", "grains_oilseeds"),
                "005602": ("SOYBEANS", "grains_oilseeds"),
                "001602": ("WHEAT", "grains_oilseeds"),
                "039601": ("RICE", "grains_oilseeds"),
                "033661": ("COTTON", "softs"),
                "080732": ("SUGAR", "softs"),
                "083731": ("COFFEE", "softs"),
                "073732": ("COCOA", "softs"),
                "057642": ("CATTLE", "livestock"),
                "054642": ("HOGS", "livestock"),
            },
        )
        for row in rows:
            if row["report_family"] == "disaggregated":
                self.assertTrue(row["market_name"])
                self.assertEqual(row["percentile_window"], "156")
                self.assertEqual(row["percentile_min_observations"], "52")

    def test_tff_contracts_use_null_for_inapplicable_commodity_fields(self):
        rows = load_config_rows("context.cftc_contracts")

        for row in rows:
            if row["report_family"] == "tff":
                with self.subTest(contract_code=row["contract_code"]):
                    self.assertIsNone(row["commodity_code"])
                    self.assertIsNone(row["commodity_family"])
                    self.assertIsNone(row["percentile_window"])
                    self.assertIsNone(row["percentile_min_observations"])

    def test_json_matches_lossless_legacy_conversion_hashes(self):
        document = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(document["schema_version"], "1.0")
        for section, expected_hash in EXPECTED_SECTION_HASHES.items():
            with self.subTest(section=section):
                self.assertEqual(rows_hash(load_config_rows(section)), expected_hash)

    def test_all_five_pipelines_use_json_by_default(self):
        self.assertEqual(len(load_index_universe()), 20)
        self.assertEqual(len(load_equity_sectors()), 34)
        self.assertEqual(len(load_gics_sectors()), 11)
        self.assertEqual(len(load_macro_asset_universe()), 58)
        providers = build_default_providers(
            start=date(2026, 8, 3),
            end=date(2026, 8, 9),
            environ={},
        )
        self.assertIn("yahoo_volatility_signals", providers)

    def test_requested_commodity_prices_use_only_official_eia_or_world_bank_sources(self):
        rows = load_config_rows("macro")
        commodity_rows = {
            row["commodity_code"]: row
            for row in rows
            if row.get("commodity_code")
            and row.get("commodity_family") != "digital_asset"
        }
        requested = {
            "NATGAS_HH",
            "WTI",
            "BRENT",
            "COPPER_COMEX",
            "GOLD_COMEX",
            "CORN",
            "SOYBEANS",
            "WHEAT",
            "RICE",
            "COTTON",
            "SUGAR",
            "COFFEE",
            "COCOA",
            "CATTLE",
        }

        self.assertEqual(set(commodity_rows), requested)
        self.assertTrue(all(
            row["provider"] in {"eia_v2", "world_bank_pink_sheet"}
            for row in commodity_rows.values()
        ))
        self.assertTrue(all(
            row["price_kind"]
            in {"official_cash", "official_monthly_benchmark"}
            for row in commodity_rows.values()
        ))
        self.assertEqual(commodity_rows["WTI"]["provider_symbol"], "RWTC")
        self.assertEqual(commodity_rows["BRENT"]["provider_symbol"], "RBRTE")
        self.assertEqual(
            commodity_rows["NATGAS_HH"]["provider_symbol"],
            "RNGWHHD",
        )
        btc = next(row for row in rows if row.get("commodity_code") == "BTC_USD")
        self.assertEqual(btc["provider"], "yahoo_chart")
        self.assertEqual(btc["commodity_family"], "digital_asset")

    def test_default_loader_returns_an_independent_copy(self):
        first = load_config_rows("indices")
        second = load_config_rows("indices")
        first[0]["ticker"] = "changed"
        self.assertNotEqual(first, second)

    def test_explicit_csv_path_remains_supported_for_test_universes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "universe.csv"
            path.write_text("code,label\nA,Alpha\n", encoding="utf-8")
            self.assertEqual(
                load_config_rows("ignored", path),
                [{"code": "A", "label": "Alpha"}],
            )

    def test_unknown_json_section_is_rejected_clearly(self):
        with self.assertRaisesRegex(KeyError, "unknown config section"):
            load_config_rows("context.missing")


if __name__ == "__main__":
    unittest.main()
