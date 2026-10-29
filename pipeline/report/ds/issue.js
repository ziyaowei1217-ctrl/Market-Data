/* 市场一周: lays out an issue spec (written by pipeline/report/issue.py) with the Richard Wei
   Finance components. Bands are measured in the browser, packed onto A4 pages, charts grow
   and gaps even out so each page ends on the bottom line (weekly.md, "Filling the page").
   render.py calls window.renderIssue() once the fonts have loaded; it sets window.ISSUE_REPORT. */
window.renderIssue = function () {
  'use strict';
  var F = window.RWFinance, h = React.createElement;
  var BODY = 1042 - 150;          // body-bottom − body-top
  var GAP_MIN = 23, GAP_MAX = 67, GAP_GROWN = 45;
  var spec = window.ISSUE;

  // ---------------------------------------------------------------- blocks
  function chartEl(c, grow) {
    var props = Object.assign({}, c.props);
    if (grow && props.height) props.height = Math.round(props.height + grow);
    if (c.c === 'DataTable') return h(F.DataTable, props);
    return h(F[c.c], props);
  }
  function block(b, i, grow) {
    var key = i;
    switch (b.t) {
      case 'kicker': return h(F.Kicker, { key: key }, b.text);
      case 'heading': return h('h3', { key: key, className: 'rwf-section-title' }, b.text);
      case 'para': return h(F.Para, { key: key, lead: b.lead, small: b.small }, b.text);
      case 'source': return h(F.SourceNote, { key: key, prefix: '' }, b.text);
      case 'risk': return h(F.RiskWarning, { key: key, lead: b.lead }, b.text);
      case 'keyfigs': return h('div', { key: key, className: 'mw-keyfigs' }, b.items.map(function (k, j) {
        return h(F.KeyFigure, { key: j, value: k.value, label: k.label });
      }));
      case 'chart':
        return h('div', { key: key, 'data-chart': b.key, 'data-title': b.title },
          h(F.ChartBlock, { title: b.title, qualifier: b.qualifier },
            chartEl(b.chart, b.grow ? Math.min(grow, b.growMax == null ? grow : b.growMax) : 0),
            b.source ? h('figcaption', null, h(F.SourceNote, { prefix: '' }, b.source)) : null));
      case 'pair':
        return h('div', { key: key, className: 'mw-pair' }, b.blocks.map(function (x, j) { return block(x, j, grow); }));
      case 'group':
        return h('div', { key: key, className: 'mw-group' }, b.blocks.map(function (x, j) { return block(x, j, grow); }));
      case 'disclosures':
        return h(F.Disclosures, { key: key, intro: b.intro, sources: b.sources },
          (b.paras || []).map(function (p, j) { return h('p', { key: j }, p.lead ? h('b', null, p.lead) : null, p.text); }));
      case 'band':
        return h(F.Band, { key: key, layout: b.layout, title: b.title },
          b.cols.map(function (col, j) {
            return h('div', { key: j, className: 'mw-col' }, col.map(function (x, k) { return block(x, k, grow); }));
          }));
      default: throw new Error('unknown block ' + b.t);
    }
  }
  function growable(b) {
    if (b.t === 'chart') return !!b.grow;
    var kids = b.t === 'band' ? [].concat.apply([], b.cols) : (b.blocks || []);
    return kids.some(growable);
  }

  // ---------------------------------------------------------------- measuring
  var probe = document.createElement('div');
  probe.className = 'rwf mw-probe';
  probe.setAttribute('lang', spec.lang || 'zh');
  if (spec.market) probe.setAttribute('data-market', spec.market);
  document.body.appendChild(probe);
  function heightOf(el) {
    ReactDOM.flushSync(function () { probeRoot.render(el); });
    return probe.firstChild ? probe.firstChild.getBoundingClientRect().height : 0;
  }
  var probeRoot = ReactDOM.createRoot(probe);

  // ---------------------------------------------------------------- packing
  function pack(section) {
    var warn = section.warning ? heightOf(h(F.RiskWarning, { lead: section.warning.lead }, section.warning.text)) : 0;
    var pages = [], cur = [], used = 0;
    section.bands.forEach(function (b) {
      var hb = heightOf(block(b, 0, 0));
      var need = used + (cur.length ? GAP_MIN : 0) + hb;
      var reserve = warn ? GAP_MIN + warn : 0;
      if (cur.length && need + reserve > BODY) { pages.push(cur); cur = []; need = hb; }
      cur.push({ spec: b, h: hb });
      used = need;
    });
    if (cur.length) pages.push(cur);
    return pages.map(function (bands) { return fill(bands, warn, section); });
  }

  // Spend spare height: charts grow first (to leave gaps of about 45px), then the gaps between
  // blocks even out between 23 and 67px. Narrative charts never grow past their text (not growable).
  function fill(bands, warn, section) {
    var gaps = bands.length - 1 + (warn ? 1 : 0);
    var used = bands.reduce(function (a, b) { return a + b.h; }, 0) + warn;
    var canGrow = bands.map(function (b) { return growable(b.spec); });
    var n = canGrow.filter(Boolean).length;
    var room = BODY - used - gaps * GAP_GROWN;
    var g = n && room > 0 ? Math.min(section.growMax || 120, room / n) : 0;
    for (var pass = 0; g > 0 && pass < 4; pass++) {
      var total = warn + gaps * GAP_MIN;
      bands.forEach(function (b, i) { b.hg = canGrow[i] ? heightOf(block(b.spec, 0, g)) : b.h; total += b.hg; });
      if (total <= BODY) break;
      g = Math.max(0, g - (total - BODY) / n - 1);
    }
    var grow = canGrow.map(function (c) { return c ? g : 0; });
    if (g > 0) used = warn + bands.reduce(function (a, b, i) { return a + (grow[i] ? b.hg : b.h); }, 0);
    var gap = gaps ? (BODY - used) / gaps : 0;
    return { bands: bands, grow: grow, warn: !!warn, fill: gaps > 0 && gap <= GAP_MAX, gap: gap };
  }

  // ---------------------------------------------------------------- pages
  var plan = [];   // [{section, page}]
  (spec.sections || []).forEach(function (s) {
    pack(s).forEach(function (pg) { plan.push({ section: s, page: pg }); });
  });
  probeRoot.unmount();
  probe.remove();

  var starts = {};
  plan.forEach(function (p, i) {
    var t = p.section.contents || p.section.title;
    if (!starts[t]) starts[t] = [i + 2, i + 2]; else starts[t][1] = i + 2;
  });
  var contents = Object.keys(starts).map(function (t) {
    var r = starts[t];
    return { label: t, pages: r[0] === r[1] ? r[0] : r };
  });

  function coverPage() {
    var c = spec.cover;
    var side = c.side.map(function (s, i) {
      return h(F.SideBlock, { key: i, first: i === 0, title: s.title, items: s.items },
        s.contents ? h(F.Contents, { items: contents, label: s.title }) : null,
        (s.blocks || []).map(function (b, j) { return block(b, j, 0); }));
    });
    return h(F.Page, { key: 'cover', kind: 'cover', page: 1, series: spec.series, date: spec.date, lang: spec.lang,
                       market: spec.market, titleLines: c.titleLines, lede: c.lede, side: side, label: '第 1 页' },
      c.main.map(function (g, i) { return h('div', { key: i, className: 'mw-group' }, g.map(function (b, j) { return block(b, j, 0); })); }));
  }

  var pages = [coverPage()].concat(plan.map(function (p, i) {
    var s = p.section, pg = p.page;
    var kids = pg.bands.map(function (b, j) { return block(b.spec, j, pg.grow[j]); });
    if (pg.warn) kids.push(h(F.RiskWarning, { key: 'w', lead: s.warning.lead }, s.warning.text));
    return h(F.Page, { key: i, page: i + 2, series: spec.series, date: spec.date, section: s.section || s.title, title: s.title,
                       lang: spec.lang, market: spec.market, fill: s.fill === false ? false : pg.fill, label: '第 ' + (i + 2) + ' 页' }, kids);
  }));

  var root = document.getElementById('issue');
  ReactDOM.flushSync(function () { ReactDOM.createRoot(root).render(pages); });

  // ---------------------------------------------------------------- report
  var overflow = [];
  Array.prototype.forEach.call(document.querySelectorAll('.rwf-page'), function (page, i) {
    var limit = page.getBoundingClientRect().top + 1042 + 2;
    Array.prototype.forEach.call(page.querySelectorAll('.rwf-body > *, .rwf-cover-main > *, .rwf-cover-side > *'), function (el) {
      if (el.getBoundingClientRect().bottom > limit) overflow.push({ page: i + 1, text: (el.textContent || '').slice(0, 40) });
    });
  });
  window.ISSUE_REPORT = {
    pages: pages.length,
    charts: Array.prototype.map.call(document.querySelectorAll('[data-chart]'), function (el) { return el.getAttribute('data-chart'); }),
    overflow: overflow,
    plan: plan.map(function (p, i) { return { page: i + 2, section: p.section.title, bands: p.page.bands.length, gap: Math.round(p.page.gap), fill: p.page.fill }; })
  };
};
