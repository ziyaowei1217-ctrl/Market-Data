# Capital Weekly Market Sense P0/P1 Public-Data Expansion Design

**Date:** 2026-08-11

**Status:** Approved in conversation; ready for implementation planning after review

**Repository:** Capital Weekly market-data repository root

**Depends on:** completion and integration of Capital Weekly terminal-redesign backend Tasks 1–3

## 1. Objective

Extend the Capital Weekly backend toward the full seven-layer Market Sense model
without changing its five-pipeline atomic release architecture. The first release
uses only free public sources and covers:

- point-in-time US macro releases;
- real yields and market-based inflation expectations;
- public positioning, short-interest, ETF-flow, and aggregate options data;
- reported fundamentals, margins, and trailing valuation for a configured
  30–50-company US watchlist;
- confirmed official calendars for macro, monetary-policy, Treasury, securities
  issuance, election, fiscal, and regulatory events.

Future paid sources for Fed-implied paths, consensus estimates, revisions,
forward valuation, detailed options positioning, and issuance calendars must be
addable through the same provider contracts without migrating the public output
schemas.

## 2. Confirmed Product Decisions

- Keep the existing five top-level pipelines. Do not add a sixth release
  pipeline.
- Use free public sources only for P0/P1.
- Do not use browser automation, paid consensus, proprietary fund-flow estimates,
  level-2 order books, tick data, or unofficial political-event aggregation.
- Company fundamentals cover a user-configured 30–50-company watchlist. Do not
  invent a production company list.
- Political events include only dates that can be retrieved from an official
  election, fiscal, legislative, or regulatory source.
- Future events cover the report week plus the next 28 calendar days.
- Every value must be point-in-time correct for the target Sunday.
- Existing current-week outputs, tests, and unrelated dirty files must be
  preserved.

## 3. Considered Approaches

### 3.1 Selected: modular expansion inside the five pipelines

Add focused provider modules below `macro_assets` and `weekly_context`, publish
domain-specific CSVs, and keep the current coordinator, manifest, status, and
atomic publication model.

This approach minimizes cross-repository disruption, preserves the approved
release contract, and gives paid sources a stable adapter boundary.

### 3.2 Rejected: add independent top-level pipelines

Separate macro-release, fundamentals, and positioning pipelines would improve
process isolation but would turn the five-pipeline release into an eight-pipeline
release and require coordinated changes to the backend coordinator, manifest,
frontend refresh state, contracts, and tests.

### 3.3 Rejected: one generic metrics/events table

A single generic table would reduce file count but would weaken type safety across
economic vintages, corporate reporting periods, options open interest, and future
calendar dates. Domain-specific validation is more important than minimizing
files.

## 4. Architecture And Module Boundaries

The `macro_assets` pipeline adds real-yield and breakeven rows while retaining
the current return, basis-point-change, source-log, and cutoff behavior.

The `weekly_context` pipeline gains focused modules:

- `economic_releases`: GDP, CPI, Core CPI, PCE, Core PCE, NFP,
  unemployment, ISM, and Retail Sales;
- `public_positioning`: ICI ETF category flows, FINRA short interest and
  short-sale volume, and CFTC dealer/swap-dealer positioning;
- `options_activity`: public Cboe/OCC aggregate volume, open interest, and
  put/call measures;
- `fundamentals`: SEC-reported actuals, margins, TTM metrics, and trailing
  valuation for the configured company watchlist;
- `official_calendar`: macro releases, FOMC events, Treasury auctions, confirmed
  company filings and offerings, and official election/fiscal/regulatory dates.

The existing `providers.py` becomes a registry and composition layer rather than
the home of domain parsing logic. Each domain module owns its parser,
normalization, freshness checks, and deterministic calculations.

Every provider consumes a target window, `as_of_date`, configuration, and an
HTTP session. It returns normalized rows, the raw response, source metadata,
status, and factual error details. Providers also declare:

- `source_tier`: `public` or `licensed`;
- `requiredness`: `required` or `optional`;
- provider and schema versions;
- frequency and freshness policy.

Only public providers are registered in P0/P1. Disabled licensed providers make
no requests, generate no warnings, and publish no placeholder numbers.

## 5. Output Tables

Reuse existing tables where their semantics already fit:

