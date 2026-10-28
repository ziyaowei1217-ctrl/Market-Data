"""Chart system for the weekly market report, built on the Richard Wei Finance design system.

Every chart is a *story* (finding, units, takeaway, evidence) plus a *plot* that fits any
box: a full-width standalone export, or one, two or three columns of the Weekly
Commentary. About 90% of every chart is ink, grey and white; cobalt marks the one series
or item a chart is about; IBCS notation gives actual values a solid dark fill and
comparison periods a lighter grey; up/down uses teal/vermilion (红涨绿跌 with
`market_colors: "cn"`), always with a sign and a triangle. Brand green appears only in
the issue's nameplate and running heads, never in a chart.
"""
from pathlib import Path
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.offsetbox import AnnotationBbox, HPacker, TextArea
from matplotlib.ticker import MaxNLocator, FuncFormatter
import numpy as np
import pandas as pd

from .data import normalize, weekly_returns, tolerance, values_at

MM = 1 / 25.4
PX = .75  # design-system px -> pt

# ── Tokens (light theme; the system has one theme) ────────────────────────────
BRAND = '#102820'                     # identity only: nameplate, running-head series name
SURFACE = '#ffffff'
SUNKEN = '#f4f4f3'
LINE_SUBTLE = '#e8e8e8'
LINE = '#d4d4d4'
LINE_STRONG = '#141414'
INK = '#141414'
INK_MUTED = '#5e5e5e'
ACCENT = '#1e3bd6'
ACCENT_SOFT = '#e9edfd'
TEAL, TEAL_SOFT = '#00766e', '#e0f1ef'
VERMILION, VERMILION_SOFT = '#b93d0a', '#fbeae2'
GOOD, BAD = TEAL, VERMILION           # IBCS variances: never swap by market
AC = '#333333'                         # scenario: actual
PY = '#8a8a8a'                         # scenario: prior period
RANGE_1, RANGE_2 = '#c9c9c9', '#e1e1e1'
CONTEXT = PY
GREYS = LinearSegmentedColormap.from_list('greys', [SUNKEN, RANGE_2, RANGE_1, PY, AC])
MISSING_TEXT = '–'
BASELINE = 18 * PX * 25.4 / 72        # the weekly's 18px baseline in mm


class Register:
    """Type sizes (pt) and line steps (mm): regular for standalone charts, compact for the weekly."""

    def __init__(self, compact):
        self.compact = compact
        self.message = 16 * PX if compact else 22 * PX       # subhead-dense 16/18 | title 22/28
        self.message_lead = BASELINE if compact else 28 * PX * 25.4 / 72
        self.label = 11 * PX
        self.body = 12 * PX                                   # body-dense / caption
        self.body_lead = BASELINE if compact else 16 * PX * 25.4 / 72
        self.table = 12 * PX if compact else 13 * PX
        self.tick = 11 * PX
        self.source = 11 * PX if compact else 12 * PX
        self.source_lead = 14 * PX * 25.4 / 72 if compact else 16 * PX * 25.4 / 72
        self.axis_bottom = 5.2


REGULAR, COMPACT = Register(False), Register(True)

FONT_DIR = Path(__file__).parent / 'assets' / 'fonts'
FONT_FILES = ['PublicSansTF-Regular.ttf', 'PublicSansTF-SemiBold.ttf', 'Newsreader-Medium.ttf',
              'Newsreader-Regular.ttf', 'NotoSansSC-Regular.ttf', 'NotoSansSC-SemiBold.ttf',
              'NotoSerifSC-Medium.ttf']
SANS = ['Public Sans TF', 'Noto Sans SC']
SERIF = ['Newsreader', 'Noto Serif SC']


_COVERAGE = None


def coverage():
    """Code points every role can draw: Latin in both Latin faces, or CJK in both (GB2312 subset) CJK faces."""
    global _COVERAGE
    if _COVERAGE is None:
        from matplotlib.ft2font import FT2Font
        cmap = {name: set(FT2Font(str(FONT_DIR / name)).get_charmap()) for name in FONT_FILES}
        latin = cmap['PublicSansTF-Regular.ttf'] & cmap['Newsreader-Regular.ttf']
        cjk = cmap['NotoSansSC-Regular.ttf'] & cmap['NotoSansSC-SemiBold.ttf'] & cmap['NotoSerifSC-Medium.ttf']
        _COVERAGE = latin | cjk
    return _COVERAGE


def missing_glyphs(*values):
    """Characters in the given strings (nested lists/dicts allowed) that the bundled fonts cannot draw."""
    found, stack = set(), list(values)
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            stack.extend(value.keys())
            stack.extend(value.values())
        elif isinstance(value, (list, tuple, set)):
            stack.extend(value)
        elif isinstance(value, str):
            found.update(c for c in value if not c.isspace() and ord(c) not in coverage())
    return ''.join(sorted(found))


