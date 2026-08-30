#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.internal.capital_weekly.context.providers import build_default_providers
from pipeline.internal.capital_weekly.weekly_context import (
    publish_weekly_context_bundle,
    run_weekly_context,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch public weekly context data without browser automation."
    )
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--start-date", type=date.fromisoformat, default=None)
    parser.add_argument("--end-date", type=date.fromisoformat, default=None)
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Optional legacy CSV config directory; defaults to pipeline/config.json.",
    )
    parser.add_argument(
        "--providers",
        default=None,
        help="Comma-separated provider names; default runs every configured provider.",
    )
    parser.add_argument("--no-raw-cache", action="store_true")
    args = parser.parse_args()
    end = args.end_date or date.today()
    start = args.start_date or end - timedelta(days=6)
    output = Path(
        args.output_dir
        or f"outputs/capital_weekly_context_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    raw_dir = None if args.no_raw_cache else output.parent / f".{output.name}.raw"
    providers = build_default_providers(
        start=start,
        end=end,
        data_dir=args.data_dir,
    )
    if args.providers:
        requested = [name.strip() for name in args.providers.split(",") if name.strip()]
        unknown = sorted(set(requested) - set(providers))
        if unknown:
            parser.error(f"unknown providers: {', '.join(unknown)}")
        providers = {name: providers[name] for name in requested}
    audit_secrets = tuple(
        secret
        for name in ("EIA_API_KEY", "USDA_API_KEY")
        if (secret := os.environ.get(name, "").strip())
    )
    tables = run_weekly_context(
        providers,
        raw_dir=raw_dir,
        as_of_date=end,
        audit_secrets=audit_secrets,
    )
    publish_weekly_context_bundle(tables, output)
    print(f"saved: {output}")
    print(f"window: {start} to {end}")
    print(f"providers: {len(tables['source_log'])}")
    for row in tables["source_log"]:
        print(
            f"- {row['provider']}: {row['status']} "
            f"({row['observations']} observations)"
        )


if __name__ == "__main__":
    main()
