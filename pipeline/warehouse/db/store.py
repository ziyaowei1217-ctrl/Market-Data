"""Storage backends: Postgres (Supabase) for production, SQLite for tests/offline.

Observations are versioned. ``write_observations`` only inserts a row when an
observation is new or its value changed, so revisions accumulate over time:

* provider vintages (ALFRED) are stored as given (``vintage_source='provider'``);
* the very first load of a series is dated ``obs_date + release_lag_days``
  (``backfill_estimate``) because the true publication date is unknown;
* anything that appears or changes later is dated by the fetch day (``first_seen``).
"""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

SCHEMA_SQL = Path(__file__).with_name("schema.sql")
VALUE_TOLERANCE = 1e-9

INDICATOR_COLUMNS = [
    "indicator_id", "module", "name", "definition", "unit", "source_freq", "weekly_rule", "cost",
    "source_desc", "limits", "source_url", "extra_url", "check_status", "evidence", "catalog_version",
    "method", "phase", "formula", "coverage_note",
]
SERIES_COLUMNS = [
    "series_key", "provider", "code", "params", "title", "frequency", "unit", "source_url",
    "release_lag_days", "vintages",
]


@dataclass(frozen=True)
class Observation:
    obs_date: date
    value: float | None
    realtime_start: date | None = None  # provider vintage, if any


def _clean(value: float | None) -> float | None:
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def plan_new_rows(
    existing_latest: dict[date, float | None],
    has_rows: bool,
    observations: Sequence[Observation],
    *,
    fetch_day: date,
    release_lag_days: int,
) -> list[tuple[date, date, float | None, str]]:
    """Decide which (obs_date, realtime_start, value, vintage_source) rows to insert."""
    rows: list[tuple[date, date, float | None, str]] = []
    for obs in observations:
        value = _clean(obs.value)
        if obs.realtime_start is not None:
            rows.append((obs.obs_date, obs.realtime_start, value, "provider"))
            continue
        if obs.obs_date in existing_latest:
            old = existing_latest[obs.obs_date]
            same = (old is None and value is None) or (
                old is not None and value is not None and abs(old - value) <= VALUE_TOLERANCE * max(1.0, abs(old))
            )
            if same:
                continue
            rows.append((obs.obs_date, fetch_day, value, "first_seen"))
        elif not has_rows:
            estimate = min(obs.obs_date + timedelta(days=release_lag_days), fetch_day)
            rows.append((obs.obs_date, estimate, value, "backfill_estimate"))
        else:
            rows.append((obs.obs_date, fetch_day, value, "first_seen"))
    # Skip value-less rows for brand-new observations: missing stays absent.
    return [r for r in rows if r[2] is not None or r[0] in existing_latest]


class Store:
    """Interface shared by both backends."""

    def init_schema(self) -> None: ...
    def upsert_indicators(self, rows: Iterable[dict]) -> int: ...
    def upsert_series(self, rows: Iterable[dict]) -> int: ...
    def latest_values(self, series_key: str) -> tuple[dict[date, float | None], bool]: ...
    def insert_observations(self, series_key: str, rows: list[tuple[date, date, float | None, str]]) -> int: ...
    def update_series_status(self, series_key: str, status: str, message: str) -> None: ...
    def load_observations(self, keys: Sequence[str], since: date | None = None) -> dict[str, pd.DataFrame]: ...
    def upsert_weekly(self, rows: Iterable) -> int: ...
    def log(self, run_id: str, runner: str, provider: str, series_key: str | None, status: str, rows: int, message: str) -> None: ...
    def weekly_count(self) -> int: ...
    def upsert_report_pages(self, source: str, report_date: date, url: str, pages: Sequence[str]) -> int: ...
    def indicator_formulas(self) -> dict[str, str]: ...
    def prune_series(self, keep: Sequence[str]) -> int: ...
    def get_meta(self, key: str) -> str | None: ...
    def earliest_obs(self, series_key: str) -> date | None: ...
    def set_meta(self, key: str, value: str) -> None: ...
    def close(self) -> None: ...

    last_write_initial: bool = False

    def write_observations(
        self, series_key: str, observations: Sequence[Observation], *, release_lag_days: int, fetch_day: date | None = None
    ) -> int:
        fetch_day = fetch_day or datetime.now(timezone.utc).date()
        existing, has_rows = self.latest_values(series_key)
        self.last_write_initial = not has_rows
        rows = plan_new_rows(
            existing, has_rows, observations, fetch_day=fetch_day, release_lag_days=release_lag_days
        )
        return self.insert_observations(series_key, rows) if rows else 0


