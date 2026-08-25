from datetime import date
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from pipeline.capital_weekly.macro_assets import fetch_macro_assets
from pipeline.scripts import fetch_macro_assets as fetch_cli


class MacroAsOfTests(unittest.TestCase):
    def test_explicit_as_of_date_excludes_later_observations(self):
        header = (
            "asset_class,group,series_code,name_cn,name_en,provider,provider_symbol,"
            "source,source_url,frequency,level_unit,change_unit,sort_order,notes\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            universe = Path(directory) / "universe.csv"
            universe.write_text(
                header
                + "foreign_exchange,fx,TEST,测试,Test,fred,TEST,FRED,"
                "https://example.test,daily,index_level,pct,1,test\n",
                encoding="utf-8",
            )
            history = [
                {"date": date(2025, 12, 31), "value": 90.0},
                {"date": date(2026, 7, 24), "value": 100.0},
                {"date": date(2026, 7, 31), "value": 105.0},
                {"date": date(2026, 8, 3), "value": 999.0},
            ]
            with patch(
                "pipeline.capital_weekly.macro_assets._fetch_config_history",
                return_value=(history, b"fixture", "https://example.test"),
            ):
                detail, source_log = fetch_macro_assets(
                    universe,
                    as_of_date=date(2026, 8, 2),
                )

        self.assertEqual(detail.loc[0, "latest_date"], "2026-07-31")
        self.assertEqual(detail.loc[0, "latest_value"], 105.0)
        self.assertEqual(source_log.loc[0, "latest_date"], "2026-07-31")

    def test_new_treasury_and_inflation_series_apply_cutoff_before_derivation(self):
        header = (
            "asset_class,group,series_code,name_cn,name_en,provider,provider_symbol,"
            "source,source_url,frequency,level_unit,change_unit,sort_order,notes,"
            "calculation_id,formula_version,input_series_codes\n"
        )
        rows = (
            "fixed_income,sovereign_curve,UST10Y,名义10年,Nominal 10Y,us_treasury,"
            "10-year,Treasury,https://example.test/nominal,daily,percent,bp,1,,,,\n"
            "fixed_income,sovereign_curve,UST5Y,名义5年,Nominal 5Y,us_treasury,"
            "5-year,Treasury,https://example.test/nominal,daily,percent,bp,2,,,,\n"
            "fixed_income,sovereign_curve,UST_REAL5Y,实际5年,Real 5Y,"
            "us_treasury_real,5-year,Treasury,https://example.test/real,daily,"
            "percent,bp,3,,,,\n"
            "fixed_income,sovereign_curve,UST_REAL10Y,实际10年,Real 10Y,"
            "us_treasury_real,10-year,Treasury,https://example.test/real,daily,"
            "percent,bp,4,,,,\n"
            "fixed_income,inflation_expectations,US_BE5Y,5年盈亏平衡,5Y Breakeven,"
            "calculated,UST5Y-UST_REAL5Y,Calculated,https://example.test/calculated,"
            "daily,percent,bp,5,Registered,breakeven,breakeven-v1,UST5Y|UST_REAL5Y\n"
            "fixed_income,inflation_expectations,US_BE10Y,10年盈亏平衡,10Y Breakeven,"
            "calculated,UST10Y-UST_REAL10Y,Calculated,https://example.test/calculated,"
            "daily,percent,bp,6,Registered,breakeven,breakeven-v1,UST10Y|UST_REAL10Y\n"
            "fixed_income,inflation_expectations,US_5Y5Y,5年5年远期通胀,5Y5Y Inflation,"
            "calculated,US_BE5Y-US_BE10Y,Calculated,https://example.test/calculated,"
            "daily,percent,bp,7,Registered,five_year_five_year,"
            "forward-inflation-v1,US_BE5Y|US_BE10Y\n"
        )
        latest_values = {
            "UST10Y": 4.2,
            "UST5Y": 4.0,
            "UST_REAL5Y": 1.9,
            "UST_REAL10Y": 2.0,
        }

        def fake_fetch(config, session, as_of_date=None):
            latest = latest_values[config.series_code]
            return (
                [
                    {"date": date(2025, 12, 31), "value": latest - 0.5},
                    {"date": date(2026, 8, 7), "value": latest},
                    {"date": date(2026, 8, 10), "value": latest + 0.2},
                ],
                b"fixture",
                config.source_url,
            )

        with tempfile.TemporaryDirectory() as directory:
            universe = Path(directory) / "universe.csv"
            universe.write_text(header + rows, encoding="utf-8")
            with patch(
                "pipeline.capital_weekly.macro_assets._fetch_config_history",
                side_effect=fake_fetch,
            ):
                detail, source_log = fetch_macro_assets(
                    universe,
                    as_of_date=date(2026, 8, 9),
                )

        new_codes = {
            "UST5Y",
            "UST_REAL5Y",
            "UST_REAL10Y",
            "US_BE5Y",
            "US_BE10Y",
            "US_5Y5Y",
        }
        new_detail = detail.loc[detail["series_code"].isin(new_codes)]
        new_audit = source_log.loc[source_log["series_code"].isin(new_codes)]
        self.assertEqual(set(new_detail["series_code"]), new_codes)
        self.assertTrue((new_detail["latest_date"] == "2026-08-07").all())
        self.assertTrue((new_audit["latest_date"] == "2026-08-07").all())
        self.assertTrue((new_audit["known_as_of"] == "2026-08-07").all())
        expected_lineage = {
            "US_BE5Y": (
                "breakeven",
                "breakeven-v1",
                "UST5Y|UST_REAL5Y",
            ),
            "US_BE10Y": (
                "breakeven",
                "breakeven-v1",
                "UST10Y|UST_REAL10Y",
            ),
            "US_5Y5Y": (
                "five_year_five_year",
                "forward-inflation-v1",
                "US_BE5Y|US_BE10Y",
            ),
        }
        for series_code, expected in expected_lineage.items():
            with self.subTest(series_code=series_code):
                audit = new_audit.loc[
                    new_audit["series_code"] == series_code
                ].iloc[0]
                self.assertEqual(
                    (
                        audit["calculation_id"],
                        audit["formula_version"],
                        audit["input_series_codes"],
                    ),
                    expected,
                )
        observed_audit = new_audit.loc[
            new_audit["series_code"].isin(
                {"UST5Y", "UST_REAL5Y", "UST_REAL10Y"}
            )
        ]
        self.assertTrue((observed_audit["calculation_id"] == "").all())
        self.assertTrue((observed_audit["formula_version"] == "").all())
        self.assertTrue((observed_audit["input_series_codes"] == "").all())

    def test_cli_forwards_explicit_as_of_date_to_fetcher(self):
        detail = pd.DataFrame(
            {"asset_class": ["fixed_income"], "qc_flag": ["OK"]}
        )
        source_log = pd.DataFrame({"status": ["OK"]})

        with tempfile.TemporaryDirectory() as directory, patch(
            "pipeline.scripts.fetch_macro_assets.fetch_macro_assets",
            return_value=(detail, source_log),
        ) as fetcher, patch(
            "pipeline.scripts.fetch_macro_assets.add_macro_ranks",
            side_effect=lambda frame: frame,
        ), patch(
            "pipeline.scripts.fetch_macro_assets.build_macro_divergence",
            return_value=pd.DataFrame(),
        ), patch.object(
            sys,
            "argv",
            [
                "fetch_macro_assets.py",
                "--output-dir",
                directory,
                "--as-of-date",
                "2026-08-02",
                "--no-raw-cache",
            ],
        ):
            fetch_cli.main()

        fetcher.assert_called_once_with(
            "pipeline/config/capital_weekly_macro_assets.csv",
            raw_dir=None,
            as_of_date=date(2026, 8, 2),
        )


if __name__ == "__main__":
    unittest.main()
