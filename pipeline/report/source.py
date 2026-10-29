"""Weekly issue inputs from the warehouse: issue.json → (levels, yields, metadata).

Each series is read at its latest vintage, cut at the Friday cutoff, and placed on a
Monday–Friday calendar. A market holiday inside a series (at most three weekdays) carries
the previous close; the end of a series is never extended, so a feed that stops early shows
its own last date ("截至10月22日") in the chart notes. A series with nothing within six days
of either weekly cutoff is left out of the issue and listed on the front page.
"""
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

import pandas as pd

from .data import ASOF_DAYS, validate_levels
from .rates import TENORS, validate_yields

CONFIG = Path(__file__).with_name('issue.json')
HOLIDAY_FILL = 3


def friday_cutoff(day):
    """The weekly cutoff: the last Friday on or before `day`."""
    return day - timedelta(days=(day.weekday() - 4) % 7)


def default_cutoff(today):
    """The last Friday whose close is in: on a Friday itself, the week before."""
    return friday_cutoff(today - timedelta(days=1))


def month_day(value):
    value = pd.Timestamp(value)
    return f'{value.month}月{value.day}日'


def load_config(path=CONFIG):
    config = json.loads(Path(path).read_text(encoding='utf-8'))
    assets, yields = config.get('assets', []), config.get('yields', [])
    names = [a.get('name') for a in assets]
    if not 1 <= len(assets) <= 6 or len(set(names)) != len(names) or any(not a.get('series') for a in assets):
        raise ValueError('issue.json: assets 需要 1–6 个不重名、带 series 的资产。')
    tenors = [y.get('tenor') for y in yields]
    if len(set(tenors)) != len(tenors) or any(t not in TENORS or not y.get('series') for t, y in zip(tenors, yields)):
        raise ValueError('issue.json: yields 的 tenor 须为 ' + '、'.join(TENORS) + '，且带 series。')
    for item in assets + yields:
        if item.get('proxy') and not str(item.get('note', '')).endswith('代理'):
            raise ValueError(f"issue.json: 代理序列 {item['series']} 的 note 须以「代理」结尾。")
    return config


def latest_vintage(frame):
    """Observations (obs_date, realtime_start, value) → one value per obs_date, newest vintage; nulls dropped."""
    if frame is None or frame.empty:
        return pd.Series(dtype=float)
    frame = frame.sort_values(['obs_date', 'realtime_start'], kind='mergesort')
    last = frame.drop_duplicates('obs_date', keep='last')  # a newer null vintage withdraws the value
    values = pd.Series(pd.to_numeric(last['value'], errors='coerce').to_numpy(),
                       index=pd.to_datetime(last['obs_date']).dt.normalize())
    return values.dropna()


class StoreFetcher:
    """Direct database access (WAREHOUSE_DB_URL), as the warehouse workflow uses."""

    def __init__(self, store):
        self.store = store

    def fetch(self, keys, since):
        frames = self.store.load_observations(list(keys), since)
        return {key: latest_vintage(frames.get(key)) for key in keys}


class RestFetcher:
    """Reader access over the REST API (WAREHOUSE_EMAIL / WAREHOUSE_PASSWORD)."""

    def fetch(self, keys, since):
        from pipeline.warehouse import client
        result = {}
        for key in keys:
            rows = client.series(key, since.isoformat())
            if rows.empty:
                result[key] = pd.Series(dtype=float)
                continue
            values = pd.Series(pd.to_numeric(rows['value'], errors='coerce').to_numpy(),
                               index=pd.to_datetime(rows['obs_date']).dt.normalize())
            result[key] = values.dropna()
        return result


def on_weekdays(series, start, cutoff):
    """Place a series on the Monday–Friday calendar; carry a close across short holidays only."""
    days = pd.bdate_range(start, cutoff)
    raw = series[(series.index >= pd.Timestamp(start)) & (series.index <= pd.Timestamp(cutoff))]
    raw = raw[raw.index.dayofweek < 5]
    if raw.empty:
        return pd.Series(float('nan'), index=days)
    placed = raw.reindex(days).ffill(limit=HOLIDAY_FILL)
    return placed.where(placed.index <= raw.index.max())


