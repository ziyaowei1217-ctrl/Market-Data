# Daily Market Data System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-command daily market-research pipeline with revision-aware historical CSVs, dated snapshots, explicit source tiers, and at least 54 operational indicators from the agreed 68-indicator research core.

**Architecture:** A new `capital_weekly.daily` package owns the indicator registry, normalized row model, history merge, snapshot selection, provider orchestration, and atomic publication. Source-specific providers adapt official macro, Treasury, positioning, catalyst, and S&P aggregate data plus the existing market collectors into one long-form schema, while the current weekly collectors and workbook flow remain unchanged.

**Tech Stack:** Python 3.9+, pandas, requests, openpyxl, unittest, existing Node workbook verifier.

## Global Constraints

- The primary command is `python3 scripts/run_daily.py --as-of-date YYYY-MM-DD`.
- Generated history lives under `outputs/history/`; dated snapshots live under `outputs/daily/YYYYMMDD/`.
- United States data is the research core; existing China, Hong Kong, and global series remain enabled.
- Every series is labelled `official`, `public_proxy`, or `unavailable_without_estimates`.
- A provider failure is visible but does not stop unrelated providers.
- Repeating a date is deterministic and does not duplicate history.
- Macro revisions create new vintages and never overwrite older values.
- No generated market data is committed to Git.
- Existing weekly CSV schemas, commands, workbook names, and tests remain compatible.
- Production behavior is implemented test-first with fixture-based tests and no live network dependency in the default suite.

---

### Task 1: Core Indicator Registry And Normalized Models

**Files:**
- Create: `capital_weekly/daily/__init__.py`
- Create: `capital_weekly/daily/model.py`
- Create: `capital_weekly/daily/registry.py`
- Create: `data/capital_daily_indicator_registry.csv`
- Create: `tests/test_capital_daily_registry.py`

**Interfaces:**
- Produces: `IndicatorDefinition`, `DailyProviderResult`, `ProviderStatus`, `NORMALIZED_COLUMNS`, `load_indicator_registry(path)`, and `registry_summary(definitions)`.
- Consumes: only Python standard library and the tracked CSV registry.
- Later tasks rely on `IndicatorDefinition.series_code`, `.dataset`, `.frequency`, `.unit`, `.source_tier`, `.operational`, and `.max_stale_days` retaining these exact names.

- [ ] **Step 1: Write the failing registry and model tests**

```python
from datetime import date
import unittest

from capital_weekly.daily.model import DailyProviderResult, ProviderStatus
from capital_weekly.daily.registry import load_indicator_registry, registry_summary


class DailyRegistryTests(unittest.TestCase):
    def test_registry_contains_the_68_item_research_core(self):
        definitions = load_indicator_registry()
        summary = registry_summary(definitions)
        self.assertEqual(summary["core_total"], 68)
        self.assertGreaterEqual(summary["operational_total"], 54)
        self.assertEqual(
            summary["requires_estimates"],
            {"SP500_NTM_EPS", "SP500_EPS_REVISIONS", "SP500_FORWARD_PE"},
        )

    def test_provider_result_rejects_rows_without_a_dataset(self):
        status = ProviderStatus(
            provider="fixture", status="OK", as_of_date=date(2026, 8, 10)
        )
        with self.assertRaisesRegex(ValueError, "dataset"):
            DailyProviderResult(rows=({"series_code": "CPI"},), statuses=(status,))
```

- [ ] **Step 2: Run the new test and verify the missing-package failure**

Run: `python3 -m unittest -v tests.test_capital_daily_registry`

Expected: `ModuleNotFoundError: No module named 'capital_weekly.daily'`.

- [ ] **Step 3: Implement the normalized dataclasses and validation**

```python
NORMALIZED_COLUMNS = (
    "dataset", "series_code", "series_name", "observation_date",
    "vintage_date", "as_of_date", "value", "unit", "frequency",
    "source", "source_url", "source_tier", "qc_flag",
)

@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    status: str
    as_of_date: date
    dataset: str | None = None
    observations: int = 0
    latest_date: date | None = None
    source: str | None = None
    source_url: str | None = None
    source_tier: str | None = None
    elapsed_ms: int = 0
    notes: str = ""

@dataclass(frozen=True)
class DailyProviderResult:
    rows: tuple[dict, ...]
    statuses: tuple[ProviderStatus, ...]
    raw_files: tuple[tuple[str, bytes], ...] = ()

    def __post_init__(self):
        for row in self.rows:
            missing = set(NORMALIZED_COLUMNS) - set(row)
            if missing:
                raise ValueError(f"Normalized row missing required fields: {', '.join(sorted(missing))}")
```

