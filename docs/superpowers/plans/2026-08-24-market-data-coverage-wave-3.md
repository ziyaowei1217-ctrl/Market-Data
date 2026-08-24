# Market Data Coverage Wave 3 Implementation Plan

> **Scope:** Execute Wave 3 from the approved market-data coverage design. This plan starts from the completed Wave 2 backend and frontend heads and does not publish or refresh a live formal week.

## Goal

Add an auditable Macro Releases & Events vertical covering point-in-time public economic releases, a clearly named actual-data momentum proxy, the official FOMC calendar, the existing official economic calendars, and SEC-confirmed earnings events. Preserve paid/licensed gaps explicitly and expose the results in the dashboard without claiming consensus surprise data or forecast earnings dates.

## Contract decisions

- BLS, BEA, and Census point-in-time source adapters are wired into the default provider registry; each observation is filtered by target-Sunday availability before derived calculations.
- The macro proxy is the difference between 3-month annualized and year-over-year inflation for headline/core CPI and PCE. It is labelled `momentum gap proxy`, never Citi Economic Surprise Index or consensus surprise.
- Consensus and surprise fields stay null unless a licensed consensus source is introduced later.
- ISM PMI values are not republished because the official source restricts time-series reproduction. The exact optional provider is audited as `UNAVAILABLE_LICENSED`; no alternative value is substituted.
- FOMC policy-decision dates come from the dedicated Federal Reserve FOMC calendar and retain the official U.S. event date plus Beijing release time.
- Earnings events are retrospective SEC-confirmed filings/releases only. They are not presented as a complete future earnings calendar.
- Wave 3 reuses the coordinated-release v4 file topology because all required tables and standard headers already exist. Dataset contracts v1-v4 remain readable.

## Task 1: Public economic releases and momentum proxy

**Files**

- Modify: `capital_weekly/context/economic_releases.py`
- Modify: `capital_weekly/context/economic_sources/__init__.py`
- Modify: `capital_weekly/context/providers.py`
- Add/modify focused economic-source and provider tests in `tests/`

**TDD sequence**

1. Add deterministic tests proving BLS, BEA, and Census providers are registered and preserve their point-in-time cutoff behavior.
2. Add tests for headline/core CPI and PCE momentum-gap proxy rows, input lineage, units, and null consensus/surprise fields.
3. Add tests proving calculations never use an observation published after the target Sunday.
4. Run the focused modules and capture the expected RED.
5. Implement the smallest calculation and registry changes to reach GREEN.

## Task 2: Official calendars and licensed-gap audit

**Files**

- Modify: `capital_weekly/context/events.py`
- Modify: `capital_weekly/context/providers.py`
- Modify: `capital_weekly/weekly_release.py`
- Add/modify focused event, provider, and release-policy tests in `tests/`

**TDD sequence**

1. Add a fixture-driven parser test for the dedicated Federal Reserve FOMC meeting calendar, including multi-day meetings, SEP flags, U.S. event date, and Beijing release time.
2. Add an exact allow-list policy for the optional ISM PMI provider with `UNAVAILABLE_LICENSED`; prove unknown or required licensed failures still block release.
3. Verify existing BLS/Fed/Census economic events and SEC earnings-release events remain source-linked and Sunday-bounded.
4. Register the FOMC and licensed-gap providers without changing the v4 table topology.
5. Run focused release/context tests, then the full backend suite.

## Task 3: Dashboard Macro Releases & Events presentation

**Files**

- Modify the frontend market-data types and context signal/view components.
- Add release tables/cards for economic actuals, momentum proxies, official calendars, and SEC-confirmed earnings events.
- Extend two-week fixtures, unit/integration tests, and Playwright coverage.

**TDD sequence**

1. Add failing UI tests for economic-release values, null-consensus language, momentum-proxy labelling, FOMC events, and SEC-confirmed earnings events.
2. Implement the sections within the existing `Events & Context` route and terminal design system.
3. Add lineage/detail handling for source, release/as-of dates, units, calculation inputs, and forecast limitations.
4. Add an end-to-end navigation and detail scenario.
5. Run frontend tests, lint, typecheck, production build, and Playwright.

## Task 4: Verification and handoff

1. Run focused backend tests followed by `python3 -m unittest -v`.
2. Run the existing workbook smoke test.
3. Run frontend unit/integration tests, lint, typecheck, build, and Playwright.
4. Review diffs for target-Sunday cutoff, provenance, proxy labelling, licensed-gap policy, contract compatibility, and unrelated-file preservation.
5. Commit backend and frontend Wave 3 files separately and report SHAs, RED/GREEN evidence, full test results, and remaining upstream risks.
