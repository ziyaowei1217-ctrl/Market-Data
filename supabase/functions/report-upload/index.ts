// Signed upload links for the weekly issue (private Storage bucket "reports"), used by the report workflow.
//
// The caller proves it can write to the database: it inserts sha256(token) into
// public.report_upload_tokens (see pipeline/report/storage.sql) over the warehouse connection
// string, then sends the token here. No long-lived upload secret is shared with GitHub, and the
// function's own service key never leaves Supabase. Tokens expire after 30 minutes.
//
// Deploy: supabase functions deploy report-upload --no-verify-jwt

type Json = any;
export type Env = { supabaseUrl: string; secretKey: string };

const TOKEN_RE = /^[0-9a-f]{64}$/;
// weekly/<Friday>/<file>.pdf|png|json, or the weekly/latest.json pointer; nothing else in the bucket.
const PATH_RE = /^weekly\/(\d{4}-\d{2}-\d{2}\/[a-z0-9][a-z0-9-]*\.(pdf|png|json)|latest\.json)$/;
const MAX_PATHS = 80;

export async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function json(body: Json, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

export function makeHandler(env: Env, fetchImpl: typeof fetch = fetch) {
  const key = env.secretKey;
  // New secret keys go on apikey only; legacy service_role JWTs also as a bearer token.
  const auth = (): Record<string, string> =>
    key.startsWith("sb_secret_") ? { apikey: key } : { apikey: key, Authorization: `Bearer ${key}` };

  return async (req: Request): Promise<Response> => {
    if (req.method !== "POST") return json({ error: "use POST" }, 405);
    let body: Json;
    try {
      body = await req.json();
    } catch (_) {
      return json({ error: "body must be JSON" }, 400);
    }
    const token = String(body?.token ?? "");
    if (!TOKEN_RE.test(token)) return json({ error: "invalid or expired token" }, 401);
    const paths = body?.paths;
    if (!Array.isArray(paths) || paths.length === 0 || paths.length > MAX_PATHS ||
        !paths.every((p: Json) => typeof p === "string" && PATH_RE.test(p))) {
      return json({ error: "paths must be weekly/<YYYY-MM-DD>/<name>.pdf|png|json or weekly/latest.json" }, 400);
    }

    const hash = await sha256Hex(token);
    const q = new URLSearchParams({ token_hash: `eq.${hash}`, expires_at: `gt.${new Date().toISOString()}`, select: "token_hash" });
    const check = await fetchImpl(`${env.supabaseUrl}/rest/v1/report_upload_tokens?${q}`, { headers: auth() });
    if (!check.ok) return json({ error: `token check failed (${check.status})` }, 502);
    if (!(await check.json()).length) return json({ error: "invalid or expired token" }, 401);

    const uploads: { path: string; url: string }[] = [];
    for (const path of [...new Set(paths as string[])]) {
      const r = await fetchImpl(`${env.supabaseUrl}/storage/v1/object/upload/sign/reports/${path}`, {
        method: "POST",
        headers: { ...auth(), "x-upsert": "true" },
      });
      if (!r.ok) return json({ error: `signing failed for ${path} (${r.status})` }, 502);
      const signed = await r.json();
      uploads.push({ path, url: `${env.supabaseUrl}/storage/v1${signed.url}` });
    }
    console.log(JSON.stringify({ signed: uploads.length }));
    return json({ uploads });
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
