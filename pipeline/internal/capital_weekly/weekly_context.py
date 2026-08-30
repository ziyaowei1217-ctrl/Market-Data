from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from typing import Mapping

import pandas as pd

from .context.common import METRIC_FIELDS, normalize_metric_rows
from .context.economic_releases import (
    ECONOMIC_RELEASE_FIELDS,
    normalize_economic_release_rows,
    validate_economic_release_input_references,
)
from .context.provider_contracts import (
    ContextProvider,
    ProviderResult,
    filter_known_as_of,
)


CATEGORY_FILES = {
    "events": "events.csv",
    "economic_releases": "economic_releases.csv",
    "market_internals": "market_internals.csv",
    "positioning_flows": "positioning_flows.csv",
    "company_events": "company_events.csv",
    "commodity_fundamentals": "commodity_fundamentals.csv",
    "financial_conditions": "financial_conditions.csv",
    "source_log": "source_log.csv",
}

EVENT_FIELDS = (
    "event_date",
    "release_time_bjt",
    "release_datetime_bjt",
    "region",
    "event_type",
    "event_name",
    "reference_period",
    "actual",
    "previous",
    "revised_previous",
    "evidence_status",
    "source",
    "source_url",
    "qc_flag",
)
SOURCE_LOG_FIELDS = (
    "provider",
    "source_tier",
    "requiredness",
    "provider_version",
    "schema_version",
    "frequency",
    "freshness_days",
    "latest_known_as_of",
    "warnings",
    "category",
    "status",
    "observations",
    "as_of_date",
    "source",
    "source_url",
    "elapsed_ms",
    "notes",
)
COMPANY_EVENT_FIELDS = METRIC_FIELDS + (
    "event_date",
    "ticker",
    "cik",
    "form",
    "event_type",
    "accession_number",
    "report_date",
    "accepted_at",
    "items",
    "evidence_status",
)
CATEGORY_FIELDS: dict[str, tuple[str, ...]] = {
    "events": EVENT_FIELDS,
    "economic_releases": ECONOMIC_RELEASE_FIELDS,
    "market_internals": METRIC_FIELDS,
    "positioning_flows": METRIC_FIELDS,
    "company_events": COMPANY_EVENT_FIELDS,
    "commodity_fundamentals": METRIC_FIELDS,
    "financial_conditions": METRIC_FIELDS,
    "source_log": SOURCE_LOG_FIELDS,
}


def _safe_provider_name(name: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "_" for character in name)


def run_weekly_context(
    providers: Mapping[str, ContextProvider],
    raw_dir: str | Path | None = None,
    as_of_date: date | None = None,
) -> dict[str, list[dict]]:
    tables = {category: [] for category in CATEGORY_FILES}
    raw_path = Path(raw_dir) if raw_dir else None
    if raw_path:
        raw_path.mkdir(parents=True, exist_ok=True)
    run_date = as_of_date or date.today()

    for provider_name, provider in providers.items():
        started = time.monotonic()
        try:
            if provider_name != provider.spec.name:
                raise ValueError(
                    f"Provider mapping key {provider_name!r} does not match "
                    f"ProviderSpec name {provider.spec.name!r}"
                )
            result = provider.fetch()
            if result.category != provider.spec.category:
                raise ValueError(
                    f"Provider result category {result.category!r} does not match "
                    f"ProviderSpec category {provider.spec.category!r}"
                )
            rows = (
                normalize_economic_release_rows(result.rows)
                if result.category == "economic_releases"
                else normalize_metric_rows(result.rows)
                if result.category != "events"
                else [dict(row) for row in result.rows]
            )
            if provider.spec.category not in tables or provider.spec.category == "source_log":
                raise ValueError(f"Unsupported context category: {result.category}")
            if raw_path:
                raw_content = (
                    result.raw_text
                    if isinstance(result.raw_text, bytes)
                    else result.raw_text.encode("utf-8")
                )
                (raw_path / f"{_safe_provider_name(provider_name)}.raw").write_bytes(
                    raw_content
                )
            rows_declare_known_as_of = any(
                "known_as_of" in row for row in rows
            )
            if rows_declare_known_as_of:
                rows = filter_known_as_of(rows, run_date)
                if not rows:
                    unavailable_note = (
                        "No rows are known on or before target Sunday "
                        f"{run_date.isoformat()}."
                    )
                    notes = "; ".join(
                        note for note in (result.notes, unavailable_note) if note
                    )
                    tables["source_log"].append(
                        {
                            "provider": provider_name,
                            "source_tier": provider.spec.source_tier,
                            "requiredness": provider.spec.requiredness,
                            "provider_version": provider.spec.provider_version,
                            "schema_version": provider.spec.schema_version,
                            "frequency": provider.spec.frequency,
                            "freshness_days": provider.spec.freshness_days,
                            "latest_known_as_of": None,
                            "warnings": notes,
                            "category": provider.spec.category,
                            "status": "POINT_IN_TIME_UNAVAILABLE",
                            "observations": 0,
                            "as_of_date": run_date.isoformat(),
                            "source": result.source,
                            "source_url": result.source_url,
                            "elapsed_ms": int((time.monotonic() - started) * 1000),
                            "notes": notes,
                        }
                    )
                    continue
            tables[provider.spec.category].extend(rows)
            tables["source_log"].append(
                {
                    "provider": provider_name,
                    "source_tier": provider.spec.source_tier,
                    "requiredness": provider.spec.requiredness,
                    "provider_version": provider.spec.provider_version,
                    "schema_version": provider.spec.schema_version,
                    "frequency": provider.spec.frequency,
                    "freshness_days": provider.spec.freshness_days,
                    "latest_known_as_of": _latest_known_as_of(rows),
                    "warnings": result.notes,
                    "category": provider.spec.category,
                    "status": result.status,
                    "observations": len(rows),
                    "as_of_date": run_date.isoformat(),
                    "source": result.source,
                    "source_url": result.source_url,
                    "elapsed_ms": int((time.monotonic() - started) * 1000),
                    "notes": result.notes,
                }
            )
        except Exception as error:
            tables["source_log"].append(
                {
                    "provider": provider_name,
                    "source_tier": provider.spec.source_tier,
                    "requiredness": provider.spec.requiredness,
                    "provider_version": provider.spec.provider_version,
                    "schema_version": provider.spec.schema_version,
                    "frequency": provider.spec.frequency,
                    "freshness_days": provider.spec.freshness_days,
                    "latest_known_as_of": None,
                    "warnings": str(error),
                    "category": provider.spec.category,
                    "status": "FETCH_FAILED",
                    "observations": 0,
                    "as_of_date": run_date.isoformat(),
                    "source": provider.spec.failure_source or None,
                    "source_url": provider.spec.failure_source_url or None,
                    "elapsed_ms": int((time.monotonic() - started) * 1000),
                    "notes": str(error),
                }
            )
    _validate_combined_economic_releases(tables, run_date)
    return tables


