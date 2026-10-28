"""Street-style charts in the Richard Wei Finance style; values come from validated inputs."""
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.colors import TwoSlopeNorm, Normalize
from matplotlib.ticker import MaxNLocator, FuncFormatter

from .charts import (chart, standalone, plot_axes, fit_left, legend_top, axes_at, clean_axes, hgrid, vgrid,
                    baseline, line_panel, end_dot, draw_matrix, matrix_axes, highlights, series_color,
                    market, diverging, level, change, plain, font, text_width, cn_date, date_axis, wrap,
                    move_word, ACCENT, AC, PY, RANGE_1, RANGE_2, INK, INK_MUTED, SURFACE, GOOD, BAD, GREYS)

LABELS = {
    'drawdown': '从前高回撤', 'volatility': '滚动波动率', 'rolling_correlation': '滚动相关性',
    'correlation': '跨资产相关性', 'risk_return': '收益与风险', 'distribution': '日收益分布',
    'candlestick': 'K 线与成交量', 'relative': '相对基准表现', 'calendar': '月度收益日历',
    'flows': '分类别资金流', 'valuation': '估值历史与参考区间', 'football': '估值区间比较',
    'waterfall': '财务变动桥接', 'sensitivity': '情景敏感性矩阵'}
TITLES = {key: (i + 7, label) for i, (key, label) in enumerate(LABELS.items())}
SHADES = [AC, PY, RANGE_1, RANGE_2]   # part-to-whole categories, dark to light, white gaps between

wrapped = wrap  # backwards-compatible name


def pct(v, _=None):
    return plain(v, 'g') + '%'


def num(value):
    """Amounts as given: integers stay integers, otherwise one decimal; thousands separators."""
    return level(value, 0 if float(value).is_integer() else 1)


def num_change(value):
    return change(value, 0 if float(value).is_integer() else 1, '')


def story(key, **parts):
    parts['label'] = LABELS[key]
    return parts


# ── Drawdown ──────────────────────────────────────────────────────────────────
@chart('drawdown')
def story_drawdown(data, meta):
    last = data.ffill().iloc[-1]
    deep, shallow = last.idxmin(), last.idxmax()
    near = int((last > -1).sum())
    return story('drawdown', message=f'{deep}距前高 {change(last[deep])}，回撤最深',
                 unit=f'距样本内历史最高值（%），{cn_date(data.index[0])} 起',
                 take_head=f'{deep}回撤最深',
                 take_text=f'{near}/{len(last)} 个资产处于前高 1% 以内；{shallow}距前高 {change(last[shallow])}。',
                 note='只计入样本内前高，不代表完整持有期最大回撤。',
                 evidence=[(n, change(v)) for n, v in last.sort_values().items()], evidence_head='距前高')


@chart('drawdown')
def plot_drawdown(fig, rect, data, meta, reg, s):
    chosen = highlights(meta, data.columns)
    floor = np.nanmin(data.to_numpy())
    ax = line_panel(fig, rect, reg, data, chosen, lambda v: change(v),
                    (min(floor * 1.1, -1), max(-floor * .04, .3)), yfmt=pct, base=0)


# ── Volatility ────────────────────────────────────────────────────────────────
@chart('volatility')
def story_volatility(data, meta):
    annual = meta.get('annualization', 252)
    last = data.ffill().iloc[-1]
    top, low = last.idxmax(), last.idxmin()
    return story('volatility', message=f'{top}波动率最高，为 {last[top]:.1f}%',
                 unit=f'21 个收益观察值的年化波动率（%），样本标准差 × √{annual:g}',
                 take_head=f'{top}波动最大', take_text=f'{low}最低，为 {last[low]:.1f}%；两者相差 {last[top] - last[low]:.1f} 个百分点。',
                 evidence=[(n, f'{v:.1f}%') for n, v in last.sort_values(ascending=False).items()], evidence_head='最新年化波动率')


@chart('volatility')
def plot_volatility(fig, rect, data, meta, reg, s):
    chosen = highlights(meta, data.columns)
    line_panel(fig, rect, reg, data, chosen, lambda v: f'{v:.1f}%', (0, np.nanmax(data.to_numpy()) * 1.12),
               yfmt=pct, base=0)


