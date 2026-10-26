"""Read-only client for classmates and agents (sign-in required).

    export WAREHOUSE_EMAIL=you@example.com WAREHOUSE_PASSWORD=...
    from pipeline.warehouse.client import weekly, latest, find
    df = weekly(["12-007", "12-003"], start="2024-01-01")   # long format
    wide = df.pivot(index="week_cutoff", columns="name", values="value")
    wide.plot()

Reading needs a Supabase Auth account whose (confirmed) email is on the
``readers`` list kept by the database owner. First time only:

    python3 -m pipeline.warehouse.client signup you@example.com   # then click the email link

The publishable key below only identifies the project; without a signed-in
reader it returns no rows.
"""

from __future__ import annotations

import getpass
import os
import sys
import time
from typing import Iterable

import pandas as pd
import requests

SUPABASE_URL = os.environ.get("WAREHOUSE_REST_URL", "https://ujomxngmefoplrsxmuyf.supabase.co")
PUBLISHABLE_KEY = os.environ.get("WAREHOUSE_PUBLISHABLE_KEY", "sb_publishable_d5Go9QOSznfvLdN2rTwnVw_Ib4aNktm")

_session: dict = {}


def signup(email: str, password: str) -> None:
    """Create an account; Supabase emails a confirmation link. Ask the owner to add the email to readers."""
    r = requests.post(f"{SUPABASE_URL}/auth/v1/signup", json={"email": email, "password": password},
                      headers={"apikey": PUBLISHABLE_KEY}, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"signup failed: {r.status_code} {r.text[:200]}")


def login(email: str | None = None, password: str | None = None) -> None:
    """Sign in with email and password (defaults: WAREHOUSE_EMAIL / WAREHOUSE_PASSWORD)."""
    email = email or os.environ.get("WAREHOUSE_EMAIL")
    password = password or os.environ.get("WAREHOUSE_PASSWORD")
    if not email or not password:
        raise RuntimeError("set WAREHOUSE_EMAIL and WAREHOUSE_PASSWORD, or call login(email, password)")
    r = requests.post(f"{SUPABASE_URL}/auth/v1/token", params={"grant_type": "password"},
                      json={"email": email, "password": password}, headers={"apikey": PUBLISHABLE_KEY}, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"login failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    _session.update(token=data["access_token"], expires=time.time() + int(data.get("expires_in", 3600)) - 60)


def _token() -> str:
    if os.environ.get("WAREHOUSE_ACCESS_TOKEN"):
        return os.environ["WAREHOUSE_ACCESS_TOKEN"]
    if not _session or time.time() >= _session["expires"]:
        login()
    return _session["token"]


def _get(table: str, params: dict) -> pd.DataFrame:
    headers = {"apikey": PUBLISHABLE_KEY, "Authorization": f"Bearer {_token()}"}
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
    return pd.DataFrame(rows)  # empty when the account is not on the readers list


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


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "signup":
        signup(sys.argv[2], getpass.getpass("password: "))
        print("check your inbox for the confirmation link, then ask the owner to add you to readers")
    else:
        print("usage: python3 -m pipeline.warehouse.client signup you@example.com")
