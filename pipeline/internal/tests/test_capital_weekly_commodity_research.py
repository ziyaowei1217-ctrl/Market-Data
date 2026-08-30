from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pipeline.internal.capital_weekly.commodity_research import (
    METRIC_HISTORY_FIELDS,
    PRICE_HISTORY_FIELDS,
    bounded_metric_history,
    bounded_price_history,
    load_history_limits,
    stable_record_id,
)


LIMITS = {
    "daily": 400,
    "weekly": 160,
    "monthly": 84,
    "annual": 12,
    "marketing_year": 12,
}


def _price_config(
    series_code: str,
    frequency: str,
    *,
    provider: str = "eia_v2",
    commodity_code: str | None = None,
) -> dict:
    code = commodity_code or series_code
    return {
        "series_code": series_code,
        "provider": provider,
        "frequency": frequency,
        "level_unit": f"native-{frequency}",
        "source": "Official fixture",
        "source_url": "https://official.example.test/prices",
        "commodity_code": code,
        "commodity_family": "refined_products",
        "price_kind": (
            "official_cash"
            if provider == "eia_v2"
            else "official_monthly_benchmark"
        ),
    }


def _price_points(
    as_of: date,
    *,
    count: int,
    step_days: int,
) -> list[dict]:
    first = as_of - timedelta(days=(count - 1) * step_days)
    return [
        {
            "date": first + timedelta(days=index * step_days),
            "known_as_of": datetime.combine(
                first + timedelta(days=index * step_days),
                datetime.min.time(),
                tzinfo=timezone.utc,
            ).isoformat(),
            "value": float(index + 1),
        }
        for index in range(count)
    ]


def _metric_row(
    observation_date: date,
    *,
    frequency: str = "weekly",
    value: float = 10.0,
    known_as_of: str | None = None,
    qc_flag: str = "OK",
    source_url: str = "https://official.example.test/metric",
    metric_role: str = "physical_fundamental",
    measurement_kind: str = "inventory",
) -> dict:
    return {
        "as_of_date": observation_date,
        "category": "commodity_fundamentals",
        "metric_code": "stocks",
        "metric_name": "Official stocks",
        "value": value,
        "unit": "native-bcf",
        "frequency": frequency,
        "market": "US",
        "source": "Official fixture",
        "source_url": source_url,
        "qc_flag": qc_flag,
        "commodity_code": "NATGAS_HH",
        "commodity_family": "natural_gas",
        "metric_role": metric_role,
        "measurement_kind": measurement_kind,
        "participant_class": None,
        "known_as_of": known_as_of
        or datetime.combine(
            observation_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        ).isoformat(),
        "reference_period": observation_date.isoformat(),
    }


class StableRecordIdTests(unittest.TestCase):
    def test_canonical_utf8_json_produces_stable_sha256_identity(self):
        left = {
            "series": "WTI",
            "code": "WTI",
            "observation_date": "2026-08-28",
            "known_as_of": "2026-08-28T12:00:00+00:00",
        }
        right = dict(reversed(tuple(left.items())))

        self.assertEqual(
            stable_record_id("commodity_price_history", left),
            "1032a8342a32869a1608b8537e74986d71878dee362d61a2587ec513d1707c44",
        )
        self.assertEqual(
            stable_record_id("commodity_price_history", left),
            stable_record_id("commodity_price_history", right),
        )


