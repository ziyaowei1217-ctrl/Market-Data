"""python3 -m pipeline.report build: this week's issue straight from the warehouse."""
import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path

from .charts import export_report
from .source import CONFIG, RestFetcher, StoreFetcher, build_inputs, default_cutoff, drawable, load_config


def build_issue_from_warehouse(fetcher, output, cutoff, config_path=CONFIG, now=None):
    """Fetch, draw and write weekly-report.pdf, the single charts, and issue.json (a summary for upload)."""
    from pypdf import PdfReader
    config = load_config(config_path)
    levels, yields, meta = build_inputs(config, fetcher, cutoff, now)
    charts = drawable(config['charts'], levels, yields)
    paths = export_report(levels, meta, output, yields=yields, selected=charts)
    output = Path(output)
    summary = dict(as_of=meta['as_of'], week_start=meta['week_start'], updated_at=meta['updated_at'],
                   pages=len(PdfReader(paths[0]).pages), charts=charts, omitted=meta['omitted'],
                   series_notes=meta['series_notes'], files=[p.name for p in paths])
    (output / 'issue.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return summary


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
    args = parser.parse_args(argv)
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
