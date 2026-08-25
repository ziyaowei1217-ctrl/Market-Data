from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Literal

from .weekly_context import CATEGORY_FIELDS
from .weekly_release import (
    DATASET_CONTRACT_VERSION,
    HONG_KONG,
    LEGACY_DATASET_CONTRACT_VERSION,
    MANIFEST_SCHEMA_VERSION,
    LEGACY_CONTEXT_SOURCE_LOG_COLUMNS,
    RELEASE_DATASETS,
    SUPPORTED_DATASET_CONTRACT_VERSIONS,
    ReleaseAlreadyRunning,
    ReleaseValidationError,
    WeekWindow,
    _atomic_write_json,
    _publish_directory,
    build_pipeline_specs,
    build_release_manifest,
    safe_error_reason,
    release_write_lock,
    validate_staged_week,
)


WEEK_ID_PATTERN = re.compile(r"^week_(\d{8})-(\d{8})$")
MigrationStatus = Literal[
    "migratable", "already-valid", "repaired", "skipped", "failed"
]


@dataclass(frozen=True)
class MigrationResult:
    week_id: str
    status: MigrationStatus
    repaired_files: tuple[str, ...] = ()
    reason: str | None = None


def _window_from_week_id(week_id: str) -> WeekWindow:
    match = WEEK_ID_PATTERN.fullmatch(week_id)
    if match is None:
        raise ValueError("--week must match week_YYYYMMDD-YYYYMMDD")
    try:
        start = datetime.strptime(match.group(1), "%Y%m%d").date()
        end = datetime.strptime(match.group(2), "%Y%m%d").date()
    except ValueError as error:
        raise ValueError("--week must match week_YYYYMMDD-YYYYMMDD") from error
    if start.weekday() != 0 or end.weekday() != 6 or (end - start).days != 6:
        raise ValueError("--week must identify one Monday-to-Sunday week")
    return WeekWindow(start=start, end=end, week_id=week_id)


def _first_symlink(root: Path) -> Path | None:
    if root.is_symlink():
        return root
    for path in root.rglob("*"):
        if path.is_symlink():
            return path
    return None


def _legacy_pipeline_runs(root: Path, window: WeekWindow) -> list[dict]:
    return [
        {
            "name": spec.name,
            "status": "validated_legacy",
            "started_at": None,
            "finished_at": None,
            "elapsed_ms": None,
        }
        for spec in build_pipeline_specs(root, window)
    ]


def _dataset_contract_version(week: Path, window: WeekWindow) -> int:
    context_dir = next(
        Path(spec.output_dir)
        for spec in build_pipeline_specs(week, window)
        if spec.name == "weekly_context"
    )
    economic_releases = context_dir / "economic_releases.csv"
    source_log = context_dir / "source_log.csv"
    has_economic_releases = economic_releases.exists() or economic_releases.is_symlink()
    try:
        with source_log.open(newline="", encoding="utf-8-sig") as file:
            source_log_columns = tuple(next(csv.reader(file, strict=True), ()))
    except (OSError, csv.Error) as error:
        raise ReleaseValidationError(
            f"source_log.csv cannot be read: {safe_error_reason(error)}"
        ) from error
    has_expanded_source_log = bool(
        set(CATEGORY_FIELDS["source_log"])
        - set(LEGACY_CONTEXT_SOURCE_LOG_COLUMNS)
        & set(source_log_columns)
    )
    if has_economic_releases and has_expanded_source_log:
        return DATASET_CONTRACT_VERSION
    if not has_economic_releases and not has_expanded_source_log:
        return LEGACY_DATASET_CONTRACT_VERSION
    raise ReleaseValidationError(
        "Mixed dataset contract markers; economic_releases.csv and source_log.csv "
        "must both be legacy or current"
    )


def _valid_existing_manifest(week: Path, window: WeekWindow) -> bool:
    manifest_path = week / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        contract_version = manifest.get("dataset_contract_version")
        if contract_version not in SUPPORTED_DATASET_CONTRACT_VERSIONS:
            return False
        validated = validate_staged_week(
            week,
            window,
            dataset_contract_version=contract_version,
        )
    except (OSError, ValueError, ReleaseValidationError, json.JSONDecodeError):
        return False
    if not isinstance(manifest, dict):
        return False
    valid_pipeline_statuses = {
        "coordinated": {"succeeded"},
        "migrated": {"validated_legacy"},
    }
    publication_mode = manifest.get("publication_mode")
    pipelines = manifest.get("pipelines")
    expected_pipeline_names = {
        spec.name for spec in build_pipeline_specs(week, window)
    }
    return (
        manifest.get("manifest_schema_version") == MANIFEST_SCHEMA_VERSION
        and manifest.get("dataset_contract_version") == contract_version
        and publication_mode in valid_pipeline_statuses
        and manifest.get("week_id") == window.week_id
        and manifest.get("week_start") == window.start.isoformat()
        and manifest.get("week_end") == window.end.isoformat()
        and manifest.get("timezone") == HONG_KONG.key
        and manifest.get("status") == "complete"
        and manifest.get("failures") == []
        and manifest.get("files") == validated["files"]
        and isinstance(pipelines, list)
        and len(pipelines) == 5
        and {
            pipeline.get("name")
            for pipeline in pipelines
            if isinstance(pipeline, dict)
        } == expected_pipeline_names
        and all(
            isinstance(pipeline, dict)
            and pipeline.get("status") in valid_pipeline_statuses[publication_mode]
            for pipeline in pipelines
        )
    )


