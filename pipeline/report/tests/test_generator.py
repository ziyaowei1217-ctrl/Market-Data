import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]


class DataTests(unittest.TestCase):
    def test_duplicate_csv_headers_are_rejected_before_pandas_renames_them(self):
        from pipeline.report.data import create_demo, load_inputs
        with tempfile.TemporaryDirectory() as folder:
            csv, meta = create_demo(folder)
            for content in ('date,A,A\n2026-10-16,100,100\n2026-10-23,101,102\n',
                            'date,\n2026-10-16,100\n2026-10-23,101\n'):
                csv.write_text(content)
                with self.subTest(content=content), self.assertRaises(ValueError):
                    load_inputs(csv, meta)

    def test_rebase_uses_first_common_date_and_keeps_missing_values(self):
        from pipeline.report.data import normalize
        frame = pd.DataFrame({'A': [90., 100., np.nan, 110.], 'B': [np.nan, 50., 55., 60.]},
                             index=pd.date_range('2026-10-19', periods=4))
        result = normalize(frame)
        self.assertEqual(str(result.index[0].date()), '2026-10-20')
        self.assertEqual(result.iloc[0].tolist(), [100., 100.])
        self.assertAlmostEqual(result.iloc[-1]['A'], 110.)
        self.assertAlmostEqual(result.iloc[-1]['B'], 120.)
        self.assertTrue(pd.isna(result.iloc[1]['A']))

    def test_weekly_return_uses_exact_dates_and_percentage_units(self):
        from pipeline.report.data import weekly_returns
        frame = pd.DataFrame({'A': [100., 110.], 'B': [200., 190.]},
                             index=pd.to_datetime(['2026-10-16', '2026-10-23']))
        result = weekly_returns(frame, '2026-10-16', '2026-10-23')
        self.assertAlmostEqual(result['A'], 10.)
        self.assertAlmostEqual(result['B'], -5.)
        with self.assertRaises(ValueError):
            weekly_returns(frame, '2026-10-15', '2026-10-23')

    def test_rejects_duplicate_dates_zero_levels_and_infinity(self):
        from pipeline.report.data import validate_levels
        for values, dates in [([1., 2.], ['2026-10-20'] * 2),
                              ([0., 2.], ['2026-10-20', '2026-10-21']),
                              ([1., np.inf], ['2026-10-20', '2026-10-21'])]:
            with self.subTest(values=values, dates=dates), self.assertRaises(ValueError):
                validate_levels(pd.DataFrame({'A': values}, index=pd.to_datetime(dates)), '2026-10-23')

    def test_cutoff_excludes_future_rows(self):
        from pipeline.report.data import validate_levels
        frame = pd.DataFrame({'A': [1., 2., 999.]}, index=pd.date_range('2026-10-20', periods=3))
        result = validate_levels(frame, '2026-10-21')
        self.assertEqual(result['A'].tolist(), [1., 2.])


class ExportTests(unittest.TestCase):
    def test_long_ranking_labels_stay_within_chart(self):
        from pipeline.report.data import create_demo, load_inputs
        from pipeline.report.charts import setup_theme, ranking_panel, MM
        import matplotlib.pyplot as plt
        with tempfile.TemporaryDirectory() as folder:
            frame, meta = load_inputs(*create_demo(folder))
            frame.columns = ['这是十二个字的资产名称啊', '乙', '丙', '丁', '戊', '己']
            setup_theme()
            fig = plt.figure(figsize=(170 * MM, 111 * MM))
            ranking_panel(fig, 4, 7, 162, frame, meta)
            fig.canvas.draw()
            for label in fig.axes[0].get_yticklabels():
                self.assertGreaterEqual(label.get_window_extent().x0, 0)
            plt.close(fig)

    def test_demo_exports_a4_pdf_and_two_print_resolution_pngs(self):
        from pypdf import PdfReader
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, '-m', 'pipeline.report', '--demo', '--charts', 'trends', 'returns', '--output-dir', folder],
                                    capture_output=True, text=True, cwd=REPO)
            self.assertEqual(result.returncode, 0, result.stderr)
            root = Path(folder)
            pdf = PdfReader(root / 'weekly-report.pdf')
            self.assertEqual(len(pdf.pages), 1)
            page = pdf.pages[0]
            self.assertAlmostEqual(float(page.mediabox.width), 210 / 25.4 * 72, places=1)
            self.assertAlmostEqual(float(page.mediabox.height), 297 / 25.4 * 72, places=1)
            self.assertIn('DEMO', page.extract_text())
            for name in ['cross-asset-trends.png', 'weekly-returns.png']:
                with Image.open(root / name) as im:
                    self.assertGreaterEqual(im.width, 2000)
                    self.assertAlmostEqual(im.info['dpi'][0], 300, places=0)