def font(role='sans', size=None):
    """sans 400 · semibold (sans 600) · serif (500, headlines) · figure (serif 400, big numbers)."""
    if role in ('serif', 'figure'):
        prop = FontProperties(family=SERIF, weight=500 if role == 'serif' else 400)
    else:
        prop = FontProperties(family=SANS, weight=600 if role == 'semibold' else 400)
    if size:
        prop.set_size(size)
    return prop


def setup_theme():
    import logging
    logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
    for name in FONT_FILES:
        path = FONT_DIR / name
        if not path.exists():
            raise ValueError(f'缺少字体：{path}')
        font_manager.fontManager.addfont(str(path))
    plt.rcParams.update({
        'font.family': SANS, 'font.weight': 400, 'font.size': 9,
        'text.color': INK, 'axes.labelcolor': INK_MUTED,
        'xtick.color': INK_MUTED, 'ytick.color': INK_MUTED,
        'xtick.labelsize': 11 * PX, 'ytick.labelsize': 11 * PX,
        'axes.unicode_minus': True, 'pdf.fonttype': 42, 'ps.fonttype': 42,
        'figure.facecolor': SURFACE, 'savefig.facecolor': SURFACE, 'axes.facecolor': 'none',
        'lines.solid_capstyle': 'butt', 'lines.solid_joinstyle': 'round',
        'legend.frameon': False})


# ── Market colours & highlights ───────────────────────────────────────────────
def market(meta):
    """(up, down, up_soft, down_soft); 红涨绿跌 when market_colors is "cn"."""
    mode = meta.get('market_colors', 'global')
    if mode not in ('global', 'cn'):
        raise ValueError('market_colors 只能是 "global"（青涨橙红跌）或 "cn"（红涨绿跌）。')
    if mode == 'cn':
        return VERMILION, TEAL, VERMILION_SOFT, TEAL_SOFT
    return TEAL, VERMILION, TEAL_SOFT, VERMILION_SOFT


def diverging(meta):
    up, down, up_soft, down_soft = market(meta)
    return LinearSegmentedColormap.from_list('market', [(0, down), (.3, down_soft), (.5, SUNKEN),
                                                        (.7, up_soft), (1, up)])


def highlights(meta, columns):
    """1–2 assets to emphasise: the first in cobalt, the second in actual-ink; default focus_asset."""
    columns = list(columns)
    names = meta.get('highlight')
    if names is None:
        names = [meta.get('focus_asset', columns[0])]
    if isinstance(names, str):
        names = [names]
    if (not isinstance(names, list) or not 1 <= len(names) <= 2 or len(set(names)) != len(names)
            or any(name not in columns for name in names)):
        raise ValueError('highlight 须为 1–2 个不重复的资产名称，且必须是资产列之一。')
    return names


def series_color(name, chosen):
    if name in chosen:
        return ACCENT if chosen.index(name) == 0 else AC
    return CONTEXT


# ── Numbers & dates (fixed precision per measure) ─────────────────────────────
def _minus(text):
    return text.replace('-', '−')


def level(value, digits=2):
    """Prices and levels: thousands separators, no sign."""
    return MISSING_TEXT if not np.isfinite(value) else _minus(f'{value:,.{digits}f}')


def change(value, digits=1, suffix='%'):
    """Changes always carry a sign; percent sticks to the number."""
    if not np.isfinite(value):
        return MISSING_TEXT
    body = f'{abs(value):,.{digits}f}'
    sign = '' if float(body.replace(',', '')) == 0 else ('+' if value > 0 else '−')
    return f'{sign}{body}{suffix}'


def bp(value, signed=True):
    return (change(value, 0, '') if signed else level(value, 0)) + ' bp'


def signed(value, fmt='.1f'):
    digits = int(fmt[1]) if fmt.startswith('.') and fmt[1].isdigit() else 0
    return change(value, digits, '')


def plain(value, fmt='.2f'):
    return _minus(format(value, fmt))


def move_word(value, up='上涨', down='下跌'):
    return up if value >= 0 else down


def cn_date(value, short=False):
    d = pd.Timestamp(value)
    return f'{d.month}月{d.day}日' if short else f'{d.year}年{d.month}月{d.day}日'


def cn_range(start, end):
    a, b = pd.Timestamp(start), pd.Timestamp(end)
    if a.year == b.year:
        return f'{cn_date(a, True)}–{cn_date(b, True)}（{b.year}年）'
    return f'{cn_date(a)}–{cn_date(b)}'


def wrap(label, n=6):
    label = str(label)
    if label.isascii():
        return label
    return '\n'.join(label[i:i + n] for i in range(0, len(label), n))


def text_on(fill):
    def lum(c):
        r, g, b = [v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4 for v in to_rgb(c)]
        return .2126 * r + .7152 * g + .0722 * b
    l = lum(fill)
    return SURFACE if 1.05 / (l + .05) > (l + .05) / (lum(INK) + .05) else INK


# ── Measuring and wrapping text ───────────────────────────────────────────────
_WIDTHS = {}
_TOKEN = re.compile(r"[!-~−–×·]+|\s+|.", re.S)
_NO_LINE_START = set('，。、；：？！）》」』%,.;:!?)]')


