// Read-only MCP server for the Capital Weekly warehouse (资本市场周报数据库).
//
// Transport: MCP Streamable HTTP, stateless; every POST carries one JSON-RPC message and
// gets a JSON response (no SSE stream). Access: a personal reader key, passed as
// `?key=cw_...` in the URL or as `Authorization: Bearer cw_...`. Keys are issued by the
// owner with `select private.issue_reader_key('email', 'label')` and stored hashed in
// public.reader_keys; removing the email from public.readers revokes them.
//
// Tools are curated (search / describe / weekly / latest / raw series / status); there is
// no free-form SQL. No external dependencies: fetch + WebCrypto only, so the same file runs
// on Supabase Edge Functions (Deno) and under Node for tests.

export type Env = { supabaseUrl: string; secretKey: string };
type Json = any;

const SERVER_INFO = { name: "capital-weekly-warehouse", version: "1.1.0" };
const PROTOCOL_VERSIONS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"];
const MAX_WEEKLY_ROWS = 5000;
const MAX_SERIES_ROWS = 6000;
const MAX_LATEST_ROWS = 400;

const INSTRUCTIONS = `资本市场周报数据库（只读）。1959 个指标来自《全球资管周报｜数据采集清单》，每周六更新，周度截点为周五（week_cutoff）。
用法：先 search_indicators 用中文关键词找指标（如 "美国10年国债"、"CPI"、"PMI"、"S&P 500"），不要猜 ID；再 get_weekly / get_latest 取数，get_series 取原始频率序列。
- method：api = 官方/免费接口；proxy = 替代来源（coverage_note 以「代理：」开头写明替代品，引用或画图时必须注明）；manual = 人工维护的官方公告（如选举日期，数值写成 YYYYMMDD），有值时可用；pending / excluded 没有数值，告诉用户 coverage_note 里的原因，不要拿相近指标冒充。
- status：只有 ok 的值可直接使用；stale 停更或过期，missing_input 原始缺失或尚未发布，insufficient_history 历史不够，no_vintage 缺少发布版本，provisional 议息结果尚未生效。
- obs_date 是实际观察期：月度、季度数据在周度表里沿用最近一次发布值，要写明。
- 画图：同一张图只放同一单位；缺口留空，不插值、不填 0；图注写来源与截至日期。
- MSCI、ISM、S&P Global 等数据仅供读者名单内部学习使用，不要导出整表转给名单外的人。
- weekly_report：本库每周自动出的《市场一周》PDF 与单图 PNG 的一小时下载链接；链接同样只在读者名单内使用。`;

// ----------------------------------------------------------------------------- tools

