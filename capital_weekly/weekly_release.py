from __future__ import annotations

import csv
import fcntl
import hashlib
import json
import math
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import warnings
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from pathlib import Path
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .weekly_context import CATEGORY_FIELDS


HONG_KONG = ZoneInfo("Asia/Hong_Kong")
COORDINATOR_VERSION = "1"
MANIFEST_SCHEMA_VERSION = 2
LEGACY_DATASET_CONTRACT_VERSION = 1
DATASET_CONTRACT_VERSION = 2
SUPPORTED_DATASET_CONTRACT_VERSIONS = frozenset(
    {LEGACY_DATASET_CONTRACT_VERSION, DATASET_CONTRACT_VERSION}
)
PUBLICATION_MODES = frozenset({"coordinated", "migrated"})


@dataclass(frozen=True)
class WeekWindow:
    start: date
    end: date
    week_id: str


@dataclass(frozen=True)
class PipelineSpec:
    name: str
    command: tuple[str, ...]
    output_dir: str


class ReleaseValidationError(ValueError):
    pass


class ReleaseAlreadyRunning(RuntimeError):
    pass


class ReleasePipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class DatasetSpec:
    pipeline: str
    filename: str
    required_columns: tuple[str, ...]
    require_exact_columns: bool = False
    allow_empty: bool = False
    require_valid_row: bool = False
    date_columns: tuple[str, ...] = ()
    timestamp_columns: tuple[str, ...] = ()
    numeric_columns: tuple[str, ...] = ()
    source_url_column: str | None = None
    qc_column: str | None = None
    status_column: str | None = None
    accepted_statuses: frozenset[str] = frozenset()


