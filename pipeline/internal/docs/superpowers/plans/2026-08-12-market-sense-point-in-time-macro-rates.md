# Market Sense Point-in-Time Macro And Rates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add point-in-time-correct US macro releases, Treasury real yields, 5Y/10Y breakevens, and 5Y5Y inflation to the existing five-pipeline Capital Weekly backend without allowing later releases or revisions to leak into an older formal week.

**Architecture:** Keep `macro_assets` and `weekly_context` as the two affected top-level pipelines. Add a shared provider-definition and point-in-time contract below `capital_weekly/context`, source-specific parsers for immutable official release artifacts, a typed `economic_releases.csv`, and registered Treasury calculations; extend the existing weekly release validator and manifest rather than adding a pipeline. BLS, BEA, and Census use official archived release artifacts, while ISM uses an immutable prospective capture store and refuses historical backfill when no eligible capture exists.

**Tech Stack:** Python 3 standard library, `pandas`, `requests`, existing `pypdf`, `unittest`, deterministic HTML/CSV/JSON/XLSX fixtures, existing five-pipeline release coordinator.

**Authoritative design:** `docs/superpowers/specs/2026-08-11-market-sense-public-data-expansion-design.md`

## Global Constraints

- Keep the existing five top-level pipelines. Do not add a sixth release pipeline.
- Use free public sources only for P0/P1.
- Do not use browser automation, paid consensus, proprietary fund-flow estimates, level-2 order books, tick data, or unofficial political-event aggregation.
- Every published record must satisfy `known_as_of <= target Sunday end in Asia/Hong_Kong`.
- Later revisions cannot overwrite an older weekly vintage.
- If a historical vintage cannot be proven, use `POINT_IN_TIME_UNAVAILABLE`; never substitute the currently revised value.
- Preserve raw weekly responses from the feature launch onward.
- `consensus_value` and `surprise_value` remain null in P0/P1.
- Required provider failure blocks formal publication; optional failure produces a manifest warning and retains standard-header empty tables.
- Empty optional tables retain their exact standard headers.
- Any failed staging run leaves the prior complete week visible.
- Tests use deterministic fake responses, histories, clocks, and runners. Do not run a real network refresh unless the user explicitly requests it.
- Do not modify the Next.js repository from this backend plan.
- Preserve unrelated dirty and untracked files. Each task commits only the files it owns.

## Source And Vintage Decisions

- BLS CPI and Employment Situation data come from archived BLS news-release HTML or PDF artifacts linked by the official archive pages. Do not use the current BLS time-series API to recreate an older weekly vintage.
- BEA GDP and Personal Income and Outlays data come from the official BEA release archive and the release-specific table artifacts linked from each archived release.
- Census retail sales come from the archived Advance Monthly Retail Trade release page or its release-specific table artifact.
- ISM Manufacturing PMI is captured prospectively from the official report page. An eligible local capture must have `captured_at <= target Sunday 23:59:59.999999 Asia/Hong_Kong`; otherwise the provider returns `POINT_IN_TIME_UNAVAILABLE`.
- Treasury nominal and real curves come from the official Daily Treasury Par Yield Curve and Daily Treasury Par Real Yield Curve CSV endpoints, filtered to `date <= as_of_date` before snapshot calculations.
- The registered 5Y5Y formula is `(((1 + be10 / 100) ** 2) / (1 + be5 / 100) - 1) * 100`, evaluated only on dates shared by the 5Y and 10Y breakeven histories.

## Planned File Structure

- `capital_weekly/context/provider_contracts.py`: provider metadata, HKT cutoff, immutable capture selection, and point-in-time filtering.
- `capital_weekly/context/economic_releases.py`: typed release schema, primary keys, vintage selection, and registered economic calculations.
- `capital_weekly/context/economic_sources/bls.py`: CPI/Core CPI, NFP, and unemployment parsers/providers.
- `capital_weekly/context/economic_sources/bea.py`: GDP, PCE, and Core PCE parsers/providers.
- `capital_weekly/context/economic_sources/census.py`: retail-sales parser/provider.
- `capital_weekly/context/economic_sources/ism.py`: prospective ISM capture parser/provider.
- `capital_weekly/context/economic_sources/__init__.py`: builds the four required economic provider definitions.
- `data/capital_weekly_economic_indicators.csv`: the nine approved indicator identities and display metadata.
- `capital_weekly/weekly_context.py`: publishes the new table and richer source log.
- `capital_weekly/context/providers.py`: composes existing and new provider definitions.
- `capital_weekly/macro_assets.py`: official real-curve fetch and registered breakeven/forward calculations.
- `data/capital_weekly_macro_assets.csv`: real-yield and calculated inflation rows plus provider/formula metadata.
- `capital_weekly/weekly_release.py`: strict timestamp, provider-requiredness, table-coverage, warning, and manifest validation.
- `scripts/fetch_weekly_context.py`: passes the raw-capture root and prints warnings.
- `README.md`: documents point-in-time behavior and offline verification.

---

### Task 1: Establish Shared Provider And Point-In-Time Contracts

