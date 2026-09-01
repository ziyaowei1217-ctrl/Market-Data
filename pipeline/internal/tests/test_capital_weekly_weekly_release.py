from __future__ import annotations

import csv
import ast
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
import fcntl
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from pipeline.internal.capital_weekly import weekly_release as weekly_release_module
from pipeline.internal.capital_weekly.commodity_research import (
    METRIC_HISTORY_FIELDS,
    PRICE_HISTORY_FIELDS,
    RESEARCH_FACT_FIELDS,
    build_research_facts,
    load_formula_specs,
)
from pipeline.internal.capital_weekly.weekly_context import CATEGORY_FIELDS
from pipeline.internal.capital_weekly.context.provider_contracts import (
    FIXED_REQUIRED_CONTEXT_IDENTITIES,
)
from pipeline.internal.capital_weekly.weekly_release import (
    ReleaseAlreadyRunning,
    ReleasePipelineError,
    ReleaseValidationError,
    build_output_bundle,
    build_pipeline_specs,
    latest_finished_week,
    release_datasets_for_contract,
    run_latest_release,
    validate_staged_week,
)


RETURN_DATE_FIELDS = [
    "latest_date",
    "daily_base_date",
    "weekly_base_date",
    "mtd_base_date",
    "ytd_base_date",
]
RETURN_NUMERIC_FIELDS = [
    "latest_value",
    "daily_base_value",
    "daily_change",
    "weekly_base_value",
    "weekly_change",
    "mtd_base_value",
    "mtd_change",
    "ytd_base_value",
    "ytd_change",
]
RANK_FIELDS = ["daily_rank", "weekly_rank", "mtd_rank", "ytd_rank"]
INDEX_FIELDS = [
    "region", "index_name_cn", "index_name_en", "ticker", "currency",
    "provider", "provider_symbol", "source", "notes", *RETURN_DATE_FIELDS,
    *RETURN_NUMERIC_FIELDS, "change_unit", "qc_flag", "source_url",
]
SECTOR_FIELDS = [
    "market", "taxonomy", "taxonomy_version", "taxonomy_level", "sector_code",
    "sector_name_cn", "sector_name_en", "ticker", "currency", "provider",
    "provider_symbol", "source", "instrument_type", "sort_order", "notes",
    *RETURN_DATE_FIELDS, *RETURN_NUMERIC_FIELDS, "change_unit", "qc_flag",
    "source_url", *RANK_FIELDS,
]
GICS_FIELDS = [
    "gics_sector_code", "sector_name_cn", "sector_name_en", "ticker",
    "currency", "provider", "provider_symbol", "source", "proxy_type", "notes",
    *RETURN_DATE_FIELDS, *RETURN_NUMERIC_FIELDS, "change_unit", "qc_flag",
    "source_url",
]
COMMODITY_MACRO_FIELDS = [
    "commodity_code",
    "commodity_family",
    "price_kind",
    "known_as_of",
    "provider_route",
]
MACRO_FIELDS = [
    "asset_class", "group", "series_code", "name_cn", "name_en", "provider",
    "provider_symbol", "source", "source_url", "frequency", "level_unit",
    "change_unit", "sort_order", "notes", *RETURN_DATE_FIELDS,
    *RETURN_NUMERIC_FIELDS, "qc_flag", *RANK_FIELDS, *COMMODITY_MACRO_FIELDS,
]
MACRO_V3_FIELDS = [
    *MACRO_FIELDS,
    "calculation_id",
    "formula_version",
    "input_series_codes",
    "window_observations",
    "minimum_observations",
    "correlation_observations",
]
SECTOR_DIVERGENCE_FIELDS = [
    "market", "market_cn", "horizon", "horizon_cn", "valid_count",
    "positive_count", "flat_count", "negative_count", "breadth_ratio",
    "leader_laggard_spread", "dispersion", "median_return", "top_3",
    "bottom_3", "commentary_cn", "qc_flag",
]
MACRO_DIVERGENCE_FIELDS = [
    "asset_class", "group", "group_cn", "horizon", "horizon_cn", "change_unit",
    "valid_count", "up_count", "flat_count", "down_count", "median_change",
    "change_range", "dispersion", "top_movers", "bottom_movers",
    "commentary_cn", "qc_flag",
]
INDEX_SOURCE_LOG_FIELDS = [
    "ticker", "source", "status", "observations", *RETURN_DATE_FIELDS,
    "latest_value", "daily_base_value", "weekly_base_value", "mtd_base_value",
    "ytd_base_value", "elapsed_ms", "source_url", "notes",
]
SECTOR_SOURCE_LOG_FIELDS = [
    "market", "taxonomy", "sector_code", "sector_name_en", "ticker",
    "sort_order", "source", "status", "observations", *RETURN_DATE_FIELDS,
    "latest_value", "daily_base_value", "weekly_base_value", "mtd_base_value",
    "ytd_base_value", "elapsed_ms", "source_url", "notes", "raw_cache_status",
    "raw_cache_error",
]
GICS_SOURCE_LOG_FIELDS = [
    "ticker", "gics_sector_code", "sector_name_en", "source", "status",
    "observations", *RETURN_DATE_FIELDS, "latest_value", "daily_base_value",
    "weekly_base_value", "mtd_base_value", "ytd_base_value", "elapsed_ms",
    "source_url", "notes",
]
MACRO_SOURCE_LOG_FIELDS = [
    "series_code", "sort_order", "source", "status", "error", "observations",
    "latest_date", "latest_value", "source_url", "elapsed_ms",
    "raw_cache_status", "raw_cache_error",
]
MACRO_SOURCE_LOG_V3_FIELDS = [
    *MACRO_SOURCE_LOG_FIELDS,
    "provider",
    "provider_symbol",
    "source_tier",
    "requiredness",
    "provider_version",
    "schema_version",
    "frequency",
    "freshness_days",
    "known_as_of",
    "warnings",
    "calculation_id",
    "formula_version",
    "input_series_codes",
]
LEGACY_CONTEXT_SOURCE_LOG_FIELDS = [
    "provider",
    "category",
    "status",
    "observations",
    "as_of_date",
    "source",
    "source_url",
    "elapsed_ms",
    "notes",
]
STAGED_CONTEXT_SOURCE_LOG_FIELDS = [
    "provider",
    "source_tier",
    "requiredness",
    "provider_version",
    "schema_version",
    "frequency",
    "freshness_days",
    "latest_known_as_of",
    "warnings",
    "category",
    "status",
    "observations",
    "as_of_date",
    "source",
    "source_url",
    "elapsed_ms",
    "notes",
    "phase",
    "attempts",
    "error_code",
]
PUBLIC_CONTEXT_SOURCE_LOG_FIELDS = STAGED_CONTEXT_SOURCE_LOG_FIELDS[:-3]
PUBLIC_MACRO_FIELDS = [
    field for field in MACRO_FIELDS if field not in COMMODITY_MACRO_FIELDS
]
PUBLIC_MACRO_V3_FIELDS = [
    *PUBLIC_MACRO_FIELDS,
    "calculation_id",
    "formula_version",
    "input_series_codes",
    "known_as_of",
    "window_observations",
    "minimum_observations",
    "correlation_observations",
]
PUBLIC_METRIC_FIELDS = [
    "as_of_date",
    "category",
    "metric_code",
    "metric_name",
    "value",
    "unit",
    "frequency",
    "market",
    "source",
    "source_url",
    "qc_flag",
]
PUBLIC_COMPANY_EVENT_FIELDS = [
    *PUBLIC_METRIC_FIELDS,
    "event_date",
    "ticker",
    "cik",
    "form",
    "event_type",
    "accession_number",
    "report_date",
    "accepted_at",
    "items",
    "evidence_status",
]
PUBLIC_CONTRACT_SPEC_FINGERPRINTS = {
    1: "18050dccb95c3988eee0bb104c34bd9d43aa4ba745d9e93f0a1e3526a9f72876",
    2: "b6617b7094d00bd89ba3355e95d5c1fb60f0564508d72a4b95328d89c7e8b868",
    3: "20f07dfd8e3eca157d30691bd69173ceb65e56dfe92ae0eb5d9a70bed276747c",
    4: "4309e4c0e4ae67df639ece6d4b59f63e9a43ccba0cfd0441dba2302cad2e04f3",
    5: "b56c2fbe9154d23b6edf6b091bb192b783e1ceb98cd423cc2d69b81c07cce746",
}

NUMERIC_FIELDS = set(RETURN_NUMERIC_FIELDS + RANK_FIELDS) | {
    "sort_order", "observations", "elapsed_ms", "valid_count", "positive_count",
    "flat_count", "negative_count", "up_count", "down_count", "breadth_ratio",
    "leader_laggard_spread", "dispersion", "median_return", "median_change",
    "change_range", "value",
    "window_observations", "minimum_observations", "correlation_observations",
    "freshness_days",
}
DATE_FIELDS = set(RETURN_DATE_FIELDS) | {
    "as_of_date", "event_date", "report_date",
}

PRODUCTION_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"
V2_COMMODITY_UNIVERSE = {
    "NATGAS_HH": "natural_gas",
    "WTI": "refined_products",
    "BRENT": "refined_products",
    "RBOB_US": "refined_products",
    "ULSD_US": "refined_products",
    "JET_US": "refined_products",
    "PROPANE_US": "refined_products",
    "COPPER_COMEX": "copper",
    "GOLD_COMEX": "gold",
    "CORN": "grains_oilseeds",
    "SOYBEANS": "grains_oilseeds",
    "WHEAT": "grains_oilseeds",
    "RICE": "grains_oilseeds",
    "COTTON": "softs",
    "SUGAR": "softs",
    "COFFEE": "softs",
    "COCOA": "softs",
    "CATTLE": "livestock",
    "HOGS": "livestock",
}
V2_CFTC_PARTICIPANTS = (
    "producer",
    "swap_dealer",
    "managed_money",
    "other_reportable",
)


def write_csv(
    path: Path,
    fields: list[str] | tuple[str, ...],
    rows: list[dict],
    *,
    complete_context_log: bool = True,
) -> None:
    output_rows = list(rows)
    if complete_context_log and tuple(fields) == CATEGORY_FIELDS["source_log"]:
        present = {
            (str(row.get("provider") or ""), str(row.get("category") or ""))
            for row in output_rows
        }
        output_rows.extend(
            fixture_row(
                CATEGORY_FIELDS["source_log"],
                provider=provider,
                category=category,
                status="OK",
                requiredness="required",
                observations="0",
                as_of_date="2026-08-09",
            )
            for provider, category in FIXED_REQUIRED_CONTEXT_IDENTITIES
            if (provider, category) not in present
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def fixture_row(fields, **overrides) -> dict:
    row = {}
    for field in fields:
        if field in DATE_FIELDS:
            row[field] = "2026-08-07"
        elif field == "requiredness":
            row[field] = "required"
        elif field == "source_tier":
            row[field] = "official"
        elif field in {
            "freshness_days",
            "known_as_of",
            "latest_known_as_of",
            "error_code",
        }:
            row[field] = ""
        elif field == "phase":
            row[field] = "normalized"
        elif field == "attempts":
            row[field] = "1"
        elif field in NUMERIC_FIELDS:
            row[field] = "1"
        elif field == "source_url":
            row[field] = "https://example.test/source"
        elif field in {"qc_flag", "status"}:
            row[field] = "OK"
        else:
            row[field] = "fixture"
    row.update(overrides)
    return row


USDA_PSD_FAMILIES = {
    "CORN": "grains_oilseeds",
    "SOYBEANS": "grains_oilseeds",
    "WHEAT": "grains_oilseeds",
    "RICE": "grains_oilseeds",
    "COTTON": "softs",
    "SUGAR": "softs",
    "COFFEE": "softs",
    "COCOA": "softs",
    "CATTLE": "livestock",
    "HOGS": "livestock",
}
USDA_ESR_FAMILIES = {
    code: USDA_PSD_FAMILIES[code]
    for code in ("CORN", "SOYBEANS", "WHEAT", "RICE", "COTTON")
}


def usda_source_rows(*, status: str, requiredness: str) -> list[dict]:
    return [
        fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider=provider,
            category="commodity_fundamentals",
            requiredness=requiredness,
            status=status,
            observations="0" if status == "NOT_CONFIGURED" else "1",
            as_of_date="2026-08-09",
            source="USDA Foreign Agricultural Service",
            source_url="https://api.fas.usda.gov/",
        )
        for provider in ("usda_psd", "usda_esr")
    ]


def usda_fundamental_rows(
    psd_families: dict[str, str],
    esr_families: dict[str, str],
) -> list[dict]:
    rows = []
    for provider, families in (
        ("usda_psd", psd_families),
        ("usda_esr", esr_families),
    ):
        for commodity_code, family in families.items():
            rows.append(fixture_row(
                CATEGORY_FIELDS["commodity_fundamentals"],
                as_of_date="2026-08-07",
                metric_code=f"{provider}_{commodity_code.lower()}_fixture",
                commodity_code=commodity_code,
                commodity_family=family,
                metric_role="physical_fundamental",
                measurement_kind="supply" if provider == "usda_psd" else "trade",
                participant_class="",
                known_as_of="2026-08-07T12:00:00-04:00",
                reference_period="2026",
                source="USDA Foreign Agricultural Service",
                source_url=f"https://api.fas.usda.gov/api/{provider[5:]}/fixture",
            ))
    return rows


def economic_release_row(**overrides) -> dict:
    row = fixture_row(
        CATEGORY_FIELDS["economic_releases"],
        release_at_bjt="2026-08-07T20:30:00+08:00",
        as_of_date="2026-08-09",
        known_as_of="2026-08-07T08:30:00-04:00",
        value="1",
        previous_value="",
        revised_previous="",
        consensus_value="",
        surprise_value="",
    )
    row.update(overrides)
    return row


def write_valid_pipeline_output(pipeline: str, output: Path) -> None:
    history_files = {
        "equity_indices": (
            "02_equity_indices.csv", INDEX_FIELDS,
            fixture_row(INDEX_FIELDS, ticker="INDEX"),
            INDEX_SOURCE_LOG_FIELDS,
            fixture_row(INDEX_SOURCE_LOG_FIELDS, ticker="INDEX"),
        ),
        "equity_sectors": (
            "03_equity_sectors.csv", SECTOR_FIELDS,
            fixture_row(SECTOR_FIELDS, sector_code="SECTOR"),
            SECTOR_SOURCE_LOG_FIELDS,
            fixture_row(SECTOR_SOURCE_LOG_FIELDS, sector_code="SECTOR"),
        ),
        "gics_sectors": (
            "03_gics_sectors.csv", GICS_FIELDS,
            fixture_row(GICS_FIELDS, gics_sector_code="GICS"),
            GICS_SOURCE_LOG_FIELDS,
            fixture_row(GICS_SOURCE_LOG_FIELDS, gics_sector_code="GICS"),
        ),
    }
    if pipeline in history_files:
        filename, fields, row, log_fields, log_row = history_files[pipeline]
        write_csv(output / filename, fields, [row])
        write_csv(output / "source_log.csv", log_fields, [log_row])
        snapshot_name = {
            "equity_indices": "equity_indices_snapshot.json",
            "equity_sectors": "equity_sectors_snapshot.json",
            "gics_sectors": "gics_sectors_snapshot.json",
        }[pipeline]
        (output / snapshot_name).write_text("{}", encoding="utf-8")

    if pipeline == "equity_sectors":
        write_csv(
            output / "sector_divergence.csv",
            SECTOR_DIVERGENCE_FIELDS,
            [fixture_row(SECTOR_DIVERGENCE_FIELDS, market="US", horizon="weekly")],
        )

    if pipeline == "macro_assets":
        for filename in (
            "fixed_income.csv",
            "commodities.csv",
            "foreign_exchange.csv",
            "policy_rates.csv",
            "money_market.csv",
        ):
            write_csv(
                output / filename,
                MACRO_V3_FIELDS,
                [fixture_row(MACRO_V3_FIELDS, series_code=filename)],
            )
        write_csv(
            output / "liquidity.csv",
            MACRO_V3_FIELDS,
            [fixture_row(MACRO_V3_FIELDS, series_code="FED_TOTAL_ASSETS")],
        )
        write_csv(output / "cross_asset.csv", MACRO_V3_FIELDS, [])
        write_csv(
            output / "macro_divergence.csv",
            MACRO_DIVERGENCE_FIELDS,
            [fixture_row(MACRO_DIVERGENCE_FIELDS, asset_class="fixed_income")],
        )
        write_csv(
            output / "source_log.csv",
            MACRO_SOURCE_LOG_V3_FIELDS,
            [fixture_row(MACRO_SOURCE_LOG_V3_FIELDS, series_code="MACRO")],
        )
        (output / "macro_assets_snapshot.json").write_text("{}", encoding="utf-8")

    if pipeline == "weekly_context":
        for category, fields in CATEGORY_FIELDS.items():
            rows = []
            if category == "source_log":
                rows = [
                    {
                        "provider": "fixture",
                        "source_tier": "public",
                        "requiredness": "required",
                        "provider_version": "fixture-v1",
                        "schema_version": "fixture-v1",
                        "frequency": "daily",
                        "freshness_days": "",
                        "latest_known_as_of": "",
                        "warnings": "",
                        "category": "market_internals",
                        "status": "OK",
                        "observations": "0",
                        "as_of_date": "2026-08-09",
                        "source": "Fixture",
                        "source_url": "https://example.test/context",
                        "elapsed_ms": "1",
                        "notes": "",
                        "phase": "normalized",
                        "attempts": "1",
                        "error_code": "",
                    },
                    *usda_source_rows(
                        status="NOT_CONFIGURED",
                        requiredness="optional",
                    ),
                ]
            write_csv(output / f"{category}.csv", fields, rows)
        (output / "weekly_context_snapshot.json").write_text("{}", encoding="utf-8")


def write_valid_staged_week(root: Path, window) -> dict[str, Path]:
    directories = {
        spec.name: Path(spec.output_dir)
        for spec in build_pipeline_specs(root, window)
    }
    for pipeline, output in directories.items():
        write_valid_pipeline_output(pipeline, output)
    return directories


def write_legacy_contract_fixture(
    outputs: dict[str, Path],
    dataset_contract_version: int,
) -> None:
    if dataset_contract_version not in range(1, 6):
        raise ValueError("legacy fixture contract must be in 1..5")

    macro_fields = (
        PUBLIC_MACRO_FIELDS
        if dataset_contract_version <= 2
        else PUBLIC_MACRO_V3_FIELDS
    )

    def select_fields(
        rows: list[dict[str, str]],
        fields: list[str],
    ) -> list[dict[str, str]]:
        return [
            {field: row.get(field, "") for field in fields}
            for row in rows
        ]

    for filename in (
        "fixed_income.csv",
        "commodities.csv",
        "foreign_exchange.csv",
        "policy_rates.csv",
        "money_market.csv",
    ):
        rows = read_csv_rows(outputs["macro_assets"] / filename)
        for row in rows:
            row["known_as_of"] = ""
        write_csv(
            outputs["macro_assets"] / filename,
            macro_fields,
            select_fields(rows, macro_fields),
        )
    if dataset_contract_version >= 3:
        for filename in ("liquidity.csv", "cross_asset.csv"):
            rows = read_csv_rows(outputs["macro_assets"] / filename)
            for row in rows:
                row["known_as_of"] = ""
            write_csv(
                outputs["macro_assets"] / filename,
                PUBLIC_MACRO_V3_FIELDS,
                select_fields(rows, PUBLIC_MACRO_V3_FIELDS),
            )
    macro_source_fields = (
        MACRO_SOURCE_LOG_FIELDS
        if dataset_contract_version <= 2
        else MACRO_SOURCE_LOG_V3_FIELDS
    )
    write_csv(
        outputs["macro_assets"] / "source_log.csv",
        macro_source_fields,
        select_fields(
            read_csv_rows(outputs["macro_assets"] / "source_log.csv"),
            macro_source_fields,
        ),
    )

    for category in (
        "market_internals",
        "positioning_flows",
        "commodity_fundamentals",
        "financial_conditions",
    ):
        path = outputs["weekly_context"] / f"{category}.csv"
        write_csv(
            path,
            PUBLIC_METRIC_FIELDS,
            select_fields(read_csv_rows(path), PUBLIC_METRIC_FIELDS),
        )
    if dataset_contract_version >= 4:
        path = outputs["weekly_context"] / "fund_flows.csv"
        write_csv(
            path,
            PUBLIC_METRIC_FIELDS,
            select_fields(read_csv_rows(path), PUBLIC_METRIC_FIELDS),
        )
    company_events_path = outputs["weekly_context"] / "company_events.csv"
    write_csv(
        company_events_path,
        PUBLIC_COMPANY_EVENT_FIELDS,
        select_fields(
            read_csv_rows(company_events_path),
            PUBLIC_COMPANY_EVENT_FIELDS,
        ),
    )
    context_source_fields = (
        LEGACY_CONTEXT_SOURCE_LOG_FIELDS
        if dataset_contract_version == 1
        else PUBLIC_CONTEXT_SOURCE_LOG_FIELDS
    )
    write_csv(
        outputs["weekly_context"] / "source_log.csv",
        context_source_fields,
        select_fields(
            [
                row
                for row in read_csv_rows(
                    outputs["weekly_context"] / "source_log.csv"
                )
                if row.get("status") == "OK"
            ],
            context_source_fields,
        ),
    )

    macro_csv_files = {
        "fixed_income.csv",
        "commodities.csv",
        "foreign_exchange.csv",
        "policy_rates.csv",
        "money_market.csv",
        "macro_divergence.csv",
        "source_log.csv",
    }
    if dataset_contract_version >= 3:
        macro_csv_files.update({"liquidity.csv", "cross_asset.csv"})
    context_csv_files = {
        "events.csv",
        "market_internals.csv",
        "positioning_flows.csv",
        "company_events.csv",
        "commodity_fundamentals.csv",
        "financial_conditions.csv",
        "source_log.csv",
    }
    if dataset_contract_version >= 2:
        context_csv_files.add("economic_releases.csv")
    if dataset_contract_version >= 4:
        context_csv_files.add("fund_flows.csv")
    if dataset_contract_version >= 5:
        context_csv_files.update(
            {"company_fundamentals.csv", "capital_markets.csv"}
        )
    for output, allowed in (
        (outputs["macro_assets"], macro_csv_files),
        (outputs["weekly_context"], context_csv_files),
    ):
        for path in output.glob("*.csv"):
            if path.name not in allowed:
                path.unlink()