RETURN_DATE_COLUMNS = (
    "latest_date",
    "daily_base_date",
    "weekly_base_date",
    "mtd_base_date",
    "ytd_base_date",
)
RETURN_NUMERIC_COLUMNS = (
    "latest_value",
    "daily_base_value",
    "daily_change",
    "weekly_base_value",
    "weekly_change",
    "mtd_base_value",
    "mtd_change",
    "ytd_base_value",
    "ytd_change",
)
RANK_COLUMNS = ("daily_rank", "weekly_rank", "mtd_rank", "ytd_rank")
INDEX_COLUMNS = (
    "region", "index_name_cn", "index_name_en", "ticker", "currency",
    "provider", "provider_symbol", "source", "notes", *RETURN_DATE_COLUMNS,
    *RETURN_NUMERIC_COLUMNS, "change_unit", "qc_flag", "source_url",
)
SECTOR_COLUMNS = (
    "market", "taxonomy", "taxonomy_version", "taxonomy_level", "sector_code",
    "sector_name_cn", "sector_name_en", "ticker", "currency", "provider",
    "provider_symbol", "source", "instrument_type", "sort_order", "notes",
    *RETURN_DATE_COLUMNS, *RETURN_NUMERIC_COLUMNS, "change_unit", "qc_flag",
    "source_url", *RANK_COLUMNS,
)
GICS_COLUMNS = (
    "gics_sector_code", "sector_name_cn", "sector_name_en", "ticker",
    "currency", "provider", "provider_symbol", "source", "proxy_type", "notes",
    *RETURN_DATE_COLUMNS, *RETURN_NUMERIC_COLUMNS, "change_unit", "qc_flag",
    "source_url",
)
MACRO_COLUMNS = (
    "asset_class", "group", "series_code", "name_cn", "name_en", "provider",
    "provider_symbol", "source", "source_url", "frequency", "level_unit",
    "change_unit", "sort_order", "notes", *RETURN_DATE_COLUMNS,
    *RETURN_NUMERIC_COLUMNS, "qc_flag", *RANK_COLUMNS,
)
SECTOR_DIVERGENCE_COLUMNS = (
    "market", "market_cn", "horizon", "horizon_cn", "valid_count",
    "positive_count", "flat_count", "negative_count", "breadth_ratio",
    "leader_laggard_spread", "dispersion", "median_return", "top_3",
    "bottom_3", "commentary_cn", "qc_flag",
)
MACRO_DIVERGENCE_COLUMNS = (
    "asset_class", "group", "group_cn", "horizon", "horizon_cn", "change_unit",
    "valid_count", "up_count", "flat_count", "down_count", "median_change",
    "change_range", "dispersion", "top_movers", "bottom_movers",
    "commentary_cn", "qc_flag",
)
INDEX_SOURCE_LOG_COLUMNS = (
    "ticker", "source", "status", "observations", *RETURN_DATE_COLUMNS,
    "latest_value", "daily_base_value", "weekly_base_value", "mtd_base_value",
    "ytd_base_value", "elapsed_ms", "source_url", "notes",
)
SECTOR_SOURCE_LOG_COLUMNS = (
    "market", "taxonomy", "sector_code", "sector_name_en", "ticker",
    "sort_order", "source", "status", "observations", *RETURN_DATE_COLUMNS,
    "latest_value", "daily_base_value", "weekly_base_value", "mtd_base_value",
    "ytd_base_value", "elapsed_ms", "source_url", "notes", "raw_cache_status",
    "raw_cache_error",
)
GICS_SOURCE_LOG_COLUMNS = (
    "ticker", "gics_sector_code", "sector_name_en", "source", "status",
    "observations", *RETURN_DATE_COLUMNS, "latest_value", "daily_base_value",
    "weekly_base_value", "mtd_base_value", "ytd_base_value", "elapsed_ms",
    "source_url", "notes",
)
MACRO_SOURCE_LOG_COLUMNS = (
    "series_code", "sort_order", "source", "status", "error", "observations",
    "latest_date", "latest_value", "source_url", "elapsed_ms",
    "raw_cache_status", "raw_cache_error",
)
SOURCE_LOG_NUMERIC_COLUMNS = (
    "observations", "latest_value", "daily_base_value", "weekly_base_value",
    "mtd_base_value", "ytd_base_value", "elapsed_ms",
)
SUCCESS_SOURCE_STATUSES = frozenset({"OK"})
CONTEXT_SOURCE_STATUSES = frozenset(
    {
        "OK",
        "NOT_CONFIGURED",
        "INSUFFICIENT_DATA",
        "POINT_IN_TIME_UNAVAILABLE",
        "FETCH_FAILED",
    }
)
CONTEXT_OPTIONAL_STATUS_POLICIES = {
    "NOT_CONFIGURED": frozenset(
        {
            ("sec_company_events", "company_events"),
            ("eia_commodities", "commodity_fundamentals"),
        }
    ),
    "INSUFFICIENT_DATA": frozenset(
        {("fred_financial_conditions", "financial_conditions")}
    ),
    "POINT_IN_TIME_UNAVAILABLE": frozenset(
        {
            ("sec_company_events", "company_events"),
            ("eia_commodities", "commodity_fundamentals"),
            ("fred_financial_conditions", "financial_conditions"),
        }
    ),
    "FETCH_FAILED": frozenset(
        {("yahoo_volatility_signals", "financial_conditions")}
    ),
}
CONTEXT_REQUIREDNESS_VALUES = frozenset({"required", "optional"})
ACCEPTED_QC_FLAGS = frozenset({"OK", "INSUFFICIENT_DATA"})
CALCULATED_SOURCE_POLICIES = {
    "calculated:UST10Y-UST2Y (shared Treasury observation dates)": (
        "series_code",
        ("UST10Y", "UST2Y"),
    )
}


def _dataset(
    pipeline: str,
    filename: str,
    required_columns: tuple[str, ...],
    **kwargs,
) -> DatasetSpec:
    return DatasetSpec(pipeline, filename, required_columns, **kwargs)