**Files:**
- Create: `capital_weekly/context/provider_contracts.py`
- Modify: `capital_weekly/weekly_context.py`
- Modify: `capital_weekly/context/providers.py`
- Create: `tests/test_capital_weekly_point_in_time.py`
- Modify: `tests/test_capital_weekly_weekly_context.py`
- Modify: `tests/test_capital_weekly_context_providers.py`

**Interfaces:**
- Produces: `ProviderSpec(name: str, category: str, source_tier: str, requiredness: str, provider_version: str, schema_version: str, frequency: str, freshness_days: int | None)`.
- Produces: `ContextProvider(spec: ProviderSpec, fetch: Callable[[], ProviderResult])`.
- Produces: `target_sunday_cutoff(as_of_date: date) -> datetime`.
- Produces: `filter_known_as_of(rows: Iterable[dict], as_of_date: date) -> list[dict]`.
- Produces: `select_capture_at_or_before(captures: Iterable[CaptureMetadata], as_of_date: date) -> CaptureMetadata` raising `PointInTimeUnavailable` when none qualifies.
- Preserves: `ProviderResult` remains importable from `capital_weekly.weekly_context`.

- [ ] **Step 1: Write failing cutoff, capture-selection, and provider-log tests**

```python
def test_filter_known_as_of_excludes_a_monday_revision(self):
    rows = [
        {"record_id": "old", "known_as_of": "2026-08-07T08:30:00-04:00"},
        {"record_id": "new", "known_as_of": "2026-08-10T08:30:00-04:00"},
    ]
    self.assertEqual(
        [row["record_id"] for row in filter_known_as_of(rows, date(2026, 8, 9))],
        ["old"],
    )

def test_capture_selection_refuses_a_capture_created_after_sunday(self):
    captures = [
        CaptureMetadata(
            provider="ism_manufacturing",
            captured_at="2026-08-10T09:00:00+08:00",
            path=Path("monday.raw"),
            sha256="a" * 64,
            source_url="https://www.ismworld.org/",
        )
    ]
    with self.assertRaises(PointInTimeUnavailable):
        select_capture_at_or_before(captures, date(2026, 8, 9))
```

Extend the weekly-context test so one successful provider log row contains the exact values `public`, `required`, `1.0.0`, and `economic-release-v1` from its `ProviderSpec`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python3 -m unittest -v tests.test_capital_weekly_point_in_time tests.test_capital_weekly_weekly_context tests.test_capital_weekly_context_providers`

Expected: FAIL because `capital_weekly.context.provider_contracts` and the new source-log fields do not exist.

- [ ] **Step 3: Implement the shared immutable contracts**

```python
HONG_KONG = ZoneInfo("Asia/Hong_Kong")
SOURCE_TIERS = frozenset({"public", "licensed"})
REQUIREDNESS_VALUES = frozenset({"required", "optional"})

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

    def __post_init__(self) -> None:
        if self.source_tier not in SOURCE_TIERS:
            raise ValueError(f"Unsupported source tier: {self.source_tier}")
        if self.requiredness not in REQUIREDNESS_VALUES:
            raise ValueError(f"Unsupported requiredness: {self.requiredness}")

@dataclass(frozen=True)
class ContextProvider:
    spec: ProviderSpec
    fetch: Callable[[], "ProviderResult"]

def target_sunday_cutoff(as_of_date: date) -> datetime:
    return datetime.combine(as_of_date, time.max, tzinfo=HONG_KONG)

def filter_known_as_of(rows: Iterable[dict], as_of_date: date) -> list[dict]:
    cutoff = target_sunday_cutoff(as_of_date)
    accepted = []
    for row in rows:
        raw = str(row.get("known_as_of") or "")
        known = datetime.fromisoformat(raw)
        if known.tzinfo is None:
            raise ValueError("known_as_of must include a UTC offset")
        if known.astimezone(HONG_KONG) <= cutoff:
            accepted.append(dict(row))
    return accepted
