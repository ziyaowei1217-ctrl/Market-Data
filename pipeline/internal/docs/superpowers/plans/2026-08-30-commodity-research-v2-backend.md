# Commodity Research V2 Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish reliable official-source commodity histories and auditable registered research facts for all 19 configured commodities without weakening atomic release gates.

**Architecture:** A shared official-GET executor provides bounded retry and sanitized traces. Existing provider-specific parsers remain authoritative; a pure research assembler builds bounded histories and registered facts from normalized point-in-time rows. The release publisher adds three tables to the existing macro/context JSON owners and validates them from `pipeline/config.json` before atomically replacing output and the latest cache generation.

**Tech Stack:** Python 3.9+, `requests`, pandas, standard-library dataclasses/JSON/hashlib, `unittest`, Node workbook compatibility test.

**Spec:** `pipeline/internal/docs/superpowers/specs/2026-08-30-commodity-research-v2-design.md`

## Global Constraints

- Work only in `/Users/a1-6/Documents/market data/.worktrees/commodity-research-backend`.
- Read `AGENTS.md`, the V1 commodity database spec, the V2 spec, and the current task report before editing.
- Apply `as_of_date` and aware `known_as_of` cutoff before selecting or calculating any value.
- `pipeline/config.json` is the only production configuration source.
- Keep five pipeline domains and exactly six stable files in `output/`.
- A required-source failure leaves output and the prior successful cache byte-identical and removes staging.
- Only free official Commodity Research sources are eligible; never add a vendor fallback.
- Do not run a live refresh until Task 7 and explicit controller authorization.
- Follow RED-GREEN TDD. Run focused modules before `python3 -m unittest -v`.
- Run `node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs` and `validate_output_bundle` before task completion.
- Each task owns only the files listed in that task and ends in a separate commit plus independent review.

## File Structure

- Create `pipeline/internal/capital_weekly/official_http.py`: bounded official GET execution and sanitized traces.
- Modify `pipeline/internal/capital_weekly/context/provider_contracts.py`: provider phase/error/result metadata.
- Modify `pipeline/internal/capital_weekly/context/providers.py`: shared executor adoption for EIA/USDA/CME/USGS/CFTC transports.
- Modify `pipeline/internal/capital_weekly/context/eia_commodities.py`: exact batch requests and metadata validation.
- Modify `pipeline/internal/capital_weekly/macro_assets.py`: compatible bundle API and price-history emission.
- Create `pipeline/internal/capital_weekly/commodity_research.py`: stable record IDs, bounded histories, registered facts.
- Modify `pipeline/internal/capital_weekly/weekly_context.py`: source-log diagnostics and context history/fact tables.
- Modify `pipeline/internal/capital_weekly/weekly_release.py`: staged/output schemas and config-derived validation.
- Modify `pipeline/internal/scripts/fetch_macro_assets.py`: write macro price-history CSV from the bundle API.
- Modify `pipeline/internal/scripts/fetch_weekly_context.py`: write context history and research-fact CSVs.
- Create `pipeline/internal/scripts/probe_commodity_sources.py`: read-only EIA/official-source diagnostics.
- Modify `pipeline/config.json`: retry policies, history limits, and registered formulas.
- Add focused tests under `pipeline/internal/tests/`; no test performs network I/O.

---

### Task 1: Bounded Official HTTP Executor

**Files:**

- Create: `pipeline/internal/capital_weekly/official_http.py`
- Test: `pipeline/internal/tests/test_capital_weekly_official_http.py`

**Interfaces:**

- Produces `OfficialHttpPolicy(connect_timeout, read_timeout, total_timeout, max_attempts, backoff_seconds, retry_after_cap)`.
- Produces `OfficialHttpTrace(attempts, elapsed_ms, status_codes, final_url)`.
- Produces `OfficialHttpResponse(body, url, headers, trace)`.
- Produces `OfficialHttpError(code, phase, retryable, attempts, safe_message)`.
- Produces `official_get(session, url, *, policy, headers=None, params=None, audit_secrets=(), sleep=time.sleep, monotonic=time.monotonic) -> OfficialHttpResponse`.

- [ ] **Step 1: Write retry and deadline RED tests**