# ── Rolling correlation ───────────────────────────────────────────────────────
@chart('rolling_correlation')
def story_rolling(data, meta):
    pair = meta.get('correlation_pair', ['前两列资产', ''])
    valid = data.dropna()
    last = valid.iloc[-1]
    return story('rolling_correlation', message=f'{pair[0]}与{pair[1]}的相关系数为 {plain(last, ".2f")}',
                 unit='60 个日收益观察值的 Pearson 相关系数',
                 take_head='相关性为正' if last > 0 else '相关性为负',
                 take_text=f'样本内区间 {plain(valid.min(), ".2f")} 至 {plain(valid.max(), ".2f")}；最新值截至{cn_date(valid.index[-1], True)}。',
                 evidence=[('最新', plain(last, '.2f')), ('样本最低', plain(valid.min(), '.2f')),
                           ('样本最高', plain(valid.max(), '.2f')), ('样本均值', plain(valid.mean(), '.2f'))],
                 evidence_head='相关系数')


@chart('rolling_correlation')
def plot_rolling(fig, rect, data, meta, reg, s):
    valid = data.dropna()
    last = valid.iloc[-1]
    right = text_width(fig, plain(last, '.2f'), 'semibold', reg.table) + 3
    ax = plot_axes(fig, rect, reg, right=right)
    hgrid(ax)
    ax.set_ylim(-1.05, 1.05)
    ax.set_yticks([-1, 0, 1] if rect[3] < 35 else [-1, -.5, 0, .5, 1])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: plain(v, 'g')))
    fit_left(fig, ax, rect, reg, right=right)
    date_axis(ax, data.index)
    baseline(ax, 0)
    ax.plot(data.index, data, color=AC, lw=1.2, zorder=4)
    end_dot(ax, valid.index[-1], last, ACCENT)
    ax.annotate(plain(last, '.2f'), (valid.index[-1], last), xytext=(5, 0), textcoords='offset points',
                va='center', fontsize=reg.table, color=INK, fontproperties=font('semibold'), annotation_clip=False)


# ── Correlation matrix ────────────────────────────────────────────────────────
def _lower(data):
    names = list(data.index)
    values, rows, cols = data.to_numpy()[1:, :-1], names[1:], names[:-1]
    blank = np.array([[c > r for c in range(len(cols))] for r in range(len(rows))])
    masked = np.where(blank, np.nan, values)
    return values, rows, cols, blank, masked


@chart('correlation')
def story_correlation(data, meta):
    if len(data) < 2:
        return story('correlation', message='只有一个资产，无法比较相关性', unit='日收益 Pearson 相关系数',
                     take_head='资产不足', take_text='至少需要两个资产。', evidence=[], evidence_head='')
    values, rows, cols, blank, masked = _lower(data)
    r, c = np.unravel_index(np.nanargmax(np.abs(masked)), masked.shape)
    pairs = np.abs(masked[np.isfinite(masked)])
    low = int((pairs < .1).sum())
    ranked = sorted(((abs(masked[i, j]), rows[i], cols[j], masked[i, j]) for i in range(len(rows))
                     for j in range(len(cols)) if np.isfinite(masked[i, j])), reverse=True)
    return story('correlation', message=f'{rows[r]}与{cols[c]}相关性最强（{plain(values[r, c], ".2f")}）',
                 unit='日收益 Pearson 相关系数，所有资产共同有效样本',
                 take_head='相关性普遍偏低' if np.nanmax(pairs) < .3 else f'{rows[r]}与{cols[c]}联动',
                 take_text=f'{len(pairs)} 对资产中 {low} 对的相关系数绝对值低于 0.10。',
                 note='只显示下三角；灰度越深相关性越强，蓝色为绝对值最大的一对。',
                 evidence=[(f'{a} / {b}', plain(v, '.2f')) for _, a, b, v in ranked[:6]], evidence_head='相关系数，按绝对值')


@chart('correlation')
def plot_correlation(fig, rect, data, meta, reg, s):
    if len(data) < 2:
        values, rows, cols, blank, strongest = data.to_numpy(), list(data.index), list(data.index), None, None
    else:
        values, rows, cols, blank, masked = _lower(data)
        r, c = np.unravel_index(np.nanargmax(np.abs(masked)), masked.shape)
        strongest = (int(r), int(c))
    ax = matrix_axes(fig, rect, reg, rows, cols, rows_max_h=len(rows) * 8)
    draw_matrix(ax, values, rows, cols, lambda v: GREYS(min(abs(v), 1) * .85), lambda v: plain(v, '.2f'), reg,
                blank=blank, emphasis=strongest)


