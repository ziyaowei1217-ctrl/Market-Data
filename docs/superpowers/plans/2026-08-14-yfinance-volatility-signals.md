# Yahoo Volatility Signals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional, point-in-time-correct `yfinance` provider that publishes five Cboe volatility index levels and three deterministic term-structure metrics into Capital Weekly's existing financial-conditions context.

**Architecture:** A new focused volatility module owns configuration validation, Yahoo DataFrame normalization, target-Sunday truncation, matched-date calculations, and raw serialization. The existing provider registry composes that module with `yfinance.download`, while the weekly-release validator narrowly allows `FETCH_FAILED` only for this optional provider identity.

**Tech Stack:** Python 3, pandas, yfinance 1.x, unittest, existing Capital Weekly provider and atomic-release contracts.

## Global Constraints

- Work only in `/Users/a1-6/Documents/market data`; do not modify the Next.js repository.
- Preserve the existing five-pipeline atomic release and existing CSV schemas.
- Add `yfinance>=1.5,<2`; do not add another Yahoo client or browser automation.
- Treat Yahoo Finance as an optional public research source suitable only for the local desktop product.
- Apply the target-Sunday cutoff before selecting any value or calculating any metric.
- Use the latest common trading date for every multi-series calculation.
- Publish no ETF-flow proxy, historical option-chain reconstruction, 25-delta skew, regime label, or generated market opinion.
- Keep the EIA credential out of code, tests, documentation, patches, command output, and Git history.
- Automated tests use deterministic fake DataFrames and make no network requests.
- A read-only Yahoo smoke fetch must not write or replace a formal weekly output.
- Follow TDD and capture the expected RED before production changes.
- Run focused tests followed by `python3 -m unittest -v`.
- Commit only the files listed by the task that owns them.

---

### Task 1: Build the volatility history and calculation domain

**Files:**
- Create: `capital_weekly/context/volatility.py`
- Create: `data/capital_weekly_yahoo_volatility.csv`
- Create: `tests/test_capital_weekly_volatility.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `YahooVolatilitySeries(metric_code: str, metric_name: str, ticker: str, unit: str, role: str)`.
- Produces: `load_yahoo_volatility_config(path: str | Path) -> tuple[YahooVolatilitySeries, ...]`.
- Produces: `extract_yahoo_close_histories(frame: pd.DataFrame, series: Iterable[YahooVolatilitySeries], as_of_date: date) -> dict[str, pd.Series]`, keyed by configured role.
- Produces: `calculate_yahoo_volatility_metrics(histories: Mapping[str, pd.Series], series: Iterable[YahooVolatilitySeries], as_of_date: date, max_lag_days: int = 7) -> list[dict[str, Any]]`.
- Produces: `serialize_yahoo_close_histories(histories: Mapping[str, pd.Series], series: Iterable[YahooVolatilitySeries]) -> str`.
- Consumed by: Task 2's `yahoo_volatility_signals` provider.

- [ ] **Step 1: Write the failing configuration and happy-path tests**

Create `tests/test_capital_weekly_volatility.py` with this deterministic Yahoo-shaped frame:

```python
from datetime import date
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from capital_weekly.context.volatility import (
    YahooVolatilitySeries,
    calculate_yahoo_volatility_metrics,
    extract_yahoo_close_histories,
    load_yahoo_volatility_config,
    serialize_yahoo_close_histories,
)


CONFIG = (
    ("vix_9d_level", "Cboe S&P 500 9-Day Volatility Index", "^VIX9D", "index_points", "vix_9d"),
    ("vix_1m_level", "Cboe VIX 30-Day Volatility Index", "^VIX", "index_points", "vix_1m"),
    ("vix_3m_level", "Cboe S&P 500 3-Month Volatility Index", "^VIX3M", "index_points", "vix_3m"),
    ("vix_6m_level", "Cboe S&P 500 6-Month Volatility Index", "^VIX6M", "index_points", "vix_6m"),
    ("cboe_skew_level", "Cboe SKEW Index", "^SKEW", "index_points", "skew"),
)


