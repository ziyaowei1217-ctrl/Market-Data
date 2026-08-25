from __future__ import annotations

import csv
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .equity_indices import (
    _drop_unfinished_current_day,
    _session,
    fetch_history,
    source_url,
)
from .history import truncate_history_as_of
from .returns import calculate_return_snapshot


DEFAULT_UNIVERSE_PATH = Path("pipeline/config/capital_weekly_equity_sectors.csv")


@dataclass(frozen=True)
class EquitySectorConfig:
    market: str
    taxonomy: str
    taxonomy_version: str
    taxonomy_level: str
    sector_code: str
    sector_name_cn: str
    sector_name_en: str
    ticker: str
    currency: str
    provider: str
    provider_symbol: str
    source: str
    instrument_type: str
    sort_order: int
    notes: str = ""


def load_sector_universe(
    path: str | Path = DEFAULT_UNIVERSE_PATH,
) -> list[EquitySectorConfig]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        rows = []
        for raw in csv.DictReader(file):
            raw["sort_order"] = int(raw["sort_order"])
            rows.append(EquitySectorConfig(**raw))
    return rows


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None


def _snapshot_fields(snapshot: Any) -> dict[str, Any]:
    return {
        "latest_date": _iso(snapshot.latest_date),
        "latest_value": snapshot.latest_value,
        "daily_base_date": _iso(snapshot.daily_base_date),
        "daily_base_value": snapshot.daily_base_value,
        "daily_change": snapshot.daily_change,
        "weekly_base_date": _iso(snapshot.weekly_base_date),
        "weekly_base_value": snapshot.weekly_base_value,
        "weekly_change": snapshot.weekly_change,
        "mtd_base_date": _iso(snapshot.mtd_base_date),
        "mtd_base_value": snapshot.mtd_base_value,
        "mtd_change": snapshot.mtd_change,
        "ytd_base_date": _iso(snapshot.ytd_base_date),
        "ytd_base_value": snapshot.ytd_base_value,
        "ytd_change": snapshot.ytd_change,
        "change_unit": snapshot.change_unit,
        "qc_flag": snapshot.qc_flag,
    }


def _series_for_returns(history: pd.DataFrame) -> list[dict[str, Any]]:
    return [{"date": row.date, "value": float(row.close)} for row in history.itertuples(index=False)]


def _success_row(config: EquitySectorConfig, snapshot: Any, url: str) -> dict[str, Any]:
    row = asdict(config)
    row.update(_snapshot_fields(snapshot))
    row["source_url"] = url
    return row


def _failed_row(config: EquitySectorConfig, url: str, error: Exception) -> dict[str, Any]:
    row = asdict(config)
    for key in (
        "latest_date", "latest_value", "daily_base_date", "daily_base_value",
        "daily_change", "weekly_base_date", "weekly_base_value", "weekly_change",
        "mtd_base_date", "mtd_base_value", "mtd_change", "ytd_base_date",
        "ytd_base_value", "ytd_change",
    ):
        row[key] = None
    row.update({"change_unit": "pct", "qc_flag": "FETCH_FAILED", "source_url": url,
                "notes": " | ".join(part for part in (config.notes, str(error)) if part)})
    return row


def _success_source_row(config: EquitySectorConfig, history: pd.DataFrame, snapshot: Any,
                        url: str, started_at: datetime) -> dict[str, Any]:
    fields = _snapshot_fields(snapshot)
    return {
        "market": config.market, "taxonomy": config.taxonomy, "sector_code": config.sector_code,
        "sector_name_en": config.sector_name_en, "ticker": config.ticker,
        "sort_order": config.sort_order, "source": config.source, "status": "OK",
        "observations": len(history),
        **{key: fields[key] for key in (
            "latest_date", "latest_value", "daily_base_date", "daily_base_value",
            "weekly_base_date", "weekly_base_value", "mtd_base_date", "mtd_base_value",
            "ytd_base_date", "ytd_base_value",
        )},
        "elapsed_ms": int((datetime.now() - started_at).total_seconds() * 1000),
        "source_url": url, "notes": config.notes,
    }


def _failed_source_row(config: EquitySectorConfig, url: str, error: Exception,
                       started_at: datetime) -> dict[str, Any]:
    row = {
        "market": config.market, "taxonomy": config.taxonomy, "sector_code": config.sector_code,
        "sector_name_en": config.sector_name_en, "ticker": config.ticker,
        "sort_order": config.sort_order, "source": config.source, "status": "FETCH_FAILED",
        "observations": 0,
        "elapsed_ms": int((datetime.now() - started_at).total_seconds() * 1000),
        "source_url": url,
        "notes": " | ".join(part for part in (config.notes, str(error)) if part),
    }
    for key in (
        "latest_date", "latest_value", "daily_base_date", "daily_base_value",
        "weekly_base_date", "weekly_base_value", "mtd_base_date", "mtd_base_value",
        "ytd_base_date", "ytd_base_value",
    ):
        row[key] = None
    return row


def _atomic_write_text(path: Path, text: str) -> None:
    """Durably stage text beside its destination, then publish it atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as file:
            temp_path = Path(file.name)
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def fetch_equity_sectors(
    universe_path: str | Path = DEFAULT_UNIVERSE_PATH,
    raw_dir: str | Path | None = None,
    as_of_date: date | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    session = _session()
    rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    raw_path = Path(raw_dir) if raw_dir else None
    if raw_path:
        raw_path.mkdir(parents=True, exist_ok=True)

    for config in load_sector_universe(universe_path):
        started_at = datetime.now()
        url = ""
        try:
            url = source_url(config)
            history, raw_text = fetch_history(config, session=session)
            history = _drop_unfinished_current_day(history, config)
            history = truncate_history_as_of(history, as_of_date)
            snapshot = calculate_return_snapshot(_series_for_returns(history), "pct")
            raw_cache_status = "DISABLED"
            raw_cache_error = ""
            if raw_path:
                safe_ticker = config.ticker.replace(".", "_").replace("/", "_")
                try:
                    _atomic_write_text(raw_path / f"{safe_ticker}.txt", raw_text)
                    raw_cache_status = "OK"
                except Exception as cache_error:
                    raw_cache_status = "CACHE_WRITE_FAILED"
                    raw_cache_error = str(cache_error)
            rows.append(_success_row(config, snapshot, url))
            source_row = _success_source_row(config, history, snapshot, url, started_at)
            source_row.update({
                "raw_cache_status": raw_cache_status,
                "raw_cache_error": raw_cache_error,
            })
            source_rows.append(source_row)
        except Exception as error:
            rows.append(_failed_row(config, url, error))
            source_row = _failed_source_row(config, url, error, started_at)
            source_row.update({"raw_cache_status": "NOT_WRITTEN", "raw_cache_error": ""})
            source_rows.append(source_row)

    data = pd.DataFrame(rows).sort_values(["market", "sort_order"], kind="stable")
    source_log = pd.DataFrame(source_rows).sort_values(["market", "sort_order"], kind="stable")
    return data.reset_index(drop=True), source_log.reset_index(drop=True)
