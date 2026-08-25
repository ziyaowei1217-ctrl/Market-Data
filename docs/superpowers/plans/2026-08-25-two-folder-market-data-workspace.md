# Capital Weekly Two-Folder Workspace Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the existing backend into a `pipeline/` source tree and a stable `output/` containing only the latest complete five-pipeline JSON release.

**Architecture:** Move all tracked backend implementation, configuration, tests, and engineering documents under `pipeline/`, while preserving focused internal modules behind five public pipeline entrypoints. Reuse the existing CSV staging and release validator internally, then convert the validated staged release into five strict JSON envelopes plus `release.json`; publish the output and one-generation raw cache as a rollback-safe pair.

**Tech Stack:** Python 3 standard library, pandas, unittest, Node.js built-in test runner, JSON, Git worktrees.

**Spec:** `docs/superpowers/specs/2026-08-25-two-folder-market-data-workspace-design.md`

## Global Constraints

- This task reorganizes the existing backend; it does not create or modify a frontend.
- Do not add data sources, change formulas, or run a real network refresh.
- Keep only the latest complete successful release; historical week browsing is removed.
- The five output filenames and `release.json` remain stable across refreshes.
- Apply `as_of_date` before every snapshot calculation.
- Publish only after all five pipelines and cross-file validation succeed.
- Keep exactly one successful raw-cache generation under `pipeline/.cache/`.
- Preserve unrelated untracked content and every dirty-worktree change until a recoverable archive exists.
- Move superseded generated material to Trash; do not permanently delete it in this task.
- Do not delete Git branches.
- Baseline evidence before the move is 315 passing Python tests and 2 passing Node tests on 2026-08-25.

---

### Task 1: Move the tracked repository into the `pipeline` package

**Files:**
- Move: `capital_weekly/` to `pipeline/capital_weekly/`
- Move: `scripts/` to `pipeline/scripts/`
- Move: `tests/` to `pipeline/tests/`
- Move: `docs/` to `pipeline/docs/`
- Move: `requirements.txt` to `pipeline/requirements.txt`
- Create: `pipeline/__init__.py`
- Create: `pipeline/indices.py`
- Create: `pipeline/sectors.py`
- Create: `pipeline/gics.py`
- Create: `pipeline/macro.py`
- Create: `pipeline/context.py`
- Modify: `.gitignore`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: all moved Python tests and scripts whose import or patch paths use `capital_weekly` or `scripts`

**Interfaces:**
- Produces: import namespace `pipeline.capital_weekly`.
- Produces: public diagnostic entrypoints `python3 -m pipeline.indices`, `pipeline.sectors`, `pipeline.gics`, `pipeline.macro`, and `pipeline.context`.
- Preserves: all existing fetcher function signatures and deterministic test behavior.

- [ ] **Step 1: Add a failing layout/import contract test**

Create `tests/test_workspace_layout.py` before moving the tests:

```python
from pathlib import Path
import importlib
import unittest


class WorkspaceLayoutTests(unittest.TestCase):
    def workspace_root(self):
        parent = Path(__file__).resolve().parent.parent
        return parent.parent if parent.name == "pipeline" else parent

    def test_pipeline_namespace_and_public_entrypoints_exist(self):
        root = self.workspace_root()
        self.assertTrue((root / "pipeline").is_dir())
        for module in ("indices", "sectors", "gics", "macro", "context"):
            importlib.import_module(f"pipeline.{module}")

    def test_tracked_source_directories_are_collapsed_under_pipeline(self):
        root = self.workspace_root()
        visible = {path.name for path in root.iterdir() if path.is_dir() and not path.name.startswith(".")}
        self.assertTrue({"pipeline"}.issubset(visible))
        self.assertFalse({"capital_weekly", "data", "scripts", "tests", "docs"} & visible)
```

- [ ] **Step 2: Run the contract test and verify RED**

Run: `python3 -m unittest -v tests.test_workspace_layout`

Expected: FAIL because `pipeline` and the five entrypoint modules do not exist.

- [ ] **Step 3: Move tracked directories and update Python namespaces mechanically**

Use `git mv` for tracked paths. Add `pipeline/__init__.py`. Replace production and test imports as follows:

```text
from capital_weekly...  -> from pipeline.capital_weekly...
from scripts...         -> from pipeline.scripts...
"scripts.fetch_..."    -> "pipeline.scripts.fetch_..."
```