| File | Change |
| --- | --- |
| `fixed_income.csv` | Add real yields, 5Y/10Y breakevens, and 5Y5Y forward inflation |
| `events.csv` | Add known-as-of metadata and official macro, policy, auction, filing, issuance, election, fiscal, and regulatory events |
| `positioning_flows.csv` | Add ETF category flows, FINRA short measures, and CFTC dealer classifications |

Add three typed tables:

| File | Purpose |
| --- | --- |
| `economic_releases.csv` | Point-in-time actual, previous, revised, and future optional consensus values |
| `options_activity.csv` | Aggregate call/put volume, open interest, and ratios |
| `company_fundamentals.csv` | Long-form reported and derived watchlist fundamentals |

All new tables include:

```text
as_of_date
known_as_of
source
source_url
source_tier
qc_flag
```

Economic releases additionally include:

```text
indicator_code
observation_period
release_at_bjt
vintage_date
value
previous_value
revised_previous
consensus_value
surprise_value
unit
frequency
seasonal_adjustment
```

In P0/P1, `consensus_value` and `surprise_value` remain null and are not shown.
They are reserved for a future licensed provider using the same schema.

Company fundamentals use a long table. Revenue, operating income, net income,
EPS, margins, TTM measures, and trailing multiples are separate metric rows.
Each derived row records a calculation ID, formula version, and input record IDs.

## 6. Point-In-Time Rules

- Every published record must satisfy `known_as_of <= target Sunday end in
  Asia/Hong_Kong`.
- An observation period may precede the week, but its release or revision must
  have been public by the target Sunday.
- Later revisions cannot overwrite an older weekly vintage.
- If a historical vintage cannot be proven, mark it
  `POINT_IN_TIME_UNAVAILABLE`; never substitute the currently revised value.
- Preserve raw weekly responses from the feature launch onward to form a durable
  first-release and revision history.
- SEC facts must have `filed_at <= as_of_date`. TTM calculations use only facts
  filed by that date.
- Valuation price dates must not exceed the target Sunday.
- A future event date may exceed the target Sunday by at most 28 calendar days,
  but its `known_as_of` must not exceed the target Sunday.
- Historical weeks cannot be backfilled from a schedule that became known later.
- Release validation checks market observation dates for market data and
  `known_as_of` for future calendar records.

## 7. Sources And Calculation Boundaries

### 7.1 Sources

- BLS, BEA, and Census for official US macro data;
- ISM for current official releases and release dates, cached prospectively;
- US Treasury nominal and real curves for real yields and inflation calculations;
- ICI for weekly aggregate ETF category net issuance;
- FINRA for biweekly short interest and separately labeled daily short-sale
  volume;
- CFTC TFF and disaggregated reports for dealer/intermediary, swap-dealer,
  asset-manager, leveraged-fund, and managed-money classifications;
- Cboe and OCC for public aggregate options volume and open interest;
- SEC Company Facts, Submissions, and filing documents for watchlist actuals and
  confirmed company events;
- BLS, BEA, Census, Federal Reserve, TreasuryDirect, SEC, FEC, and relevant
  official agencies for event dates.

### 7.2 Registered Calculations

- CPI/PCE: MoM, YoY, and three-month annualized change;
- GDP: QoQ SAAR and YoY change;
- NFP: monthly change and published revisions;
- ISM: level and distance from 50, without generated regime commentary;
- breakeven: matched-maturity nominal yield minus real yield;
- 5Y5Y: a registered forward-inflation formula with explicit inputs;
- positioning: net, weekly change, share of open interest, and rolling
  three-year percentile;
- options: volume and OI put/call ratios, weekly volume, and week-end OI;
- fundamentals: gross, operating, and net margins, TTM EPS, trailing P/E, and
  P/S.

### 7.3 Semantic Prohibitions

- Do not label short-sale volume as short interest.
- Do not label CFTC dealer positioning as options dealer gamma.
- Do not label a trend model as observed CTA positioning.
- Do not calculate an economic or earnings surprise without a configured
  consensus source.
- Do not infer an unconfirmed earnings date or offering size from filing history.
- Do not use a current SEC restatement in a historical week unless it was filed
  by that week.

## 8. Error Handling And Release Policy

