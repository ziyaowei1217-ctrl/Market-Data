import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  SaltProviderNext, Button, Text, H1, H2, H3, Label, Input, Dropdown, Option, ComboBox,
  Table, THead, TBody, TR, TH, TD, Tabs, TabBar, TabList, Tab, TabTrigger, TabPanel,
  ToggleButtonGroup, ToggleButton, Banner, BannerContent, BannerActions, Spinner,
  StackLayout, FlexLayout, FormField, FormFieldLabel,
} from "@salt-ds/core";
import { CloseIcon, SearchIcon, RefreshIcon } from "@salt-ds/icons";
import { call, describeError, fetchMeta, fetchWeekly, getMcp, rowsOf } from "./data.js";
import { loadPerspective, polishChart, SCHEMAS, trueMinus } from "./psp.js";
import { noteHealth } from "./health.js";
import { confirmSession, discardSession, getSession, onSession, signIn, signOut } from "./auth.js";
import {
  cleanQuery, conclusion, decimals, fmtChange, fmtDay, fmtLocal, fmtValue, isChangeSeries,
  isoDay, METHOD_LABEL, num, STATUS_LABEL, summarize, toDate,
} from "./format.js";

const DEFAULT_IDS = ["12-003", "12-007"];
const MAX_IDS = 10;
const RANGES = [
  { v: "1Y", label: "1年", days: 365 },
  { v: "3Y", label: "3年", days: 3 * 365 },
  { v: "ALL", label: "全部", days: null },
];
const TABS = ["trend", "week", "coverage"];

// Chart colours from the style guide: one cobalt highlight, dark grey second, light greys after.
const ROLE_COLORS = {
  light: ["#1e3bd6", "#333333", "#8a8a8a", "#b3b3b3", "#6b6b6b", "#c9c9c9", "#575757", "#a0a0a0", "#d4d4d4", "#7a7a7a"],
  dark: ["#8c9cff", "#e0e0e0", "#9a9a9a", "#6e6e6e", "#bdbdbd", "#5a5a5a", "#cfcfcf", "#808080", "#4a4a4a", "#adadad"],
};
const METHOD_COLORS = { 接口: 0, 代理: 1, 公告: 2, 待接入: 3, 排除: 5 };

const store = {
  get(k, d) { try { const v = JSON.parse(localStorage.getItem(k)); return v ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* per-viewer convenience only */ } },
};

function useMode() {
  const get = () => {
    const t = document.documentElement.getAttribute("data-theme");
    if (t === "dark" || t === "light") return t;
    return window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  };
  const [mode, setMode] = useState(get);
  useEffect(() => {
    const mq = window.matchMedia ? matchMedia("(prefers-color-scheme: dark)") : null;
    const on = () => setMode(get());
    mq && mq.addEventListener("change", on);
    const mo = new MutationObserver(on);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => { mq && mq.removeEventListener("change", on); mo.disconnect(); };
  }, []);
  return mode;
}

// Perspective's viewer must not be restored while a previous restore is still running.
function useSerial() {
  const chain = useRef(Promise.resolve());
  return useCallback((job) => {
    chain.current = chain.current.then(job, job).catch(() => {});
    return chain.current;
  }, []);
}

const groupKey = (r) => `${r.unit || ""}|${isChangeSeries(r.name) ? "chg" : "lvl"}`;
const pspTheme = (mode) => (mode === "dark" ? "Pro Dark" : "Pro Light");

function ErrorBanner({ error, onRetry, compact }) {
  if (!error) return null;
  const d = describeError(error);
  return (
    <Banner status={d.code === "tool_error" ? "error" : "warning"} className={compact ? "cw-banner-compact" : undefined}>
      <BannerContent>
        <Text><strong>{d.title}</strong>{d.text ? `。${d.text}` : ""}</Text>
      </BannerContent>
      {(d.canAsk || d.canRetry) && onRetry ? (
        <BannerActions>
          <Button appearance="bordered" sentiment="neutral" onClick={onRetry}>{d.canAsk ? "允许并加载" : "重试"}</Button>
        </BannerActions>
      ) : null}
    </Banner>
  );
}

function Loading({ label }) {
  return (
    <FlexLayout gap={1} align="center" className="cw-loading">
      <Spinner size="small" aria-label={label} />
      <Text color="secondary">{label}</Text>
    </FlexLayout>
  );
}

function Change({ c, label }) {
  if (!c || c.text === "–") return <span className="cw-muted">–</span>;
  return (
    <span className={c.dir > 0 ? "cw-up" : c.dir < 0 ? "cw-down" : "cw-flat"}>
      {label ? <span className="cw-chg-label">{label}</span> : null}
      {c.text}
    </span>
  );
}

function MethodTag({ method }) {
  if (!method) return <span className="cw-muted">–</span>;
  return <span className={`cw-tag cw-tag-${method}`}>{METHOD_LABEL[method] || method}</span>;
}