```

Move `ProviderResult` to `provider_contracts.py`, import and re-export it from `weekly_context.py`, and make `run_weekly_context` accept `Mapping[str, ContextProvider]`. Add these exact source-log columns after `provider`: `source_tier`, `requiredness`, `provider_version`, `schema_version`, `frequency`, `freshness_days`, `latest_known_as_of`, `warnings`.

- [ ] **Step 4: Wrap every existing default provider in a `ContextProvider`**

Use `ProviderSpec` values derived from the existing registry. Mark `sec_company_events`, `eia_commodities`, and `fred_financial_conditions` optional; mark the remaining currently registered sources required. Use `source_tier="public"`, `provider_version="1.0.0"`, and `schema_version="context-metric-v1"` for existing providers.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `python3 -m unittest -v tests.test_capital_weekly_point_in_time tests.test_capital_weekly_weekly_context tests.test_capital_weekly_context_providers`

Expected: all focused tests pass.

- [ ] **Step 6: Commit the shared contracts**

```bash
git add capital_weekly/context/provider_contracts.py capital_weekly/weekly_context.py capital_weekly/context/providers.py tests/test_capital_weekly_point_in_time.py tests/test_capital_weekly_weekly_context.py tests/test_capital_weekly_context_providers.py
git commit -m "feat: add point-in-time provider contracts"
```

---

### Task 2: Define Economic Release Rows, Vintages, And Calculations

**Files:**
- Create: `capital_weekly/context/economic_releases.py`
- Modify: `capital_weekly/weekly_context.py`
- Create: `tests/test_capital_weekly_economic_releases.py`

**Interfaces:**
- Produces: `ECONOMIC_RELEASE_FIELDS: tuple[str, ...]`.
- Produces: `build_release_row(indicator_code: str, observation_period: str, release_at_bjt: str, value: float, unit: str, frequency: str, source: str, source_url: str, known_as_of: str, as_of_date: date, *, indicator_name: str | None = None, vintage_date: str = "initial", previous_value: float | None = None, revised_previous: float | None = None, seasonal_adjustment: str = "", calculation_id: str = "observed", formula_version: str = "source-v1", input_record_ids: tuple[str, ...] = ()) -> dict` with `consensus_value=None` and `surprise_value=None`.
- Produces: `select_latest_vintages(rows: Iterable[dict], as_of_date: date) -> list[dict]`.
- Produces: `derive_price_index_rows(rows: Iterable[dict], indicator_code: str) -> list[dict]`.
- Produces: `derive_real_gdp_rows(rows: Iterable[dict]) -> list[dict]`.
- Produces: `derive_ism_rows(row: dict) -> list[dict]`.

- [ ] **Step 1: Write failing schema, vintage, and calculation tests**

```python
def test_revision_after_sunday_cannot_replace_the_eligible_vintage(self):
    rows = [
        release_row("CPI_INDEX_SA", "2026-06", 326.1, "2026-07-14T08:30:00-04:00", "v1"),
        release_row("CPI_INDEX_SA", "2026-06", 326.4, "2026-08-10T08:30:00-04:00", "v2"),
    ]
    selected = select_latest_vintages(rows, date(2026, 8, 9))
    self.assertEqual(selected[0]["value"], 326.1)
    self.assertEqual(selected[0]["vintage_date"], "v1")

def test_absent_consensus_keeps_consensus_and_surprise_null(self):
    row = build_release_row(
        indicator_code="NFP_CHANGE",
        observation_period="2026-07",
        release_at_bjt="2026-08-07T20:30:00+08:00",
        value=125000.0,
        unit="persons",
        frequency="monthly",
        source="U.S. Bureau of Labor Statistics",
        source_url="https://www.bls.gov/news.release/",
        known_as_of="2026-08-07T08:30:00-04:00",
        as_of_date=date(2026, 8, 9),
    )
    self.assertIsNone(row["consensus_value"])
    self.assertIsNone(row["surprise_value"])
```

Add literal-value tests for CPI/PCE MoM, YoY, and three-month annualized changes; GDP QoQ SAAR and YoY; and ISM distance from 50. Assert each derived row contains `calculation_id`, `formula_version="economic-v1"`, and pipe-delimited `input_record_ids`.

- [ ] **Step 2: Run the economic-release test and verify RED**

Run: `python3 -m unittest -v tests.test_capital_weekly_economic_releases`

Expected: FAIL because `economic_releases.py` and `economic_releases` category schema do not exist.

- [ ] **Step 3: Implement the exact table contract**

```python
ECONOMIC_RELEASE_FIELDS = (
    "record_id", "indicator_code", "indicator_name", "observation_period",
    "release_at_bjt", "vintage_date", "as_of_date", "known_as_of",
    "value", "previous_value", "revised_previous", "consensus_value",
    "surprise_value", "unit", "frequency", "seasonal_adjustment",
    "calculation_id", "formula_version", "input_record_ids", "source",
    "source_url", "source_tier", "qc_flag",
)

def percent_change(current: float, base: float) -> float:
    if base == 0:
        raise ValueError("Percent change base cannot be zero")
    return (current / base - 1.0) * 100.0

def annualized_three_month_change(current: float, three_month_base: float) -> float:
    if three_month_base <= 0 or current <= 0:
        raise ValueError("Annualized price-index inputs must be positive")
    return ((current / three_month_base) ** 4 - 1.0) * 100.0
