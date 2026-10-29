// Run: node --experimental-strip-types --test supabase/functions/report-upload/server.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { makeHandler, sha256Hex } from "./index.ts";

const ENV = { supabaseUrl: "https://db.example", secretKey: "sb_secret_test" };
const TOKEN = "ab".repeat(32);

type Call = { url: URL; method: string; headers: any };

async function fakeSupabase(calls: Call[], { tokenKnown = true } = {}) {
  const hash = await sha256Hex(TOKEN);
  return async (input: any, init: any = {}) => {
    const url = new URL(String(input));
    calls.push({ url, method: init.method ?? "GET", headers: init.headers });
    if (url.pathname === "/rest/v1/report_upload_tokens") {
      const ok = tokenKnown && url.searchParams.get("token_hash") === `eq.${hash}` && url.searchParams.get("expires_at")!.startsWith("gt.");
      return new Response(JSON.stringify(ok ? [{ token_hash: hash }] : []), { status: 200 });
    }
    if (url.pathname.startsWith("/storage/v1/object/upload/sign/reports/")) {
      const path = url.pathname.replace("/storage/v1/object/upload/sign/reports/", "");
      return new Response(JSON.stringify({ url: `/object/upload/sign/reports/${path}?token=signed` }), { status: 200 });
    }
    return new Response("not found", { status: 404 });
  };
}

async function post(handler: any, body: any) {
  const r = await handler(new Request("https://fn.example/functions/v1/report-upload", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  }));
  return { status: r.status, body: await r.json() };
}

test("a known token gets signed upload links for issue files", async () => {
  const calls: Call[] = [];
  const h = makeHandler(ENV, (await fakeSupabase(calls)) as any);
  const r = await post(h, { token: TOKEN, paths: ["weekly/2026-10-23/weekly-report.pdf", "weekly/2026-10-23/issue.json", "weekly/latest.json"] });
  assert.equal(r.status, 200);
  assert.deepEqual(r.body.uploads.map((u: any) => u.path), ["weekly/2026-10-23/weekly-report.pdf", "weekly/2026-10-23/issue.json", "weekly/latest.json"]);
  assert.equal(r.body.uploads[0].url, "https://db.example/storage/v1/object/upload/sign/reports/weekly/2026-10-23/weekly-report.pdf?token=signed");
  const sign = calls.filter((c) => c.url.pathname.startsWith("/storage/"));
  assert.equal(sign.length, 3);
  assert.equal(sign[0].method, "POST");
  assert.equal(sign[0].headers.apikey, "sb_secret_test");
  assert.equal(sign[0].headers.Authorization, undefined);
  assert.equal(sign[0].headers["x-upsert"], "true");
});

test("unknown, expired or malformed tokens get nothing", async () => {
  const calls: Call[] = [];
  const h = makeHandler(ENV, (await fakeSupabase(calls, { tokenKnown: false })) as any);
  assert.equal((await post(h, { token: TOKEN, paths: ["weekly/latest.json"] })).status, 401);
  assert.equal((await post(h, { token: "short", paths: ["weekly/latest.json"] })).status, 401);
  assert.equal(calls.filter((c) => c.url.pathname.startsWith("/storage/")).length, 0);
});

test("only issue paths in the reports bucket can be signed", async () => {
  const calls: Call[] = [];
  const h = makeHandler(ENV, (await fakeSupabase(calls)) as any);
  for (const path of ["weekly/2026-10-23/../../x.pdf", "../reports/weekly/latest.json", "other/2026-10-23/a.pdf",
                      "weekly/2026-10-23/a.exe", "weekly/26-10-23/a.pdf", "weekly/2026-10-23/sub/a.pdf"]) {
    const r = await post(h, { token: TOKEN, paths: [path] });
    assert.equal(r.status, 400, path);
  }
  assert.equal((await post(h, { token: TOKEN, paths: [] })).status, 400);
  assert.equal(calls.length, 0); // rejected before any database or storage call
});

test("only POST is served", async () => {
  const h = makeHandler(ENV, (await fakeSupabase([])) as any);
  const r = await h(new Request("https://fn.example/functions/v1/report-upload", { method: "GET" }));
  assert.equal(r.status, 405);
});