def config_rows():
    return tuple(YahooVolatilitySeries(*row) for row in CONFIG)


def yahoo_frame():
    index = pd.to_datetime(["2026-08-06", "2026-08-07", "2026-08-10"])
    values = {
        ("^VIX9D", "Close"): [15.0, 14.0, 99.0],
        ("^VIX", "Close"): [17.0, 16.0, 99.0],
        ("^VIX3M", "Close"): [21.0, 20.0, 99.0],
        ("^VIX6M", "Close"): [23.0, 22.0, 99.0],
        ("^SKEW", "Close"): [145.0, float("nan"), 199.0],
    }
    return pd.DataFrame(values, index=index)


class YahooVolatilityTests(unittest.TestCase):
    def test_truncates_future_rows_and_calculates_only_on_matched_dates(self):
        config = config_rows()
        histories = extract_yahoo_close_histories(
            yahoo_frame(), config, date(2026, 8, 9)
        )
        metrics = calculate_yahoo_volatility_metrics(
            histories, config, date(2026, 8, 9)
        )
        by_code = {row["metric_code"]: row for row in metrics}

        self.assertEqual(len(metrics), 8)
        self.assertEqual(by_code["vix_1m_level"]["value"], 16.0)
        self.assertEqual(
            by_code["cboe_skew_level"]["as_of_date"], date(2026, 8, 6)
        )
        self.assertEqual(by_code["vix_1m_3m_spread"]["value"], -4.0)
        self.assertEqual(by_code["vix_1m_3m_ratio"]["value"], 0.8)
        self.assertEqual(by_code["vix_9d_1m_spread"]["value"], -2.0)
        self.assertNotIn(date(2026, 8, 10), histories["vix_1m"].index)
```

Also add a config-loading test that writes the exact five roles to a temporary CSV and asserts they load in file order.

- [ ] **Step 2: Run the new module test and verify the expected RED**

Run:

```bash
python3 -m unittest -v tests.test_capital_weekly_volatility
```

Expected: FAIL with `ModuleNotFoundError: No module named 'capital_weekly.context.volatility'`.

- [ ] **Step 3: Add dependency and exact symbol registry**

Append to `requirements.txt`:

```text
yfinance>=1.5,<2
```

Create `data/capital_weekly_yahoo_volatility.csv`:

```csv
metric_code,metric_name,ticker,unit,role
vix_9d_level,Cboe S&P 500 9-Day Volatility Index,^VIX9D,index_points,vix_9d
vix_1m_level,Cboe VIX 30-Day Volatility Index,^VIX,index_points,vix_1m
vix_3m_level,Cboe S&P 500 3-Month Volatility Index,^VIX3M,index_points,vix_3m
vix_6m_level,Cboe S&P 500 6-Month Volatility Index,^VIX6M,index_points,vix_6m
cboe_skew_level,Cboe SKEW Index,^SKEW,index_points,skew
```

Install the constrained dependency:

```bash
python3 -m pip install 'yfinance>=1.5,<2'
```

Expected: installation succeeds without creating or modifying another repository file.

- [ ] **Step 4: Implement configuration and Yahoo history extraction**

Create `capital_weekly/context/volatility.py` with:

```python
from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import quote

import pandas as pd


REQUIRED_ROLES = frozenset({"vix_9d", "vix_1m", "vix_3m", "vix_6m", "skew"})
TERM_ROLES = ("vix_9d", "vix_1m", "vix_3m", "vix_6m")


@dataclass(frozen=True)
class YahooVolatilitySeries:
    metric_code: str
    metric_name: str
    ticker: str
    unit: str
    role: str


def yahoo_history_url(ticker: str) -> str:
    return f"https://finance.yahoo.com/quote/{quote(ticker, safe='')}/history/"