```

Use SHA-256 over `indicator_code|observation_period|vintage_date|calculation_id|input_record_ids` for `record_id`. Reject non-finite values, duplicate record IDs, unknown calculation IDs, naive timestamps, and non-public sources in this P0/P1 plan.

- [ ] **Step 4: Register the category in the weekly bundle**

Add `"economic_releases": "economic_releases.csv"` to `CATEGORY_FILES`, map it to `ECONOMIC_RELEASE_FIELDS`, and normalize it with the economic-release validator rather than `normalize_metric_rows`.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `python3 -m unittest -v tests.test_capital_weekly_economic_releases tests.test_capital_weekly_weekly_context`

Expected: all focused tests pass, including a header-only `economic_releases.csv` when the publisher is invoked without rows.

- [ ] **Step 6: Commit the release contract**

```bash
git add capital_weekly/context/economic_releases.py capital_weekly/weekly_context.py tests/test_capital_weekly_economic_releases.py tests/test_capital_weekly_weekly_context.py
git commit -m "feat: define point-in-time economic releases"
```

---

### Task 3: Add Archived BLS CPI And Employment Releases

**Files:**
- Create: `capital_weekly/context/economic_sources/__init__.py`
- Create: `capital_weekly/context/economic_sources/bls.py`
- Create: `tests/test_capital_weekly_economic_bls.py`

**Interfaces:**
- Produces: `parse_cpi_release(text: str, source_url: str, as_of_date: date) -> list[dict]`.
- Produces: `parse_employment_release(text: str, source_url: str, as_of_date: date) -> list[dict]`.
- Produces: `build_bls_provider(start: date, end: date, session) -> ContextProvider`.
- Required output families: CPI, Core CPI, NFP, and unemployment.

- [ ] **Step 1: Add minimal archived-release fixtures and failing parser tests**

Store the release fragments as Python string literals in the test module. Include the embargo timestamp, observation month, CPI all-items and less-food-and-energy rows, NFP change, unemployment rate, and the two prior-month NFP revisions.

```python
def test_bls_archived_release_preserves_publication_time_and_revisions(self):
    rows = parse_employment_release(
        EMPLOYMENT_ARCHIVE_HTML,
        "https://www.bls.gov/news.release/archives/empsit_08072026.htm",
        date(2026, 8, 9),
    )
    nfp = next(row for row in rows if row["indicator_code"] == "NFP_CHANGE")
    self.assertEqual(nfp["observation_period"], "2026-07")
    self.assertEqual(nfp["known_as_of"], "2026-08-07T08:30:00-04:00")
    self.assertEqual(nfp["previous_value"], 57000.0)
    self.assertEqual(nfp["revised_previous"], 42000.0)
```

- [ ] **Step 2: Run the BLS test and verify RED**

Run: `python3 -m unittest -v tests.test_capital_weekly_economic_bls`

Expected: FAIL because the BLS economic source module does not exist.

- [ ] **Step 3: Implement archived-link discovery and strict table parsing**

Use only links below these official indexes:

```python
CPI_ARCHIVE = "https://www.bls.gov/bls/news-release/cpi.htm"
EMPLOYMENT_ARCHIVE = "https://www.bls.gov/bls/news-release/empsit.htm"
ALLOWED_RELEASE_PREFIX = "https://www.bls.gov/news.release/archives/"
```

Reject redirects or discovered links outside `bls.gov`, require an embargo timestamp with a UTC offset after conversion, select the latest release whose publication timestamp is on or before the target cutoff, and parse values from the archived artifact itself. Do not query `api.bls.gov` for historical values.

- [ ] **Step 4: Add revision and time-travel cases**

Assert that a Monday BLS release is excluded from the prior Sunday, a later archived revision does not mutate the selected older release, missing core CPI fails the provider, and conflicting duplicate table rows raise `ValueError`.

- [ ] **Step 5: Run the BLS tests and verify GREEN**

Run: `python3 -m unittest -v tests.test_capital_weekly_economic_bls tests.test_capital_weekly_economic_releases`

Expected: all focused tests pass without network access.

- [ ] **Step 6: Commit the BLS provider**

```bash
git add capital_weekly/context/economic_sources/__init__.py capital_weekly/context/economic_sources/bls.py tests/test_capital_weekly_economic_bls.py
git commit -m "feat: ingest archived BLS macro releases"
```

---

### Task 4: Add Archived BEA GDP And PCE Releases

**Files:**
- Create: `capital_weekly/context/economic_sources/bea.py`
- Create: `tests/test_capital_weekly_economic_bea.py`

**Interfaces:**
- Produces: `parse_gdp_release(text: str, source_url: str, as_of_date: date) -> list[dict]`.
- Produces: `parse_pio_release(text: str, source_url: str, as_of_date: date) -> list[dict]`.
- Produces: `build_bea_provider(start: date, end: date, session) -> ContextProvider`.
- Required output families: real GDP, PCE price index, and Core PCE price index.

- [ ] **Step 1: Write failing archived-vintage tests**

```python
def test_gdp_second_estimate_is_not_visible_before_its_release(self):
    releases = [
        parse_gdp_release(GDP_ADVANCE_HTML, ADVANCE_URL, date(2026, 5, 24)),
        parse_gdp_release(GDP_SECOND_HTML, SECOND_URL, date(2026, 5, 31)),
    ]
    selected = select_latest_vintages(
        [row for release in releases for row in release],
        date(2026, 5, 24),
    )
    self.assertEqual(
        next(row for row in selected if row["indicator_code"] == "REAL_GDP_QOQ_SAAR")["vintage_date"],
        "advance",
    )
```

Add literal assertions for GDP QoQ SAAR/YoY and PCE/Core PCE MoM/YoY/three-month annualized values from controlled release tables.

- [ ] **Step 2: Run the BEA test and verify RED**

Run: `python3 -m unittest -v tests.test_capital_weekly_economic_bea`

Expected: FAIL because the BEA source module does not exist.

- [ ] **Step 3: Implement strict archive parsing**

Use the BEA release archive at `https://www.bea.gov/news/archive`. Accept only release-specific `bea.gov` links. Read the release timestamp, estimate label (`advance`, `second`, `third`, or `annual_update`), observation period, and the release table values. Prefer HTML tables; use the already installed `pypdf` only when the release offers no machine-readable table.

Normalize BEA timestamps to timezone-aware ISO strings, store the estimate label in `vintage_date`, and keep every calculation tied to literal input record IDs from the same release artifact.

