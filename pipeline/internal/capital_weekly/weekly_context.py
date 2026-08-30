from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from typing import Mapping, Sequence
from urllib.parse import quote, quote_plus

import pandas as pd

from pipeline.internal.common import sanitize_audit_bytes, sanitize_audit_text

from .commodity_research import (
    METRIC_HISTORY_FIELDS,
    bounded_metric_history,
)

from .context.common import (
    METRIC_FIELDS,
    normalize_metric_rows,
    validate_provider_attempts,
    validate_provider_phase,
)
from .context.economic_releases import (
    ECONOMIC_RELEASE_FIELDS,
    normalize_economic_release_rows,
    validate_economic_release_input_references,
)
from .context.provider_contracts import (
    ContextProvider,
    ProviderPhaseError,
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
    "commodity_metric_history": "commodity_metric_history.csv",
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
    "phase",
    "attempts",
    "error_code",
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
    "commodity_metric_history": METRIC_HISTORY_FIELDS,
    "financial_conditions": METRIC_FIELDS,
    "source_log": SOURCE_LOG_FIELDS,
}


def _safe_provider_name(name: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "_" for character in name)


def run_weekly_context(
    providers: Mapping[str, ContextProvider],
    raw_dir: str | Path | None = None,
    as_of_date: date | None = None,
    audit_secrets: Sequence[str] = (),
    history_limits: Mapping[str, object] | None = None,
    commodity_registry: Mapping[str, object] | None = None,
) -> dict[str, list[dict]]:
    normalized_audit_secrets = _normalize_audit_secrets(audit_secrets)
    tables = {category: [] for category in CATEGORY_FILES}
    commodity_history_inputs: list[dict] = []
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
            completed_phase = validate_provider_phase(
                result.completed_phase,
                completed=result.status == "OK",
            )
            attempts = validate_provider_attempts(result.attempts)
            if result.category != provider.spec.category:
                raise ValueError(
                    f"Provider result category {result.category!r} does not match "
                    f"ProviderSpec category {provider.spec.category!r}"
                )
            safe_result_notes = sanitize_audit_text(
                result.notes,
                secrets=normalized_audit_secrets,
            )
            safe_result_source_url = sanitize_audit_text(
                result.source_url,
                secrets=normalized_audit_secrets,
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
            if (
                not result.raw_is_diagnostic
                and _contains_configured_secret(
                    result.raw_text,
                    normalized_audit_secrets,
                )
            ):
                qualifier = "Successful " if result.status == "OK" else ""
                raise ValueError(
                    f"{qualifier}raw source contains a configured credential"
                )
            if raw_path:
                if isinstance(result.raw_text, bytes) and result.raw_is_diagnostic:
                    raw_content = sanitize_audit_bytes(
                        result.raw_text,
                        secrets=normalized_audit_secrets,
                    )
                elif result.raw_is_diagnostic:
                    raw_content = sanitize_audit_text(
                        result.raw_text,
                        secrets=normalized_audit_secrets,
                    ).encode("utf-8")
                elif isinstance(result.raw_text, bytes):
                    raw_content = result.raw_text
                else:
                    raw_content = result.raw_text.encode("utf-8")
                (raw_path / f"{_safe_provider_name(provider_name)}.raw").write_bytes(
                    raw_content
                )
            rows_declare_known_as_of = any(
                row.get("known_as_of") is not None for row in rows
            )
            if rows_declare_known_as_of:
                rows = filter_known_as_of(rows, run_date)
                if not rows:
                    unavailable_note = (
                        "No rows are known on or before target Sunday "
                        f"{run_date.isoformat()}."
                    )
                    notes = "; ".join(
                        note
                        for note in (safe_result_notes, unavailable_note)
                        if note
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
                            "source_url": safe_result_source_url,
                            "elapsed_ms": int((time.monotonic() - started) * 1000),
                            "notes": notes,
                            "phase": completed_phase,
                            "attempts": attempts,
                            "error_code": None,
                        }
                    )
                    continue
            for row in rows:
                if row.get("source_url") is not None:
                    row["source_url"] = sanitize_audit_text(
                        row["source_url"],
                        secrets=normalized_audit_secrets,
                    )
            if (
                result.status == "OK"
                and result.category
                in {"commodity_fundamentals", "positioning_flows"}
            ):
                commodity_history_inputs.extend(
                    row
                    for row in rows
                    if row.get("commodity_code") not in (None, "")
                )
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
                    "warnings": safe_result_notes,
                    "category": provider.spec.category,
                    "status": result.status,
                    "observations": len(rows),
                    "as_of_date": run_date.isoformat(),
                    "source": result.source,
                    "source_url": safe_result_source_url,
                    "elapsed_ms": int((time.monotonic() - started) * 1000),
                    "notes": safe_result_notes,
                    "phase": completed_phase,
                    "attempts": attempts,
                    "error_code": None,
                }
            )
        except Exception as error:
            phase, attempts, error_code, safe_error = _provider_error_metadata(
                error,
                secrets=normalized_audit_secrets,
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
                    "warnings": safe_error,
                    "category": provider.spec.category,
                    "status": "FETCH_FAILED",
                    "observations": 0,
                    "as_of_date": run_date.isoformat(),
                    "source": None,
                    "source_url": None,
                    "elapsed_ms": int((time.monotonic() - started) * 1000),
                    "notes": safe_error,
                    "phase": phase,
                    "attempts": attempts,
                    "error_code": error_code,
                }
            )
    _validate_combined_economic_releases(
        tables,
        run_date,
        audit_secrets=normalized_audit_secrets,
    )
    if history_limits is None and commodity_registry is None:
        tables["commodity_metric_history"] = []
    elif history_limits is None or commodity_registry is None:
        raise ValueError(
            "history_limits and commodity_registry must be injected together"
        )
    else:
        tables["commodity_metric_history"] = bounded_metric_history(
            commodity_history_inputs,
            run_date,
            history_limits,
            commodity_registry,
        )
    return tables