# ── Risk / return ─────────────────────────────────────────────────────────────
@chart('risk_return')
def story_risk_return(data, meta):
    annual = meta.get('annualization', 252)
    best, calm = data['return'].idxmax(), data.risk.idxmin()
    return story('risk_return', message=f'{best}年化收益最高，为 {data.loc[best, "return"]:.1f}%',
                 unit=f'日收益均值 × {annual:g} 与标准差 × √{annual:g}（%），历史样本',
                 take_head=f'{best}收益最高',
                 take_text=f'{best}波动率 {data.loc[best, "risk"]:.1f}%；{calm}波动率最低（{data.loc[calm, "risk"]:.1f}%）。',
                 note='均值年化不等于 CAGR，不代表预期收益。',
                 evidence=[(n, f"{r['return']:.1f}% / {r.risk:.1f}%") for n, r in data.sort_values('return', ascending=False).iterrows()],
                 evidence_head='年化收益 / 波动率')


@chart('risk_return')
def plot_risk_return(fig, rect, data, meta, reg, s):
    chosen = highlights(meta, data.index)
    x, y, w, h = rect
    title_h = reg.label * 25.4 / 72 * 1.5 + 1
    bottom = reg.axis_bottom + reg.label * 25.4 / 72 * 1.5 + 1
    ax = plot_axes(fig, rect, reg, top=title_h, bottom=bottom, right=2)
    hgrid(ax)
    ax.margins(.18)
    ax.scatter(data.risk, data['return'], s=0)
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_formatter(FuncFormatter(pct))
    ax.xaxis.set_major_locator(MaxNLocator(4 if w < 70 else 6))
    ax.xaxis.set_major_formatter(FuncFormatter(pct))
    left = fit_left(fig, ax, rect, reg, top=title_h, bottom=bottom, right=2)
    baseline(ax, 0)
    midpoint = (data.risk.min() + data.risk.max()) / 2
    for i, name in enumerate(sorted(data.index, key=lambda n: n in chosen)):
        row = data.loc[name]
        strong = name in chosen
        ax.scatter(row.risk, row['return'], s=40 if strong else 24, color=series_color(name, chosen),
                   edgecolors=SURFACE, lw=1, zorder=5 if strong else 4)
        right = row.risk > midpoint
        ax.annotate(name, (row.risk, row['return']), xytext=(-6 if right else 6, 5 if i % 2 == 0 else -9),
                    textcoords='offset points', ha='right' if right else 'left', fontsize=reg.body,
                    color=INK if strong else INK_MUTED, fontproperties=font('semibold' if strong else 'sans'))
    from .charts import text
    text(fig, x + left, y, '年化算术平均收益', reg.label, INK_MUTED, 'semibold')
    ax.set_xlabel('年化波动率', fontsize=reg.label, labelpad=3, color=INK_MUTED, fontproperties=font('semibold', reg.label))


# ── Distribution ──────────────────────────────────────────────────────────────
@chart('distribution')
def story_distribution(data, meta):
    focus = meta.get('focus_asset', '首列资产')
    latest = data.iloc[-1]
    ups = (data > 0).mean() * 100
    side = '高于' if latest > data.mean() else '低于'
    return story('distribution', message=f'{focus}日收益均值 {change(data.mean())}，标准差 {data.std():.1f}%',
                 unit=f'单日价格变化（%）的频数分布，{len(data)} 个观察值',
                 take_head=f'最新一日{side}均值',
                 take_text=f'{cn_date(data.index[-1], True)}单日 {change(latest)}；样本内 {ups:.0f}% 的交易日收涨。',
                 note='频数分布描述历史样本，不是概率预测。',
                 evidence=[('均值', change(data.mean())), ('标准差', f'{data.std():.1f}%'), ('最新', change(latest)),
                           ('最低', change(data.min())), ('最高', change(data.max())), ('观察值', f'{len(data)}')],
                 evidence_head='单日涨跌幅')


