from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from pipeline.capital_weekly import weekly_release as weekly_release_module
from pipeline.capital_weekly.release_migration import migrate_releases
from pipeline.capital_weekly.weekly_context import CATEGORY_FIELDS
from pipeline.capital_weekly.weekly_release import (
    ReleaseAlreadyRunning,
    latest_finished_week,
    run_weekly_release,
)
from pipeline.tests.test_capital_weekly_weekly_release import (
    FakePipelineRunner,
    write_csv,
    write_valid_staged_week,
)


HONG_KONG = ZoneInfo("Asia/Hong_Kong")
LEGACY_CONTEXT_SOURCE_LOG_FIELDS = (
    "provider",
    "category",
    "status",
    "observations",
    "as_of_date",
    "source",
    "source_url",
    "elapsed_ms",
    "notes",
)


class ReleaseMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.outputs = self.root / "outputs"
        self.outputs.mkdir()
        self.now = datetime(2026, 8, 12, 9, 30, tzinfo=HONG_KONG)
        self.window = latest_finished_week(self.now)
        self.week = self.outputs / self.window.week_id
        self.pipeline_dirs = write_valid_staged_week(self.week, self.window)
        self.context = self.pipeline_dirs["weekly_context"]

    def make_legacy_contract_week(self):
        (self.context / "economic_releases.csv").unlink()
        write_csv(
            self.context / "source_log.csv",
            LEGACY_CONTEXT_SOURCE_LOG_FIELDS,
            [
                {
                    "provider": "fixture",
                    "category": "market_internals",
                    "status": "OK",
                    "observations": "0",
                    "as_of_date": "2026-08-09",
                    "source": "Fixture",
                    "source_url": "https://example.test/context",
                    "elapsed_ms": "1",
                    "notes": "",
                }
            ],
        )

    def test_dry_run_reports_repairable_blank_optional_files_without_writing(self):
        company = self.context / "company_events.csv"
        company.write_text("\n", encoding="utf-8")
        before = company.read_bytes()

        result = migrate_releases(self.root, dry_run=True, now_hkt=self.now)

        self.assertEqual(result[0].status, "migratable")
        self.assertEqual(
            result[0].repaired_files,
            (
                "capital_weekly_context_20260809/company_events.csv",
            ),
        )
        self.assertEqual(company.read_bytes(), before)
        self.assertFalse((self.week / "manifest.json").exists())

    def test_exact_week_filter_rejects_path_input(self):
        with self.assertRaisesRegex(ValueError, "week_YYYYMMDD-YYYYMMDD"):
            migrate_releases(
                self.root,
                dry_run=True,
                week_id="../week_20260803-20260809",
                now_hkt=self.now,
            )

    def test_migration_publishes_headers_and_a_truthful_manifest(self):
        company = self.context / "company_events.csv"
        company.write_text(" \n", encoding="utf-8")

        result = migrate_releases(self.root, dry_run=False, now_hkt=self.now)

        manifest = json.loads((self.week / "manifest.json").read_text())
        self.assertEqual(result[0].status, "repaired")
        self.assertEqual(manifest["publication_mode"], "migrated")
        self.assertEqual(manifest["manifest_schema_version"], 2)
        self.assertEqual(manifest["dataset_contract_version"], 2)
        self.assertEqual(manifest["migrated_at"], "2026-08-12T09:30:00+08:00")
        self.assertTrue(
            all(
                pipeline["status"] == "validated_legacy"
                for pipeline in manifest["pipelines"]
            )
        )
        self.assertEqual(
            company.read_text(encoding="utf-8").strip(),
            ",".join(CATEGORY_FIELDS["company_events"]),
        )

    def test_migration_versions_a_pre_economic_release_week_as_contract_v1(self):
        self.make_legacy_contract_week()

        result = migrate_releases(self.root, dry_run=False, now_hkt=self.now)

        manifest = json.loads((self.week / "manifest.json").read_text())
        self.assertEqual(result[0].status, "repaired")
        self.assertEqual(manifest["dataset_contract_version"], 1)
        self.assertFalse(
            any(
                entry["path"].endswith("/economic_releases.csv")
                for entry in manifest["files"]
            )
        )

    def test_migration_skips_a_mixed_current_contract_week(self):
        (self.context / "economic_releases.csv").unlink()

        result = migrate_releases(self.root, dry_run=False, now_hkt=self.now)

        self.assertEqual(result[0].status, "skipped")
        self.assertIn("mixed dataset contract", result[0].reason.lower())
        self.assertFalse((self.week / "manifest.json").exists())

    def test_second_run_keeps_valid_manifest_bytes_and_mtime(self):
        migrate_releases(self.root, dry_run=False, now_hkt=self.now)
        manifest = self.week / "manifest.json"
        before = (manifest.read_bytes(), manifest.stat().st_mtime_ns)

        result = migrate_releases(
            self.root,
            dry_run=False,
            now_hkt=datetime(2026, 8, 12, 10, 30, tzinfo=HONG_KONG),
        )

        self.assertEqual(result[0].status, "already-valid")
        self.assertEqual((manifest.read_bytes(), manifest.stat().st_mtime_ns), before)

    def test_existing_manifest_requires_exact_canonical_pipeline_names(self):
        migrate_releases(self.root, dry_run=False, now_hkt=self.now)
        manifest_path = self.week / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["pipelines"][-1]["name"] = "equity_indices"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = migrate_releases(self.root, dry_run=False, now_hkt=self.now)

        self.assertEqual(result[0].status, "skipped")
        self.assertIn("Existing manifest is invalid", result[0].reason)

    def test_existing_manifest_with_mismatched_file_hash_is_skipped(self):
        migrate_releases(self.root, dry_run=False, now_hkt=self.now)
        manifest_path = self.week / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][0]["sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = migrate_releases(self.root, dry_run=False, now_hkt=self.now)

        self.assertEqual(result[0].status, "skipped")
        self.assertIn("Existing manifest is invalid", result[0].reason)

    def test_nonempty_invalid_optional_file_is_skipped_without_changes(self):
        company = self.context / "company_events.csv"
        company.write_text("wrong_header\nvalue\n", encoding="utf-8")
        before = company.read_bytes()

        result = migrate_releases(self.root, dry_run=False, now_hkt=self.now)

        self.assertEqual(result[0].status, "skipped")
        self.assertIn("missing required columns", result[0].reason)
        self.assertEqual(company.read_bytes(), before)
        self.assertFalse((self.week / "manifest.json").exists())

    def test_symlinked_week_file_is_skipped(self):
        company = self.context / "company_events.csv"
        company.unlink()
        outside = self.root / "outside.csv"
        outside.write_text("outside\n", encoding="utf-8")
        company.symlink_to(outside)

        result = migrate_releases(self.root, dry_run=False, now_hkt=self.now)

        self.assertEqual(result[0].status, "skipped")
        self.assertIn("symbolic link", result[0].reason)
        self.assertTrue(company.is_symlink())
        self.assertFalse((self.week / "manifest.json").exists())

    def test_refresh_lock_rejects_formal_migration_without_changing_the_week(self):
        before = {
            path.relative_to(self.week).as_posix(): path.read_bytes()
            for path in self.week.rglob("*")
            if path.is_file()
        }
        lock_path = self.outputs / ".capital_weekly_refresh.lock"
        lock_file = lock_path.open("a+")
        self.addCleanup(lock_file.close)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        result = migrate_releases(self.root, dry_run=False, now_hkt=self.now)

        self.assertEqual(result[0].status, "failed")
        self.assertIn("release write", result[0].reason.lower())
        after = {
            path.relative_to(self.week).as_posix(): path.read_bytes()
            for path in self.week.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)
        self.assertFalse((self.week / "manifest.json").exists())

    def test_formal_migration_lock_rejects_refresh_before_any_pipeline_runs(self):
        runner = FakePipelineRunner()
        refresh_status = self.root / "state" / "refresh-status.json"
        refresh_was_rejected = False
        real_publish = weekly_release_module._publish_directory

        def publish_while_probing_refresh(staging, destination):
            nonlocal refresh_was_rejected
            with self.assertRaises(ReleaseAlreadyRunning):
                run_weekly_release(
                    self.root,
                    now_hkt=self.now,
                    status_path=refresh_status,
                    runner=runner,
                )
            refresh_was_rejected = True
            real_publish(staging, destination)

        with patch(
            "pipeline.capital_weekly.release_migration._publish_directory",
            side_effect=publish_while_probing_refresh,
        ):
            result = migrate_releases(self.root, dry_run=False, now_hkt=self.now)

        self.assertEqual(result[0].status, "repaired")
        self.assertTrue(refresh_was_rejected)
        self.assertEqual(runner.calls, [])
        self.assertFalse(refresh_status.exists())
        self.assertEqual(
            json.loads((self.week / "manifest.json").read_text())["publication_mode"],
            "migrated",
        )

    def test_publish_failure_restores_original_week(self):
        marker = self.week / "original-marker.txt"
        marker.write_text("original", encoding="utf-8")
        original_files = {
            path.relative_to(self.week).as_posix(): path.read_bytes()
            for path in self.week.rglob("*")
            if path.is_file()
        }

        def fail_after_swap(staging, destination):
            backup = destination.with_name(f".{destination.name}.test-backup")
            os.replace(destination, backup)
            try:
                os.replace(staging, destination)
                raise OSError("simulated migration publish failure")
            except Exception:
                os.replace(destination, staging)
                os.replace(backup, destination)
                raise

        with patch(
            "pipeline.capital_weekly.release_migration._publish_directory",
            side_effect=fail_after_swap,
        ):
            result = migrate_releases(self.root, dry_run=False, now_hkt=self.now)

        self.assertEqual(result[0].status, "failed")
        self.assertIn("simulated migration publish failure", result[0].reason)
        restored_files = {
            path.relative_to(self.week).as_posix(): path.read_bytes()
            for path in self.week.rglob("*")
            if path.is_file()
        }
        self.assertEqual(restored_files, original_files)

    def test_migration_reason_hides_absolute_paths_from_filesystem_errors(self):
        secret_path = self.root / "private" / "credentials.csv"

        with patch(
            "pipeline.capital_weekly.release_migration._publish_directory",
            side_effect=OSError(2, "No such file or directory", secret_path),
        ):
            result = migrate_releases(self.root, dry_run=False, now_hkt=self.now)

        self.assertEqual(result[0].status, "failed")
        self.assertIn("credentials.csv", result[0].reason)
        self.assertNotIn(str(self.root), result[0].reason)


class MigrationCliTests(unittest.TestCase):
    @staticmethod
    def load_cli_module():
        script = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "migrate_capital_weekly_releases.py"
        )
        spec = importlib.util.spec_from_file_location(
            "migrate_capital_weekly_releases_cli", script
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_cli_prints_one_json_result_and_forwards_dry_run_and_week(self):
        module = self.load_cli_module()
        calls = []

        def migration_runner(project_root, *, dry_run, week_id):
            calls.append((project_root, dry_run, week_id))
            return [
                module.MigrationResult(
                    week_id="week_20260803-20260809",
                    status="migratable",
                    repaired_files=("context/company_events.csv",),
                )
            ]

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = module.main(
                ["--dry-run", "--week", "week_20260803-20260809"],
                migration_runner=migration_runner,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls[0][1:], (True, "week_20260803-20260809"))
        self.assertEqual(
            json.loads(output.getvalue()),
            {
                "week_id": "week_20260803-20260809",
                "status": "migratable",
                "repaired_files": ["context/company_events.csv"],
                "reason": None,
            },
        )


if __name__ == "__main__":
    unittest.main()
