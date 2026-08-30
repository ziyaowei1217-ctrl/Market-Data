from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

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
    "macro": "3af0dc58b4fd12c729a36bc151baf7aab343aa2250181081ecc3d23f9a2e5705",
    "context.cftc_contracts": "a006bb29c4cac5053b1fa31a9ff3aae701cbef3c20e994e52957aa51bd39c473",
    "context.company_watchlist": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "context.eia_series": "c9a967fcd4831cfbe9c0a20b19fa0d08475e6d338908997cb7c4c419dafaff08",
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
        self.assertEqual(len(load_macro_asset_universe()), 47)
        providers = build_default_providers(
            start=date(2026, 8, 3),
            end=date(2026, 8, 9),
            environ={},
        )
        self.assertIn("yahoo_volatility_signals", providers)

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