- [ ] **Step 4: Add malformed and revised-release coverage**

Assert that a release missing the estimate label fails, an annual update published after Sunday is excluded, and two values for the same line/period/vintage fail rather than choosing one.

- [ ] **Step 5: Run the BEA tests and verify GREEN**

Run: `python3 -m unittest -v tests.test_capital_weekly_economic_bea tests.test_capital_weekly_economic_releases`

Expected: all focused tests pass.

- [ ] **Step 6: Commit the BEA provider**

```bash
git add capital_weekly/context/economic_sources/bea.py tests/test_capital_weekly_economic_bea.py
git commit -m "feat: ingest archived BEA macro releases"
```

---

### Task 5: Add Archived Census Retail Sales

**Files:**
- Create: `capital_weekly/context/economic_sources/census.py`
- Create: `tests/test_capital_weekly_economic_census.py`

**Interfaces:**
- Produces: `parse_retail_sales_release(text: str, source_url: str, as_of_date: date) -> list[dict]`.
- Produces: `build_census_provider(start: date, end: date, session) -> ContextProvider`.
- Required output family: total retail and food-services sales, seasonally adjusted.

- [ ] **Step 1: Write failing report and revision tests**

```python
def test_retail_release_keeps_the_revised_previous_value(self):
    rows = parse_retail_sales_release(RETAIL_ARCHIVE_HTML, RETAIL_URL, date(2026, 8, 9))
    monthly = next(row for row in rows if row["indicator_code"] == "RETAIL_SALES_MOM")
    self.assertEqual(monthly["observation_period"], "2026-06")
    self.assertEqual(monthly["previous_value"], 0.9)
    self.assertEqual(monthly["revised_previous"], 1.0)
```

Assert the provider derives YoY from the release-specific level history, not from a current Census time series downloaded after the target date.

- [ ] **Step 2: Run the Census test and verify RED**

Run: `python3 -m unittest -v tests.test_capital_weekly_economic_census`

Expected: FAIL because the Census source module does not exist.

- [ ] **Step 3: Implement official archived-release discovery and parsing**

Discover release artifacts from `https://www.census.gov/retail/data.html` and `https://www.census.gov/retail/sales.html`. Accept only `census.gov` links, require the release timestamp and total retail-and-food-services seasonally adjusted row, and reject source tables whose units are not millions of current dollars.

- [ ] **Step 4: Run the Census tests and verify GREEN**

Run: `python3 -m unittest -v tests.test_capital_weekly_economic_census tests.test_capital_weekly_economic_releases`

Expected: all focused tests pass.

- [ ] **Step 5: Commit the Census provider**

```bash
git add capital_weekly/context/economic_sources/census.py tests/test_capital_weekly_economic_census.py
git commit -m "feat: ingest archived Census retail releases"
```

---

### Task 6: Add Prospective ISM Manufacturing Captures And Register All Nine Indicators

**Files:**
- Create: `capital_weekly/context/economic_sources/ism.py`
- Modify: `capital_weekly/context/economic_sources/__init__.py`
- Modify: `capital_weekly/context/providers.py`
- Modify: `capital_weekly/weekly_context.py`
- Modify: `scripts/fetch_weekly_context.py`
- Create: `data/capital_weekly_economic_indicators.csv`
- Create: `tests/test_capital_weekly_economic_ism.py`
- Modify: `tests/test_capital_weekly_context_providers.py`
- Modify: `tests/test_capital_weekly_weekly_context.py`

**Interfaces:**
- Produces: `parse_ism_manufacturing_release(text: str, source_url: str, captured_at: datetime, as_of_date: date) -> list[dict]`.
- Produces: `build_economic_release_providers(start: date, end: date, session, capture_root: Path) -> dict[str, ContextProvider]`.
- CLI adds: `--capture-root`, defaulting to `outputs/.capital-weekly-source-cache`.
- Publishes: non-empty `economic_releases.csv` when every required economic provider succeeds.

- [ ] **Step 1: Write failing prospective-capture tests**

```python
def test_ism_requires_an_eligible_capture_for_a_historical_week(self):
    with self.assertRaises(PointInTimeUnavailable):
        load_ism_capture(
            capture_root=self.capture_root,
            as_of_date=date(2026, 8, 9),
        )

def test_ism_emits_level_and_registered_distance_from_50(self):
    rows = parse_ism_manufacturing_release(
        ISM_HTML,
        ISM_URL,
        datetime(2026, 8, 3, 10, 5, tzinfo=ZoneInfo("America/New_York")),
        date(2026, 8, 9),
    )
    values = {row["indicator_code"]: row["value"] for row in rows}
    self.assertEqual(values, {"ISM_MANUFACTURING_PMI": 48.7, "ISM_MANUFACTURING_DISTANCE_50": -1.3})
```

- [ ] **Step 2: Run ISM and registry tests and verify RED**

Run: `python3 -m unittest -v tests.test_capital_weekly_economic_ism tests.test_capital_weekly_context_providers tests.test_capital_weekly_weekly_context`

Expected: FAIL because the ISM capture loader, economic indicator config, and four-provider registry are absent.

- [ ] **Step 3: Implement the immutable capture layout**