Create a deterministic fake session whose `get` sequence is transport error,
HTTP 429 with `Retry-After: 2`, then HTTP 200. Assert exactly three attempts,
sleep calls `[policy.backoff_seconds[0], 2.0]`, exact response bytes, and a
credential-free final URL. Add independent tests proving HTTP 400 and schema
callbacks are never retried, total deadline stops before a further attempt,
and percent/plus/plain secrets are absent from errors and traces.

```python
response = official_get(
    session,
    "https://api.eia.gov/v2/data/?api_key=secret",
    policy=OfficialHttpPolicy(2, 5, 20, 3, (0.5, 1.0), 5),
    audit_secrets=("secret",),
    sleep=sleeps.append,
    monotonic=clock,
)
self.assertEqual(response.trace.attempts, 3)
self.assertEqual(sleeps, [0.5, 2.0])
self.assertNotIn("secret", response.trace.final_url)
```

- [ ] **Step 2: Run RED**

Run:

```bash
python3 -m unittest -v pipeline.internal.tests.test_capital_weekly_official_http
```

Expected: import failure for `pipeline.internal.capital_weekly.official_http`.

- [ ] **Step 3: Implement the executor**

Use only idempotent `session.get`. Retry `requests.Timeout`,
`requests.ConnectionError`, and HTTP `408`, `425`, `429`, `500`, `502`, `503`,
`504`. Parse numeric and HTTP-date `Retry-After`; cap it by
`retry_after_cap` and remaining total time. Pass `(connect_timeout,
read_timeout)` to `requests`. Build safe errors with `sanitize_audit_text` and
never include response bodies.

- [ ] **Step 4: Run GREEN and mutation check**

Run the focused module. Temporarily remove `429` from the retry set, confirm the
429 test fails, restore the branch, and rerun to GREEN.

- [ ] **Step 5: Run compatibility tests**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_official_http \
  pipeline.internal.tests.test_capital_weekly_context_providers \
  pipeline.internal.tests.test_capital_weekly_macro_assets
```

- [ ] **Step 6: Commit**

```bash
git add pipeline/internal/capital_weekly/official_http.py \
  pipeline/internal/tests/test_capital_weekly_official_http.py
git commit -m "feat: add bounded official http executor"
```

### Task 2: Provider Phase and Source-Log Contract

**Files:**

- Modify: `pipeline/internal/capital_weekly/context/provider_contracts.py`
- Modify: `pipeline/internal/capital_weekly/context/common.py`
- Modify: `pipeline/internal/capital_weekly/weekly_context.py`
- Modify: `pipeline/internal/capital_weekly/weekly_release.py`
- Test: `pipeline/internal/tests/test_capital_weekly_weekly_context.py`
- Test: `pipeline/internal/tests/test_capital_weekly_weekly_release.py`

**Interfaces:**

- Produces `ProviderPhaseError(error_code, failure_phase, safe_message, attempts=1)`.
- Extends `ProviderResult` with `attempts: int = 1` and `completed_phase: str = "normalized"`.
- Extends context `source_log` with `phase`, `attempts`, and `error_code`.
- Allowed phases are `config`, `metadata`, `retrieve`, `raw`, `parse`, `point_in_time`, `freshness`, `coverage`, and `normalized`.

- [ ] **Step 1: Write source-log RED tests**

Add one successful provider and one provider raising
`ProviderPhaseError("EIA_TIMEOUT", "retrieve", "request timed out", 3)`.
Assert successful `phase`, `attempts`, and `error_code` fields are `normalized`, `1`, and `null`; failed fields
are `retrieve`, `3`, and `EIA_TIMEOUT`; business rows remain zero for the
failed provider. Add mutations for unknown phase, attempts zero, naive/future
`known_as_of`, and secret-bearing `safe_message`.

- [ ] **Step 2: Run RED**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_weekly_context \
  pipeline.internal.tests.test_capital_weekly_weekly_release
```

Expected: missing constructor fields and staged CSV schema mismatch.

- [ ] **Step 3: Implement phase metadata**

Normalize all uncaught provider exceptions to error code
`UNCLASSIFIED_PROVIDER_FAILURE`, phase `retrieve`, attempts `1`, with sanitized
text. Reject unknown phases and nonpositive attempts before writing raw or
business rows. Include the new exact columns in `SOURCE_LOG_FIELDS` and staged
release datasets.

