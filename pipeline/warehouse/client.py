"""Read-only client for classmates and agents (no password needed).

    from pipeline.warehouse.client import weekly, latest, find
    df = weekly(["12-007", "12-003"], start="2024-01-01")   # long format
    wide = df.pivot(index="week_cutoff", columns="name", values="value")
    wide.plot()

Uses the Supabase REST API with the project's publishable key. Row-level
security only allows SELECT, so this key is safe to share.
"""

from __future__ import annotations

import os
from typing import Iterable

import pandas as pd
import requests

SUPABASE_URL = os.environ.get("WAREHOUSE_REST_URL", "https://ujomxngmefoplrsxmuyf.supabase.co")
PUBLISHABLE_KEY = os.environ.get("WAREHOUSE_PUBLISHABLE_KEY", "sb_publishable_d5Go9QOSznfvLdN2rTwnVw_Ib4aNktm")


def _get(table: str, params: dict) -> pd.DataFrame:
    headers = {"apikey": PUBLISHABLE_KEY, "Authorization": f"Bearer {PUBLISHABLE_KEY}"}
    rows: list[dict] = []
    offset = 0
    while True:
        page = {**params, "offset": offset, "limit": 1000}
        response = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", params=page, headers=headers, timeout=60)
        response.raise_for_status()
        batch = response.json()
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return pd.DataFrame(rows)


def weekly(indicator_ids: Iterable[str], start: str | None = None, only_ok: bool = True) -> pd.DataFrame:
    """Weekly values (week_cutoff, indicator_id, name, unit, value, obs_date, status)."""
    ids = ",".join(indicator_ids)
    params = {"indicator_id": f"in.({ids})", "order": "week_cutoff",
              "select": "week_cutoff,indicator_id,name,unit,value,obs_date,status"}
    if start:
        params["week_cutoff"] = f"gte.{start}"
    if only_ok:
        params["status"] = "eq.ok"
    df = _get("weekly", params)
    if not df.empty:
        df["week_cutoff"] = pd.to_datetime(df["week_cutoff"])
    return df


def latest(module: str | None = None) -> pd.DataFrame:
    params = {"select": "indicator_id,module,name,unit,value,obs_date,status", "order": "indicator_id"}
    if module:
        params["module"] = f"eq.{module}"
    return _get("latest_week", params)


def find(text: str) -> pd.DataFrame:
    """Search the catalog by name, e.g. find('CPI')."""
    return _get("catalog", {"name": f"ilike.*{text}*",
                            "select": "indicator_id,module,name,unit,method,coverage_note,first_week,last_week"})


def series(series_key: str, start: str | None = None) -> pd.DataFrame:
    """Raw observations (latest version) in native frequency, e.g. series('FRED:DGS10')."""
    params = {"series_key": f"eq.{series_key}", "order": "obs_date", "select": "obs_date,value,realtime_start"}
    if start:
        params["obs_date"] = f"gte.{start}"
    return _get("obs_latest", params)
