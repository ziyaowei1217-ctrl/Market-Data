// Run: node --experimental-strip-types --test supabase/functions/warehouse-mcp/server.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { makeHandler, sha256Hex } from "./index.ts";

const KEY = "cw_" + "ab".repeat(24);
const ENV = { supabaseUrl: "https://db.example", secretKey: "sb_secret_test" };

type Call = { path: string; params: URLSearchParams; method: string; headers: any; body?: any };

async function fakeDb(calls: Call[]) {
  const keyHash = await sha256Hex(KEY);
  return async (input: any, init: any = {}) => {
    const url = new URL(String(input));
    const path = url.pathname.replace("/rest/v1/", "");
    calls.push({ path, params: url.searchParams, method: init.method ?? "GET", headers: init.headers, body: init.body });
    const p = url.searchParams;
    if (path === "/storage/v1/object/reports/weekly/latest.json") {
      return new Response(JSON.stringify({
        as_of: "2026-10-23", week_start: "2026-10-16", path: "weekly/2026-10-23", pages: 6, charts: ["trends", "returns"],
        omitted: [], series_notes: { "黄金": "COMEX 期货近月代理" },
        files: ["weekly-report.pdf", "cross-asset-trends.png", "cross-asset-trends.pdf", "weekly-returns.png", "weekly-returns.pdf"],
      }), { status: 200 });
    }
    if (path.startsWith("/storage/v1/object/reports/")) {
      return new Response(JSON.stringify({ statusCode: "404", error: "not_found", message: "Object not found" }), { status: 400 });
    }
    if (path === "/storage/v1/object/sign/reports") {
      const { paths } = JSON.parse(init.body);
      return new Response(JSON.stringify(paths.map((x: string) => ({ error: null, path: x, signedURL: `/object/sign/reports/${x}?token=t` }))), { status: 200 });
    }
    let rows: any[] = [];
    if (path === "reader_keys" && (init.method ?? "GET") === "GET") {
      rows = p.get("key_hash") === `eq.${keyHash}` ? [{ email: "me@example.com" }] : [];
    } else if (path === "reader_keys") {
      return new Response(null, { status: 204 });
    } else if (path === "catalog" && p.get("and")) {
      // search: PostgREST returns matches in text order of indicator_id
      rows = [
        { indicator_id: "109-016", module: "美债期限情景测算", name: "美国10年平价国债：前6个月曲线下移50bp的一年总回报", unit: "%", method: "api", coverage_note: "自算", last_week: "2026-10-23" },
        { indicator_id: "12-007", module: "利率信用", name: "美国10年国债收益率", unit: "%", method: "api", coverage_note: "FRED DGS10", last_week: "2026-10-23" },
        { indicator_id: "12-008", module: "利率信用", name: "美国10年国债收益率周变动", unit: "bp", method: "api", coverage_note: "FRED DGS10", last_week: "2026-10-23" },
        { indicator_id: "61-002", module: "美国宏观", name: "美国10年期限溢价", unit: "%", method: "pending", coverage_note: "暂无来源", last_week: null },
      ];
    } else if (path === "catalog") {
      rows = [{ indicator_id: "12-007", module: "利率信用", name: "美国10年国债收益率", unit: "%", method: "api", coverage_note: "FRED DGS10", last_week: "2026-10-23", first_week: "2021-10-01", ok_weeks: 265 }];
    } else if (path === "weekly") {
      rows = [
        { week_cutoff: "2026-10-16", indicator_id: "12-007", value: 5.09, obs_date: "2026-10-16", status: "ok" },
        { week_cutoff: "2026-10-23", indicator_id: "12-007", value: 4.960000000000001, obs_date: "2026-10-22", status: "ok" },
      ];
    } else if (path === "indicators") {
      rows = [{ indicator_id: "12-007", module: "利率信用", name: "美国10年国债收益率", method: "api", formula: "{FRED:DGS10}" },
              { indicator_id: "12-003", module: "利率信用", name: "美国2年国债收益率", method: "api" },
              { indicator_id: "97-041", module: "跨资产历史图", name: "x", method: "report" }];
    } else if (path === "latest_week") {
      rows = [
        { week_cutoff: "2026-10-23", indicator_id: "112-301", module: "利率信用", name: "美国30年TIPS实际收益率", unit: "%", value: 3.05, obs_date: "2026-10-22", status: "ok", method: "api" },
        { week_cutoff: "2026-10-23", indicator_id: "12-004", module: "利率信用", name: "美国2年国债收益率周变动", unit: "bp", value: -8.99999999999999, obs_date: "2026-10-22", status: "ok", method: "api" },
        { week_cutoff: "2026-10-23", indicator_id: "12-007", module: "利率信用", name: "美国10年国债收益率", unit: "%", value: 4.96, obs_date: "2026-10-22", status: "ok", method: "api" },
      ];
    }
    const offset = Number(p.get("offset") ?? 0), limit = Number(p.get("limit") ?? 1000);
    return new Response(JSON.stringify(rows.slice(offset, offset + limit)), { status: 200, headers: { "Content-Type": "application/json" } });
  };
}