Write content to `<capture_root>/ism_manufacturing/YYYYMMDDTHHMMSSZ-<sha256>.raw` and sidecar metadata to the same basename with `.json`. The sidecar contains exactly `provider`, `captured_at`, `sha256`, `source_url`, and `content_type`. Write each file atomically and never overwrite an existing hash.

When the target Sunday is earlier than the live fetch date, select only an existing eligible capture. A live fetch may create a capture for the current run, but its `captured_at` must still be on or before the target cutoff to be used for that target week.

- [ ] **Step 4: Create the nine-indicator configuration**

```csv
indicator_family,provider,required,frequency,source_tier
GDP,bea_gdp,true,quarterly,public
CPI,bls_cpi,true,monthly,public
CORE_CPI,bls_cpi,true,monthly,public
PCE,bea_pio,true,monthly,public
CORE_PCE,bea_pio,true,monthly,public
NFP,bls_employment,true,monthly,public
UNEMPLOYMENT,bls_employment,true,monthly,public
ISM_MANUFACTURING,ism_manufacturing,true,monthly,public
RETAIL_SALES,census_retail_sales,true,monthly,public
```

Validate exact family uniqueness and reject unknown providers or non-public tiers.

- [ ] **Step 5: Register and publish the economic providers**

Compose `bls_cpi`, `bls_employment`, `bea_gdp`, `bea_pio`, `census_retail_sales`, and `ism_manufacturing` into the existing default provider registry. All six definitions use `requiredness="required"`; provider success requires coverage of all nine configured families.

Pass `capture_root` from the CLI to `build_default_providers`, preserve the existing `--providers` filter, and include point-in-time failures in the printed audit summary.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `python3 -m unittest -v tests.test_capital_weekly_economic_ism tests.test_capital_weekly_economic_bls tests.test_capital_weekly_economic_bea tests.test_capital_weekly_economic_census tests.test_capital_weekly_context_providers tests.test_capital_weekly_weekly_context`

Expected: all focused tests pass without network access.

- [ ] **Step 7: Commit the integrated economic domain**

```bash
git add capital_weekly/context/economic_sources/ism.py capital_weekly/context/economic_sources/__init__.py capital_weekly/context/providers.py capital_weekly/weekly_context.py scripts/fetch_weekly_context.py data/capital_weekly_economic_indicators.csv tests/test_capital_weekly_economic_ism.py tests/test_capital_weekly_context_providers.py tests/test_capital_weekly_weekly_context.py
git commit -m "feat: publish required point-in-time macro releases"
```

---

### Task 7: Add Treasury Real Yields, Breakevens, And 5Y5Y

**Files:**
- Modify: `capital_weekly/macro_assets.py`
- Modify: `data/capital_weekly_macro_assets.csv`
- Modify: `tests/test_capital_weekly_macro_assets.py`
- Modify: `tests/test_capital_weekly_macro_as_of.py`

**Interfaces:**
- Produces: `align_series_histories(histories: Mapping[str, Iterable[dict]], input_codes: tuple[str, ...], calculator: Callable[[float, float], float]) -> list[dict]`.
- Produces: `calculate_five_year_five_year(be5: float, be10: float) -> float`.
- New series: `UST5Y`, `UST_REAL5Y`, `UST_REAL10Y`, `US_BE5Y`, `US_BE10Y`, `US_5Y5Y`.
- Preserves: all history is filtered to `date <= as_of_date` before any snapshot or derived-series calculation.

- [ ] **Step 1: Write failing parser, formula, alignment, and cutoff tests**

```python
def test_five_year_five_year_uses_registered_compounding_formula(self):
    expected = (((1.0 + 2.4 / 100.0) ** 2) / (1.0 + 2.1 / 100.0) - 1.0) * 100.0
    self.assertAlmostEqual(calculate_five_year_five_year(2.1, 2.4), expected, places=12)

def test_breakeven_uses_only_dates_shared_by_nominal_and_real_curves(self):
    result = align_series_histories(
        {
            "UST5Y": [{"date": date(2026, 8, 7), "value": 4.0}],
            "UST_REAL5Y": [
                {"date": date(2026, 8, 6), "value": 1.8},
                {"date": date(2026, 8, 7), "value": 1.9},
            ],
        },
        ("UST5Y", "UST_REAL5Y"),
        lambda nominal, real: nominal - real,
    )
    self.assertEqual(result, [{"date": date(2026, 8, 7), "value": 2.1}])
```

Add an integration test whose fake nominal and real Treasury CSVs contain `2026-08-10`; with `as_of_date=date(2026, 8, 9)`, every new series must report `latest_date == "2026-08-07"`.

- [ ] **Step 2: Run the macro tests and verify RED**

Run: `python3 -m unittest -v tests.test_capital_weekly_macro_assets tests.test_capital_weekly_macro_as_of`

Expected: FAIL because the real-curve provider, new series, and registered calculations do not exist.

- [ ] **Step 3: Add the official real-curve fetch**

Extend the Treasury provider map with `provider="us_treasury_real"`, fields `5 YR` and `10 YR`, and URL query `type=daily_treasury_real_yield_curve`. Keep the existing nominal URL query `type=daily_treasury_yield_curve`. Fetch the previous and current calendar years, then apply the shared `as_of_date` cutoff.