- [ ] **Step 4: Create the complete 68-row registry**

Create one `research_core=1` row for every agreed item, using these stable codes:

```text
REGIME: REAL_GDP,CPI,CORE_CPI,PCE,CORE_PCE,NFP,UNEMPLOYMENT,ISM_MFG,ISM_SERVICES,RETAIL_SALES,FED_FUNDS
PRICING: FED_IMPLIED_PATH,UST2Y,UST5Y,UST10Y,UST30Y,UST2S10S,UST10Y_REAL,UST10Y_BREAKEVEN,USIG_OAS,USHY_OAS
CROSS_ASSET: SP500,NASDAQ100,RUSSELL2000,HSI,HSCEI,DXY,USDJPY,USDCNH,GOLD,WTI,COPPER,VIX,MOVE
INTERNALS: XLE,XLB,XLI,XLY,XLP,XLV,XLF,XLK,XLC,XLU,XLRE,SP500_EQUAL_WEIGHT,US_GROWTH,US_VALUE,US_MOMENTUM,ADVANCE_DECLINE,PCT_ABOVE_50DMA,PCT_ABOVE_200DMA
FUNDAMENTALS: SP500_NTM_EPS,SP500_EPS_REVISIONS,SP500_EPS_GROWTH,SP500_FORWARD_PE,SP500_NET_MARGIN
POSITIONING: CFTC_POSITIONING,ETF_FLOWS,SHORT_INTEREST,PUT_CALL,OPTIONS_OI,VIX_TERM_STRUCTURE
CATALYSTS: MACRO_CALENDAR,FOMC_CALENDAR,EARNINGS_CALENDAR,TREASURY_AUCTIONS,IPO_MA_CALENDAR
```

Use these registry columns exactly:

```text
research_core,dataset,series_code,series_name,provider,provider_symbol,frequency,unit,source,source_url,source_tier,operational,max_stale_days,sort_order,notes
```

Mark the three commercial-estimates codes as `unavailable_without_estimates` and `operational=false`. Mark public but deferred series explicitly rather than omitting them. Include enough official and existing proxy routes for `operational_total >= 54`.

- [ ] **Step 5: Run registry tests and the existing import smoke test**

Run: `python3 -m unittest -v tests.test_capital_daily_registry tests.test_capital_weekly_weekly_context`

Expected: all tests pass.

- [ ] **Step 6: Commit the registry and normalized model**

```bash
git add capital_weekly/daily/__init__.py capital_weekly/daily/model.py capital_weekly/daily/registry.py data/capital_daily_indicator_registry.csv tests/test_capital_daily_registry.py
git commit -m "feat: define daily indicator registry"
```

### Task 2: Revision-Aware History And Snapshot Selection

**Files:**
- Create: `capital_weekly/daily/history.py`
- Create: `tests/test_capital_daily_history.py`

**Interfaces:**
- Consumes: normalized row dictionaries using `NORMALIZED_COLUMNS`.
- Produces: `normalize_frame(frame)`, `merge_history(existing, incoming)`, `select_latest_snapshot(history, as_of_date)`, `validate_freshness(snapshot, definitions, as_of_date)`, and `history_filename(dataset)`.
- Identity key: `dataset,series_code,observation_date,vintage_date`.

- [ ] **Step 1: Write failing history tests for idempotency and revisions**

