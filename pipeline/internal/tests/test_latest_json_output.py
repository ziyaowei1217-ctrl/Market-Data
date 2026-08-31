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

UNVERSIONED_LEGACY_TABLES = {
    "indices": {"indices"},
    "sectors": {"sectors", "divergence"},
    "gics": {"sectors"},
    "macro": {
        "fixed_income",
        "policy_rates",
        "money_market",
        "foreign_exchange",
        "commodities",
        "divergence",
    },
    "context": {
        "events",
        "economic_releases",
        "financial_conditions",
        "market_internals",
        "positioning_flows",
        "company_events",
        "commodity_fundamentals",
    },
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

    def _write_document_and_refresh_file_entry(
        self,
        release: dict,
        name: str,
        document: dict,
    ) -> None:
        path = self.output / name
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        entry = next(item for item in release["files"] if item["name"] == name)
        entry["bytes"] = path.stat().st_size
        entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()

    def _make_unversioned_legacy_output(
        self,
        *,
        include_capabilities: bool,
    ) -> dict:
        release = build_output_bundle(self.staged_week, self.output)
        release.pop("dataset_contract_version")
        if not include_capabilities:
            release.pop("capabilities")

        documents = {}
        for pipeline in UNVERSIONED_LEGACY_TABLES:
            name = f"{pipeline}.json"
            document = json.loads((self.output / name).read_text(encoding="utf-8"))
            document.pop("dataset_contract_version")
            allowed_tables = set(UNVERSIONED_LEGACY_TABLES[pipeline])
            if pipeline == "context" and include_capabilities:
                allowed_tables.add("capability_audit")
            document["tables"] = {
                table: rows
                for table, rows in document["tables"].items()
                if table in allowed_tables
            }
            documents[pipeline] = document
            self._write_document_and_refresh_file_entry(release, name, document)

        for entry in release["pipelines"]:
            document = documents[entry["name"]]
            entry["rows"] = {
                **{
                    table: len(rows)
                    for table, rows in document["tables"].items()
                },
                "source_log": len(document["source_log"]),
            }
        (self.output / "release.json").write_text(
            json.dumps(release, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return release

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
        self.assertEqual(context["tables"]["fund_flows"], [])
        self.assertEqual(context["tables"]["company_fundamentals"], [])
        self.assertEqual(context["tables"]["capital_markets"], [])
        release = json.loads(
            (self.output / "release.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            context["tables"]["capability_audit"],
            release["capabilities"],
        )
        self.assertEqual(len(release["capabilities"]), 79)
        serialized = "\n".join(
            path.read_text(encoding="utf-8") for path in self.output.glob("*.json")
        )
        self.assertNotIn("NaN", serialized)
        self.assertNotIn("Infinity", serialized)

    def test_release_hashes_cover_exactly_the_five_business_files(self):
        release = build_output_bundle(self.staged_week, self.output)

        entries = {entry["name"]: entry for entry in release["files"]}
        self.assertEqual(len(entries), 5)
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

    def test_capability_audit_must_match_between_context_and_release(self):
        release = build_output_bundle(self.staged_week, self.output)
        context_path = self.output / "context.json"
        context = json.loads(context_path.read_text(encoding="utf-8"))
        context["tables"]["capability_audit"][0]["reason"] = "tampered"
        context_path.write_text(
            json.dumps(context, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        context_entry = next(
            item for item in release["files"] if item["name"] == "context.json"
        )
        context_entry["bytes"] = context_path.stat().st_size
        context_entry["sha256"] = hashlib.sha256(context_path.read_bytes()).hexdigest()
        (self.output / "release.json").write_text(
            json.dumps(release, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ReleaseValidationError, "capability audit"):
            validate_output_bundle(self.output)

    def test_unversioned_legacy_output_retains_strict_baseline_compatibility(self):
        release = self._make_unversioned_legacy_output(include_capabilities=False)

        self.assertEqual(validate_output_bundle(self.output), release)

        context_path = self.output / "context.json"
        context = json.loads(context_path.read_text(encoding="utf-8"))
        context["tables"]["unexpected"] = []
        self._write_document_and_refresh_file_entry(
            release,
            "context.json",
            context,
        )
        context_pipeline = next(
            item for item in release["pipelines"] if item["name"] == "context"
        )
        context_pipeline["rows"]["unexpected"] = 0
        (self.output / "release.json").write_text(
            json.dumps(release, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ReleaseValidationError, "table contract"):
            validate_output_bundle(self.output)

    def test_unversioned_legacy_capability_audit_must_match_when_present(self):
        release = self._make_unversioned_legacy_output(include_capabilities=True)

        self.assertEqual(validate_output_bundle(self.output), release)

        context_path = self.output / "context.json"
        context = json.loads(context_path.read_text(encoding="utf-8"))
        context["tables"]["capability_audit"][0]["reason"] = "tampered"
        self._write_document_and_refresh_file_entry(
            release,
            "context.json",
            context,
        )
        (self.output / "release.json").write_text(
            json.dumps(release, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ReleaseValidationError, "capability audit"):
            validate_output_bundle(self.output)

    def test_versioned_contract_table_mismatch_remains_rejected(self):
        release = build_output_bundle(self.staged_week, self.output)
        macro_path = self.output / "macro.json"
        macro = json.loads(macro_path.read_text(encoding="utf-8"))
        macro["tables"].pop("liquidity")
        self._write_document_and_refresh_file_entry(release, "macro.json", macro)
        macro_pipeline = next(
            item for item in release["pipelines"] if item["name"] == "macro"
        )
        macro_pipeline["rows"].pop("liquidity")
        (self.output / "release.json").write_text(
            json.dumps(release, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ReleaseValidationError, "table contract"):
            validate_output_bundle(self.output)


class ContractSixJsonOutputTests(unittest.TestCase):
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
            dataset_contract_version=6,
        )
        (self.staged_week / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.output = self.root / "output"

    def test_contract_six_publishes_exact_six_files_and_additive_tables(self):
        release = build_output_bundle(
            self.staged_week,
            self.output,
            release_id="v2-fixture-release",
        )

        self.assertEqual({path.name for path in self.output.iterdir()}, EXPECTED_FILES)
        self.assertEqual(release["dataset_contract_version"], 6)
        macro = json.loads((self.output / "macro.json").read_text(encoding="utf-8"))
        context = json.loads((self.output / "context.json").read_text(encoding="utf-8"))
        self.assertEqual(macro["dataset_contract_version"], 6)
        self.assertEqual(context["dataset_contract_version"], 6)
        self.assertIn("commodity_price_history", macro["tables"])
        self.assertIn("commodity_metric_history", context["tables"])
        self.assertIn("commodity_research_facts", context["tables"])
        self.assertEqual(
            set(macro["tables"]) - {
                "fixed_income", "policy_rates", "money_market",
                "foreign_exchange", "commodities", "liquidity",
                "cross_asset", "divergence",
            },
            {"commodity_price_history"},
        )
        self.assertEqual(
            set(context["tables"]) - {
                "events", "economic_releases", "financial_conditions",
                "market_internals", "positioning_flows", "company_events",
                "commodity_fundamentals", "fund_flows",
                "company_fundamentals", "capital_markets",
                "capability_audit",
            },
            {"commodity_metric_history", "commodity_research_facts"},
        )

    def test_contract_six_facts_publish_arrays_resolving_to_history_rows(self):
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
        self.assertEqual(validate_output_bundle(self.output)["dataset_contract_version"], 6)


if __name__ == "__main__":
    unittest.main()
