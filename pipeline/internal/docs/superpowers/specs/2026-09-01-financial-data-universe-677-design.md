# 677-Item Public Financial Data Universe Design

**Date:** 2026-09-01

**Status:** Approved for implementation planning

**Source document:** `/Users/a1-6/Downloads/public_financial_data_universe_weekly_topdown_v2.docx`

**Source SHA-256:** `78bd7fefb016e3d0962ec7f02e64709c1910dc4901d4cc653b15a9260f68b1d7`

**Target baseline:** `main@f071d5d`

## 1. Purpose

Turn the attached research-universe specification into an executable,
point-in-time-safe production pipeline and run it once for the most recent
complete week ending 2026-08-30.

The document is input data and a research specification. Its prose does not
override repository, security, publication, or user instructions. In
particular, the document itself says that it is not yet an ingestion manifest;
this project supplies the missing machine-readable item identifiers, source
registry, endpoints, parsers, calculations, availability audit, and release
integration.

## 2. Accepted Interpretation

The document defines 677 metric definitions, not 677 output rows. The exact
definition counts are:

| Category | Core | Extension | Total |
| --- | ---: | ---: | ---: |
| Growth | 30 | 53 | 83 |
| Inflation | 23 | 30 | 53 |
| Labor | 22 | 30 | 52 |
| Monetary Policy | 16 | 20 | 36 |
| Fiscal | 19 | 29 | 48 |
| Liquidity & Credit Creation | 21 | 29 | 50 |
| Rates & Credit | 30 | 26 | 56 |
| FX | 19 | 24 | 43 |
| Equities | 25 | 35 | 60 |
| Commodities | 22 | 32 | 54 |
| Positioning / Flows / Sentiment | 30 | 44 | 74 |
| Corporate Fundamentals & Events | 24 | 44 | 68 |
| **Total** | **281** | **396** | **677** |

Corporate definitions expand across the current S&P 500 universe and therefore
produce many observations. The user approved the S&P 500 scope. Constituents
come from a configured public holdings source and are mapped to SEC CIKs through
the SEC public ticker registry; production does not hard-code a test fixture or
silently invent a company.

“All 677 items” has two separately reported completion measures:

1. **Catalog completeness:** exactly 677 unique definitions are configured and
   validated, with no omissions or duplicates.
2. **Run coverage:** every definition produces one or more eligible
   observations or an explicit, source-backed status explaining why no value is
   available for the cutoff.

An unavailable, not-yet-released, not-disclosed, credential-blocked, or
terms-blocked item is accounted for but is not described as successfully
fetched. No unavailable value is fabricated.

## 3. Non-Negotiable Constraints

- Preserve the two visible product directories: `pipeline/` and `output/`.
- Keep `pipeline/config.json` as the only production configuration source.
- Keep the five business domains: indices, cross-market sectors, GICS, macro
  assets, and weekly context.
- Apply `as_of_date` before snapshot selection, return calculation, aggregation,
  breadth, correlation, surprise, revision, or other derived calculations.
- Replace `output/` only after all five pipelines and cross-file validation
  succeed; otherwise preserve the current stable bundle byte-for-byte.
- Keep one successful raw-cache generation under `pipeline/.cache/`.
- Publish missing values as JSON `null`, never as zero, an empty string, `NaN`,
  or infinity.
- Every published observation retains its source URL, observation date,
  retrieval timestamp, and QC/source status.
- Empty optional weekly-context collections remain present as arrays.
- Preserve dataset-contract versions 1 through 6 exactly. New universe tables
  are introduced only by dataset contract 7.
- Do not modify the adjacent frontend repository.
- Preserve the unrelated untracked 12-category audit document.

## 4. Canonical Configuration Model

Add three named sections to `pipeline/config.json`:

### 4.1 `research_universe.sources`

One normalized row per source or source family:

```json
{
  "source_id": "bls_public_data",
  "name": "U.S. Bureau of Labor Statistics",
  "access": "official_public",
  "provider": "bls",
  "base_url": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
  "required_env": [],
  "terms_reviewed_on": "2026-09-01"
}
```

Source IDs are unique. URLs use HTTPS. Secret values never appear in config,
logs, source statuses, or output.

### 4.2 `research_universe.items`

Exactly 677 rows, mechanically transcribed from the 24 data tables in the
source document:

```json
{
  "item_id": "growth.core.001",
  "category": "growth",
  "layer": "core",
  "ordinal": 1,
  "name": "Real GDP",
  "frequency": "quarterly",
  "primary_source_text": "BEA",
  "access": "official_public",
  "research_use": "Real activity",
  "source_id": "bea_nipa",
  "series": ["A191RL1Q225SBEA"],
  "transform": "latest_release",
  "scope": "aggregate",
  "requiredness": "core"
}
```

