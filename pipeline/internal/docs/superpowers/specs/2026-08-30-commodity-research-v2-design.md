# Capital Weekly Commodity Research V2

**Date:** 2026-08-30

**Status:** Approved direction; written specification pending final user review

**Repositories:**

- Data pipeline: `/Users/a1-6/Documents/market data`
- Research terminal: `/Users/a1-6/Documents/行业与个股分析`

## 1. Objective

Upgrade Commodity Research from a validated snapshot table into a reliable,
multi-screen research workspace for:

1. Natural gas.
2. Refined products, with WTI and Brent retained as upstream anchors.
3. Copper.
4. Gold.
5. Agriculture, split into grains and oilseeds, soft commodities, and
   livestock.

The upgrade has three equal goals:

- make the official-source refresh diagnosable and resilient enough to publish
  the expanded contract without weakening any required-source gate;
- publish bounded histories and registered factual calculations that explain
  changes in price, physical balance, and positioning;
- replace the single dense Commodity Research table surface with an overview
  and five focused research screens.

The product remains a sourced research terminal, not a forecasting, trading,
recommendation, or backtesting system.

## 2. Binding Constraints

The V2 design preserves all existing repository and publication rules.

- The market-data workspace keeps only the visible product directories
  `pipeline/` and `output/`.
- `output/` contains exactly the latest complete six-file JSON release. It has
  no dated, weekly, historical, or provider-specific directories.
- `pipeline/config.json` remains the only production configuration source.
- The five acquisition domains remain indices, cross-market sectors, GICS,
  macro assets, and weekly context.
- A release becomes visible only after all five domains and cross-file
  validation succeed.
- A required-source failure leaves the prior six output files byte-identical.
- The raw cache changes only with a successful release and retains one latest
  successful generation.
- Missing values remain JSON `null`; zero, empty strings, `NaN`, and infinity
  are never substitutes.
- Every displayed fact retains observation date, known-as-of when applicable,
  source URL, quality status, and stable release provenance.
- Only free official sources are eligible for Commodity Research. Credentials
  for free official APIs remain server-side.
- Point-in-time eligibility is applied before selection, change calculations,
  percentiles, seasonal comparisons, or aggregation.

## 3. Chosen Approach

V2 uses a reliability-first, backend-owned research contract.

The rejected alternatives are:

- **UI-only redesign.** It would make the empty real release look better but
  would not solve failed official publication, bounded history, or factual
  comparisons.
- **Frontend-owned analytics.** It would duplicate formulas across components,
  make auditability weaker, and allow presentation changes to alter research
  semantics.
- **Forecasting or signal scoring.** It would exceed the approved official-fact
  product boundary and create claims that the current sources cannot support.

Backend V2 therefore owns source retrieval, point-in-time selection, history,
and registered calculations. The frontend owns only composition, filtering,
formatting, interaction, and visual comparison of already published facts.

## 4. Product Information Architecture

`05 商品研究` remains one top-level terminal page. It gains a local research
navigation with six screens:

1. **Overview** — coverage, freshness, latest price changes, physical changes,
   positioning context, and official-source status across the full universe.
2. **Natural Gas** — Henry Hub, storage, production, consumption, LNG trade,
   seasonal context, and CFTC positioning.
3. **Refined Products** — WTI/Brent anchors, crude and product stocks, refinery
   activity, product supplied, trade, and WTI/RBOB/ULSD positioning.
4. **Copper** — World Bank benchmark, COMEX registered/eligible stocks, CFTC,
   current eligible USGS structural context, and the permanent LME limitation.
5. **Gold** — World Bank benchmark, COMEX depository stocks, CFTC, and current
   eligible USGS structural context.
6. **Agriculture** — grains/oilseeds, softs, and livestock subsections combining
   World Bank, USDA PSD/ESR, and CFTC coverage.

The current five primary family tabs are replaced by this local navigation.
The terminal's global pages remain seven; Context and Audit are not split or
renumbered again.

Each focused screen follows the same reading order:

1. screen identity, data-as-of summary, and coverage limitations;
2. price history and return facts;
3. physical balance or inventory facts;
4. positioning facts;
5. source/freshness strip and record-level inspection.

## 5. Research Universe

V2 retains the exact immutable codes from V1:

| Family | Codes |
| --- | --- |
| Natural gas | `NATGAS_HH` |
| Refined products | `WTI`, `BRENT`, `RBOB_US`, `ULSD_US`, `JET_US`, `PROPANE_US` |
| Copper | `COPPER_COMEX` |
| Gold | `GOLD_COMEX` |
| Grains/oilseeds | `CORN`, `SOYBEANS`, `WHEAT`, `RICE` |
| Softs | `COTTON`, `SUGAR`, `COFFEE`, `COCOA` |
| Livestock | `CATTLE`, `HOGS` |

No label parsing, metric-prefix inference, fuzzy market matching, or
frontend-only alias can add a commodity. `COMEX_GOLD` remains only the legacy
macro `series_code` for `commodity_code=GOLD_COMEX`.

## 6. Official Source Policy

V2 keeps the V1 source map and adds no paid or vendor fallback.

| Provider | V2 use | Requiredness rule |
| --- | --- | --- |
| EIA API v2 | Energy prices and physical fundamentals | Required when configured with a valid key |
| World Bank Pink Sheet | Monthly metal and agriculture benchmarks | Required for configured benchmarks |
| CFTC PRE | Commodity open interest and positioning | Required for configured contracts |
| CME/COMEX | Copper and gold warehouse/depository reports | Supplemental but strictly attributed |
| USDA FAS PSD | Agriculture balances and stocks-to-use inputs | Required when `USDA_API_KEY` is configured |
| USDA FAS ESR | Weekly export sales and shipments | Required when `USDA_API_KEY` is configured |
| USGS NMIC | Eligible current structural metal facts | Supplemental |
| USDA NASS | Only future verified machine-readable official facts | Disabled until independently proven |

Yahoo, exchange quote-page scraping, paid LME history, unversioned analyst
estimates, and cached rows from a prior release are not eligible substitutes.

## 7. Refresh Reliability Architecture

### 7.1 Request executor

All official HTTP GET providers use one bounded request executor with:

- provider-specific connect, read, and total deadlines from config;
- a maximum attempt count declared in config;
- retry only for transport errors, HTTP `408`, `425`, `429`, and `5xx`;
- exact `Retry-After` support capped by the provider total deadline;
- deterministic backoff in tests and bounded jitter only in production;
- no retry for schema, identity, unit, freshness, point-in-time, or coverage
  validation failures;
- secret removal from exception text, prepared URLs, headers, notes, raw
  diagnostics, and source-log errors.

Retries operate only inside one refresh execution. A failed refresh still
removes staging and does not create a resumable or historical generation.

### 7.2 Provider phases

Every provider reports explicit phases:

1. credential/config validation;
2. official metadata or lookup validation;
3. data retrieval and pagination;
4. raw-byte preservation;
5. parsing and source identity checks;
6. point-in-time selection;
7. freshness and coverage validation;
8. normalized row emission.

The source log records the failed phase, attempt count, elapsed time, official
route without credentials, latest eligible observation, and a stable error
code. It does not serialize secrets or uncontrolled response bodies.

### 7.3 EIA-specific hardening

EIA price, natural-gas, and refined-products providers remain independent.
They use route-native facet identifiers, unit codes, and descriptions validated
against official metadata before data retrieval. Series are requested in
bounded configured batches so one oversized query cannot suppress a family.

A production-compatible probe command exercises metadata plus the most recent
eligible page without writing output, cache, status, or staging. The probe is
diagnostic only; it cannot substitute for a complete refresh.

### 7.4 Atomic cache and output

Raw responses accumulate only in the active staging generation. After all five
pipelines and release validation pass, publication atomically replaces:

- the six stable JSON files; and
- the one latest cache generation.

If any required phase fails, both output and prior successful cache remain
byte-identical and staging is removed.

## 8. Published Data Contract

V2 does not add a seventh stable file. It adds bounded history and registered
research tables to the existing owners.

### 8.1 Macro price history

`macro.json.tables.commodity_price_history` contains one row per eligible
observation:

```text
release_id
as_of_date
commodity_code
commodity_family
series_code
price_kind
observation_date
known_as_of
value
unit
source
source_url
qc_flag
```

The existing `macro.json.tables.commodities` remains the latest price/return
snapshot. History does not create another latest-price owner.

### 8.2 Context metric history

`context.json.tables.commodity_metric_history` contains bounded eligible
observations for physical and positioning metrics:

```text
release_id
as_of_date
commodity_code
commodity_family
metric_code
metric_role
measurement_kind
participant_class
observation_date
known_as_of
reference_period
value
unit
source
source_url
qc_flag
```

