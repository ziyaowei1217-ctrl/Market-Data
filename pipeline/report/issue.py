"""市场一周: the issue's content, as a spec that ds/issue.js lays out with the Richard Wei
Finance components (render.py prints it).

The issue argues top-down in the system's fixed order: the cover states the week in two title
lines and a lede; 市场仪表盘, 风险与相关 and 固定收益 follow, each band titled with a finding and
each chart titled with its measure, with its source and date beneath; 来源与方法 closes. Every
sentence is a dated fact computed from the inputs: the issue states no views and no forecasts.
"""
import numpy as np
import pandas as pd

from .data import obs_dates, tolerance, values_at, weekly_returns
from .rates import TENORS, curve_snapshot, horizon_returns, spread_bp
from .street_data import daily_returns, rolling_volatility

SERIES = '市场一周'
WARNING = {'lead': '过往业绩并不预示未来表现。', 'text': '市场有风险，投资需谨慎。'}
SOURCES_PAGE = '来源与方法'
MINUS = '−'
W_NARRATIVE, W_HALF, W_THIRD, W_FULL = 348, 336, 216, 696
ROLES = ['subject', 'context', 'compare', 'light']
ASOF_WINDOW = 6   # chart baselines and period starts: the last close on or before the date


# ── Words and numbers (writing.md: dates day first, one precision per measure, true minus) ──
def md(value):
    value = pd.Timestamp(value)
    return f'{value.month}月{value.day}日'


def ymd(value):
    value = pd.Timestamp(value)
    return f'{value.year}年{value.month}月{value.day}日'


def num(value, digits=1, signed=False, unit=''):
    if value is None or not np.isfinite(value):
        return '–'
    body = f'{abs(value):,.{digits}f}'
    if float(body.replace(',', '')) == 0:
        return body + unit
    return ('+' if value > 0 and signed else MINUS if value < 0 else '') + body + unit


def pct(value, digits=1, signed=True):
    return num(value, digits, signed, '%')


def bp(value, signed=True):
    return num(value, 0, signed, 'bp')


def moved(value, digits=1, up='涨', down='跌', flat='持平'):
    """'涨 0.6%' / '跌 4.1%' / '持平' — the verb carries the sign."""
    if value is None or not np.isfinite(value) or round(abs(value), digits) == 0:
        return flat
    return f'{up if value > 0 else down} {abs(value):.{digits}f}%'


def bp_moved(value, up='上行', down='下行', flat='持平'):
    if value is None or not np.isfinite(value) or round(abs(value)) == 0:
        return flat
    return f'{up if value > 0 else down} {abs(value):.0f}bp'


def clean(values):
    return [None if v is None or not np.isfinite(v) else round(float(v), 4) for v in values]


def month_labels(index):
    return [f'{d.year % 100}年{d.month}月' for d in index]


