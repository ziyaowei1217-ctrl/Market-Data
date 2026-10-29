/* @ds-bundle: {"format":4,"namespace":"RWFinance","components":[{"name":"Page"},{"name":"Band"},{"name":"Kicker"},{"name":"Para"},{"name":"SideBlock"},{"name":"Contents"},{"name":"ChartBlock"},{"name":"SourceNote"},{"name":"LineChart"},{"name":"ColumnChart"},{"name":"BarChart"},{"name":"DataTable"},{"name":"Num"},{"name":"Delta"},{"name":"KeyFigure"},{"name":"Positioning"},{"name":"ScenarioSet"},{"name":"Notes"},{"name":"Marker"},{"name":"RiskWarning"},{"name":"Disclosures"}]} */
(function () {
  'use strict';
  var React = window.React;
  var h = React.createElement;
  var MINUS = '−';
  var EN_DASH = '–';
  var NBSP = ' ';

  function cx() {
    return Array.prototype.filter.call(arguments, Boolean).join(' ');
  }
  function pad2(n) {
    var s = String(n);
    return s.length < 2 ? '0' + s : s;
  }
  function textWidth(s, size, bold) {
    // Public Sans averages about 0.56em a character (0.6em bold); enough to size margins.
    // [market-data patch] CJK and full-width characters take a full em.
    var w = 0;
    Array.prototype.forEach.call(String(s == null ? '' : s), function (c) {
      w += /[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]/.test(c) ? 1 : (bold ? 0.6 : 0.56);
    });
    return w * size;
  }

  /* ---------- number formatting ---------- */

  var COMPACT = {
    en: [[1e12, 'T'], [1e9, 'B'], [1e6, 'M'], [1e3, 'K']],
    zh: [[1e8, '亿'], [1e4, '万']]
  };
  function defaultDecimals(format, compacted) {
    if (format === 'percent') return 1;
    if (format === 'bp') return 0;
    if (format === 'multiple') return 1;
    return compacted ? 1 : 2;
  }
  function isBlank(value) {
    return value === null || value === undefined || value === '' || !isFinite(Number(value));
  }
  function formatNumber(value, opts) {
    var o = opts || {};
    if (isBlank(value)) return o.empty != null ? o.empty : EN_DASH;
    var v = Number(value);
    var format = o.format || 'number';
    var abs = Math.abs(v);
    var compactSuffix = '';
    if (o.compact && COMPACT[o.compact]) {
      var steps = COMPACT[o.compact];
      for (var i = 0; i < steps.length; i++) {
        if (abs >= steps[i][0]) { abs = abs / steps[i][0]; compactSuffix = steps[i][1]; break; }
      }
    }
    var d = o.decimals != null ? o.decimals : defaultDecimals(format, !!compactSuffix);
    var rounded = Number(abs.toFixed(d));
    var body = rounded.toLocaleString(o.locale || 'en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
    var suffix = format === 'percent' ? '%' : format === 'bp' ? 'bp' : format === 'multiple' ? '×' : '';
    var unit = '';
    if (o.unit) unit = (/^[　-鿿＀-￯]/.test(o.unit) ? '' : NBSP) + o.unit;
    var text = (o.currency || '') + body + compactSuffix + suffix + unit;
    var sign = rounded === 0 ? 0 : v < 0 ? -1 : 1;
    if (sign < 0) return o.negative === 'parens' ? '(' + text + ')' : MINUS + text;
    if (sign > 0 && o.signed) return '+' + text;
    return text;
  }
  function signOf(value, decimals) {
    if (isBlank(value)) return 0;
    var v = Number(value);
    var r = Number(Math.abs(v).toFixed(decimals));
    return r === 0 ? 0 : v < 0 ? -1 : 1;
  }
  function Triangle(dir) {
    return h('svg', { viewBox: '0 0 8 8', 'aria-hidden': 'true', focusable: 'false' },
      h('path', { d: dir > 0 ? 'M4 0.5 L7.6 7 L0.4 7 Z' : 'M0.4 1 L7.6 1 L4 7.5 Z' }));
  }

  function Num(props) {
    var p = props || {};
    return h('span', { className: cx('rwf-num', p.className), title: p.title }, formatNumber(p.value, p));
  }

  function Delta(props) {
    var p = props || {};
    var format = p.format || 'percent';
    var d = p.decimals != null ? p.decimals : defaultDecimals(format, false);
    var s = signOf(p.value, d);
    var mode = p.mode || 'market';
    var tone, word;
    if (isBlank(p.value)) { tone = 'rwf-flat'; word = 'no data'; }
    else if (s === 0) { tone = 'rwf-flat'; word = 'unchanged'; }
    else if (mode === 'variance') {
      var better = p.polarity === 'lower' ? s < 0 : s > 0;
      tone = better ? 'rwf-good' : 'rwf-bad';
      word = better ? 'favorable' : 'unfavorable';
    } else {
      tone = s > 0 ? 'rwf-up' : 'rwf-down';
      word = s > 0 ? 'up' : 'down';
    }
    var text = formatNumber(p.value, { format: format, decimals: d, signed: true, currency: p.currency, unit: p.unit });
    return h('span', { className: cx('rwf-delta', p.chip && 'rwf-chip', tone, p.className) },
      s !== 0 && p.icon !== false ? Triangle(s) : null,
      h('span', { className: 'rwf-sr' }, word + ' '),
      text);
  }

  function KeyFigure(props) {
    var p = props || {};
    return h('div', { className: cx('rwf-keyfigure', p.className) },
      h('span', { className: 'rwf-keyfig' }, p.value),
      p.label ? h('span', { className: 'rwf-keyfig-label' }, p.label) : null);
  }

  /* ---------- Page ---------- */

  function Page(props) {
    var p = props || {};
    var kind = p.kind || 'standard';
    var meta = [p.date, p.section].filter(Boolean).join(' · ');
    var odd = p.page == null || Number(p.page) % 2 === 1;
    var head = [
      h('div', { key: 'head', className: 'rwf-head' },
        h('span', { className: 'rwf-label rwf-series' }, p.series || 'Weekly commentary'),
        meta ? h('span', { className: 'rwf-label rwf-meta' }, meta) : null),
      h('div', { key: 'rule', className: 'rwf-head-rule', 'aria-hidden': 'true' })
    ];
    var content;
    if (kind === 'cover') {
      var lines = p.titleLines || [p.title];
      content = [
        h('h1', { key: 't', className: 'rwf-cover-title' },
          lines[0] != null ? h('span', { className: 'rwf-line1' }, lines[0]) : null,
          lines[1] != null ? h('span', { className: 'rwf-line2' }, lines[1]) : null),
        p.lede ? h('p', { key: 'l', className: 'rwf-cover-lede' }, p.lede) : null,
        h('div', { key: 'c', className: 'rwf-cover-cols' },
          h('div', { className: 'rwf-cover-main' }, p.children),
          h('aside', { className: 'rwf-cover-side' }, p.side))
      ];
    } else {
      content = [
        p.title != null ? h('div', { key: 't', className: 'rwf-title-area' }, h('h2', { className: 'rwf-page-title' }, p.title)) : null,
        h('div', { key: 'b', className: cx('rwf-body', p.fill === false && 'is-top') }, p.children)
      ];
    }
    return h('section', {
      className: cx('rwf-page', kind === 'cover' && 'rwf-is-cover', p.className),
      lang: p.lang,
      'data-market': p.market,
      'aria-label': p.label || (kind === 'cover' ? 'Page 1' : p.title ? String(p.title) : 'Page')
    },
      head, content,
      p.page != null ? h('div', { className: cx('rwf-folio', odd ? 'is-odd' : 'is-even') }, pad2(p.page)) : null);
  }

  /* ---------- Band ---------- */

  function Band(props) {
    var p = props || {};
    var layout = p.layout || 'narrative';
    var cols = React.Children.toArray(p.children);
    var spanTitle = !(layout === 'narrative' || layout === 'halves');
    var title = p.title != null ? h('h3', { className: 'rwf-section-title' }, p.title) : null;
    return h('section', { className: cx('rwf-band', 'is-' + layout, p.plain && 'is-plain', p.className) },
      title && spanTitle ? h('div', { className: 'rwf-band-title-row' }, title) : null,
      cols.map(function (c, i) {
        return h('div', { key: i, className: 'rwf-col' }, i === 0 && title && !spanTitle ? title : null, c);
      }));
  }

  /* ---------- Text ---------- */

  function Kicker(props) {
    var p = props || {};
    return h('span', { className: cx('rwf-label rwf-kicker', p.className) }, p.children);
  }

  function Para(props) {
    var p = props || {};
    return h('p', { className: cx('rwf-para', p.small && 'rwf-small', p.className) },
      p.lead ? h('span', { className: 'rwf-lead' }, p.lead) : null,
      p.lead ? ' ' : null,
      p.children);
  }

  function SideBlock(props) {
    var p = props || {};
    return h('section', { className: cx('rwf-side', p.first && 'is-first', p.className) },
      p.title ? h('h3', { className: 'rwf-section-title' }, p.title) : null,
      (p.items || []).map(function (it, i) {
        return h('div', { key: i, className: 'rwf-side-item' },
          it.head ? h('span', { className: 'rwf-side-head' }, it.head) : null,
          it.text);
      }),
      p.children);
  }

  function pageRange(pages) {
    if (Array.isArray(pages)) return pad2(pages[0]) + EN_DASH + pad2(pages[1]);
    return pad2(pages);
  }

  function Contents(props) {
    var p = props || {};
    return h('ol', { className: cx('rwf-contents', p.className), 'aria-label': p.label || 'In this issue' },
      (p.items || []).map(function (it, i) {
        var label = it.href ? h('a', { href: it.href }, it.label) : it.label;
        return h('li', { key: i }, h('span', null, label), h('span', { className: 'rwf-pages' }, pageRange(it.pages)));
      }));
  }

  /* ---------- Chart and table blocks ---------- */

  function SourceNote(props) {
    var p = props || {};
    var prefix = p.prefix != null ? p.prefix : 'Source:';
    return h('p', { className: cx('rwf-source', p.className) },
      p.source ? (prefix ? prefix + ' ' : '') + p.source + (p.asOf ? '; as of ' + p.asOf + '.' : '') : null,
      p.source && p.children ? ' ' : null,
      p.children);
  }

  function ChartBlock(props) {
    var p = props || {};
    return h('figure', { className: cx('rwf-figure', p.className) },
      p.title != null ? h('h4', { className: 'rwf-block-title' }, p.title,
        p.qualifier ? h('span', { className: 'rwf-q' }, ', ' + p.qualifier) : null) : null,
      p.children,
      p.source || p.note ? h('figcaption', null, h(SourceNote, { source: p.source, asOf: p.asOf }, p.note)) : null);
  }

  /* ---------- Chart helpers ---------- */

  var ROLE_ORDER = { light: 0, context: 1, compare: 2, subject: 3 };
  function roleOf(s, i, n) {
    if (s.role) return s.role;
    if (n === 1) return 'subject';
    return ['subject', 'context', 'compare', 'light'][Math.min(i, 3)];
  }
  function niceStep(span, count) {
    var raw = span / Math.max(1, count);
    var mag = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10));
    var r = raw / mag;
    var step = r <= 1 ? 1 : r <= 2 ? 2 : r <= 2.5 ? 2.5 : r <= 5 ? 5 : 10;
    return step * mag;
  }
  function niceTicks(lo, hi, count) {
    if (lo === hi) { lo -= 1; hi += 1; }
    var step = niceStep(hi - lo, count || 5);
    var start = Math.floor(lo / step + 1e-9) * step;
    var end = Math.ceil(hi / step - 1e-9) * step;
    var out = [];
    for (var v = start; v <= end + step / 2; v += step) out.push(Number(v.toFixed(10)));
    return { ticks: out, step: step };
  }
  function stepDecimals(step) {
    if (step >= 1) return 0;
    return Math.min(4, Math.ceil(-Math.log(step) / Math.LN10 - 1e-9));
  }
  function spread(items, minGap, lo, hi) {
    items.sort(function (a, b) { return a.y - b.y; });
    for (var i = 1; i < items.length; i++) {
      if (items[i].y - items[i - 1].y < minGap) items[i].y = items[i - 1].y + minGap;
    }
    var over = items.length ? items[items.length - 1].y - hi : 0;
    if (over > 0) for (var j = items.length - 1; j >= 0; j--) {
      items[j].y -= over;
      if (j > 0 && items[j].y - items[j - 1].y >= minGap) break;
    }
    if (items.length && items[0].y < lo) {
      var d = lo - items[0].y;
      items.forEach(function (it) { it.y += d; });
    }
    return items;
  }
  function pickIndices(n, count) {
    if (n <= 0) return [];
    if (n <= count) return Array.from({ length: n }, function (_, i) { return i; });
    var out = [];
    for (var i = 0; i < count; i++) out.push(Math.round(i * (n - 1) / (count - 1)));
    return out.filter(function (v, i, a) { return a.indexOf(v) === i; });
  }
  function wrapLabel(text, maxChars) {
    var words = String(text).split(' ');
    var lines = [''];
    words.forEach(function (w) {
      var cur = lines[lines.length - 1];
      if (!cur) lines[lines.length - 1] = w;
      else if ((cur + ' ' + w).length <= maxChars) lines[lines.length - 1] = cur + ' ' + w;
      else lines.push(w);
    });
    return lines.slice(0, 2);
  }

  /* ---------- LineChart ---------- */

  function LineChart(props) {
    var p = props || {};
    var W = p.width || 348, H = p.height || 200;
    var series = p.series || [];
    var labels = p.labels || [];
    var n = labels.length || Math.max.apply(null, series.map(function (s) { return s.data.length; }).concat([0]));
    var vals = [];
    series.forEach(function (s) { s.data.forEach(function (v) { if (!isBlank(v)) vals.push(Number(v)); }); });
    if (p.reference) vals.push(Number(p.reference.value));
    (p.bands || []).forEach(function (b) { vals.push(b.from, b.to); });
    var lo = p.domain ? p.domain[0] : Math.min.apply(null, vals);
    var hi = p.domain ? p.domain[1] : Math.max.apply(null, vals);
    var nt = niceTicks(lo, hi, p.yTicks || 5);
    var ticks = nt.ticks;
    if (!p.domain) { lo = ticks[0]; hi = ticks[ticks.length - 1]; }
    else ticks = ticks.filter(function (t) { return t >= lo - 1e-9 && t <= hi + 1e-9; });
    var tickDec = p.tickDecimals != null ? p.tickDecimals : stepDecimals(nt.step);
    var tickFmt = function (v) { return formatNumber(v, { decimals: tickDec }); };
    var endDec = p.decimals != null ? p.decimals : Math.max(tickDec, 1);
    var endFmt = function (v) { return formatNumber(v, { format: p.format, decimals: endDec }); };
    var multi = series.length > 1;
    var showLegend = p.legend != null ? p.legend : multi;
    var left = Math.max.apply(null, ticks.map(function (t) { return textWidth(tickFmt(t), 10); })) + 8;
    var right = p.endLabels === false ? 6 : 8 + Math.max.apply(null, series.map(function (s) {
      var last = null; s.data.forEach(function (v) { if (!isBlank(v)) last = v; });
      return textWidth(endFmt(last), 10, true);
    }).concat([0]));
    var top = showLegend ? 18 : p.unit ? 16 : 6;
    var bottom = 18;
    var x0 = left, x1 = W - right, y0 = top, y1 = H - bottom;
    var X = function (i) { return n <= 1 ? x0 : x0 + (x1 - x0) * i / (n - 1); };
    var Y = function (v) { return y1 - (Number(v) - lo) / (hi - lo || 1) * (y1 - y0); };
    var ordered = series.map(function (s, i) { return { s: s, role: roleOf(s, i, series.length), i: i }; })
      .sort(function (a, b) { return ROLE_ORDER[a.role] - ROLE_ORDER[b.role]; });
    var cls = { subject: 'is-subject', context: 'is-context', compare: 'is-compare', light: 'is-light' };
    var paths = ordered.map(function (o) {
      var d = '', pen = false;
      o.s.data.forEach(function (v, i) {
        if (isBlank(v)) { pen = false; return; }
        d += (pen ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1);
        pen = true;
      });
      return h('path', { key: 'p' + o.i, className: cx('rwf-line', cls[o.role], o.s.dashed && 'is-dashed'), d: d });
    });
    var ends = p.endLabels === false ? [] : spread(ordered.map(function (o) {
      var last = null, li = -1;
      o.s.data.forEach(function (v, i) { if (!isBlank(v)) { last = v; li = i; } });
      return last == null ? null : { y: Y(last) + 3.5, text: endFmt(last), role: o.role, key: o.i, dotX: X(li), dotY: Y(last) };
    }).filter(Boolean), 11, y0 + 4, y1 + 3);
    var xIdx = pickIndices(n, p.xTicks || 4);
    var zeroInside = lo < 0 && hi > 0;
    return h('svg', { className: cx('rwf-chart', p.className), viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img', 'aria-label': p.label || 'Chart' },
      p.unit ? h('text', { x: x0 - 6, y: showLegend ? y0 - 4 : 9, textAnchor: 'end' }, p.unit) : null,
      (p.bands || []).map(function (b, i) {
        return h('rect', { key: 'b' + i, className: 'rwf-band-fill', x: x0, width: x1 - x0, y: Y(b.to), height: Math.max(0, Y(b.from) - Y(b.to)) });
      }),
      ticks.map(function (t, i) {
        return h('g', { key: 't' + i },
          i > 0 ? h('line', { className: 'rwf-grid', x1: x0, x2: x1, y1: Y(t), y2: Y(t) }) : null,
          h('text', { x: x0 - 6, y: Y(t) + 3.5, textAnchor: 'end' }, tickFmt(t)));
      }),
      h('line', { className: 'rwf-axis', x1: x0, x2: x1, y1: zeroInside ? Y(0) : y1, y2: zeroInside ? Y(0) : y1 }),
      p.reference ? h('g', null,
        h('line', { className: 'rwf-ref', x1: x0, x2: x1, y1: Y(p.reference.value), y2: Y(p.reference.value) }),
        p.reference.label ? h('text', { x: x1 - 2, y: Y(p.reference.value) - 4, textAnchor: 'end' }, p.reference.label) : null) : null,
      xIdx.map(function (i, k) {
        var anchor = k === 0 && xIdx.length > 1 ? 'start' : k === xIdx.length - 1 && xIdx.length > 1 ? 'end' : 'middle';
        return h('text', { key: 'x' + i, x: X(i), y: H - 4, textAnchor: anchor }, labels[i] != null ? labels[i] : '');
      }),
      paths,
      ends.map(function (e) {
        return h('g', { key: 'e' + e.key },
          e.role === 'subject' ? h('circle', { cx: e.dotX, cy: e.dotY, r: 2, className: 'is-fill-subject' }) : null,
          h('text', { x: x1 + 4, y: e.y, className: 'is-text-' + e.role }, e.text));
      }),
      showLegend ? h('g', null, (function () {
        var x = x0, out = [];
        series.forEach(function (s, i) {
          var role = roleOf(s, i, series.length);
          out.push(h('line', { key: 'k' + i, x1: x, x2: x + 10, y1: 5.5, y2: 5.5, className: cx('rwf-line', cls[role], s.dashed && 'is-dashed') }));
          out.push(h('text', { key: 'l' + i, x: x + 14, y: 9, className: 'is-text-' + role }, s.name));
          x += 14 + textWidth(s.name, 10, true) + 12;
        });
        return out;
      })()) : null);
  }

  /* ---------- ColumnChart ---------- */

  function ColumnChart(props) {
    var p = props || {};
    var W = p.width || 348, H = p.height || 200;
    var cats = p.categories || [];
    var series = p.series || [];
    var vals = [0];
    series.forEach(function (s) { s.data.forEach(function (v) { if (!isBlank(v)) vals.push(Number(v)); }); });
    var nt = niceTicks(Math.min.apply(null, vals), Math.max.apply(null, vals), p.yTicks || 4);
    var axis = !!p.axis;
    // [market-data patch] without an axis, scale to the data (a nice-tick floor left an empty band below zero).
    var lo = axis ? Math.min(0, nt.ticks[0]) : Math.min.apply(null, vals);
    var hi = axis ? nt.ticks[nt.ticks.length - 1] : Math.max.apply(null, vals);
    var dec = p.decimals != null ? p.decimals : 1;
    var fmt = function (v) { return formatNumber(v, { format: p.format, decimals: dec }); };
    var tickDec = stepDecimals(nt.step);
    var left = axis ? Math.max.apply(null, nt.ticks.map(function (t) { return textWidth(formatNumber(t, { decimals: tickDec }), 10); })) + 8 : 2;
    var legendH = (p.legend != null ? p.legend : series.length > 1) ? 16 : 0;
    var band = (W - left - 2) / Math.max(1, cats.length);
    var maxChars = Math.max(4, Math.floor(band / 5.6));
    var twoLine = cats.some(function (c) { return String(c).length > maxChars; });
    var top = legendH + (p.valueLabels === false ? 4 : 14);
    var bottom = twoLine ? 30 : 18;
    var negRoom = lo < 0 && p.valueLabels !== false ? 12 : 0;
    var y0 = top, y1 = H - bottom - negRoom;
    var Y = function (v) { return y1 - (v - lo) / (hi - lo || 1) * (y1 - y0); };
    var gap = band * (p.gap != null ? p.gap : 0.3);
    var bw = (band - gap) / Math.max(1, series.length);
    var fill = { subject: 'is-fill-subject', context: 'is-fill-context', compare: 'is-fill-compare', light: 'is-fill-light' };
    var txt = { subject: 'is-text-subject', context: 'rwf-t-strong', compare: 'rwf-t-strong', light: 'rwf-t-strong' };
    return h('svg', { className: cx('rwf-chart', p.className), viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img', 'aria-label': p.label || 'Chart' },
      legendH ? h('g', null, series.map(function (s, i) {
        var role = roleOf(s, i, series.length);
        var x = left + i * 88;
        return h('g', { key: 'lg' + i },
          h('rect', { x: x, y: 2, width: 8, height: 8, className: fill[role] }),
          h('text', { x: x + 12, y: 9.5, className: 'rwf-t-strong' }, s.name));
      })) : null,
      axis ? nt.ticks.map(function (t, i) {
        return h('g', { key: 't' + i },
          h('line', { className: 'rwf-grid', x1: left, x2: W - 2, y1: Y(t), y2: Y(t) }),
          h('text', { x: left - 6, y: Y(t) + 3.5, textAnchor: 'end' }, formatNumber(t, { decimals: tickDec })));
      }) : null,
      cats.map(function (c, ci) {
        var bx = left + ci * band + gap / 2;
        return h('g', { key: 'c' + ci },
          series.map(function (s, si) {
            var v = s.data[ci];
            if (isBlank(v)) return null;
            var role = roleOf(s, si, series.length);
            var yTop = Math.min(Y(v), Y(0)), hgt = Math.abs(Y(v) - Y(0));
            var x = bx + si * bw;
            return h('g', { key: 's' + si },
              h('rect', { x: x + 0.5, width: Math.max(1, bw - 1), y: yTop, height: Math.max(0.5, hgt), className: fill[role] }),
              p.valueLabels === false ? null : h('text', { x: x + bw / 2, y: v >= 0 ? yTop - 3 : yTop + hgt + 10, textAnchor: 'middle', className: txt[role] }, fmt(v)));
          }),
          wrapLabel(c, maxChars).map(function (line, li) {
            // [market-data patch] y1 already leaves negRoom; adding it again put labels below the SVG.
            return h('text', { key: 'xl' + li, x: left + ci * band + band / 2, y: H - bottom + 13 + li * 11, textAnchor: 'middle', className: 'rwf-t-strong' }, line);
          }));
      }),
      h('line', { className: 'rwf-axis', x1: left, x2: W - 2, y1: Y(0), y2: Y(0) }));
  }

  /* ---------- BarChart (horizontal, named categories) ---------- */

  function BarChart(props) {
    var p = props || {};
    var W = p.width || 348;
    var rows = (p.data || []).slice();
    if (p.sort === 'desc') rows.sort(function (a, b) { return b.value - a.value; });
    if (p.sort === 'asc') rows.sort(function (a, b) { return a.value - b.value; });
    var hl = p.highlight == null ? [] : [].concat(p.highlight);
    var dec = p.decimals != null ? p.decimals : 1;
    var fmt = function (v) { return formatNumber(v, { format: p.format, decimals: dec, signed: p.signed }); };
    var rowH = p.rowHeight || 16, barH = Math.round(rowH * 0.56);
    var H = rows.length * rowH + 4;
    var labelW = p.labelWidth || Math.min(W * 0.42, Math.max.apply(null, rows.map(function (r) { return textWidth(r.label, 10); }).concat([20])) + 8);
    var valW = Math.max.apply(null, rows.map(function (r) { return textWidth(fmt(r.value), 10, true); }).concat([10])) + 6;
    var vals = rows.map(function (r) { return Number(r.value); }).concat([0]);
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    // [market-data patch] leave room for the label of a value at zero or above, not only above zero.
    var x0 = labelW + (lo < 0 ? valW : 0), x1 = W - (rows.some(function (r) { return Number(r.value) >= 0; }) ? valW : 2);
    var X = function (v) { return x0 + (v - lo) / (hi - lo || 1) * (x1 - x0); };
    var zero = X(0);
    var base = p.role || 'context';
    return h('svg', { className: cx('rwf-chart', p.className), viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img', 'aria-label': p.label || 'Chart' },
      rows.map(function (r, i) {
        var role = r.role || (hl.indexOf(r.label) >= 0 ? 'subject' : base);
        var y = i * rowH + 2;
        var v = Number(r.value);
        var bx = Math.min(X(v), zero), bw = Math.abs(X(v) - zero);
        var strong = role === 'subject';
        return h('g', { key: i },
          h('text', { x: 0, y: y + rowH / 2 + 3.5, className: strong ? 'rwf-t-strong' : null, style: strong ? null : { fill: 'var(--ink, #312f2a)' } }, r.label),
          h('rect', { x: bx, y: y + (rowH - barH) / 2, width: Math.max(0.5, bw), height: barH, className: 'is-fill-' + role }),
          h('text', { x: v >= 0 ? X(v) + 4 : X(v) - 4, y: y + rowH / 2 + 3.5, textAnchor: v >= 0 ? 'start' : 'end', className: strong ? 'is-text-subject' : 'rwf-t-strong' }, fmt(v)));
      }),
      h('line', { className: 'rwf-axis', x1: zero, x2: zero, y1: 0, y2: H }));
  }

  /* ---------- DataTable ---------- */

  function cellValue(col, row) {
    var v = row[col.key];
    if (col.type === 'delta') return h(Delta, { value: v, format: col.format, decimals: col.decimals, mode: col.mode, polarity: col.polarity, icon: col.icon });
    if (col.type === 'number' || (col.type == null && typeof v === 'number')) return formatNumber(v, col);
    return v == null ? EN_DASH : v;
  }

  function DataTable(props) {
    var p = props || {};
    var cols = p.columns || [];
    var isNum = function (c) { return c.align ? c.align === 'right' : (c.type === 'number' || c.type === 'delta'); };
    var hl = p.highlight;
    return h('table', { className: cx('rwf-table', p.rules === 'dashed' && 'is-dashed', p.className), 'aria-label': p.label },
      p.caption ? h('caption', null, p.caption) : null,
      cols.some(function (c) { return c.width; }) ? h('colgroup', null, cols.map(function (c, i) { return h('col', { key: i, style: c.width ? { width: c.width } : null }); })) : null,
      h('thead', null,
        p.headGroups ? h('tr', null, p.headGroups.map(function (g, i) {
          return h('th', { key: i, colSpan: g.span || 1, className: cx(g.label && 'rwf-th', 'is-num'), style: g.label ? { textAlign: 'center' } : { borderBottom: 0 } }, g.label || '');
        })) : null,
        h('tr', null, cols.map(function (c, i) {
          return h('th', { key: i, scope: 'col', className: cx('rwf-th', isNum(c) && 'is-num', c.band && 'is-band') }, c.label);
        }))),
      h('tbody', null, (p.rows || []).map(function (r, ri) {
        if (r.group != null && Object.keys(r).length === 1) {
          return h('tr', { key: ri, className: 'rwf-group' }, h('td', { colSpan: cols.length }, r.group));
        }
        var on = typeof hl === 'function' ? hl(r, ri) : hl === ri;
        return h('tr', { key: ri, className: on ? 'is-highlight' : null },
          cols.map(function (c, ci) {
            var tag = ci === 0 && p.rowHeaders !== false ? 'th' : 'td';
            return h(tag, { key: ci, scope: tag === 'th' ? 'row' : null, className: cx(isNum(c) && 'is-num', c.band && 'is-band'), style: tag === 'th' ? { fontWeight: on ? 700 : 400 } : null }, cellValue(c, r));
          }));
      }),
      p.total ? h('tr', { className: 'rwf-total' }, cols.map(function (c, ci) {
        return h('td', { key: ci, className: cx(isNum(c) && 'is-num', c.band && 'is-band') }, cellValue(c, p.total));
      })) : null));
  }

  /* ---------- Positioning ---------- */

  function viewText(v, labels) {
    if (v === 0) return labels.neutral;
    return (v > 0 ? '+' : MINUS) + Math.abs(v);
  }
  function Scale(view, prev) {
    return h('span', { className: 'rwf-scale', 'aria-hidden': 'true' }, [-2, -1, 0, 1, 2].map(function (s) {
      return h('span', { key: s, className: cx('rwf-slot', s < 0 ? 'is-under' : s > 0 ? 'is-over' : 'is-neutral', s === view && 'is-now', prev != null && prev !== view && s === prev && 'is-prev') });
    }));
  }

  function Positioning(props) {
    var p = props || {};
    var labels = Object.assign({ under: 'Underweight', neutral: 'Neutral', over: 'Overweight', asset: 'Asset', view: 'Positioning', text: 'Our assessment', from: 'from' }, p.labels || {});
    return h('div', { className: cx('rwf-positioning', p.className) },
      h('div', { className: 'rwf-pos-legend' },
        h('span', { className: 'rwf-pos-key' }, h('span', { className: 'rwf-slot is-under' }), labels.under),
        h('span', { className: 'rwf-pos-key' }, h('span', { className: 'rwf-slot is-neutral' }), labels.neutral),
        h('span', { className: 'rwf-pos-key' }, h('span', { className: 'rwf-slot is-over' }), labels.over),
        h('span', { className: 'rwf-pos-key' }, h('span', { className: 'rwf-slot is-now' }), labels.now || 'Current view'),
        h('span', { className: 'rwf-pos-key' }, h('span', { className: 'rwf-slot is-prev' }), labels.prev || 'Previous view'),
        p.basis ? h('span', null, p.basis) : null),
      h('table', { className: 'rwf-table', 'aria-label': p.label || 'Positioning' },
        h('colgroup', null, h('col', { style: { width: p.assetWidth || '24%' } }), h('col', { style: { width: '96px' } }), h('col')),
        h('thead', null, h('tr', null,
          h('th', { scope: 'col', className: 'rwf-th' }, labels.asset),
          h('th', { scope: 'col', className: 'rwf-th' }, labels.view),
          h('th', { scope: 'col', className: 'rwf-th' }, labels.text))),
        h('tbody', null, (p.groups || []).reduce(function (acc, g, gi) {
          acc.push(h('tr', { key: 'g' + gi, className: 'rwf-group' }, h('td', { colSpan: 3 }, g.name)));
          (g.rows || []).forEach(function (r, ri) {
            var changed = r.prev != null && r.prev !== r.view;
            acc.push(h('tr', { key: gi + '-' + ri },
              h('th', { scope: 'row', style: { fontWeight: 400 } }, r.asset),
              h('td', { className: 'rwf-pos-cell' },
                Scale(r.view, r.prev),
                h('span', { className: 'rwf-pos-value' }, viewText(r.view, labels),
                  changed ? h('span', { className: 'rwf-pos-change' }, ' (' + labels.from + ' ' + viewText(r.prev, labels) + ')') : null),
                h('span', { className: 'rwf-sr' }, (r.view > 0 ? labels.over : r.view < 0 ? labels.under : labels.neutral))),
              h('td', null, r.text)));
          });
          return acc;
        }, []))),
      p.note ? h(SourceNote, { prefix: '' }, p.note) : null);
  }

  /* ---------- Scenarios ---------- */

  function ScenarioSet(props) {
    var p = props || {};
    return h('div', { className: cx('rwf-scenarios', p.className) }, (p.scenarios || []).map(function (s, i) {
      return h('section', { key: i, className: cx('rwf-scenario', s.kind === 'base' && 'is-base') },
        h('div', { className: 'rwf-scenario-head' },
          h('span', { className: 'rwf-label' }, s.label),
          h('span', { className: 'rwf-scenario-tag', 'aria-hidden': 'true' }, s.tag)),
        s.title ? h('h4', { className: 'rwf-scenario-title' }, s.title) : null,
        (s.paras || []).map(function (pa, j) { return h(Para, { key: j, lead: pa.lead }, pa.text); }));
    }));
  }

  /* ---------- Numbered notes ---------- */

  function Notes(props) {
    var p = props || {};
    return h('div', { className: cx('rwf-notes', p.className), style: { '--rwf-cols': p.columns || 3 } }, (p.items || []).map(function (it, i) {
      return h('section', { key: i, className: 'rwf-note' },
        h('h4', { className: 'rwf-note-label' },
          it.n != null || p.numbered !== false ? h('span', { className: 'rwf-note-n' }, pad2(it.n != null ? it.n : i + 1)) : null,
          h('span', null, it.title)),
        typeof it.text === 'string' ? h(Para, null, it.text) : it.text);
    }));
  }

  function Marker(props) {
    var p = props || {};
    return h('span', { className: cx('rwf-marker', p.className), 'aria-hidden': p.label ? null : 'true', 'aria-label': p.label }, p.n);
  }

  /* ---------- Compliance ---------- */

  function RiskWarning(props) {
    var p = props || {};
    var lead = p.lead != null ? p.lead : 'Past performance is not a reliable indicator of future results.';
    return h('p', { className: cx('rwf-warning', p.className) },
      lead ? h('b', null, lead) : null,
      p.forecasts ? ' Forecasts are not a reliable indicator of future performance.' : null,
      p.children ? ' ' : null,
      p.children);
  }

  function Disclosures(props) {
    var p = props || {};
    return h('div', { className: cx('rwf-disclosures-block', p.className) },
      p.intro ? h(Para, null, p.intro) : null,
      p.sources ? h('ul', { className: 'rwf-src-list', style: { marginTop: 12 } }, p.sources.map(function (s, i) {
        return h('li', { key: i }, h('b', null, s.head), ' ', s.text);
      })) : null,
      p.children ? h('div', { className: 'rwf-disclosures' }, p.children) : null);
  }

  var api = {
    Page: Page, Band: Band, Kicker: Kicker, Para: Para, SideBlock: SideBlock, Contents: Contents,
    ChartBlock: ChartBlock, SourceNote: SourceNote, LineChart: LineChart, ColumnChart: ColumnChart, BarChart: BarChart,
    DataTable: DataTable, Num: Num, Delta: Delta, KeyFigure: KeyFigure, Positioning: Positioning,
    ScenarioSet: ScenarioSet, Notes: Notes, Marker: Marker, RiskWarning: RiskWarning, Disclosures: Disclosures,
    formatNumber: formatNumber
  };
  window.RWFinance = api;
})();