RELEASE_DATASETS = (
    _dataset(
        "equity_indices",
        "02_equity_indices.csv",
        INDEX_COLUMNS,
        require_valid_row=True,
        date_columns=RETURN_DATE_COLUMNS,
        numeric_columns=RETURN_NUMERIC_COLUMNS,
        source_url_column="source_url",
        qc_column="qc_flag",
    ),
    _dataset(
        "equity_indices",
        "source_log.csv",
        INDEX_SOURCE_LOG_COLUMNS,
        date_columns=RETURN_DATE_COLUMNS,
        numeric_columns=SOURCE_LOG_NUMERIC_COLUMNS,
        source_url_column="source_url",
        status_column="status",
        accepted_statuses=SUCCESS_SOURCE_STATUSES,
    ),
    _dataset(
        "equity_sectors",
        "03_equity_sectors.csv",
        SECTOR_COLUMNS,
        require_valid_row=True,
        date_columns=RETURN_DATE_COLUMNS,
        numeric_columns=("sort_order", *RETURN_NUMERIC_COLUMNS, *RANK_COLUMNS),
        source_url_column="source_url",
        qc_column="qc_flag",
    ),
    _dataset(
        "equity_sectors",
        "sector_divergence.csv",
        SECTOR_DIVERGENCE_COLUMNS,
        numeric_columns=(
            "valid_count", "positive_count", "flat_count", "negative_count",
            "breadth_ratio", "leader_laggard_spread", "dispersion",
            "median_return",
        ),
        qc_column="qc_flag",
    ),
    _dataset(
        "equity_sectors",
        "source_log.csv",
        SECTOR_SOURCE_LOG_COLUMNS,
        date_columns=RETURN_DATE_COLUMNS,
        numeric_columns=("sort_order", *SOURCE_LOG_NUMERIC_COLUMNS),
        source_url_column="source_url",
        status_column="status",
        accepted_statuses=SUCCESS_SOURCE_STATUSES,
    ),
    _dataset(
        "gics_sectors",
        "03_gics_sectors.csv",
        GICS_COLUMNS,
        require_valid_row=True,
        date_columns=RETURN_DATE_COLUMNS,
        numeric_columns=RETURN_NUMERIC_COLUMNS,
        source_url_column="source_url",
        qc_column="qc_flag",
    ),
    _dataset(
        "gics_sectors",
        "source_log.csv",
        GICS_SOURCE_LOG_COLUMNS,
        date_columns=RETURN_DATE_COLUMNS,
        numeric_columns=SOURCE_LOG_NUMERIC_COLUMNS,
        source_url_column="source_url",
        status_column="status",
        accepted_statuses=SUCCESS_SOURCE_STATUSES,
    ),
    *(
        _dataset(
            "macro_assets",
            filename,
            MACRO_COLUMNS,
            require_valid_row=True,
            date_columns=RETURN_DATE_COLUMNS,
            numeric_columns=("sort_order", *RETURN_NUMERIC_COLUMNS, *RANK_COLUMNS),
            source_url_column="source_url",
            qc_column="qc_flag",
        )
        for filename in (
            "fixed_income.csv",
            "commodities.csv",
            "foreign_exchange.csv",
            "policy_rates.csv",
            "money_market.csv",
        )
    ),
    _dataset(
        "macro_assets",
        "macro_divergence.csv",
        MACRO_DIVERGENCE_COLUMNS,
        numeric_columns=(
            "valid_count", "up_count", "flat_count", "down_count",
            "median_change", "change_range", "dispersion",
        ),
        qc_column="qc_flag",
    ),
    _dataset(
        "macro_assets",
        "source_log.csv",
        MACRO_SOURCE_LOG_COLUMNS,
        date_columns=("latest_date",),
        numeric_columns=("sort_order", "observations", "latest_value", "elapsed_ms"),
        source_url_column="source_url",
        status_column="status",
        accepted_statuses=SUCCESS_SOURCE_STATUSES,
    ),
    *(
        _dataset(
            "weekly_context",
            f"{category}.csv",
            tuple(fields),
            allow_empty=category != "source_log",
            date_columns=(
                ("event_date",)
                if category == "events"
                else ("as_of_date", "event_date", "report_date")
                if category == "company_events"
                else ("as_of_date",)
            ),
            timestamp_columns=("release_at_bjt", "known_as_of")
            if category == "economic_releases"
            else (),
            numeric_columns=(
                "value",
                "previous_value",
                "revised_previous",
                "consensus_value",
                "surprise_value",
            )
            if category == "economic_releases"
            else ("value",)
            if "value" in fields
            else ("freshness_days", "observations", "elapsed_ms")
            if category == "source_log"
            else (),
            source_url_column="source_url",
            qc_column="qc_flag" if "qc_flag" in fields else None,
            status_column="status" if category == "source_log" else None,
            accepted_statuses=(
                CONTEXT_SOURCE_STATUSES
                if category == "source_log"
                else frozenset()
            ),
            require_exact_columns=category == "source_log",
        )
        for category, fields in CATEGORY_FIELDS.items()
    ),
)

