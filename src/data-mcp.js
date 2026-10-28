// Calls to the viewer's 「金融数据库」 connector through the artifact's mcp capability.
export const SERVER = "金融数据库";
const CACHE = { cache: { staleTime: 15 * 60 * 1000, gcTime: 24 * 60 * 60 * 1000 } };

let mcpPromise = null;
export function getMcp() {
  if (!mcpPromise) mcpPromise = window.claude && typeof window.claude.use === "function" ? window.claude.use("mcp").catch(() => null) : Promise.resolve(null);
  return mcpPromise;
}

// What the viewer can do about each failure; codes from the mcp contract.
export function describeError(e) {
  const code = (e && e.code) || "upstream_error";
  const msg = (e && e.message) || "";
  switch (code) {
    case "needs_reauth":
      return { code, title: "「金融数据库」的连接已过期", text: "到 Claude 的 设置 → 连接器 里重新连接「金融数据库」，再回来刷新这一页。" };
    case "server_not_connected":
    case "server_not_found":
      return { code, title: "还没有接上「金融数据库」", text: "到 Claude 的 设置 → 连接器 里添加名为「金融数据库」的自定义连接器（地址和钥匙见项目里的《数据库使用说明》），再刷新这一页。" };
    case "selection_required":
      return { code, title: "有多个同名的「金融数据库」", text: "在 Claude 弹出的提示里选一个要用的连接器。" };
    case "not_in_manifest":
    case "approval_required":
    case "consent_required":
      return { code, title: "这个页面还没获准读取「金融数据库」", text: "点「允许并加载」，在 Claude 的提示里选择允许。", canAsk: true };
    case "blocked_by_policy":
      return { code, title: "组织策略不允许这个页面使用「金融数据库」", text: "请联系组织管理员。" };
    case "server_unavailable":
      return { code, title: "数据库暂时没有响应", text: "稍后点「重试」。", canRetry: true };
    case "tool_error":
      return { code, title: "数据库拒绝了这次查询", text: msg };
    case "not_granted":
    case "capability_disabled":
    case "capability_removed":
      return { code, title: "这个视图不能读取连接器", text: "在 Claude 里打开这个页面（网页版或桌面版），才能读取「金融数据库」。" };
    default:
      return { code, title: "读取数据时出错", text: msg || "稍后重试。", canRetry: true };
  }
}

const payloadOf = (r) => {
  let p = r && r.payload !== undefined ? r.payload : r;
  if (p && typeof p === "object" && Array.isArray(p.content) && p.payload === undefined && !p.columns && !p.modules && !p.latest_week) {
    const text = p.content.map((c) => (c && c.text) || "").join("");
    try { p = JSON.parse(text); } catch { p = text; }
  }
  if (typeof p === "string") {
    try { p = JSON.parse(p); } catch { const err = new Error(p.slice(0, 300)); err.code = "tool_error"; throw err; }
  }
  return p;
};

export async function call(tool, input, { fresh = false } = {}) {
  const mcp = await getMcp();
  if (!mcp) { const e = new Error("no mcp"); e.code = "not_granted"; throw e; }
  const opts = fresh ? { cache: { staleTime: 0, gcTime: CACHE.cache.gcTime, refresh: true } } : CACHE;
  let r;
  try {
    r = await mcp.callTool(SERVER, tool, input, opts);
  } catch (e) {
    if (e && e.retryable && (e.code === "server_unavailable" || e.code === "upstream_error")) {
      await new Promise((res) => setTimeout(res, Math.min(e.retryAfterMs || 0, 5000) + 600 + Math.random() * 800));
      r = await mcp.callTool(SERVER, tool, input, opts);
    } else throw e;
  }
  return payloadOf(r);
}

export const rowsOf = (p) => (p && Array.isArray(p.columns) && Array.isArray(p.rows) ? p.rows.map((cells) => Object.fromEntries(p.columns.map((c, i) => [c, cells[i] ?? null]))) : []);

export async function fetchWeekly(ids) {
  if (!ids.length) return [];
  const p = await call("get_weekly", { indicator_ids: ids });
  const info = (p && p.indicators) || {};
  return rowsOf(p).map((r) => {
    const m = info[r.indicator_id] || {};
    return {
      week_cutoff: r.week_cutoff,
      indicator_id: r.indicator_id,
      name: m.name ?? r.indicator_id,
      unit: m.unit ?? "",
      method: m.method ?? "",
      coverage_note: m.coverage_note ?? "",
      value: r.value == null ? null : Number(r.value),
      obs_date: r.obs_date,
    };
  });
}

export async function fetchMeta(ids) {
  // Names for ids without weekly rows (pending indicators): one describe each, small and rare.
  const out = {};
  await Promise.all(ids.map(async (id) => {
    try {
      const p = await call("describe_indicator", { indicator_id: id });
      out[id] = { name: p.name || p.indicator?.name || id, unit: p.unit || p.indicator?.unit || "", method: p.method || p.indicator?.method || "", coverage_note: p.coverage_note || p.indicator?.coverage_note || "" };
    } catch { out[id] = { name: id, unit: "", method: "", coverage_note: "" }; }
  }));
  return out;
}
