from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pipeline.internal.capital_weekly.weekly_release import (
    ReleaseValidationError,
    WeekWindow,
    build_output_bundle,
    validate_output_bundle,
    validate_staged_week,
)
from pipeline.internal.tests.test_capital_weekly_weekly_release import (
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
        write_valid_staged_week(self.staged_week, self.window)
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


if __name__ == "__main__":
    unittest.main()