class HighlightTests(unittest.TestCase):
    def test_highlight_names_one_or_two_existing_assets(self):
        from pipeline.report.charts import highlights
        cols = ['A', 'B', 'C']
        self.assertEqual(highlights({}, cols), ['A'])
        self.assertEqual(highlights({'focus_asset': 'B'}, cols), ['B'])
        self.assertEqual(highlights({'highlight': ['C', 'A']}, cols), ['C', 'A'])
        for bad in (['X'], ['A', 'B', 'C'], ['A', 'A'], [], 5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                highlights({'highlight': bad}, cols)


class StyleTests(unittest.TestCase):
    def test_number_formats_follow_design_system(self):
        from pipeline.report.charts import change, level, bp, MISSING_TEXT
        self.assertEqual(change(2.345), '+2.3%')
        self.assertEqual(change(-0.92), '−0.9%')
        self.assertEqual(change(0.0), '0.0%')
        self.assertEqual(level(4349.081), '4,349.08')
        self.assertEqual(level(-1.5), '−1.50')
        self.assertEqual(bp(22.4), '+22 bp')
        self.assertEqual(change(float('nan')), MISSING_TEXT)

    def test_text_outside_bundled_fonts_is_rejected_before_drawing(self):
        from pipeline.report.charts import validate_style
        frame = pd.DataFrame({'美国股票': [1.0, 2.0]})
        validate_style({'titles': {'trends': '美股领涨'}}, frame, ['trends'])
        with self.assertRaisesRegex(ValueError, '𠮷'):
            validate_style({'titles': {'trends': '𠮷野家领涨'}}, frame, ['trends'])
        with self.assertRaisesRegex(ValueError, '𠮷'):
            validate_style({}, pd.DataFrame({'𠮷野家': [1.0, 2.0]}), ['trends'])

    def test_a_change_that_rounds_to_zero_is_drawn_flat(self):
        import matplotlib.pyplot as plt
        from pipeline.report.charts import delta, COMPACT, INK
        fig, ax = plt.subplots()
        flat = delta(ax, (0, 0), -0.03, '0.0%', ('green', 'red'), COMPACT)
        down = delta(ax, (0, 0), -0.4, '−0.4%', ('green', 'red'), COMPACT)
        plt.close(fig)
        self.assertEqual(len(flat.offsetbox.get_children()), 1)
        self.assertEqual(flat.offsetbox.get_children()[0]._text.get_color(), INK)
        self.assertEqual(len(down.offsetbox.get_children()), 2)

    def test_market_colours_swap_only_for_cn(self):
        from pipeline.report.charts import market, TEAL, VERMILION
        self.assertEqual(market({})[:2], (TEAL, VERMILION))
        self.assertEqual(market({'market_colors': 'cn'})[:2], (VERMILION, TEAL))
        with self.assertRaises(ValueError):
            market({'market_colors': 'red'})


class WeeklyLayoutTests(unittest.TestCase):
    def test_pack_fills_three_columns_and_keeps_every_chart(self):
        from pipeline.report.weekly import pack, COLS
        keys = ['returns', 'curve', 'spread', 'heatmap', 'calendar', 'football', 'distribution']
        rows = pack(keys)
        placed = [key for row in rows for key, _ in row]
        self.assertEqual(sorted(placed), sorted(keys))
        for row in rows:
            self.assertEqual(sum(span for _, span in row), COLS)

    def test_thesis_page_only_for_a_full_issue(self):
        from pipeline.report.weekly import choose_thesis
        self.assertIsNone(choose_thesis(['trends', 'returns'], {}))
        self.assertEqual(choose_thesis(['trends', 'returns', 'curve', 'spread'], {}), 'trends')
        self.assertEqual(choose_thesis(['trends', 'returns', 'curve', 'spread'], {'thesis': 'curve'}), 'curve')
        self.assertIsNone(choose_thesis(['trends', 'returns', 'curve', 'spread'], {'thesis': False}))


if __name__ == '__main__':
    unittest.main()