# ── The week's numbers ─────────────────────────────────────────────────────────
class Week:
    def __init__(self, levels, yields, meta):
        self.meta, self.levels, self.yields = meta, levels, yields
        self.days = tolerance(meta)
        self.as_of, self.start = pd.Timestamp(meta['as_of']), pd.Timestamp(meta['week_start'])
        self.year_ago = self.as_of - pd.DateOffset(years=1)
        self.names = list(levels.columns)
        self.focus = meta.get('focus_asset') if meta.get('focus_asset') in self.names else self.names[0]
        self.notes = meta.get('series_notes') or {}

        self.weekly = weekly_returns(levels, self.start, self.as_of, self.days)
        self.last = values_at(levels, self.as_of, self.days) if self.days else levels.loc[self.as_of]
        self.asset_date = obs_dates(levels, self.as_of, max(self.days, ASOF_WINDOW)).max()
        starts = meta.get('heatmap_starts') or {
            '1周': f'{self.start:%Y-%m-%d}', '1个月': f'{self.as_of - pd.DateOffset(months=1):%Y-%m-%d}',
            '3个月': f'{self.as_of - pd.DateOffset(months=3):%Y-%m-%d}',
            '年初至今': f'{pd.Timestamp(year=self.as_of.year - 1, month=12, day=31):%Y-%m-%d}'}
        starts = {{'1W': '1周', '1M': '1个月', '3M': '3个月', 'YTD': '年初至今'}.get(k, k): v for k, v in starts.items()}
        self.horizons = horizon_returns(levels, starts, self.as_of, ASOF_WINDOW)

        window = levels.loc[self.year_ago - pd.Timedelta(days=ASOF_WINDOW):self.as_of]
        base = values_at(levels, self.year_ago, ASOF_WINDOW).fillna(window.bfill().iloc[0])
        self.year = window.loc[self.year_ago:]
        self.index = self.year / base * 100
        self.high = self.year.max()
        self.high_date = self.year.idxmax()
        self.drawdown = (self.last / self.high - 1) * 100
        vol = rolling_volatility(levels.loc[self.year_ago - pd.Timedelta(days=60):self.as_of])
        self.vol = vol.loc[self.year_ago:]
        self.vol_now = values_at(self.vol, self.as_of, ASOF_WINDOW)

        pair = meta.get('correlation_pair') or self.names[:2]
        self.pair = pair if len(pair) == 2 and all(p in self.names for p in pair) else self.names[:2]
        rets = daily_returns(levels.loc[self.year_ago - pd.Timedelta(days=120):self.as_of])
        corr = rets[self.pair[0]].rolling(60, min_periods=60).corr(rets[self.pair[1]]).clip(-1, 1)
        self.corr = corr.loc[self.year_ago:]

        self.rates = yields is not None and len(yields.columns) >= 2
        if self.rates:
            self.tenors = [t for t in TENORS if t in yields.columns]
            self.before, self.after = curve_snapshot(yields, self.start, self.as_of, self.days)
            self.change = (self.after - self.before) * 100
            dates = obs_dates(yields, self.as_of, max(self.days, ASOF_WINDOW))
            self.rate_date = dates.max()
            self.rate_start = obs_dates(yields, self.start, max(self.days, ASOF_WINDOW)).max()
            self.spread = spread_bp(yields).loc[self.year_ago:self.as_of].dropna() \
                if {'2Y', '10Y'} <= set(self.tenors) else None

    def proxies(self, names):
        return [n for n in names if '代理' in self.notes.get(n, '')]

    def asset_source(self, names=None):
        text = f"来源：{self.meta['source']}；截至{md(self.asset_date)}。"
        if self.proxies(names or self.names):
            text += f'含代理序列，见「{SOURCES_PAGE}」。'
        return text

    def rate_source(self):
        return f"来源：{self.meta.get('rates_source') or self.meta['source']}；截至{md(self.rate_date)}。"


# ── Blocks ─────────────────────────────────────────────────────────────────────
def para(text, lead=None):
    return {'t': 'para', 'lead': lead, 'text': text}


def chart(key, title, qualifier, source, component, props, grow=False, grow_max=None):
    """grow: the chart may take spare page height (up to grow_max px) before the gaps widen."""
    props = {k: v for k, v in props.items() if v is not None}
    return {'t': 'chart', 'key': key, 'title': title, 'qualifier': qualifier, 'source': source,
            'chart': {'c': component, 'props': props}, 'grow': grow, 'growMax': grow_max}


def band(title, layout, *cols):
    return {'t': 'band', 'title': title, 'layout': layout, 'cols': [list(c) for c in cols]}


def line_props(labels, series, width, height, **extra):
    series = [dict(s, role=s.get('role') or ROLES[min(i, 3)]) for i, s in enumerate(series)]
    return dict({'labels': labels, 'series': series, 'width': width, 'height': height, 'xTicks': 4}, **extra)


def ordered(names, first):
    return ([first] if first in names else []) + [n for n in names if n != first]


def panels(week):
    groups = week.meta.get('panels')
    if not groups:
        half = (len(week.names) + 1) // 2
        groups = [{'title': '、'.join(week.names[:half][:2]) + ('等' if half > 2 else ''), 'assets': week.names[:half]},
                  {'title': '、'.join(week.names[half:][:2]) + ('等' if len(week.names) - half > 2 else ''),
                   'assets': week.names[half:]}]
    return [g for g in ({'title': g['title'], 'assets': [a for a in g['assets'] if a in week.names][:4]} for g in groups)
            if g['assets']]