def _normalize_audit_secrets(secrets: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw_secret in secrets:
        secret = str(raw_secret).strip()
        if secret and secret not in normalized:
            normalized.append(secret)
    return tuple(normalized)


def _contains_configured_secret(
    raw_content: str | bytes,
    secrets: Sequence[str],
) -> bool:
    content = (
        raw_content
        if isinstance(raw_content, bytes)
        else raw_content.encode("utf-8")
    )
    for secret in secrets:
        candidates = {
            secret,
            quote(secret, safe=""),
            quote_plus(secret, safe=""),
        }
        if any(candidate.encode("utf-8") in content for candidate in candidates):
            return True
    return False


def _provider_error_metadata(
    error: Exception,
    *,
    secrets: Sequence[str],
) -> tuple[str, int, str, str]:
    if isinstance(error, ProviderPhaseError):
        try:
            phase = validate_provider_phase(error.failure_phase, completed=False)
            attempts = validate_provider_attempts(error.attempts)
        except ValueError:
            pass
        else:
            return (
                phase,
                attempts,
                sanitize_audit_text(error.error_code, secrets=secrets),
                sanitize_audit_text(error.safe_message, secrets=secrets),
            )
    return (
        "retrieve",
        1,
        "UNCLASSIFIED_PROVIDER_FAILURE",
        sanitize_audit_text(error, secrets=secrets),
    )


def _validate_combined_economic_releases(
    tables: dict[str, list[dict]],
    as_of_date: date,
    *,
    audit_secrets: tuple[str, ...] = (),
) -> None:
    try:
        tables["economic_releases"] = normalize_economic_release_rows(
            tables["economic_releases"]
        )
        validate_economic_release_input_references(tables["economic_releases"])
    except ValueError as error:
        safe_error = sanitize_audit_text(error, secrets=audit_secrets)
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
                "warnings": safe_error,
                "category": "economic_releases",
                "status": "FETCH_FAILED",
                "observations": 0,
                "as_of_date": as_of_date.isoformat(),
                "source": None,
                "source_url": None,
                "elapsed_ms": 0,
                "notes": safe_error,
                "phase": "normalized",
                "attempts": 1,
                "error_code": "UNCLASSIFIED_PROVIDER_FAILURE",
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
