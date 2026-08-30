# Commodity Research Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish official-source commodity prices, physical fundamentals, and correctly classified CFTC positioning for natural gas, refined products, copper, gold, and agriculture through the existing stable `macro.json` and `context.json` files.

**Architecture:** Preserve the five acquisition domains and atomic stable release. Add an explicit `commodity_code` contract across canonical macro prices and context metrics, split CFTC financial and physical-commodity report semantics, and implement small provider modules for EIA, World Bank, CME/COMEX, USDA, and optional USGS/NASS data. Every provider enforces observation and known-as-of cutoffs before calculations.

**Tech Stack:** Python 3, pandas, requests, openpyxl, unittest; JSON stable release with SHA-256 manifests.

**Spec:** `pipeline/internal/docs/superpowers/specs/2026-08-30-commodity-research-database-design.md`

## Global Constraints

- Work in `/Users/a1-6/Documents/market data` and preserve unrelated files.
- Keep exactly `indices.json`, `sectors.json`, `gics.json`, `macro.json`, `context.json`, and `release.json` in `output/`.
- `pipeline/config.json` is the only production configuration source.
- Prices belong to macro; fundamentals and positioning belong to context.
- New Commodity Research values use free official sources only.
- Apply `as_of_date` and `known_as_of` before every selection or calculation.
- Preserve source-native units; unknown units fail closed.
- Missing values are `null`, never zero, empty strings, NaN, or Infinity.
- A required-provider failure never replaces the previous complete stable output.
- Keep one latest successful raw-cache generation under `pipeline/.cache/`.
- Automated tests are deterministic and do not access the network.
- Each production change follows RED, GREEN, refactor, focused tests, and a task-scoped commit.

---

## Planned File Structure

- Modify `pipeline/config.json`: commodity taxonomy, official price definitions, CFTC report families, and official-provider series.
- Modify `pipeline/internal/capital_weekly/macro_assets.py`: additive macro taxonomy and official price dispatch.
- Create `pipeline/internal/capital_weekly/commodity_prices.py`: pure EIA and World Bank price parsers.
- Modify `pipeline/internal/capital_weekly/context/common.py`: additive context composition fields.
- Modify `pipeline/internal/capital_weekly/weekly_context.py`: publish the additive context schema.
- Modify `pipeline/internal/capital_weekly/context/positioning.py`: separate TFF and Disaggregated CFTC parsers.
- Create `pipeline/internal/capital_weekly/context/eia_commodities.py`: EIA physical-series parsing and calculations.
- Create `pipeline/internal/capital_weekly/context/metal_inventories.py`: COMEX copper and gold workbook parsing.
- Create `pipeline/internal/capital_weekly/context/usda_commodities.py`: USDA lookup, PSD, ESR, and stock-to-use logic.
- Modify `pipeline/internal/capital_weekly/context/providers.py`: provider transports and registry only.
- Modify `pipeline/internal/capital_weekly/weekly_release.py`: additive columns, provider-status policies, and cross-domain commodity validation.
- Modify focused tests under `pipeline/internal/tests/` and the config hash fixture.

---

### Task 1: Add the additive commodity composition contract

**Files:**

- Modify: `pipeline/config.json`
- Modify: `pipeline/internal/capital_weekly/macro_assets.py`
- Modify: `pipeline/internal/capital_weekly/context/common.py`
- Modify: `pipeline/internal/capital_weekly/context/providers.py`
- Modify: `pipeline/internal/capital_weekly/weekly_context.py`
- Modify: `pipeline/internal/capital_weekly/weekly_release.py`
- Test: `pipeline/internal/tests/test_pipeline_config.py`
- Test: `pipeline/internal/tests/test_capital_weekly_macro_assets.py`
- Test: `pipeline/internal/tests/test_capital_weekly_weekly_context.py`
- Test: `pipeline/internal/tests/test_capital_weekly_weekly_release.py`

**Interfaces:**