@chart('distribution')
def plot_distribution(fig, rect, data, meta, reg, s):
    latest = data.iloc[-1]
    handles = [Line2D([], [], color=AC, lw=1, label=f'均值 {change(data.mean())}'),
               Line2D([], [], color=ACCENT, lw=1.5, label=f'最新 {change(latest)}')]
    top = legend_top(fig, rect, handles, reg)
    ax = plot_axes(fig, rect, reg, top=top, right=2)
    hgrid(ax)
    bins = min(28, max(8, int(np.sqrt(len(data)) * 1.6)))
    counts, edges, _ = ax.hist(data, bins=bins, color=RANGE_1, edgecolor=SURFACE, lw=.8, zorder=2)
    ax.set_ylim(0, counts.max() * 1.12)
    ax.yaxis.set_major_locator(MaxNLocator(3, integer=True))
    ax.xaxis.set_major_locator(MaxNLocator(4 if rect[2] < 70 else 6))
    ax.xaxis.set_major_formatter(FuncFormatter(pct))
    fit_left(fig, ax, rect, reg, top=top, right=2)
    baseline(ax, 0)
    ax.axvline(data.mean(), color=AC, lw=1, zorder=4)
    ax.axvline(latest, color=ACCENT, lw=1.5, zorder=5)


# ── Candlestick ───────────────────────────────────────────────────────────────
@chart('candlestick')
def story_candlestick(data, meta):
    unit = meta.get('chart_units', {}).get('candlestick', '')
    data = data.tail(60)
    first, last = data.close.iloc[0], data.close.iloc[-1]
    move = (last / first - 1) * 100
    off = (last / data.high.max() - 1) * 100
    ups = int((data.close >= data.open).sum())
    return story('candlestick', message=f'收于 {level(last)}，近 {len(data)} 个交易日{move_word(move)} {abs(move):.1f}%',
                 unit=f'{unit}，最近 {len(data)} 个交易观察日',
                 take_head=f'距区间高点 {change(off)}',
                 take_text=f'区间最高 {level(data.high.max())}、最低 {level(data.low.min())}；{len(data)} 个交易日中 {ups} 个收涨。',
                 evidence=[('最新收盘', level(last)), (f'{len(data)} 日变化', change(move)), ('区间最高', level(data.high.max())),
                           ('区间最低', level(data.low.min())), ('收涨天数', f'{ups}')], evidence_head='价格')


@chart('candlestick')
def plot_candlestick(fig, rect, data, meta, reg, s):
    data = data.tail(60)
    up, down, *_ = market(meta)
    handles = [Patch(facecolor=up, label='收涨'), Patch(facecolor=down, label='收跌')]
    top = legend_top(fig, rect, handles, reg)
    x, y, w, h = rect
    last = data.close.iloc[-1]
    right = text_width(fig, level(last), 'semibold', reg.table) + 3
    body_h = h - top - reg.axis_bottom
    price_h, vol_h, gap = body_h * .66, body_h * .26, body_h * .08
    ax = plot_axes(fig, (x, y, w, top + price_h), reg, top=top, bottom=0, right=right)
    hgrid(ax)
    ax.set_xlim(-1, len(data))
    ax.set_ylim(data.low.min() * .99, data.high.max() * 1.01)
    ax.yaxis.set_major_locator(MaxNLocator(3))
    left = fit_left(fig, ax, (x, y, w, top + price_h), reg, right=right, top=top, bottom=0)
    volume = axes_at(fig, x + left, y + top + price_h + gap, w - left - right, vol_h)
    clean_axes(volume, reg)
    pos = np.arange(len(data))
    colors = [up if row.close >= row.open else down for row in data.itertuples()]
    ax.vlines(pos, data.low, data.high, color=colors, lw=.6, zorder=2)
    for i, row in enumerate(data.itertuples()):
        if row.close == row.open:
            ax.hlines(row.close, i - .32, i + .32, color=colors[i], lw=.8, zorder=3)
        else:
            ax.add_patch(Rectangle((i - .32, min(row.open, row.close)), .64, abs(row.close - row.open),
                                   facecolor=colors[i], edgecolor='none', zorder=3))
    ax.set_xticks([])
    ax.annotate(level(last), (len(data) - 1, last), xytext=(7, 0), textcoords='offset points', va='center',
                fontsize=reg.table, color=INK, fontproperties=font('semibold'), annotation_clip=False)
    volume.bar(pos, data.volume / 1e6, color=RANGE_1, width=.64)
    baseline(volume, 0)
    volume.set_xlim(ax.get_xlim())
    ticks = np.unique(np.linspace(0, len(data) - 1, 3 if w < 80 else 4).astype(int))
    volume.set_xticks(ticks, [cn_date(data.index[i], True) for i in ticks])
    volume.set_yticks([])
    volume.text(0, 1, '成交量', transform=volume.transAxes, va='bottom', fontsize=reg.label, color=INK_MUTED,
                fontproperties=font('semibold'))


