# Market-Data Coverage Wave 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore formal weekly publication for the already implemented Treasury real-yield, breakeven, 5Y5Y, and Yahoo volatility metrics and make those records visible with correct derived provenance in the Capital Weekly Dashboard.

**Architecture:** Keep the existing five-pipeline release. Extend the backend and frontend calculated-source registries so every existing Treasury calculation is validated through its HTTP-sourced dependencies, then let the existing optional volatility provider flow through `financial_conditions.csv`. The Dashboard loads calculated fixed-income rows as derived records, renders them in the macro view, and renders successful volatility rows in the existing context evidence view.

**Tech Stack:** Python 3, pandas, unittest; Next.js 16, React 19, TypeScript 5, Vitest, Testing Library, Playwright.

**Spec:** `docs/superpowers/specs/2026-08-23-market-data-coverage-completion-design.md`

## Global Constraints

- Work in isolated worktrees created at execution time.
- Preserve unrelated dirty and untracked files in both original checkouts.
- Do not modify or delete existing formal weekly output directories.
- Apply the target-Sunday cutoff before any value or calculation.
- A calculated row is valid only when every registered dependency is present in
  the same dataset and recursively resolves to finite HTTP(S)-sourced inputs.
  Cyclic calculated dependencies are invalid.
- Yahoo volatility remains optional and all-or-nothing; `FETCH_FAILED` remains visible and does not publish stale rows.
- Do not run a live network refresh during automated verification.
- Follow TDD and record the expected RED before production changes.
- Run focused tests followed by the complete repository suites.
- Commit only the files owned by the current task.

---

## Planned File Structure

### Market-data repository

- Modify `capital_weekly/weekly_release.py`: register all existing Treasury calculated-source references and their dependencies.
- Modify `tests/test_capital_weekly_weekly_release.py`: prove valid calculated rows pass and missing dependencies fail.

### Dashboard repository

- Modify `lib/market/types.ts`: let a calculated-source policy carry the registered formula.
- Modify `lib/market/csv.ts`: emit derived provenance for registered calculated rows after dependency validation.
- Modify `lib/market/contracts.ts`: register 2s10s, 5Y/10Y breakeven, and 5Y5Y policies.
- Modify `tests/market/csv.test.ts`: verify derived provenance and missing-dependency rejection.
- Modify `components/terminal/views/macro-view.tsx`: retain validated derived records instead of filtering them out for lacking a direct URL.
- Modify `tests/market/macro-view.test.tsx`: verify calculated rates render and open formula provenance.
- Modify `tests/market/context-view.test.tsx`: verify VIX levels and term metrics render through financial-condition evidence.
- Modify `tests/helpers/market-fixture.ts`: generate a complete Wave 0 two-week fixture.
- Create `scripts/regenerate-market-fixture-manifests.mjs`: recompute static E2E fixture row counts and hashes after fixture CSV edits.
- Modify `tests/market/loaders.test.ts`: verify Wave 0 fixture loading.
- Modify `e2e/dashboard.spec.ts`: verify real yields, breakevens, and VIX provenance in the browser.

---

### Task 1: Register every backend Treasury calculation

**Repository:** `/Users/a1-6/Documents/market data`

**Files:**

- Modify: `capital_weekly/weekly_release.py`
- Modify: `tests/test_capital_weekly_weekly_release.py`

**Interfaces:**

- Consumes: calculated references emitted by `capital_weekly.macro_assets.CALCULATED_SOURCE_REFERENCES`.
- Produces: `CALCULATED_SOURCE_POLICIES: dict[str, tuple[str, tuple[str, ...]]]` entries for `UST10Y2Y`, `US_BE5Y`, `US_BE10Y`, and `US_5Y5Y`.
- Invariant: a calculated record passes only if all dependency rows exist and
  recursively terminate in HTTP(S)-sourced rows without a cycle.

- [ ] **Step 1: Add a failing acceptance test for all four calculated rows**

Add this test beside `test_calculated_curve_requires_both_http_sourced_dependencies`:

```python
def test_accepts_every_registered_treasury_calculation(self):
    path = self.outputs["macro_assets"] / "fixed_income.csv"
    rows = [
        fixture_row(MACRO_FIELDS, series_code=code)
        for code in ("UST2Y", "UST5Y", "UST10Y", "UST_REAL5Y", "UST_REAL10Y")
    ]
    rows.extend(
        [
            fixture_row(
                MACRO_FIELDS,
                series_code="UST10Y2Y",
                provider="calculated",
                source_url=(
                    "calculated:UST10Y-UST2Y "
                    "(shared Treasury observation dates)"
                ),
            ),
            fixture_row(
                MACRO_FIELDS,
                series_code="US_BE5Y",
                provider="calculated",
                source_url=(
                    "calculated:UST5Y-UST_REAL5Y "
                    "(shared Treasury observation dates)"
                ),
            ),
            fixture_row(
                MACRO_FIELDS,
                series_code="US_BE10Y",
                provider="calculated",
                source_url=(
                    "calculated:UST10Y-UST_REAL10Y "
                    "(shared Treasury observation dates)"
                ),
            ),
            fixture_row(
                MACRO_FIELDS,
                series_code="US_5Y5Y",
                provider="calculated",
                source_url=(
                    "calculated:5Y5Y from US_BE5Y and US_BE10Y "
                    "(shared Treasury observation dates)"
                ),
            ),
        ]
    )
    write_csv(path, MACRO_FIELDS, rows)

    manifest = validate_staged_week(self.root, self.window)

    entry = next(item for item in manifest["files"] if item["path"].endswith("fixed_income.csv"))
    self.assertEqual(entry["rows"], len(rows))
```

- [ ] **Step 2: Run the acceptance test and verify RED**

Run:

```bash
python3 -m unittest -v \
  tests.test_capital_weekly_weekly_release.StagedValidationTests.test_accepts_every_registered_treasury_calculation
```

Expected: FAIL because the breakeven or 5Y5Y `source_url` is not a registered calculation reference.

- [ ] **Step 3: Add failing missing-dependency cases**

Add one subtest per new reference. Remove one dependency from an otherwise valid fixed-income table and assert the error names the exact missing code:

```python
cases = {
    "US_BE5Y": ("UST_REAL5Y", "calculated:UST5Y-UST_REAL5Y (shared Treasury observation dates)"),
    "US_BE10Y": ("UST_REAL10Y", "calculated:UST10Y-UST_REAL10Y (shared Treasury observation dates)"),
    "US_5Y5Y": ("US_BE10Y", "calculated:5Y5Y from US_BE5Y and US_BE10Y (shared Treasury observation dates)"),
}
```

For `US_5Y5Y`, include `US_BE5Y` and `US_BE10Y` as valid calculated rows plus their five HTTP-sourced Treasury dependencies before removing `US_BE10Y`.

- [ ] **Step 4: Register the backend policies and recursive resolver**

Replace the one-entry registry with:

```python
CALCULATED_SOURCE_POLICIES = {
    CALCULATED_SOURCE_REFERENCES["UST10Y2Y"]: (
        "series_code",
        ("UST10Y", "UST2Y"),
    ),
    CALCULATED_SOURCE_REFERENCES["US_BE5Y"]: (
        "series_code",
        ("UST5Y", "UST_REAL5Y"),
    ),
    CALCULATED_SOURCE_REFERENCES["US_BE10Y"]: (
        "series_code",
        ("UST10Y", "UST_REAL10Y"),
    ),
    CALCULATED_SOURCE_REFERENCES["US_5Y5Y"]: (
        "series_code",
        ("US_BE5Y", "US_BE10Y"),
    ),
}
```

Import `CALCULATED_SOURCE_REFERENCES` from `capital_weekly.macro_assets` so the validator cannot drift from the producer strings.

Update `_source_reference_error` to resolve dependencies recursively. A direct
HTTP(S) row succeeds. A calculated row must have `provider == "calculated"`, a
registered reference, and resolvable dependencies. Track `(identity_column,
identity_value)` entries in a `visiting` set and return `calculated dependency
cycle` when an entry repeats. This allows `US_5Y5Y` to depend on `US_BE5Y` and
`US_BE10Y`, which in turn terminate in Treasury HTTP sources.

