# 677-Item Public Financial Data Universe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the attached 677-item research universe into an executable, source-audited, point-in-time-safe contract-7 pipeline and run it once for the week ending 2026-08-30.

**Architecture:** Store all production source and item definitions in `pipeline/config.json`, validate them into immutable catalog records, execute grouped source adapters, and normalize results into observation and item-level coverage rows. Publish the new catalog, observations, and coverage tables inside the existing weekly-context business domain so the five-file atomic release model and historical contracts remain intact.

**Tech Stack:** Python 3.9+, standard-library `unittest`, `requests`, pandas, openpyxl, pypdf, yfinance, SEC XBRL/filing JSON, JSON production configuration, Node.js built-in test runner.

**Spec:** `pipeline/internal/docs/superpowers/specs/2026-09-01-financial-data-universe-677-design.md`

## Global Constraints

- Source input is `/Users/a1-6/Downloads/public_financial_data_universe_weekly_topdown_v2.docx` with SHA-256 `78bd7fefb016e3d0962ec7f02e64709c1910dc4901d4cc653b15a9260f68b1d7`.
- Target cutoff is the most recent complete week ending `2026-08-30`; all release, observation, constituent-snapshot, and calculation eligibility checks use that cutoff.
- Preserve exactly the visible product directories `pipeline/` and `output/`; do not edit the adjacent frontend checkout.
- Keep `pipeline/config.json` as the only production configuration source; a document importer is a development tool, never a production fallback.
- Keep the five business files `indices.json`, `sectors.json`, `gics.json`, `macro.json`, and `context.json`; contract 7 adds tables within `context.json` and does not add a sixth domain.
- Preserve dataset-contract versions 1 through 6 exactly.
- Apply `as_of_date` before snapshots, returns, breadth, correlations, surprises, revisions, aggregates, or other calculations.
- Missing values use JSON `null`; zero, empty strings, `NaN`, and infinity are not missing-value sentinels.
- Every published observation retains source URL, observation date, retrieval timestamp, status, and QC status.
- A 677-row coverage table is mandatory. Non-success status is not reported as fetched data.
- Company metrics use the user-approved current S&P 500 scope, a configured public holdings source, and SEC public ticker-to-CIK mapping.
- Do not bypass credentials, paywalls, robots restrictions, access controls, or terms.
- Live execution is authorized once. Do not issue a second live refresh or individual live retry after that run without a new user decision.
- A failed run preserves the current stable output and successful cache byte-for-byte.
- Preserve the unrelated untracked `pipeline/internal/docs/2026-08-30-current-data-12-category-audit.md`.
- Every behavior change starts with a focused failing test whose expected value is independent of the implementation, then the smallest implementation, focused GREEN, related GREEN, and a task-owned commit.

---

### Task 1: Reproducible 677-Item Catalog Import

**Files:**
- Create: `pipeline/internal/scripts/import_research_universe_docx.py`
- Modify: `pipeline/config.json`
- Create: `pipeline/internal/tests/test_research_universe_import.py`
- Modify: `pipeline/internal/tests/test_pipeline_config.py`

**Interfaces:**
- Consumes: the approved DOCX path passed explicitly on the command line; no default production document path.
- Produces: `extract_universe_rows(docx_path: Path) -> list[dict[str, object]]` and exactly 677 base rows under `research_universe.items` in `pipeline/config.json`.

- [ ] **Step 1: Write the failing catalog-count and anchor tests**

```python
EXPECTED_COUNTS = {
    "growth": (30, 53),
    "inflation": (23, 30),
    "labor": (22, 30),
    "monetary_policy": (16, 20),
    "fiscal": (19, 29),
    "liquidity_credit_creation": (21, 29),
    "rates_credit": (30, 26),
    "fx": (19, 24),
    "equities": (25, 35),
    "commodities": (22, 32),
    "positioning_flows_sentiment": (30, 44),
    "corporate_fundamentals_events": (24, 44),
}

def test_config_contains_the_exact_document_universe(self):
    rows = load_config_rows("research_universe.items")
    self.assertEqual(len(rows), 677)
    self.assertEqual(len({row["item_id"] for row in rows}), 677)
    for category, (core, extension) in EXPECTED_COUNTS.items():
        self.assertEqual(
            sum(row["category"] == category and row["layer"] == "core" for row in rows),
            core,
        )
        self.assertEqual(
            sum(row["category"] == category and row["layer"] == "extension" for row in rows),
            extension,
        )
    self.assertEqual(rows[0]["name"], "Real GDP")
    self.assertEqual(rows[-1]["name"], "Earnings Release KPI extraction")
```

The production change this test catches is an omitted, duplicated, reordered,
or category-misclassified document row.

- [ ] **Step 2: Run the tests and capture RED**

Run:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_research_universe_import \
  pipeline.internal.tests.test_pipeline_config
```

Expected: failure because `research_universe.items` and the importer do not
exist.

- [ ] **Step 3: Implement the document-table extractor**

Parse DOCX table XML with `zipfile` and `xml.etree.ElementTree`, so the repository
does not gain a runtime dependency on `python-docx`. Accept only six-column
tables with the exact header:

```python
ITEM_HEADER = (
    "#", "Data item", "Freq.", "Primary public source", "Access", "Research use",
)