# ── Relative performance ──────────────────────────────────────────────────────
@chart('relative')
def story_relative(data, meta):
    benchmark = meta.get('benchmark', data.columns[0])
    others = [n for n in data.columns if n != benchmark]
    last = data[others].ffill().iloc[-1]
    top, bottom = last.idxmax(), last.idxmin()
    ahead = int((last > 100).sum())
    message = (f'{top}跑赢{benchmark} {last[top] - 100:.1f}%' if last[top] > 100
               else f'所有资产均跑输{benchmark}，{top}差距最小')
    return story('relative', message=message, unit=f'各资产 ÷ {benchmark}，共同起点 {cn_date(data.index[0])} = 100',
                 take_head=f'{ahead}/{len(last)} 个资产跑赢',
                 take_text=f'{bottom}相对{benchmark}最低，为 {level(last[bottom])}。',
                 note='高于 100 表示自共同起点以来跑赢基准；此图不是 RSI。',
                 evidence=[(n, level(v)) for n, v in last.sort_values(ascending=False).items()], evidence_head=f'相对{benchmark}（起点 = 100）')


@chart('relative')
def plot_relative(fig, rect, data, meta, reg, s):
    benchmark = meta.get('benchmark', data.columns[0])
    chosen = highlights(meta, data.columns)
    others = [n for n in data.columns if n != benchmark]
    emphasis = chosen if any(n in others for n in chosen) else others[:1]
    lo, hi = np.nanmin(data[others].to_numpy()), np.nanmax(data[others].to_numpy())
    span = max(hi - lo, 4)
    extra = [(100, data.index[-1], f'基准 {benchmark}', '100', INK, True)]
    line_panel(fig, rect, reg, data[others], emphasis, lambda v: level(v),
               (min(lo, 100) - .06 * span, max(hi, 100) + .06 * span), base=100, extra=extra)


# ── Monthly calendar ──────────────────────────────────────────────────────────
def _calendar(data):
    values = data.to_numpy()
    flat = values.ravel()
    finite = np.flatnonzero(np.isfinite(flat))
    blank = np.zeros_like(values, dtype=bool)
    if len(finite):
        outside = np.ones(flat.shape, dtype=bool)
        outside[finite[0]:finite[-1] + 1] = False
        blank = outside.reshape(values.shape)
    return values, flat, finite, blank


@chart('calendar')
def story_calendar(data, meta):
    focus = meta.get('focus_asset', '首列资产')
    values, flat, finite, blank = _calendar(data)
    if len(finite):
        best, worst = finite[np.argmax(flat[finite])], finite[np.argmin(flat[finite])]
        name = lambda i: f'{data.index[i // 12]}年{data.columns[i % 12]}月'
        message = f'{name(best)}涨幅最大（{change(flat[best])}）'
        pos = int((flat[finite] > 0).sum())
        text_value = f'样本内 {pos}/{len(finite)} 个月上涨；最弱为{name(worst)}（{change(flat[worst])}）。'
        evidence = [(name(i), change(flat[i])) for i in finite[-6:][::-1]]
    else:
        message, text_value, evidence = '样本内没有完整的月度收益', '至少需要两个相邻月份的价格。', []
    return story('calendar', message=message, unit=f'{focus}月末价格变化（%），最多展示最近 8 年',
                 take_head='月度表现分化' if len(finite) else '数据不足', take_text=text_value,
                 note='当月为截至观察日的月内收益；空白为样本外月份，– 为样本内缺失。',
                 evidence=evidence, evidence_head='最近六个月')


@chart('calendar')
def plot_calendar(fig, rect, data, meta, reg, s):
    values, flat, finite, blank = _calendar(data)
    extent = max(np.nanmax(np.abs(values)), .1)
    norm = TwoSlopeNorm(vmin=-extent, vcenter=0, vmax=extent)
    cmap = diverging(meta)
    labels = [f'{m}月' for m in data.columns]
    ax = matrix_axes(fig, rect, reg, data.index, labels, rows_max_h=len(data) * 8)
    draw_matrix(ax, values, data.index, labels, lambda v: cmap(norm(v)), lambda v: change(v, 1, ''), reg, blank=blank)


