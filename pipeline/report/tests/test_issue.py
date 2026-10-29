"""The 市场一周 issue in the Richard Wei Finance design system: content spec and rendering (offline)."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]


def demo_inputs(market='cn', yields=True, **extra):
    from pipeline.report.data import create_demo, load_inputs
    from pipeline.report.rates import create_rates_demo, load_yields
    folder = tempfile.mkdtemp()
    levels, meta = load_inputs(*create_demo(folder))
    curve = load_yields(create_rates_demo(folder), meta['as_of']) if yields else None
    meta.update(market_colors=market, highlight=['美国股票', '黄金'], focus_asset='美国股票', **extra)
    return levels, curve, meta


def walk(node):
    """Every block in a spec (cover groups, side blocks, bands, columns, pairs)."""
    if isinstance(node, dict):
        if 't' in node:
            yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


class IssueSpecTests(unittest.TestCase):
    def test_sections_follow_the_issue_order(self):
        from pipeline.report.issue import issue_spec
        spec = issue_spec(*demo_inputs())
        self.assertEqual([s['title'] for s in spec['sections']], ['市场仪表盘', '风险与相关', '固定收益', '来源与方法'])
        self.assertEqual((spec['lang'], spec['market'], spec['series']), ('zh', 'cn', '市场一周'))
        no_rates = issue_spec(*demo_inputs(yields=False))
        self.assertNotIn('固定收益', [s['title'] for s in no_rates['sections']])

    def test_us_convention_unless_the_edition_is_chinese_market(self):
        from pipeline.report.issue import issue_spec
        self.assertIsNone(issue_spec(*demo_inputs(market='global'))['market'])

    def test_cover_states_the_week_in_two_short_lines_and_a_dated_lede(self):
        from pipeline.report.issue import issue_spec
        levels, curve, meta = demo_inputs()
        cover = issue_spec(levels, curve, meta)['cover']
        lead, main = cover['titleLines']
        self.assertTrue(1 <= len(lead) <= 16 and 1 <= len(main) <= 16, cover['titleLines'])
        self.assertIn('黄金', main)                     # the demo's biggest weekly move
        self.assertIn('10月23日', cover['lede'])
        custom = issue_spec(levels, curve, {**meta, 'cover': {'lead': '自定引题', 'title': '自定主标题'}})['cover']
        self.assertEqual(custom['titleLines'], ['自定引题', '自定主标题'])

    def test_every_chart_has_a_dated_source_and_one_subject(self):
        from pipeline.report.issue import issue_spec
        spec = issue_spec(*demo_inputs())
        charts = [b for b in walk(spec) if b['t'] == 'chart']
        self.assertGreaterEqual(len(charts), 9)
        self.assertEqual(len({c['key'] for c in charts}), len(charts))
        for c in charts:
            self.assertTrue(c['source'].startswith('来源：') and '截至' in c['source'], c['key'])
            props = c['chart']['props']
            if c['chart']['c'] == 'LineChart':
                roles = [s.get('role') for s in props['series']]
                self.assertLessEqual(len(roles), 4, c['key'])
                self.assertEqual(roles.count('subject'), 1, c['key'])

    def test_figures_match_the_calculations(self):
        from pipeline.report.issue import issue_spec
        from pipeline.report.data import weekly_returns
        from pipeline.report.rates import curve_snapshot
        levels, curve, meta = demo_inputs()
        spec = issue_spec(levels, curve, meta)
        charts = {b['key']: b for b in walk(spec) if b['t'] == 'chart'}
        weekly = weekly_returns(levels, meta['week_start'], meta['week_end'])
        columns = charts['asset-returns']['chart']['props']
        week = next(s for s in columns['series'] if s['role'] == 'subject')
        self.assertEqual(week['data'], [round(weekly[n], 4) for n in columns['categories']])
        before, after = curve_snapshot(curve, meta['week_start'], meta['week_end'])
        line = charts['yield-curve']['chart']['props']
        now = next(s for s in line['series'] if s['role'] == 'subject')
        self.assertEqual(now['data'], [round(after[t], 4) for t in line['labels']])

    def test_pages_with_returns_carry_the_risk_warning(self):
        from pipeline.report.issue import issue_spec
        spec = issue_spec(*demo_inputs())
        for section in spec['sections'][:-1]:
            self.assertEqual(section['warning']['lead'], '过往业绩并不预示未来表现。')
        risk = [b for b in walk(spec['cover']) if b['t'] == 'risk']
        self.assertEqual(len(risk), 1)

    def test_sources_page_names_proxies_dates_gaps_and_the_issuer(self):
        from pipeline.report.issue import issue_spec
        levels, curve, meta = demo_inputs(series_notes={'黄金': 'COMEX 期货近月代理'},
                                          omitted=['铜（最新数据为10月9日）'],
                                          series_sources={'黄金': 'Yahoo Finance：COMEX 黄金期货近月'})
        last = issue_spec(levels, curve, meta)['sections'][-1]
        text = json.dumps(last, ensure_ascii=False)
        for needle in ('COMEX 期货近月代理', '铜（最新数据为10月9日）', '发布方', '发布时间', '信息来源', '风险提示'):
            self.assertIn(needle, text)
        self.assertFalse(last.get('warning'))

    def test_demo_issues_say_so(self):
        from pipeline.report.issue import issue_spec
        spec = issue_spec(*demo_inputs())
        self.assertIn('模拟数据', spec['date'])


class IssueRenderTests(unittest.TestCase):
    def test_the_demo_issue_fills_a4_pages_without_overflow(self):
        from pypdf import PdfReader
        from pipeline.report.issue import issue_spec
        from pipeline.report.render import render
        spec = issue_spec(*demo_inputs())
        with tempfile.TemporaryDirectory() as folder:
            pdf, charts = Path(folder) / 'issue.pdf', Path(folder) / 'charts'
            report = render(spec, pdf, charts, scale=1)
            self.assertEqual(report['overflow'], [])
            reader = PdfReader(pdf)
            self.assertEqual(len(reader.pages), report['pages'])
            self.assertTrue(4 <= report['pages'] <= 7, report)
            for page in reader.pages:
                self.assertAlmostEqual(float(page.mediabox.width), 595.3, delta=1)
                self.assertAlmostEqual(float(page.mediabox.height), 841.9, delta=1)
            text = ''.join(p.extract_text() for p in reader.pages)
            for needle in ('市场一周', '来源与方法', '过往业绩并不预示未来表现', '模拟数据'):
                self.assertIn(needle, text)
            pngs = sorted(p.stem for p in charts.glob('*.png'))
            self.assertEqual(pngs, sorted(report['charts']))


if __name__ == '__main__':
    unittest.main()
