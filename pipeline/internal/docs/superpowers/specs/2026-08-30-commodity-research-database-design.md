# Capital Weekly Commodity Research Database

**Date:** 2026-08-30

**Status:** Approved for implementation

**Repositories:**

- Market data: `/Users/a1-6/Documents/market data`
- Dashboard: `/Users/a1-6/Documents/行业与个股分析`

## 1. Objective

Build a complete, auditable commodity-research surface for five areas:

1. Natural gas.
2. Refined products, with crude oil retained as the upstream anchor.
3. Copper.
4. Gold.
5. Agriculture, grouped into grains and oilseeds, soft commodities, and
   livestock.

Each area combines price, physical balance or inventory, and positioning.
Only free official sources are eligible. Paid LME, proprietary futures data,
vendor estimates, and invented substitutes are excluded.

The change must preserve the existing five acquisition domains, five business
JSON files, stable `output/` filenames, atomic publication, and one latest
successful raw-cache generation.

## 2. Product Decisions

- Add a first-class Dashboard page: `05 商品研究 / COMMODITIES`.
- Renumber the current Context and Audit pages to 06 and 07 without otherwise
  splitting Context in this change.
- Keep each fact in one canonical backend table. The Dashboard composes prices,
  fundamentals, and positioning by a stable `commodity_code`.
- Keep price ownership in `macro.json.tables.commodities`.
- Replace the existing Yahoo WTI, Brent, and COMEX Gold commodity prices with
  eligible EIA or World Bank official benchmarks. BTC remains an existing macro
  asset but is not part of Commodity Research.
- Keep physical fundamentals in
  `context.json.tables.commodity_fundamentals`.
- Keep commodity positioning in `context.json.tables.positioning_flows`.
- Do not create `commodities.json`, dated release folders, duplicate price
  rows, or a second production configuration source.
- Show every feed's own observation date. A monthly price, weekly COT report,
  and daily warehouse report must not be presented as if they shared one date.

## 3. Source Policy

### 3.1 Eligible sources

| Source | Use | Credential | Cadence |
| --- | --- | --- | --- |
| U.S. EIA API v2 | Energy prices, storage, supply, demand, refining, trade | Existing `EIA_API_KEY` | Daily, weekly, monthly |
| USDA FAS PSD API | Global agriculture production, use, trade, and stocks | New free `USDA_API_KEY` | Monthly revisions / marketing year |
| USDA FAS ESR API | U.S. weekly export sales, exports, and outstanding sales | New free `USDA_API_KEY` | Weekly |
| USDA NASS official releases | Cattle, hog, crop, and near-term physical detail where deterministic | No key or free key, source-dependent | Weekly, monthly, quarterly |
| CFTC Public Reporting Environment | Disaggregated commodity positioning | None required for normal use | Weekly |
| CME/COMEX public registrar reports | Registered and eligible copper/gold warehouse stocks | None | Trading daily |
| World Bank Pink Sheet | Official free monthly benchmark prices | None | Monthly |
| USGS NMIC | Structural mine production and reserves | None | Annual; monthly only when current publication resumes |

### 3.2 Explicit limitations

- LME warehouse stocks are not included because the required historical data
  are licensed. Copper COMEX stocks are labeled `deliverable_inventory_proxy`,
  never global copper inventory.
- No durable free official daily futures-price history exists for every area.
  EIA daily energy cash prices and World Bank monthly international benchmarks
  are used at their true frequencies. The system does not scrape exchange
  quote pages.
- COMEX gold stocks measure exchange deliverability, not global above-ground
  bullion.
- USGS monthly copper and gold surveys are supplemental while current public
  posting is paused. The annual Mineral Commodity Summary is structural
  context, not a weekly signal.
- Missing official coverage is explicit. It is never replaced with Yahoo,
  zero, an empty string, `NaN`, `Infinity`, or an unlabeled proxy.

## 4. Research Universe

### 4.1 Natural gas

Canonical code: `NATGAS_HH`.

- Henry Hub spot price.
- Lower-48 and available regional working-gas storage.
- Weekly storage change and year-over-year change.
- Five-year seasonal range or deviation, calculated only from eligible EIA
  history with a versioned formula.
- Monthly dry-gas production, consumption by major sector, and LNG trade where
  the EIA route provides stable dated observations.
- CFTC Henry Hub open interest; producer, swap-dealer, managed-money, and other
  reportable net positions; weekly changes; configured trailing percentiles.

### 4.2 Refined products

Canonical codes: `WTI`, `BRENT`, `RBOB_US`, `ULSD_US`, `JET_US`, and
`PROPANE_US` where the corresponding official series exists.

- WTI and Brent cash benchmarks as upstream anchors.
- Commercial crude excluding SPR, finished motor gasoline, distillate, jet
  fuel, and propane stocks.
- Refinery utilization and crude inputs.
- Product supplied, production, imports, and exports for gasoline, distillate,
  and jet fuel where EIA publishes a stable weekly series.
- Weekly level and percentage changes calculated from the latest two eligible
  observations.