def text_width(fig, value, role='sans', size=9):
    """Rendered width in mm (cached)."""
    key = (value, role, round(size, 2))
    if key not in _WIDTHS:
        renderer = fig.canvas.get_renderer()
        w, _, _ = renderer.get_text_width_height_descent(value, font(role, size), ismath=False)
        _WIDTHS[key] = w / renderer.dpi * 25.4
    return _WIDTHS[key]


def wrap_lines(fig, value, role, size, width):
    """Greedy line breaking for mixed Chinese/Latin text; ASCII runs never split."""
    lines, current = [], ''
    for token in _TOKEN.findall(str(value)):
        trial = current + token
        if current and text_width(fig, trial.rstrip(), role, size) > width:
            if not token.strip():
                lines.append(current.rstrip())
                current = ''
                continue
            if token[0] in _NO_LINE_START:
                current = trial
                continue
            lines.append(current.rstrip())
            current = token.lstrip()
        else:
            current = trial
    if current.strip():
        lines.append(current.rstrip())
    return lines or ['']


# ── Layout primitives ─────────────────────────────────────────────────────────
def fig_size_mm(fig):
    return fig.get_size_inches() / MM


def text(fig, x, y, value, size=9, color=INK, role='sans', **kwargs):
    """Text positioned from the top-left in physical millimetres."""
    width, height = fig_size_mm(fig)
    kwargs.setdefault('va', 'top')
    return fig.text(x / width, 1 - y / height, value, fontproperties=font(role),
                    fontsize=size, color=color, **kwargs)


def lines_at(fig, x, y, lines, size, lead, color=INK, role='sans', **kwargs):
    for i, line in enumerate(lines):
        text(fig, x, y + i * lead, line, size, color, role, **kwargs)
    return y + len(lines) * lead


def rule(fig, x, y, width, color=LINE_STRONG, lw=PX):
    w, h = fig_size_mm(fig)
    fig.add_artist(Line2D([x / w, (x + width) / w], [1 - y / h] * 2, transform=fig.transFigure,
                          color=color, linewidth=lw, solid_capstyle='butt'))


def vrule(fig, x, y0, y1, color=LINE, lw=PX):
    w, h = fig_size_mm(fig)
    fig.add_artist(Line2D([x / w] * 2, [1 - y0 / h, 1 - y1 / h], transform=fig.transFigure,
                          color=color, linewidth=lw, solid_capstyle='butt'))


def fill(fig, x, y, width, height, color):
    w, h = fig_size_mm(fig)
    fig.add_artist(Rectangle((x / w, 1 - (y + height) / h), width / w, height / h,
                             transform=fig.transFigure, facecolor=color, edgecolor='none'))


def axes_at(fig, x, y, width, height):
    w, h = fig_size_mm(fig)
    return fig.add_axes([x / w, 1 - (y + height) / h, max(width, 1) / w, max(height, 1) / h])


def clean_axes(ax, reg=REGULAR):
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis='both', which='both', length=0, labelsize=reg.tick, pad=3.5, colors=INK_MUTED)
    ax.set_axisbelow(True)
    ax.set_facecolor('none')


def hgrid(ax):
    ax.grid(axis='y', color=LINE_SUBTLE, lw=PX)
    ax.grid(axis='x', visible=False)


def vgrid(ax):
    ax.grid(axis='x', color=LINE_SUBTLE, lw=PX)
    ax.grid(axis='y', visible=False)


def baseline(ax, value=0, vertical=False):
    (ax.axvline if vertical else ax.axhline)(value, color=LINE_STRONG, lw=PX, zorder=3)


def data_per_mm(ax):
    fw, fh = fig_size_mm(ax.figure)
    box = ax.get_position()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    return abs(x1 - x0) / (box.width * fw), abs(y1 - y0) / (box.height * fh)


def plot_axes(fig, rect, reg, left=9, right=0, top=0, bottom=None):
    x, y, w, h = rect
    bottom = reg.axis_bottom if bottom is None else bottom
    ax = axes_at(fig, x + left, y + top, w - left - right, h - top - bottom)
    clean_axes(ax, reg)
    return ax


def fit_left(fig, ax, rect, reg, right=0, top=0, bottom=None, extra=1.8):
    """Move the axes' left edge to just clear its y tick labels (call after limits/formatter)."""
    x, y, w, h = rect
    bottom = reg.axis_bottom if bottom is None else bottom
    lo, hi = sorted(ax.get_ylim())
    locs = [v for v in ax.yaxis.get_majorticklocs() if lo - 1e-9 <= v <= hi + 1e-9]
    labels = ax.yaxis.get_major_formatter().format_ticks(locs) if locs else ['']
    left = max(text_width(fig, str(t), 'sans', reg.tick) for t in labels) + extra
    fw, fh = fig_size_mm(fig)
    ax.set_position([(x + left) / fw, 1 - (y + h - bottom) / fh, (w - left - right) / fw, (h - top - bottom) / fh])
    return left


