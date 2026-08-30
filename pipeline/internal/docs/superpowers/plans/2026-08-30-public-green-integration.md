# Public Green Data Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Semantically port the approved Wave 0-5 public-data capabilities from `codex/public-green-data-pipeline@56ed7ad` into the current five-domain Capital Weekly backend.

**Architecture:** Treat the source tip as a read-only behavioral reference and adapt each capability into `pipeline/internal/` with `pipeline/config.json` as the only production configuration source. Provider results continue through the existing point-in-time weekly-context staging path, and publication remains an atomic five-file JSON bundle plus `release.json` validation metadata.

**Tech Stack:** Python 3.9+, standard-library `unittest`, pandas, requests, yfinance, openpyxl, pypdf, Git, Node.js built-in test runner.

**Spec:** `pipeline/internal/docs/superpowers/specs/2026-08-30-public-green-integration-design.md`

## Global Constraints

- Source behavior is pinned to `codex/public-green-data-pipeline@56ed7ad`; target work starts from `main@104572b` in a new ignored isolated worktree.
- Preserve exactly two visible product directories: `pipeline/` and `output/`; do not recreate root `capital_weekly/`, `data/`, `tests/`, dated output directories, or legacy production CSV configuration.
- Keep `pipeline/config.json` as the only production configuration source. Explicit CSV paths remain supported only for deterministic tests and diagnostics.
- Preserve the five business files `indices.json`, `sectors.json`, `gics.json`, `macro.json`, and `context.json`; `release.json` hashes exactly those five files.
- Apply `as_of_date` before release selection, snapshot returns, revisions, correlations, or other derived calculations.
- Missing values serialize as JSON `null`; optional collections serialize as arrays even when empty; no business field uses zero, an empty string, `NaN`, or infinity as a missing-value sentinel.
- Every published business record retains source URL, observation date, and QC or source status.
- Required provider failure blocks publication. Allowed optional failures are explicit in the source log and leave an empty stable collection.
- Do not run a real network refresh. Tests use deterministic fake sessions, fixture text, and fake histories.
- Do not populate the production company watchlist; `context.company_watchlist` remains `[]` unless the user separately supplies entries.
- Do not modify the untracked current-data audit, the dirty `commodity-research-backend` worktree, or the adjacent frontend checkout.
- Every behavior slice records an expected focused RED before implementation, then focused GREEN, related test GREEN, and a task-owned commit.

---

### Task 1: Configuration and Provider Contracts

**Files:**
- Modify: `pipeline/config.json`
- Modify: `pipeline/internal/common.py`
- Modify: `pipeline/internal/capital_weekly/context/provider_contracts.py`
- Modify: `pipeline/internal/capital_weekly/context/providers.py`
- Modify: `pipeline/internal/capital_weekly/weekly_context.py`
- Modify: `pipeline/internal/tests/test_pipeline_config.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_context_providers.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_weekly_context.py`

**Interfaces:**
- Consumes: `load_config_rows(section: str) -> list[dict]` from `pipeline.internal.common`.
- Produces: `ProviderSpec.failure_source: str`, `ProviderSpec.failure_source_url: str`, validated `context.breadth_universe` rows, classification-aware `context.cftc_contracts` rows, and a production-empty `context.company_watchlist`.

- [ ] **Step 1: Add failing configuration and provider-contract tests**

```python
def test_public_green_config_is_json_backed_and_watchlist_stays_empty(self):
    breadth = load_config_rows("context.breadth_universe")
    cftc = load_config_rows("context.cftc_contracts")
    self.assertEqual({row["symbol"] for row in breadth}, {
        "XLC", "XLY", "XLP", "XLE", "XLF", "XLV",
        "XLI", "XLB", "XLRE", "XLK", "XLU",
    })
    self.assertEqual({row["report_type"] for row in cftc}, {"tff", "disaggregated"})
    self.assertEqual(load_config_rows("context.company_watchlist"), [])

def test_provider_failure_provenance_is_typed(self):
    spec = ProviderSpec(
        name="optional", category="market_internals", source_tier="public",
        requiredness="optional", provider_version="1.0.0",
        schema_version="context-metric-v1", frequency="daily",
        freshness_days=7, failure_source="Official Source",
        failure_source_url="https://example.gov/data",
    )
    self.assertEqual(spec.failure_source, "Official Source")
    self.assertEqual(spec.failure_source_url, "https://example.gov/data")
```

- [ ] **Step 2: Run the focused tests and capture RED**

