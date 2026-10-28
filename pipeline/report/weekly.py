"""The Weekly Commentary: a dense A4 issue built from the selected charts.

Page 1 opens under the brand-green nameplate with a row of KPI tiles; one thesis page
carries the week's main finding, one large chart and its evidence; data pages run three
columns with hairline column rules (broken where a block spans columns), and every chart
carries its takeaway directly beneath it. Running heads carry the series name in brand
green; the footer carries the update time and page number.
"""
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

from .charts import (STORIES, PLOTS, story_for, full_note, COMPACT, REGULAR, BASELINE, MM, BRAND, SURFACE, INK, INK_MUTED, LINE,
                    LINE_SUBTLE, LINE_STRONG, PX, compose, block_heights, draw_block, text, lines_at, rule,
                    vrule, fill, wrap_lines, text_width, delta, market, highlights, level, change, bp,
                    cn_date, cn_range)

PAGE_W, PAGE_H = 210, 297
MX = 18                         # side margin
WIDTH = PAGE_W - 2 * MX         # 174 mm
COLS, GUTTER = 3, 6
COL_W = (WIDTH - (COLS - 1) * GUTTER) / COLS
TOP, BOTTOM = 22, 277           # content area on running-head pages
ROW_GAP = 7
PLOT_H = 38
SPAN = {'trends': 2, 'returns': 1, 'curve': 2, 'spread': 1, 'heatmap': 2, 'comparison': 2, 'drawdown': 2,
        'volatility': 2, 'rolling_correlation': 1, 'correlation': 2, 'risk_return': 2, 'distribution': 1,
        'candlestick': 2, 'relative': 2, 'calendar': 3, 'flows': 2, 'valuation': 1, 'football': 1,
        'waterfall': 2, 'sensitivity': 2}
SPAN['football'] = 2


def desired_plot_h(key, data):
    """Plot height a chart needs in the weekly; a row takes the tallest of its blocks."""
    try:
        if key == 'comparison':
            return len(data.columns) * 4.4 + 16
        if key in ('heatmap',):
            return len(data) * 6 + 9
        if key == 'correlation':
            return max(len(data) - 1, 1) * 6 + 9
        if key in ('calendar', 'sensitivity'):
            return len(data) * 6.5 + 9
        if key == 'football':
            return len(data) * 7 + 8
        if key == 'returns':
            return len(data.columns) * 5.6 + 6
    except Exception:
        pass
    return {'candlestick': 54, 'risk_return': 46}.get(key, PLOT_H)


def col_x(col):
    return MX + col * (COL_W + GUTTER)


def span_w(span):
    return span * COL_W + (span - 1) * GUTTER


def pack(keys):
    """First-fit into rows of three columns, then widen the last block of any row with a gap."""
    rows = []
    for key in keys:
        span = SPAN.get(key, 2)
        for row in rows:
            if sum(s for _, s in row) + span <= COLS:
                row.append([key, span])
                break
        else:
            rows.append([[key, span]])
    for row in rows:
        free = COLS - sum(s for _, s in row)
        if free:
            row[-1][1] += free
    return rows


def issue_week(meta):
    d = pd.Timestamp(meta['as_of'])
    year, week, _ = d.isocalendar()
    return f'{year}年第 {week} 周'


# ── Page furniture ────────────────────────────────────────────────────────────
def running_head(fig, meta):
    text(fig, MX, 10.5, '市场一周', 12, BRAND, 'serif')
    text(fig, MX + WIDTH, 11.5, f"{cn_date(meta['as_of'])}  ·  {issue_week(meta)}", COMPACT.label, INK_MUTED,
         ha='right')
    rule(fig, MX, 16.5, WIDTH, LINE)


def footer(fig, meta, page, pages):
    rule(fig, MX, 281, WIDTH, LINE)
    tail = '  ·  DEMO 模拟数据，非真实行情' if meta['is_demo'] else ''
    if page == 1 and meta.get('omitted'):
        tail += f"  ·  本期未列入：{'、'.join(meta['omitted'])}"
    text(fig, MX, 283.3, f"数据更新 {meta['updated_at']}{tail}", COMPACT.label, INK_MUTED)
    text(fig, MX + WIDTH, 283.3, f'{page} / {pages}', COMPACT.label, INK_MUTED, ha='right')


