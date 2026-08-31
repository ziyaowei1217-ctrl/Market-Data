import json
import unittest
from datetime import date
from dataclasses import replace

from pipeline.internal.common import load_config_rows
from pipeline.internal.capital_weekly.context.commodities import (
    calculate_weekly_change,
    eia_not_configured_result,
    parse_eia_series,
)
from pipeline.internal.capital_weekly.context import eia_commodities as eia_module
from pipeline.internal.capital_weekly.context.eia_commodities import (
    EiaBatchError,
    EiaBatchSpec,
    build_eia_batch_specs,
    eia_response_total,
    fetch_eia_batches,
    latest_and_changes,
    parse_eia_metric_series,
)


class CommodityFundamentalTests(unittest.TestCase):
    def eia_spec(self, **overrides):
        spec = {
            "provider": "eia_natural_gas",
            "commodity_code": "NATGAS_HH",
            "commodity_family": "natural_gas",
            "route": "natural-gas/stor/wkly",
            "frequency": "weekly",
            "facets": {
                "duoarea": "R48",
                "process": "SWO",
                "series": "NW2_EPG0_SWO_R48_BCF",
            },
            "metric_code": "eia_ng_storage_lower48",
            "metric_name": "Lower 48 working gas in underground storage",
            "measurement_kind": "inventory",
            "source_description": (
                "Lower 48 Working Gas in Underground Storage "
                "(Billion Cubic Feet)"
            ),
            "expected_unit": "BCF",
            "freshness_days": "10",
        }
        spec.update(overrides)
        return spec

    def test_eia_price_natural_gas_and_petroleum_routes_use_exact_bounded_batches(self):
        rows = [
            self.eia_spec(
                route=route,
                frequency=frequency,
                facets={"series": series},
                metric_code=f"metric_{index}",
            )
            for index, (route, frequency, series) in enumerate(
                (
                    ("petroleum/pri/spt", "daily", "RWTC"),
                    ("petroleum/pri/spt", "daily", "RBRTE"),
                    ("natural-gas/pri/fut", "daily", "RNGWHHD"),
                    ("natural-gas/sum/snd", "monthly", "N9070US2"),
                    ("natural-gas/sum/snd", "monthly", "N3010US2"),
                    ("natural-gas/sum/snd", "monthly", "N3020US2"),
                    ("petroleum/sum/sndw", "weekly", "WCESTUS1"),
                    ("petroleum/sum/sndw", "weekly", "WGTSTUS1"),
                    ("petroleum/sum/sndw", "weekly", "WDISTUS1"),
                )
            )
        ]

        batches = build_eia_batch_specs(
            rows,
            request_batch_size=2,
            page_length=7,
            start="2026-01-01",
            end="2026-08-23",
        )

        self.assertEqual(
            [(item.route, item.frequency, len(item.facets["series"])) for item in batches],
            [
                ("natural-gas/pri/fut", "daily", 1),
                ("natural-gas/sum/snd", "monthly", 2),
                ("natural-gas/sum/snd", "monthly", 1),
                ("petroleum/pri/spt", "daily", 2),
                ("petroleum/sum/sndw", "weekly", 2),
                ("petroleum/sum/sndw", "weekly", 1),
            ],
        )
        self.assertTrue(all(item.page_length == 7 for item in batches))

    def test_fetch_eia_batches_validates_metadata_before_paginated_rows_and_coverage(self):
        specs = [
            EiaBatchSpec(
                route="petroleum/pri/spt",
                facets={"series": ("RWTC", "RBRTE")},
                frequency="daily",
                start="2026-08-01",
                end="2026-08-23",
                page_length=2,
            )
        ]
        metadata = {
            "RWTC": {
                "facets": {"series": "RWTC"},
                "source_description": "Cushing, OK WTI Spot Price FOB",
                "expected_unit": "$/BBL",
            },
            "RBRTE": {
                "facets": {"series": "RBRTE"},
                "source_description": "Europe Brent Spot Price FOB",
                "expected_unit": "$/BBL",
            },
        }

        class Client:
            def __init__(self):
                self.calls = []

            def fetch_metadata(self, spec, expected):
                self.calls.append(("metadata", spec.route, tuple(sorted(expected))))

            def fetch_page(self, spec, *, offset, length):
                self.calls.append(("page", offset, length))
                rows = [
                    {
                        "period": "2026-08-21",
                        "series": "RWTC",
                        "series-description": "Cushing, OK WTI Spot Price FOB",
                        "units": "$/BBL",
                        "value": "63.0",
                    },
                    {
                        "period": "2026-08-20",
                        "series": "RWTC",
                        "series-description": "Cushing, OK WTI Spot Price FOB",
                        "units": "$/BBL",
                        "value": "62.0",
                    },
                    {
                        "period": "2026-08-21",
                        "series": "RBRTE",
                        "series-description": "Europe Brent Spot Price FOB",
                        "units": "$/BBL",
                        "value": "67.0",
                    },
                ]
                page = rows[offset : offset + length]
                return {"response": {"total": len(rows), "data": page}}

        client = Client()
        pages = fetch_eia_batches(client, specs, expected_metadata=metadata)

        self.assertEqual(
            client.calls,
            [
                ("metadata", "petroleum/pri/spt", ("RBRTE", "RWTC")),
                ("page", 0, 2),
                ("page", 2, 2),
            ],
        )
        self.assertEqual(sum(len(page["response"]["data"]) for page in pages), 3)

        missing = Client()
        missing.fetch_page = lambda spec, *, offset, length: {
            "response": {
                "total": 1,
                "data": [{
                    "period": "2026-08-21",
                    "series": "RWTC",
                    "series-description": "Cushing, OK WTI Spot Price FOB",
                    "units": "$/BBL",
                    "value": "63.0",
                }],
            }
        }
        with self.assertRaisesRegex(ValueError, "missing.*RBRTE"):
            fetch_eia_batches(missing, specs, expected_metadata=metadata)

        duplicate = [specs[0], replace(specs[0], facets={"series": ("RWTC",)})]
        with self.assertRaisesRegex(ValueError, "duplicate.*RWTC"):
            fetch_eia_batches(Client(), duplicate, expected_metadata=metadata)

    def test_fetch_eia_batches_requires_explicit_strict_and_consistent_total(self):
        spec = EiaBatchSpec(
            route="petroleum/pri/spt",
            facets={"series": ("RWTC",)},
            frequency="daily",
            start="2026-08-01",
            end="2026-08-23",
            page_length=1,
        )
        metadata = {
            "RWTC": {
                "facets": {"series": "RWTC"},
                "source_description": "Cushing, OK WTI Spot Price FOB",
                "expected_unit": "$/BBL",
            }
        }

        def row(period):
            return {
                "period": period,
                "series": "RWTC",
                "series-description": "Cushing, OK WTI Spot Price FOB",
                "units": "$/BBL",
                "value": "63.0",
            }

        class Client:
            def __init__(self, pages):
                self.pages = list(pages)

            def fetch_metadata(self, _spec, _expected):
                return None

            def fetch_page(self, _spec, *, offset, length):
                self.request = (offset, length)
                return self.pages.pop(0)

        malformed = (
            ("missing", {"response": {"data": [row("2026-08-21")]}}),
            ("negative", {"response": {"total": -1, "data": [row("2026-08-21")]}}),
            ("float", {"response": {"total": 1.5, "data": [row("2026-08-21")]}}),
            ("noncanonical", {"response": {"total": "01", "data": [row("2026-08-21")]}}),
        )
        for label, payload in malformed:
            with self.subTest(label=label):
                with self.assertRaisesRegex(EiaBatchError, "total") as raised:
                    fetch_eia_batches(
                        Client([payload]), [spec], expected_metadata=metadata
                    )
                self.assertEqual(raised.exception.phase, "coverage")

        inconsistent = Client([
            {"response": {"total": 2, "data": [row("2026-08-21")]}},
            {"response": {"total": 3, "data": [row("2026-08-20")]}},
            {"response": {"total": 3, "data": [row("2026-08-19")]}},
        ])
        with self.assertRaisesRegex(EiaBatchError, "changed across pages") as raised:
            fetch_eia_batches(inconsistent, [spec], expected_metadata=metadata)
        self.assertEqual(raised.exception.phase, "coverage")

    def test_eia_response_total_matches_official_endpoint_contracts(self):
        cases = (
            (
                "metadata",
                {"facets": [{"id": "RWTC", "name": "WTI"}], "totalFacets": 1},
            ),
            (
                "data",
                {"data": [{"period": "2026-08-21"}], "total": "1"},
            ),
        )
        for label, response in cases:
            with self.subTest(label=label):
                self.assertEqual(
                    eia_response_total(
                        response,
                        offset=0,
                        page_count=1,
                        requested_length=400,
                    ),
                    1,
                )

        for label, response in (
            ("metadata missing totalFacets", {"facets": []}),
            ("metadata string totalFacets", {"facets": [], "totalFacets": "0"}),
            ("ambiguous metadata totals", {"facets": [], "totalFacets": 0, "total": 0}),
            ("noncanonical data total", {"data": [], "total": "00"}),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "total"):
                    eia_response_total(
                        response,
                        offset=0,
                        page_count=0,
                        requested_length=400,
                    )

    def test_eia_metadata_all_facets_contract_is_exact_and_not_data_pagination(self):
        facet_ids = [f"SERIES_{index:03d}" for index in range(608)]
        response = {
            "facets": [{"id": identifier} for identifier in facet_ids],
            "totalFacets": 608,
        }
        validator = getattr(eia_module, "eia_metadata_facet_ids", None)
        self.assertIsNotNone(validator)
        self.assertEqual(validator(response), set(facet_ids))

        malformed = (
            (
                "non-integral total",
                {"facets": [{"id": "A"}], "totalFacets": "1"},
                "totalFacets",
            ),
            (
                "inconsistent total",
                {"facets": [{"id": "A"}], "totalFacets": 2},
                "count",
            ),
            (
                "duplicate identifier",
                {
                    "facets": [{"id": "A"}, {"id": "A"}],
                    "totalFacets": 2,
                },
                "duplicate",
            ),
            (
                "ambiguous data response",
                {
                    "facets": [{"id": "A"}],
                    "totalFacets": 1,
                    "data": [],
                },
                "ambiguous",
            ),
        )
        for label, malformed_response, message in malformed:
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, message):
                    validator(malformed_response)

    def test_current_lower_48_description_matches_production_config(self):
        spec = next(
            item
            for item in load_config_rows("context.eia_series")
            if item["metric_code"] == "eia_ng_storage_lower48"
        )
        payload = {
            "response": {
                "data": [{
                    "period": "2026-08-21",
                    "duoarea": "R48",
                    "process": "SWO",
                    "series": "NW2_EPG0_SWO_R48_BCF",
                    "series-description": (
                        "Weekly Lower 48 States Natural Gas Working Underground "
                        "Storage (Billion Cubic Feet)"
                    ),
                    "units": "BCF",
                    "value": "3125",
                }]
            }
        }

        try:
            rows = parse_eia_metric_series(json.dumps(payload), spec)
        except ValueError as error:
            self.fail(str(error))

        self.assertEqual(rows[-1]["metric_code"], "eia_ng_storage_lower48")

    def test_metric_parser_requires_exact_facets_description_and_native_unit(self):
        payload = {
            "response": {
                "data": [
                    {
                        "period": "2026-08-21",
                        "duoarea": "R48",
                        "process": "SWO",
                        "series": "NW2_EPG0_SWO_R48_BCF",
                        "series-description": (
                            "Lower 48 Working Gas in Underground Storage "
                            "(Billion Cubic Feet)"
                        ),
                        "units": "BCF",
                        "value": "3125",
                    }
                ]
            }
        }

        rows = parse_eia_metric_series(json.dumps(payload), self.eia_spec())

        self.assertEqual(rows[0]["value"], 3125.0)
        self.assertEqual(rows[0]["unit"], "BCF")
        self.assertEqual(rows[0]["commodity_family"], "natural_gas")
        for field, value, message in (
            ("process", "SNO", "facet"),
            ("series", "NW2_EPG0_SWO_R31_BCF", "facet"),
            ("series-description", "renamed upstream", "description"),
            ("units", "MMCF", "unit"),
        ):
            changed = json.loads(json.dumps(payload))
            changed["response"]["data"][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                parse_eia_metric_series(json.dumps(changed), self.eia_spec())

    def test_metric_parser_rejects_duplicates_nonfinite_and_unknown_units(self):
        base = {
            "period": "2026-08-21",
            "duoarea": "R48",
            "process": "SWO",
            "series": "NW2_EPG0_SWO_R48_BCF",
            "series-description": (
                "Lower 48 Working Gas in Underground Storage "
                "(Billion Cubic Feet)"
            ),
            "units": "BCF",
            "value": "3125",
        }
        duplicate = {"response": {"data": [base, dict(base)]}}
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            parse_eia_metric_series(json.dumps(duplicate), self.eia_spec())

        nonfinite = {"response": {"data": [{**base, "value": "NaN"}]}}
        with self.assertRaisesRegex(ValueError, "finite"):
            parse_eia_metric_series(json.dumps(nonfinite), self.eia_spec())

        unknown_unit = {"response": {"data": [{**base, "units": "mystery"}]}}
        with self.assertRaisesRegex(ValueError, "unit"):
            parse_eia_metric_series(json.dumps(unknown_unit), self.eia_spec())

    def test_monthly_route_requires_month_period_and_preserves_native_unit(self):
        spec = self.eia_spec(
            route="natural-gas/sum/snd",
            frequency="monthly",
            facets={"series": "N9070US2"},
            metric_code="eia_ng_dry_production",
            metric_name="U.S. dry natural gas production",
            measurement_kind="supply",
            source_description="U.S. Dry Natural Gas Production (MMcf)",
            expected_unit="MMCF",
            freshness_days="10",
        )
        row = {
            "period": "2026-06",
            "series": "N9070US2",
            "series-description": "U.S. Dry Natural Gas Production (MMcf)",
            "units": "MMCF",
            "value": "3210000",
        }

        parsed = parse_eia_metric_series(
            json.dumps({"response": {"data": [row]}}),
            spec,
        )
        self.assertEqual(parsed[0]["period"], "2026-06")
        self.assertEqual(parsed[0]["unit"], "MMCF")

        with self.assertRaisesRegex(ValueError, "frequency"):
            parse_eia_metric_series(
                json.dumps({"response": {"data": [{**row, "period": "2026-06-30"}]}}),
                spec,
            )

    def test_cutoff_precedes_latest_selection_and_change_calculation(self):
        rows = [
            {
                "period": "2026-08-28",
                "known_as_of": "2026-08-28T12:00:00-04:00",
                "metric_code": "storage",
                "metric_name": "Storage",
                "measurement_kind": "inventory",
                "value": 999.0,
                "unit": "BCF",
            },
            {
                "period": "2026-08-14",
                "known_as_of": "2026-08-15T12:00:00-04:00",
                "metric_code": "storage",
                "metric_name": "Storage",
                "measurement_kind": "inventory",
                "value": 3000.0,
                "unit": "BCF",
            },
            {
                "period": "2026-08-21",
                "known_as_of": "2026-08-24T00:00:00+08:00",
                "metric_code": "storage",
                "metric_name": "Storage",
                "measurement_kind": "inventory",
                "value": 3060.0,
                "unit": "BCF",
            },
            {
                "period": "2026-08-07",
                "known_as_of": "2026-08-08T12:00:00-04:00",
                "metric_code": "storage",
                "metric_name": "Storage",
                "measurement_kind": "inventory",
                "value": 2975.0,
                "unit": "BCF",
            },
        ]

        metrics = latest_and_changes(rows, date(2026, 8, 23))

        self.assertEqual(
            [(row["metric_code"], row["value"]) for row in metrics],
            [
                ("storage", 3000.0),
                ("storage_change", 25.0),
                ("storage_change_pct", 25.0 / 2975.0),
            ],
        )
        self.assertTrue(all(row["period"] == "2026-08-14" for row in metrics))

    def test_seasonal_deviation_requires_five_prior_same_week_observations(self):
        rows = [
            {
                "period": period,
                "metric_code": "storage",
                "metric_name": "Storage",
                "measurement_kind": "inventory",
                "seasonal_deviation": True,
                "value": value,
                "unit": "BCF",
            }
            for period, value in (
                ("2021-08-27", 100.0),
                ("2022-08-26", 110.0),
                ("2023-08-25", 120.0),
                ("2024-08-23", 130.0),
                ("2025-08-22", 140.0),
                ("2026-08-21", 150.0),
            )
        ]

        complete = latest_and_changes(rows, date(2026, 8, 23))
        seasonal = complete[-1]
        self.assertEqual(seasonal["metric_code"], "storage_seasonal_deviation")
        self.assertEqual(seasonal["value"], 30.0)
        self.assertEqual(seasonal["measurement_kind"], "inventory")
        self.assertIn("formula_version=eia-seasonal-v1", seasonal["reference_period"])

        insufficient = latest_and_changes(rows[1:], date(2026, 8, 23))
        self.assertNotIn(
            "storage_seasonal_deviation",
            {row["metric_code"] for row in insufficient},
        )

    def test_seasonal_deviation_uses_explicit_booleans_not_truthy_strings(self):
        payload = {
            "response": {
                "data": [
                    {
                        "period": "2026-08-21",
                        "duoarea": "R48",
                        "process": "SWO",
                        "series": "NW2_EPG0_SWO_R48_BCF",
                        "series-description": (
                            "Lower 48 Working Gas in Underground Storage "
                            "(Billion Cubic Feet)"
                        ),
                        "units": "BCF",
                        "value": "3125",
                    }
                ]
            }
        }
        for configured, expected in (
            (True, True),
            (False, False),
            ("true", True),
            ("false", False),
        ):
            with self.subTest(configured=configured):
                rows = parse_eia_metric_series(
                    json.dumps(payload),
                    self.eia_spec(seasonal_deviation=configured),
                )
                self.assertIs(rows[0]["seasonal_deviation"], expected)

        with self.assertRaisesRegex(ValueError, "seasonal_deviation"):
            parse_eia_metric_series(
                json.dumps(payload),
                self.eia_spec(seasonal_deviation="yes"),
            )

    def test_eia_parser_validates_units_and_orders_periods(self):
        payload = {
            "response": {
                "data": [
                    {
                        "period": "2026-07-24",
                        "value": "425000",
                        "series-description": "U.S. Ending Stocks of Crude Oil",
                        "unit": "Thousand Barrels",
                    },
                    {
                        "period": "2026-07-17",
                        "value": "420000",
                        "series-description": "U.S. Ending Stocks of Crude Oil",
                        "unit": "Thousand Barrels",
                    },
                ]
            }
        }

        rows = parse_eia_series(
            json.dumps(payload),
            metric_code="eia_crude_stocks",
            expected_unit="Thousand Barrels",
        )

        self.assertEqual([row["period"] for row in rows], ["2026-07-17", "2026-07-24"])
        self.assertEqual(rows[-1]["value"], 425000.0)
        self.assertEqual(rows[-1]["unit"], "Thousand Barrels")

    def test_eia_parser_accepts_the_current_plural_units_code(self):
        payload = {
            "response": {
                "data": [
                    {
                        "period": "2026-08-21",
                        "value": "415401",
                        "series-description": (
                            "U.S. Ending Stocks excluding SPR of Crude Oil "
                            "and Petroleum Products (Thousand Barrels)"
                        ),
                        "units": "MBBL",
                    }
                ]
            }
        }

        rows = parse_eia_series(
            json.dumps(payload),
            metric_code="eia_weekly_petroleum_wtestus1",
            expected_unit="Thousand Barrels",
        )

        self.assertEqual(rows[0]["unit"], "Thousand Barrels")

    def test_eia_parser_rejects_unexpected_units_and_duplicate_periods(self):
        wrong_unit = {
            "response": {
                "data": [
                    {"period": "2026-07-24", "value": "1", "unit": "Percent"}
                ]
            }
        }
        with self.assertRaisesRegex(ValueError, "unit"):
            parse_eia_series(
                json.dumps(wrong_unit),
                metric_code="stocks",
                expected_unit="Thousand Barrels",
            )

        duplicate = {
            "response": {
                "data": [
                    {"period": "2026-07-24", "value": "1", "unit": "Barrels"},
                    {"period": "2026-07-24", "value": "2", "unit": "Barrels"},
                ]
            }
        }
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            parse_eia_series(
                json.dumps(duplicate),
                metric_code="stocks",
                expected_unit="Barrels",
            )

    def test_weekly_change_uses_latest_two_observations(self):
        rows = [
            {"period": "2026-07-10", "value": 100.0},
            {"period": "2026-07-17", "value": 110.0},
            {"period": "2026-07-24", "value": 107.0},
        ]

        result = calculate_weekly_change(rows)

        self.assertEqual(result["period"], "2026-07-24")
        self.assertEqual(result["change"], -3.0)
        self.assertAlmostEqual(result["change_pct"], -3 / 110)

    def test_missing_eia_key_is_visible_not_configured_status(self):
        result = eia_not_configured_result()

        self.assertEqual(result.category, "commodity_fundamentals")
        self.assertEqual(result.status, "NOT_CONFIGURED")
        self.assertEqual(result.rows, [])
        self.assertIn("EIA_API_KEY", result.notes)


if __name__ == "__main__":
    unittest.main()
