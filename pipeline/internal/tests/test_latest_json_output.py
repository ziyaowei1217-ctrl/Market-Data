from __future__ import annotations

import hashlib
import json
import math
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from pipeline.internal.capital_weekly.weekly_release import (
    ReleaseValidationError,
    WeekWindow,
    build_output_bundle,
    validate_output_bundle,
    validate_staged_week,
)
from pipeline.internal.tests.test_capital_weekly_weekly_release import (
    exact_gate_config,
    write_complete_commodity_research_fixture,
    write_complete_v2_release_fixture,
    write_valid_staged_week,
)


EXPECTED_FILES = {
    "indices.json",
    "sectors.json",
    "gics.json",
    "macro.json",
    "context.json",
    "release.json",
}

SUPPORTED_COMMODITY_CODES = {
    "NATGAS_HH": "natural_gas",
    "WTI": "refined_products",
    "RBOB_US": "refined_products",
    "ULSD_US": "refined_products",
    "JET_FUEL_US": "refined_products",
    "PROPANE_US": "refined_products",
    "COPPER_COMEX": "copper",
    "GOLD_COMEX": "gold",
    "CORN": "grains_oilseeds",
    "SOYBEANS": "grains_oilseeds",
    "WHEAT": "grains_oilseeds",
    "RICE": "grains_oilseeds",
    "COTTON": "softs",
    "SUGAR": "softs",
    "COFFEE": "softs",
    "COCOA": "softs",
    "CATTLE": "livestock",
    "HOGS": "livestock",
}


class LatestJsonOutputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.window = WeekWindow(
            date(2026, 8, 3),
            date(2026, 8, 9),
            "week_20260803-20260809",
        )
        self.staged_week = self.root / self.window.week_id
        config_path = self.root / "exact-gate-config.json"
        config_path.write_text(json.dumps(exact_gate_config()), encoding="utf-8")
        config_patcher = patch(
            "pipeline.internal.common.DEFAULT_CONFIG_PATH",
            config_path,
        )
        config_patcher.start()
        self.addCleanup(config_patcher.stop)
        outputs = write_valid_staged_week(self.staged_week, self.window)
        write_complete_commodity_research_fixture(outputs)
        manifest = validate_staged_week(self.staged_week, self.window)
        (self.staged_week / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.output = self.root / "output"

    def tearDown(self):
        self.temporary.cleanup()

    def test_builds_exact_stable_files_with_one_release_identity(self):
        release = build_output_bundle(
            self.staged_week,
            self.output,
            release_id="fixture-release",
        )

        self.assertEqual({path.name for path in self.output.iterdir()}, EXPECTED_FILES)
        identities = {
            json.loads(path.read_text(encoding="utf-8"))["release_id"]
            for path in self.output.glob("*.json")
        }
        self.assertEqual(identities, {"fixture-release"})
        self.assertEqual(release, validate_output_bundle(self.output))

    def test_fixture_publishes_complete_commodity_research_coverage(self):
        build_output_bundle(self.staged_week, self.output)

        release = validate_output_bundle(self.output)
        self.assertEqual(
            [(pipeline["name"], pipeline["status"]) for pipeline in release["pipelines"]],
            [
                ("indices", "complete"),
                ("sectors", "complete"),
                ("gics", "complete"),
                ("macro", "complete"),
                ("context", "complete"),
            ],
        )
        macro = json.loads((self.output / "macro.json").read_text(encoding="utf-8"))
        context = json.loads(
            (self.output / "context.json").read_text(encoding="utf-8")
        )
        rows = [
            *macro["tables"]["commodities"],
            *context["tables"]["commodity_fundamentals"],
            *context["tables"]["positioning_flows"],
        ]
        research_rows = [
            row for row in rows if row.get("commodity_family") != "digital_asset"
        ]
        self.assertEqual(
            {row["commodity_family"] for row in research_rows},
            {
                "natural_gas",
                "refined_products",
                "copper",
                "gold",
                "grains_oilseeds",
                "softs",
                "livestock",
            },
        )
        for row in research_rows:
            code = row.get("commodity_code")
            self.assertEqual(SUPPORTED_COMMODITY_CODES.get(code), row["commodity_family"])
            self.assertRegex(row["source_url"], r"^https?://")
            observation_date = row.get("latest_date") or row.get("as_of_date")
            self.assertRegex(observation_date, r"^\d{4}-\d{2}-\d{2}$")
            value = row.get("latest_value", row.get("value"))
            self.assertTrue(value is None or math.isfinite(value))
            self.assertIn(row["qc_flag"], {"OK", "INSUFFICIENT_DATA"})
        self.assertNotIn("BTC_USD", {row.get("commodity_code") for row in research_rows})

    def test_converts_numbers_blanks_and_empty_optional_tables_strictly(self):
        build_output_bundle(self.staged_week, self.output)

        indices = json.loads((self.output / "indices.json").read_text(encoding="utf-8"))
        context = json.loads((self.output / "context.json").read_text(encoding="utf-8"))
        self.assertIsInstance(
            indices["tables"]["indices"][0]["latest_value"],
            (int, float),
        )
        self.assertNotIsInstance(
            indices["tables"]["indices"][0]["latest_value"],
            str,
        )
        self.assertIsNone(context["source_log"][0]["freshness_days"])
        self.assertEqual(context["tables"]["events"], [])
        self.assertEqual(context["tables"]["economic_releases"], [])
        serialized = "\n".join(
            path.read_text(encoding="utf-8") for path in self.output.glob("*.json")
        )
        self.assertNotIn("NaN", serialized)
        self.assertNotIn("Infinity", serialized)

    def test_release_hashes_cover_exactly_the_five_business_files(self):
        release = build_output_bundle(self.staged_week, self.output)

        entries = {entry["name"]: entry for entry in release["files"]}
        self.assertEqual(set(entries), EXPECTED_FILES - {"release.json"})
        for name, entry in entries.items():
            self.assertEqual(
                entry["sha256"],
                hashlib.sha256((self.output / name).read_bytes()).hexdigest(),
            )

    def test_mutated_business_file_fails_validation(self):
        build_output_bundle(self.staged_week, self.output)
        path = self.output / "indices.json"
        path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")

        with self.assertRaisesRegex(ReleaseValidationError, "hash mismatch"):
            validate_output_bundle(self.output)


class ContractThreeJsonOutputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.window = WeekWindow(
            date(2026, 8, 3),
            date(2026, 8, 9),
            "week_20260803-20260809",
        )
        self.staged_week = self.root / self.window.week_id
        outputs = write_valid_staged_week(self.staged_week, self.window)
        write_complete_v2_release_fixture(outputs)
        manifest = validate_staged_week(
            self.staged_week,
            self.window,
            dataset_contract_version=3,
        )
        (self.staged_week / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.output = self.root / "output"

    def test_contract_three_publishes_exact_six_files_and_additive_tables(self):
        release = build_output_bundle(
            self.staged_week,
            self.output,
            release_id="v2-fixture-release",
        )

        self.assertEqual({path.name for path in self.output.iterdir()}, EXPECTED_FILES)
        self.assertEqual(release["dataset_contract_version"], 3)
        macro = json.loads((self.output / "macro.json").read_text(encoding="utf-8"))
        context = json.loads((self.output / "context.json").read_text(encoding="utf-8"))
        self.assertEqual(macro["dataset_contract_version"], 3)
        self.assertEqual(context["dataset_contract_version"], 3)
        self.assertIn("commodity_price_history", macro["tables"])
        self.assertIn("commodity_metric_history", context["tables"])
        self.assertIn("commodity_research_facts", context["tables"])
        self.assertEqual(
            set(macro["tables"]) - {
                "fixed_income", "policy_rates", "money_market",
                "foreign_exchange", "commodities", "divergence",
            },
            {"commodity_price_history"},
        )
        self.assertEqual(
            set(context["tables"]) - {
                "events", "economic_releases", "financial_conditions",
                "market_internals", "positioning_flows", "company_events",
                "commodity_fundamentals",
            },
            {"commodity_metric_history", "commodity_research_facts"},
        )

    def test_contract_three_facts_publish_arrays_resolving_to_history_rows(self):
        build_output_bundle(self.staged_week, self.output)

        macro = json.loads((self.output / "macro.json").read_text(encoding="utf-8"))
        context = json.loads((self.output / "context.json").read_text(encoding="utf-8"))
        history_ids = {
            row["record_id"]
            for row in (
                *macro["tables"]["commodity_price_history"],
                *context["tables"]["commodity_metric_history"],
            )
        }
        facts = context["tables"]["commodity_research_facts"]
        self.assertEqual(len(facts), 8)
        for fact in facts:
            with self.subTest(fact_code=fact["fact_code"]):
                self.assertIsInstance(fact["input_record_ids"], list)
                self.assertIsInstance(fact["source_urls"], list)
                self.assertTrue(fact["input_record_ids"])
                self.assertLessEqual(set(fact["input_record_ids"]), history_ids)
                self.assertTrue(all(url.startswith("https://") for url in fact["source_urls"]))
        self.assertEqual(validate_output_bundle(self.output)["dataset_contract_version"], 3)


if __name__ == "__main__":
    unittest.main()