```python
from datetime import date
import unittest
import pandas as pd

from capital_weekly.daily.history import merge_history, select_latest_snapshot


def row(value, vintage):
    return {
        "dataset": "macro_actuals", "series_code": "CPI",
        "series_name": "Consumer Price Index",
        "observation_date": "2026-06-01", "vintage_date": vintage,
        "as_of_date": vintage, "value": value, "unit": "index",
        "frequency": "monthly", "source": "BLS via FRED",
        "source_url": "https://fred.stlouisfed.org/series/CPIAUCSL",
        "source_tier": "official", "qc_flag": "OK",
    }


class DailyHistoryTests(unittest.TestCase):
    def test_identical_rerun_does_not_create_a_new_vintage(self):
        existing = pd.DataFrame([row(321.5, "2026-07-15")])
        incoming = pd.DataFrame([row(321.5, "2026-08-10")])
        merged = merge_history(existing, incoming)
        self.assertEqual(len(merged), 1)

    def test_changed_macro_value_creates_a_new_vintage(self):
        existing = pd.DataFrame([row(321.5, "2026-07-15")])
        incoming = pd.DataFrame([row(321.7, "2026-08-10")])
        merged = merge_history(existing, incoming)
        self.assertEqual(len(merged), 2)

    def test_snapshot_never_uses_a_future_vintage(self):
        history = pd.DataFrame([
            row(321.5, "2026-07-15"), row(321.7, "2026-08-10")
        ])
        snapshot = select_latest_snapshot(history, date(2026, 8, 1))
        self.assertEqual(snapshot.iloc[0]["value"], 321.5)
```

- [ ] **Step 2: Run the test and verify the missing-module failure**

Run: `python3 -m unittest -v tests.test_capital_daily_history`

Expected: import failure for `capital_weekly.daily.history`.

- [ ] **Step 3: Implement deterministic normalization and history merge**

```python
IDENTITY_COLUMNS = ["dataset", "series_code", "observation_date", "vintage_date"]

def merge_history(existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    old = normalize_frame(existing)
    new = normalize_frame(incoming)
    accepted = []
    for record in new.to_dict("records"):
        same_observation = old[
            (old["dataset"] == record["dataset"])
            & (old["series_code"] == record["series_code"])
            & (old["observation_date"] == record["observation_date"])
        ]
        latest = same_observation.sort_values("vintage_date").tail(1)
        if not latest.empty and latest.iloc[0]["value"] == record["value"]:
            continue
        accepted.append(record)
    combined = pd.concat([old, pd.DataFrame(accepted)], ignore_index=True)
    if combined.duplicated(IDENTITY_COLUMNS).any():
        raise ValueError("Duplicate daily history identity key")
    return combined.sort_values(IDENTITY_COLUMNS).reset_index(drop=True)
```

`normalize_frame` must parse all three date fields, coerce only finite numeric values, assign `INVALID_VALUE` when needed, and preserve the exact normalized column order. `select_latest_snapshot` filters `vintage_date <= as_of_date`, then selects the latest observation and latest eligible vintage per `dataset,series_code`.

- [ ] **Step 4: Add freshness tests and implementation**

Add tests proving daily series use `max_stale_days`, monthly and quarterly series do not use the daily threshold, and future observation dates raise `ValueError`. Implement `validate_freshness` to return rows with explicit `STALE` flags instead of deleting them.

- [ ] **Step 5: Run daily history and existing return tests**

Run: `python3 -m unittest -v tests.test_capital_daily_history tests.test_capital_weekly_returns`

Expected: all tests pass.

- [ ] **Step 6: Commit the history layer**

```bash
git add capital_weekly/daily/history.py tests/test_capital_daily_history.py
git commit -m "feat: add revision-aware daily history"
```

### Task 3: Atomic Publisher, Orchestrator, And One-Command CLI

**Files:**
- Create: `capital_weekly/daily/publisher.py`
- Create: `capital_weekly/daily/orchestrator.py`
- Create: `capital_weekly/daily/providers/__init__.py`
- Create: `scripts/run_daily.py`
- Create: `tests/test_capital_daily_orchestrator.py`
- Create: `tests/test_run_daily_cli.py`

**Interfaces:**
- Produces: `run_daily(providers, registry, outputs_root, as_of_date) -> RunSummary`.
- Provider signature: `Callable[[date], DailyProviderResult]`.
- Produces: `publish_daily_bundle(outputs_root, as_of_date, histories, snapshots, statuses, manifest)`.
- CLI options: `--as-of-date`, `--outputs-root`, `--registry`, and `--no-raw-cache`.

- [ ] **Step 1: Write the failing orchestrator integration test**

