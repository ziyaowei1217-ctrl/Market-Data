# 资本市场周报数据台

资本市场周报数据库（Capital Weekly warehouse）的查询与看图网站：搜索指标、看周度走势、查本周各板块数值、看采集覆盖情况。

- 界面：J.P. Morgan 开源的 [Salt 设计系统](https://www.saltdesignsystem.com/)（Salt Next 主题）
- 表格和图表：[FINOS Perspective](https://perspective.finos.org/)（原 J.P. Morgan 开源，WebAssembly 引擎）
- 数据：Supabase 上的周报数据库，每周六自动更新

## 谁能看数据

网站代码是公开的，但里面没有任何数据。数据要用邮箱和密码登录后才从数据库读取，
只有 `public.readers` 读者名单上、邮箱已验证的账号能读到（数据库的行级权限 `private.is_reader()`）。
不在名单上的账号登录时会被告知「不在读者名单上」。

加一位同学（数据库所有者在 Supabase 后台操作）：

1. SQL Editor：`insert into public.readers (email) values ('同学邮箱');`（小写）
2. Authentication → Add user：填同学邮箱和初始密码，勾选 Auto Confirm User，把密码私下发给本人

MSCI、ISM、S&P Global 等数据仅供读者名单内部学习使用，不要导出整表转给名单外的人。

## 部署

源码在 `market-data` 仓库的 `site` 分支，打包好的网站在 `gh-pages` 分支（与数据管线的分支互不影响）。
推送到 `site` 后，GitHub Actions（`.github/workflows/pages.yml`）自动构建并更新 `gh-pages`，
GitHub Pages 从 `gh-pages` 发布，网址：https://ziyaowei1217-ctrl.github.io/market-data/

## 本地构建

```bash
npm ci
node build.mjs web        # dist/：网站版（Supabase 登录）
node build.mjs artifact   # artifact/：Claude 网页版（用查看者自己的「金融数据库」连接器）
```

`dist/` 可以用任意静态服务器预览，例如 `python3 -m http.server -d dist`。

## 结构

| 文件 | 内容 |
| --- | --- |
| `src/app.jsx` | 页面（React + Salt）：走势分析、本周一览、覆盖情况、登录 |
| `src/data-web.js` | 网站版取数：Supabase REST，查询逻辑与 MCP 服务器一致 |
| `src/data-mcp.js` | Claude 版取数：通过查看者的「金融数据库」连接器 |
| `src/auth.js` | 邮箱密码登录、自动续期、退出 |
| `src/psp.js` | Perspective 加载、表结构，以及图表的中文日期轴和负号 |
| `src/format.js` | 数字、日期、涨跌格式（按《周报图表样式规范》） |
| `public/index.html` | 页面骨架与样式 |
| `build.mjs` | 打包脚本：esbuild 打包，复制 Perspective 和 Salt 的文件 |

依赖版本全部锁定（`package-lock.json`）。
