from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from pipeline.capital_weekly.weekly_release import (
    ReleaseAlreadyRunning,
    ReleasePipelineError,
    ReleaseValidationError,
    _publish_output_cache_pair,
    _source_manifest,
    _stage_latest_cache,
    build_output_bundle,
    build_pipeline_specs,
    latest_finished_week,
    run_latest_release,
    validate_output_bundle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HONG_KONG = ZoneInfo("Asia/Hong_Kong")
FORMAL_WEEK_PATTERN = re.compile(r"^week_\d{8}-\d{8}$")


def select_latest_complete_week(legacy_outputs: Path) -> Path:
    root = Path(legacy_outputs)
    if root.is_symlink() or not root.is_dir():
        raise ReleaseValidationError("Legacy outputs root must be a regular directory")
    valid = []
    for candidate in root.iterdir():
        if (
            not FORMAL_WEEK_PATTERN.fullmatch(candidate.name)
            or candidate.is_symlink()
            or not candidate.is_dir()
        ):
            continue
        try:
            _manifest, window, _contract_version = _source_manifest(candidate)
        except (OSError, ReleaseValidationError):
            continue
        valid.append((window.end, candidate.name, candidate))
    if not valid:
        raise ReleaseValidationError("No valid complete week exists in legacy outputs")
    return max(valid)[2]


def migrate_existing_output(project_root: Path, legacy_outputs: Path) -> Path:
    root = Path(project_root).resolve()
    selected = select_latest_complete_week(legacy_outputs)
    _manifest, window, _contract_version = _source_manifest(selected)
    staging_parent = root / "pipeline" / ".staging"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging_job = Path(tempfile.mkdtemp(prefix="offline-", dir=staging_parent))
    staging_output = staging_job / "output"
    staging_cache = staging_job / "cache"
    output = root / "output"
    cache = root / "pipeline" / ".cache"
    try:
        release = build_output_bundle(selected, staging_output)
        specs = build_pipeline_specs(selected, window)
        _stage_latest_cache(staging_cache, specs, release)
        validate_output_bundle(staging_output)
        _publish_output_cache_pair(staging_output, output, staging_cache, cache)
        return output
    finally:
        if staging_job.exists():
            shutil.rmtree(staging_job)


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


def main(
    argv=None,
    *,
    release_runner=run_latest_release,
    offline_runner=migrate_existing_output,
) -> int:
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
    parser.add_argument(
        "--from-existing",
        type=Path,
        default=None,
        help="Initialize output from the newest valid local week without networking.",
    )
    args = parser.parse_args(argv)
    if args.from_existing is not None and args.as_of_date is not None:
        parser.error("--from-existing cannot be combined with --as-of-date")
    override_now = (
        _override_now(args.as_of_date, parser)
        if args.as_of_date is not None
        else None
    )
    try:
        if args.from_existing is not None:
            legacy_outputs = (
                args.from_existing
                if args.from_existing.is_absolute()
                else PROJECT_ROOT / args.from_existing
            )
            published = offline_runner(PROJECT_ROOT, legacy_outputs)
        else:
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
        OSError,
    ) as error:
        print(f"Capital Weekly refresh failed: {error}", file=sys.stderr)
        return 1
    print(published)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
