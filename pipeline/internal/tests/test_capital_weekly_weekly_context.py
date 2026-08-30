from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import hashlib
import json
import unittest
from urllib.parse import quote, quote_plus

import pandas as pd

from pipeline.internal.capital_weekly.weekly_context import (
    CATEGORY_FIELDS,
    CATEGORY_FILES,
    ProviderResult,
    normalize_metric_rows,
    publish_weekly_context_bundle,
    run_weekly_context,
)
from pipeline.internal.capital_weekly.context.provider_contracts import ContextProvider, ProviderSpec
from pipeline.internal.capital_weekly.context.economic_releases import build_release_row
from pipeline.internal.capital_weekly.context.economic_releases import derive_price_index_rows
from pipeline.internal.capital_weekly.context.providers import metric_rows


EXPECTED_EMPTY_FIELDS = {
    "economic_releases": [
        "record_id",
        "indicator_code",
        "indicator_name",
        "observation_period",
        "release_at_bjt",
        "vintage_date",
        "as_of_date",
        "known_as_of",
        "value",
        "previous_value",
        "revised_previous",
        "consensus_value",
        "surprise_value",
        "unit",
        "frequency",
        "seasonal_adjustment",
        "calculation_id",
        "formula_version",
        "input_record_ids",
        "source",
        "source_url",
        "source_tier",
        "qc_flag",
    ],
    "company_events": [
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
    ],
    "commodity_fundamentals": [
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
    ],
}

COMMODITY_METRIC_FIELD_NAMES = (
    "commodity_code",
    "commodity_family",
    "metric_role",
    "measurement_kind",
    "participant_class",
    "known_as_of",
    "reference_period",
)
EXPECTED_EMPTY_FIELDS["company_events"][11:11] = COMMODITY_METRIC_FIELD_NAMES
EXPECTED_EMPTY_FIELDS["commodity_fundamentals"].extend(COMMODITY_METRIC_FIELD_NAMES)


def metric(code: str, value: float = 1.0) -> dict:
    return {
        "as_of_date": date(2026, 7, 24),
        "category": "market_internals",
        "metric_code": code,
        "metric_name": code,
        "value": value,
        "unit": "ratio",
        "frequency": "daily",
        "market": "US",
        "source": "Fixture",
        "source_url": "https://example.test/data",
        "qc_flag": "OK",
    }


def company_event() -> dict:
    return {
        "as_of_date": date(2026, 7, 24),
        "category": "company_events",
        "metric_code": "EARNINGS_RELEASE",
        "metric_name": "Earnings release",
        "value": 18.5,
        "unit": "usd",
        "frequency": "quarterly",
        "market": "US",
        "source": "Fixture",
        "source_url": "https://example.test/company-event",
        "qc_flag": "OK",
        "event_date": "2026-07-24",
        "ticker": "FIX",
        "cik": "0000123456",
        "form": "8-K",
        "event_type": "EARNINGS_RELEASE",
        "accession_number": "0000123456-26-000001",
        "report_date": "2026-06-30",
        "accepted_at": "2026-07-24T08:30:00-04:00",
        "items": "2.02",
        "evidence_status": "CONFIRMED",
    }