- [ ] **Step 5: Run focused backend tests**

Run:

```bash
python3 -m unittest -v \
  tests.test_capital_weekly_weekly_release \
  tests.test_capital_weekly_macro_assets \
  tests.test_capital_weekly_macro_as_of \
  tests.test_capital_weekly_volatility
```

Expected: all focused tests pass.

- [ ] **Step 6: Run the complete backend suite**

Run:

```bash
python3 -m unittest -v
```

Expected: all tests pass with no network access.

- [ ] **Step 7: Commit Task 1**

```bash
git add capital_weekly/weekly_release.py tests/test_capital_weekly_weekly_release.py
git commit -m "fix: validate registered Treasury calculations"
```

---

### Task 2: Preserve calculated fixed-income provenance in the Dashboard loader

**Repository:** `/Users/a1-6/Documents/行业与个股分析`

**Files:**

- Modify: `lib/market/types.ts`
- Modify: `lib/market/csv.ts`
- Modify: `lib/market/contracts.ts`
- Modify: `tests/market/csv.test.ts`

**Interfaces:**

- Extends: `CalculatedSourcePolicy` with `formula: string`.
- Produces: calculated fixed-income records with `provenance.kind === "derived"`, `source_url === ""`, a registered `formula`, and the same fixed-income CSV as the input file.
- Preserves: recursive dependency and HTTP-root validation before derived provenance is created.

- [ ] **Step 1: Write a failing parser test for 5Y breakeven provenance**

Create a `fixedIncomeContract` CSV string containing HTTP-sourced `UST5Y`, HTTP-sourced `UST_REAL5Y`, and calculated `US_BE5Y`. Parse it and assert:

```typescript
const breakeven = rows.find((row) => row.series_code === "US_BE5Y");
expect(breakeven?.provenance).toMatchObject({
  kind: "derived",
  source_url: "",
  formula: "UST5Y - UST_REAL5Y on shared Treasury observation dates",
});
expect(breakeven?.provenance.input_files).toEqual([
  "macro/fixed_income.csv",
]);
```

- [ ] **Step 2: Run the parser test and verify RED**

Run:

```bash
npm test -- tests/market/csv.test.ts
```

Expected: FAIL because calculated rows currently receive source provenance through the first dependency URL.

- [ ] **Step 3: Write failing parser tests for all policies and dependency rejection**

Assert these exact formulas:

```typescript
const formulas = {
  UST10Y2Y: "UST10Y - UST2Y on shared Treasury observation dates",
  US_BE5Y: "UST5Y - UST_REAL5Y on shared Treasury observation dates",
  US_BE10Y: "UST10Y - UST_REAL10Y on shared Treasury observation dates",
  US_5Y5Y: "(((1 + BE10Y / 100)^2) / (1 + BE5Y / 100) - 1) * 100",
};
```

For each calculated reference, remove one dependency and assert parsing rejects
the row with `registered calculation reference` in the error. Add a synthetic
two-row calculated cycle and assert it is rejected with `calculated dependency
cycle`.

- [ ] **Step 4: Extend the policy type and provenance builder**

Change the type to:

```typescript
export interface CalculatedSourcePolicy {
  reference: string;
  identityColumn: string;
  dependencyValues: readonly string[];
  formula: string;
}
```

In `lib/market/csv.ts`, resolve both the matching policy and its dependency
roots recursively. A dependency may be directly HTTP-sourced or another
registered calculated row. Track visited row identities and reject cycles.
Pass the policy into `provenanceFor`. When present, return:

```typescript
{
  ...base,
  ...quality,
  kind: "derived",
  source_url: "",
  formula: policy.formula,
  input_files: [base.file],
}
```

Do not create derived provenance until every dependency recursively terminates
in at least one HTTP(S) source.

- [ ] **Step 5: Register all fixed-income policies**

In `fixedIncomeContract`, register the exact four references produced by the backend and the formulas from Step 3. Leave other macro tables without calculated policies.

