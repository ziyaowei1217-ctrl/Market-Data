# Market Data Coverage Wave 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the coverage matrix with a deterministic capability inventory in every new formal-week manifest and a Dashboard audit table that distinguishes available data, explicit proxies, unconfigured public paths, licensed gaps, and non-applicable items without publishing placeholder values.

**Architecture:** Keep dataset contract version 5 and the existing five pipelines. Add manifest schema version 3 with a backend-generated `capabilities` array derived from registered CSV evidence and source-log status, while preserving read compatibility for schema version 2 weeks. The Dashboard validates schema 3, carries capability records in `WeekSnapshot`, and presents them only on Data Audit; Wave 5 adds no alternative-data business-value table because no stable auditable Google Trends acquisition path is available.

**Tech Stack:** Python 3 standard library and `unittest`; TypeScript, Next.js, React, Vitest, Testing Library, and Playwright.

**Spec:** `docs/superpowers/specs/2026-08-23-market-data-coverage-completion-design.md`

## Global Constraints

- Apply the target Sunday cutoff before calculating any snapshot or capability evidence.
- Never publish placeholder numbers for paid, licensed, missing, or unconfigured data.
- Capability status is exactly one of `available`, `failed`, `not_configured`, `unavailable_licensed`, or `not_applicable` and always carries a factual reason.
- Public proxies remain separately named and set `proxy: true`; they never inherit a proprietary product name.
- Manifest schema version 2 remains readable; new coordinated and migrated manifests use schema version 3.
- Tests use deterministic fixture files and never perform a real network refresh.
- Backend and frontend work stay in separate branches/worktrees; do not merge, push, or publish a formal week in this plan.

---

### Task 1: Deterministic backend capability manifest

**Files:**
- Create: `capital_weekly/capabilities.py`
- Modify: `capital_weekly/weekly_release.py`
- Modify: `capital_weekly/release_migration.py`
- Modify: `README.md`
- Create: `tests/test_capital_weekly_capabilities.py`
- Modify: `tests/test_capital_weekly_weekly_release.py`
- Modify: `tests/test_capital_weekly_release_migration.py`

**Interfaces:**
- Consumes: validated release directory paths, `weekly_context/source_log.csv`, typed output CSV rows, and the target `WeekWindow.end` already enforced by release validation.
- Produces: `build_capability_manifest(release_root: Path, target_end: date) -> list[dict[str, object]]` and manifest schema 3 field `capabilities`.
- Each capability record contains `capability_id`, `module`, `label`, `status`, `reason`, `proxy`, and `evidence_files`.

- [ ] **Step 1: Write failing capability-registry and evaluator tests**

  Cover unique/stable identifiers, the complete approved matrix, evidence-driven `available`, proxy flags, source-log mappings for `NOT_CONFIGURED` and `UNAVAILABLE_LICENSED`, missing registered evidence as `failed`, Google Trends as `not_configured`, and paid datasets as `unavailable_licensed`.

- [ ] **Step 2: Run the focused capability test and verify RED**

  Run: `python3 -m unittest -v tests.test_capital_weekly_capabilities`

  Expected: import failure for `capital_weekly.capabilities`.

- [ ] **Step 3: Implement the declarative registry and evaluator**

  Use immutable capability specifications and exact CSV identity rules. Read only validated files under the release root; preserve relative evidence paths; map optional provider statuses without inventing values. Include all rows from the approved user matrix, with separate available proxy capabilities where a proxy exists and explicit licensed/unconfigured rows for excluded products.

- [ ] **Step 4: Write failing release and migration manifest tests**

  Assert new manifests use `manifest_schema_version: 3`, include unique capability records, keep dataset contract version 5, and compare capability content when recognizing an existing manifest. Assert migrated releases regenerate audit metadata without adding business rows.

- [ ] **Step 5: Integrate manifest schema 3**

  Set `MANIFEST_SCHEMA_VERSION = 3`, call `build_capability_manifest` only after dataset validation, include the result in `build_release_manifest`, and require exact regenerated capability equality in existing-manifest validation.

- [ ] **Step 6: Document capability semantics**

  Add the five statuses, proxy rule, Google Trends decision, and schema 2 compatibility boundary to the coordinated-release README section.

- [ ] **Step 7: Run backend verification**

  Run focused modules, then `python3 -m unittest -v`, `python3 -m unittest -v tests.test_capital_weekly_workbook`, and `git diff --check`.

