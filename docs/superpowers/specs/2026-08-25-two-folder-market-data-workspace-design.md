# Capital Weekly Two-Folder Workspace Reorganization Design

**Date:** 2026-08-25

**Status:** Chat-approved; pending written-spec review

**Repository:** `/Users/a1-6/Documents/market data`

## 1. Goal

Reorganize the existing market-data repository so its only visible top-level
directories are `pipeline/` and `output/`. Preserve the current five data
domains and their calculations, but replace week-named publication trees with
five stable JSON outputs that always represent the latest complete successful
refresh.

This is a file and publication-layout reorganization. It does not add a new
data source, create a new frontend, change a market-data formula, or run a live
network refresh.

## 2. Confirmed Product Decisions

- Keep only the latest complete successful release.
- Remove historical-week selection and immutable weekly snapshot retention.
- Do not create a new `week_YYYYMMDD-YYYYMMDD` directory on refresh.
- Publish five stable business JSON files, one for each existing pipeline.
- Keep one generation of raw fetch cache under `pipeline/.cache/`.
- Update the cache only after a complete successful refresh, so it matches the
  active output generation.
- Keep the current five-pipeline all-or-nothing publication rule.
- Create the future frontend as a separate sibling repository, but do not
  create or modify any frontend in this reorganization.

## 3. Target Workspace

The only visible top-level directories are:

```text
market data/
├── pipeline/
└── output/
```

Repository metadata and conventional top-level files may remain at the root:
`.git/`, `.gitignore`, `AGENTS.md`, `README.md`, `LICENSE`, and dependency
metadata. Generated development directories such as `.worktrees/`, `tmp/`,
`deploy/`, `.superpowers/`, and `outputs/` are not part of the final visible
project structure.

The operational layout is:

```text
pipeline/
├── refresh.py
├── common.py
├── config.json
├── indices.py
├── sectors.py
├── gics.py
├── macro.py
├── context.py
├── tests/
├── docs/
├── .cache/
└── .staging/

output/
├── indices.json
├── sectors.json
├── gics.json
├── macro.json
├── context.json
└── release.json
```

The five domain modules are the public operational entrypoints. Existing
provider-specific logic may remain as focused internal modules under
`pipeline/` when merging it into a domain entrypoint would create an
unmaintainable file. The “approximately ten files” target applies to the
business-facing pipeline and output surface, not to deterministic tests or
focused internal implementation modules.

## 4. File Responsibilities

### 4.1 Pipeline entrypoints

| File | Responsibility |
| --- | --- |
| `pipeline/indices.py` | Fetch, normalize, clean, and validate global equity indices. |
| `pipeline/sectors.py` | Fetch, normalize, clean, and validate A/H/US sector data and divergence. |
| `pipeline/gics.py` | Fetch, normalize, clean, and validate global GICS proxy data. |
| `pipeline/macro.py` | Fetch, normalize, clean, and validate fixed income, policy rates, money market, FX, commodities, and macro divergence. |
| `pipeline/context.py` | Fetch, normalize, clean, and validate events, economic releases, financial conditions, internals, positioning, company events, and commodity fundamentals. |

`pipeline/common.py` owns shared date truncation, null normalization, numeric
validation, stable ordering, deduplication, source metadata, hashing, and JSON
serialization. `pipeline/config.json` consolidates the existing versioned
universe and provider configuration without embedding business lists in code.

`pipeline/refresh.py` is the only coordinated publication entrypoint. Single
pipeline entrypoints remain useful for diagnosis but cannot directly replace
the active `output/` release.

### 4.2 Stable outputs

| File | Main collections |
| --- | --- |
| `output/indices.json` | `indices`, `source_log` |
| `output/sectors.json` | `sectors`, `divergence`, `source_log` |
| `output/gics.json` | `sectors`, `source_log` |
| `output/macro.json` | `fixed_income`, `policy_rates`, `money_market`, `foreign_exchange`, `commodities`, `divergence`, `source_log` |
| `output/context.json` | `events`, `economic_releases`, `financial_conditions`, `market_internals`, `positioning_flows`, `company_events`, `commodity_fundamentals`, `source_log` |

Each business output uses the following envelope:

```json
{
  "schema_version": "1.0",
  "release_id": "20260825T120000-0700-ab12cd",
  "as_of_date": "2026-08-23",
  "pipeline": "indices",
  "status": "complete",
  "tables": {},
  "source_log": []
}
```

`output/release.json` is written last and contains the common `release_id`,
`as_of_date`, generation timestamp, overall status, the five pipeline statuses,
row counts, filenames, and SHA-256 hashes. A consumer accepts a release only
when all six files exist, every business file identifies the same release, and
the hashes match `release.json`.

## 5. Cleaning Contract