def legend_top(fig, rect, handles, reg):
    """Legend in rows across the top of a plot box; returns the height it uses (mm)."""
    if not handles:
        return 0
    x, y, w, _ = rect
    widths = [4.5 + 1.4 + text_width(fig, h.get_label(), 'sans', reg.tick) + 3.5 for h in handles]
    ncol = len(handles)
    while ncol > 1:
        cols = [max(widths[i::ncol]) for i in range(ncol)]
        if sum(cols) <= w:
            break
        ncol -= 1
    rows = -(-len(handles) // ncol)
    fw, fh = fig_size_mm(fig)
    fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(x / fw, 1 - y / fh), ncol=ncol,
               borderaxespad=0, borderpad=0, handlelength=1.6, handleheight=.8, columnspacing=1.2,
               handletextpad=.4, labelspacing=.35, prop=font('sans', reg.tick), labelcolor=INK_MUTED,
               frameon=False)
    return rows * reg.tick * 25.4 / 72 * 1.45 + 2.2


def date_axis(ax, index):
    span = (index[-1] - index[0]).days
    if span > 1100:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{mdates.num2date(v).year}年'))
    elif span >= 90:
        width = ax.get_position().width * fig_size_mm(ax.figure)[0]
        months = (1, 7) if width < 60 else (1, 4, 7, 10) if span > 200 else range(1, 13)
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=months))

        def month(v, _):
            d = mdates.num2date(v)
            return f'{d.year}年{d.month}月' if d.month == 1 else f'{d.month}月'
        ax.xaxis.set_major_formatter(FuncFormatter(month))
    else:
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=2, maxticks=4))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: cn_date(mdates.num2date(v), True)))
    ax.set_xlim(index[0], index[-1])


def delta(ax, xy, value, text_value, colors, reg, ha='left', offset=4.5, coords='data', size=None):
    """Delta: small triangle + signed number in the up/down colour; flat values stay ink."""
    up, down = colors
    size = size or reg.table
    color = up if value > 0 else down if value < 0 else INK
    parts = []
    if value != 0:
        parts.append(TextArea('▲' if value > 0 else '▼',
                              textprops=dict(color=color, fontsize=size * .5, fontproperties=font('sans'))))
    parts.append(TextArea(text_value, textprops=dict(color=color, fontsize=size, fontproperties=font('semibold'))))
    box = HPacker(children=parts, align='center', pad=0, sep=1.4)
    ab = AnnotationBbox(box, xy, xybox=(offset if ha == 'left' else -offset, 0), xycoords=coords,
                        boxcoords='offset points', box_alignment=(0 if ha == 'left' else 1, .5),
                        frameon=False, pad=0, annotation_clip=False)
    ax.add_artist(ab)
    return ab


def delta_width(fig, text_value, reg):
    return text_width(fig, text_value, 'semibold', reg.table) + reg.table * .5 * 25.4 / 72 + 2.2


def draw_matrix(ax, values, rowlabels, collabels, colorize, fmt, reg, blank=None, gap=.8, emphasis=None):
    """Flat cells separated by a white gap (no borders); missing cells show an en dash."""
    values = np.asarray(values, dtype=float)
    rows, cols = values.shape
    clean_axes(ax, reg)
    ax.set_xlim(0, cols)
    ax.set_ylim(rows, 0)
    dx, dy = data_per_mm(ax)
    gx, gy = min(gap * dx / 2, .2), min(gap * dy / 2, .2)
    for r in range(rows):
        for c in range(cols):
            if blank is not None and blank[r][c]:
                continue
            value = values[r, c]
            finite = np.isfinite(value)
            shade = ACCENT if emphasis == (r, c) else (colorize(value) if finite else SUNKEN)
            ax.add_patch(Rectangle((c + gx, r + gy), 1 - 2 * gx, 1 - 2 * gy,
                                   facecolor=shade, edgecolor='none', linewidth=0))
            ax.text(c + .5, r + .5, fmt(value) if finite else MISSING_TEXT, ha='center', va='center',
                    fontsize=reg.table, color=text_on(shade) if finite else INK_MUTED,
                    fontproperties=font('semibold' if emphasis == (r, c) else 'sans'))
    ax.set_xticks(np.arange(cols) + .5, [str(v) for v in collabels])
    ax.set_yticks(np.arange(rows) + .5, [str(v) for v in rowlabels])
    ax.xaxis.tick_top()
    ax.tick_params(axis='x', labelcolor=INK_MUTED, labelsize=reg.label, pad=3)
    ax.tick_params(axis='y', labelcolor=INK, labelsize=reg.body, pad=5)
    for label in ax.get_xticklabels():
        label.set_fontproperties(font('semibold', reg.label))
    return ax