def _validate_combined_economic_releases(
    tables: dict[str, list[dict]],
    as_of_date: date,
) -> None:
    try:
        tables["economic_releases"] = normalize_economic_release_rows(
            tables["economic_releases"]
        )
        validate_economic_release_input_references(tables["economic_releases"])
    except ValueError as error:
        tables["economic_releases"] = []
        tables["source_log"].append(
            {
                "provider": "economic_releases_validation",
                "source_tier": "public",
                "requiredness": "required",
                "provider_version": "economic-release-v1",
                "schema_version": "economic-release-v1",
                "frequency": "event",
                "freshness_days": None,
                "latest_known_as_of": None,
                "warnings": str(error),
                "category": "economic_releases",
                "status": "FETCH_FAILED",
                "observations": 0,
                "as_of_date": as_of_date.isoformat(),
                "source": None,
                "source_url": None,
                "elapsed_ms": 0,
                "notes": str(error),
            }
        )


def _latest_known_as_of(rows: list[dict]) -> str | None:
    known_values: list[tuple[datetime, str]] = []
    for row in rows:
        if not row.get("known_as_of"):
            continue
        raw = str(row["known_as_of"])
        known = datetime.fromisoformat(raw)
        if known.tzinfo is None:
            raise ValueError("known_as_of must include a UTC offset")
        known_values.append((known, raw))
    return max(known_values, default=(None, None), key=lambda item: item[0])[1]


def _json_ready(value):
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, (date, pd.Timestamp)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def publish_weekly_context_bundle(
    tables: dict[str, list[dict]],
    output_dir: str | Path,
) -> None:
    destination = Path(output_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent)
    )
    backup = destination.with_name(f".{destination.name}.backup")
    try:
        for category, filename in CATEGORY_FILES.items():
            pd.DataFrame(
                tables.get(category, []), columns=CATEGORY_FIELDS[category]
            ).to_csv(
                staging / filename, index=False
            )
        snapshot = {
            category: _json_ready(tables.get(category, []))
            for category in CATEGORY_FILES
        }
        (staging / "weekly_context_snapshot.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        if backup.exists():
            shutil.rmtree(backup)
        if destination.exists():
            os.replace(destination, backup)
        try:
            os.replace(staging, destination)
        except Exception:
            if backup.exists():
                os.replace(backup, destination)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


__all__ = [
    "CATEGORY_FIELDS",
    "ProviderResult",
    "normalize_metric_rows",
    "publish_weekly_context_bundle",
    "run_weekly_context",
]
