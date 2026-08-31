# Active Backend Branch Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the two active backend branches, integrate their compatible public-data and commodity-research capabilities into `main`, repair ChinaBond, publish one validated current weekly bundle, and remove only the merged active worktrees and branches.

**Architecture:** Treat `codex/public-green-integration` as the current five-domain/public-capability baseline and `codex/commodity-research-backend` as an additive official-commodity subsystem. Preserve public release contracts 1–5, introduce contract 6 for their union, keep exactly five business JSON files, and route commodity history and facts through tables nested in `macro.json` and `context.json`. Resolve the overlapping provider, macro, context, and release modules semantically; no branch tree is selected wholesale.

**Tech Stack:** Python 3.9 standard library and `unittest`, pandas, requests, Node.js built-in test runner, Git worktrees, JSON/CSV publication, SHA-256 manifests.

**Spec:** `pipeline/internal/docs/superpowers/specs/2026-08-30-active-branch-consolidation-design.md`

## Global Constraints

- Keep only `pipeline/` and `output/` as visible top-level product directories.
- Keep `pipeline/config.json` as the only production configuration source.
- Keep exactly five acquisition and publication domains: indices, cross-market sectors, GICS, macro assets, and weekly context.
- Apply `as_of_date` before selecting or deriving any observation.
- Publish a stable bundle only after all five pipelines and cross-file validation succeed.
- Preserve the active `output/` and successful `pipeline/.cache/` generation until a final live refresh succeeds.
- Preserve missing values as `null`, never zero, an empty string, `NaN`, or infinity.
- Preserve each business record's source URL, observation date, and QC/source status.
- Preserve `pipeline/internal/docs/2026-08-30-current-data-12-category-audit.md` byte-for-byte and do not commit it.
- Use deterministic histories/runners for tests. The only network run in this plan is the final user-authorized coordinated refresh.
- Use `apply_patch` for source and test edits. Do not rebase, reset, force-delete, or force-remove a worktree.
- Final dataset-contract numbering is 1–6: public contracts 1–5 keep their existing meaning; contract 6 is the public-green plus commodity-research union. Manifest schema remains 3 and output schema remains `1.0`.
- Do not claim the 677-item universe is complete; no production company watchlist is invented.

## File and Responsibility Map

- `pipeline/config.json`: one production configuration document; final exact top-level and row-set union.
- `pipeline/internal/capital_weekly/context/provider_contracts.py`: union provider result/spec types, failure provenance, phase diagnostics, and fixed required identities.
- `pipeline/internal/capital_weekly/context/providers.py`: one provider registry containing all public-green and commodity providers.
- `pipeline/internal/capital_weekly/macro_assets.py`: public macro/liquidity/cross-asset calculations plus official EIA/World Bank price acquisition and bounded commodity histories.
- `pipeline/internal/scripts/fetch_macro_assets.py`: writes all public macro tables and `commodity_price_history.csv` from `MacroAssetBundle`.
- `pipeline/internal/capital_weekly/weekly_context.py`: public context categories plus commodity metric histories, research facts, and provider-phase diagnostics.
- `pipeline/internal/capital_weekly/weekly_release.py`: contracts 1–6, staged validation, five-file output mapping, atomic publish, and failure status.
- `README.md`: unified runtime, credentials, failure behavior, and publication contract.
- `pipeline/internal/tests/test_active_branch_consolidation.py`: new cross-branch acceptance test for contract 6 and exact configuration union.
- Existing tests in `pipeline/internal/tests/`: retain both behavior families; update only expectations made obsolete by contract 6 and the exact unified config.
- `pipeline/internal/capital_weekly/macro_assets.py`, `pipeline/config.json`, and `pipeline/internal/tests/test_capital_weekly_macro_assets.py`: ChinaBond endpoint, envelope parser, source URLs, and focused tests.

---

### Task 1: Freeze Inputs and Create the Recoverable Safety Record

**Files:**
- Preserve: `pipeline/internal/docs/2026-08-30-current-data-12-category-audit.md`
- Read: `output/release.json`
- Read: `output/*.json`
- Archive outside worktree: `.git/codex-archives/2026-08-30-active-branch-consolidation/`

**Interfaces:**
- Consumes: clean active worktrees, the committed plan tip on `main` whose first unpublished parent is `4114618`, `codex/public-green-integration@9c086eb`, and `codex/commodity-research-backend@9e7670b`.
- Produces: exact branch/worktree/status record, stable-output identity, SHA-256 fingerprints, and a recoverable copy of the unrelated audit file.

- [ ] **Step 1: Confirm branch and worktree identities**

Run:

