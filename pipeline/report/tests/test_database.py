"""Weekly issue from the warehouse: as-of cutoffs, series notes, and the database adapter (no network)."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]


def lagging_frame():
    """Business days to Fri 2026-10-23; 'B' stops on Wed 10-21 (a lagging feed), 'C' misses Fri 10-16."""
    index = pd.bdate_range('2026-09-01', '2026-10-23')
    frame = pd.DataFrame({'A': np.linspace(100, 110, len(index)), 'B': np.linspace(50, 40, len(index)),
                          'C': np.linspace(10, 12, len(index))}, index=index)
    frame.loc['2026-10-22':, 'B'] = np.nan
    frame.loc['2026-10-16', 'C'] = np.nan
    return frame


class AsOfTests(unittest.TestCase):
    def test_exact_rule_is_unchanged_and_asof_takes_last_value_within_six_days(self):
        from pipeline.report.data import weekly_returns, tolerance
        frame = lagging_frame()
        self.assertEqual(tolerance({}), 0)
        self.assertEqual(tolerance({'date_rule': 'asof'}), 6)
        with self.assertRaises(ValueError):
            tolerance({'date_rule': 'nearest'})
        with self.assertRaises(ValueError):
            weekly_returns(frame, '2026-10-16', '2026-10-23')
        result = weekly_returns(frame, '2026-10-16', '2026-10-23', days=6)
        self.assertAlmostEqual(result['B'], (frame.loc['2026-10-21', 'B'] / frame.loc['2026-10-16', 'B'] - 1) * 100)
        self.assertAlmostEqual(result['C'], (frame.loc['2026-10-23', 'C'] / frame.loc['2026-10-15', 'C'] - 1) * 100)

    def test_asof_still_refuses_values_older_than_the_window(self):
        from pipeline.report.data import weekly_returns
        frame = lagging_frame()
        frame.loc['2026-10-09':, 'B'] = np.nan
        with self.assertRaisesRegex(ValueError, 'B'):
            weekly_returns(frame, '2026-10-16', '2026-10-23', days=6)

    def test_obs_dates_report_the_day_each_value_comes_from(self):
        from pipeline.report.data import obs_dates
        dates = obs_dates(lagging_frame(), '2026-10-23', 6)
        self.assertEqual(dates['A'], pd.Timestamp('2026-10-23'))
        self.assertEqual(dates['B'], pd.Timestamp('2026-10-21'))

    def test_rates_follow_the_same_rule(self):
        from pipeline.report.rates import curve_snapshot, horizon_returns
        yields = pd.DataFrame({'2Y': [3.5, 3.6, np.nan], '10Y': [4.0, 4.1, 4.2]},
                              index=pd.to_datetime(['2026-10-16', '2026-10-22', '2026-10-23']))
        with self.assertRaises(ValueError):
            curve_snapshot(yields, '2026-10-16', '2026-10-23')
        before, after = curve_snapshot(yields, '2026-10-16', '2026-10-23', days=6)
        self.assertEqual(after['2Y'], 3.6)
        frame = lagging_frame()
        table = horizon_returns(frame, {'1W': '2026-10-16', '1M': '2026-09-23'}, '2026-10-23', days=6)
        self.assertAlmostEqual(table.loc['B', '1W'], (frame.loc['2026-10-21', 'B'] / frame.loc['2026-10-16', 'B'] - 1) * 100)


class SeriesNoteTests(unittest.TestCase):
    def test_series_notes_reach_only_the_charts_that_show_the_series(self):
        from pipeline.report.charts import chart_notes
        meta = {'focus_asset': 'A', 'series_notes': {'B': 'ETF 总回报代理', '10Y': '截至10月22日'}}
        notes = chart_notes(['trends', 'distribution', 'curve', 'football'], meta, ['A', 'B'], ['2Y', '10Y'])
        self.assertEqual(notes['trends'], 'B：ETF 总回报代理。')
        self.assertNotIn('distribution', notes)
        self.assertEqual(notes['curve'], '10Y：截至10月22日。')
        self.assertNotIn('football', notes)

    def test_weekly_blocks_point_to_the_data_notes_while_single_charts_carry_them(self):
        from pipeline.report.charts import source_text, compose, COMPACT, REGULAR, SERIES_POINTER
        import matplotlib.pyplot as plt
        meta = {'source': '测试', 'as_of': '2026-10-23', 'updated_at': '2026-10-24 14:00 UTC', 'is_demo': False}
        story = {'label': 'x', 'message': 'y', 'unit': 'z', 'note': '只计入样本内前高。', 'series_note': 'B：ETF 总回报代理。'}
        self.assertIn(SERIES_POINTER, source_text(meta, story, COMPACT))
        self.assertNotIn('ETF', source_text(meta, story, COMPACT))
        fig = plt.figure()
        lines = ''.join(compose(fig, 'trends', story, meta, REGULAR, 160, takeaway=False)['source'])
        plt.close(fig)
        self.assertIn('B：ETF 总回报代理。', lines)


def seed_store(path, stale_gold=False):
    """A small SQLite warehouse with every series the bundled issue config asks for."""
    from pipeline.report.source import load_config
    from pipeline.warehouse.db.store import SQLiteStore
    store = SQLiteStore(path)
    store.init_schema()
    config = load_config()
    days = pd.bdate_range('2025-09-01', '2026-10-23')
    rng = np.random.default_rng(7)
    for i, item in enumerate(config['assets'] + config['yields']):
        values = (4 + rng.normal(0, .02, len(days)).cumsum()) if item in config['yields'] \
            else 100 * np.exp(rng.normal(0, .008, len(days)).cumsum())
        rows = [(d.date(), d.date(), float(v), 'backfill_estimate') for d, v in zip(days, values)]
        if item['series'] == 'FRED:SP500' or item['series'] == 'YAHOO:SPY:TR':
            rows = [r for r in rows if r[0] <= date(2026, 10, 22)]          # a feed one day behind
        if stale_gold and item['series'] == 'YAHOO:GC=F':
            rows = [r for r in rows if r[0] <= date(2026, 10, 9)]
        store.insert_observations(item['series'], rows)
    # A later revision of one observation: the newest vintage must win.
    first = config['assets'][0]['series']
    store.insert_observations(first, [(date(2026, 10, 16), date(2026, 10, 20), 123.0, 'first_seen')])
    store.close()
    return config


class SourceTests(unittest.TestCase):
    def test_cutoff_is_the_last_friday_on_or_before_the_day(self):
        from pipeline.report.source import friday_cutoff
        self.assertEqual(friday_cutoff(date(2026, 10, 24)), date(2026, 10, 23))
        self.assertEqual(friday_cutoff(date(2026, 10, 23)), date(2026, 10, 23))
        self.assertEqual(friday_cutoff(date(2026, 10, 26)), date(2026, 10, 23))

    def test_default_cutoff_is_the_last_finished_friday(self):
        from pipeline.report.source import default_cutoff
        self.assertEqual(default_cutoff(date(2026, 10, 24)), date(2026, 10, 23))   # Saturday
        self.assertEqual(default_cutoff(date(2026, 10, 30)), date(2026, 10, 23))   # Friday, before the close
        self.assertEqual(default_cutoff(date(2026, 10, 26)), date(2026, 10, 23))   # Monday

    def test_a_withdrawn_value_stays_withdrawn(self):
        from pipeline.report.source import latest_vintage
        frame = pd.DataFrame({'obs_date': pd.to_datetime(['2026-10-22', '2026-10-22', '2026-10-23']),
                              'realtime_start': pd.to_datetime(['2026-10-23', '2026-10-26', '2026-10-24']),
                              'value': [100.0, np.nan, 101.0]})
        self.assertEqual(latest_vintage(frame).to_dict(), {pd.Timestamp('2026-10-23'): 101.0})

    def test_bundled_config_names_catalog_series_and_flags_every_proxy(self):
        from pipeline.report.source import load_config
        from pipeline.warehouse.catalog.mapping import load_mapping, load_series
        config = load_config()
        keys = {s['key'] for s in load_series()}
        mapping = load_mapping()
        for item in config['assets'] + config['yields']:
            self.assertIn(item['series'], keys)
            uses = [m for m in mapping.values() if '{' + item['series'] + '}' in m['formula']]
            if item.get('proxy') or any(m['method'] == 'proxy' for m in uses if m['formula'].strip() == '{' + item['series'] + '}'):
                self.assertTrue(item.get('note', '').endswith('代理'), item)

    def test_inputs_use_latest_vintage_asof_cutoff_and_name_lagging_series(self):
        from pipeline.report.source import build_inputs, StoreFetcher
        from pipeline.warehouse.db.store import SQLiteStore
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'w.db'
            config = seed_store(path)
            store = SQLiteStore(path)
            levels, yields, meta = build_inputs(config, StoreFetcher(store), date(2026, 10, 23),
                                                now=datetime(2026, 10, 24, 14, tzinfo=timezone.utc))
        names = [a['name'] for a in config['assets']]
        self.assertEqual(list(levels.columns), names)
        self.assertEqual(levels.loc['2026-10-16', names[0]], 123.0)
        self.assertEqual(levels.index.max(), pd.Timestamp('2026-10-23'))
        self.assertEqual(list(yields.columns), [y['tenor'] for y in config['yields']])
        self.assertEqual((meta['as_of'], meta['week_start'], meta['week_end']), ('2026-10-23', '2026-10-16', '2026-10-23'))
        self.assertEqual(meta['date_rule'], 'asof')
        self.assertFalse(meta['is_demo'])
        self.assertEqual(meta['heatmap_starts']['YTD'], '2025-12-31')
        self.assertIn('截至10月22日', meta['series_notes'][names[0]])
        for item in config['assets']:
            if item.get('note'):
                self.assertIn(item['note'], meta['series_notes'][item['name']])
        self.assertEqual(meta['omitted'], [])

    def test_stale_series_are_left_out_and_said_so(self):
        from pipeline.report.source import build_inputs, StoreFetcher
        from pipeline.warehouse.db.store import SQLiteStore
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'w.db'
            config = seed_store(path, stale_gold=True)
            levels, _, meta = build_inputs(config, StoreFetcher(SQLiteStore(path)), date(2026, 10, 23),
                                           now=datetime(2026, 10, 24, 14, tzinfo=timezone.utc))
        self.assertNotIn('黄金', levels.columns)
        self.assertNotIn('黄金', meta.get('highlight', []))
        self.assertEqual(meta['omitted'], ['黄金（最新数据为10月9日）'])

    def test_build_command_writes_a_real_issue_from_the_database(self):
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'w.db'
            seed_store(path)
            out = Path(folder) / 'issue'
            run = subprocess.run([sys.executable, '-m', 'pipeline.report', 'build', '--db', f'sqlite:///{path}',
                                  '--week', '2026-10-23', '--output-dir', str(out)],
                                 capture_output=True, text=True, cwd=REPO)
            self.assertEqual(run.returncode, 0, run.stderr)
            pdf = PdfReader(out / 'weekly-report.pdf')
            text = ''.join(page.extract_text() for page in pdf.pages)
            self.assertNotIn('DEMO', text)
            self.assertIn('代理', text)
            last = pdf.pages[-1].extract_text()
            self.assertIn('数据说明', last)
            self.assertIn('SPY 总回报代理，截至10月22日', last)
            self.assertIn('10月23日', text)
            summary = json.loads((out / 'issue.json').read_text(encoding='utf-8'))
            self.assertEqual(summary['as_of'], '2026-10-23')
            self.assertEqual(summary['pages'], len(pdf.pages))


if __name__ == '__main__':
    unittest.main()
