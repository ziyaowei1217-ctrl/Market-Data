"""python3 -m pipeline.report build: this week's issue straight from the warehouse."""
import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path

from .source import CONFIG, RestFetcher, StoreFetcher, build_inputs, default_cutoff, load_config

PLAYWRIGHT_HINT = '需要 Playwright 与 Chromium：pip install playwright && python -m playwright install chromium'


def write_issue(levels, yields, meta, output, charts=True):
    """Draw 市场一周 with the design system: weekly-report.pdf, plus <chart>.png for each chart block."""
    from .issue import issue_spec
    from .render import render
    try:
        import playwright  # noqa: F401
    except ImportError as exc:
        raise ValueError(PLAYWRIGHT_HINT) from exc
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = render(issue_spec(levels, yields, meta), output / 'weekly-report.pdf', output if charts else None)
    if report['overflow']:
        raise ValueError('版面超出底线：' + '；'.join(f"第 {o['page']} 页 {o['text']}" for o in report['overflow']))
    return report


def summarize(meta, report, output):
    summary = dict(as_of=meta['as_of'], week_start=meta['week_start'], updated_at=meta['updated_at'],
                   pages=report['pages'], charts=report['charts'], omitted=meta.get('omitted', []),
                   series_notes=meta.get('series_notes', {}),
                   files=['weekly-report.pdf'] + [f'{key}.png' for key in report['charts']])
    (Path(output) / 'issue.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return summary


def build_issue_from_warehouse(fetcher, output, cutoff, config_path=CONFIG, now=None):
    """Fetch, draw and write weekly-report.pdf, one PNG per chart, and issue.json (a summary for upload)."""
    config = load_config(config_path)
    levels, yields, meta = build_inputs(config, fetcher, cutoff, now)
    return summarize(meta, write_issue(levels, yields, meta, output), output)


def build_demo(output):
    """The same issue from the fixed-seed demo data: no database, for previews and tests."""
    import tempfile
    from .data import create_demo, load_inputs
    from .rates import create_rates_demo, load_yields
    with tempfile.TemporaryDirectory() as folder:
        levels, meta = load_inputs(*create_demo(folder))
        yields = load_yields(create_rates_demo(folder), meta['as_of'])
    meta.update(market_colors='cn', focus_asset='美国股票', highlight=['美国股票', '黄金'],
                correlation_pair=['美国股票', '美国国债'])
    return summarize(meta, write_issue(levels, yields, meta, output), output)


def choose_fetcher(db):
    db = db or os.environ.get('WAREHOUSE_DB_URL')
    if db:
        from pipeline.warehouse.db.store import open_store
        return StoreFetcher(open_store(db))
    if os.environ.get('WAREHOUSE_EMAIL') or os.environ.get('WAREHOUSE_ACCESS_TOKEN'):
        return RestFetcher()
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(prog='python3 -m pipeline.report build', description='从数据库生成本周周报 PDF。')
    parser.add_argument('--week', type=date.fromisoformat, help='周度截点（周五，YYYY-MM-DD）；默认最近一个已收盘的周五')
    parser.add_argument('--db', help='数据库连接串（默认读 WAREHOUSE_DB_URL）；都没有时用读者账号 '
                                     'WAREHOUSE_EMAIL / WAREHOUSE_PASSWORD 走 REST')
    parser.add_argument('--config', type=Path, default=CONFIG, help='资产、期限与图表配置（默认 pipeline/report/issue.json）')
    parser.add_argument('--output-dir', type=Path, default=Path('outputs/weekly'))
    parser.add_argument('--demo', action='store_true', help='用固定种子的模拟数据出一期样张，不连数据库')
    args = parser.parse_args(argv)
    if args.demo:
        try:
            summary = build_demo(args.output_dir)
        except (ValueError, OSError) as exc:
            parser.exit(2, f'无法生成周报：{exc}\n')
        print((args.output_dir / 'weekly-report.pdf').resolve())
        print(f"{summary['as_of']} · {summary['pages']} 页 · {len(summary['charts'])} 张图 · 模拟数据")
        return
    cutoff = args.week or default_cutoff(datetime.now(timezone.utc).date())
    if cutoff.weekday() != 4:
        parser.error(f'{cutoff} 不是周五；周报以周五为截点。')
    fetcher = choose_fetcher(args.db)
    if fetcher is None:
        parser.error('请设置 WAREHOUSE_DB_URL（或 --db），或读者账号 WAREHOUSE_EMAIL / WAREHOUSE_PASSWORD。')
    try:
        summary = build_issue_from_warehouse(fetcher, args.output_dir, cutoff, args.config)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.exit(2, f'无法生成周报：{exc}\n')
    print((args.output_dir / 'weekly-report.pdf').resolve())
    print(f"{summary['as_of']} · {summary['pages']} 页 · {len(summary['charts'])} 张图")
    for line in summary['omitted']:
        print(f'未列入：{line}')