- [ ] **Step 4: Run GREEN**

Run the two focused modules and verify existing V1 provider status semantics
remain unchanged.

- [ ] **Step 5: Validate the active V1 output compatibility path**

The stable loader must continue accepting dataset contract version 2 without
the new additive source-log columns. Add a direct legacy fixture assertion and
run `test_latest_json_output`.

- [ ] **Step 6: Commit**

```bash
git add pipeline/internal/capital_weekly/context/provider_contracts.py \
  pipeline/internal/capital_weekly/context/common.py \
  pipeline/internal/capital_weekly/weekly_context.py \
  pipeline/internal/capital_weekly/weekly_release.py \
  pipeline/internal/tests/test_capital_weekly_weekly_context.py \
  pipeline/internal/tests/test_capital_weekly_weekly_release.py
git commit -m "feat: publish provider phase diagnostics"
```

### Task 3: Official Commodity Transports, EIA Batching, and Read-Only Probe

**Files:**

- Modify: `pipeline/internal/capital_weekly/context/eia_commodities.py`
- Modify: `pipeline/internal/capital_weekly/context/providers.py`
- Modify: `pipeline/internal/capital_weekly/macro_assets.py`
- Modify: `pipeline/internal/capital_weekly/commodity_prices.py`
- Create: `pipeline/internal/scripts/probe_commodity_sources.py`
- Modify: `pipeline/config.json`
- Test: `pipeline/internal/tests/test_capital_weekly_commodities.py`
- Test: `pipeline/internal/tests/test_capital_weekly_commodity_prices.py`
- Test: `pipeline/internal/tests/test_capital_weekly_context_providers.py`
- Test: `pipeline/internal/tests/test_capital_weekly_macro_assets.py`
- Test: `pipeline/internal/tests/test_capital_weekly_positioning.py`
- Test: `pipeline/internal/tests/test_capital_weekly_metal_inventories.py`
- Test: `pipeline/internal/tests/test_capital_weekly_usda_commodities.py`
- Test: `pipeline/internal/tests/test_pipeline_config.py`

**Interfaces:**

- Produces `EiaBatchSpec(route, facets, frequency, start, end, page_length)`.
- Produces `fetch_eia_batches(client, specs, *, expected_metadata) -> list[dict]`.
- Probe command:

```bash
python3 -m pipeline.internal.scripts.probe_commodity_sources \
  --config pipeline/config.json --as-of 2026-08-23 --provider eia
```

The probe prints sanitized JSON to stdout and writes no file.

- [ ] **Step 1: Write exact batching RED tests**

Create fixtures for price, natural-gas, and petroleum routes. Assert configured
series are split into batches no larger than `request_batch_size`, every page
uses `offset` and `length`, metadata description/unit/facet checks happen
before row parsing, duplicate/missing series fail coverage, and an HTTP retry
trace propagates attempts into `ProviderResult`.

Add transport-boundary tests proving the configured World Bank, CFTC, CME,
USGS, USDA PSD, and USDA ESR commodity providers call `official_get` with their
exact policy and audit secrets. Assert validation errors from each parser are
not retried, and successful binary CME/USGS raw bytes remain byte-exact.

- [ ] **Step 2: Write probe no-mutation RED test**

Run `probe_commodity_sources.main()` against a fake client with temporary
output/cache/staging/status paths. Assert stdout contains provider, phase,
attempts, series count, latest eligible date, and sanitized route; assert all
temporary trees remain byte-identical and no new path appears.

- [ ] **Step 3: Run RED**

Run the four focused modules. Expected failures: no batch interface, no retry
policy config, and no probe module.

- [ ] **Step 4: Implement EIA integration**

Adopt `official_get` for every configured Commodity Research HTTP GET transport:
EIA, World Bank, CFTC, CME, USGS, USDA PSD, and USDA ESR. Preserve each current
provider-specific parser and exact official identity registry; the shared
executor ends at response bytes and never normalizes provider schemas. Config
must declare, for each commodity provider, `connect_timeout`, `read_timeout`, `total_timeout`,
`max_attempts`, `retry_backoff_seconds`, `retry_after_cap`,
with `request_batch_size` and `page_length` additionally required for EIA;
parsing rejects missing keys or hidden defaults.

- [ ] **Step 5: Implement the read-only probe**