const TOOLS = [
  {
    name: "search_indicators",
    description:
      "Search the indicator catalog (names are in Chinese). Every keyword must match the indicator name, ID or module. Returns indicator_id, module, name, unit, method, a short coverage note and the latest week with a value. Indicators excluded on request are left out unless method = excluded.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Keywords separated by spaces, e.g. \"美国 10年 国债\", \"CPI 同比\", \"PMI\", \"12-007\"" },
        module: { type: "string", description: "Optional exact module name, e.g. 利率信用 (see list_modules)" },
        method: { type: "string", enum: ["api", "proxy", "manual", "pending", "excluded"], description: "Optional collection method filter" },
        limit: { type: "integer", minimum: 1, maximum: 50, default: 20 },
      },
      required: ["query"],
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: "list_modules",
    description: "List the 44 catalog modules with indicator counts by collection method.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: "describe_indicator",
    description:
      "Full definition of one indicator: definition, unit, frequency, weekly rule, source, formula over raw series, coverage note, history range and its latest value.",
    inputSchema: {
      type: "object",
      properties: { indicator_id: { type: "string", description: "e.g. 12-007" } },
      required: ["indicator_id"],
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: "get_weekly",
    description:
      "Weekly values (Friday cut-offs, history from 2021-10) for up to 20 indicators, as columns/rows. By default only status = ok rows are returned. Use this for weekly charts and tables.",
    inputSchema: {
      type: "object",
      properties: {
        indicator_ids: { type: "array", items: { type: "string" }, minItems: 1, maxItems: 20, description: "e.g. [\"12-003\", \"12-007\"]" },
        start: { type: "string", description: "First week_cutoff, YYYY-MM-DD (optional)" },
        end: { type: "string", description: "Last week_cutoff, YYYY-MM-DD (optional)" },
        include_all_status: { type: "boolean", default: false, description: "Also return rows whose status is not ok (value may be null)" },
      },
      required: ["indicator_ids"],
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: "get_latest",
    description:
      "The most recent week's values, for one module or a list of indicators (at least one of the two). Includes status and obs_date.",
    inputSchema: {
      type: "object",
      properties: {
        module: { type: "string", description: "Exact module name, e.g. 利率信用" },
        indicator_ids: { type: "array", items: { type: "string" }, maxItems: 100 },
      },
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: "get_series",
    description:
      "A raw source series at its native frequency (daily/monthly/...), latest version of each observation, e.g. FRED:DGS10. Series keys appear in describe_indicator's formula inside {braces}.",
    inputSchema: {
      type: "object",
      properties: {
        series_key: { type: "string", description: "e.g. FRED:DGS10, YAHOO:AGG:TR, NBS:cpi_yoy" },
        start: { type: "string", description: "YYYY-MM-DD (optional)" },
        end: { type: "string", description: "YYYY-MM-DD (optional)" },
      },
      required: ["series_key"],
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: "data_status",
    description: "Freshness of the database: latest week, last fetch time, status counts for the latest week, and source series with problems.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: "weekly_report",
    description:
      "The 市场一周 weekly issue drawn from this database: one-hour download links to the PDF and to each chart as a PNG, with the cutoff, chart list and series notes (proxies, earlier observation dates). Latest issue by default.",
    inputSchema: {
      type: "object",
      properties: { week: { type: "string", description: "Friday cutoff YYYY-MM-DD (optional; default the latest issue)" } },
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
];

const REPORT_LINK_SECONDS = 3600;

class ToolError extends Error {}

const ID_RE = /^\d{2,3}-\d{3}$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function checkIds(ids: Json, max: number): string[] {
  if (!Array.isArray(ids) || ids.length === 0) throw new ToolError("indicator_ids must be a non-empty list");
  if (ids.length > max) throw new ToolError(`at most ${max} indicator_ids per call`);
  const out = ids.map((x) => String(x).trim());
  const bad = out.filter((x) => !ID_RE.test(x));
  if (bad.length) throw new ToolError(`not indicator IDs: ${bad.join(", ")} (format 12-007; use search_indicators)`);
  return [...new Set(out)];
}

function checkDate(value: Json, name: string): string | undefined {
  if (value === undefined || value === null || value === "") return undefined;
  if (typeof value !== "string" || !DATE_RE.test(value)) throw new ToolError(`${name} must be YYYY-MM-DD`);
  return value;
}

/** Strip characters that have meaning in PostgREST filter syntax. */
function cleanToken(t: string): string {
  return t.replace(/[,()*:"'\\%]/g, "").trim();
}

function dateRange(column: string, start?: string, end?: string): Record<string, string> {
  if (start && end) return { and: `(${column}.gte.${start},${column}.lte.${end})` };
  if (start) return { [column]: `gte.${start}` };
  if (end) return { [column]: `lte.${end}` };
  return {};
}

// ----------------------------------------------------------------------------- data access

export class Warehouse {
  env: Env;
  fetchImpl: typeof fetch;

  constructor(env: Env, fetchImpl: typeof fetch) {
    this.env = env;
    this.fetchImpl = fetchImpl;
  }

  headers(): Record<string, string> {
    const k = this.env.secretKey;
    // New secret keys go on apikey only; legacy service_role JWTs also as a bearer token.
    return k.startsWith("sb_secret_") ? { apikey: k } : { apikey: k, Authorization: `Bearer ${k}` };
  }

  /** GET a PostgREST resource, following pages of 1000 rows up to maxRows. */
  async rows(path: string, params: Record<string, string>, maxRows = 1000): Promise<{ rows: Json[]; truncated: boolean }> {
    const out: Json[] = [];
    let offset = 0;
    while (out.length < maxRows) {
      const limit = Math.min(1000, maxRows - out.length + 1);
      const q = new URLSearchParams({ ...params, limit: String(limit), offset: String(offset) });
      const r = await this.fetchImpl(`${this.env.supabaseUrl}/rest/v1/${path}?${q}`, { headers: this.headers() });
      if (!r.ok) throw new Error(`database request failed (${r.status}): ${(await r.text()).slice(0, 200)}`);
      const batch = await r.json();
      out.push(...batch);
      if (batch.length < limit) return { rows: out.slice(0, maxRows), truncated: out.length > maxRows };
      offset += batch.length;
    }
    return { rows: out.slice(0, maxRows), truncated: true };
  }

  /** A Storage API request with the service key (the reports bucket is private). */
  async storage(path: string, init: RequestInit = {}): Promise<Response> {
    return this.fetchImpl(`${this.env.supabaseUrl}/storage/v1/${path}`, {
      ...init,
      headers: { ...this.headers(), ...((init.headers as Record<string, string>) ?? {}) },
    });
  }

  async readerForKey(key: string): Promise<string | null> {
    if (!/^cw_[0-9a-f]{48}$/.test(key)) return null;
    const hash = await sha256Hex(key);
    const { rows } = await this.rows("reader_keys", { key_hash: `eq.${hash}`, select: "email" }, 1);
    if (!rows.length) return null;
    // best effort; failure to record usage must not block the request
    try {
      await this.fetchImpl(`${this.env.supabaseUrl}/rest/v1/reader_keys?key_hash=eq.${hash}`, {
        method: "PATCH",
        headers: { ...this.headers(), "Content-Type": "application/json", Prefer: "return=minimal" },
        body: JSON.stringify({ last_used_at: new Date().toISOString() }),
      });
    } catch (_) { /* ignore */ }
    return rows[0].email;
  }
}

export async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Trim binary floating-point noise (4.960000000000001 -> 4.96) without losing real precision. */
function tidy(v: Json): Json {
  return typeof v === "number" && Number.isFinite(v) ? Number(v.toPrecision(12)) : v;
}

/** Numeric order for IDs: 12-007 < 112-301 (text order would put 112 first). */
function byId(a: Json, b: Json): number {
  const [a1, a2] = String(a).split("-").map(Number);
  const [b1, b2] = String(b).split("-").map(Number);
  return a1 - b1 || a2 - b2 || String(a).localeCompare(String(b));
}

/** Search order: indicators with data first, the whole phrase in the name, shortest (plainest) names, then ID. */
function rankMatches(rows: Json[], tokens: string[]): Json[] {
  const phrase = tokens.join("");
  const score = (r: Json) => {
    const name = String(r.name ?? "");
    return (r.last_week ? 4 : 0) + (name.includes(phrase) ? 2 : 0) + (name.startsWith(tokens[0]) ? 1 : 0);
  };
  return [...rows].sort((a, b) =>
    score(b) - score(a) || String(a.name ?? "").length - String(b.name ?? "").length || byId(a.indicator_id, b.indicator_id));
}

function table(rows: Json[], columns: string[]) {
  return { columns, rows: rows.map((r) => columns.map((c) => tidy(r[c] ?? null))) };
}

function short(text: Json, n = 140): string {
  const s = String(text ?? "");
  return s.length > n ? s.slice(0, n) + "…" : s;
}

// ----------------------------------------------------------------------------- tool handlers

export async function callTool(w: Warehouse, name: string, args: Json): Promise<Json> {
  args = args ?? {};
  switch (name) {
    case "search_indicators": {
      const tokens = String(args.query ?? "").split(/\s+/).map(cleanToken).filter(Boolean).slice(0, 6);
      if (!tokens.length) throw new ToolError("query is empty");
      const limit = Math.max(1, Math.min(50, Number(args.limit ?? 20) || 20));
      const params: Record<string, string> = {
        select: "indicator_id,module,name,unit,method,coverage_note,last_week",
        order: "indicator_id",
        and: `(${tokens.map((t) => `or(name.ilike.*${t}*,indicator_id.ilike.*${t}*,module.ilike.*${t}*)`).join(",")})`,
      };
      if (args.module) params.module = `eq.${cleanToken(String(args.module))}`;
      // excluded = boards dropped on request; only shown when asked for by name
      params.method = args.method ? `eq.${cleanToken(String(args.method))}` : "neq.excluded";
      // fetch a wide candidate set, then rank here: PostgREST can only sort by column
      const { rows, truncated } = await w.rows("catalog", params, 300);
      const best = rankMatches(rows, tokens).slice(0, limit);
      return {
        matches: truncated ? "300+" : rows.length,
        more_available: truncated || rows.length > best.length,
        ...table(best.map((r) => ({ ...r, coverage_note: short(r.coverage_note) })),
          ["indicator_id", "module", "name", "unit", "method", "coverage_note", "last_week"]),
      };
    }
    case "list_modules": {
      const { rows } = await w.rows("indicators", { select: "indicator_id,module,method", order: "indicator_id" }, 3000);
      rows.sort((a, b) => byId(a.indicator_id, b.indicator_id)); // modules in catalog order
      const by: Record<string, Record<string, number>> = {};
      for (const r of rows) {
        by[r.module] ??= {};
        by[r.module][r.method] = (by[r.module][r.method] ?? 0) + 1;
      }
      return {
        modules: Object.entries(by).map(([module, counts]) => ({
          module, total: Object.values(counts).reduce((a, b) => a + b, 0), ...counts,
        })),
      };
    }
    case "describe_indicator": {
      const [id] = checkIds([args.indicator_id], 1);
      const cols = "indicator_id,module,name,definition,unit,source_freq,weekly_rule,source_desc,limits,source_url,method,formula,coverage_note";
      const [ind, cat, latest] = await Promise.all([
        w.rows("indicators", { indicator_id: `eq.${id}`, select: cols }, 1),
        w.rows("catalog", { indicator_id: `eq.${id}`, select: "first_week,last_week,ok_weeks" }, 1),
        w.rows("latest_week", { indicator_id: `eq.${id}`, select: "week_cutoff,value,obs_date,status" }, 1),
      ]);
      if (!ind.rows.length) throw new ToolError(`no indicator ${id}`);
      const last = latest.rows[0];
      return { ...ind.rows[0], ...(cat.rows[0] ?? {}), latest: last ? { ...last, value: tidy(last.value) } : null };
    }
    case "get_weekly": {
      const ids = checkIds(args.indicator_ids, 20);
      const start = checkDate(args.start, "start");
      const end = checkDate(args.end, "end");
      const params: Record<string, string> = {
        indicator_id: `in.(${ids.join(",")})`,
        select: "week_cutoff,indicator_id,value,obs_date,status",
        order: "indicator_id,week_cutoff",
        ...dateRange("week_cutoff", start, end),
      };
      if (!args.include_all_status) params.status = "eq.ok";
      const [data, meta] = await Promise.all([
        w.rows("weekly", params, MAX_WEEKLY_ROWS),
        w.rows("catalog", { indicator_id: `in.(${ids.join(",")})`, select: "indicator_id,name,unit,method,coverage_note" }, 20),
      ]);
      const indicators: Record<string, Json> = {};
      for (const m of meta.rows) {
        indicators[m.indicator_id] = { name: m.name, unit: m.unit, method: m.method, coverage_note: short(m.coverage_note, 200) };
      }
      const missing = ids.filter((i) => !indicators[i]);
      data.rows.sort((a, b) => byId(a.indicator_id, b.indicator_id)); // stable: weeks stay in order
      return {
        indicators,
        ...(missing.length ? { unknown_ids: missing } : {}),
        ...table(data.rows, ["week_cutoff", "indicator_id", "value", "obs_date", "status"]),
        truncated: data.truncated,
        ...(data.truncated ? { note: `limited to ${MAX_WEEKLY_ROWS} rows; narrow the date range or the indicator list` } : {}),
      };
    }
    case "get_latest": {
      const params: Record<string, string> = {
        select: "week_cutoff,indicator_id,module,name,unit,value,obs_date,status,method",
        order: "indicator_id",
      };
      if (args.indicator_ids?.length) params.indicator_id = `in.(${checkIds(args.indicator_ids, 100).join(",")})`;
      else if (args.module) params.module = `eq.${cleanToken(String(args.module))}`;
      else throw new ToolError("give module or indicator_ids (use list_modules / search_indicators)");
      const { rows, truncated } = await w.rows("latest_week", params, MAX_LATEST_ROWS);
      rows.sort((a, b) => byId(a.indicator_id, b.indicator_id));
      return {
        week_cutoff: rows[0]?.week_cutoff ?? null,
        ...table(rows, ["indicator_id", "module", "name", "unit", "value", "obs_date", "status", "method"]),
        truncated,
      };
    }
    case "get_series": {
      const key = String(args.series_key ?? "").trim();
      if (!/^[A-Z][A-Z0-9_]*:[^()]{1,160}$/.test(key)) throw new ToolError("series_key looks like PROVIDER:CODE, e.g. FRED:DGS10");
      const start = checkDate(args.start, "start");
      const end = checkDate(args.end, "end");
      const [data, info] = await Promise.all([
        w.rows("obs_latest", { series_key: `eq.${key}`, select: "obs_date,value,realtime_start", order: "obs_date", ...dateRange("obs_date", start, end) }, MAX_SERIES_ROWS),
        w.rows("series", { series_key: `eq.${key}`, select: "series_key,provider,title,frequency,unit,source_url,last_status,last_message" }, 1),
      ]);
      if (!info.rows.length) throw new ToolError(`no series ${key}`);
      return { series: info.rows[0], ...table(data.rows, ["obs_date", "value", "realtime_start"]), truncated: data.truncated };
    }
    case "data_status": {
      const [week, fetchLog, latest, series] = await Promise.all([
        w.rows("weekly_values", { select: "week_cutoff", order: "week_cutoff.desc" }, 1),
        w.rows("fetch_log", { select: "logged_at,run_id", order: "logged_at.desc" }, 1),
        w.rows("latest_week", { select: "status" }, 3000),
        w.rows("series", { select: "series_key,provider,last_status,last_message" }, 3000),
      ]);
      const statusCounts: Record<string, number> = {};
      for (const r of latest.rows) statusCounts[r.status] = (statusCounts[r.status] ?? 0) + 1;
      const problems = series.rows.filter((r) => r.last_status && r.last_status !== "ok");
      return {
        latest_week: week.rows[0]?.week_cutoff ?? null,
        last_fetch: fetchLog.rows[0]?.logged_at ?? null,
        latest_week_status_counts: statusCounts,
        series_total: series.rows.length,
        series_with_problems: problems.slice(0, 40).map((r) => ({ series_key: r.series_key, status: r.last_status, message: short(r.last_message, 100) })),
      };
    }
    case "weekly_report": {
      const week = checkDate(args.week, "week");
      const r = await w.storage(`object/reports/${week ? `weekly/${week}/issue.json` : "weekly/latest.json"}`);
      if (r.status === 400 || r.status === 404) {
        throw new ToolError(week ? `no issue for ${week}: issues are dated by their Friday cutoff` : "no issue has been published yet");
      }
      if (!r.ok) throw new Error(`storage request failed (${r.status})`);
      const issue = await r.json();
      const folder = String(issue.path ?? `weekly/${issue.as_of}`);
      // Only ever sign files inside one issue folder of the reports bucket.
      if (!/^weekly\/\d{4}-\d{2}-\d{2}$/.test(folder)) throw new Error("unexpected issue path in storage");
      const pngs: string[] = (Array.isArray(issue.files) ? issue.files : [])
        .map(String)
        .filter((f: string) => /^[a-z0-9][a-z0-9-]*\.png$/.test(f));
      const s = await w.storage("object/sign/reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expiresIn: REPORT_LINK_SECONDS, paths: ["weekly-report.pdf", ...pngs].map((f) => `${folder}/${f}`) }),
      });
      if (!s.ok) throw new Error(`storage signing failed (${s.status})`);
      const link = new Map<string, string>();
      for (const row of await s.json()) {
        if (row.signedURL) link.set(String(row.path).split("/").pop()!, `${w.env.supabaseUrl}/storage/v1${row.signedURL}`);
      }
      return {
        as_of: issue.as_of,
        week_start: issue.week_start ?? null,
        pages: issue.pages ?? null,
        charts: issue.charts ?? [],
        omitted: issue.omitted ?? [],
        series_notes: issue.series_notes ?? {},
        pdf_url: link.get("weekly-report.pdf") ?? null,
        chart_png_urls: Object.fromEntries(pngs.filter((f) => link.has(f)).map((f) => [f.replace(/\.png$/, ""), link.get(f)!])),
        expires_in_seconds: REPORT_LINK_SECONDS,
        usage: "Links expire in one hour. The issue contains MSCI and other licensed data: for readers' internal study only; do not forward, repost or attach it outside the reader list. Name proxies (series_notes) when quoting charts.",
      };
    }
    default:
      throw new ToolError(`unknown tool ${name}`);
  }
}

// ----------------------------------------------------------------------------- JSON-RPC / HTTP

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, GET, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, content-type, accept, mcp-session-id, mcp-protocol-version, x-api-key",
};

function json(body: Json, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...CORS } });
}

function rpcError(id: Json, code: number, message: string) {
  return { jsonrpc: "2.0", id: id ?? null, error: { code, message } };
}

function keyFrom(req: Request): string {
  const url = new URL(req.url);
  const q = url.searchParams.get("key");
  if (q) return q.trim();
  const auth = req.headers.get("authorization") ?? "";
  if (auth.toLowerCase().startsWith("bearer ")) return auth.slice(7).trim();
  return (req.headers.get("x-api-key") ?? "").trim();
}

async function handleMessage(w: Warehouse, msg: Json, email: string): Promise<Json | null> {
  if (!msg || msg.jsonrpc !== "2.0" || typeof msg.method !== "string") {
    return rpcError(msg?.id, -32600, "invalid JSON-RPC request");
  }
  const isNotification = msg.id === undefined || msg.id === null;
  if (isNotification) return null; // notifications/initialized, cancelled, ...
  const { id, method, params } = msg;
  switch (method) {
    case "initialize": {
      const asked = params?.protocolVersion;
      return {
        jsonrpc: "2.0", id,
        result: {
          protocolVersion: PROTOCOL_VERSIONS.includes(asked) ? asked : "2025-06-18",
          capabilities: { tools: { listChanged: false } },
          serverInfo: SERVER_INFO,
          instructions: INSTRUCTIONS,
        },
      };
    }
    case "ping":
      return { jsonrpc: "2.0", id, result: {} };
    case "tools/list":
      return { jsonrpc: "2.0", id, result: { tools: TOOLS } };
    case "resources/list":
      return { jsonrpc: "2.0", id, result: { resources: [] } };
    case "prompts/list":
      return { jsonrpc: "2.0", id, result: { prompts: [] } };
    case "tools/call": {
      const name = params?.name;
      const started = Date.now();
      try {
        const result = await callTool(w, name, params?.arguments);
        console.log(JSON.stringify({ tool: name, reader: email, ms: Date.now() - started }));
        return { jsonrpc: "2.0", id, result: { content: [{ type: "text", text: JSON.stringify(result) }] } };
      } catch (error) {
        const message = error instanceof ToolError ? error.message : `internal error: ${(error as Error).message}`;
        console.log(JSON.stringify({ tool: name, reader: email, error: message }));
        return { jsonrpc: "2.0", id, result: { content: [{ type: "text", text: message }], isError: true } };
      }
    }
    default:
      return rpcError(id, -32601, `method not found: ${method}`);
  }
}

export function makeHandler(env: Env, fetchImpl: typeof fetch = fetch) {
  const w = new Warehouse(env, fetchImpl);
  return async (req: Request): Promise<Response> => {
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (req.method === "GET") {
      // No server-initiated stream; a plain GET (browser, health check) gets a description.
      return new Response(
        JSON.stringify({ server: SERVER_INFO, transport: "streamable-http (POST JSON-RPC)", auth: "?key=cw_... or Authorization: Bearer cw_..." }),
        { status: 405, headers: { "Content-Type": "application/json", Allow: "POST, OPTIONS", ...CORS } },
      );
    }
    if (req.method === "DELETE") return new Response(null, { status: 200, headers: CORS });
    if (req.method !== "POST") return json(rpcError(null, -32600, "use POST"), 405);

    const email = await w.readerForKey(keyFrom(req)).catch(() => null);
    if (!email) {
      return json(rpcError(null, -32001, "missing or invalid reader key: ask the database owner for your personal connector URL"), 401);
    }
    let body: Json;
    try {
      body = await req.json();
    } catch (_) {
      return json(rpcError(null, -32700, "parse error"), 400);
    }
    if (Array.isArray(body)) {
      const replies = (await Promise.all(body.map((m) => handleMessage(w, m, email)))).filter((r) => r !== null);
      return replies.length ? json(replies) : new Response(null, { status: 202, headers: CORS });
    }
    const reply = await handleMessage(w, body, email);
    return reply === null ? new Response(null, { status: 202, headers: CORS }) : json(reply);
  };
}

// ----------------------------------------------------------------------------- Deno entry point

const deno = (globalThis as any).Deno;
if (deno?.serve) {
  const secrets = (() => {
    try {
      return JSON.parse(deno.env.get("SUPABASE_SECRET_KEYS") ?? "{}");
    } catch (_) {
      return {};
    }
  })();
  const secretKey = secrets.default ?? deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  deno.serve(makeHandler({ supabaseUrl: deno.env.get("SUPABASE_URL"), secretKey }));
}
