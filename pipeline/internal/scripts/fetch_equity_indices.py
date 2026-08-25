#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.internal.capital_weekly.equity_indices import fetch_equity_indices


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch capital-weekly equity index data from free public APIs."
    )
    parser.add_argument(
        "--universe",
        default=None,
        help="Optional CSV universe override; defaults to pipeline/config.json.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Defaults to outputs/capital_weekly_equity_indices_python_<timestamp>.",
    )
    parser.add_argument(
        "--no-raw-cache",
        action="store_true",
        help="Skip writing raw API responses.",
    )
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=None,
        help="Only use observations on or before this ISO date.",
    )
    args = parser.parse_args()

    output_dir = Path(
        args.output_dir
        or f"outputs/capital_weekly_equity_indices_python_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = None if args.no_raw_cache else output_dir / "raw"

    data, source_log = fetch_equity_indices(
        args.universe,
        raw_dir=raw_dir,
        as_of_date=args.as_of_date,
    )
    data.to_csv(output_dir / "02_equity_indices.csv", index=False)
    source_log.to_csv(output_dir / "source_log.csv", index=False)

    snapshot = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "rows": data.where(data.notna(), None).to_dict(orient="records"),
        "source_log": source_log.where(source_log.notna(), None).to_dict(orient="records"),
    }
    (output_dir / "equity_indices_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ok_count = int((data["qc_flag"] == "OK").sum()) if "qc_flag" in data else 0
    print(f"saved: {output_dir}")
    print(f"rows: {len(data)} ok: {ok_count} failed: {len(data) - ok_count}")


if __name__ == "__main__":
    main()
