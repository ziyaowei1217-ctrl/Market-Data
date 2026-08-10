from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .equity_indices import _session, fetch_history, source_url
from .returns import calculate_return_snapshot


DEFAULT_UNIVERSE_PATH = Path("data/capital_weekly_gics_sectors.csv")


@dataclass(frozen=True)
class SectorConfig:
    gics_sector_code: str
    sector_name_cn: str
    sector_name_en: str
    ticker: str
    currency: str
    provider: str
    provider_symbol: str
    source: str
    proxy_type: str
    notes: str = ""

    @property
    def region(self) -> str:
        return "US GICS"

    @property
    def index_name_cn(self) -> str:
        return self.sector_name_cn

    @property
    def index_name_en(self) -> str:
        return self.sector_name_en


def load_sector_universe(path: str | Path = DEFAULT_UNIVERSE_PATH) -> list[SectorConfig]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        return [SectorConfig(**row) for row in csv.DictReader(file)]


def _series_for_returns(history: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {"date": row.date, "value": float(row.close)}
        for row in history.itertuples(index=False)
    ]


def _snapshot_row(config: SectorConfig, snapshot: Any, url: str) -> dict[str, Any]:
    row = asdict(config)
    row.update(
        {
            "latest_date": snapshot.latest_date.isoformat(),
            "latest_value": snapshot.latest_value,
            "daily_base_date": snapshot.daily_base_date.isoformat()
            if snapshot.daily_base_date
            else None,
            "daily_base_value": snapshot.daily_base_value,
            "daily_change": snapshot.daily_change,
            "weekly_base_date": snapshot.weekly_base_date.isoformat()
            if snapshot.weekly_base_date
            else None,
            "weekly_base_value": snapshot.weekly_base_value,
            "weekly_change": snapshot.weekly_change,
            "mtd_base_date": snapshot.mtd_base_date.isoformat()
            if snapshot.mtd_base_date
            else None,
            "mtd_base_value": snapshot.mtd_base_value,
            "mtd_change": snapshot.mtd_change,
            "ytd_base_date": snapshot.ytd_base_date.isoformat()
            if snapshot.ytd_base_date
            else None,
            "ytd_base_value": snapshot.ytd_base_value,
            "ytd_change": snapshot.ytd_change,
            "change_unit": snapshot.change_unit,
            "qc_flag": snapshot.qc_flag,
            "source_url": url,
        }
    )
    return row


def fetch_gics_sectors(
    universe_path: str | Path = DEFAULT_UNIVERSE_PATH,
    raw_dir: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    session = _session()
    rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    raw_path = Path(raw_dir) if raw_dir else None
    if raw_path:
        raw_path.mkdir(parents=True, exist_ok=True)

    for sector in load_sector_universe(universe_path):
        url = source_url(sector)
        started_at = datetime.now()
        try:
            history, raw_text = fetch_history(sector, session=session)
            if raw_path:
                (raw_path / f"{sector.ticker}.txt").write_text(raw_text, encoding="utf-8")
            snapshot = calculate_return_snapshot(_series_for_returns(history), "pct")
            rows.append(_snapshot_row(sector, snapshot, url))
            source_rows.append(
                {
                    "ticker": sector.ticker,
                    "gics_sector_code": sector.gics_sector_code,
                    "sector_name_en": sector.sector_name_en,
                    "source": sector.source,
                    "status": "OK",
                    "observations": len(history),
                    "latest_date": snapshot.latest_date.isoformat(),
                    "latest_value": snapshot.latest_value,
                    "daily_base_date": snapshot.daily_base_date.isoformat(),
                    "daily_base_value": snapshot.daily_base_value,
                    "weekly_base_date": snapshot.weekly_base_date.isoformat()
                    if snapshot.weekly_base_date
                    else None,
                    "weekly_base_value": snapshot.weekly_base_value,
                    "mtd_base_date": snapshot.mtd_base_date.isoformat()
                    if snapshot.mtd_base_date
                    else None,
                    "mtd_base_value": snapshot.mtd_base_value,
                    "ytd_base_date": snapshot.ytd_base_date.isoformat()
                    if snapshot.ytd_base_date
                    else None,
                    "ytd_base_value": snapshot.ytd_base_value,
                    "elapsed_ms": int((datetime.now() - started_at).total_seconds() * 1000),
                    "source_url": url,
                    "notes": sector.notes,
                }
            )
        except Exception as error:
            failed = asdict(sector)
            failed.update(
                {
                    "latest_date": None,
                    "latest_value": None,
                    "daily_base_date": None,
                    "daily_base_value": None,
                    "daily_change": None,
                    "weekly_base_date": None,
                    "weekly_base_value": None,
                    "weekly_change": None,
                    "mtd_base_date": None,
                    "mtd_base_value": None,
                    "mtd_change": None,
                    "ytd_base_date": None,
                    "ytd_base_value": None,
                    "ytd_change": None,
                    "change_unit": "pct",
                    "qc_flag": "FETCH_FAILED",
                    "source_url": url,
                }
            )
            rows.append(failed)
            source_rows.append(
                {
                    "ticker": sector.ticker,
                    "gics_sector_code": sector.gics_sector_code,
                    "sector_name_en": sector.sector_name_en,
                    "source": sector.source,
                    "status": "FETCH_FAILED",
                    "observations": 0,
                    "latest_date": None,
                    "latest_value": None,
                    "daily_base_date": None,
                    "daily_base_value": None,
                    "weekly_base_date": None,
                    "weekly_base_value": None,
                    "mtd_base_date": None,
                    "mtd_base_value": None,
                    "ytd_base_date": None,
                    "ytd_base_value": None,
                    "elapsed_ms": int((datetime.now() - started_at).total_seconds() * 1000),
                    "source_url": url,
                    "notes": str(error),
                }
            )

    return pd.DataFrame(rows), pd.DataFrame(source_rows)