# ── Cover ──────────────────────────────────────────────────────────────────────
def cover(week):
    w = week.weekly.sort_values(ascending=False)
    big = w.abs().idxmax()
    main = f'{big}{moved(w[big])}' if round(abs(w[big]), 1) else '资产涨跌互现'
    ups, n = int((w.round(1) > 0).sum()), len(w)
    if week.rates and '10Y' in week.tenors:
        lead = f'10年美债{bp_moved(week.change["10Y"])}'
    else:
        lead = f'{n} 个资产{ups}涨{int((w.round(1) < 0).sum())}跌'
    custom = week.meta.get('cover') or {}
    lead, main = custom.get('lead') or lead, custom.get('title') or main

    leader, laggard = w.index[0], w.index[-1]
    lede = (f'截至{md(week.as_of)}当周，{n} 个资产中 {ups} 个上涨：{leader}{moved(w[leader])} 居首，'
            f'{laggard}{moved(w[laggard])} 居末。')
    if week.rates and '10Y' in week.tenors:
        lede += f'10年美债收益率{bp_moved(week.change["10Y"])} 至 {week.after["10Y"]:.2f}%。'
    if week.meta.get('is_demo'):
        lede += '本期为模拟数据，非真实行情。'
    lede = custom.get('lede') or lede

    ytd = week.horizons['年初至今'].dropna().sort_values(ascending=False)
    points = [para('、'.join(f'{k} {pct(v)}' for k, v in w.items()) + '。', '资产表现。')]
    if week.rates:
        parts = '、'.join(f'{t} {bp(week.change[t])}' for t in week.tenors if t in ('2Y', '10Y', '30Y')) \
            or '、'.join(f'{t} {bp(week.change[t])}' for t in week.tenors)
        text = f'美债收益率周变动：{parts}。'
        if week.spread is not None and len(week.spread):
            prior = week.spread.loc[:week.start]
            if len(prior):
                text += f'10Y−2Y 利差{bp_moved(week.spread.iloc[-1] - prior.iloc[-1], "走阔", "收窄")} 至 {bp(week.spread.iloc[-1], False)}。'
        points.append(para(text, '利率。'))

    # The chart pair carries the main line: this week's moves, then the biggest mover's quarter.
    quarter = week.levels.loc[week.as_of - pd.DateOffset(months=3):week.as_of]
    names = ordered([big, week.focus], big)
    q = quarter[names] / values_at(quarter[names], quarter.index[0], ASOF_WINDOW) * 100
    pair = {'t': 'pair', 'blocks': [
        chart('cover-week', '本周涨跌幅', '%', week.asset_source(list(w.index)), 'BarChart',
              dict(width=W_THIRD, sort='desc', highlight=big, decimals=1, signed=True, rowHeight=30,
                   data=[{'label': k, 'value': round(float(v), 4)} for k, v in w.items()])),
        chart('cover-quarter', '近3个月走势', '3个月前 = 100', week.asset_source(names), 'LineChart',
              line_props(month_labels(q.index), [{'name': k, 'data': clean(q[k])} for k in names],
                         W_THIRD, 290, decimals=1, reference={'value': 100}, xTicks=3))]}
    quarter_move = q[big].dropna().iloc[-1] - 100
    trend_head = f'{big}近3个月{moved(quarter_move)}，本周{moved(w[big])}'
    closing = []
    if len(ytd):
        closing = [{'t': 'heading', 'text': f'年初至今{ytd.index[0]}{moved(ytd.iloc[0])}，{ytd.index[-1]}{moved(ytd.iloc[-1])}'},
                   para('年初至今涨跌幅：' + '、'.join(f'{k} {pct(v)}' for k, v in ytd.items()) + '。')]
        three = week.horizons['3个月'].dropna().sort_values(ascending=False)
        if len(three):
            closing.append(para('近3个月：' + '、'.join(f'{k} {pct(v)}' for k, v in three.items()) + '。'))
    main_col = [
        [{'t': 'kicker', 'text': '本周要点'}, *points],
        [{'t': 'kicker', 'text': '本周走势'}, {'t': 'heading', 'text': trend_head}, pair],
        closing + [{'t': 'risk', **WARNING}]]

    figures = [{'value': pct(week.weekly[week.focus]), 'label': f'{week.focus} · 本周'}]
    if week.rates and '10Y' in week.tenors:
        figures.append({'value': f'{week.after["10Y"]:.2f}%', 'label': f'10年美债收益率 · 较上周 {bp(week.change["10Y"])}'})
    if week.focus in ytd:
        figures.append({'value': pct(ytd[week.focus]), 'label': f'{week.focus} · 年初至今'})
    scope = [{'head': '截点', 'text': f'周五（{md(week.as_of)}）。' + (
        '各序列取截点当日或之前 6 天内最近的观察值。' if week.days else '各序列取截点当日收盘。')}]
    proxies = week.proxies(week.names)
    if proxies:
        scope.append({'head': '代理', 'text': f'{"、".join(proxies)}为代理序列，见「{SOURCES_PAGE}」。'})
    if week.meta.get('omitted'):
        scope.append({'head': '本期未列入', 'text': '、'.join(week.meta['omitted']) + '。'})
    side = [{'title': '关键数字', 'blocks': [{'t': 'keyfigs', 'items': figures}]},
            {'title': '数据口径', 'items': scope},
            {'title': '本期内容', 'contents': True}]
    return {'titleLines': [lead, main], 'lede': lede, 'main': main_col, 'side': side}