```python
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from capital_weekly.daily.model import DailyProviderResult, ProviderStatus
from capital_weekly.daily.orchestrator import run_daily


class DailyOrchestratorTests(unittest.TestCase):
    def test_one_provider_failure_does_not_block_a_valid_snapshot(self):
        def successful(run_date):
            return DailyProviderResult(
                rows=(normalized_sp500_row(run_date),),
                statuses=(ProviderStatus(
                    provider="fixture_ok", dataset="cross_asset", status="OK",
                    observations=1, as_of_date=run_date,
                ),),
            )

        def failed(run_date):
            raise RuntimeError("temporary provider failure")

        with TemporaryDirectory() as directory:
            summary = run_daily(
                {"fixture_ok": successful, "fixture_bad": failed},
                registry=fixture_registry(), outputs_root=Path(directory),
                as_of_date=date(2026, 8, 10),
            )
            daily = Path(directory) / "daily" / "20260810"
            self.assertTrue((daily / "snapshot.csv").exists())
            self.assertIn("FETCH_FAILED", (daily / "source_log.csv").read_text())
            self.assertEqual(summary.published_date, date(2026, 8, 10))
```

- [ ] **Step 2: Run tests and verify the missing orchestrator failure**

Run: `python3 -m unittest -v tests.test_capital_daily_orchestrator`

Expected: import failure for the orchestrator.

- [ ] **Step 3: Implement provider isolation and dataset grouping**

`run_daily` must execute every callable, catch exceptions into a `ProviderStatus(status="FETCH_FAILED")`, combine successful rows, split them by `dataset`, merge each dataset with its existing `outputs/history/<dataset>.csv`, select an as-of snapshot, and build a manifest with registry coverage, provider counts, row counts, and calculated-series metadata. Create `capital_weekly.daily.providers.build_default_daily_providers` with a valid empty ordered mapping in this task so the CLI has a stable import; later provider tasks populate it.

- [ ] **Step 4: Implement rollback-safe publication**

Use a staging directory beneath `outputs_root`. Write all history and daily files to staging, validate their required columns and manifest counts, move existing targets to uniquely named backups, publish staged targets with `os.replace`, and restore backups if any replace fails. Remove backups only after every target succeeds.

Required daily files are:

```text
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
```

- [ ] **Step 5: Add rerun and rollback tests**

Add tests proving a second identical run leaves history row counts unchanged, replaces the dated directory, and restores both history and snapshot files when an injected `os.replace` failure occurs.

- [ ] **Step 6: Write the CLI test before the CLI**

Patch `capital_weekly.daily.providers.build_default_daily_providers` and `run_daily`, invoke `scripts/run_daily.py` with `--as-of-date 2026-08-10 --outputs-root <temp>`, and assert that the parsed date and output root are passed unchanged.

- [ ] **Step 7: Implement `scripts/run_daily.py`**

```python
def main() -> int:
    args = parser().parse_args()
    run_date = date.fromisoformat(args.as_of_date) if args.as_of_date else date.today()
    registry = load_indicator_registry(args.registry)
    providers = build_default_daily_providers(
        registry=registry, raw_cache=not args.no_raw_cache
    )
    summary = run_daily(
        providers, registry=registry,
        outputs_root=Path(args.outputs_root), as_of_date=run_date,
    )
    print(f"saved: {summary.daily_directory}")
    return 0
```

- [ ] **Step 8: Run orchestrator and CLI tests**

Run: `python3 -m unittest -v tests.test_capital_daily_orchestrator tests.test_run_daily_cli`

Expected: all tests pass.

- [ ] **Step 9: Commit the daily framework**

```bash
git add capital_weekly/daily/publisher.py capital_weekly/daily/orchestrator.py capital_weekly/daily/providers/__init__.py scripts/run_daily.py tests/test_capital_daily_orchestrator.py tests/test_run_daily_cli.py
git commit -m "feat: add one-command daily pipeline"
```

### Task 4: Official Macro Actuals And Treasury Pricing

**Files:**
- Modify: `capital_weekly/daily/providers/__init__.py`
- Create: `capital_weekly/daily/providers/macro.py`
- Create: `tests/test_capital_daily_macro_provider.py`
- Modify: `capital_weekly/macro_assets.py`
- Modify: `data/capital_weekly_macro_assets.csv`
- Modify: `tests/test_capital_weekly_macro_assets.py`

**Interfaces:**
- Produces: `parse_fred_observations(text, definition, run_date)`, `fetch_macro_actuals(run_date, session, definitions)`, and `build_macro_provider(session, definitions)`.
- Extends `_fetch_config_history` with `us_treasury_real` and US 5-year nominal support.
- Calculated `UST10Y_BREAKEVEN = UST10Y - UST10Y_REAL` only on shared dates.