- Extends `MacroAssetConfig` with `commodity_code`, `commodity_family`, `price_kind`, `known_as_of`, and `provider_route`, defaulting to empty strings for unrelated rows.
- Extends context metric rows with `commodity_code`, `commodity_family`, `metric_role`, `measurement_kind`, `participant_class`, `known_as_of`, and `reference_period`, defaulting to `None` for unrelated rows.
- Produces `metric_rows(..., metadata: Mapping[str, Any] | None = None)`.
- Preserves existing series and metric codes.

- [ ] **Step 1: Write failing additive-schema tests**

Add assertions that a commodity macro config preserves its taxonomy while a fixed-income row receives empty defaults:

```python
universe = load_macro_asset_universe()
wti = next(row for row in universe if row.series_code == "WTI")
self.assertEqual(wti.commodity_code, "WTI")
self.assertEqual(wti.commodity_family, "refined_products")
self.assertEqual(wti.price_kind, "official_cash")
self.assertEqual(
    next(row for row in universe if row.series_code == "UST2Y").commodity_code,
    "",
)
```

Add a context normalization test that passes an old-format metric row and expects every new field to exist with `None`. Add a publisher test that the `commodity_fundamentals.csv` and `positioning_flows.csv` headers include the seven new fields. Add staged-release tests that reject a nonempty Commodity Research row without `commodity_code` or with an unsupported family.

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_macro_assets \
  pipeline.internal.tests.test_capital_weekly_weekly_context \
  pipeline.internal.tests.test_capital_weekly_weekly_release
