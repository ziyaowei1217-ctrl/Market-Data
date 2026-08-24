# Market Data Coverage Wave 4 Implementation Plan

> **Scope:** Execute Wave 4 from the approved market-data coverage design. Start from the completed Wave 3 backend and frontend heads. Do not run a real network refresh or publish a formal week.

## Goal

Add point-in-time SEC watchlist fundamentals, trailing valuation and valuation-percentile calculations, a rules-based guidance-direction proxy, and filing-based SEC/HKEX capital-markets activity. Publish them through the existing five-pipeline atomic release and display them on a dedicated Companies & Capital Markets dashboard page. Do not invent a production watchlist, consensus estimate, forward multiple, comprehensive IPO volume, or comprehensive M&A coverage.

## Contract decisions

- Add typed `company_fundamentals.csv` and `capital_markets.csv` tables to `weekly_context`; bump the current dataset contract to v5 while keeping v1-v4 readable.
- Every SEC fact must have `filed <= target Sunday`; every market price must have `price_date <= target Sunday`. Derived values retain calculation IDs, formula versions, and input record IDs.
- Company fundamentals remain optional and `NOT_CONFIGURED` while the enabled watchlist is empty. Once enabled, the SEC fundamentals provider is required and needs a descriptive `SEC_USER_AGENT`.
- Reported metrics include revenue, EPS, operating income, net income, operating cash flow, capex, and available balance-sheet facts. Derived metrics include FCF, gross/operating/net margin, TTM measures, trailing P/E, P/B, P/S, and EV/EBITDA only when every required input exists.
- Historical valuation percentile is calculated only from point-in-time historical valuation observations whose fact filings and prices were both known by their observation cutoff. Insufficient history publishes no percentile row.
- Guidance is a filing-text rules proxy with explicit `guidance_direction_proxy` naming. It is not management consensus, earnings surprise, or revision breadth.
- SEC/HKEX capital-markets records are filing/listing activity. SEC IPO filing counts are labelled as a filing-count proxy, not issuance dollars. M&A rows require both an eligible filing item and transaction language; the table does not claim comprehensive deal-database coverage.
- Existing `company_events.csv` remains the source of confirmed earnings/periodic filing events.

## Task 1: SEC Company Facts and calculations

**Files**

- Create `capital_weekly/context/fundamentals.py`.
- Modify `capital_weekly/context/providers.py` and `capital_weekly/weekly_context.py`.
- Add focused fundamentals/provider/context tests.

**TDD sequence**

1. Add deterministic Company Facts fixtures proving post-Sunday filings are excluded and earlier vintages are not overwritten.
2. Add calculation tests for reported rows, four-quarter TTM, FCF, margins, trailing multiples, missing-input suppression, and input lineage.
3. Add historical-valuation percentile tests with a point-in-time price/fact history and an insufficient-history case.
4. Add provider tests for empty-watchlist `NOT_CONFIGURED`, enabled-watchlist requiredness, SEC user-agent enforcement, and price cutoff.
5. Capture RED, implement the smallest pure parsers/calculations and registry wiring, then reach focused GREEN.

## Task 2: Guidance proxy and filing-based capital markets

**Files**

- Create `capital_weekly/context/capital_markets.py`.
- Modify `capital_weekly/context/providers.py` and `capital_weekly/weekly_context.py`.
- Add focused parser/provider/context tests.

**TDD sequence**

1. Add filing-text tests for raised, lowered, reaffirmed, provided, mixed, and absent guidance signals.
2. Add SEC daily-index tests for S-1/F-1/424B4 filing activity and weekly aggregate filing-count proxy rows.
3. Add M&A tests requiring an eligible 8-K item plus merger/acquisition language.
4. Add a deterministic HKEX listing-table parser fixture and factual empty/failure behavior.
5. Preserve source URL, known-as-of cutoff, proxy naming, and non-comprehensive coverage notes.

## Task 3: Release contract v5

**Files**

- Modify `capital_weekly/weekly_release.py` and release/migration tests.
- Update README for watchlist activation, new tables, and limitations.

**TDD sequence**

1. Add failing v5 schema, exact-header, point-in-time, calculation-lineage, status-policy, and manifest tests.
2. Add both tables to the coordinated release and optional empty-table topology.
3. Prove v1-v4 remain readable and a failed enabled-watchlist provider blocks replacement of the prior complete week.
4. Run focused modules followed by the full backend suite and workbook smoke test.

## Task 4: Companies & Capital Markets dashboard

**Files**

- Add a dedicated terminal view and navigation entry.
- Extend dataset contracts, loaders, search, detail drawer, fixtures, and styles.
- Add unit/integration and Playwright tests.

**TDD sequence**

1. Add failing loader and view tests for reported facts, derived metrics, valuation percentiles, guidance-proxy labelling, IPO filing-count limitations, and M&A/HKEX provenance.
2. Implement compact searchable sections; omit empty business sections while retaining audit evidence.
3. Add detail-drawer fields for company, period, filing/known-as-of, formula, inputs, proxy type, form/accession, and limitations.
4. Extend the two-week fixture and prove company data remains week-specific.
5. Run frontend tests, lint, typecheck, production build, and Playwright.

## Verification and handoff

1. Run focused backend tests, then `python3 -m unittest -v` and the workbook smoke test.
2. Run frontend unit/integration tests, lint, typecheck, build, and full Playwright.
3. Review all derived values for cutoff ordering, provenance, formula identity, missing-input suppression, and proxy labelling.
4. Commit backend and frontend Wave 4 files separately and report SHAs, RED/GREEN evidence, full results, and remaining upstream risks.