def _frames_from_rows(rows, keys) -> dict[str, pd.DataFrame]:
    columns = ["series_key", "obs_date", "realtime_start", "value", "vintage_source"]
    df = pd.DataFrame(rows, columns=columns)
    out: dict[str, pd.DataFrame] = {}
    for key in keys:
        part = df[df["series_key"] == key].drop(columns=["series_key"])
        part = part.assign(
            obs_date=pd.to_datetime(part["obs_date"]),
            realtime_start=pd.to_datetime(part["realtime_start"]),
            value=pd.to_numeric(part["value"], errors="coerce"),
        )
        out[key] = part.reset_index(drop=True)
    return out


# --------------------------------------------------------------------------- SQLite


SQLITE_DDL = """
create table if not exists indicators (
  indicator_id text primary key, module text, name text, definition text, unit text, source_freq text,
  weekly_rule text, cost text, source_desc text, limits text, source_url text, extra_url text,
  check_status text, evidence text, catalog_version text, method text, phase text, formula text,
  coverage_note text, updated_at text);
create table if not exists series (
  series_key text primary key, provider text, code text, params text, title text, frequency text, unit text,
  source_url text, release_lag_days integer, vintages integer, first_obs text, last_obs text,
  last_fetched_at text, last_status text, last_message text);
create table if not exists observations (
  series_key text, obs_date text, realtime_start text, value real, vintage_source text, fetched_at text,
  primary key (series_key, obs_date, realtime_start));
create table if not exists weekly_values (
  indicator_id text, week_cutoff text, value real, obs_date text, status text, detail text, computed_at text,
  primary key (indicator_id, week_cutoff));
create table if not exists fetch_log (
  id integer primary key autoincrement, run_id text, runner text, provider text, series_key text,
  status text, rows_written integer, message text, logged_at text);
create table if not exists warehouse_meta (key text primary key, value text, updated_at text);
create table if not exists report_pages (
  source text, report_date text, page integer, url text, text text, fetched_at text,
  primary key (source, report_date, page));
"""