- [ ] **Step 6: Run focused frontend contract tests**

Run:

```bash
npm test -- tests/market/csv.test.ts tests/market/loaders.test.ts tests/market/manifest.test.ts
npm run lint
```

Expected: all tests and lint pass.

- [ ] **Step 7: Commit Task 2**

```bash
git add lib/market/types.ts lib/market/csv.ts lib/market/contracts.ts tests/market/csv.test.ts
git commit -m "feat: preserve derived Treasury provenance"
```

---

### Task 3: Render Wave 0 rates and volatility records

**Repository:** `/Users/a1-6/Documents/行业与个股分析`

**Files:**

- Modify: `components/terminal/views/macro-view.tsx`
- Modify: `tests/market/macro-view.test.tsx`
- Modify: `tests/market/context-view.test.tsx`

**Interfaces:**

- Consumes: source and derived `MacroRecord` values from Task 2.
- Produces: macro tables containing both record kinds when quality is `OK`.
- Proves: VIX levels and term rows already loaded through `financialConditions` render in the context evidence table.

- [ ] **Step 1: Write a failing calculated-rate rendering test**

Create a `MacroRecord` whose provenance is:

```typescript
provenance: {
  week: week.id,
  dataset: "fixedIncome",
  file: "macro/fixed_income.csv",
  kind: "derived",
  source_url: "",
  formula: "UST5Y - UST_REAL5Y on shared Treasury observation dates",
  input_files: ["macro/fixed_income.csv"],
  qc_flag: "OK",
}
```

Render `MacroView` and assert `US_BE5Y` and its value are visible and clicking its inspect button returns that exact record.

- [ ] **Step 2: Run the macro-view test and verify RED**

Run:

```bash
npm test -- tests/market/macro-view.test.tsx
```

Expected: FAIL because `MacroView` filters out rows without a direct HTTP URL.

- [ ] **Step 3: Retain validated derived macro rows**

Replace the direct URL filter with a predicate that accepts either record kind and requires successful quality:

```typescript
function displayable(record: MacroRecord): boolean {
  const quality = record.provenance.qc_flag ?? record.provenance.source_status;
  return quality === "OK" && (
    record.provenance.kind === "derived" ||
    /^https?:\/\//i.test(record.provenance.source_url)
  );
}
```

- [ ] **Step 4: Add a VIX context rendering test**

Add `vix_1m_level` and `vix_1m_3m_ratio` records to a snapshot's `financialConditions` and assert the financial evidence table contains both codes, values, dates, `Yahoo Finance (Cboe indices)`, and inspect buttons.

- [ ] **Step 5: Run focused view tests**

Run:

```bash
npm test -- tests/market/macro-view.test.tsx tests/market/context-view.test.tsx tests/dashboard.test.tsx
```

Expected: all focused tests pass.

- [ ] **Step 6: Run frontend lint and build**

Run:

```bash
npm run lint
npm run build
```

Expected: both commands exit 0.

- [ ] **Step 7: Commit Task 3**

```bash
git add components/terminal/views/macro-view.tsx tests/market/macro-view.test.tsx tests/market/context-view.test.tsx
git commit -m "feat: display Wave 0 rates and volatility"
```

---

### Task 4: Verify Wave 0 through loaders and the browser

**Repository:** `/Users/a1-6/Documents/行业与个股分析`

**Files:**

- Modify: `tests/helpers/market-fixture.ts`
- Modify: `tests/market/loaders.test.ts`
- Modify: `e2e/dashboard.spec.ts`
- Create: `scripts/regenerate-market-fixture-manifests.mjs`
- Regenerate: `tests/fixtures/market-data/outputs/week_20260727-20260802/**`
- Regenerate: `tests/fixtures/market-data/outputs/week_20260803-20260809/**`

**Interfaces:**

- Produces: two complete manifest-valid fixture weeks containing nominal 5Y, real 5Y/10Y, 5Y/10Y breakevens, 5Y5Y, VIX 9D/1M/3M/6M, SKEW, and three term calculations.
- Proves: the latest formal fixture week displays the new records and their source or calculation provenance.

