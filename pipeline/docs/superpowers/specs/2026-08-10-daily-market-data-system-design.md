# Daily Market Data System Design

## Purpose

Extend the existing public weekly market-data toolkit into a daily research
system without breaking the current weekly workflow. The daily system will use
the United States as its primary research market while retaining the existing
China, Hong Kong, and global market series.

The system will target at least 54 of the 68 agreed research indicators using
official or maintainable public sources. Existing public market proxies remain
available, but every source is labelled so users can distinguish official data
from a free proxy and from data that cannot be replicated without a commercial
estimates product.

## Goals

- Provide one daily command that runs every configured data family.
- Maintain an append-only, revision-aware historical CSV layer.
- Produce a self-contained snapshot directory for each run date.
- Preserve the existing weekly output and workbook workflow.
- Isolate provider failures and make every failure visible in a source log.
- Make repeated runs for the same date deterministic and duplicate-free.
- Keep the repository usable without paid data subscriptions.

## Non-Goals

- Reproduce Bloomberg, FactSet, LSEG, or Capital IQ consensus estimates.
- Publish generated data or workbooks in the Git repository.
- Provide tick, order-book, or licensed real-time market data.
- Build company-level forecasts, point-in-time index membership, dealer gamma,
  CTA positioning, or prime-broker flow estimates.
- Replace CSV storage with a database in this phase.

## User Interface

The primary command is:

```bash
python3 scripts/run_daily.py --as-of-date 2026-08-10
```

If `--as-of-date` is omitted, the command uses the current date in the local
timezone. The command returns a non-zero exit code only when the run cannot
publish a structurally valid snapshot. Individual provider failures are
recorded and do not stop unrelated providers.

The existing five acquisition commands remain supported for focused runs and
for backward compatibility.

## Architecture

The implementation adds a daily orchestration layer above focused provider
modules. Each provider fetches one source family and returns normalized long
rows plus a provider status record. The orchestrator merges results by dataset,
updates the historical layer, derives the run-date snapshot, validates the
bundle, and publishes it atomically.

The daily system is divided into these components:

1. `registry`: declarative indicator definitions, source tier, frequency,
   expected unit, dataset, and freshness rule.
2. `providers`: parsers and fetchers for macro actuals, Treasury pricing,
   market proxies, positioning, fundamentals, and catalysts.
3. `history`: revision-aware merge, duplicate prevention, sorting, and atomic
   CSV publication.
4. `snapshot`: selects information available as of the run date and computes
   derived changes where supported.
5. `orchestrator`: executes providers independently, aggregates logs, validates
   outputs, and publishes the daily directory.

Provider modules remain small and source-specific. Network access is injected
through a session object so parser and orchestrator tests use fixed fixtures
instead of live services.

## Source Tiers

Every configured indicator has one of these source tiers:

- `official`: a government, central bank, regulator, exchange, or issuer-owned
  machine-readable source.
- `public_proxy`: a free public market-data or ETF proxy whose methodology,
  licensing, or availability is weaker than an official source.
- `unavailable_without_estimates`: a field that cannot be reproduced at
  institutional quality without a commercial estimates dataset.

Source tier is stored in configuration, normalized output, the daily manifest,
and the source log. A proxy is never silently presented as official data.

## Initial Data Scope

### Regime

Add official observations for:

- real GDP;
- CPI and core CPI;
- PCE and core PCE;
- nonfarm payrolls;
- unemployment rate;
- retail sales.

Existing policy-rate and financial-condition series remain. ISM Manufacturing
and Services stay outside the stable tier until a durable machine-readable
route with acceptable public-use terms is available.

### Pricing

Add:

- US Treasury 5-year nominal yield;
- US Treasury 10-year real yield;
- calculated 10-year breakeven inflation.

Existing 2-year, 10-year, 30-year, 2s10s, investment-grade OAS, and high-yield
OAS series remain. The free stable tier does not claim an official full Fed
implied path.

### Cross-Asset

