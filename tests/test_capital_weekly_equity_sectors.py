from collections import Counter
from datetime import date
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

from capital_weekly.equity_sectors import fetch_equity_sectors, load_sector_universe
from scripts import fetch_equity_sectors as fetch_cli


class EquitySectorUniverseTests(unittest.TestCase):
    def test_universe_has_expected_market_counts_and_unique_keys(self):
        sectors = load_sector_universe()

        self.assertEqual(
            Counter(sector.market for sector in sectors),
            {"US": 11, "China A": 11, "HK": 12},
        )
        self.assertEqual(len(sectors), 34)
        self.assertEqual(
            len({(s.market, s.taxonomy, s.sector_code) for s in sectors}),
            34,
        )
        self.assertEqual(
            sorted(s.sort_order for s in sectors if s.market == "China A"),
            list(range(1, 12)),
        )
        self.assertTrue(all(s.taxonomy_level == "Level 1" for s in sectors))

    def test_hk_universe_uses_exact_hang_seng_index_codes(self):
        hk_sectors = [sector for sector in load_sector_universe() if sector.market == "HK"]

        self.assertEqual({sector.provider for sector in hk_sectors}, {"hsi_chart"})
        self.assertEqual({sector.source for sector in hk_sectors}, {"Hang Seng Indexes"})
        self.assertEqual(
            {sector.ticker: sector.provider_symbol for sector in hk_sectors},
            {
                "HSCIEN": "00011.01",
                "HSCIMT": "00011.02",
                "HSCIIN": "00011.03",
                "HSCICD": "00011.12",
                "HSCICS": "00011.13",
                "HSCIH": "00011.14",
                "HSCITC": "00011.06",
                "HSCIUT": "00011.07",
                "HSCIFN": "00011.08",
                "HSCIPC": "00011.09",
                "HSCIIT": "00011.10",
                "HSCICO": "00011.11",
            },
        )