def write_complete_commodity_research_fixture(outputs: dict[str, Path]) -> None:
    identities = (
        ("NATGAS_HH", "natural_gas"),
        ("WTI", "refined_products"),
        ("COPPER_COMEX", "copper"),
        ("GOLD_COMEX", "gold"),
        ("CORN", "grains_oilseeds"),
        ("COTTON", "softs"),
        ("CATTLE", "livestock"),
    )
    price_rows = []
    fundamental_rows = []
    positioning_rows = []
    for index, (commodity_code, family) in enumerate(identities, start=1):
        if family in {"natural_gas", "refined_products"}:
            price_provider = "eia_v2"
            price_source = "U.S. Energy Information Administration Open Data"
            price_url = "https://api.eia.gov/v2/"
            fundamental_source = "U.S. Energy Information Administration"
            fundamental_url = "https://api.eia.gov/v2/"
        elif family in {"copper", "gold"}:
            price_provider = "world_bank_pink_sheet"
            price_source = "World Bank Commodity Price Data (Pink Sheet)"
            price_url = "https://www.worldbank.org/en/research/commodity-markets"
            fundamental_source = "U.S. Geological Survey"
            fundamental_url = "https://pubs.usgs.gov/periodicals/mcs2026/"
        else:
            price_provider = "world_bank_pink_sheet"
            price_source = "World Bank Commodity Price Data (Pink Sheet)"
            price_url = "https://www.worldbank.org/en/research/commodity-markets"
            fundamental_source = "USDA Foreign Agricultural Service"
            fundamental_url = "https://api.fas.usda.gov/"
        price_rows.append(fixture_row(
            MACRO_FIELDS,
            asset_class="commodity",
            group="commodities",
            series_code=f"{commodity_code}_PRICE",
            provider=price_provider,
            source=price_source,
            source_url=price_url,
            commodity_code=commodity_code,
            commodity_family=family,
            price_kind="official_cash",
            known_as_of="",
            latest_value=str(index),
            qc_flag="OK",
        ))
        fundamental_rows.append(fixture_row(
            CATEGORY_FIELDS["commodity_fundamentals"],
            as_of_date="2026-08-07",
            category="commodity_fundamentals",
            metric_code=f"fixture_{commodity_code.lower()}_physical_level",
            value=str(index),
            source=fundamental_source,
            source_url=fundamental_url,
            qc_flag="OK",
            commodity_code=commodity_code,
            commodity_family=family,
            metric_role="physical_fundamental",
            measurement_kind="inventory",
            participant_class="",
            known_as_of="2026-08-07T12:00:00-04:00",
            reference_period="2026-08-07",
        ))
        positioning_rows.append(fixture_row(
            CATEGORY_FIELDS["positioning_flows"],
            as_of_date="2026-08-04",
            category="positioning_flows",
            metric_code=f"fixture_{commodity_code.lower()}_open_interest",
            value=str(index),
            source="U.S. Commodity Futures Trading Commission",
            source_url="https://publicreporting.cftc.gov/resource/72hh-3qpy.csv",
            qc_flag="OK",
            commodity_code=commodity_code,
            commodity_family=family,
            metric_role="positioning",
            measurement_kind="open_interest",
            participant_class="",
            known_as_of="2026-08-07T15:30:00-04:00",
            reference_period="2026-08-04",
        ))
    price_rows.append(fixture_row(
        MACRO_FIELDS,
        asset_class="commodity",
        group="commodities",
        series_code="BTC_USD",
        provider="yahoo_chart",
        source="Yahoo Finance chart API (public vendor proxy)",
        source_url="https://query2.finance.yahoo.com/v8/finance/chart/BTC-USD",
        commodity_code="BTC_USD",
        commodity_family="digital_asset",
        price_kind="vendor_proxy",
        known_as_of="",
        qc_flag="OK",
    ))
    write_exact_gate_fixture(outputs)
    price_rows = [
        *read_csv_rows(outputs["macro_assets"] / "commodities.csv"),
        *price_rows,
    ]
    fundamental_rows = [
        *read_csv_rows(
            outputs["weekly_context"] / "commodity_fundamentals.csv"
        ),
        *fundamental_rows,
    ]
    positioning_rows = [
        *read_csv_rows(outputs["weekly_context"] / "positioning_flows.csv"),
        *positioning_rows,
    ]
    write_csv(outputs["macro_assets"] / "commodities.csv", MACRO_V3_FIELDS, price_rows)
    write_csv(
        outputs["weekly_context"] / "commodity_fundamentals.csv",
        CATEGORY_FIELDS["commodity_fundamentals"],
        fundamental_rows,
    )
    write_csv(
        outputs["weekly_context"] / "positioning_flows.csv",
        CATEGORY_FIELDS["positioning_flows"],
        positioning_rows,
    )


def exact_gate_config() -> dict:
    return {
        "macro": [
            {
                "asset_class": "commodity",
                "series_code": "WTI",
                "provider": "eia_v2",
                "commodity_code": "WTI",
                "commodity_family": "refined_products",
                "price_kind": "official_cash",
            },
            {
                "asset_class": "commodity",
                "series_code": "COMEX_GOLD",
                "provider": "world_bank_pink_sheet",
                "commodity_code": "GOLD_COMEX",
                "commodity_family": "gold",
                "price_kind": "official_monthly_benchmark",
            },
        ],
        "context": {
            "cftc_contracts": [
                {
                    "contract_code": "067651",
                    "metric_code": "WTI_COT",
                    "report_family": "disaggregated",
                    "market_name": "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE",
                    "commodity_code": "WTI",
                    "commodity_family": "refined_products",
                },
                {
                    "contract_code": "088691",
                    "metric_code": "GOLD_COMEX_COT",
                    "report_family": "disaggregated",
                    "market_name": "GOLD - COMMODITY EXCHANGE INC.",
                    "commodity_code": "GOLD_COMEX",
                    "commodity_family": "gold",
                },
            ],
            "eia_series": [
                {
                    "provider": "eia_refined_products",
                    "metric_code": "eia_crude_stocks_ex_spr",
                    "commodity_code": "WTI",
                    "commodity_family": "refined_products",
                },
                {
                    "provider": "eia_refined_products",
                    "metric_code": "eia_gasoline_stocks",
                    "commodity_code": "RBOB_US",
                    "commodity_family": "refined_products",
                },
            ],
            "usda_psd": [
                {"commodity_code": "CORN", "commodity_family": "grains_oilseeds"}
            ],
            "usda_esr": [
                {"commodity_code": "CORN", "commodity_family": "grains_oilseeds"}
            ],
            "metals": [
                {
                    "provider": "comex_gold_stocks",
                    "source": "CME Group",
                    "source_url": "https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls",
                    "commodity_code": "GOLD_COMEX",
                    "commodity_family": "gold",
                    "expected_metric_codes": [
                        "gold_comex_registered_inventory",
                        "gold_comex_eligible_inventory",
                        "gold_comex_total_inventory",
                    ],
                    "expected_observations": "3",
                }
            ],
        },
    }


def write_exact_gate_fixture(outputs: dict[str, Path]) -> None:
    prices = [
        fixture_row(
            MACRO_FIELDS,
            asset_class="commodity",
            series_code="WTI",
            provider="eia_v2",
            source="U.S. Energy Information Administration Open Data",
            source_url="https://www.eia.gov/opendata/",
            commodity_code="WTI",
            commodity_family="refined_products",
            price_kind="official_cash",
            known_as_of="2026-08-08T12:00:00-04:00",
            latest_value="75",
        ),
        fixture_row(
            MACRO_FIELDS,
            asset_class="commodity",
            series_code="COMEX_GOLD",
            provider="world_bank_pink_sheet",
            source="World Bank Commodity Price Data (Pink Sheet)",
            source_url="https://www.worldbank.org/en/research/commodity-markets",
            commodity_code="GOLD_COMEX",
            commodity_family="gold",
            price_kind="official_monthly_benchmark",
            known_as_of="2026-08-08T12:00:00-04:00",
            latest_value="2400",
        ),
    ]
    macro_statuses = [
        fixture_row(MACRO_SOURCE_LOG_V3_FIELDS, series_code=series_code)
        for series_code in ("WTI", "COMEX_GOLD")
    ]
    fundamentals = [
        fixture_row(
            CATEGORY_FIELDS["commodity_fundamentals"],
            as_of_date="2026-08-07",
            metric_code=metric_code,
            commodity_code=commodity_code,
            commodity_family="refined_products",
            metric_role="physical_fundamental",
            measurement_kind="inventory",
            participant_class="",
            known_as_of="2026-08-07T12:00:00-04:00",
            reference_period="2026-08-07",
            source="U.S. Energy Information Administration",
            source_url="https://api.eia.gov/v2/petroleum/sum/sndw/data/",
        )
        for metric_code, commodity_code in (
            ("eia_crude_stocks_ex_spr", "WTI"),
            ("eia_gasoline_stocks", "RBOB_US"),
        )
    ]
    positioning = [
        fixture_row(
            CATEGORY_FIELDS["positioning_flows"],
            as_of_date="2026-08-04",
            metric_code=f"{commodity_code}_open_interest",
            market=market,
            commodity_code=commodity_code,
            commodity_family=family,
            metric_role="positioning",
            measurement_kind="open_interest",
            participant_class="",
            known_as_of="2026-08-07T15:30:00-04:00",
            reference_period="2026-08-04",
            source="U.S. Commodity Futures Trading Commission",
            source_url="https://publicreporting.cftc.gov/resource/72hh-3qpy.csv",
        )
        for commodity_code, family, market in (
            (
                "WTI",
                "refined_products",
                "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE",
            ),
            ("GOLD_COMEX", "gold", "GOLD - COMMODITY EXCHANGE INC."),
        )
    ]
    context_statuses = [
        fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="eia_refined_products",
            category="commodity_fundamentals",
            requiredness="required",
            status="OK",
            observations="2",
            as_of_date="2026-08-09",
            source_url="https://api.eia.gov/v2/",
        ),
        fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="cftc_disaggregated",
            category="positioning_flows",
            requiredness="required",
            status="OK",
            observations="2",
            as_of_date="2026-08-09",
            source_url="https://publicreporting.cftc.gov/",
        ),
        *usda_source_rows(status="NOT_CONFIGURED", requiredness="optional"),
        fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="comex_gold_stocks",
            category="commodity_fundamentals",
            requiredness="optional",
            status="FETCH_FAILED",
            observations="0",
            as_of_date="2026-08-09",
            source="CME Group",
            source_url="https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls",
        ),
    ]
    write_csv(outputs["macro_assets"] / "commodities.csv", MACRO_V3_FIELDS, prices)
    write_csv(
        outputs["macro_assets"] / "source_log.csv",
        MACRO_SOURCE_LOG_V3_FIELDS,
        macro_statuses,
    )
    write_csv(
        outputs["weekly_context"] / "commodity_fundamentals.csv",
        CATEGORY_FIELDS["commodity_fundamentals"],
        fundamentals,
    )
    write_csv(
        outputs["weekly_context"] / "positioning_flows.csv",
        CATEGORY_FIELDS["positioning_flows"],
        positioning,
    )
    write_csv(
        outputs["weekly_context"] / "source_log.csv",
        CATEGORY_FIELDS["source_log"],
        context_statuses,
    )


def merge_context_status_rows(
    outputs: dict[str, Path],
    replacements: list[dict[str, str]],
) -> None:
    path = outputs["weekly_context"] / "source_log.csv"
    replacement_providers = {row["provider"] for row in replacements}
    retained = [
        row
        for row in read_csv_rows(path)
        if row["provider"] not in replacement_providers
    ]
    write_csv(
        path,
        CATEGORY_FIELDS["source_log"],
        [*retained, *replacements],
    )


def configured_gold_metal_rows() -> list[dict[str, str]]:
    return [
        fixture_row(
            CATEGORY_FIELDS["commodity_fundamentals"],
            as_of_date="2026-08-07",
            metric_code=metric_code,
            commodity_code="GOLD_COMEX",
            commodity_family="gold",
            metric_role="physical_fundamental",
            measurement_kind="inventory",
            participant_class="",
            known_as_of="2026-08-07T23:59:59-05:00",
            reference_period="2026-08-07",
            source="CME Group",
            source_url=(
                "https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls"
            ),
        )
        for metric_code in (
            "gold_comex_registered_inventory",
            "gold_comex_eligible_inventory",
            "gold_comex_total_inventory",
        )
    ]