Dependency-inject the client in tests. Production resolves `EIA_API_KEY` from
the environment, validates metadata and one latest eligible page per batch,
and returns exit 1 with a sanitized error JSON object on failure. It must not
call a pipeline runner or cache writer.

- [ ] **Step 6: Run GREEN and commit**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_commodities \
  pipeline.internal.tests.test_capital_weekly_commodity_prices \
  pipeline.internal.tests.test_capital_weekly_context_providers \
  pipeline.internal.tests.test_capital_weekly_macro_assets \
  pipeline.internal.tests.test_capital_weekly_positioning \
  pipeline.internal.tests.test_capital_weekly_metal_inventories \
  pipeline.internal.tests.test_capital_weekly_usda_commodities \
  pipeline.internal.tests.test_pipeline_config
git add pipeline/internal/capital_weekly/context/eia_commodities.py \
  pipeline/internal/capital_weekly/context/providers.py \
  pipeline/internal/capital_weekly/macro_assets.py \
  pipeline/internal/capital_weekly/commodity_prices.py \
  pipeline/internal/scripts/probe_commodity_sources.py \
  pipeline/config.json pipeline/internal/tests
git commit -m "feat: harden official EIA retrieval"
```

### Task 4: Bounded Commodity History Contract

**Files:**

- Create: `pipeline/internal/capital_weekly/commodity_research.py`
- Modify: `pipeline/internal/capital_weekly/macro_assets.py`
- Modify: `pipeline/internal/scripts/fetch_macro_assets.py`
- Modify: `pipeline/internal/capital_weekly/weekly_context.py`
- Modify: `pipeline/internal/scripts/fetch_weekly_context.py`
- Modify: `pipeline/config.json`
- Test: `pipeline/internal/tests/test_capital_weekly_commodity_research.py`
- Test: `pipeline/internal/tests/test_capital_weekly_macro_assets.py`
- Test: `pipeline/internal/tests/test_capital_weekly_weekly_context.py`

**Interfaces:**

- Produces `stable_record_id(namespace: str, identity: Mapping[str, object]) -> str`.
- Produces `bounded_price_history(histories, universe, as_of_date, limits) -> list[dict]`.
- Produces `bounded_metric_history(rows, as_of_date, limits) -> list[dict]`.
- Produces `MacroAssetBundle(detail: DataFrame, source_log: DataFrame, commodity_price_history: DataFrame)`.
- Produces `fetch_macro_asset_bundle(...) -> MacroAssetBundle` while preserving
  `fetch_macro_assets(...) -> tuple[DataFrame, DataFrame]` as the V1 wrapper.
- Adds `commodity_price_history.csv`, `commodity_metric_history.csv` staging tables.

- [ ] **Step 1: Write pure history RED tests**

Use daily, weekly, monthly, and annual rows straddling the cutoff. Assert exact
window maxima `400/160/84/12`, oldest rows trimmed after point-in-time
selection, stable ascending order, identical semantic rows receive identical
SHA-256 record IDs, duplicate identities fail, nonfinite values become no row
rather than zero, and source-native units remain unchanged.

- [ ] **Step 2: Write pipeline compatibility RED tests**

Assert the bundle contains EIA/World Bank price histories only for configured
Commodity Research codes; the old tuple wrapper remains exactly two values.
Assert weekly context returns the new history category without changing the
existing arrays.

- [ ] **Step 3: Run RED**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_commodity_research \
  pipeline.internal.tests.test_capital_weekly_macro_assets \
  pipeline.internal.tests.test_capital_weekly_weekly_context
```

- [ ] **Step 4: Implement history builders**

Derive identity hashes from canonical JSON with sorted keys and compact UTF-8
encoding. Price identity is code, series, observation date, and known-as-of.
Metric identity is code, metric, role, measurement, participant, observation
date, known-as-of, and reference period. Reject missing source URL, QC other
than `OK`, unsupported taxonomy, or future/naive timestamps.

- [ ] **Step 5: Wire scripts and config**

Add explicit `history_limits` keys for `daily=400`, `weekly=160`,
`monthly=84`, `annual=12`, and `marketing_year=12`; parsing fails when any key
is absent or nonpositive. Writers use the exact field order declared in
`commodity_research.py`.

- [ ] **Step 6: Run GREEN and commit**

