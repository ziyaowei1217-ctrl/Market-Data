from __future__ import annotations

import csv
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime
import fcntl
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from pipeline.internal.capital_weekly import weekly_release as weekly_release_module
from pipeline.internal.capital_weekly.weekly_context import CATEGORY_FIELDS
from pipeline.internal.capital_weekly.weekly_release import (
    ReleaseAlreadyRunning,
    ReleasePipelineError,
    ReleaseValidationError,
    build_pipeline_specs,
    latest_finished_week,
    run_latest_release,
    validate_staged_week,
)


RETURN_DATE_FIELDS = [
    "latest_date",
    "daily_base_date",
    "weekly_base_date",
    "mtd_base_date",
    "ytd_base_date",
]
RETURN_NUMERIC_FIELDS = [
    "latest_value",
    "daily_base_value",
    "daily_change",
    "weekly_base_value",
    "weekly_change",
    "mtd_base_value",
    "mtd_change",
    "ytd_base_value",
    "ytd_change",
]
RANK_FIELDS = ["daily_rank", "weekly_rank", "mtd_rank", "ytd_rank"]
INDEX_FIELDS = [
    "region", "index_name_cn", "index_name_en", "ticker", "currency",
    "provider", "provider_symbol", "source", "notes", *RETURN_DATE_FIELDS,
    *RETURN_NUMERIC_FIELDS, "change_unit", "qc_flag", "source_url",
]
SECTOR_FIELDS = [
    "market", "taxonomy", "taxonomy_version", "taxonomy_level", "sector_code",
    "sector_name_cn", "sector_name_en", "ticker", "currency", "provider",
    "provider_symbol", "source", "instrument_type", "sort_order", "notes",
    *RETURN_DATE_FIELDS, *RETURN_NUMERIC_FIELDS, "change_unit", "qc_flag",
    "source_url", *RANK_FIELDS,
]
GICS_FIELDS = [
    "gics_sector_code", "sector_name_cn", "sector_name_en", "ticker",
    "currency", "provider", "provider_symbol", "source", "proxy_type", "notes",
    *RETURN_DATE_FIELDS, *RETURN_NUMERIC_FIELDS, "change_unit", "qc_flag",
    "source_url",
]
COMMODITY_MACRO_FIELDS = [
    "commodity_code",
    "commodity_family",
    "price_kind",
    "known_as_of",
    "provider_route",
]
MACRO_FIELDS = [
    "asset_class", "group", "series_code", "name_cn", "name_en", "provider",
    "provider_symbol", "source", "source_url", "frequency", "level_unit",
    "change_unit", "sort_order", "notes", *RETURN_DATE_FIELDS,
    *RETURN_NUMERIC_FIELDS, "qc_flag", *RANK_FIELDS, *COMMODITY_MACRO_FIELDS,
]
SECTOR_DIVERGENCE_FIELDS = [
    "market", "market_cn", "horizon", "horizon_cn", "valid_count",
    "positive_count", "flat_count", "negative_count", "breadth_ratio",
    "leader_laggard_spread", "dispersion", "median_return", "top_3",
    "bottom_3", "commentary_cn", "qc_flag",
]
MACRO_DIVERGENCE_FIELDS = [
    "asset_class", "group", "group_cn", "horizon", "horizon_cn", "change_unit",
    "valid_count", "up_count", "flat_count", "down_count", "median_change",
    "change_range", "dispersion", "top_movers", "bottom_movers",
    "commentary_cn", "qc_flag",
]
INDEX_SOURCE_LOG_FIELDS = [
    "ticker", "source", "status", "observations", *RETURN_DATE_FIELDS,
    "latest_value", "daily_base_value", "weekly_base_value", "mtd_base_value",
    "ytd_base_value", "elapsed_ms", "source_url", "notes",
]
SECTOR_SOURCE_LOG_FIELDS = [
    "market", "taxonomy", "sector_code", "sector_name_en", "ticker",
    "sort_order", "source", "status", "observations", *RETURN_DATE_FIELDS,
    "latest_value", "daily_base_value", "weekly_base_value", "mtd_base_value",
    "ytd_base_value", "elapsed_ms", "source_url", "notes", "raw_cache_status",
    "raw_cache_error",
]
GICS_SOURCE_LOG_FIELDS = [
    "ticker", "gics_sector_code", "sector_name_en", "source", "status",
    "observations", *RETURN_DATE_FIELDS, "latest_value", "daily_base_value",
    "weekly_base_value", "mtd_base_value", "ytd_base_value", "elapsed_ms",
    "source_url", "notes",
]
MACRO_SOURCE_LOG_FIELDS = [
    "series_code", "sort_order", "source", "status", "error", "observations",
    "latest_date", "latest_value", "source_url", "elapsed_ms",
    "raw_cache_status", "raw_cache_error",
]
LEGACY_CONTEXT_SOURCE_LOG_FIELDS = [
    "provider",
    "category",
    "status",
    "observations",
    "as_of_date",
    "source",
    "source_url",
    "elapsed_ms",
    "notes",
]

NUMERIC_FIELDS = set(RETURN_NUMERIC_FIELDS + RANK_FIELDS) | {
    "sort_order", "observations", "elapsed_ms", "valid_count", "positive_count",
    "flat_count", "negative_count", "up_count", "down_count", "breadth_ratio",
    "leader_laggard_spread", "dispersion", "median_return", "median_change",
    "change_range", "value",
}
DATE_FIELDS = set(RETURN_DATE_FIELDS) | {"as_of_date", "event_date", "report_date"}