Run:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_pipeline_config \
  pipeline.internal.tests.test_capital_weekly_context_providers \
  pipeline.internal.tests.test_capital_weekly_weekly_context
```

Expected: failure because `context.breadth_universe`, CFTC `report_type`, and the two failure-provenance fields are absent.

- [ ] **Step 3: Extend the provider contract without changing existing callers**

```python
@dataclass(frozen=True)
class ProviderSpec:
    name: str
    category: str
    source_tier: str
    requiredness: str
    provider_version: str
    schema_version: str
    frequency: str
    freshness_days: int | None
    failure_source: str = ""
    failure_source_url: str = ""
```

In `run_weekly_context`, use these values when an optional fetch raises before a `ProviderResult` exists:

```python
"source": provider.spec.failure_source or None,
"source_url": provider.spec.failure_source_url or None,
```

- [ ] **Step 4: Translate source CSV configuration into JSON**

Add the eleven source rows from `data/capital_weekly_breadth_universe.csv` at the pinned source tip to `context.breadth_universe`. Add `report_type` to all four CFTC rows: `13874A` and `098662` use `tff`; `088691` and `067651` use `disaggregated`. Preserve `context.company_watchlist` as an empty array.

Production loading remains:

```python
if data_dir is None:
    breadth_universe = load_config_rows("context.breadth_universe")
    cftc_rows = load_config_rows("context.cftc_contracts")
else:
    breadth_universe = _config(Path(data_dir) / "capital_weekly_breadth_universe.csv")
    cftc_rows = _config(Path(data_dir) / "capital_weekly_cftc_contracts.csv")
```

Reject blank or duplicate breadth symbols, blank or duplicate CFTC contract codes, unknown report types, and a missing TFF or Disaggregated classification.

- [ ] **Step 5: Re-run focused tests and the configuration boundary tests**

Run:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_pipeline_config \
  pipeline.internal.tests.test_capital_weekly_context_providers \
  pipeline.internal.tests.test_workspace_layout
```

Expected: PASS with all production configuration read from `pipeline/config.json`.

- [ ] **Step 6: Commit Task 1**

```bash
git add pipeline/config.json pipeline/internal/common.py \
  pipeline/internal/capital_weekly/context/provider_contracts.py \
  pipeline/internal/capital_weekly/context/providers.py \
  pipeline/internal/capital_weekly/weekly_context.py \
  pipeline/internal/tests/test_pipeline_config.py \
  pipeline/internal/tests/test_capital_weekly_context_providers.py \
  pipeline/internal/tests/test_capital_weekly_weekly_context.py
git commit -m "feat: extend public provider contracts"
```

---

### Task 2: Registered Macro Series and Cross-Asset Calculations

**Files:**
- Create: `pipeline/internal/capital_weekly/cross_asset.py`
- Create: `pipeline/internal/tests/test_capital_weekly_cross_asset.py`
- Modify: `pipeline/internal/capital_weekly/macro_assets.py`
- Modify: `pipeline/internal/capital_weekly/weekly_release.py`
- Modify: `pipeline/config.json`
- Modify: `pipeline/internal/tests/test_capital_weekly_macro_assets.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_weekly_release.py`

**Interfaces:**
- Consumes: normalized history dictionaries with `date` and `value`; `as_of_date`-filtered histories from the current macro runner.
- Produces: `rolling_correlation_history(histories, left_code, right_code, left_transform, right_transform, *, window, minimum_observations) -> list[dict]`, `CORRELATION_SPECS`, and registered calculated-source references.

- [ ] **Step 1: Port the source cross-asset tests and update imports**

Use the tests from `tests/test_capital_weekly_cross_asset.py` at `56ed7ad`, replacing `capital_weekly` imports with `pipeline.internal.capital_weekly`. Keep these cases: mixed return/level-change transforms, inner-date join, minimum observations, non-finite rejection, and zero-variance rejection.

Core assertion:

```python
result = rolling_correlation_history(
    histories, "SPY_CLOSE_PROXY", "TLT_CLOSE_PROXY",
    "pct_return", "pct_return", window=3, minimum_observations=3,
)
self.assertEqual(result[-1]["observations"], 3)
self.assertAlmostEqual(result[-1]["value"], expected_correlation)
```

- [ ] **Step 2: Run the new module and capture RED**

Run:

```bash
python3 -m unittest -v pipeline.internal.tests.test_capital_weekly_cross_asset
```

Expected: import failure because `pipeline.internal.capital_weekly.cross_asset` does not exist.

- [ ] **Step 3: Port the calculation kernel**