def _repair_blank_optional_context_files(
    working: Path,
    window: WeekWindow,
) -> tuple[str, ...]:
    context_dir = next(
        Path(spec.output_dir)
        for spec in build_pipeline_specs(working, window)
        if spec.name == "weekly_context"
    )
    repairable = {
        spec.filename
        for spec in RELEASE_DATASETS
        if spec.pipeline == "weekly_context" and spec.allow_empty
    }
    repaired = []
    for filename in sorted(repairable):
        path = context_dir / filename
        if not path.is_file() or path.is_symlink():
            continue
        try:
            contents = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        if contents.strip():
            continue
        category = path.stem
        fields = CATEGORY_FIELDS.get(category)
        if fields is None:
            continue
        with path.open("w", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(fields)
        repaired.append(path.relative_to(working).as_posix())
    return tuple(repaired)


def _migrate_one(
    week: Path,
    *,
    dry_run: bool,
    now_hkt: datetime,
) -> MigrationResult:
    week_id = week.name
    try:
        window = _window_from_week_id(week_id)
    except ValueError as error:
        return MigrationResult(week_id, "skipped", reason=safe_error_reason(error))
    symlink = _first_symlink(week)
    if symlink is not None:
        return MigrationResult(
            week_id,
            "skipped",
            reason=f"Published path must not be a symbolic link: {symlink.name}",
        )
    manifest_path = week / "manifest.json"
    if manifest_path.exists():
        if _valid_existing_manifest(week, window):
            return MigrationResult(week_id, "already-valid")
        return MigrationResult(
            week_id,
            "skipped",
            reason="Existing manifest is invalid; refusing to overwrite it",
        )

    working = Path(
        tempfile.mkdtemp(prefix=f".{week_id}.migration-", dir=week.parent)
    )
    try:
        shutil.copytree(week, working, dirs_exist_ok=True, symlinks=True)
        copied_symlink = _first_symlink(working)
        if copied_symlink is not None:
            return MigrationResult(
                week_id,
                "skipped",
                reason=(
                    "Published path must not be a symbolic link: "
                    f"{copied_symlink.name}"
                ),
            )
        repaired_files = _repair_blank_optional_context_files(working, window)
        try:
            contract_version = _dataset_contract_version(working, window)
            validate_staged_week(
                working,
                window,
                dataset_contract_version=contract_version,
            )
        except ReleaseValidationError as error:
            return MigrationResult(
                week_id,
                "skipped",
                repaired_files=repaired_files,
                reason=safe_error_reason(error),
            )
        if dry_run:
            return MigrationResult(
                week_id,
                "migratable",
                repaired_files=repaired_files,
            )

        migrated_at = now_hkt.astimezone(HONG_KONG).isoformat(timespec="seconds")
        manifest = build_release_manifest(
            working,
            window,
            publication_mode="migrated",
            pipeline_runs=_legacy_pipeline_runs(working, window),
            dataset_contract_version=contract_version,
            generated_at=migrated_at,
            migrated_at=migrated_at,
        )
        _atomic_write_json(working / "manifest.json", manifest)
        try:
            _publish_directory(working, week)
        except Exception as error:
            return MigrationResult(
                week_id,
                "failed",
                repaired_files=repaired_files,
                reason=safe_error_reason(error),
            )
        return MigrationResult(
            week_id,
            "repaired",
            repaired_files=repaired_files,
        )
    except Exception as error:
        return MigrationResult(week_id, "failed", reason=safe_error_reason(error))
    finally:
        if working.exists():
            shutil.rmtree(working)


def migrate_releases(
    project_root: Path,
    *,
    dry_run: bool,
    week_id: str | None = None,
    now_hkt: datetime | None = None,
) -> list[MigrationResult]:
    if week_id is not None:
        _window_from_week_id(week_id)
    root = Path(project_root).resolve()
    outputs = root / "outputs"
    current = now_hkt or datetime.now(HONG_KONG)
    if week_id is not None:
        candidate = outputs / week_id
        if not candidate.is_dir() or candidate.is_symlink():
            return [
                MigrationResult(
                    week_id,
                    "skipped",
                    reason="Week directory does not exist or is not a regular directory",
                )
            ]
        weeks = [candidate]
    else:
        try:
            weeks = sorted(
                (
                    entry
                    for entry in outputs.iterdir()
                    if entry.is_dir()
                    and not entry.is_symlink()
                    and WEEK_ID_PATTERN.fullmatch(entry.name)
                ),
                key=lambda entry: entry.name,
            )
        except FileNotFoundError:
            return []
    if dry_run or not weeks:
        return [
            _migrate_one(week, dry_run=dry_run, now_hkt=current)
            for week in weeks
        ]
    try:
        with release_write_lock(outputs, operation="release migration"):
            return [
                _migrate_one(week, dry_run=False, now_hkt=current)
                for week in weeks
            ]
    except ReleaseAlreadyRunning as error:
        reason = safe_error_reason(error)
        return [
            MigrationResult(week.name, "failed", reason=reason)
            for week in weeks
        ]


__all__ = ["MigrationResult", "migrate_releases"]