```

Expected: failures name missing dataclass arguments or missing CSV fields.

- [ ] **Step 3: Implement additive defaults and schema publication**

Add after the existing optional `MacroAssetConfig` fields:

```python
commodity_code: str = ""
commodity_family: str = ""
price_kind: str = ""
known_as_of: str = ""
provider_route: str = ""
```

In `normalize_metric_rows`, call `row.setdefault(field, None)` for every field in:

```python
COMMODITY_METRIC_FIELDS = (
    "commodity_code",
    "commodity_family",
    "metric_role",
    "measurement_kind",
    "participant_class",
    "known_as_of",
    "reference_period",
)
```

Define `METRIC_FIELDS` as the existing base tuple plus `COMMODITY_METRIC_FIELDS`. Extend `metric_rows` with a `metadata` mapping and merge only keys registered in `COMMODITY_METRIC_FIELDS`.

- [ ] **Step 4: Add initial taxonomy without activating new feeds**

Set existing records as follows:

```text
WTI          commodity_code=WTI          family=refined_products
BRENT        commodity_code=BRENT        family=refined_products
COMEX_GOLD   commodity_code=GOLD_COMEX   family=gold
BTC_USD      commodity_code=BTC_USD      family=digital_asset
```

Set `price_kind=official_cash` for WTI/BRENT only after Task 3 changes their providers; until then retain their factual `vendor_proxy` label. `digital_asset` is valid in macro but excluded from Commodity Research cross-file requirements.

- [ ] **Step 5: Update release columns and validation**

Add the macro fields to `MACRO_COLUMNS`, add the context fields through `CATEGORY_FIELDS`, and validate Commodity Research families against:

```python
COMMODITY_RESEARCH_FAMILIES = frozenset({
    "natural_gas",
    "refined_products",
    "copper",
    "gold",
    "grains_oilseeds",
    "softs",
    "livestock",
})
```

Rows whose family is `digital_asset` remain valid macro rows but do not satisfy Commodity Research coverage.

- [ ] **Step 6: Update the exact config hash and run GREEN**

Recalculate only the intended `macro` and `context` hashes in `test_pipeline_config.py`. Run the focused command from Step 2, then:

```bash
python3 -m unittest -v pipeline.internal.tests.test_pipeline_config
```

Expected: all focused tests pass.

- [ ] **Step 7: Commit Task 1**

```bash
git add pipeline/config.json pipeline/internal/capital_weekly/macro_assets.py pipeline/internal/capital_weekly/context/common.py pipeline/internal/capital_weekly/context/providers.py pipeline/internal/capital_weekly/weekly_context.py pipeline/internal/capital_weekly/weekly_release.py pipeline/internal/tests/test_pipeline_config.py pipeline/internal/tests/test_capital_weekly_macro_assets.py pipeline/internal/tests/test_capital_weekly_weekly_context.py pipeline/internal/tests/test_capital_weekly_weekly_release.py
git commit -m "feat: add commodity composition contract"
```

---

### Task 2: Correct CFTC commodity positioning semantics

**Files:**

- Modify: `pipeline/config.json`
- Modify: `pipeline/internal/capital_weekly/context/positioning.py`
- Modify: `pipeline/internal/capital_weekly/context/providers.py`
- Test: `pipeline/internal/tests/test_capital_weekly_positioning.py`
- Test: `pipeline/internal/tests/test_capital_weekly_context_providers.py`
- Test: `pipeline/internal/tests/test_pipeline_config.py`

**Interfaces:**

- Preserves `parse_cftc_tff_csv(text, contract_codes)` for DXY and S&P 500.
- Produces `parse_cftc_disaggregated_csv(text, contracts) -> list[dict]` for physical commodities.
- Produces `cftc_known_as_of(report_date: date) -> str` using Friday 15:30 America/New_York converted to an offset timestamp.
- Emits `open_interest`, `producer_net`, `swap_dealer_net`, `managed_money_net`, `other_reportable_net`, weekly changes, and configured percentiles.

- [ ] **Step 1: Add a failing Disaggregated parser fixture**

Use a deterministic CSV with official long-format columns:

```text
Market_and_Exchange_Names,CFTC_Contract_Market_Code,Report_Date_as_YYYY-MM-DD,Open_Interest_All,Prod_Merc_Positions_Long_All,Prod_Merc_Positions_Short_All,Swap_Positions_Long_All,Swap__Positions_Short_All,M_Money_Positions_Long_All,M_Money_Positions_Short_All,Other_Rept_Positions_Long_All,Other_Rept_Positions_Short_All
GOLD - COMMODITY EXCHANGE INC.,088691,2026-08-18,500000,100000,200000,120000,70000,250000,100000,30000,20000
```

Assert the result has `managed_money_net == 150000`, `producer_net == -100000`, `swap_dealer_net == 50000`, a Friday release timestamp, and the configured `commodity_code`.

- [ ] **Step 2: Add failing cutoff and report-family tests**

Assert a Tuesday row is excluded for an `as_of_date` before its Friday release, included on the following Sunday, and never parsed with TFF `asset_manager` semantics. Assert an absent configured code raises `ValueError("CFTC response contained no configured contracts")`.

- [ ] **Step 3: Run RED**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_positioning \
  pipeline.internal.tests.test_capital_weekly_context_providers
```

Expected: import or missing-function failure for `parse_cftc_disaggregated_csv`.

- [ ] **Step 4: Implement the separate parser and normalized rows**

Use explicit required columns for the four participant classes. Calculate net as long minus short. Sort by `(commodity_code, report_date)`, calculate changes only against the previous report for the same contract, and calculate percentiles over configured history with a declared window and minimum observation count.

Emit one context metric row per measurement with:

```python
metadata={
    "commodity_code": spec["commodity_code"],
    "commodity_family": spec["commodity_family"],
    "metric_role": "positioning",
    "measurement_kind": measurement_kind,
    "participant_class": participant_class,
    "known_as_of": observation["known_as_of"],
    "reference_period": observation["report_date"].isoformat(),
}
```

- [ ] **Step 5: Split providers by report family**

Keep the existing TFF annual archive for DXY/SP500. Fetch the official CFTC Disaggregated Futures Only CSV/Socrata dataset for commodity contracts. Provider definitions become `cftc_tff` and `cftc_disaggregated`; both remain required when their contract list is nonempty.