Add:

- Hang Seng China Enterprises Index;
- USD/JPY;
- copper.

Existing equity indices, DXY, USD/CNH, gold, WTI, VIX, and other global series
remain. Proprietary index observations delivered through a public page or
vendor endpoint are labelled `public_proxy`. MOVE is not part of the stable
tier.

### Internals

Add ETF proxy series for:

- S&P 500 Equal Weight;
- US large-cap growth;
- US large-cap value;
- US momentum.

Existing 11 US sector ETF proxies and Nasdaq advance/decline statistics remain.
The code may retain reusable moving-average breadth calculations, but percentage
above 50-day and 200-day moving averages are not counted as operational until a
maintainable constituent-history source is connected.

### Fundamentals

Add S&P 500 aggregate actual metrics for:

- EPS growth;
- net profit margin.

The system must label the reporting period and publication or vintage date.
NTM EPS consensus, EPS revisions, and consensus forward P/E remain
`unavailable_without_estimates` and are not approximated from unrelated data.

### Positioning

Add:

- FINRA equity short interest;
- Cboe aggregate put/call statistics;
- the Cboe VIX futures settlement curve and simple term-structure measures.

Existing CFTC positioning remains. FINRA margin balances are retained as a
separate metric and must not be labelled short interest. Detailed option-chain
open interest and ETF-by-ETF flows remain outside the stable tier.

### Catalysts

Add the announced US Treasury auction calendar. Existing BLS, Census, and
Federal Reserve calendars remain. Future company earnings dates and unified
IPO/M&A calendars remain best-effort future work because public sources are
fragmented and change frequently.

## Normalized Data Model

Historical CSV rows use this common schema where applicable:

| Field | Meaning |
| --- | --- |
| `dataset` | Output family such as `macro_actuals` or `rates_pricing` |
| `series_code` | Stable machine identifier |
| `series_name` | Human-readable English name |
| `observation_date` | Date or period represented by the value |
| `vintage_date` | Date on which this version became available |
| `as_of_date` | Daily run date |
| `value` | Numeric value or null when explicitly unavailable |
| `unit` | Normalized unit |
| `frequency` | Daily, weekly, monthly, quarterly, or event |
| `source` | Source organization or provider |
| `source_url` | Evidence URL used by the provider |
| `source_tier` | `official`, `public_proxy`, or estimates-unavailable |
| `qc_flag` | `OK` or an explicit quality state |

The historical identity key is:

```text
dataset + series_code + observation_date + vintage_date
```

For unrevised daily market data, `vintage_date` equals `observation_date`.
For macroeconomic data, a new release or revision creates a new vintage row
instead of overwriting the earlier value. A snapshot selects the latest vintage
whose `vintage_date` is not later than its `as_of_date`, preventing future-data
leakage.

Event rows use a stable event identifier plus announced date and source. They
retain event-specific fields such as release time, auction date, security term,
offering amount, and status in their dataset CSV.

## Storage Layout

Generated files remain under ignored `outputs/` paths:

```text
outputs/
  history/
    macro_actuals.csv
    rates_pricing.csv
    cross_asset.csv
    internals.csv
    fundamentals.csv
    positioning.csv
    catalysts.csv
  daily/
    20260810/
      snapshot.csv
      macro_actuals.csv
      rates_pricing.csv
      cross_asset.csv
      internals.csv
      fundamentals.csv
      positioning.csv
      catalysts.csv
      source_log.csv
      manifest.json
  week_YYYYMMDD-YYYYMMDD/
    ... existing weekly outputs ...
```

`outputs/history/` is the cumulative local store. Each dated daily directory is
immutable after a successful run unless the user deliberately reruns that date;
in that case the directory is atomically replaced with the deterministic result
of the new run.

## Daily Run Flow

1. Load and validate the indicator registry.
2. Resolve the run date and create an isolated staging directory.
3. Execute provider groups independently and collect normalized rows and status
   records.