# ── Flows ─────────────────────────────────────────────────────────────────────
@chart('flows')
def story_flows(data, meta):
    unit = meta.get('chart_units', {}).get('flows', '')
    net = data.sum(axis=1)
    last = net.iloc[-1]
    lead = data.iloc[-1].abs().idxmax()
    inflow = int((net > 0).sum())
    return story('flows', message=f"{cn_date(data.index[-1], True)}当周净{'流入' if last >= 0 else '流出'} {num(abs(last))}（{unit}）",
                 unit=f'{unit}，正负资金流分别堆叠，蓝点为净额',
                 take_head=f"本期净{'流入' if last >= 0 else '流出'}",
                 take_text=f'{lead}变动最大（{num_change(data.iloc[-1][lead])}）；{len(net)} 期中 {inflow} 期净流入。',
                 evidence=[(c, num_change(v)) for c, v in data.iloc[-1].items()] + [('净额', num_change(last))],
                 evidence_head=f'{cn_date(data.index[-1], True)}当周')


@chart('flows')
def plot_flows(fig, rect, data, meta, reg, s):
    handles = [Patch(facecolor=SHADES[i], label=name) for i, name in enumerate(data)]
    handles.append(Line2D([], [], ls='none', marker='o', color=ACCENT, mec=SURFACE, ms=5, label='净额'))
    top = legend_top(fig, rect, handles, reg)
    ax = plot_axes(fig, rect, reg, top=top, right=2)
    hgrid(ax)
    positions = np.arange(len(data))
    pos, neg = np.zeros(len(data)), np.zeros(len(data))
    for i, name in enumerate(data):
        values = data[name].to_numpy()
        bottom = np.where(values >= 0, pos, neg)
        ax.bar(positions, values, bottom=bottom, color=SHADES[i], width=.62, edgecolor=SURFACE, linewidth=.8, zorder=2)
        pos += np.maximum(values, 0)
        neg += np.minimum(values, 0)
    ax.scatter(positions, data.sum(axis=1), s=16, color=ACCENT, edgecolors=SURFACE, lw=1, zorder=5)
    ax.set_xlim(-.6, len(data) - .4)
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: plain(v, 'g')))
    fit_left(fig, ax, rect, reg, top=top, right=2)
    baseline(ax, 0)
    ticks = np.unique(np.linspace(0, len(data) - 1, min(4 if rect[2] < 90 else 5, len(data))).astype(int))
    ax.set_xticks(ticks, [cn_date(data.index[i], True) for i in ticks])


# ── Valuation history ─────────────────────────────────────────────────────────
@chart('valuation')
def story_valuation(data, meta):
    unit = meta.get('chart_units', {}).get('valuation', '')
    last = data.actual.iloc[-1]
    lo, hi = data.lower.iloc[-1], data.upper.iloc[-1]
    where = '高于参考区间上沿' if last > hi else '低于参考区间下沿' if last < lo else '位于参考区间内'
    above = (data.actual > data.upper).mean() * 100
    return story('valuation', message=f'最新 {level(last)}，{where}', unit=f'{unit}，灰色带为外部输入的参考区间',
                 take_head=where[:4] if len(where) > 4 else where,
                 take_text=f'参考区间 {level(lo)}–{level(hi)}；样本内 {above:.0f}% 的观察日高于上沿。',
                 evidence=[('最新', level(last)), ('区间下沿', level(lo)), ('区间上沿', level(hi)),
                           ('样本最低', level(data.actual.min())), ('样本最高', level(data.actual.max()))],
                 evidence_head=unit)


@chart('valuation')
def plot_valuation(fig, rect, data, meta, reg, s):
    last = data.actual.iloc[-1]
    handles = [Patch(facecolor=RANGE_2, lw=0, label='参考区间（输入）'), Line2D([], [], color=AC, lw=1.2, label='观察值')]
    top = legend_top(fig, rect, handles, reg)
    right = text_width(fig, level(last), 'semibold', reg.table) + 3
    ax = plot_axes(fig, rect, reg, top=top, right=right)
    hgrid(ax)
    lo, hi = min(data.lower.min(), data.actual.min()), max(data.upper.max(), data.actual.max())
    pad = (hi - lo) * .06
    ax.set_ylim(lo - pad, hi + pad)
    ax.yaxis.set_major_locator(MaxNLocator(4))
    fit_left(fig, ax, rect, reg, top=top, right=right)
    date_axis(ax, data.index)
    ax.fill_between(data.index, data.lower, data.upper, color=RANGE_2, lw=0, zorder=2)
    ax.plot(data.index, data.actual, color=AC, lw=1.2, zorder=4)
    end_dot(ax, data.index[-1], last, ACCENT)
    ax.annotate(level(last), (data.index[-1], last), xytext=(5, 0), textcoords='offset points', va='center',
                fontsize=reg.table, color=INK, fontproperties=font('semibold'), annotation_clip=False)