```

`load_yahoo_volatility_config` must require the exact CSV header, nonblank fields, exactly one row per required role, unique tickers, unique metric codes, and `unit == "index_points"`.

`extract_yahoo_close_histories` must accept columns shaped as `(ticker, "Close")` or `("Close", ticker)`; accept a single-level `Close` column only for one configured series; normalize timestamps to `date`; reject duplicate normalized dates; discard rows after `as_of_date`; drop aligned missing cells independently per ticker; reject infinity and empty ticker histories; and return float series sorted by date and keyed by role.

- [ ] **Step 5: Implement matched-date metrics**

Use the exact common-date and freshness logic:

```python
common_dates = set(histories[TERM_ROLES[0]].index)
for role in TERM_ROLES[1:]:
    common_dates &= set(histories[role].index)
if not common_dates:
    raise ValueError("Yahoo volatility term indices have no common date")
term_date = max(common_dates)
skew_date = max(histories["skew"].index)
for label, observed in (("term structure", term_date), ("SKEW", skew_date)):
    lag = (as_of_date - observed).days
    if lag < 0 or lag > max_lag_days:
        raise ValueError(f"Yahoo {label} date is outside the freshness window")
```

Return five observed rows with `metric_code`, `metric_name`, `ticker`, `as_of_date`, `value`, `unit`, and `source_url`, followed by:

```python
{
    "metric_code": "vix_1m_3m_spread",
    "metric_name": "VIX 1M minus 3M spread",
    "as_of_date": term_date,
    "value": vix_1m - vix_3m,
    "unit": "index_points",
    "source_url": yahoo_history_url(role_map["vix_3m"].ticker),
},
{
    "metric_code": "vix_1m_3m_ratio",
    "metric_name": "VIX 1M to 3M ratio",
    "as_of_date": term_date,
    "value": vix_1m / vix_3m,
    "unit": "ratio",
    "source_url": yahoo_history_url(role_map["vix_3m"].ticker),
},
{
    "metric_code": "vix_9d_1m_spread",
    "metric_name": "VIX 9D minus 1M spread",
    "as_of_date": term_date,
    "value": vix_9d - vix_1m,
    "unit": "index_points",
    "source_url": yahoo_history_url(role_map["vix_1m"].ticker),
},
```

Reject zero VIX3M and any non-finite calculated result.

- [ ] **Step 6: Add RED tests for invalid inputs and serialization**

Add separate tests that:

- reject duplicate roles, missing `skew`, duplicate tickers, and unknown roles;
- reject disjoint term dates, stale SKEW, zero VIX3M, infinity, and duplicate normalized dates;
- verify deterministic raw header `date,ticker,close`, configured ticker order, ascending date order, and absence of the future row;
- verify the single-series `Close` shape through a one-series extraction test.

Run the focused module. Expected: new tests fail at the missing validation and serialization branches.

- [ ] **Step 7: Implement deterministic raw serialization**

Implement:

```python
def serialize_yahoo_close_histories(
    histories: Mapping[str, pd.Series],
    series: Iterable[YahooVolatilitySeries],
) -> str:
    role_map = {item.role: item for item in series}
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("date", "ticker", "close"))
    for role in ("vix_9d", "vix_1m", "vix_3m", "vix_6m", "skew"):
        ticker = role_map[role].ticker
        for observed, value in histories[role].items():
            writer.writerow((observed.isoformat(), ticker, repr(float(value))))
    return output.getvalue()