Semantically port `capital_weekly/cross_asset.py@56ed7ad`. Preserve the cutoff-safe date join and finite/variance checks:

```python
eligible_dates = sorted(set(left_transformed) & set(right_transformed))
for end_index in range(window - 1, len(eligible_dates)):
    dates = eligible_dates[end_index - window + 1 : end_index + 1]
    if len(dates) < minimum_observations:
        continue
    value = _pearson(
        [left_transformed[item] for item in dates],
        [right_transformed[item] for item in dates],
    )
```

- [ ] **Step 4: Add the 23 missing macro rows and calculation registry**

Translate the pinned source rows for:

```text
AUD_USD, COMEX_COPPER, EQUITY_USD_CORR_13W, EQUITY_USD_CORR_26W,
EUR_USD, FED_NET_LIQUIDITY, FED_TOTAL_ASSETS, GBP_USD,
GOLD_REAL_YIELD_CORR_13W, GOLD_REAL_YIELD_CORR_26W,
OIL_BREAKEVEN_CORR_13W, OIL_BREAKEVEN_CORR_26W,
ON_RRP_TAKE_UP, SPY_CLOSE_PROXY, TGA_BALANCE, TLT_CLOSE_PROXY,
USD_CAD, USD_CHF, USD_JPY, USHY_IG_OAS, UST30Y5Y,
US_STOCK_BOND_CORR_13W, US_STOCK_BOND_CORR_26W
```

Register `rolling_correlation`, its exact input codes, transforms, window sizes, formula version `rolling-correlation-v1`, and `calculated:` source reference. Make correlation rows optional calculated series so insufficient overlap does not invent a value.

- [ ] **Step 5: Add macro and release-contract assertions, then run focused GREEN**

```python
self.assertEqual(config.calculation_id, "rolling_correlation")
self.assertEqual(detail["formula_version"], "rolling-correlation-v1")
if detail["qc_flag"] == "INSUFFICIENT_DATA":
    self.assertIsNone(detail["latest_value"])
```

Run:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_cross_asset \
  pipeline.internal.tests.test_capital_weekly_macro_assets \
  pipeline.internal.tests.test_capital_weekly_macro_as_of \
  pipeline.internal.tests.test_capital_weekly_weekly_release
```

Expected: PASS; calculated rows cite registered input series and never use future observations.

- [ ] **Step 6: Commit Task 2**

```bash
git add pipeline/config.json \
  pipeline/internal/capital_weekly/cross_asset.py \
  pipeline/internal/capital_weekly/macro_assets.py \
  pipeline/internal/capital_weekly/weekly_release.py \
  pipeline/internal/tests/test_capital_weekly_cross_asset.py \
  pipeline/internal/tests/test_capital_weekly_macro_assets.py \
  pipeline/internal/tests/test_capital_weekly_weekly_release.py
git commit -m "feat: add public macro calculations"
```

---

### Task 3: Official Economic Releases and Completed FOMC Decisions

**Files:**
- Create: `pipeline/internal/capital_weekly/context/economic_sources/census_release_common.py`
- Create: `pipeline/internal/capital_weekly/context/economic_sources/census_housing.py`
- Create: `pipeline/internal/capital_weekly/context/economic_sources/census_durable_goods.py`
- Create: `pipeline/internal/tests/test_capital_weekly_economic_census_housing.py`
- Create: `pipeline/internal/tests/test_capital_weekly_economic_census_durable_goods.py`
- Modify: `pipeline/internal/capital_weekly/context/economic_sources/bea.py`
- Modify: `pipeline/internal/capital_weekly/context/economic_sources/bls.py`
- Modify: `pipeline/internal/capital_weekly/context/economic_sources/census.py`
- Modify: `pipeline/internal/capital_weekly/context/economic_sources/__init__.py`
- Modify: `pipeline/internal/capital_weekly/context/economic_releases.py`
- Modify: `pipeline/internal/capital_weekly/context/events.py`
- Modify: `pipeline/internal/capital_weekly/context/providers.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_economic_bea.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_economic_bls.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_economic_census.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_economic_releases.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_events.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_context_providers.py`

**Interfaces:**
- Consumes: `ContextProvider`, `ProviderResult`, fake HTTP sessions, target `start` and Sunday `end` dates.
- Produces: `build_bea_provider`, `build_bls_provider`, `build_census_provider`, `build_census_housing_provider`, `build_census_durable_goods_provider`, and a registered `fomc_calendar` provider.

- [ ] **Step 1: Port the missing official-release tests and import paths**

Bring over the additional pinned tests for CPI/payroll/unemployment/AHE, GDP/PCE/income/outlays, retail sales, housing, durable goods, archive identity, revision matching, post-cutoff exclusion, and completed FOMC statement enrichment.

Provider-registration assertion:

```python
providers = build_default_providers(
    start=date(2026, 8, 17), end=date(2026, 8, 23),
    session=fake_session, yahoo_downloader=fake_download,
)
self.assertTrue({
    "bls_economic_releases", "bea_economic_releases",
    "census_retail_sales", "census_housing",
    "census_durable_goods", "fomc_calendar",
}.issubset(providers))
```

- [ ] **Step 2: Run the economic modules and capture RED**

Run:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_economic_bea \
  pipeline.internal.tests.test_capital_weekly_economic_bls \
  pipeline.internal.tests.test_capital_weekly_economic_census \
  pipeline.internal.tests.test_capital_weekly_economic_census_housing \
  pipeline.internal.tests.test_capital_weekly_economic_census_durable_goods \
  pipeline.internal.tests.test_capital_weekly_economic_releases \
  pipeline.internal.tests.test_capital_weekly_events \
  pipeline.internal.tests.test_capital_weekly_context_providers
```

