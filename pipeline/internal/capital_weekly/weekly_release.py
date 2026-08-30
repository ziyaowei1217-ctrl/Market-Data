from __future__ import annotations

import ast
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

from pipeline.internal import common as common_config
from pipeline.internal.common import load_config_rows
from pipeline.internal.common import sanitize_audit_text

from .commodity_research import (
    METRIC_HISTORY_FIELDS,
    PRICE_HISTORY_FIELDS,
    RESEARCH_FACT_FIELDS,
    build_research_facts,
    load_formula_specs,
    stable_record_id,
    validate_commodity_registry,
    validate_history_limits,
)
from .macro_assets import CALCULATED_SOURCE_REFERENCES
from .context.common import (
    MEASUREMENT_KIND_VALUES,
    METRIC_ROLE_VALUES,
    PARTICIPANT_CLASS_VALUES,
)
from .context.provider_contracts import PROVIDER_PHASES, target_sunday_cutoff
from .weekly_context import CATEGORY_FIELDS


HONG_KONG = ZoneInfo("Asia/Hong_Kong")
COORDINATOR_VERSION = "1"
MANIFEST_SCHEMA_VERSION = 2
LEGACY_DATASET_CONTRACT_VERSION = 1
COMPATIBILITY_DATASET_CONTRACT_VERSION = 2
DATASET_CONTRACT_VERSION = 3
SUPPORTED_DATASET_CONTRACT_VERSIONS = frozenset(
    {
        LEGACY_DATASET_CONTRACT_VERSION,
        COMPATIBILITY_DATASET_CONTRACT_VERSION,
        DATASET_CONTRACT_VERSION,
    }
)
PUBLICATION_MODES = frozenset({"coordinated", "migrated"})
OUTPUT_SCHEMA_VERSION = "1.0"
OUTPUT_BUSINESS_FILES = (
    "indices.json",
    "sectors.json",
    "gics.json",
    "macro.json",
    "context.json",
)
OUTPUT_FILES = frozenset((*OUTPUT_BUSINESS_FILES, "release.json"))
OUTPUT_TABLES = {
    "indices": (
        "equity_indices",
        (("indices", "02_equity_indices.csv"),),
    ),
    "sectors": (
        "equity_sectors",
        (
            ("sectors", "03_equity_sectors.csv"),
            ("divergence", "sector_divergence.csv"),
        ),
    ),
    "gics": (
        "gics_sectors",
        (("sectors", "03_gics_sectors.csv"),),
    ),
    "macro": (
        "macro_assets",
        (
            ("fixed_income", "fixed_income.csv"),
            ("policy_rates", "policy_rates.csv"),
            ("money_market", "money_market.csv"),
            ("foreign_exchange", "foreign_exchange.csv"),
            ("commodities", "commodities.csv"),
            ("commodity_price_history", "commodity_price_history.csv"),
            ("divergence", "macro_divergence.csv"),
        ),
    ),
    "context": (
        "weekly_context",
        tuple(
            (category, f"{category}.csv")
            for category in (
                "events",
                "economic_releases",
                "financial_conditions",
                "market_internals",
                "positioning_flows",
                "company_events",
                "commodity_fundamentals",
                "commodity_metric_history",
                "commodity_research_facts",
            )
        ),
    ),
}
V2_OUTPUT_TABLES = frozenset(
    {
        ("macro", "commodity_price_history"),
        ("context", "commodity_metric_history"),
        ("context", "commodity_research_facts"),
    }
)


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
    json_array_columns: tuple[str, ...] = ()
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
    "commodity_code", "commodity_family", "price_kind", "known_as_of",
    "provider_route",
)
COMMODITY_RESEARCH_FAMILIES = frozenset({
    "natural_gas",
    "refined_products",
    "copper",
    "gold",
    "grains_oilseeds",
    "softs",
    "livestock",
})
REFINED_PRODUCT_CODES = frozenset(
    {"WTI", "BRENT", "RBOB_US", "ULSD_US", "JET_US", "PROPANE_US"}
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
OUTPUT_INTEGER_COLUMNS = frozenset(
    {
        "attempts",
        "observations",
        "elapsed_ms",
        "sort_order",
        "valid_count",
        "positive_count",
        "flat_count",
        "negative_count",
        "up_count",
        "down_count",
        *RANK_COLUMNS,
    }
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
            ("eia_natural_gas", "commodity_fundamentals"),
            ("eia_refined_products", "commodity_fundamentals"),
            ("usda_psd", "commodity_fundamentals"),
            ("usda_esr", "commodity_fundamentals"),
        }
    ),
    "INSUFFICIENT_DATA": frozenset(
        {("fred_financial_conditions", "financial_conditions")}
    ),
    "POINT_IN_TIME_UNAVAILABLE": frozenset(
        {
            ("sec_company_events", "company_events"),
            ("fred_financial_conditions", "financial_conditions"),
            ("comex_copper_stocks", "commodity_fundamentals"),
            ("comex_gold_stocks", "commodity_fundamentals"),
            ("usgs_copper_structural", "commodity_fundamentals"),
            ("usgs_gold_structural", "commodity_fundamentals"),
        }
    ),
    "FETCH_FAILED": frozenset(
        {
            ("yahoo_volatility_signals", "financial_conditions"),
            ("comex_copper_stocks", "commodity_fundamentals"),
            ("comex_gold_stocks", "commodity_fundamentals"),
            ("usgs_copper_structural", "commodity_fundamentals"),
            ("usgs_gold_structural", "commodity_fundamentals"),
        }
    ),
}
CONTEXT_REQUIREDNESS_VALUES = frozenset({"required", "optional"})
ACCEPTED_QC_FLAGS = frozenset({"OK", "INSUFFICIENT_DATA"})
CALCULATED_SOURCE_POLICIES = {
    CALCULATED_SOURCE_REFERENCES["UST10Y2Y"]: (
        "series_code",
        ("UST10Y", "UST2Y"),
    ),
    CALCULATED_SOURCE_REFERENCES["US_BE5Y"]: (
        "series_code",
        ("UST5Y", "UST_REAL5Y"),
    ),
    CALCULATED_SOURCE_REFERENCES["US_BE10Y"]: (
        "series_code",
        ("UST10Y", "UST_REAL10Y"),
    ),
    CALCULATED_SOURCE_REFERENCES["US_5Y5Y"]: (
        "series_code",
        ("US_BE5Y", "US_BE10Y"),
    ),
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
    _dataset(
        "macro_assets",
        "commodity_price_history.csv",
        PRICE_HISTORY_FIELDS,
        require_exact_columns=True,
        date_columns=("as_of_date", "observation_date"),
        numeric_columns=("value",),
        source_url_column="source_url",
        qc_column="qc_flag",
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
            else ("freshness_days", "observations", "elapsed_ms", "attempts")
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
        if category not in {
            "commodity_metric_history",
            "commodity_research_facts",
        }
    ),
    _dataset(
        "weekly_context",
        "commodity_metric_history.csv",
        METRIC_HISTORY_FIELDS,
        require_exact_columns=True,
        date_columns=("as_of_date", "observation_date"),
        numeric_columns=("value",),
        source_url_column="source_url",
        qc_column="qc_flag",
    ),
    _dataset(
        "weekly_context",
        "commodity_research_facts.csv",
        RESEARCH_FACT_FIELDS,
        require_exact_columns=True,
        allow_empty=True,
        date_columns=("as_of_date", "observation_date"),
        numeric_columns=("value",),
        json_array_columns=("input_record_ids", "source_urls"),
        qc_column="qc_flag",
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
V2_ADDITIVE_DATASETS = frozenset(
    {
        ("macro_assets", "commodity_price_history.csv"),
        ("weekly_context", "commodity_metric_history.csv"),
        ("weekly_context", "commodity_research_facts.csv"),
    }
)
CONTRACT_TWO_RELEASE_DATASETS = tuple(
    dataset
    for dataset in RELEASE_DATASETS
    if (dataset.pipeline, dataset.filename) not in V2_ADDITIVE_DATASETS
)
LEGACY_RELEASE_DATASETS = tuple(
    replace(dataset, required_columns=LEGACY_CONTEXT_SOURCE_LOG_COLUMNS)
    if dataset.pipeline == "weekly_context" and dataset.filename == "source_log.csv"
    else dataset
    for dataset in CONTRACT_TWO_RELEASE_DATASETS
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
    if dataset_contract_version == COMPATIBILITY_DATASET_CONTRACT_VERSION:
        return CONTRACT_TWO_RELEASE_DATASETS
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
            "pipeline.indices",
            f"capital_weekly_equity_indices_python_{end_stamp}",
        ),
        (
            "equity_sectors",
            "pipeline.sectors",
            f"capital_weekly_equity_sectors_python_{end_stamp}",
        ),
        (
            "gics_sectors",
            "pipeline.gics",
            f"capital_weekly_gics_sectors_python_{end_stamp}",
        ),
        (
            "macro_assets",
            "pipeline.macro",
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
                    "-m",
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
                "-m",
                "pipeline.context",
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
    dataset_contract_version: int = COMPATIBILITY_DATASET_CONTRACT_VERSION,
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
    def resolve(
        candidate: dict[str, str],
        visiting: set[tuple[str, str]],
    ) -> str | None:
        value = (candidate.get(column) or "").strip()
        if _contains_http_url(value):
            return None
        policy = CALCULATED_SOURCE_POLICIES.get(value)
        provider_is_valid = (
            "provider" not in candidate
            or (candidate.get("provider") or "").strip().lower()
            == "calculated"
        )
        if not provider_is_valid or not policy:
            return "must contain an HTTP(S) URL or registered calculation reference"
        identity_column, dependencies = policy
        identity_value = (candidate.get(identity_column) or "").strip()
        identity = (identity_column, identity_value)
        if identity in visiting:
            return f"contains calculated dependency cycle: {identity_value or value}"
        visiting.add(identity)
        try:
            missing_dependencies = []
            for dependency in dependencies:
                dependency_row = next(
                    (
                        item
                        for item in rows
                        if (item.get(identity_column) or "").strip()
                        == dependency
                    ),
                    None,
                )
                if dependency_row is None or resolve(dependency_row, visiting):
                    missing_dependencies.append(dependency)
            if missing_dependencies:
                return (
                    "registered calculation is missing HTTP(S) dependencies: "
                    + ", ".join(missing_dependencies)
                )
            return None
        finally:
            visiting.remove(identity)

    return resolve(row, set())


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
        dataset_contract_version >= COMPATIBILITY_DATASET_CONTRACT_VERSION
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
        phase = (row.get("phase") or "").strip()
        if phase not in PROVIDER_PHASES:
            raise ReleaseValidationError(
                f"{path.name} row {row_number} has unsupported provider phase: "
                f"{phase or 'blank'}"
            )
        raw_attempts = (row.get("attempts") or "").strip()
        try:
            attempts = float(raw_attempts)
        except ValueError as error:
            raise ReleaseValidationError(
                f"{path.name} row {row_number} attempts must be a positive integer"
            ) from error
        if (
            not math.isfinite(attempts)
            or not attempts.is_integer()
            or attempts <= 0
        ):
            raise ReleaseValidationError(
                f"{path.name} row {row_number} attempts must be a positive integer"
            )
        status = (row.get("status") or "").strip().upper()
        if status == "OK":
            if phase != "normalized":
                raise ReleaseValidationError(
                    f"{path.name} row {row_number} successful provider phase "
                    "must be normalized"
                )
            if (row.get("error_code") or "").strip():
                raise ReleaseValidationError(
                    f"{path.name} row {row_number} successful provider error_code "
                    "must be blank"
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
            timestamp = datetime.fromisoformat(
                raw_timestamp[:-1] + "+00:00"
                if raw_timestamp.endswith("Z")
                else raw_timestamp
            )
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
    if spec.pipeline == "macro_assets" and spec.filename == "commodities.csv":
        raw_known_as_of = (row.get("known_as_of") or "").strip()
        if raw_known_as_of:
            try:
                known_as_of = datetime.fromisoformat(
                    raw_known_as_of[:-1] + "+00:00"
                    if raw_known_as_of.endswith("Z")
                    else raw_known_as_of
                )
            except ValueError as error:
                raise ReleaseValidationError(
                    f"{path.name} row {row_number} known_as_of must include a UTC offset"
                ) from error
            if known_as_of.tzinfo is None or known_as_of.utcoffset() is None:
                raise ReleaseValidationError(
                    f"{path.name} row {row_number} known_as_of must include a UTC offset"
                )
            if known_as_of.astimezone(HONG_KONG) > cutoff:
                raise ReleaseValidationError(
                    f"{path.name} row {row_number} known_as_of exceeds {window.end}"
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
    family = (row.get("commodity_family") or "").strip()
    commodity_code = (row.get("commodity_code") or "").strip()
    is_macro_commodity = (
        spec.pipeline == "macro_assets"
        and spec.filename == "commodities.csv"
        and (row.get("asset_class") or "").strip() == "commodity"
        and family != "digital_asset"
    )
    is_context_commodity = (
        spec.pipeline == "weekly_context"
        and spec.filename in {"commodity_fundamentals.csv", "positioning_flows.csv"}
        and any(
            (row.get(field) or "").strip()
            for field in (
                "commodity_code",
                "commodity_family",
                "metric_role",
                "measurement_kind",
                "participant_class",
                "known_as_of",
                "reference_period",
            )
        )
    )
    if not (is_macro_commodity or is_context_commodity):
        return
    if not commodity_code:
        raise ReleaseValidationError(
            f"{path.name} row {row_number} Commodity Research row requires commodity_code"
        )
    if family not in COMMODITY_RESEARCH_FAMILIES:
        raise ReleaseValidationError(
            f"{path.name} row {row_number} commodity_family is unsupported: {family or 'blank'}"
        )
    if family == "refined_products" and commodity_code not in REFINED_PRODUCT_CODES:
        raise ReleaseValidationError(
            f"{path.name} row {row_number} refined-products commodity_code "
            f"is unsupported: {commodity_code}"
        )
    if is_context_commodity:
        for field, allowed in (
            ("metric_role", METRIC_ROLE_VALUES),
            ("measurement_kind", MEASUREMENT_KIND_VALUES),
            ("participant_class", PARTICIPANT_CLASS_VALUES),
        ):
            value = (row.get(field) or "").strip()
            if value and value not in allowed:
                raise ReleaseValidationError(
                    f"{path.name} row {row_number} {field} is unsupported: {value}"
                )
        raw_known_as_of = (row.get("known_as_of") or "").strip()
        if raw_known_as_of:
            try:
                known_as_of = datetime.fromisoformat(
                    raw_known_as_of[:-1] + "+00:00"
                    if raw_known_as_of.endswith("Z")
                    else raw_known_as_of
                )
            except ValueError as error:
                raise ReleaseValidationError(
                    f"{path.name} row {row_number} known_as_of must include a UTC offset"
                ) from error
            if known_as_of.tzinfo is None or known_as_of.utcoffset() is None:
                raise ReleaseValidationError(
                    f"{path.name} row {row_number} known_as_of must include a UTC offset"
                )
            if known_as_of.astimezone(HONG_KONG) > cutoff:
                raise ReleaseValidationError(
                    f"{path.name} row {row_number} known_as_of exceeds {window.end}"
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
    dataset_contract_version: int = COMPATIBILITY_DATASET_CONTRACT_VERSION,
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
    validated_rows: dict[tuple[str, str], list[dict[str, str]]] = {}
    for dataset in release_datasets_for_contract(dataset_contract_version):
        path = pipeline_dirs[dataset.pipeline] / dataset.filename
        rows = _read_dataset(path, dataset)
        validated_rows[(dataset.pipeline, dataset.filename)] = rows
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
    if dataset_contract_version >= COMPATIBILITY_DATASET_CONTRACT_VERSION:
        _validate_usda_agriculture_coverage(validated_rows)
        _validate_eia_physical_coverage(validated_rows)
        _validate_configured_commodity_coverage(validated_rows, window)
    if dataset_contract_version == DATASET_CONTRACT_VERSION:
        _validate_commodity_research_v2(validated_rows, window)
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


def _configured_rows(
    section: str,
    *,
    identity_field: str,
    required_fields: tuple[str, ...],
    include: Callable[[dict], bool] | None = None,
) -> list[dict[str, str]]:
    configured: list[dict[str, str]] = []
    identities: set[str] = set()
    for raw_row in load_config_rows(section):
        if include is not None and not include(raw_row):
            continue
        row = {field: str(raw_row.get(field) or "").strip() for field in required_fields}
        missing = [field for field, value in row.items() if not value]
        if missing:
            raise ReleaseValidationError(
                f"{section} configured coverage requires " + ", ".join(missing)
            )
        identity = row[identity_field]
        if identity in identities:
            raise ReleaseValidationError(
                f"{section} configured coverage has duplicate {identity_field}: "
                f"{identity}"
            )
        identities.add(identity)
        configured.append(row)
    return configured


def _configured_metal_rows() -> list[dict]:
    configured: list[dict] = []
    providers: set[str] = set()
    scalar_fields = (
        "provider",
        "source",
        "source_url",
        "commodity_code",
        "commodity_family",
    )
    for raw_row in load_config_rows("context.metals"):
        row = {
            field: str(raw_row.get(field) or "").strip()
            for field in scalar_fields
        }
        missing = [field for field, value in row.items() if not value]
        raw_codes = raw_row.get("expected_metric_codes")
        if isinstance(raw_codes, str):
            try:
                raw_codes = json.loads(raw_codes)
            except json.JSONDecodeError as error:
                raise ReleaseValidationError(
                    "context.metals expected_metric_codes must be a JSON array"
                ) from error
        if not isinstance(raw_codes, list):
            missing.append("expected_metric_codes")
            metric_codes: list[str] = []
        else:
            metric_codes = [str(value or "").strip() for value in raw_codes]
            if not metric_codes or any(not value for value in metric_codes):
                missing.append("expected_metric_codes")
        raw_observations = str(raw_row.get("expected_observations") or "").strip()
        if not raw_observations:
            missing.append("expected_observations")
        if missing:
            raise ReleaseValidationError(
                "context.metals configured coverage requires "
                + ", ".join(sorted(set(missing)))
            )
        provider = row["provider"]
        if provider in providers:
            raise ReleaseValidationError(
                f"context.metals configured coverage has duplicate provider: {provider}"
            )
        providers.add(provider)
        if len(metric_codes) != len(set(metric_codes)):
            raise ReleaseValidationError(
                f"{provider} expected_metric_codes must be unique"
            )
        try:
            expected_observations = int(raw_observations)
        except ValueError as error:
            raise ReleaseValidationError(
                f"{provider} expected_observations must be an integer"
            ) from error
        if expected_observations <= 0 or expected_observations != len(metric_codes):
            raise ReleaseValidationError(
                f"{provider} expected_observations must equal expected_metric_codes"
            )
        configured.append(
            {
                **row,
                "expected_metric_codes": tuple(metric_codes),
                "expected_observations": expected_observations,
            }
        )
    return configured


def _require_unique_context_status(
    source_rows: list[dict[str, str]],
    provider: str,
) -> dict[str, str]:
    matches = [
        row
        for row in source_rows
        if (row.get("provider") or "").strip() == provider
    ]
    if not matches:
        raise ReleaseValidationError(
            f"configured provider status missing for {provider}"
        )
    if len(matches) != 1:
        raise ReleaseValidationError(
            f"configured provider status must be unique for {provider}"
        )
    return matches[0]


def _usable_business_value(
    row: dict[str, str],
    window: WeekWindow,
    *,
    date_column: str,
    value_column: str,
) -> bool:
    if (row.get("qc_flag") or "").strip().upper() != "OK":
        return False
    raw_date = (row.get(date_column) or "").strip()
    raw_value = (row.get(value_column) or "").strip()
    if not raw_date or not raw_value:
        return False
    try:
        observation_date = date.fromisoformat(raw_date)
        value = float(raw_value)
    except ValueError:
        return False
    return observation_date <= window.end and math.isfinite(value)


def _official_host(source_url: str, domain: str) -> bool:
    host = (urlparse(source_url).hostname or "").lower()
    return host == domain or host.endswith(f".{domain}")


def _validate_configured_commodity_coverage(
    datasets: dict[tuple[str, str], list[dict[str, str]]],
    window: WeekWindow,
) -> None:
    price_rows = datasets.get(("macro_assets", "commodities.csv"), [])
    macro_source_rows = datasets.get(("macro_assets", "source_log.csv"), [])
    context_source_rows = datasets.get(("weekly_context", "source_log.csv"), [])
    fundamental_rows = datasets.get(
        ("weekly_context", "commodity_fundamentals.csv"),
        [],
    )
    positioning_rows = datasets.get(
        ("weekly_context", "positioning_flows.csv"),
        [],
    )

    macro_config = _configured_rows(
        "macro",
        identity_field="series_code",
        required_fields=(
            "series_code",
            "provider",
            "commodity_code",
            "commodity_family",
            "price_kind",
        ),
        include=lambda row: (
            str(row.get("asset_class") or "").strip() == "commodity"
            and str(row.get("commodity_family") or "").strip()
            in COMMODITY_RESEARCH_FAMILIES
        ),
    )
    if not macro_config:
        raise ReleaseValidationError("configured macro commodity coverage is empty")
    for expected in macro_config:
        series_code = expected["series_code"]
        matches = [
            row
            for row in price_rows
            if (row.get("series_code") or "").strip() == series_code
        ]
        exact = [
            row
            for row in matches
            if all(
                (row.get(field) or "").strip() == expected[field]
                for field in (
                    "provider",
                    "commodity_code",
                    "commodity_family",
                    "price_kind",
                )
            )
            and (row.get("asset_class") or "").strip() == "commodity"
            and (
                expected["provider"] != "world_bank_pink_sheet"
                or _official_host(
                    (row.get("source_url") or "").strip(),
                    "worldbank.org",
                )
            )
            and (
                expected["provider"] != "eia_v2"
                or _official_host(
                    (row.get("source_url") or "").strip(),
                    "eia.gov",
                )
            )
            and _usable_business_value(
                row,
                window,
                date_column="latest_date",
                value_column="latest_value",
            )
        ]
        if len(matches) != 1 or len(exact) != 1:
            raise ReleaseValidationError(
                f"configured macro price missing, duplicated, or mismapped: {series_code}"
            )
        status_matches = [
            row
            for row in macro_source_rows
            if (row.get("series_code") or "").strip() == series_code
        ]
        if (
            len(status_matches) != 1
            or (status_matches[0].get("status") or "").strip().upper() != "OK"
        ):
            raise ReleaseValidationError(
                f"configured macro source status missing, duplicated, or not OK: "
                f"{series_code}"
            )

    cftc_config = _configured_rows(
        "context.cftc_contracts",
        identity_field="contract_code",
        required_fields=(
            "contract_code",
            "market_name",
            "report_family",
            "commodity_code",
            "commodity_family",
        ),
        include=lambda row: bool(str(row.get("commodity_code") or "").strip()),
    )
    cftc_by_provider: dict[str, list[dict[str, str]]] = {}
    for expected in cftc_config:
        provider = f"cftc_{expected['report_family']}"
        cftc_by_provider.setdefault(provider, []).append(expected)
    for provider, contracts in cftc_by_provider.items():
        status_row = _require_unique_context_status(context_source_rows, provider)
        if (
            (status_row.get("status") or "").strip().upper() != "OK"
            or (status_row.get("requiredness") or "").strip() != "required"
        ):
            raise ReleaseValidationError(f"{provider} must be required and OK")
        for expected in contracts:
            code = expected["commodity_code"]
            family = expected["commodity_family"]
            open_interest = [
                row
                for row in positioning_rows
                if (row.get("market") or "").strip() == expected["market_name"]
                and (row.get("commodity_code") or "").strip() == code
                and (row.get("commodity_family") or "").strip() == family
                and (row.get("metric_role") or "").strip() == "positioning"
                and (row.get("metric_code") or "").strip()
                == f"{code}_open_interest"
                and (row.get("measurement_kind") or "").strip()
                == "open_interest"
                and (row.get("source") or "").strip()
                == "U.S. Commodity Futures Trading Commission"
                and _official_host(
                    (row.get("source_url") or "").strip(),
                    "cftc.gov",
                )
                and _usable_business_value(
                    row,
                    window,
                    date_column="as_of_date",
                    value_column="value",
                )
            ]
            if len(open_interest) != 1:
                raise ReleaseValidationError(
                    f"{provider} CFTC contract identity missing, duplicated, or "
                    f"mismapped: "
                    f"{expected['contract_code']} / {code} / {family}"
                )

    eia_config = _configured_rows(
        "context.eia_series",
        identity_field="metric_code",
        required_fields=(
            "provider",
            "metric_code",
            "commodity_code",
            "commodity_family",
        ),
    )
    eia_by_provider: dict[str, list[dict[str, str]]] = {}
    for expected in eia_config:
        eia_by_provider.setdefault(expected["provider"], []).append(expected)
    for provider, metrics in eia_by_provider.items():
        status_row = _require_unique_context_status(context_source_rows, provider)
        status = (status_row.get("status") or "").strip().upper()
        requiredness = (status_row.get("requiredness") or "").strip()
        configured_metric_codes = {row["metric_code"] for row in metrics}
        provider_rows = [
            row
            for row in fundamental_rows
            if any(
                (row.get("metric_code") or "").strip() == metric_code
                or (row.get("metric_code") or "").strip().startswith(
                    f"{metric_code}_"
                )
                for metric_code in configured_metric_codes
            )
        ]
        if status == "NOT_CONFIGURED":
            if requiredness != "optional" or provider_rows:
                raise ReleaseValidationError(
                    f"{provider} NOT_CONFIGURED must be optional with no base or "
                    "derived rows"
                )
            continue
        if status != "OK" or requiredness != "required":
            raise ReleaseValidationError(f"{provider} must be required and OK")
        for expected in metrics:
            metric_code = expected["metric_code"]
            exact = [
                row
                for row in fundamental_rows
                if (row.get("metric_code") or "").strip() == metric_code
                and (row.get("commodity_code") or "").strip()
                == expected["commodity_code"]
                and (row.get("commodity_family") or "").strip()
                == expected["commodity_family"]
                and (row.get("metric_role") or "").strip()
                == "physical_fundamental"
                and _usable_business_value(
                    row,
                    window,
                    date_column="as_of_date",
                    value_column="value",
                )
            ]
            if len(exact) != 1:
                raise ReleaseValidationError(
                    f"{provider} missing, duplicated, or mismapped configured metric: "
                    f"{metric_code}"
                )

    metals_config = _configured_metal_rows()
    for expected in metals_config:
        provider = expected["provider"]
        status_row = _require_unique_context_status(
            context_source_rows,
            provider,
        )
        if (status_row.get("requiredness") or "").strip() != "optional":
            raise ReleaseValidationError(
                f"supplemental provider {provider} must be optional"
            )
        if (
            (status_row.get("source") or "").strip() != expected["source"]
            or (status_row.get("source_url") or "").strip()
            != expected["source_url"]
        ):
            raise ReleaseValidationError(
                f"supplemental provider {provider} status provenance is mismapped"
            )
        code = expected["commodity_code"]
        family = expected["commodity_family"]
        expected_metric_codes = set(expected["expected_metric_codes"])
        identity_rows = [
            row
            for row in fundamental_rows
            if (row.get("metric_code") or "").strip() in expected_metric_codes
        ]
        provider_rows = [
            row
            for row in fundamental_rows
            if (
                (row.get("metric_code") or "").strip() in expected_metric_codes
                or (
                    (row.get("source") or "").strip() == expected["source"]
                    and (row.get("source_url") or "").strip()
                    == expected["source_url"]
                )
            )
        ]
        raw_observations = (status_row.get("observations") or "").strip()
        try:
            status_observations = int(raw_observations)
        except ValueError as error:
            raise ReleaseValidationError(
                f"{provider} source-log observations must be an integer"
            ) from error
        status = (status_row.get("status") or "").strip().upper()
        if status != "OK":
            if status_observations != 0:
                raise ReleaseValidationError(
                    f"{provider} {status} source-log observations must be zero"
                )
            if provider_rows:
                raise ReleaseValidationError(
                    f"{provider} {status} requires zero attributed provider rows"
                )
            continue
        expected_observations = expected["expected_observations"]
        if (
            status_observations != expected_observations
            or status_observations != len(provider_rows)
        ):
            raise ReleaseValidationError(
                f"{provider} source-log observations must equal configured and "
                "business row counts"
            )
        actual_metric_codes = [
            (row.get("metric_code") or "").strip() for row in provider_rows
        ]
        if (
            len(provider_rows) != expected_observations
            or len(identity_rows) != expected_observations
            or set(actual_metric_codes) != expected_metric_codes
            or any(
                actual_metric_codes.count(metric_code) != 1
                for metric_code in expected_metric_codes
            )
        ):
            raise ReleaseValidationError(
                f"{provider} OK requires complete business rows and exact metric "
                "identities exactly once"
            )
        exact_rows = [
            row
            for row in provider_rows
            if (row.get("commodity_code") or "").strip() == code
            and (row.get("commodity_family") or "").strip() == family
            and (row.get("source") or "").strip() == expected["source"]
            and (row.get("source_url") or "").strip() == expected["source_url"]
            and (row.get("metric_role") or "").strip()
            == "physical_fundamental"
            and _usable_business_value(
                row,
                window,
                date_column="as_of_date",
                value_column="value",
            )
        ]
        if len(exact_rows) != len(provider_rows):
            raise ReleaseValidationError(
                f"{provider} business rows must map to {code} / {family}"
            )


def _validate_eia_physical_coverage(
    datasets: dict[tuple[str, str], list[dict[str, str]]],
) -> None:
    source_rows = datasets.get(("weekly_context", "source_log.csv"), [])
    fundamental_rows = datasets.get(
        ("weekly_context", "commodity_fundamentals.csv"),
        [],
    )
    provider_families = {
        "eia_natural_gas": ("natural_gas", "https://api.eia.gov/v2/natural-gas/"),
        "eia_refined_products": (
            "refined_products",
            "https://api.eia.gov/v2/petroleum/",
        ),
    }
    for provider, (family, source_url_prefix) in provider_families.items():
        active = any(
            (row.get("provider") or "").strip() == provider
            and (row.get("status") or "").strip().upper() == "OK"
            for row in source_rows
        )
        if not active:
            continue
        covered = any(
            (row.get("commodity_family") or "").strip() == family
            and (row.get("metric_role") or "").strip()
            == "physical_fundamental"
            and (row.get("measurement_kind") or "").strip()
            in MEASUREMENT_KIND_VALUES
            and (row.get("source") or "").strip()
            == "U.S. Energy Information Administration"
            and (row.get("source_url") or "").strip().startswith(source_url_prefix)
            for row in fundamental_rows
        )
        if not covered:
            raise ReleaseValidationError(
                f"{provider} has no official EIA physical fundamental row "
                f"for active family {family}"
            )


def _validate_usda_agriculture_coverage(
    datasets: dict[tuple[str, str], list[dict[str, str]]],
) -> None:
    source_rows = datasets.get(("weekly_context", "source_log.csv"), [])
    fundamental_rows = datasets.get(
        ("weekly_context", "commodity_fundamentals.csv"),
        [],
    )
    configured: dict[str, dict[str, str]] = {}
    for provider in ("usda_psd", "usda_esr"):
        mapping: dict[str, str] = {}
        for row in load_config_rows(f"context.{provider}"):
            code = str(row.get("commodity_code") or "").strip()
            family = str(row.get("commodity_family") or "").strip()
            if not code or not family:
                raise ReleaseValidationError(
                    f"{provider} configured coverage requires code and family"
                )
            if code in mapping:
                raise ReleaseValidationError(
                    f"{provider} configured coverage has duplicate code: {code}"
                )
            mapping[code] = family
        if not mapping:
            raise ReleaseValidationError(
                f"{provider} configured coverage must not be empty"
            )
        configured[provider] = mapping
    provider_rows = {
        provider: [
            row
            for row in source_rows
            if (row.get("provider") or "").strip() == provider
        ]
        for provider in configured
    }
    missing_statuses = [
        provider for provider, rows in provider_rows.items() if not rows
    ]
    if missing_statuses:
        raise ReleaseValidationError(
            "USDA agriculture capability status missing for: "
            + ", ".join(sorted(missing_statuses))
        )
    duplicate_statuses = [
        provider for provider, rows in provider_rows.items() if len(rows) != 1
    ]
    if duplicate_statuses:
        raise ReleaseValidationError(
            "USDA agriculture capability status must be unique for: "
            + ", ".join(sorted(duplicate_statuses))
        )
    statuses = {
        provider: (rows[0].get("status") or "").strip().upper()
        for provider, rows in provider_rows.items()
    }
    if len(set(statuses.values())) != 1:
        raise ReleaseValidationError(
            "USDA PSD and ESR capability statuses must reflect the same key state"
        )
    for provider, expected_mapping in configured.items():
        expected_codes = frozenset(expected_mapping)
        source_row = provider_rows[provider][0]
        status = statuses[provider]
        requiredness = (source_row.get("requiredness") or "").strip()
        provider_prefix = f"{provider}_"
        rows = [
            row
            for row in fundamental_rows
            if (row.get("metric_code") or "").strip().startswith(provider_prefix)
        ]
        if status == "NOT_CONFIGURED":
            if requiredness != "optional" or rows:
                raise ReleaseValidationError(
                    f"{provider} NOT_CONFIGURED must be optional with no rows"
                )
            continue
        if status != "OK" or requiredness != "required":
            raise ReleaseValidationError(
                f"{provider} configured capability must be required and OK"
            )
        actual_codes = {(row.get("commodity_code") or "").strip() for row in rows}
        unknown_codes = sorted(actual_codes - expected_codes)
        if unknown_codes:
            raise ReleaseValidationError(
                f"{provider} has unconfigured commodity_code: "
                + ", ".join(unknown_codes)
            )
        missing_codes = sorted(expected_codes - actual_codes)
        if missing_codes:
            raise ReleaseValidationError(
                f"{provider} missing configured commodity_code rows: "
                + ", ".join(missing_codes)
            )
        for row in rows:
            code = (row.get("commodity_code") or "").strip()
            family = (row.get("commodity_family") or "").strip()
            expected_family = expected_mapping[code]
            if family != expected_family:
                raise ReleaseValidationError(
                    f"{provider} {code} commodity_family must be {expected_family}"
                )
            source = (row.get("source") or "").strip()
            source_url = (row.get("source_url") or "").strip()
            host = (urlparse(source_url).hostname or "").lower()
            if (
                source != "USDA Foreign Agricultural Service"
                or host != "api.fas.usda.gov"
            ):
                raise ReleaseValidationError(
                    "USDA row requires official FAS provenance"
                )


def _research_validation_config() -> dict:
    try:
        document = json.loads(
            Path(common_config.DEFAULT_CONFIG_PATH).read_text(encoding="utf-8")
        )
        research = document["commodity_research"]
        raw_universe = research["universe"]
        raw_limits = research["history_limits"]
        raw_metric_registry = research["metric_registry"]
        raw_providers = research["providers"]
        raw_facts = research["facts"]
        macro_rows = document["macro"]
        context = document["context"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise ReleaseValidationError(
            "Commodity Research V2 validation config is incomplete"
        ) from error
    if not isinstance(raw_universe, list):
        raise ReleaseValidationError(
            "commodity_research.universe must be an exact row list"
        )
    universe_mapping: dict[str, object] = {}
    duplicate_codes: set[str] = set()
    for row in raw_universe:
        if not isinstance(row, dict) or set(row) != {
            "commodity_code",
            "commodity_family",
        }:
            raise ReleaseValidationError(
                "commodity_research.universe rows must declare exact fields"
            )
        code = str(row.get("commodity_code") or "").strip()
        if code in universe_mapping:
            duplicate_codes.add(code)
        universe_mapping[code] = row.get("commodity_family")
    if len(raw_universe) != 19 or duplicate_codes:
        detail = (
            "; duplicate commodity_code: " + ", ".join(sorted(duplicate_codes))
            if duplicate_codes
            else ""
        )
        raise ReleaseValidationError(
            "commodity_research.universe must declare exact 19 unique rows"
            + detail
        )
    try:
        registry = validate_commodity_registry(universe_mapping)
        limits = validate_history_limits(raw_limits)
    except (TypeError, ValueError) as error:
        raise ReleaseValidationError(str(error)) from error
    if len(registry) != 19 or set(registry.values()) != set(COMMODITY_RESEARCH_FAMILIES):
        raise ReleaseValidationError(
            "commodity_research.universe must declare exact 19-code seven-family coverage"
        )
    provider_fields = {
        "provider",
        "dataset",
        "source",
        "official_host",
        "frequency",
        "measurement_kind",
        "source_url_path_prefix",
    }
    if not isinstance(raw_providers, list) or not raw_providers:
        raise ReleaseValidationError(
            "commodity_research.providers must be a nonempty row list"
        )
    providers: dict[str, dict[str, str]] = {}
    for raw in raw_providers:
        if not isinstance(raw, dict) or set(raw) != provider_fields:
            raise ReleaseValidationError(
                "commodity_research provider must declare exact validation fields"
            )
        row = {field: str(raw.get(field) or "").strip() for field in provider_fields}
        if any(not value for value in row.values()):
            raise ReleaseValidationError(
                "commodity_research provider validation fields must not be blank"
            )
        provider = row["provider"]
        if provider in providers:
            raise ReleaseValidationError(
                f"Duplicate commodity_research provider: {provider}"
            )
        if row["dataset"] not in {"price_history", "metric_history"}:
            raise ReleaseValidationError(
                f"Unsupported commodity research provider dataset: {row['dataset']}"
            )
        host = row["official_host"].lower()
        if host != row["official_host"] or not re.fullmatch(r"[a-z0-9.-]+", host):
            raise ReleaseValidationError(
                f"Invalid official host for commodity provider {provider}"
            )
        if row["frequency"] != "configured" and row["frequency"] not in limits:
            raise ReleaseValidationError(
                f"Invalid frequency for commodity provider {provider}"
            )
        if row["measurement_kind"] not in {
            "configured",
            *MEASUREMENT_KIND_VALUES,
        }:
            raise ReleaseValidationError(
                f"Invalid measurement kind for commodity provider {provider}"
            )
        if not row["source_url_path_prefix"].startswith("/"):
            raise ReleaseValidationError(
                f"Invalid source URL path prefix for commodity provider {provider}"
            )
        providers[provider] = row
    if not isinstance(raw_facts, list) or len(raw_facts) != 8:
        raise ReleaseValidationError(
            "commodity_research.facts must declare exact eight registered facts"
        )
    try:
        formula_specs = load_formula_specs(common_config.DEFAULT_CONFIG_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ReleaseValidationError(str(error)) from error
    return {
        "document": document,
        "registry": registry,
        "limits": limits,
        "providers": providers,
        "metric_registry": raw_metric_registry,
        "formula_specs": formula_specs,
        "fact_rows": {row["fact_code"]: row for row in raw_facts},
        "macro_rows": macro_rows,
        "context": context,
    }


def _required_row_text(row: dict, field: str, label: str) -> str:
    value = row.get(field)
    normalized = str(value or "").strip()
    if not normalized:
        raise ReleaseValidationError(f"{label} {field} must not be blank")
    return normalized


def _finite_row_value(row: dict, label: str) -> float | int:
    value = row.get("value")
    if isinstance(value, bool):
        raise ReleaseValidationError(f"{label} value must be finite")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise ReleaseValidationError(f"{label} value must be finite") from error
    if not math.isfinite(numeric):
        raise ReleaseValidationError(f"{label} value must be finite")
    return int(numeric) if numeric.is_integer() else numeric


def _canonical_v2_known_as_of(
    value: object,
    window: WeekWindow,
    label: str,
) -> tuple[datetime | None, str | None]:
    if value is None or not str(value).strip():
        return None, None
    raw = str(value).strip()
    if not raw.endswith("Z"):
        raise ReleaseValidationError(f"{label} known_as_of must use canonical UTC Z")
    try:
        known = datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError as error:
        raise ReleaseValidationError(
            f"{label} known_as_of must use canonical UTC Z"
        ) from error
    canonical = known.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
    if canonical != raw:
        raise ReleaseValidationError(f"{label} known_as_of must use canonical UTC Z")
    if known > target_sunday_cutoff(window.end):
        raise ReleaseValidationError(f"{label} known_as_of exceeds target Sunday cutoff")
    return known, raw


def _v2_observation_date(row: dict, window: WeekWindow, label: str) -> date:
    raw = _required_row_text(row, "observation_date", label)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raise ReleaseValidationError(f"{label} observation_date must be canonical")
    try:
        observation = date.fromisoformat(raw)
    except ValueError as error:
        raise ReleaseValidationError(
            f"{label} observation_date must be canonical"
        ) from error
    if observation > window.end:
        raise ReleaseValidationError(f"{label} observation_date exceeds as_of_date")
    return observation


def _validate_v2_record_id(
    row: dict,
    *,
    namespace: str,
    identity: dict,
    label: str,
) -> str:
    record_id = _required_row_text(row, "record_id", label)
    expected = stable_record_id(namespace, identity)
    if not re.fullmatch(r"[0-9a-f]{64}", record_id) or record_id != expected:
        raise ReleaseValidationError(
            f"record_id does not match {label} identity ({namespace})"
        )
    return record_id


def _policy_matches_url(policy: dict[str, str], source_url: str) -> bool:
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower()
    official = policy["official_host"]
    return (
        parsed.scheme.lower() in {"http", "https"}
        and (host == official or host.endswith(f".{official}"))
        and parsed.path.startswith(policy["source_url_path_prefix"])
    )


def _require_policy_provenance(
    row: dict,
    policy: dict[str, str],
    label: str,
) -> str:
    source = _required_row_text(row, "source", label)
    source_url = _required_row_text(row, "source_url", label)
    if source != policy["source"]:
        raise ReleaseValidationError(
            f"{label} source must match provider {policy['provider']}"
        )
    if not _policy_matches_url(policy, source_url):
        raise ReleaseValidationError(
            f"{label} official source host/path must match "
            f"{policy['official_host']}{policy['source_url_path_prefix']}"
        )
    return source_url


def _context_status_index(rows: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for row in rows:
        provider = str(row.get("provider") or "").strip()
        if provider in index:
            raise ReleaseValidationError(
                f"configured provider status must be unique for {provider}"
            )
        index[provider] = row
    return index


def _validate_context_provider_statuses(
    statuses: dict[str, dict],
    providers: dict[str, dict[str, str]],
    business_counts: dict[str, int],
) -> None:
    for provider, policy in providers.items():
        if policy["dataset"] != "metric_history":
            continue
        row = statuses.get(provider)
        if row is None:
            raise ReleaseValidationError(
                f"{provider} configured provider status is missing"
            )
        expected = business_counts.get(provider, 0)
        _validate_provider_status(row, policy, expected, provider)


def _validate_provider_status(
    row: dict,
    policy: dict[str, str],
    expected: int,
    label: str,
    rows_label: str = "business rows",
    observation_limit: int | None = None,
    frequency: str | None = None,
) -> None:
    source = str(row.get("source") or "").strip()
    source_url = str(row.get("source_url") or "").strip()
    parsed_url = urlparse(source_url)
    status_host = (parsed_url.hostname or "").lower()
    official_host = policy["official_host"]
    if (
        source != policy["source"]
        or parsed_url.scheme not in {"http", "https"}
        or not (
            status_host == official_host
            or status_host.endswith(f".{official_host}")
        )
    ):
        raise ReleaseValidationError(
            f"{label} status provenance must match configured source and official host"
        )
    raw_observations = row.get("observations")
    if isinstance(raw_observations, bool):
        observations = None
    elif isinstance(raw_observations, int) and raw_observations >= 0:
        observations = raw_observations
    elif isinstance(raw_observations, str) and re.fullmatch(
        r"(?:0|[1-9][0-9]*)",
        raw_observations,
    ):
        observations = int(raw_observations)
    else:
        observations = None
    if observations is None:
        raise ReleaseValidationError(
            f"{label} status observations must be a canonical integer"
        )
    status = str(row.get("status") or "").strip().upper()
    if observation_limit is not None:
        if status != "OK":
            if observations != 0 or expected != 0:
                raise ReleaseValidationError(
                    f"{label} non-OK status requires zero raw observations and "
                    f"zero published {rows_label}: raw {observations}, "
                    f"published {expected}"
                )
            return
        if observations <= 0:
            raise ReleaseValidationError(
                f"{label} OK status observations must be a positive canonical "
                f"integer: got {observations}"
            )
        bounded_expected = min(observations, observation_limit)
        if expected != bounded_expected:
            raise ReleaseValidationError(
                f"{label} bounded price history {frequency or 'configured'} limit "
                f"{observation_limit} count mismatch: raw {observations}, "
                f"expected {bounded_expected}, published {expected}"
            )
        return
    if observations != expected:
        raise ReleaseValidationError(
            f"{label} status observations must equal attributed {rows_label}: "
            f"expected {expected}, got {observations}"
        )
    if status != "OK" and expected != 0:
        raise ReleaseValidationError(
            f"{label} requires zero {rows_label} while status is {status}"
        )


def _metric_descriptors(config: dict) -> dict:
    providers = config["providers"]
    registry = config["registry"]
    context = config["context"]
    configured = config["metric_registry"]
    if not isinstance(configured, dict) or set(configured) != {
        "eia_variants",
        "cftc_variants",
        "usda_psd",
        "usda_esr",
    }:
        raise ReleaseValidationError(
            "commodity_research.metric_registry must declare exact sections"
        )
    descriptors: dict[str, dict] = {}

    def register(metric_code: str, descriptor: dict) -> None:
        existing = descriptors.get(metric_code)
        if existing is not None and existing != descriptor:
            raise ReleaseValidationError(
                f"Configured metric identity is ambiguous: {metric_code}"
            )
        descriptors[metric_code] = descriptor

    eia_variants = configured["eia_variants"]
    if not isinstance(eia_variants, list) or not eia_variants:
        raise ReleaseValidationError(
            "commodity_research metric registry EIA variants are invalid"
        )
    normalized_eia: list[dict[str, str]] = []
    seen_eia_suffixes: set[str] = set()
    for raw in eia_variants:
        if not isinstance(raw, dict) or set(raw) != {
            "suffix",
            "unit",
            "metric_role",
        }:
            raise ReleaseValidationError(
                "commodity_research EIA metric variant fields are invalid"
            )
        suffix = str(raw["suffix"])
        unit = str(raw["unit"] or "").strip()
        role = str(raw["metric_role"] or "").strip()
        if (
            suffix in seen_eia_suffixes
            or not re.fullmatch(r"(?:|_[a-z0-9_]+)", suffix)
            or not unit
            or role not in METRIC_ROLE_VALUES
        ):
            raise ReleaseValidationError(
                "commodity_research EIA metric variant is invalid"
            )
        seen_eia_suffixes.add(suffix)
        normalized_eia.append({"suffix": suffix, "unit": unit, "metric_role": role})

    for item in context["eia_series"]:
        provider = str(item["provider"])
        if provider not in providers:
            raise ReleaseValidationError(f"Missing provider policy for {provider}")
        base = str(item["metric_code"])
        for variant in normalized_eia:
            unit = (
                str(item["expected_unit"])
                if variant["unit"] == "configured"
                else variant["unit"]
            )
            register(base + variant["suffix"], {
                "provider": provider,
                "frequency": str(item["frequency"]),
                "commodity_code": str(item["commodity_code"]),
                "commodity_family": str(item["commodity_family"]),
                "metric_role": variant["metric_role"],
                "measurement_kind": str(item["measurement_kind"]),
                "participant_class": None,
                "unit": unit,
            })

    cftc_variants = configured["cftc_variants"]
    if not isinstance(cftc_variants, list) or not cftc_variants:
        raise ReleaseValidationError(
            "commodity_research metric registry CFTC variants are invalid"
        )
    normalized_cftc: list[dict] = []
    cftc_fields = {
        "provider",
        "suffix",
        "metric_role",
        "measurement_kind",
        "participant_class",
        "unit",
        "frequency",
    }
    seen_cftc_suffixes: set[str] = set()
    for raw in cftc_variants:
        if not isinstance(raw, dict) or set(raw) != cftc_fields:
            raise ReleaseValidationError(
                "commodity_research CFTC metric variant fields are invalid"
            )
        row = dict(raw)
        provider = str(row["provider"] or "").strip()
        suffix = str(row["suffix"] or "").strip()
        role = str(row["metric_role"] or "").strip()
        kind = str(row["measurement_kind"] or "").strip()
        participant = row["participant_class"]
        participant = str(participant).strip() if participant is not None else None
        unit = str(row["unit"] or "").strip()
        frequency = str(row["frequency"] or "").strip()
        if (
            provider not in providers
            or suffix in seen_cftc_suffixes
            or not re.fullmatch(r"[a-z0-9_]+", suffix)
            or role not in METRIC_ROLE_VALUES
            or kind not in MEASUREMENT_KIND_VALUES
            or (
                participant is not None
                and participant not in PARTICIPANT_CLASS_VALUES
            )
            or not unit
            or frequency not in config["limits"]
        ):
            raise ReleaseValidationError(
                "commodity_research CFTC metric variant is invalid"
            )
        seen_cftc_suffixes.add(suffix)
        normalized_cftc.append({
            "provider": provider,
            "suffix": suffix,
            "metric_role": role,
            "measurement_kind": kind,
            "participant_class": participant,
            "unit": unit,
            "frequency": frequency,
        })
    for contract in context["cftc_contracts"]:
        code = str(contract.get("commodity_code") or "").strip()
        if not code:
            continue
        family = str(contract.get("commodity_family") or "").strip()
        if registry.get(code) != family:
            raise ReleaseValidationError(
                f"Configured CFTC code-family mismatch: {code}"
            )
        for variant in normalized_cftc:
            register(f"{code}_{variant['suffix']}", {
                "provider": variant["provider"],
                "frequency": variant["frequency"],
                "commodity_code": code,
                "commodity_family": family,
                "metric_role": variant["metric_role"],
                "measurement_kind": variant["measurement_kind"],
                "participant_class": variant["participant_class"],
                "unit": variant["unit"],
            })

    for item in context["metals"]:
        provider = str(item["provider"])
        policy = providers.get(provider)
        if policy is None or policy["measurement_kind"] == "configured":
            raise ReleaseValidationError(
                f"Configured metal provider requires an exact measurement kind: {provider}"
            )
        kind = policy["measurement_kind"]
        for metric_code in item["expected_metric_codes"]:
            register(str(metric_code), {
                "provider": provider,
                "frequency": str(item["frequency"]),
                "commodity_code": str(item["commodity_code"]),
                "commodity_family": str(item["commodity_family"]),
                "metric_role": "physical_fundamental",
                "measurement_kind": kind,
                "participant_class": None,
                "unit": str(item["expected_unit"]),
            })
    usda_registry: dict[str, dict] = {}
    for section, expected_groups in (
        ("usda_psd", {"commodity", "country", "market_year", "metric"}),
        ("usda_esr", {"commodity", "market_year", "metric"}),
    ):
        raw = configured[section]
        section_fields = {
            "provider",
            "metric_role",
            "frequency",
            "metric_code_pattern",
            "metrics",
        }
        section_fields |= (
            {"country_identifiers", "reference_period"}
            if section == "usda_psd"
            else {"market", "reference_period"}
        )
        if not isinstance(raw, dict) or set(raw) != section_fields:
            raise ReleaseValidationError(
                f"commodity_research {section} metric registry fields are invalid"
            )
        provider = str(raw["provider"] or "").strip()
        role = str(raw["metric_role"] or "").strip()
        frequency = str(raw["frequency"] or "").strip()
        try:
            pattern = re.compile(str(raw["metric_code_pattern"]))
        except re.error as error:
            raise ReleaseValidationError(
                f"commodity_research {section} metric pattern is invalid"
            ) from error
        if (
            provider not in providers
            or provider not in context
            or role not in METRIC_ROLE_VALUES
            or frequency not in config["limits"]
            or set(pattern.groupindex) != expected_groups
            or not isinstance(raw["metrics"], list)
            or not raw["metrics"]
        ):
            raise ReleaseValidationError(
                f"commodity_research {section} metric registry is invalid"
            )
        metrics: dict[str, dict[str, str]] = {}
        for metric_raw in raw["metrics"]:
            if not isinstance(metric_raw, dict) or set(metric_raw) != {
                "metric",
                "measurement_kind",
                "unit",
            }:
                raise ReleaseValidationError(
                    f"commodity_research {section} metric fields are invalid"
                )
            metric = str(metric_raw["metric"] or "").strip()
            kind = str(metric_raw["measurement_kind"] or "").strip()
            unit = str(metric_raw["unit"] or "").strip()
            if (
                not re.fullmatch(r"[a-z0-9_]+", metric)
                or metric in metrics
                or kind not in MEASUREMENT_KIND_VALUES
                or not unit
            ):
                raise ReleaseValidationError(
                    f"commodity_research {section} metric identity is invalid"
                )
            metrics[metric] = {"measurement_kind": kind, "unit": unit}
        metadata: dict[str, object]
        reference_period = str(raw["reference_period"] or "").strip()
        if section == "usda_psd":
            raw_countries = raw["country_identifiers"]
            countries: dict[str, str] = {}
            country_markets: set[str] = set()
            if not isinstance(raw_countries, list) or not raw_countries:
                raise ReleaseValidationError(
                    "commodity_research USDA PSD country registry is invalid"
                )
            for country_raw in raw_countries:
                if not isinstance(country_raw, dict) or set(country_raw) != {
                    "identifier",
                    "market",
                }:
                    raise ReleaseValidationError(
                        "commodity_research USDA PSD country fields are invalid"
                    )
                identifier = str(country_raw["identifier"] or "").strip()
                market = str(country_raw["market"] or "").strip()
                normalized_identifier = identifier.lower()
                if (
                    not re.fullmatch(r"[A-Z0-9]+", identifier)
                    or normalized_identifier in countries
                    or not market
                    or market in country_markets
                ):
                    raise ReleaseValidationError(
                        "commodity_research USDA PSD country identity is invalid"
                    )
                countries[normalized_identifier] = market
                country_markets.add(market)
            configured_markets = {
                str(market)
                for item in context[section]
                for market in item.get("country_names", [])
            }
            if (
                country_markets != configured_markets
                or reference_period != "market_year"
            ):
                raise ReleaseValidationError(
                    "commodity_research USDA PSD country/period registry is invalid"
                )
            metadata = {
                "countries": countries,
                "reference_period": reference_period,
            }
        else:
            market = str(raw["market"] or "").strip()
            if not market or reference_period != "observation_date":
                raise ReleaseValidationError(
                    "commodity_research USDA ESR market/period registry is invalid"
                )
            metadata = {
                "market": market,
                "reference_period": reference_period,
            }
        usda_registry[section] = {
            "provider": provider,
            "metric_role": role,
            "frequency": frequency,
            "pattern": pattern,
            "metrics": metrics,
            **metadata,
        }
    return {"exact": descriptors, "usda": usda_registry}


def _usda_metric_descriptor(
    row: dict,
    config: dict,
    registered: dict,
    window: WeekWindow,
) -> dict | None:
    metric_code = str(row.get("metric_code") or "").strip()
    code = str(row.get("commodity_code") or "").strip()
    family = str(row.get("commodity_family") or "").strip()
    unit = str(row.get("unit") or "").strip()
    reference_period = str(row.get("reference_period") or "").strip()
    for section, spec in registered.items():
        match = spec["pattern"].fullmatch(metric_code)
        if match is None:
            continue
        parts = match.groupdict()
        metric = spec["metrics"].get(parts["metric"])
        items = {
            str(item.get("commodity_code") or "").strip(): item
            for item in config["context"][section]
        }
        item = items.get(code)
        if (
            item is None
            or parts["commodity"] != code.lower()
            or family != str(item.get("commodity_family") or "").strip()
        ):
            raise ReleaseValidationError(
                f"commodity metric identity is not registered: {metric_code}"
            )
        allowed_years = {
            window.end.year + int(offset)
            for offset in item.get("market_year_offsets", [])
        }
        if metric is None or int(parts["market_year"]) not in allowed_years:
            raise ReleaseValidationError(
                f"commodity metric identity is not registered: {metric_code}"
            )
        if section == "usda_psd":
            country = parts["country"]
            expected_market = spec["countries"].get(country)
            if expected_market is None:
                raise ReleaseValidationError(
                    f"USDA PSD country is not configured: {country}"
                )
            if expected_market not in set(item.get("country_names", [])):
                raise ReleaseValidationError(
                    f"USDA PSD country is not configured for {code}: {country}"
                )
            if "market" in row and str(row.get("market") or "").strip() != expected_market:
                raise ReleaseValidationError(
                    f"USDA PSD market must match configured country: {expected_market}"
                )
            if reference_period != parts["market_year"]:
                raise ReleaseValidationError(
                    "USDA PSD reference_period must match configured market year: "
                    f"{parts['market_year']}"
                )
            configured_metrics = set(item.get("attributes", {}))
            if parts["metric"] == "stock_to_use":
                allowed = {"ending_stocks", "domestic_use"} <= configured_metrics
            else:
                allowed = parts["metric"] in configured_metrics
            configured_units = {str(value) for value in item.get("unit_names", [])}
        else:
            expected_reference = str(
                row.get("observation_date") or row.get("as_of_date") or ""
            ).strip()
            if "market" in row and str(row.get("market") or "").strip() != spec["market"]:
                raise ReleaseValidationError(
                    f"USDA ESR market must match configured identity: {spec['market']}"
                )
            if reference_period != expected_reference:
                raise ReleaseValidationError(
                    "USDA ESR reference_period must match configured observation date: "
                    f"{expected_reference}"
                )
            allowed = True
            configured_units = {str(item.get("unit_name") or "")}
        expected_unit = metric["unit"]
        if expected_unit == "configured":
            if unit not in configured_units:
                allowed = False
            expected_unit = unit
        elif unit != expected_unit:
            allowed = False
        if not allowed:
            raise ReleaseValidationError(
                f"commodity metric identity is not registered: {metric_code}"
            )
        return {
            "provider": spec["provider"],
            "frequency": spec["frequency"],
            "commodity_code": code,
            "commodity_family": family,
            "metric_role": spec["metric_role"],
            "measurement_kind": metric["measurement_kind"],
            "participant_class": None,
            "unit": expected_unit,
        }
    return None


def _metric_descriptor(
    row: dict,
    config: dict,
    descriptors: dict,
    window: WeekWindow,
) -> dict:
    metric_code = _required_row_text(row, "metric_code", "commodity metric history")
    descriptor = descriptors["exact"].get(metric_code)
    if descriptor is None:
        descriptor = _usda_metric_descriptor(
            row,
            config,
            descriptors["usda"],
            window,
        )
    if descriptor is None:
        raise ReleaseValidationError(
            f"commodity metric identity is not registered: {metric_code}"
        )
    return descriptor


def _validate_metric_descriptor_identity(
    row: dict,
    descriptor: dict,
    label: str,
) -> tuple[str, str, str, str, str | None, str]:
    metric_code = _required_row_text(row, "metric_code", label)
    participant = str(row.get("participant_class") or "").strip() or None
    actual = {
        "commodity_code": _required_row_text(row, "commodity_code", label),
        "commodity_family": _required_row_text(row, "commodity_family", label),
        "metric_role": _required_row_text(row, "metric_role", label),
        "measurement_kind": _required_row_text(row, "measurement_kind", label),
        "participant_class": participant,
        "unit": _required_row_text(row, "unit", label),
    }
    for field, value in actual.items():
        if value != descriptor[field]:
            raise ReleaseValidationError(
                f"{label} {field} is mismapped for {metric_code}"
            )
    return (
        str(actual["commodity_code"]),
        str(actual["commodity_family"]),
        str(actual["metric_role"]),
        str(actual["measurement_kind"]),
        participant,
        str(actual["unit"]),
    )


def _parse_v2_array(value: object, field: str) -> list[str]:
    if isinstance(value, list):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(value)
            except (SyntaxError, ValueError) as error:
                raise ReleaseValidationError(
                    f"commodity research fact {field} must be an array"
                ) from error
    else:
        parsed = None
    if not isinstance(parsed, (list, tuple)) or not parsed:
        raise ReleaseValidationError(
            f"commodity research fact {field} must be a nonempty array"
        )
    normalized = [str(item or "").strip() for item in parsed]
    if any(not item for item in normalized):
        raise ReleaseValidationError(
            f"commodity research fact {field} must contain nonblank strings"
        )
    return normalized


def _validate_commodity_research_v2(
    datasets: dict[tuple[str, str], list[dict]],
    window: WeekWindow,
) -> None:
    config = _research_validation_config()
    registry = config["registry"]
    limits = config["limits"]
    providers = config["providers"]
    price_rows = datasets[("macro_assets", "commodity_price_history.csv")]
    metric_rows = datasets[("weekly_context", "commodity_metric_history.csv")]
    fact_rows = datasets[("weekly_context", "commodity_research_facts.csv")]
    macro_status_rows = datasets[("macro_assets", "source_log.csv")]
    context_status_rows = datasets[("weekly_context", "source_log.csv")]
    context_status = _context_status_index(context_status_rows)

    configured_prices: dict[str, dict] = {}
    configured_nonresearch_prices: dict[str, tuple[str, str]] = {}
    for item in config["macro_rows"]:
        code = str(item.get("commodity_code") or "").strip()
        family = str(item.get("commodity_family") or "").strip()
        provider = str(item.get("provider") or "").strip()
        series = str(item.get("series_code") or "").strip()
        if not code:
            continue
        if family == "digital_asset":
            if not series or series in configured_nonresearch_prices:
                raise ReleaseValidationError(
                    f"Configured nonresearch macro identity is duplicated: {series}"
                )
            configured_nonresearch_prices[series] = (code, family)
            continue
        if registry.get(code) != family or provider not in providers:
            raise ReleaseValidationError(
                f"Configured macro commodity identity is invalid: {code}"
            )
        if not series or series in configured_prices:
            raise ReleaseValidationError(
                f"Configured macro price identity is duplicated: {series}"
            )
        configured_prices[series] = item

    macro_status: dict[str, dict] = {}
    for row in macro_status_rows:
        series = str(row.get("series_code") or "").strip()
        if series in macro_status:
            raise ReleaseValidationError(
                f"configured macro source status must be unique for {series}"
            )
        macro_status[series] = row

    for row in datasets[("macro_assets", "commodities.csv")]:
        series = str(row.get("series_code") or "").strip()
        code = str(row.get("commodity_code") or "").strip()
        family = str(row.get("commodity_family") or "").strip()
        if not code and not family:
            continue
        if configured_nonresearch_prices.get(series) == (code, family):
            continue
        required_family = registry.get(code)
        if required_family is None:
            raise ReleaseValidationError(
                f"macro commodity base row {code or series or 'blank'} is unregistered"
            )
        if family != required_family:
            raise ReleaseValidationError(
                f"macro commodity base row {code} family {family or 'blank'} "
                f"requires {required_family}"
            )
        expected = configured_prices.get(series)
        if expected is None:
            raise ReleaseValidationError(
                f"macro commodity base row {code}/{series or 'blank'} is unconfigured"
            )
        if (
            code != str(expected["commodity_code"])
            or family != str(expected["commodity_family"])
        ):
            raise ReleaseValidationError(
                f"macro commodity base row {code}/{series} is mismapped"
            )
        provider = str(expected["provider"])
        _require_policy_provenance(
            row,
            providers[provider],
            f"macro commodity base row {code}/{series}",
        )

    normalized_price: list[dict] = []
    price_identities: set[tuple] = set()
    price_groups: dict[tuple[str, str], list[dict]] = {}
    price_codes: set[str] = set()
    for row in price_rows:
        label = "commodity price history"
        if str(row.get("as_of_date") or "").strip() != window.end.isoformat():
            raise ReleaseValidationError(f"{label} as_of_date must equal release as_of_date")
        series = _required_row_text(row, "series_code", label)
        expected = configured_prices.get(series)
        if expected is None:
            code = str(row.get("commodity_code") or "").strip()
            raise ReleaseValidationError(
                f"{label} contains unconfigured or excluded code: {code or series}"
            )
        code = _required_row_text(row, "commodity_code", label)
        family = _required_row_text(row, "commodity_family", label)
        if code == "BTC_USD" or family == "digital_asset":
            raise ReleaseValidationError("BTC_USD/digital_asset is excluded from V2 history")
        if code != str(expected["commodity_code"]) or family != registry.get(code):
            raise ReleaseValidationError(
                f"commodity price history code-family mismatch: {code} requires "
                f"{registry.get(code) or 'configured identity'}"
            )
        for field, configured_field in (
            ("price_kind", "price_kind"),
            ("source", "source"),
            ("unit", "level_unit"),
        ):
            if str(row.get(field) or "").strip() != str(expected.get(configured_field) or "").strip():
                raise ReleaseValidationError(
                    f"{label} {field} is mismapped for {series}"
                )
        provider = str(expected["provider"])
        policy = providers[provider]
        _require_policy_provenance(row, policy, label)
        status = macro_status.get(series)
        if status is None or str(status.get("status") or "").strip().upper() != "OK":
            raise ReleaseValidationError(
                f"{provider} requires zero V2 rows unless macro status is OK: {series}"
            )
        observation = _v2_observation_date(row, window, label)
        _known, known_text = _canonical_v2_known_as_of(
            row.get("known_as_of"), window, label
        )
        value = _finite_row_value(row, label)
        if str(row.get("qc_flag") or "").strip() != "OK":
            raise ReleaseValidationError(f"{label} qc_flag must be OK")
        identity = {
            "code": code,
            "known_as_of": known_text,
            "observation_date": observation.isoformat(),
            "series": series,
        }
        semantic = tuple(identity.values())
        if semantic in price_identities:
            raise ReleaseValidationError(
                f"commodity price history duplicate semantic identity: {series}"
            )
        price_identities.add(semantic)
        record_id = _validate_v2_record_id(
            row,
            namespace="commodity_price_history",
            identity=identity,
            label=label,
        )
        normalized = {
            **row,
            "record_id": record_id,
            "known_as_of": known_text,
            "observation_date": observation.isoformat(),
            "value": value,
        }
        normalized_price.append(normalized)
        price_groups.setdefault((code, series), []).append(normalized)
        price_codes.add(code)

    actual_price_series = set(price_groups)
    missing_prices = sorted(
        series for series, item in configured_prices.items()
        if (str(item["commodity_code"]), series) not in actual_price_series
    )
    if missing_prices:
        raise ReleaseValidationError(
            "configured price history is missing: " + ", ".join(missing_prices)
        )
    expected_price_order = sorted(
        normalized_price,
        key=lambda row: (
            row["commodity_code"],
            row["series_code"],
            row["observation_date"],
            row["known_as_of"] or "",
            row["record_id"],
        ),
    )
    if [row["record_id"] for row in normalized_price] != [
        row["record_id"] for row in expected_price_order
    ]:
        changed = next(
            (
                row["series_code"]
                for row, expected in zip(normalized_price, expected_price_order)
                if row["record_id"] != expected["record_id"]
            ),
            "unknown",
        )
        raise ReleaseValidationError(f"commodity price history ordering is invalid: {changed}")
    for series, item in configured_prices.items():
        status = macro_status.get(series)
        if status is None:
            raise ReleaseValidationError(
                f"{series} configured macro price status is missing"
            )
        provider = str(item["provider"])
        code = str(item["commodity_code"])
        frequency = str(item.get("frequency") or "").strip()
        limit = limits.get(frequency)
        if limit is None:
            raise ReleaseValidationError(
                f"commodity price history limit is missing for {frequency}: {series}"
            )
        rows = price_groups[(code, series)]
        _validate_provider_status(
            status,
            providers[provider],
            len(rows),
            f"{provider}/{series}",
            "price history rows",
            observation_limit=limit,
            frequency=frequency,
        )
        if len(rows) > limit:
            raise ReleaseValidationError(
                f"commodity price history limit exceeds {frequency} {limit}: {series}"
            )

    descriptors = _metric_descriptors(config)
    normalized_metric: list[dict] = []
    metric_identities: set[tuple] = set()
    metric_groups: dict[tuple, list[dict]] = {}
    history_ids: dict[str, dict] = {
        row["record_id"]: row for row in normalized_price
    }
    for row in metric_rows:
        label = "commodity metric history"
        if str(row.get("as_of_date") or "").strip() != window.end.isoformat():
            raise ReleaseValidationError(f"{label} as_of_date must equal release as_of_date")
        code = _required_row_text(row, "commodity_code", label)
        family = _required_row_text(row, "commodity_family", label)
        if code == "BTC_USD" or family == "digital_asset":
            raise ReleaseValidationError("BTC_USD/digital_asset is excluded from V2 history")
        if registry.get(code) != family:
            raise ReleaseValidationError(
                f"commodity metric history code-family mismatch: {code} requires "
                f"{registry.get(code) or 'configured identity'}"
            )
        descriptor = _metric_descriptor(row, config, descriptors, window)
        code, family, role, kind, participant, unit = (
            _validate_metric_descriptor_identity(row, descriptor, label)
        )
        provider = descriptor["provider"]
        policy = providers[provider]
        _require_policy_provenance(row, policy, label)
        status = context_status.get(provider)
        status_value = str((status or {}).get("status") or "").strip().upper()
        if status_value != "OK":
            raise ReleaseValidationError(
                f"{provider} requires zero V2 rows while status is {status_value or 'missing'}"
            )
        observation = _v2_observation_date(row, window, label)
        _known, known_text = _canonical_v2_known_as_of(
            row.get("known_as_of"), window, label
        )
        reference = str(row.get("reference_period") or "").strip() or None
        value = _finite_row_value(row, label)
        if str(row.get("qc_flag") or "").strip() != "OK":
            raise ReleaseValidationError(f"{label} qc_flag must be OK")
        identity = {
            "code": code,
            "known_as_of": known_text,
            "measurement": kind,
            "metric": str(row["metric_code"]),
            "observation_date": observation.isoformat(),
            "participant": participant,
            "reference_period": reference,
            "role": role,
        }
        semantic = tuple(identity.values())
        if semantic in metric_identities:
            raise ReleaseValidationError(
                f"commodity metric history duplicate semantic identity: {row['metric_code']}"
            )
        metric_identities.add(semantic)
        record_id = _validate_v2_record_id(
            row,
            namespace="commodity_metric_history",
            identity=identity,
            label=label,
        )
        normalized = {
            **row,
            "record_id": record_id,
            "participant_class": participant,
            "known_as_of": known_text,
            "reference_period": reference,
            "observation_date": observation.isoformat(),
            "value": value,
        }
        normalized_metric.append(normalized)
        group = (code, str(row["metric_code"]), role, kind, participant)
        metric_groups.setdefault(group, []).append(normalized)
        if record_id in history_ids:
            raise ReleaseValidationError(f"Duplicate V2 history record_id: {record_id}")
        history_ids[record_id] = normalized

    expected_metric_order = sorted(
        normalized_metric,
        key=lambda row: (
            row["commodity_code"],
            row["metric_code"],
            row["metric_role"],
            row["measurement_kind"],
            row["participant_class"] or "",
            row["observation_date"],
            row["known_as_of"] or "",
            row["record_id"],
        ),
    )
    if [row["record_id"] for row in normalized_metric] != [
        row["record_id"] for row in expected_metric_order
    ]:
        changed = next(
            (
                row["metric_code"]
                for row, expected in zip(normalized_metric, expected_metric_order)
                if row["record_id"] != expected["record_id"]
            ),
            "unknown",
        )
        raise ReleaseValidationError(f"commodity metric history ordering is invalid: {changed}")
    for group, rows in metric_groups.items():
        descriptor = _metric_descriptor(rows[0], config, descriptors, window)
        frequency = descriptor["frequency"]
        limit = limits.get(frequency)
        if limit is None or len(rows) > limit:
            raise ReleaseValidationError(
                f"commodity metric history limit exceeds {frequency} {limit}: {group[1]}"
            )

    base_rows = [
        *datasets[("weekly_context", "commodity_fundamentals.csv")],
        *datasets[("weekly_context", "positioning_flows.csv")],
    ]
    expected_groups: set[tuple] = set()
    business_counts: dict[str, int] = {}
    for row in base_rows:
        code = str(row.get("commodity_code") or "").strip()
        family = str(row.get("commodity_family") or "").strip()
        if not code and not family:
            continue
        required_family = registry.get(code)
        if required_family is None:
            raise ReleaseValidationError(
                f"context commodity base row {code or 'blank'} is unregistered"
            )
        if family != required_family:
            raise ReleaseValidationError(
                f"context commodity base row {code} family {family or 'blank'} "
                f"requires {required_family}"
            )
        descriptor = _metric_descriptor(row, config, descriptors, window)
        _validate_metric_descriptor_identity(
            row,
            descriptor,
            "commodity context base row",
        )
        provider = descriptor["provider"]
        _require_policy_provenance(
            row,
            providers[provider],
            f"{provider} business row",
        )
        if str(row.get("qc_flag") or "").strip().upper() != "OK":
            continue
        business_counts[provider] = business_counts.get(provider, 0) + 1
        expected_groups.add((
            code,
            str(row.get("metric_code") or "").strip(),
            str(row.get("metric_role") or "").strip(),
            str(row.get("measurement_kind") or "").strip(),
            str(row.get("participant_class") or "").strip() or None,
        ))
    _validate_context_provider_statuses(
        context_status,
        providers,
        business_counts,
    )
    actual_groups = set(metric_groups)
    if actual_groups != expected_groups:
        missing = sorted(str(group) for group in expected_groups - actual_groups)
        extra = sorted(str(group) for group in actual_groups - expected_groups)
        raise ReleaseValidationError(
            "commodity metric history exact business-row coverage mismatch; "
            f"missing={missing}; extra={extra}"
        )

    history_codes = price_codes | {group[0] for group in metric_groups}
    if history_codes != set(registry):
        missing = sorted(set(registry) - history_codes)
        extra = sorted(history_codes - set(registry))
        raise ReleaseValidationError(
            "commodity history exact configured code coverage mismatch; "
            f"missing={missing}; extra={extra}"
        )

    normalized_facts: dict[str, dict] = {}
    fact_identities: set[tuple] = set()
    for row in fact_rows:
        label = "commodity research fact"
        fact_code = _required_row_text(row, "fact_code", label)
        configured = config["fact_rows"].get(fact_code)
        if configured is None:
            raise ReleaseValidationError(f"Unregistered fact_code: {fact_code}")
        if fact_code in normalized_facts:
            raise ReleaseValidationError(
                f"commodity research fact duplicate semantic identity: {fact_code}"
            )
        code = _required_row_text(row, "commodity_code", label)
        family = _required_row_text(row, "commodity_family", label)
        if code != configured["commodity_code"] or family != registry.get(code):
            raise ReleaseValidationError(
                f"commodity research fact code-family mismatch: {fact_code}"
            )
        for field, expected_field in (
            ("fact_kind", "fact_kind"),
            ("unit", "output_unit"),
            ("formula_id", "formula_id"),
            ("formula_version", "version"),
        ):
            if str(row.get(field) or "").strip() != str(configured[expected_field]):
                raise ReleaseValidationError(
                    f"commodity research fact {field} mismatch: {fact_code}"
                )
        if str(row.get("as_of_date") or "").strip() != window.end.isoformat():
            raise ReleaseValidationError(f"{label} as_of_date must equal release as_of_date")
        observation = _v2_observation_date(row, window, label)
        _known, known_text = _canonical_v2_known_as_of(
            row.get("known_as_of"), window, label
        )
        reference = _required_row_text(row, "reference_period", label)
        value = _finite_row_value(row, label)
        if str(row.get("qc_flag") or "").strip() != "OK":
            raise ReleaseValidationError(f"{label} qc_flag must be OK")
        input_ids = _parse_v2_array(row.get("input_record_ids"), "input_record_ids")
        orphan = sorted(set(input_ids) - set(history_ids))
        if orphan:
            raise ReleaseValidationError(
                "commodity research fact orphan input_record_id: " + ", ".join(orphan)
            )
        if input_ids != sorted(set(input_ids)):
            raise ReleaseValidationError(
                f"commodity research fact input_record_ids must be sorted and unique: {fact_code}"
            )
        inputs = [history_ids[record_id] for record_id in input_ids]
        if any(item["commodity_code"] != code for item in inputs):
            raise ReleaseValidationError(
                f"commodity research fact inputs have mixed identity: {fact_code}"
            )
        source_urls = _parse_v2_array(row.get("source_urls"), "source_urls")
        expected_urls = sorted({str(item["source_url"]) for item in inputs})
        if source_urls != expected_urls:
            raise ReleaseValidationError(
                f"commodity research fact source_urls mismatch: {fact_code}"
            )
        if configured["formula_id"] == "stock_to_use_v1":
            vintages = {
                (item.get("known_as_of"), item.get("reference_period"))
                for item in inputs
            }
            if len(vintages) != 1 or any(None in vintage for vintage in vintages):
                raise ReleaseValidationError(
                    "stock_to_use_v1 inputs must use the same USDA vintage"
                )
        identity = {
            "commodity_code": code,
            "fact_code": fact_code,
            "formula_id": str(row["formula_id"]),
            "formula_version": str(row["formula_version"]),
            "known_as_of": known_text,
            "observation_date": observation.isoformat(),
            "reference_period": reference,
        }
        semantic = tuple(identity.values())
        if semantic in fact_identities:
            raise ReleaseValidationError(
                f"commodity research fact duplicate semantic identity: {fact_code}"
            )
        fact_identities.add(semantic)
        record_id = _validate_v2_record_id(
            row,
            namespace="commodity_research_facts",
            identity=identity,
            label=label,
        )
        normalized_facts[fact_code] = {
            **row,
            "record_id": record_id,
            "value": value,
            "observation_date": observation.isoformat(),
            "known_as_of": known_text,
            "input_record_ids": input_ids,
            "source_urls": source_urls,
        }

    try:
        expected_facts = build_research_facts(
            normalized_price,
            normalized_metric,
            config["formula_specs"],
            window.end,
        )
    except ValueError as error:
        message = str(error)
        if "same known_as_of" in message or "same reference_period" in message:
            message = "stock_to_use_v1 inputs must use the same USDA vintage"
        raise ReleaseValidationError(message) from error
    expected_by_code = {row["fact_code"]: row for row in expected_facts}
    if set(normalized_facts) != set(expected_by_code):
        raise ReleaseValidationError(
            "commodity research registered fact coverage mismatch; "
            f"expected={sorted(expected_by_code)}; actual={sorted(normalized_facts)}"
        )
    for fact_code, expected in expected_by_code.items():
        actual = normalized_facts[fact_code]
        for field in RESEARCH_FACT_FIELDS:
            if actual[field] != expected[field]:
                raise ReleaseValidationError(
                    f"commodity research formula output mismatch: {fact_code}.{field}"
                )


def _strict_json_object(path: Path, root: Path) -> dict:
    _ensure_regular_contained_file(path, root)

    def reject_constant(value: str):
        raise ValueError(f"non-standard JSON constant {value}")

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ReleaseValidationError(f"Invalid strict JSON file: {path.name}") from error
    if not isinstance(payload, dict):
        raise ReleaseValidationError(f"JSON root must be an object: {path.name}")
    return payload


def _source_manifest(release_root: Path) -> tuple[dict, WeekWindow, int]:
    root = Path(release_root)
    if root.is_symlink() or not root.is_dir():
        raise ReleaseValidationError("Source release root must be a regular directory")
    manifest = _strict_json_object(root / "manifest.json", root)
    if manifest.get("status") != "complete":
        raise ReleaseValidationError("Source release manifest is not complete")
    try:
        start = date.fromisoformat(manifest["week_start"])
        end = date.fromisoformat(manifest["week_end"])
        week_id = str(manifest["week_id"])
        contract_version = int(manifest["dataset_contract_version"])
    except (KeyError, TypeError, ValueError) as error:
        raise ReleaseValidationError("Source release manifest identity is invalid") from error
    window = WeekWindow(start, end, week_id)
    if end - start != timedelta(days=6) or week_id != f"week_{start:%Y%m%d}-{end:%Y%m%d}":
        raise ReleaseValidationError("Source release week identity is inconsistent")
    release_datasets_for_contract(contract_version)

    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ReleaseValidationError("Source release file manifest is invalid")
    expected_paths: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ReleaseValidationError("Source release file manifest is invalid")
        relative = entry.get("path")
        expected_hash = entry.get("sha256")
        if (
            not isinstance(relative, str)
            or not relative
            or relative in expected_paths
            or not isinstance(expected_hash, str)
        ):
            raise ReleaseValidationError("Source release file manifest is invalid")
        path = root / relative
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ReleaseValidationError("Source release file path escapes its root") from error
        _ensure_regular_contained_file(path, root)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ReleaseValidationError(f"Source release hash mismatch: {relative}")
        expected_paths.add(relative)
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != root / "manifest.json"
    }
    if actual_paths != expected_paths:
        raise ReleaseValidationError("Source release files do not match its manifest")

    validate_staged_week(
        root,
        window,
        dataset_contract_version=contract_version,
    )
    return manifest, window, contract_version


def _typed_csv_rows(path: Path, dataset: DatasetSpec) -> list[dict]:
    rows: list[dict] = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, strict=True)
            for raw in reader:
                row = {}
                for key, value in raw.items():
                    if value == "":
                        row[key] = None
                    elif key in dataset.json_array_columns:
                        row[key] = _parse_v2_array(value, key)
                    elif key in dataset.numeric_columns:
                        try:
                            number = float(value)
                        except ValueError as error:
                            raise ReleaseValidationError(
                                f"Invalid output number: {dataset.filename}.{key}"
                            ) from error
                        if not math.isfinite(number):
                            raise ReleaseValidationError(
                                f"Non-finite output value: {dataset.filename}.{key}"
                            )
                        row[key] = (
                            int(number)
                            if number.is_integer()
                            and key in OUTPUT_INTEGER_COLUMNS
                            else number
                        )
                    else:
                        row[key] = value
                rows.append(row)
    except csv.Error as error:
        raise ReleaseValidationError(
            f"{dataset.filename} contains malformed CSV: {error}"
        ) from error
    return rows


def _new_output_release_id() -> str:
    generated = datetime.now(HONG_KONG)
    return f"{generated:%Y%m%dT%H%M%S%z}-{uuid.uuid4().hex[:6]}"


def _output_tables_for_contract(
    dataset_contract_version: int,
) -> dict[str, tuple[str, tuple[tuple[str, str], ...]]]:
    release_datasets_for_contract(dataset_contract_version)
    return {
        public_name: (
            source_pipeline,
            tuple(
                (table_name, filename)
                for table_name, filename in table_files
                if dataset_contract_version == DATASET_CONTRACT_VERSION
                or (public_name, table_name) not in V2_OUTPUT_TABLES
            ),
        )
        for public_name, (source_pipeline, table_files) in OUTPUT_TABLES.items()
    }


def build_output_bundle(
    release_root: Path,
    destination: Path,
    *,
    release_id: str | None = None,
) -> dict:
    """Convert one complete staged-week release into five stable JSON files."""
    source_root = Path(release_root)
    source_manifest, window, contract_version = _source_manifest(source_root)
    output_root = Path(destination)
    if output_root.is_symlink():
        raise ReleaseValidationError("Output root must not be a symbolic link")
    output_root.mkdir(parents=True, exist_ok=True)
    if any(output_root.iterdir()):
        raise ReleaseValidationError("Output destination must be empty")

    identity = release_id or _new_output_release_id()
    if not identity.strip():
        raise ReleaseValidationError("Output release_id must not be blank")
    generated_at = datetime.now(HONG_KONG).isoformat(timespec="seconds")
    pipeline_dirs = {
        spec.name: Path(spec.output_dir)
        for spec in build_pipeline_specs(source_root, window)
    }
    datasets = {
        (dataset.pipeline, dataset.filename): dataset
        for dataset in release_datasets_for_contract(contract_version)
    }
    output_tables = _output_tables_for_contract(contract_version)
    pipeline_entries = []
    file_entries = []
    for public_name, (source_pipeline, table_files) in output_tables.items():
        tables = {}
        row_counts = {}
        for table_name, filename in table_files:
            dataset = datasets.get((source_pipeline, filename))
            if dataset is None:
                if public_name == "context" and table_name == "economic_releases":
                    rows = []
                else:
                    raise ReleaseValidationError(
                        f"Output table is not registered: {source_pipeline}/{filename}"
                    )
            else:
                rows = _typed_csv_rows(
                    pipeline_dirs[source_pipeline] / filename,
                    dataset,
                )
            tables[table_name] = rows
            row_counts[table_name] = len(rows)
        source_dataset = datasets[(source_pipeline, "source_log.csv")]
        source_log = _typed_csv_rows(
            pipeline_dirs[source_pipeline] / "source_log.csv",
            source_dataset,
        )
        document = {
            "schema_version": OUTPUT_SCHEMA_VERSION,
            "dataset_contract_version": contract_version,
            "release_id": identity,
            "as_of_date": window.end.isoformat(),
            "pipeline": public_name,
            "status": "complete",
            "tables": tables,
            "source_log": source_log,
        }
        filename = f"{public_name}.json"
        path = output_root / filename
        _atomic_write_json(path, document)
        pipeline_entries.append(
            {
                "name": public_name,
                "status": "complete",
                "file": filename,
                "rows": {**row_counts, "source_log": len(source_log)},
            }
        )
        file_entries.append(
            {
                "name": filename,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    release = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "dataset_contract_version": contract_version,
        "release_id": identity,
        "as_of_date": window.end.isoformat(),
        "generated_at": generated_at,
        "status": "complete",
        "source_week_id": source_manifest["week_id"],
        "pipelines": pipeline_entries,
        "files": file_entries,
    }
    _atomic_write_json(output_root / "release.json", release)
    return validate_output_bundle(output_root)


def validate_output_bundle(output_root: Path) -> dict:
    root = Path(output_root)
    if root.is_symlink() or not root.is_dir():
        raise ReleaseValidationError("Output root must be a regular directory")
    paths = list(root.iterdir())
    if any(path.is_symlink() or not path.is_file() for path in paths):
        raise ReleaseValidationError("Output bundle may contain only regular files")
    names = {path.name for path in paths}
    if names != OUTPUT_FILES:
        missing = sorted(OUTPUT_FILES - names)
        extra = sorted(names - OUTPUT_FILES)
        detail = ", ".join(
            part
            for part in (
                f"missing: {', '.join(missing)}" if missing else "",
                f"extra: {', '.join(extra)}" if extra else "",
            )
            if part
        )
        raise ReleaseValidationError(f"Unexpected output files ({detail})")

    release = _strict_json_object(root / "release.json", root)
    identity = release.get("release_id")
    as_of_date = release.get("as_of_date")
    if (
        release.get("schema_version") != OUTPUT_SCHEMA_VERSION
        or release.get("status") != "complete"
        or not isinstance(identity, str)
        or not identity.strip()
        or not isinstance(as_of_date, str)
    ):
        raise ReleaseValidationError("release.json identity or status is invalid")
    try:
        date.fromisoformat(as_of_date)
    except ValueError as error:
        raise ReleaseValidationError("release.json as_of_date is invalid") from error
    raw_contract_version = release.get("dataset_contract_version")
    if raw_contract_version is None:
        contract_version = COMPATIBILITY_DATASET_CONTRACT_VERSION
    elif (
        isinstance(raw_contract_version, bool)
        or not isinstance(raw_contract_version, int)
    ):
        raise ReleaseValidationError("release.json dataset contract is invalid")
    else:
        contract_version = raw_contract_version
    output_tables = _output_tables_for_contract(contract_version)

    entries = release.get("files")
    if not isinstance(entries, list):
        raise ReleaseValidationError("release.json file list is invalid")
    by_name = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise ReleaseValidationError("release.json file entry is invalid")
        name = entry["name"]
        if name in by_name:
            raise ReleaseValidationError(f"Duplicate release file entry: {name}")
        by_name[name] = entry
    if set(by_name) != set(OUTPUT_BUSINESS_FILES):
        raise ReleaseValidationError("release.json must hash exactly five business files")

    documents: dict[str, dict] = {}
    for name in OUTPUT_BUSINESS_FILES:
        document = _strict_json_object(root / name, root)
        expected_pipeline = name.removesuffix(".json")
        document_contract_version = document.get("dataset_contract_version")
        if document_contract_version is None:
            document_contract_version = COMPATIBILITY_DATASET_CONTRACT_VERSION
        expected_tables = {
            table_name
            for table_name, _filename in output_tables[expected_pipeline][1]
        }
        if (
            document.get("schema_version") != OUTPUT_SCHEMA_VERSION
            or document_contract_version != contract_version
            or document.get("release_id") != identity
            or document.get("as_of_date") != as_of_date
            or document.get("pipeline") != expected_pipeline
            or document.get("status") != "complete"
            or not isinstance(document.get("tables"), dict)
            or not isinstance(document.get("source_log"), list)
        ):
            raise ReleaseValidationError(f"Output identity mismatch: {name}")
        if set(document["tables"]) != expected_tables or any(
            not isinstance(rows, list)
            for rows in document["tables"].values()
        ):
            raise ReleaseValidationError(f"Output table contract mismatch: {name}")
        actual_hash = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if by_name[name].get("sha256") != actual_hash:
            raise ReleaseValidationError(f"Output hash mismatch: {name}")
        if by_name[name].get("bytes") != (root / name).stat().st_size:
            raise ReleaseValidationError(f"Output size mismatch: {name}")
        documents[expected_pipeline] = document

    pipelines = release.get("pipelines")
    if not isinstance(pipelines, list):
        raise ReleaseValidationError("release.json pipeline list is invalid")
    pipeline_entries: dict[str, dict] = {}
    for entry in pipelines:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise ReleaseValidationError("release.json pipeline entry is invalid")
        name = entry["name"]
        if name in pipeline_entries:
            raise ReleaseValidationError(f"Duplicate release pipeline entry: {name}")
        pipeline_entries[name] = entry
    if set(pipeline_entries) != set(output_tables):
        raise ReleaseValidationError("release.json pipeline statuses are incomplete")
    for name, entry in pipeline_entries.items():
        document = documents[name]
        expected_rows = {
            table_name: len(document["tables"][table_name])
            for table_name, _filename in output_tables[name][1]
        }
        expected_rows["source_log"] = len(document["source_log"])
        if (
            entry.get("status") != "complete"
            or entry.get("file") != f"{name}.json"
            or entry.get("rows") != expected_rows
        ):
            raise ReleaseValidationError(
                f"release.json pipeline status or row counts are invalid: {name}"
            )
    if contract_version == DATASET_CONTRACT_VERSION:
        validation_rows = {
            ("macro_assets", "commodities.csv"):
                documents["macro"]["tables"]["commodities"],
            ("macro_assets", "commodity_price_history.csv"):
                documents["macro"]["tables"]["commodity_price_history"],
            ("macro_assets", "source_log.csv"):
                documents["macro"]["source_log"],
            ("weekly_context", "commodity_fundamentals.csv"):
                documents["context"]["tables"]["commodity_fundamentals"],
            ("weekly_context", "positioning_flows.csv"):
                documents["context"]["tables"]["positioning_flows"],
            ("weekly_context", "commodity_metric_history.csv"):
                documents["context"]["tables"]["commodity_metric_history"],
            ("weekly_context", "commodity_research_facts.csv"):
                documents["context"]["tables"]["commodity_research_facts"],
            ("weekly_context", "source_log.csv"):
                documents["context"]["source_log"],
        }
        end = date.fromisoformat(as_of_date)
        _validate_commodity_research_v2(
            validation_rows,
            WeekWindow(
                start=end - timedelta(days=6),
                end=end,
                week_id=f"week_{end - timedelta(days=6):%Y%m%d}-{end:%Y%m%d}",
            ),
        )
    return release


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
    reason = sanitize_audit_text(error).strip() or type(error).__name__

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


def _required_provider_failure_status(
    specs: tuple[PipelineSpec, ...],
) -> dict[str, object] | None:
    context = next((spec for spec in specs if spec.name == "weekly_context"), None)
    if context is None:
        return None
    source_log = Path(context.output_dir) / "source_log.csv"
    if not source_log.is_file() or source_log.is_symlink():
        return None
    try:
        with source_log.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle, strict=True))
    except (OSError, UnicodeError, csv.Error):
        return None
    for row in rows:
        status = str(row.get("status") or "").strip().upper()
        if (
            str(row.get("requiredness") or "").strip() != "required"
            or status == "OK"
        ):
            continue
        provider = str(row.get("provider") or "").strip()
        phase = str(row.get("phase") or "").strip()
        raw_attempts = str(row.get("attempts") or "").strip()
        error_code = str(row.get("error_code") or "").strip().upper()
        if not re.fullmatch(r"[a-z0-9_]+", provider):
            provider = "unknown_provider"
        if phase not in PROVIDER_PHASES:
            phase = "retrieve"
        attempts = int(raw_attempts) if re.fullmatch(r"[1-9][0-9]*", raw_attempts) else 1
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", error_code):
            error_code = "PROVIDER_FAILURE"
        return {
            "pipeline": "weekly_context",
            "provider": provider,
            "phase": phase,
            "attempts": attempts,
            "error_code": error_code,
        }
    return None


@contextmanager
def release_write_lock(
    lock_root: Path,
    *,
    operation: str,
    lock_name: str = ".capital_weekly_refresh.lock",
):
    lock_root.mkdir(parents=True, exist_ok=True)
    lock_path = lock_root / lock_name
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


def _stage_latest_cache(
    staging_cache: Path,
    specs: tuple[PipelineSpec, ...],
    release: dict,
) -> None:
    staging_cache.mkdir(parents=True, exist_ok=False)
    by_pipeline = {spec.name: Path(spec.output_dir) for spec in specs}
    sources = {
        "indices": by_pipeline["equity_indices"] / "raw",
        "sectors": by_pipeline["equity_sectors"] / "raw",
        "gics": by_pipeline["gics_sectors"] / "raw",
        "macro": by_pipeline["macro_assets"] / "raw",
        "context": by_pipeline["weekly_context"].parent
        / f".{by_pipeline['weekly_context'].name}.raw",
    }
    for public_name, source in sources.items():
        destination = staging_cache / public_name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            destination.mkdir()
    _atomic_write_json(
        staging_cache / "cache.json",
        {
            "schema_version": OUTPUT_SCHEMA_VERSION,
            "release_id": release["release_id"],
            "as_of_date": release["as_of_date"],
            "status": "complete",
            "pipelines": list(sources),
        },
    )


def _publish_output_cache_pair(
    staging_output: Path,
    output: Path,
    staging_cache: Path,
    cache: Path,
    finalize: Callable[[], None] | None = None,
) -> None:
    transaction_id = uuid.uuid4().hex
    output_backup = output.with_name(f".{output.name}.backup-{transaction_id}")
    cache_backup = cache.with_name(f".{cache.name.lstrip('.')}.backup-{transaction_id}")
    output_backed_up = False
    cache_backed_up = False
    output_published = False
    cache_published = False
    try:
        if output.exists():
            os.replace(output, output_backup)
            output_backed_up = True
        if cache.exists():
            os.replace(cache, cache_backup)
            cache_backed_up = True
        os.replace(staging_output, output)
        output_published = True
        os.replace(staging_cache, cache)
        cache_published = True
        if finalize is not None:
            finalize()
    except Exception:
        if cache_published and cache.exists():
            os.replace(cache, staging_cache)
        if cache_backed_up and cache_backup.exists():
            os.replace(cache_backup, cache)
        if output_published and output.exists():
            os.replace(output, staging_output)
        if output_backed_up and output_backup.exists():
            os.replace(output_backup, output)
        raise
    for backup in (output_backup, cache_backup):
        if backup.exists():
            try:
                shutil.rmtree(backup)
            except OSError as error:
                try:
                    warnings.warn(
                        f"Published latest release, but backup cleanup failed: {error}",
                        RuntimeWarning,
                    )
                except RuntimeWarning:
                    pass


def run_latest_release(
    project_root: Path,
    now_hkt: datetime | None = None,
    status_path: Path | None = None,
    runner=subprocess.run,
) -> Path:
    root = Path(project_root).resolve()
    pipeline_root = root / "pipeline"
    state_root = pipeline_root / ".state"
    staging_root = pipeline_root / ".staging"
    destination = root / "output"
    cache = pipeline_root / ".cache"
    window = latest_finished_week(now_hkt)
    status_file = (
        Path(status_path)
        if status_path is not None
        else state_root / "status.json"
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
        "pipeline": None,
        "provider": None,
        "phase": None,
        "attempts": None,
        "error_code": None,
    }
    with release_write_lock(
        state_root,
        operation=f"refresh for {window.week_id}",
        lock_name="refresh.lock",
    ):
        staging_root.mkdir(parents=True, exist_ok=True)
        staging_job = staging_root / job_id
        staging_job.mkdir()
        staging_week = staging_job / "week"
        staging_week.mkdir()
        staging_output = staging_job / "output"
        staging_cache = staging_job / "cache"
        specs: tuple[PipelineSpec, ...] = ()
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
            manifest = validate_staged_week(
                staging_week,
                window,
                dataset_contract_version=DATASET_CONTRACT_VERSION,
            )
            manifest["pipelines"] = pipeline_runs
            _atomic_write_json(staging_week / "manifest.json", manifest)
            status["current_pipeline"] = "output"
            _write_status(status_file, status)
            release = build_output_bundle(staging_week, staging_output)
            status["current_pipeline"] = "cache"
            _write_status(status_file, status)
            _stage_latest_cache(staging_cache, specs, release)
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

            _publish_output_cache_pair(
                staging_output,
                destination,
                staging_cache,
                cache,
                finalize_release,
            )
            return destination
        except Exception as error:
            provider_failure = _required_provider_failure_status(specs)
            status.update(
                {
                    "status": "failed",
                    "finished_at": _status_timestamp(),
                    "error": safe_error_reason(error),
                }
            )
            if provider_failure is not None:
                status.update(provider_failure)
            _write_status(status_file, status)
            raise
        finally:
            if staging_job.exists():
                shutil.rmtree(staging_job)


run_weekly_release = run_latest_release


__all__ = [
    "PipelineSpec",
    "DATASET_CONTRACT_VERSION",
    "LEGACY_DATASET_CONTRACT_VERSION",
    "MANIFEST_SCHEMA_VERSION",
    "OUTPUT_BUSINESS_FILES",
    "OUTPUT_SCHEMA_VERSION",
    "RELEASE_DATASETS",
    "SUPPORTED_DATASET_CONTRACT_VERSIONS",
    "ReleaseAlreadyRunning",
    "ReleasePipelineError",
    "ReleaseValidationError",
    "WeekWindow",
    "_publish_output_cache_pair",
    "_publish_directory",
    "build_output_bundle",
    "build_pipeline_specs",
    "build_release_manifest",
    "file_manifest",
    "latest_finished_week",
    "release_write_lock",
    "run_latest_release",
    "run_weekly_release",
    "release_datasets_for_contract",
    "safe_error_reason",
    "validate_staged_week",
    "validate_output_bundle",
]
