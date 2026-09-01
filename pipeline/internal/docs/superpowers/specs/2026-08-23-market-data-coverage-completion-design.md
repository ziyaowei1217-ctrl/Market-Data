# Capital Weekly Public Market-Data Coverage Completion

**Date:** 2026-08-23

**Status:** Approved for implementation

**Repositories:**

- Market data: `/Users/a1-6/Documents/market data`
- Dashboard: `/Users/a1-6/Documents/行业与个股分析`

## 1. Objective

Complete the publicly obtainable portions of the Capital Weekly market-sense
coverage matrix and make each completed metric usable end to end: acquired or
calculated in the backend, validated in an atomic formal weekly release,
auditable to a source and point-in-time cutoff, and visible in the Dashboard.

Paid or licensed series are not fabricated. When no defensible public source
exists, the capability remains explicitly unavailable in the audit model or is
represented by a separately named and documented proxy.

## 2. Definition of Done

A metric is complete only when all of the following are true:

1. A deterministic provider or registered calculation produces it.
2. `as_of_date` and, where applicable, `known_as_of` are enforced before any
   snapshot or derived value is calculated.
3. The formal weekly release validates and manifests the output.
4. The Dashboard contract loads the record with provenance.
5. The appropriate Dashboard page renders the record and its limitations.
6. Backend, frontend, release, and end-to-end tests pass.

Code-only support, an empty header, an ad-hoc output, or a draft directory does
not count as completion.

## 3. Scope Policy

### 3.1 Included

- Free public official sources where available.
- Transparent calculations from registered input series.
- Clearly labeled public-vendor proxies when no stable official value feed is
  available and local research use is permitted.
- Point-in-time historical backfill only when an immutable source proves what
  was known by the target Sunday.
- Forward accumulation from first successful capture when point-in-time
  backfill cannot be proven.

### 3.2 Excluded or unavailable without a licensed source

- CTA positioning sold by investment banks.
- Dealer gamma exposure reconstructed from licensed option-chain history.
- EPFR flows and comprehensive mutual-fund flows.
- Forward consensus, earnings or sales revision breadth, and forward P/E.
- CDX history, comprehensive ECM/DCM volumes, app downloads, and complete web
  traffic when no free redistribution-safe source exists.

These entries must never produce placeholder numbers. The data-audit model may
record `UNAVAILABLE_LICENSED` with a factual reason.

## 4. Delivery Strategy

Use vertical releases. Every wave completes backend, formal release, frontend,
and end-to-end verification before the next wave begins.

### Wave 0: Restore and formalize the current baseline

- Repair the current release-validation failure.
- Formally publish UST 5Y, 5Y/10Y real yields, 5Y/10Y breakevens, and 5Y5Y.
- Formally publish the existing optional VIX levels and registered term metrics
  when their provider succeeds; preserve factual failure evidence otherwise.
- Ensure the formal latest-week selector never exposes a draft or failed week.

### Wave 1: High-confidence macro market structure

- Fed balance sheet, TGA, ON RRP take-up, and calculated net liquidity.
- 5s30s and HY minus IG spreads.
- Copper and a broader major-FX set.
- Stock-bond, equity-dollar, gold-real-yield, and oil-breakeven correlations.
- Dashboard macro/liquidity presentation and provenance.

### Wave 2: Breadth, positioning, and public flows

- Registered-universe 20/50/200-day breadth, advance/decline, new highs/lows,
  and equal-weight versus cap-weight performance.
- Expanded CFTC coverage and positioning percentiles.
- Public ETF issuance/AUM or issuer-implied flow where dated NAV and shares
  align exactly.
- Public HKEX Stock Connect measures that remain available under a documented
  official definition; unavailable northbound measures are not inferred.
- Dashboard market-state presentation.

### Wave 3: Point-in-time macro releases and calendars

- CPI, core CPI, PCE, core PCE, payrolls, unemployment, GDP, retail sales, and
  ISM when an eligible immutable capture exists.
- A separately named macro-momentum or trend-deviation proxy. It must not be
  called a Citi Economic Surprise Index and must not claim consensus surprise.
- FOMC, economic, and confirmed earnings-event calendars from official sources.
- Dashboard economic/event presentation.

### Wave 4: Companies and capital markets

- SEC Submissions and Company Facts for a configured enabled watchlist.
- Reported EPS, revenue, margins, FCF, TTM measures, trailing valuation, and
  historical valuation percentiles using only facts filed by the cutoff.
- Rules-based and explicitly labeled guidance proxy from public filings or
  attached earnings releases.
- SEC/HKEX filing-based IPO statistics and filing/announcement-based M&A
  events, without claiming comprehensive transaction-database coverage.
- Dashboard company/capital-markets presentation.

### Wave 5: Optional alternative data

- Google Trends only if a stable, auditable local-research acquisition path is
  available at implementation time.
- No app-download or complete web-traffic integration without a suitable free
  source.

## 5. Architecture

Retain the existing five top-level acquisition pipelines and weekly atomic
release coordinator.

- `macro_assets` owns liquidity, rates, spreads, credit, commodities, FX, and
  cross-asset calculations.
- `weekly_context` owns volatility, breadth, positioning, flows, economic
  releases, events, company fundamentals, valuation, and capital markets.
- Equity-index, cross-market-sector, and GICS histories remain independent
  acquisition domains and can supply registered inputs to downstream
  calculations without moving their source ownership.
- The Dashboard reads only formal `week_YYYYMMDD-YYYYMMDD` releases whose
  manifest is complete and valid.

Provider modules remain small and domain-specific. The provider registry
composes them through shared metadata and result contracts. Calculations are
pure functions over dated input records and do not perform network access.

## 6. Output Tables