def matrix_axes(fig, rect, reg, rowlabels, collabels, rows_max_h=None):
    """Axes for a matrix: left clears the row labels, top clears the column heads."""
    x, y, w, h = rect
    left = max(text_width(fig, str(v), 'sans', reg.body) for v in rowlabels) + 3
    top = reg.label * 25.4 / 72 * 1.6 + 1.5
    height = h - top - 1
    if rows_max_h:
        height = min(height, rows_max_h)
    return axes_at(fig, x + left, y + top, w - left, height)


def end_dot(ax, x, y, color, size=4, zorder=6):
    ax.plot(x, y, 'o', color=color, markersize=size, markeredgecolor=SURFACE,
            markeredgewidth=1, zorder=zorder, clip_on=False)


def label_text(name, value_text):
    return f'{name}  {value_text}'


def end_label_width(fig, entries, reg):
    return max(text_width(fig, label_text(e[2], e[3]), 'semibold' if e[5] else 'sans', reg.body)
               for e in entries) + 3.5


def end_labels(ax, entries, reg):
    """Direct labels at line ends with thin leaders in the series colour; text stays ink.
    entries = [(y_value, date, name, value_text, colour, strong)]."""
    fw, fh = fig_size_mm(ax.figure)
    plot_h = ax.get_position().height * fh
    plot_w = ax.get_position().width * fw
    low, high = ax.get_ylim()
    gap = (reg.body * 25.4 / 72 * 1.25 + .4) * (high - low) / plot_h
    order = sorted(range(len(entries)), key=lambda i: entries[i][0])
    positions = np.array([entries[i][0] for i in order], dtype=float)
    for i in range(1, len(positions)):
        positions[i] = max(positions[i], positions[i - 1] + gap)
    if positions[-1] > high - gap / 3:
        positions -= positions[-1] - (high - gap / 3)
    for i in range(len(positions) - 2, -1, -1):
        positions[i] = min(positions[i], positions[i + 1] - gap)
    transform = ax.get_yaxis_transform()
    x0 = 1 + 1.2 / plot_w
    x1 = 1 + 2.6 / plot_w
    for i, pos in zip(order, positions):
        value, date, name, value_text, color, strong = entries[i]
        ax.annotate('', xy=(date, value), xycoords='data', xytext=(x0, pos), textcoords=transform,
                    annotation_clip=False,
                    arrowprops=dict(arrowstyle='-', color=color, lw=PX, shrinkA=0, shrinkB=2))
        ax.text(x1, pos, label_text(name, value_text), transform=transform, va='center', ha='left',
                fontsize=reg.body, color=INK if strong else INK_MUTED,
                fontproperties=font('semibold' if strong else 'sans'), clip_on=False)


def emphasis_entries(frame, chosen, value_fmt, extra=None):
    entries = list(extra or [])
    for name in frame.columns:
        valid = frame[name].dropna()
        if valid.empty:
            continue
        strong = name in chosen
        entries.append((valid.iloc[-1], valid.index[-1], name, value_fmt(valid.iloc[-1]),
                        series_color(name, chosen), strong))
    return entries


def emphasis_lines(ax, frame, chosen, entries, reg):
    """Context series in grey underneath, emphasised series on top, all labelled at the end."""
    for name in sorted(frame.columns, key=lambda n: (n in chosen, -chosen.index(n) if n in chosen else 0)):
        series = frame[name]
        valid = series.dropna()
        if valid.empty:
            continue
        strong = name in chosen
        first = strong and chosen.index(name) == 0
        color = series_color(name, chosen)
        ax.plot(series.index, series, color=color, lw=1.5 if first else 1.1 if strong else .75,
                zorder=5 if first else 4 if strong else 3)
        if strong:
            end_dot(ax, valid.index[-1], valid.iloc[-1], color)
    end_labels(ax, entries, reg)


def line_panel(fig, rect, reg, frame, chosen, value_fmt, ylim, yfmt=None, base=None, extra=None):
    """Shared multi-series line chart with direct end labels."""
    entries = emphasis_entries(frame, chosen, value_fmt, extra)
    right = end_label_width(fig, entries, reg)
    ax = plot_axes(fig, rect, reg, right=right)
    hgrid(ax)
    ax.set_ylim(*ylim)
    ax.yaxis.set_major_locator(MaxNLocator(5 if rect[3] > 40 else 4))
    if yfmt:
        ax.yaxis.set_major_formatter(FuncFormatter(yfmt))
    fit_left(fig, ax, rect, reg, right=right)
    date_axis(ax, frame.index)
    if base is not None:
        baseline(ax, base)
    emphasis_lines(ax, frame, chosen, entries, reg)
    return ax


# ── The chart block: header, plot, takeaway, source ───────────────────────────
def source_text(meta, story, reg):
    note = (story.get('note') or '') + (SERIES_POINTER if story.get('series_note') else '')
    if reg.compact:
        text_value = f"来源：{meta['source']}。截至{cn_date(meta['as_of'], True)}。"
        return text_value + (f'注：{note}' if note else '')
    return None