- [ ] **Step 8: Commit backend Task 1**

  Commit message: `feat: audit market data capabilities`

---

### Task 2: Dashboard capability audit

**Files:**
- Modify: `lib/market/types.ts`
- Modify: `lib/market/manifest.ts`
- Modify: `lib/market/loaders.ts`
- Modify: `components/terminal/views/audit-view.tsx`
- Modify: `components/terminal/detail-drawer.tsx` only if capability detail becomes interactive; otherwise leave unchanged.
- Modify: `app/globals.css`
- Modify: `tests/helpers/market-fixture.ts`
- Modify: `tests/fixtures/market-data/outputs/week_20260803-20260809/manifest.json`
- Modify: `tests/market/manifest.test.ts`
- Modify: `tests/market/loaders.test.ts`
- Modify: `tests/market/audit-view.test.tsx`
- Modify: `e2e/dashboard.spec.ts`

**Interfaces:**
- Consumes: schema 2 or schema 3 manifest JSON; schema 3 `capabilities` records from Task 1.
- Produces: `ReleaseCapability`, a schema-versioned manifest union, `WeekSnapshot.capabilities`, and a non-interactive `能力覆盖表` on Data Audit.

- [ ] **Step 1: Write failing manifest and loader tests**

  Require strict schema 3 capability fields, the exact status enum, unique safe IDs, boolean proxy flags, safe evidence paths that reference manifest files for `available` rows, schema 2 compatibility with an empty capability list, and schema 3 loader propagation.

- [ ] **Step 2: Run manifest and loader tests and verify RED**

  Run: `npm test -- tests/market/manifest.test.ts tests/market/loaders.test.ts`

  Expected: schema 3 rejected and `WeekSnapshot.capabilities` absent.

- [ ] **Step 3: Implement schema-versioned parsing and loading**

  Accept manifest schema versions 2 and 3. Validate every schema 3 capability before file loading, reject duplicates and unknown statuses, and expose `capabilities: []` for schema 2.

- [ ] **Step 4: Write the failing Audit page test**

  Assert the table shows module, capability, status, proxy/direct classification, reason, and evidence; global search filters capability rows; licensed gaps and Google Trends stay visible without numeric values; schema 2 weeks render no capability section.

- [ ] **Step 5: Implement the capability audit section**

  Add an accessible `能力覆盖表` ahead of source health. Use status labels without converting unavailable entries into failures of the weekly release, display `公开代理` for `proxy: true`, and keep source fetch filters scoped to the existing source table.

- [ ] **Step 6: Upgrade deterministic fixtures**

  Make the latest fixture schema 3 with representative available, proxy, not-configured, licensed, and non-applicable records whose evidence paths are already in the manifest. Leave the older fixture schema 2.

- [ ] **Step 7: Add end-to-end coverage**

  On the latest week, verify Google Trends, CTA positioning, a public proxy, reason copy, and evidence. Switch to the older schema 2 week and verify the capability table is absent. Do not start a real refresh.

- [ ] **Step 8: Run frontend verification**

  Run `npm test`, `npm run lint`, `npx tsc --noEmit`, `npm run build`, `npm run test:e2e`, and `git diff --check`. Move generated Next.js/Playwright artifacts out of the worktree before committing.

- [ ] **Step 9: Commit frontend Task 2**

  Commit message: `feat: display capability coverage audit`

---

### Task 3: Cross-wave completion audit

**Files:**
- No product-file changes expected.

**Interfaces:**
- Consumes: Wave 1–5 backend and frontend branch heads.
- Produces: verification evidence and a final matrix summary; it does not merge or publish.

- [ ] **Step 1: Verify isolated branch cleanliness and commit scope**

  Record backend/frontend branch names, commit SHAs, changed-file lists, and `git status --short`. Confirm the main data-repository `deploy/` baseline remains untouched.

- [ ] **Step 2: Run fresh cumulative backend verification**

  Run the full Python unittest suite and workbook tests on the Wave 5 backend branch.

- [ ] **Step 3: Run fresh cumulative frontend verification**

  Run full Vitest, ESLint, TypeScript, production build, and all Playwright tests on the Wave 5 frontend branch.

- [ ] **Step 4: Audit the coverage matrix line by line**

  Reconcile each user-matrix row to one of: direct integrated data, registered calculation, explicitly named public proxy, `not_configured`, `unavailable_licensed`, or `not_applicable`. Report any remaining source-smoke, live-refresh, and publication risks without claiming those actions occurred.