- [ ] **Step 6: Activate the verified contract map**

Configure these official CFTC codes and families:

```text
023651 NATGAS_HH      natural_gas
067651 WTI            refined_products
111659 RBOB_US        refined_products
022651 ULSD_US        refined_products
085692 COPPER_COMEX   copper
088691 GOLD_COMEX     gold
002602 CORN           grains_oilseeds
005602 SOYBEANS       grains_oilseeds
001602 WHEAT          grains_oilseeds
039601 RICE           grains_oilseeds
033661 COTTON         softs
080732 SUGAR          softs
083731 COFFEE         softs
073732 COCOA          softs
057642 CATTLE         livestock
054642 HOGS           livestock
```

The provider must verify every code against the returned market name before publication; a mismatched or absent code fails closed.

- [ ] **Step 7: Run GREEN and commit**

Run the focused tests, config tests, and:

```bash
python3 -m unittest -v pipeline.internal.tests.test_capital_weekly_weekly_context
```

Then commit:

```bash
git add pipeline/config.json pipeline/internal/capital_weekly/context/positioning.py pipeline/internal/capital_weekly/context/providers.py pipeline/internal/tests/test_capital_weekly_positioning.py pipeline/internal/tests/test_capital_weekly_context_providers.py pipeline/internal/tests/test_pipeline_config.py
git commit -m "feat: add official commodity positioning"
```

---

### Task 3: Replace commodity vendor prices with official price adapters

**Files:**

- Create: `pipeline/internal/capital_weekly/commodity_prices.py`
- Modify: `pipeline/internal/capital_weekly/macro_assets.py`
- Modify: `pipeline/config.json`
- Test: `pipeline/internal/tests/test_capital_weekly_commodity_prices.py`
- Test: `pipeline/internal/tests/test_capital_weekly_macro_assets.py`
- Test: `pipeline/internal/tests/test_pipeline_config.py`

**Interfaces:**

- Produces `parse_eia_price_series(text, series_code, expected_unit) -> list[dict]`.
- Produces `parse_world_bank_monthly_prices(content, columns) -> dict[str, list[dict]]`.
- Adds macro providers `eia_v2` and `world_bank_pink_sheet`.
- Retains source workbook/response bytes in the macro raw cache.

- [ ] **Step 1: Write failing EIA and World Bank parser tests**

Use an EIA JSON fixture with `period`, `series`, `series-description`, `unit`/`units`, and `value`. Assert date ordering, exact series filtering, unit validation, and rejection of duplicates/nonfinite values.

Build a small in-memory OOXML fixture with the Pink Sheet layout: metadata rows, a `Monthly Prices` heading, a date column, and `Natural gas, US`, `Crude oil, WTI`, `Crude oil, Brent`, `Copper`, `Gold`, `Maize`, `Soybeans`, `Wheat, US SRW`, `Rice, Thai 5%`, `Cotton, A Index`, `Sugar, world`, `Coffee, Arabica`, `Cocoa`, and `Beef` columns. Assert the parser returns only finite dated observations and preserves workbook units.

- [ ] **Step 2: Run RED**

```bash
python3 -m unittest -v pipeline.internal.tests.test_capital_weekly_commodity_prices
```

Expected: module import failure.

- [ ] **Step 3: Implement pure parsers**

`parse_world_bank_monthly_prices` finds the header by normalized exact labels, not column position; parses dates as month-end observation dates; rejects a missing requested column; and returns source-native values without converting monthly benchmarks into daily prices.

- [ ] **Step 4: Add macro provider dispatch and per-source fetch reuse**

`eia_v2` uses `provider_route` plus `provider_symbol`. `world_bank_pink_sheet` discovers the current official monthly workbook link from the World Bank commodity page, downloads it once per refresh, and reuses the parsed workbook for all configured price columns. Discovery must accept only an HTTPS World Bank host and a link labeled as monthly historical prices.

- [ ] **Step 5: Replace requested commodity price sources**