Required providers include the nine macro indicators, real yields and
breakevens, ICI ETF category flows, CFTC/FINRA positioning, Cboe/OCC aggregates,
and SEC fundamentals when a watchlist is enabled. Fetch, schema, semantic,
staleness, or point-in-time failure blocks formal publication.

Optional providers include company IR calendars, zero-row issuance and
political-event categories, and disabled future licensed sources. Optional
failure produces a manifest warning, retains standard headers, and creates no
frontend section.

Additional rules:

- `NOT_CONFIGURED` is allowed only for optional providers.
- An empty production watchlist disables the fundamentals provider without
  inventing companies. Once enabled, it becomes required.
- Freshness is configured separately for daily, weekly, biweekly, monthly, and
  quarterly data.
- Conflicting values for the same indicator, period, and vintage fail the source.
- A watchlist company failure remains visible in audit. Falling below the
  configured company-coverage threshold fails the fundamentals domain.
- Raw-cache failure records `RAW_CACHE_WARNING`; staged data may continue to
  validation when the normalized values are otherwise complete.
- Required tables cannot be header-only. Optional tables retain standard headers
  when empty.
- Non-finite values, missing source URLs, unknown formulas, duplicate primary
  keys, and records known after the target Sunday fail validation.
- Failed staging never replaces the prior complete week.

The manifest records each domain's requiredness, configuration state, status,
coverage, latest known-as-of timestamp, warnings, provider version, and formula
version.

## 9. Testing

All behavior changes use TDD. Tests use deterministic fake histories, raw
responses, clocks, and runners. Routine verification does not call real
networks.

Required cases include:

- a release after the target Sunday is excluded even when its observation period
  is earlier;
- a revision after Sunday cannot overwrite the older vintage;
- a future event known before Sunday is accepted, while one announced Monday is
  excluded;
- SEC facts filed after Sunday and prices after Sunday are excluded;
- short interest and short-sale volume remain separate metrics;
- dealer classifications cannot become dealer-gamma rows;
- absent consensus leaves consensus and surprise null;
- required failure blocks publication and optional failure produces a warning;
- optional empty tables retain exact headers;
- every derived value traces to registered inputs and a formula version;
- a fake licensed provider populates the reserved consensus fields without a
  schema migration;
- invalid values, missing provenance, time travel, and duplicate keys roll back
  atomic publication.

Verification order:

1. focused unit modules for each domain;
2. existing macro-assets, weekly-context, and weekly-release integration tests;
3. `python3 -m unittest -v`;
4. an offline five-pipeline fixture release with manifest, hashes, coverage, and
   warnings verified;
5. a read-only smoke check of one complete real week.

Do not run a real network refresh unless the user explicitly requests it.

## 10. Acceptance Criteria

- All nine macro indicators, real yields, breakevens, public positioning, and
  aggregate options measures carry point-in-time provenance.
- An enabled watchlist produces reported actuals, margins, TTM values, and
  trailing valuation without using facts or prices known after the target week.
- An empty watchlist produces no company section and no invented records.
- No formal week contains a `known_as_of` timestamp after the target Sunday.
- Existing five-pipeline atomic release and frontend-compatible provenance remain
  intact.
- Licensed providers are pluggable but P0/P1 makes no paid request and has no
  hidden paid dependency.
- Focused and full Python test suites pass.
- Any failure leaves the previous complete week visible.

## 11. Implementation Decomposition And Coordination

This program is intentionally split into three follow-on specs and plans:

1. **Point-in-time macro and rates:** shared availability/vintage contract, nine
   macro indicators, real yields, breakevens, and 5Y5Y.
2. **Public positioning and derivatives:** ETF category flows, short interest,
   options activity, and expanded CFTC dealer classifications.
3. **Watchlist fundamentals and official calendars:** SEC actuals, margins,
   trailing valuation, and official event sources.

The first subproject owns the shared provider and point-in-time contracts used by
the next two. Each subproject receives independent TDD tasks and file ownership.

Do not start implementation in files owned by active Capital Weekly backend
Tasks 1–3. Integrate those commits first, then create the new task wave from the
combined backend baseline. Do not modify the Next.js repository from these
backend tasks; frontend contracts and views are a later coordinated phase.