### 8.3 Registered calculations

`context.json.tables.commodity_research_facts` contains deterministic derived
facts. Every row includes:

```text
commodity_code
commodity_family
fact_code
fact_kind
value
unit
observation_date
known_as_of
reference_period
formula_id
formula_version
input_record_ids
source_urls
qc_flag
```

Allowed initial fact kinds are:

- absolute change;
- percentage change with nonzero eligible denominator;
- year-over-year change;
- configured trailing percentile;
- seasonal deviation using aligned week-of-year observations;
- stock-to-use using same-vintage, same-unit USDA inputs;
- coverage count and freshness age.

These are descriptive facts, not bullish/bearish labels, composite scores,
forecasts, targets, or recommendations.

### 8.4 Record identity and limits

Each history or fact row has a deterministic `record_id` derived from its
stable semantic identity, not array position. Config declares history windows
per frequency; initial limits are at most:

- 400 daily observations;
- 160 weekly observations;
- 84 monthly observations;
- 12 annual or marketing-year observations.

Rows later than `as_of_date`, known after the Sunday cutoff, stale beyond their
configured provider limit, or outside the window are not published.

## 9. Backend Composition and Validation

Provider parsers remain pure and report-specific. A new research assembler:

1. receives only normalized, eligible macro/context rows;
2. resolves exact commodity and metric identities from config;
3. builds bounded histories;
4. runs registered formula functions;
5. emits facts with exact input record IDs;
6. performs no network access and reads no previous output or cache.

Release validation is config-derived and enforces:

- exact commodity code/family coverage;
- exact provider and source attribution;
- unique record identities;
- allowed enums, aware timestamps, units, and finite-or-null values;
- history ordering, window limits, and point-in-time cutoffs;
- formula ID/version/input existence and same-vintage requirements;
- zero business rows for non-OK provider statuses;
- complete required capability status without optionality weakening core data.

## 10. Frontend Research Model

The stable loader validates and preserves the new history and fact arrays. A
pure Commodity Research V2 adapter produces:

- one immutable universe registry from the 19 backend codes;
- exact feed coverage and freshness by commodity;
- chart series grouped only by explicit record fields;
- registered facts linked back to their input records;
- diagnostics for invalid identity, enums, duplicates, formulas, sources, or
  point-in-time fields.

The adapter never calculates percentiles, seasonal values, stock-to-use, or
market conclusions. It may perform deterministic presentation transforms such
as sorting, filtering, date labeling, and selecting an already published
series.

## 11. Frontend Screens

### 11.1 Overview

The overview contains:

- a release/freshness header;
- a 19-commodity coverage matrix for price, fundamentals, and positioning;
- latest published price-return facts using each benchmark's true frequency;
- latest physical and positioning facts with their own dates;
- family filters and exact code/name/source search;
- a factual source-status panel linked to Data Audit.

It never ranks commodities by an invented score. Sorting options are explicit
facts such as latest observation date, weekly price change, or coverage count.

### 11.2 Focused screens

Each focused screen uses reusable panels:

- accessible price history chart and return table;
- physical metric selector and history chart/table;
- positioning participant selector and history chart/table;
- registered facts table with formula and input inspection;
- official sources, dates, freshness, and limitations.

Natural Gas adds storage-seasonality context. Refined Products supports
side-by-side WTI/Brent/product selection. Copper and Gold show COMEX inventory
limitations next to the relevant panel. Agriculture supports its three
subsections and preserves marketing-year reference periods.

### 11.3 Visual and interaction rules

- Reuse the terminal's square panels, one-pixel rules, warm white, charcoal,
  and orange accent.
- Charts use SVG or existing code-native primitives; no image snapshots or
  remote chart service.
- Every chart has a table-equivalent accessible representation.
- Keyboard navigation, visible focus, ARIA relationships, reduced motion, and
  1440-pixel no-overflow behavior are mandatory.
- Search checks only visible identities, names, metric labels, and sources. It
  does not expose hidden enum or taxonomy strings.
- `empty`, `invalid`, `not configured`, `fetch failed`, `stale`, and
  `filtered with no matches` remain distinct factual states.

## 12. Error and Refresh Experience

The terminal refresh status shows domain, provider, phase, attempt count, and a
sanitized stable error code. It never exposes credentials or raw response
bodies.

During refresh, the current complete release remains readable. On failure, the
terminal states that the old release remains active and links to the relevant
Data Audit source row. On success, the terminal reloads only after the new
release and all file hashes validate.