Expected: missing Census modules, absent provider keys, and missing newer BEA/BLS calculations.

- [ ] **Step 3: Port release parsing and point-in-time validation**

Semantically port the source modules at `56ed7ad` into the current package. Release artifact rules stay fail-closed:

```python
if release_timestamp.astimezone(HONG_KONG) > target_sunday_cutoff(as_of_date):
    return []
if urlparse(source_url).hostname not in ALLOWED_RELEASE_HOSTS:
    raise ValueError("release artifact is not hosted by the official source")
```

Keep release-specific fields `observation_period`, `known_as_of`, `vintage_label`, `source_url`, `qc_flag`, `calculation_id`, `formula_version`, and `input_record_ids`. Reject mismatched release months/quarters, ambiguous table values, and conflicting archive/API artifacts.

- [ ] **Step 4: Preserve the BEA API as a corroborated source**

Use `https://apps.bea.gov/api/data` only through the source implementation's revision check:

```python
api_rows = _api_series(session, dataset_name, table_name, metadata)
_validate_api_revision(api_rows, release_rows, metadata)
```

The dated official release remains primary evidence. A mismatch raises and prevents publication; it never silently substitutes the latest BEA revision.

- [ ] **Step 5: Register all official providers and completed FOMC enrichment**

Add these exact default-provider entries:

```python
providers.update({
    "bls_economic_releases": build_bls_provider(start, end, client),
    "bea_economic_releases": build_bea_provider(start, end, client),
    "census_retail_sales": build_census_provider(start, end, client),
    "census_housing": build_census_housing_provider(start, end, client),
    "census_durable_goods": build_census_durable_goods_provider(start, end, client),
    "ism_manufacturing_pmi": _ism_licensed_provider(),
})
```

Register `fomc_calendar` as a required `events` provider. Enrich only meetings whose dated official statement was known by the Sunday cutoff.

- [ ] **Step 6: Run focused and point-in-time GREEN**

Run the Step 2 command, then:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_point_in_time \
  pipeline.internal.tests.test_capital_weekly_weekly_context
```

Expected: PASS with future artifacts excluded and all derived rows resolving eligible input record IDs.

- [ ] **Step 7: Commit Task 3**

```bash
git add pipeline/internal/capital_weekly/context/economic_sources \
  pipeline/internal/capital_weekly/context/economic_releases.py \
  pipeline/internal/capital_weekly/context/events.py \
  pipeline/internal/capital_weekly/context/providers.py \
  pipeline/internal/tests/test_capital_weekly_economic_*.py \
  pipeline/internal/tests/test_capital_weekly_events.py \
  pipeline/internal/tests/test_capital_weekly_context_providers.py \
  pipeline/internal/tests/test_capital_weekly_point_in_time.py \
  pipeline/internal/tests/test_capital_weekly_weekly_context.py
