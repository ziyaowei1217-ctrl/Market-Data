import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]


class ExtendedDataTests(unittest.TestCase):
    def test_spread_is_bp_and_preserves_gaps(self):
        from pipeline.report.rates import spread_bp
        frame = pd.DataFrame({'2Y': [4., np.nan, 3.9], '10Y': [3.8, 4., 4.1]},
                             index=pd.date_range('2026-10-21', periods=3))
        result = spread_bp(frame)
        self.assertAlmostEqual(result.iloc[0], -20.)
        self.assertTrue(pd.isna(result.iloc[1]))
        self.assertAlmostEqual(result.iloc[2], 20.)

    def test_curve_sorts_tenors_and_allows_negative_yields(self):
        from pipeline.report.rates import validate_yields, curve_snapshot
        frame = pd.DataFrame({'10Y': [1., 1.2], '2Y': [-.1, .1], '1M': [-.2, 0.]},
                             index=pd.to_datetime(['2026-10-16', '2026-10-23']))
        result = validate_yields(frame, '2026-10-23')
        self.assertEqual(result.columns.tolist(), ['1M', '2Y', '10Y'])
        before, after = curve_snapshot(result, '2026-10-16', '2026-10-23')
        self.assertAlmostEqual((after - before)['2Y'] * 100, 20.)
        with self.assertRaises(ValueError):
            curve_snapshot(result, '2026-10-15', '2026-10-23')
        monthly = result.copy()
        monthly.index = pd.to_datetime(['2026-09-23', '2026-10-23'])
        with self.assertRaises(ValueError):
            curve_snapshot(monthly, '2026-09-23', '2026-10-23')

    def test_invalid_yields_rejected(self):
        from pipeline.report.rates import validate_yields
        for name, values in [('unknown', [1., 2.]), ('2Y', [1., np.inf])]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_yields(pd.DataFrame({name: values}, index=pd.date_range('2026-10-22', periods=2)), '2026-10-23')

    def test_heatmap_uses_explicit_bases_and_marks_missing(self):
        from pipeline.report.rates import horizon_returns
        frame = pd.DataFrame({'A': [100., 120.], 'B': [np.nan, 110.]},
                             index=pd.to_datetime(['2025-12-31', '2026-10-23']))
        result = horizon_returns(frame, {'YTD': '2025-12-31', '1M': '2026-09-23'}, '2026-10-23')
        self.assertAlmostEqual(result.loc['A', 'YTD'], 20.)
        self.assertTrue(pd.isna(result.loc['B', 'YTD']))
        self.assertTrue(result['1M'].isna().all())
        with self.assertRaises(ValueError):
            horizon_returns(frame, {'future': '2026-10-24'}, '2026-10-23')


class ExtendedExportTests(unittest.TestCase):
    def test_selected_heatmap_allows_missing_week_base_but_returns_rejects_it(self):
        from pipeline.report.data import create_demo
        from pipeline.report.rates import create_rates_demo
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            csv, meta = create_demo(root)
            create_rates_demo(root)
            csv.write_text('date,A\n2025-12-31,100\n2026-10-23,120\n')
            command = [sys.executable, '-m', 'pipeline.report', '--csv', str(csv), '--metadata', str(meta),
                       '--output-dir', str(root / 'out'), '--charts']
            good = subprocess.run(command + ['heatmap'], capture_output=True, text=True, cwd=REPO)
            self.assertEqual(good.returncode, 0, good.stderr)
            from pypdf import PdfReader
            text = PdfReader(root / 'out' / 'weekly-report.pdf').pages[0].extract_text()
            self.assertIn('+20.0%', text)   # percent changes: one decimal
            self.assertIn('–', text)        # missing values: en dash
            bad = subprocess.run(command + ['returns'], capture_output=True, text=True, cwd=REPO)
            self.assertNotEqual(bad.returncode, 0)

    def test_all_demo_charts_and_three_page_report(self):
        from pypdf import PdfReader
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            run = subprocess.run([sys.executable, '-m', 'pipeline.report', '--demo', '--charts', 'trends', 'returns', 'curve', 'spread', 'heatmap', 'comparison', '--output-dir', folder], capture_output=True, text=True, cwd=REPO)
            self.assertEqual(run.returncode, 0, run.stderr)
            root = Path(folder)
            self.assertEqual(len(PdfReader(root / 'weekly-report.pdf').pages), 3)
            for name in ['cross-asset-trends', 'weekly-returns', 'yield-curve', 'yield-spread', 'performance-heatmap', 'rate-comparison']:
                self.assertEqual(len(PdfReader(root / (name + '.pdf')).pages), 1)
                with Image.open(root / (name + '.png')) as im:
                    self.assertGreaterEqual(im.width, 2000)
            for page in PdfReader(root / 'weekly-report.pdf').pages:
                self.assertIn('DEMO', page.extract_text())

    def test_single_chart_selection(self):
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as folder:
            run = subprocess.run([sys.executable, '-m', 'pipeline.report', '--demo', '--charts', 'spread', '--output-dir', folder], capture_output=True, text=True, cwd=REPO)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(len(PdfReader(Path(folder) / 'weekly-report.pdf').pages), 1)
            self.assertTrue((Path(folder) / 'yield-spread.png').exists())
            self.assertFalse((Path(folder) / 'cross-asset-trends.png').exists())


if __name__ == '__main__':
    unittest.main()
