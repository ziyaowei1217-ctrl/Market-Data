// Number, date and change formats from the 周报图表样式规范 (Richard Wei Finance).
export const MINUS = "−";
const CHANGE_NAME = /(变动|变化|回报|同比|环比|增速|涨跌|增长)/;
const RATE_NAME = /(收益率|利率|利差|SOFR|EFFR|IORB|YTW|通胀率|OAS)/;
const FLOW_NAME = /(变动|变化|回报|涨跌)/; // series that are already a change: no change-of-a-change
const DAY = 864e5;

export const isChangeSeries = (name) => FLOW_NAME.test(name || "");

export function decimals(unit, name, v) {
  if (unit === "bp" || unit === "百分位" || unit === "张") return 0;
  if (/汇率/.test(name || "")) return 4;
  if (unit === "%" || unit === "百分点") return CHANGE_NAME.test(name || "") ? 1 : 2;
  if (Math.abs(v) >= 1000) return 0;
  return 2;
}

export function num(v, d) {
  if (v == null || !Number.isFinite(+v)) return "–";
  const s = new Intl.NumberFormat("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }).format(+v);
  const t = s.replace(/^-/, MINUS);
  return /^−0(\.0+)?$/.test(t) ? t.slice(1) : t;
}

const suffix = (unit) => {
  if (!unit) return "";
  if (unit === "%") return "%";
  if (unit === "bp") return " bp";
  return " " + unit;
};

export const fmtValue = (v, unit, name) => (v == null || !Number.isFinite(+v) ? "–" : num(v, decimals(unit, name, +v)) + suffix(unit));

// A change: signed, with ▲▼ so colour is never the only cue.
export function fmtChange(v, chgUnit, unit, name) {
  if (v == null || !Number.isFinite(+v)) return { text: "–", dir: 0 };
  const d = chgUnit === "bp" ? 0 : chgUnit === "个百分点" ? (CHANGE_NAME.test(name || "") ? 1 : 2) : decimals(unit, name, +v);
  const body = num(Math.abs(v), d);
  const zero = /^0(\.0+)?$/.test(body.replace(/,/g, ""));
  const dir = zero ? 0 : v > 0 ? 1 : -1;
  const sign = dir > 0 ? "+" : dir < 0 ? MINUS : "";
  const arrow = dir > 0 ? "▲ " : dir < 0 ? "▼ " : "";
  const tail = chgUnit === "个百分点" ? " 个百分点" : suffix(chgUnit);
  return { text: `${arrow}${sign}${body}${tail}`, plain: `${sign}${body}${tail}`, abs: `${body}${tail}`, dir };
}

export const toDate = (s) => (s ? new Date(String(s).slice(0, 10) + "T00:00:00Z") : null);
export const fmtDay = (s) => {
  const d = toDate(s);
  return d && !isNaN(d) ? `${d.getUTCFullYear()}年${d.getUTCMonth() + 1}月${d.getUTCDate()}日` : "–";
};
export const fmtLocal = (iso) => {
  const d = new Date(iso);
  if (!iso || isNaN(d)) return "–";
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${p(d.getHours())}:${p(d.getMinutes())}`;
};
export const isoDay = (d) => d.toISOString().slice(0, 10);

// Latest value and changes for one indicator's weekly rows (sorted or not).
export function summarize(rows) {
  const ok = rows.filter((r) => r.value != null && Number.isFinite(r.value)).sort((a, b) => (a.week_cutoff < b.week_cutoff ? -1 : 1));
  if (!ok.length) return null;
  const t = (s) => Date.parse(String(s).slice(0, 10) + "T00:00:00Z");
  const last = ok[ok.length - 1];
  const name = last.name || "";
  const bp = last.unit === "%" && RATE_NAME.test(name) && !CHANGE_NAME.test(name);
  const scale = bp ? 100 : 1;
  const lowFreq = !!last.obs_date && t(last.week_cutoff) - t(last.obs_date) > 10 * DAY;
  const flow = isChangeSeries(name);
  const prevWeek = ok.find((r) => t(r.week_cutoff) === t(last.week_cutoff) - 7 * DAY) || null;
  let prevRelease = null;
  if (lowFreq) for (let k = ok.length - 2; k >= 0; k--) if (ok[k].obs_date !== last.obs_date) { prevRelease = ok[k]; break; }
  const target = t(last.week_cutoff) - 364 * DAY;
  let ago = null;
  for (const r of ok) {
    const dd = Math.abs(t(r.week_cutoff) - target);
    if (dd <= 21 * DAY && (!ago || dd < Math.abs(t(ago.week_cutoff) - target))) ago = r;
  }
  const chgUnit = bp ? "bp" : last.unit === "%" ? "个百分点" : last.unit;
  const chg1y = ago && (lowFreq || !flow) ? (last.value - ago.value) * scale : null;
  const rate = /(收益率|利率|利差|OAS)/.test(name);
  return {
    last,
    lowFreq,
    flow,
    chgUnit,
    recent: lowFreq ? (prevRelease ? { label: "较上期", v: (last.value - prevRelease.value) * scale } : null) : !flow && prevWeek ? { label: "较上周", v: (last.value - prevWeek.value) * scale } : null,
    year: chg1y == null ? null : { v: chg1y, from: ago.week_cutoff },
    upWord: rate ? "上行" : "上升",
    downWord: rate ? "下行" : "下降",
  };
}

// A title that states the finding, from the highlighted series.
export function conclusion(s) {
  if (!s) return "";
  const { last } = s;
  const level = fmtValue(last.value, last.unit, last.name);
  if (!s.year) return `${last.name}最新 ${level}`;
  const c = fmtChange(s.year.v, s.chgUnit, last.unit, last.name);
  if (c.dir === 0) return `${last.name}最新 ${level}，与一年前持平`;
  return `${last.name}最新 ${level}，较一年前${c.dir > 0 ? s.upWord : s.downWord} ${c.abs}`;
}

export const cleanQuery = (s) => String(s || "").replace(/['"`\\\r\n\t]/g, " ").replace(/\s+/g, " ").trim().slice(0, 40);

export const METHOD_LABEL = { api: "接口", proxy: "代理", manual: "公告", pending: "待接入", excluded: "排除" };
export const STATUS_LABEL = { ok: "正常", stale: "过期", missing_input: "缺原始数据", no_vintage: "缺发布版本", insufficient_history: "历史不足", provisional: "待生效", error: "出错" };