```bash
git worktree list --porcelain
git rev-parse main codex/public-green-integration codex/commodity-research-backend
git status --short
git -C .worktrees/public-green-integration status --short
git -C .worktrees/commodity-research-backend status --short
```

Expected: the two active worktrees are registered; both are clean; main shows only the unrelated audit file as untracked. If any source tip differs, record the new tip and inspect its commits before continuing.

- [ ] **Step 2: Archive and hash the unrelated audit file**

Run:

```bash
consolidation_archive=".git/codex-archives/2026-08-30-active-branch-consolidation"
mkdir -p "$consolidation_archive"
cp -p pipeline/internal/docs/2026-08-30-current-data-12-category-audit.md "$consolidation_archive/"
shasum -a 256 pipeline/internal/docs/2026-08-30-current-data-12-category-audit.md "$consolidation_archive/2026-08-30-current-data-12-category-audit.md"
```

Expected: the two hashes are identical. The archive is recoverable under `.git/` and does not add a visible top-level product directory.

- [ ] **Step 3: Record the stable output identity before mutation**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path

release = json.loads(Path("output/release.json").read_text(encoding="utf-8"))
print({key: release.get(key) for key in ("release_id", "as_of_date", "source_week", "status")})
PY
shasum -a 256 output/*.json
```

Expected current identity: release `20260828T060805+0800-5830b4`, `as_of_date=2026-08-23`, source week `week_20260817-20260823`, status `complete`. If the identity changed because another authorized run completed, use the newly validated identity as the preservation baseline.

### Task 2: Re-verify Both Finished Source Branches

**Files:**
- Verify: `.worktrees/commodity-research-backend/pipeline/internal/capital_weekly/commodity_research.py`
- Verify: `.worktrees/commodity-research-backend/pipeline/internal/tests/test_capital_weekly_commodity_research.py`
- Verify: all tracked files in both active worktrees.

**Interfaces:**
- Consumes: commodity revision-collapse commit `9e7670b` and public-green tip `9c086eb`.
- Produces: fresh focused/full GREEN evidence before either branch enters `main`.

- [ ] **Step 1: Confirm the commodity point-in-time fix is the only post-design source change**

Run:

```bash
git show --check --stat 9e7670b
git log --oneline e6f1619..codex/commodity-research-backend
```

Expected: one commit, `9e7670b fix: collapse commodity point-in-time revisions`; no whitespace errors.

- [ ] **Step 2: Re-run the focused commodity test module**

Run from `.worktrees/commodity-research-backend`:

```bash
python3 -m unittest -v pipeline.internal.tests.test_capital_weekly_commodity_research
```

Expected: 50 tests pass, including the two formerly failing same-observation revision tests.

- [ ] **Step 3: Run the commodity branch's full verification**

Run from `.worktrees/commodity-research-backend`:

```bash
python3 -m unittest -v
node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs
```

Expected: both commands exit 0. An unexpected failure stops integration and is diagnosed with `superpowers:systematic-debugging`; it is not waived.

- [ ] **Step 4: Run the public-green branch's full verification**

Run from `.worktrees/public-green-integration`:

```bash
python3 -m unittest -v
node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs
```

Expected: both commands exit 0.

### Task 3: Carry the Approved Planning Records into Public Green and Fast-forward Main

**Files:**
- Merge only: `pipeline/internal/docs/superpowers/specs/2026-08-30-active-branch-consolidation-design.md`
- Merge only: `pipeline/internal/docs/superpowers/plans/2026-08-30-active-branch-consolidation.md`

**Interfaces:**
- Consumes: clean main containing the approved design and implementation plan, plus the clean public-green worktree.
- Produces: public-green descendant containing both approved planning records, then a fast-forwarded `main` containing the complete public-green implementation.

- [ ] **Step 1: Merge main's design-only commit into the public-green worktree**

Run from `.worktrees/public-green-integration`:

```bash
git merge --no-ff main -m "merge: carry consolidation design into public green"
git status --short
git diff HEAD^1..HEAD --stat
```

Expected: a clean merge whose second-parent contribution is only the approved design and implementation-plan documents.

- [ ] **Step 2: Fast-forward main to the synchronized public-green tip**

Run from repository root:

```bash
git merge --ff-only codex/public-green-integration
git merge-base --is-ancestor codex/public-green-integration main
git status --short
```

Expected: fast-forward succeeds; main still shows the unrelated audit file as untracked and contains no other dirty file.

### Task 4: Establish RED Acceptance Tests for the Unified Contract

**Files:**
- Create: `pipeline/internal/tests/test_active_branch_consolidation.py`

**Interfaces:**
- Consumes: public-green contract 5 and public-green-only `pipeline/config.json`.
- Produces: deterministic RED tests for contract 6, five-file output mapping, and the exact public-plus-commodity configuration.

- [ ] **Step 1: Add the cross-branch acceptance test**

Create this file with `apply_patch`:

```python
import json
from pathlib import Path
import unittest

from pipeline.internal.capital_weekly.weekly_release import (
    DATASET_CONTRACT_VERSION,
    OUTPUT_BUSINESS_FILES,
    SUPPORTED_DATASET_CONTRACT_VERSIONS,
    release_datasets_for_contract,
)


CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"
COMMODITY_TABLES = {
    ("macro_assets", "commodity_price_history.csv"),
    ("weekly_context", "commodity_metric_history.csv"),
    ("weekly_context", "commodity_research_facts.csv"),
}


class UnifiedReleaseContractTests(unittest.TestCase):
    def test_contract_six_is_additive_and_preserves_contract_five(self):
        self.assertEqual(DATASET_CONTRACT_VERSION, 6)
        self.assertEqual(SUPPORTED_DATASET_CONTRACT_VERSIONS, frozenset(range(1, 7)))
        contract_five = {
            (item.pipeline, item.filename)
            for item in release_datasets_for_contract(5)
        }
        contract_six = {
            (item.pipeline, item.filename)
            for item in release_datasets_for_contract(6)
        }
        self.assertTrue(COMMODITY_TABLES.isdisjoint(contract_five))
        self.assertTrue(COMMODITY_TABLES.issubset(contract_six))
        self.assertEqual(
            OUTPUT_BUSINESS_FILES,
            ("indices.json", "sectors.json", "gics.json", "macro.json", "context.json"),
        )

    def test_production_config_is_the_exact_semantic_union(self):
        document = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            set(document),
            {"schema_version", "indices", "sectors", "gics", "macro", "context", "commodity_research"},
        )
        self.assertEqual(len(document["indices"]), 20)
        self.assertEqual(len(document["sectors"]), 34)
        self.assertEqual(len(document["gics"]), 11)
        self.assertEqual(len(document["macro"]), 81)
        self.assertEqual(set(document["context"]), {
            "breadth_universe", "cftc_contracts", "commodity_http",
            "company_watchlist", "eia_series", "financial_conditions",
            "metals", "usda_esr", "usda_psd", "yahoo_volatility",
        })
        self.assertEqual(len(document["context"]["cftc_contracts"]), 18)
        self.assertEqual(len(document["context"]["eia_series"]), 33)
        self.assertEqual(document["context"]["company_watchlist"], [])
        by_code = {row["series_code"]: row for row in document["macro"]}
        self.assertEqual(by_code["WTI"]["provider"], "eia_v2")
        self.assertEqual(by_code["BRENT"]["provider"], "eia_v2")
        self.assertEqual(by_code["COMEX_GOLD"]["provider"], "world_bank_pink_sheet")
        self.assertEqual(by_code["BTC_USD"]["price_kind"], "vendor_proxy")
        research_codes = {
            row["commodity_code"]
            for row in document["commodity_research"]["universe"]
        }
        self.assertNotIn("BTC_USD", research_codes)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm RED before merging commodity code**

Run:

```bash
python3 -m unittest -v pipeline.internal.tests.test_active_branch_consolidation
```

Expected: both tests fail on the public-only tree; the first reports contract 5 instead of 6 and the second reports missing commodity configuration/counts. Keep this task-owned test uncommitted for the commodity merge.

### Task 5: Start the Commodity Merge and Resolve Configuration/Provider Contracts

**Files:**
- Modify: `pipeline/config.json`
- Modify: `pipeline/internal/capital_weekly/context/provider_contracts.py`
- Modify: `pipeline/internal/capital_weekly/context/providers.py`
- Modify: `pipeline/internal/tests/test_pipeline_config.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_context_providers.py`
- Modify: `README.md`
- Preserve automatic merge: `pipeline/internal/capital_weekly/context/positioning.py`
- Modify conflict test: `pipeline/internal/tests/test_capital_weekly_positioning.py`

**Interfaces:**
- Consumes: public provider registry and commodity official-provider implementations.
- Produces: one typed provider contract and registry supporting public events/releases/flows/company data plus official commodity data and diagnostics.

- [ ] **Step 1: Start a non-committing commodity merge**

Run:

```bash
git merge --no-ff --no-commit codex/commodity-research-backend
git diff --name-only --diff-filter=U
```

Expected: content conflicts in exactly these 13 files: `README.md`, `pipeline/config.json`, provider contracts/registry, macro assets, weekly context/release, macro fetch script, and five overlapping test files. Automatic merges, including `context/positioning.py`, remain intact.

- [ ] **Step 2: Resolve the provider dataclasses as a strict union**

Use `apply_patch` so `ProviderResult` and `ProviderSpec` have these exact additive fields:

```python
@dataclass(frozen=True)
class ProviderResult:
    category: str
    rows: list[dict]
    raw_text: str | bytes
    source: str
    source_url: str
    status: str = "OK"
    notes: str = ""
    raw_is_diagnostic: bool = False
    attempts: int = 1
    completed_phase: str = "normalized"


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    category: str
    source_tier: str
    requiredness: str
    provider_version: str
    schema_version: str
    frequency: str
    freshness_days: int | None
    failure_source: str = ""
    failure_source_url: str = ""
```

Retain `FIXED_REQUIRED_CONTEXT_IDENTITIES`, `PROVIDER_PHASES`, `ProviderPhaseError`, cutoff/filter/capture helpers, and export all of them through `__all__`.

- [ ] **Step 3: Resolve `pipeline/config.json` to exact union counts and identities**

Use these deterministic rules:

```text
top-level keys: schema_version, indices, sectors, gics, macro, context, commodity_research
indices/sectors/gics: public-green rows unchanged (20/34/11)
macro: 81 unique series_code rows
shared WTI, BRENT, COMEX_GOLD, BTC_USD: commodity branch definitions
public-only macro rows: retain all 23
commodity-only macro rows: retain all 11
context keys: exact 10-key union
cftc_contracts: commodity branch's 18 enriched identities
eia_series: commodity branch's 32 enriched rows plus public WTESTUS1 legacy row
company_watchlist: []
commodity_research: commodity branch document unchanged
```

Give the retained WTESTUS1 row `provider="eia_commodities"` and `freshness_days="10"`; do not assign it a commodity research code. Keep all production URLs HTTPS.

- [ ] **Step 4: Resolve the provider registry semantically**

Use the commodity branch as the base for official HTTP retries, phase errors, USDA, metals, split EIA providers, and commodity CFTC semantics. Port all public-only imports/functions and register these public-only provider names:

```python
PUBLIC_ONLY_PROVIDERS = {
    "bls_economic_releases", "bea_economic_releases",
    "census_retail_sales", "census_housing", "census_durable_goods",
    "fomc_calendar", "ism_manufacturing_pmi",
    "sec_company_fundamentals", "sec_guidance_proxy",
    "sec_capital_markets", "hkex_capital_markets",
    "yahoo_market_state", "ishares_ivv_fund", "hkex_stock_connect_flows",
    "eia_commodities",
}
```

Rename the public simple EIA function to `_legacy_eia_provider` and feed it only rows with `provider == "eia_commodities"`. Feed `eia_natural_gas` and `eia_refined_products` only their own rows. Keep the commodity branch's conditional requiredness for EIA/USDA and the public branch's fixed required identities/failure provenance.

Diagnostic CSV fixtures use the final schema. Update public fixture writers to include `report_family`, `market_name`, `freshness_days`, commodity fields, and EIA `provider`; do not maintain two production schemas.

When validating configuration, call `validate_eia_spec` only for rows whose provider is `eia_natural_gas` or `eia_refined_products`. Validate the retained `eia_commodities` row through the legacy EIA parser/registry tests so its intentionally smaller schema is explicit rather than silently ignored.

- [ ] **Step 5: Resolve config/provider tests as the union**

Retain semantic tests from both branches. Remove the two obsolete whole-section SHA expectations because the approved union intentionally changes those sections. Replace them with exact counts/identity tests in `test_active_branch_consolidation.py`. Preserve tests for:

```text
public required provider registry and failure provenance
public economic/company/flow/capital-market providers
commodity phase/attempt/error diagnostics
official EIA/USDA/metals transports and conditional requiredness
TFF vs disaggregated CFTC semantics
no API-key leakage
```

Run syntax compilation even though the merge is not yet fully resolved:

```bash
python3 -m py_compile pipeline/internal/capital_weekly/context/provider_contracts.py pipeline/internal/capital_weekly/context/providers.py
```

Expected: exit 0.

### Task 6: Resolve Macro Acquisition and Publication

**Files:**
- Modify: `pipeline/internal/capital_weekly/macro_assets.py`
- Modify: `pipeline/internal/scripts/fetch_macro_assets.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_macro_assets.py`
- Preserve/add from commodity branch: `pipeline/internal/capital_weekly/commodity_prices.py`
- Preserve/add from public branch: `pipeline/internal/capital_weekly/cross_asset.py`

**Interfaces:**
- Consumes: 81 `MacroAssetConfig` rows, official commodity HTTP policies, public calculated-series definitions.
- Produces: `fetch_macro_asset_bundle(...) -> MacroAssetBundle`, compatibility `fetch_macro_assets(...) -> tuple[pd.DataFrame, pd.DataFrame]`, public macro tables, and `commodity_price_history.csv`.

- [ ] **Step 1: Build the union `MacroAssetConfig` and calculated-series registry**

Keep the commodity branch's optional metadata fields:

```python
commodity_code: str = ""
commodity_family: str = ""
price_kind: str = ""
known_as_of: str = ""
provider_route: str = ""
freshness_days: str = ""
source_description: str = ""
```

Retain all public calculated series and correlations: `UST30Y5Y`, `USHY_IG_OAS`, `FED_NET_LIQUIDITY`, the four 13W correlations, and the four 26W correlations, in addition to the commodity branch's existing curve/breakeven calculations. Preserve public source-tier, requiredness, H.4.1 publication-lag, and optional-correlation behavior.

- [ ] **Step 2: Keep the official commodity bundle without dropping public tables**

Use the commodity `MacroAssetBundle` and `fetch_macro_asset_bundle`, but keep this compatibility boundary:

```python
def fetch_macro_assets(*args, **kwargs) -> tuple[pd.DataFrame, pd.DataFrame]:
    bundle = fetch_macro_asset_bundle(*args, **kwargs)
    return bundle.detail, bundle.source_log
```

The bundle must include bounded official price history; the legacy two-frame API remains for existing callers/tests. Apply `as_of_date` and `known_as_of` before snapshots, correlations, or research facts.

- [ ] **Step 3: Resolve the macro CLI as the table union**

Keep the commodity branch's `MacroAssetBundle` handling and write `commodity_price_history.csv`. Also retain the public logic that:

```python
publishable = detail excluding optional FETCH_FAILED rows
publishable = publishable excluding asset_class == "calculation_input"
ranked = add_macro_ranks(publishable)
divergence excludes asset_class == "cross_asset"
```

Write all eight public tables (`fixed_income`, `commodities`, `foreign_exchange`, `policy_rates`, `money_market`, `liquidity`, `cross_asset`, `macro_divergence`), the commodity price-history table, and `source_log` into the same staged directory.

- [ ] **Step 4: Resolve macro tests and compile**

Retain both provider dispatch families, all public calculated-series/correlation/as-of tests, and all EIA/World Bank/history tests. Update the exact configured macro count from branch-specific 70/58 to 81. Do not change ChinaBond expectations in this task.

Run:

```bash
python3 -m py_compile pipeline/internal/capital_weekly/macro_assets.py pipeline/internal/scripts/fetch_macro_assets.py
```

Expected: exit 0.

### Task 7: Resolve Weekly Context and Release Contract 6

**Files:**
- Modify: `pipeline/internal/capital_weekly/weekly_context.py`
- Modify: `pipeline/internal/capital_weekly/weekly_release.py`
- Modify: `pipeline/internal/tests/test_capital_weekly_weekly_release.py`
- Preserve automatic merge: `pipeline/internal/tests/test_capital_weekly_weekly_context.py`
- Preserve automatic merge: `pipeline/internal/tests/test_latest_json_output.py`
- Preserve automatic merge: `pipeline/internal/tests/test_offline_output_migration.py`

**Interfaces:**
- Consumes: union provider results, public context tables, commodity price/metric histories and facts.
- Produces: exact context-category union, contracts 1–6, five business JSON files, and atomic output/cache replacement.

- [ ] **Step 1: Resolve weekly-context categories and diagnostics**

Set `CATEGORY_FILES`/`CATEGORY_FIELDS` to the exact union:

```python
(
    "events", "economic_releases", "market_internals", "positioning_flows",
    "fund_flows", "company_fundamentals", "capital_markets", "company_events",
    "commodity_fundamentals", "commodity_metric_history",
    "commodity_research_facts", "financial_conditions", "source_log",
)
```

Keep public normalizers and input-reference validation for economic releases, fundamentals, and capital markets. Keep commodity `audit_secrets`, raw sanitization, `phase`, `attempts`, `error_code`, history bounding, and fact building. Optional categories remain present as empty lists.

- [ ] **Step 2: Define contract 6 without renumbering contracts 1–5**

Use these exact constants and routing:

```python
LEGACY_DATASET_CONTRACT_VERSION = 1
POINT_IN_TIME_DATASET_CONTRACT_VERSION = 2
WAVE_1_DATASET_CONTRACT_VERSION = 3
WAVE_2_DATASET_CONTRACT_VERSION = 4
PUBLIC_GREEN_DATASET_CONTRACT_VERSION = 5
DATASET_CONTRACT_VERSION = 6
SUPPORTED_DATASET_CONTRACT_VERSIONS = frozenset(range(1, 7))
```

`VERSION_5_RELEASE_DATASETS` is the public-green contract-five dataset tuple with no commodity-history/fact tables. `RELEASE_DATASETS` is contract 6 and adds exactly:

```python
V6_ADDITIVE_DATASETS = frozenset({
    ("macro_assets", "commodity_price_history.csv"),
    ("weekly_context", "commodity_metric_history.csv"),
    ("weekly_context", "commodity_research_facts.csv"),
})
```

`release_datasets_for_contract(1..5)` retains existing public behavior; version 6 returns `RELEASE_DATASETS`; every other integer raises `ReleaseValidationError`.

- [ ] **Step 3: Resolve output tables and validation**

Keep exactly five names in `OUTPUT_BUSINESS_FILES`. Extend only nested mappings:

```python
OUTPUT_TABLES["macro"] includes "commodity_price_history"
OUTPUT_TABLES["context"] includes "commodity_metric_history" and "commodity_research_facts"
```

Retain public capability-manifest, fixed-provider, company-reference, and calculated-source validation. Port commodity configured coverage, provider-status, cross-table record-ID, formula, taxonomy, and history validation. Keep manifest schema 3, output schema `1.0`, regular-file containment, SHA-256 validation, write-last `release.json`, and atomic output/cache pair replacement.

- [ ] **Step 4: Resolve release tests and finish all conflicts**

Keep public contract 1–5 fixtures/tests and commodity validation fixtures. Rename commodity branch assertions that called its local version `3` to contract `6`; do not change the public meanings of versions 3–5. Add assertions that contract 5 rejects/omits the three additive commodity tables and contract 6 requires them.

Run:

```bash
git diff --name-only --diff-filter=U
git diff --check
python3 -m py_compile pipeline/internal/capital_weekly/weekly_context.py pipeline/internal/capital_weekly/weekly_release.py
```

Expected: no unmerged paths, no whitespace errors, compilation succeeds.

- [ ] **Step 5: Run contract RED-to-GREEN and focused integration tests**

Run:

```bash
python3 -m unittest -v pipeline.internal.tests.test_active_branch_consolidation
python3 -m unittest -v \
  pipeline.internal.tests.test_pipeline_config \
  pipeline.internal.tests.test_capital_weekly_context_providers \
  pipeline.internal.tests.test_capital_weekly_macro_assets \
  pipeline.internal.tests.test_capital_weekly_commodity_prices \
  pipeline.internal.tests.test_capital_weekly_commodity_research \
  pipeline.internal.tests.test_capital_weekly_weekly_context \
  pipeline.internal.tests.test_capital_weekly_weekly_release \
  pipeline.internal.tests.test_latest_json_output \
  pipeline.internal.tests.test_offline_output_migration
```

Expected: the two acceptance tests that were RED in Task 4 are GREEN; all focused modules pass.

- [ ] **Step 6: Commit the semantic merge**

Run:

```bash
git add -u -- README.md pipeline/config.json pipeline/internal
git add -- pipeline/internal/tests/test_active_branch_consolidation.py
if git diff --cached --name-only | rg -q '^pipeline/internal/docs/2026-08-30-current-data-12-category-audit\.md$'; then exit 1; fi
git status --short
git commit -m "merge: consolidate public green and commodity backends"
git merge-base --is-ancestor codex/public-green-integration main
git merge-base --is-ancestor codex/commodity-research-backend main
```

Expected: the commit has two parents; both active branch tips are ancestors of main; the unrelated audit file remains untracked.

### Task 8: Repair ChinaBond with TDD on the Unified Tree

**Files:**
- Modify: `pipeline/internal/tests/test_capital_weekly_macro_assets.py`
- Modify: `pipeline/internal/capital_weekly/macro_assets.py`
- Modify: `pipeline/config.json`

**Interfaces:**
- Consumes: ChinaBond official `{flag, heList}` JSON response and the existing exact 2Y/5Y/10Y/30Y field mapping.
- Produces: `_parse_chinabond_json(text: str, field: str) -> list[dict]` and current official POST requests to `/cbweb-czb-web/czb/historyQuery`.

- [ ] **Step 1: Write failing parser and request-contract tests**

Add `_parse_chinabond_json` to the test imports and add tests equivalent to:

```python
def test_chinabond_accepts_only_successful_official_envelope(self):
    payload = json.dumps({
        "flag": "0",
        "heList": [{
            "workTime": "2026-08-28",
            "twoYear": "1.24",
            "fiveYear": "1.39",
            "tenYear": "1.68",
            "thirtyYear": "2.13",
        }],
    })
    self.assertEqual(
        _parse_chinabond_json(payload, "tenYear"),
        [{"date": date(2026, 8, 28), "value": 1.68}],
    )
    for invalid in (
        {"flag": "1", "heList": []},
        {"flag": "0"},
        {"flag": "0", "heList": {}},
    ):
        with self.subTest(invalid=invalid):
            with self.assertRaises(ValueError):
                _parse_chinabond_json(json.dumps(invalid), "tenYear")


def test_chinabond_posts_current_history_endpoint_and_parameters(self):
    response = unittest.mock.Mock(
        content=b'{"flag":"0","heList":[]}',
        text='{"flag":"0","heList":[]}',
    )
    response.raise_for_status.return_value = None
    session = unittest.mock.Mock(
        _macro_attempt_trace=[], _macro_raw_parts=[], post=unittest.mock.Mock(return_value=response)
    )
    _fetch_config_history(self._config("china_bond", "10Y"), session, as_of_date=date(2026, 8, 30))
    url = session.post.call_args.args[0]
    self.assertIn("/cbweb-czb-web/czb/historyQuery?", url)
    self.assertIn("gjqx=2,5,10,30", url)
    self.assertIn("locale=en_US", url)
    self.assertIn("qxmc=1", url)
```

- [ ] **Step 2: Run the ChinaBond tests and confirm RED**

Run:

```bash
python3 -m unittest -v \
  pipeline.internal.tests.test_capital_weekly_macro_assets.MacroAssetUniverseTests.test_chinabond_accepts_only_successful_official_envelope \
  pipeline.internal.tests.test_capital_weekly_macro_assets.MacroAssetUniverseTests.test_chinabond_posts_current_history_endpoint_and_parameters
```

Expected: parser test fails because the current parser expects an array; request test fails because the old `/cbweb-mn/pgxh/historyQuery` URL lacks `qxmc=1`.

- [ ] **Step 3: Implement the minimal official-envelope parser and URL**

Use this parser contract:

```python
def _parse_chinabond_json(text: str, field: str) -> list[dict]:
    raw = json.loads(text)
    if not isinstance(raw, dict) or str(raw.get("flag")) != "0":
        raise ValueError("ChinaBond response did not report success")
    rows = raw.get("heList")
    if not isinstance(rows, list):
        raise ValueError("ChinaBond response heList was not a JSON array")
    return _normalize_frame(pd.DataFrame(rows), "workTime", field)
```

Build the POST URL with single `&` separators:

```python
url = (
    "https://yield.chinabond.com.cn/cbweb-czb-web/czb/historyQuery?"
    f"startDate={start.isoformat()}&endDate={end.isoformat()}&"
    "gjqx=2,5,10,30&locale=en_US&qxmc=1"
)
```

Update the four CGB `source_url` values in `pipeline/config.json` to `https://yield.chinabond.com.cn/cbweb-czb-web/czb/historyQuery`. Preserve annual request chunks and exact maturity mapping.

- [ ] **Step 4: Run focused GREEN tests and commit**

Run:

```bash
python3 -m unittest -v pipeline.internal.tests.test_capital_weekly_macro_assets pipeline.internal.tests.test_pipeline_config
git diff --check
git add pipeline/config.json pipeline/internal/capital_weekly/macro_assets.py pipeline/internal/tests/test_capital_weekly_macro_assets.py
git commit -m "fix: update ChinaBond history endpoint"
```

Expected: focused modules pass and the commit contains only the endpoint/parser/config/test repair.

### Task 9: Verify Unified Main and the Preserved Stable Output

**Files:**
- Verify: all tracked files.
- Validate without modifying: `output/`.
- Verify unchanged: archived and working audit file.

**Interfaces:**
- Consumes: merged main plus ChinaBond fix.
- Produces: final deterministic test evidence and pre-refresh output validation.

- [ ] **Step 1: Run the complete Python and workbook suites**

Run:

```bash
python3 -m unittest -v
node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs
```

Expected: both suites exit 0.

- [ ] **Step 2: Validate the active output before any live refresh**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
from pipeline.internal.capital_weekly.weekly_release import validate_output_bundle

release = validate_output_bundle(Path("output"))
print(json.dumps(release, ensure_ascii=False, indent=2, sort_keys=True))
PY
```

Expected: the pre-refresh six-file stable bundle validates under its original contract and retains its baseline release identity.

- [ ] **Step 3: Recheck repository boundaries and unrelated-file hash**

Run:

```bash
find . -maxdepth 1 -mindepth 1 -not -name '.git' -not -name '.worktrees' -print | sort
shasum -a 256 pipeline/internal/docs/2026-08-30-current-data-12-category-audit.md .git/codex-archives/2026-08-30-active-branch-consolidation/2026-08-30-current-data-12-category-audit.md
git status --short
```

Expected: visible product directories are `pipeline/` and `output/`; audit hashes match; only the audit file is untracked.

### Task 10: Run the Authorized Live Refresh and Validate Publication

**Files:**
- Replace only on complete success: `output/*.json`
- Replace only on complete success: latest generation under `pipeline/.cache/`

**Interfaces:**
- Consumes: current public sources, optional `BEA_API_KEY`/`USDA_API_KEY`/`SEC_USER_AGENT`, and required `EIA_API_KEY` for official commodity prices.
- Produces: contract-6 stable output for `week_20260824-20260830`, or a factual failure status while preserving the old stable output/cache.

- [ ] **Step 1: Report credential availability without revealing secrets**

Run:

```bash
python3 - <<'PY'
import os
for name in ("EIA_API_KEY", "USDA_API_KEY", "BEA_API_KEY", "SEC_USER_AGENT"):
    print(f"{name}: {'configured' if os.environ.get(name, '').strip() else 'not configured'}")
PY
```

Expected: values are never printed. `EIA_API_KEY` must be configured for the official commodity macro rows; USDA/BEA/SEC follow their explicit optional/conditional policies.

- [ ] **Step 2: Run the single coordinated refresh**

Run:

```bash
python3 -m pipeline.refresh --as-of-date 2026-08-30
```

Expected on success: all five pipelines and cross-file validation pass, then `output/` and the latest cache are replaced atomically. Expected on provider failure: nonzero exit, factual failure status, and byte-identical old `output/` plus previous successful cache remain visible.

- [ ] **Step 3: Validate and summarize the new bundle**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
from pipeline.internal.capital_weekly.weekly_release import validate_output_bundle

root = Path("output")
release = validate_output_bundle(root)
summary = {
    "release_id": release["release_id"],
    "as_of_date": release["as_of_date"],
    "source_week": release.get("source_week"),
    "status": release["status"],
    "pipelines": release["pipelines"],
    "files": sorted(path.name for path in root.iterdir() if path.is_file()),
}
for name in ("indices", "sectors", "gics", "macro", "context"):
    document = json.loads((root / f"{name}.json").read_text(encoding="utf-8"))
    summary[f"{name}_tables"] = {
        table: len(rows) for table, rows in document["tables"].items()
    }
print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
PY
shasum -a 256 output/*.json
```

Expected: exactly six stable files, one release identity/date, five complete pipelines, contract-6 nested commodity tables, and no dated output directory.

### Task 11: Clean Up Only the Merged Active Worktrees and Branches

**Files:**
- Remove after verification: `.worktrees/public-green-integration/`
- Remove after verification: `.worktrees/commodity-research-backend/`
- Delete after ancestry checks: `codex/public-green-integration`
- Delete after ancestry checks: `codex/commodity-research-backend`

**Interfaces:**
- Consumes: clean merged source worktrees, green unified main, validated active output, recoverable audit archive.
- Produces: main as the sole active implementation line; historical unrelated branches remain untouched.

- [ ] **Step 1: Verify cleanup targets are clean and merged**

Run:

```bash
git -C .worktrees/public-green-integration status --short
git -C .worktrees/commodity-research-backend status --short
git merge-base --is-ancestor codex/public-green-integration main
git merge-base --is-ancestor codex/commodity-research-backend main
```

Expected: both statuses are empty and all ancestry checks exit 0.

- [ ] **Step 2: Remove the two worktrees without force**

Run:

```bash
git worktree remove "/Users/a1-6/Documents/market data/.worktrees/public-green-integration"
git worktree remove "/Users/a1-6/Documents/market data/.worktrees/commodity-research-backend"
git worktree prune
```

Expected: both removals succeed without `--force`.

- [ ] **Step 3: Delete only the two merged branch refs**

Run:

```bash
git branch -d codex/public-green-integration codex/commodity-research-backend
git branch --list
git worktree list
```

Expected: non-forced deletion succeeds; all historical/unrelated branches remain; only the main worktree is active for this implementation.

- [ ] **Step 4: Produce the final handoff record**

Report:

```text
starting and final main SHAs
public-green synchronization/merge SHA
commodity repair SHA 9e7670b and semantic merge SHA
ChinaBond fix SHA
all created/modified/removed files
original two RED commodity failures and 50-test focused GREEN
contract-6 RED/GREEN evidence
ChinaBond RED/GREEN evidence
both source-branch full suites and final full Python/Node results
pre-refresh and final output release identities/hashes
source week and as_of_date
live source failures or conditional NOT_CONFIGURED providers
archive path and matching audit SHA-256
removed worktrees/branches
remaining 677-universe, company-watchlist, credential, and compatibility risks
```

Do not claim completion if final tests, output validation, live publication, audit hash, ancestry checks, or non-forced cleanup fail.