async function rpc(handler: any, body: any, key: string | null = KEY) {
  const url = "https://fn.example/functions/v1/warehouse-mcp" + (key ? `?key=${key}` : "");
  const r = await handler(new Request(url, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream" }, body: JSON.stringify(body) }));
  return { status: r.status, body: r.status === 202 ? null : await r.json() };
}

test("rejects a missing or unknown key", async () => {
  const h = makeHandler(ENV, (await fakeDb([])) as any);
  assert.equal((await rpc(h, { jsonrpc: "2.0", id: 1, method: "tools/list" }, null)).status, 401);
  assert.equal((await rpc(h, { jsonrpc: "2.0", id: 1, method: "tools/list" }, "cw_" + "00".repeat(24))).status, 401);
});

test("initialize negotiates a known protocol version and lists tools", async () => {
  const h = makeHandler(ENV, (await fakeDb([])) as any);
  const init = await rpc(h, { jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "t", version: "1" } } });
  assert.equal(init.body.result.protocolVersion, "2025-06-18");
  assert.ok(init.body.result.instructions.includes("proxy"));
  const note = await rpc(h, { jsonrpc: "2.0", method: "notifications/initialized" });
  assert.equal(note.status, 202);
  const list = await rpc(h, { jsonrpc: "2.0", id: 2, method: "tools/list" });
  const names = list.body.result.tools.map((t: any) => t.name);
  assert.deepEqual(names, ["search_indicators", "list_modules", "describe_indicator", "get_weekly", "get_latest", "get_series", "data_status", "weekly_report"]);
});

test("search builds an AND of keyword filters and strips filter syntax", async () => {
  const calls: Call[] = [];
  const h = makeHandler(ENV, (await fakeDb(calls)) as any);
  const r = await rpc(h, { jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "search_indicators", arguments: { query: "美国 10年),x" } } });
  const out = JSON.parse(r.body.result.content[0].text);
  // the plain indicator first, its derived variants next, indicators without values last
  assert.deepEqual(out.rows.map((row: any) => row[0]), ["12-007", "12-008", "109-016", "61-002"]);
  const q = calls.find((c) => c.path === "catalog")!;
  assert.equal(q.params.get("and"), "(or(name.ilike.*美国*,indicator_id.ilike.*美国*,module.ilike.*美国*),or(name.ilike.*10年x*,indicator_id.ilike.*10年x*,module.ilike.*10年x*))");
  assert.equal(q.headers.apikey, "sb_secret_test");
  assert.equal(q.headers.Authorization, undefined);
  assert.equal(q.params.get("method"), "neq.excluded"); // dropped boards stay out of search
});

test("search can still ask for excluded indicators explicitly", async () => {
  const calls: Call[] = [];
  const h = makeHandler(ENV, (await fakeDb(calls)) as any);
  await rpc(h, { jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "search_indicators", arguments: { query: "估值", method: "excluded" } } });
  assert.equal(calls.find((c) => c.path === "catalog")!.params.get("method"), "eq.excluded");
});

test("get_weekly returns columns/rows with indicator metadata, ok rows only by default", async () => {
  const calls: Call[] = [];
  const h = makeHandler(ENV, (await fakeDb(calls)) as any);
  const r = await rpc(h, { jsonrpc: "2.0", id: 4, method: "tools/call", params: { name: "get_weekly", arguments: { indicator_ids: ["12-007"], start: "2026-01-01" } } });
  const out = JSON.parse(r.body.result.content[0].text);
  assert.deepEqual(out.columns, ["week_cutoff", "indicator_id", "value", "obs_date", "status"]);
  assert.equal(out.rows.length, 2);
  assert.equal(out.rows[1][2], 4.96); // floating-point noise trimmed
  assert.equal(out.indicators["12-007"].unit, "%");
  const q = calls.find((c) => c.path === "weekly")!;
  assert.equal(q.params.get("status"), "eq.ok");
  assert.equal(q.params.get("week_cutoff"), "gte.2026-01-01");
  assert.equal(q.params.get("indicator_id"), "in.(12-007)");
});