Reuse current tables where their semantics fit and add typed tables rather than
overloading a generic context table.

| File | Purpose |
| --- | --- |
| `liquidity.csv` | Fed balance sheet, TGA, ON RRP take-up, and net liquidity |
| `fixed_income.csv` | Nominal/real yields, curve and credit spreads |
| `foreign_exchange.csv` | DXY and major FX levels/returns |
| `commodities.csv` | Gold, oil, copper, and existing commodity proxies |
| `cross_asset.csv` | Registered correlation and paired-input metrics |
| `financial_conditions.csv` | Volatility levels, term metrics, and conditions |
| `market_internals.csv` | Breadth and exchange microstructure |
| `positioning_flows.csv` | CFTC and existing positioning metrics |
| `fund_flows.csv` | Public ETF, ICI, and eligible Stock Connect flows |
| `economic_releases.csv` | Point-in-time macro actuals and calculations |
| `events.csv` | Confirmed official calendars |
| `company_fundamentals.csv` | SEC reported and derived company metrics |
| `capital_markets.csv` | Filing/announcement-based IPO and M&A records |

Every business record carries, directly or through a typed equivalent:

```text
record_id
metric_code
metric_name_cn
metric_name_en
observation_date
known_as_of
value
unit
frequency
market
source
source_url
source_tier
proxy_type
calculation_id
formula_version
input_record_ids
qc_flag
notes
```

Optional fields may be empty, but missing values are never converted to zero or
display placeholders. Derived rows require a calculation identity, formula
version, and resolvable input record identities.

## 7. Source and Calculation Boundaries

### 7.1 Liquidity

Use Federal Reserve/FRED observations for total assets, Treasury General
Account, and ON RRP take-up. Do not substitute the ON RRP offering rate for
facility usage. Register:

```text
net_liquidity = fed_total_assets - tga_balance - on_rrp_take_up
```

Inputs must use matched observation dates or a documented as-of join that does
not use observations after the target Sunday.

### 7.2 Rates and credit

Use official Treasury and NY Fed sources first and current FRED/ICE BofA public
series where already integrated. Register 2s10s, 5s30s, and HY minus IG with
explicit units and matched-date inputs.

### 7.3 Volatility

Prefer public Cboe values when a stable historical path exists. A public-vendor
proxy must retain its actual source label. VIX term metrics use one matched
trading date. VVIX, put/call, and MOVE appear only when their value history and
usage posture are defensible; otherwise they remain unavailable.

### 7.4 Breadth and flows

Breadth is named after its configured universe, not an official index, unless
point-in-time constituent membership is available. Current membership is not
used for historical backfill. ETF implied flow is calculated only from exactly
aligned dated NAV and shares outstanding. Exchange turnover or short turnover
is not labeled as fund flow.

### 7.5 Macro and company data

Economic and SEC records must satisfy `known_as_of` before the target Sunday
cutoff. Public macro tables keep consensus and surprise empty. A macro proxy is
named for its formula, not a proprietary index. Historical SEC calculations use
only facts filed by the target date; later restatements do not overwrite older
vintages.

### 7.6 Cross-asset calculations

Correlations use matched daily returns and registered windows. The initial
windows are 13 and 26 weeks, with a minimum valid-observation threshold. Each
row preserves both input series codes, window, observation count, and end date.

## 8. Publication and Failure Rules

- Official core sources are required when their dataset is in the active wave.
- Non-contractual public-vendor and optional sources may fail without blocking
  unrelated core data, but they publish no stale or partial rows.
- Failed providers remain visible in source logs and manifest coverage.
- Required provider, schema, point-in-time, source URL, finite-number, or
  calculation-input failure blocks the new week.
- A failed run never replaces the previous complete formal week.
- The manifest records each capability as `available`, `failed`,
  `not_configured`, `unavailable_licensed`, or `not_applicable`, with a reason.
- Historical migration repairs schemas and manifests but never invents records.

## 9. Dashboard Information Architecture

The Dashboard expands to seven business pages plus audit:

1. Market overview.
2. Global indices.
3. Sector performance.
4. Macro and liquidity.
5. Market state.
6. Economy and events.
7. Companies and capital markets.
8. Data audit.

The current week selector, horizon selector, search, density control, and detail
drawer remain shared. Proxy metrics are visibly labeled in both tables and the
drawer. The drawer exposes the relative file, source link, cutoff, known-as-of
timestamp, calculation, inputs, and limitations.

Empty business datasets render no main-page section. Their factual absence and
reason remain visible in data audit. The frontend performs formatting and
registered presentation summaries only; backend business formulas are not
duplicated in TypeScript.

## 10. Testing and Verification

All behavior changes follow test-driven development and deterministic fixtures.
Automated tests do not perform live refreshes.

Each wave requires:

- provider parser and cutoff tests;
- calculation tests with matched and mismatched dates;
- schema, provenance, and manifest tests;
- required/optional failure and rollback tests;
- frontend parser and loader tests;
- page rendering, empty-state, proxy-label, and drawer tests;
- full Python unittest suite;
- full frontend unit tests, lint, and build;
- Playwright coverage using a two-week fixture;
- one explicitly authorized read-only source smoke check before formal refresh;
- a formal weekly release only after source smoke checks and validation pass.

## 11. Acceptance Criteria

- Every completed public metric is present in a complete formal week and visible
  on its Dashboard page.
- Every value is traceable to a source record or registered calculation.
- No formal row uses data observed or known after its target Sunday.
- No paid or missing data is represented by a fabricated value.
- Proxies are named and labeled as proxies.
- A source failure cannot replace the last complete week.
- Historical backfill occurs only when point-in-time evidence exists.
- All repository and end-to-end verification commands pass for each wave.
