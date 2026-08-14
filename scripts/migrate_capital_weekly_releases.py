#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from capital_weekly.release_migration import MigrationResult, migrate_releases


def main(argv=None, *, migration_runner=migrate_releases) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate legacy Capital Weekly directories, repair registered blank "
            "optional headers, and publish truthful versioned manifests."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate on a temporary copy without changing formal week directories.",
    )
    parser.add_argument(
        "--week",
        default=None,
        help="Process one exact week_YYYYMMDD-YYYYMMDD directory.",
    )
    args = parser.parse_args(argv)
    try:
        results = migration_runner(
            PROJECT_ROOT,
            dry_run=args.dry_run,
            week_id=args.week,
        )
    except ValueError as error:
        parser.error(str(error))
    for result in results:
        print(json.dumps(asdict(result), ensure_ascii=False, allow_nan=False))
    return int(any(result.status in {"skipped", "failed"} for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
