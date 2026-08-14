# Capital Weekly Yahoo Volatility Signals Design

**Date:** 2026-08-14

**Status:** Approach approved in conversation; pending written-spec review

**Repository:** `/Users/a1-6/Documents/market data`

**Product scope:** Local desktop Capital Weekly terminal only

## 1. Objective

Add one compact, high-value public volatility signal bundle to the existing
five-pipeline Capital Weekly release. The bundle uses the `yfinance` Python
package to retrieve Yahoo Finance histories for Cboe volatility indices and
publishes factual levels plus deterministic term-structure calculations into
the existing `financial_conditions.csv` table.

This feature improves weekly market-sense coverage without adding a new release
pipeline, a new frontend schema, paid data, inferred ETF flows, or generated
market opinions.

## 2. Confirmed Scope

The provider covers these Yahoo Finance symbols:

| Yahoo symbol | Published metric | Meaning |
| --- | --- | --- |
| `^VIX9D` | `vix_9d_level` | Cboe S&P 500 9-Day Volatility Index |
| `^VIX` | `vix_1m_level` | Cboe VIX 30-Day Volatility Index |
| `^VIX3M` | `vix_3m_level` | Cboe S&P 500 3-Month Volatility Index |
| `^VIX6M` | `vix_6m_level` | Cboe S&P 500 6-Month Volatility Index |
| `^SKEW` | `cboe_skew_level` | Cboe SKEW Index |

The provider also publishes three registered calculations on matched dates:

- `vix_1m_3m_spread = vix_1m_level - vix_3m_level`;
- `vix_1m_3m_ratio = vix_1m_level / vix_3m_level`;
- `vix_9d_1m_spread = vix_9d_level - vix_1m_level`.

The feature does not:

- download or reconstruct historical option chains;
- calculate 25-delta option skew;
- label ETF price, volume, or shares outstanding as ETF fund flow;
- add ICI ETF net issuance, FINRA short-sale volume, or OCC aggregate options
  data in this change;
- change the existing EIA provider or require an EIA key;
- modify the Next.js repository;
- create automated market conclusions or trading signals.

ICI ETF net issuance remains the next separate public-flow subproject. EIA
commodity fundamentals remain configured but disabled until the user supplies a
free `EIA_API_KEY` locally.

## 3. Source And Usage Posture

`yfinance` is an open-source Apache-licensed package that accesses Yahoo
Finance's publicly available interfaces. It is not affiliated with or endorsed
by Yahoo, and its own documentation states that downloaded Yahoo Finance data is
intended for personal use. This provider is therefore suitable only for the
approved local desktop research product.

The normalized source label is `Yahoo Finance (Cboe indices)`. Each observed
level links to the matching Yahoo Finance history page. Derived term-structure
rows link to the Yahoo Finance page for the longer-maturity input and retain the
registered formula in code and tests. Cboe documentation defines the economic
meaning of the underlying volatility indices, but Yahoo Finance remains the
value source and is not relabeled as direct Cboe data.

The dependency is constrained to `yfinance>=1.5,<2`. The provider is declared
`source_tier="public"` and `requiredness="optional"`. A Yahoo outage or schema
change is visible in `source_log.csv` but cannot block publication of an
otherwise complete week.

## 4. Architecture And File Boundaries

Create `capital_weekly/context/volatility.py` to own:

- configured symbol metadata;
- extraction and validation of `Close` histories returned by `yfinance`;
- target-Sunday truncation;
- matched-date selection;
- staleness checks;
- deterministic term-structure calculations;
- normalized metric-row construction inputs;
- deterministic serialization of fetched histories for raw capture.

Modify `capital_weekly/context/providers.py` only as the registry and composition
layer. It imports `yfinance`, injects the downloader into the volatility module,
wraps the normalized rows in `ProviderResult`, and registers
`yahoo_volatility_signals` as an optional daily `financial_conditions` provider.

Add `data/capital_weekly_yahoo_volatility.csv` as the explicit symbol registry.
The file contains:

```text
metric_code,metric_name,ticker,unit,role
```

The registry makes symbol changes reviewable and avoids hiding business data
configuration inside provider code. Unknown roles, duplicate tickers, duplicate
metric codes, or missing required roles fail provider validation.

Update `requirements.txt` with the constrained `yfinance` dependency. No new
output table or release pipeline is added.

## 5. Data Flow

1. `build_default_providers` loads the Yahoo volatility registry.
2. The provider requests daily histories from 550 calendar days before the
   target Sunday through the day after the target Sunday. The extra day is used
   only because `yfinance.download(..., end=...)` treats `end` as exclusive.
