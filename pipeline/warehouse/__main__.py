"""Command line for the Capital Weekly warehouse.

    python3 -m pipeline.warehouse init-db               # create tables/views (idempotent)
    python3 -m pipeline.warehouse sync-catalog          # load 指标目录 + series registry
    python3 -m pipeline.warehouse fetch [--provider FRED] [--runner local]
    python3 -m pipeline.warehouse derive [--backfill-from 2021-10-01]
    python3 -m pipeline.warehouse weekly                # sync + fetch + derive (the scheduled job)
    python3 -m pipeline.warehouse probe [--provider X]  # fetch a short window without writing

The database comes from --db or WAREHOUSE_DB_URL (Supabase Postgres connection
string, or sqlite:///local.db for offline work).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta

from .db.store import open_store
from .engine.weekly import ENGINE_VERSION
from .runner import OBS_START, WEEKLY_START, derive, fetch, indicators_using, series_defs, sync_catalog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m pipeline.warehouse", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=os.environ.get("WAREHOUSE_DB_URL"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db")
    sub.add_parser("sync-catalog")
    for name in ("fetch", "probe", "weekly"):
        p = sub.add_parser(name)
        p.add_argument("--provider")
        p.add_argument("--series", nargs="*")
        p.add_argument("--runner", choices=["cloud", "local"], default="cloud")
        p.add_argument("--start", type=date.fromisoformat)
    d = sub.add_parser("derive")
    d.add_argument("--backfill-from", type=date.fromisoformat)
    sub.add_parser("archive-reports")
    args = parser.parse_args(argv)

    if args.command == "probe":
        defs = series_defs(args.provider, args.series)
        start = args.start or (date.today() - timedelta(days=120))
        summaries = fetch(None, defs, start=start, runner=args.runner)
        _print_summary(summaries)
        return 0 if all(s.error == 0 for s in summaries.values()) else 1

    store = open_store(args.db)
    try:
        if args.command == "init-db":
            store.init_schema()
            print("schema ready")
        elif args.command == "sync-catalog":
            n_ind, n_ser, changed = sync_catalog(store)
            print(f"indicators: {n_ind}; series: {n_ser}; formulas changed: {len(changed)}")
        elif args.command == "fetch":
            defs = series_defs(args.provider, args.series)
            _print_summary(fetch(store, defs, start=args.start or OBS_START, runner=args.runner))
        elif args.command == "derive":
            derive(store, backfill_from=args.backfill_from)
        elif args.command == "archive-reports":
            from .providers.reports import archive_all

            print(f"report pages stored: {archive_all(store)}")
        elif args.command == "weekly":
            _, _, changed = sync_catalog(store)
            defs = series_defs(args.provider, args.series)
            summaries = fetch(store, defs, start=args.start or OBS_START, runner=args.runner)
            _print_summary(summaries)
            if store.weekly_count() == 0 or store.get_meta("engine_version") != ENGINE_VERSION:
                print(f"backfilling all weekly values from {WEEKLY_START} (engine {ENGINE_VERSION})")
                derive(store, backfill_from=WEEKLY_START)
                store.set_meta("engine_version", ENGINE_VERSION)
            else:
                fresh = [k for s in summaries.values() for k in s.initial]
                redo = changed | indicators_using(fresh)
                if redo:
                    print(f"recomputing history for {len(redo)} indicators (new/changed formula or first data)")
                    derive(store, backfill_from=WEEKLY_START, only=redo)
            derive(store)
    finally:
        store.close()
    return 0


def _print_summary(summaries) -> None:
    print("\nprovider        ok  empty  error  not_configured  rows_written")
    for s in summaries.values():
        print(f"{s.provider:<12} {s.ok:>5} {s.empty:>6} {s.error:>6} {s.not_configured:>15} {s.rows:>13}")


if __name__ == "__main__":
    sys.exit(main())
