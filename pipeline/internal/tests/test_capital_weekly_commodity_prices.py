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
from pipeline.internal.capital_weekly.macro_assets import load_macro_asset_universe


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


def _world_bank_fixture(
    *,
    heading: str = "Monthly Prices",
    date_header: str = "Date",
    parenthesized_units: bool = False,
    official_missing_marker: bool = False,
    beef_label: str = "Beef",
    gold_unit: str = "$/toz",
    omit: str | None = None,
    duplicate: str | None = None,
    invalid: tuple[str, object] | None = None,
) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Monthly Prices"
    sheet.append(["World Bank Commodity Price Data (The Pink Sheet)"])
    sheet.append([heading])
    sheet.append(["Updated 2026-08-04"])
    labels = [
        beef_label if label == "Beef" else label
        for label in WORLD_BANK_COLUMNS
        if label != omit
    ]
    if duplicate is not None:
        labels.append(duplicate)
    sheet.append([date_header, *labels])
    sheet.append([
        "",
        *(
            (
                f"({gold_unit if label == 'Gold' else WORLD_BANK_COLUMNS[label.removesuffix(' **')]})"
                if parenthesized_units
                else (
                    gold_unit
                    if label == "Gold"
                    else WORLD_BANK_COLUMNS[label.removesuffix(" **")]
                )
            )
            if label.removesuffix(" **") in WORLD_BANK_COLUMNS
            else WORLD_BANK_COLUMNS[label.strip().title()]
            for label in labels
        ),
    ])
    may_values = [float(index) for index in range(1, len(labels) + 1)]
    if official_missing_marker:
        may_values[labels.index("Crude oil, WTI")] = "…"
    sheet.append(["2026M05", *may_values])
    sheet.append([datetime(2026, 6, 1), *(float(index) + 0.5 for index in range(1, len(labels) + 1))])
    july_values = [float(index) + 1.0 for index in range(1, len(labels) + 1)]
    if invalid is not None:
        invalid_label, invalid_value = invalid
        july_values[labels.index(invalid_label)] = invalid_value
    sheet.append(["2026M07", *july_values])
    stream = io.BytesIO()
    workbook.save(stream)
    return stream.getvalue()


class EiaPriceParserTests(unittest.TestCase):
    def test_current_official_eia_price_units_match_production_config(self):
        configs = {
            item.provider_symbol: item
            for item in load_macro_asset_universe()
            if item.series_code in {"WTI", "BRENT", "NATGAS_HH"}
        }
        fixture = json.dumps({
            "response": {
                "data": [
                    {
                        "period": "2026-08-25",
                        "series": series,
                        "series-description": description,
                        "units": "$/BBL",
                        "value": value,
                    }
                    for series, description, value in (
                        ("RWTC", "Cushing, OK WTI Spot Price FOB", "63.37"),
                        ("RBRTE", "Europe Brent Spot Price FOB", "67.22"),
                        (
                            "RNGWHHD",
                            "Henry Hub Natural Gas Spot Price",
                            "2.83",
                        ),
                    )
                ]
            }
        })
        official_units = {
            "RWTC": "$/BBL",
            "RBRTE": "$/BBL",
            "RNGWHHD": "$/MMBTU",
        }
        payload = json.loads(fixture)
        for row in payload["response"]["data"]:
            row["units"] = official_units[row["series"]]
        fixture = json.dumps(payload)

        for series, config in configs.items():
            with self.subTest(series=series):
                try:
                    rows = parse_eia_price_series(
                        fixture,
                        series,
                        config.level_unit,
                    )
                except ValueError as error:
                    self.fail(str(error))
                self.assertEqual(rows[-1]["unit"], official_units[series])

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
    def test_accepts_current_official_monthly_prices_heading(self):
        try:
            production_columns = {
                item.provider_symbol: item.level_unit
                for item in load_macro_asset_universe()
                if item.provider == "world_bank_pink_sheet"
            }
            parsed = parse_world_bank_monthly_prices(
                _world_bank_fixture(
                    heading="monthly prices in nominal US dollars, 1960 to present",
                    date_header="",
                    parenthesized_units=True,
                    official_missing_marker=True,
                    beef_label="Beef **",
                    gold_unit="$/troy oz",
                ),
                production_columns,
            )
        except ValueError as error:
            self.fail(str(error))

        self.assertEqual(parsed["Gold"][-1]["date"], date(2026, 7, 31))

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
                {"date": date(2026, 7, 31), "value": 2.0, "unit": "$/mmbtu"},
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

    def test_rejects_duplicate_normalized_requested_headers(self):
        with self.assertRaisesRegex(
            ValueError,
            "duplicate requested column.*Gold",
        ):
            parse_world_bank_monthly_prices(
                _world_bank_fixture(duplicate="  GOLD  "),
                {"Gold": "$/toz"},
            )

    def test_rejects_malformed_or_nonfinite_requested_values_on_dated_rows(self):
        for label, invalid_value in (
            ("malformed", "not-a-number"),
            ("nonfinite", float("nan")),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    ValueError,
                    "Invalid World Bank value.*Gold.*2026-07-31",
                ):
                    parse_world_bank_monthly_prices(
                        _world_bank_fixture(invalid=("Gold", invalid_value)),
                        {"Gold": "$/toz"},
                    )


if __name__ == "__main__":
    unittest.main()