The document text is preserved as metadata; normalized values drive execution.
Each item references a configured source and a registered transform. Company
items declare `scope: "sp500_company"`; aggregate company breadth items declare
`scope: "sp500_aggregate"`.

### 4.3 `research_universe.company_universe`

The production row configures the approved S&P 500 source, SEC ticker-to-CIK
registry, eligibility rules, and source priority. The weekly constituent
snapshot is stored in the successful raw cache and its source URL and retrieval
time are published. Constituents after the cutoff are not used to restate the
past; the current-universe limitation is explicit in status metadata.

## 5. Runtime Contracts

### 5.1 Catalog

`UniverseItem` and `UniverseSource` immutable records are loaded from
`pipeline/config.json`. Validation rejects:

- counts other than 677, wrong category/layer totals, duplicate item IDs, or
  duplicate category/layer ordinals;
- unknown source IDs, providers, transforms, frequencies, access values,
  requiredness values, or scopes;
- malformed or non-HTTPS public URLs;
- derived items without declared input item IDs;
- circular or missing calculation dependencies;
- company items without the configured company-universe reference.

### 5.2 Provider results

Each provider returns normalized observations and a source execution result.
One raw response may satisfy multiple definitions, so the orchestrator groups
requests by source, endpoint, parameters, vintage, and cutoff before fetching.
Retries remain bounded and source-specific. Provider failures retain sanitized
diagnostic context without response bodies, query secrets, or credentials.

### 5.3 Observation rows

The normalized observation schema is:

```text
record_id, item_id, category, layer, entity_id, entity_name,
observation_date, period_start, period_end, value, unit,
source_id, source_url, retrieved_at, status, qc_status,
is_proxy, is_derived, input_record_ids, formula
```

`entity_id` and `entity_name` are `null` for aggregate metrics. Every derived
row contains resolvable input record IDs and a registered formula. A row whose
numeric value is missing may be published only with an allowed non-success
status and explanatory source execution result.

### 5.4 Coverage rows

Exactly 677 item-level coverage rows are produced for each run:

```text
item_id, category, layer, status, observation_count, latest_observation_date,
source_id, source_url, retrieved_at, reason
```

Allowed statuses are:

- `AVAILABLE`
- `NOT_RELEASED_BY_CUTOFF`
- `NOT_DISCLOSED`
- `NO_ELIGIBLE_OBSERVATION`
- `CREDENTIAL_REQUIRED`
- `PUBLIC_ACCESS_BLOCKED`
- `SOURCE_UNAVAILABLE`
- `FETCH_FAILED`
- `PARSE_FAILED`
- `CALCULATION_INPUT_MISSING`

The status taxonomy makes the difference between “successfully fetched” and
“accounted for” machine-verifiable.

## 6. Source Strategy

Source selection follows this priority:

1. official API or official machine-readable download;
2. official public HTML, PDF, spreadsheet, filing, or release artifact;
3. public-view source named in the document, with terms-monitoring metadata;
4. a transparent calculation from eligible fetched inputs;
5. an explicit non-success status.

The implementation groups adapters by stable source family rather than writing
677 independent fetchers. Existing BLS, BEA, Census, Treasury, EIA, CFTC, USDA,
SEC, World Bank, Yahoo, and market-source code is reused after point-in-time and
provenance tests. Additional families include Federal Reserve releases and
databases, FiscalData, TIC, BIS, IMF, OECD, ECB, Eurostat, BOJ, BOE, PBOC,
ChinaBond, exchange/issuer downloads, and public reports or spreadsheets named
by the document.

Public-view adapters are fail-closed. They do not bypass authentication,
paywalls, robots restrictions, or access controls. If public data is visible but
has no API, the pipeline may parse the permitted page or downloadable artifact
and pins a fixture-backed parser test. If access is not permitted or not
reproducible, the item remains explicitly blocked rather than being silently
substituted.

## 7. S&P 500 and SEC Processing

The company pipeline performs these steps:

1. fetch and parse the configured public S&P 500 holdings file;
2. normalize symbols and preserve the source snapshot;
3. map symbols to CIKs using the SEC public ticker registry;
4. fetch SEC submissions, Company Facts, filing documents, and eligible filing
   exhibits with a configured, truthful SEC user agent;
5. normalize reported XBRL concepts using concept-priority lists and retain the
   source accession, filing date, period, form, and unit;