# ── 市场仪表盘 ─────────────────────────────────────────────────────────────────
def dashboard(week):
    w = week.weekly
    order = week.names
    h = week.horizons
    leader, laggard = w.idxmax(), w.idxmin()
    columns = chart('asset-returns', '资产表现', '年初至今、近1个月与本周（%）', week.asset_source(), 'ColumnChart',
                    dict(width=W_FULL, height=190, decimals=1, categories=order, series=[
                        {'name': '年初至今', 'data': clean(h['年初至今'].reindex(order)), 'role': 'compare'},
                        {'name': '近1个月', 'data': clean(h['1个月'].reindex(order)), 'role': 'context'},
                        {'name': '本周', 'data': clean(w.reindex(order)), 'role': 'subject'}]), grow=True)
    bands = [band(f'本周{leader}{moved(w[leader])}，{laggard}{moved(w[laggard])}', 'full', [columns])]

    charts, finals = [], {}
    for i, group in enumerate(panels(week)):
        names = ordered(group['assets'], week.focus)
        idx = week.index[names]
        finals.update(idx.ffill().iloc[-1].to_dict())
        charts.append([chart(f'index-{i + 1}', group['title'], '一年前 = 100', week.asset_source(names), 'LineChart',
                             line_props(month_labels(idx.index), [{'name': n, 'data': clean(idx[n])} for n in names],
                                        W_HALF, 180, decimals=1, reference={'value': 100}), grow=True)])
    if charts:
        best = max(finals, key=finals.get)
        worst = min(finals, key=finals.get)
        title = f'近一年{best}{moved(finals[best] - 100)}，{worst}{moved(finals[worst] - 100)}'
        bands.append(band(title, 'halves', *charts))

    quoted = week.meta.get('quoted')
    rows = []
    for n in order:
        rows.append({'name': n, 'level': None if quoted is not None and n not in quoted else round(float(week.last[n]), 4),
                     **{k: None if not np.isfinite(h.loc[n, k]) else round(float(h.loc[n, k]), 4) for k in h.columns},
                     'dd': round(float(week.drawdown[n]), 4)})
    cols = [{'key': 'name', 'label': '资产'}, {'key': 'level', 'label': '最新', 'type': 'number', 'decimals': 2}]
    cols += [{'key': k, 'label': k, 'type': 'number', 'format': 'percent', 'decimals': 1, 'signed': True,
              'band': k == '年初至今'} for k in h.columns]
    cols.append({'key': 'dd', 'label': '距一年高点', 'type': 'number', 'format': 'percent', 'decimals': 1, 'signed': True})
    ytd = h['年初至今'].dropna()
    note = '“最新”只列有市场报价的资产；总回报指数的水平不具可比性，记为 –。' if quoted is not None and set(quoted) != set(order) else ''
    table = chart('asset-table', '资产回报', '各期涨跌幅（%）', week.asset_source() + note, 'DataTable',
                  dict(columns=cols, rows=rows, highlight=order.index(week.focus)))
    title = (f'年初至今{ytd.idxmax()}{moved(ytd.max())}，{int((ytd.round(1) > 0).sum())}/{len(ytd)} 个资产上涨'
             if len(ytd) else '各期涨跌幅')
    bands.append(band(title, 'full', [table]))
    return {'title': '市场仪表盘', 'section': '市场仪表盘', 'bands': bands, 'warning': WARNING}


