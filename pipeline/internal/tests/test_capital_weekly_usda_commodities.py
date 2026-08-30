from __future__ import annotations

import json
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pipeline.internal.capital_weekly.context.usda_commodities import (
    calculate_stock_to_use,
    parse_esr_records,
    parse_psd_records,
    parse_usda_lookup,
)


FIXTURES = Path(__file__).with_name("fixtures") / "usda"
HONG_KONG = ZoneInfo("Asia/Hong_Kong")


def fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


PSD_SPEC = {
    "commodity_code": "CORN",
    "commodity_family": "grains_oilseeds",
    "commodity_api_code": "0440000",
    "country_code": "00",
    "country_name": "World",
    "market_year": 2026,
    "attributes": {
        "beginning_stocks": "1",
        "production": "4",
        "imports": "6",
        "exports": "7",
        "feed_use": "10",
        "industrial_use": "11",
        "domestic_use": "12",
        "ending_stocks": "13",
    },
    "units": {"8": "1000 MT"},
}


class USDACommodityTests(unittest.TestCase):
    def test_lookup_resolves_each_official_display_name_to_one_exact_code(self):
        lookups = fixture("psd_lookups.json")

        self.assertEqual(
            parse_usda_lookup(
                lookups["commodities"],
                ("commodityName", "commodityCode"),
            ),
            {"Corn": "0440000", "Oilseed, Soybean": "2222000"},
        )
        self.assertEqual(
            parse_usda_lookup(
                lookups["attributes"],
                ("attributeName", "attributeId"),
            )["Ending Stocks"],
            "13",
        )

    def test_lookup_fails_closed_for_duplicate_missing_or_blank_identity(self):
        with self.assertRaisesRegex(ValueError, "duplicate official display name"):
            parse_usda_lookup(
                [
                    {"commodityName": "Corn", "commodityCode": "0440000"},
                    {"commodityName": "Corn", "commodityCode": "0440001"},
                ],
                ("commodityName", "commodityCode"),
            )
        with self.assertRaisesRegex(ValueError, "missing lookup field"):
            parse_usda_lookup(
                [{"commodityName": "Corn"}],
                ("commodityName", "commodityCode"),
            )
        with self.assertRaisesRegex(ValueError, "blank lookup identity"):
            parse_usda_lookup(
                [{"unitDescription": "", "unitId": 8}],
                ("unitDescription", "unitId"),
            )

    def test_psd_selects_only_latest_release_vintage_known_by_target_sunday(self):
        records = parse_psd_records(
            fixture("psd_records.json"),
            PSD_SPEC,
            datetime(2026, 8, 30, 23, 59, 59, tzinfo=HONG_KONG),
        )

        self.assertEqual(len(records), 8)
        self.assertEqual({row["release_date"] for row in records}, {
            "2026-08-12T12:00:00-04:00"
        })
        production = next(row for row in records if row["attribute"] == "production")
        self.assertEqual(production["value"], 1_210_000)
        self.assertEqual(production["unit"], "1000 MT")

    def test_psd_emits_supply_trade_and_supported_use_attributes_in_native_units(self):
        records = parse_psd_records(
            fixture("psd_records.json"),
            PSD_SPEC,
            datetime(2026, 8, 30, 23, 59, 59, tzinfo=HONG_KONG),
        )

        self.assertEqual(
            {row["attribute"] for row in records},
            {
                "beginning_stocks", "production", "imports", "exports",
                "feed_use", "industrial_use", "domestic_use", "ending_stocks",
            },
        )
        self.assertEqual({row["unit"] for row in records}, {"1000 MT"})
        self.assertTrue(all(row["commodity_code"] == "CORN" for row in records))

    def test_stock_to_use_requires_same_release_and_unit(self):
        records = parse_psd_records(
            fixture("psd_records.json"),
            PSD_SPEC,
            datetime(2026, 8, 30, 23, 59, 59, tzinfo=HONG_KONG),
        )

        ratio = calculate_stock_to_use(records)

        self.assertEqual(ratio["attribute"], "stock_to_use")
        self.assertAlmostEqual(ratio["value"], 166_000 / 1_070_000)
        self.assertEqual(ratio["unit"], "ratio")
        self.assertEqual(ratio["release_date"], "2026-08-12T12:00:00-04:00")

    def test_stock_to_use_returns_none_for_missing_zero_or_mismatched_denominator(self):
        common = {
            "commodity_code": "CORN", "commodity_family": "grains_oilseeds",
            "country_code": "00", "country_name": "World", "market_year": 2026,
            "release_date": "2026-08-12T12:00:00-04:00", "unit_code": "8",
            "unit": "1000 MT",
        }
        ending = {**common, "attribute": "ending_stocks", "value": 10}

        self.assertIsNone(calculate_stock_to_use([ending]))
        self.assertIsNone(calculate_stock_to_use([
            ending, {**common, "attribute": "domestic_use", "value": 0}
        ]))
        self.assertIsNone(calculate_stock_to_use([
            ending,
            {
                **common,
                "attribute": "domestic_use",
                "value": 100,
                "release_date": "2026-09-12T12:00:00-04:00",
            },
        ]))

    def test_esr_emits_only_release_eligible_weekly_trade_metrics(self):
        spec = {
            "commodity_code": "CORN",
            "commodity_family": "grains_oilseeds",
            "commodity_api_code": "101",
            "country_name": "All destinations",
            "aggregate_all_countries": True,
            "market_year": 2026,
            "unit_code": "1",
            "unit": "Metric Tons",
        }

        records = parse_esr_records(
            fixture("esr_records.json"),
            spec,
            datetime(2026, 8, 30, 23, 59, 59, tzinfo=HONG_KONG),
        )

        self.assertEqual(
            [(row["metric"], row["value"]) for row in records],
            [
                ("net_sales", 210_000),
                ("weekly_exports", 340_000),
                ("outstanding_sales", 4_600_000),
            ],
        )
        self.assertEqual({row["unit"] for row in records}, {"Metric Tons"})
        self.assertEqual({row["release_date"] for row in records}, {
            "2026-08-27T08:30:00-04:00"
        })
        self.assertEqual({row["week_ending_date"] for row in records}, {
            "2026-08-20"
        })

    def test_esr_validates_units_only_after_selecting_the_eligible_release_week(self):
        spec = {
            "commodity_code": "CORN",
            "commodity_family": "grains_oilseeds",
            "commodity_api_code": "101",
            "country_name": "All destinations",
            "aggregate_all_countries": True,
            "market_year": 2026,
            "unit_code": "1",
            "unit": "Metric Tons",
        }
        records = fixture("esr_records.json")
        future_bad_unit = {
            **records[-1],
            "countryCode": 9999,
            "unitId": 999,
        }

        selected = parse_esr_records(
            [*records, future_bad_unit],
            spec,
            datetime(2026, 8, 30, 23, 59, 59, tzinfo=HONG_KONG),
        )

        self.assertEqual(
            [(row["metric"], row["value"]) for row in selected],
            [
                ("net_sales", 210_000),
                ("weekly_exports", 340_000),
                ("outstanding_sales", 4_600_000),
            ],
        )

        eligible_bad_unit = {
            **records[0],
            "countryCode": 9999,
            "unitId": 999,
        }
        with self.assertRaisesRegex(ValueError, "unexpected native unit"):
            parse_esr_records(
                [records[0], records[1], eligible_bad_unit],
                spec,
                datetime(2026, 8, 30, 23, 59, 59, tzinfo=HONG_KONG),
            )


if __name__ == "__main__":
    unittest.main()