```bash
git add pipeline/internal/capital_weekly/commodity_research.py \
  pipeline/internal/capital_weekly/macro_assets.py \
  pipeline/internal/capital_weekly/weekly_context.py \
  pipeline/internal/scripts/fetch_macro_assets.py \
  pipeline/internal/scripts/fetch_weekly_context.py \
  pipeline/config.json pipeline/internal/tests
git commit -m "feat: publish bounded commodity histories"
```

### Task 5: Registered Research Facts

**Files:**

- Modify: `pipeline/internal/capital_weekly/commodity_research.py`
- Modify: `pipeline/internal/capital_weekly/weekly_context.py`
- Modify: `pipeline/internal/scripts/fetch_weekly_context.py`
- Modify: `pipeline/config.json`
- Test: `pipeline/internal/tests/test_capital_weekly_commodity_research.py`

**Interfaces:**

- Produces `FormulaSpec(formula_id, version, fact_kind, output_unit, required_inputs)`.
- Produces `build_research_facts(price_history, metric_history, formula_specs, as_of_date) -> list[dict]`.
- Initial formula IDs: `absolute_change_v1`, `percentage_change_v1`,
  `year_over_year_change_v1`, `trailing_percentile_v1`,
  `seasonal_deviation_v1`, `stock_to_use_v1`, `coverage_count_v1`, and
  `freshness_age_days_v1`.
- Adds `commodity_research_facts.csv` to weekly context.

- [ ] **Step 1: Write formula RED tests**

For every formula, assert value, unit, observation date, known-as-of,
`formula_id`, `formula_version`, exact sorted `input_record_ids`, and exact
deduplicated official `source_urls`. Add failure tests for zero denominator,
mixed unit, mixed USDA vintage, missing input record, future input, insufficient
seasonal week coverage, nonfinite result, duplicate fact identity, and
unregistered formula.

- [ ] **Step 2: Run RED**

```bash
python3 -m unittest -v pipeline.internal.tests.test_capital_weekly_commodity_research
```

Expected: missing formula registry and fact builder.

- [ ] **Step 3: Implement pure formula functions**

Each function consumes immutable row dictionaries and returns either one fact
or `None` for a factual unavailable calculation. A schema/identity/unit/vintage
violation raises `ValueError`; it never returns a guessed value. Percentile
uses configured trailing observations and a documented inclusive-rank rule.

- [ ] **Step 4: Implement config-derived dispatch**

Config maps each `fact_code` to exact commodity code, formula ID/version, and
exact input metric/series identities. The builder rejects an input selected by
prefix or label. No formula has a hidden default.

- [ ] **Step 5: Run GREEN and mutation checks**

Temporarily remove same-vintage enforcement and confirm the stock-to-use test
fails. Temporarily remove input existence validation and confirm the orphan
fact test fails. Restore and rerun GREEN.

- [ ] **Step 6: Commit**

```bash
git add pipeline/internal/capital_weekly/commodity_research.py \
  pipeline/internal/capital_weekly/weekly_context.py \
  pipeline/internal/scripts/fetch_weekly_context.py \
  pipeline/config.json \
  pipeline/internal/tests/test_capital_weekly_commodity_research.py
git commit -m "feat: add registered commodity research facts"
```

### Task 6: Config-Derived Release and Stable JSON Validation

**Files:**

- Modify: `pipeline/internal/capital_weekly/weekly_release.py`
- Modify: `pipeline/config.json`
- Test: `pipeline/internal/tests/test_capital_weekly_weekly_release.py`
- Test: `pipeline/internal/tests/test_latest_json_output.py`
- Test: `pipeline/internal/tests/test_pipeline_config.py`

**Interfaces:**

- Raises `ReleaseValidationError` for invalid history/fact identity, coverage,
  provenance, point-in-time, formula, or provider-state relationships.
- Adds `commodity_price_history` to `macro.json` and
  `commodity_metric_history` plus `commodity_research_facts` to `context.json`.
- Preserves V1 absence compatibility for the current dataset contract; V2
  candidates must declare dataset contract version 3 and all three tables.

- [ ] **Step 1: Write complete V2 fixture RED**

Build five deterministic staged pipeline directories with all 19 codes, seven
families, three new tables, exact source logs, histories, and facts. Assert the
bundle has six stable files and every fact input resolves to a published
history row.