def check(series, name, week_start, cutoff):
    """None when the series can price both weekly cutoffs; otherwise why it is left out."""
    last = series.last_valid_index()
    if last is None:
        return f'{name}（无数据）'
    if (cutoff - last).days > ASOF_DAYS:
        return f'{name}（最新数据为{month_day(last)}）'
    prior = series.loc[:week_start].last_valid_index()
    if prior is None or (week_start - prior).days > ASOF_DAYS:
        return f'{name}（{month_day(week_start)}前后缺数据）'
    return None


def build_inputs(config, fetcher, cutoff, now=None):
    cutoff = pd.Timestamp(cutoff).normalize()
    week_start = cutoff - pd.Timedelta(days=7)
    first = (cutoff - pd.Timedelta(days=int(config.get('history_days', 366)))).date()
    items = config['assets'] + config['yields']
    data = fetcher.fetch([item['series'] for item in items], first - timedelta(days=ASOF_DAYS + 1))

    omitted, notes, columns = [], {}, {'assets': {}, 'yields': {}}
    for group, label in (('assets', 'name'), ('yields', 'tenor')):
        for item in config[group]:
            name = item[label]
            series = on_weekdays(data.get(item['series'], pd.Series(dtype=float)), first, cutoff)
            reason = check(series, name, week_start, cutoff)
            if reason:
                omitted.append(reason)
                continue
            columns[group][name] = series
            parts = [item['note']] if item.get('note') else []
            last = series.last_valid_index()
            if last != cutoff:
                parts.append(f'截至{month_day(last)}')
            if parts:
                notes[name] = '，'.join(parts)

    if len(columns['assets']) < 2:
        raise ValueError('可用资产不足两个，无法出刊：' + '；'.join(omitted))
    levels = validate_levels(pd.DataFrame(columns['assets']).rename_axis('date'), cutoff)
    yields = validate_yields(pd.DataFrame(columns['yields']).rename_axis('date'), cutoff) \
        if len(columns['yields']) >= 2 else None

    style = dict(config.get('style', {}))
    kept = list(levels.columns)
    style['highlight'] = [n for n in style.get('highlight', []) if n in kept] or kept[:1]
    if style.get('focus_asset') not in kept:
        style['focus_asset'] = style['highlight'][0]
    if style.get('benchmark') not in kept:
        style.pop('benchmark', None)
    pair = style.get('correlation_pair')
    if pair and not set(pair) <= set(kept):
        style.pop('correlation_pair')

    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    year_end = pd.Timestamp(year=cutoff.year - 1, month=12, day=31)
    meta = dict(
        style,
        source=config['source'],
        **({'rates_source': config['rates_source']} if config.get('rates_source') else {}),
        updated_at=now.strftime('%Y-%m-%d %H:%M UTC'),
        as_of=f'{cutoff:%Y-%m-%d}', week_start=f'{week_start:%Y-%m-%d}', week_end=f'{cutoff:%Y-%m-%d}',
        is_demo=False,
        date_rule='asof',
        heatmap_starts={'1W': f'{week_start:%Y-%m-%d}',
                        '1M': f'{cutoff - pd.DateOffset(months=1):%Y-%m-%d}',
                        '3M': f'{cutoff - pd.DateOffset(months=3):%Y-%m-%d}',
                        'YTD': f'{year_end:%Y-%m-%d}'},
        quoted=[a['name'] for a in config['assets'] if a.get('quoted') and a['name'] in kept],
        series_sources={a['name']: a['source'] for a in config['assets'] if a.get('source') and a['name'] in kept},
        series_notes=notes,
        omitted=omitted,
    )
    return levels, yields, meta
