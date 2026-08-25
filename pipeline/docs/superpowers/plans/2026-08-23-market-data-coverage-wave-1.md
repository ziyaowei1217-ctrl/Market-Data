# Market-Data Coverage Wave 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish and display the Wave 1 public macro-market-structure set: Fed liquidity, 5s30s and HY-minus-IG spreads, copper and major FX proxies, and registered 13/26-week cross-asset correlations.

**Architecture:** Extend the existing `macro_assets` pipeline rather than add a sixth acquisition pipeline. Official and proxy input histories are cut off before calculation; pure registered calculations produce matched-date liquidity, spreads, and rolling correlations; dataset contract version 3 adds `liquidity.csv` and `cross_asset.csv` while preserving versions 1 and 2 for old formal weeks. The Dashboard loads version-3 files into the existing macro page, labels public-vendor proxies and derived rows, and exposes calculation lineage in the detail drawer.

**Tech Stack:** Python 3, pandas, unittest; Next.js 16, React 19, TypeScript 5, Vitest, Testing Library, Playwright.

**Spec:** `docs/superpowers/specs/2026-08-23-market-data-coverage-completion-design.md`

## Global Constraints

- Build Wave 1 on top of the completed Wave 0 backend and frontend branches in new isolated worktrees.
- Preserve unrelated dirty and untracked files in both original checkouts.
- Do not modify or delete existing formal weekly output directories.
- Apply `as_of_date` and source publication lag before snapshot or derived calculations.
- H.4.1 inputs use no observation before its publication day; historical formal backfill is not performed by this task.
- Net liquidity uses exact matched observation dates and USD billions: `Fed total assets - TGA - ON RRP take-up`.
- Correlations use matched daily transformations, trailing 65 and 130 observations, and minimum valid counts of 52 and 104 respectively.
- Price inputs use simple daily returns; yield and breakeven inputs use daily level changes.
- Public Yahoo/Sina inputs and calculations that depend on them are `public_proxy` and optional. Their failure publishes no business row, remains visible in `source_log.csv`, and cannot replace or block unrelated official rows.
- Every calculated row carries a registered source reference, `calculation_id`, `formula_version`, and `input_series_codes`.
- Automated tests use deterministic fixtures and never perform live network refreshes.
- Follow TDD and capture the expected RED before production changes.
- Run focused suites before complete repository suites and commit only Wave 1 files.

---

## Planned File Structure

### Market-data repository

- Create `capital_weekly/cross_asset.py`: pure daily transformation and rolling-correlation calculations.
- Modify `capital_weekly/returns.py`: support absolute USD-billion and correlation-point changes.
- Modify `capital_weekly/macro_assets.py`: normalize H.4.1 units, apply publication lag, register Wave 1 calculations, classify source tier/requiredness, and preserve lineage.
- Modify `data/capital_weekly_macro_assets.csv`: add official liquidity inputs, registered calculations, copper, major FX, hidden correlation inputs, and eight correlation outputs.
- Modify `scripts/fetch_macro_assets.py`: omit failed optional business rows and write `liquidity.csv` and `cross_asset.csv` atomically.
- Modify `capital_weekly/weekly_release.py`: add dataset contract version 3, validate new files, optional proxy failures, and calculated dependencies resolved through the complete macro source registry.
- Modify `capital_weekly/release_migration.py`: distinguish existing version-2 weeks from version-3 weeks without inventing new files.
- Modify focused tests for returns, macro assets, cutoff behavior, release validation, release migration, and CLI output.

### Dashboard repository

- Modify `lib/market/types.ts`, `lib/market/contracts.ts`, and `lib/market/loaders.ts`: support contract version 3 plus `liquidity` and `crossAsset` datasets.
- Modify `lib/market/csv.ts`: preserve registered cross-file calculation provenance and exact input-file labels.
- Modify `components/terminal/views/macro-view.tsx`: add liquidity and a purpose-built cross-asset correlation table.
- Modify `components/terminal/return-table.tsx`: render derived provenance without an empty external link.
- Modify `components/terminal/detail-drawer.tsx`: expose cutoff, source tier, formula version, calculation id, and input series.
- Modify `components/terminal/terminal-nav.tsx` and `components/terminal/terminal-shell.tsx`: rename the page to Macro & Liquidity and include new records in search/as-of behavior.
- Modify frontend contract, loader, view, fixture, E2E, and manifest tests.

---

### Task 1: Implement deterministic Wave 1 histories and calculations

**Repository:** `/Users/a1-6/Documents/market data`

**Files:**

- Create: `capital_weekly/cross_asset.py`
- Modify: `capital_weekly/returns.py`
- Modify: `capital_weekly/macro_assets.py`
- Modify: `data/capital_weekly_macro_assets.csv`
- Test: `tests/test_capital_weekly_returns.py`
- Test: `tests/test_capital_weekly_macro_assets.py`
- Test: `tests/test_capital_weekly_macro_as_of.py`