def fixture_stable_record_id(namespace: str, identity: dict) -> str:
    payload = json.dumps(
        {"identity": identity, "namespace": namespace},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _utc_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _price_history_row(config: dict, observation: date, value: float) -> dict:
    known_as_of = _utc_z(
        datetime.combine(
            observation + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
    )
    identity = {
        "code": config["commodity_code"],
        "known_as_of": known_as_of,
        "observation_date": observation.isoformat(),
        "series": config["series_code"],
    }
    return {
        "record_id": fixture_stable_record_id(
            "commodity_price_history", identity
        ),
        "as_of_date": "2026-08-09",
        "commodity_code": config["commodity_code"],
        "commodity_family": config["commodity_family"],
        "series_code": config["series_code"],
        "price_kind": config["price_kind"],
        "observation_date": observation.isoformat(),
        "known_as_of": known_as_of,
        "value": value,
        "unit": config["level_unit"],
        "source": config["source"],
        "source_url": config["source_url"],
        "qc_flag": "OK",
    }


def _metric_history_row(
    base: dict,
    *,
    observation: date | None = None,
    known_as_of: str | None = None,
    value: float | None = None,
) -> dict:
    observation_date = observation or date.fromisoformat(base["as_of_date"])
    canonical_known = known_as_of or base["known_as_of"]
    identity = {
        "code": base["commodity_code"],
        "known_as_of": canonical_known,
        "measurement": base["measurement_kind"],
        "metric": base["metric_code"],
        "observation_date": observation_date.isoformat(),
        "participant": base.get("participant_class") or None,
        "reference_period": base.get("reference_period") or None,
        "role": base["metric_role"],
    }
    return {
        "record_id": fixture_stable_record_id(
            "commodity_metric_history", identity
        ),
        "as_of_date": "2026-08-09",
        "commodity_code": base["commodity_code"],
        "commodity_family": base["commodity_family"],
        "metric_code": base["metric_code"],
        "metric_role": base["metric_role"],
        "measurement_kind": base["measurement_kind"],
        "participant_class": base.get("participant_class") or "",
        "observation_date": observation_date.isoformat(),
        "known_as_of": canonical_known,
        "reference_period": base.get("reference_period") or "",
        "value": value if value is not None else float(base["value"]),
        "unit": base["unit"],
        "source": base["source"],
        "source_url": base["source_url"],
        "qc_flag": "OK",
    }


def _provider_status(
    *,
    provider: str,
    category: str,
    requiredness: str,
    status: str,
    observations: int,
    source: str,
    source_url: str,
    frequency: str,
) -> dict:
    return fixture_row(
        CATEGORY_FIELDS["source_log"],
        provider=provider,
        category=category,
        requiredness=requiredness,
        status=status,
        observations=str(observations),
        as_of_date="2026-08-09",
        source=source,
        source_url=source_url,
        frequency=frequency,
        phase="normalized" if status == "OK" else "coverage",
        error_code="" if status == "OK" else "FIXTURE_UNAVAILABLE",
    )


def write_complete_v2_release_fixture(
    outputs: dict[str, Path],
    *,
    config_path: Path = PRODUCTION_CONFIG_PATH,
    expected_registry: dict[str, str] | None = None,
) -> dict[str, list[dict]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    macro_config = [
        row
        for row in config["macro"]
        if row.get("commodity_code")
        and row.get("commodity_family") != "digital_asset"
    ]
    configured_registry = {
        row["commodity_code"]: row["commodity_family"]
        for row in config["commodity_research"]["universe"]
    }
    required_registry = expected_registry or V2_COMMODITY_UNIVERSE
    if configured_registry != required_registry:
        raise AssertionError("production fixture requires the exact 19-code registry")

    price_snapshots = []
    macro_statuses = []
    price_history = []
    for index, item in enumerate(macro_config, start=1):
        price_snapshots.append(fixture_row(
            MACRO_FIELDS,
            asset_class="commodity",
            group="commodities",
            series_code=item["series_code"],
            provider=item["provider"],
            provider_symbol=item["provider_symbol"],
            source=item["source"],
            source_url=item["source_url"],
            frequency=item["frequency"],
            level_unit=item["level_unit"],
            latest_date="2026-08-07",
            latest_value=str(100 + index),
            commodity_code=item["commodity_code"],
            commodity_family=item["commodity_family"],
            price_kind=item["price_kind"],
            known_as_of="2026-08-08T00:00:00Z",
            provider_route=item.get("provider_route") or "",
        ))
        observations = [date(2026, 8, 7)]
        if item["series_code"] == "WTI":
            observations = [
                date(2025, 8, 7),
                date(2026, 8, 6),
                date(2026, 8, 7),
            ]
        elif item["series_code"] == "COMEX_GOLD":
            observations = []
            for months_before in reversed(range(84)):
                month_index = 2026 * 12 + 7 - months_before
                observations.append(date(
                    month_index // 12,
                    month_index % 12 + 1,
                    7,
                ))
        raw_observations = (
            86 if item["series_code"] == "COMEX_GOLD" else len(observations)
        )
        macro_statuses.append(fixture_row(
            MACRO_SOURCE_LOG_V3_FIELDS,
            series_code=item["series_code"],
            source=item["source"],
            source_url=item["source_url"],
            latest_date="2026-08-07",
            latest_value=str(100 + index),
            observations=str(raw_observations),
        ))
        for offset, observation in enumerate(observations):
            value = 70 + offset if item["series_code"] == "WTI" else 100 + index
            price_history.append(_price_history_row(item, observation, value))
    price_history.sort(key=lambda row: (
        row["commodity_code"],
        row["series_code"],
        row["observation_date"],
        row["known_as_of"],
        row["record_id"],
    ))

    fundamentals = []
    positioning = []
    context_statuses = []
    by_provider: dict[str, list[dict]] = {}

    for index, item in enumerate(config["context"]["eia_series"], start=1):
        if not item.get("commodity_code"):
            continue
        row = fixture_row(
            CATEGORY_FIELDS["commodity_fundamentals"],
            as_of_date="2026-08-06",
            category="commodity_fundamentals",
            metric_code=item["metric_code"],
            value=str(200 + index),
            unit=item["expected_unit"],
            source="U.S. Energy Information Administration",
            source_url=f"https://api.eia.gov/v2/{item['route']}/data/",
            commodity_code=item["commodity_code"],
            commodity_family=item["commodity_family"],
            metric_role="physical_fundamental",
            measurement_kind=item["measurement_kind"],
            participant_class="",
            known_as_of="2026-08-07T12:00:00Z",
            reference_period="2026-08-06",
        )
        fundamentals.append(row)
        by_provider.setdefault(item["provider"], []).append(row)

    for contract in config["context"]["cftc_contracts"]:
        if not contract.get("commodity_code"):
            continue
        measurements = [("open_interest", "open_interest", "")]
        for participant in V2_CFTC_PARTICIPANTS:
            measurements.extend((
                (f"{participant}_net", "net_position", participant),
                (f"{participant}_net_change", "net_position", participant),
                (f"{participant}_percentile", "percentile", participant),
            ))
        for index, (suffix, measurement, participant) in enumerate(measurements):
            row = fixture_row(
                CATEGORY_FIELDS["positioning_flows"],
                as_of_date="2026-08-04",
                category="positioning_flows",
                market=contract["market_name"],
                metric_code=f"{contract['commodity_code']}_{suffix}",
                value=str(300 + index),
                unit="ratio" if suffix.endswith("percentile") else "contracts",
                source="U.S. Commodity Futures Trading Commission",
                source_url=(
                    "https://publicreporting.cftc.gov/resource/72hh-3qpy.csv"
                ),
                commodity_code=contract["commodity_code"],
                commodity_family=contract["commodity_family"],
                metric_role="positioning",
                measurement_kind=measurement,
                participant_class=participant,
                known_as_of="2026-08-07T19:30:00Z",
                reference_period="2026-08-04",
            )
            positioning.append(row)
    by_provider["cftc_disaggregated"] = positioning

    psd_rows = []
    for index, item in enumerate(config["context"]["usda_psd"], start=1):
        attributes = (
            ("ending_stocks", "inventory", 25.0),
            ("domestic_use", "demand", 100.0),
        ) if item["commodity_code"] == "CORN" else (
            ("production", "supply", float(400 + index)),
        )
        for attribute, measurement, value in attributes:
            row = fixture_row(
                CATEGORY_FIELDS["commodity_fundamentals"],
                as_of_date="2026-08-07",
                category="commodity_fundamentals",
                market="World",
                metric_code=(
                    f"usda_psd_{item['commodity_code'].lower()}_00_2026_{attribute}"
                ),
                value=str(value),
                unit=item["unit_names"][0],
                source="USDA Foreign Agricultural Service",
                source_url=(
                    "https://api.fas.usda.gov/api/psd/commodity/fixture/"
                    "world/year/2026"
                ),
                commodity_code=item["commodity_code"],
                commodity_family=item["commodity_family"],
                metric_role="physical_fundamental",
                measurement_kind=measurement,
                participant_class="",
                known_as_of="2026-08-07T12:00:00Z",
                reference_period="2026",
            )
            psd_rows.append(row)
            fundamentals.append(row)
    by_provider["usda_psd"] = psd_rows

    esr_rows = []
    for index, item in enumerate(config["context"]["usda_esr"], start=1):
        row = fixture_row(
            CATEGORY_FIELDS["commodity_fundamentals"],
            as_of_date="2026-08-06",
            category="commodity_fundamentals",
            market="United States export sales (all destinations)",
            metric_code=f"usda_esr_{item['commodity_code'].lower()}_2026_net_sales",
            value=str(500 + index),
            unit=item["unit_name"],
            source="USDA Foreign Agricultural Service",
            source_url=(
                "https://api.fas.usda.gov/api/esr/exports/commodityCode/"
                "fixture/allCountries/2026"
            ),
            commodity_code=item["commodity_code"],
            commodity_family=item["commodity_family"],
            metric_role="physical_fundamental",
            measurement_kind="trade",
            participant_class="",
            known_as_of="2026-08-07T12:00:00Z",
            reference_period="2026-08-06",
        )
        esr_rows.append(row)
        fundamentals.append(row)
    by_provider["usda_esr"] = esr_rows

    for provider, rows in by_provider.items():
        if provider.startswith("eia_"):
            source = "U.S. Energy Information Administration"
            source_url = "https://api.eia.gov/v2/"
            frequency = "weekly"
            category = "commodity_fundamentals"
        elif provider == "cftc_disaggregated":
            source = "U.S. Commodity Futures Trading Commission"
            source_url = "https://publicreporting.cftc.gov/"
            frequency = "weekly"
            category = "positioning_flows"
        else:
            source = "USDA Foreign Agricultural Service"
            source_url = "https://apps.fas.usda.gov/opendatawebV2/"
            frequency = "monthly" if provider == "usda_psd" else "weekly"
            category = "commodity_fundamentals"
        context_statuses.append(_provider_status(
            provider=provider,
            category=category,
            requiredness="required",
            status="OK",
            observations=len(rows),
            source=source,
            source_url=source_url,
            frequency=frequency,
        ))
    for item in config["context"]["metals"]:
        context_statuses.append(_provider_status(
            provider=item["provider"],
            category="commodity_fundamentals",
            requiredness="optional",
            status="POINT_IN_TIME_UNAVAILABLE",
            observations=0,
            source=item["source"],
            source_url=item["source_url"],
            frequency=item["frequency"],
        ))

    metric_history = [
        _metric_history_row(row)
        for row in (*fundamentals, *positioning)
    ]
    managed_base = next(
        row for row in positioning
        if row["metric_code"] == "NATGAS_HH_managed_money_net"
    )
    for weeks_back in range(1, 52):
        observation = date(2026, 8, 4) - timedelta(weeks=weeks_back)
        metric_history.append(_metric_history_row(
            managed_base,
            observation=observation,
            known_as_of=_utc_z(datetime.combine(
                observation + timedelta(days=3),
                datetime.min.time(),
                tzinfo=timezone.utc,
            )),
            value=300 - weeks_back,
        ))
    storage_base = next(
        row for row in fundamentals
        if row["metric_code"] == "eia_ng_storage_lower48"
    )
    current_iso_week = date(2026, 8, 6).isocalendar().week
    for prior_year in range(2021, 2026):
        observation = date.fromisocalendar(prior_year, current_iso_week, 4)
        metric_history.append(_metric_history_row(
            storage_base,
            observation=observation,
            known_as_of=_utc_z(datetime.combine(
                observation + timedelta(days=1),
                datetime.min.time(),
                tzinfo=timezone.utc,
            )),
            value=180 + prior_year - 2021,
        ))
    metric_history.sort(key=lambda row: (
        row["commodity_code"],
        row["metric_code"],
        row["metric_role"],
        row["measurement_kind"],
        row["participant_class"],
        row["observation_date"],
        row["known_as_of"],
        row["record_id"],
    ))

    formula_specs = load_formula_specs(config_path)
    facts = build_research_facts(
        price_history,
        [
            {key: (None if value == "" else value) for key, value in row.items()}
            for row in metric_history
        ],
        formula_specs,
        date(2026, 8, 9),
    )
    if set(fact["fact_code"] for fact in facts) != set(formula_specs):
        raise AssertionError("complete V2 fixture must emit every registered fact")

    write_csv(
        outputs["macro_assets"] / "commodities.csv",
        MACRO_V3_FIELDS,
        price_snapshots,
    )
    write_csv(
        outputs["macro_assets"] / "source_log.csv",
        MACRO_SOURCE_LOG_V3_FIELDS,
        macro_statuses,
    )
    write_csv(
        outputs["macro_assets"] / "commodity_price_history.csv",
        PRICE_HISTORY_FIELDS,
        price_history,
    )
    write_csv(
        outputs["weekly_context"] / "commodity_fundamentals.csv",
        CATEGORY_FIELDS["commodity_fundamentals"],
        fundamentals,
    )
    write_csv(
        outputs["weekly_context"] / "positioning_flows.csv",
        CATEGORY_FIELDS["positioning_flows"],
        positioning,
    )
    write_csv(
        outputs["weekly_context"] / "source_log.csv",
        CATEGORY_FIELDS["source_log"],
        context_statuses,
    )
    write_csv(
        outputs["weekly_context"] / "commodity_metric_history.csv",
        METRIC_HISTORY_FIELDS,
        metric_history,
    )
    write_csv(
        outputs["weekly_context"] / "commodity_research_facts.csv",
        RESEARCH_FACT_FIELDS,
        [
            {
                **fact,
                "input_record_ids": repr(fact["input_record_ids"]),
                "source_urls": repr(fact["source_urls"]),
            }
            for fact in facts
        ],
    )
    return {
        "commodity_price_history": price_history,
        "commodity_metric_history": metric_history,
        "commodity_research_facts": facts,
    }


def rewrite_v2_research_facts(outputs: dict[str, Path]) -> None:
    def normalized_rows(path: Path) -> list[dict]:
        return [
            {key: (None if value == "" else value) for key, value in row.items()}
            for row in read_csv_rows(path)
        ]

    facts = build_research_facts(
        normalized_rows(
            outputs["macro_assets"] / "commodity_price_history.csv"
        ),
        normalized_rows(
            outputs["weekly_context"] / "commodity_metric_history.csv"
        ),
        load_formula_specs(PRODUCTION_CONFIG_PATH),
        date(2026, 8, 9),
    )
    write_csv(
        outputs["weekly_context"] / "commodity_research_facts.csv",
        RESEARCH_FACT_FIELDS,
        [
            {
                **fact,
                "input_record_ids": repr(fact["input_record_ids"]),
                "source_urls": repr(fact["source_urls"]),
            }
            for fact in facts
        ],
    )


class WeekWindowTests(unittest.TestCase):
    def test_tuesday_targets_the_previous_finished_sunday(self):
        now = datetime(2026, 8, 11, 10, 0, tzinfo=ZoneInfo("Asia/Hong_Kong"))

        window = latest_finished_week(now)

        self.assertEqual(window.start, date(2026, 8, 3))
        self.assertEqual(window.end, date(2026, 8, 9))
        self.assertEqual(window.week_id, "week_20260803-20260809")

    def test_sunday_targets_the_prior_week(self):
        now = datetime(2026, 8, 9, 12, 0, tzinfo=ZoneInfo("Asia/Hong_Kong"))

        self.assertEqual(latest_finished_week(now).end, date(2026, 8, 2))

    def test_pipeline_commands_use_the_finished_window_and_staged_outputs(self):
        window = latest_finished_week(
            datetime(2026, 8, 11, 10, 0, tzinfo=ZoneInfo("Asia/Hong_Kong"))
        )
        with TemporaryDirectory() as directory:
            staging_week = Path(directory) / window.week_id

            specs = build_pipeline_specs(staging_week, window)

            self.assertEqual(
                [spec.name for spec in specs],
                [
                    "equity_indices",
                    "equity_sectors",
                    "gics_sectors",
                    "macro_assets",
                    "weekly_context",
                ],
            )
            for spec in specs[:4]:
                self.assertIn("--as-of-date", spec.command)
                self.assertEqual(
                    spec.command[spec.command.index("--as-of-date") + 1],
                    "2026-08-09",
                )
            context = specs[4]
            self.assertEqual(
                context.command[context.command.index("--start-date") + 1],
                "2026-08-03",
            )
            self.assertEqual(
                context.command[context.command.index("--end-date") + 1],
                "2026-08-09",
            )
            for spec in specs:
                output = Path(spec.output_dir)
                self.assertEqual(output.parent, staging_week)
                self.assertTrue(output.name.endswith("20260809"))
                self.assertEqual(
                    spec.command[spec.command.index("--output-dir") + 1],
                    spec.output_dir,
                )


class SafeErrorReasonTests(unittest.TestCase):
    def test_unquoted_absolute_path_keeps_only_the_basename(self):
        error = RuntimeError("cannot read /Users/alice/private/token.txt")

        self.assertEqual(
            weekly_release_module.safe_error_reason(error),
            "cannot read token.txt",
        )

    def test_parenthesized_absolute_path_keeps_surrounding_punctuation(self):
        error = RuntimeError("cannot read (/Users/alice/private/token.txt), retry")

        self.assertEqual(
            weekly_release_module.safe_error_reason(error),
            "cannot read (token.txt), retry",
        )

    def test_unquoted_absolute_path_with_spaces_keeps_only_the_basename(self):
        error = RuntimeError(
            "cannot read /Users/alice/market data/private/token.txt"
        )

        self.assertEqual(
            weekly_release_module.safe_error_reason(error),
            "cannot read token.txt",
        )

    def test_http_url_is_not_mistaken_for_an_absolute_file_path(self):
        error = RuntimeError("source https://example.test/path failed")

        self.assertEqual(
            weekly_release_module.safe_error_reason(error),
            "source https://example.test/path failed",
        )


class StagedValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "week_20260803-20260809"
        self.window = latest_finished_week(
            datetime(2026, 8, 11, 10, 0, tzinfo=ZoneInfo("Asia/Hong_Kong"))
        )
        self.outputs = write_valid_staged_week(self.root, self.window)
        write_complete_v2_release_fixture(self.outputs)

    def _exact_gate_config_path(self) -> Path:
        config_path = Path(self.temporary.name) / "exact-gate-config.json"
        config_path.write_text(
            json.dumps(exact_gate_config()),
            encoding="utf-8",
        )
        return config_path

    def test_contracts_one_through_five_match_public_parent_dataset_specs(self):
        for version, expected_fingerprint in PUBLIC_CONTRACT_SPEC_FINGERPRINTS.items():
            with self.subTest(version=version):
                specs = []
                for spec in release_datasets_for_contract(version):
                    item = asdict(spec)
                    item["accepted_statuses"] = sorted(item["accepted_statuses"])
                    specs.append(item)
                canonical = json.dumps(
                    specs,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                self.assertEqual(
                    hashlib.sha256(canonical).hexdigest(),
                    expected_fingerprint,
                )

                by_identity = {
                    (spec.pipeline, spec.filename): spec
                    for spec in release_datasets_for_contract(version)
                }
                macro = by_identity[("macro_assets", "commodities.csv")]
                self.assertEqual(
                    macro.required_columns,
                    tuple(
                        PUBLIC_MACRO_FIELDS
                        if version <= 2
                        else PUBLIC_MACRO_V3_FIELDS
                    ),
                )
                self.assertEqual(macro.timestamp_columns, ())
                self.assertEqual(
                    macro.date_columns,
                    tuple(
                        RETURN_DATE_FIELDS
                        if version <= 2
                        else (*RETURN_DATE_FIELDS, "known_as_of")
                    ),
                )
                context_metric = by_identity[
                    ("weekly_context", "commodity_fundamentals.csv")
                ]
                self.assertEqual(
                    context_metric.required_columns,
                    tuple(PUBLIC_METRIC_FIELDS),
                )
                source_log = by_identity[("weekly_context", "source_log.csv")]
                self.assertEqual(
                    source_log.required_columns,
                    tuple(
                        LEGACY_CONTEXT_SOURCE_LOG_FIELDS
                        if version == 1
                        else PUBLIC_CONTEXT_SOURCE_LOG_FIELDS
                    ),
                )
                self.assertEqual(
                    source_log.numeric_columns,
                    ("freshness_days", "observations", "elapsed_ms"),
                )

    def test_exact_contract_six_fixture_reaches_research_validation(self):
        with patch.object(
            weekly_release_module,
            "_validate_commodity_research_v2",
            side_effect=ReleaseValidationError(
                "contract-six-entrypoint-sentinel"
            ),
        ):
            with self.assertRaisesRegex(
                ReleaseValidationError,
                "contract-six-entrypoint-sentinel",
            ):
                validate_staged_week(self.root, self.window)

    def test_valid_public_legacy_fixtures_without_v6_fields_pass_contracts_one_to_five(self):
        for version in range(1, 6):
            with self.subTest(version=version):
                root = Path(self.temporary.name) / f"legacy-v{version}"
                outputs = write_valid_staged_week(root, self.window)
                write_exact_gate_fixture(outputs)
                write_legacy_contract_fixture(outputs, version)

                with patch(
                    "pipeline.internal.common.DEFAULT_CONFIG_PATH",
                    self._exact_gate_config_path(),
                ):
                    manifest = validate_staged_week(
                        root,
                        self.window,
                        dataset_contract_version=version,
                    )

                self.assertEqual(manifest["dataset_contract_version"], version)

    def test_exact_configured_commodity_gate_accepts_complete_fixture(self):
        manifest = validate_staged_week(self.root, self.window)

        self.assertEqual(manifest["dataset_contract_version"], 6)

    def test_exact_gate_rejects_missing_configured_macro_price_and_status(self):
        for missing_artifact in ("price", "status"):
            with self.subTest(missing_artifact=missing_artifact):
                write_complete_v2_release_fixture(self.outputs)
                if missing_artifact == "price":
                    path = self.outputs["macro_assets"] / "commodities.csv"
                    rows = [
                        row
                        for row in read_csv_rows(path)
                        if row["series_code"] != "WTI"
                    ]
                    write_csv(path, MACRO_V3_FIELDS, rows)
                else:
                    path = self.outputs["macro_assets"] / "source_log.csv"
                    rows = [
                        row
                        for row in read_csv_rows(path)
                        if row["series_code"] != "WTI"
                    ]
                    write_csv(path, MACRO_SOURCE_LOG_V3_FIELDS, rows)
                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    r"configured macro.*WTI",
                ):
                    validate_staged_week(self.root, self.window)

    def test_exact_gate_rejects_missing_configured_eia_metric(self):
        path = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        rows = [
            row
            for row in read_csv_rows(path)
            if row["metric_code"] != "eia_gasoline_stocks"
        ]
        write_csv(path, CATEGORY_FIELDS["commodity_fundamentals"], rows)

        with self.assertRaisesRegex(
            ReleaseValidationError,
            r"eia_refined_products.*eia_gasoline_stocks",
        ):
            validate_staged_week(self.root, self.window)

    def test_exact_gate_rejects_duplicate_configured_provider_status(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        rows = read_csv_rows(path)
        target = next(
            row for row in rows if row["provider"] == "eia_refined_products"
        )
        rows.append(dict(target))
        write_csv(path, CATEGORY_FIELDS["source_log"], rows)

        with self.assertRaisesRegex(
            ReleaseValidationError,
            r"status.*unique.*eia_refined_products",
        ):
            validate_staged_week(self.root, self.window)

    def test_exact_gate_rejects_missing_configured_cftc_commodity(self):
        path = self.outputs["weekly_context"] / "positioning_flows.csv"
        rows = [
            row for row in read_csv_rows(path) if row["commodity_code"] != "WTI"
        ]
        write_csv(path, CATEGORY_FIELDS["positioning_flows"], rows)

        with self.assertRaisesRegex(
            ReleaseValidationError,
            r"cftc_disaggregated.*WTI",
        ):
            validate_staged_week(self.root, self.window)

    def test_exact_gate_rejects_mismapped_cftc_open_interest_identity(self):
        for field, bad_value in (
            ("market", "WRONG CONTRACT MARKET"),
            ("metric_code", "WTI_managed_money_net"),
        ):
            with self.subTest(field=field):
                write_complete_v2_release_fixture(self.outputs)
                path = self.outputs["weekly_context"] / "positioning_flows.csv"
                rows = read_csv_rows(path)
                target = next(
                    row
                    for row in rows
                    if row["metric_code"] == "WTI_open_interest"
                )
                target[field] = bad_value
                write_csv(path, CATEGORY_FIELDS["positioning_flows"], rows)

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    r"CFTC contract identity.*067651.*WTI",
                ):
                    validate_staged_week(self.root, self.window)

    def test_exact_gate_not_configured_eia_rejects_residual_derived_rows(self):
        merge_context_status_rows(
            self.outputs,
            [
                fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider="eia_refined_products",
                    category="commodity_fundamentals",
                    requiredness="optional",
                    status="NOT_CONFIGURED",
                    observations="0",
                    source_url="https://api.eia.gov/v2/",
                )
            ],
        )
        path = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        derived = fixture_row(
            CATEGORY_FIELDS["commodity_fundamentals"],
            as_of_date="2026-08-07",
            metric_code="eia_crude_stocks_ex_spr_change",
            commodity_code="WTI",
            commodity_family="refined_products",
            metric_role="physical_fundamental",
            measurement_kind="inventory",
            participant_class="",
            known_as_of="2026-08-07T12:00:00-04:00",
            reference_period="2026-07-31 to 2026-08-07",
            source="U.S. Energy Information Administration",
            source_url="https://api.eia.gov/v2/petroleum/sum/sndw/data/",
        )
        retained = [
            row
            for row in read_csv_rows(path)
            if not (
                row["source"] == "U.S. Energy Information Administration"
                and row["commodity_family"] == "refined_products"
            )
        ]
        write_csv(
            path,
            CATEGORY_FIELDS["commodity_fundamentals"],
            [*retained, derived],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            r"eia_refined_products NOT_CONFIGURED.*no base or derived rows",
        ):
            validate_staged_week(self.root, self.window)

    def test_exact_gate_requires_each_configured_supplemental_status(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        rows = [
            row
            for row in read_csv_rows(path)
            if row["provider"] != "comex_gold_stocks"
        ]
        write_csv(path, CATEGORY_FIELDS["source_log"], rows)

        with self.assertRaisesRegex(
            ReleaseValidationError,
            r"status.*comex_gold_stocks",
        ):
            validate_staged_week(self.root, self.window)

    def test_exact_gate_requires_business_rows_for_ok_configured_metal(self):
        merge_context_status_rows(
            self.outputs,
            [
                fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider="comex_gold_stocks",
                    category="commodity_fundamentals",
                    requiredness="optional",
                    status="OK",
                    observations="3",
                    source="CME Group",
                    source_url="https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls",
                )
            ],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            r"comex_gold_stocks.*observations",
        ):
            validate_staged_week(self.root, self.window)

    def test_exact_gate_rejects_wrong_family_for_configured_metal(self):
        merge_context_status_rows(
            self.outputs,
            [
                fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider="comex_gold_stocks",
                    category="commodity_fundamentals",
                    requiredness="optional",
                    status="OK",
                    observations="3",
                    source="CME Group",
                    source_url="https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls",
                )
            ],
        )
        path = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        rows = read_csv_rows(path)
        metal_rows = configured_gold_metal_rows()
        metal_rows[2]["commodity_family"] = "copper"
        rows.extend(metal_rows)
        write_csv(path, CATEGORY_FIELDS["commodity_fundamentals"], rows)

        with self.assertRaisesRegex(
            ReleaseValidationError,
            r"comex_gold_stocks.*GOLD_COMEX.*gold",
        ):
            validate_staged_week(self.root, self.window)

    def test_exact_gate_non_ok_configured_metal_requires_zero_rows(self):
        for mutation in ("real_metric_mutated_url", "mutated_metric_exact_url"):
            with self.subTest(mutation=mutation):
                write_complete_v2_release_fixture(self.outputs)
                merge_context_status_rows(
                    self.outputs,
                    [_provider_status(
                        provider="comex_gold_stocks",
                        category="commodity_fundamentals",
                        requiredness="optional",
                        status="FETCH_FAILED",
                        observations=0,
                        source="CME Group",
                        source_url=(
                            "https://www.cmegroup.com/delivery_reports/"
                            "Gold_Stocks.xls"
                        ),
                        frequency="daily",
                    )],
                )
                path = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
                rows = read_csv_rows(path)
                residual = configured_gold_metal_rows()[2]
                if mutation == "real_metric_mutated_url":
                    residual["source_url"] = (
                        "https://www.cmegroup.com/delivery_reports/"
                        "Gold_Stocks_Alternate.xls"
                    )
                else:
                    residual["metric_code"] = "gold_comex_wrong_inventory"
                rows.append(residual)
                write_csv(path, CATEGORY_FIELDS["commodity_fundamentals"], rows)

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    r"comex_gold_stocks FETCH_FAILED.*requires zero",
                ):
                    validate_staged_week(self.root, self.window)

    def test_exact_gate_requires_complete_unique_metal_identities_and_count(self):
        mutations = {
            "partial_ok": lambda rows, status: rows.__delitem__(slice(1, None)),
            "missing": lambda rows, status: rows.pop(1),
            "duplicate": lambda rows, status: rows.__setitem__(2, dict(rows[0])),
            "wrong_metric": lambda rows, status: rows[2].__setitem__(
                "metric_code", "gold_comex_wrong_inventory"
            ),
            "observations_mismatch": lambda rows, status: status.__setitem__(
                "observations", "2"
            ),
        }
        for mutation, mutate in mutations.items():
            with self.subTest(mutation=mutation):
                write_complete_v2_release_fixture(self.outputs)
                status = fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider="comex_gold_stocks",
                    category="commodity_fundamentals",
                    requiredness="optional",
                    status="OK",
                    observations="3",
                    source="CME Group",
                    source_url=(
                        "https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls"
                    ),
                )
                rows = configured_gold_metal_rows()
                mutate(rows, status)
                path = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
                existing = read_csv_rows(path)
                write_csv(
                    path,
                    CATEGORY_FIELDS["commodity_fundamentals"],
                    [*existing, *rows],
                )
                merge_context_status_rows(self.outputs, [status])
                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    r"comex_gold_stocks.*(?:metric identities|observations)",
                ):
                    validate_staged_week(self.root, self.window)

    def test_official_provenance_rejects_lookalike_world_bank_and_cftc_hosts(self):
        for artifact, lookalike, expected_error in (
            (
                "price",
                "https://notworldbank.org/commodity-prices.xlsx",
                "configured macro price.*COMEX_GOLD",
            ),
            (
                "positioning",
                "https://notcftc.gov/resource/72hh-3qpy.csv",
                "CFTC contract identity.*088691.*GOLD_COMEX",
            ),
        ):
            with self.subTest(artifact=artifact):
                write_complete_v2_release_fixture(self.outputs)
                if artifact == "price":
                    path = self.outputs["macro_assets"] / "commodities.csv"
                    fields = MACRO_V3_FIELDS
                    rows = read_csv_rows(path)
                    target = next(row for row in rows if row["series_code"] == "COMEX_GOLD")
                else:
                    path = self.outputs["weekly_context"] / "positioning_flows.csv"
                    fields = CATEGORY_FIELDS["positioning_flows"]
                    rows = read_csv_rows(path)
                    target = next(row for row in rows if row["commodity_code"] == "GOLD_COMEX")
                target["source_url"] = lookalike
                write_csv(path, fields, rows)

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    expected_error,
                ):
                    validate_staged_week(self.root, self.window)

    def test_rejects_a_missing_required_file(self):
        missing = self.outputs["equity_indices"] / "02_equity_indices.csv"
        missing.unlink()

        with self.assertRaisesRegex(ReleaseValidationError, "02_equity_indices.csv"):
            validate_staged_week(self.root, self.window)

    def test_contract_v2_keeps_the_pre_wave_1_file_set(self):
        write_legacy_contract_fixture(self.outputs, 2)

        manifest = validate_staged_week(
            self.root,
            self.window,
            dataset_contract_version=2,
        )

        self.assertEqual(manifest["dataset_contract_version"], 2)

    def test_contract_v3_keeps_the_pre_fund_flow_file_set(self):
        write_legacy_contract_fixture(self.outputs, 3)

        manifest = validate_staged_week(
            self.root,
            self.window,
            dataset_contract_version=3,
        )

        self.assertEqual(manifest["dataset_contract_version"], 3)

    def test_contract_v4_keeps_the_pre_company_data_file_set(self):
        write_legacy_contract_fixture(self.outputs, 4)

        manifest = validate_staged_week(
            self.root,
            self.window,
            dataset_contract_version=4,
        )

        self.assertEqual(manifest["dataset_contract_version"], 4)

    def test_optional_macro_proxy_failure_is_audited_without_blocking_release(self):
        path = self.outputs["macro_assets"] / "source_log.csv"
        configured_rows = read_csv_rows(path)
        proxy_row = fixture_row(
            MACRO_SOURCE_LOG_V3_FIELDS,
            series_code="COMEX_COPPER",
            provider="yahoo_chart",
            source_tier="public_proxy",
            requiredness="optional",
            status="FETCH_FAILED",
        )
        rows = [
            *configured_rows,
            fixture_row(MACRO_SOURCE_LOG_V3_FIELDS, series_code="OFFICIAL"),
            proxy_row,
        ]
        write_csv(path, MACRO_SOURCE_LOG_V3_FIELDS, rows)

        validate_staged_week(self.root, self.window)

        proxy_row["requiredness"] = "required"
        write_csv(path, MACRO_SOURCE_LOG_V3_FIELDS, rows)
        with self.assertRaisesRegex(ReleaseValidationError, "FETCH_FAILED"):
            validate_staged_week(self.root, self.window)

    def test_optional_claim_does_not_allow_official_chinabond_failure(self):
        path = self.outputs["macro_assets"] / "source_log.csv"
        rows = [
            fixture_row(MACRO_SOURCE_LOG_V3_FIELDS, series_code="OFFICIAL"),
            fixture_row(
                MACRO_SOURCE_LOG_V3_FIELDS,
                series_code="CGB10Y",
                provider="china_bond",
                source_tier="official",
                requiredness="optional",
                status="FETCH_FAILED",
            ),
        ]
        write_csv(path, MACRO_SOURCE_LOG_V3_FIELDS, rows)

        with self.assertRaisesRegex(ReleaseValidationError, "FETCH_FAILED"):
            validate_staged_week(self.root, self.window)

    def test_cross_asset_calculation_resolves_dependencies_from_macro_source_log(self):
        cross_asset = self.outputs["macro_assets"] / "cross_asset.csv"
        write_csv(
            cross_asset,
            MACRO_V3_FIELDS,
            [
                fixture_row(
                    MACRO_V3_FIELDS,
                    asset_class="cross_asset",
                    series_code="US_STOCK_BOND_CORR_13W",
                    provider="calculated",
                    source_url=weekly_release_module.CALCULATED_SOURCE_REFERENCES[
                        "US_STOCK_BOND_CORR_13W"
                    ],
                    calculation_id="rolling_correlation",
                    formula_version="rolling-correlation-v1",
                    input_series_codes="SPY_CLOSE_PROXY|TLT_CLOSE_PROXY",
                )
            ],
        )
        source_log = self.outputs["macro_assets"] / "source_log.csv"
        dependency_rows = [
            fixture_row(
                MACRO_SOURCE_LOG_V3_FIELDS,
                series_code=series_code,
                provider="yahoo_chart",
                source_tier="public_proxy",
                requiredness="optional",
                source_url=f"https://example.test/{series_code}",
            )
            for series_code in ("SPY_CLOSE_PROXY", "TLT_CLOSE_PROXY")
        ]
        dependency_rows.append(
            fixture_row(
                MACRO_SOURCE_LOG_V3_FIELDS,
                series_code="US_STOCK_BOND_CORR_13W",
                provider="calculated",
                source_tier="public_proxy",
                requiredness="optional",
                source_url=weekly_release_module.CALCULATED_SOURCE_REFERENCES[
                    "US_STOCK_BOND_CORR_13W"
                ],
                calculation_id="rolling_correlation",
                formula_version="rolling-correlation-v1",
                input_series_codes="SPY_CLOSE_PROXY|TLT_CLOSE_PROXY",
            )
        )
        configured_rows = read_csv_rows(source_log)
        write_csv(
            source_log,
            MACRO_SOURCE_LOG_V3_FIELDS,
            [*configured_rows, *dependency_rows],
        )

        validate_staged_week(self.root, self.window)

        write_csv(
            source_log,
            MACRO_SOURCE_LOG_V3_FIELDS,
            [*configured_rows, dependency_rows[0], dependency_rows[-1]],
        )
        with self.assertRaisesRegex(ReleaseValidationError, "TLT_CLOSE_PROXY"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_required_table_with_only_a_header(self):
        path = self.outputs["macro_assets"] / "fixed_income.csv"
        write_csv(path, MACRO_V3_FIELDS, [])

        with self.assertRaisesRegex(ReleaseValidationError, "fixed_income.csv.*empty"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_missing_required_column(self):
        path = self.outputs["gics_sectors"] / "03_gics_sectors.csv"
        fields = [field for field in GICS_FIELDS if field != "source_url"]
        write_csv(path, fields, [fixture_row(fields, gics_sector_code="GICS")])

        with self.assertRaisesRegex(ReleaseValidationError, "source_url"):
            validate_staged_week(self.root, self.window)

    def test_rejects_any_published_csv_without_a_header(self):
        path = self.outputs["weekly_context"] / "unregistered_optional.csv"
        path.write_text("\n", encoding="utf-8")

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "unregistered_optional.csv.*standard header",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_symlinked_published_file(self):
        target = self.root.parent / "outside.csv"
        target.write_text("value\n1\n", encoding="utf-8")
        published = self.outputs["weekly_context"] / "events.csv"
        published.unlink()
        published.symlink_to(target)

        with self.assertRaisesRegex(ReleaseValidationError, "symbolic link"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_duplicate_csv_header(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        fields = [*INDEX_FIELDS, "ticker"]
        write_csv(path, fields, [fixture_row(fields, ticker="INDEX")])

        with self.assertRaisesRegex(ReleaseValidationError, "duplicate.*ticker"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_ragged_csv_row(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        content = path.read_text(encoding="utf-8").rstrip("\n")
        path.write_text(f"{content},unexpected\n", encoding="utf-8")

        with self.assertRaisesRegex(ReleaseValidationError, "column count"):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_unterminated_quoted_csv_field(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        content = path.read_text(encoding="utf-8").rstrip("\n")
        path.write_text(f'{content},"unterminated\n', encoding="utf-8")

        with self.assertRaisesRegex(ReleaseValidationError, "malformed CSV"):
            validate_staged_week(self.root, self.window)

    def test_rejects_fetch_failed_in_a_source_log(self):
        path = self.outputs["equity_sectors"] / "source_log.csv"
        row = fixture_row(
            SECTOR_SOURCE_LOG_FIELDS,
            sector_code="SECTOR",
            status="FETCH_FAILED",
        )
        write_csv(path, SECTOR_SOURCE_LOG_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "FETCH_FAILED"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_visible_record_after_the_target_sunday(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        row = fixture_row(INDEX_FIELDS, ticker="INDEX", latest_date="2026-08-10")
        write_csv(path, INDEX_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "2026-08-10.*2026-08-09"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_visible_record_without_a_source_url(self):
        path = self.outputs["macro_assets"] / "commodities.csv"
        row = fixture_row(
            MACRO_V3_FIELDS,
            series_code="COMMODITY",
            source_url="",
        )
        write_csv(path, MACRO_V3_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "source_url"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_commodity_research_row_without_a_commodity_code(self):
        path = self.outputs["macro_assets"] / "commodities.csv"
        row = fixture_row(
            MACRO_FIELDS,
            asset_class="commodity",
            series_code="WTI",
            commodity_code="",
            commodity_family="refined_products",
            known_as_of="2026-08-08T12:00:00-04:00",
        )
        write_csv(path, MACRO_V3_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "commodity_code"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_commodity_research_row_with_an_unsupported_family(self):
        path = self.outputs["macro_assets"] / "commodities.csv"
        row = fixture_row(
            MACRO_FIELDS,
            asset_class="commodity",
            series_code="WTI",
            commodity_code="WTI",
            commodity_family="unknown_family",
            known_as_of="2026-08-08T12:00:00-04:00",
        )
        write_csv(path, MACRO_V3_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "commodity_family"):
            validate_staged_week(self.root, self.window)

    def test_rejects_unsupported_non_null_commodity_semantic_vocabulary(self):
        path = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        valid = fixture_row(
            CATEGORY_FIELDS["commodity_fundamentals"],
            as_of_date="2026-08-07",
            commodity_code="WTI",
            commodity_family="refined_products",
            metric_role="physical_fundamental",
            measurement_kind="inventory",
            participant_class="",
            known_as_of="2026-08-07T12:00:00-04:00",
            reference_period="2026-08-07",
        )
        for field, unsupported in (
            ("metric_role", "fundamental"),
            ("measurement_kind", "physical_level"),
        ):
            with self.subTest(field=field):
                write_csv(
                    path,
                    CATEGORY_FIELDS["commodity_fundamentals"],
                    [{**valid, field: unsupported}],
                )
                with self.assertRaisesRegex(ReleaseValidationError, field):
                    validate_staged_week(self.root, self.window)

    def test_rejects_malformed_naive_or_future_commodity_known_as_of(self):
        cases = (
            (
                "commodity_fundamentals",
                "physical_fundamental",
                "inventory",
            ),
            ("positioning_flows", "positioning", "open_interest"),
        )
        for category, role, kind in cases:
            path = self.outputs["weekly_context"] / f"{category}.csv"
            base = fixture_row(
                CATEGORY_FIELDS[category],
                as_of_date="2026-08-07",
                commodity_code="WTI",
                commodity_family="refined_products",
                metric_role=role,
                measurement_kind=kind,
                participant_class="",
                reference_period="2026-08-07",
            )
            for known_as_of in (
                "not-a-timestamp",
                "2026-08-09T12:00:00",
                "2026-08-10T00:00:00+08:00",
            ):
                with self.subTest(category=category, known_as_of=known_as_of):
                    write_csv(
                        path,
                        CATEGORY_FIELDS[category],
                        [{**base, "known_as_of": known_as_of}],
                    )
                    with self.assertRaisesRegex(
                        ReleaseValidationError,
                        "known_as_of.*(?:UTC offset|exceeds)",
                    ):
                        validate_staged_week(self.root, self.window)

    def test_rejects_malformed_naive_or_future_macro_commodity_known_as_of(self):
        path = self.outputs["macro_assets"] / "commodities.csv"
        for known_as_of in (
            "not-a-timestamp",
            "2026-08-09T12:00:00",
            "2026-08-10T00:00:00+08:00",
        ):
            with self.subTest(known_as_of=known_as_of):
                write_exact_gate_fixture(self.outputs)
                rows = read_csv_rows(path)
                target = next(
                    row for row in rows if row["series_code"] == "COMEX_GOLD"
                )
                target["known_as_of"] = known_as_of
                write_csv(path, MACRO_V3_FIELDS, rows)

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    "known_as_of.*(?:UTC offset|exceeds)",
                ):
                    validate_staged_week(self.root, self.window)

    def test_commodity_divergence_summary_does_not_require_instrument_identity(self):
        path = self.outputs["macro_assets"] / "macro_divergence.csv"
        row = fixture_row(
            MACRO_DIVERGENCE_FIELDS,
            asset_class="commodity",
            group="commodities",
        )
        write_csv(path, MACRO_DIVERGENCE_FIELDS, [row])

        try:
            validate_staged_week(self.root, self.window)
        except ReleaseValidationError as error:
            self.fail(str(error))

    def test_rejects_a_non_finite_numeric_value(self):
        path = self.outputs["gics_sectors"] / "03_gics_sectors.csv"
        row = fixture_row(GICS_FIELDS, gics_sector_code="GICS", latest_value="NaN")
        write_csv(path, GICS_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "latest_value.*finite"):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_economic_release_known_after_target_sunday(self):
        path = self.outputs["weekly_context"] / "economic_releases.csv"
        write_csv(
            path,
            CATEGORY_FIELDS["economic_releases"],
            [economic_release_row(known_as_of="2026-08-10T00:00:00+08:00")],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "known_as_of.*2026-08-09",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_economic_release_without_a_known_timestamp(self):
        path = self.outputs["weekly_context"] / "economic_releases.csv"
        write_csv(
            path,
            CATEGORY_FIELDS["economic_releases"],
            [economic_release_row(known_as_of="")],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "known_as_of.*UTC offset",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_economic_release_timestamp_without_a_utc_offset(self):
        path = self.outputs["weekly_context"] / "economic_releases.csv"
        write_csv(
            path,
            CATEGORY_FIELDS["economic_releases"],
            [economic_release_row(release_at_bjt="2026-08-07T20:30:00")],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "release_at_bjt.*UTC offset",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_economic_release_published_after_target_sunday(self):
        path = self.outputs["weekly_context"] / "economic_releases.csv"
        write_csv(
            path,
            CATEGORY_FIELDS["economic_releases"],
            [economic_release_row(release_at_bjt="2026-08-10T00:00:00+08:00")],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "release_at_bjt.*2026-08-09",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_non_finite_optional_economic_release_value(self):
        path = self.outputs["weekly_context"] / "economic_releases.csv"
        write_csv(
            path,
            CATEGORY_FIELDS["economic_releases"],
            [economic_release_row(previous_value="NaN")],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "previous_value.*finite",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_frontend_required_identity_column(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        fields = [field for field in INDEX_FIELDS if field != "region"]
        write_csv(path, fields, [fixture_row(fields, ticker="INDEX")])

        with self.assertRaisesRegex(ReleaseValidationError, "region"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_frontend_required_source_log_column(self):
        path = self.outputs["gics_sectors"] / "source_log.csv"
        fields = [field for field in GICS_SOURCE_LOG_FIELDS if field != "observations"]
        write_csv(path, fields, [fixture_row(fields, gics_sector_code="GICS")])

        with self.assertRaisesRegex(ReleaseValidationError, "observations"):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_extra_current_context_source_log_column(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        fields = [*CATEGORY_FIELDS["source_log"], "unexpected"]
        write_csv(path, fields, [fixture_row(fields, unexpected="extra")])

        with self.assertRaisesRegex(ReleaseValidationError, "unexpected columns"):
            validate_staged_week(self.root, self.window)

    def test_current_staged_context_source_log_accepts_retried_success(self):
        row = fixture_row(
            STAGED_CONTEXT_SOURCE_LOG_FIELDS,
            provider="fixture",
            category="market_internals",
            status="OK",
            as_of_date="2026-08-09",
            phase="normalized",
            attempts="2",
            error_code="",
        )
        merge_context_status_rows(self.outputs, [row])

        validate_staged_week(self.root, self.window)

    def test_rejects_invalid_current_context_provider_phase_contract(self):
        cases = (
            ("unknown phase", {"phase": "discovery"}, "phase"),
            ("zero attempts", {"attempts": "0"}, "attempts"),
            ("negative attempts", {"attempts": "-1"}, "attempts"),
            ("non_integer attempts", {"attempts": "1.5"}, "attempts"),
            ("incomplete success phase", {"phase": "retrieve"}, "normalized"),
            ("success error code", {"error_code": "EIA_TIMEOUT"}, "error_code"),
        )
        for label, mutation, expected_error in cases:
            with self.subTest(label=label):
                row_data = {
                    "provider": "fixture",
                    "category": "market_internals",
                    "status": "OK",
                    "as_of_date": "2026-08-09",
                    "phase": "normalized",
                    "attempts": "1",
                    "error_code": "",
                }
                row_data.update(mutation)
                row = fixture_row(
                    STAGED_CONTEXT_SOURCE_LOG_FIELDS,
                    **row_data,
                )
                merge_context_status_rows(self.outputs, [row])

                with self.assertRaisesRegex(ReleaseValidationError, expected_error):
                    validate_staged_week(self.root, self.window)

    def test_context_source_log_retried_attempts_publish_as_integer_two(self):
        row = fixture_row(
            STAGED_CONTEXT_SOURCE_LOG_FIELDS,
            provider="retried-fixture",
            category="market_internals",
            status="OK",
            as_of_date="2026-08-09",
            phase="normalized",
            attempts="2",
            error_code="",
        )
        merge_context_status_rows(self.outputs, [row])
        manifest = validate_staged_week(self.root, self.window)
        (self.root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        with TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            build_output_bundle(self.root, output, release_id="attempts-fixture")
            context = json.loads((output / "context.json").read_text(encoding="utf-8"))

        retried = next(
            row
            for row in context["source_log"]
            if row["provider"] == "retried-fixture"
        )
        self.assertIs(type(retried["attempts"]), int)
        self.assertEqual(retried["attempts"], 2)

    def test_rejects_an_extra_legacy_context_source_log_column(self):
        (self.outputs["weekly_context"] / "economic_releases.csv").unlink()
        path = self.outputs["weekly_context"] / "source_log.csv"
        fields = [*LEGACY_CONTEXT_SOURCE_LOG_FIELDS, "unexpected"]
        write_csv(path, fields, [fixture_row(fields, unexpected="extra")])

        with self.assertRaisesRegex(ReleaseValidationError, "unexpected columns"):
            validate_staged_week(
                self.root,
                self.window,
                dataset_contract_version=1,
            )

    def test_allows_blank_optional_change_beside_a_valid_core_value(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        row = fixture_row(INDEX_FIELDS, ticker="INDEX", weekly_change="")
        write_csv(path, INDEX_FIELDS, [row])

        validate_staged_week(self.root, self.window)

    def test_allows_blank_optional_base_rank_and_source_log_numeric_cells(self):
        data_path = self.outputs["equity_sectors"] / "03_equity_sectors.csv"
        data_row = fixture_row(
            SECTOR_FIELDS,
            sector_code="SECTOR",
            daily_base_value="",
            weekly_rank="",
        )
        write_csv(data_path, SECTOR_FIELDS, [data_row])
        source_path = self.outputs["equity_sectors"] / "source_log.csv"
        source_row = fixture_row(
            SECTOR_SOURCE_LOG_FIELDS,
            sector_code="SECTOR",
            weekly_base_value="",
        )
        write_csv(source_path, SECTOR_SOURCE_LOG_FIELDS, [source_row])

        validate_staged_week(self.root, self.window)

    def test_allows_insufficient_summary_rows_when_core_data_is_valid(self):
        path = self.outputs["equity_sectors"] / "sector_divergence.csv"
        row = fixture_row(
            SECTOR_DIVERGENCE_FIELDS,
            market="US",
            qc_flag="INSUFFICIENT_DATA",
            valid_count="0",
            breadth_ratio="",
            leader_laggard_spread="",
            dispersion="",
            median_return="",
        )
        write_csv(path, SECTOR_DIVERGENCE_FIELDS, [row])

        validate_staged_week(self.root, self.window)

    def test_rejects_a_core_table_without_any_valid_row(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        row = fixture_row(
            INDEX_FIELDS,
            ticker="INDEX",
            latest_date="",
            latest_value="",
            qc_flag="INSUFFICIENT_DATA",
        )
        write_csv(path, INDEX_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "valid row"):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_unknown_or_unapproved_optional_source_status(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fixture",
            status="MYSTERY",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(ReleaseValidationError, "MYSTERY"):
            validate_staged_week(self.root, self.window)

        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="unregistered_optional_provider",
            category="company_events",
            status="NOT_CONFIGURED",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(ReleaseValidationError, "NOT_CONFIGURED"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_blank_source_status(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fixture",
            status="",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(ReleaseValidationError, "blank"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_source_log_without_an_http_source_url(self):
        path = self.outputs["equity_indices"] / "source_log.csv"
        row = fixture_row(
            INDEX_SOURCE_LOG_FIELDS,
            ticker="INDEX",
            source_url="",
        )
        write_csv(path, INDEX_SOURCE_LOG_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, r"HTTP\(S\)"):
            validate_staged_week(self.root, self.window)

    def test_accepts_not_configured_from_an_optional_context_provider(self):
        merge_context_status_rows(
            self.outputs,
            [_provider_status(
                provider="eia_natural_gas",
                category="commodity_fundamentals",
                requiredness="optional",
                status="NOT_CONFIGURED",
                observations=0,
                source="U.S. Energy Information Administration",
                source_url="https://api.eia.gov/v2/",
                frequency="weekly",
            )],
        )
        fundamentals_path = (
            self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        )
        write_csv(
            fundamentals_path,
            CATEGORY_FIELDS["commodity_fundamentals"],
            [
                row
                for row in read_csv_rows(fundamentals_path)
                if not (
                    row["source"] == "U.S. Energy Information Administration"
                    and row["commodity_family"] == "natural_gas"
                )
            ],
        )
        history_path = (
            self.outputs["weekly_context"] / "commodity_metric_history.csv"
        )
        write_csv(
            history_path,
            METRIC_HISTORY_FIELDS,
            [
                row
                for row in read_csv_rows(history_path)
                if not (
                    row["source"] == "U.S. Energy Information Administration"
                    and row["commodity_family"] == "natural_gas"
                )
            ],
        )
        rewrite_v2_research_facts(self.outputs)

        validate_staged_week(self.root, self.window)

    def test_accepts_separate_usda_not_configured_capability_statuses(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        rows = [
            fixture_row(
                CATEGORY_FIELDS["source_log"],
                provider=provider,
                category="commodity_fundamentals",
                requiredness="optional",
                status="NOT_CONFIGURED",
                observations="0",
                as_of_date="2026-08-09",
                source="USDA Foreign Agricultural Service",
                source_url="https://api.fas.usda.gov/",
            )
            for provider in ("usda_psd", "usda_esr")
        ]
        merge_context_status_rows(self.outputs, rows)
        fundamentals_path = (
            self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        )
        write_csv(
            fundamentals_path,
            CATEGORY_FIELDS["commodity_fundamentals"],
            [
                row
                for row in read_csv_rows(fundamentals_path)
                if not row["metric_code"].startswith(("usda_psd_", "usda_esr_"))
            ],
        )
        history_path = (
            self.outputs["weekly_context"] / "commodity_metric_history.csv"
        )
        write_csv(
            history_path,
            METRIC_HISTORY_FIELDS,
            [
                row
                for row in read_csv_rows(history_path)
                if not row["metric_code"].startswith(("usda_psd_", "usda_esr_"))
            ],
        )
        rewrite_v2_research_facts(self.outputs)

        validate_staged_week(self.root, self.window)

    def test_usda_capability_status_is_required_even_when_both_rows_are_absent(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        retained = [
            row
            for row in read_csv_rows(path)
            if row["provider"] not in {"usda_psd", "usda_esr"}
        ]
        write_csv(
            path,
            CATEGORY_FIELDS["source_log"],
            retained,
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "USDA agriculture capability status missing.*usda_esr.*usda_psd",
        ):
            validate_staged_week(self.root, self.window)

    def test_usda_capability_status_requires_both_independent_subsections(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="usda_psd",
            category="commodity_fundamentals",
            requiredness="optional",
            status="NOT_CONFIGURED",
            observations="0",
            as_of_date="2026-08-09",
            source="USDA Foreign Agricultural Service",
            source_url="https://api.fas.usda.gov/",
        )
        retained = [
            existing
            for existing in read_csv_rows(path)
            if existing["provider"] not in {"usda_psd", "usda_esr"}
        ]
        write_csv(path, CATEGORY_FIELDS["source_log"], [*retained, row])

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "USDA agriculture capability status missing.*usda_esr",
        ):
            validate_staged_week(self.root, self.window)

    def test_active_usda_subsections_require_each_configured_commodity_code(self):
        fundamentals = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        write_csv(
            fundamentals,
            CATEGORY_FIELDS["commodity_fundamentals"],
            [
                row
                for row in read_csv_rows(fundamentals)
                if not (
                    row["metric_code"].startswith("usda_psd_")
                    and row["commodity_code"] == "SOYBEANS"
                )
            ],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "usda_psd.*missing configured commodity_code.*SOYBEANS",
        ):
            validate_staged_week(self.root, self.window)

    def test_usda_coverage_uses_the_configured_code_family_mapping(self):
        config = json.loads(PRODUCTION_CONFIG_PATH.read_text(encoding="utf-8"))
        for rows in (
            config["macro"],
            config["context"]["cftc_contracts"],
            config["context"]["usda_psd"],
            config["context"]["usda_esr"],
            config["commodity_research"]["universe"],
            config["commodity_research"]["facts"],
        ):
            for row in rows:
                if row.get("commodity_code") == "CORN":
                    row["commodity_family"] = "softs"
        config_path = Path(self.temporary.name) / "corn-softs-config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        alternate_registry = {
            **V2_COMMODITY_UNIVERSE,
            "CORN": "softs",
        }
        write_complete_v2_release_fixture(
            self.outputs,
            config_path=config_path,
            expected_registry=alternate_registry,
        )
        corn_rows = [
            row
            for row in read_csv_rows(
                self.outputs["weekly_context"] / "commodity_fundamentals.csv"
            )
            if row["metric_code"].startswith(("usda_psd_corn_", "usda_esr_corn_"))
        ]
        self.assertTrue(corn_rows)
        self.assertEqual(
            {row["commodity_family"] for row in corn_rows},
            {"softs"},
        )

        with patch("pipeline.internal.common.DEFAULT_CONFIG_PATH", config_path):
            validate_staged_week(self.root, self.window)

        real_load_config_rows = weekly_release_module.load_config_rows

        def hardcoded_production_family(section: str):
            rows = real_load_config_rows(section)
            if section not in {"context.usda_psd", "context.usda_esr"}:
                return rows
            return [
                {
                    **row,
                    "commodity_family": (
                        "grains_oilseeds"
                        if row.get("commodity_code") == "CORN"
                        else row.get("commodity_family")
                    ),
                }
                for row in rows
            ]

        with patch("pipeline.internal.common.DEFAULT_CONFIG_PATH", config_path):
            with patch.object(
                weekly_release_module,
                "load_config_rows",
                side_effect=hardcoded_production_family,
            ):
                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    r"usda_(?:psd|esr).*CORN.*commodity_family.*grains_oilseeds",
                ):
                    validate_staged_week(self.root, self.window)

    def test_usda_coverage_rejects_a_wrong_family_for_a_configured_code(self):
        path = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        rows = read_csv_rows(path)
        target = next(
            row
            for row in rows
            if row["metric_code"].startswith("usda_psd_corn_")
        )
        target["commodity_family"] = "softs"
        write_csv(
            path,
            CATEGORY_FIELDS["commodity_fundamentals"],
            rows,
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "usda_psd.*CORN.*commodity_family.*grains_oilseeds",
        ):
            validate_staged_week(self.root, self.window)

    def test_active_usda_rows_require_exact_codes_and_official_fas_provenance(self):
        path = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        rows = read_csv_rows(path)
        target = next(
            row
            for row in rows
            if row["metric_code"].startswith("usda_psd_corn_")
        )
        target["source_url"] = "https://example.test/not-usda"
        write_csv(
            path,
            CATEGORY_FIELDS["commodity_fundamentals"],
            rows,
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "USDA row requires official FAS provenance",
        ):
            validate_staged_week(self.root, self.window)

    def test_active_eia_families_each_require_a_physical_fundamental_row(self):
        fundamentals = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        write_csv(
            fundamentals,
            CATEGORY_FIELDS["commodity_fundamentals"],
            [
                row
                for row in read_csv_rows(fundamentals)
                if not (
                    row["source"] == "U.S. Energy Information Administration"
                    and row["commodity_family"] == "refined_products"
                )
            ],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "eia_refined_products.*physical fundamental",
        ):
            validate_staged_week(self.root, self.window)

    def test_unrelated_same_family_row_cannot_satisfy_active_eia_coverage(self):
        fundamentals = self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        unrelated = fixture_row(
            CATEGORY_FIELDS["commodity_fundamentals"],
            as_of_date="2026-08-07",
            commodity_code="NATGAS_HH",
            commodity_family="natural_gas",
            metric_role="physical_fundamental",
            measurement_kind="inventory",
            participant_class="",
            known_as_of="",
            reference_period="2026-08-07",
            source="Unrelated natural gas source",
            source_url="https://example.test/natural-gas",
        )
        write_csv(
            fundamentals,
            CATEGORY_FIELDS["commodity_fundamentals"],
            [
                row
                for row in read_csv_rows(fundamentals)
                if not (
                    row["source"] == "U.S. Energy Information Administration"
                    and row["commodity_family"] == "natural_gas"
                )
            ] + [unrelated],
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "eia_natural_gas.*official EIA physical fundamental",
        ):
            validate_staged_week(self.root, self.window)

    def test_accepts_insufficient_data_from_an_optional_context_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fred_financial_conditions",
            category="financial_conditions",
            requiredness="optional",
            status="INSUFFICIENT_DATA",
            as_of_date="2026-08-09",
        )
        merge_context_status_rows(self.outputs, [row])

        validate_staged_week(self.root, self.window)

    def test_accepts_point_in_time_unavailable_from_registered_optional_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="sec_company_events",
            category="company_events",
            requiredness="optional",
            status="POINT_IN_TIME_UNAVAILABLE",
            observations="0",
            as_of_date="2026-08-09",
        )
        merge_context_status_rows(self.outputs, [row])

        validate_staged_week(self.root, self.window)

    def test_rejects_point_in_time_unavailable_from_same_allowlisted_required_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="sec_company_events",
            category="company_events",
            requiredness="required",
            status="POINT_IN_TIME_UNAVAILABLE",
            observations="0",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "POINT_IN_TIME_UNAVAILABLE",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_an_unknown_current_context_requiredness(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fixture",
            category="market_internals",
            requiredness="best-effort",
            status="OK",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(ReleaseValidationError, "requiredness"):
            validate_staged_week(self.root, self.window)

    def test_rejects_current_context_latest_known_as_of_after_target_sunday(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fixture",
            category="market_internals",
            latest_known_as_of="2026-08-10T00:00:00+08:00",
            status="OK",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "latest_known_as_of.*exceeds",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_invalid_current_context_latest_known_as_of(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        for latest_known_as_of in (
            "not-a-timestamp",
            "2026-08-09T12:00:00",
        ):
            with self.subTest(latest_known_as_of=latest_known_as_of):
                row = fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider="fixture",
                    category="market_internals",
                    latest_known_as_of=latest_known_as_of,
                    status="OK",
                    as_of_date="2026-08-09",
                )
                write_csv(
                    path,
                    CATEGORY_FIELDS["source_log"],
                    [
                        row,
                        *usda_source_rows(
                            status="NOT_CONFIGURED",
                            requiredness="optional",
                        ),
                    ],
                )

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    "latest_known_as_of.*UTC offset",
                ):
                    validate_staged_week(self.root, self.window)

    def test_rejects_non_finite_or_non_numeric_current_context_freshness_days(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        for freshness_days in ("NaN", "Infinity", "not-a-number"):
            with self.subTest(freshness_days=freshness_days):
                row = fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider="fixture",
                    category="market_internals",
                    freshness_days=freshness_days,
                    status="OK",
                    as_of_date="2026-08-09",
                )
                write_csv(path, CATEGORY_FIELDS["source_log"], [row])

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    "freshness_days.*finite",
                ):
                    validate_staged_week(self.root, self.window)

    def test_accepts_blank_current_context_freshness_and_latest_known_as_of(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fixture",
            category="market_internals",
            freshness_days="",
            latest_known_as_of="",
            status="OK",
            as_of_date="2026-08-09",
        )
        merge_context_status_rows(self.outputs, [row])

        validate_staged_week(self.root, self.window)

    def test_accepts_finite_freshness_and_eligible_latest_known_as_of(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="fixture",
            category="market_internals",
            freshness_days="7",
            latest_known_as_of="2026-08-09T23:59:59+08:00",
            status="OK",
            as_of_date="2026-08-09",
        )
        merge_context_status_rows(self.outputs, [row])

        validate_staged_week(self.root, self.window)

    def test_rejects_point_in_time_unavailable_from_a_required_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="bls_economic_releases",
            category="economic_releases",
            requiredness="required",
            status="POINT_IN_TIME_UNAVAILABLE",
            observations="0",
            as_of_date="2026-08-09",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "POINT_IN_TIME_UNAVAILABLE",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_fetch_failed_from_a_registered_optional_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        for provider, category in (
            ("sec_company_events", "company_events"),
            ("fred_financial_conditions", "financial_conditions"),
        ):
            with self.subTest(provider=provider):
                row = fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider=provider,
                    category=category,
                    requiredness="optional",
                    status="FETCH_FAILED",
                    observations="0",
                    as_of_date="2026-08-09",
                )
                write_csv(path, CATEGORY_FIELDS["source_log"], [row])

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    "FETCH_FAILED",
                ):
                    validate_staged_week(self.root, self.window)

    def test_accepts_fetch_failed_from_optional_yahoo_volatility_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="yahoo_volatility_signals",
            category="financial_conditions",
            requiredness="optional",
            status="FETCH_FAILED",
            observations="0",
            as_of_date="2026-08-09",
            source="Yahoo Finance (Cboe indices)",
            source_url="https://finance.yahoo.com/",
        )
        merge_context_status_rows(self.outputs, [row])

        validate_staged_week(self.root, self.window)

    def test_accepts_metal_supplemental_failures_without_weakening_core_coverage(self):
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="comex_gold_stocks",
            category="commodity_fundamentals",
            requiredness="optional",
            status="FETCH_FAILED",
            observations="0",
            as_of_date="2026-08-09",
            source="CME Group",
            source_url="https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls",
        )
        merge_context_status_rows(self.outputs, [row])

        validate_staged_week(self.root, self.window)

    def test_metal_supplemental_failure_cannot_replace_world_bank_price_or_cftc(self):
        for missing, expected in (
            ("price", r"configured macro price.*COMEX_GOLD"),
            ("positioning", r"CFTC contract identity.*088691.*GOLD_COMEX"),
        ):
            with self.subTest(missing=missing):
                write_complete_v2_release_fixture(self.outputs)
                if missing == "price":
                    path = self.outputs["macro_assets"] / "commodities.csv"
                    rows = [
                        row
                        for row in read_csv_rows(path)
                        if row["series_code"] != "COMEX_GOLD"
                    ]
                    fields = MACRO_V3_FIELDS
                else:
                    path = self.outputs["weekly_context"] / "positioning_flows.csv"
                    rows = [
                        row
                        for row in read_csv_rows(path)
                        if row["commodity_code"] != "GOLD_COMEX"
                    ]
                    fields = CATEGORY_FIELDS["positioning_flows"]
                write_csv(path, fields, rows)

                with self.assertRaisesRegex(ReleaseValidationError, expected):
                    validate_staged_week(self.root, self.window)

    def test_insufficient_configured_world_bank_row_does_not_satisfy_core_coverage(self):
        path = self.outputs["macro_assets"] / "commodities.csv"
        rows = read_csv_rows(path)
        target = next(row for row in rows if row["series_code"] == "COMEX_GOLD")
        target.update(qc_flag="INSUFFICIENT_DATA", latest_value="")
        write_csv(path, MACRO_V3_FIELDS, rows)

        with self.assertRaisesRegex(
            ReleaseValidationError,
            r"configured macro price.*COMEX_GOLD",
        ):
            validate_staged_week(self.root, self.window)

    def test_blank_insufficient_cftc_open_interest_does_not_satisfy_core_coverage(self):
        path = self.outputs["weekly_context"] / "positioning_flows.csv"
        rows = read_csv_rows(path)
        target = next(
            row
            for row in rows
            if row["metric_code"] == "GOLD_COMEX_open_interest"
        )
        target.update(as_of_date="", value="", qc_flag="INSUFFICIENT_DATA")
        write_csv(path, CATEGORY_FIELDS["positioning_flows"], rows)

        with self.assertRaisesRegex(
            ReleaseValidationError,
            r"CFTC contract identity.*088691.*GOLD_COMEX",
        ):
            validate_staged_week(self.root, self.window)

    def test_rejects_fetch_failed_from_required_yahoo_volatility_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        row = fixture_row(
            CATEGORY_FIELDS["source_log"],
            provider="yahoo_volatility_signals",
            category="financial_conditions",
            requiredness="required",
            status="FETCH_FAILED",
            observations="0",
            as_of_date="2026-08-09",
            source="Yahoo Finance (Cboe indices)",
            source_url="https://finance.yahoo.com/",
        )
        write_csv(path, CATEGORY_FIELDS["source_log"], [row])

        with self.assertRaisesRegex(ReleaseValidationError, "FETCH_FAILED"):
            validate_staged_week(self.root, self.window)

    def test_calculated_curve_requires_both_http_sourced_dependencies(self):
        path = self.outputs["macro_assets"] / "fixed_income.csv"
        calculated_reference = (
            "calculated:UST10Y-UST2Y (shared Treasury observation dates)"
        )
        rows = [
            fixture_row(MACRO_V3_FIELDS, series_code="UST10Y"),
            fixture_row(
                MACRO_V3_FIELDS,
                series_code="UST10Y2Y",
                provider="calculated",
                source_url=calculated_reference,
            ),
        ]
        write_csv(path, MACRO_V3_FIELDS, rows)

        with self.assertRaisesRegex(ReleaseValidationError, "UST2Y"):
            validate_staged_week(self.root, self.window)

    def test_accepts_every_registered_treasury_calculation(self):
        path = self.outputs["macro_assets"] / "fixed_income.csv"
        rows = [
            fixture_row(MACRO_V3_FIELDS, series_code=code)
            for code in (
                "UST2Y",
                "UST5Y",
                "UST10Y",
                "UST_REAL5Y",
                "UST_REAL10Y",
            )
        ]
        rows.extend(
            [
                fixture_row(
                    MACRO_V3_FIELDS,
                    series_code="UST10Y2Y",
                    provider="calculated",
                    source_url=(
                        "calculated:UST10Y-UST2Y "
                        "(shared Treasury observation dates)"
                    ),
                ),
                fixture_row(
                    MACRO_V3_FIELDS,
                    series_code="US_BE5Y",
                    provider="calculated",
                    source_url=(
                        "calculated:UST5Y-UST_REAL5Y "
                        "(shared Treasury observation dates)"
                    ),
                ),
                fixture_row(
                    MACRO_V3_FIELDS,
                    series_code="US_BE10Y",
                    provider="calculated",
                    source_url=(
                        "calculated:UST10Y-UST_REAL10Y "
                        "(shared Treasury observation dates)"
                    ),
                ),
                fixture_row(
                    MACRO_V3_FIELDS,
                    series_code="US_5Y5Y",
                    provider="calculated",
                    source_url=(
                        "calculated:5Y5Y from US_BE5Y and US_BE10Y "
                        "(shared Treasury observation dates)"
                    ),
                ),
            ]
        )
        write_csv(path, MACRO_V3_FIELDS, rows)

        manifest = validate_staged_week(self.root, self.window)

        entry = next(
            item
            for item in manifest["files"]
            if item["path"].endswith("fixed_income.csv")
        )
        self.assertEqual(entry["rows"], len(rows))

    def test_each_new_treasury_calculation_requires_its_dependency(self):
        path = self.outputs["macro_assets"] / "fixed_income.csv"
        observed_rows = [
            fixture_row(MACRO_V3_FIELDS, series_code=code)
            for code in (
                "UST2Y",
                "UST5Y",
                "UST10Y",
                "UST_REAL5Y",
                "UST_REAL10Y",
            )
        ]
        calculated_rows = [
            fixture_row(
                MACRO_V3_FIELDS,
                series_code="UST10Y2Y",
                provider="calculated",
                source_url=(
                    "calculated:UST10Y-UST2Y "
                    "(shared Treasury observation dates)"
                ),
            ),
            fixture_row(
                MACRO_V3_FIELDS,
                series_code="US_BE5Y",
                provider="calculated",
                source_url=(
                    "calculated:UST5Y-UST_REAL5Y "
                    "(shared Treasury observation dates)"
                ),
            ),
            fixture_row(
                MACRO_V3_FIELDS,
                series_code="US_BE10Y",
                provider="calculated",
                source_url=(
                    "calculated:UST10Y-UST_REAL10Y "
                    "(shared Treasury observation dates)"
                ),
            ),
            fixture_row(
                MACRO_V3_FIELDS,
                series_code="US_5Y5Y",
                provider="calculated",
                source_url=(
                    "calculated:5Y5Y from US_BE5Y and US_BE10Y "
                    "(shared Treasury observation dates)"
                ),
            ),
        ]
        cases = (
            ("US_BE5Y", "UST_REAL5Y"),
            ("US_BE10Y", "UST_REAL10Y"),
            ("US_5Y5Y", "US_BE10Y"),
        )

        for series_code, missing_dependency in cases:
            with self.subTest(series_code=series_code):
                rows = [
                    row
                    for row in observed_rows + calculated_rows
                    if row["series_code"] != missing_dependency
                ]
                write_csv(path, MACRO_V3_FIELDS, rows)

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    missing_dependency,
                ):
                    validate_staged_week(self.root, self.window)

    def test_rejects_a_non_http_source_reference(self):
        path = self.outputs["gics_sectors"] / "03_gics_sectors.csv"
        row = fixture_row(
            GICS_FIELDS,
            gics_sector_code="GICS",
            source_url="not-a-url",
        )
        write_csv(path, GICS_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "HTTP\(S\)"):
            validate_staged_week(self.root, self.window)

    def test_rejects_a_non_canonical_date(self):
        path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        row = fixture_row(INDEX_FIELDS, ticker="INDEX", latest_date="2026-8-7")
        write_csv(path, INDEX_FIELDS, [row])

        with self.assertRaisesRegex(ReleaseValidationError, "YYYY-MM-DD"):
            validate_staged_week(self.root, self.window)

    def test_accepts_standard_header_zero_row_optional_context_tables(self):
        manifest = validate_staged_week(self.root, self.window)

        context_files = {
            item["path"]: item["rows"]
            for item in manifest["files"]
            if "capital_weekly_context_20260809" in item["path"]
        }
        self.assertEqual(context_files["capital_weekly_context_20260809/events.csv"], 0)
        self.assertEqual(
            context_files[
                "capital_weekly_context_20260809/commodity_fundamentals.csv"
            ],
            len(
                read_csv_rows(
                    self.outputs["weekly_context"]
                    / "commodity_fundamentals.csv"
                )
            ),
        )
        json.dumps(manifest, allow_nan=False)

    def test_manifest_records_complete_week_identity_and_exact_file_integrity(self):
        raw_file = self.outputs["equity_indices"] / "raw" / "fixture.txt"
        raw_file.parent.mkdir()
        raw_file.write_text("raw fixture", encoding="utf-8")
        nested_manifest = raw_file.with_name("manifest.json")
        nested_manifest.write_text('{"kind": "provider"}', encoding="utf-8")

        manifest = validate_staged_week(self.root, self.window)

        self.assertEqual(manifest["manifest_schema_version"], 3)
        self.assertEqual(manifest["dataset_contract_version"], 6)
        self.assertEqual(manifest["publication_mode"], "coordinated")
        self.assertEqual(manifest["week_start"], "2026-08-03")
        self.assertEqual(manifest["week_end"], "2026-08-09")
        self.assertEqual(manifest["timezone"], "Asia/Hong_Kong")
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(manifest["failures"], [])
        self.assertEqual(len(manifest["capabilities"]), 79)
        self.assertEqual(
            len({item["capability_id"] for item in manifest["capabilities"]}),
            79,
        )
        self.assertTrue(
            all(
                set(item) == {
                    "capability_id", "module", "label", "status", "reason",
                    "proxy", "evidence_files",
                }
                for item in manifest["capabilities"]
            )
        )
        self.assertFalse(any("value" in item for item in manifest["capabilities"]))
        self.assertTrue(manifest["coordinator_version"])
        self.assertEqual(len(manifest["pipelines"]), 5)
        for pipeline in manifest["pipelines"]:
            self.assertEqual(
                set(pipeline),
                {
                    "name",
                    "status",
                    "started_at",
                    "finished_at",
                    "elapsed_ms",
                },
            )
            self.assertEqual(pipeline["status"], "validated")
            self.assertIsNone(pipeline["started_at"])
            self.assertIsNone(pipeline["finished_at"])
            self.assertIsNone(pipeline["elapsed_ms"])
        index_path = self.outputs["equity_indices"] / "02_equity_indices.csv"
        index_entry = next(
            item
            for item in manifest["files"]
            if item["path"].endswith("/02_equity_indices.csv")
        )
        self.assertEqual(index_entry["rows"], 1)
        self.assertEqual(
            index_entry["sha256"],
            hashlib.sha256(index_path.read_bytes()).hexdigest(),
        )
        raw_entry = next(
            item for item in manifest["files"] if item["path"].endswith("raw/fixture.txt")
        )
        self.assertIsNone(raw_entry["rows"])
        nested_manifest_path = (
            "capital_weekly_equity_indices_python_20260809/raw/manifest.json"
        )
        entries_by_path = {item["path"]: item for item in manifest["files"]}
        self.assertIn(nested_manifest_path, entries_by_path)
        nested_manifest_entry = entries_by_path[nested_manifest_path]
        self.assertIsNone(nested_manifest_entry["rows"])
        snapshot_entry = next(
            item
            for item in manifest["files"]
            if item["path"].endswith("equity_indices_snapshot.json")
        )
        self.assertIsNone(snapshot_entry["rows"])

    def test_manifest_row_counts_ignore_blank_csv_records(self):
        events = self.outputs["weekly_context"] / "events.csv"
        events.write_text(
            events.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )

        manifest = validate_staged_week(self.root, self.window)

        events_entry = next(
            item
            for item in manifest["files"]
            if item["path"].endswith("/events.csv")
        )
        self.assertEqual(events_entry["rows"], 0)

    def test_current_contract_rejects_a_missing_economic_releases_table(self):
        (self.outputs["weekly_context"] / "economic_releases.csv").unlink()

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "economic_releases.csv",
        ):
            validate_staged_week(self.root, self.window)

    def test_legacy_contract_rejects_current_economic_releases_table(self):
        with self.assertRaisesRegex(
            ReleaseValidationError,
            "economic_releases.csv.*legacy dataset contract",
        ):
            validate_staged_week(
                self.root,
                self.window,
                dataset_contract_version=1,
            )

    def test_legacy_contract_infers_optional_status_from_identity(self):
        context = self.outputs["weekly_context"]
        (context / "economic_releases.csv").unlink()
        write_csv(
            context / "source_log.csv",
            LEGACY_CONTEXT_SOURCE_LOG_FIELDS,
            [
                fixture_row(
                    LEGACY_CONTEXT_SOURCE_LOG_FIELDS,
                    provider="sec_company_events",
                    category="company_events",
                    status="POINT_IN_TIME_UNAVAILABLE",
                    observations="0",
                    as_of_date="2026-08-09",
                )
            ],
        )

        validate_staged_week(
            self.root,
            self.window,
            dataset_contract_version=1,
        )

    def test_legacy_contract_rejects_expanded_context_source_log(self):
        (self.outputs["weekly_context"] / "economic_releases.csv").unlink()

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "source_log.csv.*legacy dataset contract",
        ):
            validate_staged_week(
                self.root,
                self.window,
                dataset_contract_version=1,
            )


    def test_current_contract_requires_every_fixed_required_context_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        write_csv(
            path,
            CATEGORY_FIELDS["source_log"],
            [
                fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider="fixture",
                    category="market_internals",
                )
            ],
            complete_context_log=False,
        )

        with self.assertRaisesRegex(
            ReleaseValidationError,
            "missing required context provider.*bea_economic_releases",
        ):
            validate_staged_week(self.root, self.window)

    def test_accepts_registered_optional_public_provider_gaps(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        base_rows = read_csv_rows(path)
        cases = (
            ("yahoo_market_state", "market_internals", "FETCH_FAILED", "public"),
            ("hkex_stock_connect_flows", "fund_flows", "FETCH_FAILED", "public"),
            ("ishares_ivv_fund", "fund_flows", "POINT_IN_TIME_UNAVAILABLE", "public"),
            ("eia_commodities", "commodity_fundamentals", "FETCH_FAILED", "public"),
            ("ism_manufacturing_pmi", "economic_releases", "UNAVAILABLE_LICENSED", "licensed"),
        )
        for provider, category, status, source_tier in cases:
            with self.subTest(provider=provider, status=status):
                row = fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider=provider,
                    category=category,
                    source_tier=source_tier,
                    requiredness="optional",
                    status=status,
                    observations="0",
                    as_of_date="2026-08-09",
                )
                write_csv(
                    path,
                    CATEGORY_FIELDS["source_log"],
                    [
                        *(
                            existing
                            for existing in base_rows
                            if existing["provider"] != provider
                        ),
                        row,
                    ],
                )

                validate_staged_week(self.root, self.window)

    def test_rejects_unavailable_licensed_for_unknown_or_required_provider(self):
        path = self.outputs["weekly_context"] / "source_log.csv"
        cases = (
            ("unknown_provider", "optional", "licensed"),
            ("ism_manufacturing_pmi", "required", "licensed"),
            ("ism_manufacturing_pmi", "optional", "public"),
        )
        for provider, requiredness, source_tier in cases:
            with self.subTest(
                provider=provider,
                requiredness=requiredness,
                source_tier=source_tier,
            ):
                row = fixture_row(
                    CATEGORY_FIELDS["source_log"],
                    provider=provider,
                    category="economic_releases",
                    source_tier=source_tier,
                    requiredness=requiredness,
                    status="UNAVAILABLE_LICENSED",
                    observations="0",
                    as_of_date="2026-08-09",
                )
                write_csv(path, CATEGORY_FIELDS["source_log"], [row])

                with self.assertRaisesRegex(
                    ReleaseValidationError,
                    "UNAVAILABLE_LICENSED",
                ):
                    validate_staged_week(self.root, self.window)


class CommodityResearchV2ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "week_20260803-20260809"
        self.window = latest_finished_week(
            datetime(2026, 8, 11, 10, 0, tzinfo=ZoneInfo("Asia/Hong_Kong"))
        )
        self.outputs = write_valid_staged_week(self.root, self.window)
        self.tables = write_complete_v2_release_fixture(self.outputs)

    def _validate(self) -> dict:
        return validate_staged_week(
            self.root,
            self.window,
            dataset_contract_version=6,
        )

    def _reset(self) -> None:
        self.tables = write_complete_v2_release_fixture(self.outputs)

    def _rewrite(self, table: str, rows: list[dict]) -> None:
        locations = {
            "price": (
                self.outputs["macro_assets"] / "commodity_price_history.csv",
                PRICE_HISTORY_FIELDS,
            ),
            "metric": (
                self.outputs["weekly_context"] / "commodity_metric_history.csv",
                METRIC_HISTORY_FIELDS,
            ),
            "facts": (
                self.outputs["weekly_context"] / "commodity_research_facts.csv",
                RESEARCH_FACT_FIELDS,
            ),
        }
        path, fields = locations[table]
        write_csv(path, fields, rows)

    def _non_ok_context_row(self) -> dict:
        return fixture_row(
            CATEGORY_FIELDS["commodity_fundamentals"],
            as_of_date="2026-08-06",
            category="commodity_fundamentals",
            market="United States",
            metric_code="eia_crude_stocks_ex_spr_change",
            value="1",
            unit="MBBL",
            source="U.S. Energy Information Administration",
            source_url="https://api.eia.gov/v2/petroleum/sum/sndw/data/",
            commodity_code="WTI",
            commodity_family="refined_products",
            metric_role="physical_fundamental",
            measurement_kind="inventory",
            participant_class="",
            known_as_of="2026-08-07T12:00:00Z",
            reference_period="2026-08-06",
            qc_flag="INSUFFICIENT_DATA",
        )

    def test_contract_six_registers_exact_additive_tables(self):
        version_five = {
            (spec.pipeline, spec.filename)
            for spec in release_datasets_for_contract(5)
        }
        version_six = {
            (spec.pipeline, spec.filename)
            for spec in release_datasets_for_contract(6)
        }

        self.assertEqual(
            version_six - version_five,
            {
                ("macro_assets", "commodity_price_history.csv"),
                ("weekly_context", "commodity_metric_history.csv"),
                ("weekly_context", "commodity_research_facts.csv"),
            },
        )

    def test_complete_contract_six_fixture_has_exact_universe_and_fact_inputs(self):
        manifest = self._validate()

        self.assertEqual(manifest["dataset_contract_version"], 6)
        all_history = [
            *self.tables["commodity_price_history"],
            *self.tables["commodity_metric_history"],
        ]
        self.assertEqual(
            {row["commodity_code"] for row in all_history},
            set(V2_COMMODITY_UNIVERSE),
        )
        self.assertEqual(
            {row["commodity_family"] for row in all_history},
            set(V2_COMMODITY_UNIVERSE.values()),
        )
        published_ids = {row["record_id"] for row in all_history}
        facts = self.tables["commodity_research_facts"]
        self.assertEqual(len(facts), 8)
        for fact in facts:
            with self.subTest(fact_code=fact["fact_code"]):
                self.assertTrue(fact["input_record_ids"])
                self.assertLessEqual(set(fact["input_record_ids"]), published_ids)

    def test_price_status_reconciles_raw_count_to_configured_history_limit(self):
        self._validate()

        gold_history = [
            row
            for row in self.tables["commodity_price_history"]
            if row["series_code"] == "COMEX_GOLD"
        ]
        status_rows = read_csv_rows(
            self.outputs["macro_assets"] / "source_log.csv"
        )
        gold_status = next(
            row for row in status_rows if row["series_code"] == "COMEX_GOLD"
        )
        self.assertEqual(len(gold_history), 84)
        self.assertEqual(gold_status["observations"], "86")

    def test_contract_six_preserves_valid_non_ok_tagged_context_row(self):
        context_path = (
            self.outputs["weekly_context"] / "commodity_fundamentals.csv"
        )
        rows = read_csv_rows(context_path)
        rows.append(self._non_ok_context_row())
        write_csv(
            context_path,
            CATEGORY_FIELDS["commodity_fundamentals"],
            rows,
        )

        self._validate()

    def test_price_status_rejects_invalid_bounded_count_relationships(self):
        cases = (
            (
                "price_status_undercount",
                r"COMEX_GOLD.*raw 83.*expected 83.*published 84",
            ),
            (
                "price_status_premature_truncation",
                r"COMEX_GOLD.*raw 86.*expected 84.*published 83",
            ),
            (
                "price_history_over_published",
                r"COMEX_GOLD.*raw 86.*expected 84.*published 85",
            ),
            (
                "price_status_nonintegral",
                r"COMEX_GOLD.*status observations.*canonical integer",
            ),
            (
                "price_status_non_ok_residual",
                r"source_log.csv.*unacceptable status.*FETCH_FAILED",
            ),
        )
        for mutation, expected in cases:
            with self.subTest(mutation=mutation):
                self._reset()
                self._apply_mutation(mutation)
                with self.assertRaisesRegex(ReleaseValidationError, expected):
                    self._validate()

    def test_non_ok_tagged_context_rows_still_validate_identity_and_provenance(self):
        cases = (
            (
                "non_ok_unknown_metric",
                r"metric identity is not registered.*rogue_non_ok_metric",
            ),
            (
                "non_ok_corrupt_provenance",
                r"eia_refined_products.*business row.*source must match provider",
            ),
        )
        for mutation, expected in cases:
            with self.subTest(mutation=mutation):
                self._reset()
                self._apply_mutation(mutation)
                with self.assertRaisesRegex(ReleaseValidationError, expected):
                    self._validate()

    def test_non_ok_tagged_context_rows_match_exact_metric_descriptor(self):
        cases = (
            (
                "non_ok_descriptor_code",
                r"commodity context base row.*commodity_code.*eia_crude_stocks_ex_spr_change",
            ),
            (
                "non_ok_descriptor_family",
                r"context commodity base row WTI family natural_gas.*refined_products",
            ),
            (
                "non_ok_descriptor_role",
                r"commodity context base row.*metric_role.*eia_crude_stocks_ex_spr_change",
            ),
            (
                "non_ok_descriptor_kind",
                r"commodity context base row.*measurement_kind.*eia_crude_stocks_ex_spr_change",
            ),
            (
                "non_ok_descriptor_participant",
                r"commodity context base row.*participant_class.*eia_crude_stocks_ex_spr_change",
            ),
            (
                "non_ok_descriptor_unit",
                r"commodity context base row.*unit.*eia_crude_stocks_ex_spr_change",
            ),
        )
        for mutation, expected in cases:
            with self.subTest(mutation=mutation):
                self._reset()
                self._apply_mutation(mutation)
                with self.assertRaisesRegex(ReleaseValidationError, expected):
                    self._validate()

    def test_contract_six_rejects_table_driven_cross_table_mutations(self):
        cases = (
            ("code_family", r"code-family.*WTI.*refined_products"),
            ("record_id", r"record_id.*commodity price history"),
            ("duplicate_identity", r"duplicate.*semantic identity"),
            ("observation_order", r"history ordering.*WTI"),
            ("history_limit", r"(?:history limit|bounded price history).*daily.*400"),
            ("future_known_as_of", r"known_as_of.*cutoff"),
            ("naive_known_as_of", r"known_as_of.*UTC Z"),
            ("nonfinite_value", r"value must be finite"),
            ("source_host", r"official source host.*worldbank.org"),
            ("formula_id", r"formula_id.*wti_absolute_change"),
            ("formula_version", r"formula_version.*wti_absolute_change"),
            ("orphan_input", r"orphan input_record_id"),
            ("mixed_vintage", r"same USDA vintage"),
            ("provider_residual", r"comex_gold_stocks.*zero V2 rows"),
            ("unregistered_metric", r"metric identity is not registered.*totally_unregistered_usda_metric"),
            ("status_observation_count", r"cftc_disaggregated.*observations.*208"),
            ("status_provenance", r"cftc_disaggregated.*status provenance"),
            ("price_status_observation_count", r"WTI.*OK status observations.*positive.*got 0"),
            ("price_status_provenance", r"WTI.*status provenance"),
            ("usda_evil_country", r"USDA PSD.*country.*evilcountry"),
            ("usda_wrong_reference_period", r"USDA PSD.*reference_period.*2026"),
            ("usda_wrong_market", r"USDA PSD.*market.*World"),
            ("base_macro_rogue", r"macro commodity base row.*ROGUE.*unregistered"),
            ("base_macro_family", r"configured macro price.*WTI"),
            ("base_context_rogue", r"context commodity base row.*ROGUE.*unregistered"),
            ("base_context_family", r"eia_refined_products.*eia_crude_stocks_ex_spr"),
            ("missing_configured_code", r"configured price history.*BRENT"),
            ("btc_inclusion", r"BTC_USD|digital_asset"),
            ("fact_value", r"formula output mismatch.*wti_absolute_change.*value"),
            ("wrong_resolving_input", r"formula output mismatch.*wti_absolute_change.*input_record_ids"),
        )
        for mutation, expected in cases:
            with self.subTest(mutation=mutation):
                self._reset()
                self._apply_mutation(mutation)
                with self.assertRaisesRegex(ReleaseValidationError, expected):
                    self._validate()

    def _apply_mutation(self, mutation: str) -> None:
        price_rows = read_csv_rows(
            self.outputs["macro_assets"] / "commodity_price_history.csv"
        )
        metric_rows = read_csv_rows(
            self.outputs["weekly_context"] / "commodity_metric_history.csv"
        )
        fact_rows = read_csv_rows(
            self.outputs["weekly_context"] / "commodity_research_facts.csv"
        )
        if mutation == "code_family":
            next(row for row in price_rows if row["series_code"] == "WTI")[
                "commodity_family"
            ] = "gold"
            self._rewrite("price", price_rows)
        elif mutation == "record_id":
            price_rows[0]["record_id"] = "0" * 64
            self._rewrite("price", price_rows)
        elif mutation == "duplicate_identity":
            duplicate = dict(price_rows[0])
            duplicate["record_id"] = "1" * 64
            price_rows.insert(1, duplicate)
            self._rewrite("price", price_rows)
        elif mutation == "observation_order":
            indices = [
                index for index, row in enumerate(price_rows)
                if row["series_code"] == "WTI"
            ]
            price_rows[indices[0]], price_rows[indices[1]] = (
                price_rows[indices[1]],
                price_rows[indices[0]],
            )
            self._rewrite("price", price_rows)
        elif mutation == "history_limit":
            config = json.loads(PRODUCTION_CONFIG_PATH.read_text(encoding="utf-8"))
            wti = next(row for row in config["macro"] if row["series_code"] == "WTI")
            occupied = {
                row["observation_date"] for row in price_rows
                if row["series_code"] == "WTI"
            }
            observation = date(2024, 1, 1)
            while sum(row["series_code"] == "WTI" for row in price_rows) <= 400:
                if observation.isoformat() not in occupied:
                    price_rows.append(_price_history_row(wti, observation, 50.0))
                observation += timedelta(days=1)
            price_rows.sort(key=lambda row: (
                row["commodity_code"], row["series_code"],
                row["observation_date"], row["known_as_of"], row["record_id"],
            ))
            self._rewrite("price", price_rows)
        elif mutation in {"future_known_as_of", "naive_known_as_of"}:
            row = price_rows[0]
            row["known_as_of"] = (
                "2026-08-10T00:00:00Z"
                if mutation == "future_known_as_of"
                else "2026-08-08T00:00:00"
            )
            self._rewrite("price", price_rows)
        elif mutation == "nonfinite_value":
            price_rows[0]["value"] = "NaN"
            self._rewrite("price", price_rows)
        elif mutation == "source_host":
            next(
                row for row in price_rows
                if row["series_code"] == "COMEX_GOLD"
            )["source_url"] = "https://notworldbank.org/prices.xlsx"
            self._rewrite("price", price_rows)
        elif mutation in {"formula_id", "formula_version"}:
            row = next(
                row for row in fact_rows
                if row["fact_code"] == "wti_absolute_change"
            )
            field = "formula_id" if mutation == "formula_id" else "formula_version"
            row[field] = "unregistered" if field == "formula_id" else "9.9.9"
            self._rewrite("facts", fact_rows)
        elif mutation == "orphan_input":
            row = fact_rows[0]
            inputs = ast.literal_eval(row["input_record_ids"])
            inputs[0] = "f" * 64
            row["input_record_ids"] = repr(inputs)
            self._rewrite("facts", fact_rows)
        elif mutation == "mixed_vintage":
            denominator = next(
                row for row in metric_rows
                if row["metric_code"]
                == "usda_psd_corn_00_2026_domestic_use"
            )
            old_id = denominator["record_id"]
            denominator["known_as_of"] = "2026-08-08T12:00:00Z"
            identity = {
                "code": denominator["commodity_code"],
                "known_as_of": denominator["known_as_of"],
                "measurement": denominator["measurement_kind"],
                "metric": denominator["metric_code"],
                "observation_date": denominator["observation_date"],
                "participant": denominator["participant_class"] or None,
                "reference_period": denominator["reference_period"] or None,
                "role": denominator["metric_role"],
            }
            denominator["record_id"] = fixture_stable_record_id(
                "commodity_metric_history", identity
            )
            fact = next(
                row for row in fact_rows
                if row["fact_code"] == "corn_world_2026_stock_to_use"
            )
            inputs = ast.literal_eval(fact["input_record_ids"])
            fact["input_record_ids"] = repr([
                denominator["record_id"] if value == old_id else value
                for value in inputs
            ])
            self._rewrite("metric", metric_rows)
            self._rewrite("facts", fact_rows)
        elif mutation == "provider_residual":
            config = json.loads(PRODUCTION_CONFIG_PATH.read_text(encoding="utf-8"))
            metal = next(
                row for row in config["context"]["metals"]
                if row["provider"] == "comex_gold_stocks"
            )
            base = fixture_row(
                CATEGORY_FIELDS["commodity_fundamentals"],
                as_of_date="2026-08-07",
                metric_code=metal["expected_metric_codes"][0],
                value="1",
                unit=metal["expected_unit"],
                source=metal["source"],
                source_url=metal["source_url"],
                commodity_code=metal["commodity_code"],
                commodity_family=metal["commodity_family"],
                metric_role="physical_fundamental",
                measurement_kind="inventory",
                participant_class="",
                known_as_of="2026-08-07T12:00:00Z",
                reference_period="2026-08-07",
            )
            metric_rows.append(_metric_history_row(base))
            metric_rows.sort(key=lambda row: (
                row["commodity_code"], row["metric_code"], row["metric_role"],
                row["measurement_kind"], row["participant_class"],
                row["observation_date"], row["known_as_of"], row["record_id"],
            ))
            self._rewrite("metric", metric_rows)
        elif mutation == "unregistered_metric":
            fundamentals_path = (
                self.outputs["weekly_context"] / "commodity_fundamentals.csv"
            )
            fundamental_rows = read_csv_rows(fundamentals_path)
            base = fixture_row(
                CATEGORY_FIELDS["commodity_fundamentals"],
                as_of_date="2026-08-07",
                category="commodity_fundamentals",
                market="World",
                metric_code="totally_unregistered_usda_metric",
                value="7",
                unit="made_up_native_unit",
                source="USDA Foreign Agricultural Service",
                source_url=(
                    "https://api.fas.usda.gov/api/psd/commodity/fixture/"
                    "world/year/2026"
                ),
                commodity_code="CORN",
                commodity_family="grains_oilseeds",
                metric_role="physical_fundamental",
                measurement_kind="supply",
                participant_class="",
                known_as_of="2026-08-07T12:00:00Z",
                reference_period="2026",
            )
            fundamental_rows.append(base)
            write_csv(
                fundamentals_path,
                CATEGORY_FIELDS["commodity_fundamentals"],
                fundamental_rows,
            )
            metric_rows.append(_metric_history_row(base))
            metric_rows.sort(key=lambda row: (
                row["commodity_code"], row["metric_code"], row["metric_role"],
                row["measurement_kind"], row["participant_class"],
                row["observation_date"], row["known_as_of"], row["record_id"],
            ))
            self._rewrite("metric", metric_rows)
            status_path = self.outputs["weekly_context"] / "source_log.csv"
            status_rows = read_csv_rows(status_path)
            psd_status = next(
                row for row in status_rows if row["provider"] == "usda_psd"
            )
            psd_status["observations"] = str(int(psd_status["observations"]) + 1)
            write_csv(status_path, CATEGORY_FIELDS["source_log"], status_rows)
        elif mutation in {"status_observation_count", "status_provenance"}:
            status_path = self.outputs["weekly_context"] / "source_log.csv"
            status_rows = read_csv_rows(status_path)
            status = next(
                row
                for row in status_rows
                if row["provider"] == "cftc_disaggregated"
            )
            if mutation == "status_observation_count":
                status["observations"] = "0"
            else:
                status["source"] = "Impostor"
                status["source_url"] = "https://example.com/resource/fixture"
            write_csv(status_path, CATEGORY_FIELDS["source_log"], status_rows)
        elif mutation in {
            "price_status_observation_count",
            "price_status_provenance",
            "price_status_undercount",
            "price_status_nonintegral",
            "price_status_non_ok_residual",
        }:
            status_path = self.outputs["macro_assets"] / "source_log.csv"
            status_rows = read_csv_rows(status_path)
            target_series = (
                "COMEX_GOLD"
                if mutation in {"price_status_undercount", "price_status_nonintegral"}
                else "WTI"
            )
            status = next(
                row for row in status_rows if row["series_code"] == target_series
            )
            if mutation == "price_status_observation_count":
                status["observations"] = "0"
            elif mutation == "price_status_undercount":
                status["observations"] = "83"
            elif mutation == "price_status_nonintegral":
                status["observations"] = "86.0"
            elif mutation == "price_status_non_ok_residual":
                status["status"] = "FETCH_FAILED"
                status["observations"] = "0"
            else:
                status["source"] = "Impostor"
                status["source_url"] = "https://example.com/prices"
            write_csv(status_path, MACRO_SOURCE_LOG_V3_FIELDS, status_rows)
        elif mutation in {
            "price_status_premature_truncation",
            "price_history_over_published",
        }:
            gold_rows = [
                row for row in price_rows if row["series_code"] == "COMEX_GOLD"
            ]
            if mutation == "price_status_premature_truncation":
                removed = gold_rows[0]
                price_rows = [
                    row for row in price_rows if row["record_id"] != removed["record_id"]
                ]
            else:
                config = json.loads(
                    PRODUCTION_CONFIG_PATH.read_text(encoding="utf-8")
                )
                gold = next(
                    row for row in config["macro"]
                    if row["series_code"] == "COMEX_GOLD"
                )
                price_rows.append(_price_history_row(
                    gold,
                    date(2019, 8, 7),
                    1,
                ))
            price_rows.sort(key=lambda row: (
                row["commodity_code"], row["series_code"],
                row["observation_date"], row["known_as_of"], row["record_id"],
            ))
            self._rewrite("price", price_rows)
        elif mutation in {
            "usda_evil_country",
            "usda_wrong_reference_period",
            "usda_wrong_market",
        }:
            fundamentals_path = (
                self.outputs["weekly_context"] / "commodity_fundamentals.csv"
            )
            fundamental_rows = read_csv_rows(fundamentals_path)
            base = next(
                row for row in fundamental_rows
                if row["metric_code"] == "usda_psd_corn_00_2026_ending_stocks"
            )
            original_metric_code = base["metric_code"]
            if mutation == "usda_evil_country":
                base["metric_code"] = (
                    "usda_psd_corn_evilcountry_2026_ending_stocks"
                )
            elif mutation == "usda_wrong_reference_period":
                base["reference_period"] = "2025"
            else:
                base["market"] = "Mars"
            write_csv(
                fundamentals_path,
                CATEGORY_FIELDS["commodity_fundamentals"],
                fundamental_rows,
            )
            if mutation != "usda_wrong_market":
                replacement = _metric_history_row(base)
                metric_rows = [
                    replacement if row["metric_code"] == original_metric_code else row
                    for row in metric_rows
                ]
                metric_rows.sort(key=lambda row: (
                    row["commodity_code"], row["metric_code"], row["metric_role"],
                    row["measurement_kind"], row["participant_class"],
                    row["observation_date"], row["known_as_of"], row["record_id"],
                ))
                self._rewrite("metric", metric_rows)
        elif mutation in {"base_macro_rogue", "base_macro_family"}:
            macro_path = self.outputs["macro_assets"] / "commodities.csv"
            macro_rows = read_csv_rows(macro_path)
            if mutation == "base_macro_rogue":
                macro_rows.append(fixture_row(
                    MACRO_FIELDS,
                    asset_class="commodity",
                    group="commodities",
                    series_code="ROGUE",
                    source="Impostor",
                    source_url="https://example.com/rogue",
                    commodity_code="ROGUE",
                    commodity_family="gold",
                    price_kind="official_cash",
                    known_as_of="2026-08-08T00:00:00Z",
                    latest_value="1",
                    qc_flag="OK",
                ))
            else:
                next(row for row in macro_rows if row["series_code"] == "WTI")[
                    "commodity_family"
                ] = "gold"
            write_csv(macro_path, MACRO_V3_FIELDS, macro_rows)
        elif mutation in {"base_context_rogue", "base_context_family"}:
            context_path = (
                self.outputs["weekly_context"] / "commodity_fundamentals.csv"
            )
            context_rows = read_csv_rows(context_path)
            if mutation == "base_context_rogue":
                context_rows.append(fixture_row(
                    CATEGORY_FIELDS["commodity_fundamentals"],
                    as_of_date="2026-08-07",
                    category="commodity_fundamentals",
                    market="World",
                    metric_code="rogue_metric",
                    value="1",
                    unit="fixture",
                    source="Impostor",
                    source_url="https://example.com/rogue",
                    commodity_code="ROGUE",
                    commodity_family="gold",
                    metric_role="physical_fundamental",
                    measurement_kind="inventory",
                    participant_class="",
                    known_as_of="2026-08-07T12:00:00Z",
                    reference_period="2026-08-07",
                    qc_flag="OK",
                ))
            else:
                next(
                    row for row in context_rows
                    if row["metric_code"] == "eia_crude_stocks_ex_spr"
                )["commodity_family"] = "gold"
            write_csv(
                context_path,
                CATEGORY_FIELDS["commodity_fundamentals"],
                context_rows,
            )
        elif mutation in {
            "non_ok_unknown_metric",
            "non_ok_corrupt_provenance",
            "non_ok_descriptor_code",
            "non_ok_descriptor_family",
            "non_ok_descriptor_role",
            "non_ok_descriptor_kind",
            "non_ok_descriptor_participant",
            "non_ok_descriptor_unit",
        }:
            context_path = (
                self.outputs["weekly_context"] / "commodity_fundamentals.csv"
            )
            context_rows = read_csv_rows(context_path)
            row = self._non_ok_context_row()
            if mutation == "non_ok_unknown_metric":
                row["metric_code"] = "rogue_non_ok_metric"
            elif mutation == "non_ok_corrupt_provenance":
                row["source"] = "Impostor"
                row["source_url"] = "https://example.com/not-eia"
            elif mutation == "non_ok_descriptor_code":
                row["commodity_code"] = "BRENT"
            elif mutation == "non_ok_descriptor_family":
                row["commodity_family"] = "natural_gas"
            elif mutation == "non_ok_descriptor_role":
                row["metric_role"] = "positioning"
            elif mutation == "non_ok_descriptor_kind":
                row["measurement_kind"] = "supply"
            elif mutation == "non_ok_descriptor_participant":
                row["participant_class"] = "producer"
            else:
                row["unit"] = "BBL"
            context_rows.append(row)
            write_csv(
                context_path,
                CATEGORY_FIELDS["commodity_fundamentals"],
                context_rows,
            )
        elif mutation == "missing_configured_code":
            price_rows = [
                row for row in price_rows if row["commodity_code"] != "BRENT"
            ]
            self._rewrite("price", price_rows)
        elif mutation == "btc_inclusion":
            btc = {
                "series_code": "BTC_USD",
                "commodity_code": "BTC_USD",
                "commodity_family": "digital_asset",
                "price_kind": "vendor_proxy",
                "level_unit": "usd_per_btc",
                "source": "Yahoo Finance chart API (public vendor proxy)",
                "source_url": "https://query2.finance.yahoo.com/v8/finance/chart/BTC-USD",
            }
            price_rows.append(_price_history_row(btc, date(2026, 8, 7), 1.0))
            self._rewrite("price", price_rows)
        elif mutation == "fact_value":
            fact = next(
                row for row in fact_rows
                if row["fact_code"] == "wti_absolute_change"
            )
            fact["value"] = str(float(fact["value"]) + 1.0)
            self._rewrite("facts", fact_rows)
        elif mutation == "wrong_resolving_input":
            fact = next(
                row for row in fact_rows
                if row["fact_code"] == "wti_absolute_change"
            )
            wti_rows = [
                row for row in price_rows if row["series_code"] == "WTI"
            ]
            inputs = ast.literal_eval(fact["input_record_ids"])
            wrong_id = wti_rows[0]["record_id"]
            self.assertNotIn(wrong_id, inputs)
            fact["input_record_ids"] = repr(sorted([wrong_id, inputs[-1]]))
            self._rewrite("facts", fact_rows)
        else:
            raise AssertionError(f"unknown mutation: {mutation}")

    def test_contract_six_rejects_duplicate_raw_universe_rows(self):
        document = json.loads(PRODUCTION_CONFIG_PATH.read_text(encoding="utf-8"))
        document["commodity_research"]["universe"].append(
            dict(document["commodity_research"]["universe"][0])
        )
        config_path = Path(self.temporary.name) / "duplicate-universe.json"
        config_path.write_text(json.dumps(document), encoding="utf-8")

        with patch("pipeline.internal.common.DEFAULT_CONFIG_PATH", config_path):
            with self.assertRaisesRegex(
                ReleaseValidationError,
                r"universe.*exact 19.*duplicate.*NATGAS_HH",
            ):
                self._validate()

    def test_contract_six_preserves_explicitly_noncommodity_base_rows(self):
        macro_path = self.outputs["macro_assets"] / "commodities.csv"
        macro_rows = read_csv_rows(macro_path)
        macro_rows.append(fixture_row(
            MACRO_FIELDS,
            asset_class="commodity",
            group="commodities",
            series_code="BTC_USD",
            provider="yahoo_chart",
            source="Yahoo Finance chart API (public vendor proxy)",
            source_url="https://query2.finance.yahoo.com/v8/finance/chart/BTC-USD",
            commodity_code="BTC_USD",
            commodity_family="digital_asset",
            price_kind="vendor_proxy",
            known_as_of="2026-08-08T00:00:00Z",
            latest_value="1",
            qc_flag="OK",
        ))
        write_csv(macro_path, MACRO_V3_FIELDS, macro_rows)

        context_path = self.outputs["weekly_context"] / "positioning_flows.csv"
        context_rows = read_csv_rows(context_path)
        context_rows.append(fixture_row(
            CATEGORY_FIELDS["positioning_flows"],
            market="U.S. TREASURY BONDS",
            metric_code="tff_asset_manager_net",
            source="U.S. Commodity Futures Trading Commission",
            source_url="https://publicreporting.cftc.gov/resource/gpe5-46if.csv",
            commodity_code="",
            commodity_family="",
            metric_role="",
            measurement_kind="",
            participant_class="",
            known_as_of="",
            reference_period="",
        ))
        write_csv(
            context_path,
            CATEGORY_FIELDS["positioning_flows"],
            context_rows,
        )

        self._validate()

    def test_contract_six_preserves_macro_proxy_without_commodity_semantics(self):
        macro_path = self.outputs["macro_assets"] / "commodities.csv"
        macro_rows = read_csv_rows(macro_path)
        macro_rows.append(fixture_row(
            MACRO_FIELDS,
            asset_class="commodity",
            group="commodities",
            series_code="COMEX_COPPER",
            provider="yahoo_chart",
            source="Yahoo Finance chart API (public vendor proxy)",
            source_url="https://query1.finance.yahoo.com/v8/finance/chart/HG=F",
            commodity_code="",
            commodity_family="",
            price_kind="",
            known_as_of="2026-08-08T00:00:00Z",
            latest_value="1",
            qc_flag="OK",
        ))
        write_csv(macro_path, MACRO_V3_FIELDS, macro_rows)

        try:
            self._validate()
        except ReleaseValidationError as error:
            self.fail(str(error))


class FakePipelineRunner:
    PIPELINES = {
        "pipeline.indices": "equity_indices",
        "pipeline.sectors": "equity_sectors",
        "pipeline.gics": "gics_sectors",
        "pipeline.macro": "macro_assets",
        "pipeline.context": "weekly_context",
    }

    def __init__(self, fail_pipeline: str | None = None, generation: str = "current"):
        self.fail_pipeline = fail_pipeline
        self.generation = generation
        self.calls = []

    def __call__(self, command, *, check, cwd):
        pipeline = self.PIPELINES[command[2]]
        self.calls.append((tuple(command), check, Path(cwd)))
        if pipeline == self.fail_pipeline:
            raise subprocess.CalledProcessError(2, command)
        output = Path(command[command.index("--output-dir") + 1])
        write_valid_pipeline_output(pipeline, output)
        if pipeline == "weekly_context":
            release_root = output.parent
            write_complete_v2_release_fixture(
                {
                    "macro_assets": next(
                        release_root.glob("capital_weekly_macro_assets_python_*")
                    ),
                    "weekly_context": output,
                }
            )
        raw = (
            output.parent / f".{output.name}.raw"
            if pipeline == "weekly_context"
            else output / "raw"
        )
        raw.mkdir(parents=True, exist_ok=True)
        (raw / "generation.txt").write_text(self.generation, encoding="utf-8")


class FakeRequiredCommodityProviderFailureRunner(FakePipelineRunner):
    def __call__(self, command, *, check, cwd):
        super().__call__(command, check=check, cwd=cwd)
        if self.PIPELINES[command[2]] != "weekly_context":
            return
        output = Path(command[command.index("--output-dir") + 1])
        rows = [
            fixture_row(
                CATEGORY_FIELDS["source_log"],
                provider="eia_refined_products",
                category="commodity_fundamentals",
                requiredness="required",
                status="FETCH_FAILED",
                observations="0",
                as_of_date="2026-08-09",
                source="U.S. Energy Information Administration",
                source_url="https://api.eia.gov/v2/petroleum/",
                notes=(
                    "request failed at "
                    "https://api.eia.gov/v2/petroleum/?api_key=coordinator-secret"
                ),
                phase="retrieve",
                attempts="3",
                error_code="EIA_TIMEOUT",
            ),
            *usda_source_rows(status="NOT_CONFIGURED", requiredness="optional"),
        ]
        write_csv(output / "source_log.csv", CATEGORY_FIELDS["source_log"], rows)


class FakeUntrustedRequiredProviderStatusRunner(
    FakeRequiredCommodityProviderFailureRunner
):
    def __call__(self, command, *, check, cwd):
        super().__call__(command, check=check, cwd=cwd)
        if self.PIPELINES[command[2]] != "weekly_context":
            return
        output = Path(command[command.index("--output-dir") + 1])
        with (output / "source_log.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        rows[0]["status"] = "FETCH_FAILED?api_key=PROBE_SENTINEL"
        rows[0]["error_code"] = ""
        write_csv(output / "source_log.csv", CATEGORY_FIELDS["source_log"], rows)


def directory_bytes(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


class ReleaseOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project_root = Path(self.temporary.name).resolve()
        self.status_path = self.project_root / "state" / "refresh-status.json"
        self.now = datetime(
            2026, 8, 11, 13, 25, tzinfo=ZoneInfo("Asia/Hong_Kong")
        )

    def test_success_activates_contract_six_and_atomic_succeeded_status(self):
        runner = FakePipelineRunner()

        published = run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=runner,
        )

        self.assertEqual(
            published,
            self.project_root / "output",
        )
        manifest = json.loads((published / "release.json").read_text())
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["dataset_contract_version"], 6)
        self.assertEqual(manifest["source_week_id"], "week_20260803-20260809")
        self.assertEqual(manifest["status"], "complete")
        context = json.loads((published / "context.json").read_text())
        self.assertEqual(
            set(context["tables"]),
            {
                "events",
                "economic_releases",
                "financial_conditions",
                "market_internals",
                "positioning_flows",
                "company_events",
                "commodity_fundamentals",
                "fund_flows",
                "company_fundamentals",
                "capital_markets",
                "commodity_metric_history",
                "commodity_research_facts",
                "capability_audit",
            },
        )
        self.assertEqual(
            {path.name for path in published.iterdir()},
            {
                "indices.json",
                "sectors.json",
                "gics.json",
                "macro.json",
                "context.json",
                "release.json",
            },
        )
        self.assertFalse(any(published.glob("week_*")))
        self.assertEqual(
            [pipeline["name"] for pipeline in manifest["pipelines"]],
            ["indices", "sectors", "gics", "macro", "context"],
        )
        for pipeline in manifest["pipelines"]:
            self.assertEqual(pipeline["status"], "complete")
        validated = weekly_release_module.validate_output_bundle(published)
        self.assertEqual(validated["dataset_contract_version"], 6)
        macro = json.loads((published / "macro.json").read_text())
        context = json.loads((published / "context.json").read_text())
        self.assertTrue(macro["tables"]["commodity_price_history"])
        self.assertTrue(context["tables"]["commodity_metric_history"])
        self.assertTrue(context["tables"]["commodity_research_facts"])
        json.dumps(manifest, allow_nan=False)
        status = json.loads(self.status_path.read_text())
        self.assertEqual(
            set(status),
            {
                "job_id",
                "status",
                "pid",
                "updated_at",
                "week_id",
                "current_pipeline",
                "completed",
                "total",
                "started_at",
                "finished_at",
                "error",
                "pipeline",
                "provider",
                "phase",
                "attempts",
                "error_code",
            },
        )
        self.assertEqual(status["status"], "succeeded")
        self.assertEqual(status["pid"], os.getpid())
        self.assertIsInstance(status["updated_at"], str)
        self.assertEqual(status["completed"], 5)
        self.assertEqual(status["total"], 5)
        self.assertIsNone(status["current_pipeline"])
        self.assertIsNone(status["error"])
        self.assertIsNone(status["pipeline"])
        self.assertIsNone(status["provider"])
        self.assertIsNone(status["phase"])
        self.assertIsNone(status["attempts"])
        self.assertIsNone(status["error_code"])
        self.assertIsNotNone(status["finished_at"])
        self.assertEqual(len(runner.calls), 5)
        for _command, check, cwd in runner.calls:
            self.assertTrue(check)
            self.assertEqual(cwd, self.project_root)
        self.assertEqual(list(self.status_path.parent.glob(".*.tmp")), [])
        staging_root = self.project_root / "pipeline" / ".staging"
        self.assertFalse(staging_root.exists() and any(staging_root.iterdir()))
        cache = self.project_root / "pipeline" / ".cache"
        self.assertEqual(
            {path.name for path in cache.iterdir()},
            {"indices", "sectors", "gics", "macro", "context", "cache.json"},
        )

    def test_status_uses_execution_clock_not_the_window_override_clock(self):
        runner = FakePipelineRunner()
        real_datetime = datetime

        class FixedExecutionDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                value = real_datetime(2026, 8, 11, 18, 45, tzinfo=tz)
                return cls.fromtimestamp(value.timestamp(), tz)

        with patch(
            "pipeline.internal.capital_weekly.weekly_release.datetime",
            FixedExecutionDateTime,
        ):
            run_latest_release(
                self.project_root,
                now_hkt=self.now,
                status_path=self.status_path,
                runner=runner,
            )

        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["started_at"], "2026-08-11T18:45:00+08:00")
        self.assertTrue(status["job_id"].startswith("20260811T184500-"))

    def test_default_status_file_matches_the_refresh_api_location(self):
        runner = FakePipelineRunner()

        run_latest_release(
            self.project_root,
            now_hkt=self.now,
            runner=runner,
        )

        status_path = self.project_root / "pipeline" / ".state" / "status.json"
        self.assertTrue(status_path.is_file())
        self.assertEqual(json.loads(status_path.read_text())["status"], "succeeded")

    def test_two_successes_replace_the_same_files_and_keep_only_latest_cache(self):
        first = run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="first"),
        )
        first_names = {path.name for path in first.iterdir()}
        first_release_id = json.loads((first / "release.json").read_text())["release_id"]

        second = run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="second"),
        )

        self.assertEqual(first, second)
        self.assertEqual({path.name for path in second.iterdir()}, first_names)
        self.assertNotEqual(
            json.loads((second / "release.json").read_text())["release_id"],
            first_release_id,
        )
        cache = self.project_root / "pipeline" / ".cache"
        self.assertEqual(
            set(directory_bytes(cache)),
            {
                "cache.json",
                "indices/generation.txt",
                "sectors/generation.txt",
                "gics/generation.txt",
                "macro/generation.txt",
                "context/generation.txt",
            },
        )
        for pipeline in ("indices", "sectors", "gics", "macro", "context"):
            self.assertEqual(
                (cache / pipeline / "generation.txt").read_text(),
                "second",
            )
        self.assertNotIn(b"first", b"".join(directory_bytes(cache).values()))
        self.assertFalse(
            any(
                part.startswith("week_") or part in {"history", "historical"}
                for path in cache.rglob("*")
                for part in path.relative_to(cache).parts
            )
        )
        cache_identity = json.loads((cache / "cache.json").read_text())
        self.assertEqual(
            cache_identity["release_id"],
            json.loads((second / "release.json").read_text())["release_id"],
        )

    def test_required_commodity_provider_failure_preserves_all_stable_hashes(self):
        run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="prior"),
        )
        published = self.project_root / "output"
        cache = self.project_root / "pipeline" / ".cache"
        staging = self.project_root / "pipeline" / ".staging"
        prior_hashes = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in published.iterdir()
        }
        prior_cache = directory_bytes(cache)

        with self.assertRaisesRegex(ReleaseValidationError, "FETCH_FAILED"):
            run_latest_release(
                self.project_root,
                now_hkt=self.now,
                status_path=self.status_path,
                runner=FakeRequiredCommodityProviderFailureRunner(
                    generation="must-not-publish"
                ),
            )

        self.assertEqual(
            {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in published.iterdir()
            },
            prior_hashes,
        )
        self.assertEqual(set(prior_hashes), set(weekly_release_module.OUTPUT_FILES))
        self.assertEqual(directory_bytes(cache), prior_cache)
        self.assertTrue(staging.is_dir())
        self.assertEqual(list(staging.iterdir()), [])
        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["status"], "failed")
        self.assertEqual(status["current_pipeline"], "validation")
        self.assertEqual(status["completed"], 5)
        self.assertEqual(status.get("pipeline"), "weekly_context")
        self.assertEqual(status.get("provider"), "eia_refined_products")
        self.assertEqual(status.get("phase"), "retrieve")
        self.assertEqual(status.get("attempts"), 3)
        self.assertEqual(status.get("error_code"), "EIA_TIMEOUT")
        serialized_status = self.status_path.read_text()
        self.assertNotIn("coordinator-secret", serialized_status)
        self.assertNotIn("api_key", serialized_status.lower())

    def test_required_context_failure_never_derives_status_code_from_raw_status(self):
        with self.assertRaises(ReleaseValidationError):
            run_latest_release(
                self.project_root,
                now_hkt=self.now,
                status_path=self.status_path,
                runner=FakeUntrustedRequiredProviderStatusRunner(),
            )

        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["pipeline"], "weekly_context")
        self.assertEqual(status["error_code"], "PROVIDER_FAILURE")
        serialized_status = json.dumps(status)
        self.assertNotIn("PROBE_SENTINEL", serialized_status)
        self.assertNotIn("?api_key=PROBE_SENTINEL", serialized_status.lower())

    def test_pipeline_failure_preserves_prior_release_and_names_pipeline(self):
        run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="prior"),
        )
        published = self.project_root / "output"
        cache = self.project_root / "pipeline" / ".cache"
        prior_output = directory_bytes(published)
        prior_cache = directory_bytes(cache)
        runner = FakePipelineRunner(fail_pipeline="equity_sectors")

        with self.assertRaisesRegex(ReleasePipelineError, "equity_sectors"):
            run_latest_release(
                self.project_root,
                now_hkt=self.now,
                status_path=self.status_path,
                runner=runner,
            )

        self.assertEqual(directory_bytes(published), prior_output)
        self.assertEqual(directory_bytes(cache), prior_cache)
        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["status"], "failed")
        self.assertEqual(status["current_pipeline"], "equity_sectors")
        self.assertIn("equity_sectors", status["error"])
        self.assertEqual(status["completed"], 1)
        self.assertEqual(len(runner.calls), 2)
        staging_root = self.project_root / "pipeline" / ".staging"
        self.assertFalse(staging_root.exists() and any(staging_root.iterdir()))

    def test_build_pipeline_specs_failure_preserves_original_exception_and_cleans_staging(self):
        def fail_build_specs(*_args, **_kwargs):
            raise RuntimeError("pipeline spec construction sentinel")

        with patch.object(
            weekly_release_module,
            "build_pipeline_specs",
            side_effect=fail_build_specs,
        ):
            with self.assertRaisesRegex(RuntimeError, "pipeline spec construction sentinel"):
                run_latest_release(
                    self.project_root,
                    now_hkt=self.now,
                    status_path=self.status_path,
                    runner=FakePipelineRunner(),
                )

        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["status"], "failed")
        self.assertIsNone(status["current_pipeline"])
        self.assertIn("pipeline spec construction sentinel", status["error"])
        staging_root = self.project_root / "pipeline" / ".staging"
        self.assertTrue(staging_root.is_dir())
        self.assertEqual(list(staging_root.iterdir()), [])

    def test_status_hides_absolute_paths_from_unexpected_errors(self):
        secret_path = self.project_root / "private" / "credentials.txt"

        def fail_with_filesystem_error(*_args, **_kwargs):
            raise OSError(2, "No such file or directory", secret_path)

        with self.assertRaises(OSError):
            run_latest_release(
                self.project_root,
                now_hkt=self.now,
                status_path=self.status_path,
                runner=fail_with_filesystem_error,
            )

        status = json.loads(self.status_path.read_text())
        self.assertIn("credentials.txt", status["error"])
        self.assertNotIn(str(self.project_root), status["error"])

    def test_output_replacement_failure_rolls_output_and_cache_back(self):
        run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="prior"),
        )
        destination = self.project_root / "output"
        cache = self.project_root / "pipeline" / ".cache"
        prior_output = directory_bytes(destination)
        prior_cache = directory_bytes(cache)
        real_replace = os.replace

        def fail_output_swap(source, target):
            if Path(source).name == "output" and Path(target) == destination:
                raise OSError("simulated output swap failure")
            real_replace(source, target)

        with patch(
            "pipeline.internal.capital_weekly.weekly_release.os.replace",
            side_effect=fail_output_swap,
        ):
            with self.assertRaisesRegex(OSError, "simulated output swap failure"):
                run_latest_release(
                    self.project_root,
                    now_hkt=self.now,
                    status_path=self.status_path,
                    runner=FakePipelineRunner(generation="new"),
                )

        self.assertEqual(directory_bytes(destination), prior_output)
        self.assertEqual(directory_bytes(cache), prior_cache)

    def test_cache_replacement_failure_rolls_output_and_cache_back(self):
        run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="prior"),
        )
        destination = self.project_root / "output"
        cache = self.project_root / "pipeline" / ".cache"
        prior_output = directory_bytes(destination)
        prior_cache = directory_bytes(cache)
        real_replace = os.replace

        def fail_cache_swap(source, target):
            if Path(source).name == "cache" and Path(target) == cache:
                raise OSError("simulated cache swap failure")
            real_replace(source, target)

        with patch(
            "pipeline.internal.capital_weekly.weekly_release.os.replace",
            side_effect=fail_cache_swap,
        ):
            with self.assertRaisesRegex(OSError, "simulated cache swap failure"):
                run_latest_release(
                    self.project_root,
                    now_hkt=self.now,
                    status_path=self.status_path,
                    runner=FakePipelineRunner(generation="new"),
                )

        self.assertEqual(directory_bytes(destination), prior_output)
        self.assertEqual(directory_bytes(cache), prior_cache)

    def test_final_status_write_failure_rolls_output_and_cache_back(self):
        run_latest_release(
            self.project_root,
            now_hkt=self.now,
            status_path=self.status_path,
            runner=FakePipelineRunner(generation="prior"),
        )
        destination = self.project_root / "output"
        cache = self.project_root / "pipeline" / ".cache"
        prior_output = directory_bytes(destination)
        prior_cache = directory_bytes(cache)
        real_atomic_write_json = weekly_release_module._atomic_write_json

        def fail_succeeded_status(path, payload):
            if payload.get("status") == "succeeded":
                raise OSError("simulated final status failure")
            return real_atomic_write_json(path, payload)

        with patch(
            "pipeline.internal.capital_weekly.weekly_release._atomic_write_json",
            side_effect=fail_succeeded_status,
        ):
            with self.assertRaisesRegex(OSError, "simulated final status failure"):
                run_latest_release(
                    self.project_root,
                    now_hkt=self.now,
                    status_path=self.status_path,
                    runner=FakePipelineRunner(generation="new"),
                )

        self.assertEqual(directory_bytes(destination), prior_output)
        self.assertEqual(directory_bytes(cache), prior_cache)
        status = json.loads(self.status_path.read_text())
        self.assertEqual(status["status"], "failed")
        self.assertEqual(status["current_pipeline"], "publish")

    def test_held_lock_rejects_a_second_release_without_running_pipelines(self):
        state = self.project_root / "pipeline" / ".state"
        state.mkdir(parents=True)
        lock_path = state / "refresh.lock"
        lock_file = lock_path.open("a+")
        self.addCleanup(lock_file.close)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        runner = FakePipelineRunner()

        with self.assertRaises(ReleaseAlreadyRunning):
            run_latest_release(
                self.project_root,
                now_hkt=self.now,
                status_path=self.status_path,
                runner=runner,
            )

        self.assertEqual(runner.calls, [])
        self.assertFalse(self.status_path.exists())


