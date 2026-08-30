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
    "macro": "3b140652f11dd61bd9654b2a335814e37b47e260f912482e8f24b34097ef5320",
    "context.cftc_contracts": "49509b00fb72d32b07ce15fa0f3d885e45af93f94eaf520ed6dec873aabe4ae6",
    "context.breadth_universe": "e2de8ddd1e00d211bd7e043278d1eeaadc38002bb17127d62c55e9422e0f1c5c",
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
    def test_public_green_config_is_json_backed_and_watchlist_stays_empty(self):
        breadth = load_config_rows("context.breadth_universe")
        cftc = load_config_rows("context.cftc_contracts")

        self.assertEqual(
            {row["symbol"] for row in breadth},
            {
                "XLC",
                "XLY",
                "XLP",
                "XLE",
                "XLF",
                "XLV",
                "XLI",
                "XLB",
                "XLRE",
                "XLK",
                "XLU",
            },
        )
        self.assertEqual(
            {row["report_type"] for row in cftc},
            {"tff", "disaggregated"},
        )
        self.assertEqual(load_config_rows("context.company_watchlist"), [])

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
        self.assertEqual(len(load_macro_asset_universe()), 70)
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
