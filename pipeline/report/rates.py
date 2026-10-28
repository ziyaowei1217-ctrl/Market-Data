"""Rate levels are percentage numbers (4.25 means 4.25%); differences are bp."""
from pathlib import Path
import csv
import json

import numpy as np
import pandas as pd

TENORS = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '20Y', '30Y']


def validate_yields(frame, cutoff):
    if (not isinstance(frame.index, pd.DatetimeIndex) or frame.index.hasnans
            or frame.index.has_duplicates or frame.index.tz is not None
            or (frame.index != frame.index.normalize()).any()):
        raise ValueError('收益率日期必须为不重复、不带时区的日频日期。')
    if not 1 <= len(frame.columns) <= len(TENORS) or frame.columns.has_duplicates:
        raise ValueError('收益率需要 1–11 个不重名的期限列。')
    if any(name not in TENORS for name in frame.columns):
        raise ValueError('收益率期限仅支持：' + ', '.join(TENORS))
    frame = frame.apply(pd.to_numeric, errors='raise').sort_index().loc[:pd.Timestamp(cutoff)]
    if np.isinf(frame.to_numpy(dtype=float)).any():
        raise ValueError('收益率不能包含无穷值。')
    if len(frame) < 2 or (frame.count() < 2).any():
        raise ValueError('截止日之前每个期限至少需要两个有效观测值。')
    return frame[[tenor for tenor in TENORS if tenor in frame.columns]]


def load_yields(path, cutoff):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        header = next(csv.reader(handle), [])
    if not header or any(not name.strip() for name in header) or len(set(header)) != len(header):
        raise ValueError('收益率 CSV 列名不能为空或重复。')
    frame = pd.read_csv(path)
    if 'date' not in frame:
        raise ValueError('收益率 CSV 必须含 date 列。')
    frame['date'] = pd.to_datetime(frame['date'], format='%Y-%m-%d', errors='raise')
    return validate_yields(frame.set_index('date'), cutoff)


def curve_snapshot(frame, start, end):
    dates = [pd.Timestamp(start), pd.Timestamp(end)]
    if dates[0] >= dates[1] or any(date not in frame.index for date in dates):
        raise ValueError('对比日期必须按先后排列并存在于收益率 CSV。')
    if dates[1] - dates[0] != pd.Timedelta(days=7):
        raise ValueError('周度收益率对比日期必须相隔 7 天。')
    if frame.loc[dates].isna().any().any():
        raise ValueError('收益率对比日期存在缺失值；不会自动补值。')
    return frame.loc[dates[0]], frame.loc[dates[1]]


def spread_bp(frame):
    if not {'2Y', '10Y'}.issubset(frame.columns):
        raise ValueError('2s10s 利差需要 2Y 和 10Y 两列。')
    result = (frame['10Y'] - frame['2Y']) * 100
    if result.count() < 2:
        raise ValueError('利差至少需要两个两期限均有数据的日期。')
    return result


def horizon_returns(frame, starts, end):
    if not isinstance(starts, dict) or not 1 <= len(starts) <= 4:
        raise ValueError('heatmap_starts 须为含 1–4 个比较区间的字典。')
    end = pd.Timestamp(end)
    if end not in frame.index or frame.loc[end].isna().any():
        raise ValueError('热力图截止日必须存在且所有资产有数据。')
    result = {}
    for label, date in starts.items():
        if not isinstance(label, str) or not label.strip() or len(label) > 6:
            raise ValueError('热力图区间名称须为 1–6 个字符。')
        date = pd.Timestamp(date)
        if pd.isna(date) or date.tz is not None or date != date.normalize() or date >= end:
            raise ValueError('热力图基准日必须是早于截止日的有效日频日期。')
        base = frame.loc[date] if date in frame.index else pd.Series(np.nan, index=frame.columns)
        result[label] = (frame.loc[end] / base - 1) * 100
    return pd.DataFrame(result)


def create_rates_demo(folder):
    folder = Path(folder)
    dates = pd.bdate_range('2025-10-24', '2026-10-23')
    rng = np.random.default_rng(625)
    t = np.linspace(0, 1, len(dates))
    current = [3.72, 3.68, 3.59, 3.52, 3.65, 3.76, 3.93, 4.10, 4.28, 4.65, 4.71]
    previous = [3.75, 3.72, 3.65, 3.60, 3.72, 3.80, 3.91, 4.04, 4.17, 4.51, 4.55]
    initial = [4.2, 4.15, 4.1, 4.05, 4.1, 4.0, 3.9, 3.85, 3.8, 4.1, 4.2]
    week = dates.get_loc(pd.Timestamp('2026-10-16'))
    data = {}
    for tenor, first, before, after in zip(TENORS, initial, previous, current):
        noise = np.cumsum(rng.normal(0, .012, len(t)))
        bridge = noise - noise[0] - t * (noise[-1] - noise[0])
        values = first + t * (after - first) + bridge
        values[week:] = np.linspace(before, after, len(t) - week)
        data[tenor] = values
    pd.DataFrame(data, index=dates).rename_axis('date').to_csv(folder / 'yields.csv', float_format='%.6f')
    path = folder / 'metadata.json'
    meta = json.loads(path.read_text(encoding='utf-8'))
    meta['source'] = '模拟数据 · 资产种子24 / 利率种子625'
    meta['heatmap_starts'] = {'1W': '2026-10-16', '1M': '2026-09-23', '3M': '2026-07-23', 'YTD': '2025-12-31'}
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return folder / 'yields.csv'
