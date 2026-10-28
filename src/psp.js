// Perspective (FINOS, originally J.P. Morgan): engine in a worker, viewer and plugins as custom elements.
// Files are published next to the page under vendor/, so the WebAssembly loads from this origin.
let ready = null;

export function loadPerspective() {
  if (!ready) {
    ready = (async () => {
      const at = (p) => new URL("vendor/" + p, document.baseURI).href;
      const { default: perspective } = await import(at("perspective/cdn/perspective.js"));
      await import(at("perspective-viewer/cdn/perspective-viewer.js"));
      await Promise.all([
        import(at("perspective-viewer-datagrid/cdn/perspective-viewer-datagrid.js")),
        import(at("perspective-viewer-d3fc/cdn/perspective-viewer-d3fc.js")),
      ]);
      await customElements.whenDefined("perspective-viewer");
      const worker = await perspective.worker();
      return { perspective, worker };
    })();
    ready.catch(() => { ready = null; });
  }
  return ready;
}

// Weekly series, this week's values by module, and catalogue coverage live in three tables.
export const SCHEMAS = {
  weekly: { 日期: "date", indicator_id: "string", 指标: "string", unit: "string", grp: "string", 数值: "float", obs_date: "string", method: "string" },
  latest: { 编号: "string", 指标: "string", 数值: "float", 单位: "string", 观察期: "string", 状态: "string", 方式: "string" },
  coverage: { 板块: "string", 方式: "string", 指标数: "integer" },
};

// Replace a minus hyphen with a true minus in the datagrid, after each draw.
export function trueMinus(viewer) {
  const tryHook = () => {
    const dg = viewer.querySelector("perspective-viewer-datagrid");
    const rt = dg && (dg.regular_table || dg.regularTable);
    if (!rt || rt.__cwMinus) return !!(rt && rt.__cwMinus);
    rt.__cwMinus = true;
    rt.addStyleListener(() => {
      for (const td of rt.querySelectorAll("td")) {
        const t = td.textContent;
        if (t && t.charCodeAt(0) === 45 && /^-[\d.,]+/.test(t)) td.textContent = "−" + t.slice(1);
      }
    });
    rt.draw && rt.draw();
    return true;
  };
  if (!tryHook()) setTimeout(tryHook, 400);
}

// Perspective's charts are d3fc inside an open shadow root. Make them read like the rest of the page:
// Chinese dates on the time axis, a true minus sign, no duplicate legend or raw column titles,
// and tick labels that never overlap.
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const SHORT = MONTHS.map((m) => m.slice(0, 3));
function zhTick(t) {
  let m;
  if ((m = MONTHS.indexOf(t)) >= 0) return `${m + 1}月`;
  if ((m = SHORT.indexOf(t)) >= 0) return `${m + 1}月`;
  if (/^\d{4}$/.test(t)) return `${t}年`;
  if ((m = t.match(/^([A-Z][a-z]{2}) (\d{1,2})$/)) && SHORT.includes(m[1])) return `${SHORT.indexOf(m[1]) + 1}月${+m[2]}日`;
  if ((m = t.match(/^[A-Z][a-z]{2} (\d{1,2})$/))) return `${+m[1]}日`;
  if (/^-\d/.test(t)) return "−" + t.slice(1);
  return null;
}
const CHART_CSS = `
  .x-label, .y-label { display: none !important; }
  .legend-container, [class*="legend"] { visibility: hidden !important; pointer-events: none !important; }
  .x-axis text, .y-axis text { font-size: 11px; }
`;
function thin(svg) {
  const box = svg.getBoundingClientRect();
  const items = [...svg.querySelectorAll("g.tick text")].map((t) => {
    t.style.visibility = "";
    const r = t.getBoundingClientRect();
    return { t, l: r.left, r: r.right, year: /年$/.test(t.textContent) && !/月/.test(t.textContent) };
  }).filter((x) => x.r > x.l);
  const kept = [];
  const fits = (x) => x.l >= box.left - 1 && x.r <= box.right + 1 && kept.every((k) => x.r + 8 <= k.l || x.l >= k.r + 8);
  for (const x of items.filter((i) => i.year)) if (fits(x)) kept.push(x);
  for (const x of items.filter((i) => !i.year)) if (fits(x)) kept.push(x);
  for (const x of items) if (!kept.includes(x)) x.t.style.visibility = "hidden";
}
export function polishChart(viewer) {
  const plug = viewer.firstElementChild;
  const sr = plug && plug.shadowRoot;
  if (!sr || plug.localName.indexOf("d3fc") < 0) return;
  if (!sr.querySelector("style[data-cw]")) {
    const st = document.createElement("style");
    st.dataset.cw = "1";
    st.textContent = CHART_CSS;
    sr.append(st);
  }
  const fix = () => {
    for (const t of sr.querySelectorAll(".x-axis text, .y-axis text")) {
      const z = zhTick(t.textContent);
      if (z != null && z !== t.textContent) t.textContent = z;
    }
    const xs = sr.querySelector(".x-axis svg");
    if (xs && plug.localName !== "perspective-viewer-d3fc-xbar") thin(xs);
  };
  fix();
  if (!plug.__cwObs) {
    let queued = false;
    plug.__cwObs = new MutationObserver(() => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => { queued = false; fix(); });
    });
    plug.__cwObs.observe(sr, { subtree: true, childList: true, characterData: true });
  }
}
