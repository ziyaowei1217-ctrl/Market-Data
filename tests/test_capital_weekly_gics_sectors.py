import unittest

from capital_weekly.gics_sectors import load_sector_universe


class GicsSectorConfigTests(unittest.TestCase):
    def test_universe_has_11_unique_gics_sectors(self):
        sectors = load_sector_universe()

        self.assertEqual(len(sectors), 11)
        self.assertEqual(len({sector.gics_sector_code for sector in sectors}), 11)
        self.assertEqual(len({sector.ticker for sector in sectors}), 11)
        self.assertTrue(all(sector.provider == "sina_us" for sector in sectors))


if __name__ == "__main__":
    unittest.main()