LEGACY_CONTEXT_SOURCE_LOG_COLUMNS = (
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
CURRENT_CONTEXT_SOURCE_LOG_ONLY_COLUMNS = frozenset(
    CATEGORY_FIELDS["source_log"]
) - frozenset(LEGACY_CONTEXT_SOURCE_LOG_COLUMNS)
LEGACY_RELEASE_DATASETS = tuple(
    replace(dataset, required_columns=LEGACY_CONTEXT_SOURCE_LOG_COLUMNS)
    if dataset.pipeline == "weekly_context" and dataset.filename == "source_log.csv"
    else dataset
    for dataset in RELEASE_DATASETS
    if not (
        dataset.pipeline == "weekly_context"
        and dataset.filename == "economic_releases.csv"
    )
)


def release_datasets_for_contract(
    dataset_contract_version: int,
) -> tuple[DatasetSpec, ...]:
    if dataset_contract_version == LEGACY_DATASET_CONTRACT_VERSION:
        return LEGACY_RELEASE_DATASETS
    if dataset_contract_version == DATASET_CONTRACT_VERSION:
        return RELEASE_DATASETS
    raise ReleaseValidationError(
        f"Unsupported dataset contract version: {dataset_contract_version}"
    )


def latest_finished_week(now_hkt: datetime | None = None) -> WeekWindow:
    current = now_hkt or datetime.now(HONG_KONG)
    days_since_previous_sunday = current.weekday() + 1
    end = current.date() - timedelta(days=days_since_previous_sunday)
    start = end - timedelta(days=6)
    return WeekWindow(start, end, f"week_{start:%Y%m%d}-{end:%Y%m%d}")


def build_pipeline_specs(
    staging_week: str | Path,
    window: WeekWindow,
) -> tuple[PipelineSpec, ...]:
    staging_root = Path(staging_week)
    end_stamp = f"{window.end:%Y%m%d}"
    as_of = window.end.isoformat()
    definitions = (
        (
            "equity_indices",
            "scripts/fetch_equity_indices.py",
            f"capital_weekly_equity_indices_python_{end_stamp}",
        ),
        (
            "equity_sectors",
            "scripts/fetch_equity_sectors.py",
            f"capital_weekly_equity_sectors_python_{end_stamp}",
        ),
        (
            "gics_sectors",
            "scripts/fetch_gics_sectors.py",
            f"capital_weekly_gics_sectors_python_{end_stamp}",
        ),
        (
            "macro_assets",
            "scripts/fetch_macro_assets.py",
            f"capital_weekly_macro_assets_python_{end_stamp}",
        ),
    )
    specs = []
    for name, script, output_name in definitions:
        output_dir = str(staging_root / output_name)
        specs.append(
            PipelineSpec(
                name=name,
                command=(
                    sys.executable,
                    script,
                    "--output-dir",
                    output_dir,
                    "--as-of-date",
                    as_of,
                ),
                output_dir=output_dir,
            )
        )
    context_output = str(staging_root / f"capital_weekly_context_{end_stamp}")
    specs.append(
        PipelineSpec(
            name="weekly_context",
            command=(
                sys.executable,
                "scripts/fetch_weekly_context.py",
                "--output-dir",
                context_output,
                "--start-date",
                window.start.isoformat(),
                "--end-date",
                as_of,
            ),
            output_dir=context_output,
        )
    )
    return tuple(specs)


def file_manifest(path: Path, release_root: Path) -> dict:
    content = path.read_bytes()
    row_count = None
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as file:
            row_count = max(
                sum(1 for row in csv.reader(file) if row) - 1,
                0,
            )
    return {
        "path": path.relative_to(release_root).as_posix(),
        "rows": row_count,
        "sha256": hashlib.sha256(content).hexdigest(),
        "status": "OK",
    }


def _ensure_regular_contained_file(path: Path, release_root: Path) -> None:
    if path.is_symlink():
        raise ReleaseValidationError(
            f"Published path must not be a symbolic link: {path.name}"
        )
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as error:
        raise ReleaseValidationError(f"Missing required file: {path.name}") from error
    if not stat.S_ISREG(mode):
        raise ReleaseValidationError(f"Published path must be a regular file: {path.name}")
    try:
        path.resolve(strict=True).relative_to(release_root.resolve(strict=True))
    except ValueError as error:
        raise ReleaseValidationError(
            f"Published path escapes the release root: {path.name}"
        ) from error


def _published_file_manifests(release_root: Path) -> list[dict]:
    if release_root.is_symlink():
        raise ReleaseValidationError("Release root must not be a symbolic link")
    published_files = []
    for path in release_root.rglob("*"):
        if path.is_symlink():
            raise ReleaseValidationError(
                f"Published path must not be a symbolic link: {path.name}"
            )
        if path.is_file() and path != release_root / "manifest.json":
            _ensure_regular_contained_file(path, release_root)
            published_files.append(path)
    published_files.sort(key=lambda path: path.relative_to(release_root).as_posix())
    for path in published_files:
        if path.suffix.lower() == ".csv":
            _validate_csv_header(path)
    return [file_manifest(path, release_root) for path in published_files]


def build_release_manifest(
    root: Path,
    window: WeekWindow,
    *,
    publication_mode: str,
    pipeline_runs: list[dict],
    dataset_contract_version: int = DATASET_CONTRACT_VERSION,
    generated_at: str | None = None,
    migrated_at: str | None = None,
) -> dict:
    if publication_mode not in PUBLICATION_MODES:
        raise ReleaseValidationError(f"Unknown publication mode: {publication_mode}")
    release_datasets_for_contract(dataset_contract_version)
    release_root = Path(root)
    manifest = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "dataset_contract_version": dataset_contract_version,
        "publication_mode": publication_mode,
        "week_id": window.week_id,
        "week_start": window.start.isoformat(),
        "week_end": window.end.isoformat(),
        "timezone": HONG_KONG.key,
        "start_date": window.start.isoformat(),
        "end_date": window.end.isoformat(),
        "generated_at": generated_at or datetime.now(HONG_KONG).isoformat(
            timespec="seconds"
        ),
        "status": "complete",
        "pipelines": pipeline_runs,
        "files": _published_file_manifests(release_root),
        "failures": [],
        "coordinator_version": COORDINATOR_VERSION,
    }
    if migrated_at is not None:
        manifest["migrated_at"] = migrated_at
    return manifest


