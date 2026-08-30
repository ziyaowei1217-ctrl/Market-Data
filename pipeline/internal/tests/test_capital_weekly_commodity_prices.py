from __future__ import annotations

import io
import json
import unittest
from datetime import date, datetime

from openpyxl import Workbook

from pipeline.internal.capital_weekly.commodity_prices import (
    parse_eia_price_series,
    parse_world_bank_monthly_prices,
)


WORLD_BANK_COLUMNS = {
    "Natural gas, US": "$/mmbtu",
    "Crude oil, WTI": "$/bbl",
    "Crude oil, Brent": "$/bbl",
    "Copper": "$/mt",
    "Gold": "$/toz",
    "Maize": "$/mt",
    "Soybeans": "$/mt",
    "Wheat, US SRW": "$/mt",
    "Rice, Thai 5%": "$/mt",
    "Cotton, A Index": "$/kg",
    "Sugar, world": "$/kg",
    "Coffee, Arabica": "$/kg",
    "Cocoa": "$/kg",
    "Beef": "$/kg",
}


def _world_bank_fixture(*, omit: str | None = None) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Monthly Prices"
    sheet.append(["World Bank Commodity Price Data (The Pink Sheet)"])
    sheet.append(["Monthly Prices"])
    sheet.append(["Updated 2026-08-04"])
    labels = [label for label in WORLD_BANK_COLUMNS if label != omit]
    sheet.append(["Date", *labels])
    sheet.append(["", *(WORLD_BANK_COLUMNS[label] for label in labels)])
    sheet.append(["2026M05", *(float(index) for index in range(1, len(labels) + 1))])
    sheet.append([datetime(2026, 6, 1), *(float(index) + 0.5 for index in range(1, len(labels) + 1))])
    sheet.append(["2026M07", *(float("nan") if index == 1 else float(index) + 1.0 for index in range(1, len(labels) + 1))])
    stream = io.BytesIO()
    workbook.save(stream)
    return stream.getvalue()


class EiaPriceParserTests(unittest.TestCase):
    def test_filters_exact_series_validates_unit_and_sorts_dates(self):
        fixture = json.dumps(
            {
                "response": {
                    "data": [
                        {
                            "period": "2026-07-02",
                            "series": "RWTC",
                            "series-description": "Cushing WTI Spot Price FOB",
                            "unit": "Dollars per Barrel",
                            "value": "68.25",
                        },
                        {
                            "period": "2026-07-01",
                            "series": "RBRTE",
                            "series-description": "Brent Spot Price",
                            "units": "Dollars per Barrel",
                            "value": "70.00",
                        },
                        {
                            "period": "2026-07-01",
                            "series": "RWTC",
                            "series-description": "Cushing WTI Spot Price FOB",
                            "units": "Dollars per Barrel",
                            "value": 67.5,
                        },
                    ]
                }
            }
        )

        result = parse_eia_price_series(
            fixture,
            "RWTC",
            "Dollars per Barrel",
        )

        self.assertEqual(
            result,
            [
                {
                    "date": date(2026, 7, 1),
                    "value": 67.5,
                    "unit": "Dollars per Barrel",
                },
                {
                    "date": date(2026, 7, 2),
                    "value": 68.25,
                    "unit": "Dollars per Barrel",
                },
            ],
        )

    def test_rejects_unit_mismatch(self):
        fixture = json.dumps(
            {
                "response": {
                    "data": [
                        {
                            "period": "2026-07-01",
                            "series": "RWTC",
                            "unit": "Dollars per Gallon",
                            "value": 2.5,
                        }
                    ]
                }
            }
        )

        with self.assertRaisesRegex(ValueError, "Unexpected EIA unit"):
            parse_eia_price_series(fixture, "RWTC", "Dollars per Barrel")

    def test_rejects_duplicate_dates_and_nonfinite_values(self):
        cases = {
            "duplicate": [
                {"period": "2026-07-01", "series": "RWTC", "unit": "Dollars per Barrel", "value": 1},
                {"period": "2026-07-01", "series": "RWTC", "unit": "Dollars per Barrel", "value": 2},
            ],
            "nonfinite": [
                {"period": "2026-07-01", "series": "RWTC", "unit": "Dollars per Barrel", "value": "NaN"},
            ],
        }
        for label, rows in cases.items():
            with self.subTest(label=label):
                fixture = json.dumps({"response": {"data": rows}})
                with self.assertRaises(ValueError):
                    parse_eia_price_series(
                        fixture,
                        "RWTC",
                        "Dollars per Barrel",
                    )


class WorldBankPriceParserTests(unittest.TestCase):
    def test_finds_exact_columns_and_preserves_month_end_dates_and_units(self):
        parsed = parse_world_bank_monthly_prices(
            _world_bank_fixture(),
            WORLD_BANK_COLUMNS,
        )

        self.assertEqual(set(parsed), set(WORLD_BANK_COLUMNS))
        self.assertEqual(
            parsed["Natural gas, US"],
            [
                {"date": date(2026, 5, 31), "value": 1.0, "unit": "$/mmbtu"},
                {"date": date(2026, 6, 30), "value": 1.5, "unit": "$/mmbtu"},
            ],
        )
        self.assertEqual(
            parsed["Beef"][-1],
            {"date": date(2026, 7, 31), "value": 15.0, "unit": "$/kg"},
        )

    def test_rejects_a_missing_requested_column(self):
        with self.assertRaisesRegex(ValueError, "missing requested column.*Cocoa"):
            parse_world_bank_monthly_prices(
                _world_bank_fixture(omit="Cocoa"),
                {"Cocoa": "$/kg"},
            )

    def test_rejects_a_source_unit_mismatch(self):
        with self.assertRaisesRegex(ValueError, "Unexpected World Bank unit"):
            parse_world_bank_monthly_prices(
                _world_bank_fixture(),
                {"Gold": "$/kg"},
            )


if __name__ == "__main__":
    unittest.main()
