// Website build: the same read-only "tools" the MCP connector offers, run in the browser
// against Supabase REST with the reader's own session. Logic mirrors
// supabase/functions/warehouse-mcp/index.ts in the warehouse repository.
import { accessToken, AuthError, onSession, PUBLISHABLE_KEY, SUPABASE_URL } from "./auth.js";

const ID_RE = /^\d{2,3}-\d{3}$/;
const MAX_WEEKLY_ROWS = 5000;
const MAX_LATEST_ROWS = 400;

class DbError extends Error {
  constructor(code, message) { super(message); this.code = code; }
}

const cleanToken = (t) => t.replace(/[,()*:"'\\%]/g, "").trim();
const tidy = (v) => (typeof v === "number" && Number.isFinite(v) ? Number(v.toPrecision(12)) : v);
const byId = (a, b) => {
  const [a1, a2] = String(a).split("-").map(Number);
  const [b1, b2] = String(b).split("-").map(Number);
  return a1 - b1 || a2 - b2 || String(a).localeCompare(String(b));
};
const short = (text, n = 140) => { const s = String(text ?? ""); return s.length > n ? s.slice(0, n) + "…" : s; };
const table = (rows, columns) => ({ columns, rows: rows.map((r) => columns.map((c) => tidy(r[c] ?? null))) });
function rankMatches(rows, tokens) {
  const phrase = tokens.join("");
  const score = (r) => { const name = String(r.name ?? ""); return (r.last_week ? 4 : 0) + (name.includes(phrase) ? 2 : 0) + (name.startsWith(tokens[0]) ? 1 : 0); };
  return [...rows].sort((a, b) => score(b) - score(a) || String(a.name ?? "").length - String(b.name ?? "").length || byId(a.indicator_id, b.indicator_id));
}
function checkIds(ids, max) {
  if (!Array.isArray(ids) || !ids.length) throw new DbError("tool_error", "indicator_ids must be a non-empty list");
  if (ids.length > max) throw new DbError("tool_error", `at most ${max} indicator_ids per call`);
  const out = ids.map((x) => String(x).trim());
  if (out.some((x) => !ID_RE.test(x))) throw new DbError("tool_error", "not indicator IDs");
  return [...new Set(out)];
}

// GET a PostgREST resource, following pages of 1000 rows up to maxRows.
async function rows(path, params, maxRows = 1000) {
  const out = [];
  let offset = 0;
  while (out.length < maxRows) {
    const limit = Math.min(1000, maxRows - out.length + 1);
    const q = new URLSearchParams({ ...params, limit: String(limit), offset: String(offset) });
    const batch = await get(`${SUPABASE_URL}/rest/v1/${path}?${q}`);
    out.push(...batch);
    if (batch.length < limit) return { rows: out.slice(0, maxRows), truncated: out.length > maxRows };
    offset += batch.length;
  }
  return { rows: out.slice(0, maxRows), truncated: true };
}

async function get(url, retried = false) {
  const token = await accessToken();
  let r;
  try {
    r = await fetch(url, { headers: { apikey: PUBLISHABLE_KEY, Authorization: `Bearer ${token}` } });
  } catch {
    throw new DbError("network", "连不上数据库服务器");
  }
  if (r.status === 401 && !retried) {
    await accessToken({ force: true });
    return get(url, true);
  }
  if (!r.ok) throw new DbError(r.status === 401 ? "needs_login" : "tool_error", `数据库请求失败（${r.status}）：${(await r.text()).slice(0, 200)}`);
  return r.json();
}

const TOOLS = {
  async search_indicators(args) {
    const tokens = String(args.query ?? "").split(/\s+/).map(cleanToken).filter(Boolean).slice(0, 6);
    if (!tokens.length) throw new DbError("tool_error", "query is empty");
    const limit = Math.max(1, Math.min(50, Number(args.limit ?? 20) || 20));
    const params = {
      select: "indicator_id,module,name,unit,method,coverage_note,last_week",
      order: "indicator_id",
      and: `(${tokens.map((t) => `or(name.ilike.*${t}*,indicator_id.ilike.*${t}*,module.ilike.*${t}*)`).join(",")})`,
    };
    if (args.module) params.module = `eq.${cleanToken(String(args.module))}`;
    params.method = args.method ? `eq.${cleanToken(String(args.method))}` : "neq.excluded";
    const { rows: found, truncated } = await rows("catalog", params, 300);
    const best = rankMatches(found, tokens).slice(0, limit);
    return {
      matches: truncated ? "300+" : found.length,
      more_available: truncated || found.length > best.length,
      ...table(best.map((r) => ({ ...r, coverage_note: short(r.coverage_note) })), ["indicator_id", "module", "name", "unit", "method", "coverage_note", "last_week"]),
    };
  },
  async list_modules() {
    const { rows: all } = await rows("indicators", { select: "indicator_id,module,method", order: "indicator_id" }, 3000);
    all.sort((a, b) => byId(a.indicator_id, b.indicator_id));
    const by = {};
    for (const r of all) { by[r.module] ??= {}; by[r.module][r.method] = (by[r.module][r.method] ?? 0) + 1; }
    return { modules: Object.entries(by).map(([module, counts]) => ({ module, total: Object.values(counts).reduce((a, b) => a + b, 0), ...counts })) };
  },
  async describe_indicator(args) {
    const [id] = checkIds([args.indicator_id], 1);
    const cols = "indicator_id,module,name,definition,unit,source_freq,weekly_rule,source_desc,limits,source_url,method,formula,coverage_note";
    const [ind, cat] = await Promise.all([
      rows("indicators", { indicator_id: `eq.${id}`, select: cols }, 1),
      rows("catalog", { indicator_id: `eq.${id}`, select: "first_week,last_week,ok_weeks" }, 1),
    ]);
    if (!ind.rows.length) throw new DbError("tool_error", `no indicator ${id}`);
    return { ...ind.rows[0], ...(cat.rows[0] ?? {}) };
  },
  async get_weekly(args) {
    const ids = checkIds(args.indicator_ids, 20);
    const params = { indicator_id: `in.(${ids.join(",")})`, select: "week_cutoff,indicator_id,value,obs_date,status", order: "indicator_id,week_cutoff", status: "eq.ok" };
    const [data, meta] = await Promise.all([
      rows("weekly", params, MAX_WEEKLY_ROWS),
      rows("catalog", { indicator_id: `in.(${ids.join(",")})`, select: "indicator_id,name,unit,method,coverage_note" }, 20),
    ]);
    const indicators = {};
    for (const m of meta.rows) indicators[m.indicator_id] = { name: m.name, unit: m.unit, method: m.method, coverage_note: short(m.coverage_note, 200) };
    data.rows.sort((a, b) => byId(a.indicator_id, b.indicator_id));
    return { indicators, ...table(data.rows, ["week_cutoff", "indicator_id", "value", "obs_date", "status"]), truncated: data.truncated };
  },
  async get_latest(args) {
    if (!args.module) throw new DbError("tool_error", "give module");
    const { rows: found, truncated } = await rows("latest_week", {
      select: "week_cutoff,indicator_id,module,name,unit,value,obs_date,status,method",
      order: "indicator_id",
      module: `eq.${cleanToken(String(args.module))}`,
    }, MAX_LATEST_ROWS);
    found.sort((a, b) => byId(a.indicator_id, b.indicator_id));
    return { week_cutoff: found[0]?.week_cutoff ?? null, ...table(found, ["indicator_id", "module", "name", "unit", "value", "obs_date", "status", "method"]), truncated };
  },
  async data_status() {
    const [week, log, latest] = await Promise.all([
      rows("weekly_values", { select: "week_cutoff", order: "week_cutoff.desc" }, 1),
      rows("fetch_log", { select: "logged_at", order: "logged_at.desc" }, 1),
      rows("latest_week", { select: "status" }, 3000),
    ]);
    const counts = {};
    for (const r of latest.rows) counts[r.status] = (counts[r.status] ?? 0) + 1;
    if (!week.rows.length && !latest.rows.length) throw new DbError("not_reader", "这个账号不在读者名单上");
    return { latest_week: week.rows[0]?.week_cutoff ?? null, last_fetch: log.rows[0]?.logged_at ?? null, latest_week_status_counts: counts };
  },
};

// Signed in: data calls can run.
export const getMcp = () => Promise.resolve({ web: true });

const cache = new Map();
onSession(() => cache.clear()); // never show one account's answers to the next
export async function call(tool, input = {}, { fresh = false } = {}) {
  const key = tool + JSON.stringify(input);
  const hit = cache.get(key);
  if (hit && !fresh && Date.now() - hit.at < 10 * 60 * 1000) return hit.value;
  const fn = TOOLS[tool];
  if (!fn) throw new DbError("tool_error", `unknown tool ${tool}`);
  try {
    const value = await fn(input);
    cache.set(key, { at: Date.now(), value });
    return value;
  } catch (e) {
    if (e instanceof AuthError) throw new DbError(e.code === "network" ? "network" : "needs_login", e.message);
    throw e;
  }
}

export function describeError(e) {
  const code = (e && e.code) || "error";
  switch (code) {
    case "needs_login":
      return { code, title: "登录已过期", text: "请退出后重新登录。" };
    case "not_reader":
      return { code, title: "这个账号还不在读者名单上", text: "把你的邮箱发给管理员，加入名单后刷新这一页。" };
    case "network":
      return { code, title: "连不上数据库", text: "检查网络后点「重试」。", canRetry: true };
    case "tool_error":
      return { code, title: "数据库拒绝了这次查询", text: (e && e.message) || "" };
    default:
      return { code, title: "读取数据时出错", text: (e && e.message) || "稍后重试。", canRetry: true };
  }
}

export const rowsOf = (p) => (p && Array.isArray(p.columns) && Array.isArray(p.rows) ? p.rows.map((cells) => Object.fromEntries(p.columns.map((c, i) => [c, cells[i] ?? null]))) : []);

export async function fetchWeekly(ids) {
  if (!ids.length) return [];
  const p = await call("get_weekly", { indicator_ids: ids });
  const info = (p && p.indicators) || {};
  return rowsOf(p).map((r) => {
    const m = info[r.indicator_id] || {};
    return { week_cutoff: r.week_cutoff, indicator_id: r.indicator_id, name: m.name ?? r.indicator_id, unit: m.unit ?? "", method: m.method ?? "", coverage_note: m.coverage_note ?? "", value: r.value == null ? null : Number(r.value), obs_date: r.obs_date };
  });
}

export async function fetchMeta(ids) {
  const out = {};
  await Promise.all(ids.map(async (id) => {
    try {
      const p = await call("describe_indicator", { indicator_id: id });
      out[id] = { name: p.name || id, unit: p.unit || "", method: p.method || "", coverage_note: p.coverage_note || "" };
    } catch { out[id] = { name: id, unit: "", method: "", coverage_note: "" }; }
  }));
  return out;
}