git commit -m "feat: register official economic releases"
```

---

### Task 4: Market State, Breadth, Positioning, and CFTC Classes

**Files:**
- Modify: `pipeline/internal/capital_weekly/context/market_internals.py`
- Modify: `pipeline/internal/capital_weekly/context/positioning.py`
- Modify: `pipeline/internal/capital_weekly/context/providers.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_market_internals.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_positioning.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_context_providers.py`

**Interfaces:**
- Consumes: `context.breadth_universe`, Yahoo-style histories, CFTC TFF and Disaggregated CSV captures, Sunday cutoff.
- Produces: `calculate_breadth`, `calculate_registered_universe_state`, `calculate_style_relative_windows`, `parse_cftc_disaggregated_csv`, and default providers `yahoo_market_state` and `cftc_disaggregated`.

- [ ] **Step 1: Add the pinned market-state and classification tests**

Keep explicit assertions for 20/50/200-session participation, advance/decline, 52-week highs/lows, RSP/SPY relative return, registered-universe labeling, commodity producer/merchant classification, report-release cutoff, change, and trailing percentile.

```python
self.assertEqual(result["universe_type"], "registered_sector_etf_proxy")
self.assertNotIn("historical_constituent_breadth", result)
self.assertEqual(disaggregated[0]["metric_code"], "GOLD_COT")
self.assertEqual(disaggregated[0]["classification"], "producer_merchant")
```

- [ ] **Step 2: Run focused tests and capture RED**

Run:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_market_internals \
  pipeline.internal.tests.test_capital_weekly_positioning \
  pipeline.internal.tests.test_capital_weekly_context_providers
```

Expected: missing market-state functions and no Disaggregated CFTC provider.

- [ ] **Step 3: Port market calculations and conservative labels**

Port the `56ed7ad` functions. Calculate on histories truncated to `end`; expose the universe as a current registered proxy set, not a historical-vintage index constituent set.

```python
eligible = frame.loc[frame.index.date <= end].copy()
if len(eligible) < 200:
    state["above_200d_ratio"] = None
```

Use `qc_flag="INSUFFICIENT_DATA"` when a metric's required lookback is absent.

- [ ] **Step 4: Split CFTC parsing by official report type**

```python
CFTC_URLS = {
    "tff": "https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip",
    "disaggregated": "https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip",
}
```

Build separate configs from `report_type`, require both classifications, and register `cftc_tff` plus `cftc_disaggregated`. Select only rows whose official release date is eligible by the target Sunday before calculating changes and percentiles.

- [ ] **Step 5: Register Yahoo market state with explicit optional failure provenance**

```python
"yahoo_market_state": ContextProvider(
    spec=ProviderSpec(
        name="yahoo_market_state", category="market_internals",
        source_tier="public", requiredness="optional",
        provider_version="1.0.0", schema_version="context-metric-v1",
        frequency="daily", freshness_days=7,
        failure_source="Yahoo Finance (registered sector ETF proxy universe)",
        failure_source_url=YAHOO_FINANCE_URL,
    ),
    fetch=lambda: _yahoo_market_state_provider(yahoo_download, end, breadth_universe),
)
```

- [ ] **Step 6: Run focused GREEN and commit**

Run the Step 2 command. Expected: PASS with proxy naming and CFTC classifications preserved.

```bash
git add pipeline/internal/capital_weekly/context/market_internals.py \
  pipeline/internal/capital_weekly/context/positioning.py \
  pipeline/internal/capital_weekly/context/providers.py \
  pipeline/internal/tests/test_capital_weekly_market_internals.py \
  pipeline/internal/tests/test_capital_weekly_positioning.py \
  pipeline/internal/tests/test_capital_weekly_context_providers.py
git commit -m "feat: add market state and cftc classes"
```

---

### Task 5: Auditable Public Fund Flows

**Files:**
- Create: `pipeline/internal/capital_weekly/context/public_flows.py`
- Create: `pipeline/internal/tests/test_capital_weekly_public_flows.py`
- Modify: `pipeline/internal/capital_weekly/context/providers.py`
- Modify: `pipeline/internal/capital_weekly/weekly_context.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_context_providers.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_weekly_context.py`

**Interfaces:**
- Consumes: issuer page text, HKEX daily Stock Connect text, two cutoff-eligible issuer observations.
- Produces: `parse_ishares_fund_page`, `calculate_etf_implied_flow`, `parse_hkex_stock_connect_daily`, provider category `fund_flows`, and `fund_flows.csv`.

- [ ] **Step 1: Add public-flow parser and integration tests**

Port the pinned parser tests and add a weekly-context empty-table assertion:

```python
self.assertEqual(tables["fund_flows"], [])
self.assertEqual(CATEGORY_FILES["fund_flows"], "fund_flows.csv")

with self.assertRaises(ValueError):
    calculate_etf_implied_flow(current_only, current_only)
```

- [ ] **Step 2: Run focused tests and capture RED**

Run:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_public_flows \
  pipeline.internal.tests.test_capital_weekly_weekly_context \
  pipeline.internal.tests.test_capital_weekly_context_providers