Update every moved script's project-root insertion to insert the repository root, not the `pipeline/` directory:

```python
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
```

The five public modules delegate without duplicating implementation. Example:

```python
# pipeline/indices.py
from pipeline.scripts.fetch_equity_indices import main

if __name__ == "__main__":
    main()
```

Use the corresponding existing script for the other four domains.

- [ ] **Step 4: Update commands and ignore rules**

Update `.gitignore` from `outputs/` to the new runtime paths:

```gitignore
output/
pipeline/.cache/
pipeline/.staging/
pipeline/.state/
```

Update `AGENTS.md` and `README.md` so focused and full tests run from the repository root:

```bash
python3 -m unittest -v
node --test pipeline/tests/test_verify_weekly_workbooks.mjs
```

Document that only `pipeline/` and `output/` are visible product directories and that the adjacent frontend is not compatible with the new stable-output contract.

- [ ] **Step 5: Run moved focused tests and verify GREEN**

Run:

```bash
python3 -m unittest -v \
  pipeline.tests.test_workspace_layout \
  pipeline.tests.test_capital_weekly_history \
  pipeline.tests.test_capital_weekly_equity_indices \
  pipeline.tests.test_capital_weekly_equity_sectors \
  pipeline.tests.test_capital_weekly_gics_sectors
```

Expected: all selected tests pass. The layout test rejects legacy tracked source directories but permits generated directories until Task 6 cleanup.

- [ ] **Step 6: Run the full relocated baseline**

Run: `python3 -m unittest -v`

Expected: 316 tests pass, comprising the prior 315 tests plus the layout contract.

Run: `node --test pipeline/tests/test_verify_weekly_workbooks.mjs`

Expected: 2 tests pass.

- [ ] **Step 7: Commit the structural move**

```bash
git add -A pipeline capital_weekly scripts tests docs requirements.txt .gitignore AGENTS.md README.md
git commit -m "refactor: organize backend under pipeline"
```

---

### Task 2: Consolidate versioned configuration into one JSON file

**Files:**
- Create: `pipeline/config.json`
- Create: `pipeline/common.py`
- Modify: `pipeline/capital_weekly/equity_indices.py`
- Modify: `pipeline/capital_weekly/equity_sectors.py`
- Modify: `pipeline/capital_weekly/gics_sectors.py`
- Modify: `pipeline/capital_weekly/macro_assets.py`
- Modify: `pipeline/capital_weekly/context/providers.py`
- Modify: `pipeline/scripts/fetch_equity_indices.py`
- Modify: `pipeline/scripts/fetch_equity_sectors.py`
- Modify: `pipeline/scripts/fetch_gics_sectors.py`
- Modify: `pipeline/scripts/fetch_macro_assets.py`
- Modify: `pipeline/scripts/fetch_weekly_context.py`
- Modify: configuration and provider tests under `pipeline/tests/`
- Delete after verification: the nine moved CSV configuration files under `pipeline/config/`

**Interfaces:**
- Produces: `load_config_rows(section: str, path: str | Path | None = None) -> list[dict[str, str]]`.
- Produces: JSON sections `indices`, `sectors`, `gics`, `macro`, and `context` with the five context configuration tables nested below `context`.
- Preserves: explicit CSV paths accepted by unit tests and diagnostic commands.

- [ ] **Step 1: Add failing JSON configuration tests**

Create `pipeline/tests/test_pipeline_config.py`:

```python
from pathlib import Path
import unittest

from pipeline.common import load_config_rows


class PipelineConfigTests(unittest.TestCase):
    def test_single_config_contains_every_registered_domain(self):
        self.assertEqual(len(load_config_rows("indices")), 20)
        self.assertGreater(len(load_config_rows("sectors")), 20)
        self.assertEqual(len(load_config_rows("gics")), 11)
        self.assertEqual(len(load_config_rows("macro")), 47)
        for section in (
            "context.cftc_contracts",
            "context.company_watchlist",
            "context.eia_series",
            "context.financial_conditions",
            "context.yahoo_volatility",
        ):
            self.assertIsInstance(load_config_rows(section), list)

    def test_rows_are_returned_as_independent_string_mappings(self):
        first = load_config_rows("indices")
        second = load_config_rows("indices")
        self.assertIsNot(first, second)
        self.assertTrue(all(isinstance(value, str) for value in first[0].values()))
```