def extract_universe_rows(docx_path: Path) -> list[dict[str, object]]:
    if sha256_file(docx_path) != APPROVED_SOURCE_SHA256:
        raise ValueError("Research-universe document hash does not match approved source")
    tables = _read_docx_tables(docx_path)
    item_tables = [table for table in tables if tuple(table[0]) == ITEM_HEADER]
    if len(item_tables) != 24:
        raise ValueError(f"Expected 24 item tables, found {len(item_tables)}")
    return _normalize_item_tables(item_tables)
```

Normalize category, layer, ordinal, frequency, access, and stable item ID while
preserving the document's item name, source text, and research-use text.

- [ ] **Step 4: Run the importer in explicit update mode**

Run:

```bash
python3 pipeline/internal/scripts/import_research_universe_docx.py \
  --input /Users/a1-6/Downloads/public_financial_data_universe_weekly_topdown_v2.docx \
  --config pipeline/config.json \
  --update
```

The update replaces only `research_universe.items`, writes stable sorted JSON,
and refuses any count other than 677. It does not infer endpoints or use the
document as a production dependency.

- [ ] **Step 5: Re-run the focused tests and verify GREEN**

Run the Step 2 command. Expected: PASS, including the exact 12-category counts,
281 Core rows, 396 Extension rows, and 677 unique IDs.

- [ ] **Step 6: Commit Task 1**

```bash
git add pipeline/config.json \
  pipeline/internal/scripts/import_research_universe_docx.py \
  pipeline/internal/tests/test_research_universe_import.py \
  pipeline/internal/tests/test_pipeline_config.py
git commit -m "feat: import 677-item research universe"
```

---

### Task 2: Catalog, Source, and Calculation Contracts

**Files:**
- Create: `pipeline/internal/capital_weekly/research_universe.py`
- Modify: `pipeline/config.json`
- Create: `pipeline/internal/tests/test_capital_weekly_research_universe.py`
- Modify: `pipeline/internal/tests/test_pipeline_config.py`

**Interfaces:**
- Consumes: `load_config_rows("research_universe.items")`, `load_config_rows("research_universe.sources")`, and `load_config_rows("research_universe.company_universe")`.
- Produces: `UniverseSource`, `UniverseItem`, `CompanyUniverseSpec`, `load_research_universe() -> ResearchUniverse`, and `validate_research_universe(universe: ResearchUniverse) -> None`.

- [ ] **Step 1: Write failing validation tests**

```python
def test_universe_rejects_unknown_source_and_derived_cycles(self):
    rows = [
        item("growth.core.001", source_id="missing"),
        item("growth.core.002", source_id="derived", transform="ratio",
             input_item_ids=("growth.core.003",)),
        item("growth.core.003", source_id="derived", transform="ratio",
             input_item_ids=("growth.core.002",)),
    ]
    with self.assertRaisesRegex(ValueError, "unknown source_id"):
        validate_research_universe(universe(items=rows, sources=[]))
```

Add independent cases for duplicate IDs, wrong totals, non-HTTPS URLs, unknown
provider/transform/frequency/access/scope, missing derived inputs, company scope
without a company-universe row, and valid topological calculation order. Each
test names the mutation it catches.

- [ ] **Step 2: Run the new module and capture RED**

```bash
python3 -m unittest -v pipeline.internal.tests.test_capital_weekly_research_universe
```

Expected: import failure because `research_universe.py` does not exist.

- [ ] **Step 3: Implement immutable models and fail-closed validation**

```python
@dataclass(frozen=True)
class UniverseSource:
    source_id: str
    name: str
    access: str
    provider: str
    base_url: str | None
    required_env: tuple[str, ...]
    terms_reviewed_on: date | None

@dataclass(frozen=True)
class UniverseItem:
    item_id: str
    category: str
    layer: str
    ordinal: int
    name: str
    frequency: str
    primary_source_text: str
    access: str
    research_use: str
    source_id: str
    locator: Mapping[str, object]
    transform: str
    input_item_ids: tuple[str, ...]
    scope: str
    requiredness: str
```

Use literal allowlists for statuses and normalized enums. Resolve calculation
dependencies with a topological sort and raise with the first unresolved or
cyclic item ID.

- [ ] **Step 4: Add normalized source rows and item execution metadata**

Populate `research_universe.sources` by normalizing the document's 165 exact
source strings into source families. Enrich every item with `source_id`,
`locator`, `transform`, `input_item_ids`, `scope`, and `requiredness`. Direct
items without a permitted reproducible endpoint use provider
`unavailable_public_source` with a literal reason and reviewed access state;
they do not masquerade as executable fetched data.

Run a config audit that emits no row with a blank source ID, unknown provider,
missing locator for a direct adapter, or missing inputs for a derived adapter.

- [ ] **Step 5: Run focused validation and config tests**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_research_universe \
  pipeline.internal.tests.test_pipeline_config
```