**Interfaces:**

- Produces `rolling_correlation_history(histories, left_code, right_code, left_transform, right_transform, window, minimum_observations) -> list[dict[str, date | float]]`.
- Registers `UST30Y5Y`, `USHY_IG_OAS`, `FED_NET_LIQUIDITY`, and eight `<PAIR>_CORR_<13W|26W>` series.
- Normalizes `WALCL` and `WTREGEN` from USD millions to USD billions before storing their histories.
- Treats H.4.1 observations as known one calendar day after their observation date.

- [ ] **Step 1: Write failing pure-calculation tests**

Add deterministic tests proving:

```python
result = rolling_correlation_history(
    histories,
    "LEFT",
    "RIGHT",
    "pct_return",
    "level_change",
    window=5,
    minimum_observations=4,
)
self.assertEqual(result[-1]["date"], date(2026, 8, 7))
self.assertAlmostEqual(result[-1]["value"], expected_correlation)
```

Also assert exact-date inner joins, zero-variance rejection, non-finite rejection, and no output before the minimum observation count. Add return tests showing `usd_billions` and `correlation_points` changes are absolute differences.

- [ ] **Step 2: Run the calculation tests and verify RED**

Run:

```bash
python3 -m unittest -v \
  tests.test_capital_weekly_returns \
  tests.test_capital_weekly_cross_asset
```

Expected: FAIL because `capital_weekly.cross_asset` and the two absolute change units do not exist.

- [ ] **Step 3: Implement the pure calculation module and units**

Implement independent daily transforms, exact-date alignment, trailing windows, minimum-count enforcement, and finite Pearson correlation. Extend `ChangeUnit` and `_change` so `usd_billions` and `correlation_points` return `latest - base`.

- [ ] **Step 4: Write failing macro-provider and cutoff tests**

Use fake histories to assert:

- `fred_millions_to_billions` maps `8_100_000` to `8_100.0`.
- a Wednesday H.4.1 observation is excluded by a Wednesday cutoff and included by Thursday.
- ON RRP uses `RRPONTSYD` take-up, never `RRPONTSYAWARD`.
- net liquidity equals matched-date assets minus TGA minus take-up.
- 5s30s and HY-minus-IG use exact shared dates.
- each 13/26-week correlation uses the registered inputs, transforms, windows, and minimum observations.
- proxy inputs and dependent correlation records are `public_proxy` and `optional`; official liquidity records are `official` and `required`.

- [ ] **Step 5: Run the macro tests and verify RED**

Run:

```bash
python3 -m unittest -v \
  tests.test_capital_weekly_macro_assets \
  tests.test_capital_weekly_macro_as_of
```

Expected: FAIL because the Wave 1 registry, provider normalization, publication lag, and calculation dispatch are absent.

- [ ] **Step 6: Implement the provider registry and universe**

Add these stable families:

```text
FED_TOTAL_ASSETS     WALCL       official      USD billions
TGA_BALANCE         WTREGEN     official      USD billions
ON_RRP_TAKE_UP      RRPONTSYD   official      USD billions
FED_NET_LIQUIDITY   calculated  official      USD billions
UST30Y5Y            calculated  official      percentage points
USHY_IG_OAS         calculated  official      percentage points
COMEX_COPPER        HG=F        public_proxy  USD/pound
EUR_USD USD_JPY GBP_USD AUD_USD USD_CAD USD_CHF
SPY_CLOSE_PROXY TLT_CLOSE_PROXY             hidden public_proxy inputs
```

Register the eight correlation rows for stock/bond, equity/USD, gold/real-yield, and oil/breakeven across 13 and 26 weeks. The `source_url` of every calculated row must come from one exact `CALCULATED_SOURCE_REFERENCES` entry.

- [ ] **Step 7: Run focused Task 1 tests**

Run:

```bash
python3 -m unittest -v \
  tests.test_capital_weekly_returns \
  tests.test_capital_weekly_cross_asset \
  tests.test_capital_weekly_macro_assets \
  tests.test_capital_weekly_macro_as_of
```

Expected: all tests pass without network access.

- [ ] **Step 8: Commit Task 1**

```bash
git add capital_weekly/cross_asset.py capital_weekly/returns.py \
  capital_weekly/macro_assets.py data/capital_weekly_macro_assets.csv \
  tests/test_capital_weekly_returns.py \
  tests/test_capital_weekly_cross_asset.py \
  tests/test_capital_weekly_macro_assets.py \
  tests/test_capital_weekly_macro_as_of.py
git commit -m "feat: add Wave 1 macro calculations"
```

---

### Task 2: Publish Wave 1 through dataset contract version 3

**Repository:** `/Users/a1-6/Documents/market data`

**Files:**

