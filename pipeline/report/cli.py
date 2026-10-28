#!/usr/bin/env python3
"""Local financial chart generator: CSV → PNG and vector PDF."""
import argparse
import sys
from pathlib import Path
import tempfile

from .data import create_demo, load_inputs, load_metadata
from .rates import create_rates_demo, load_yields
from .charts import export_report
from .street_data import STREET, create_street_demo, load_bundle

CHARTS = ['trends', 'returns', 'curve', 'spread', 'heatmap', 'comparison'] + STREET


def main():
    if sys.argv[1:2] == ['build']:
        from .build import main as build
        return build(sys.argv[2:])
    parser = argparse.ArgumentParser(description=__doc__ + '  从数据库出刊：python3 -m pipeline.report build --help')
    parser.add_argument('--demo', action='store_true', help='使用固定种子的模拟数据')
    parser.add_argument('--csv', type=Path, help='资产价格/指数宽表：date + 1–6 个资产列')
    parser.add_argument('--yields', type=Path, help='收益率宽表：date + 1M/2Y/10Y 等期限；4.25 表示 4.25%')
    parser.add_argument('--bundle', type=Path, help='附加表格目录：candlestick/waterfall/football/sensitivity/flows/valuation.csv')
    parser.add_argument('--metadata', type=Path, help='来源、日期、heatmap_starts 等 JSON 元数据')
    parser.add_argument('--charts', nargs='+', choices=['all'] + CHARTS,
                        help='选择图表；demo 默认全部，CSV 默认 trends returns')
    parser.add_argument('--output-dir', type=Path, default=Path('outputs'))
    args = parser.parse_args()
    if args.demo and (args.csv or args.yields or args.metadata or args.bundle):
        parser.error('--demo 不能与 --csv / --yields / --bundle / --metadata 混用')
    if not args.demo and not (args.metadata and (args.csv or args.yields or args.bundle)):
        parser.error('请选择 --demo，或提供 --metadata 及 --csv / --yields / --bundle')
    if args.charts and 'all' in args.charts and len(args.charts) > 1:
        parser.error('all 不能与其他图表名称混用')
    selected = args.charts or (CHARTS if args.demo else ['trends', 'returns'])
    if selected == ['all']:
        selected = CHARTS
    try:
        if args.demo:
            with tempfile.TemporaryDirectory() as folder:
                csv_path, meta_path = create_demo(folder)
                yields_path = create_rates_demo(folder)
                create_street_demo(folder)
                frame, meta = load_inputs(csv_path, meta_path)
                bundle = load_bundle(folder, meta['as_of'])
                yields = load_yields(yields_path, meta['as_of'])
        else:
            meta = load_metadata(args.metadata)
            frame = load_inputs(args.csv, args.metadata)[0] if args.csv else None
            yields = load_yields(args.yields, meta['as_of']) if args.yields else None
            bundle = load_bundle(args.bundle, meta['as_of']) if args.bundle else {}
        for path in export_report(frame, meta, args.output_dir, yields, selected, bundle):
            print(path.resolve())
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.exit(2, f'无法生成图表：{exc}\n')


if __name__ == '__main__':
    main()