Expected: PASS with exact source references and deterministic calculation order.

- [ ] **Step 6: Commit Task 2**

```bash
git add pipeline/config.json \
  pipeline/internal/capital_weekly/research_universe.py \
  pipeline/internal/tests/test_capital_weekly_research_universe.py \
  pipeline/internal/tests/test_pipeline_config.py
git commit -m "feat: validate research universe contracts"
```

---

### Task 3: Normalized Observations, Coverage, and Grouped Execution

**Files:**
- Create: `pipeline/internal/capital_weekly/research_execution.py`
- Create: `pipeline/internal/tests/test_capital_weekly_research_execution.py`
- Modify: `pipeline/internal/capital_weekly/official_http.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_official_http.py`

**Interfaces:**
- Consumes: validated `ResearchUniverse`, `as_of_date: date`, provider registry, and injected HTTP session/clock.
- Produces: `UniverseObservation`, `UniverseCoverage`, `SourceExecution`, `run_research_universe(...) -> UniverseRunResult`, and `build_coverage(...) -> tuple[UniverseCoverage, ...]`.

- [ ] **Step 1: Write failing execution and status tests**

```python
def test_grouped_execution_fetches_one_source_request_for_two_items(self):
    session = CompleteFakeSession({REQUEST_URL: COMPLETE_OFFICIAL_RESPONSE})
    result = run_research_universe(
        universe=two_items_same_request(),
        as_of_date=date(2026, 8, 30),
        session=session,
        now=lambda: datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    self.assertEqual(session.request_count, 1)
    self.assertEqual([row.status for row in result.coverage], ["AVAILABLE", "AVAILABLE"])
```

Add cases proving future observations are removed before latest selection,
credentials yield `CREDENTIAL_REQUIRED`, a legitimate no-release result differs
from parse/fetch failure, missing numeric values remain `None`, errors are
sanitized, coverage has exactly one row per item, and a core fetch failure is
marked release-blocking.

- [ ] **Step 2: Run focused tests and capture RED**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_research_execution \
  pipeline.internal.tests.test_capital_weekly_official_http
```

Expected: import failure for the new execution module.

- [ ] **Step 3: Implement normalized records and request grouping**

```python
@dataclass(frozen=True)
class UniverseObservation:
    record_id: str
    item_id: str
    category: str
    layer: str
    entity_id: str | None
    entity_name: str | None
    observation_date: date
    period_start: date | None
    period_end: date | None
    value: float | int | str | None
    unit: str | None
    source_id: str
    source_url: str
    retrieved_at: datetime
    status: str
    qc_status: str
    is_proxy: bool
    is_derived: bool
    input_record_ids: tuple[str, ...]
    formula: str | None
```

Group direct requests by a canonical `RequestKey`. Apply the cutoff to parsed
histories before any adapter chooses a release or snapshot. Build coverage from
actual normalized results, never from provider registration alone.

- [ ] **Step 4: Add bounded HTTP execution and sanitized failures**

Extend the existing official HTTP boundary to expose status code, content type,
retrieval timestamp, and content hash without logging response bodies or secret
query parameters. Make network fakes reproduce these fields completely.

- [ ] **Step 5: Re-run focused tests and mutation cases**

Run the Step 2 command. Then mutate the fake response to contain a future row,
blank numeric cell, malformed content type, and missing credential; each named
test must fail before restoring production behavior. Expected final result:
PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add pipeline/internal/capital_weekly/research_execution.py \
  pipeline/internal/capital_weekly/official_http.py \
  pipeline/internal/tests/test_capital_weekly_research_execution.py \
  pipeline/internal/tests/test_capital_weekly_official_http.py
git commit -m "feat: add grouped universe execution"
```

---

### Task 4: Official U.S. and International Source Adapters

**Files:**
- Create: `pipeline/internal/capital_weekly/research_sources/__init__.py`
- Create: `pipeline/internal/capital_weekly/research_sources/official_series.py`
- Create: `pipeline/internal/capital_weekly/research_sources/official_artifacts.py`
- Create: `pipeline/internal/capital_weekly/research_sources/international.py`
- Create: `pipeline/internal/tests/test_capital_weekly_research_official_series.py`
- Create: `pipeline/internal/tests/test_capital_weekly_research_official_artifacts.py`
- Create: `pipeline/internal/tests/test_capital_weekly_research_international.py`
- Add fixtures under: `pipeline/internal/tests/fixtures/research_universe/`
- Modify: `pipeline/internal/capital_weekly/research_execution.py`
- Modify: `pipeline/config.json`

**Interfaces:**
- Consumes: `UniverseItem.locator`, `as_of_date`, grouped HTTP responses, and existing BLS/BEA/Census/Treasury/EIA/CFTC/USDA parsers.
- Produces: registered adapters with signature `adapter(items: tuple[UniverseItem, ...], context: AdapterContext) -> AdapterResult` for official JSON, CSV, SDMX, XML, HTML-table, XLSX, and PDF artifacts.

- [ ] **Step 1: Add one failing real-parser fixture test per adapter family**