- Modify: `scripts/fetch_macro_assets.py`
- Modify: `capital_weekly/weekly_release.py`
- Modify: `capital_weekly/release_migration.py`
- Test: `tests/test_capital_weekly_macro_assets.py`
- Test: `tests/test_capital_weekly_weekly_release.py`
- Test: `tests/test_capital_weekly_release_migration.py`

**Interfaces:**

- Produces `liquidity.csv` and `cross_asset.csv` in the existing macro pipeline directory.
- Sets `DATASET_CONTRACT_VERSION = 3`; versions 1 and 2 remain readable and validate against their historical file sets.
- Resolves registered macro dependencies by `series_code` across all macro business rows and `macro/source_log.csv`.
- Allows `FETCH_FAILED` only when the macro source-log row says `requiredness=optional`; failed optional detail rows are absent from business CSVs.

- [ ] **Step 1: Write failing CLI and release tests**

Assert the CLI atomically writes both new files, filters failed optional proxy rows, and keeps their failure rows in `source_log.csv`. Extend staged fixtures so version 3 requires non-empty valid `liquidity.csv`, permits empty `cross_asset.csv`, and accepts a registered cross-asset row only when all named source-log dependencies resolve to HTTP(S) roots.

- [ ] **Step 2: Run release tests and verify RED**

Run:

```bash
python3 -m unittest -v \
  tests.test_capital_weekly_macro_assets \
  tests.test_capital_weekly_weekly_release \
  tests.test_capital_weekly_release_migration
```

Expected: FAIL because the CLI emits neither file and contract version 3 is unsupported.

- [ ] **Step 3: Implement versioned publication and dependency validation**

Keep separate file sets for contracts 1, 2, and 3. Read all staged macro datasets before row validation, build a single calculation-dependency registry keyed by `series_code`, and use it only for macro calculated rows. Reject missing inputs, unregistered references, cycles, non-HTTP roots, post-Sunday dates, and non-finite values.

- [ ] **Step 4: Implement migration detection without backfill**

Detect version 3 only when both new macro files exist alongside the version-2 context markers. A week with neither file remains version 2. A week with exactly one file is a mixed contract and must fail rather than fabricate the other file.

- [ ] **Step 5: Run focused and complete backend tests**

Run:

```bash
python3 -m unittest -v \
  tests.test_capital_weekly_macro_assets \
  tests.test_capital_weekly_weekly_release \
  tests.test_capital_weekly_release_migration
python3 -m unittest -v
node --test tests/test_verify_weekly_workbooks.mjs
```

Expected: all tests pass without network access.

- [ ] **Step 6: Commit Task 2**

```bash
git add scripts/fetch_macro_assets.py capital_weekly/weekly_release.py \
  capital_weekly/release_migration.py \
  tests/test_capital_weekly_macro_assets.py \
  tests/test_capital_weekly_weekly_release.py \
  tests/test_capital_weekly_release_migration.py
git commit -m "feat: publish Wave 1 macro datasets"
```

---

### Task 3: Load and display Wave 1 in the Dashboard

**Repository:** `/Users/a1-6/Documents/行业与个股分析`

**Files:**

- Modify: `lib/market/types.ts`
- Modify: `lib/market/contracts.ts`
- Modify: `lib/market/csv.ts`
- Modify: `lib/market/loaders.ts`
- Modify: `components/terminal/views/macro-view.tsx`
- Modify: `components/terminal/return-table.tsx`
- Modify: `components/terminal/detail-drawer.tsx`
- Modify: `components/terminal/terminal-nav.tsx`
- Modify: `components/terminal/terminal-shell.tsx`
- Test: `tests/market/csv.test.ts`
- Test: `tests/market/loaders.test.ts`
- Test: `tests/market/macro-view.test.tsx`
- Test: `tests/dashboard.test.tsx`

**Interfaces:**

- Extends `DatasetContractVersion` to `1 | 2 | 3` and `DatasetKey` with `liquidity` and `crossAsset`.
- Extends `WeekSnapshot.macro` with `liquidity: MacroRecord[]` and `crossAsset: MacroRecord[]`.
- Lets each registered calculated-source policy declare exact `inputFiles` for drawer provenance.
- Version 1 and 2 snapshots return empty arrays for the new keys; version 3 requires and loads their contracts.

- [ ] **Step 1: Write failing contract and loader tests**

Assert versions 1 and 2 keep their existing contract lists, version 3 includes both new files, a version-3 fixture loads both arrays, and a registered correlation receives derived provenance with its exact formula and input files.

- [ ] **Step 2: Run contract tests and verify RED**

Run:

```bash
npm test -- tests/market/csv.test.ts tests/market/loaders.test.ts
```

Expected: FAIL because version 3 and both datasets do not exist.

- [ ] **Step 3: Implement contracts, parsing, and loader types**

