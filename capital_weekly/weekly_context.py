from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd

from .context.common import normalize_metric_rows


CATEGORY_FILES = {
    "events": "events.csv",
    "market_internals": "market_internals.csv",
    "positioning_flows": "positioning_flows.csv",
    "company_events": "company_events.csv",
    "commodity_fundamentals": "commodity_fundamentals.csv",
    "financial_conditions": "financial_conditions.csv",
    "source_log": "source_log.csv",
}


@dataclass(frozen=True)
class ProviderResult:
    category: str
    rows: list[dict]
    raw_text: str | bytes
    source: str
    source_url: str
    status: str = "OK"
    notes: str = ""


def _safe_provider_name(name: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "_" for character in name)


def run_weekly_context(
    providers: dict[str, Callable[[], ProviderResult]],
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
            result = provider()
            rows = (
                normalize_metric_rows(result.rows)
                if result.category != "events"
                else [dict(row) for row in result.rows]
            )
            if result.category not in tables or result.category == "source_log":
                raise ValueError(f"Unsupported context category: {result.category}")
            tables[result.category].extend(rows)
            if raw_path:
                raw_content = (
                    result.raw_text
                    if isinstance(result.raw_text, bytes)
                    else result.raw_text.encode("utf-8")
                )
                (raw_path / f"{_safe_provider_name(provider_name)}.raw").write_bytes(
                    raw_content
                )
            tables["source_log"].append(
                {
                    "provider": provider_name,
                    "category": result.category,
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
                    "category": None,
                    "status": "FETCH_FAILED",
                    "observations": 0,
                    "as_of_date": run_date.isoformat(),
                    "source": None,
                    "source_url": None,
                    "elapsed_ms": int((time.monotonic() - started) * 1000),
                    "notes": str(error),
                }
            )
    return tables


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
            pd.DataFrame(tables.get(category, [])).to_csv(
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
    "ProviderResult",
    "normalize_metric_rows",
    "publish_weekly_context_bundle",
    "run_weekly_context",
]