```

Expected: missing module/category/providers.

- [ ] **Step 3: Port parsers and restricted derivations**

Port `public_flows.py@56ed7ad`. Preserve these rules:

```python
if current["observation_date"] <= previous["observation_date"]:
    raise ValueError("issuer observations must be strictly ordered")
implied_flow = (
    current["net_assets"] - previous["net_assets"]
    - previous["net_assets"] * current["nav_return"]
)
```

Publish issuer NAV, net assets, and shares as dated facts. Publish ETF implied flow only with two ordered eligible observations. Publish HKEX Southbound buy, sell, turnover, and calculated net buy; omit Northbound net flow when the official source exposes only turnover.

- [ ] **Step 4: Register providers and table schema**

Register `ishares_ivv_fund` and `hkex_stock_connect_flows` as optional daily `fund_flows` providers with seven-day freshness. Add `fund_flows` to `CATEGORY_FILES` and `CATEGORY_FIELDS` using `METRIC_FIELDS`.

- [ ] **Step 5: Run focused GREEN and commit**

Run the Step 2 command. Expected: PASS; an empty flow table still serializes with its full header.

```bash
git add pipeline/internal/capital_weekly/context/public_flows.py \
  pipeline/internal/capital_weekly/context/providers.py \
  pipeline/internal/capital_weekly/weekly_context.py \
  pipeline/internal/tests/test_capital_weekly_public_flows.py \
  pipeline/internal/tests/test_capital_weekly_context_providers.py \
  pipeline/internal/tests/test_capital_weekly_weekly_context.py
git commit -m "feat: add auditable public flows"
```

---

### Task 6: Watchlist-Gated SEC Fundamentals and Capital Markets

**Files:**
- Create: `pipeline/internal/capital_weekly/context/fundamentals.py`
- Create: `pipeline/internal/capital_weekly/context/capital_markets.py`
- Create: `pipeline/internal/tests/test_capital_weekly_fundamentals.py`
- Create: `pipeline/internal/tests/test_capital_weekly_capital_markets.py`
- Modify: `pipeline/internal/capital_weekly/context/company_events.py`
- Modify: `pipeline/internal/capital_weekly/context/providers.py`
- Modify: `pipeline/internal/capital_weekly/weekly_context.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_company_events.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_context_providers.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_weekly_context.py`

**Interfaces:**
- Consumes: `context.company_watchlist`, SEC submissions/company facts/filing text, cutoff-eligible public price history, HKEX official listing HTML.
- Produces: typed `company_fundamentals` and `capital_markets` rows, their validators, and four default providers: `sec_company_fundamentals`, `sec_guidance_proxy`, `sec_capital_markets`, `hkex_capital_markets`.

- [ ] **Step 1: Add typed-contract, calculation, and event tests**

Port the pinned tests for standalone-quarter derivation, TTM metrics, margins, free cash flow, historical valuation percentiles, missing-input suppression, input-reference validation, SEC IPO forms, guidance-language proxy, 8-K M&A classification, cutoff exclusion, and HKEX source links.

Add the production-empty behavior:

```python
result = providers["sec_company_fundamentals"].fetch()
self.assertEqual(result.status, "NOT_CONFIGURED")
self.assertEqual(result.rows, [])
self.assertIn("watchlist is empty", result.notes.lower())
```

- [ ] **Step 2: Run focused tests and capture RED**

Run:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_fundamentals \
  pipeline.internal.tests.test_capital_weekly_capital_markets \
  pipeline.internal.tests.test_capital_weekly_company_events \
  pipeline.internal.tests.test_capital_weekly_context_providers \
  pipeline.internal.tests.test_capital_weekly_weekly_context
```

Expected: missing typed modules/categories/provider keys.

- [ ] **Step 3: Port fundamentals with auditable input references**

Port `fundamentals.py@56ed7ad` with package-path adaptation. Keep `FORMULA_VERSION = "fundamentals-v1"`; every derived row names all source record IDs. Suppress only the affected multiple when price, shares, debt, cash, earnings, EBITDA, or FCF is unavailable.

```python
if any(value is None for value in required_inputs):
    return None
return make_company_fundamental_row(
    calculation_id=calculation_id,
    formula_version=FORMULA_VERSION,
    input_record_ids="|".join(input_ids),
    **values,
)
```

- [ ] **Step 4: Port capital-market event contracts and parsers**

Port `capital_markets.py@56ed7ad`. SEC IPO activity is limited to S-1, F-1, and 424B4 records known by cutoff. Guidance and M&A remain filing-text proxies with explicit evidence labels. HKEX rows retain the official detail link and do not infer offering size.