# ── 风险与相关 ─────────────────────────────────────────────────────────────────
def risk(week):
    dd = week.drawdown.dropna().sort_values()
    worst = dd.index[0]
    near = [n for n, v in dd.items() if v > -1]
    p1 = (f'截至{md(week.as_of)}，{"、".join(near)}距近一年高点不足 1%。' if near
          else f'截至{md(week.as_of)}，没有资产处于近一年高点 1% 以内。')
    p2 = f'{worst}于{ymd(week.high_date[worst])}创近一年高点，此后回落 {abs(dd[worst]):.1f}%。'
    drawdown = band(f'{worst}距一年高点回撤 {abs(dd[worst]):.1f}%，回撤最深', 'narrative',
                    [para(p1), para(p2, '最深回撤。')],
                    [chart('drawdown', '距近一年高点', '%', week.asset_source(), 'BarChart',
                           dict(width=W_NARRATIVE, sort='asc', highlight=worst, decimals=1, signed=True, rowHeight=20,
                                data=[{'label': n, 'value': round(float(v), 4)} for n, v in dd.items()]))])

    vol = week.vol_now.dropna().sort_values(ascending=False)
    hi, lo = vol.index[0], vol.index[-1]
    shown = ordered([n for n in dict.fromkeys([hi, week.focus, lo])], hi)[:3]
    series = week.vol[shown]
    focus_range = week.vol[week.focus].dropna()
    texts = [para(f'21 日年化波动率：{hi} {vol[hi]:.1f}%，{lo} {vol[lo]:.1f}% 最低。')]
    if week.focus not in (hi, lo) and len(focus_range):
        texts.append(para(f'{week.focus}为 {vol[week.focus]:.1f}%，近一年区间 {focus_range.min():.1f}%–{focus_range.max():.1f}%。'))
    texts.append(para('波动率为 21 个交易日日收益的标准差乘以 √252，描述历史波动，不是预测。', '口径。'))
    volatility = band(f'{hi}波动率 {vol[hi]:.1f}%，为各资产最高', 'narrative', texts,
                      [chart('volatility', '21 日年化波动率', '%', week.asset_source(shown), 'LineChart',
                             line_props(month_labels(series.index), [{'name': n, 'data': clean(series[n])} for n in shown],
                                        W_NARRATIVE, 200, decimals=1, format='percent'), grow=True, grow_max=20)])

    a, b = week.pair
    corr = week.corr.dropna()
    bands = [drawdown, volatility]
    if len(corr):
        now = corr.iloc[-1]
        sign = '同向' if now > 0 else '反向'
        texts = [para(f'截至{md(corr.index[-1])}，{a}与{b}的 60 日相关系数为 {now:.2f}，近一年区间 {corr.min():.2f} 至 {corr.max():.2f}。'),
                 para(f'相关系数为{"正" if now > 0 else "负"}，表示近 60 个交易日两者大体{sign}波动；绝对值越接近 1，联动越紧。', '口径。')]
        bands.append(band(f'{a}与{b} 60 日相关系数为 {now:.2f}', 'narrative', texts,
                          [chart('correlation', '60 日滚动相关系数', f'{a}与{b}', week.asset_source([a, b]), 'LineChart',
                                 line_props(month_labels(corr.index), [{'name': f'{a}与{b}', 'data': clean(corr)}],
                                            W_NARRATIVE, 200, decimals=2, tickDecimals=1, reference={'value': 0},
                                            legend=False), grow=True, grow_max=20)]))
    return {'title': '风险与相关', 'section': '风险与相关', 'bands': bands, 'warning': WARNING}