// ---------- search ----------
function SearchBox({ ids, onAdd, onNotice }) {
  const [q, setQ] = useState("");
  const [opts, setOpts] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const seq = useRef(0);
  useEffect(() => {
    const query = cleanQuery(q);
    if (!query) { setOpts([]); setErr(null); return; }
    const n = ++seq.current;
    const t = setTimeout(async () => {
      setBusy(true);
      try {
        const p = await call("search_indicators", { query, limit: 30 });
        if (n === seq.current) { setOpts(rowsOf(p)); setErr(null); }
      } catch (e) {
        if (n === seq.current) { setOpts([]); setErr(e); }
      } finally {
        if (n === seq.current) setBusy(false);
      }
    }, 280);
    return () => clearTimeout(t);
  }, [q]);

  const pick = (item) => {
    if (!item) return;
    if (!item.last_week) { onNotice(`「${item.name}」暂无数值${item.coverage_note ? "：" + item.coverage_note : ""}`); return; }
    onAdd(item.indicator_id, item.name);
    setQ("");
    setOpts([]);
  };

  return (
    <div className="cw-search">
      <ComboBox
        className="cw-combo"
        placeholder="搜索指标并加入，例如：美国 10年、CPI 同比、高收益 OAS"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        selected={[]}
        onSelectionChange={(e, sel) => pick(sel[sel.length - 1])}
        valueToString={(item) => (item && item.name) || ""}
        startAdornment={<SearchIcon aria-hidden />}
        endAdornment={busy ? <Spinner size="small" aria-label="正在搜索" /> : null}
        aria-label="搜索指标"
      >
        {opts.map((o) => (
          <Option key={o.indicator_id} value={o} disabled={ids.includes(o.indicator_id)}>
            <div className="cw-opt">
              <span className="cw-opt-name">{o.name}</span>
              <span className="cw-opt-meta">
                {o.indicator_id} · {o.module} · {o.unit || "无单位"} · {METHOD_LABEL[o.method] || o.method}
                {ids.includes(o.indicator_id) ? " · 已在列表中" : o.last_week ? ` · 最近 ${fmtDay(o.last_week)}` : " · 暂无数值"}
              </span>
            </div>
          </Option>
        ))}
        {q.trim() && !busy && !opts.length && !err ? <Option value={null} disabled>没有匹配的指标，换个关键词试试</Option> : null}
      </ComboBox>
      {err ? <ErrorBanner error={err} compact /> : null}
    </div>
  );
}

// ---------- watchlist ----------
function Watchlist({ ids, summaries, meta, colorOf, loading, onRemove }) {
  return (
    <div className="cw-table-wrap">
      <Table className="cw-table" divider="tertiary">
        <THead>
          <TR>
            <TH>指标</TH>
            <TH className="cw-num">最新值</TH>
            <TH className="cw-num">近期变化</TH>
            <TH className="cw-num">较一年前</TH>
            <TH className="cw-hide-sm">观察期</TH>
            <TH className="cw-hide-sm">方式</TH>
            <TH><span className="cw-sr">移除</span></TH>
          </TR>
        </THead>
        <TBody>
          {ids.map((id) => {
            const s = summaries[id];
            const m = s ? s.last : meta[id];
            const name = (m && m.name) || id;
            const recent = s && s.recent ? fmtChange(s.recent.v, s.chgUnit, s.last.unit, s.last.name) : null;
            const year = s && s.year ? fmtChange(s.year.v, s.chgUnit, s.last.unit, s.last.name) : null;
            return (
              <TR key={id}>
                <TD>
                  <div className="cw-ind">
                    <span className="cw-swatch" style={{ background: s ? colorOf(id) : "transparent" }} aria-hidden />
                    <div className="cw-ind-text">
                      <span className="cw-ind-name">{name}</span>
                      <span className="cw-ind-id">{id}{m && m.unit ? ` · ${m.unit}` : ""}{s && s.lowFreq ? " · 按月或按季发布" : ""}</span>
                    </div>
                  </div>
                </TD>
                <TD className="cw-num cw-strong">{s ? fmtValue(s.last.value, s.last.unit, s.last.name) : loading ? "…" : "–"}</TD>
                <TD className="cw-num">{s ? <Change c={recent} label={s.recent ? s.recent.label : ""} /> : "–"}</TD>
                <TD className="cw-num">{s ? <Change c={year} /> : "–"}</TD>
                <TD className="cw-hide-sm">{s ? fmtDay(s.last.obs_date) : !loading && meta[id] ? <span className="cw-muted">暂无周度数值</span> : "–"}</TD>
                <TD className="cw-hide-sm"><MethodTag method={m && m.method} /></TD>
                <TD className="cw-act">
                  <Button appearance="transparent" sentiment="neutral" aria-label={`移除 ${name}`} disabled={ids.length === 1} onClick={() => onRemove(id)}>
                    <CloseIcon aria-hidden />
                  </Button>
                </TD>
              </TR>
            );
          })}
        </TBody>
      </Table>
    </div>
  );
}