Replace WTI, Brent, and COMEX Gold vendor definitions with EIA or World Bank official sources. Add official entries for Henry Hub, copper, and the agriculture benchmark columns listed in Step 1. Keep BTC unchanged and excluded through `commodity_family=digital_asset`.

Every new price row declares `price_kind=official_cash` for EIA or `official_monthly_benchmark` for World Bank. No requested Commodity Research row retains `provider=yahoo_chart`.

- [ ] **Step 6: Add as-of and atomicity tests**

Assert observations after `as_of_date` are removed before return calculation; a monthly series uses the latest month on or before the cutoff; a requested missing workbook column fails that series; and any required macro source failure prevents publishing a partial macro bundle.

- [ ] **Step 7: Run GREEN and commit**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_commodity_prices \
  pipeline.internal.tests.test_capital_weekly_macro_assets \
  pipeline.internal.tests.test_capital_weekly_macro_as_of \
  pipeline.internal.tests.test_pipeline_config
```

Commit only Task 3 files:

```bash
git add pipeline/config.json pipeline/internal/capital_weekly/commodity_prices.py pipeline/internal/capital_weekly/macro_assets.py pipeline/internal/tests/test_capital_weekly_commodity_prices.py pipeline/internal/tests/test_capital_weekly_macro_assets.py pipeline/internal/tests/test_pipeline_config.py
git commit -m "feat: source official commodity prices"
```

---

### Task 4: Expand EIA natural-gas and refined-product fundamentals

**Files:**

- Create: `pipeline/internal/capital_weekly/context/eia_commodities.py`
- Modify: `pipeline/internal/capital_weekly/context/commodities.py`
- Modify: `pipeline/internal/capital_weekly/context/providers.py`
- Modify: `pipeline/config.json`
- Modify: `pipeline/internal/capital_weekly/weekly_release.py`
- Test: `pipeline/internal/tests/test_capital_weekly_commodities.py`
- Test: `pipeline/internal/tests/test_capital_weekly_context_providers.py`
- Test: `pipeline/internal/tests/test_capital_weekly_weekly_release.py`
- Test: `pipeline/internal/tests/test_pipeline_config.py`

**Interfaces:**

- Produces `parse_eia_metric_series(text, spec) -> list[dict]`.
- Produces `latest_and_changes(rows, cutoff) -> list[dict]`.
- Registers independent providers `eia_natural_gas` and `eia_refined_products`.

- [ ] **Step 1: Write failing route, unit, and cutoff tests**

Use one fixture per route shape. Assert exact facet matching, source description and unit validation, duplicate-period rejection, cutoff before selection, and no future record leakage. Assert weekly changes use the latest two eligible observations, not the first two returned by the API.

- [ ] **Step 2: Write failing family-isolation and credential tests**

With no `EIA_API_KEY`, expect two separate `NOT_CONFIGURED` results. With a configured key and a natural-gas transport failure, assert refined products still produce their deterministic result but the required natural-gas provider status blocks stable replacement.

- [ ] **Step 3: Run RED**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_commodities \
  pipeline.internal.tests.test_capital_weekly_context_providers
```

Expected: missing provider/module failures.

- [ ] **Step 4: Implement generic EIA parsing and calculations**

Each config row contains `provider`, `commodity_code`, `commodity_family`, `route`, `frequency`, `facets`, `metric_code`, `metric_name`, `measurement_kind`, `expected_unit`, and `freshness_days`. Build query parameters from the config facet object; do not concatenate unescaped facet values.

Emit source-native level rows plus registered `_change` and `_change_pct` rows. Seasonal deviation is emitted only when at least five prior same-week observations exist and declares `formula_version=eia-seasonal-v1` in `reference_period` or calculation metadata.

- [ ] **Step 5: Configure the full energy metric set**

Natural gas covers Henry Hub context, Lower-48/regional working gas, weekly storage change, dry production, sector consumption, and LNG trade where the official route is active.

