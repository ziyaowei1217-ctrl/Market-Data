#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import uuid
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from capital_weekly.macro_assets import fetch_macro_assets
from capital_weekly.macro_divergence import add_macro_ranks, build_macro_divergence


def strict_records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso", double_precision=15))


def _publish_directory(staging_dir: Path, output_dir: Path) -> None:
    """Swap a complete staged bundle into place, rolling back on failure."""
    backup_dir = output_dir.with_name(f".{output_dir.name}.backup-{uuid.uuid4().hex}")
    had_output = output_dir.exists()
    if had_output:
        os.replace(output_dir, backup_dir)
    try:
        os.replace(staging_dir, output_dir)
    except Exception:
        if had_output and backup_dir.exists():
            os.replace(backup_dir, output_dir)
        raise
    if backup_dir.exists():
        shutil.rmtree(backup_dir)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch fixed-income, commodity, foreign-exchange, and other macro assets."
    )
    parser.add_argument("--universe", default="data/capital_weekly_macro_assets.csv")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=None)
    parser.add_argument("--no-raw-cache", action="store_true")
    args = parser.parse_args()

    output_dir = Path(
        args.output_dir
        or f"outputs/capital_weekly_macro_assets_python_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(
        prefix=f".{output_dir.name}.staging-", dir=output_dir.parent,
    ))
    try:
        raw_dir = None if args.no_raw_cache else staging_dir / "raw"
        if raw_dir is not None:
            raw_dir.mkdir()
        detail, source_log = fetch_macro_assets(
            args.universe,
            raw_dir=raw_dir,
            as_of_date=args.as_of_date,
        )
        ranked = add_macro_ranks(detail)
        divergence = build_macro_divergence(ranked)
        fixed_income = ranked.loc[ranked["asset_class"].eq("fixed_income")].copy()
        commodities = ranked.loc[ranked["asset_class"].eq("commodity")].copy()
        foreign_exchange = ranked.loc[ranked["asset_class"].eq("foreign_exchange")].copy()
        policy_rates = ranked.loc[ranked["asset_class"].eq("policy_rate")].copy()
        money_market = ranked.loc[ranked["asset_class"].eq("money_market")].copy()

        fixed_income.to_csv(staging_dir / "fixed_income.csv", index=False)
        commodities.to_csv(staging_dir / "commodities.csv", index=False)
        foreign_exchange.to_csv(staging_dir / "foreign_exchange.csv", index=False)
        policy_rates.to_csv(staging_dir / "policy_rates.csv", index=False)
        money_market.to_csv(staging_dir / "money_market.csv", index=False)
        divergence.to_csv(staging_dir / "macro_divergence.csv", index=False)
        source_log.to_csv(staging_dir / "source_log.csv", index=False)
        snapshot = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "fixed_income": strict_records(fixed_income),
            "commodities": strict_records(commodities),
            "foreign_exchange": strict_records(foreign_exchange),
            "policy_rates": strict_records(policy_rates),
            "money_market": strict_records(money_market),
            "macro_divergence": strict_records(divergence),
            "source_log": strict_records(source_log),
        }
        (staging_dir / "macro_assets_snapshot.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        _publish_directory(staging_dir, output_dir)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

    configured = len(detail)
    failed = int(detail["qc_flag"].eq("FETCH_FAILED").sum())
    print(f"configured: {configured}")
    print(f"fetched: {configured - failed}")
    print(f"failed: {failed}")
    for asset_class in ("fixed_income", "commodity", "foreign_exchange", "policy_rate", "money_market"):
        class_rows = detail.loc[detail["asset_class"].eq(asset_class)]
        class_configured = len(class_rows)
        class_failed = int(class_rows["qc_flag"].eq("FETCH_FAILED").sum())
        print(
            f"{asset_class}: configured={class_configured}, "
            f"fetched={class_configured - class_failed}, failed={class_failed}"
        )
    print(f"summary rows: {len(divergence)}")


if __name__ == "__main__":
    main()
