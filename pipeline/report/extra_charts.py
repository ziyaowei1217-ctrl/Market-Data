"""Rates and cross-horizon charts in the Richard Wei Finance style."""
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import MaxNLocator, FuncFormatter
import numpy as np
import pandas as pd

from .charts import (chart, standalone, plot_axes, fit_left, legend_top, axes_at, clean_axes, hgrid, vgrid,
                    baseline, end_dot, draw_matrix, matrix_axes, delta, delta_width, market, diverging,
                    level, change, bp, plain, font, text_width, cn_date, cn_range, date_axis,
                    ACCENT, AC, PY, INK, INK_MUTED, LINE, SURFACE, RANGE_2, LINE_SUBTLE, PX)
from .rates import curve_snapshot, spread_bp, horizon_returns
from .data import tolerance

__all__ = ['date_axis', 'yield_panel', 'spread_panel', 'heatmap_panel', 'comparison_panel']


# ── Yield curve ───────────────────────────────────────────────────────────────
@chart('curve')
def story_curve(frame, meta):
    before, after = curve_snapshot(frame, meta['week_start'], meta['week_end'], tolerance(meta))
    moves = (after - before) * 100
    if {'2Y', '10Y'}.issubset(after.index):
        slope = ((after['10Y'] - after['2Y']) - (before['10Y'] - before['2Y'])) * 100
        message = f"曲线{'陡峭化' if slope > 0 else '平坦化'}，10Y {'上行' if moves['10Y'] > 0 else '下行'} {abs(moves['10Y']):.0f} bp"
        head = f"曲线{'陡峭化' if slope > 0 else '平坦化'}"
        text_value = (f"2Y {bp(moves['2Y'])}，10Y {bp(moves['10Y'])}，10Y−2Y 利差"
                      f"{'走阔' if slope > 0 else '收窄'} {abs(slope):.0f} bp。")
    else:
        tenor = after.index[-1]
        message = f"{tenor} 收益率{'上行' if moves[tenor] > 0 else '下行'} {abs(moves[tenor]):.0f} bp"
        head, text_value = f'{tenor} {bp(moves[tenor])}', f'{len(moves)} 个期限中 {int((moves > 0).sum())} 个上行。'
    return dict(label='国债收益率曲线', message=message,
                unit=f"收益率（%），{cn_date(meta['week_end'])} 与一周前",
                take_head=head, take_text=text_value + f'变动最大的是 {moves.abs().idxmax()}（{bp(moves[moves.abs().idxmax()])}）。',
                evidence=[(t, f'{after[t]:.2f}%  {bp(moves[t])}') for t in after.index], evidence_head='本周收益率与周变动')


@chart('curve')
def plot_curve(fig, rect, frame, meta, reg, story):
    before, after = curve_snapshot(frame, meta['week_start'], meta['week_end'], tolerance(meta))
    handles = [Line2D([], [], color=PY, lw=1.1, marker='o', ms=3.4, mec=SURFACE, label=f"上周（{cn_date(meta['week_start'], True)}）"),
               Line2D([], [], color=AC, lw=1.5, marker='o', ms=4, mec=SURFACE, label=f"本周（{cn_date(meta['week_end'], True)}）")]
    top = legend_top(fig, rect, handles, reg)
    ax = plot_axes(fig, rect, reg, top=top, right=2)
    hgrid(ax)
    positions = np.arange(len(after))
    lo, hi = min(before.min(), after.min()), max(before.max(), after.max())
    pad = max(hi - lo, .1) * .25
    ax.set_ylim(lo - pad, hi + pad)
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.1f}%'))
    fit_left(fig, ax, rect, reg, right=2, top=top)
    ax.plot(positions, before, color=PY, lw=1.1, zorder=3)
    ax.plot(positions, before, 'o', color=PY, ms=3.4, mec=SURFACE, mew=.8, zorder=3)
    ax.plot(positions, after, color=AC, lw=1.5, zorder=4)
    ax.plot(positions, after, 'o', color=AC, ms=4, mec=SURFACE, mew=.9, zorder=4)
    ax.set_xticks(positions, after.index)
    ax.set_xlim(-.4, len(after) - .6)
    for i in sorted({0, len(after) - 1}):
        ax.annotate(f'{after.iloc[i]:.2f}%', (i, after.iloc[i]), xytext=(0, 6), textcoords='offset points',
                    ha='center' if 0 < i < len(after) - 1 else ('left' if i == 0 else 'right'),
                    color=INK, fontsize=reg.body, fontproperties=font('semibold'))


