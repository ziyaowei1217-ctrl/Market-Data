# Active Backend Branch Consolidation Design

**Date:** 2026-08-30

**Status:** Approved for implementation planning

**Target repository:** `/Users/a1-6/Documents/market data`

**Target branch:** `main@5bd90c6`

**Active source branches:**

- `codex/public-green-integration@9c086eb`
- `codex/commodity-research-backend@e6f1619`

## 1. Objective

Finish the two active backend worktrees, integrate their compatible capabilities
into `main`, repair the current ChinaBond production-source failure, and leave a
single tested backend branch that can publish the latest complete weekly JSON
bundle atomically.

The integration must preserve the current two-folder product layout. It must not
restore obsolete production CSV configuration, dated output directories, a sixth
top-level business domain, or changes from the adjacent frontend repository.

## 2. Branch Scope

### 2.1 Branches to integrate

`codex/public-green-integration` is based directly on the current `main` and is
the semantic port of the earlier public-data Wave 0-5 work into the current
repository architecture. Its complete Python and workbook-compatibility test
suites passed before this design was written.

`codex/commodity-research-backend` is an independent implementation based on
`main@c2cd31c`. It adds official commodity prices, physical fundamentals,
positioning, bounded histories, provider diagnostics, and contract-three
publication. Its current full Python suite has two failing tests that share one
root cause: multiple eligible vintages for the same semantic observation are not
collapsed to the latest eligible vintage.

### 2.2 Branches not merged independently

The Wave 0-5 branches are ancestors of `codex/public-green-data-pipeline` and are
already the source history for the semantic public-green port. They are not
merged separately.

Older branches based on the retired repository layout remain historical recovery
references. They are not mechanically merged because doing so would reintroduce
obsolete paths and publication contracts. This consolidation deletes only the
two active branches after their commits are present in `main` and all merged-tree
verification passes.

## 3. Preservation and Safety Boundaries

- Keep only `pipeline/` and `output/` as visible top-level product directories.
- Keep `pipeline/config.json` as the only production configuration source.
- Keep the five acquisition and publication domains: indices, cross-market
  sectors, GICS, macro assets, and weekly context.
- Apply `as_of_date` before selecting or deriving any observation.
- Publish a new stable bundle only after all five pipelines and cross-file
  validation succeed.
- Preserve the current stable output identity until the final authorized live
  refresh succeeds.
- Preserve one successful raw-cache generation under `pipeline/.cache/`.
- Preserve empty optional collections as arrays and missing JSON values as
  `null`; never substitute zero, an empty string, `NaN`, or infinity.
- Preserve record-level source URL, observation date, and QC/source status.
- Preserve the unrelated untracked audit file
  `pipeline/internal/docs/2026-08-30-current-data-12-category-audit.md` without
  committing it as part of this integration.
- Archive any newly discovered unrelated dirty or untracked worktree files
  recoverably before cleanup.

## 4. Pre-Merge Commodity Repair

The existing failing tests are the RED evidence for the commodity repair:

- `BoundedPriceHistoryTests.test_same_observation_revisions_keep_only_the_latest_eligible_vintage`
- `BoundedMetricHistoryTests.test_same_observation_and_reference_revisions_keep_latest_eligible_vintage`

The implementation will group eligible rows by semantic observation identity
before history trimming. Price identity uses configured series/commodity and
observation date. Metric identity additionally includes the metric identity and
normalized reference period. Within each group, the row with the latest
normalized UTC `known_as_of` timestamp wins. Exact duplicate semantic identities
at the same timestamp remain an error; later vintages do not hide malformed,
future, non-finite, unconfigured, or provenance-invalid rows.

The focused test module must turn GREEN before the branch full suite and workbook
compatibility test are rerun. The repair is committed on the commodity branch so
the source branch is genuinely finished before integration.

## 5. Integration Sequence

1. Capture the starting branch tips, worktree paths, statuses, stable output
   identity, and the unrelated untracked audit file hash.
2. Repair and verify `codex/commodity-research-backend`.
3. Fast-forward `main` to `codex/public-green-integration`.
4. Merge the repaired commodity branch into `main` with a merge commit.
5. Resolve overlapping files semantically, preserving both approved capability
   sets and the current repository/publication architecture.
6. Add the ChinaBond endpoint and response-envelope repair through a separate
   TDD commit on the merged tree.
7. Run focused, full, workbook, output-bundle, and live-refresh verification.
8. Remove the two clean active worktrees and delete their merged branches with
   non-forced deletion.

No rebase, reset, force deletion, force push, or bulk checkout of another branch
tree is used.

## 6. Conflict Ownership Rules