3. Returned timestamps are normalized to calendar dates. All rows with
   `date > target Sunday` are discarded before selecting values or calculating
   any metric.
4. Every configured ticker must provide finite daily closing values.
5. The four term-structure indices use their latest common trading date on or
   before the target Sunday. SKEW uses its latest valid date independently.
6. Each selected date must be no more than seven calendar days before the target
   Sunday. A future, stale, empty, duplicate-date, non-finite, or malformed
   history fails the optional provider.
7. The provider publishes five observed levels and three deterministic derived
   metrics to `financial_conditions.csv` using the existing context metric
   schema.
8. The fetched date/close histories are serialized in stable symbol/date order
   into the provider's raw capture file.
9. The existing weekly-context publisher records provider status, observations,
   provenance, elapsed time, and factual failure details in `source_log.csv`.

## 6. Calculation And Semantic Rules

All observed volatility index values use unit `index_points`. The ratio uses
unit `ratio`; the two spreads use unit `index_points`.

The provider publishes no `contango`, `backwardation`, `risk-on`, `risk-off`,
`fear`, `complacency`, or tail-risk regime label. Those interpretations require a
separate approved formula and are outside this task.

Calculations require matched observation dates. The provider never subtracts a
Friday VIX value from a Thursday VIX3M value merely because both are the latest
available rows. A zero VIX3M denominator is invalid rather than converted to a
missing or infinite ratio.

SKEW is published only as an observed level. The provider does not apply a fixed
historical threshold because Cboe has reviewed changes to the SKEW methodology
and any interpretation rule would require separate versioning.

## 7. Error Handling And Release Policy

`yahoo_volatility_signals` is optional because Yahoo Finance is an unofficial,
non-contractual research source. The provider follows the existing optional
source behavior:

- success publishes all eight rows and an `OK` source-log record;
- any missing required ticker, malformed frame, stale value, mismatched date,
  non-finite value, or download exception publishes no Yahoo volatility rows and
  records `FETCH_FAILED` with the factual error;
- provider failure does not replace or invalidate valid rows from the existing
  FRED financial-conditions provider;
- provider failure does not block formal weekly publication;
- no previous-week Yahoo value is silently copied into the target week;
- failed or partial data never receives an `OK` quality flag.

The provider is all-or-nothing within one week so derived values cannot appear
without their complete observed input set.

## 8. Testing Strategy

All behavior changes use TDD. Automated tests inject deterministic pandas
histories and never call Yahoo Finance.

Focused tests cover:

- configuration validation;
- `yfinance` single- and multi-level column shapes expected from one or multiple
  tickers;
- truncation of observations after the target Sunday;
- latest common-date selection across the four term indices;
- independent SKEW date selection;
- exact levels, spread, and ratio formulas;
- deterministic raw serialization;
- rejection of empty, stale, duplicate-date, future-only, non-finite, missing
  ticker, and zero-denominator histories;
- registry metadata and optional requiredness;
- a provider failure remaining visible without blocking unrelated optional or
  required context data;
- preservation of the exact existing context table schema.

Verification order:

1. `python3 -m unittest -v tests.test_capital_weekly_volatility`;
2. `python3 -m unittest -v tests.test_capital_weekly_context_providers tests.test_capital_weekly_weekly_context`;
3. `python3 -m unittest -v tests.test_capital_weekly_weekly_release`;
4. `python3 -m unittest -v`;
5. one isolated, read-only `yfinance` smoke fetch for the five symbols, without
   writing a formal weekly output or launching the five-pipeline refresh.

## 9. Acceptance Criteria

- `requirements.txt` installs `yfinance>=1.5,<2`.
- The default provider registry includes optional
  `yahoo_volatility_signals`.
- A valid fake history publishes exactly five observed levels and three derived
  term-structure metrics.
- No published Yahoo observation or derived input date exceeds the target
  Sunday.
- Every derived metric uses a single matched trading date.
- Every row has an HTTP(S) source URL and `OK` quality flag only after complete
  validation.
- Yahoo failure remains visible in audit and does not block a complete week.
- No ETF-flow proxy, option-chain history, generated interpretation, or frontend
  change enters the task.
- Focused and full Python tests pass.

## 10. Public References

- yfinance project and usage posture:
  `https://github.com/ranaroussi/yfinance`
- yfinance download API:
  `https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html`
- Cboe VIX term structure and index definitions:
  `https://www.cboe.com/tradable-products/vix/term-structure`
- Cboe SKEW index listing:
  `https://www.cboe.com/us/indices/benchmark_indices/`