Refined products cover crude excluding SPR, gasoline, distillate, jet fuel and propane stocks; refinery utilization and crude inputs; production, product supplied, imports, and exports for gasoline, distillate, and jet fuel where EIA publishes the series.

At startup, validate configured series against the official EIA facet metadata and exact expected unit. A missing configured series is a provider failure.

- [ ] **Step 6: Register failure policies and cross-file coverage**

Replace the one `eia_commodities` allowlist with the two provider names. When the EIA key is present, mark both required; without the key, mark optional and allow only `NOT_CONFIGURED`. Staged release validation requires at least one physical-fundamental row for both active families.

- [ ] **Step 7: Run GREEN and commit**

Run focused tests plus weekly release tests, then commit:

```bash
git add pipeline/config.json pipeline/internal/capital_weekly/context/eia_commodities.py pipeline/internal/capital_weekly/context/commodities.py pipeline/internal/capital_weekly/context/providers.py pipeline/internal/capital_weekly/weekly_release.py pipeline/internal/tests/test_capital_weekly_commodities.py pipeline/internal/tests/test_capital_weekly_context_providers.py pipeline/internal/tests/test_capital_weekly_weekly_release.py pipeline/internal/tests/test_pipeline_config.py
git commit -m "feat: expand official energy fundamentals"
```

---

### Task 5: Add COMEX and USGS metals fundamentals

**Files:**

- Create: `pipeline/internal/capital_weekly/context/metal_inventories.py`
- Modify: `pipeline/internal/capital_weekly/context/providers.py`
- Modify: `pipeline/config.json`
- Modify: `pipeline/internal/capital_weekly/weekly_release.py`
- Test: `pipeline/internal/tests/test_capital_weekly_metal_inventories.py`
- Test: `pipeline/internal/tests/test_capital_weekly_context_providers.py`
- Test: `pipeline/internal/tests/test_capital_weekly_weekly_release.py`
- Test: `pipeline/internal/tests/test_pipeline_config.py`

**Interfaces:**

- Produces `parse_comex_stocks(content: bytes, spec) -> list[dict]`.
- Registers `comex_copper_stocks` and `comex_gold_stocks` as supplemental independent providers.
- Emits `registered`, `eligible`, and `total` inventory with the workbook report date.

- [ ] **Step 1: Write failing workbook parser tests**

Build deterministic `.xlsx` fixtures with report date, depository rows, registered stock, eligible stock, totals, and unit labels. Assert exact total reconciliation, rejection of changed headers/units, finite values, and report-date extraction. Add a legacy binary `.xls` fixture only if the production CME URL still returns BIFF; otherwise reject non-OOXML content with a factual schema error.

- [ ] **Step 2: Run RED**

```bash
python3 -m unittest -v pipeline.internal.tests.test_capital_weekly_metal_inventories
```

Expected: module import failure.

- [ ] **Step 3: Implement parsing and provenance**

The parser preserves source unit, inventory type, report date, and all rows needed to recompute totals. The provider raw cache stores exact bytes; the weekly source log records URL, byte count, SHA-256, and schema signature in notes. Copper rows use `measurement_kind=inventory` and a factual limitation note `deliverable_inventory_proxy; LME not included`.

- [ ] **Step 4: Add optional USGS structural context**

Parse only an official current USGS table whose publication date is no more than 400 days before the target Sunday. Emit annual mine production and reserves with `measurement_kind=structural`. If the current table cannot be parsed or the monthly survey remains paused, publish no row and a supplemental source-log status; never carry the old survey forward as current.

- [ ] **Step 5: Register supplemental failure behavior**

CME and USGS failures do not block unrelated core families, but they publish no partial rows. Add explicit optional status allowlists. Release validation still requires World Bank price and CFTC positioning for active copper and gold.

- [ ] **Step 6: Run GREEN and commit**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_metal_inventories \
  pipeline.internal.tests.test_capital_weekly_context_providers \
  pipeline.internal.tests.test_capital_weekly_weekly_release \
  pipeline.internal.tests.test_pipeline_config