The merge has overlapping changes in configuration, provider contracts,
provider registration, macro/context composition, release validation, scripts,
and tests. Conflict resolution follows these ownership rules.

### 6.1 Configuration

`pipeline/config.json` becomes the validated union of public-green and commodity
configuration. Existing identifiers remain stable. Commodity-specific HTTP,
taxonomy, history, source, freshness, CFTC, EIA, World Bank, USDA, and metals
sections are additive. Public-green macro, economic, flow, SEC, company, and
capability sections remain present. Duplicate identifiers or contradictory
provider semantics fail configuration validation.

### 6.2 Provider contracts and registry

Public-green owns the general typed provider contract, capability states,
economic releases, flows, company fundamentals, and capital-markets providers.
Commodity adds provider-phase diagnostics, official commodity transports,
commodity-specific requiredness, and commodity semantic metadata. The final
registry contains both sets with unique provider identities and no silent
fallback to obsolete providers.

### 6.3 Macro assets

Public-green macro calculations, liquidity, cross-asset, rates, FX, and audit
metadata remain available. Commodity adds official EIA and World Bank price
providers, bounded price histories, commodity taxonomy, and exact source
metadata. Commodity ownership does not replace non-commodity macro behavior.

### 6.4 Weekly context

Public-green economic, event, market-state, public-flow, company, and
capital-markets tables remain. Commodity adds physical fundamentals,
positioning, histories, provider diagnostics, and commodity joins. The final
context output keeps optional empty arrays and publishes no stale partial rows.

### 6.5 Release contract

The commodity branch's additive contract-three files and validation become the
newest supported contract. Legacy/current contract-one and contract-two source
bundles remain readable for validated offline migration and existing stable
output validation. `release.json` continues to hash exactly five business JSON
files. Every contract-three auxiliary file is referenced from those business
files and validated without becoming a sixth business domain.

### 6.6 Tests and documentation

Tests are combined rather than choosing one branch's version wholesale. When
both branches extend one test module, the final file retains both behavior
families and removes only assertions made obsolete by the approved unified
contract. Repository documentation describes the unified current behavior; both
approved design and implementation-plan records remain tracked.

## 7. ChinaBond Production Repair

The existing adapter calls the retired endpoint
`/cbweb-mn/pgxh/historyQuery`, which currently accepts the TLS connection and
request but returns no response before timeout. The current official history
page calls `/cbweb-czb-web/czb/historyQuery` with `qxmc=1` and returns an object
containing `flag` and `heList`.

A focused failing test will require the current URL, request parameters, and
response envelope. The parser will accept only a successful official envelope,
validate that `heList` is an array, preserve the existing exact maturity-field
mapping, and reject empty or malformed responses. The live refresh remains
fail-closed if ChinaBond is unavailable.

## 8. Verification Gates

### 8.1 Commodity branch before merge

- Run the focused commodity-history test module and confirm the two existing RED
  failures.
- Implement the minimal repair and confirm the focused module is GREEN.
- Run `python3 -m unittest -v`.
- Run `node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs`.

### 8.2 Unified `main`

- Run focused modules for configuration, macro assets, commodity research,
  provider registry, weekly context, weekly release, latest JSON output, and
  offline migration.
- Run `python3 -m unittest -v`.
- Run `node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs`.
- Run `pipeline.internal.capital_weekly.weekly_release.validate_output_bundle`
  against the active `output/` before the live refresh.
- Confirm the unrelated audit file hash and the two-folder workspace boundary.

### 8.3 Live refresh

Run the single coordinated entrypoint for the latest finished Sunday. A required
provider or validation failure leaves the old stable output and successful cache
visible. On success, validate the new bundle again and report its release ID,
source week, cutoff, row counts, source failures, hashes, and remaining universe
coverage limitations.

## 9. Completion and Cleanup

Completion requires all verification gates to pass and the active `output/`
bundle to validate. Then:

- remove `.worktrees/public-green-integration` and
  `.worktrees/commodity-research-backend` without force;
- prune stale worktree registrations;
- delete `codex/public-green-integration` and
  `codex/commodity-research-backend` with `git branch -d`;
- leave historical, superseded, and unrelated branches untouched;
- report every integration/fix commit, moved/created/deleted file, RED/GREEN
  evidence, full test results, stable output identity, live-refresh result,
  cleanup archive, and remaining compatibility or 677-universe coverage risks.

## 10. Explicit Non-Goals

- Claiming that integration alone completes all 677 research-universe items.
- Populating a production company watchlist without a separately defined
  universe.
- Restoring legacy `outputs/`, production CSV configuration, or dated release
  directories.
- Modifying the adjacent frontend repository.
- Deleting historical branches that are not ancestors of the final merged
  `main`.