# ── 固定收益 ───────────────────────────────────────────────────────────────────
def rates(week):
    t, ch = week.tenors, week.change
    big = ch.abs().idxmax()
    bands = []
    shape = ''
    if {'2Y', '10Y'} <= set(t):
        twist = (ch['10Y'] - ch['2Y'])
        shape = '陡峭化' if round(twist) > 0 else '平坦化' if round(twist) < 0 else '平移'
    head_t = '10Y' if '10Y' in t else big
    title = f'曲线{shape}，{head_t} {bp_moved(ch[head_t])}' if shape else f'{head_t} 收益率{bp_moved(ch[head_t])}'
    texts = [para('周变动：' + '、'.join(f'{x} {bp(ch[x])}' for x in t) + '。'),
             para(f'变动最大的是 {big}（{bp(ch[big])}），本周 {week.after[big]:.2f}%。')]
    if week.rate_date < week.as_of:
        texts.append(para(f'收益率最新观察为{md(week.rate_date)}，早于周五截点。', '日期。'))
    bands.append(band(title, 'narrative', texts,
                      [chart('yield-curve', '美债收益率曲线', '%', week.rate_source(), 'LineChart',
                             line_props(t, [{'name': f'本周（{md(week.rate_date)}）', 'data': clean(week.after[t])},
                                            {'name': f'上周（{md(week.rate_start)}）', 'data': clean(week.before[t])}],
                                        W_NARRATIVE, 200, decimals=2, format='percent', xTicks=min(len(t), 6)),
                             grow=True, grow_max=20)]))

    s = week.spread
    if s is not None and len(s):
        now = s.iloc[-1]
        prior = s.loc[:week.start]
        diff = now - prior.iloc[-1] if len(prior) else np.nan
        inverted = int((s < 0).sum())
        title = f'10Y−2Y 利差为 {bp(now, False)}' + (f'，较一周前{bp_moved(diff, "走阔", "收窄")}' if np.isfinite(diff) else '')
        inversion = f'其中 {inverted} 个交易日倒挂（利差小于 0）' if inverted else '期间没有倒挂'
        texts = [para(f'近一年区间 {bp(s.min(), False)} 至 {bp(s.max(), False)}，{inversion}。'),
                 para('利差为 10 年减 2 年收益率；1bp 等于 0.01 个百分点。', '口径。')]
        bands.append(band(title, 'narrative', texts,
                          [chart('yield-spread', '10Y−2Y 利差', 'bp', week.rate_source(), 'LineChart',
                                 line_props(month_labels(s.index), [{'name': '10Y−2Y', 'data': clean(s)}], W_NARRATIVE, 200,
                                            decimals=0, format='bp', legend=False,
                                            reference={'value': 0, 'label': '倒挂线'} if s.min() < 15 else None),
                                 grow=True, grow_max=20)]))

    rows = [{'tenor': x, 'before': round(float(week.before[x]), 4), 'after': round(float(week.after[x]), 4),
             'change': round(float(ch[x]), 4)} for x in t]
    up = int((ch.round() > 0).sum())
    short = [x for x in t if x in ('3M', '1M', '6M', '1Y', '2Y')]
    long = [x for x in t if x in ('10Y', '20Y', '30Y')]
    texts = [para(f'{len(t)} 个期限中 {up} 个上行，{int((ch.round() < 0).sum())} 个下行。')]
    if short and long:
        texts.append(para(f'短端（{"、".join(short)}）平均 {bp(ch[short].mean())}，长端（{"、".join(long)}）平均 {bp(ch[long].mean())}。'))
    bands.append(band(f'{len(t)} 个期限中 {up} 个上行，{big} 变动最大', 'narrative', texts,
                      [chart('rate-table', '美债收益率', f'{md(week.rate_start)}与{md(week.rate_date)}（%）', week.rate_source(),
                             'DataTable', dict(columns=[
                                 {'key': 'tenor', 'label': '期限'},
                                 {'key': 'before', 'label': '上周', 'type': 'number', 'decimals': 2},
                                 {'key': 'after', 'label': '本周', 'type': 'number', 'decimals': 2},
                                 {'key': 'change', 'label': '变动（bp）', 'type': 'delta', 'format': 'bp', 'mode': 'market'}],
                                 rows=rows, highlight=t.index(big)))]))
    return {'title': '固定收益', 'section': '固定收益', 'bands': bands, 'warning': WARNING}


