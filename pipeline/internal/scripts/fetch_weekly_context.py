#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.internal.capital_weekly.context.providers import build_default_providers
from pipeline.internal.capital_weekly.macro_assets import (
    load_commodity_research_config,
)
from pipeline.internal.capital_weekly.commodity_research import (
    PRICE_HISTORY_FIELDS,
    load_formula_specs,
)
from pipeline.internal.capital_weekly.weekly_context import (
    publish_weekly_context_bundle,
    run_weekly_context,
)


def _load_current_staged_price_history(
    context_output: Path,
    as_of_date: date,
) -> list[dict]:
    expected_context_name = f"capital_weekly_context_{as_of_date:%Y%m%d}"
    if context_output.name != expected_context_name:
        return []
    macro_output = context_output.parent / (
        f"capital_weekly_macro_assets_python_{as_of_date:%Y%m%d}"
    )
    path = macro_output / "commodity_price_history.csv"
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_file():
        raise ValueError("Staged commodity price history must be a regular file")
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != list(PRICE_HISTORY_FIELDS):
            raise ValueError(
                "Staged commodity price history has an unexpected schema"
            )
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Staged commodity price history has a ragged row")
            if not any(str(value).strip() for value in row.values()):
                continue
            rows.append(
                {
                    key: None if value == "" else value
                    for key, value in row.items()
                }
            )
    return rows


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
    research_config = load_commodity_research_config(
        args.data_dir
        if args.data_dir and Path(args.data_dir).suffix.lower() == ".json"
        else None
    )
    formula_specs = load_formula_specs(
        args.data_dir
        if args.data_dir and Path(args.data_dir).suffix.lower() == ".json"
        else None
    )
    price_history = _load_current_staged_price_history(output, end)
    tables = run_weekly_context(
        providers,
        raw_dir=raw_dir,
        as_of_date=end,
        audit_secrets=audit_secrets,
        history_limits=research_config.history_limits,
        commodity_registry=research_config.commodity_registry,
        formula_specs=formula_specs,
        price_history=price_history,
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