Use complete, minimized source fixtures with source-identifying metadata for:

```text
BLS; BEA; Census; Federal Reserve/FRED releases; Treasury/FiscalData/TIC;
EIA; CFTC; USDA; SEC aggregate data; FDIC; NY Fed; OCC;
World Bank; IMF SDMX; OECD SDMX; BIS SDMX;
ECB/Eurostat; BOE; BOJ; PBOC/ChinaBond; official exchange downloads.
```

Representative boundary assertion:

```python
def test_sdmx_adapter_uses_the_latest_period_known_by_cutoff(self):
    rows = parse_sdmx_json(SDMX_FIXTURE, locator=LOCATOR)
    result = normalize_direct_item(ITEM, rows, as_of_date=date(2026, 8, 30))
    self.assertEqual(result.observations[0].observation_date, date(2026, 8, 28))
    self.assertEqual(result.observations[0].value, 103.4)
```

The fixtures include a later observation so removing the cutoff causes a real
test failure.

- [ ] **Step 2: Run the three new modules and capture RED**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_research_official_series \
  pipeline.internal.tests.test_capital_weekly_research_official_artifacts \
  pipeline.internal.tests.test_capital_weekly_research_international
```

Expected: import failures because the adapter package does not exist.

- [ ] **Step 3: Implement generic official series adapters**

Implement source-specific request builders on top of shared parsers:

```python
ADAPTERS = {
    "bls": fetch_bls,
    "bea": fetch_bea,
    "census": fetch_census,
    "fred_csv": fetch_fred_csv,
    "fiscaldata": fetch_fiscaldata,
    "eia": fetch_eia,
    "sdmx_json": fetch_sdmx_json,
    "world_bank": fetch_world_bank,
}
```

Reuse existing production parsers through thin normalized adapters when their
point-in-time and provenance tests pass. Do not copy working parser logic into a
second implementation.

- [ ] **Step 4: Implement official artifact adapters**

Add parser boundaries for dated release HTML, CSV, XLSX, XML, and PDF. Every
locator declares its parser, table/sheet/series selector, unit, release-date
field, observation-date field, and freshness rule. Reject ambiguous multiple
matches instead of taking the first page or cell.

- [ ] **Step 5: Complete item locators for official-source definitions**

For every catalog item whose approved source family is official, add a literal
series code or artifact selector to its config locator. Run
`validate_research_universe` and reject any official item still routed to
`unavailable_public_source` unless the official publisher offers no permitted,
reproducible public observation. Record that exact reason in the source row.

- [ ] **Step 6: Run focused adapters plus existing provider regressions**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_research_official_series \
  pipeline.internal.tests.test_capital_weekly_research_official_artifacts \
  pipeline.internal.tests.test_capital_weekly_research_international \
  pipeline.internal.tests.test_capital_weekly_economic_bls \
  pipeline.internal.tests.test_capital_weekly_economic_bea \
  pipeline.internal.tests.test_capital_weekly_economic_census \
  pipeline.internal.tests.test_capital_weekly_macro_assets \
  pipeline.internal.tests.test_capital_weekly_context_providers
```

Expected: PASS with no live network access.

- [ ] **Step 7: Commit Task 4**

```bash
git add pipeline/config.json \
  pipeline/internal/capital_weekly/research_sources \
  pipeline/internal/capital_weekly/research_execution.py \
  pipeline/internal/tests/test_capital_weekly_research_official_series.py \
  pipeline/internal/tests/test_capital_weekly_research_official_artifacts.py \
  pipeline/internal/tests/test_capital_weekly_research_international.py \
  pipeline/internal/tests/fixtures/research_universe
git commit -m "feat: add official universe source adapters"
```

---

### Task 5: Registered Derived-Item Calculation Graph

**Files:**
- Create: `pipeline/internal/capital_weekly/research_calculations.py`
- Create: `pipeline/internal/tests/test_capital_weekly_research_calculations.py`
- Modify: `pipeline/internal/capital_weekly/research_execution.py`
- Modify: `pipeline/config.json`

**Interfaces:**
- Consumes: cutoff-filtered direct observations indexed by item/entity/period and topologically sorted derived `UniverseItem` rows.
- Produces: `calculate_universe_items(items, observations, as_of_date) -> tuple[UniverseObservation, ...]` and a literal transform registry.

- [ ] **Step 1: Write failing calculation behavior tests**

```python
def test_ratio_uses_same_entity_and_period_and_declares_lineage(self):
    rows = calculate_universe_items(
        (derived_item("corporate.core.012", "subtract", ("debt", "cash")),),
        observations=(debt("AAPL", "2026-Q2", 90.0), cash("AAPL", "2026-Q2", 30.0)),
        as_of_date=date(2026, 8, 30),
    )
    self.assertEqual(rows[0].value, 60.0)
    self.assertEqual(rows[0].input_record_ids, ("debt-aapl-q2", "cash-aapl-q2"))
```