6. calculate only metrics whose registered inputs are present;
7. distinguish company non-disclosure from provider failure;
8. calculate S&P 500 breadth only from companies with eligible comparable
   periods and publish denominator counts.

IR-only metrics are extracted only from public company or SEC-hosted artifacts.
Non-standard KPI extraction retains the matched source document and is never
generalized to companies that did not disclose that KPI.

## 8. Publication Model

The five business files remain unchanged. Contract 7 adds two tables inside
`context.json.tables`:

- `research_universe_catalog`
- `research_universe_observations`
- `research_universe_coverage`

The catalog and coverage tables always have exactly 677 rows. Observation rows
may be larger or smaller depending on company expansion, disclosure, and the
cutoff. Existing domain-native records continue to publish in their current
tables; the universe observations are the normalized cross-category view used
to prove 677-item coverage.

Contract-7 validation checks catalog identity, count totals, source references,
coverage completeness, observation-to-item references, derived lineage,
point-in-time dates, null semantics, source URLs, status consistency, and
cross-file release identity. Contracts 1 through 6 retain their historical
schemas and validation behavior.

Core provider failures do not replace the stable output. Extension items may
publish a non-success coverage state when the source is legitimately
unavailable, not released, not disclosed, or blocked; programming errors,
malformed schemas, unresolved definitions, and incomplete 677-row coverage
always block publication.

## 9. Cache and Atomicity

All live work occurs in a staging directory. Raw artifacts are content-addressed
and record request identity, source ID, retrieval time, and cutoff. After a fully
validated run, the new release and its raw-cache generation replace the stable
pair. On any failure, neither stable `output/` nor the successful cache is
partially modified.

The live run is authorized once by the user's request. Individual retry probes
or additional live refreshes require a new explicit decision after the first
run's result is known. Read-only source discovery does not publish data.

## 10. Testing and Verification

Every behavior change follows RED-GREEN-refactor with deterministic fixtures.
Tests exercise real parsers and orchestration boundaries; only network I/O and
time are replaced by complete deterministic fakes.

Required verification:

1. exact 677-item and 12-category count tests;
2. source and transform reference validation;
3. cutoff, revision, release-date, and calculation-lineage tests;
4. one controlled parser fixture for every enabled source adapter;
5. S&P 500 constituent, SEC mapping, disclosure, and breadth tests;
6. provider-status and source-sanitization tests;
7. contract-7 build, serialization, and mutation tests;
8. historical contract 1-6 compatibility tests;
9. focused provider tests, then `python3 -m unittest -v`;
10. `node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs`;
11. active-output validation before the live run;
12. post-run validation and stable-pair preservation checks.

## 11. Delivery Slices

The work is implemented as four consecutive, independently reviewable slices:

1. **Catalog and execution foundation:** exact 677-item config, source registry,
   validation, normalized observations, and coverage statuses.
2. **Official and derived sources:** official APIs/downloads, artifact parsers,
   grouped request execution, and calculation graph.
3. **Public-view and company sources:** permitted public artifacts, S&P 500
   membership, SEC facts/events/text, and company breadth.
4. **Contract 7 and live publication:** five-domain integration, compatibility,
   full verification, one authorized live run, and coverage report.

Each slice has its own focused RED/GREEN evidence and task-owned commit.

## 12. Completion Criteria

Implementation is complete when:

- `pipeline/config.json` contains exactly 677 valid unique item definitions;
- every item references a validated source and executable transform or direct
  observation path;
- deterministic tests cover every enabled adapter family and all status paths;
- S&P 500 company processing uses a real public constituent snapshot and SEC
  CIK mapping, not a fixture or invented production list;
- contract 7 publishes a 677-row catalog and a 677-row coverage table within the
  existing five-domain bundle;
- the full Python suite, workbook suite, and active-output validator pass;
- one authorized run is attempted for 2026-08-30;
- a successful run atomically replaces the stable output and cache, while a
  failed run leaves both stable trees byte-identical;
- the handoff reports fetched counts, non-success counts by exact reason,
  provider failures, release identity, output/cache preservation, commits,
  RED/GREEN evidence, and remaining access or licensing risks.

## 13. Explicit Non-Goals

- Treating the 68 corporate definitions as only 68 single-company records.
- Claiming a blocked or non-disclosed item was fetched.
- Circumventing authentication, paywalls, access controls, or terms.
- Using a current constituent list as if it were a historical-vintage S&P 500
  list without an explicit limitation label.
- Adding a sixth business domain or dated output directories.
- Replacing the stable output after a partial or invalid run.
- Editing the adjacent frontend repository.
