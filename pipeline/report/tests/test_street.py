from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]


class StreetDataTests(unittest.TestCase):
    def test_numeric_columns_named_label_are_not_skipped(self):
        from pipeline.report.street_data import validate_table
        cases=[('flows',pd.DataFrame({'date':['2026-10-01','2026-10-02'],'label':['wrong','data']})),
               ('sensitivity',pd.DataFrame({'scenario':['case'],'label':['wrong']}))]
        for key,frame in cases:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_table(key,frame,'2026-10-23')

    def test_relative_needs_observations_after_common_baseline(self):
        from pipeline.report.street_data import relative_performance
        frame=pd.DataFrame({'A':[100.,np.nan,110.],'B':[np.nan,100.,120.]},index=pd.date_range('2026-10-01',periods=3))
        with self.assertRaises(ValueError):
            relative_performance(frame,'B')

    def test_drawdown_and_returns_do_not_fill_gaps(self):
        from pipeline.report.street_data import drawdowns, daily_returns
        frame = pd.DataFrame({'A': [100., 120., 90., np.nan, 108.]}, index=pd.bdate_range('2026-10-01', periods=5))
        dd=drawdowns(frame)
        self.assertAlmostEqual(dd.iloc[2,0], -25.)
        self.assertAlmostEqual(dd.iloc[4,0], -10.)
        returns=daily_returns(frame)
        self.assertTrue(pd.isna(returns.iloc[4,0]))

    def test_rolling_volatility_sample_std_and_full_window(self):
        from pipeline.report.street_data import rolling_volatility
        frame=pd.DataFrame({'A':[100.,110.,99.,108.9]},index=pd.bdate_range('2026-10-01',periods=4))
        result=rolling_volatility(frame,window=3,annualization=1)
        self.assertTrue(pd.isna(result.iloc[2,0]))
        self.assertAlmostEqual(result.iloc[3,0],11.5470053838)

    def test_relative_ratio_and_complete_month_return(self):
        from pipeline.report.street_data import relative_performance, calendar_returns
        f=pd.DataFrame({'A':[100.,110.,121.], 'B':[100.,100.,110.]},index=pd.to_datetime(['2025-12-31','2026-01-30','2026-02-27']))
        self.assertAlmostEqual(relative_performance(f,'B').iloc[-1]['A'],110.)
        result=calendar_returns(f['A'], '2026-02-27')
        self.assertAlmostEqual(result.loc[2026,1],10.)
        self.assertAlmostEqual(result.loc[2026,2],10.)

    def test_bundle_rejects_bad_ohlc_bridge_and_range(self):
        from pipeline.report.street_data import validate_table
        cases=[('candlestick',pd.DataFrame({'date':['2026-10-01','2026-10-02'],'open':[100,100],'high':[99,102],'low':[98,99],'close':[101,101],'volume':[1,2]})),
               ('waterfall',pd.DataFrame({'label':['Start','Move','End'],'value':[100,10,120],'kind':['total','change','total']})),
               ('football',pd.DataFrame({'label':['DCF'],'low':[120.],'high':[100.]}))]
        for key,frame in cases:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_table(key, frame, '2026-10-23')


class StreetExportTests(unittest.TestCase):
    def test_sensitivity_headers_align_with_values_and_preserve_decimals(self):
        from pipeline.report.charts import setup_theme, MM
        from pipeline.report.street_charts import render
        import matplotlib.pyplot as plt
        setup_theme()
        frame=pd.DataFrame({'7.0%':[1.11,1.21],'scenario':['low','high'],'9.0%':[1.12,1.22]})
        meta={'source':'test','as_of':'2026-10-23','updated_at':'2026-10-23 UTC','is_demo':True,
              'chart_units':{'sensitivity':'USD / share'}}
        fig=plt.figure(figsize=(170*MM,111*MM))
        render('sensitivity',fig,4,7,162,frame,meta)
        ax=fig.axes[0]
        self.assertEqual([t.get_text() for t in ax.get_xticklabels()],['7.0%','9.0%'])
        self.assertIn('1.11',[t.get_text() for t in ax.texts])
        self.assertIn('1.22',[t.get_text() for t in ax.texts])
        plt.close(fig)

    def test_full_street_demo(self):
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as folder:
            run=subprocess.run([sys.executable, '-m', 'pipeline.report', '--demo','--charts','all','--output-dir',folder],capture_output=True, text=True, cwd=REPO)
            self.assertEqual(run.returncode,0,run.stderr)
            root=Path(folder)
            pages=PdfReader(root/'weekly-report.pdf').pages
            # Weekly Commentary: front page + thesis page + three-column data pages, denser than one chart per half page.
            self.assertLess(len(pages),10)
            texts=[page.extract_text() for page in pages]
            for page_text in texts:
                self.assertIn('DEMO',page_text)
            self.assertIn('本期论点',texts[1])
            from pipeline.report.street_charts import LABELS
            joined=''.join(texts).replace('\n','').replace(' ','')
            for label in list(LABELS.values())+['本周资产表现','国债收益率曲线','期限利差','跨周期表现','利率周度变动']:
                self.assertIn(label.replace(' ',''),joined)
            self.assertEqual(len(list(root.glob('*.png'))),20)
            self.assertEqual(len(list(root.glob('*.pdf'))),21)


if __name__=='__main__': unittest.main()


class LabelPlacementTests(unittest.TestCase):
    def test_risk_return_labels_do_not_collide_in_a_tight_cluster(self):
        import matplotlib.pyplot as plt
        from matplotlib.text import Annotation
        from pipeline.report.charts import setup_theme, standalone, MM
        from pipeline.report import street_charts  # noqa: F401
        setup_theme()
        # Synthetic figures: two pairs of near-identical dots and one outlier.
        data = pd.DataFrame({'return': [9.0, 9.6, 1.5, -2.0, -1.6, 3.0],
                             'risk': [10.0, 10.8, 5.2, 4.4, 4.0, 24.0]},
                            index=['全球股票', '美国股票', '美元指数', '美国综合债', '美国国债', '黄金'])
        meta = {'source': '测试', 'as_of': '2026-10-23', 'updated_at': '2026-10-24 14:00 UTC', 'is_demo': False,
                'highlight': ['美国股票', '黄金']}
        fig = plt.figure(figsize=(114 * MM, 70 * MM))
        standalone(fig, 'risk_return', data, meta, 2, 2, 110)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        boxes = [a.get_window_extent(renderer) for ax in fig.axes for a in ax.texts if isinstance(a, Annotation)]
        plt.close(fig)
        self.assertEqual(len(boxes), 6)
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                self.assertFalse(boxes[i].overlaps(boxes[j]), (i, j))
