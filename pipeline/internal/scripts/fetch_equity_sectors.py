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

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.internal.capital_weekly.equity_sectors import fetch_equity_sectors
from pipeline.internal.capital_weekly.sector_divergence import add_return_ranks, build_divergence_summary


def strict_records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso"))


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
    parser = argparse.ArgumentParser(description="Fetch A/H/US equity-sector data.")
    parser.add_argument("--universe", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--no-raw-cache", action="store_true")
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=None,
        help="Only use observations on or before this ISO date.",
    )
    args = parser.parse_args()

    output_dir = Path(
        args.output_dir
        or f"outputs/capital_weekly_equity_sectors_python_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(
        prefix=f".{output_dir.name}.staging-", dir=output_dir.parent,
    ))
    try:
        raw_dir = None if args.no_raw_cache else staging_dir / "raw"
        data, source_log = fetch_equity_sectors(
            args.universe,
            raw_dir=raw_dir,
            as_of_date=args.as_of_date,
        )
        ranked = add_return_ranks(data)
        summary = build_divergence_summary(ranked)

        ranked.to_csv(staging_dir / "03_equity_sectors.csv", index=False)
        summary.to_csv(staging_dir / "sector_divergence.csv", index=False)
        source_log.to_csv(staging_dir / "source_log.csv", index=False)
        snapshot = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "rows": strict_records(ranked),
            "summary": strict_records(summary),
            "source_log": strict_records(source_log),
        }
        (staging_dir / "equity_sectors_snapshot.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
        )
        _publish_directory(staging_dir, output_dir)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

    configured = len(data)
    failed = int((data["qc_flag"] == "FETCH_FAILED").sum()) if "qc_flag" in data else 0
    print(f"configured: {configured}")
    print(f"fetched: {configured - failed}")
    print(f"failed: {failed}")
    print(f"summary rows: {len(summary)}")


if __name__ == "__main__":
    main()