# ── 2s10s spread ──────────────────────────────────────────────────────────────
@chart('spread')
def story_spread(frame, meta):
    spread = spread_bp(frame)
    valid = spread.dropna()
    last, date = valid.iloc[-1], valid.index[-1]
    week = pd.Timestamp(meta['week_start'])
    prior = valid.loc[week - pd.Timedelta(days=tolerance(meta)):week]
    diff, ref = (last - prior.iloc[-1], '一周前') if len(prior) else (last - valid.iloc[0], '样本起点')
    inverted = int((valid < 0).sum())
    return dict(label='期限利差',
                message=f"10Y−2Y 利差为 {bp(last, False)}，较{ref}{'走阔' if diff > 0 else '收窄'} {abs(diff):.0f} bp",
                unit='10Y − 2Y（bp），1 bp = 0.01 个百分点',
                take_head='曲线倒挂' if last < 0 else '利差为正',
                take_text=(f'样本内最低 {bp(valid.min(), False)}、最高 {bp(valid.max(), False)}；'
                           f'{inverted} 个观察日处于倒挂。'),
                evidence=[('最新', bp(last, False)), (ref, bp(last - diff, False)), ('样本最低', bp(valid.min(), False)),
                          ('样本最高', bp(valid.max(), False)), ('倒挂天数', f'{inverted}')],
                evidence_head='利差（bp）', last=last, date=date)


@chart('spread')
def plot_spread(fig, rect, frame, meta, reg, story):
    spread = spread_bp(frame)
    valid = spread.dropna()
    last, date = valid.iloc[-1], valid.index[-1]
    handles = [Patch(facecolor=RANGE_2, lw=0, label='倒挂区间'),
               Line2D([], [], ls='none', marker='o', color=ACCENT, mec=SURFACE, ms=5, label=f'最新（{cn_date(date, True)}）')]
    top = legend_top(fig, rect, handles, reg)
    right = text_width(fig, bp(last, False), 'semibold', reg.table) + 3
    ax = plot_axes(fig, rect, reg, top=top, right=right)
    hgrid(ax)
    low, high = min(valid.min(), 0), max(valid.max(), 0)
    pad = max(high - low, 10) * .1
    ax.set_ylim(low - pad, high + pad)
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: plain(v, 'g')))
    fit_left(fig, ax, rect, reg, right=right, top=top)
    date_axis(ax, spread.index)
    ax.fill_between(spread.index, spread, 0, where=spread < 0, color=RANGE_2, lw=0, interpolate=True, zorder=2)
    baseline(ax, 0)
    ax.plot(spread.index, spread, color=AC, lw=1.2, zorder=4)
    end_dot(ax, date, last, ACCENT)
    ax.annotate(bp(last, False), (date, last), xytext=(5, 0), textcoords='offset points', va='center',
                color=INK, fontsize=reg.table, fontproperties=font('semibold'), annotation_clip=False)


# ── Cross-horizon heatmap ─────────────────────────────────────────────────────
@chart('heatmap')
def story_heatmap(frame, meta):
    starts = meta.get('heatmap_starts')
    returns = horizon_returns(frame, starts, meta['as_of'], tolerance(meta))
    last = returns.columns[-1]
    col = returns[last].dropna()
    first = returns.columns[0]
    one = returns[first].dropna()
    if len(col):
        message = f"{last} 区间{col.idxmax()}{move_word(col.max())} {abs(col.max()):.1f}%，居各资产之首"
        text_value = f"{last} 区间 {int((col > 0).sum())}/{len(col)} 个资产上涨。"
        if len(one) and first != last:
            text_value += f"{first} 区间{one.idxmax()}涨幅最大（{change(one.max())}）。"
    else:
        message, text_value = f'{last} 区间数据缺失', '基准日缺少数据的格子显示为 –。'
    bases = '，'.join(f'{label} {cn_date(date)}' for label, date in starts.items())
    return dict(label='跨周期表现', message=message, unit=f"累计涨跌幅（%），截至 {cn_date(meta['as_of'])}",
                take_head=f'{col.idxmax()}领先' if len(col) else '数据缺失', take_text=text_value,
                note=f'基准日：{bases}。',
                evidence=[(name, change(v)) for name, v in col.sort_values(ascending=False).items()],
                evidence_head=f'{last} 累计涨跌幅')


def move_word(value):
    return '上涨' if value >= 0 else '下跌'


@chart('heatmap')
def plot_heatmap(fig, rect, frame, meta, reg, story):
    returns = horizon_returns(frame, meta.get('heatmap_starts'), meta['as_of'], tolerance(meta))
    values = returns.to_numpy()
    finite = values[np.isfinite(values)]
    extent = max(np.abs(finite).max(), .1) if len(finite) else 1.
    norm = TwoSlopeNorm(vmin=-extent, vcenter=0, vmax=extent)
    cmap = diverging(meta)
    ax = matrix_axes(fig, rect, reg, returns.index, returns.columns, rows_max_h=len(returns) * 8)
    draw_matrix(ax, values, returns.index, returns.columns, lambda v: cmap(norm(v)), lambda v: change(v), reg)