Add independent tests for percent change, difference, sum, ratio, margin,
rolling mean, rolling percentile, diffusion/breadth, correlation, surprise,
revision, TTM, annualization, real/nominal conversion, weighted aggregate, zero
denominator, mismatched periods, missing inputs, non-finite results, and future
inputs.

- [ ] **Step 2: Run the new module and capture RED**

```bash
python3 -m unittest -v pipeline.internal.tests.test_capital_weekly_research_calculations
```

Expected: import failure for `research_calculations.py`.

- [ ] **Step 3: Implement the literal transform registry**

```python
TRANSFORMS = {
    "difference": calculate_difference,
    "sum": calculate_sum,
    "ratio": calculate_ratio,
    "percent_change": calculate_percent_change,
    "margin": calculate_ratio,
    "rolling_mean": calculate_rolling_mean,
    "rolling_percentile": calculate_rolling_percentile,
    "breadth": calculate_breadth,
    "correlation": calculate_correlation,
    "surprise": calculate_surprise,
    "revision": calculate_revision,
    "ttm": calculate_ttm,
    "annualize": calculate_annualized,
    "weighted_aggregate": calculate_weighted_aggregate,
}
```

Every transform receives already cutoff-filtered inputs, validates compatible
entity/period/unit semantics, and emits resolvable record lineage.

- [ ] **Step 4: Register all derived document items**

Populate literal input item IDs and transform parameters for every item whose
document access is `Derived` or whose research definition requires a formula.
Reject a derived item with no registered transform, a direct item pretending to
be derived, and any unresolved dependency.

- [ ] **Step 5: Run calculation and execution tests**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_research_calculations \
  pipeline.internal.tests.test_capital_weekly_research_execution \
  pipeline.internal.tests.test_capital_weekly_returns \
  pipeline.internal.tests.test_capital_weekly_cross_asset \
  pipeline.internal.tests.test_capital_weekly_fundamentals
```

Expected: PASS and no derived observation without lineage.

- [ ] **Step 6: Commit Task 5**

```bash
git add pipeline/config.json \
  pipeline/internal/capital_weekly/research_calculations.py \
  pipeline/internal/capital_weekly/research_execution.py \
  pipeline/internal/tests/test_capital_weekly_research_calculations.py
git commit -m "feat: calculate derived universe items"
```

---

### Task 6: S&P 500 Constituents and SEC Company Expansion

**Files:**
- Create: `pipeline/internal/capital_weekly/research_sources/sp500_sec.py`
- Create: `pipeline/internal/tests/test_capital_weekly_research_sp500_sec.py`
- Add fixtures under: `pipeline/internal/tests/fixtures/research_universe/sp500_sec/`
- Modify: `pipeline/internal/capital_weekly/context/fundamentals.py`
- Modify: `pipeline/internal/capital_weekly/context/company_events.py`
- Modify: `pipeline/internal/capital_weekly/research_execution.py`
- Modify: `pipeline/config.json`
- Modify: `pipeline/internal/tests/test_capital_weekly_fundamentals.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_company_events.py`

**Interfaces:**
- Consumes: configured public holdings CSV/XLSX, SEC ticker registry, truthful `SEC_USER_AGENT`, Company Facts, submissions, filing metadata, and filing artifacts.
- Produces: `CompanyUniverseSnapshot`, normalized per-company observations for the 68 company definitions, filing/event observations, and S&P 500 breadth with eligible denominators.

- [ ] **Step 1: Write failing constituent and SEC expansion tests**

```python
def test_company_expansion_maps_public_holdings_symbols_to_sec_ciks(self):
    snapshot = build_company_universe(
        holdings_bytes=SP500_HOLDINGS_FIXTURE,
        sec_tickers_json=SEC_TICKERS_FIXTURE,
        as_of_date=date(2026, 8, 30),
        retrieved_at=RETRIEVED_AT,
    )
    self.assertEqual(snapshot.companies[0].ticker, "AAPL")
    self.assertEqual(snapshot.companies[0].cik, "0000320193")
    self.assertEqual(snapshot.source_url, SP500_SOURCE_URL)
```

Add cases for ticker punctuation normalization, duplicate share classes,
unmapped ticker failure, current-universe limitation status, missing SEC user
agent, fiscal-period selection by filing date, amended filings, units, reported
versus derived facts, non-disclosure, filing events, and breadth denominators.

- [ ] **Step 2: Run focused modules and capture RED**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_research_sp500_sec \
  pipeline.internal.tests.test_capital_weekly_fundamentals \
  pipeline.internal.tests.test_capital_weekly_company_events
```

Expected: import failure for the S&P/SEC adapter and failures for automatic
company-universe expansion.

- [ ] **Step 3: Implement public constituent parsing and SEC mapping**

Parse only the configured holdings artifact and SEC ticker registry. Preserve
both content hashes. Do not load a fallback ticker list from test data, source
code, or a neighboring repository. A missing truthful SEC user agent returns
`CREDENTIAL_REQUIRED` for SEC-dependent definitions and never places a request.

- [ ] **Step 4: Extend SEC fact and filing normalization**

