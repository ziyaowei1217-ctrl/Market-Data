# Capital Weekly data-pipeline instructions

## Repository boundary

- `pipeline/` contains all tracked implementation, configuration, tests, and engineering documents.
- `output/` contains only the latest complete successful JSON release and is not committed to Git.
- The only visible top-level product directories are `pipeline/` and `output/`.
- The frontend is a separate future repository. Do not modify the adjacent Next.js checkout from this backend repository.

## Data and publication rules

- Apply `as_of_date` before calculating any snapshot return or derived value.
- Keep the existing five data domains: indices, cross-market sectors, GICS, macro assets, and weekly context.
- A release becomes visible only after all five pipelines and cross-file validation succeed.
- Refresh replaces the stable files in `output/`; it must not create dated or historical week directories.
- Keep one successful raw-cache generation under `pipeline/.cache/`.
- `pipeline/config.json` is the only production configuration source; explicit
  CSV paths exist only for deterministic tests and diagnostics.
- Empty optional context collections remain present as empty arrays.
- Never use zero, an empty string, `NaN`, or `Infinity` to represent missing JSON data; use `null`.
- Every published business record retains its source URL, observation date, and QC or source status.
- Tests use deterministic fake histories or runners. Do not run a real network refresh unless the user explicitly requests it.
- Offline initialization may read an explicitly supplied legacy `outputs/`
  tree, but it must validate manifests and hashes and must never invoke a
  pipeline runner.

## Warehouse subsystem (`pipeline/warehouse/`)

- The warehouse is a separate subsystem that keeps versioned history in Supabase
  Postgres; it never reads or writes `output/` and does not change the five pipelines.
- Its catalog comes from the 数据采集清单 workbook (`catalog/indicators.csv`) and
  `catalog/mapping.py`; regenerate the CSVs instead of editing them by hand.
- Missing data stays NULL with an explicit `status`; never fill with zero.
- Reading requires a signed-in Supabase account whose confirmed email is in
  `public.readers` (`private.is_reader()` policy); anon sees nothing. Never commit
  reader emails or passwords; add readers in the database, not in `schema.sql`.
- `supabase/functions/warehouse-mcp/` is the read-only MCP server (Edge Function, deployed
  with `--no-verify-jwt`; it checks personal `cw_` reader keys stored as hashes in
  `public.reader_keys`). Never commit a reader key. Tests:
  `node --experimental-strip-types --test supabase/functions/warehouse-mcp/server.test.ts`.
- `method = 'manual'` rows come from `catalog/manual/*.csv` (official announcements only,
  dates as YYYYMMDD) and are computed when they have a formula.
- Checking a new source's layout from the cloud: list it in `catalog/inspect_urls.txt`
  (modes FOLLOW / RAW / LINKS / JSONKEYS / GREP; `{X_API_KEY}` placeholders are masked) and run
  `gh workflow run warehouse.yml --ref warehouse -f command=inspect`; previews come back as the
  job's check-run annotations (about 4 KB each) and nothing is written to the database.
- `method = 'proxy'` values come from a stand-in (an ETF tracking the index, or a
  sister index family); say so when charting them.
- Scheduled and manual runs start on the default branch but check out `warehouse`;
  `sync_catalog` refuses to run from a checkout older than the one that last wrote the catalog.
- Tests: `python3 -m unittest discover -s pipeline/warehouse/tests -t .` (no network).
- See `pipeline/warehouse/README.md` for tables, formulas and operations.

## Report subsystem (`pipeline/report/`)

- Draws the weekly issue 市场一周 (A4 PDF plus single charts) from the warehouse; it reads
  warehouse data only (observations, newest vintage) and never writes it, `output/`, or the five
  pipelines. Its only database objects are in `pipeline/report/storage.sql` (the `reports` bucket,
  its readers-only policy, and one-time upload tickets). `pipeline/report/issue.json` is its
  configuration (assets, tenors, charts).
- The issue is laid out with the Richard Wei Finance design system's own components, vendored in
  `pipeline/report/ds/` (with marked local patches; see its README), by `issue.py` (content) and
  `render.py` (headless Chromium via Playwright). Keep its rules: one crimson subject per chart,
  findings as band titles, a dated source under every chart, the risk warning on pages with returns,
  facts only (no views or forecasts).
- Weekly cutoff is Friday; `date_rule = "asof"` uses each series' last value on or before the
  cutoff within six days and names proxies and earlier observation dates in the issue's data notes.
  Missing data stays blank; never interpolate or fill with zero.
- `.github/workflows/report.yml` runs after the scheduled warehouse run and uploads to the private
  Storage bucket `reports` (`storage.sql`: readers only) through signed links from the
  `supabase/functions/report-upload/` Edge Function (deployed with `--no-verify-jwt`; it trusts only
  tickets the workflow wrote over `WAREHOUSE_DB_URL`). Tests:
  `node --experimental-strip-types --test supabase/functions/report-upload/server.test.ts`.
  This repository is public and issues contain
  licensed data: never upload issues as workflow artifacts or print data values to logs, and never
  commit real-data fixtures.
- Tests: `python3 -m unittest discover -s pipeline/report/tests -t .` (no network; SQLite fakes).

## Development workflow

- Follow TDD for behavior changes and show the expected RED before implementation.
- Run focused unittest modules followed by `python3 -m unittest -v`.
- Run `node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs` while the workbook compatibility tests remain present.
- Validate the active output with
  `pipeline.internal.capital_weekly.weekly_release.validate_output_bundle` before
  cleanup or completion.
- Do not switch branches, rebase, reset, or merge other work inside an execution chat.
- Preserve unrelated dirty or untracked files and archive them recoverably before cleanup.
- Commit only the files owned by the active implementation-plan task.

## Handoff

Report commit SHAs, moved/created/deleted files, RED/GREEN evidence, full test results, the source release used for offline conversion, the stable output identity, the recoverable cleanup archive, and remaining compatibility risks.