class HistoryLimitConfigTests(unittest.TestCase):
    def _write_config(self, root: Path, limits: dict) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        path = root / "config.json"
        path.write_text(
            json.dumps({"commodity_research": {"history_limits": limits}}),
            encoding="utf-8",
        )
        return path

    def test_loads_all_explicit_positive_frequency_limits(self):
        with TemporaryDirectory() as directory:
            path = self._write_config(Path(directory), LIMITS)

            self.assertEqual(load_history_limits(path), LIMITS)

    def test_missing_or_nonpositive_limit_fails_without_a_default(self):
        invalid_limits = [
            {key: value for key, value in LIMITS.items() if key != "weekly"},
            {**LIMITS, "daily": 0},
            {**LIMITS, "monthly": -1},
            {**LIMITS, "annual": 1.5},
            {**LIMITS, "marketing_year": True},
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for index, limits in enumerate(invalid_limits):
                with self.subTest(limits=limits):
                    path = self._write_config(root / str(index), limits)
                    with self.assertRaisesRegex(ValueError, "history_limits"):
                        load_history_limits(path)


class BoundedPriceHistoryTests(unittest.TestCase):
    def test_point_in_time_selection_precedes_exact_frequency_windows(self):
        as_of = date(2026, 8, 30)
        definitions = (
            ("DAILY", "daily", 402, 1, 400, "eia_v2"),
            ("WEEKLY", "weekly", 162, 7, 160, "eia_v2"),
            ("MONTHLY", "monthly", 86, 28, 84, "world_bank_pink_sheet"),
            ("ANNUAL", "annual", 14, 365, 12, "world_bank_pink_sheet"),
        )
        universe = []
        histories = {}
        expected_oldest = {}
        for series, frequency, count, step, limit, provider in definitions:
            universe.append(_price_config(series, frequency, provider=provider))
            points = _price_points(as_of, count=count, step_days=step)
            expected_oldest[series] = points[-limit]["date"].isoformat()
            points.extend(
                [
                    {
                        "date": as_of + timedelta(days=1),
                        "known_as_of": "2026-08-31T00:00:00+00:00",
                        "value": 999_001.0,
                    },
                    {
                        "date": as_of,
                        "known_as_of": "2026-08-31T00:00:00+00:00",
                        "value": 999_002.0,
                    },
                ]
            )
            histories[series] = points

        rows = bounded_price_history(histories, universe, as_of, LIMITS)

        self.assertTrue(all(tuple(row) == PRICE_HISTORY_FIELDS for row in rows))
        for series, _frequency, _count, _step, limit, _provider in definitions:
            with self.subTest(series=series):
                selected = [row for row in rows if row["series_code"] == series]
                self.assertEqual(len(selected), limit)
                self.assertEqual(selected[0]["observation_date"], expected_oldest[series])
                self.assertEqual(
                    [row["observation_date"] for row in selected],
                    sorted(row["observation_date"] for row in selected),
                )
                self.assertEqual(selected[-1]["unit"], f"native-{_frequency}")
                self.assertNotIn(999_001.0, [row["value"] for row in selected])
                self.assertNotIn(999_002.0, [row["value"] for row in selected])

    def test_duplicate_semantic_identity_fails_even_when_values_match(self):
        as_of = date(2026, 8, 30)
        point = {
            "date": as_of,
            "known_as_of": "2026-08-30T00:00:00+00:00",
            "value": 78.5,
        }

        with self.assertRaisesRegex(ValueError, "Duplicate.*identity"):
            bounded_price_history(
                {"WTI": [point, dict(point)]},
                [_price_config("WTI", "daily")],
                as_of,
                LIMITS,
            )

    def test_nonfinite_price_is_omitted_and_never_coerced_to_zero(self):
        rows = bounded_price_history(
            {
                "WTI": [
                    {
                        "date": date(2026, 8, 29),
                        "known_as_of": "2026-08-29T00:00:00+00:00",
                        "value": float("nan"),
                    },
                    {
                        "date": date(2026, 8, 30),
                        "known_as_of": "2026-08-30T00:00:00+00:00",
                        "value": 78.5,
                    },
                ]
            },
            [_price_config("WTI", "daily")],
            date(2026, 8, 30),
            LIMITS,
        )

        self.assertEqual([row["value"] for row in rows], [78.5])
        self.assertNotIn(0, [row["value"] for row in rows])

    def test_nonofficial_price_provider_is_not_a_commodity_research_history(self):
        rows = bounded_price_history(
            {"BTC_USD": _price_points(date(2026, 8, 30), count=2, step_days=1)},
            [
                _price_config(
                    "BTC_USD",
                    "daily",
                    provider="yahoo_chart",
                    commodity_code="BTC_USD",
                )
            ],
            date(2026, 8, 30),
            LIMITS,
        )

        self.assertEqual(rows, [])


class BoundedMetricHistoryTests(unittest.TestCase):
    def test_metric_history_is_bounded_sorted_and_preserves_native_units(self):
        as_of = date(2026, 8, 30)
        first = as_of - timedelta(days=161 * 7)
        inputs = [
            _metric_row(first + timedelta(days=index * 7), value=float(index + 1))
            for index in range(162)
        ]

        rows = bounded_metric_history(inputs, as_of, LIMITS)

        self.assertEqual(len(rows), 160)
        self.assertTrue(all(tuple(row) == METRIC_HISTORY_FIELDS for row in rows))
        self.assertEqual(rows[0]["observation_date"], inputs[2]["as_of_date"].isoformat())
        self.assertEqual(rows[-1]["unit"], "native-bcf")
        self.assertEqual(
            [row["observation_date"] for row in rows],
            sorted(row["observation_date"] for row in rows),
        )

    def test_duplicate_metric_identity_fails_and_nonfinite_row_is_omitted(self):
        as_of = date(2026, 8, 30)
        row = _metric_row(as_of)
        with self.assertRaisesRegex(ValueError, "Duplicate.*identity"):
            bounded_metric_history([row, dict(row)], as_of, LIMITS)

        selected = bounded_metric_history(
            [
                _metric_row(as_of - timedelta(days=7), value=-math.inf),
                _metric_row(as_of, value=12.0),
            ],
            as_of,
            LIMITS,
        )
        self.assertEqual([item["value"] for item in selected], [12.0])

    def test_invalid_source_qc_taxonomy_or_timestamp_fails_closed(self):
        as_of = date(2026, 8, 30)
        invalid = (
            (_metric_row(as_of, source_url=""), "source_url"),
            (_metric_row(as_of, qc_flag="FETCH_FAILED"), "qc_flag"),
            (_metric_row(as_of, metric_role="fundamental"), "metric_role"),
            (_metric_row(as_of, measurement_kind="physical_level"), "measurement_kind"),
            (_metric_row(as_of, known_as_of="2026-08-30T12:00:00"), "UTC offset"),
        )
        for row, message in invalid:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    bounded_metric_history([row], as_of, LIMITS)

        self.assertEqual(
            bounded_metric_history(
                [_metric_row(as_of, known_as_of="2026-08-31T00:00:00+00:00")],
                as_of,
                LIMITS,
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