// ---------- one chart per unit ----------
function ChartCard({ group, psp, start, mode, latestWeek }) {
  const ref = useRef(null);
  const loaded = useRef(false);
  const [err, setErr] = useState(null);
  const d = decimals(group.unit, group.series[0].name, group.series[0].sum ? group.series[0].sum.last.value : 0);
  const sortedNames = useMemo(() => group.series.map((s) => s.name).slice().sort((a, b) => (a < b ? -1 : a > b ? 1 : 0)), [group]);

  const serial = useSerial();
  useEffect(() => {
    const v = ref.current;
    if (!v || !psp) return;
    let live = true;
    serial(async () => {
      if (!live) return;
      try {
        if (!loaded.current) { await v.load(psp.tables.weekly); loaded.current = true; }
        if (!live) return;
        const colors = ROLE_COLORS[mode];
        sortedNames.forEach((n, i) => {
          const role = group.series.findIndex((s) => s.name === n);
          v.style.setProperty(`--d3fc-series-${i + 1}`, colors[role % colors.length]);
        });
        v.style.setProperty("--d3fc-series", colors[0]);
        await v.restore({
          plugin: "Y Line",
          settings: false,
          theme: pspTheme(mode),
          title: null,
          group_by: ["日期"],
          split_by: ["指标"],
          columns: ["数值"],
          aggregates: { 数值: "last" },
          filter: [["grp", "==", group.key], ...(start ? [["日期", ">=", start]] : [])],
          sort: [],
          expressions: {},
          columns_config: { 数值: { number_format: { minimumFractionDigits: 0, maximumFractionDigits: d } } },
        });
        await v.restyleElement();
        polishChart(v);
        setErr(null);
      } catch (e) { if (live) setErr(e); }
    });
    return () => { live = false; };
  }, [psp, group.key, sortedNames.join("|"), group.series.map((s) => s.id).join(","), start, mode, d]);

  const s0 = group.series[0].sum;
  const proxies = group.series.filter((s) => s.method === "proxy" && s.note);
  const sources = [...new Set(group.series.filter((s) => s.method !== "proxy" && s.note).map((s) => s.note))];
  const lowFreq = group.series.filter((s) => s.sum && s.sum.lowFreq);
  const kindWord = group.kind === "chg" ? "变动与回报" : "水平值";
  const firstWeek = group.firstWeek;

  return (
    <section className="cw-card cw-chart-card" aria-label={`${group.unit || "无单位"} ${kindWord}`}>
      <Text styleAs="label" color="secondary" className="cw-overline">{group.unit || "无单位"} · {kindWord}</Text>
      <H3 className="cw-chart-title">{conclusion(s0)}</H3>
      <Text color="secondary" className="cw-period">
        周五截点周度值（{group.unit || "无单位"}），{firstWeek ? fmtDay(firstWeek) : "–"}–{fmtDay(latestWeek)}
      </Text>
      <div className="cw-legend">
        {group.series.map((s, i) => {
          const c = s.sum && s.sum.recent ? fmtChange(s.sum.recent.v, s.sum.chgUnit, s.sum.last.unit, s.sum.last.name) : null;
          return (
            <span className="cw-leg" key={s.id}>
              <span className="cw-leg-line" style={{ background: ROLE_COLORS[mode][i % 10] }} aria-hidden />
              <span>{s.name}</span>
              {s.sum ? <strong>{fmtValue(s.sum.last.value, s.sum.last.unit, s.sum.last.name)}</strong> : null}
              {c ? <Change c={c} label={s.sum.recent.label} /> : null}
            </span>
          );
        })}
      </div>
      {err ? <ErrorBanner error={{ code: "upstream_error", message: "图表没能画出来：" + (err.message || err) }} compact /> : null}
      <perspective-viewer ref={ref} class="cw-viewer cw-viewer-chart"></perspective-viewer>
      <div className="cw-notes">
        {sources.length ? <Text styleAs="label" color="secondary">来源：{sources.join("；")}。截至 {fmtDay(latestWeek)}。</Text> : null}
        {proxies.map((s) => <Text styleAs="label" color="secondary" key={s.id}>{s.name}：{s.note}</Text>)}
        {lowFreq.map((s) => (
          <Text styleAs="label" color="secondary" key={s.id + "-obs"}>
            {s.name}按月或按季发布，周度值沿用最近一次发布；最新一期观察期 {fmtDay(s.sum.last.obs_date)}（记在该期第一天），「较上期」比的是上一次发布。
          </Text>
        ))}
      </div>
    </section>
  );
}