# ── 来源与方法 ─────────────────────────────────────────────────────────────────
def sources(week):
    meta = week.meta
    lag = obs_dates(week.levels, week.as_of, max(week.days, ASOF_WINDOW))
    origin = meta.get('series_sources') or {}
    items = []
    for n in week.names:
        bits = [origin.get(n) or meta['source'], week.notes.get(n, '').split('，截至')[0]]
        text = '；'.join(b for b in bits if b) + f'；最新观察 {md(lag[n])}。'
        items.append({'head': f'{n}：', 'text': text})
    if week.rates:
        items.append({'head': '美债收益率：', 'text': f"{meta.get('rates_source') or meta['source']}；"
                                                   f'{"、".join(week.tenors)}；最新观察 {md(week.rate_date)}。'})
    items.append({'head': '日期规则：', 'text': ('周五截点；各序列取截点当日或之前 6 天内最近的观察值，节假日沿用前一交易日收盘，'
                                              '序列末端不外推。' if week.days else '周五截点；取截点当日收盘。')
                  + '跨周期基准取基准日当日或之前最近的收盘。缺失保持空白，不插值。'})
    items.append({'head': '缺口：', 'text': ('、'.join(meta['omitted']) + '。') if meta.get('omitted') else '本期没有未列入的序列。'})
    intro = (f'本期覆盖 {ymd(week.start + pd.Timedelta(days=1))}至{ymd(week.as_of)}（周五截点），'
             f'数据更新于 {meta["updated_at"]}。本刊只陈述数据，不含观点或预测。')
    if meta.get('is_demo'):
        intro += '本期为模拟数据，非真实行情。'
    paras = [
        {'lead': '重要信息。', 'text': '本刊仅供读者名单内部学习交流，不构成投资建议、要约或推荐。数据来自公开或授权来源，'
                                  '我们认为可靠，但不保证准确与完整。MSCI 等授权数据仅限读者名单内部使用，请勿转发至名单之外。'},
        {'lead': '发布方：', 'text': f'{SERIES}（Capital Weekly 数据库）。发布时间：{meta["updated_at"]}。'
                                f'信息来源：见上列各项。'},
        {'lead': '风险提示：', 'text': '过往业绩并不预示未来表现。市场有风险，投资需谨慎。代理序列（ETF 总回报、期货近月合约）'
                                  '与其代表的指数之间存在跟踪误差；收益率与价格可能有修订。'}]
    return {'title': SOURCES_PAGE, 'section': SOURCES_PAGE, 'warning': None, 'fill': False,
            'bands': [{'t': 'disclosures', 'intro': intro, 'sources': items, 'paras': paras}]}


def issue_spec(levels, yields, meta):
    """The whole issue as JSON-ready data for ds/issue.js."""
    week = Week(levels, yields, meta)
    market = 'cn' if meta.get('market_colors') == 'cn' else None
    date = ymd(week.as_of) + (' · 模拟数据' if meta.get('is_demo') else '')
    sections = [dashboard(week), risk(week)]
    if week.rates:
        sections.append(rates(week))
    sections.append(sources(week))
    return {'lang': 'zh', 'market': market, 'series': SERIES, 'date': date,
            'cover': cover(week), 'sections': sections}