A missing `USDA_API_KEY` remains a factual paired `NOT_CONFIGURED` state. The
UI may explain where the server-side key is required but must not collect or
store it in the browser.

## 13. Testing Strategy

All behavioral changes follow RED-GREEN TDD.

Backend coverage includes:

- deterministic request retry/deadline/`Retry-After` tests;
- secret-bearing URL/header/error mutation tests;
- exact EIA metadata, facets, units, batching, and pagination fixtures;
- all 19 commodity codes and seven families;
- point-in-time, freshness, history-window, unique identity, and formula-input
  mutation tests;
- required-provider rollback proving all six output and prior cache hashes are
  unchanged;
- two successful generations proving latest-only cache replacement;
- a full five-pipeline staged release with histories and research facts.

Frontend coverage includes:

- pure adapter tests for histories, facts, invalid coverage, and exclusions;
- component tests for all six screens, dates, filters, charts, tables, source
  inspection, and factual empty/error states;
- shell tests for view-scoped search, as-of, quality, and refresh error copy;
- browser tests activating every Commodity Research screen and inspecting
  EIA, World Bank, CFTC, CME, and USDA provenance;
- 1440-pixel overflow and keyboard/ARIA checks;
- Playwright normal, failure, signal, concurrency, and special-path isolation
  regressions retained from V1.

No automated test performs a live network refresh.

## 14. Delivery Sequence

Implementation is ordered so later work cannot mask an unreliable source
layer.

1. **Reliability foundation** — request executor, provider phases, diagnostics,
   and EIA batching/probes.
2. **History and fact contract** — schemas, config, assemblers, formulas,
   validators, and deterministic complete release.
3. **Frontend data model** — loader, pure adapter, histories, facts, coverage,
   and diagnostics.
4. **Six-screen workspace** — overview, five focused screens, charts, tables,
   source/freshness panels, accessibility, and responsive layout.
5. **Integration and publication** — shell, refresh status, E2E, stable-output
   validation, and one explicitly authorized live official-source refresh.
6. **Independent review** — backend contract/security review, frontend
   product/accessibility review, blocking-fix rounds, and final verification.

Backend and frontend tasks use separate commits and ownership boundaries. The
frontend may use only the canonical deterministic release fixture until the
backend contract task is independently approved.

## 15. Acceptance Criteria

V2 is complete only when all of the following are true:

- the complete deterministic release contains all 19 commodity codes, seven
  families, bounded histories, registered facts, and exact official source
  provenance;
- every registered fact can be reconstructed from published input record IDs
  and its versioned formula;
- a required provider failure preserves all six prior output hashes and the
  prior successful cache generation;
- request retries are bounded, credential-safe, phase-attributed, and never
  retry validation failures;
- the frontend exposes Overview, Natural Gas, Refined Products, Copper, Gold,
  and Agriculture screens with separate price, physical, and positioning
  dates;
- every visible chart value is available in an accessible table and retains a
  source inspection path;
- full backend tests, workbook compatibility, full frontend tests, lint,
  production build, E2E, output validation, and worktree diff checks pass;
- independent reviewers report no unresolved blocking or important finding;
- the market-data workspace still has only the visible product directories
  `pipeline/` and `output/`, and `output/` still has exactly six stable files;
- the final live refresh either publishes a fully valid expanded release or
  fails closed with a precise official-source boundary while the previous
  release remains byte-identical. External source availability is not faked to
  satisfy completion.

## 16. Explicit Non-Goals

V2 does not add:

- forecasts, targets, bullish/bearish calls, or automated narratives;
- trading, order entry, alerts, portfolios, backtests, or position sizing;
- paid LME, exchange-licensed history, vendor estimates, or unofficial
  substitute sources;
- a database server, cloud deployment, user accounts, or background scheduler;
- historical release directories or multiple retained cache generations;
- a seventh stable output file;
- source-native values rewritten into invented common units.

## 17. Compatibility and Rollout

All new stable JSON tables are additive. V1 snapshot tables and fields remain
valid while the V2 frontend is developed. The V2 frontend treats absent V2
history/fact arrays in the current stable release as factual unavailability,
not loader failure, so the previous complete release remains readable.

The first V2 publication activates only after the upgraded validator confirms
the full configured contract. Rollback requires no conversion: the publisher
continues to expose the prior complete six-file release until a new candidate
passes atomically.