// ---------- this week, by module ----------
function WeekGrid({ psp, module, modules, onModule, rows, loading, error, onRetry, mode, onPick }) {
  const ref = useRef(null);
  const loaded = useRef(false);
  const [filter, setFilter] = useState("");
  const options = modules.filter((m) => m.api + m.proxy + m.manual > 0);
  const serial = useSerial();

  useEffect(() => {
    const v = ref.current;
    if (!v || !psp) return;
    serial(async () => {
      if (!loaded.current) {
        await v.load(psp.tables.latest);
        loaded.current = true;
        v.addEventListener("perspective-click", (e) => {
          const row = e.detail && e.detail.row;
          if (row && row["编号"]) onPick.current(row["编号"], row["指标"], row["状态"]);
        });
      }
      await v.restore({
        plugin: "Datagrid",
        settings: false,
        theme: pspTheme(mode),
        title: null,
        columns: ["编号", "指标", "数值", "单位", "观察期", "状态", "方式"],
        group_by: [],
        split_by: [],
        sort: [],
        expressions: {},
        filter: filter ? [["指标", "contains", filter]] : [],
        columns_config: { 数值: { number_fg_mode: "disabled", number_format: { minimumFractionDigits: 0, maximumFractionDigits: 4 } } },
      });
      trueMinus(v);
    });
  }, [psp, mode, filter]);

  return (
    <StackLayout gap={2}>
      <FlexLayout gap={2} align="end" wrap className="cw-toolbar">
        <div className="cw-field">
          <Label id="module-label">板块</Label>
          <Dropdown
            aria-labelledby="module-label"
            className="cw-dropdown"
            bordered
            value={module}
            selected={[module]}
            onSelectionChange={(e, sel) => sel[0] && onModule(sel[0])}
          >
            {(options.length ? options : [{ module, api: 0, proxy: 0, manual: 0 }]).map((m) => (
              <Option key={m.module} value={m.module}>{m.module}{options.length ? `（${m.api + m.proxy + m.manual} 个有数）` : ""}</Option>
            ))}
          </Dropdown>
        </div>
        <div className="cw-field cw-grow">
          <Label id="filter-label">在本板块内筛选</Label>
          <Input
            aria-labelledby="filter-label"
            bordered
            startAdornment={<SearchIcon aria-hidden />}
            inputProps={{ placeholder: "指标名称里的字，例如：收益率" }}
            value={filter}
            onChange={(e) => setFilter(cleanQuery(e.target.value))}
          />
        </div>
        <Text color="secondary" className="cw-hint">点表格里的一行，把它加入走势分析。月度、季度数据沿用最近一次发布，以「观察期」为准。</Text>
      </FlexLayout>
      <ErrorBanner error={error} onRetry={onRetry} />
      <div className="cw-card cw-grid-card">
        {loading ? <div className="cw-overlay"><Loading label="正在读取本周数值" /></div> : null}
        <perspective-viewer ref={ref} class="cw-viewer cw-viewer-grid"></perspective-viewer>
      </div>
      <Text styleAs="label" color="secondary">{rows.length ? `共 ${num(rows.length, 0)} 个指标；` : ""}表头可排序；右上角按钮可切换成图表或做透视分组。</Text>
    </StackLayout>
  );
}

// ---------- coverage ----------
function Coverage({ psp, modules, mode }) {
  const ref = useRef(null);
  const loaded = useRef(false);
  const totals = useMemo(() => {
    const t = { api: 0, proxy: 0, manual: 0, pending: 0, excluded: 0, total: 0 };
    for (const m of modules) for (const k of Object.keys(t)) t[k] += m[k] || 0;
    return t;
  }, [modules]);

  const serial = useSerial();
  useEffect(() => {
    const v = ref.current;
    if (!v || !psp || !modules.length) return;
    serial(async () => {
      if (!loaded.current) { await v.load(psp.tables.coverage); loaded.current = true; }
      const colors = ROLE_COLORS[mode];
      ["代理", "公告", "待接入", "排除", "接口"].forEach((n, i) => v.style.setProperty(`--d3fc-series-${i + 1}`, colors[METHOD_COLORS[n]]));
      await v.restore({
        plugin: "X Bar",
        settings: false,
        theme: pspTheme(mode),
        title: null,
        group_by: ["板块"],
        split_by: ["方式"],
        columns: ["指标数"],
        aggregates: { 指标数: "sum" },
        sort: [["指标数", "desc"]],
        filter: [],
        expressions: {},
      });
      await v.restyleElement();
      polishChart(v);
    });
  }, [psp, modules, mode]);

  const facts = [
    ["接口", totals.api, "官方或免费接口直取或派生"],
    ["代理", totals.proxy, "替代来源，说明里写明替代品"],
    ["公告", totals.manual, "人工维护的官方公告"],
    ["待接入", totals.pending, "暂无免费来源"],
    ["排除", totals.excluded, "按需求不采集"],
  ];
  return (
    <StackLayout gap={2}>
      <div className="cw-facts-row">
        {facts.map(([k, v, note]) => (
          <div className="cw-fact" key={k}>
            <Text styleAs="label" color="secondary">{k}</Text>
            <Text styleAs="display3" className="cw-fact-num">{num(v, 0)}</Text>
            <Text styleAs="label" color="secondary">{note}</Text>
          </div>
        ))}
      </div>
      <section className="cw-card">
        <Text styleAs="label" color="secondary" className="cw-overline">指标目录 · 采集方式</Text>
        <H3 className="cw-chart-title">
          {totals.total ? `${num(totals.total, 0)} 个指标里 ${num(totals.api + totals.proxy + totals.manual, 0)} 个能算出数值，${num(totals.pending, 0)} 个待接入` : "正在读取目录"}
        </H3>
        <Text color="secondary" className="cw-period">各板块指标数，按采集方式分段</Text>
        <div className="cw-legend">
          {["接口", "代理", "公告", "待接入", "排除"].map((k) => (
            <span className="cw-leg" key={k}>
              <span className="cw-leg-box" style={{ background: ROLE_COLORS[mode][METHOD_COLORS[k]] }} aria-hidden />
              <span>{k}</span>
            </span>
          ))}
        </div>
        <perspective-viewer ref={ref} class="cw-viewer cw-viewer-coverage"></perspective-viewer>
      </section>
    </StackLayout>
  );
}