Register liquidity policies for net liquidity and cross-asset policies for all eight correlations. Keep exact row-specific formulas, use `macro/source_log.csv` as the external input registry in provenance, and do not weaken source validation for versions 1 or 2.

- [ ] **Step 4: Write failing page and drawer tests**

Assert:

- navigation says `宏观与流动性`;
- liquidity rows render in their own section;
- correlations render as coefficients with 13/26-week labels and input series;
- proxy names contain a visible `代理` label;
- derived rows do not render empty external anchors;
- opening a derived record shows `known_as_of`, source tier, calculation id, formula version, input series, formula, and input files.

- [ ] **Step 5: Run page tests and verify RED**

Run:

```bash
npm test -- tests/market/macro-view.test.tsx tests/dashboard.test.tsx
```

Expected: FAIL because the page has no liquidity/correlation presentation and the drawer omits Wave 1 lineage fields.

- [ ] **Step 6: Implement the Macro & Liquidity presentation**

Add a liquidity return table and a compact cross-asset table with code/name, window, coefficient, end date, inputs, quality, and derived source label. Include both arrays in global search and data-as-of calculations. Preserve empty-section behavior.

- [ ] **Step 7: Run focused frontend tests**

Run:

```bash
npm test -- \
  tests/market/csv.test.ts \
  tests/market/contracts.test.ts \
  tests/market/loaders.test.ts \
  tests/market/macro-view.test.tsx \
  tests/dashboard.test.tsx
```

Expected: all focused tests pass.

- [ ] **Step 8: Commit Task 3**

```bash
git add lib/market/types.ts lib/market/contracts.ts lib/market/csv.ts \
  lib/market/loaders.ts components/terminal/views/macro-view.tsx \
  components/terminal/return-table.tsx components/terminal/detail-drawer.tsx \
  components/terminal/terminal-nav.tsx components/terminal/terminal-shell.tsx \
  tests/market/csv.test.ts tests/market/contracts.test.ts \
  tests/market/loaders.test.ts tests/market/macro-view.test.tsx \
  tests/dashboard.test.tsx
git commit -m "feat: display Wave 1 macro structure"
```

---

### Task 4: Prove Wave 1 end to end with a two-week fixture

**Repository:** `/Users/a1-6/Documents/行业与个股分析`

**Files:**

- Modify: `tests/helpers/market-fixture.ts`
- Modify: `tests/fixtures/market-data/outputs/week_20260727-20260802/manifest.json`
- Modify: `tests/fixtures/market-data/outputs/week_20260803-20260809/manifest.json`
- Create: both weeks' `liquidity.csv` and `cross_asset.csv`
- Modify: both weeks' fixed-income, commodity, FX, and macro source-log fixtures as required by Wave 1 lineage
- Modify: `scripts/regenerate-market-fixture-manifests.mjs`
- Modify: `e2e/dashboard.spec.ts`

**Interfaces:**

- Produces two complete deterministic version-3 weeks with different Wave 1 values.
- Preserves exact manifest hashes and row counts after fixture edits.
- Proves the browser can search, render, compare, and inspect Wave 1 data without a live backend refresh.

- [ ] **Step 1: Write the failing E2E assertions**

Navigate to Macro & Liquidity and assert visible official liquidity rows, net-liquidity formula provenance, copper/FX proxy labels, 13/26-week correlations, and the changed value after selecting the previous week.

- [ ] **Step 2: Run the focused E2E and verify RED**

Run:

```bash
npx playwright test e2e/dashboard.spec.ts --grep "Wave 1"
```

Expected: FAIL because the version-3 fixture files and UI evidence are absent.

- [ ] **Step 3: Extend the two-week fixture and regenerate manifests**

Create valid deterministic rows for every Wave 1 family, update the helper snapshot shape, and run:

```bash
node scripts/regenerate-market-fixture-manifests.mjs
```

- [ ] **Step 4: Run complete frontend verification**

Run:

```bash
npm test
npm run lint
npm run build
npx playwright test
```

Expected: all unit, lint, build, and browser tests pass.

- [ ] **Step 5: Commit Task 4**

```bash
git add tests/helpers/market-fixture.ts tests/fixtures/market-data \
  scripts/regenerate-market-fixture-manifests.mjs e2e/dashboard.spec.ts
git commit -m "test: verify Wave 1 market data end to end"
```

---

## Final Verification and Handoff

- [ ] Confirm both Wave 1 worktrees are clean.
- [ ] Record backend RED evidence, backend focused GREEN, full `python3 -m unittest -v`, and workbook verifier result.
- [ ] Record frontend RED evidence, focused GREEN, full unit, lint, build, and Playwright results.
- [ ] Do not run a live refresh or publish a real formal week without explicit user authorization.
- [ ] Report both branch names, commit SHAs, files changed, remaining source risks, and the next unimplemented wave.