class EquitySectorFetchTests(unittest.TestCase):
    def legacy_investing_sector_appends_reported_ytd_baseline_after_session_filter(self):
        with TemporaryDirectory() as directory:
            universe_path = Path(directory) / "universe.csv"
            universe_path.write_text(
                "market,taxonomy,taxonomy_version,taxonomy_level,sector_code,"
                "sector_name_cn,sector_name_en,ticker,currency,provider,"
                "provider_symbol,source,instrument_type,sort_order,notes\n"
                "HK,HSICS,2.0,Level 1,10,能源,Energy,HSCIEN,HKD,investing_page,"
                "hsci-energy,Investing.com,Index,1,\n",
                encoding="utf-8",
            )
            history = pd.DataFrame({
                "date": [date(2025, 1, 2), date(2025, 3, 3), date(2025, 3, 4)],
                "open": [100, 108, 110], "high": [100, 108, 110],
                "low": [100, 108, 110], "close": [100, 108, 110],
                "volume": [1, 1, 1],
            })
            history.attrs["investing_pct_ytd"] = 10.0
            history.attrs["investing_pct_ytd_date"] = date(2025, 3, 4)

            with patch("capital_weekly.equity_sectors.fetch_history",
                       return_value=(history, "investing raw response")):
                data, source_log = fetch_equity_sectors(universe_path)

            self.assertEqual(data.loc[0, "ytd_base_date"], "2024-12-31")
            self.assertAlmostEqual(data.loc[0, "ytd_base_value"], 100.0)
            self.assertAlmostEqual(data.loc[0, "ytd_change"], 0.10)
            self.assertEqual(source_log.loc[0, "ytd_base_date"], "2024-12-31")

    def test_fetcher_keeps_failed_sector_and_caches_successful_raw_response(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            universe_path = root / "universe.csv"
            raw_dir = root / "raw"
            universe_path.write_text(
                "market,taxonomy,taxonomy_version,taxonomy_level,sector_code,"
                "sector_name_cn,sector_name_en,ticker,currency,provider,"
                "provider_symbol,source,instrument_type,sort_order,notes\n"
                "HK,GICS,2018,Level 1,10,Energy,Energy,VALID,HKD,tencent_kline,"
                "hkVALID,Tencent,Index,1,\n"
                "HK,GICS,2018,Level 1,15,Materials,Materials,BAD,HKD,unsupported,"
                "BAD,Unknown,Index,2,\n",
                encoding="utf-8",
            )
            history = pd.DataFrame(
                {
                    "date": [
                        date(2024, 12, 31),
                        date(2025, 1, 31),
                        date(2025, 2, 28),
                        date(2025, 3, 3),
                        date(2025, 3, 4),
                    ],
                    "open": [100, 101, 102, 103, 104],
                    "high": [100, 101, 102, 103, 104],
                    "low": [100, 101, 102, 103, 104],
                    "close": [100, 101, 102, 103, 104],
                    "volume": [1, 1, 1, 1, 1],
                }
            )

            with patch(
                "capital_weekly.equity_sectors.fetch_history",
                return_value=(history, "valid raw response"),
            ):
                data, source_log = fetch_equity_sectors(universe_path, raw_dir=raw_dir)

            self.assertEqual(len(data), 2)
            self.assertEqual(data.loc[0, "qc_flag"], "OK")
            self.assertEqual(data.loc[1, "qc_flag"], "FETCH_FAILED")
            self.assertEqual(source_log.loc[1, "status"], "FETCH_FAILED")
            self.assertIn("Unsupported provider", source_log.loc[1, "notes"])
            self.assertTrue((raw_dir / "VALID.txt").exists())

    def test_fetcher_does_not_cache_raw_response_when_snapshot_fails(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            universe_path = root / "universe.csv"
            raw_dir = root / "raw"
            universe_path.write_text(
                "market,taxonomy,taxonomy_version,taxonomy_level,sector_code,"
                "sector_name_cn,sector_name_en,ticker,currency,provider,"
                "provider_symbol,source,instrument_type,sort_order,notes\n"
                "HK,GICS,2018,Level 1,10,Energy,Energy,SHORT,HKD,tencent_kline,"
                "hkSHORT,Tencent,Index,1,\n",
                encoding="utf-8",
            )
            history = pd.DataFrame(
                {
                    "date": [date(2025, 3, 4)],
                    "open": [100],
                    "high": [100],
                    "low": [100],
                    "close": [100],
                    "volume": [1],
                }
            )

            with patch(
                "capital_weekly.equity_sectors.fetch_history",
                return_value=(history, "short raw response"),
            ):
                data, source_log = fetch_equity_sectors(universe_path, raw_dir=raw_dir)

            self.assertEqual(data.loc[0, "qc_flag"], "FETCH_FAILED")
            self.assertEqual(source_log.loc[0, "status"], "FETCH_FAILED")
            self.assertFalse((raw_dir / "SHORT.txt").exists())

    def test_cli_writes_strict_json_with_null_for_failed_numeric_values(self):
        data = pd.DataFrame(
            {
                "market": ["US", "US"],
                "sector_name_cn": ["信息技术", "能源"],
                "sort_order": [1, 2],
                "daily_change": [0.01, float("nan")],
                "weekly_change": [0.02, float("nan")],
                "mtd_change": [0.03, float("nan")],
                "ytd_change": [0.04, float("nan")],
                "qc_flag": ["OK", "FETCH_FAILED"],
            }
        )
        source_log = pd.DataFrame({"market": ["US", "US"], "status": ["OK", "FETCH_FAILED"]})

        with TemporaryDirectory() as directory:
            with patch("scripts.fetch_equity_sectors.fetch_equity_sectors", return_value=(data, source_log)):
                with patch.object(sys, "argv", ["fetch_equity_sectors.py", "--output-dir", directory, "--no-raw-cache"]):
                    fetch_cli.main()

            root = Path(directory)
            self.assertTrue((root / "03_equity_sectors.csv").exists())
            self.assertTrue((root / "sector_divergence.csv").exists())
            self.assertTrue((root / "source_log.csv").exists())
            snapshot = json.loads((root / "equity_sectors_snapshot.json").read_text(encoding="utf-8"))
            self.assertIsNone(snapshot["rows"][1]["weekly_change"])

    def test_fetcher_keeps_computed_row_and_audits_raw_cache_write_failure(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            universe_path = root / "universe.csv"
            raw_dir = root / "raw"
            universe_path.write_text(
                "market,taxonomy,taxonomy_version,taxonomy_level,sector_code,"
                "sector_name_cn,sector_name_en,ticker,currency,provider,"
                "provider_symbol,source,instrument_type,sort_order,notes\n"
                "HK,GICS,2018,Level 1,10,Energy,Energy,VALID,HKD,tencent_kline,"
                "hkVALID,Tencent,Index,1,\n",
                encoding="utf-8",
            )
            history = pd.DataFrame(
                {
                    "date": [
                        date(2024, 12, 31),
                        date(2025, 1, 31),
                        date(2025, 2, 28),
                        date(2025, 3, 3),
                        date(2025, 3, 4),
                    ],
                    "open": [100, 101, 102, 103, 104],
                    "high": [100, 101, 102, 103, 104],
                    "low": [100, 101, 102, 103, 104],
                    "close": [100, 101, 102, 103, 104],
                    "volume": [1, 1, 1, 1, 1],
                }
            )
            raw_dir.mkdir()
            (raw_dir / "VALID.txt").mkdir()

            with patch(
                "capital_weekly.equity_sectors.fetch_history",
                return_value=(history, "valid raw response"),
            ):
                data, source_log = fetch_equity_sectors(universe_path, raw_dir=raw_dir)

            self.assertEqual(len(data), 1)
            self.assertEqual(len(source_log), 1)
            self.assertEqual(data.loc[0, "qc_flag"], "OK")
            self.assertEqual(source_log.loc[0, "status"], "OK")
            self.assertEqual(source_log.loc[0, "raw_cache_status"], "CACHE_WRITE_FAILED")
            self.assertIn("Is a directory", source_log.loc[0, "raw_cache_error"])

    def test_raw_cache_write_is_atomic_and_leaves_no_temp_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            universe_path = root / "universe.csv"
            raw_dir = root / "raw"
            universe_path.write_text(
                "market,taxonomy,taxonomy_version,taxonomy_level,sector_code,"
                "sector_name_cn,sector_name_en,ticker,currency,provider,"
                "provider_symbol,source,instrument_type,sort_order,notes\n"
                "HK,GICS,2018,Level 1,10,Energy,Energy,VALID,HKD,tencent_kline,"
                "hkVALID,Tencent,Index,1,\n",
                encoding="utf-8",
            )
            history = pd.DataFrame({
                "date": [date(2024, 12, 31), date(2025, 1, 31), date(2025, 2, 28),
                         date(2025, 3, 3), date(2025, 3, 4)],
                "open": [100, 101, 102, 103, 104], "high": [100, 101, 102, 103, 104],
                "low": [100, 101, 102, 103, 104], "close": [100, 101, 102, 103, 104],
                "volume": [1, 1, 1, 1, 1],
            })
            with patch("capital_weekly.equity_sectors.fetch_history",
                       return_value=(history, "valid raw response")):
                data, source_log = fetch_equity_sectors(universe_path, raw_dir=raw_dir)

            self.assertEqual((raw_dir / "VALID.txt").read_text(encoding="utf-8"),
                             "valid raw response")
            self.assertEqual(list(raw_dir.glob("*.tmp")), [])
            self.assertEqual(data.loc[0, "qc_flag"], "OK")
            self.assertEqual(source_log.loc[0, "raw_cache_status"], "OK")

    def test_cli_rolls_back_whole_output_bundle_when_publish_fails(self):
        data = pd.DataFrame({
            "market": ["US"], "sector_name_cn": ["信息技术"], "sort_order": [1],
            "daily_change": [0.01], "weekly_change": [0.02],
            "mtd_change": [0.03], "ytd_change": [0.04], "qc_flag": ["OK"],
        })
        source_log = pd.DataFrame({"market": ["US"], "status": ["OK"]})
        with TemporaryDirectory() as directory:
            root = Path(directory) / "published"
            root.mkdir()
            (root / "marker.txt").write_text("old bundle", encoding="utf-8")
            real_replace = fetch_cli.os.replace

            def fail_staging_publish(src, dst):
                if Path(dst) == root and ".staging-" in Path(src).name:
                    raise OSError("publish failed")
                return real_replace(src, dst)

            with patch("scripts.fetch_equity_sectors.fetch_equity_sectors",
                       return_value=(data, source_log)), \
                 patch("scripts.fetch_equity_sectors.os.replace", side_effect=fail_staging_publish), \
                 patch.object(sys, "argv", ["fetch_equity_sectors.py", "--output-dir", str(root),
                                            "--no-raw-cache"]):
                with self.assertRaisesRegex(OSError, "publish failed"):
                    fetch_cli.main()

            self.assertEqual((root / "marker.txt").read_text(encoding="utf-8"), "old bundle")
            self.assertFalse((root / "03_equity_sectors.csv").exists())
