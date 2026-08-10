# Capital Weekly Market Data

Capital Weekly Market Data is a public-data pipeline for producing an
auditable weekly cross-asset research pack. It collects global equity indices,
A/H/US sector data, US GICS sector proxies, macro assets, and weekly market
context, then packages normalized CSV files into four Excel workbooks.

Generated data and workbooks are intentionally excluded from this repository.
Every output bundle includes a source log so users can review provider,
observation date, status, and provenance before relying on a result.

## Pipeline

1. Global equity indices — 20 configured indices.
2. Cross-market sectors — 34 A/H/US sector rows plus divergence summaries.
3. US GICS sectors — 11 Sector SPDR ETF proxies.
4. Macro assets — fixed income, policy rates, money markets, commodities, FX,
   and cross-sectional divergence.
5. Weekly context — events, positioning, financial conditions, market
   internals, exchange microstructure, selected SEC filings, and optional EIA
   fundamentals.

## Requirements

- Python 3.9 or newer
- Node.js for workbook packaging
- `@oai/artifact-tool` supplied by the Codex workspace runtime

The Python requirements include `pypdf` for official policy-document parsing.

Install the Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

The Python acquisition and CSV stages are portable. The workbook builder and
verifier currently depend on the Codex-bundled `@oai/artifact-tool`; ensure
your Node environment can resolve that package. Do not commit `node_modules`
or a machine-specific symlink.

## Optional environment variables

- `EIA_API_KEY`: enables the EIA commodity-fundamentals provider. Without it,
  the source log records `NOT_CONFIGURED`.
- `SEC_USER_AGENT`: enables requests for companies listed in
  `data/capital_weekly_company_watchlist.csv`. Use a descriptive value that
  includes an organization and contact address.

No credentials are stored in the repository.

## Run a weekly cycle

The output directory must follow `outputs/week_YYYYMMDD-YYYYMMDD/`. This
example builds the week ending 9 August 2026:

```bash
period="20260803-20260809"
week_dir="outputs/week_${period}"

python3 scripts/fetch_equity_indices.py \
  --output-dir "${week_dir}/capital_weekly_equity_indices_python_20260809"

python3 scripts/fetch_equity_sectors.py \
  --output-dir "${week_dir}/capital_weekly_equity_sectors_python_20260809"

python3 scripts/fetch_gics_sectors.py \
  --output-dir "${week_dir}/capital_weekly_gics_sectors_python_20260809"

python3 scripts/fetch_macro_assets.py \
  --as-of-date 2026-08-09 \
  --output-dir "${week_dir}/capital_weekly_macro_assets_python_20260809"

python3 scripts/fetch_weekly_context.py \
  --start-date 2026-08-03 \
  --end-date 2026-08-09 \
  --output-dir "${week_dir}/capital_weekly_context_20260809"
```

Network providers can fail independently. Check every `source_log.csv` before
building the workbooks; a generated file is not evidence that every source
succeeded.

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

Tests use fixtures and mocks; they do not require a full live weekly fetch.

## Data and usage notes

- Public providers can change schemas, delay observations, or block automated
  requests.
- US GICS rows use tradable ETF proxies rather than official index values.
- Confirm licensing and redistribution terms before publishing generated data.
- This project is a research-data tool, not investment advice.

## License

MIT. See `LICENSE`.

## 使用手册
目前需要在终端运行 5 个采集程序。以 2026-08-03 至 2026-08-09 这一周为例：
1. 下载并安装
git clone https://github.com/ziyaowei1217-ctrl/Market-Data.git
cd Market-Data

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
2. 采集每周数据
period="20260803-20260809"
week_dir="outputs/week_${period}"

python3 scripts/fetch_equity_indices.py \
  --output-dir "${week_dir}/capital_weekly_equity_indices_python_20260809"

python3 scripts/fetch_equity_sectors.py \
  --output-dir "${week_dir}/capital_weekly_equity_sectors_python_20260809"

python3 scripts/fetch_gics_sectors.py \
  --output-dir "${week_dir}/capital_weekly_gics_sectors_python_20260809"

python3 scripts/fetch_macro_assets.py \
  --as-of-date 2026-08-09 \
  --output-dir "${week_dir}/capital_weekly_macro_assets_python_20260809"

python3 scripts/fetch_weekly_context.py \
  --start-date 2026-08-03 \
  --end-date 2026-08-09 \
  --output-dir "${week_dir}/capital_weekly_context_20260809"
生成结果位于：
outputs/week_20260803-20260809/
里面会有股票指数、行业、宏观资产、事件背景等 CSV，以及数据来源状态 source_log.csv。每周运行时只需要替换开始日期、结束日期和目录日期。
