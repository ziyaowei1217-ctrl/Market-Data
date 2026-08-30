# Public Green Data Integration Design

**Date:** 2026-08-30

**Status:** Approved for implementation planning

**Source capability tip:** `codex/public-green-data-pipeline@56ed7ad`

**Target baseline:** `main@c2cd31c`

## 1. Purpose

Integrate the public-data capabilities developed across the Market Data Coverage
Wave 0-5 chain and the final `public-green-data-pipeline` branch into the current
Capital Weekly backend without restoring the obsolete repository layout,
configuration model, historical-output directories, or publication contract.

The source branch already contains the linear Wave 0-5 history. Therefore the
integration uses its tip as the single functional reference rather than merging
the six Wave branches independently.

## 2. Constraints

- Preserve the two visible product directories: `pipeline/` and `output/`.
- Keep `pipeline/config.json` as the only production configuration source.
- Keep the five published business domains: indices, cross-market sectors,
  GICS, macro assets, and weekly context.
- Publish only the latest complete stable JSON bundle in `output/`.
- Apply the requested `as_of_date` before selecting releases or calculating
  snapshots, returns, revisions, or derived values.
- Never expose a partial release. All five pipelines and cross-file validation
  must succeed before replacement of the stable bundle.
- Retain one successful raw-cache generation under `pipeline/.cache/`.
- Preserve empty optional collections as arrays and represent missing values as
  JSON `null`, never as zero, an empty string, `NaN`, or infinity.
- Preserve source URL, observation date, and QC/source status on every published
  business record.
- Do not perform a real network refresh during implementation or verification.
- Preserve the unrelated untracked audit document and the separate dirty
  `commodity-research-backend` worktree.

## 3. Integration Strategy

The integration will be a semantic port, not a Git merge or bulk cherry-pick.
The source branch predates the current `pipeline/internal/` consolidation and
uses CSV production configuration plus dated output directories. Direct history
integration would reintroduce retired paths and publication contracts.

Work will occur in a new isolated worktree created from the current `main`.
Source-branch files will be read as reference implementations. Each capability
will be adapted to current module paths, JSON configuration, five-domain output,
and validation contracts. The source branch itself and the active commodity
worktree will not be modified.

## 4. Capability Scope

### 4.1 Macro calculations and registered datasets

Port the Wave 0-1 calculations and public series that remain valid under the
current ontology, including registered Treasury calculations and additional
macro series. Configuration rows move into `pipeline/config.json`; no legacy
production CSV is restored.

### 4.2 Market state, breadth, and positioning

Port the Wave 2 market-state functionality:

- 20/50/200-session participation;
- advance/decline and 52-week breadth;
- equal-weight versus capitalization-weight relative performance;
- classification-correct CFTC financial and commodity positioning;
- eligible position changes and trailing percentiles.

Proxy metrics must remain explicitly labelled as proxies. The integration must
not convert a component series into an unimplemented derived metric or treat
current constituents as a historical-vintage universe.

### 4.3 Official macro releases and Fed decisions

Port the Wave 3 and public-green point-in-time providers:

- BLS CPI, payrolls, unemployment, and average hourly earnings;
- BEA real GDP, headline/core PCE inflation, personal income, disposable
  personal income, and consumption changes;
- Census retail sales, housing, and durable-goods releases;
- completed FOMC decisions enriched from dated official statements.

Release-specific artifacts are the primary point-in-time source. The BEA API
may be used only where the source implementation proves that the selected API
table revision matches the dated official release. Future releases and data not
known by the target-Sunday cutoff are excluded.

### 4.4 Public flows

Port issuer and exchange facts that have auditable dated observations:

- issuer NAV, net assets, and shares outstanding;
- ETF implied flow only when two eligible observations exist;
- HKEX Southbound buy, sell, turnover, and directly calculable net buy;
- available official Northbound turnover fields.

The pipeline must not infer unavailable Northbound net flow or label a single
asset/share snapshot as a flow.

### 4.5 Company fundamentals and capital-markets events

Port the Wave 4 SEC functionality behind an explicitly configured company
watchlist:

- reported company facts and eligible derived TTM/margin/cash-flow metrics;
- point-in-time valuation metrics when every required input exists;
- filing and selected guidance-direction event proxies;
- S-1, F-1, 424B4, and eligible 8-K activity;
- available official HKEX listing facts.

