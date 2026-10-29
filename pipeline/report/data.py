"""Explicit data contracts for price/index-level charts (not yields or raw percentages)."""
from datetime import datetime, timezone
from pathlib import Path
import json
import csv

import numpy as np
import pandas as pd


def validate_levels(frame, cutoff):
    frame = frame.copy()
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.hasnans:
        raise ValueError('date 必须是有效日期。')
    if frame.index.tz is not None or (frame.index != frame.index.normalize()).any():
        raise ValueError('date 必须为不带时区的日频日期。')
    if frame.index.has_duplicates:
        raise ValueError('date 不允许重复。')
    if not 1 <= len(frame.columns) <= 6 or frame.columns.has_duplicates:
        raise ValueError('需要 1–6 个不重名的资产列。')
    if any(not isinstance(c, str) or not c.strip() or len(c) > 12 for c in frame.columns):
        raise ValueError('资产名称须为 1–12 个字符。')
    frame = frame.apply(pd.to_numeric, errors='raise').sort_index()
    frame = frame.loc[:pd.Timestamp(cutoff)]
    values = frame.to_numpy(dtype=float)
    if np.isinf(values).any() or (values <= 0).any():
        raise ValueError('资产价格/指数必须为正数，不能包含无穷值。')
    if len(frame) < 2 or (frame.count() < 2).any():
        raise ValueError('截止日期之前每个资产至少需要两个有效值。')
    return frame


def normalize(frame):
    common = frame.dropna(how='any')
    if common.empty:
        raise ValueError('找不到所有资产都有观测值的共同基准日。')
    base_date = common.index[0]
    result = frame.loc[base_date:] / common.iloc[0] * 100
    if len(result) < 2 or (result.count() < 2).any():
        raise ValueError('共同基准日之后每个资产至少需要两个有效值。')
    return result


ASOF_DAYS = 6


def tolerance(meta):
    """'exact' (default): the dates must exist. 'asof': last value on/before the date, within 6 days."""
    rule = meta.get('date_rule', 'exact')
    if rule not in ('exact', 'asof'):
        raise ValueError('date_rule 只能是 "exact" 或 "asof"。')
    return ASOF_DAYS if rule == 'asof' else 0


def values_at(frame, date, days):
    """Each column's last valid value on/before date and no older than `days`; NaN where there is none."""
    date = pd.Timestamp(date)
    window = frame.loc[date - pd.Timedelta(days=days):date]
    if window.empty:
        return pd.Series(np.nan, index=frame.columns)
    return window.ffill().iloc[-1]


def obs_dates(frame, date, days):
    """The observation date behind each column's value_at; NaT where there is none."""
    date = pd.Timestamp(date)
    window = frame.loc[date - pd.Timedelta(days=days):date]
    return pd.Series({name: window[name].last_valid_index() for name in frame.columns}, dtype='datetime64[ns]')


def require_values(values, date, days):
    missing = [str(name) for name in values.index[values.isna()]]
    if missing:
        raise ValueError(f"{'、'.join(missing)} 在 {pd.Timestamp(date):%Y-%m-%d} 前 {days} 天内没有数据。")
    return values


def weekly_returns(frame, start, end, days=0):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if end - start != pd.Timedelta(days=7):
        raise ValueError('周涨跌幅起止日期必须相隔 7 天。')
    if days:
        before = require_values(values_at(frame, start, days), start, days)
        after = require_values(values_at(frame, end, days), end, days)
        return (after / before - 1) * 100
    if start not in frame.index or end not in frame.index:
        raise ValueError('周涨跌幅起止日期必须在 CSV 中存在；不会自动补值。')
    if frame.loc[[start, end]].isna().any().any():
        raise ValueError('周涨跌幅起止日期存在缺失值；请明确选定可比较的日期。')
    return (frame.loc[end] / frame.loc[start] - 1) * 100


def load_metadata(metadata_path):
    meta = json.loads(Path(metadata_path).read_text(encoding='utf-8'))
    for key in ('source', 'updated_at', 'as_of', 'week_start', 'week_end', 'is_demo'):
        if key not in meta:
            raise ValueError(f'metadata 缺少 {key}')
    if not isinstance(meta['is_demo'], bool):
        raise ValueError('is_demo 必须是布尔值。')
    if not isinstance(meta['source'], str) or not meta['source'].strip() or len(meta['source']) > 50:
        raise ValueError('source 须为 1–50 个字符。')
    updated = datetime.fromisoformat(meta['updated_at'].replace('Z', '+00:00'))
    if updated.tzinfo is None:
        raise ValueError('updated_at 必须包含时区。')
    for key in ('as_of', 'week_start', 'week_end'):
        datetime.strptime(meta[key], '%Y-%m-%d')
    if meta['week_end'] != meta['as_of']:
        raise ValueError('第一版要求 week_end 与 as_of 相同。')
    meta['updated_at'] = updated.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    return meta


def load_inputs(csv_path, metadata_path):
    meta = load_metadata(metadata_path)
    with Path(csv_path).open(encoding='utf-8-sig', newline='') as handle:
        header = next(csv.reader(handle), [])
    if len(header) != len(set(header)):
        raise ValueError('CSV 列名不允许重复。')
    if not header or any(not name.strip() for name in header):
        raise ValueError('CSV 列名不允许为空。')
    frame = pd.read_csv(csv_path)
    if 'date' not in frame.columns:
        raise ValueError('CSV 必须含 date 列。')
    frame['date'] = pd.to_datetime(frame['date'], format='%Y-%m-%d', errors='raise')
    frame = validate_levels(frame.set_index('date'), meta['as_of'])
    return frame, meta


def create_demo(folder):
    """Synthetic paths; fixed seed, same observations feed both charts."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    dates = pd.bdate_range('2025-10-24', '2026-10-23')
    rng = np.random.default_rng(24)
    names = ['美国股票', '黄金', '全球股票', '美国国债', '投资级债', '美元指数']
    target = [118.4, 128.6, 112.9, 105.2, 108.1, 97.3]
    weekly = [1.84, 2.31, 1.12, -0.48, 0.36, -0.92]
    data = {}
    t = np.linspace(0, 1, len(dates))
    start_idx = dates.get_loc(pd.Timestamp('2026-10-16'))
    for name, final, change in zip(names, target, weekly):
        noise = np.cumsum(rng.normal(0, .006, len(dates)))
        bridge = noise - t * noise[-1]
        path = 100 * np.exp(t * np.log(final / 100) + bridge)
        prior = final / (1 + change / 100)
        path[start_idx:] = np.linspace(prior, final, len(dates) - start_idx)
        data[name] = path
    frame = pd.DataFrame(data, index=dates).rename_axis('date')
    frame.to_csv(folder / 'levels.csv', float_format='%.6f')
    meta = dict(source='模拟数据 · 固定随机种子 24', updated_at='2026-10-23T20:00:00Z',
                as_of='2026-10-23', week_start='2026-10-16', week_end='2026-10-23', is_demo=True)
    (folder / 'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return folder / 'levels.csv', folder / 'metadata.json'