def compose(fig, key, story, meta, reg, width, takeaway):
    """Wrap every text element of a block to its width."""
    message = (meta.get('titles') or {}).get(key) or story['message']
    custom = (meta.get('takeaways') or {}).get(key) or {}
    parts = {
        'label': story['label'],
        'message': wrap_lines(fig, message, 'serif', reg.message, width),
        'unit': wrap_lines(fig, story['unit'], 'sans', reg.body, width),
    }
    if takeaway:
        parts['take_head'] = wrap_lines(fig, custom.get('heading') or story['take_head'], 'semibold', reg.body, width)
        parts['take_text'] = wrap_lines(fig, custom.get('text') or story['take_text'], 'sans', reg.body, width)
    if reg.compact:
        parts['source'] = wrap_lines(fig, source_text(meta, story, reg), 'sans', reg.source, width)
    else:
        lines = []
        if full_note(story):
            lines += wrap_lines(fig, full_note(story), 'sans', reg.source, width)
        lines += wrap_lines(fig, f"来源：{meta['source']}", 'sans', reg.source, width)
        tail = '  ·  DEMO 模拟数据，非真实行情' if meta['is_demo'] else ''
        lines += wrap_lines(fig, f"观察截止 {cn_date(meta['as_of'])}  ·  数据更新 {meta['updated_at']}{tail}",
                            'sans', reg.source, width)
        parts['source'] = lines
    return parts


def block_heights(parts, reg):
    label_lead = BASELINE if reg.compact else 4.6
    header = 1.6 + label_lead + len(parts['message']) * reg.message_lead + len(parts['unit']) * reg.body_lead + 1.6
    take = 0
    if 'take_head' in parts:
        take = 2.2 + (len(parts['take_head']) + len(parts['take_text'])) * reg.body_lead
    source = 1.6 + len(parts['source']) * reg.source_lead
    return header, take, source


def draw_block(fig, key, data, meta, x, y, width, plot_h, reg, story, parts, heights):
    """Draw a block whose header/takeaway/source heights are given (so a row lines up)."""
    header_h, take_h, source_h = heights
    rule(fig, x, y, width)
    yy = y + 1.6
    text(fig, x, yy, parts['label'], reg.label, INK_MUTED, 'semibold')
    yy += BASELINE if reg.compact else 4.6
    yy = lines_at(fig, x, yy, parts['message'], reg.message, reg.message_lead, INK, 'serif')
    lines_at(fig, x, yy, parts['unit'], reg.body, reg.body_lead, INK_MUTED)
    PLOTS[key](fig, (x, y + header_h, width, plot_h), data, meta, reg, story)
    yy = y + header_h + plot_h
    if 'take_head' in parts:
        yy += 2.2
        yy = lines_at(fig, x, yy, parts['take_head'], reg.body, reg.body_lead, INK, 'semibold')
        lines_at(fig, x, yy, parts['take_text'], reg.body, reg.body_lead, INK)
    yy = y + header_h + plot_h + take_h + 1.6
    lines_at(fig, x, yy, parts['source'], reg.source, reg.source_lead, INK_MUTED)
    return y + header_h + plot_h + take_h + source_h


RATE_CHARTS = {'curve', 'spread', 'comparison'}
TABLE_CHARTS = {'candlestick', 'waterfall', 'football', 'sensitivity', 'flows', 'valuation'}


def chart_series(key, meta, assets, tenors):
    """The asset or tenor names a chart draws, for attaching series notes."""
    assets = [] if assets is None else list(assets)
    tenors = [] if tenors is None else list(tenors)
    if key in TABLE_CHARTS:
        return []
    if key == 'spread':
        return [t for t in ('2Y', '10Y') if t in tenors]
    if key in RATE_CHARTS:
        return tenors
    if key in ('distribution', 'calendar'):
        return [meta.get('focus_asset', assets[0])] if assets else []
    if key == 'rolling_correlation':
        return list(meta.get('correlation_pair', assets[:2]))
    return assets


def chart_notes(selected, meta, assets, tenors):
    """meta['series_notes'] ({name: note}, e.g. proxies and lagging dates) → {chart: 'name：note。…'}."""
    notes = meta.get('series_notes') or {}
    result = {}
    for key in selected:
        groups = {}  # note → names, in drawing order; '3M、2Y、10Y：截至10月22日'
        for name in chart_series(key, meta, assets, tenors):
            if notes.get(name):
                groups.setdefault(notes[name], []).append(name)
        if groups:
            result[key] = '；'.join(f"{'、'.join(names)}：{note}" for note, names in groups.items()) + '。'
    return result


SERIES_POINTER = '代理与观察日见末页数据说明。'


def story_for(key, data, meta):
    """A chart's story plus this issue's series notes for it (proxies, earlier observation dates)."""
    story = STORIES[key](data, meta)
    extra = (meta.get('chart_notes') or {}).get(key)
    return {**story, 'series_note': extra} if extra else story


def full_note(story):
    return (story.get('note') or '') + (story.get('series_note') or '')