- [ ] **Step 1: Write failing FRED macro parser tests**

Use a CSV fixture with `observation_date,CPIAUCSL`, a missing-value row containing `.`, and two valid monthly rows. Assert canonical rows use `series_code=CPI`, retain observation dates, set `vintage_date` and `as_of_date` to the run date, use the registry unit, and reject a missing value column.

- [ ] **Step 2: Run the parser test and confirm it fails because the provider is missing**

Run: `python3 -m unittest -v tests.test_capital_daily_macro_provider`

Expected: import failure for `capital_weekly.daily.providers.macro`.

- [ ] **Step 3: Implement the eight official macro mappings**

Use FRED graph CSV routes without an API key:

```python
FRED_MACRO_SERIES = {
    "REAL_GDP": "GDPC1",
    "CPI": "CPIAUCSL",
    "CORE_CPI": "CPILFESL",
    "PCE": "PCEPI",
    "CORE_PCE": "PCEPILFE",
    "NFP": "PAYEMS",
    "UNEMPLOYMENT": "UNRATE",
    "RETAIL_SALES": "RSXFS",
}
```

Fetch `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<symbol>&cosd=<start>&coed=<run_date>`, parse all available observations, and return granular source statuses. The history merge suppresses unchanged daily refetches and creates a new run-date vintage only when an observation changes.

- [ ] **Step 4: Write failing nominal, real-yield, and breakeven tests**

Add a Treasury fixture containing `Date,5 Yr` and a real-yield fixture containing `Date,10 YR`. Assert the new provider dispatch returns 5-year nominal and 10-year real histories, and assert `align_curve_spread` or a new generic `align_difference` calculates nominal minus real only on shared dates.

- [ ] **Step 5: Extend the existing Treasury provider and configuration**

Add these rows to `capital_weekly_macro_assets.csv` with unique sort orders:

```text
UST5Y,us_treasury,5-year,percent,bp
UST10Y_REAL,us_treasury_real,10-year,percent,bp
UST10Y_BREAKEVEN,calculated,UST10Y-UST10Y_REAL,percentage_points,bp
```

Update nominal field mapping to include `"5-year": "5 Yr"`. Implement the real-yield URL with `type=daily_treasury_real_yield_curve`, map `10-year` to `10 YR`, and generalize calculated dispatch so the existing 2s10s series and new breakeven series both use explicitly configured inputs.

- [ ] **Step 6: Register the macro provider in `build_default_daily_providers`**

Return an ordered mapping containing `macro_actuals` before market providers. Inject a shared requests session with the repository's retry and User-Agent behavior.

- [ ] **Step 7: Run focused and regression tests**

Run: `python3 -m unittest -v tests.test_capital_daily_macro_provider tests.test_capital_weekly_macro_assets tests.test_capital_weekly_macro_divergence`

Expected: all tests pass.

- [ ] **Step 8: Commit macro actuals and Treasury pricing**

```bash
git add capital_weekly/daily/providers/__init__.py capital_weekly/daily/providers/macro.py capital_weekly/macro_assets.py data/capital_weekly_macro_assets.csv tests/test_capital_daily_macro_provider.py tests/test_capital_weekly_macro_assets.py
git commit -m "feat: add daily macro actuals and real yields"
```

### Task 5: Existing Market Bridge, Missing Cross-Asset Series, And Style Internals

**Files:**
- Create: `capital_weekly/daily/providers/market.py`
- Create: `data/capital_daily_style_proxies.csv`
- Create: `tests/test_capital_daily_market_provider.py`
- Modify: `data/capital_weekly_equity_indices.csv`
- Modify: `data/capital_weekly_macro_assets.csv`
- Modify: `capital_weekly/macro_assets.py`
- Modify: `tests/test_capital_weekly_equity_indices.py`

**Interfaces:**
- Produces: `map_snapshot_rows(frame, definitions, dataset, run_date)` and `fetch_market_bundle(run_date)`.
- Consumes: `fetch_equity_indices`, `fetch_gics_sectors`, `fetch_macro_assets`, and a style-proxy universe using the existing US security history parser.
- Produces normalized datasets `rates_pricing`, `cross_asset`, and `internals`.