def nameplate(fig, meta):
    """The one large field of brand green in the issue."""
    fill(fig, 0, 0, PAGE_W, 40, BRAND)
    text(fig, MX, 8.5, '资本市场周报  ·  WEEKLY MARKETS', COMPACT.label, SURFACE, 'semibold')
    text(fig, MX, 14, '市场一周', 34, SURFACE, 'serif')
    text(fig, MX + WIDTH, 23, cn_date(meta['as_of']), 12 * PX * 1.25, SURFACE, 'serif', ha='right')
    marker = issue_week(meta) + ('  ·  DEMO 模拟数据' if meta['is_demo'] else '')
    text(fig, MX + WIDTH, 30.5, marker, COMPACT.label, SURFACE, ha='right')


def quoted(meta, name):
    """Whether an asset's level is a market quote; meta['quoted'] lists them (default: every asset)."""
    names = meta.get('quoted')
    return names is None or name in names


def kpi_tiles(frame, yields, meta):
    """Overview first: the focus asset, the week's leader, and the 10Y yield (or the laggard)."""
    tiles = []
    up_down = market(meta)[:2]
    start, end = meta['week_start'], meta['week_end']
    try:
        from .data import weekly_returns, tolerance, values_at
        changes = weekly_returns(frame, start, end, tolerance(meta))
        last = values_at(frame, end, tolerance(meta))
        chosen = highlights(meta, frame.columns)
    except Exception:
        changes, chosen = None, []
    if changes is not None:
        names = []
        for name in [chosen[0], changes.idxmax(), changes.idxmin()]:
            if name not in names:
                names.append(name)
        for name in names:
            tile = dict(label=f'{name}  ·  本周', figure=level(last[name]), value=changes[name],
                        delta=change(changes[name]), period=f'较{cn_date(start, True)}')
            if not quoted(meta, name):  # a total-return index level means nothing to a reader
                tile.update(figure=change(changes[name]), value=None, delta=None)
            tiles.append(tile)
    if yields is not None and '10Y' in getattr(yields, 'columns', []):
        try:
            from .rates import curve_snapshot
            from .data import tolerance
            before, after = curve_snapshot(yields, start, end, tolerance(meta))
            move = (after['10Y'] - before['10Y']) * 100
            tile = dict(label='10Y 收益率  ·  本周', figure=f"{after['10Y']:.2f}%", value=round(move),
                        delta=bp(move), period=f'较{cn_date(start, True)}')
            tiles = tiles[:2] + [tile]
        except Exception:
            pass
    return tiles[:3], up_down


def draw_kpis(fig, y, tiles, colors):
    reg = COMPACT
    for i, tile in enumerate(tiles):
        x = col_x(i)
        rule(fig, x, y, COL_W)
        text(fig, x, y + 1.6, tile['label'], reg.label, INK_MUTED, 'semibold')
        text(fig, x, y + 6.2, tile['figure'], 21, INK, 'figure')
        ax = fig.add_axes([0, 0, 1, 1], frameon=False)
        ax.set_axis_off()
        ax.set_xlim(0, PAGE_W)
        ax.set_ylim(PAGE_H, 0)
        dw = 0
        if tile['delta'] is not None:
            delta(ax, (x, y + 17.6), tile['value'], tile['delta'], colors, reg, ha='left', offset=0)
            dw = text_width(fig, tile['delta'], 'semibold', reg.table) + 4.5
        text(fig, x + dw, y + 15.9, tile['period'], reg.label, INK_MUTED)
    return y + 22 + ROW_GAP if tiles else y


# ── Rows of chart blocks ──────────────────────────────────────────────────────
def measure_rows(fig, rows, datasets, meta):
    measured = []
    for row in rows:
        blocks, col = [], 0
        for key, span in row:
            width = span_w(span)
            story = story_for(key, datasets[key], meta)
            parts = compose(fig, key, story, meta, COMPACT, width, takeaway=True)
            blocks.append(dict(key=key, col=col, span=span, width=width, story=story, parts=parts,
                               heights=block_heights(parts, COMPACT)))
            col += span
        heights = tuple(max(b['heights'][i] for b in blocks) for i in range(3))
        plot_h = min(max(desired_plot_h(b['key'], datasets[b['key']]) for b in blocks), 70)
        measured.append(dict(blocks=blocks, heights=heights, plot_h=plot_h,
                             total=heights[0] + plot_h + heights[1] + heights[2]))
    return measured