test("get_latest sorts indicator IDs numerically and trims float noise", async () => {
  const h = makeHandler(ENV, (await fakeDb([])) as any);
  const r = await rpc(h, { jsonrpc: "2.0", id: 9, method: "tools/call", params: { name: "get_latest", arguments: { module: "利率信用" } } });
  const out = JSON.parse(r.body.result.content[0].text);
  assert.deepEqual(out.rows.map((row: any) => row[0]), ["12-004", "12-007", "112-301"]);
  assert.equal(out.rows[0][4], -9);
});

test("bad arguments come back as tool errors, not crashes", async () => {
  const h = makeHandler(ENV, (await fakeDb([])) as any);
  const r = await rpc(h, { jsonrpc: "2.0", id: 5, method: "tools/call", params: { name: "get_weekly", arguments: { indicator_ids: ["DROP TABLE"] } } });
  assert.equal(r.body.result.isError, true);
  assert.match(r.body.result.content[0].text, /not indicator IDs/);
  const r2 = await rpc(h, { jsonrpc: "2.0", id: 6, method: "tools/call", params: { name: "get_latest", arguments: {} } });
  assert.equal(r2.body.result.isError, true);
});

test("list_modules aggregates counts by method", async () => {
  const h = makeHandler(ENV, (await fakeDb([])) as any);
  const r = await rpc(h, { jsonrpc: "2.0", id: 7, method: "tools/call", params: { name: "list_modules", arguments: {} } });
  const out = JSON.parse(r.body.result.content[0].text);
  const rates = out.modules.find((m: any) => m.module === "利率信用");
  assert.deepEqual(rates, { module: "利率信用", total: 2, api: 2 });
});

test("unknown methods return JSON-RPC errors; GET explains the transport", async () => {
  const h = makeHandler(ENV, (await fakeDb([])) as any);
  const r = await rpc(h, { jsonrpc: "2.0", id: 8, method: "sampling/createMessage" });
  assert.equal(r.body.error.code, -32601);
  const g = await h(new Request("https://fn.example/functions/v1/warehouse-mcp", { method: "GET" }));
  assert.equal(g.status, 405);
});

test("weekly_report signs one-hour links to the latest issue's PDF and chart images", async () => {
  const calls: Call[] = [];
  const h = makeHandler(ENV, (await fakeDb(calls)) as any);
  const r = await rpc(h, { jsonrpc: "2.0", id: 10, method: "tools/call", params: { name: "weekly_report", arguments: {} } });
  const out = JSON.parse(r.body.result.content[0].text);
  assert.equal(out.as_of, "2026-10-23");
  assert.equal(out.pdf_url, "https://db.example/storage/v1/object/sign/reports/weekly/2026-10-23/weekly-report.pdf?token=t");
  assert.deepEqual(Object.keys(out.chart_png_urls), ["cross-asset-trends", "weekly-returns"]);
  assert.equal(out.expires_in_seconds, 3600);
  assert.deepEqual(out.series_notes, { "黄金": "COMEX 期货近月代理" });
  assert.match(out.usage, /MSCI/);
  const sign = calls.find((c) => c.path === "/storage/v1/object/sign/reports")!;
  assert.equal(sign.method, "POST");
  assert.equal(sign.headers.apikey, "sb_secret_test");
  assert.equal(JSON.parse(sign.body).expiresIn, 3600);
});

test("weekly_report for a week without an issue is a tool error", async () => {
  const h = makeHandler(ENV, (await fakeDb([])) as any);
  const r = await rpc(h, { jsonrpc: "2.0", id: 11, method: "tools/call", params: { name: "weekly_report", arguments: { week: "2026-10-16" } } });
  assert.equal(r.body.result.isError, true);
  assert.match(r.body.result.content[0].text, /no issue for 2026-10-16/);
  const bad = await rpc(h, { jsonrpc: "2.0", id: 12, method: "tools/call", params: { name: "weekly_report", arguments: { week: "last week" } } });
  assert.match(bad.body.result.content[0].text, /YYYY-MM-DD/);
});