// ---------- the page ----------
function Shell({ mode, account, onSignOut }) {
  const [mcpState, setMcpState] = useState("checking");
  const [status, setStatus] = useState(null);
  const [statusErr, setStatusErr] = useState(null);
  const [modules, setModules] = useState([]);
  const [psp, setPsp] = useState(null);
  const [pspErr, setPspErr] = useState(null);
  const [tab, setTab] = useState(() => (TABS.includes(location.hash.slice(1)) ? location.hash.slice(1) : "trend"));
  const [ids, setIds] = useState(() => {
    const v = store.get("cw-ids", DEFAULT_IDS);
    return Array.isArray(v) && v.length && v.every((x) => /^\d{2,3}-\d{3}$/.test(x)) ? v.slice(0, MAX_IDS) : DEFAULT_IDS;
  });
  const [range, setRange] = useState(() => (RANGES.some((r) => r.v === store.get("cw-range")) ? store.get("cw-range") : "3Y"));
  const [weekly, setWeekly] = useState([]);
  const [weeklyLoading, setWeeklyLoading] = useState(false);
  const [weeklyErr, setWeeklyErr] = useState(null);
  const [weeklyLoaded, setWeeklyLoaded] = useState(false);
  const [meta, setMeta] = useState({});
  const [module, setModule] = useState(() => store.get("cw-module", "利率信用"));
  const [latestRows, setLatestRows] = useState([]);
  const [latestLoading, setLatestLoading] = useState(false);
  const [latestErr, setLatestErr] = useState(null);
  const [notice, setNotice] = useState("");
  const [reload, setReload] = useState(0);
  const noticeTimer = useRef(null);

  const say = useCallback((msg) => {
    setNotice(msg);
    clearTimeout(noticeTimer.current);
    noticeTimer.current = setTimeout(() => setNotice(""), 4500);
  }, []);

  useEffect(() => { store.set("cw-ids", ids); }, [ids]);
  useEffect(() => { store.set("cw-range", range); }, [range]);
  useEffect(() => { store.set("cw-module", module); }, [module]);
  useEffect(() => {
    const on = () => { const h = location.hash.slice(1); if (TABS.includes(h)) setTab(h); };
    addEventListener("hashchange", on);
    return () => removeEventListener("hashchange", on);
  }, []);

  useEffect(() => { getMcp().then((m) => { setMcpState(m ? "ready" : "absent"); if (!m) noteHealth({ mcp: "absent" }); }); }, []);

  useEffect(() => {
    loadPerspective()
      .then(async ({ worker }) => {
        const tables = {
          weekly: await worker.table(SCHEMAS.weekly),
          latest: await worker.table(SCHEMAS.latest),
          coverage: await worker.table(SCHEMAS.coverage),
        };
        setPsp({ worker, tables });
        noteHealth({ perspective: "ok" });
      })
      .catch((e) => { setPspErr(e); noteHealth({ perspective: "error: " + String((e && e.message) || e).slice(0, 300) }); });
  }, []);

  // Freshness and the catalogue.
  useEffect(() => {
    if (mcpState !== "ready") return;
    let live = true;
    call("data_status", {}, { fresh: reload > 0 })
      .then((p) => { if (live) { setStatus(p); setStatusErr(null); noteHealth({ mcp: "ok", latest_week: p && p.latest_week }); } })
      .catch((e) => { if (live) setStatusErr(e); noteHealth({ mcp: "error: " + ((e && e.code) || "") + " " + String((e && e.message) || "").slice(0, 200) }); });
    call("list_modules", {})
      .then((p) => {
        if (!live) return;
        setModules((p.modules || []).map((m) => ({ module: m.module, total: m.total || 0, api: m.api || 0, proxy: m.proxy || 0, manual: m.manual || 0, pending: m.pending || 0, excluded: m.excluded || 0 })));
      })
      .catch(() => {});
    return () => { live = false; };
  }, [mcpState, reload]);

  // Weekly series for the watchlist.
  useEffect(() => {
    if (mcpState !== "ready") return;
    let live = true;
    setWeeklyLoading(true);
    fetchWeekly(ids)
      .then(async (rows) => {
        if (!live) return;
        setWeekly(rows);
        setWeeklyErr(null);
        setWeeklyLoaded(true);
        const have = new Set(rows.map((r) => r.indicator_id));
        const missing = ids.filter((id) => !have.has(id) && !meta[id]);
        if (missing.length) {
          const m = await fetchMeta(missing);
          if (live) setMeta((old) => ({ ...old, ...m }));
        }
      })
      .catch((e) => live && setWeeklyErr(e))
      .finally(() => live && setWeeklyLoading(false));
    return () => { live = false; };
  }, [mcpState, ids.join(","), reload]);

  useEffect(() => {
    if (!psp) return;
    psp.tables.weekly
      .replace(weekly.map((r) => ({ 日期: r.week_cutoff, indicator_id: r.indicator_id, 指标: r.name, unit: r.unit, grp: groupKey(r), 数值: r.value, obs_date: r.obs_date, method: r.method })))
      .catch(() => {});
  }, [psp, weekly]);

  // This week's values for one module.
  useEffect(() => {
    if (mcpState !== "ready") return;
    let live = true;
    setLatestLoading(true);
    call("get_latest", { module })
      .then((p) => {
        if (!live) return;
        const rows = rowsOf(p).map((r) => ({
          编号: r.indicator_id,
          指标: r.name,
          数值: r.value == null ? null : Number(num(r.value, decimals(r.unit, r.name, Number(r.value))).replace(/,/g, "").replace("−", "-")),
          单位: r.unit || "",
          观察期: r.obs_date || "",
          状态: STATUS_LABEL[r.status] || r.status || "",
          方式: METHOD_LABEL[r.method] || r.method || "",
        }));
        setLatestRows(rows);
        setLatestErr(null);
      })
      .catch((e) => live && setLatestErr(e))
      .finally(() => live && setLatestLoading(false));
    return () => { live = false; };
  }, [mcpState, module, reload]);

  useEffect(() => {
    if (psp) psp.tables.latest.replace(latestRows).catch(() => {});
  }, [psp, latestRows]);

  useEffect(() => {
    if (!psp || !modules.length) return;
    const long = [];
    for (const m of modules) for (const [k, label] of Object.entries(METHOD_LABEL)) if (m[k]) long.push({ 板块: m.module, 方式: label, 指标数: m[k] });
    psp.tables.coverage.replace(long).catch(() => {});
  }, [psp, modules]);

  const addId = useCallback((id, name) => {
    setIds((old) => {
      if (old.includes(id)) { say(`「${name || id}」已经在列表里`); return old; }
      if (old.length >= MAX_IDS) { say(`最多同时看 ${MAX_IDS} 个指标，先移除一个`); return old; }
      say(`已加入：${name || id}`);
      return [...old, id];
    });
  }, [say]);
  const removeId = useCallback((id) => setIds((old) => (old.length > 1 ? old.filter((x) => x !== id) : old)), []);
  const pickFromGrid = useRef(null);
  pickFromGrid.current = (id, name, st) => {
    if (st && st !== STATUS_LABEL.ok) { say(`「${name}」本周没有可用数值（${st}）`); return; }
    addId(id, name);
  };

  // Derived: one summary per indicator, one chart per unit and kind.
  const latestWeek = (status && status.latest_week) || weekly.reduce((m, r) => (r.week_cutoff > m ? r.week_cutoff : m), "");
  const summaries = useMemo(() => {
    const by = {};
    for (const r of weekly) (by[r.indicator_id] ||= []).push(r);
    const out = {};
    for (const [id, rows] of Object.entries(by)) out[id] = summarize(rows);
    return out;
  }, [weekly]);
  const start = useMemo(() => {
    const r = RANGES.find((x) => x.v === range);
    if (!r || !r.days || !latestWeek) return null;
    return isoDay(new Date(toDate(latestWeek).getTime() - r.days * 864e5));
  }, [range, latestWeek]);
  const groups = useMemo(() => {
    const out = new Map();
    for (const id of ids) {
      const s = summaries[id];
      if (!s) continue;
      const key = groupKey(s.last);
      if (!out.has(key)) out.set(key, { key, unit: s.last.unit, kind: key.endsWith("|chg") ? "chg" : "lvl", series: [] });
      out.get(key).series.push({ id, name: s.last.name, method: s.last.method, note: s.last.coverage_note, sum: s });
    }
    for (const g of out.values()) {
      const weeks = weekly.filter((r) => g.series.some((s) => s.id === r.indicator_id) && r.value != null && (!start || r.week_cutoff >= start)).map((r) => r.week_cutoff);
      g.firstWeek = weeks.length ? weeks.reduce((a, b) => (a < b ? a : b)) : null;
    }
    return [...out.values()];
  }, [ids, summaries, weekly, start]);
  const colorOf = useCallback((id) => {
    for (const g of groups) {
      const i = g.series.findIndex((s) => s.id === id);
      if (i >= 0) return ROLE_COLORS[mode][i % 10];
    }
    return "transparent";
  }, [groups, mode]);
  const noData = weeklyLoaded && !weeklyErr && !weeklyLoading ? ids.filter((id) => !summaries[id]) : [];

  const counts = status && status.latest_week_status_counts ? status.latest_week_status_counts : null;
  const computed = counts ? Object.values(counts).reduce((a, b) => a + b, 0) : null;
  const pageError = mcpState === "ready" && statusErr && weeklyErr && latestErr && (statusErr.code || "") === (weeklyErr.code || "") ? statusErr : null;
  const retry = () => setReload((n) => n + 1);

  return (
    <div className="cw-page">
      <header className="cw-head">
        <div className="cw-brand">
          <Text styleAs="label" color="secondary" className="cw-eyebrow">Capital Weekly · 周报数据库</Text>
          <H1 className="cw-title">资本市场周报数据台</H1>
        </div>
        <dl className="cw-facts" aria-label="数据新鲜度">
          <div><dt>数据截至</dt><dd>{status ? `${fmtDay(status.latest_week)}（周五）` : "…"}</dd></div>
          <div><dt>本周有值</dt><dd>{counts ? `${num(counts.ok || 0, 0)} / ${num(computed, 0)}` : "…"}</dd></div>
          <div><dt>最近抓取</dt><dd>{status ? fmtLocal(status.last_fetch) : "…"}</dd></div>
          {account ? <div><dt>账号</dt><dd className="cw-account">{account}</dd></div> : null}
          <div className="cw-refresh">
            <Button appearance="transparent" sentiment="neutral" onClick={retry} aria-label="重新读取数据">
              <RefreshIcon aria-hidden />
            </Button>
            {onSignOut ? <Button appearance="bordered" sentiment="neutral" onClick={onSignOut}>退出</Button> : null}
          </div>
        </dl>
      </header>

      {mcpState === "absent" ? (
        <Banner status="warning">
          <BannerContent>
            <Text><strong>这个页面要在 Claude 里打开才能读取数据库。</strong>用 Claude 网页版或桌面版打开它，并在 设置 → 连接器 里接上「金融数据库」。</Text>
          </BannerContent>
        </Banner>
      ) : null}
      {pageError ? <ErrorBanner error={pageError} onRetry={retry} /> : null}
      {!pageError && statusErr && ["not_reader", "needs_login"].includes(statusErr.code) ? <ErrorBanner error={statusErr} /> : null}
      {pspErr ? (
        <Banner status="error">
          <BannerContent>
            <Text><strong>表格和图表组件没能加载。</strong>{String(pspErr.message || pspErr)}。刷新页面再试一次。</Text>
          </BannerContent>
        </Banner>
      ) : null}

      <Tabs value={tab} onChange={(e, v) => { setTab(v); try { history.replaceState(null, "", "#" + v); } catch { location.hash = v; } }}>
        <TabBar divider>
          <TabList aria-label="视图">
            <Tab value="trend"><TabTrigger>走势分析</TabTrigger></Tab>
            <Tab value="week"><TabTrigger>本周一览</TabTrigger></Tab>
            <Tab value="coverage"><TabTrigger>覆盖情况</TabTrigger></Tab>
          </TabList>
        </TabBar>

        <TabPanel value="trend" className="cw-panel">
          <StackLayout gap={2}>
            <FlexLayout gap={2} align="end" justify="space-between" wrap className="cw-toolbar">
              <SearchBox ids={ids} onAdd={addId} onNotice={say} />
              <FlexLayout gap={1} align="center" className="cw-range">
                <Label id="range-label">区间</Label>
                <ToggleButtonGroup aria-labelledby="range-label" value={range} onChange={(e) => setRange(e.currentTarget.value)}>
                  {RANGES.map((r) => <ToggleButton key={r.v} value={r.v}>{r.label}</ToggleButton>)}
                </ToggleButtonGroup>
                <Button appearance="transparent" sentiment="neutral" onClick={() => { setIds(DEFAULT_IDS); setRange("3Y"); say("已恢复默认"); }}>恢复默认</Button>
              </FlexLayout>
            </FlexLayout>
            {!pageError ? <ErrorBanner error={weeklyErr} onRetry={retry} /> : null}
            <Watchlist ids={ids} summaries={summaries} meta={meta} colorOf={colorOf} loading={weeklyLoading} onRemove={removeId} />
            {noData.length ? (
              <Text color="secondary" className="cw-hint">
                {noData.map((id) => (meta[id] && meta[id].name) || id).join("、")}暂无周度数值{noData.length === 1 && meta[noData[0]] && meta[noData[0]].coverage_note ? `：${meta[noData[0]].coverage_note}` : "（多为尚未接入的数据源）"}。
              </Text>
            ) : null}
            {mcpState === "ready" && weeklyLoading && !weekly.length ? <Loading label="正在读取周度序列" /> : null}
            {!psp && !pspErr ? <Loading label="正在加载 Perspective" /> : null}
            <div className="cw-charts">
              {groups.map((g) => <ChartCard key={g.key} group={g} psp={psp} start={start} mode={mode} latestWeek={latestWeek} />)}
            </div>
          </StackLayout>
        </TabPanel>

        <TabPanel value="week" className="cw-panel">
          <WeekGrid
            psp={psp}
            module={module}
            modules={modules}
            onModule={setModule}
            rows={latestRows}
            loading={latestLoading}
            error={pageError ? null : latestErr}
            onRetry={retry}
            mode={mode}
            onPick={pickFromGrid}
          />
        </TabPanel>

        <TabPanel value="coverage" className="cw-panel">
          <Coverage psp={psp} modules={modules} mode={mode} />
        </TabPanel>
      </Tabs>

      <footer className="cw-foot">
        <Text styleAs="label" color="secondary">方式：接口＝官方或免费接口；代理＝替代来源（说明里写明替代品，引用时注明）；公告＝人工维护的官方公告；待接入＝暂无免费来源，没有数值。图里只画状态正常的周度值，缺口留空，不插值。</Text>
        <Text styleAs="label" color="secondary">MSCI、ISM、S&amp;P Global 等数据仅供名单内同学学习使用，不要导出整表转给名单外的人。界面用 J.P. Morgan 开源的 Salt 设计系统，表格和图表用 FINOS Perspective（原 J.P. Morgan 开源）。</Text>
      </footer>

      <div className="cw-toast" role="status" aria-live="polite" hidden={!notice}>{notice}</div>
    </div>
  );
}