```

Commit:

```bash
git add pipeline/config.json pipeline/internal/capital_weekly/context/metal_inventories.py pipeline/internal/capital_weekly/context/providers.py pipeline/internal/capital_weekly/weekly_release.py pipeline/internal/tests/test_capital_weekly_metal_inventories.py pipeline/internal/tests/test_capital_weekly_context_providers.py pipeline/internal/tests/test_capital_weekly_weekly_release.py pipeline/internal/tests/test_pipeline_config.py
git commit -m "feat: add official metals inventories"
```

---

### Task 6: Add USDA agriculture supply, trade, and positioning coverage

**Files:**

- Create: `pipeline/internal/capital_weekly/context/usda_commodities.py`
- Modify: `pipeline/internal/capital_weekly/context/providers.py`
- Modify: `pipeline/config.json`
- Modify: `pipeline/internal/capital_weekly/weekly_release.py`
- Test: `pipeline/internal/tests/test_capital_weekly_usda_commodities.py`
- Test: `pipeline/internal/tests/test_capital_weekly_context_providers.py`
- Test: `pipeline/internal/tests/test_capital_weekly_weekly_release.py`
- Test: `pipeline/internal/tests/test_pipeline_config.py`

**Interfaces:**

- Produces `parse_usda_lookup(payload, key_fields) -> dict`.
- Produces `parse_psd_records(payload, spec, cutoff) -> list[dict]`.
- Produces `parse_esr_records(payload, spec, cutoff) -> list[dict]`.
- Produces `calculate_stock_to_use(records) -> dict | None`.
- Registers independent `usda_psd` and `usda_esr` providers.

- [ ] **Step 1: Write failing lookup and revision-vintage tests**

Use fixtures for commodity, attribute, country, unit, and release-date lookups. Assert the configured display name resolves to one exact official code; duplicate or absent matches fail. Use two PSD releases that revise the same market year and assert only the release known by the target Sunday is selected.

- [ ] **Step 2: Write failing PSD, ESR, unit, and calculation tests**

Assert PSD emits production, beginning/ending stocks, imports, exports, domestic use, and supported feed/crush/industrial attributes with source-native units. Assert ESR emits weekly net sales, exports, and outstanding sales only when its release timestamp is eligible. Assert stock-to-use uses matching release vintage and unit and returns `None` for a zero/missing denominator.

- [ ] **Step 3: Run RED**

```bash
python3 -m unittest -v pipeline.internal.tests.test_capital_weekly_usda_commodities
```

Expected: module import failure.

- [ ] **Step 4: Implement credential and lookup handling**

Without `USDA_API_KEY`, return separate `NOT_CONFIGURED` results for PSD and ESR. With a key, fetch and cache official lookup responses first, resolve configured commodity/attribute/unit identities, then fetch only configured commodity/market-year combinations. Do not log or persist the key.

- [ ] **Step 5: Configure agriculture groups**

Configure:

```text
grains_oilseeds: CORN, SOYBEANS, WHEAT, RICE
softs: COTTON, SUGAR, COFFEE, COCOA
livestock: CATTLE/BEEF, HOGS/PORK
```

Use world aggregates plus a short configured list of key countries where PSD provides them. ESR rows are enabled only for commodities returned by the ESR commodity lookup. NASS cattle/hog detail remains supplemental and is added only through a stable machine-readable official release.

- [ ] **Step 6: Register conditional requiredness and release coverage**

With the USDA key configured, PSD and ESR become required for the configured eligible subsets; without it, only `NOT_CONFIGURED` is accepted. Release validation checks each active agriculture subsection has a capability status and rejects missing configured `commodity_code` rows.

- [ ] **Step 7: Run GREEN and commit**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_usda_commodities \
  pipeline.internal.tests.test_capital_weekly_context_providers \
  pipeline.internal.tests.test_capital_weekly_weekly_release \
  pipeline.internal.tests.test_pipeline_config
```