# ── Weekly rate moves (dumbbell + table) ──────────────────────────────────────
@chart('comparison')
def story_comparison(frame, meta):
    before, after = curve_snapshot(frame, meta['week_start'], meta['week_end'], tolerance(meta))
    moves = (after - before) * 100
    big = moves.abs().idxmax()
    rising = int((moves > 0).sum())
    short = [t for t in moves.index if t in ('1M', '3M', '6M', '1Y')]
    long = [t for t in moves.index if t in ('10Y', '20Y', '30Y')]
    text_value = ''
    if short and long:
        text_value = f'1 年及以内平均 {bp(moves[short].mean())}，10 年及以上平均 {bp(moves[long].mean())}。'
    return dict(label='利率周度变动', message=f"{len(moves)} 个期限中 {rising} 个上行，{big} 变动最大（{bp(moves[big])}）",
                unit=f"收益率（%），{cn_range(meta['week_start'], meta['week_end'])}",
                take_head='短端下行、长端上行' if short and long and moves[short].mean() < 0 < moves[long].mean()
                else f'{rising} 个期限上行',
                take_text=text_value or f'{big} 变动最大。',
                evidence=[(t, bp(m)) for t, m in moves.items()], evidence_head='较上周（bp）')


@chart('comparison')
def plot_comparison(fig, rect, frame, meta, reg, story):
    before, after = curve_snapshot(frame, meta['week_start'], meta['week_end'], tolerance(meta))
    moves = (after - before) * 100
    up, down, *_ = market(meta)
    handles = [Line2D([], [], ls='none', marker='o', color=PY, mec=SURFACE, ms=5, label='上周'),
               Line2D([], [], ls='none', marker='o', color=AC, mec=SURFACE, ms=5.6, label='本周')]
    top = legend_top(fig, rect, handles, reg)
    num_w = text_width(fig, '0.00', 'sans', reg.body) + 4
    delta_w = max(delta_width(fig, change(m, 0, ''), reg) for m in moves) + 2
    head_w = text_width(fig, '较上周 bp', 'semibold', reg.label) + 1
    cols = [num_w, num_w, max(delta_w, head_w)]
    right = sum(cols) + 4
    left = max(text_width(fig, t, 'sans', reg.body) for t in after.index) + 3
    x, y, w, h = rect
    ax = plot_axes(fig, rect, reg, left=left, top=top + 4, right=right)
    vgrid(ax)
    rows = np.arange(len(after))
    ax.hlines(rows, np.minimum(before, after), np.maximum(before, after), color=LINE, lw=2, zorder=2)
    ax.scatter(before, rows, color=PY, edgecolors=SURFACE, s=20, lw=.8, zorder=3)
    ax.scatter(after, rows, color=AC, edgecolors=SURFACE, s=26, lw=.9, zorder=4)
    ax.set_yticks(rows, after.index)
    ax.tick_params(axis='y', labelcolor=INK, labelsize=reg.body)
    # A little more space after every fifth row, as in the system's tables.
    ax.set_ylim(len(after) - .4, -.6)
    ax.xaxis.set_major_locator(MaxNLocator(3 if w - left - right < 50 else 4))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.1f}%'))
    ax.margins(x=.12)
    plot_w = w - left - right
    transform = ax.get_yaxis_transform()
    edges, acc = [], 4
    for c in cols:
        acc += c
        edges.append(1 + acc / plot_w)
    for edge, head in zip(edges, ['上周', '本周', '较上周 bp']):
        ax.text(edge, -1.15, head, transform=transform, ha='right', va='center', fontsize=reg.label,
                color=INK_MUTED, clip_on=False, fontproperties=font('semibold'))
    for row, (old, new, move) in enumerate(zip(before, after, moves)):
        ax.text(edges[0], row, f'{old:.2f}', transform=transform, ha='right', va='center',
                fontsize=reg.body, color=INK_MUTED, clip_on=False)
        ax.text(edges[1], row, f'{new:.2f}', transform=transform, ha='right', va='center',
                fontsize=reg.body, color=INK, clip_on=False)
        delta(ax, (edges[2], row), round(move), change(move, 0, ''), (up, down), reg, ha='right', offset=0,
              coords=transform, size=reg.body)


# Backwards-compatible single-chart entry points.
def yield_panel(fig, x, y, width, frame, meta):
    return standalone(fig, 'curve', frame, meta, x, y, width)


def spread_panel(fig, x, y, width, frame, meta):
    return standalone(fig, 'spread', frame, meta, x, y, width)


def heatmap_panel(fig, x, y, width, frame, meta):
    return standalone(fig, 'heatmap', frame, meta, x, y, width)


def comparison_panel(fig, x, y, width, frame, meta):
    return standalone(fig, 'comparison', frame, meta, x, y, width)
