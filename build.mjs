// Build the site.
//   node build.mjs web       -> dist/      the GitHub Pages website (Supabase sign-in)
//   node build.mjs artifact  -> artifact/  the Claude artifact (viewer's 「金融数据库」 connector)
import { build } from "esbuild";
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

const target = process.argv[2] === "artifact" ? "artifact" : "web";
const out = target === "web" ? "dist" : "artifact";
rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });

await build({
  entryPoints: ["src/app.jsx"],
  bundle: true,
  minify: true,
  format: "iife",
  jsx: "automatic",
  target: "es2020",
  define: { "process.env.NODE_ENV": '"production"', __WEB__: String(target === "web") },
  outfile: join(out, "app.js"),
  logLevel: "warning",
});

// Perspective (engine, viewer, plugins, WebAssembly) and Salt's theme, served from this site.
const vendor = {
  "perspective/cdn/perspective.js": "@finos/perspective/dist/cdn/perspective.js",
  "perspective/cdn/perspective-server.worker.js": "@finos/perspective/dist/cdn/perspective-server.worker.js",
  "perspective/wasm/perspective-server.wasm": "@finos/perspective/dist/wasm/perspective-server.wasm",
  "perspective-viewer/cdn/perspective-viewer.js": "@finos/perspective-viewer/dist/cdn/perspective-viewer.js",
  "perspective-viewer/wasm/perspective-viewer.wasm": "@finos/perspective-viewer/dist/wasm/perspective-viewer.wasm",
  "perspective-viewer/css/themes.css": "@finos/perspective-viewer/dist/css/themes.css",
  "perspective-viewer-datagrid/cdn/perspective-viewer-datagrid.js": "@finos/perspective-viewer-datagrid/dist/cdn/perspective-viewer-datagrid.js",
  "perspective-viewer-d3fc/cdn/perspective-viewer-d3fc.js": "@finos/perspective-viewer-d3fc/dist/cdn/perspective-viewer-d3fc.js",
  "salt/index.css": "@salt-ds/theme/index.css",
  "salt/theme-next.css": "@salt-ds/theme/css/theme-next.css",
};
for (const [to, from] of Object.entries(vendor)) {
  const dest = join(out, "vendor", to);
  mkdirSync(dirname(dest), { recursive: true });
  const src = join("node_modules", from);
  if (to.endsWith(".js")) writeFileSync(dest, readFileSync(src, "utf8").replace(/\/\/# sourceMappingURL=.*$/gm, ""));
  else cpSync(src, dest);
}

// The page. The artifact host adds its own document skeleton; the website needs a full document.
const page = readFileSync("public/index.html", "utf8");
if (target === "artifact") {
  writeFileSync(join(out, "index.html"), page);
} else {
  const cut = page.indexOf('<div id="app">');
  const head = page.slice(0, cut).replace(/<meta name="claude:viewport-fit-sides"[^>]*>\n?/, "");
  const body = page.slice(cut);
  const icon = "data:image/svg+xml," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="#141414"/><path d="M6 22l6-7 5 4 9-11" stroke="#8c9cff" stroke-width="3" fill="none"/></svg>');
  writeFileSync(join(out, "index.html"), `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<meta name="description" content="资本市场周报数据库的查询与看图台，读者名单内部使用。">
<link rel="icon" href="${icon}">
<style>html{color-scheme:light dark}body{margin:0}[hidden]{display:none!important}:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>
${head}</head>
<body>
${body}</body>
</html>
`);
  writeFileSync(join(out, ".nojekyll"), "");
}
console.log(`built ${out}/`);