```

Add the exact validation branches from Step 6 without converting invalid values to zero.

- [ ] **Step 8: Verify and commit Task 1**

Run:

```bash
python3 -m unittest -v tests.test_capital_weekly_volatility
git diff --check
```

Expected: all volatility tests pass and the diff check is clean.

Commit:

```bash
git add requirements.txt data/capital_weekly_yahoo_volatility.csv capital_weekly/context/volatility.py tests/test_capital_weekly_volatility.py
git commit -m "feat: add Yahoo volatility signal calculations"
```

---

### Task 2: Register the optional provider and preserve the release gate

**Files:**
- Modify: `capital_weekly/context/providers.py`
- Modify: `capital_weekly/weekly_release.py`
- Modify: `tests/test_capital_weekly_context_providers.py`
- Modify: `tests/test_capital_weekly_weekly_release.py`

**Interfaces:**
- Consumes: Task 1's configuration, history, calculation, and serialization functions.
- Produces: optional provider `yahoo_volatility_signals` in `build_default_providers`.
- Produces: eight rows in the existing `financial_conditions` schema.
- Produces: a narrow release-policy allowlist for `("yahoo_volatility_signals", "financial_conditions")`.

- [ ] **Step 1: Write failing provider-registry and fetch tests**

Extend the temporary data directory in `tests/test_capital_weekly_context_providers.py` with Task 1's five-row registry. Add a fake downloader returning the deterministic frame and assert:

```python
providers = build_default_providers(
    start=date(2026, 8, 3),
    end=date(2026, 8, 9),
    data_dir=data_dir,
    environ={},
    yahoo_downloader=fake_download,
)
provider = providers["yahoo_volatility_signals"]
result = provider.fetch()

self.assertEqual(provider.spec.category, "financial_conditions")
self.assertEqual(provider.spec.requiredness, "optional")
self.assertEqual(provider.spec.freshness_days, 7)
self.assertEqual(len(result.rows), 8)
self.assertEqual(calls[0]["end"], "2026-08-10")
self.assertFalse(calls[0]["threads"])
self.assertFalse(calls[0]["progress"])
self.assertIn("date,ticker,close", result.raw_text)
```

- [ ] **Step 2: Verify the provider RED**

Run:

```bash
python3 -m unittest -v tests.test_capital_weekly_context_providers
```

Expected: FAIL because `build_default_providers` lacks `yahoo_downloader` and the provider registry lacks `yahoo_volatility_signals`.

- [ ] **Step 3: Implement provider composition**

Import `yfinance as yf` and Task 1's module. Extend the factory signature with:

```python
yahoo_downloader: Callable[..., Any] | None = None,
```

Load `capital_weekly_yahoo_volatility.csv` and select:

```python
download = yahoo_downloader or yf.download
```

The provider calls:

```python
frame = downloader(
    tickers=[item.ticker for item in config],
    start=(end - timedelta(days=550)).isoformat(),
    end=(end + timedelta(days=1)).isoformat(),
    interval="1d",
    auto_adjust=False,
    actions=False,
    group_by="ticker",
    threads=False,
    progress=False,
)
```

Convert every returned metric into the existing context schema:

```python
{
    "as_of_date": metric["as_of_date"],
    "category": "financial_conditions",
    "metric_code": metric["metric_code"],
    "metric_name": metric["metric_name"],
    "value": metric["value"],
    "unit": metric["unit"],
    "frequency": "daily",
    "market": "US",
    "source": "Yahoo Finance (Cboe indices)",
    "source_url": metric["source_url"],
    "qc_flag": "OK",
}
```

Return `ProviderResult` with serialized history, source label `Yahoo Finance (Cboe indices)`, and `https://finance.yahoo.com/`. Register the provider as `("financial_conditions", "daily", "optional")` and set only its `freshness_days` to `7`.

- [ ] **Step 4: Write failing release-policy tests**

Add one test accepting this row:

```python
row = fixture_row(
    CATEGORY_FIELDS["source_log"],
    provider="yahoo_volatility_signals",
    category="financial_conditions",
    requiredness="optional",
    status="FETCH_FAILED",
    observations="0",
    as_of_date="2026-08-09",
    source_url="https://finance.yahoo.com/",
)
```

Add a second test changing only `requiredness="required"` and asserting `ReleaseValidationError`. Retain the existing optional SEC test that rejects `FETCH_FAILED`.

- [ ] **Step 5: Verify the release-policy RED**

