from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from pipeline.capital_weekly.weekly_release import (
    ReleaseAlreadyRunning,
    ReleasePipelineError,
    ReleaseValidationError,
    latest_finished_week,
    run_latest_release,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HONG_KONG = ZoneInfo("Asia/Hong_Kong")


def _override_now(as_of_date: date, parser: argparse.ArgumentParser) -> datetime:
    if as_of_date.weekday() != 6:
        parser.error("--as-of-date must be a Sunday for a formal weekly release")
    latest_end = latest_finished_week(datetime.now(HONG_KONG)).end
    if as_of_date > latest_end:
        parser.error(
            "--as-of-date must not be later than the latest finished Sunday "
            f"({latest_end.isoformat()})"
        )
    following_monday = as_of_date + timedelta(days=1)
    return datetime.combine(following_monday, time.min, tzinfo=HONG_KONG)


def main(argv=None, *, release_runner=run_latest_release) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh the five latest Capital Weekly JSON outputs atomically."
    )
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=None,
        help="Override the release window end date (must be a finished Sunday).",
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        default=None,
        help="Write atomic refresh status JSON to this path.",
    )
    args = parser.parse_args(argv)
    override_now = (
        _override_now(args.as_of_date, parser)
        if args.as_of_date is not None
        else None
    )
    try:
        published = release_runner(
            PROJECT_ROOT,
            now_hkt=override_now,
            status_path=args.status_file,
        )
    except (
        ReleaseAlreadyRunning,
        ReleasePipelineError,
        ReleaseValidationError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"Capital Weekly refresh failed: {error}", file=sys.stderr)
        return 1
    print(published)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
