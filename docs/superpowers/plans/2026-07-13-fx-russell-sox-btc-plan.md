# FX, Russell 2000, SOX and BTC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add report-required FX, Russell 2000, SOX and BTC/USD histories to the existing CSV and Excel deliverables.

**Architecture:** Extend the existing configuration-driven equity and macro fetchers. Russell 2000 and SOX stay in the equity-index pipeline; FX and BTC use the macro pipeline, which gains dedicated `foreign_exchange` output and workbook sheets while preserving its audit log and divergence logic.

**Tech Stack:** Python 3, pandas, requests, unittest, JavaScript, `@oai/artifact-tool`.

## Global Constraints

- Preserve daily, weekly, MTD and YTD return conventions already used by the project.
- Do not describe vendor histories as official settlement data.
- Keep all source URLs and QC flags visible.
- Do not restore removed short-term interest-rate indicators.

---

### Task 1: Add real Russell 2000 and SOX histories

**Files:**
- Modify: `data/capital_weekly_equity_indices.csv`
- Modify: `capital_weekly/equity_indices.py`
- Modify: `tests/test_capital_weekly_equity_indices.py`

**Interfaces:**
- Consumes: existing `IndexConfig`, `fetch_equity_indices()` and return-calculation pipeline.
- Produces: unique `RUT` and `SOX` rows in `02_equity_indices.csv` and `equity_indices_snapshot.json`.

- [ ] Add a failing configuration test asserting Russell 2000 and SOX exist and that Nasdaq 100 no longer mentions Russell.
- [ ] Run `python -m unittest tests.test_capital_weekly_equity_indices -v` and confirm the new assertion fails.
- [ ] Add stable public historical symbols for Russell 2000 and SOX using an existing or narrowly added provider parser.
- [ ] Run the index tests and confirm they pass.

### Task 2: Add report-required FX and BTC/USD histories

**Files:**
- Modify: `data/capital_weekly_macro_assets.csv`
- Modify: `capital_weekly/macro_assets.py`
- Modify: `scripts/fetch_macro_assets.py`
- Modify: `tests/test_capital_weekly_macro_assets.py`

**Interfaces:**
- Consumes: `fetch_macro_assets()`, existing Yahoo chart parser and macro return/rank functions.
- Produces: `foreign_exchange.csv`, expanded `commodities.csv`, snapshot keys `foreign_exchange` and `commodities`.

- [ ] Add failing tests asserting DXY, USD/CNY, USD/CNH, USD/HKD and BTC/USD exist with `pct` change units and unique codes.
- [ ] Add a failing test that USD pairs retain the report direction and that null observations are discarded.
- [ ] Run `python -m unittest tests.test_capital_weekly_macro_assets tests.test_capital_weekly_macro_divergence -v` and confirm the new tests fail for missing configuration/output.
- [ ] Add the five configurations and reuse the Yahoo chart history parser with explicit proxy notes.
- [ ] Split `foreign_exchange` rows into `foreign_exchange.csv` and the snapshot without changing fixed-income outputs.
- [ ] Run the macro tests and confirm they pass.

### Task 3: Extend workbook presentation and assertions

**Files:**
- Modify: `scripts/build_macro_assets_workbook.mjs`
- Modify: `scripts/build_equity_indices_workbook.mjs` if present; otherwise extend the existing index export path without introducing a second final workbook.
- Test: workbook inspection and export assertions embedded in the builders.

**Interfaces:**
- Consumes: updated snapshots from Tasks 1 and 2.
- Produces: updated `02_equity_indices_python.xlsx` and `fixed_income_commodities_python.xlsx`.

- [ ] Add `fx_divergence` and `foreign_exchange` sheets to the macro workbook sheet-order assertion.
- [ ] Update expected row counts for five commodity/alternative rows and four FX rows.
- [ ] Apply the existing title, header, heatmap, date, QC and source-link formatting conventions.
- [ ] Inspect key ranges and scan for `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?` and `#N/A`.
- [ ] Render every changed sheet and confirm text and sources are legible below the existing 4000px width cap.

### Task 4: Fetch, reconcile and publish

**Files:**
- Update: `outputs/capital_weekly_equity_indices_python_20260710/`
- Update: `outputs/capital_weekly_macro_assets_python_20260713/`

**Interfaces:**
- Consumes: completed fetchers and builders.
- Produces: final CSVs, snapshots, source logs and two formal Excel workbooks.

- [ ] Run both fetchers against live public sources.
- [ ] Assert all six requested additions have `qc_flag=OK`, non-null latest values and current/latest completed trading dates.
- [ ] Reconcile Russell 2000, SOX and BTC/USD levels against a second public quote page; reconcile FX direction and order of magnitude.
- [ ] Build both workbooks with the bundled Node runtime and `@oai/artifact-tool`.
- [ ] Run the full relevant unittest suite and record zero failures.
- [ ] List the final files and report any source-timing caveat explicitly.