class CliWrapperTests(unittest.TestCase):
    @staticmethod
    def load_cli_module():
        return importlib.import_module("pipeline.refresh")

    def test_as_of_override_ends_on_supplied_sunday_and_prints_release(self):
        module = self.load_cli_module()
        calls = []

        def release_runner(project_root, *, now_hkt, status_path):
            calls.append((project_root, now_hkt, status_path))
            return project_root / "output"

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = module.main(
                [
                    "--as-of-date",
                    "2026-08-09",
                    "--status-file",
                    "/tmp/capital-weekly-test-status.json",
                ],
                release_runner=release_runner,
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 1)
        project_root, override_now, status_path = calls[0]
        self.assertEqual(project_root, Path(module.__file__).resolve().parents[1])
        self.assertEqual(latest_finished_week(override_now).end, date(2026, 8, 9))
        self.assertEqual(status_path, Path("/tmp/capital-weekly-test-status.json"))
        self.assertEqual(
            stdout.getvalue().strip(),
            str(project_root / "output"),
        )

    def test_validation_failure_exits_nonzero_with_the_error(self):
        module = self.load_cli_module()

        def release_runner(_project_root, *, now_hkt, status_path):
            raise ReleaseValidationError("missing fixed_income.csv")

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = module.main(
                ["--as-of-date", "2026-08-09"],
                release_runner=release_runner,
            )

        self.assertEqual(exit_code, 1)
        self.assertIn("missing fixed_income.csv", stderr.getvalue())

    def test_current_unfinished_sunday_override_is_rejected(self):
        module = self.load_cli_module()
        real_datetime = datetime

        class CurrentSundayDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                value = real_datetime(2026, 8, 9, 12, 0, tzinfo=tz)
                return cls.fromtimestamp(value.timestamp(), tz)

        calls = []
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with patch.object(module, "datetime", CurrentSundayDateTime):
                with self.assertRaises(SystemExit) as raised:
                    module.main(
                        ["--as-of-date", "2026-08-09"],
                        release_runner=lambda *args, **kwargs: calls.append(
                            (args, kwargs)
                        ),
                    )

        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(calls, [])
        self.assertIn("latest finished Sunday (2026-08-02)", stderr.getvalue())

    def test_future_sunday_override_is_rejected(self):
        module = self.load_cli_module()
        real_datetime = datetime

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                value = real_datetime(2026, 8, 14, 12, 0, tzinfo=tz)
                return cls.fromtimestamp(value.timestamp(), tz)

        calls = []
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with patch.object(module, "datetime", FixedDateTime):
                with self.assertRaises(SystemExit) as raised:
                    module.main(
                        ["--as-of-date", "2026-08-16"],
                        release_runner=lambda *args, **kwargs: calls.append(
                            (args, kwargs)
                        ),
                    )

        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(calls, [])
        self.assertIn("latest finished Sunday (2026-08-09)", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
