from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from pipeline import refresh
from pipeline.internal.capital_weekly.weekly_release import (
    ReleaseValidationError,
    WeekWindow,
    validate_output_bundle,
    validate_staged_week,
)
from pipeline.internal.tests.test_capital_weekly_weekly_release import (
    exact_gate_config,
    write_exact_gate_fixture,
    write_valid_staged_week,
)


def write_complete_week(outputs: Path, start: date, end: date) -> Path:
    window = WeekWindow(start, end, f"week_{start:%Y%m%d}-{end:%Y%m%d}")
    week = outputs / window.week_id
    staged_outputs = write_valid_staged_week(week, window)
    write_exact_gate_fixture(staged_outputs)
    manifest = validate_staged_week(week, window)
    (week / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return week


class OfflineOutputMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.outputs = self.root / "outputs"
        self.outputs.mkdir()
        config_path = self.root / "exact-gate-config.json"
        config_path.write_text(json.dumps(exact_gate_config()), encoding="utf-8")
        config_patcher = patch(
            "pipeline.internal.common.DEFAULT_CONFIG_PATH",
            config_path,
        )
        config_patcher.start()
        self.addCleanup(config_patcher.stop)

    def test_selects_newest_valid_formal_week_only(self):
        older = write_complete_week(
            self.outputs,
            date(2026, 8, 3),
            date(2026, 8, 9),
        )
        newest_valid = write_complete_week(
            self.outputs,
            date(2026, 8, 10),
            date(2026, 8, 16),
        )
        failed = write_complete_week(
            self.outputs,
            date(2026, 8, 17),
            date(2026, 8, 23),
        )
        failed_manifest = json.loads((failed / "manifest.json").read_text())
        failed_manifest["status"] = "failed"
        (failed / "manifest.json").write_text(json.dumps(failed_manifest), encoding="utf-8")
        (self.outputs / "week_20260824-20260830_draft").mkdir()
        (self.outputs / "ad_hoc_20260824-20260830").mkdir()

        selected = refresh.select_latest_complete_week(self.outputs)

        self.assertEqual(selected, newest_valid)
        self.assertTrue(older.is_dir())
        self.assertTrue(failed.is_dir())

    def test_rejects_newer_malformed_hash_mismatched_and_inconsistent_candidates(self):
        valid = write_complete_week(
            self.outputs,
            date(2026, 8, 3),
            date(2026, 8, 9),
        )
        malformed = self.outputs / "week_20260810-20260816"
        malformed.mkdir()
        (malformed / "manifest.json").write_text("{", encoding="utf-8")
        mismatched = write_complete_week(
            self.outputs,
            date(2026, 8, 17),
            date(2026, 8, 23),
        )
        index_file = next(mismatched.rglob("02_equity_indices.csv"))
        index_file.write_text(index_file.read_text() + "\n", encoding="utf-8")
        inconsistent = write_complete_week(
            self.outputs,
            date(2026, 8, 24),
            date(2026, 8, 30),
        )
        inconsistent_manifest = json.loads((inconsistent / "manifest.json").read_text())
        inconsistent_manifest["week_end"] = "2026-08-29"
        (inconsistent / "manifest.json").write_text(
            json.dumps(inconsistent_manifest), encoding="utf-8"
        )
        symlink = self.outputs / "week_20260831-20260906"
        symlink.symlink_to(valid, target_is_directory=True)

        self.assertEqual(refresh.select_latest_complete_week(self.outputs), valid)

    def test_raises_when_no_complete_formal_week_exists(self):
        (self.outputs / "week_20260810-20260816_draft").mkdir()
        with self.assertRaisesRegex(ReleaseValidationError, "No valid complete week"):
            refresh.select_latest_complete_week(self.outputs)

    def test_cli_offline_conversion_never_calls_pipeline_runner(self):
        source = write_complete_week(
            self.outputs,
            date(2026, 8, 3),
            date(2026, 8, 9),
        )
        release_calls = []
        stdout = StringIO()

        with patch.object(refresh, "PROJECT_ROOT", self.root), redirect_stdout(stdout):
            result = refresh.main(
                ["--from-existing", "outputs"],
                release_runner=lambda *args, **kwargs: release_calls.append((args, kwargs)),
            )

        self.assertEqual(result, 0)
        self.assertEqual(release_calls, [])
        self.assertEqual(stdout.getvalue().strip(), str((self.root / "output").resolve()))
        release = validate_output_bundle(self.root / "output")
        self.assertEqual(release["source_week_id"], source.name)


if __name__ == "__main__":
    unittest.main()