- [ ] **Step 2: Write table-driven mutation REDs**

Mutate one field at a time: code/family, record ID, duplicate identity,
observation order, history limit, future/naive known-as-of, nonfinite value,
source host, formula ID/version, orphan input, mixed-vintage fact, provider
status with residual rows, missing configured code, and BTC inclusion. Each
mutation must raise a specific `ReleaseValidationError`.

- [ ] **Step 3: Run RED**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_weekly_release \
  pipeline.internal.tests.test_latest_json_output \
  pipeline.internal.tests.test_pipeline_config
```

- [ ] **Step 4: Implement versioned table mapping**

Extend `release_datasets_for_contract(3)` and `OUTPUT_TABLES`; do not require
V2 tables when validating the preserved contract-2 active output. Build all
coverage expectations from exact config identities and provider mappings.

- [ ] **Step 5: Implement cross-table validation**

Index histories by `record_id`, facts by semantic identity, and source logs by
provider. Validate exact rows and relationships before writing any JSON.
Official host checks accept only exact host or dot-subdomain matches.

- [ ] **Step 6: Run GREEN and commit**

```bash
git add pipeline/internal/capital_weekly/weekly_release.py pipeline/config.json \
  pipeline/internal/tests/test_capital_weekly_weekly_release.py \
  pipeline/internal/tests/test_latest_json_output.py \
  pipeline/internal/tests/test_pipeline_config.py
git commit -m "feat: validate commodity research v2 releases"
```

### Task 7: Coordinator Rollback, Full Verification, and One Live Attempt

**Files:**

- Modify: `pipeline/internal/tests/test_capital_weekly_weekly_release.py`
- Modify: `pipeline/internal/capital_weekly/weekly_release.py`
- Modify: `pipeline/internal/docs/REPOSITORY_STRUCTURE.md`
- Create: `.superpowers/sdd/2026-08-30-commodity-research-v2/backend-final-report.md`

**Interfaces:**

- Uses existing `run_latest_release(...)` and `validate_output_bundle(...)`.
- Produces no new production interface.

- [ ] **Step 1: Write coordinator RED tests**

Add a required EIA failure after other staged pipelines succeed. Assert the six
output SHA-256 values and prior cache bytes are unchanged, staging has zero
children, and status reports pipeline, provider, phase, attempts, and sanitized
error code. Add two successful fake generations proving cache replacement
retains only `cache.json` and one latest generation per domain.

- [ ] **Step 2: Run RED then GREEN**

Run the weekly-release focused module, implement only coordinator/status
changes required by the tests, rerun, and commit the behavior with its test.

- [ ] **Step 3: Run full deterministic verification**

```bash
python3 -m unittest -v
node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs
python3 -c 'from pathlib import Path; from pipeline.internal.capital_weekly.weekly_release import validate_output_bundle; validate_output_bundle(Path("/Users/a1-6/Documents/market data/output"))'
git diff --check
```

Record exact counts, active release identity, six hashes, cache/staging file
sets, dependency versions, and secret-scan results.

- [ ] **Step 4: Run official read-only probes**

Run the EIA probe and equivalent existing official parsers for World Bank,
CFTC, CME, USGS, and USDA documentation/credential state. Probes may read the
network but must not mutate output, cache, staging, or status. Stop and fix only
verified factual schema/config mismatches with a new RED/GREEN test.

- [ ] **Step 5: Run one authorized live refresh**

Capture all six output and cache hashes first. Run the coordinator for the
latest finished Sunday. Do not manually publish staging. On success, validate
the complete V2 release and cache layout. On failure, do not retry unless the
controller explicitly authorizes another attempt; prove rollback hashes and
report the exact official-source boundary.

- [ ] **Step 6: Document and commit**

Update repository documentation with the V2 tables, probe command, retry
semantics, and six-screen consumer contract. Write the final report with RED,
GREEN, live outcome, files, commits, hashes, cleanup archive, and risks.

```bash
git add pipeline/internal/capital_weekly/weekly_release.py \
  pipeline/internal/tests/test_capital_weekly_weekly_release.py \
  pipeline/internal/docs/REPOSITORY_STRUCTURE.md
git commit -m "docs: verify commodity research v2 publication"
```