4. Validate types, dates, units, duplicate keys, freshness, and future leakage.
5. Merge successful rows into staged historical CSV files.
6. Select the run-date snapshot from the staged history.
7. Write dataset files, combined `snapshot.csv`, `source_log.csv`, and
   `manifest.json`.
8. Validate the complete staged bundle.
9. Atomically replace the run-date snapshot and affected history files.

No formal output is published before all structural validation passes.

## Freshness And Quality Rules

- Daily market series must not contain observations later than the run date.
- Daily series are stale after their configured business-day allowance.
- Weekly, monthly, and quarterly sources use frequency-specific freshness
  windows rather than daily thresholds.
- Non-finite numeric values become null with an explicit `INVALID_VALUE` flag.
- Missing required columns, duplicate identity keys, unit mismatches, and
  impossible dates fail the affected provider.
- Empty but valid calendars or source windows are distinguished from fetch
  failures.
- Calculated series record their input series and calculation method in the
  manifest.
- Every provider records elapsed time, observation count, latest available
  date, status, evidence URL, and diagnostic notes.

## Failure Handling

Provider failures are isolated. A failed provider contributes a
`FETCH_FAILED`, `PARSE_FAILED`, `STALE`, `NOT_CONFIGURED`, or other explicit
status to `source_log.csv`; unrelated providers continue.

The run may publish a partial snapshot when the bundle is structurally valid.
The manifest records completeness by dataset and source tier. The command exits
non-zero only when it cannot produce a valid manifest, history merge, or daily
snapshot, not merely because one external site is temporarily unavailable.

All history and snapshot writes use same-filesystem staging plus atomic rename.
An interrupted run leaves the previous published state intact.

## Testing Strategy

All production behavior follows test-first development.

### Parser Contract Tests

Each new source receives fixture-based tests for its normal response, missing
fields, malformed values, duplicate observations, unit mismatches, and empty
responses. Tests do not call live services.

### History Tests

History tests prove that:

- identical reruns are idempotent;
- daily observations are not duplicated;
- revised macro values create new vintage rows;
- snapshot selection cannot use a future vintage;
- sorting and CSV column order are deterministic.

### Orchestration Tests

Orchestrator tests use injected providers and temporary directories to prove:

- all provider groups are invoked;
- one provider failure does not suppress successful providers;
- source logs and manifests agree with generated files;
- invalid staged data is not published;
- an existing daily directory is replaced atomically on rerun.

### Regression Tests

The complete existing Python and Node test suites must remain green. Weekly
builder and verifier contract tests remain part of the release gate.

### Live Smoke Tests

Optional live smoke tests may verify the smallest current observation from each
source family. They are not part of the default test suite or GitHub CI because
external availability should not create false repository failures.

## Backward Compatibility

- Existing configuration files and focused acquisition scripts remain valid.
- Existing weekly directory naming and workbook file naming remain unchanged.
- New normalized daily history does not alter existing weekly CSV schemas.
- Weekly orchestration may later consume daily history, but the initial release
  keeps the present weekly collectors as an independent fallback.

## Documentation

README instructions will include:

- environment setup;
- the one-command daily run;
- output directory descriptions;
- source-tier definitions;
- optional credentials;
- how to inspect source failures;
- how to run tests;
- known public-data and licensing limitations.

## Acceptance Criteria

The feature is complete when:

1. `scripts/run_daily.py` creates both cumulative history and a dated snapshot
   from one command.
2. Repeating the same run is idempotent and duplicate-free.
3. Revised macro data is preserved as a new vintage and snapshot selection is
   as-of correct.
4. The agreed stable public indicators are represented in the registry and
   unavailable estimates are explicitly labelled rather than fabricated.
5. Provider failures are isolated and visible in `source_log.csv` and
   `manifest.json`.
6. The full fixture-based test suite passes without network access.
7. Existing weekly acquisition, workbook naming, and verification behavior
   remain compatible.
8. Public README instructions are sufficient for a new user to install and run
   the daily CSV system.