def draw_row(fig, y, row, datasets, meta):
    for block in row['blocks']:
        draw_block(fig, block['key'], datasets[block['key']], meta, col_x(block['col']), y, block['width'],
                   row['plot_h'], COMPACT, block['story'], block['parts'], row['heights'])
    # Column rules in each gutter no block spans.
    covered = set()
    for block in row['blocks']:
        covered.update(range(block['col'], block['col'] + block['span'] - 1))
    for gutter in range(COLS - 1):
        if gutter not in covered:
            x = col_x(gutter) + COL_W + GUTTER / 2
            vrule(fig, x, y, y + row['total'])
    return y + row['total'] + ROW_GAP


# ── Thesis page ───────────────────────────────────────────────────────────────
def draw_thesis(fig, key, data, meta):
    reg = COMPACT
    story = story_for(key, data, meta)
    message = (meta.get('titles') or {}).get(key) or story['message']
    custom = (meta.get('takeaways') or {}).get(key) or {}
    y = TOP + 2
    text(fig, MX, y, f"本期论点  ·  {story['label']}", reg.label, INK_MUTED, 'semibold')
    y += BASELINE + 1
    lines = wrap_lines(fig, message, 'serif', 36, WIDTH)[:3]
    y = lines_at(fig, MX, y, lines, 36, 54 * PX * 25.4 / 72, INK, 'serif')
    lede = custom.get('text') or story['take_text']
    y = lines_at(fig, MX, y + 2, wrap_lines(fig, lede, 'serif', 13.5, WIDTH * .82), 13.5, 27 * PX * 25.4 / 72,
                 INK_MUTED, 'serif') + 6
    chart_w = span_w(2)
    # Chart block (unit line + large plot) in columns one and two.
    rule(fig, MX, y, chart_w)
    unit = wrap_lines(fig, story['unit'], 'sans', reg.body, chart_w)
    yy = lines_at(fig, MX, y + 1.6, unit, reg.body, reg.body_lead, INK_MUTED) + 2
    note = full_note(story)
    source = wrap_lines(fig, f"来源：{meta['source']}。截至{cn_date(meta['as_of'])}。" + (f"注：{note}" if note else ''),
                        'sans', reg.source, chart_w)
    plot_h = BOTTOM - 4 - yy - len(source) * reg.source_lead - 4
    PLOTS[key](fig, (MX, yy, chart_w, plot_h), data, meta, REGULAR, story)
    lines_at(fig, MX, yy + plot_h + 2.5, source, reg.source, reg.source_lead, INK_MUTED)
    # Evidence in column three.
    ex, ew = col_x(2), COL_W
    vrule(fig, col_x(1) + COL_W + GUTTER / 2, y, BOTTOM - 4)
    rule(fig, ex, y, ew)
    text(fig, ex, y + 1.6, '证据', reg.label, INK_MUTED, 'semibold')
    ey = y + 1.6 + BASELINE
    head = custom.get('heading') or story['take_head']
    ey = lines_at(fig, ex, ey, wrap_lines(fig, head, 'serif', reg.message, ew), reg.message, reg.message_lead, INK, 'serif')
    ey = lines_at(fig, ex, ey + 1, wrap_lines(fig, story['take_text'], 'sans', reg.body, ew), reg.body, reg.body_lead, INK) + 4
    if story.get('evidence'):
        rule(fig, ex, ey, ew)
        ey += 1.6
        ey = lines_at(fig, ex, ey, wrap_lines(fig, story.get('evidence_head', ''), 'semibold', reg.label, ew),
                      reg.label, BASELINE, INK_MUTED, 'semibold')
        rule(fig, ex, ey + .4, ew, LINE)
        ey += 1.6
        for i, (label, value) in enumerate(story['evidence'][:14]):
            if i and i % 5 == 0:
                rule(fig, ex, ey - .6, ew, LINE_SUBTLE)
            text(fig, ex, ey, str(label), reg.table, INK)
            text(fig, ex + ew, ey, str(value), reg.table, INK, 'semibold', ha='right')
            ey += BASELINE


# ── Data notes: one place for proxies, observation dates and the date rule ───
DATE_RULE = ('周度截点为周五。各序列取截点前最近一个观察值（不早于 6 天）；节假日沿用前一交易日收盘，'
             '序列末端不外推。缺失保持空白，不插值。')


