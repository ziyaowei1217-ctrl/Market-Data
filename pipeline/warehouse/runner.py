"""Warehouse operations: sync catalog, fetch sources, derive weekly values."""

from __future__ import annotations

import os
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Sequence

import pandas as pd
import requests

from .catalog.build_catalog import load_catalog
from .catalog.mapping import load_mapping, load_series
from .db.store import Observation, Store
from .engine.weekly import compute, last_completed_friday, week_cutoffs
from .providers import breadth, factset, official  # noqa: F401  (registers providers)
from .providers.base import REGISTRY, FetchResult, SeriesDef

# A value older than this (by the fastest-moving input's frequency) is reported as
# status "stale" instead of "ok": e.g. a daily series that stopped updating.
MAX_AGE_DAYS = {"D": 14, "W": 28, "M": 95, "Q": 200, "A": 760, "E": 120}

INTENTIONALLY_DATED = ("snap(", "at_year(", "year_ret(", "before_change(", "prior(", "rev(", "first(", "prev_vintage(")

OBS_START = date(2020, 10, 1)      # 5 years of weekly history plus a one-year look-back
WEEKLY_START = date(2021, 10, 1)


@dataclass
class FetchSummary:
    provider: str
    ok: int = 0
    empty: int = 0
    error: int = 0
    not_configured: int = 0
    rows: int = 0
    initial: list[str] = None  # series loaded for the first time in this run

    def __post_init__(self):
        self.initial = []


def series_defs(only_provider: str | None = None, only_keys: Sequence[str] | None = None, runner: str | None = None) -> list[SeriesDef]:
    defs = []
    for r in load_series():
        if only_provider and r["provider"] != only_provider:
            continue
        if only_keys and r["key"] not in only_keys:
            continue
        if runner and r.get("runner", "cloud") != runner:
            continue
        defs.append(SeriesDef(
            key=r["key"], provider=r["provider"], code=r["code"], params=r["params"], title=r["title"],
            frequency=r["frequency"], unit=r["unit"], source_url=r["source_url"],
            release_lag_days=r["release_lag_days"], vintages=r["vintages"], runner=r.get("runner", "cloud"),
        ))
    return defs


def sync_catalog(store: Store) -> tuple[int, int, set[str]]:
    """Upsert catalog and registry. Returns counts and the indicator ids whose
    formula is new or changed (their history must be recomputed)."""
    previous = store.indicator_formulas()
    mapping = load_mapping()
    rows = []
    for r in load_catalog():
        m = mapping.get(r["indicator_id"], {})
        rows.append({**r, "method": m.get("method", "pending"), "phase": m.get("phase", ""),
                     "formula": m.get("formula", ""), "coverage_note": m.get("coverage_note", "")})
    n_ind = store.upsert_indicators(rows)
    series_rows = [
        {"series_key": d.key, "provider": d.provider, "code": d.code, "params": dict(d.params), "title": d.title,
         "frequency": d.frequency, "unit": d.unit, "source_url": d.source_url,
         "release_lag_days": d.release_lag_days, "vintages": d.vintages}
        for d in series_defs()
    ]
    n_ser = store.upsert_series(series_rows)
    store.prune_series([r["series_key"] for r in series_rows])
    changed = {r["indicator_id"] for r in rows if r["formula"] and previous.get(r["indicator_id"]) != r["formula"]}
    return n_ind, n_ser, changed


def fetch(
    store: Store | None,
    defs: Sequence[SeriesDef],
    *,
    start: date = OBS_START,
    runner: str = "cloud",
    run_id: str | None = None,
    session: requests.Session | None = None,
    env: dict | None = None,
    log=print,
) -> dict[str, FetchSummary]:
    """Fetch every series; write to ``store`` (or just report when store is None)."""
    run_id = run_id or f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    by_provider: dict[str, list[SeriesDef]] = defaultdict(list)
    for d in defs:
        by_provider[d.provider].append(d)
    summaries: dict[str, FetchSummary] = {}
    fetch_day = datetime.now(timezone.utc).date()
    for provider_name, items in sorted(by_provider.items()):
        cls = REGISTRY.get(provider_name)
        summary = summaries.setdefault(provider_name, FetchSummary(provider_name))
        if cls is None:
            for d in items:
                summary.error += 1
                log(f"  {d.key}: no provider {provider_name}")
            continue
        provider = cls(session=session, env=env)
        results = provider.fetch(items, start)
        by_key = {d.key: d for d in items}
        for result in results:
            d = by_key[result.key]
            written = 0
            if result.status == "ok" and store is not None:
                written = store.write_observations(
                    d.key, result.observations, release_lag_days=d.release_lag_days, fetch_day=fetch_day
                )
                if store.last_write_initial and written:
                    summary.initial.append(d.key)
            setattr(summary, result.status, getattr(summary, result.status) + 1)
            summary.rows += written
            last = result.observations[-1].obs_date.isoformat() if result.observations else "-"
            message = result.message or f"{len(result.observations)} obs, last {last}"
            if store is not None:
                store.update_series_status(d.key, result.status, message)
                store.log(run_id, runner, provider_name, d.key, result.status, written, message)
            log(f"  [{result.status:>14}] {d.key:<55} {message}")
    return summaries


def formulas_for(method: str = "api") -> dict[str, str]:
    return {iid: m["formula"] for iid, m in load_mapping().items() if m["method"] == method and m["formula"]}


def indicators_using(series_keys: Iterable[str]) -> set[str]:
    keys = set(series_keys)
    return {iid for iid, text in formulas_for("api").items() if keys & set(_series_in(text))}


def derive(
    store: Store,
    *,
    cutoffs: Sequence[pd.Timestamp] | None = None,
    backfill_from: date | None = None,
    only: Iterable[str] | None = None,
    log=print,
) -> int:
    """Compute weekly values. Default: the latest completed week with all data stored so far.
    ``backfill_from``: every Friday since that date, from the latest stored versions (fast mode)."""
    formulas = formulas_for("api")
    if only is not None:
        only = set(only)
        formulas = {k: v for k, v in formulas.items() if k in only}
    if not formulas:
        return 0
    keys = sorted({k for text in formulas.values() for k in _series_in(text)})
    raw = store.load_observations(keys)
    defs = {d.key: d for d in series_defs()}
    max_age = {}
    for iid, text in formulas.items():
        if any(fn in text for fn in INTENTIONALLY_DATED):
            continue  # snapshots / prior values carry an older obs_date by design
        ages = [MAX_AGE_DAYS.get(defs[k].frequency, 95) + defs[k].release_lag_days for k in _series_in(text) if k in defs]
        if ages:
            max_age[iid] = max(ages)
    if backfill_from is not None:
        cuts = week_cutoffs(backfill_from, last_completed_friday().date())
        values = compute(formulas, raw, cuts, fast=True, max_age_days=max_age)
    else:
        cuts = list(cutoffs) if cutoffs else [last_completed_friday()]
        values = compute(formulas, raw, cuts, known_now=pd.Timestamp(datetime.now(timezone.utc).date()) + pd.Timedelta(days=1),
                         max_age_days=max_age)
    n = store.upsert_weekly(values)
    ok = sum(1 for v in values if v.status == "ok")
    log(f"weekly values: {n} rows for {len(cuts)} week(s); ok={ok}")
    return n


def _series_in(text: str) -> list[str]:
    from .engine.formula import parse

    return list(parse(text).series)