- [ ] **Step 1: Write failing mapping tests with fixture DataFrames**

Test that an existing snapshot row with `latest_date`, `latest_value`, and `qc_flag` maps to the canonical dates, value, source tier, unit, and dataset. Test that a `FETCH_FAILED` legacy row is excluded from normalized values but retained as a source status.

- [ ] **Step 2: Run the mapping test and verify the provider import fails**

Run: `python3 -m unittest -v tests.test_capital_daily_market_provider`

Expected: import failure for `capital_weekly.daily.providers.market`.

- [ ] **Step 3: Add missing cross-asset configuration**

Add:

```text
HSCEI: provider=tencent_kline, provider_symbol=hkHSCEI, source_tier=public_proxy
USDJPY: provider=yahoo_chart, provider_symbol=JPY=X, unit=jpy_per_usd, source_tier=public_proxy
COPPER: provider=yahoo_chart, provider_symbol=HG=F, unit=usd_per_pound, source_tier=public_proxy
```

Keep the existing HSI, USD/CNH, gold, WTI, DXY, and global rows unchanged. Add a parser/config test proving all three new symbols load with unique codes and deterministic sort orders.

- [ ] **Step 4: Add the four style proxies in a separate tracked universe**

Create `capital_daily_style_proxies.csv` with the same columns used by the existing US equity history collector and these rows:

```text
SP500_EQUAL_WEIGHT,RSP,S&P 500 Equal Weight ETF proxy
US_GROWTH,IWF,Russell 1000 Growth ETF proxy
US_VALUE,IWD,Russell 1000 Value ETF proxy
US_MOMENTUM,MTUM,MSCI USA Momentum ETF proxy
```

All four use `public_proxy`, USD, daily frequency, and distinct notes stating that ETF returns are not official factor-index levels.

- [ ] **Step 5: Implement and register the market bridge**

Call the existing collectors with injected universe paths, map their latest valid observations into normalized rows, preserve their granular source logs, and return one `DailyProviderResult`. Do not change any legacy output schema.

- [ ] **Step 6: Run market and legacy tests**

Run: `python3 -m unittest -v tests.test_capital_daily_market_provider tests.test_capital_weekly_equity_indices tests.test_capital_weekly_gics_sectors tests.test_capital_weekly_macro_assets`

Expected: all tests pass.

- [ ] **Step 7: Commit the market bridge and new series**

```bash
git add capital_weekly/daily/providers/market.py data/capital_daily_style_proxies.csv data/capital_weekly_equity_indices.csv data/capital_weekly_macro_assets.csv capital_weekly/macro_assets.py tests/test_capital_daily_market_provider.py tests/test_capital_weekly_equity_indices.py
git commit -m "feat: extend daily cross-asset and internals data"
```

### Task 6: Public Positioning And Treasury Auction Catalysts

**Files:**
- Create: `capital_weekly/daily/providers/positioning.py`
- Create: `capital_weekly/daily/providers/catalysts.py`
- Create: `data/capital_daily_short_interest_symbols.csv`
- Create: `tests/test_capital_daily_positioning_provider.py`
- Create: `tests/test_capital_daily_catalysts_provider.py`
- Modify: `capital_weekly/daily/providers/__init__.py`

**Interfaces:**
- Produces: `parse_finra_short_interest(payload)`, `parse_cboe_put_call_csv(text)`, `parse_cboe_vix_curve(text, run_date)`, and `fetch_public_positioning(run_date, session)`.
- Produces: `parse_treasury_auctions(payload, start, end)` and `fetch_treasury_auctions(run_date, session)`.
- Reuses existing CFTC rows through the weekly context provider without relabelling FINRA margin as short interest.

- [ ] **Step 1: Write failing FINRA short-interest tests**

Use a JSON fixture with `issueSymbolIdentifier`, `settlementDate`, `currentShortPositionQuantity`, `previousShortPositionQuantity`, `averageDailyVolumeQuantity`, and `daysToCoverQuantity`. Assert numeric normalization, date parsing, symbol filtering, duplicate rejection, and that the dataset is `positioning` with `series_code=SHORT_INTEREST`.

- [ ] **Step 2: Write failing Cboe put/call and VIX curve tests**