- [ ] **Step 5: Add categories, validation, and provider registration**

Add `company_fundamentals.csv` using `COMPANY_FUNDAMENTAL_FIELDS` and `capital_markets.csv` using `CAPITAL_MARKET_FIELDS`. In `run_weekly_context`, normalize and validate these types before appending:

```python
if result.category == "company_fundamentals":
    rows = normalize_company_fundamental_rows(result.rows)
elif result.category == "capital_markets":
    rows = normalize_capital_market_rows(result.rows)
```

Run combined fundamental input-reference validation after all providers. Requiredness for `sec_company_fundamentals` is `optional` when the watchlist is empty and `required` when enabled rows exist.

- [ ] **Step 6: Run focused GREEN and commit**

Run the Step 2 command. Expected: PASS; production watchlist remains empty and all new collections remain present.

```bash
git add pipeline/internal/capital_weekly/context/fundamentals.py \
  pipeline/internal/capital_weekly/context/capital_markets.py \
  pipeline/internal/capital_weekly/context/company_events.py \
  pipeline/internal/capital_weekly/context/providers.py \
  pipeline/internal/capital_weekly/weekly_context.py \
  pipeline/internal/tests/test_capital_weekly_fundamentals.py \
  pipeline/internal/tests/test_capital_weekly_capital_markets.py \
  pipeline/internal/tests/test_capital_weekly_company_events.py \
  pipeline/internal/tests/test_capital_weekly_context_providers.py \
  pipeline/internal/tests/test_capital_weekly_weekly_context.py
git commit -m "feat: add watchlist gated sec data"
```

---

### Task 7: Capability Audit and Five-Domain Publication Contract

**Files:**
- Create: `pipeline/internal/capital_weekly/capabilities.py`
- Create: `pipeline/internal/tests/test_capital_weekly_capabilities.py`
- Modify: `pipeline/internal/capital_weekly/weekly_release.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_weekly_release.py`
- Modify: `pipeline/internal/tests/test_latest_json_output.py`
- Modify: `pipeline/internal/tests/test_offline_output_migration.py`

**Interfaces:**
- Consumes: staged release root, target Sunday, context provider source-log rows, exact business table evidence.
- Produces: `build_capability_manifest(release_root: Path, target_end: date) -> list[dict]`, dataset contract version 5, four added `context.json.tables` arrays, and a matching `release.json.capabilities` validation view.

- [ ] **Step 1: Add capability and publication tests**

Port the pinned capability registry tests and add stable JSON assertions:

```python
self.assertEqual(set(bundle), {
    "indices.json", "sectors.json", "gics.json",
    "macro.json", "context.json", "release.json",
})
self.assertTrue({
    "fund_flows", "company_fundamentals", "capital_markets",
    "capability_audit",
}.issubset(context_document["tables"]))
self.assertIsInstance(context_document["tables"]["fund_flows"], list)
self.assertEqual(
    context_document["tables"]["capability_audit"],
    release_document["capabilities"],
)
self.assertEqual(len(release_document["business_files"]), 5)
```

Capability evidence assertion:

```python
row = next(item for item in manifest if item["capability_id"] == capability_id)
self.assertIn(row["status"], {
    "available", "failed", "not_configured",
    "unavailable_licensed", "not_applicable",
})
self.assertTrue(row["reason"])
```

- [ ] **Step 2: Run publication tests and capture RED**

Run:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_capabilities \
  pipeline.internal.tests.test_capital_weekly_weekly_release \
  pipeline.internal.tests.test_latest_json_output \
  pipeline.internal.tests.test_offline_output_migration
```

Expected: missing capability module, absent context tables, and older dataset contract.

- [ ] **Step 3: Port capability evidence rules**

Port `capabilities.py@56ed7ad` and adapt path discovery to `pipeline/internal` staging. A capability becomes `available` only if its exact registered table rows are eligible by cutoff; module presence and empty tables do not count.

```python
if _matches(spec.evidence, eligible_rows):
    status, reason = "available", "eligible release evidence is present"
else:
    status, reason = _missing_status(spec, provider_status)