def notes_lines(fig, meta):
    """[(name, wrapped note lines)], intro lines and closing lines of the data-notes block."""
    width = WIDTH - 30
    rows = [(name, wrap_lines(fig, note, 'sans', COMPACT.table, width))
            for name, note in (meta.get('series_notes') or {}).items()]
    intro = wrap_lines(fig, DATE_RULE, 'sans', COMPACT.body, WIDTH) if meta.get('date_rule') == 'asof' else []
    tail = []
    if meta.get('omitted'):
        tail = wrap_lines(fig, f"本期未列入：{'、'.join(meta['omitted'])}。", 'sans', COMPACT.body, WIDTH)
    return rows, intro, tail


def notes_height(fig, meta):
    rows, intro, tail = notes_lines(fig, meta)
    if not (rows or tail):
        return 0
    reg = COMPACT
    return (1.6 + BASELINE + len(intro) * reg.body_lead + 2 + sum(len(lines) for _, lines in rows) * reg.body_lead
            + (2 + len(tail) * reg.body_lead if tail else 0) + 2)


def draw_notes(fig, y, meta):
    reg = COMPACT
    rows, intro, tail = notes_lines(fig, meta)
    rule(fig, MX, y, WIDTH)
    text(fig, MX, y + 1.6, '数据说明', reg.label, INK_MUTED, 'semibold')
    y = lines_at(fig, MX, y + 1.6 + BASELINE, intro, reg.body, reg.body_lead, INK) + 2
    for name, lines in rows:
        text(fig, MX, y, name, reg.table, INK, 'semibold')
        y = lines_at(fig, MX + 30, y, lines, reg.table, reg.body_lead, INK)
    if tail:
        y = lines_at(fig, MX, y + 2, tail, reg.body, reg.body_lead, INK)
    return y


# ── The issue ─────────────────────────────────────────────────────────────────
def choose_thesis(selected, meta):
    thesis = meta.get('thesis')
    if thesis is False or len(selected) < 4:
        return None
    # A thesis chart that isn't in this issue falls back to the first selected chart.
    return thesis if thesis in selected else selected[0]


def build_issue(path, selected, datasets, frame, yields, meta):
    thesis = choose_thesis(selected, meta)
    rows = pack([k for k in selected if k != thesis])
    scratch = plt.figure(figsize=(PAGE_W * MM, PAGE_H * MM))
    measured = measure_rows(scratch, rows, datasets, meta)
    tiles, colors = kpi_tiles(frame, yields, meta)
    plt.close(scratch)

    # Lay rows onto pages: page 1 under the nameplate and tiles, the thesis page second.
    first_top = 48 + (22 + ROW_GAP if tiles else 0)
    pages, ends, remaining, start = [], [], list(measured), first_top
    while remaining:
        # Fill each page in reading order; if the next row doesn't fit, pull up a later one that does.
        page, y, i = [], start, 0
        while i < len(remaining):
            row = remaining[i]
            if not page or y + row['total'] <= BOTTOM:
                page.append(remaining.pop(i))
                y += row['total'] + ROW_GAP
            else:
                i += 1
        pages.append(page)
        ends.append(y)
        start = TOP + 2
    pages, ends = pages or [[]], ends or [first_top]
    scratch = plt.figure(figsize=(PAGE_W * MM, PAGE_H * MM))
    notes_h = notes_height(scratch, meta)
    plt.close(scratch)
    if notes_h and ends[-1] + notes_h > BOTTOM:
        pages.append([])
    notes_page = len(pages) - 1 if notes_h else None
    plan = [('front', pages[0], notes_page == 0)]
    if thesis:
        plan.append(('thesis', None, False))
    plan += [('data', rows_, notes_page == i) for i, rows_ in enumerate(pages[1:], start=1)]

    with PdfPages(path, metadata={'Title': '市场一周', 'Author': 'Capital Weekly',
                  'Subject': 'Simulated data template preview' if meta['is_demo'] else 'Weekly market commentary'}) as pdf:
        for number, (kind, page_rows, notes) in enumerate(plan, start=1):
            fig = plt.figure(figsize=(PAGE_W * MM, PAGE_H * MM))
            if kind == 'front':
                nameplate(fig, meta)
                y = draw_kpis(fig, 48, tiles, colors)
            else:
                running_head(fig, meta)
                y = TOP + 2
            if kind == 'thesis':
                draw_thesis(fig, thesis, datasets[thesis], meta)
            else:
                for row in page_rows:
                    y = draw_row(fig, y, row, datasets, meta)
            if notes:
                draw_notes(fig, y, meta)
            footer(fig, meta, number, len(plan))
            pdf.savefig(fig)
            plt.close(fig)