class SQLiteStore(Store):
    def __init__(self, path: str | Path = ":memory:"):
        self.conn = sqlite3.connect(str(path))

    def init_schema(self) -> None:
        self.conn.executescript(SQLITE_DDL)
        self.conn.commit()

    def upsert_indicators(self, rows):
        rows = list(rows)
        cols = INDICATOR_COLUMNS + ["updated_at"]
        now = datetime.now(timezone.utc).isoformat()
        self.conn.executemany(
            f"insert or replace into indicators ({','.join(cols)}) values ({','.join('?' * len(cols))})",
            [[r.get(c) for c in INDICATOR_COLUMNS] + [now] for r in rows],
        )
        self.conn.commit()
        return len(rows)

    def upsert_series(self, rows):
        rows = list(rows)
        for r in rows:
            self.conn.execute(
                f"""insert into series ({','.join(SERIES_COLUMNS)}) values ({','.join('?' * len(SERIES_COLUMNS))})
                on conflict(series_key) do update set provider=excluded.provider, code=excluded.code,
                params=excluded.params, title=excluded.title, frequency=excluded.frequency, unit=excluded.unit,
                source_url=excluded.source_url, release_lag_days=excluded.release_lag_days, vintages=excluded.vintages""",
                [json.dumps(r[c], ensure_ascii=False) if c == "params" else r.get(c) for c in SERIES_COLUMNS],
            )
        self.conn.commit()
        return len(rows)

    def latest_values(self, series_key):
        cur = self.conn.execute(
            "select obs_date, value from observations where series_key=? order by obs_date, realtime_start",
            (series_key,),
        )
        latest: dict[date, float | None] = {}
        for obs_date, value in cur:
            latest[date.fromisoformat(obs_date)] = value
        return latest, bool(latest)

    def insert_observations(self, series_key, rows):
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.executemany(
            "insert or ignore into observations values (?,?,?,?,?,?)",
            [(series_key, o.isoformat(), r.isoformat(), v, s, now) for o, r, v, s in rows],
        )
        self.conn.execute(
            """update series set first_obs=(select min(obs_date) from observations where series_key=?),
               last_obs=(select max(obs_date) from observations where series_key=?) where series_key=?""",
            (series_key, series_key, series_key),
        )
        self.conn.commit()
        return cur.rowcount if cur.rowcount >= 0 else len(rows)

    def update_series_status(self, series_key, status, message):
        self.conn.execute(
            "update series set last_status=?, last_message=?, last_fetched_at=? where series_key=?",
            (status, message[:500], datetime.now(timezone.utc).isoformat(), series_key),
        )
        self.conn.commit()

    def load_observations(self, keys, since=None):
        keys = list(keys)
        if not keys:
            return {}
        q = f"select series_key, obs_date, realtime_start, value, vintage_source from observations where series_key in ({','.join('?' * len(keys))})"
        params: list = list(keys)
        if since:
            q += " and obs_date >= ?"
            params.append(since.isoformat())
        return _frames_from_rows(self.conn.execute(q, params).fetchall(), keys)

    def upsert_weekly(self, rows):
        rows = list(rows)
        now = datetime.now(timezone.utc).isoformat()
        self.conn.executemany(
            "insert or replace into weekly_values values (?,?,?,?,?,?,?)",
            [(r.indicator_id, r.week_cutoff.isoformat(), r.value,
              r.obs_date.isoformat() if r.obs_date else None, r.status, r.detail, now) for r in rows],
        )
        self.conn.commit()
        return len(rows)

    def log(self, run_id, runner, provider, series_key, status, rows, message):
        self.conn.execute(
            "insert into fetch_log (run_id, runner, provider, series_key, status, rows_written, message, logged_at) values (?,?,?,?,?,?,?,?)",
            (run_id, runner, provider, series_key, status, rows, message[:1000], datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def weekly_count(self):
        return int(self.conn.execute("select count(*) from weekly_values").fetchone()[0])

    def indicator_formulas(self):
        return {r[0]: r[1] or "" for r in self.conn.execute("select indicator_id, formula from indicators")}

    def get_meta(self, key):
        row = self.conn.execute("select value from warehouse_meta where key=?", (key,)).fetchone()
        return row[0] if row else None

    def earliest_obs(self, series_key):
        row = self.conn.execute("select min(obs_date) from observations where series_key=?", (series_key,)).fetchone()
        return date.fromisoformat(row[0]) if row and row[0] else None

    def set_meta(self, key, value):
        self.conn.execute("insert or replace into warehouse_meta values (?,?,?)", (key, value, datetime.now(timezone.utc).isoformat()))
        self.conn.commit()

    def prune_series(self, keep):
        keep = list(keep)
        q = f"select series_key from series where series_key not in ({','.join('?' * len(keep))})"
        stale = [r[0] for r in self.conn.execute(q, keep)]
        for key in stale:
            self.conn.execute("delete from observations where series_key=?", (key,))
            self.conn.execute("delete from series where series_key=?", (key,))
        self.conn.commit()
        return len(stale)

    def upsert_report_pages(self, source, report_date, url, pages):
        now = datetime.now(timezone.utc).isoformat()
        self.conn.executemany(
            "insert or replace into report_pages values (?,?,?,?,?,?)",
            [(source, report_date.isoformat(), i + 1, url, text, now) for i, text in enumerate(pages)],
        )
        self.conn.commit()
        return len(pages)

    def close(self):
        self.conn.close()


# --------------------------------------------------------------------------- Postgres


class PostgresStore(Store):
    def __init__(self, dsn: str):
        import psycopg

        self.conn = psycopg.connect(dsn, autocommit=False, prepare_threshold=None)

    def init_schema(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        self.conn.commit()

    def upsert_indicators(self, rows):
        rows = list(rows)
        cols = INDICATOR_COLUMNS
        updates = ", ".join(f"{c}=excluded.{c}" for c in cols[1:])
        with self.conn.cursor() as cur:
            cur.executemany(
                f"insert into public.indicators ({','.join(cols)}) values ({','.join(['%s'] * len(cols))}) "
                f"on conflict (indicator_id) do update set {updates}, updated_at=now()",
                [[r.get(c) for c in cols] for r in rows],
            )
        self.conn.commit()
        return len(rows)

    def upsert_series(self, rows):
        rows = list(rows)
        cols = SERIES_COLUMNS
        updates = ", ".join(f"{c}=excluded.{c}" for c in cols[1:])
        with self.conn.cursor() as cur:
            cur.executemany(
                f"insert into public.series ({','.join(cols)}) values ({','.join(['%s'] * len(cols))}) "
                f"on conflict (series_key) do update set {updates}",
                [[json.dumps(r[c], ensure_ascii=False) if c == "params" else r.get(c) for c in cols] for r in rows],
            )
        self.conn.commit()
        return len(rows)

    def latest_values(self, series_key):
        with self.conn.cursor() as cur:
            cur.execute(
                "select distinct on (obs_date) obs_date, value from public.observations "
                "where series_key=%s order by obs_date, realtime_start desc",
                (series_key,),
            )
            latest = {row[0]: row[1] for row in cur.fetchall()}
        return latest, bool(latest)

    def insert_observations(self, series_key, rows):
        with self.conn.cursor() as cur:
            cur.execute(
                "create temp table if not exists _obs (obs_date date, realtime_start date, value double precision, vintage_source text) on commit drop"
            )
            with cur.copy("copy _obs (obs_date, realtime_start, value, vintage_source) from stdin") as copy:
                for row in rows:
                    copy.write_row(row)
            cur.execute(
                "insert into public.observations (series_key, obs_date, realtime_start, value, vintage_source) "
                "select %s, obs_date, realtime_start, value, vintage_source from _obs "
                "on conflict do nothing",
                (series_key,),
            )
            written = cur.rowcount
            cur.execute(
                """update public.series s set first_obs = x.mn, last_obs = x.mx
                   from (select min(obs_date) mn, max(obs_date) mx from public.observations where series_key=%s) x
                   where s.series_key=%s""",
                (series_key, series_key),
            )
        self.conn.commit()
        return written

    def update_series_status(self, series_key, status, message):
        with self.conn.cursor() as cur:
            cur.execute(
                "update public.series set last_status=%s, last_message=%s, last_fetched_at=now() where series_key=%s",
                (status, message[:500], series_key),
            )
        self.conn.commit()

    def load_observations(self, keys, since=None):
        keys = list(keys)
        if not keys:
            return {}
        q = ("select series_key, obs_date, realtime_start, value, vintage_source from public.observations "
             "where series_key = any(%s)")
        params: list = [keys]
        if since:
            q += " and obs_date >= %s"
            params.append(since)
        with self.conn.cursor() as cur:
            cur.execute(q, params)
            rows = cur.fetchall()
        return _frames_from_rows(rows, keys)

    def upsert_weekly(self, rows):
        rows = list(rows)
        with self.conn.cursor() as cur:
            cur.execute(
                "create temp table if not exists _wk (indicator_id text, week_cutoff date, value double precision, obs_date date, status text, detail text) on commit drop"
            )
            with cur.copy("copy _wk from stdin") as copy:
                for r in rows:
                    copy.write_row((r.indicator_id, r.week_cutoff, r.value, r.obs_date, r.status, r.detail))
            cur.execute(
                """insert into public.weekly_values (indicator_id, week_cutoff, value, obs_date, status, detail)
                   select w.indicator_id, w.week_cutoff, w.value, w.obs_date, w.status, w.detail from _wk w
                   join public.indicators i using (indicator_id)
                   on conflict (indicator_id, week_cutoff) do update set value=excluded.value,
                   obs_date=excluded.obs_date, status=excluded.status, detail=excluded.detail, computed_at=now()"""
            )
        self.conn.commit()
        return len(rows)

    def log(self, run_id, runner, provider, series_key, status, rows, message):
        with self.conn.cursor() as cur:
            cur.execute(
                "insert into public.fetch_log (run_id, runner, provider, series_key, status, rows_written, message) values (%s,%s,%s,%s,%s,%s,%s)",
                (run_id, runner, provider, series_key, status, rows, message[:1000]),
            )
        self.conn.commit()

    def weekly_count(self):
        with self.conn.cursor() as cur:
            cur.execute("select count(*) from public.weekly_values")
            return int(cur.fetchone()[0])

    def indicator_formulas(self):
        with self.conn.cursor() as cur:
            cur.execute("select indicator_id, coalesce(formula, '') from public.indicators")
            return dict(cur.fetchall())

    def get_meta(self, key):
        with self.conn.cursor() as cur:
            cur.execute("select value from public.warehouse_meta where key=%s", (key,))
            row = cur.fetchone()
        return row[0] if row else None

    def earliest_obs(self, series_key):
        with self.conn.cursor() as cur:
            cur.execute("select min(obs_date) from public.observations where series_key=%s", (series_key,))
            row = cur.fetchone()
        return row[0] if row else None

    def set_meta(self, key, value):
        with self.conn.cursor() as cur:
            cur.execute("""insert into public.warehouse_meta (key, value) values (%s,%s)
                           on conflict (key) do update set value=excluded.value, updated_at=now()""", (key, value))
        self.conn.commit()

    def prune_series(self, keep):
        with self.conn.cursor() as cur:
            cur.execute("delete from public.series where not (series_key = any(%s))", (list(keep),))
            n = cur.rowcount
        self.conn.commit()
        return n

    def upsert_report_pages(self, source, report_date, url, pages):
        with self.conn.cursor() as cur:
            cur.executemany(
                """insert into public.report_pages (source, report_date, page, url, text) values (%s,%s,%s,%s,%s)
                   on conflict (source, report_date, page) do update set url=excluded.url, text=excluded.text, fetched_at=now()""",
                [(source, report_date, i + 1, url, text.replace("\x00", "")) for i, text in enumerate(pages)],
            )
        self.conn.commit()
        return len(pages)

    def close(self):
        self.conn.close()


def open_store(url: str | None) -> Store:
    """postgres://... -> PostgresStore; sqlite:///path or a file path -> SQLiteStore."""
    if not url:
        raise ValueError("set WAREHOUSE_DB_URL (Supabase connection string) or pass --db sqlite:///path.db")
    if url.startswith(("postgres://", "postgresql://")):
        return PostgresStore(url)
    if url.startswith("sqlite:///"):
        return SQLiteStore(url[len("sqlite:///"):])
    return SQLiteStore(url)