Add XBRL concept-priority mappings for the document's reported financial
definitions and retain accession, filed date, fiscal period, form, unit, and
source URL. Add filing/document classifiers for 10-K, 10-Q, 8-K, Form 4,
registration/prospectus, S-1/F-1, 424B4, Form 10, debt/equity issuance,
cybersecurity, auditor, executive, M&A, restructuring, and bankruptcy signals.
Classifiers emit evidence spans and source links; ambiguous documents remain
unclassified.

- [ ] **Step 5: Implement disclosure-aware company outputs and breadth**

For every company definition, distinguish `AVAILABLE`, `NOT_DISCLOSED`, and
provider failure. Derived company metrics use same-company, comparable-period
inputs. Aggregate revenue, margin, and capex breadth publish numerator,
denominator, constituent-snapshot hash, and the current-universe limitation.

- [ ] **Step 6: Run focused SEC and execution regressions**

Run the Step 2 command plus:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_research_execution \
  pipeline.internal.tests.test_capital_weekly_capital_markets \
  pipeline.internal.tests.test_capital_weekly_weekly_context
```

Expected: PASS with fixtures only.

- [ ] **Step 7: Commit Task 6**

```bash
git add pipeline/config.json \
  pipeline/internal/capital_weekly/research_sources/sp500_sec.py \
  pipeline/internal/capital_weekly/research_execution.py \
  pipeline/internal/capital_weekly/context/fundamentals.py \
  pipeline/internal/capital_weekly/context/company_events.py \
  pipeline/internal/tests/test_capital_weekly_research_sp500_sec.py \
  pipeline/internal/tests/test_capital_weekly_fundamentals.py \
  pipeline/internal/tests/test_capital_weekly_company_events.py \
  pipeline/internal/tests/fixtures/research_universe/sp500_sec
git commit -m "feat: expand universe across S&P 500 companies"
```

---

### Task 7: Permitted Public-View Artifacts and Availability Audit

**Files:**
- Create: `pipeline/internal/capital_weekly/research_sources/public_view.py`
- Create: `pipeline/internal/tests/test_capital_weekly_research_public_view.py`
- Add fixtures under: `pipeline/internal/tests/fixtures/research_universe/public_view/`
- Modify: `pipeline/internal/capital_weekly/research_execution.py`
- Modify: `pipeline/config.json`

**Interfaces:**
- Consumes: configured public HTML/download locators, terms-review dates, complete fixture responses, and item definitions still lacking official adapters.
- Produces: normalized public-view observations or exact `PUBLIC_ACCESS_BLOCKED`/`SOURCE_UNAVAILABLE` coverage states with reviewed reasons.

- [ ] **Step 1: Write failing parser and access-state tests**

```python
def test_public_view_adapter_rejects_login_page_instead_of_parsing_it(self):
    result = fetch_public_view_items(
        (ITEM,),
        context_with_response(status=200, content_type="text/html", body=LOGIN_HTML),
    )
    self.assertEqual(result.status, "PUBLIC_ACCESS_BLOCKED")
    self.assertEqual(result.observations, ())
```

Add real-parser fixture cases for permitted tables, downloadable CSV/XLSX/PDF,
renamed columns, no-data pages, multiple-match ambiguity, stale terms-review
date, robots/access denial, and source attribution. The production mutation each
test catches is named in the test docstring.

- [ ] **Step 2: Run the new module and capture RED**

```bash
python3 -m unittest -v pipeline.internal.tests.test_capital_weekly_research_public_view
```

Expected: import failure because `public_view.py` does not exist.

- [ ] **Step 3: Implement fail-closed public artifact adapters**

Implement explicit selectors only:

```python
PUBLIC_VIEW_PARSERS = {
    "html_table": parse_named_html_table,
    "download_csv": parse_configured_csv,
    "download_xlsx": parse_configured_sheet,
    "dated_pdf_table": parse_configured_pdf_table,
}
```

Require expected content type, identifying headers, one unambiguous selected
table/sheet, observation date, source URL, and a non-expired terms review. Detect
login, challenge, denial, and paywall responses before parsing.

- [ ] **Step 4: Finish the source-availability audit**

For every item not covered by official or derived adapters, either configure a
permitted reproducible public artifact locator or assign a literal reviewed
non-success reason. Validate that every one of the 677 rows is in exactly one
execution class: direct official, direct public-view, derived, conditional
company disclosure, or explicit unavailable source.

- [ ] **Step 5: Run public-view, universe, and execution tests**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_research_public_view \
  pipeline.internal.tests.test_capital_weekly_research_universe \
  pipeline.internal.tests.test_capital_weekly_research_execution
```

Expected: PASS with no live access and no unclassified item.

- [ ] **Step 6: Commit Task 7**

```bash
git add pipeline/config.json \
  pipeline/internal/capital_weekly/research_sources/public_view.py \
  pipeline/internal/capital_weekly/research_execution.py \
  pipeline/internal/tests/test_capital_weekly_research_public_view.py \
  pipeline/internal/tests/fixtures/research_universe/public_view
git commit -m "feat: audit public-view universe sources"
```

---

### Task 8: Contract-7 Publication and Historical Compatibility