- [ ] **Step 2: Run the configuration tests and verify RED**

Run: `python3 -m unittest -v pipeline.tests.test_pipeline_config`

Expected: FAIL because `pipeline.common` and `pipeline/config.json` do not exist.

- [ ] **Step 3: Convert the nine CSV configurations without changing values**

Generate `pipeline/config.json` mechanically from the moved CSV files. The exact top-level mapping is:

```json
{
  "schema_version": "1.0",
  "indices": [],
  "sectors": [],
  "gics": [],
  "macro": [],
  "context": {
    "cftc_contracts": [],
    "company_watchlist": [],
    "eia_series": [],
    "financial_conditions": [],
    "yahoo_volatility": []
  }
}
```

Preserve CSV row order, column names, and every cell as a JSON string. Serialize with UTF-8, two-space indentation, `ensure_ascii=False`, and `allow_nan=False`.

- [ ] **Step 4: Implement the shared loader with CSV compatibility**

```python
# pipeline/common.py
from copy import deepcopy
import csv
import json
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config_rows(section: str, path: str | Path | None = None) -> list[dict[str, str]]:
    if path is not None and Path(path).suffix.lower() == ".csv":
        with Path(path).open(newline="", encoding="utf-8") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    value = payload
    for part in section.split("."):
        value = value[part]
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError(f"Configuration section is not a row list: {section}")
    return deepcopy(value)
```

Update the four market-universe loaders to default to `None` and call their registered JSON section, while retaining explicit CSV input. Update `build_default_providers` to load the five `context.*` sections from the JSON file by default and retain its explicit legacy directory path for deterministic compatibility tests.

- [ ] **Step 5: Update CLI defaults and run focused tests**

CLI `--universe` and `--data-dir` defaults become `None`; explicit test paths continue to work. Run:

```bash
python3 -m unittest -v \
  pipeline.tests.test_pipeline_config \
  pipeline.tests.test_capital_weekly_equity_indices \
  pipeline.tests.test_capital_weekly_equity_sectors \
  pipeline.tests.test_capital_weekly_gics_sectors \
  pipeline.tests.test_capital_weekly_macro_assets \
  pipeline.tests.test_capital_weekly_context_providers
```

Expected: all focused tests pass.

- [ ] **Step 6: Prove the conversion is lossless and remove duplicate CSV configs**

Before deleting each CSV, compare its `csv.DictReader` rows exactly with the corresponding JSON section. The comparison must assert equality for keys, string values, row count, and row order. Delete the nine CSVs only after all comparisons pass.

- [ ] **Step 7: Run the full suite and commit**

Run: `python3 -m unittest -v`

Expected: all repository tests pass.

```bash
git add pipeline/config.json pipeline/common.py pipeline/capital_weekly pipeline/scripts pipeline/tests pipeline/config
git commit -m "refactor: consolidate pipeline configuration"
```

---

### Task 3: Build and validate the five stable JSON outputs

**Files:**
- Modify: `pipeline/common.py`
- Create: `pipeline/tests/test_latest_json_output.py`
- Modify: `pipeline/capital_weekly/weekly_release.py`

**Interfaces:**
- Produces: `build_output_bundle(release_root: Path, destination: Path, *, release_id: str | None = None) -> dict`.
- Produces: `validate_output_bundle(output_root: Path) -> dict` returning parsed `release.json` or raising `ReleaseValidationError`.
- Produces exactly: `indices.json`, `sectors.json`, `gics.json`, `macro.json`, `context.json`, and `release.json`.

- [ ] **Step 1: Add failing strict-output tests**

Create a current-contract staged-week fixture using the existing deterministic helper from `test_capital_weekly_weekly_release.py`. Test:

```python
def test_builds_exact_stable_files_with_one_release_identity(self):
    release = build_output_bundle(self.staged_week, self.output)
    self.assertEqual(
        {path.name for path in self.output.iterdir()},
        {"indices.json", "sectors.json", "gics.json", "macro.json", "context.json", "release.json"},
    )
    identities = {
        json.loads(path.read_text(encoding="utf-8"))["release_id"]
        for path in self.output.glob("*.json")
    }
    self.assertEqual(identities, {release["release_id"]})
```