def write_csv(path: Path, fields: list[str] | tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fixture_row(fields, **overrides) -> dict:
    row = {}
    for field in fields:
        if field in DATE_FIELDS:
            row[field] = "2026-08-07"
        elif field == "requiredness":
            row[field] = "required"
        elif field in {"freshness_days", "latest_known_as_of"}:
            row[field] = ""
        elif field in NUMERIC_FIELDS:
            row[field] = "1"
        elif field == "source_url":
            row[field] = "https://example.test/source"
        elif field in {"qc_flag", "status"}:
            row[field] = "OK"
        else:
            row[field] = "fixture"
    row.update(overrides)
    return row


def economic_release_row(**overrides) -> dict:
    row = fixture_row(
        CATEGORY_FIELDS["economic_releases"],
        release_at_bjt="2026-08-07T20:30:00+08:00",
        as_of_date="2026-08-09",
        known_as_of="2026-08-07T08:30:00-04:00",
        value="1",
        previous_value="",
        revised_previous="",
        consensus_value="",
        surprise_value="",
    )
    row.update(overrides)
    return row


def write_valid_pipeline_output(pipeline: str, output: Path) -> None:
    history_files = {
        "equity_indices": (
            "02_equity_indices.csv", INDEX_FIELDS,
            fixture_row(INDEX_FIELDS, ticker="INDEX"),
            INDEX_SOURCE_LOG_FIELDS,
            fixture_row(INDEX_SOURCE_LOG_FIELDS, ticker="INDEX"),
        ),
        "equity_sectors": (
            "03_equity_sectors.csv", SECTOR_FIELDS,
            fixture_row(SECTOR_FIELDS, sector_code="SECTOR"),
            SECTOR_SOURCE_LOG_FIELDS,
            fixture_row(SECTOR_SOURCE_LOG_FIELDS, sector_code="SECTOR"),
        ),
        "gics_sectors": (
            "03_gics_sectors.csv", GICS_FIELDS,
            fixture_row(GICS_FIELDS, gics_sector_code="GICS"),
            GICS_SOURCE_LOG_FIELDS,
            fixture_row(GICS_SOURCE_LOG_FIELDS, gics_sector_code="GICS"),
        ),
    }
    if pipeline in history_files:
        filename, fields, row, log_fields, log_row = history_files[pipeline]
        write_csv(output / filename, fields, [row])
        write_csv(output / "source_log.csv", log_fields, [log_row])
        snapshot_name = {
            "equity_indices": "equity_indices_snapshot.json",
            "equity_sectors": "equity_sectors_snapshot.json",
            "gics_sectors": "gics_sectors_snapshot.json",
        }[pipeline]
        (output / snapshot_name).write_text("{}", encoding="utf-8")

    if pipeline == "equity_sectors":
        write_csv(
            output / "sector_divergence.csv",
            SECTOR_DIVERGENCE_FIELDS,
            [fixture_row(SECTOR_DIVERGENCE_FIELDS, market="US", horizon="weekly")],
        )

    if pipeline == "macro_assets":
        for filename in (
            "fixed_income.csv",
            "commodities.csv",
            "foreign_exchange.csv",
            "policy_rates.csv",
            "money_market.csv",
        ):
            write_csv(
                output / filename,
                MACRO_FIELDS,
                [fixture_row(MACRO_FIELDS, series_code=filename)],
            )
        write_csv(
            output / "macro_divergence.csv",
            MACRO_DIVERGENCE_FIELDS,
            [fixture_row(MACRO_DIVERGENCE_FIELDS, asset_class="fixed_income")],
        )
        write_csv(
            output / "source_log.csv",
            MACRO_SOURCE_LOG_FIELDS,
            [fixture_row(MACRO_SOURCE_LOG_FIELDS, series_code="MACRO")],
        )
        (output / "macro_assets_snapshot.json").write_text("{}", encoding="utf-8")

    if pipeline == "weekly_context":
        for category, fields in CATEGORY_FIELDS.items():
            rows = []
            if category == "source_log":
                rows = [
                    {
                        "provider": "fixture",
                        "source_tier": "public",
                        "requiredness": "required",
                        "provider_version": "fixture-v1",
                        "schema_version": "fixture-v1",
                        "frequency": "daily",
                        "freshness_days": "",
                        "latest_known_as_of": "",
                        "warnings": "",
                        "category": "market_internals",
                        "status": "OK",
                        "observations": "0",
                        "as_of_date": "2026-08-09",
                        "source": "Fixture",
                        "source_url": "https://example.test/context",
                        "elapsed_ms": "1",
                        "notes": "",
                    }
                ]
            write_csv(output / f"{category}.csv", fields, rows)
        (output / "weekly_context_snapshot.json").write_text("{}", encoding="utf-8")


def write_valid_staged_week(root: Path, window) -> dict[str, Path]:
    directories = {
        spec.name: Path(spec.output_dir)
        for spec in build_pipeline_specs(root, window)
    }
    for pipeline, output in directories.items():
        write_valid_pipeline_output(pipeline, output)
    return directories


def write_metal_core_coverage(outputs: dict[str, Path], metals: tuple[str, ...]) -> None:
    identities = {
        "copper": ("COPPER_COMEX", "COPPER_PRICE"),
        "gold": ("GOLD_COMEX", "COMEX_GOLD"),
    }
    prices = []
    positioning = []
    for family in metals:
        commodity_code, series_code = identities[family]
        prices.append(
            fixture_row(
                MACRO_FIELDS,
                asset_class="commodity",
                series_code=series_code,
                provider="world_bank_pink_sheet",
                source="World Bank Pink Sheet",
                source_url="https://thedocs.worldbank.org/commodity-prices.xlsx",
                commodity_code=commodity_code,
                commodity_family=family,
                price_kind="official_monthly_benchmark",
                known_as_of="",
            )
        )
        positioning.append(
            fixture_row(
                CATEGORY_FIELDS["positioning_flows"],
                as_of_date="2026-08-04",
                category="positioning_flows",
                commodity_code=commodity_code,
                commodity_family=family,
                metric_role="positioning",
                measurement_kind="open_interest",
                participant_class="",
                known_as_of="2026-08-07T15:30:00-04:00",
                reference_period="2026-08-04",
                source="U.S. Commodity Futures Trading Commission",
                source_url="https://publicreporting.cftc.gov/resource/72hh-3qpy.csv",
            )
        )
    write_csv(outputs["macro_assets"] / "commodities.csv", MACRO_FIELDS, prices)
    write_csv(
        outputs["weekly_context"] / "positioning_flows.csv",
        CATEGORY_FIELDS["positioning_flows"],
        positioning,
    )


class WeekWindowTests(unittest.TestCase):
    def test_tuesday_targets_the_previous_finished_sunday(self):
        now = datetime(2026, 8, 11, 10, 0, tzinfo=ZoneInfo("Asia/Hong_Kong"))

        window = latest_finished_week(now)

        self.assertEqual(window.start, date(2026, 8, 3))
        self.assertEqual(window.end, date(2026, 8, 9))
        self.assertEqual(window.week_id, "week_20260803-20260809")

    def test_sunday_targets_the_prior_week(self):
        now = datetime(2026, 8, 9, 12, 0, tzinfo=ZoneInfo("Asia/Hong_Kong"))

        self.assertEqual(latest_finished_week(now).end, date(2026, 8, 2))

    def test_pipeline_commands_use_the_finished_window_and_staged_outputs(self):
        window = latest_finished_week(
            datetime(2026, 8, 11, 10, 0, tzinfo=ZoneInfo("Asia/Hong_Kong"))
        )
        with TemporaryDirectory() as directory:
            staging_week = Path(directory) / window.week_id

            specs = build_pipeline_specs(staging_week, window)

            self.assertEqual(
                [spec.name for spec in specs],
                [
                    "equity_indices",
                    "equity_sectors",
                    "gics_sectors",
                    "macro_assets",
                    "weekly_context",
                ],
            )
            for spec in specs[:4]:
                self.assertIn("--as-of-date", spec.command)
                self.assertEqual(
                    spec.command[spec.command.index("--as-of-date") + 1],
                    "2026-08-09",
                )
            context = specs[4]
            self.assertEqual(
                context.command[context.command.index("--start-date") + 1],
                "2026-08-03",
            )
            self.assertEqual(
                context.command[context.command.index("--end-date") + 1],
                "2026-08-09",
            )
            for spec in specs:
                output = Path(spec.output_dir)
                self.assertEqual(output.parent, staging_week)
                self.assertTrue(output.name.endswith("20260809"))
                self.assertEqual(
                    spec.command[spec.command.index("--output-dir") + 1],
                    spec.output_dir,
                )


class SafeErrorReasonTests(unittest.TestCase):
    def test_unquoted_absolute_path_keeps_only_the_basename(self):
        error = RuntimeError("cannot read /Users/alice/private/token.txt")

        self.assertEqual(
            weekly_release_module.safe_error_reason(error),
            "cannot read token.txt",
        )

    def test_parenthesized_absolute_path_keeps_surrounding_punctuation(self):
        error = RuntimeError("cannot read (/Users/alice/private/token.txt), retry")

        self.assertEqual(
            weekly_release_module.safe_error_reason(error),
            "cannot read (token.txt), retry",
        )

    def test_unquoted_absolute_path_with_spaces_keeps_only_the_basename(self):
        error = RuntimeError(
            "cannot read /Users/alice/market data/private/token.txt"
        )

        self.assertEqual(
            weekly_release_module.safe_error_reason(error),
            "cannot read token.txt",
        )

    def test_http_url_is_not_mistaken_for_an_absolute_file_path(self):
        error = RuntimeError("source https://example.test/path failed")

        self.assertEqual(
            weekly_release_module.safe_error_reason(error),
            "source https://example.test/path failed",
        )


class StagedValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "week_20260803-20260809"
        self.window = latest_finished_week(
            datetime(2026, 8, 11, 10, 0, tzinfo=ZoneInfo("Asia/Hong_Kong"))
        )
        self.outputs = write_valid_staged_week(self.root, self.window)

    def test_rejects_a_missing_required_file(self):
        missing = self.outputs["equity_indices"] / "02_equity_indices.csv"
        missing.unlink()

        with self.assertRaisesRegex(ReleaseValidationError, "02_equity_indices.csv"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_required_table_with_only_a_header(self):
        path = self.outputs["macro_assets"] / "fixed_income.csv"
        write_csv(path, MACRO_FIELDS, [])

        with self.assertRaisesRegex(ReleaseValidationError, "fixed_income.csv.*empty"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_missing_required_column(self):
        path = self.outputs["gics_sectors"] / "03_gics_sectors.csv"
        fields = [field for field in GICS_FIELDS if field != "source_url"]
        write_csv(path, fields, [fixture_row(fields, gics_sector_code="GICS")])

        with self.assertRaisesRegex(ReleaseValidationError, "source_url"):
            validate_staged_week(self.root, self.window)

    def test_rejects_any_published_csv_without_a_header(self):
        path = self.outputs["weekly_context"] / "unregistered_optional.csv"
        path.write_text("\n", encoding="utf-8")

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "unregistered_optional.csv.*standard header",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_symlinked_published_file(self):
        target = self.root.parent / "outside.csv"
        target.write_text("value\n1\n", encoding="utf-8")
        published = self.outputs["weekly_context"] / "events.csv"
        published.unlink()
        published.symlink_to(target)

        with self.assertRaisesRegex(ReleaseValidationError, "symbolic link"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_duplicate_csv_header(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        fields = [*INDEX_FIELDS, "ticker"]
        write_csv(path, fields, [fixture_row(fields, ticker="INDEX")])

        with self.assertRaisesRegex(ReleaseValidationError, "duplicate.*ticker"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_ragged_csv_row(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        content = path.read_text(encoding="utf-8").rstrip("\n")
        path.write_text(f"{content},unexpected\n", encoding="utf-8")

        with self.assertRaisesRegex(ReleaseValidationError, "column count"):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_unterminated_quoted_csv_field(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        content = path.read_text(encoding="utf-8").rstrip("\n")
        path.write_text(f'{content},"unterminated\n', encoding="utf-8")

        with self.assertRaisesRegex(ReleaseValidationError, "malformed CSV"):
            validate_staged_week(self.root, self.window)

    def test_rejects_fetch_failed_in_a_source_log(self):
        path = self.outputs["equity_sectors"] / "source_log.csv"
        row = fixture_row(
            SECTOR_SOURCE_LOG_FIELDS,
            sector_code="SECTOR",
            status="FETCH_FAILED",
        )
        write_csv(path, SECTOR_SOURCE_LOG_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "FETCH_FAILED"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_visible_record_after_the_target_sunday(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        row = fixture_row(INDEX_FIELDS, ticker="INDEX", latest_date="2026-08-10")
        write_csv(path, INDEX_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "2026-08-10.*2026-08-09"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_visible_record_without_a_source_url(self):
        path = self.outputs["macro_assets"] / "commodities.csv"
        row = fixture_row(MACRO_FIELDS, series_code="COMMODITY", source_url="")
        write_csv(path, MACRO_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "source_url"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_commodity_research_row_without_a_commodity_code(self):
        path = self.outputs["macro_assets"] / "commodities.csv"
        row = fixture_row(
            MACRO_FIELDS,
            asset_class="commodity",
            series_code="WTI",
            commodity_code="",
            commodity_family="refined_products",
        )
        write_csv(path, MACRO_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "commodity_code"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_commodity_research_row_with_an_unsupported_family(self):
        path = self.outputs["macro_assets"] / "commodities.csv"
        row = fixture_row(
            MACRO_FIELDS,
            asset_class="commodity",
            series_code="WTI",
            commodity_code="WTI",
            commodity_family="unknown_family",
        )
        write_csv(path, MACRO_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "commodity_family"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_non_finite_numeric_value(self):
        path = self.outputs["gics_sectors"] / "03_gics_sectors.csv"
        row = fixture_row(GICS_FIELDS, gics_sector_code="GICS", latest_value="NaN")
        write_csv(path, GICS_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "latest_value.*finite"):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_economic_release_known_after_target_sunday(self):
        path = self.outputs["weekly_context"] / "economic_releases.csv"
        write_csv(
            path,
            CATEGORY_FIELDS["economic_releases"],
            [economic_release_row(known_as_of="2026-08-10T00:00:00+08:00")],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "known_as_of.*2026-08-09",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_economic_release_without_a_known_timestamp(self):
        path = self.outputs["weekly_context"] / "economic_releases.csv"
        write_csv(
            path,
            CATEGORY_FIELDS["economic_releases"],
            [economic_release_row(known_as_of="")],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "known_as_of.*UTC offset",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_economic_release_timestamp_without_a_utc_offset(self):
        path = self.outputs["weekly_context"] / "economic_releases.csv"
        write_csv(
            path,
            CATEGORY_FIELDS["economic_releases"],
            [economic_release_row(release_at_bjt="2026-08-07T20:30:00")],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "release_at_bjt.*UTC offset",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_economic_release_published_after_target_sunday(self):
        path = self.outputs["weekly_context"] / "economic_releases.csv"
        write_csv(
            path,
            CATEGORY_FIELDS["economic_releases"],
            [economic_release_row(release_at_bjt="2026-08-10T00:00:00+08:00")],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "release_at_bjt.*2026-08-09",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_non_finite_optional_economic_release_value(self):
        path = self.outputs["weekly_context"] / "economic_releases.csv"
        write_csv(
            path,
            CATEGORY_FIELDS["economic_releases"],
            [economic_release_row(previous_value="NaN")],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "previous_value.*finite",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_frontend_required_identity_column(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        fields = [field for field in INDEX_FIELDS if field != "region"]
        write_csv(path, fields, [fixture_row(fields, ticker="INDEX")])

        with self.assertRaisesRegex(ReleaseValidationError, "region"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_frontend_required_source_log_column(self):
        path = self.outputs["gics_sectors"] / "source_log.csv"
        fields = [field for field in GICS_SOURCE_LOG_FIELDS if field != "observations"]
        write_csv(path, fields, [fixture_row(fields, gics_sector_code="GICS")])

        with self.assertRaisesRegex(ReleaseValidationError, "observations"):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_extra_current_context_source_log_column(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        fields = [*CATEGORY_FIELDS["source_log"], "unexpected"]
        write_csv(path, fields, [fixture_row(fields, unexpected="extra")])

        with self.assertRaisesRegex(ReleaseValidationError, "unexpected columns"):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_extra_legacy_context_source_log_column(self):
        (self.outputs["weekly_context"] / "economic_releases.csv").unlink()
        path = self.outputs["weekly_context"] / "source_log.csv"
        fields = [*LEGACY_CONTEXT_SOURCE_LOG_FIELDS, "unexpected"]
        write_csv(path, fields, [fixture_row(fields, unexpected="extra")])

        with self.assertRaisesRegex(ReleaseValidationError, "unexpected columns"):
            validate_staged_week(
                self.root,
                self.window,
                dataset_contract_version=1,
            )

    def test_allows_blank_optional_change_beside_a_valid_core_value(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        row = fixture_row(INDEX_FIELDS, ticker="INDEX", weekly_change="")
        write_csv(path, INDEX_FIELDS, [row])

        validate_staged_week(self.root, self.window)

    def test_allows_blank_optional_base_rank_and_source_log_numeric_cells(self):
        data_path = self.outputs["equity_sectors"] / "03_equity_sectors.csv"
        data_row = fixture_row(
            SECTOR_FIELDS,
            sector_code="SECTOR",
            daily_base_value="",
            weekly_rank="",
        )
        write_csv(data_path, SECTOR_FIELDS, [data_row])
        source_path = self.outputs["equity_sectors"] / "source_log.csv"
        source_row = fixture_row(
            SECTOR_SOURCE_LOG_FIELDS,
            sector_code="SECTOR",
            weekly_base_value="",
        )
        write_csv(source_path, SECTOR_SOURCE_LOG_FIELDS, [source_row])

        validate_staged_week(self.root, self.window)

    def test_allows_insufficient_summary_rows_when_core_data_is_valid(self):
        path = self.outputs["equity_sectors"] / "sector_divergence.csv"
        row = fixture_row(
            SECTOR_DIVERGENCE_FIELDS,
            market="US",
            qc_flag="INSUFFICIENT_DATA",
            valid_count="0",
            breadth_ratio="",
            leader_laggard_spread="",
            dispersion="",
            median_return="",
        )
        write_csv(path, SECTOR_DIVERGENCE_FIELDS, [row])

        validate_staged_week(self.root, self.window)

    def test_rejects_a_core_table_without_any_valid_row(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        row = fixture_row(
            INDEX_FIELDS,
            ticker="INDEX",
            latest_date="",
            latest_value="",
            qc_flag="INSUFFICIENT_DATA",
        )
        write_csv(path, INDEX_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "valid row"):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_unknown_or_unapproved_optional_source_status(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fixture",
            status="MYSTERY",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(ReleaseValidationError, "MYSTERY"):
            validate_staged_week(self.root, self.window)

        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="unregistered_optional_provider",
            category="company_events",
            status="NOT_CONFIGURED",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(ReleaseValidationError, "NOT_CONFIGURED"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_blank_source_status(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fixture",
            status="",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(ReleaseValidationError, "blank"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_source_log_without_an_http_source_url(self):
        path = self.outputs["equity_indices"] / "source_log.csv"
        row = fixture_row(
            INDEX_SOURCE_LOG_FIELDS,
            ticker="INDEX",
            source_url="",
        )
        write_csv(path, INDEX_SOURCE_LOG_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, r"HTTP\(S\)"):
            validate_staged_week(self.root, self.window)

    def test_accepts_not_configured_from_an_optional_context_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        rows = [
            fixture_row(
                CATEGORY_FIELDS["source_log"],
                provider=provider,
                category="commodity_fundamentals",
                requiredness="optional",
                status="NOT_CONFIGURED",
                observations="0",
                as_of_date="2026-08-09",
                source_url="https://www.eia.gov/opendata/",
            )
            for provider in ("eia_natural_gas", "eia_refined_products")
        ]
        write_csv(path, CATEGORY_FIELDS["source_log"], rows)

        validate_staged_week(self.root, self.window)

    def test_active_eia_families_each_require_a_physical_fundamental_row(self):
        source_log = self.outputs["weekly_context"] / "source_log.csv"
        provider_rows = [
            fixture_row(
                CATEGORY_FIELDS["source_log"],
                provider=provider,
                category="commodity_fundamentals",
                requiredness="required",
                status="OK",
                observations="1",
                as_of_date="2026-08-09",
                source="U.S. Energy Information Administration",
                source_url="https://api.eia.gov/v2/",
            )
            for provider in ("eia_natural_gas", "eia_refined_products")
        ]
        write_csv(source_log, CATEGORY_FIELDS["source_log"], provider_rows)
        fundamentals = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        natural_row = fixture_row(
            CATEGORY_FIELDS["commodity_fundamentals"],
            as_of_date="2026-08-07",
            commodity_code="NATGAS_HH",
            commodity_family="natural_gas",
            metric_role="fundamental",
            measurement_kind="physical_level",
            participant_class="",
            known_as_of="",
            reference_period="2026-08-07",
            source="U.S. Energy Information Administration",
            source_url="https://api.eia.gov/v2/natural-gas/stor/wkly/data/",
        )
        write_csv(
            fundamentals,
            CATEGORY_FIELDS["commodity_fundamentals"],
            [natural_row],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "eia_refined_products.*physical fundamental",
        ):
            validate_staged_week(self.root, self.window)

    def test_unrelated_same_family_row_cannot_satisfy_active_eia_coverage(self):
        source_log = self.outputs["weekly_context"] / "source_log.csv"
        active = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="eia_natural_gas",
            category="commodity_fundamentals",
            requiredness="required",
            status="OK",
            observations="1",
            as_of_date="2026-08-09",
            source="U.S. Energy Information Administration",
            source_url="https://api.eia.gov/v2/",
        )
        write_csv(source_log, CATEGORY_FIELDS["source_log"], [active])
        fundamentals = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        unrelated = fixture_row(
            CATEGORY_FIELDS["commodity_fundamentals"],
            as_of_date="2026-08-07",
            commodity_code="NATGAS_HH",
            commodity_family="natural_gas",
            metric_role="fundamental",
            measurement_kind="physical_level",
            participant_class="",
            known_as_of="",
            reference_period="2026-08-07",
            source="Unrelated natural gas source",
            source_url="https://example.test/natural-gas",
        )
        write_csv(
            fundamentals,
            CATEGORY_FIELDS["commodity_fundamentals"],
            [unrelated],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "eia_natural_gas.*official EIA physical fundamental",
        ):
            validate_staged_week(self.root, self.window)

    def test_accepts_insufficient_data_from_an_optional_context_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fred_financial_conditions",
            category="financial_conditions",
            requiredness="optional",
            status="INSUFFICIENT_DATA",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        validate_staged_week(self.root, self.window)

    def test_accepts_point_in_time_unavailable_from_registered_optional_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="sec_company_events",
            category="company_events",
            requiredness="optional",
            status="POINT_IN_TIME_UNAVAILABLE",
            observations="0",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        validate_staged_week(self.root, self.window)

    def test_rejects_point_in_time_unavailable_from_same_allowlisted_required_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="sec_company_events",
            category="company_events",
            requiredness="required",
            status="POINT_IN_TIME_UNAVAILABLE",
            observations="0",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "POINT_IN_TIME_UNAVAILABLE",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_unknown_current_context_requiredness(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fixture",
            category="market_internals",
            requiredness="best-effort",
            status="OK",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(ReleaseValidationError, "requiredness"):
            validate_staged_week(self.root, self.window)

    def test_rejects_current_context_latest_known_as_of_after_target_sunday(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fixture",
            category="market_internals",
            latest_known_as_of="2026-08-10T00:00:00+08:00",
            status="OK",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "latest_known_as_of.*exceeds",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_invalid_current_context_latest_known_as_of(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        for latest_known_as_of in (
            "not-a-timestamp",
            "2026-08-09T12:00:00",
        ):
            with self.subTest(latest_known_as_of=latest_known_as_of):
                row = fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider="fixture",
                    category="market_internals",
                    latest_known_as_of=latest_known_as_of,
                    status="OK",
                    as_of_date="2026-08-09",
                )
                write_csv(path, CATEGORY_FIELDS["source_log"], [row])

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    "latest_known_as_of.*UTC offset",
                ):
                    validate_staged_week(self.root, self.window)

    def test_rejects_non_finite_or_non_numeric_current_context_freshness_days(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        for freshness_days in ("NaN", "Infinity", "not-a-number"):
            with self.subTest(freshness_days=freshness_days):
                row = fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider="fixture",
                    category="market_internals",
                    freshness_days=freshness_days,
                    status="OK",
                    as_of_date="2026-08-09",
                )
                write_csv(path, CATEGORY_FIELDS["source_log"], [row])

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    "freshness_days.*finite",
                ):
                    validate_staged_week(self.root, self.window)

    def test_accepts_blank_current_context_freshness_and_latest_known_as_of(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fixture",
            category="market_internals",
            freshness_days="",
            latest_known_as_of="",
            status="OK",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        validate_staged_week(self.root, self.window)

    def test_accepts_finite_freshness_and_eligible_latest_known_as_of(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fixture",
            category="market_internals",
            freshness_days="7",
            latest_known_as_of="2026-08-09T23:59:59+08:00",
            status="OK",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        validate_staged_week(self.root, self.window)

    def test_rejects_point_in_time_unavailable_from_a_required_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="bls_economic_releases",
            category="economic_releases",
            requiredness="required",
            status="POINT_IN_TIME_UNAVAILABLE",
            observations="0",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "POINT_IN_TIME_UNAVAILABLE",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_fetch_failed_from_a_registered_optional_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        for provider, category in (
            ("sec_company_events", "company_events"),
            ("fred_financial_conditions", "financial_conditions"),
        ):
            with self.subTest(provider=provider):
                row = fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider=provider,
                    category=category,
                    requiredness="optional",
                    status="FETCH_FAILED",
                    observations="0",
                    as_of_date="2026-08-09",
                )
                write_csv(path, CATEGORY_FIELDS["source_log"], [row])

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    "FETCH_FAILED",
                ):
                    validate_staged_week(self.root, self.window)

    def test_accepts_fetch_failed_from_optional_yahoo_volatility_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="yahoo_volatility_signals",
            category="financial_conditions",
            requiredness="optional",
            status="FETCH_FAILED",
            observations="0",
            as_of_date="2026-08-09",
            source="Yahoo Finance (Cboe indices)",
            source_url="https://finance.yahoo.com/",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        validate_staged_week(self.root, self.window)

    def test_accepts_metal_supplemental_failures_without_weakening_core_coverage(self):
        write_metal_core_coverage(self.outputs, ("copper", "gold"))
        path = self.outputs["weekly_context"] / "source_log.csv"
        providers = (
            ("comex_copper_stocks", "https://www.cmegroup.com/delivery_reports/Copper_Stocks.xls"),
            ("comex_gold_stocks", "https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls"),
            ("usgs_copper_structural", "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-copper.pdf"),
            ("usgs_gold_structural", "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-gold.pdf"),
        )
        rows = [
            fixture_row(
                CATEGORY_FIELDS["source_log"],
                provider=provider,
                category="commodity_fundamentals",
                requiredness="optional",
                status="FETCH_FAILED",
                observations="0",
                as_of_date="2026-08-09",
                source_url=url,
            )
            for provider, url in providers
        ]
        write_csv(path, CATEGORY_FIELDS["source_log"], rows)

        validate_staged_week(self.root, self.window)

    def test_metal_supplemental_failure_cannot_replace_world_bank_price_or_cftc(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="comex_copper_stocks",
            category="commodity_fundamentals",
            requiredness="optional",
            status="FETCH_FAILED",
            observations="0",
            as_of_date="2026-08-09",
            source_url="https://www.cmegroup.com/delivery_reports/Copper_Stocks.xls",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "copper.*World Bank price",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_fetch_failed_from_required_yahoo_volatility_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="yahoo_volatility_signals",
            category="financial_conditions",
            requiredness="required",
            status="FETCH_FAILED",
            observations="0",
            as_of_date="2026-08-09",
            source="Yahoo Finance (Cboe indices)",
            source_url="https://finance.yahoo.com/",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(ReleaseValidationError, "FETCH_FAILED"):
            validate_staged_week(self.root, self.window)

    def test_calculated_curve_requires_both_http_sourced_dependencies(self):
        path = self.outputs["macro_assets"] / "fixed_income.csv"
        calculated_reference = (
            "calculated:UST10Y-UST2Y (shared Treasury observation dates)"
        )
        rows = [
            fixture_row(MACRO_FIELDS, series_code="UST10Y"),
            fixture_row(
                MACRO_FIELDS,
                series_code="UST10Y2Y",
                provider="calculated",
                source_url=calculated_reference,
            ),
        ]
        write_csv(path, MACRO_FIELDS, rows)

        with self.assertRaisesRegex(ReleaseValidationError, "UST2Y"):
            validate_staged_week(self.root, self.window)

    def test_accepts_every_registered_treasury_calculation(self):
        path = self.outputs["macro_assets"] / "fixed_income.csv"
        rows = [
            fixture_row(MACRO_FIELDS, series_code=code)
            for code in (
                "UST2Y",
                "UST5Y",
                "UST10Y",
                "UST_REAL5Y",
                "UST_REAL10Y",
            )
        ]
        rows.extend(
            [
                fixture_row(
                    MACRO_FIELDS,
                    series_code="UST10Y2Y",
                    provider="calculated",
                    source_url=(
                        "calculated:UST10Y-UST2Y "
                        "(shared Treasury observation dates)"
                    ),
                ),
                fixture_row(
                    MACRO_FIELDS,
                    series_code="US_BE5Y",
                    provider="calculated",
                    source_url=(
                        "calculated:UST5Y-UST_REAL5Y "
                        "(shared Treasury observation dates)"
                    ),
                ),
                fixture_row(
                    MACRO_FIELDS,
                    series_code="US_BE10Y",
                    provider="calculated",
                    source_url=(
                        "calculated:UST10Y-UST_REAL10Y "
                        "(shared Treasury observation dates)"
                    ),
                ),
                fixture_row(
                    MACRO_FIELDS,
                    series_code="US_5Y5Y",
                    provider="calculated",
                    source_url=(
                        "calculated:5Y5Y from US_BE5Y and US_BE10Y "
                        "(shared Treasury observation dates)"
                    ),
                ),
            ]
        )
        write_csv(path, MACRO_FIELDS, rows)

        manifest = validate_staged_week(self.root, self.window)

        entry = next(
            item
            for item in manifest["files"]
            if item["path"].endswith("fixed_income.csv")
        )
        self.assertEqual(entry["rows"], len(rows))

    def test_each_new_treasury_calculation_requires_its_dependency(self):
        path = self.outputs["macro_assets"] / "fixed_income.csv"
        observed_rows = [
            fixture_row(MACRO_FIELDS, series_code=code)
            for code in (
                "UST2Y",
                "UST5Y",
                "UST10Y",
                "UST_REAL5Y",
                "UST_REAL10Y",
            )
        ]
        calculated_rows = [
            fixture_row(
                MACRO_FIELDS,
                series_code="UST10Y2Y",
                provider="calculated",
                source_url=(
                    "calculated:UST10Y-UST2Y "
                    "(shared Treasury observation dates)"
                ),
            ),
            fixture_row(
                MACRO_FIELDS,
                series_code="US_BE5Y",
                provider="calculated",
                source_url=(
                    "calculated:UST5Y-UST_REAL5Y "
                    "(shared Treasury observation dates)"
                ),
            ),
            fixture_row(
                MACRO_FIELDS,
                series_code="US_BE10Y",
                provider="calculated",
                source_url=(
                    "calculated:UST10Y-UST_REAL10Y "
                    "(shared Treasury observation dates)"
                ),
            ),
            fixture_row(
                MACRO_FIELDS,
                series_code="US_5Y5Y",
                provider="calculated",
                source_url=(
                    "calculated:5Y5Y from US_BE5Y and US_BE10Y "
                    "(shared Treasury observation dates)"
                ),
            ),
        ]
        cases = (
            ("US_BE5Y", "UST_REAL5Y"),
            ("US_BE10Y", "UST_REAL10Y"),
            ("US_5Y5Y", "US_BE10Y"),
        )

        for series_code, missing_dependency in cases:
            with self.subTest(series_code=series_code):
                rows = [
                    row
                    for row in observed_rows + calculated_rows
                    if row["series_code"] != missing_dependency
                ]
                write_csv(path, MACRO_FIELDS, rows)

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    missing_dependency,
                ):
                    validate_staged_week(self.root, self.window)

    def test_rejects_a_non_http_source_reference(self):
        path = self.outputs["gics_sectors"] / "03_gics_sectors.csv"
        row = fixture_row(
            GICS_FIELDS,
            gics_sector_code="GICS",
            source_url="not-a-url",
        )
        write_csv(path, GICS_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "HTTP\(S\)"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_non_canonical_date(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        row = fixture_row(INDEX_FIELDS, ticker="INDEX", latest_date="2026-8-7")
        write_csv(path, INDEX_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "YYYY-MM-DD"):
            validate_staged_week(self.root, self.window)

    def test_accepts_standard_header_zero_row_optional_context_tables(self):
        manifest = validate_staged_week(self.root, self.window)

        context_files = {
            item["path"]: item["rows"]
            for item in manifest["files"]
            if "capital_weekly_context_20260809" in item["path"]
        }
        self.assertEqual(context_files["capital_weekly_context_20260809/events.csv"], 0)
        self.assertEqual(
            context_files[
                "capital_weekly_context_20260809/commodity_fundamentals.csv"
            ],
            0,
        )
        json.dumps(manifest, allow_nan=False)

    def test_manifest_records_complete_week_identity_and_exact_file_integrity(self):
        raw_file = self.outputs["equity_indices"] / "raw" / "fixture.txt"
        raw_file.parent.mkdir()
        raw_file.write_text("raw fixture", encoding="utf-8")
        nested_manifest = raw_file.with_name("manifest.json")
        nested_manifest.write_text('{"kind": "provider"}', encoding="utf-8")

        manifest = validate_staged_week(self.root, self.window)

        self.assertEqual(manifest["manifest_schema_version"], 2)
        self.assertEqual(manifest["dataset_contract_version"], 2)
        self.assertEqual(manifest["publication_mode"], "coordinated")
        self.assertEqual(manifest["week_start"], "2026-08-03")
        self.assertEqual(manifest["week_end"], "2026-08-09")
        self.assertEqual(manifest["timezone"], "Asia/Hong_Kong")
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(manifest["failures"], [])
        self.assertTrue(manifest["coordinator_version"])
        self.assertEqual(len(manifest["pipelines"]), 5)
        for pipeline in manifest["pipelines"]:
            self.assertEqual(
                set(pipeline),
                {
                    "name",
                    "status",
                    "started_at",
                    "finished_at",
                    "elapsed_ms",
                },
            )
            self.assertEqual(pipeline["status"], "validated")
            self.assertIsNone(pipeline["started_at"])
            self.assertIsNone(pipeline["finished_at"])
            self.assertIsNone(pipeline["elapsed_ms"])
        index_path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        index_entry = next(
            item
            for item in manifest["files"]
            if item["path"].endswith("/02_equity_indices.csv")
        )
        self.assertEqual(index_entry["rows"], 1)
        self.assertEqual(
            index_entry["sha256"],
            hashlib.sha256(index_path.read_bytes()).hexdigest(),
        )
        raw_entry = next(
            item for item in manifest["files"] if item["path"].endswith("raw/fixture.txt")
        )
        self.assertIsNone(raw_entry["rows"])
        nested_manifest_path = (
            "capital_weekly_equity_indices_python_20260809/raw/manifest.json"
        )
        entries_by_path = {item["path"]: item for item in manifest["files"]}
        self.assertIn(nested_manifest_path, entries_by_path)
        nested_manifest_entry = entries_by_path[nested_manifest_path]
        self.assertIsNone(nested_manifest_entry["rows"])
        snapshot_entry = next(
            item
            for item in manifest["files"]
            if item["path"].endswith("equity_indices_snapshot.json")
        )
        self.assertIsNone(snapshot_entry["rows"])

    def test_manifest_row_counts_ignore_blank_csv_records(self):
        events = self.outputs["weekly_context"] / "events.csv"
        events.write_text(
            events.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )

        manifest = validate_staged_week(self.root, self.window)

        events_entry = next(
            item
            for item in manifest["files"]
            if item["path"].endswith("/events.csv")
        )
        self.assertEqual(events_entry["rows"], 0)

    def test_current_contract_rejects_a_missing_economic_releases_table(self):
        (self.outputs["weekly_context"] / "economic_releases.csv").unlink()

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "economic_releases.csv",
        ):
            validate_staged_week(self.root, self.window)

    def test_legacy_contract_rejects_current_economic_releases_table(self):
        with self.assertRaisesRegex(
            ReleaseValidationError,
            "economic_releases.csv.*legacy dataset contract",
        ):
            validate_staged_week(
                self.root,
                self.window,
                dataset_contract_version=1,
            )

    def test_legacy_contract_infers_optional_status_from_identity(self):
        context = self.outputs["weekly_context"]
        (context / "economic_releases.csv").unlink()
        write_csv(
            context / "source_log.csv",
            LEGACY_CONTEXT_SOURCE_LOG_FIELDS,
            [
                fixture_row(
                    LEGACY_CONTEXT_SOURCE_LOG_FIELDS,
                    provider="sec_company_events",
                    category="company_events",
                    status="POINT_IN_TIME_UNAVAILABLE",
                    observations="0",
                    as_of_date="2026-08-09",
                )
            ],
        )

        validate_staged_week(
            self.root,
            self.window,
            dataset_contract_version=1,
        )

    def test_legacy_contract_rejects_expanded_context_source_log(self):
        (self.outputs["weekly_context"] / "economic_releases.csv").unlink()

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "source_log.csv.*legacy dataset contract",
        ):
            validate_staged_week(
                self.root,
                self.window,
                dataset_contract_version=1,
            )


class FakePipelineRunner:
    PIPELINES = {
        "pipeline.indices": "equity_indices",
        "pipeline.sectors": "equity_sectors",
        "pipeline.gics": "gics_sectors",
        "pipeline.macro": "macro_assets",
        "pipeline.context": "weekly_context",
    }

    def __init__(self, fail_pipeline: str | None = None, generation: str = "current"):
        self.fail_pipeline = fail_pipeline
        self.generation = generation
        self.calls = []

    def __call__(self, command, *, check, cwd):
        pipeline = self.PIPELINES[command[2]]
        self.calls.append((tuple(command), check, Path(cwd)))
        if pipeline == self.fail_pipeline:
            raise subprocess.CalledProcessError(2, command)
        output = Path(command[command.index("--output-dir") + 1])
        write_valid_pipeline_output(pipeline, output)
        raw = (
            output.parent / f".{output.name}.raw"
            if pipeline == "weekly_context"
            else output / "raw"
        )
        raw.mkdir(parents=True, exist_ok=True)
        (raw / "generation.txt").write_text(self.generation, encoding="utf-8")


def directory_bytes(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


class ReleaseOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project_root = Path(self.temporary.name).resolve()
        self.status_path = self.project_root / "state" / "refresh-status.json"
        self.now = datetime(
            2026, 8, 11, 13, 25, tzinfo=ZoneInfo("Asia/Hong_Kong")
        )

    def test_success_publishes_stable_output_and_atomic_succeeded_status(self):
        runner = FakePipelineRunner()

        published = run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=runner,
        )

        self.assertEqual(
            published,
            self.project_root / "output",
        )
        manifest = json.loads((published / "release.json").read_text())
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["source_week_id"], "week_20260803-20260809")
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(
            {path.name for path in published.iterdir()},
            {
                "indices.json",
                "sectors.json",
                "gics.json",
                "macro.json",
                "context.json",
                "release.json",
            },
        )
        self.assertFalse(any(published.glob("week_*")))
        self.assertEqual(
            [pipeline["name"] for pipeline in manifest["pipelines"]],
            ["indices", "sectors", "gics", "macro", "context"],
        )
        for pipeline in manifest["pipelines"]:
            self.assertEqual(pipeline["status"], "complete")
        json.dumps(manifest, allow_nan=False)
        status = json.loads(self.status_path.read_text())
        self.assertEqual(
            set(status),
            {
                "job_id",
                "status",
                "pid",
                "updated_at",
                "week_id",
                "current_pipeline",
                "completed",
                "total",
                "started_at",
                "finished_at",
                "error",
            },
        )
        self.assertEqual(status["status"], "succeeded")
        self.assertEqual(status["pid"], os.getpid())
        self.assertIsInstance(status["updated_at"], str)
        self.assertEqual(status["completed"], 5)
        self.assertEqual(status["total"], 5)
        self.assertIsNone(status["current_pipeline"])
        self.assertIsNone(status["error"])
        self.assertIsNotNone(status["finished_at"])
        self.assertEqual(len(runner.calls), 5)
        for _command, check, cwd in runner.calls:
            self.assertTrue(check)
            self.assertEqual(cwd, self.project_root)
        self.assertEqual(list(self.status_path.parent.glob(".*.tmp")), [])
        staging_root = self.project_root / "pipeline" / ".staging"
        self.assertFalse(staging_root.exists() and any(staging_root.iterdir()))
        cache = self.project_root / "pipeline" / ".cache"
        self.assertEqual(
            {path.name for path in cache.iterdir()},
            {"indices", "sectors", "gics", "macro", "context", "cache.json"},
        )

    def test_status_uses_execution_clock_not_the_window_override_clock(self):
        runner = FakePipelineRunner()
        real_datetime = datetime

        class FixedExecutionDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                value = real_datetime(2026, 8, 11, 18, 45, tzinfo=tz)
                return cls.fromtimestamp(value.timestamp(), tz)

        with patch(
            "pipeline.internal.capital_weekly.weekly_release.datetime",
            FixedExecutionDateTime,
        ):
            run_latest_release(
                self.project_root,
                now_hkt=self.now,
                status_path=self.status_path,
                runner=runner,
            )

        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["started_at"], "2026-08-11T18:45:00+08:00")
        self.assertTrue(status["job_id"].startswith("20260811T184500-"))

    def test_default_status_file_matches_the_refresh_api_location(self):
        runner = FakePipelineRunner()

        run_latest_release(
            self.project_root,
            now_hkt=self.now,
            runner=runner,
        )

        status_path = self.project_root / "pipeline" / ".state" / "status.json"
        self.assertTrue(status_path.is_file())
        self.assertEqual(json.loads(status_path.read_text())["status"], "succeeded")

    def test_two_successes_replace_the_same_files_and_keep_only_latest_cache(self):
        first = run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="first"),
        )
        first_names = {path.name for path in first.iterdir()}
        first_release_id = json.loads((first / "release.json").read_text())["release_id"]

        second = run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="second"),
        )

        self.assertEqual(first, second)
        self.assertEqual({path.name for path in second.iterdir()}, first_names)
        self.assertNotEqual(
            json.loads((second / "release.json").read_text())["release_id"],
            first_release_id,
        )
        cache = self.project_root / "pipeline" / ".cache"
        for pipeline in ("indices", "sectors", "gics", "macro", "context"):
            self.assertEqual(
                (cache / pipeline / "generation.txt").read_text(),
                "second",
            )
        self.assertNotIn(b"first", b"".join(directory_bytes(cache).values()))

    def test_pipeline_failure_preserves_prior_release_and_names_pipeline(self):
        run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="prior"),
        )
        published = self.project_root / "output"
        cache = self.project_root / "pipeline" / ".cache"
        prior_output = directory_bytes(published)
        prior_cache = directory_bytes(cache)
        runner = FakePipelineRunner(fail_pipeline="equity_sectors")

        with self.assertRaisesRegex(ReleasePipelineError, "equity_sectors"):
            run_latest_release(
                self.project_root,
                now_hkt=self.now,
                status_path=self.status_path,
                runner=runner,
            )

        self.assertEqual(directory_bytes(published), prior_output)
        self.assertEqual(directory_bytes(cache), prior_cache)
        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["status"], "failed")
        self.assertEqual(status["current_pipeline"], "equity_sectors")
        self.assertIn("equity_sectors", status["error"])
        self.assertEqual(status["completed"], 1)
        self.assertEqual(len(runner.calls), 2)
        staging_root = self.project_root / "pipeline" / ".staging"
        self.assertFalse(staging_root.exists() and any(staging_root.iterdir()))

    def test_status_hides_absolute_paths_from_unexpected_errors(self):
        secret_path = self.project_root / "private" / "credentials.txt"

        def fail_with_filesystem_error(*_args, **_kwargs):
            raise OSError(2, "No such file or directory", secret_path)

        with self.assertRaises(OSError):
            run_latest_release(
                self.project_root,
                now_hkt=self.now,
                status_path=self.status_path,
                runner=fail_with_filesystem_error,
            )

        status = json.loads(self.status_path.read_text())
        self.assertIn("credentials.txt", status["error"])
        self.assertNotIn(str(self.project_root), status["error"])

    def test_output_replacement_failure_rolls_output_and_cache_back(self):
        run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="prior"),
        )
        destination = self.project_root / "output"
        cache = self.project_root / "pipeline" / ".cache"
        prior_output = directory_bytes(destination)
        prior_cache = directory_bytes(cache)
        real_replace = os.replace

        def fail_output_swap(source, target):
            if Path(source).name == "output" and Path(target) == destination:
                raise OSError("simulated output swap failure")
            real_replace(source, target)

        with patch(
            "pipeline.internal.capital_weekly.weekly_release.os.replace",
            side_effect=fail_output_swap,
        ):
            with self.assertRaisesRegex(OSError, "simulated output swap failure"):
                run_latest_release(
                    self.project_root,
                    now_hkt=self.now,
                    status_path=self.status_path,
                    runner=FakePipelineRunner(generation="new"),
                )

        self.assertEqual(directory_bytes(destination), prior_output)
        self.assertEqual(directory_bytes(cache), prior_cache)

    def test_cache_replacement_failure_rolls_output_and_cache_back(self):
        run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="prior"),
        )
        destination = self.project_root / "output"
        cache = self.project_root / "pipeline" / ".cache"
        prior_output = directory_bytes(destination)
        prior_cache = directory_bytes(cache)
        real_replace = os.replace

        def fail_cache_swap(source, target):
            if Path(source).name == "cache" and Path(target) == cache:
                raise OSError("simulated cache swap failure")
            real_replace(source, target)

        with patch(
            "pipeline.internal.capital_weekly.weekly_release.os.replace",
            side_effect=fail_cache_swap,
        ):
            with self.assertRaisesRegex(OSError, "simulated cache swap failure"):
                run_latest_release(
                    self.project_root,
                    now_hkt=self.now,
                    status_path=self.status_path,
                    runner=FakePipelineRunner(generation="new"),
                )

        self.assertEqual(directory_bytes(destination), prior_output)
        self.assertEqual(directory_bytes(cache), prior_cache)

    def test_final_status_write_failure_rolls_output_and_cache_back(self):
        run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="prior"),
        )
        destination = self.project_root / "output"
        cache = self.project_root / "pipeline" / ".cache"
        prior_output = directory_bytes(destination)
        prior_cache = directory_bytes(cache)
        real_atomic_write_json = weekly_release_module._atomic_write_json

        def fail_succeeded_status(path, payload):
            if payload.get("status") == "succeeded":
                raise OSError("simulated final status failure")
            return real_atomic_write_json(path, payload)

        with patch(
            "pipeline.internal.capital_weekly.weekly_release._atomic_write_json",
            side_effect=fail_succeeded_status,
        ):
            with self.assertRaisesRegex(OSError, "simulated final status failure"):
                run_latest_release(
                    self.project_root,
                    now_hkt=self.now,
                    status_path=self.status_path,
                    runner=FakePipelineRunner(generation="new"),
                )

        self.assertEqual(directory_bytes(destination), prior_output)
        self.assertEqual(directory_bytes(cache), prior_cache)
        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["status"], "failed")
        self.assertEqual(status["current_pipeline"], "publish")

    def test_held_lock_rejects_a_second_release_without_running_pipelines(self):
        state = self.project_root / "pipeline" / ".state"
        state.mkdir(parents=True)
        lock_path = state / "refresh.lock"
        lock_file = lock_path.open("a+")
        self.addCleanup(lock_file.close)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        runner = FakePipelineRunner()

        with self.assertRaises(ReleaseAlreadyRunning):
            run_latest_release(
                self.project_root,
                now_hkt=self.now,
                status_path=self.status_path,
                runner=runner,
            )

        self.assertEqual(runner.calls, [])
        self.assertFalse(self.status_path.exists())


class CliWrapperTests(unittest.TestCase):
    @staticmethod
    def load_cli_module():
        return importlib.import_module("pipeline.refresh")

    def test_as_of_override_ends_on_supplied_sunday_and_prints_release(self):
        module = self.load_cli_module()
        calls = []

        def release_runner(project_root, *, now_hkt, status_path):
            calls.append((project_root, now_hkt, status_path))
            return project_root / "output"

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = module.main(
                [
                    "--as-of-date",
                    "2026-08-09",
                    "--status-file",
                    "/tmp/capital-weekly-test-status.json",
                ],
                release_runner=release_runner,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 1)
        project_root, override_now, status_path = calls[0]
        self.assertEqual(project_root, Path(module.__file__).resolve().parents[1])
        self.assertEqual(latest_finished_week(override_now).end, date(2026, 8, 9))
        self.assertEqual(status_path, Path("/tmp/capital-weekly-test-status.json"))
        self.assertEqual(
            stdout.getvalue().strip(),
            str(project_root / "output"),
        )

    def test_validation_failure_exits_nonzero_with_the_error(self):
        module = self.load_cli_module()

        def release_runner(_project_root, *, now_hkt, status_path):
            raise ReleaseValidationError("missing fixed_income.csv")

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = module.main(
                ["--as-of-date", "2026-08-09"],
                release_runner=release_runner,
            )

        self.assertEqual(exit_code, 1)
        self.assertIn("missing fixed_income.csv", stderr.getvalue())

    def test_current_unfinished_sunday_override_is_rejected(self):
        module = self.load_cli_module()
        real_datetime = datetime

        class CurrentSundayDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                value = real_datetime(2026, 8, 9, 12, 0, tzinfo=tz)
                return cls.fromtimestamp(value.timestamp(), tz)

        calls = []
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with patch.object(module, "datetime", CurrentSundayDateTime):
                with self.assertRaises(SystemExit) as raised:
                    module.main(
                        ["--as-of-date", "2026-08-09"],
                        release_runner=lambda *args, **kwargs: calls.append(
                            (args, kwargs)
                        ),
                    )

        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(calls, [])
        self.assertIn("latest finished Sunday (2026-08-02)", stderr.getvalue())

    def test_future_sunday_override_is_rejected(self):
        module = self.load_cli_module()
        real_datetime = datetime

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                value = real_datetime(2026, 8, 14, 12, 0, tzinfo=tz)
                return cls.fromtimestamp(value.timestamp(), tz)

        calls = []
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with patch.object(module, "datetime", FixedDateTime):
                with self.assertRaises(SystemExit) as raised:
                    module.main(
                        ["--as-of-date", "2026-08-16"],
                        release_runner=lambda *args, **kwargs: calls.append(
                            (args, kwargs)
                        ),
                    )

        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(calls, [])
        self.assertIn("latest finished Sunday (2026-08-09)", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