// ---------- website sign-in ----------
function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) { setErr("请填写邮箱和密码。"); return; }
    setBusy(true);
    setErr("");
    try {
      await signIn(email, password);
      try {
        await call("data_status", {}, { fresh: true });
        confirmSession();
      } catch (x) {
        await discardSession();
        setErr(x.code === "not_reader" ? "这个账号还不在读者名单上。把你的邮箱发给管理员，加入名单后再登录。" : x.message || "登录后读取数据失败。");
      }
    } catch (x) {
      setErr(x.message || "登录失败。");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="cw-login">
      <div className="cw-login-card">
        <Text styleAs="label" color="secondary" className="cw-eyebrow">Capital Weekly · 周报数据库</Text>
        <H1 className="cw-title">资本市场周报数据台</H1>
        <Text color="secondary">用读者名单上的邮箱和密码登录。账号由管理员开通，忘记密码也请找管理员重置。</Text>
        <form className="cw-login-form" onSubmit={submit} noValidate>
          <FormField>
            <FormFieldLabel>邮箱</FormFieldLabel>
            <Input bordered value={email} onChange={(e) => setEmail(e.target.value)} inputProps={{ id: "email", name: "email", type: "email", autoComplete: "username", inputMode: "email" }} />
          </FormField>
          <FormField>
            <FormFieldLabel>密码</FormFieldLabel>
            <Input bordered value={password} onChange={(e) => setPassword(e.target.value)} inputProps={{ id: "password", name: "password", type: "password", autoComplete: "current-password" }} />
          </FormField>
          {err ? (
            <Banner status="error">
              <BannerContent><Text>{err}</Text></BannerContent>
            </Banner>
          ) : null}
          <Button type="submit" sentiment="accented" appearance="solid" disabled={busy}>{busy ? "正在登录…" : "登录"}</Button>
        </form>
        <Text styleAs="label" color="secondary">MSCI、ISM、S&amp;P Global 等数据仅供名单内同学学习使用。</Text>
      </div>
    </div>
  );
}

function AuthGate({ mode }) {
  const [session, setSession] = useState(getSession);
  useEffect(() => onSession(setSession), []);
  if (!session) return <Login />;
  return <Shell mode={mode} account={session.email} onSignOut={() => signOut()} />;
}

function App() {
  const mode = useMode();
  return (
    <SaltProviderNext mode={mode} accent="blue" corner="sharp" headingFont="Open Sans" actionFont="Open Sans" density="medium" applyClassesTo="root">
      {__WEB__ ? <AuthGate mode={mode} /> : <Shell mode={mode} />}
    </SaltProviderNext>
  );
}

createRoot(document.getElementById("app")).render(<App />);
