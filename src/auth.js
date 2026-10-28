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
export const confirmSession = (s) => save(s || session);
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

// Where links in Supabase's emails should land (the site itself).
const here = () => location.origin + location.pathname;

// Sign up with email + password. Supabase emails a verification link; the account works after it is clicked.
export async function signUp(email, password) {
  let r;
  try {
    r = await fetch(`${SUPABASE_URL}/auth/v1/signup?redirect_to=${encodeURIComponent(here())}`, {
      method: "POST",
      headers: { apikey: PUBLISHABLE_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
    });
  } catch {
    throw new AuthError("network", "连不上数据库服务器，检查网络后再试。");
  }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    const code = j.error_code || "";
    const msg = j.msg || j.error_description || j.message || "";
    if (/weak_password/.test(code) || /Password should/i.test(msg)) throw new AuthError("weak_password", "密码太短，至少 6 位。");
    if (/user_already_exists/.test(code) || /already registered/i.test(msg)) throw new AuthError("exists", "这个邮箱已经注册过，直接登录即可。");
    if (r.status === 429 || /rate/i.test(code)) throw new AuthError("rate_limited", "验证邮件发得太频繁，过一会儿再试。");
    throw new AuthError("auth_error", msg || `注册失败（${r.status}）。`);
  }
  if (j.access_token) return { signedIn: true, session: { access_token: j.access_token, refresh_token: j.refresh_token, expires_at: j.expires_at || Math.floor(Date.now() / 1000) + (j.expires_in || 3600), email: email.trim().toLowerCase() } };
  const user = j.user || j;
  if (Array.isArray(user.identities) && user.identities.length === 0) throw new AuthError("exists", "这个邮箱已经注册过，直接登录即可。");
  return { signedIn: false };
}

// Email a link that lets the viewer set a new password.
export async function requestReset(email) {
  let r;
  try {
    r = await fetch(`${SUPABASE_URL}/auth/v1/recover?redirect_to=${encodeURIComponent(here())}`, {
      method: "POST",
      headers: { apikey: PUBLISHABLE_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim().toLowerCase() }),
    });
  } catch {
    throw new AuthError("network", "连不上数据库服务器，检查网络后再试。");
  }
  if (r.status === 429) throw new AuthError("rate_limited", "邮件发得太频繁，过一会儿再试。");
  if (!r.ok) { const j = await r.json().catch(() => ({})); throw new AuthError("auth_error", j.msg || `发送失败（${r.status}）。`); }
}

export async function setPassword(password) {
  const token = await accessToken();
  const r = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
    method: "PUT",
    headers: { apikey: PUBLISHABLE_KEY, Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (/weak_password/.test(j.error_code || "")) throw new AuthError("weak_password", "密码太短，至少 6 位。");
    if (/same_password/.test(j.error_code || "")) throw new AuthError("same_password", "新密码不能和旧密码一样。");
    throw new AuthError("auth_error", j.msg || `修改失败（${r.status}）。`);
  }
}

// Links in verification and reset emails come back with the session in the URL hash.
export function takeSessionFromLink() {
  const h = new URLSearchParams(location.hash.slice(1));
  const access = h.get("access_token");
  const refreshToken = h.get("refresh_token");
  const type = h.get("type") || "";
  const error = h.get("error_description");
  if (!access && !error) return null;
  try { history.replaceState(null, "", location.pathname + location.search); } catch { location.hash = ""; }
  if (error) return { error: error.replace(/\+/g, " ") };
  let email = "";
  try { email = JSON.parse(atob(access.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).email || ""; } catch { /* email shown as blank */ }
  save({ access_token: access, refresh_token: refreshToken, expires_at: Number(h.get("expires_at")) || Math.floor(Date.now() / 1000) + Number(h.get("expires_in") || 3600), email });
  return { type };
}