```

Raw-cache filenames cannot satisfy a business-table evidence rule.

- [ ] **Step 4: Extend the current release contract without adding a sixth domain**

Advance the dataset contract through source-compatible version constants to version 5. Add the three provider-produced context CSVs to current `RELEASE_DATASETS` and `OUTPUT_TABLES["context"]`; preserve all older supported contract versions for offline migration. After staged CSV validation, compute the capability rows once, inject the same rows into `context.json.tables.capability_audit`, and add them to the release manifest:

```python
capabilities = build_capability_manifest(release_root, window.end)
context_document["tables"]["capability_audit"] = capabilities
manifest["capabilities"] = capabilities
```

Update optional-source policies for the new providers. Enforce exact typed columns for fundamentals and capital markets, valid dates/timestamps/source URLs/QC flags, capability-state consistency between `context.json` and `release.json`, and empty-array preservation in JSON.

- [ ] **Step 5: Verify migration remains offline and stable hashes remain five-file**

The migration tests must supply a validated legacy source tree with manifest hashes and monkeypatch every runner to raise if invoked. Assert the converted `release.json` names the source release identity and lists only the five stable business files.

- [ ] **Step 6: Run focused GREEN and commit**

Run the Step 2 command. Expected: PASS for current and legacy dataset contracts.

```bash
git add pipeline/internal/capital_weekly/capabilities.py \
  pipeline/internal/capital_weekly/weekly_release.py \
  pipeline/internal/tests/test_capital_weekly_capabilities.py \
  pipeline/internal/tests/test_capital_weekly_weekly_release.py \
  pipeline/internal/tests/test_latest_json_output.py \
  pipeline/internal/tests/test_offline_output_migration.py
git commit -m "feat: publish public capability audit"
```

---

### Task 8: Full Verification, Stable Output Audit, and Handoff Evidence

**Files:**
- Modify only if verification exposes an integration-owned defect: files already listed in Tasks 1-7.
- Do not modify: `output/`, the untracked audit document, or `.worktrees/commodity-research-backend`.

**Interfaces:**
- Consumes: all Task 1-7 commits and the pre-existing stable output bundle.
- Produces: full test evidence, stable output validation, unchanged release identity, repository-scope audit, and final integration commit list.

- [ ] **Step 1: Record immutable identities before final verification**

```bash
git rev-parse HEAD
git status --short
python3 - <<'PY'
import json
from pathlib import Path
release = json.loads(Path("output/release.json").read_text())
print(release.get("release_id"))
print(release.get("as_of_date"))
print(release.get("source_release"))
PY
```

Expected stable identity: `20260828T060805+0800-5830b4`, `as_of_date` `2026-08-23`, source week `week_20260817-20260823`.

- [ ] **Step 2: Run every Python test**

Run:

```bash
python3 -m unittest -v
```

Expected: all tests PASS with no network refresh.

- [ ] **Step 3: Run workbook compatibility tests**

Run:

```bash
node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs
```

Expected: PASS.

- [ ] **Step 4: Validate the active stable output bundle**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
from pipeline.internal.capital_weekly.weekly_release import validate_output_bundle

validate_output_bundle(Path("output"))
print("active output bundle valid")
PY
```

Expected: `active output bundle valid`.

- [ ] **Step 5: Prove the active output was not refreshed**

Re-read `output/release.json` and compare its release ID, as-of date, source week, and business-file hashes to Step 1. Expected: byte identities unchanged.

- [ ] **Step 6: Audit repository boundaries and unrelated work**

```bash
git status --short
find . -maxdepth 1 -mindepth 1 -not -name .git -not -name .worktrees -print
git -C .worktrees/commodity-research-backend status --short
```

Expected: only `./pipeline` and `./output` are visible product directories; the untracked audit and commodity worktree status match their pre-integration state.

- [ ] **Step 7: Create a recoverable cleanup archive only if integration-owned temporary files exist**

If verification created task-owned scratch files, move those exact files into a timestamped directory under `pipeline/.cache/integration-cleanup/` and record the path. Do not move user-owned dirty or untracked files. If no scratch files exist, record `cleanup archive: not needed`.

- [ ] **Step 8: Record final handoff**

Report:

```text
source functional reference: codex/public-green-data-pipeline@56ed7ad
target behavior baseline: main@104572b
task commit SHAs: copy the seven hashes printed by `git log --reverse --format='%H %s' 104572b..HEAD`
files created/modified/deleted: copy `git diff --name-status 104572b..HEAD`
RED evidence: copy the recorded focused failure commands and their first causal failure
GREEN evidence: copy each focused pass plus the full Python and Node summaries
offline conversion source: none used during integration
stable output identity: 20260828T060805+0800-5830b4 / 2026-08-23
cleanup archive: report the exact archive directory printed in Step 7, or `not needed`
remaining compatibility risks: public endpoints remain subject to future format changes; no live refresh was run; production SEC watchlist remains empty
```