- [ ] **Step 4: Generalize registered calculations**

```python
def calculate_five_year_five_year(be5: float, be10: float) -> float:
    if be5 <= -100.0 or be10 <= -100.0:
        raise ValueError("Breakeven inputs must be greater than -100 percent")
    return (((1.0 + be10 / 100.0) ** 2) / (1.0 + be5 / 100.0) - 1.0) * 100.0

CALCULATED_SERIES = {
    "UST10Y2Y": (("UST10Y", "UST2Y"), lambda ten, two: ten - two, "curve-spread-v1"),
    "US_BE5Y": (("UST5Y", "UST_REAL5Y"), lambda nominal, real: nominal - real, "breakeven-v1"),
    "US_BE10Y": (("UST10Y", "UST_REAL10Y"), lambda nominal, real: nominal - real, "breakeven-v1"),
    "US_5Y5Y": (("US_BE5Y", "US_BE10Y"), calculate_five_year_five_year, "forward-inflation-v1"),
}
```

Calculated rows must store `calculation_id`, `formula_version`, and pipe-delimited `input_series_codes`. Observed rows leave those fields blank. Extend source-log rows with the same provider metadata introduced in Task 1 and set `known_as_of` to the latest eligible Treasury observation date.

- [ ] **Step 5: Update the macro universe deterministically**

Insert the six new fixed-income rows after `UST10Y2Y`. Use official Treasury source URLs and `change_unit=bp`. Shift existing sort orders by six so all `sort_order` values remain unique and contiguous.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `python3 -m unittest -v tests.test_capital_weekly_macro_assets tests.test_capital_weekly_macro_as_of tests.test_capital_weekly_macro_divergence`

Expected: all focused tests pass; configured macro series count is 47 and every new series has one detail row and one source-log row.

- [ ] **Step 7: Commit the rates expansion**

```bash
git add capital_weekly/macro_assets.py data/capital_weekly_macro_assets.csv tests/test_capital_weekly_macro_assets.py tests/test_capital_weekly_macro_as_of.py
git commit -m "feat: add real yields and inflation expectations"
```

---

### Task 8: Enforce Requiredness, Timestamp Cutoffs, And Manifest Domain Metadata

**Files:**
- Modify: `capital_weekly/weekly_release.py`
- Modify: `tests/test_capital_weekly_weekly_release.py`

**Interfaces:**
- Extends: `DatasetSpec` with `datetime_columns`, `future_date_columns`, and `required_indicator_families`.
- Extends manifest: top-level `warnings: list[str]` and `domains: list[dict]`.
- Each domain manifest row contains: `name`, `requiredness`, `configuration_state`, `status`, `coverage`, `latest_known_as_of`, `warnings`, `provider_version`, `schema_version`, and `formula_version`.

- [ ] **Step 1: Write failing validation and manifest tests**

Add one staged-week test for each behavior:

```python
def test_rejects_known_as_of_after_target_sunday(self):
    self.write_valid_staged_week()
    self.mutate_csv(
        "economic_releases.csv",
        lambda row: {**row, "known_as_of": "2026-08-10T08:30:00-04:00"},
    )
    with self.assertRaisesRegex(ReleaseValidationError, "known_as_of"):
        validate_staged_week(self.root, self.window)

def test_optional_provider_failure_becomes_manifest_warning(self):
    self.write_valid_staged_week()
    self.append_context_source_log(
        provider="optional_fixture",
        requiredness="optional",
        status="FETCH_FAILED",
    )
    manifest = validate_staged_week(self.root, self.window)
    self.assertTrue(any("optional_fixture" in warning for warning in manifest["warnings"]))
```

Also assert: a required provider failure rejects publication; a required economic table missing any of the nine families is rejected; an optional header-only table is accepted; a future event up to 28 days after Sunday is accepted only when `known_as_of` is eligible; and the manifest domain record reproduces provider/schema/formula versions from source logs.

- [ ] **Step 2: Run the release tests and verify RED**

Run: `python3 -m unittest -v tests.test_capital_weekly_weekly_release`

Expected: the new tests fail because timestamps, requiredness, warnings, domains, and economic-family coverage are not validated.

- [ ] **Step 3: Extend dataset validation**

Register `economic_releases.csv` as a required non-empty context dataset. Validate `release_at_bjt` and `known_as_of` as timezone-aware ISO timestamps, require `known_as_of <= target_sunday_cutoff(window.end)`, and require all nine configured families.

Split ordinary observation dates from future event dates. Market observation dates remain `<= window.end`; registered future event dates may be `<= window.end + timedelta(days=28)` only when the row's `known_as_of` remains within the target cutoff.

- [ ] **Step 4: Implement provider-status policy and domain manifests**

```python
REQUIRED_FAILURE_STATUSES = frozenset({
    "FETCH_FAILED", "POINT_IN_TIME_UNAVAILABLE", "INSUFFICIENT_DATA",
    "NOT_CONFIGURED",
})
OPTIONAL_WARNING_STATUSES = REQUIRED_FAILURE_STATUSES

def provider_warning(row: dict[str, str]) -> str | None:
    status = row["status"].strip().upper()
    if row["requiredness"] == "required" and status in REQUIRED_FAILURE_STATUSES:
        raise ReleaseValidationError(
            f"Required provider {row['provider']} has status {status}"
        )
    if row["requiredness"] == "optional" and status in OPTIONAL_WARNING_STATUSES:
        return f"Optional provider {row['provider']} has status {status}"
    return None
```