def _validate_csv_header(path: Path) -> None:
    try:
        with path.open(newline="", encoding="utf-8-sig") as file:
            header = next(csv.reader(file, strict=True), None)
    except csv.Error as error:
        raise ReleaseValidationError(
            f"{path.name} contains malformed CSV: {error}"
        ) from error
    if not header or any(not column.strip() for column in header):
        raise ReleaseValidationError(
            f"{path.name} must contain a standard header"
        )


def _read_dataset(path: Path, spec: DatasetSpec) -> list[dict[str, str]]:
    _ensure_regular_contained_file(path, path.parents[1])
    if not path.is_file():
        raise ReleaseValidationError(f"Missing required file: {path.name}")
    try:
        with path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file, strict=True)
            columns = tuple(reader.fieldnames or ())
            duplicates = sorted(
                {column for column in columns if columns.count(column) > 1}
            )
            if duplicates:
                raise ReleaseValidationError(
                    f"{path.name} has duplicate columns: {', '.join(duplicates)}"
                )
            missing = [
                column for column in spec.required_columns if column not in columns
            ]
            if missing:
                raise ReleaseValidationError(
                    f"{path.name} missing required columns: {', '.join(missing)}"
                )
            if spec.require_exact_columns:
                unexpected = [
                    column
                    for column in columns
                    if column not in spec.required_columns
                ]
                if unexpected:
                    raise ReleaseValidationError(
                        f"{path.name} has unexpected columns: "
                        + ", ".join(unexpected)
                    )
            rows = list(reader)
    except csv.Error as error:
        raise ReleaseValidationError(
            f"{path.name} contains malformed CSV: {error}"
        ) from error
    for row_number, row in enumerate(rows, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ReleaseValidationError(
                f"{path.name} row {row_number} has an invalid column count"
            )
    if not rows and not spec.allow_empty:
        raise ReleaseValidationError(f"Required table {path.name} is empty")
    return rows


def _csv_columns(path: Path, release_root: Path) -> tuple[str, ...]:
    _ensure_regular_contained_file(path, release_root)
    try:
        with path.open(newline="", encoding="utf-8-sig") as file:
            columns = tuple(next(csv.reader(file, strict=True), ()))
    except csv.Error as error:
        raise ReleaseValidationError(
            f"{path.name} contains malformed CSV: {error}"
        ) from error
    if not columns or any(not column.strip() for column in columns):
        raise ReleaseValidationError(f"{path.name} must contain a standard header")
    return columns


def _validate_dataset_contract_boundary(
    release_root: Path,
    window: WeekWindow,
    dataset_contract_version: int,
) -> None:
    if dataset_contract_version != LEGACY_DATASET_CONTRACT_VERSION:
        return
    context_dir = next(
        Path(spec.output_dir)
        for spec in build_pipeline_specs(release_root, window)
        if spec.name == "weekly_context"
    )
    economic_releases = context_dir / "economic_releases.csv"
    if economic_releases.exists() or economic_releases.is_symlink():
        raise ReleaseValidationError(
            "economic_releases.csv is not valid for the legacy dataset contract"
        )
    source_log = context_dir / "source_log.csv"
    columns = _csv_columns(source_log, release_root)
    if CURRENT_CONTEXT_SOURCE_LOG_ONLY_COLUMNS.intersection(columns):
        raise ReleaseValidationError(
            "source_log.csv is not valid for the legacy dataset contract"
        )


def _contains_http_url(value: str) -> bool:
    match = re.search(r"(?:^|[\s|])(https?://[^\s|]+)", value, re.IGNORECASE)
    if not match:
        return False
    parsed = urlparse(match.group(1))
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def _source_reference_error(
    row: dict[str, str],
    column: str,
    rows: list[dict[str, str]],
) -> str | None:
    value = (row.get(column) or "").strip()
    if _contains_http_url(value):
        return None
    policy = CALCULATED_SOURCE_POLICIES.get(value)
    provider_is_valid = (
        "provider" not in row
        or (row.get("provider") or "").strip().lower() == "calculated"
    )
    if not provider_is_valid or not policy:
        return "must contain an HTTP(S) URL or registered calculation reference"
    identity_column, dependencies = policy
    missing_dependencies = [
        dependency
        for dependency in dependencies
        if not any(
            (candidate.get(identity_column) or "").strip() == dependency
            and _contains_http_url((candidate.get(column) or "").strip())
            for candidate in rows
        )
    ]
    if missing_dependencies:
        return (
            "registered calculation is missing HTTP(S) dependencies: "
            + ", ".join(missing_dependencies)
        )
    return None


def _validate_row(
    path: Path,
    row_number: int,
    row: dict[str, str],
    spec: DatasetSpec,
    window: WeekWindow,
    rows: list[dict[str, str]],
    dataset_contract_version: int,
) -> None:
    is_current_context_source_log = (
        dataset_contract_version == DATASET_CONTRACT_VERSION
        and spec.pipeline == "weekly_context"
        and spec.filename == "source_log.csv"
    )
    requiredness = ""
    if is_current_context_source_log:
        requiredness = (row.get("requiredness") or "").strip()
        if requiredness not in CONTEXT_REQUIREDNESS_VALUES:
            raise ReleaseValidationError(
                f"{path.name} row {row_number} requiredness must be required or optional"
            )
        raw_latest_known_as_of = (row.get("latest_known_as_of") or "").strip()
        if raw_latest_known_as_of:
            try:
                latest_known_as_of = datetime.fromisoformat(
                    raw_latest_known_as_of
                )
            except ValueError as error:
                raise ReleaseValidationError(
                    f"{path.name} row {row_number} latest_known_as_of "
                    "must include a UTC offset"
                ) from error
            if (
                latest_known_as_of.tzinfo is None
                or latest_known_as_of.utcoffset() is None
            ):
                raise ReleaseValidationError(
                    f"{path.name} row {row_number} latest_known_as_of "
                    "must include a UTC offset"
                )
            cutoff = datetime.combine(
                window.end,
                datetime.max.time(),
                tzinfo=HONG_KONG,
            )
            if latest_known_as_of.astimezone(HONG_KONG) > cutoff:
                raise ReleaseValidationError(
                    f"{path.name} row {row_number} latest_known_as_of "
                    f"exceeds {window.end}"
                )
    if spec.status_column:
        status = (row.get(spec.status_column) or "").strip().upper()
        optional_identity = (
            (row.get("provider") or "").strip(),
            (row.get("category") or "").strip(),
        )
        status_is_accepted = status in spec.accepted_statuses and (
            status == "OK"
            or (
                optional_identity in CONTEXT_OPTIONAL_STATUS_POLICIES.get(
                    status,
                    frozenset(),
                )
                and (
                    not is_current_context_source_log
                    or requiredness == "optional"
                )
            )
        )
        if not status_is_accepted:
            raise ReleaseValidationError(
                f"{path.name} row {row_number} has unacceptable status: {status or 'blank'}"
            )
    if spec.qc_column:
        qc_flag = (row.get(spec.qc_column) or "").strip().upper()
        if qc_flag not in ACCEPTED_QC_FLAGS:
            raise ReleaseValidationError(
                f"{path.name} row {row_number} has unacceptable qc_flag: "
                f"{qc_flag or 'blank'}"
            )
    for column in spec.date_columns:
        raw_date = (row.get(column) or "").strip()
        if not raw_date:
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
            raise ReleaseValidationError(
                f"{path.name} row {row_number} {column} must be a valid YYYY-MM-DD date"
            )
        try:
            observation_date = date.fromisoformat(raw_date)
        except ValueError as error:
            raise ReleaseValidationError(
                f"{path.name} row {row_number} {column} must be a valid YYYY-MM-DD date"
            ) from error
        if observation_date > window.end:
            raise ReleaseValidationError(
                f"{path.name} row {row_number} date {observation_date} exceeds {window.end}"
            )
    cutoff = datetime.combine(window.end, datetime.max.time(), tzinfo=HONG_KONG)
    for column in spec.timestamp_columns:
        raw_timestamp = (row.get(column) or "").strip()
        try:
            timestamp = datetime.fromisoformat(raw_timestamp)
        except ValueError as error:
            raise ReleaseValidationError(
                f"{path.name} row {row_number} {column} must include a UTC offset"
            ) from error
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ReleaseValidationError(
                f"{path.name} row {row_number} {column} must include a UTC offset"
            )
        if timestamp.astimezone(HONG_KONG) > cutoff:
            raise ReleaseValidationError(
                f"{path.name} row {row_number} {column} exceeds {window.end}"
            )
    source_error = (
        _source_reference_error(row, spec.source_url_column, rows)
        if spec.source_url_column
        else None
    )
    if source_error:
        raise ReleaseValidationError(
            f"{path.name} row {row_number} {spec.source_url_column} {source_error}"
        )
    for column in spec.numeric_columns:
        raw_value = (row.get(column) or "").strip()
        if not raw_value:
            continue
        try:
            value = float(raw_value)
        except ValueError as error:
            raise ReleaseValidationError(
                f"{path.name} row {row_number} {column} must be finite"
            ) from error
        if not math.isfinite(value):
            raise ReleaseValidationError(
                f"{path.name} row {row_number} {column} must be finite"
            )


def _is_valid_core_row(row: dict[str, str], spec: DatasetSpec) -> bool:
    if not spec.require_valid_row:
        return True
    return (
        (row.get(spec.qc_column or "") or "").strip().upper() == "OK"
        and bool((row.get("latest_date") or "").strip())
        and bool((row.get("latest_value") or "").strip())
    )


def validate_staged_week(
    root: Path,
    window: WeekWindow,
    *,
    dataset_contract_version: int = DATASET_CONTRACT_VERSION,
) -> dict:
    release_root = Path(root)
    _validate_dataset_contract_boundary(
        release_root,
        window,
        dataset_contract_version,
    )
    pipeline_dirs = {
        spec.name: Path(spec.output_dir)
        for spec in build_pipeline_specs(release_root, window)
    }
    for dataset in release_datasets_for_contract(dataset_contract_version):
        path = pipeline_dirs[dataset.pipeline] / dataset.filename
        rows = _read_dataset(path, dataset)
        for row_number, row in enumerate(rows, start=2):
            _validate_row(
                path,
                row_number,
                row,
                dataset,
                window,
                rows,
                dataset_contract_version,
            )
        if dataset.require_valid_row and not any(
            _is_valid_core_row(row, dataset) for row in rows
        ):
            raise ReleaseValidationError(
                f"Required table {path.name} has no valid row"
            )
    pipelines = [
        {
            "name": pipeline.name,
            "status": "validated",
            "started_at": None,
            "finished_at": None,
            "elapsed_ms": None,
        }
        for pipeline in build_pipeline_specs(release_root, window)
    ]
    return build_release_manifest(
        release_root,
        window,
        publication_mode="coordinated",
        pipeline_runs=pipelines,
        dataset_contract_version=dataset_contract_version,
    )


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary = Path(file.name)
            json.dump(
                payload,
                file,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _publish_directory(
    staging_dir: Path,
    output_dir: Path,
    finalize: Callable[[], None] | None = None,
) -> None:
    backup_dir = output_dir.with_name(
        f".{output_dir.name}.backup-{uuid.uuid4().hex}"
    )
    had_output = output_dir.exists()
    if had_output:
        os.replace(output_dir, backup_dir)
    try:
        os.replace(staging_dir, output_dir)
        if finalize is not None:
            finalize()
    except Exception:
        if output_dir.exists() and not staging_dir.exists():
            os.replace(output_dir, staging_dir)
        if had_output and backup_dir.exists():
            os.replace(backup_dir, output_dir)
        raise
    if backup_dir.exists():
        try:
            shutil.rmtree(backup_dir)
        except OSError as error:
            try:
                warnings.warn(
                    f"Published {output_dir.name}, but backup cleanup failed: {error}",
                    RuntimeWarning,
                )
            except RuntimeWarning:
                pass


def _status_timestamp() -> str:
    return datetime.now(HONG_KONG).isoformat(timespec="seconds")


def safe_error_reason(error: BaseException) -> str:
    reason = str(error).strip() or type(error).__name__

    def replace_quoted_path(match: re.Match[str]) -> str:
        quote = match.group("quote")
        return f"{quote}{Path(match.group('path')).name}{quote}"

    reason = re.sub(
        r"(?P<quote>['\"])(?P<path>/[^'\"]+)(?P=quote)",
        replace_quoted_path,
        reason,
    )
    reason = re.sub(
        r"(?<![:\w/])/(?P<path>[^'\",;)\n]+)",
        lambda match: Path(f"/{match.group('path')}").name,
        reason,
    )
    return reason


def _write_status(path: Path, status: dict) -> None:
    status["updated_at"] = _status_timestamp()
    _atomic_write_json(path, status)


@contextmanager
def release_write_lock(outputs: Path, *, operation: str):
    outputs.mkdir(parents=True, exist_ok=True)
    lock_path = outputs / ".capital_weekly_refresh.lock"
    lock_file = lock_path.open("a+")
    acquired = False
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError as error:
            raise ReleaseAlreadyRunning(
                "Another Capital Weekly release write is already running; "
                f"cannot start {operation}"
            ) from error
        yield
    finally:
        if acquired:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()


def run_weekly_release(
    project_root: Path,
    now_hkt: datetime | None = None,
    status_path: Path | None = None,
    runner=subprocess.run,
) -> Path:
    root = Path(project_root).resolve()
    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    window = latest_finished_week(now_hkt)
    destination = outputs / window.week_id
    status_file = (
        Path(status_path)
        if status_path is not None
        else outputs / ".capital-weekly-refresh" / "status.json"
    )
    started = datetime.now(HONG_KONG)
    job_id = f"{started:%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    status = {
        "job_id": job_id,
        "status": "running",
        "pid": os.getpid(),
        "updated_at": started.isoformat(timespec="seconds"),
        "week_id": window.week_id,
        "current_pipeline": None,
        "completed": 0,
        "total": 5,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": None,
        "error": None,
    }
    with release_write_lock(outputs, operation=f"refresh for {window.week_id}"):
        staging_week = Path(
            tempfile.mkdtemp(prefix=f".{window.week_id}.staging-", dir=outputs)
        )
        try:
            _write_status(status_file, status)
            specs = build_pipeline_specs(staging_week, window)
            pipeline_runs = []
            for spec in specs:
                status["current_pipeline"] = spec.name
                _write_status(status_file, status)
                pipeline_started = datetime.now(HONG_KONG)
                pipeline_timer = time.monotonic()
                try:
                    runner(spec.command, check=True, cwd=root)
                except subprocess.CalledProcessError as error:
                    raise ReleasePipelineError(
                        f"Pipeline {spec.name} failed with exit code {error.returncode}"
                    ) from error
                pipeline_finished = datetime.now(HONG_KONG)
                pipeline_runs.append(
                    {
                        "name": spec.name,
                        "status": "succeeded",
                        "started_at": pipeline_started.isoformat(timespec="seconds"),
                        "finished_at": pipeline_finished.isoformat(timespec="seconds"),
                        "elapsed_ms": int((time.monotonic() - pipeline_timer) * 1000),
                    }
                )
                status["completed"] += 1
                _write_status(status_file, status)

            status["current_pipeline"] = "validation"
            _write_status(status_file, status)
            manifest = validate_staged_week(staging_week, window)
            manifest["pipelines"] = pipeline_runs
            _atomic_write_json(staging_week / "manifest.json", manifest)
            status["current_pipeline"] = "publish"
            _write_status(status_file, status)

            def finalize_release() -> None:
                succeeded_status = {
                    **status,
                    "status": "succeeded",
                    "current_pipeline": None,
                    "finished_at": _status_timestamp(),
                    "error": None,
                }
                _write_status(status_file, succeeded_status)
                status.update(succeeded_status)

            _publish_directory(staging_week, destination, finalize_release)
            return destination
        except Exception as error:
            status.update(
                {
                    "status": "failed",
                    "finished_at": _status_timestamp(),
                    "error": safe_error_reason(error),
                }
            )
            _write_status(status_file, status)
            raise
        finally:
            if staging_week.exists():
                shutil.rmtree(staging_week)


__all__ = [
    "PipelineSpec",
    "DATASET_CONTRACT_VERSION",
    "LEGACY_DATASET_CONTRACT_VERSION",
    "MANIFEST_SCHEMA_VERSION",
    "RELEASE_DATASETS",
    "SUPPORTED_DATASET_CONTRACT_VERSIONS",
    "ReleaseAlreadyRunning",
    "ReleasePipelineError",
    "ReleaseValidationError",
    "WeekWindow",
    "_publish_directory",
    "build_pipeline_specs",
    "build_release_manifest",
    "file_manifest",
    "latest_finished_week",
    "release_write_lock",
    "run_weekly_release",
    "release_datasets_for_contract",
    "safe_error_reason",
    "validate_staged_week",
]
