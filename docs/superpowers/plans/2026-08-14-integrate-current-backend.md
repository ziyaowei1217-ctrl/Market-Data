# Current Capital Weekly Backend Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebase the current tested Capital Weekly backend capabilities onto the unrelated public `main` history without losing the public workbook packager, verifier, license, or repository hygiene.

**Architecture:** Start from `origin/main` in an isolated worktree and use commit `32c288b` only as a source tree, never as a merge parent. Prove the public baseline cannot satisfy the current backend tests, then transplant the matching Python modules, scripts, configuration, and tests as one coherent state. Reconcile documentation separately so public-only assets remain intact.

**Tech Stack:** Python 3.9+, pandas, requests, pypdf, unittest, Node.js test runner, Git worktrees.

## Global Constraints

- Keep the public branch history based on `origin/main`; do not merge unrelated histories.
- Keep exactly five acquisition pipelines and the coordinated atomic release entrypoint.
- Apply `as_of_date` before calculating every snapshot return.
- Never publish a formal week containing observations after the target Sunday.
- Empty optional context tables retain their standard headers.
- A new week becomes visible only after all five pipelines and release validation succeed.
- Keep `scripts/build_weekly_workbooks.mjs`, `scripts/verify_weekly_workbooks.mjs`, `tests/test_verify_weekly_workbooks.mjs`, and `LICENSE` from public `main`.
- Do not restore `data/capital_weekly_market_proxies.csv`; it has no production reader.
- Do not restore any legacy per-domain workbook script, generated output, cache, market-size pipeline, or Node dependency directory.
- Retain `pandas>=2.0`, `requests>=2.31,<3`, and `pypdf>=5,<7`.
- Use deterministic tests only; do not run a real network refresh.
- Do not modify the Next.js repository.

---

### Task 1: Integrate the tested backend state with a RED/GREEN transplant

**Files:**
- Create: `capital_weekly/history.py`
- Create: `capital_weekly/weekly_release.py`
- Create: `capital_weekly/release_migration.py`
- Create: `capital_weekly/context/provider_contracts.py`
- Create: `capital_weekly/context/economic_releases.py`
- Create: `capital_weekly/context/economic_sources/__init__.py`
- Create: `capital_weekly/context/economic_sources/bls.py`
- Create: `capital_weekly/context/economic_sources/bea.py`
- Create: `capital_weekly/context/economic_sources/census.py`
- Modify: `capital_weekly/equity_indices.py`
- Modify: `capital_weekly/equity_sectors.py`
- Modify: `capital_weekly/gics_sectors.py`
- Modify: `capital_weekly/macro_assets.py`
- Modify: `capital_weekly/context/providers.py`
- Modify: `capital_weekly/weekly_context.py`
- Modify: `data/capital_weekly_macro_assets.csv`
- Modify: `scripts/fetch_equity_indices.py`
- Modify: `scripts/fetch_equity_sectors.py`
- Modify: `scripts/fetch_gics_sectors.py`
- Create: `scripts/refresh_capital_weekly.py`
- Create: `scripts/migrate_capital_weekly_releases.py`
- Create or modify: the corresponding `tests/test_capital_weekly_*.py` modules listed by the source-tree diff

**Interfaces:**
- Produces: `truncate_history_as_of(history, as_of_date)` and `--as-of-date` support for indices, sectors, and GICS.
- Produces: `run_weekly_release(...)`, `validate_staged_week(...)`, manifest-v2 publication, atomic status, locking, and rollback.
- Produces: release migration with contract-aware optional-header repair.
- Produces: point-in-time economic release contracts and archived BLS, BEA, and Census parsers.
- Produces: Treasury real yields, breakevens, and 5Y5Y calculations with lineage metadata.

- [ ] **Step 1: Transplant only the current Python tests**

Use the exact test tree from `32c288b` while preserving the public Node contract test:

```bash
git restore --source=32c288b --worktree -- tests/__init__.py 'tests/test_capital_weekly_*.py'
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
python3 -m unittest -v \
  tests.test_capital_weekly_history \
  tests.test_capital_weekly_point_in_time \
  tests.test_capital_weekly_economic_releases \
  tests.test_capital_weekly_release_migration \
  tests.test_capital_weekly_weekly_release
```

Expected: FAIL because the public baseline lacks modules such as `capital_weekly.history`, `capital_weekly.context.economic_releases`, `capital_weekly.release_migration`, and `capital_weekly.weekly_release`.

- [ ] **Step 3: Transplant the matching production files**

Restore these exact source-tree paths from `32c288b`:

```bash
git restore --source=32c288b --worktree -- \
  capital_weekly/history.py \
  capital_weekly/weekly_release.py \
  capital_weekly/release_migration.py \
  capital_weekly/equity_indices.py \
  capital_weekly/equity_sectors.py \
  capital_weekly/gics_sectors.py \
  capital_weekly/macro_assets.py \
  capital_weekly/context/provider_contracts.py \
  capital_weekly/context/economic_releases.py \
  capital_weekly/context/economic_sources/__init__.py \
  capital_weekly/context/economic_sources/bls.py \
  capital_weekly/context/economic_sources/bea.py \
  capital_weekly/context/economic_sources/census.py \
  capital_weekly/context/providers.py \
  capital_weekly/weekly_context.py \
  data/capital_weekly_macro_assets.csv \
  scripts/fetch_equity_indices.py \
  scripts/fetch_equity_sectors.py \
  scripts/fetch_gics_sectors.py \
  scripts/refresh_capital_weekly.py \
  scripts/migrate_capital_weekly_releases.py
```