- CFTC WTI, RBOB, and ULSD positioning using official contract-market codes.

### 4.3 Copper

Canonical code: `COPPER_COMEX`.

- World Bank monthly copper benchmark price.
- COMEX registered, eligible, and total warehouse stocks, with report date and
  raw workbook hash.
- CFTC COMEX copper positioning and trailing percentiles.
- Latest eligible USGS production, trade, consumption, and reserve context when
  the official publication is current.
- A permanent coverage note states that LME stocks are excluded.

### 4.4 Gold

Canonical code: `GOLD_COMEX`; retain `COMEX_GOLD` as the existing macro
`series_code` for compatibility.

- World Bank monthly gold benchmark price.
- COMEX registered, eligible, and total depository stocks, with report date and
  raw workbook hash.
- CFTC COMEX gold positioning and trailing percentiles.
- Latest eligible USGS mine-production and reserve context.

### 4.5 Agriculture

Agriculture is one Dashboard area with three subsections.

- Grains and oilseeds: corn, soybeans, wheat, and rice.
- Soft commodities: cotton, sugar, coffee, and cocoa.
- Livestock: cattle/beef and hogs/pork.

For every supported commodity, publish the eligible subset of:

- World Bank monthly benchmark price.
- USDA PSD world and configured key-country production, beginning stocks,
  imports, exports, domestic consumption, feed/crush/industrial use, and ending
  stocks.
- A versioned stock-to-use calculation when production and use inputs share an
  eligible release vintage.
- USDA ESR weekly net sales, exports, and outstanding sales where ESR covers
  the commodity.
- USDA NASS cattle-on-feed, hog, slaughter, or crop detail only when a stable
  machine-readable official release and point-in-time cutoff are proven.
- CFTC open interest and disaggregated or supplemental positioning using the
  correct report-family semantics.

The provider resolves USDA commodity, attribute, country, and unit identifiers
from official lookup endpoints and stores the lookup response in the raw
cache. It does not silently guess identifiers from names.

## 5. Cross-Domain Contract

The stable composition key is `commodity_code`. Codes are immutable after
publication.

Add the following fields to macro records:

```text
commodity_code       nullable for non-commodity records
commodity_family     nullable for non-commodity records
price_kind           official_cash | official_monthly_benchmark
known_as_of           ISO-8601 offset timestamp or null when not published
```

Add the following fields to generic context metric records:

```text
commodity_code       nullable for unrelated context records
commodity_family     nullable for unrelated context records
metric_role          physical_fundamental | positioning | null
measurement_kind     inventory | supply | demand | trade | utilization |
                     price | open_interest | net_position | percentile |
                     structural | null
participant_class    producer | swap_dealer | managed_money | other_reportable |
                     index_trader | null
known_as_of           ISO-8601 offset timestamp or null when not applicable
reference_period      source-native period or null
```

The existing `series_code`, `metric_code`, `market`, source fields, observation
date, unit, QC flag, and source status remain unchanged. `market` is not reused
as a commodity join key.

The Dashboard never infers taxonomy by parsing labels or metric-code prefixes.

## 6. Provider Architecture

Providers are small and report-family specific.

- `macro_assets` receives official EIA energy-price and World Bank Pink Sheet
  adapters. It remains the only price/return owner.
- EIA fundamentals are split into natural-gas and refined-products provider
  definitions so one family cannot suppress the other.
- USDA PSD, ESR, and optional NASS adapters are separate providers with shared
  lookup, unit, cutoff, and credential utilities.
- CME copper and gold warehouse workbooks use separate parser configurations
  over a shared binary-workbook transport.
- CFTC TFF and Disaggregated reports have separate parsers and semantics. The
  existing TFF parser continues to own DXY and S&P 500. Commodity contracts use
  the Disaggregated or Supplemental parser only.
- Pure calculation helpers perform no network access and declare formula ID,
  version, input record IDs, observation dates, and output unit.

The current erroneous condition in which Gold and WTI are configured as
Disaggregated contracts but fetched through the financial-futures archive must
be corrected before commodity positioning is activated.

## 7. Point-in-Time, Freshness, and Units

- Apply the target `as_of_date` before selecting any observation or calculating
  a return, change, percentile, seasonal comparison, or stock-to-use ratio.
- Preserve both observation date and `known_as_of`. CFTC Tuesday positions are
  not eligible before their Friday release.
- USDA revisions are selected by release vintage. A later revision never
  rewrites what was known by an earlier target Sunday.
- Default freshness limits:
  - Energy physicals: 10 calendar days.
  - CFTC: 10 calendar days from the eligible Friday release.
  - CME warehouse reports: 5 trading days.
  - USDA ESR: 14 calendar days.
  - USDA PSD/WASDE: 45 calendar days.
  - World Bank price workbook: 45 calendar days.
  - Annual USGS structural context: 400 calendar days.
- Preserve source-native units and publish a canonical display unit only through
  a registered conversion. Bcf, MMBtu, thousand barrels, thousand barrels per
  day, pounds, metric tons, troy ounces, bushels, and head are not
  interchangeable.
