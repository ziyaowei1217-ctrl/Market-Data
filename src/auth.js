// Email + password sign-in against the warehouse's Supabase project (website build only).
// The publishable key only identifies the project; data needs a signed-in reader (RLS: private.is_reader()).
export const SUPABASE_URL = "https://ujomxngmefoplrsxmuyf.supabase.co";
export const PUBLISHABLE_KEY = "sb_publishable_d5Go9QOSznfvLdN2rTwnVw_Ib4aNktm";

const STORE = "cw-session";
let session = load();
let refreshing = null;
const listeners = new Set();

function load() {
  try {
    const s = JSON.parse(localStorage.getItem(STORE));
    return s && s.access_token && s.refresh_token ? s : null;
  } catch {
    return null;
  }
}
function save(s) {
  session = s;
  try {
    if (s) localStorage.setItem(STORE, JSON.stringify(s));
    else localStorage.removeItem(STORE);
  } catch { /* a private window: the session lasts until the tab closes */ }
  for (const fn of listeners) fn(session);
}

export const getSession = () => session;
export const onSession = (fn) => { listeners.add(fn); return () => listeners.delete(fn); };

export class AuthError extends Error {
  constructor(code, message) { super(message); this.code = code; }
}

function describe(status, j) {
  const code = j.error_code || j.error || "";
  const msg = j.msg || j.error_description || j.message || "";
  if (/invalid_credentials|invalid_grant/.test(code) || /Invalid login credentials/i.test(msg)) return new AuthError("invalid_credentials", "邮箱或密码不对。");
  if (/email_not_confirmed/.test(code) || /Email not confirmed/i.test(msg)) return new AuthError("email_not_confirmed", "这个邮箱还没验证：先点注册邮件里的验证链接，再回来登录。");
  if (status === 429 || /rate/i.test(code)) return new AuthError("rate_limited", "尝试次数太多，过几分钟再试。");
  if (/refresh_token/i.test(code) || /refresh token/i.test(msg)) return new AuthError("needs_login", "登录已过期，请重新登录。");
  return new AuthError("auth_error", msg || `登录失败（${status}）。`);
}

async function tokenRequest(grant, body) {
  let r;
  try {
    r = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=${grant}`, {
      method: "POST",
      headers: { apikey: PUBLISHABLE_KEY, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new AuthError("network", "连不上数据库服务器，检查网络后再试。");
  }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw describe(r.status, j);
  return {
    access_token: j.access_token,
    refresh_token: j.refresh_token,
    expires_at: j.expires_at || Math.floor(Date.now() / 1000) + (j.expires_in || 3600),
    email: (j.user && j.user.email) || body.email || (session && session.email) || "",
  };
}

// Signing in holds the session quietly until the caller has checked the account is a reader.
export async function signIn(email, password) {
  const s = await tokenRequest("password", { email: email.trim().toLowerCase(), password });
  session = s;
  return s;
}
export const confirmSession = () => save(session);
export async function discardSession() {
  const s = session;
  session = null;
  if (s) {
    try { await fetch(`${SUPABASE_URL}/auth/v1/logout`, { method: "POST", headers: { apikey: PUBLISHABLE_KEY, Authorization: `Bearer ${s.access_token}` } }); } catch { /* ignore */ }
  }
}

async function refresh() {
  if (!session) throw new AuthError("needs_login", "请先登录。");
  if (!refreshing) {
    refreshing = tokenRequest("refresh_token", { refresh_token: session.refresh_token })
      .then((s) => { save(s); return s; })
      .catch((e) => { if (e.code !== "network") save(null); throw e; })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

// A fresh access token, refreshed a minute before it expires.
export async function accessToken({ force = false } = {}) {
  if (!session) throw new AuthError("needs_login", "请先登录。");
  if (force || session.expires_at * 1000 - Date.now() < 60_000) await refresh();
  return session.access_token;
}

export async function signOut() {
  const s = session;
  save(null);
  if (!s) return;
  try {
    await fetch(`${SUPABASE_URL}/auth/v1/logout`, { method: "POST", headers: { apikey: PUBLISHABLE_KEY, Authorization: `Bearer ${s.access_token}` } });
  } catch { /* signed out locally either way */ }
}