# ── Football field ────────────────────────────────────────────────────────────
@chart('football')
def story_football(data, meta):
    unit = meta.get('chart_units', {}).get('football', '')
    overlap_lo, overlap_hi = data.low.max(), data.high.min()
    widest = (data.high - data.low).idxmax()
    text_value = (f'各方法共同覆盖 {level(overlap_lo)}–{level(overlap_hi)}；' if overlap_lo <= overlap_hi
                  else '各方法区间没有共同重叠部分；') + f"{data.loc[widest, 'label']}区间最宽。"
    return story('football', message=f'各方法估值区间为 {level(data.low.min())}–{level(data.high.max())}',
                 unit=f'{unit}，各方法使用同一估值口径',
                 take_head='区间有重叠' if overlap_lo <= overlap_hi else '区间不重叠', take_text=text_value,
                 evidence=[(r.label, f'{level(r.low)}–{level(r.high)}') for r in data.itertuples()], evidence_head=unit)


@chart('football')
def plot_football(fig, rect, data, meta, reg, s):
    left = max(text_width(fig, str(v), 'sans', reg.body) for v in data.label) + 3.5
    pad_l = max(text_width(fig, level(v), 'sans', reg.body) for v in data.low) + 2.5
    pad_r = max(text_width(fig, level(v), 'sans', reg.body) for v in data.high) + 2.5
    ax = plot_axes(fig, rect, reg, left=left, right=0)
    vgrid(ax)
    width_mm = rect[2] - left
    lo, hi = data.low.min(), data.high.max()
    per_mm = (hi - lo) / max(width_mm - pad_l - pad_r, 10)
    ax.set_xlim(lo - pad_l * per_mm, hi + pad_r * per_mm)
    ax.set_ylim(len(data) - .5, -.5)
    ax.barh(range(len(data)), data.high - data.low, left=data.low, height=.5, color=RANGE_1, zorder=2)
    for row, (low, high) in enumerate(zip(data.low, data.high)):
        ax.annotate(level(low), (low, row), xytext=(-4, 0), textcoords='offset points', ha='right', va='center',
                    fontsize=reg.body, color=INK)
        ax.annotate(level(high), (high, row), xytext=(4, 0), textcoords='offset points', ha='left', va='center',
                    fontsize=reg.body, color=INK)
    ax.set_yticks(range(len(data)), list(data.label))
    ax.tick_params(axis='y', labelcolor=INK, labelsize=reg.body, pad=6)
    ax.xaxis.set_major_locator(MaxNLocator(4 if width_mm < 60 else 6))


# ── Waterfall ─────────────────────────────────────────────────────────────────
@chart('waterfall')
def story_waterfall(data, meta):
    unit = meta.get('chart_units', {}).get('waterfall', '')
    changes = data[data.kind == 'change']
    driver = changes.value.abs().idxmax()
    end = data.iloc[-1]
    good, bad = changes.value[changes.value > 0].sum(), changes.value[changes.value < 0].sum()
    return story('waterfall',
                 message=f"{end['label']} {num(end['value'])}，{data.loc[driver, 'label']}影响最大（{num_change(data.loc[driver, 'value'])}）",
                 unit=f'{unit}，期初 + 各项变动 = 期末；青色有利、橙红不利',
                 take_head=f"{data.loc[driver, 'label']}贡献最大",
                 take_text=f'有利项合计 {num_change(good)}，不利项合计 {num_change(bad)}，净变动 {num_change(good + bad)}。',
                 evidence=[(r.label, num(r.value) if r.kind == 'total' else num_change(r.value)) for r in data.itertuples()],
                 evidence_head=unit)