- Unknown or changed units fail that provider rather than being coerced.

## 8. Publication and Failure Rules

- A provider becomes required when its required credential is configured and
  the capability is activated in `pipeline/config.json`.
- Missing `USDA_API_KEY` publishes a `NOT_CONFIGURED` source-log record and no
  USDA rows. It does not fabricate or reuse old data.
- Once configured, EIA, USDA PSD/ESR, World Bank prices, and CFTC positioning
  are core providers. Their schema, coverage, freshness, or fetch failure
  blocks replacement of the stable release.
- CME warehouse and USGS/NASS structural details are supplemental. Their
  failure publishes no rows and remains visible in the source log.
- Every configured required commodity must have the intended price,
  fundamental, and positioning capability status represented in the release.
  A missing configured CFTC contract is a provider failure, not a silent
  omission.
- Supplemental partial availability is allowed only at provider-family
  boundaries. A corrupt row never causes the remaining rows from the same
  provider to publish.
- The previous complete stable output remains visible after any required
  failure. No stale prior commodity row is copied into a new release.
- Only the latest successful raw-cache generation remains under
  `pipeline/.cache/`.

## 9. Dashboard Design

Navigation becomes:

1. 市场总览.
2. 全球股指.
3. 行业表现.
4. 宏观资产.
5. 商品研究.
6. 事件与背景.
7. 数据审计.

The Commodity page has family tabs for Natural Gas, Refined Products, Copper,
Gold, and Agriculture. Agriculture has secondary sections for grains and
oilseeds, softs, and livestock.

Each family renders:

1. A compact coverage and date strip for price, physicals, and positioning.
2. Price levels and changes from canonical macro records.
3. Physical balance, inventory, trade, and derived fundamental tables.
4. Positioning by participant class, open interest, weekly changes, and
   percentiles.
5. Source and coverage limitations, including the copper LME exclusion.

Rows reuse the existing detail drawer and preserve release, file, dataset,
source URL, observation date, known-as-of timestamp, quality status, formula,
and inputs.

Within a valid release, a family may render its valid feeds and show compact
feed-specific empty states for unavailable supplemental data. It never shows a
placeholder price or zero. A completely empty family is omitted and remains
visible in Data Audit through its provider status.

## 10. Testing

All behavior changes follow TDD. Automated tests use deterministic fake
histories, fake API responses, and fixture workbooks; they do not access the
network.

Backend coverage:

- additive config and schema fields;
- EIA, USDA, World Bank, CME, CFTC Disaggregated, and optional NASS parsers;
- official identifier, unit, and report-family validation;
- observation and known-as-of cutoff enforcement;
- freshness and provider-family isolation;
- matched-input calculations and null handling;
- required/optional status allowlists and atomic rollback;
- stable JSON row counts, hashes, and cross-domain composition keys;
- one latest raw-cache generation.

Frontend coverage:

- normalized composition by exact `commodity_code`;
- all five families and three agriculture subsections;
- mixed feed dates, absent feeds, invalid QC, unknown codes, and duplicate
  identity handling;
- search, keyboard tabs, density, detail inspection, and provenance;
- navigation, view-scoped quality/as-of calculation, and regression exclusion
  of DXY, S&P 500, FINRA, and BTC from commodity research;
- stable release fixture hash and schema validation;
- unit tests, lint, production build, and browser smoke coverage.

Before completion, run focused tests, `python3 -m unittest -v`, workbook
compatibility, Dashboard unit tests, lint, build, browser smoke tests, one
explicitly authorized live source smoke check, a real weekly refresh, and
`validate_output_bundle`.

## 11. Delivery Sequence

1. Add the taxonomy/schema contract without changing the active data universe.
2. Split and correct CFTC TFF versus commodity Disaggregated positioning.
3. Add EIA natural-gas and refined-products price/fundamental coverage.
4. Add World Bank prices and CME/USGS metals coverage.
5. Add USDA PSD/ESR and optional NASS agriculture coverage.
6. Build the dedicated Commodity Dashboard page over the stable JSON contract.
7. Run live source probes, formal refresh, full verification, and end-to-end
   page validation.

Each sequence item is independently testable and commit-scoped. No later item
may bypass an earlier contract or publication gate.

## 12. Acceptance Criteria

- The stable release still contains exactly five business JSON files plus
  `release.json` and no dated output directories.
- Each published commodity record resolves to one canonical
  `commodity_code`, an HTTP(S) source, an observation date, a known-as-of rule,
  a valid source-native unit, and an accepted QC or provider status.
- The Commodity page composes price, physical, and positioning data without
  duplicating backend facts or parsing display labels.
- All five areas and all three agriculture subsections have explicit capability
  coverage; unavailable free-official coverage is factual and visible.
- No requested Commodity Research value comes from a paid, licensed, vendor,
  example, mock, zero-filled, stale-carried, NaN, or infinite production
  source. Existing unrelated macro/FX records remain outside this design.
- Required-source failure cannot replace the previous complete release.
- Focused, full, compatibility, build, and browser checks pass, and the active
  output validates after the real refresh.