Run:

```bash
python3 -m unittest -v tests.test_capital_weekly_weekly_release
```

Expected: the optional-Yahoo test fails with `unacceptable status: FETCH_FAILED`; required-Yahoo and optional-SEC rejection tests pass.

- [ ] **Step 6: Implement the exact allowlist**

In `capital_weekly/weekly_release.py`, add `FETCH_FAILED` to `CONTEXT_SOURCE_STATUSES` and add:

```python
"FETCH_FAILED": frozenset(
    {("yahoo_volatility_signals", "financial_conditions")}
),
```

Do not add a wildcard or another provider identity. Preserve the existing `requiredness == "optional"` check.

- [ ] **Step 7: Run focused tests**

Run:

```bash
python3 -m unittest -v \
  tests.test_capital_weekly_volatility \
  tests.test_capital_weekly_context_providers \
  tests.test_capital_weekly_weekly_context \
  tests.test_capital_weekly_weekly_release
```

Expected: all focused tests pass with no real Yahoo request.

- [ ] **Step 8: Commit Task 2**

Run:

```bash
git diff --check
git add capital_weekly/context/providers.py capital_weekly/weekly_release.py tests/test_capital_weekly_context_providers.py tests/test_capital_weekly_weekly_release.py
git commit -m "feat: register optional Yahoo volatility provider"
```

---

### Task 3: Document and verify the integrated source

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: Tasks 1–2 provider and release behavior.
- Produces: operator documentation and complete verification evidence.

- [ ] **Step 1: Update operator documentation**

Add:

```markdown
### Optional Yahoo volatility signals

The weekly-context pipeline uses `yfinance` to request `^VIX9D`, `^VIX`,
`^VIX3M`, `^VIX6M`, and `^SKEW`. It publishes observed levels plus
registered 1M–3M and 9D–1M term calculations into
`financial_conditions.csv`.

Yahoo Finance is an optional public research source for this local desktop
workflow. Its failure remains visible in `source_log.csv` but does not block
an otherwise complete week. The provider does not publish option-chain
history, ETF-flow proxies, or generated regime labels.

`EIA_API_KEY` enables the existing free EIA commodity-fundamentals provider.
Keep the key in the process environment; never place it in repository files.
```

Do not include a credential value or committed `.env` file.

- [ ] **Step 2: Run the full offline suite**

Run:

```bash
python3 -m unittest -v
```

Expected: every repository test passes without a network refresh.

- [ ] **Step 3: Run an isolated read-only Yahoo smoke fetch**

Use the production config and provider for target Sunday `2026-08-09`. Print only provider name, status, row count, and latest date. Do not call `run_weekly_release`, write under `outputs/`, print cookies or environment variables, or include the EIA credential.

Expected on source availability:

```text
provider=yahoo_volatility_signals
status=OK
rows=8
latest_date=<date on or before 2026-08-09>
```

If Yahoo is unavailable, report the exact availability risk and preserve the optional failure policy; do not fabricate rows.

- [ ] **Step 4: Inspect scope and commit documentation**

Run:

```bash
git status --short
git diff --check
```

Confirm changes are limited to:

```text
requirements.txt
data/capital_weekly_yahoo_volatility.csv
capital_weekly/context/volatility.py
capital_weekly/context/providers.py
capital_weekly/weekly_release.py
tests/test_capital_weekly_volatility.py
tests/test_capital_weekly_context_providers.py
tests/test_capital_weekly_weekly_release.py
README.md
```

Commit:

```bash
git add README.md
git commit -m "docs: document Yahoo volatility signals"
```

- [ ] **Step 5: Report the implementation handoff**

Report the three implementation commit SHAs; changed files; RED evidence for module, registry, and release policy; focused and full GREEN counts; read-only smoke result; confirmation that no credential entered Git history; and remaining risks covering Yahoo's unofficial/personal-use posture and deferred ICI ETF net issuance.