@chart('waterfall')
def plot_waterfall(fig, rect, data, meta, reg, s):
    x, y, w, h = rect
    labels = [wrap(v, 4) for v in data.label]
    lines = max(len(v.split('\n')) for v in labels)
    bottom = reg.axis_bottom + (lines - 1) * reg.tick * 25.4 / 72 * 1.25
    ax = plot_axes(fig, rect, reg, bottom=bottom, top=3, right=1)
    hgrid(ax)
    running, levels = 0, [0]
    for row in data.itertuples():
        new = row.value if row.kind == 'total' else running + row.value
        levels.extend([running, new])
        running = new
    low, high = min(levels), max(levels)
    pad = max(high - low, 1) * .08
    ax.set_ylim(low - pad if low < 0 else 0, high + pad)
    ax.set_xlim(-.6, len(data) - .4)
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: plain(v, ',.0f')))
    fit_left(fig, ax, rect, reg, bottom=bottom, top=3, right=1)
    running = 0
    for i, row in enumerate(data.itertuples()):
        if row.kind == 'total':
            start, stop, color, label = 0, row.value, AC, num(row.value)
        else:
            start, stop = running, running + row.value
            color, label = (GOOD if row.value >= 0 else BAD), num_change(row.value)
        ax.add_patch(Rectangle((i - .3, min(start, stop)), .6, abs(stop - start), facecolor=color,
                               edgecolor='none', zorder=2))
        ax.annotate(label, (i, max(start, stop)), xytext=(0, 3), textcoords='offset points', ha='center',
                    fontsize=reg.body, color=INK, fontproperties=font('semibold' if row.kind == 'total' else 'sans'))
        if i < len(data) - 1:
            ax.hlines(stop, i + .3, i + .7, color=PY, lw=.75, zorder=1)
        running = stop
    baseline(ax, 0)
    ax.set_xticks(range(len(data)), labels)
    ax.tick_params(axis='x', labelsize=reg.tick, labelcolor=INK)


# ── Sensitivity ───────────────────────────────────────────────────────────────
@chart('sensitivity')
def story_sensitivity(data, meta):
    unit = meta.get('chart_units', {}).get('sensitivity', '')
    digits = meta.get('sensitivity_decimals', 2)
    numeric = data.drop(columns='scenario')
    values = numeric.to_numpy(dtype=float)
    hi_r, hi_c = np.unravel_index(np.nanargmax(values), values.shape)
    lo_r, lo_c = np.unravel_index(np.nanargmin(values), values.shape)
    sc = list(data.scenario)
    return story('sensitivity', message=f'情景结果介于 {level(values[lo_r, lo_c], digits)}–{level(values[hi_r, hi_c], digits)}',
                 unit=f'{unit}，直接展示模型输出，未重算 DCF',
                 take_head='结果对假设敏感' if values.size > 1 else '单一情景',
                 take_text=(f'最高 {level(values[hi_r, hi_c], digits)}（{sc[hi_r]}，{numeric.columns[hi_c]}），'
                            f'最低 {level(values[lo_r, lo_c], digits)}（{sc[lo_r]}，{numeric.columns[lo_c]}）。'),
                 note='每格为对应行、列假设组合下的输入结果；灰度越深数值越高。',
                 evidence=[('最高', level(values[hi_r, hi_c], digits)), ('最低', level(values[lo_r, lo_c], digits)),
                           ('中位数', level(float(np.nanmedian(values)), digits))], evidence_head=unit)


@chart('sensitivity')
def plot_sensitivity(fig, rect, data, meta, reg, s):
    numeric = data.drop(columns='scenario')
    digits = meta.get('sensitivity_decimals', 2)
    values = numeric.to_numpy(dtype=float)
    lo, hi = np.nanmin(values), np.nanmax(values)
    norm = Normalize(lo, hi if hi > lo else lo + 1)
    ax = matrix_axes(fig, rect, reg, data.scenario, numeric.columns, rows_max_h=len(data) * 8)
    draw_matrix(ax, values, data.scenario, numeric.columns, lambda v: GREYS(.05 + .8 * norm(v)),
                lambda v: level(v, digits), reg)


# Backwards-compatible single-chart entry points.
def render(key, fig, x, y, width, data, meta):
    return standalone(fig, key, data, meta, x, y, width)


def make_panel(key):
    def panel(fig, x, y, width, data, meta):
        render(key, fig, x, y, width, data, meta)
    return panel