def standalone(fig, key, data, meta, x, y, width, height=None):
    """One chart as its own figure: header, plot, source (no takeaway)."""
    story = story_for(key, data, meta)
    parts = compose(fig, key, story, meta, REGULAR, width, takeaway=False)
    heights = block_heights(parts, REGULAR)
    if height is None:
        height = fig_size_mm(fig)[1] - y - 4
    plot_h = height - heights[0] - heights[2]
    return draw_block(fig, key, data, meta, x, y, width, plot_h, REGULAR, story, parts, heights)


STORIES, PLOTS = {}, {}


def chart(key):
    """Register story/plot functions for a chart key."""
    def register(fn):
        (STORIES if fn.__name__.startswith('story') else PLOTS)[key] = fn
        return fn
    return register


# ── Trends ────────────────────────────────────────────────────────────────────
@chart('trends')
def story_trends(frame, meta):
    indexed = normalize(frame)
    last = indexed.ffill().iloc[-1] - 100
    top, bottom = last.idxmax(), last.idxmin()
    above = int((last > 0).sum())
    return dict(
        label='跨资产走势',
        message=f'{top}累计{move_word(last[top])} {abs(last[top]):.1f}%，{bottom}{move_word(last[bottom])} {abs(last[bottom]):.1f}%',
        unit=f'价格 / 指数水平，{cn_date(indexed.index[0])} = 100',
        take_head=f'{top}领先',
        take_text=(f'自{cn_date(indexed.index[0], True)}以来，{top}与{bottom}相差 {last[top] - last[bottom]:.1f} 个百分点。'
                   f'{len(last)} 个资产中 {above} 个高于基准日水平。'),
        evidence=[(name, change(v)) for name, v in last.sort_values(ascending=False).items()],
        evidence_head='自基准日累计变化')


@chart('trends')
def plot_trends(fig, rect, frame, meta, reg, story):
    indexed = normalize(frame)
    chosen = highlights(meta, indexed.columns)
    minimum, maximum = np.nanmin(indexed), np.nanmax(indexed)
    span = max(maximum - minimum, 10)
    line_panel(fig, rect, reg, indexed, chosen, lambda v: level(v),
               (minimum - .06 * span, maximum + .06 * span), base=100)


# ── Weekly returns ranking ────────────────────────────────────────────────────
@chart('returns')
def story_returns(frame, meta):
    changes = weekly_returns(frame, meta['week_start'], meta['week_end'], tolerance(meta)).sort_values(ascending=False)
    top, bottom = changes.index[0], changes.index[-1]
    ups, downs = int((changes > 0).sum()), int((changes < 0).sum())
    return dict(
        label='本周资产表现',
        message=f'本周{top}{move_word(changes[top])} {abs(changes[top]):.1f}%，{bottom}{move_word(changes[bottom])} {abs(changes[bottom]):.1f}%',
        unit=f"周涨跌幅（%），{cn_range(meta['week_start'], meta['week_end'])}",
        take_head='涨多跌少' if ups > downs else '跌多涨少' if downs > ups else '涨跌各半',
        take_text=f'{len(changes)} 个资产中 {ups} 个上涨、{downs} 个下跌，首尾相差 {changes[top] - changes[bottom]:.1f} 个百分点。',
        evidence=[(name, change(v)) for name, v in changes.items()],
        evidence_head='本周涨跌幅')


@chart('returns')
def plot_returns(fig, rect, frame, meta, reg, story):
    """Bars from one zero line; the values sit in a right-aligned column, like a table."""
    changes = weekly_returns(frame, meta['week_start'], meta['week_end'], tolerance(meta)).sort_values(ascending=False)
    chosen = highlights(meta, frame.columns)
    up, down, *_ = market(meta)
    labels = [change(v) for v in changes]
    left = max(text_width(fig, n, 'semibold', reg.body) for n in changes.index) + 3
    right = max(delta_width(fig, t, reg) for t in labels) + 2
    ax = plot_axes(fig, rect, reg, left=left, right=right)
    vgrid(ax)
    values = changes.to_numpy()
    lo, hi = min(values.min(), 0), max(values.max(), 0)
    pad = (hi - lo) * .05
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_ylim(len(values) - .5, -.5)
    colors = [ACCENT if name == chosen[0] else AC for name in changes.index]
    ax.barh(range(len(values)), values, height=.56, color=colors, zorder=2)
    plot_w = rect[2] - left - right
    edge = 1 + right / plot_w
    for row, (value, label) in enumerate(zip(values, labels)):
        delta(ax, (edge, row), value, label, (up, down), reg, ha='right', offset=0,
              coords=ax.get_yaxis_transform())
    ax.set_yticks(range(len(values)), list(changes.index))
    ax.tick_params(axis='y', pad=6, labelcolor=INK, labelsize=reg.body)
    for tick, name in zip(ax.get_yticklabels(), changes.index):
        tick.set_fontproperties(font('semibold' if name == chosen[0] else 'sans', reg.body))
    baseline(ax, 0, vertical=True)
    ax.xaxis.set_major_locator(MaxNLocator(3 if plot_w < 45 else 5))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: plain(v, 'g') + '%'))


