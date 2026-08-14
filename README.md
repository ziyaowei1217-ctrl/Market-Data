# Capital Weekly Market Data

Capital Weekly Market Data is a public-data pipeline for producing an auditable
weekly cross-asset research pack. It collects global equity indices, A/H/US
sector data, US GICS sector proxies, macro assets, and weekly market context.
The coordinated release applies a point-in-time cutoff, validates the complete
Monday-to-Sunday bundle, and publishes a new week only when every required
pipeline succeeds.

Generated snapshots and workbooks are intentionally excluded from Git. Local
snapshots remain under `outputs/week_YYYYMMDD-YYYYMMDD/`, where the Capital
Weekly frontend can read them through `MARKET_DATA_ROOT`. Do not delete
published weeks merely to make the repository clean.

## Pipeline

The coordinated release runs five acquisition stages:

1. Global equity indices — 20 configured indices.
2. Cross-market sectors — 34 A/H/US sector rows plus divergence summaries.
3. US GICS sectors — 11 Sector SPDR ETF proxies.
4. Macro assets — fixed income, policy rates, money markets, commodities, FX,
   real yields, breakevens, and cross-sectional divergence.
5. Weekly context — events, positioning, financial conditions, market
   internals, exchange microstructure, selected SEC filings, optional EIA
   fundamentals, and point-in-time economic releases.

Every bundle includes normalized CSV files and source logs so users can review
provider status, observation dates, quality flags, and source URLs.

## Requirements

- Python 3.10 or newer
- Node.js for workbook packaging
- `@oai/artifact-tool` supplied by the Codex workspace runtime

The Python requirements include `pypdf` for official policy-document parsing
and the constrained `yfinance` 1.x client for optional Yahoo volatility
signals.

```bash
python3 -m pip install -r requirements.txt
```

The Python acquisition and CSV stages are portable. The workbook builder and
verifier currently depend on the Codex-bundled `@oai/artifact-tool`; ensure
your Node environment can resolve that package. Do not commit `node_modules`
or a machine-specific symlink.

## Optional environment variables

- `EIA_API_KEY`: enables the optional EIA commodity-fundamentals provider.
  Without it, the source log records `NOT_CONFIGURED`.
- `SEC_USER_AGENT`: enables SEC requests for companies listed in
  `data/capital_weekly_company_watchlist.csv`. Use a descriptive value that
  includes an organization and contact address.

No credentials are stored in the repository.

### Optional Yahoo volatility signals

The weekly-context pipeline uses `yfinance` to request `^VIX9D`, `^VIX`,
`^VIX3M`, `^VIX6M`, and `^SKEW`. It publishes observed levels plus registered
1M–3M and 9D–1M term calculations into `financial_conditions.csv`.

Yahoo Finance is an optional public research source for this local desktop
workflow. Its failure remains visible in `source_log.csv` but does not block an
otherwise complete week. The provider does not publish option-chain history,
ETF-flow proxies, or generated regime labels.

`yfinance` is not affiliated with or endorsed by Yahoo. Yahoo data is subject
to Yahoo's personal-use terms, so this integration remains limited to the
approved local desktop research workflow.

`EIA_API_KEY` enables the existing free EIA commodity-fundamentals provider.
Keep the key in the process environment; never place it in repository files.

## Coordinated weekly refresh

Run all five pipelines, validate the staged bundle, generate a manifest, and
atomically publish the latest finished week:

```bash
python3 scripts/refresh_capital_weekly.py
```

To reproduce an eligible historical Sunday explicitly:

```bash
python3 scripts/refresh_capital_weekly.py --as-of-date 2026-08-09
```

The coordinator applies the target Sunday cutoff before snapshot returns and
registered derived series are calculated. It writes a manifest containing the
week identity, dataset contract, pipeline status, row counts, hashes, and
validation results. A pipeline, validation, manifest, or final-status failure
leaves the previous complete week active.

Point the local frontend server at this repository with:

```bash
export MARKET_DATA_ROOT="/path/to/market-data"
```

## Individual pipeline diagnostics

The acquisition scripts can be run independently when diagnosing one domain.
Use a temporary output directory and an explicit cutoff for market histories:

```bash
python3 scripts/fetch_equity_indices.py \
  --as-of-date 2026-08-09 \
  --output-dir outputs/manual-equity-indices

python3 scripts/fetch_equity_sectors.py \
  --as-of-date 2026-08-09 \
  --output-dir outputs/manual-equity-sectors

python3 scripts/fetch_gics_sectors.py \
  --as-of-date 2026-08-09 \
  --output-dir outputs/manual-gics-sectors

python3 scripts/fetch_macro_assets.py \
  --as-of-date 2026-08-09 \
  --output-dir outputs/manual-macro-assets

python3 scripts/fetch_weekly_context.py \
  --start-date 2026-08-03 \
  --end-date 2026-08-09 \
  --output-dir outputs/manual-weekly-context
```

These commands may access live public providers. Automated tests use
deterministic fixtures, fake histories, and fake runners instead; they do not
perform a real refresh.

## Historical release migration

Inspect legacy week directories without modifying them or making network
requests:

```bash
python3 scripts/migrate_capital_weekly_releases.py --dry-run
```

The dry run reports each week as `migratable`, `already-valid`, `skipped`, or
`failed`. After review, omit `--dry-run` to repair only registered blank
optional-table headers, validate the matching historical contract, and publish
through the rollback-safe swap. Migration never invents or backfills business
records.

## Build and verify the workbooks

The builder selects the newest correctly named weekly directory under
`outputs/`:

```bash
node scripts/build_weekly_workbooks.mjs outputs tmp/workbook-previews
node scripts/verify_weekly_workbooks.mjs outputs/week_20260803-20260809
```

It produces:

- `01_股票指数_20260803-20260809.xlsx`
- `02_跨市场行业_20260803-20260809.xlsx`
- `03_宏观资产_20260803-20260809.xlsx`
- `04_事件与市场背景_20260803-20260809.xlsx`

## Configuration

The `data/` directory contains the tracked universes and provider settings.
Edit configuration deliberately and retain provider/source metadata for every
new row. The company watchlist is empty by default.

## Tests

```bash
python3 -m unittest -v
node --test tests/test_verify_weekly_workbooks.mjs
```

Tests use fixtures and mocks; they do not require a live weekly fetch.

## Data and usage notes

- Public providers can change schemas, delay observations, or block automated
  requests.
- US GICS rows use tradable ETF proxies rather than official index values.
- A generated file is not proof that every source succeeded; review source
  logs and the release manifest before relying on a snapshot.
- Confirm licensing and redistribution terms before publishing generated data.
- This project is a research-data tool, not investment advice.

## License

MIT. See `LICENSE`.