**Files:**
- Modify: `pipeline/internal/capital_weekly/weekly_context.py`
- Modify: `pipeline/internal/capital_weekly/weekly_release.py`
- Modify: `pipeline/internal/capital_weekly/capabilities.py`
- Modify: `pipeline/internal/scripts/fetch_weekly_context.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_weekly_context.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_weekly_release.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_capabilities.py`
- Modify: `pipeline/internal/tests/test_latest_json_output.py`
- Modify: `pipeline/internal/tests/test_offline_output_migration.py`

**Interfaces:**
- Consumes: `UniverseRunResult` from Task 3 and existing five-pipeline staged release.
- Produces: contract-7 `research_universe_catalog.csv`, `research_universe_observations.csv`, and `research_universe_coverage.csv`, serialized inside `context.json.tables`.

- [ ] **Step 1: Write failing contract-7 build and validation tests**

```python
def test_contract_7_requires_complete_677_item_catalog_and_coverage(self):
    staged = build_complete_contract_7_fixture()
    staged["weekly_context"]["research_universe_coverage.csv"].pop()
    with self.assertRaisesRegex(ReleaseValidationError, "coverage.*677"):
        validate_staged_week(staged, expected_week=EXPECTED_WEEK)
```

Add independent mutation tests for duplicate catalog IDs, observation unknown
item ID, future observation, invalid status, unavailable row with non-null
value, available row with no observation, broken derived lineage, non-HTTPS
source URL, wrong category totals, and cross-file release mismatch. Load fixed
contract 1-6 fixtures and assert their exact historical schemas still validate.

- [ ] **Step 2: Run release modules and capture RED**

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_weekly_context \
  pipeline.internal.tests.test_capital_weekly_weekly_release \
  pipeline.internal.tests.test_capital_weekly_capabilities \
  pipeline.internal.tests.test_latest_json_output \
  pipeline.internal.tests.test_offline_output_migration
```

Expected: failures because contract 7 and its three tables are absent.

- [ ] **Step 3: Register contract 7 without modifying contracts 1-6**

```python
PUBLIC_DATA_UNIVERSE_DATASET_CONTRACT_VERSION = 7
DATASET_CONTRACT_VERSION = PUBLIC_DATA_UNIVERSE_DATASET_CONTRACT_VERSION
SUPPORTED_DATASET_CONTRACT_VERSIONS = frozenset(range(1, 8))
```

Create a contract-specific `DatasetSpec` for each new CSV. Keep existing
versioned spec dictionaries immutable and derive JSON table routing from the
selected contract rather than the latest constants.

- [ ] **Step 4: Integrate universe execution in weekly context**

Run the validated universe after provider registration and before staged CSV
validation. Always write exactly 677 catalog and coverage rows. Treat an
incomplete catalog, unclassified item, schema failure, parser programming
error, or failed Core provider as release-blocking. Preserve legitimate
Extension non-success states.

- [ ] **Step 5: Serialize the three tables inside `context.json`**

Keep `OUTPUT_BUSINESS_FILES` unchanged. Add the three table names only for
contract 7 and validate nulls, dates, source URLs, statuses, coverage counts,
and lineage before hashes are created.

- [ ] **Step 6: Run focused and compatibility tests**

Run the Step 2 command and:

```bash
node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs
python3 - <<'PY'
from pathlib import Path
from pipeline.internal.capital_weekly.weekly_release import validate_output_bundle
print(validate_output_bundle(Path("output")))
PY
```

Expected: all Python and Node tests PASS; the existing unversioned active output
still validates without modification.

- [ ] **Step 7: Commit Task 8**

```bash
git add pipeline/internal/capital_weekly/weekly_context.py \
  pipeline/internal/capital_weekly/weekly_release.py \
  pipeline/internal/capital_weekly/capabilities.py \
  pipeline/internal/scripts/fetch_weekly_context.py \
  pipeline/internal/tests/test_capital_weekly_weekly_context.py \
  pipeline/internal/tests/test_capital_weekly_weekly_release.py \
  pipeline/internal/tests/test_capital_weekly_capabilities.py \
  pipeline/internal/tests/test_latest_json_output.py \
  pipeline/internal/tests/test_offline_output_migration.py
git commit -m "feat: publish contract 7 universe coverage"
```

---

### Task 9: Deterministic Completion Gate and Pre-Run Audit

**Files:**
- Create: `pipeline/internal/tests/test_research_universe_acceptance.py`
- Create: `pipeline/internal/docs/2026-09-01-research-universe-source-audit.md`

**Interfaces:**
- Consumes: committed contract-7 implementation and unchanged stable `output/`/successful cache.
- Produces: one acceptance module and a sanitized pre-run inventory with exact item counts by execution class and credential presence by name only.

- [ ] **Step 1: Write the acceptance test before the final wiring change**

```python
def test_all_677_items_are_classified_and_fixture_executable(self):
    universe = load_research_universe()
    result = run_research_universe(
        universe,
        as_of_date=date(2026, 8, 30),
        session=CompleteUniverseFakeSession.from_fixtures(),
        env=COMPLETE_NON_SECRET_TEST_ENV,
        now=lambda: FIXED_RETRIEVAL_TIME,
    )
    self.assertEqual(len(result.catalog), 677)
    self.assertEqual(len(result.coverage), 677)
    self.assertEqual({row.item_id for row in result.coverage}, {row.item_id for row in result.catalog})