Use a put/call CSV fixture with Date, Calls, Puts, Total, and Put/Call Ratio. Use a VIX settlement fixture with contract symbol, expiration date, and settlement price. Assert front and second monthly contracts are selected by expiration, term slope is `second_settlement - front_settlement`, and expired contracts are excluded.

- [ ] **Step 3: Run positioning tests and verify missing-provider failures**

Run: `python3 -m unittest -v tests.test_capital_daily_positioning_provider`

Expected: import failure for the new positioning provider.

- [ ] **Step 4: Implement official public positioning fetches**

Use FINRA's Equity Short Interest data route for configured symbols and Cboe's official historical put/call and daily futures settlement downloads. Create `capital_daily_short_interest_symbols.csv` with enabled rows for `SPY`, `QQQ`, and `IWM`, including a note that these are liquid market proxies rather than an aggregate of every index constituent.

The provider returns separate normalized rows for short quantity, days to cover, total put/call ratio, front VIX future, second VIX future, and VIX curve slope. Preserve source URLs and official source tier.

- [ ] **Step 5: Write failing Treasury auction parser tests**

Use an announced-auctions JSON fixture with `cusip`, `securityTerm`, `announcementDate`, `auctionDate`, `issueDate`, `maturityDate`, and `offeringAmount`. Assert the requested date window is applied, stable event IDs are deterministic, numeric offering amounts are normalized, and duplicate CUSIP/auction-date pairs raise `ValueError`.

- [ ] **Step 6: Implement TreasuryDirect announced-auction collection**

Fetch `https://www.treasurydirect.gov/TA_WS/securities/announced?format=json`, retain auctions whose auction date falls in the run-date monitoring window, and emit catalyst rows with source `U.S. TreasuryDirect`. Combine these rows with the existing BLS, Census, and Federal Reserve event providers through a daily adapter.

- [ ] **Step 7: Register positioning and catalyst providers**

Add ordered default-provider entries after market data. Ensure the same shared session is used and that each underlying source writes its own status row.

- [ ] **Step 8: Run focused and existing context tests**

Run: `python3 -m unittest -v tests.test_capital_daily_positioning_provider tests.test_capital_daily_catalysts_provider tests.test_capital_weekly_positioning tests.test_capital_weekly_events tests.test_capital_weekly_context_providers`

Expected: all tests pass.

- [ ] **Step 9: Commit positioning and catalysts**

```bash
git add capital_weekly/daily/providers/positioning.py capital_weekly/daily/providers/catalysts.py capital_weekly/daily/providers/__init__.py data/capital_daily_short_interest_symbols.csv tests/test_capital_daily_positioning_provider.py tests/test_capital_daily_catalysts_provider.py
git commit -m "feat: add public positioning and auction catalysts"
```

### Task 7: S&P 500 Aggregate Actual Fundamentals