class WeeklyContextTests(unittest.TestCase):
    def test_category_fields_cover_every_published_category(self):
        self.assertEqual(set(CATEGORY_FIELDS), set(CATEGORY_FILES))

    def test_duplicate_metric_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate metric key"):
            normalize_metric_rows([metric("ADVANCE_RATIO"), metric("ADVANCE_RATIO")])

    def test_non_finite_metric_is_visible_as_invalid_instead_of_serialized(self):
        rows = normalize_metric_rows([metric("VIX", float("inf"))])

        self.assertIsNone(rows[0]["value"])
        self.assertEqual(rows[0]["qc_flag"], "INVALID_VALUE")

    def test_normalizes_old_format_metrics_with_empty_commodity_metadata(self):
        row = normalize_metric_rows([metric("VIX")])[0]

        for field in COMMODITY_METRIC_FIELD_NAMES:
            with self.subTest(field=field):
                self.assertIn(field, row)
                self.assertIsNone(row[field])

    def test_metric_rows_only_merge_registered_commodity_metadata(self):
        row = metric_rows(
            as_of_date=date(2026, 7, 24),
            category="commodity_fundamentals",
            market="US",
            source="Fixture",
            source_url="https://example.test/data",
            frequency="weekly",
            values={"inventory": 10.0},
            units={"inventory": "barrels"},
            metadata={
                "commodity_code": "WTI",
                "measurement_kind": "inventory",
                "not_contract_metadata": "ignored",
            },
        )[0]

        self.assertEqual(row["commodity_code"], "WTI")
        self.assertEqual(row["measurement_kind"], "inventory")
        self.assertNotIn("not_contract_metadata", row)

    def test_normalization_rejects_unsupported_non_null_commodity_semantics(self):
        base = metric("INVENTORY")
        base.update(
            commodity_code="WTI",
            commodity_family="refined_products",
            metric_role="physical_fundamental",
            measurement_kind="inventory",
        )

        with self.assertRaisesRegex(ValueError, "metric_role"):
            normalize_metric_rows([{**base, "metric_role": "fundamental"}])
        with self.assertRaisesRegex(ValueError, "measurement_kind"):
            normalize_metric_rows(
                [{**base, "measurement_kind": "physical_level"}]
            )

    def test_provider_failure_does_not_abort_successful_provider(self):
        def successful():
            return ProviderResult(
                category="market_internals",
                rows=[metric("VIX", 18.5)],
                raw_text="successful raw",
                source="Fixture",
                source_url="https://example.test/success",
            )

        def failed():
            raise RuntimeError("public page changed")

        success_spec = ProviderSpec(
            name="successful",
            category="market_internals",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="daily",
            freshness_days=1,
        )
        failure_spec = ProviderSpec(
            name="failed",
            category="market_internals",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="daily",
            freshness_days=1,
        )

        tables = run_weekly_context(
            {
                "successful": ContextProvider(success_spec, successful),
                "failed": ContextProvider(failure_spec, failed),
            },
            as_of_date=date(2026, 7, 24),
        )

        self.assertEqual(tables["market_internals"][0]["value"], 18.5)
        self.assertEqual(
            {row["provider"]: row["status"] for row in tables["source_log"]},
            {"successful": "OK", "failed": "FETCH_FAILED"},
        )
        successful_log = next(
            row for row in tables["source_log"] if row["provider"] == "successful"
        )
        self.assertEqual(successful_log["source_tier"], "public")
        self.assertEqual(successful_log["requiredness"], "required")
        self.assertEqual(successful_log["provider_version"], "1.0.0")
        self.assertEqual(successful_log["schema_version"], "economic-release-v1")

    def test_credential_query_values_are_redacted_from_context_audit_artifacts(self):
        secret = "audit-sentinel-context-key"
        prepared_url = (
            "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
            f"?api_key={secret}&frequency=weekly"
        )
        spec = ProviderSpec(
            name="eia_fixture",
            category="commodity_fundamentals",
            source_tier="public",
            requiredness="required",
            provider_version="fixture-v1",
            schema_version="context-metric-v1",
            frequency="weekly",
            freshness_days=10,
        )
        provider = ContextProvider(
            spec,
            lambda: ProviderResult(
                category="commodity_fundamentals",
                rows=[],
                raw_text=f"request failed: {prepared_url}".encode("utf-8"),
                source="U.S. Energy Information Administration",
                source_url=prepared_url,
                status="FETCH_FAILED",
                notes=f"401 Client Error for url: {prepared_url}",
                raw_is_diagnostic=True,
            ),
        )

        with TemporaryDirectory() as directory:
            raw_dir = Path(directory) / "raw"
            tables = run_weekly_context(
                {"eia_fixture": provider},
                raw_dir=raw_dir,
                as_of_date=date(2026, 8, 9),
            )
            serialized = "\n".join(
                (
                    json.dumps(tables),
                    (raw_dir / "eia_fixture.raw").read_text(encoding="utf-8"),
                )
            )

        self.assertNotIn(secret, serialized)
        self.assertIn("api_key=[REDACTED]", serialized)

    def test_explicit_secrets_are_redacted_from_diagnostic_bytes_and_text(self):
        secret = "diagnostic secret/+value"
        candidates = (secret, quote(secret, safe=""), quote_plus(secret, safe=""))
        spec = ProviderSpec(
            name="diagnostic_fixture",
            category="market_internals",
            source_tier="public",
            requiredness="optional",
            provider_version="fixture-v1",
            schema_version="context-metric-v1",
            frequency="daily",
            freshness_days=1,
        )
        for raw_text in (
            " | ".join(candidates),
            " | ".join(candidates).encode("utf-8"),
        ):
            with self.subTest(raw_type=type(raw_text).__name__):
                provider = ContextProvider(
                    spec,
                    lambda: ProviderResult(
                        category="market_internals",
                        rows=[],
                        raw_text=raw_text,
                        source="Fixture",
                        source_url="https://example.test/diagnostic",
                        status="FETCH_FAILED",
                        raw_is_diagnostic=True,
                    ),
                )
                with TemporaryDirectory() as directory:
                    raw_dir = Path(directory) / "raw"
                    run_weekly_context(
                        {"diagnostic_fixture": provider},
                        raw_dir=raw_dir,
                        as_of_date=date(2026, 8, 9),
                        audit_secrets=(f" {secret} ",),
                    )
                    cached = (raw_dir / "diagnostic_fixture.raw").read_text(
                        encoding="utf-8"
                    )

                for candidate in candidates:
                    self.assertNotIn(candidate, cached)
                self.assertIn("[REDACTED]", cached)

    def test_explicit_secret_is_redacted_from_notes_urls_rows_and_exceptions(self):
        secret = "bare-runtime-secret"
        result_url = f"https://example.test/result/{secret}"
        row_url = f"https://example.test/row/{secret}"
        success_spec = ProviderSpec(
            name="secret_result_fixture",
            category="market_internals",
            source_tier="public",
            requiredness="optional",
            provider_version="fixture-v1",
            schema_version="context-metric-v1",
            frequency="daily",
            freshness_days=1,
        )
        row = metric("SECRET_RESULT")
        row["source_url"] = row_url
        failure_spec = ProviderSpec(
            name="secret_exception_fixture",
            category="market_internals",
            source_tier="public",
            requiredness="optional",
            provider_version="fixture-v1",
            schema_version="context-metric-v1",
            frequency="daily",
            freshness_days=1,
        )

        def failed():
            raise RuntimeError(f"transport failed with {secret}")

        tables = run_weekly_context(
            {
                "secret_result_fixture": ContextProvider(
                    success_spec,
                    lambda: ProviderResult(
                        category="market_internals",
                        rows=[row],
                        raw_text="official source without credential",
                        source="Fixture",
                        source_url=result_url,
                        notes=f"provider note contains {secret}",
                    ),
                ),
                "secret_exception_fixture": ContextProvider(failure_spec, failed),
            },
            as_of_date=date(2026, 8, 9),
            audit_secrets=(secret,),
        )
        serialized = json.dumps(tables)

        self.assertNotIn(secret, serialized)
        self.assertGreaterEqual(serialized.count("[REDACTED]"), 4)

    def test_successful_string_source_with_actual_secret_fails_without_cache_write(self):
        secret = "successful-string-runtime-secret"
        spec = ProviderSpec(
            name="official_string_fixture",
            category="market_internals",
            source_tier="public",
            requiredness="optional",
            provider_version="fixture-v1",
            schema_version="context-metric-v1",
            frequency="daily",
            freshness_days=1,
        )
        provider = ContextProvider(
            spec,
            lambda: ProviderResult(
                category="market_internals",
                rows=[],
                raw_text=f"official source contains {secret}",
                source="Fixture",
                source_url="https://example.test/official",
            ),
        )

        with TemporaryDirectory() as directory:
            raw_dir = Path(directory) / "raw"
            tables = run_weekly_context(
                {"official_string_fixture": provider},
                raw_dir=raw_dir,
                as_of_date=date(2026, 8, 9),
                audit_secrets=(secret,),
            )
            self.assertFalse((raw_dir / "official_string_fixture.raw").exists())

        audit = tables["source_log"][0]
        self.assertEqual(audit["status"], "FETCH_FAILED")
        self.assertNotIn(secret, json.dumps(audit))

    def test_successful_binary_source_is_cached_byte_exact_with_matching_hash(self):
        raw_bytes = b"\x00official?api_key=published-cell-value\xff"
        raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        for status in ("OK", "POINT_IN_TIME_UNAVAILABLE"):
            with self.subTest(status=status):
                spec = ProviderSpec(
                    name="official_binary_fixture",
                    category="commodity_fundamentals",
                    source_tier="public",
                    requiredness="optional",
                    provider_version="fixture-v1",
                    schema_version="context-metric-v1",
                    frequency="weekly",
                    freshness_days=5,
                )
                provider = ContextProvider(
                    spec,
                    lambda: ProviderResult(
                        category="commodity_fundamentals",
                        rows=[],
                        raw_text=raw_bytes,
                        source="CME Group",
                        source_url="https://www.cmegroup.com/official.xls",
                        status=status,
                        notes=f"bytes={len(raw_bytes)}; sha256={raw_sha256}",
                    ),
                )

                with TemporaryDirectory() as directory:
                    raw_dir = Path(directory) / "raw"
                    tables = run_weekly_context(
                        {"official_binary_fixture": provider},
                        raw_dir=raw_dir,
                        as_of_date=date(2026, 8, 9),
                    )
                    cached_bytes = (
                        raw_dir / "official_binary_fixture.raw"
                    ).read_bytes()

                self.assertEqual(cached_bytes, raw_bytes)
                self.assertEqual(hashlib.sha256(cached_bytes).hexdigest(), raw_sha256)
                self.assertIn(
                    f"sha256={raw_sha256}", tables["source_log"][0]["notes"]
                )
                self.assertEqual(tables["source_log"][0]["status"], status)

    def test_successful_binary_source_containing_actual_credential_fails_closed(self):
        secret = "actual-runtime-credential"
        raw_bytes = f"official?api_key={secret}".encode("utf-8")
        spec = ProviderSpec(
            name="official_binary_fixture",
            category="commodity_fundamentals",
            source_tier="public",
            requiredness="optional",
            provider_version="fixture-v1",
            schema_version="context-metric-v1",
            frequency="weekly",
            freshness_days=5,
        )
        provider = ContextProvider(
            spec,
            lambda: ProviderResult(
                category="commodity_fundamentals",
                rows=[],
                raw_text=raw_bytes,
                source="CME Group",
                source_url="https://www.cmegroup.com/official.xls",
            ),
        )

        with TemporaryDirectory() as directory:
            raw_dir = Path(directory) / "raw"
            tables = run_weekly_context(
                {"official_binary_fixture": provider},
                raw_dir=raw_dir,
                as_of_date=date(2026, 8, 9),
                audit_secrets=(f" {secret} ",),
            )
            self.assertFalse((raw_dir / "official_binary_fixture.raw").exists())

        audit = tables["source_log"][0]
        self.assertEqual(audit["status"], "FETCH_FAILED")
        self.assertNotIn(secret, json.dumps(audit))

        uncached_tables = run_weekly_context(
            {"official_binary_fixture": provider},
            as_of_date=date(2026, 8, 9),
            audit_secrets=(f" {secret} ",),
        )
        self.assertEqual(uncached_tables["source_log"][0]["status"], "FETCH_FAILED")
        self.assertNotIn(secret, json.dumps(uncached_tables["source_log"][0]))

    def test_source_log_orders_known_as_of_as_timestamps(self):
        spec = ProviderSpec(
            name="release_source",
            category="events",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="event",
            freshness_days=None,
        )

        tables = run_weekly_context(
            {
                "release_source": ContextProvider(
                    spec,
                    lambda: ProviderResult(
                        category="events",
                        rows=[
                            {"known_as_of": "2026-08-09T23:30:00+08:00"},
                            {"known_as_of": "2026-08-09T16:00:00-04:00"},
                        ],
                        raw_text="release artifacts",
                        source="Fixture",
                        source_url="https://example.test/releases",
                    ),
                )
            },
            as_of_date=date(2026, 8, 9),
        )

        self.assertEqual(
            tables["source_log"][0]["latest_known_as_of"],
            "2026-08-09T23:30:00+08:00",
        )

    def test_monday_revision_is_excluded_from_the_published_context_table(self):
        spec = ProviderSpec(
            name="release_source",
            category="events",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="event",
            freshness_days=None,
        )

        tables = run_weekly_context(
            {
                "release_source": ContextProvider(
                    spec,
                    lambda: ProviderResult(
                        category="events",
                        rows=[
                            {
                                "record_id": "friday-release",
                                "known_as_of": "2026-08-07T08:30:00-04:00",
                            },
                            {
                                "record_id": "monday-revision",
                                "known_as_of": "2026-08-10T08:30:00-04:00",
                            },
                        ],
                        raw_text="release artifacts",
                        source="Fixture",
                        source_url="https://example.test/releases",
                    ),
                )
            },
            as_of_date=date(2026, 8, 9),
        )

        self.assertEqual(
            [row["record_id"] for row in tables["events"]], ["friday-release"]
        )
        self.assertEqual(tables["source_log"][0]["status"], "OK")
        self.assertEqual(
            tables["source_log"][0]["latest_known_as_of"],
            "2026-08-07T08:30:00-04:00",
        )

    def test_all_after_cutoff_rows_are_visible_as_point_in_time_unavailable(self):
        spec = ProviderSpec(
            name="release_source",
            category="events",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="event",
            freshness_days=None,
        )

        tables = run_weekly_context(
            {
                "release_source": ContextProvider(
                    spec,
                    lambda: ProviderResult(
                        category="events",
                        rows=[
                            {
                                "record_id": "monday-revision",
                                "known_as_of": "2026-08-10T08:30:00-04:00",
                            }
                        ],
                        raw_text="monday artifact",
                        source="Fixture",
                        source_url="https://example.test/releases",
                    ),
                )
            },
            as_of_date=date(2026, 8, 9),
        )

        self.assertEqual(tables["events"], [])
        self.assertEqual(tables["source_log"][0]["provider"], "release_source")
        self.assertEqual(tables["source_log"][0]["category"], "events")
        self.assertEqual(
            tables["source_log"][0]["status"], "POINT_IN_TIME_UNAVAILABLE"
        )
        self.assertEqual(tables["source_log"][0]["observations"], 0)
        self.assertIsNone(tables["source_log"][0]["latest_known_as_of"])

    def test_cross_provider_economic_record_duplicate_is_not_published_and_is_audited(self):
        release = build_release_row(
            indicator_code="CPI_INDEX_SA",
            observation_period="2026-06",
            release_at_bjt="2026-07-14T20:30:00+08:00",
            value=326.1,
            unit="index",
            frequency="monthly",
            source="Official fixture",
            source_url="https://example.test/cpi",
            known_as_of="2026-07-14T08:30:00-04:00",
            as_of_date=date(2026, 8, 9),
        )
        providers = {}
        for name in ("economic_one", "economic_two"):
            spec = ProviderSpec(
                name=name,
                category="economic_releases",
                source_tier="public",
                requiredness="required",
                provider_version="1.0.0",
                schema_version="economic-release-v1",
                frequency="monthly",
                freshness_days=31,
            )
            providers[name] = ContextProvider(
                spec,
                lambda: ProviderResult(
                    category="economic_releases",
                    rows=[release],
                    raw_text="economic fixture",
                    source="Official fixture",
                    source_url="https://example.test/cpi",
                ),
            )

        tables = run_weekly_context(providers, as_of_date=date(2026, 8, 9))

        self.assertEqual(tables["economic_releases"], [])
        audit = next(
            row for row in tables["source_log"]
            if row["provider"] == "economic_releases_validation"
        )
        self.assertEqual(audit["status"], "FETCH_FAILED")
        self.assertIn("Duplicate economic release record_id", audit["notes"])

    def test_combined_economic_validation_rejects_nonexistent_derived_inputs(self):
        missing_inputs = ("a" * 64, "b" * 64)
        derived = build_release_row(
            indicator_code="CPI_INDEX_SA_MOM_PCT",
            observation_period="2026-06",
            release_at_bjt="2026-07-14T20:30:00+08:00",
            value=0.6,
            unit="percent",
            frequency="monthly",
            source="Official fixture",
            source_url="https://example.test/cpi",
            known_as_of="2026-07-14T08:30:00-04:00",
            as_of_date=date(2026, 8, 9),
            calculation_id="price_index_mom_pct",
            formula_version="economic-v1",
            input_record_ids=missing_inputs,
        )
        spec = ProviderSpec(
            name="economic_derived",
            category="economic_releases",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="monthly",
            freshness_days=31,
        )

        tables = run_weekly_context(
            {
                "economic_derived": ContextProvider(
                    spec,
                    lambda: ProviderResult(
                        category="economic_releases",
                        rows=[derived],
                        raw_text="economic fixture",
                        source="Official fixture",
                        source_url="https://example.test/cpi",
                    ),
                )
            },
            as_of_date=date(2026, 8, 9),
        )

        self.assertEqual(tables["economic_releases"], [])
        audit = next(
            row for row in tables["source_log"]
            if row["provider"] == "economic_releases_validation"
        )
        self.assertEqual(audit["status"], "FETCH_FAILED")
        self.assertIn("does not resolve", audit["notes"])

    def test_combined_economic_validation_preserves_resolved_derived_inputs(self):
        observed = [
            build_release_row(
                indicator_code="CPI_INDEX_SA",
                observation_period="2026-05",
                release_at_bjt="2026-07-14T20:30:00+08:00",
                value=324.0,
                unit="index",
                frequency="monthly",
                source="Official fixture",
                source_url="https://example.test/cpi",
                known_as_of="2026-07-14T08:30:00-04:00",
                as_of_date=date(2026, 8, 9),
            ),
            build_release_row(
                indicator_code="CPI_INDEX_SA",
                observation_period="2026-06",
                release_at_bjt="2026-07-14T20:30:00+08:00",
                value=326.1,
                unit="index",
                frequency="monthly",
                source="Official fixture",
                source_url="https://example.test/cpi",
                known_as_of="2026-07-14T08:30:00-04:00",
                as_of_date=date(2026, 8, 9),
            ),
        ]
        rows = observed + derive_price_index_rows(observed, "CPI_INDEX_SA")
        spec = ProviderSpec(
            name="economic_valid_derived",
            category="economic_releases",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="monthly",
            freshness_days=31,
        )

        tables = run_weekly_context(
            {
                "economic_valid_derived": ContextProvider(
                    spec,
                    lambda: ProviderResult(
                        category="economic_releases",
                        rows=rows,
                        raw_text="economic fixture",
                        source="Official fixture",
                        source_url="https://example.test/cpi",
                    ),
                )
            },
            as_of_date=date(2026, 8, 9),
        )

        self.assertEqual(len(tables["economic_releases"]), 3)
        self.assertFalse(
            any(
                row["provider"] == "economic_releases_validation"
                for row in tables["source_log"]
            )
        )

    def test_provider_mapping_key_mismatch_cannot_populate_a_table(self):
        spec = ProviderSpec(
            name="registered_name",
            category="events",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="event",
            freshness_days=None,
        )

        tables = run_weekly_context(
            {
                "wrong_name": ContextProvider(
                    spec,
                    lambda: ProviderResult(
                        category="events",
                        rows=[{"record_id": "must-not-publish"}],
                        raw_text="invalid provider",
                        source="Fixture",
                        source_url="https://example.test/releases",
                    ),
                )
            },
            as_of_date=date(2026, 8, 9),
        )

        self.assertEqual(tables["events"], [])
        self.assertEqual(tables["source_log"][0]["provider"], "wrong_name")
        self.assertEqual(tables["source_log"][0]["category"], "events")
        self.assertEqual(tables["source_log"][0]["status"], "FETCH_FAILED")
        self.assertIn("does not match", tables["source_log"][0]["notes"])

    def test_result_category_mismatch_cannot_populate_an_unintended_table(self):
        spec = ProviderSpec(
            name="release_source",
            category="events",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="event",
            freshness_days=None,
        )

        tables = run_weekly_context(
            {
                "release_source": ContextProvider(
                    spec,
                    lambda: ProviderResult(
                        category="market_internals",
                        rows=[metric("MUST_NOT_PUBLISH")],
                        raw_text="wrong category",
                        source="Fixture",
                        source_url="https://example.test/releases",
                    ),
                )
            },
            as_of_date=date(2026, 8, 9),
        )

        self.assertEqual(tables["events"], [])
        self.assertEqual(tables["market_internals"], [])
        self.assertEqual(tables["source_log"][0]["provider"], "release_source")
        self.assertEqual(tables["source_log"][0]["category"], "events")
        self.assertEqual(tables["source_log"][0]["status"], "FETCH_FAILED")
        self.assertIn("does not match", tables["source_log"][0]["notes"])

    def test_bundle_publisher_writes_all_category_files_and_strict_json(self):
        tables = {
            "events": [],
            "economic_releases": [],
            "market_internals": [metric("VIX", 18.5)],
            "positioning_flows": [],
            "company_events": [],
            "commodity_fundamentals": [],
            "financial_conditions": [],
            "source_log": [],
        }
        with TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"

            publish_weekly_context_bundle(tables, output)

            expected = {
                "events.csv",
                "economic_releases.csv",
                "market_internals.csv",
                "positioning_flows.csv",
                "company_events.csv",
                "commodity_fundamentals.csv",
                "financial_conditions.csv",
                "source_log.csv",
                "weekly_context_snapshot.json",
            }
            self.assertEqual({path.name for path in output.iterdir()}, expected)
            snapshot = json.loads(
                (output / "weekly_context_snapshot.json").read_text(encoding="utf-8")
            )
            self.assertEqual(snapshot["market_internals"][0]["value"], 18.5)
            for category in (
                "economic_releases",
                "company_events",
                "commodity_fundamentals",
            ):
                with (output / f"{category}.csv").open(
                    newline="", encoding="utf-8"
                ) as file:
                    self.assertEqual(
                        next(csv.reader(file)), EXPECTED_EMPTY_FIELDS[category]
                    )
                empty_table = pd.read_csv(output / f"{category}.csv")
                self.assertEqual(list(empty_table.columns), EXPECTED_EMPTY_FIELDS[category])
                self.assertTrue(empty_table.empty)

    def test_bundle_publisher_includes_commodity_metadata_headers(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"

            publish_weekly_context_bundle({}, output)

            for category in ("commodity_fundamentals", "positioning_flows"):
                with self.subTest(category=category):
                    with (output / f"{category}.csv").open(
                        newline="", encoding="utf-8"
                    ) as file:
                        header = next(csv.reader(file))
                    self.assertEqual(header[-7:], list(COMMODITY_METRIC_FIELD_NAMES))

    def test_bundle_publisher_preserves_populated_company_event_csv(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"

            publish_weekly_context_bundle(
                {"company_events": [company_event()]}, output
            )

            with (output / "company_events.csv").open(
                newline="", encoding="utf-8"
            ) as file:
                self.assertEqual(
                    next(csv.reader(file)), EXPECTED_EMPTY_FIELDS["company_events"]
                )
            with (output / "company_events.csv").open(
                newline="", encoding="utf-8"
            ) as file:
                company_events = list(csv.DictReader(file))
            self.assertEqual(
                company_events,
                [
                    {
                        "as_of_date": "2026-07-24",
                        "category": "company_events",
                        "metric_code": "EARNINGS_RELEASE",
                        "metric_name": "Earnings release",
                        "value": "18.5",
                        "unit": "usd",
                        "frequency": "quarterly",
                        "market": "US",
                        "source": "Fixture",
                        "source_url": "https://example.test/company-event",
                        "qc_flag": "OK",
                        "commodity_code": "",
                        "commodity_family": "",
                        "metric_role": "",
                        "measurement_kind": "",
                        "participant_class": "",
                        "known_as_of": "",
                        "reference_period": "",
                        "event_date": "2026-07-24",
                        "ticker": "FIX",
                        "cik": "0000123456",
                        "form": "8-K",
                        "event_type": "EARNINGS_RELEASE",
                        "accession_number": "0000123456-26-000001",
                        "report_date": "2026-06-30",
                        "accepted_at": "2026-07-24T08:30:00-04:00",
                        "items": "2.02",
                        "evidence_status": "CONFIRMED",
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