```

The expected first RED is the first missing adapter classification or fixture
route, not a skipped test or mock-only assertion.

- [ ] **Step 2: Run acceptance and capture RED**

```bash
python3 -m unittest -v pipeline.internal.tests.test_research_universe_acceptance
```

- [ ] **Step 3: Complete the final missing deterministic route**

Add the exact config locator, fixture, or explicit reviewed non-success source
classification named by the RED. Do not weaken the test, reduce the 677 set, or
convert the item to available without an observation.

- [ ] **Step 4: Run the complete deterministic verification matrix**

```bash
python3 -m unittest -v
node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs
python3 - <<'PY'
from pathlib import Path
from pipeline.internal.capital_weekly.weekly_release import validate_output_bundle
print(validate_output_bundle(Path("output")))
PY
python3 -m compileall -q pipeline
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 5: Record stable-pair and credential-presence fingerprints**

Hash the complete `output/` tree and the current successful `pipeline/.cache/`
generation before live execution. Record only whether each named environment
variable is present; never record values. Record item counts by official,
public-view, derived, conditional disclosure, and explicit unavailable class.

- [ ] **Step 6: Commit Task 9**

```bash
git add pipeline/internal/tests/test_research_universe_acceptance.py \
  pipeline/internal/docs/2026-09-01-research-universe-source-audit.md
git commit -m "test: verify complete research universe wiring"
```

---

### Task 10: One Authorized Live Run and Final Handoff

**Files:**
- Modify only on successful atomic publication: `output/*.json` and the single successful `pipeline/.cache/` generation; both remain untracked.
- Create: `pipeline/internal/docs/2026-09-01-research-universe-live-run.md`

**Interfaces:**
- Consumes: verified HEAD, target `as_of_date=2026-08-30`, configured credentials, and pre-run stable-pair fingerprints.
- Produces: one validated contract-7 stable release or a sanitized factual failure report with unchanged stable output/cache.

- [ ] **Step 1: Confirm the one-run preconditions**

Verify tracked/staged diffs are clean, the unrelated audit is the only unrelated
untracked file, the active output validates, the source document hash matches,
and the stable-pair hashes match Task 9. Record missing credential names without
values.

- [ ] **Step 2: Run the pipeline exactly once**

```bash
python3 -m pipeline.refresh --as-of-date 2026-08-30
```

Capture the complete log privately. The sanitized report may contain source
names, statuses, counts, and error classes but not query secrets, credential
values, response bodies, or sensitive URLs.

- [ ] **Step 3: Handle success or failure without retrying**

On success, validate the new output, compute the release identity, confirm the
catalog and coverage each contain 677 unique IDs, summarize observations and
statuses by category/source, and confirm the cache contains exactly one
successful generation.

On failure, do not retry. Confirm the stable output and successful cache match
the pre-run hashes byte-for-byte. Record the failing stage, affected item IDs,
sanitized source names, and exact status classes.

- [ ] **Step 4: Re-run the final verification gate**

```bash
python3 -m unittest -v
node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs
python3 - <<'PY'
from pathlib import Path
from pipeline.internal.capital_weekly.weekly_release import validate_output_bundle
print(validate_output_bundle(Path("output")))
PY
git diff --check
git status --short
```

Expected: deterministic suites and active-output validation exit 0. A live
source failure may leave the target week unpublished, but must not damage the
stable pair.

- [ ] **Step 5: Write and commit the sanitized live-run report**

The report includes commits, created/modified/deleted files, source document
hash, target week, fetched and non-success counts, exact status distribution,
provider failures, RED/GREEN evidence, full test results, active release
identity, output/cache preservation, and remaining access/licensing risks.

```bash
git add pipeline/internal/docs/2026-09-01-research-universe-live-run.md
git commit -m "docs: report 677-item universe refresh"
```

## Plan Self-Review

- **Spec coverage:** Tasks 1-2 cover the exact catalog and source model; Tasks
  3-7 cover execution, official/public sources, calculations, and S&P 500/SEC;
  Task 8 covers contract 7 and compatibility; Tasks 9-10 cover deterministic
  acceptance, the single live run, atomicity, and handoff.
- **Placeholder scan:** The plan contains no deferred implementation markers.
  Items whose public source is genuinely inaccessible receive a literal
  reviewed status through a tested adapter rather than an unfinished code path.
- **Type consistency:** Tasks 2-8 consistently consume `ResearchUniverse`,
  `UniverseItem`, `UniverseSource`, `UniverseObservation`, `UniverseCoverage`,
  `SourceExecution`, `AdapterContext`, `AdapterResult`, and `UniverseRunResult`.
  Contract-7 publication consumes the exact `UniverseRunResult` produced by the
  grouped executor.
