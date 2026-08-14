from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

from capital_weekly.gics_sectors import fetch_gics_sectors, load_sector_universe


class GicsSectorConfigTests(unittest.TestCase):
    def test_universe_has_11_unique_gics_sectors(self):
        sectors = load_sector_universe()

        self.assertEqual(len(sectors), 11)
        self.assertEqual(len({sector.gics_sector_code for sector in sectors}), 11)
        self.assertEqual(len({sector.ticker for sector in sectors}), 11)
        self.assertTrue(all(sector.provider == "sina_us" for sector in sectors))


class GicsSectorFetchTests(unittest.TestCase):
    def test_fetcher_applies_as_of_cutoff_before_snapshot_calculation(self):
        with TemporaryDirectory() as directory:
            universe_path = Path(directory) / "universe.csv"
            universe_path.write_text(
                "gics_sector_code,sector_name_cn,sector_name_en,ticker,currency,"
                "provider,provider_symbol,source,proxy_type,notes\n"
                "10,能源,Energy,TEST,USD,sina_us,.TEST,Sina Finance,ETF,\n",
                encoding="utf-8",
            )
            history = pd.DataFrame(
                {
                    "date": [date(2025, 12, 31), date(2026, 8, 7), date(2026, 8, 10)],
                    "open": [100.0, 105.0, 110.0],
                    "high": [100.0, 105.0, 110.0],
                    "low": [100.0, 105.0, 110.0],
                    "close": [100.0, 105.0, 110.0],
                    "volume": [1, 1, 1],
                }
            )

            with patch(
                "capital_weekly.gics_sectors.fetch_history",
                return_value=(history, "fake history"),
            ):
                data, source_log = fetch_gics_sectors(
                    universe_path,
                    as_of_date=date(2026, 8, 9),
                )

        self.assertEqual(data.loc[0, "latest_date"], "2026-08-07")
        self.assertEqual(source_log.loc[0, "latest_date"], "2026-08-07")


if __name__ == "__main__":
    unittest.main()