Add cases asserting numeric columns become JSON numbers, blank optional cells become `null`, optional context tables become empty arrays, no serialized text contains `NaN` or `Infinity`, hashes match, and a mutated business file fails validation.

- [ ] **Step 2: Run the new output tests and verify RED**

Run: `python3 -m unittest -v pipeline.tests.test_latest_json_output`

Expected: FAIL because the bundle functions do not exist.

- [ ] **Step 3: Implement typed CSV-to-JSON conversion from the release registry**

For every `DatasetSpec` selected by the validated manifest's contract version:

```python
def _typed_csv_rows(path: Path, dataset: DatasetSpec) -> list[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for raw in csv.DictReader(handle, strict=True):
            row = {}
            for key, value in raw.items():
                if value == "":
                    row[key] = None
                elif key in dataset.numeric_columns:
                    number = float(value)
                    if not math.isfinite(number):
                        raise ReleaseValidationError(f"Non-finite output value: {dataset.filename}.{key}")
                    row[key] = int(number) if number.is_integer() and key.endswith(("count", "rank", "order", "observations", "elapsed_ms")) else number
                else:
                    row[key] = value
            rows.append(row)
    return rows
```

Resolve pipeline directories from the already validated manifest rather than guessing another week. Preserve source CSV order. Build the five table maps defined in the design and write strict JSON using the existing atomic JSON writer.

- [ ] **Step 4: Write `release.json` last and validate hashes**

`release.json` contains `schema_version`, `release_id`, `as_of_date`, `generated_at`, `status`, `pipelines`, and `files`. Hash only the five business JSON files. `validate_output_bundle` rejects missing/extra files, mismatched release IDs or dates, non-complete statuses, unexpected names, and SHA-256 mismatches.

- [ ] **Step 5: Run focused and full tests**

Run:

```bash
python3 -m unittest -v \
  pipeline.tests.test_latest_json_output \
  pipeline.tests.test_capital_weekly_weekly_release
python3 -m unittest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit the stable output format**

```bash
git add pipeline/common.py pipeline/capital_weekly/weekly_release.py pipeline/tests/test_latest_json_output.py
git commit -m "feat: publish stable cleaned json outputs"
```

---

### Task 4: Replace week-directory publication with paired output/cache publication

**Files:**
- Modify: `pipeline/capital_weekly/weekly_release.py`
- Create: `pipeline/refresh.py`
- Modify: `pipeline/scripts/refresh_capital_weekly.py`
- Modify: `pipeline/tests/test_capital_weekly_weekly_release.py`
- Modify: `pipeline/tests/test_workspace_layout.py`
- Delete: `pipeline/capital_weekly/release_migration.py`
- Delete: `pipeline/scripts/migrate_capital_weekly_releases.py`
- Delete: `pipeline/tests/test_capital_weekly_release_migration.py`

**Interfaces:**
- Produces: `run_latest_release(project_root: Path, now_hkt: datetime | None = None, status_path: Path | None = None, runner=subprocess.run) -> Path`.
- Produces: CLI `python3 -m pipeline.refresh [--as-of-date YYYY-MM-DD]`.
- Preserves: five-pipeline all-or-nothing validation and single-flight locking.

- [ ] **Step 1: Change orchestration tests to the stable contract and verify RED**

Update deterministic runner tests to assert:

```python
self.assertEqual(published, self.project_root / "output")
self.assertEqual(
    {path.name for path in published.iterdir()},
    {"indices.json", "sectors.json", "gics.json", "macro.json", "context.json", "release.json"},
)
self.assertFalse(any((self.project_root / "output").glob("week_*")))
```

Add tests that two successful refreshes retain the exact same filenames, pipeline failure keeps output and cache byte-for-byte unchanged, output replacement failure rolls both back, cache replacement failure rolls both back, and the successful cache contains only the new generation.

- [ ] **Step 2: Run orchestration tests and verify RED**

Run: `python3 -m unittest -v pipeline.tests.test_capital_weekly_weekly_release`

Expected: FAIL because the current coordinator publishes `outputs/week_*` and has no paired cache transaction.

- [ ] **Step 3: Implement stable staging paths and paired rollback**

Use:

```text
pipeline/.state/refresh.lock
pipeline/.state/status.json
pipeline/.staging/<job_id>/week/
pipeline/.staging/<job_id>/output/
pipeline/.staging/<job_id>/cache/
output/
pipeline/.cache/
```

Run the five existing domain pipelines into the staged week, validate it, build the staged JSON bundle, and gather only raw/cache artifacts into the staged cache. Publish output and cache with backups. If either swap or final status write fails, restore both prior directories before reporting failure.

- [ ] **Step 4: Update pipeline commands and CLI**

`build_pipeline_specs` runs the five public modules:

```text
python3 -m pipeline.indices
python3 -m pipeline.sectors
python3 -m pipeline.gics
python3 -m pipeline.macro
python3 -m pipeline.context
```

Retain the existing explicit date and staged-output arguments. `pipeline/refresh.py` owns the public CLI and delegates to `run_latest_release`. Keep `pipeline/scripts/refresh_capital_weekly.py` as an internal compatibility import only until its tests pass, then remove duplicate executable behavior from it.

- [ ] **Step 5: Remove obsolete historical migration code**

After stable publication tests pass, delete the old week-manifest migration module, CLI, and tests. Historical migration is incompatible with the confirmed latest-only product contract; the one-time offline conversion is covered by Task 5.

- [ ] **Step 6: Run focused and full verification**

Run:

```bash
python3 -m unittest -v \
  pipeline.tests.test_capital_weekly_weekly_release \
  pipeline.tests.test_latest_json_output \
  pipeline.tests.test_workspace_layout
