from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from capital_weekly.weekly_context import (
    ProviderResult,
    normalize_metric_rows,
    publish_weekly_context_bundle,
    run_weekly_context,
)


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


class WeeklyContextTests(unittest.TestCase):
    def test_duplicate_metric_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate metric key"):
            normalize_metric_rows([metric("ADVANCE_RATIO"), metric("ADVANCE_RATIO")])

    def test_non_finite_metric_is_visible_as_invalid_instead_of_serialized(self):
        rows = normalize_metric_rows([metric("VIX", float("inf"))])

        self.assertIsNone(rows[0]["value"])
        self.assertEqual(rows[0]["qc_flag"], "INVALID_VALUE")

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

        tables = run_weekly_context(
            {"successful": successful, "failed": failed},
            as_of_date=date(2026, 7, 24),
        )

        self.assertEqual(tables["market_internals"][0]["value"], 18.5)
        self.assertEqual(
            {row["provider"]: row["status"] for row in tables["source_log"]},
            {"successful": "OK", "failed": "FETCH_FAILED"},
        )

    def test_bundle_publisher_writes_all_category_files_and_strict_json(self):
        tables = {
            "events": [],
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


if __name__ == "__main__":
    unittest.main()
