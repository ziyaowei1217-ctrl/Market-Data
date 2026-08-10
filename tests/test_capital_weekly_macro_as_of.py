from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from capital_weekly.macro_assets import fetch_macro_assets


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
                "capital_weekly.macro_assets._fetch_config_history",
                return_value=(history, b"fixture", "https://example.test"),
            ):
                detail, source_log = fetch_macro_assets(
                    universe,
                    as_of_date=date(2026, 8, 2),
                )

        self.assertEqual(detail.loc[0, "latest_date"], "2026-07-31")
        self.assertEqual(detail.loc[0, "latest_value"], 105.0)
        self.assertEqual(source_log.loc[0, "latest_date"], "2026-07-31")


if __name__ == "__main__":
    unittest.main()