Do not restore the deleted public workbook files or `data/capital_weekly_market_proxies.csv`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
python3 -m unittest -v \
  tests.test_capital_weekly_history \
  tests.test_capital_weekly_equity_indices \
  tests.test_capital_weekly_equity_sectors \
  tests.test_capital_weekly_gics_sectors \
  tests.test_capital_weekly_macro_as_of \
  tests.test_capital_weekly_macro_assets \
  tests.test_capital_weekly_point_in_time \
  tests.test_capital_weekly_economic_releases \
  tests.test_capital_weekly_economic_bls \
  tests.test_capital_weekly_economic_bea \
  tests.test_capital_weekly_economic_census \
  tests.test_capital_weekly_weekly_context \
  tests.test_capital_weekly_release_migration \
  tests.test_capital_weekly_weekly_release
```

Expected: all focused tests pass without network access.

- [ ] **Step 5: Run the complete Python and Node suites**

Run:

```bash
python3 -m unittest -v
node --test tests/test_verify_weekly_workbooks.mjs
node --check scripts/build_weekly_workbooks.mjs
node --check scripts/verify_weekly_workbooks.mjs
```

Expected: 293 Python tests pass, two Node contract tests pass, and both public workbook scripts pass syntax checking.

- [ ] **Step 6: Commit the backend integration**

Stage only the Python production files, configuration, scripts, and Python tests changed in this task, then commit:

```bash
git commit -m "feat: integrate current capital weekly backend"
```

---

### Task 2: Reconcile public documentation and repository hygiene

**Files:**
- Modify: `.gitignore`
- Create: `AGENTS.md`
- Modify: `README.md`
- Create: `docs/superpowers/plans/2026-07-13-fx-russell-sox-btc-plan.md`
- Create: `docs/superpowers/plans/2026-08-12-market-sense-point-in-time-macro-rates.md`
- Create: `docs/superpowers/plans/2026-08-14-integrate-current-backend.md`
- Create: `docs/superpowers/specs/2026-07-13-fx-russell-sox-btc-design.md`
- Create: `docs/superpowers/specs/2026-08-11-market-sense-public-data-expansion-design.md`

**Interfaces:**
- Documents: coordinated refresh, explicit historical cutoff, migration dry-run, local frontend data root, workbook packaging, deterministic tests, and optional providers.
- Preserves: public workbook commands and MIT license reference.

- [ ] **Step 1: Restore the active execution guidance**

Restore `AGENTS.md`, the two retained implementation plans, and their paired
design documents from `32c288b`. Replace user-specific absolute paths in
`AGENTS.md` with `CAPITAL_WEEKLY_FRONTEND_ROOT`. Keep historical internal
reports and obsolete plans out of the public tree.

- [ ] **Step 2: Merge the README contracts**

Keep the public overview, requirements, optional environment variables, workbook packaging, configuration, tests, data limitations, and license sections. Replace the duplicated manual section with the coordinated command:

```bash
python3 scripts/refresh_capital_weekly.py
python3 scripts/refresh_capital_weekly.py --as-of-date 2026-08-09
python3 scripts/migrate_capital_weekly_releases.py --dry-run
```

State that `outputs/` remains local and frontend-readable, all five pipelines must validate before publication, and failed refreshes preserve the prior complete week.

- [ ] **Step 3: Validate documentation and retained public assets**

Run:

```bash
test -f LICENSE
test -f scripts/build_weekly_workbooks.mjs
test -f scripts/verify_weekly_workbooks.mjs
test -f tests/test_verify_weekly_workbooks.mjs
rg -n 'pypdf>=5,<7' requirements.txt
rg -n 'refresh_capital_weekly.py|migrate_capital_weekly_releases.py|build_weekly_workbooks.mjs|verify_weekly_workbooks.mjs' README.md
```

Expected: every retained asset and documented command exists.

- [ ] **Step 4: Run final verification and commit documentation**

Run:

```bash
python3 -m unittest -v
node --test tests/test_verify_weekly_workbooks.mjs
git diff --check
```

Then commit:

```bash
git commit -m "docs: document the integrated weekly backend"
```

---

### Task 3: Audit the integration branch

**Files:**
- Verify: complete branch diff against `origin/main`

**Interfaces:**
- Proves: current backend behavior is present while public-only packaging and hygiene remain intact.

- [ ] **Step 1: Inspect the final file inventory**

Run:

```bash
git diff --name-status origin/main...HEAD
git status --short
find . -type d -name '__pycache__' -prune -o -type f -name '*.pyc' -print
```

Expected: no generated outputs, caches, legacy workbook scripts, market-size pipeline, or untracked files.

- [ ] **Step 2: Run the fresh completion gate**

Run:

```bash
python3 -m unittest -v
node --test tests/test_verify_weekly_workbooks.mjs
git diff --check origin/main...HEAD
```

Expected: all tests pass and the branch diff is whitespace-clean.

- [ ] **Step 3: Report without pushing**

Report both commit SHAs, RED/GREEN evidence, test totals, retained public assets, excluded files, branch path, and remaining risks. Do not push or create a PR without separate user authorization.
