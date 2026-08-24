# Market Data Coverage Wave 2 Implementation Plan

> **Scope:** Execute Wave 2 from the approved market-data coverage design. This plan starts from the completed Wave 1 backend and frontend heads and does not publish or refresh a live formal week.

## Goal

Add an auditable Market State vertical covering registered-universe breadth, equal-weight participation, correct CFTC financial/commodity positioning, official ETF assets/shares, and official HKEX Southbound flow metrics. Publish the new context topology atomically and expose it in the dashboard without fabricating unavailable paid data.

## Contract decisions

- U.S. breadth is explicitly labelled as a registered public proxy universe, never as official S&P 500 breadth.
- Every snapshot is cut off before calculations; CFTC rows are eligible only when their expected publication date is on or before the target Sunday.
- CFTC TFF and Disaggregated archives and participant classifications are parsed independently.
- ETF implied flow is emitted only when two dated issuer observations exist; otherwise assets and shares remain visible and flow remains unavailable.
- HKEX metrics cover only official Southbound fields that can be evidenced. No unavailable Northbound measure is inferred.
- Wave 2 providers are public and optional at the provider level so a fragile upstream page is audited, not silently substituted. The v4 file topology itself is required and may retain standard headers when empty.
- Dataset contracts v1-v3 remain readable; v4 becomes the coordinated-release default.

## Task 1: Backend calculations and provider adapters

**Files**

- Modify: `capital_weekly/context/market_internals.py`
- Modify: `capital_weekly/context/positioning.py`
- Modify: `capital_weekly/context/providers.py`
- Create: `capital_weekly/context/public_flows.py`
- Modify: `data/capital_weekly_cftc_contracts.csv`
- Create: `data/capital_weekly_breadth_universe.csv`
- Create/modify focused tests in `tests/`

**TDD sequence**

1. Add deterministic tests for a registered proxy universe, cutoff-before-calculation, 20/50/200-day participation, A/D, new highs/lows, and RSP-vs-SPY relative return.
2. Add tests proving TFF and Disaggregated parsing differ, both long/short nets receive historical percentiles, and a Tuesday report released after Sunday is excluded.
3. Add fixture-driven parsers for dated issuer ETF AUM/shares and official HKEX Southbound statistics; prove implied flow requires a prior dated observation.
4. Run the focused modules and capture the expected RED.
5. Implement the smallest calculation/provider changes to reach GREEN.

## Task 2: Weekly context and coordinated release v4

**Files**

- Modify: `capital_weekly/weekly_context.py`
- Modify: `capital_weekly/weekly_release.py`
- Modify: `capital_weekly/release_migration.py`
- Modify: `scripts/fetch_weekly_context.py` if needed
- Modify: release/context tests

**TDD sequence**

1. Require `fund_flows.csv` with the standard metric schema in contract v4 while retaining v1-v3 topology.
2. Register the new optional provider failure policies explicitly; unknown or required failures continue to block release.
3. Detect v4 migrations only when the complete marker topology is present; reject mixed markers.
4. Verify dates, URLs, numeric values, QC flags, source-log exact columns, and Sunday cutoffs.
5. Run focused release/context tests, then the full backend suite.

## Task 3: Dashboard Market State vertical

**Files**

- Modify the frontend dataset contract/loader/types for v4 and `fund_flows.csv`.
- Add a `Market State` navigation route/page and reusable sections for breadth, positioning, and flows.
- Add lineage/detail handling for registered-universe proxies and unavailable implied-flow history.
- Extend two-week fixtures, unit/integration tests, and Playwright coverage.

**TDD sequence**

1. Add failing contract and loader tests for v4 and the new file.
2. Add failing UI tests for breadth, positioning, flows, proxy labels, as-of propagation, and detail lineage.
3. Implement the route/page with the existing terminal design system.
4. Add an end-to-end navigation/search/detail scenario.
5. Run frontend tests, lint, typecheck, production build, and Playwright.

## Task 4: Verification and handoff

1. Run focused backend tests followed by `python3 -m unittest -v`.
2. Run the existing workbook smoke test.
3. Run frontend unit/integration tests, lint, typecheck, build, and Playwright.
4. Review diffs for cutoff, provenance, proxy labelling, contract compatibility, and unrelated-file preservation.
5. Commit backend and frontend Wave 2 files separately and report SHAs, RED/GREEN evidence, full test results, and remaining upstream risks.