Commit:

```bash
git add pipeline/config.json pipeline/internal/capital_weekly/context/usda_commodities.py pipeline/internal/capital_weekly/context/providers.py pipeline/internal/capital_weekly/weekly_release.py pipeline/internal/tests/test_capital_weekly_usda_commodities.py pipeline/internal/tests/test_capital_weekly_context_providers.py pipeline/internal/tests/test_capital_weekly_weekly_release.py pipeline/internal/tests/test_pipeline_config.py
git commit -m "feat: add official agriculture fundamentals"
```

---

### Task 7: Verify publication, cache, and live official-source behavior

**Files:**

- Modify: `README.md`
- Modify only if a verified official source requires a factual config correction: `pipeline/config.json`
- Test: `pipeline/internal/tests/test_latest_json_output.py`
- Test: `pipeline/internal/tests/test_capital_weekly_weekly_release.py`

**Interfaces:**

- Proves the expanded stable JSON contract, atomic rollback, and one-cache policy.
- Produces a complete real weekly release when every configured required credential is available.

- [ ] **Step 1: Add failing end-to-end fixture assertions**

Build a deterministic five-pipeline staged fixture containing every requested family. Assert `validate_output_bundle` reports five complete pipelines and that every Commodity Research macro/context row has a supported exact `commodity_code`, HTTP(S) source, observation date, finite-or-null value, and valid QC. Assert BTC is excluded from research coverage.

- [ ] **Step 2: Add rollback and cache-generation assertions**

Run the coordinator with a fake required commodity provider failure. Assert all six existing output files retain their prior hashes. Run a succeeding fake release twice and assert `pipeline/.cache/` contains only the latest stable cache files and no dated generation directory.

- [ ] **Step 3: Run fixture GREEN**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_latest_json_output \
  pipeline.internal.tests.test_capital_weekly_weekly_release
```

- [ ] **Step 4: Run the full deterministic backend suite**

```bash
python3 -m unittest -v
node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs
```

Expected: all tests pass without network access.

- [ ] **Step 5: Run authorized official-source smoke probes**

Probe one configured series or workbook per provider using production parsers without publishing. Print only source URL, HTTP status, parsed row count, latest eligible observation date, units, and provider status; never print API keys. Correct only a factually changed official identifier or schema and rerun its focused RED/GREEN tests.

- [ ] **Step 6: Run the real refresh**

If `USDA_API_KEY` is absent, document USDA as `NOT_CONFIGURED` and continue only if the approved conditional policy accepts it. Run:

```bash
python3 -m pipeline.refresh --as-of-date 2026-08-23
```

Expected: either a complete atomic release or a factual required-provider failure that leaves the previous release unchanged. Do not weaken validation to force publication.

- [ ] **Step 7: Validate the active output and stable layout**

Run `validate_output_bundle(Path("output"))`, list direct output files, inspect source status counts, and inspect `pipeline/.cache/` direct children. Expected: six stable files, no dated output directory, all required providers `OK`, explicitly allowed optional statuses only, and one latest cache layout.

- [ ] **Step 8: Document operation and commit**

Document `USDA_API_KEY`, official-source limitations, Commodity Research taxonomy, and failure behavior in README. Commit only the documentation, final deterministic tests, and any verified config correction:

```bash
git add README.md pipeline/config.json pipeline/internal/tests/test_latest_json_output.py pipeline/internal/tests/test_capital_weekly_weekly_release.py
git commit -m "docs: document commodity research refresh"
```

---

## Backend Plan Verification Checklist

- Every design source has a provider or an explicit supplemental/unavailable rule.
- Every requested family has price, physical, and positioning capability coverage.
- CFTC TFF and Disaggregated semantics never share participant labels.
- Every data selection enforces observation and known-as-of cutoffs.
- New fields are additive and keep existing stable output filenames.
- Requiredness, optional status, and credential behavior are explicit.
- All tasks contain focused RED/GREEN commands and task-scoped commits.