**Files:**
- Create: `capital_weekly/daily/providers/fundamentals.py`
- Create: `tests/test_capital_daily_fundamentals_provider.py`
- Modify: `capital_weekly/daily/providers/__init__.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `parse_sp500_actuals_xlsx(content, run_date)` and `fetch_sp500_actuals(run_date, session, local_path=None)`.
- Produces normalized codes `SP500_EPS_GROWTH` and `SP500_NET_MARGIN` only from actual periods.
- Accepts optional environment variable `SP500_EARNINGS_XLSX` for a user-downloaded current S&P workbook when the public web route blocks automated access.

- [ ] **Step 1: Write a failing semantic workbook parser test**

Build an in-memory workbook with openpyxl containing a title row, a header row with Period, Operating EPS, Revenue, and Net Income, and two actual quarterly rows plus one estimate row. Assert the parser ignores the estimate, calculates year-over-year EPS growth from matching quarters, calculates `net_income / revenue`, and uses the workbook publication date as `vintage_date`.

- [ ] **Step 2: Run the test and confirm missing dependencies/provider behavior**

Run: `python3 -m unittest -v tests.test_capital_daily_fundamentals_provider`

Expected: import failure for the fundamentals provider.

- [ ] **Step 3: Add the public workbook dependency and parser**

Add `openpyxl>=3.1,<4` to `requirements.txt`. Implement workbook validation by OOXML magic bytes, semantic header search rather than fixed cell addresses, explicit actual-versus-estimate classification, finite numeric validation, and clear errors when actual EPS, revenue, or net income fields are absent.

- [ ] **Step 4: Implement fetch with transparent fallback**

If `SP500_EARNINGS_XLSX` points to a readable file, parse that file and record its absolute path only in runtime diagnostics, not tracked output. Otherwise attempt the documented S&P public workbook URL. An HTML block page, login response, or non-OOXML payload must produce an explicit `FETCH_FAILED`/`NOT_CONFIGURED` source status and must not fabricate values.

- [ ] **Step 5: Register fundamentals provider and run tests**

Run: `python3 -m unittest -v tests.test_capital_daily_fundamentals_provider tests.test_capital_daily_orchestrator`

Expected: all tests pass, including failure isolation when no live workbook is available.

- [ ] **Step 6: Commit aggregate fundamentals support**

```bash
git add capital_weekly/daily/providers/fundamentals.py capital_weekly/daily/providers/__init__.py tests/test_capital_daily_fundamentals_provider.py requirements.txt
git commit -m "feat: add aggregate actual fundamentals"
```

### Task 8: Public Documentation, End-To-End Contract, And Release Verification

**Files:**
- Create: `tests/test_capital_daily_end_to_end.py`
- Modify: `README.md`
- Modify: `.env.example` if it exists; otherwise document environment variables only in `README.md`

**Interfaces:**
- Consumes: the complete daily provider registry and orchestrator.
- Produces: a user-facing installation and one-command run guide plus an offline end-to-end release contract.

- [ ] **Step 1: Write the failing end-to-end contract test**

Inject one fixture provider per dataset, run into a temporary output root, and assert:

```python
expected_daily = {
    "snapshot.csv", "macro_actuals.csv", "rates_pricing.csv",
    "cross_asset.csv", "internals.csv", "fundamentals.csv",
    "positioning.csv", "catalysts.csv", "source_log.csv", "manifest.json",
}
self.assertEqual({p.name for p in daily.iterdir() if p.is_file()}, expected_daily)
self.assertEqual(manifest["research_core_total"], 68)
self.assertGreaterEqual(manifest["operational_total"], 54)
self.assertEqual(manifest["as_of_date"], "2026-08-10")
```

Run it once to confirm it fails on the first missing integration detail before making the final integration fix.

- [ ] **Step 2: Complete default-provider and manifest integration**

Ensure `build_default_daily_providers` returns macro, market, positioning, catalyst, and fundamentals providers in deterministic order. Ensure every configured operational dataset produces a file even when all of its providers fail; the file may be header-only but its source failures must appear in the log and manifest.

- [ ] **Step 3: Update README with exact commands and limitations**

Document:

```bash
git clone https://github.com/ziyaowei1217-ctrl/Market-Data.git
cd Market-Data
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 scripts/run_daily.py --as-of-date 2026-08-10
```

Explain `outputs/history/`, `outputs/daily/YYYYMMDD/`, source tiers, rerun behavior, source-log inspection, optional `SP500_EARNINGS_XLSX`, existing `EIA_API_KEY` and `SEC_USER_AGENT`, public-proxy limitations, and the separate Codex-only workbook builder limitation.

- [ ] **Step 4: Run the complete Python test suite**

Run: `python3 -m unittest -v`

Expected: all Python tests pass with zero failures and zero errors.

- [ ] **Step 5: Run the Node workbook contract suite**

Run: `node --test tests/test_verify_weekly_workbooks.mjs`

Expected: both workbook verifier contract tests pass.

- [ ] **Step 6: Run static and repository checks**

Run:

```bash
python3 -m compileall -q capital_weekly scripts tests
git diff --check
git status -sb
```

Expected: compilation exits zero, diff check is empty, and status lists only intended daily-system files.

- [ ] **Step 7: Run an optional smallest live smoke test**

Run a dated daily command with raw caching disabled. Inspect `source_log.csv` and verify that failures remain isolated. Do not require every external provider to be `OK`; require a structurally valid daily directory and explicit statuses for all attempted sources.

- [ ] **Step 8: Commit documentation and final integration**

```bash
git add README.md tests/test_capital_daily_end_to_end.py
git commit -m "docs: document daily market data workflow"
```

- [ ] **Step 9: Final verification before push**

Re-run the complete Python suite, Node suite, compile check, `git diff --check`, and `git status -sb`. Record exact pass counts and the commit range for the final handoff before pushing `main`.