- [ ] **Step 1: Extend the fixture generator**

Generate five HTTP-sourced Treasury inputs and four calculated rows using the exact registered references. Add eight successful Yahoo volatility rows to `financial_conditions.csv` and an `OK` optional source-log entry for `yahoo_volatility_signals`.

- [ ] **Step 2: Create the deterministic manifest-regeneration script**

Create a Node script using `node:fs/promises`, `node:crypto`, and
`csv-parse/sync`. For each direct child matching `week_YYYYMMDD-YYYYMMDD` under
`tests/fixtures/market-data/outputs`, recursively enumerate every regular file
except `manifest.json`, calculate CSV row counts with the same parser options as
`tests/helpers/market-fixture.ts`, calculate SHA-256 over file bytes, sort paths,
replace only the manifest's `files` array, and write JSON with a trailing
newline.

- [ ] **Step 3: Regenerate fixtures with current hashes**

Run:

```bash
node scripts/regenerate-market-fixture-manifests.mjs
```

Expected: every changed CSV has a matching manifest row count and SHA-256. The
script does not touch business CSV values.

- [ ] **Step 4: Add loader assertions**

Assert the latest snapshot contains:

```typescript
expect(snapshot.macro.fixedIncome.map((row) => row.series_code)).toEqual(
  expect.arrayContaining(["UST5Y", "UST_REAL5Y", "UST_REAL10Y", "US_BE5Y", "US_BE10Y", "US_5Y5Y"]),
);
expect(snapshot.context.financialConditions.map((row) => row.metric_code)).toEqual(
  expect.arrayContaining(["vix_1m_level", "vix_1m_3m_ratio"]),
);
```

Also assert `US_BE5Y.provenance.kind === "derived"` and `vix_1m_level.provenance.kind === "source"`.

- [ ] **Step 5: Run loader and catalog tests**

Run:

```bash
npm test -- tests/market/loaders.test.ts tests/market/catalog.test.ts tests/market/manifest.test.ts
```

Expected: all tests pass and both fixture weeks remain selectable.

- [ ] **Step 6: Add Wave 0 Playwright assertions**

Extend the macro flow to search for `US_BE5Y`, open its drawer, and assert the registered formula and `fixed_income.csv` appear. Extend the context flow to search for `vix_1m_level`, open its drawer, and assert a Yahoo source link is present.

- [ ] **Step 7: Run complete frontend verification**

Run:

```bash
npm test
npm run lint
npm run build
npm run test:e2e
```

Expected: every command exits 0.

- [ ] **Step 8: Commit Task 4**

```bash
git add scripts/regenerate-market-fixture-manifests.mjs tests/helpers/market-fixture.ts tests/market/loaders.test.ts e2e/dashboard.spec.ts tests/fixtures/market-data
git commit -m "test: verify Wave 0 market data end to end"
```

---

### Task 5: Final Wave 0 cross-repository verification

**Repositories:** Both repositories

**Files:** No production changes expected.

- [ ] **Step 1: Run the complete backend suite from a fresh process**

```bash
python3 -m unittest -v
node --test tests/test_verify_weekly_workbooks.mjs
```

- [ ] **Step 2: Run the complete frontend suite from a fresh process**

```bash
npm test
npm run lint
npm run build
npm run test:e2e
```

- [ ] **Step 3: Inspect repository integrity**

In both worktrees run:

```bash
git status --short
git diff --check HEAD~1..HEAD
git log --oneline --decorate -6
```

Expected: only intentional task files are committed, no generated runtime output is staged, and no unrelated baseline file changed.

- [ ] **Step 4: Perform a read-only current-output smoke check**

Load the newest existing complete formal week through the Dashboard and verify that drafts remain excluded. Do not run a live provider refresh in this step.

- [ ] **Step 5: Report the live-refresh boundary**

Report that implementation and deterministic publication are complete. A new live formal week may be produced only by the coordinated refresh after source availability is checked; if the live refresh is run, preserve its status and do not replace the prior formal week on any failure.