Raw provider responses never become public output directly. Every pipeline
performs the following steps before JSON serialization:

1. Apply `as_of_date` before calculating any snapshot value or return.
2. Normalize dates to `YYYY-MM-DD` and timestamps to explicit ISO 8601 values.
3. Preserve numbers as JSON numbers and convert empty values, `NaN`, and
   infinite values to `null` or reject the record when the field is required.
4. Preserve units explicitly; do not mix ratios, percentages, basis points,
   currencies, or levels without a unit field.
5. Deduplicate by each dataset's registered stable business key.
6. Preserve `source`, `source_url`, observation date, and quality status on
   every published business record.
7. Record rejected rows and provider failures in `source_log`; never silently
   discard evidence.
8. Sort tables deterministically so identical inputs create identical JSON.
9. Serialize strict JSON with no non-standard `NaN` or `Infinity` tokens.

Optional context collections may be empty arrays, but their collection names
remain present in `context.json`.

## 6. Refresh and Publication Flow

```text
pipeline/config.json
        │
        ▼
five fetch pipelines ──► pipeline/.staging/<job>/cache
        │
        ▼
normalize + clean + validate
        │
        ▼
five staged JSON files + staged release.json
        │
        ▼
cross-file release/hash validation
        │
        ├── failure: keep current output and current cache unchanged
        │
        └── success: replace output and pipeline/.cache as one rollback unit
```

Refresh uses a single-flight lock. A second refresh request returns the active
status rather than launching another run. Staging and backup paths are hidden
under `pipeline/` and are removed after success or rollback.

The publisher stages both the output and cache generations, backs up both
active directories, and rolls both back if either replacement fails. It never
leaves a new output paired with an older cache, or a new cache paired with an
older output.

The output filenames never include a date. A later successful refresh replaces
the same six files. Failed, interrupted, or partially validated refreshes do
not change the active output.

## 7. Offline Migration

The reorganization does not perform a real network refresh. Initial stable JSON
files are derived from the newest existing week that passes the current release
validation. Draft and ad-hoc directories cannot become the initial output merely
because their dates are newer.

Migration steps must:

1. Identify the newest currently complete release using its manifest and
   existing validation logic.
2. Convert its published CSV/JSON tables into the five strict JSON envelopes.
3. Generate and validate `release.json`.
4. Compare representative row counts, dates, values, units, sources, and
   quality flags with the source release.
5. Only after verification, move superseded generated directories to a
   recoverable trash/archive location outside the repository.

No tracked source file, dirty worktree change, or untracked user artifact may
be deleted simply because another file has a similar name.

## 8. Worktree and Generated-Artifact Cleanup

Worktree cleanup is separate from branch cleanup:

- Remove clean linked worktree directories while retaining their branches and
  commits.
- Do not delete branches during this reorganization.
- For dirty linked worktrees, first prove that every tracked and untracked
  change is preserved in the current repository or a recoverable external
  archive. Stop rather than force-remove an unpreserved worktree.
- Treat `tmp/`, deployment archives, ad-hoc runs, drafts, old `outputs/week_*`
  releases, caches, and rendered verification artifacts as generated content.
  Move confirmed superseded material to Trash rather than permanently deleting
  it.

## 9. Compatibility and Scope

The existing adjacent Next.js repository expects historical `outputs/week_*`
directories. This reorganization intentionally breaks that data-discovery
contract. The adjacent frontend must not be modified in this backend task and
will no longer be considered compatible after the stable-output migration.

A future frontend will be created as a separate sibling Git repository and will
consume only the six stable files in `output/`. That future project is outside
this design's implementation scope.

The following are also out of scope:

- new data providers or business metrics;
- changes to return, ranking, divergence, or evidence formulas;
- live network refreshes for migration or testing;
- historical snapshot browsing;
- cloud deployment or multi-user concurrency.

## 10. Verification and Acceptance

The reorganization is accepted only when all of the following are true:

- The repository has only `pipeline/` and `output/` as visible top-level
  directories.
- The five existing data domains remain represented by five stable JSON files.
- Running a deterministic fake refresh twice does not create additional output
  filenames or directories.
- A failed pipeline leaves all six active output files byte-for-byte unchanged.
- All active output files share one `release_id` and `as_of_date`.
- JSON contains no `NaN`, `Infinity`, ambiguous date, or magic zero used for a
  missing value.
- Representative migrated values, dates, units, source URLs, and row counts
  reconcile with the newest previously complete release.
- `pipeline/.cache/` contains only the latest successful raw-cache generation.
- No real network request is made by migration or automated tests.
- Existing deterministic Python tests are updated for their new paths and pass.
- The adjacent frontend repository is unchanged.
- Removed generated content remains recoverable from Trash or an explicit
  external archive until the user decides to purge it permanently.