python3 -m unittest -v
```

Expected: every remaining test passes and no test expects a new `week_*` directory.

- [ ] **Step 7: Commit the latest-only coordinator**

```bash
git add -A pipeline/refresh.py pipeline/capital_weekly/weekly_release.py pipeline/capital_weekly/release_migration.py pipeline/scripts pipeline/tests
git commit -m "refactor: refresh one latest output generation"
```

---

### Task 5: Migrate the newest complete local release without network access

**Files:**
- Modify: `pipeline/refresh.py`
- Modify: `pipeline/common.py`
- Create: `pipeline/tests/test_offline_output_migration.py`
- Generate, do not stage in Git: `output/*.json`

**Interfaces:**
- Produces: `select_latest_complete_week(legacy_outputs: Path) -> Path`.
- Produces: CLI `python3 -m pipeline.refresh --from-existing outputs` for one-time offline conversion.

- [ ] **Step 1: Add failing offline-selection tests**

Create fixtures containing an older valid manifest week, a newer failed manifest week, a draft directory, and an ad-hoc directory. Assert only the newest valid formal week is selected. Assert malformed, symlinked, hash-mismatched, or date-inconsistent candidates are rejected.

- [ ] **Step 2: Run the migration tests and verify RED**

Run: `python3 -m unittest -v pipeline.tests.test_offline_output_migration`

Expected: FAIL because offline selection and conversion are not implemented.

- [ ] **Step 3: Implement read-only source selection and conversion**

Scan direct children matching `^week_\d{8}-\d{8}$`. Require a complete, internally consistent manifest and run existing release validation before selecting the newest end date. The migration command calls `build_output_bundle` and never invokes a pipeline runner or network client.

- [ ] **Step 4: Run migration tests and the real local conversion**

Run:

```bash
python3 -m unittest -v pipeline.tests.test_offline_output_migration
python3 -m pipeline.refresh --from-existing outputs
```

Expected: tests pass; the command selects the newest validated existing release and writes only the six stable JSON files under `output/`.

- [ ] **Step 5: Reconcile representative real values and integrity**

Run `validate_output_bundle(Path("output"))`, then compare every output table's row count with the source CSV. Spot-check S&P 500, one A/H/US sector each, one GICS proxy, WTI, one policy rate, and the first context event for exact date, value, unit, source URL, and QC/status agreement.

- [ ] **Step 6: Commit migration code, not generated output**

```bash
git add pipeline/refresh.py pipeline/common.py pipeline/tests/test_offline_output_migration.py
git commit -m "feat: migrate the latest validated release offline"
```

---

### Task 6: Remove obsolete worktrees and generated directories recoverably

**Files and directories outside Git tracking:**
- Remove linked worktree directories after preservation checks: `.worktrees/*`
- Move to Trash after stable output verification: `outputs/`, `tmp/`, `deploy/`, `.superpowers/`, root `.DS_Store`
- Preserve: Git branches, current `output/`, `pipeline/.cache/`, and all tracked source files

**Interfaces:**
- Produces: a workspace with only `pipeline/` and `output/` as visible directories.
- Produces: a dated recoverable archive under the macOS Trash for dirty worktree contents and superseded generated artifacts.

- [ ] **Step 1: Inventory linked worktrees immediately before cleanup**

For every linked worktree record path, branch, HEAD, dirty status, size, and whether its HEAD is represented in `main`. Save the inventory outside the repository in the dated Trash archive.

- [ ] **Step 2: Remove clean linked worktrees without deleting branches**

Use `git worktree remove <exact-path>` only for worktrees whose porcelain status is empty. Do not run `git branch -D`, `git branch -d`, or any branch-pruning command.

- [ ] **Step 3: Archive dirty linked worktrees before force removal**

For each dirty worktree, archive its complete working directory excluding nested ignored caches into the dated Trash archive. Record `git diff --binary`, `git diff --cached --binary`, and the untracked-file list beside the archive. Verify the archive can be listed and its checksums read before using `git worktree remove --force <exact-path>`.

- [ ] **Step 4: Move superseded generated content to Trash**

After `output/` passes validation, move the legacy `outputs/`, `tmp/`, `deploy/`, `.superpowers/`, and root `.DS_Store` into the same dated Trash archive. Do not permanently delete the archive.

- [ ] **Step 5: Verify the final project tree**

Tighten `pipeline/tests/test_workspace_layout.py` so its final directory test is:

```python
def test_only_target_visible_directories_remain(self):
    root = Path(__file__).resolve().parents[2]
    visible = {
        path.name
        for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    }
    self.assertEqual(visible, {"pipeline", "output"})
```

Run:

```bash
git worktree list --porcelain
git status --short
find . -maxdepth 1 -type d -not -name . -not -name .git -print | sort
```

Expected: Git lists only the main workspace; the final visible directory list is `./output` and `./pipeline`; no unrelated tracked changes or unarchived dirty worktrees remain.

---

### Task 7: Complete full verification and documentation

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `pipeline/docs/REPOSITORY_STRUCTURE.md`
- Modify: `pipeline/docs/superpowers/specs/2026-08-25-two-folder-market-data-workspace-design.md`
- Modify: this plan after it moves to `pipeline/docs/superpowers/plans/`

**Interfaces:**
- Documents: the two-folder layout, five stable JSON contracts, latest-only refresh, one-generation cache, offline migration, test commands, and absence of frontend work.

- [ ] **Step 1: Update final documentation paths and remove historical instructions**

Document the public commands:

```bash
python3 -m pip install -r pipeline/requirements.txt
python3 -m pipeline.refresh
python3 -m pipeline.refresh --as-of-date 2026-08-23
python3 -m unittest -v
node --test pipeline/tests/test_verify_weekly_workbooks.mjs
```

Remove instructions that tell users to browse, migrate, or publish `outputs/week_*` directories. State explicitly that refresh overwrites the same stable output generation only after complete validation.

- [ ] **Step 2: Run complete deterministic verification**

Run:

```bash
python3 -m unittest -v
node --test pipeline/tests/test_verify_weekly_workbooks.mjs
python3 -c 'from pathlib import Path; from pipeline.common import validate_output_bundle; validate_output_bundle(Path("output"))'
git diff --check
```

Expected: all tests pass, direct stable-output validation succeeds without changing filenames, and diff check reports no whitespace errors.

- [ ] **Step 3: Verify output and workspace invariants**

Assert:

- exactly six files exist directly under `output/`;
- all six JSON files parse strictly;
- all five business files match `release.json` hashes and identity;
- no output filename contains a date;
- no `week_*`, ad-hoc, draft, staging, or backup directory exists in the repository;
- only `pipeline/` and `output/` are visible top-level directories;
- the adjacent frontend repository has no new status changes caused by this task.

- [ ] **Step 4: Commit final documentation**

```bash
git add README.md AGENTS.md pipeline/docs
git commit -m "docs: document the simplified market data workspace"
```

- [ ] **Step 5: Report handoff evidence**

Report the commit range, files moved/created/deleted, RED/GREEN evidence for each behavior change, final Python and Node test totals, selected source release, generated output identity, recoverable Trash archive path, remaining branches, and any residual compatibility risk.