# Backwards-compatible single-chart entry points.
def trend_panel(fig, x, y, width, frame, meta):
    return standalone(fig, 'trends', frame, meta, x, y, width)


def ranking_panel(fig, x, y, width, frame, meta):
    return standalone(fig, 'returns', frame, meta, x, y, width)


# ── Export ────────────────────────────────────────────────────────────────────
HIGHLIGHT_CHARTS = {'trends', 'returns', 'drawdown', 'volatility', 'relative', 'risk_return'}
FIG_W, FIG_H = 170, 112
FILENAMES = {'trends': 'cross-asset-trends', 'returns': 'weekly-returns', 'curve': 'yield-curve',
             'spread': 'yield-spread', 'heatmap': 'performance-heatmap', 'comparison': 'rate-comparison'}


def validate_style(meta, frame, selected):
    market(meta)
    titles = meta.get('titles', {}) or {}
    if not isinstance(titles, dict) or any(not isinstance(v, str) or not 1 <= len(v.strip()) <= 30
                                           for v in titles.values()):
        raise ValueError('titles 须为 {图表名: 1–30 字的结论句}。')
    takeaways = meta.get('takeaways', {}) or {}
    if not isinstance(takeaways, dict) or any(
            not isinstance(v, dict) or not set(v) <= {'heading', 'text'}
            or any(not isinstance(t, str) or not 1 <= len(t.strip()) <= 120 for t in v.values())
            for v in takeaways.values()):
        raise ValueError('takeaways 须为 {图表名: {"heading": 短句, "text": 1–120 字}}。')
    tolerance(meta)
    for key in ('quoted', 'omitted'):
        if key in meta and (not isinstance(meta[key], list) or any(not isinstance(v, str) for v in meta[key])):
            raise ValueError(f'{key} 须为字符串列表。')
    notes = meta.get('series_notes', {})
    if not isinstance(notes, dict) or any(not isinstance(v, str) or len(v) > 40 for v in notes.values()):
        raise ValueError('series_notes 须为 {序列名: 不超过 40 字的说明}。')
    thesis = meta.get('thesis')
    if thesis is not None and thesis is not False and not isinstance(thesis, str):
        raise ValueError('thesis 须为图表名（如 "trends"），或设为 false 关闭论点页。')
    if frame is not None and HIGHLIGHT_CHARTS.intersection(selected):
        highlights(meta, frame.columns)
    missing = missing_glyphs(meta, [] if frame is None else [str(c) for c in frame.columns])
    if missing:
        raise ValueError(f'字体不含这些字符，请换成常用字或去掉：{missing}')


def export_report(frame, meta, output, yields=None, selected=None, bundle=None):
    from . import extra_charts  # noqa: F401  (registers rate and heatmap charts)
    from . import street_charts  # noqa: F401  (registers Street charts)
    from .rates import curve_snapshot, spread_bp, horizon_returns
    from .street_data import STREET, prepare
    from .weekly import build_issue

    sources = {'trends': frame, 'returns': frame, 'heatmap': frame,
               'curve': yields, 'spread': yields, 'comparison': yields}
    selected = selected or ['trends', 'returns']
    if len(set(selected)) != len(selected) or any(k not in sources and k not in STREET for k in selected):
        raise ValueError('图表选择不能重复或包含未知名称。')
    datasets = {}
    for key in selected:
        datasets[key] = prepare(key, frame, bundle or {}, meta) if key in STREET else sources[key]
    # Validate all selected calculations before creating any output files.
    for key in selected:
        data = datasets[key]
        if data is None:
            raise ValueError(f'{key} 缺少数据；资产图需 --csv，利率图需 --yields。')
        if key in ('curve', 'comparison'):
            curve_snapshot(data, meta['week_start'], meta['week_end'], tolerance(meta))
        elif key == 'spread':
            spread_bp(data)
        elif key == 'heatmap':
            horizon_returns(data, meta.get('heatmap_starts'), meta['as_of'], tolerance(meta))
        elif key == 'trends':
            normalize(data)
        elif key == 'returns':
            weekly_returns(data, meta['week_start'], meta['week_end'], tolerance(meta))
    validate_style(meta, frame, selected)
    meta = {**meta, 'chart_notes': chart_notes(selected, meta, None if frame is None else frame.columns,
                                               None if yields is None else yields.columns)}
    setup_theme()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for key in selected:
        fig = plt.figure(figsize=(FIG_W * MM, FIG_H * MM))
        standalone(fig, key, datasets[key], meta, 5, 6, FIG_W - 10)
        for extension in ('png', 'pdf'):
            path = output / f"{FILENAMES.get(key, key.replace('_', '-'))}.{extension}"
            fig.savefig(path, dpi=300)
            paths.append(path)
        plt.close(fig)
    report = output / 'weekly-report.pdf'
    build_issue(report, selected, datasets, frame, yields, meta)
    return [report] + paths
