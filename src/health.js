// A private note of how the page loaded for this viewer (data/users/<id>/health), so problems can be diagnosed.
const state = {};
let timer = null;
export function noteHealth(patch) {
  Object.assign(state, patch);
  clearTimeout(timer);
  timer = setTimeout(async () => {
    try {
      const claude = window.claude;
      if (!claude || typeof claude.use !== "function") return;
      const [db, user] = await Promise.all([claude.use("db"), claude.use("user")]);
      const id = user ? await user.id() : null;
      if (!db || !id) return;
      await db.doc(`data/users/${id}/health`).set({ ...state, at: new Date().toISOString(), ua: navigator.userAgent.slice(0, 160) });
    } catch { /* diagnostics only */ }
  }, 1500);
}