The production watchlist remains empty unless separately populated by the user.
When empty, collections remain present and the source status is
`NOT_CONFIGURED`. Test fixtures must never become production watchlist entries.

### 4.6 Capability audit

Port the Wave 5 capability inventory as an internal release-validation view.
Each approved item is classified as `available`, `failed`, `not_configured`,
`unavailable_licensed`, or `not_applicable`, with an explicit reason. Code
support or an empty output table does not qualify as `available`.

## 5. Five-Domain Publication Mapping

No sixth top-level business file will be introduced.

| Integrated data | Current publication destination |
| --- | --- |
| Treasury, policy, money-market, FX, commodity, and registered macro series | `macro.json` |
| Breadth tied to published indices | `indices.json` or derived context rows when it is market-wide rather than index-record metadata |
| Cross-market sector ranks and sector-relative measures | `sectors.json` |
| U.S. GICS proxy-specific measures | `gics.json` |
| Economic releases, Fed decisions, positioning, flows, company facts/events, capital-markets events, capability audit | `context.json` |

New weekly-context collections will be added under `context.json.tables` with
stable schemas. Corresponding source-log rows remain in `context.json`.
`release.json` continues to hash exactly the same five business files.

## 6. Configuration Model

All source-branch CSV configuration will be translated into named sections of
`pipeline/config.json`. Loaders will continue to support explicit CSV paths only
for deterministic tests and diagnostics. Production code must not search for or
silently fall back to legacy CSV configuration.

Configuration validation will reject duplicate identifiers, malformed URLs,
unknown provider types, invalid calculation dependencies, and enabled company
rows missing required identifiers.

## 7. Implementation Slices

The port will be divided into independently testable commits:

1. **Contracts and configuration:** schemas, provider contracts, capability
   states, and JSON configuration rows.
2. **Macro releases and Fed decisions:** BLS, BEA, Census, and FOMC enrichment.
3. **Market state and positioning:** breadth, relative measures, CFTC classes,
   and cross-asset calculations.
4. **Public flows:** issuer and exchange facts with conservative derivations.
5. **SEC facts and capital markets:** watchlist-gated fundamentals and events.
6. **Publication integration:** five-domain JSON serialization, source logs,
   manifests, migration compatibility, and cross-file validation.

Each slice begins with a focused failing test that demonstrates the missing
behavior in the current baseline. Only files belonging to the active slice are
committed.

## 8. Error Handling and Publication Safety

- Required provider failure blocks publication; optional provider failure is
  visible in source logs and yields an empty stable collection when allowed.
- Provider errors retain source, stage, and diagnostic context without leaking
  credentials.
- Timestamp, vintage, source URL, and point-in-time checks fail closed.
- Derived records publish only when all registered inputs are eligible and
  non-missing.
- Cross-file validation checks release identity, hashes, stable schemas,
  record-level dates and sources, and capability-state consistency.
- Offline migration validates source manifests and hashes and never invokes a
  pipeline runner.

## 9. Verification

For every implementation slice:

1. Run the focused unittest module and capture the expected RED before editing.
2. Implement the smallest source-compatible behavior.
3. Re-run the focused test to GREEN.
4. Run related provider, point-in-time, configuration, and publication tests.

Before completion:

- run `python3 -m unittest -v`;
- run `node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs`;
- run `validate_output_bundle` against the active `output/` directory;
- verify no real network refresh occurred;
- verify the existing stable output identity remains unchanged unless the user
  separately authorizes a refresh;
- verify the unrelated audit document and commodity worktree were not changed.

## 10. Completion Criteria

The integration is complete when:

- all approved source capabilities are represented in the current architecture;
- default production provider registration includes the required official
  economic sources;
- deterministic tests prove point-in-time filtering and source provenance;
- all new records serialize through the existing five-domain stable bundle;
- full Python and workbook-compatibility tests pass;
- the active stable output bundle validates;
- commits, moved/created/deleted files, RED/GREEN evidence, test results,
  offline-source identity, stable output identity, cleanup archive, and
  remaining compatibility risks are reported.

## 11. Explicit Non-Goals

- Merging or modifying the active `commodity-research-backend` worktree.
- Performing a live network refresh.
- Populating a production SEC company watchlist without a separate user choice.
- Reintroducing historical week directories, legacy `outputs/`, or production
  CSV configuration.
- Changing the adjacent frontend repository.
- Claiming full coverage of the 677-item research universe; this integration
  restores already-developed public capabilities and remains a foundation for
  later universe expansion.