Aggregate coverage as successful configured identities divided by configured identities; do not treat `NOT_CONFIGURED` optional providers as successful. Sort domain entries and warnings by provider name for deterministic JSON.

- [ ] **Step 5: Register calculated Treasury provenance**

Extend `CALCULATED_SOURCE_POLICIES` with `US_BE5Y`, `US_BE10Y`, and `US_5Y5Y` dependency identities. Require each calculated row's declared inputs to exist as successful rows with HTTP(S) provenance.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `python3 -m unittest -v tests.test_capital_weekly_weekly_release tests.test_capital_weekly_weekly_context tests.test_capital_weekly_macro_assets`

Expected: all focused tests pass.

- [ ] **Step 7: Commit release validation**

```bash
git add capital_weekly/weekly_release.py tests/test_capital_weekly_weekly_release.py
git commit -m "feat: validate point-in-time release domains"
```

---

### Task 9: Verify The Offline Five-Pipeline Release And Document Operation

**Files:**
- Create: `tests/test_capital_weekly_point_in_time_release.py`
- Modify: `README.md`

**Interfaces:**
- Proves: a deterministic fake five-pipeline run publishes all point-in-time macro/rates outputs, exact hashes, domain coverage, and warnings.
- Documents: current-week refresh, historical-capture limitation, capture-root location, and audit interpretation.

- [ ] **Step 1: Write the failing offline release test**

Use a fake `runner` that creates all five pipeline directories and valid deterministic files. The macro bundle includes six new rates rows; the context bundle includes all nine economic families and one optional warning.

```python
def test_offline_release_records_point_in_time_domains_and_hashes(self):
    published = run_weekly_release(
        self.project_root,
        now_hkt=datetime(2026, 8, 11, 10, 0, tzinfo=ZoneInfo("Asia/Hong_Kong")),
        runner=self.fake_runner,
    )
    manifest = json.loads((published / "manifest.json").read_text())
    self.assertEqual(manifest["status"], "complete")
    self.assertEqual(manifest["week_end"], "2026-08-09")
    self.assertTrue(any(item["name"] == "economic_releases" for item in manifest["domains"]))
    self.assertTrue(all(len(item["sha256"]) == 64 for item in manifest["files"]))
    self.assertFalse(self.network_was_called)
```

- [ ] **Step 2: Run the offline release test and verify RED**

Run: `python3 -m unittest -v tests.test_capital_weekly_point_in_time_release`

Expected: FAIL until the fake release and manifest contract cover the new files and domains.

- [ ] **Step 3: Complete the deterministic fixture runner**

Build expected CSV rows from literal dictionaries in the test. Do not call production parsers to calculate expected values and do not use network mocks that can accept arbitrary URLs. The fake runner must assert the exact five commands and exact target date before writing outputs.

- [ ] **Step 4: Document the operator contract**

Add a `Point-in-time macro and rates` README section with these commands:

```bash
python3 scripts/refresh_capital_weekly.py --as-of-date 2026-08-09
python3 -m unittest -v tests.test_capital_weekly_point_in_time_release
python3 -m unittest -v
```

State that historical ISM weeks require an eligible immutable capture, required point-in-time failures block publication, optional failures appear in manifest warnings, and routine tests never perform a real refresh.

- [ ] **Step 5: Run every focused module for this plan and verify GREEN**

Run:

```bash
python3 -m unittest -v \
  tests.test_capital_weekly_point_in_time \
  tests.test_capital_weekly_economic_releases \
  tests.test_capital_weekly_economic_bls \
  tests.test_capital_weekly_economic_bea \
  tests.test_capital_weekly_economic_census \
  tests.test_capital_weekly_economic_ism \
  tests.test_capital_weekly_macro_assets \
  tests.test_capital_weekly_macro_as_of \
  tests.test_capital_weekly_weekly_context \
  tests.test_capital_weekly_context_providers \
  tests.test_capital_weekly_weekly_release \
  tests.test_capital_weekly_point_in_time_release
```

Expected: all focused tests pass.

- [ ] **Step 6: Run the full repository suite**

Run: `python3 -m unittest -v`

Expected: all repository tests pass with no real network requests.

- [ ] **Step 7: Commit the offline verification and documentation**

```bash
git add tests/test_capital_weekly_point_in_time_release.py README.md
git commit -m "test: verify point-in-time weekly macro release"
```

## Final Review Gate

After Task 9, generate a whole-plan diff from the merge base and run a fresh code review. The reviewer must explicitly check:

- every required indicator family has a point-in-time proof path;
- no current official time-series value is used to recreate an older vintage;
- all derived values expose registered inputs and formula versions;
- required failures block publication while optional failures only warn;
- the five-pipeline count and command boundary remain unchanged;
- no Next.js files or unrelated dirty files were modified;
- focused and full `unittest` evidence is fresh.

Only after that review is clean should the branch-finishing workflow be invoked.
