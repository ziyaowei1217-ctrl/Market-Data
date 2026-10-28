# 市场一周（pipeline/report）

把 Capital Weekly 数据库画成每周的《市场一周》PDF 周报。每周六数据库更新成功后，GitHub Actions 自动出刊，存进 Supabase 的私有存储，只有读者名单内的账号能下载；读者的 AI 助手也能通过数据库连接器直接拿到本期 PDF 和单图。

同一套图表也可以离线使用：给本地 CSV（或 `--demo` 模拟数据）就能出图，不需要网络和账号。

## 每周自动出刊

```
周六 13:17 UTC  warehouse 工作流取数 ──成功──▶ report 工作流
                                              ├─ python -m pipeline.report build    从数据库取数、画图、排版
                                              └─ python -m pipeline.report publish  上传到 Storage 的 reports 桶
读者：python3 -m pipeline.report latest  或在 AI 助手里用连接器的 weekly_report 工具
```

**本期画什么**写在 `issue.json`：六个资产（名称、序列、是否代理）、五个美债期限、十四张图的顺序和样式（重点资产、基准、相关性对象、论点页）。改资产或图表只改这个文件；序列键必须在 `pipeline/warehouse/catalog/series.csv` 里，代理序列的 `note` 必须以「代理」结尾，测试会检查。

**日期规则**（元数据 `date_rule: "asof"`）：周度截点为周五，与数据库一致。每个序列取截点当天或之前最近的一个观察值，最多往前找 6 天；节假日沿用前一交易日收盘（最多 3 个工作日），序列末端不往后补。所以 FRED 收益率只到周四时，图里用周四的值，并注明「截至10月22日」。离线 CSV 仍要求两个日期都存在（`exact`）。

**数据说明**：用了代理序列、或者没更新到周五的序列，会写进周报最后的「数据说明」，周报里每张相关的图在来源行提示「代理与观察日见末页数据说明」；单独导出的 PNG/PDF 则把说明直接写在图下。离截点超过 6 天都没有数据的序列这一期不画，首页页脚和数据说明里写明「本期未列入：黄金（最新数据为10月9日）」。

**自己出一期**（需要数据库连接串，或读者账号）：

```bash
pip install -r pipeline/report/requirements.txt
export WAREHOUSE_DB_URL=...            # 或者 WAREHOUSE_EMAIL / WAREHOUSE_PASSWORD（读者账号，走 REST）
python3 -m pipeline.report build --week 2026-10-23 --output-dir outputs/weekly
```

输出目录里有 `weekly-report.pdf`、每张图的 PNG/PDF，以及 `issue.json`（截点、页数、图表、未列入、数据说明）。

**下载已发布的一期**（读者账号，密码不要写进仓库或聊天记录）：

```bash
export WAREHOUSE_EMAIL=you@example.com WAREHOUSE_PASSWORD=...
python3 -m pipeline.report latest                      # 最新一期 → ./市场一周-2026-10-23.pdf
python3 -m pipeline.report latest --week 2026-10-16    # 某一期
```

**存储与权限**：私有桶 `reports`，路径 `weekly/<周五>/…`，最后写 `weekly/latest.json`。`storage.sql` 只给读者名单开放读取，发布时自动执行（可重复执行）。本仓库是公开的，而周报含 MSCI 等授权数据，所以工作流**不上传 artifact、不在日志里打印数值**；周报只在读者名单内学习使用，不要转发到名单外。

**上传不需要额外的密钥**：发布时用已有的 `WAREHOUSE_DB_URL` 往 `public.report_upload_tokens` 写一张 30 分钟有效的一次性票据（只存哈希，API 用户看不到这张表），Edge Function `report-upload` 核对票据后给出签名上传链接，用完即删。Supabase 的服务密钥始终留在 Supabase 里。

**运行条件**：

- `report.yml` 由 `workflow_run` 触发，只认默认分支（main）上的那份，所以 warehouse 分支要合进 main 才会每周自动跑。在 Actions 页面手动 Run workflow 可以随时补出某一期；补的是旧的一期时，`latest.json` 仍指向更新的那期。不填日期时取最近一个已收盘的周五（周五当天取上周五）。
- 两个 Edge Function 都以 `--no-verify-jwt` 部署，改了代码要重新部署：`supabase functions deploy report-upload --no-verify-jwt`、`supabase functions deploy warehouse-mcp --no-verify-jwt`。

## 图表

| 名称 / CLI 选项 | 输入与计算 | 展示内容 |
| --- | --- | --- |
| 跨资产走势 `trends` | 价格/指数 → 共同起点 = 100 | 1–6 个资产，线末直接标注 |
| 周涨跌幅排名 `returns` | 两日期价格比值 − 1 | 实际值深灰、重点资产钴蓝，涨跌带符号与三角 |
| 收益率曲线 `curve` | 两日各期限收益率，单位 % | 本周与上周曲线；期限等距排列 |
| 期限利差 `spread` | (10Y − 2Y) × 100 | 单位 bp，橙色标出倒挂区间 |
| 表现热力图 `heatmap` | 指定基准日至截止日的累计涨跌幅 | 最多四个区间，缺失数据为 – |
| 利率哑铃图 `comparison` | 两日各期限收益率 | 两端点、原始数值、变动 bp |

每张图导出 170 × 112 mm 的 **300 dpi PNG 和矢量 PDF**。另外合成一份 A4 竖版的**周报**（`weekly-report.pdf`）：首页深绿报头 + 本周概览，第二页为本期论点，其余为三栏数据页，每张图下附要点；数据库版十四张图约六页。中文字体已嵌入。图注标明单位、来源、观察截止日和数据更新时间。`examples/` 和 `--demo` 的数据都是模拟数据。

## 新增 Street 图库

| 选项 | 图表 | 输入 |
| --- | --- | --- |
| `drawdown` | 样本内从前高回撤 | 价格宽表 |
| `volatility` | 21期滚动年化波动率 | 日频价格宽表 |
| `rolling_correlation` | 60期滚动相关性 | 日频价格宽表 |
| `correlation` | 跨资产相关性矩阵 | 日频价格宽表 |
| `risk_return` | 年化算术均值 / 波动率散点 | 日频价格宽表 |
| `distribution` | 日收益直方图 | 日频价格宽表 |
| `candlestick` | K线与成交量 | `candlestick.csv` |
| `relative` | 相对基准表现 | 价格宽表 |
| `calendar` | 月度收益日历 | 日频价格宽表 |
| `flows` | 正负堆叠资金流 | `flows.csv` |
| `valuation` | 估值历史与输入参考带 | `valuation.csv` |
| `football` | Football Field 估值区间 | `football.csv` |
| `waterfall` | 财务变动桥接 / 瀑布图 | `waterfall.csv` |
| `sensitivity` | 情景敏感性矩阵 | `sensitivity.csv` |

每个选项导出同名 PNG/PDF，名称中的下划线转为连字符。K 线、资金流、估值带、Football Field、瀑布图和敏感性矩阵需要数据库里没有的表格（OHLC、基金流向、模型输出），只能用离线 CSV 出图。

## 离线出图（CSV / 模拟数据）

在仓库根目录运行（Python 3.12+）：

```bash
pip install -r pipeline/report/requirements.txt
python3 -m pipeline.report --demo --output-dir outputs/demo
```

`--demo` 默认生成全部二十张图。选择部分图表：

```bash
python3 -m pipeline.report --demo --charts curve spread --output-dir outputs/rates
python3 -m pipeline.report --demo --charts heatmap --output-dir outputs/heatmap
```

选定图表会按命令中指定顺序排版。输出目录内同名文件会被覆盖；不会删除之前其他图表的文件。建议每期或每种选择使用独立目录。

## 读取本地 CSV

生成完整二十图：

```bash
python3 -m pipeline.report --csv pipeline/report/examples/levels.csv --yields pipeline/report/examples/yields.csv --bundle pipeline/report/examples --metadata pipeline/report/examples/metadata.json --charts all --output-dir outputs
```

只画利率图，无需资产价格 CSV：

```bash
python3 -m pipeline.report --yields pipeline/report/examples/yields.csv --metadata pipeline/report/examples/metadata.json --charts curve spread comparison --output-dir outputs/rates
```

保留原有两图用法：

```bash
python3 -m pipeline.report --csv pipeline/report/examples/levels.csv --metadata pipeline/report/examples/metadata.json --output-dir outputs/assets
```

非 demo 模式未指定 `--charts` 时，默认生成 `trends returns`。

### 资产价格：levels.csv

```csv
date,美国股票,美国国债
2026-10-16,100,100
2026-10-23,101.84,99.52
```

支持 1–6 个资产，名称为 1–12 个字符。输入必须是正数价格或指数水平，不能把收益率或已计算的涨跌幅放进这个文件。日期不得重复，列名不得为空或重复。每个资产至少两个有效观察值。

走势从所有资产都有值的第一天归一为 100。中间缺失值保持为空，曲线断开。周涨跌幅 = `(终值 / 初值 − 1) × 100`，两日期必须相隔 7 天且都有数据。不自动选择替代交易日，不前向填充，不做币种转换。价格指数、总收益指数及是否复权会影响结果，请在来源中说明。

### 国债收益率：yields.csv

```csv
date,2Y,10Y,30Y
2026-10-16,3.72,4.17,4.55
2026-10-23,3.65,4.28,4.71
```

`4.25` 表示 **4.25%**。允许零或负利率。支持 `1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y`，自动按期限排序。每个期限至少两个有效值，禁止重复日期、空/重复列名及无穷数值。

收益率曲线和哑铃图使用元数据中的 `week_start` 与 `week_end`，这两天的所有期限必须有值。利差图至少需 `2Y`、`10Y` 两列且有两个共同有效日期；缺失值保持断线，最后有效观察日期单独注明。`1 bp = 0.01 个百分点`，因此 4.28% − 3.65% = 63 bp。

### 元数据：metadata.json

```json
{
  "source": "你的数据来源与口径",
  "updated_at": "2026-10-23T20:00:00Z",
  "as_of": "2026-10-23",
  "week_start": "2026-10-16",
  "week_end": "2026-10-23",
  "is_demo": false,
  "heatmap_starts": {
    "1W": "2026-10-16",
    "1M": "2026-09-23",
    "3M": "2026-07-23",
    "YTD": "2025-12-31"
  }
}
```

- `source` 为本次输入数据的来源，最多 50 字符；不同数据源可用简短汇总注明，或分次生成。
- `updated_at` 是数据更新时间，必须含时区，输出统一为 UTC。
- `as_of` 是截止日期，其后的观察值不会使用；`week_end` 必须与其相同。
- 示例数据保持 `is_demo: true`；替换成真实数据后才设为 `false`。
- `heatmap_starts` 仅画热力图时必需，最多四列，区间名称不超过六个字符。显式提供比较日期，截止日所有资产必须有数据。
- 基准日期不在数据中或个别资产缺失时，该单元格标为 `–`（短横线）。程序不会自动回退到其他日期。
- `YTD` 应使用上一年最后一个有效收盘观察日作为基准；区间标签由你指定，程序不会推断标签对应的日历规则。节假日需明确选择日期。
- 可选 `date_rule`：默认 `"exact"`（上面三条规则）；`"asof"` 改为取每个日期当天或之前 6 天内最近的值，数据库出刊用的就是它。
- 可选 `series_notes`：`{"黄金": "COMEX 期货近月代理"}`，每条不超过 40 字，自动附到画了该序列的图下。
- 可选 `quoted`：哪些资产的水平值有意义（如金价、指数点位）。不在列表里的资产（如 ETF 总回报指数）在首页概览只显示周涨跌幅。默认全部资产。
- 可选 `omitted`：本期未列入的序列说明（字符串列表），印在首页页脚和数据说明里。

## 输出与样式

原有六图输出包含 `weekly-report.pdf`，以及下列六个文件名各自对应的 `.png`、`.pdf`：

- `cross-asset-trends`
- `weekly-returns`
- `yield-curve`
- `yield-spread`
- `performance-heatmap`
- `rate-comparison`

`charts.py` 管理颜色、字号、毫米排版及导出；`extra_charts.py` 是利率与热力图面板；`data.py` 和 `rates.py` 分别负责价格与利率/区间计算；`street_data.py` 和 `street_charts.py` 管理 Street 扩展；`weekly.py` 排周报版式；`source.py` 从数据库取数，`build.py` 出刊，`publish.py` 上传与下载；`cli.py` 是命令行入口。

视觉参考：Python Graph Gallery 的[线末直接标注](https://python-graph-gallery.com/web-line-chart-with-labels-at-line-end/)。全部绘图与排版在本地重新实现。

## 视觉规范

图表样式遵循 **Richard Wei Finance** 设计系统（财经报纸的克制风格：细线分隔、无阴影、直角、墨色为主，加上 IBCS 报告记号）。所有色值、字号和间距集中在 `charts.py` 顶部，与设计系统的 tokens 一一对应。

- **品牌色**：深绿 `#102820` 只出现在周报首页报头和每页页眉的报名上，从不用于图表数据。
- **颜色**：约九成是墨色 `#141414`、次级墨色 `#5e5e5e`、白底和细线。钴蓝 `#1e3bd6` 是唯一的强调色，只标出一张图所讲的那一条序列或那一个项目（每张图最多一处，每页最多两处）。
- **IBCS 记号**：实际值为深灰实心 `#333333`，上一期为浅灰 `#8a8a8a`，区间为 `#c9c9c9` / `#e1e1e1`。例如收益率曲线中本周为深灰、上周为浅灰；Football Field 的估值区间为浅灰条。
- **重点资产**：元数据 `highlight` 列出 1–2 个资产（默认取 `focus_asset`，否则取首列）。第一个为钴蓝，第二个为深灰实线，其余为浅灰细线；线末直接标注名称和数值，文字始终用墨色。同一资产在各图中颜色一致。
- **涨跌**：默认青色涨、橙红跌（`#00766e` / `#b93d0a`，取自色盲友好的 Okabe–Ito 色板）。在元数据设 `"market_colors": "cn"` 即切换为红涨绿跌。带颜色的涨跌数字一律同时带正负号和 ▲▼，颜色不是唯一线索。瀑布图使用"有利 / 不利"（青 / 橙红），这组颜色不随市场切换。
- **标题说结论**：每张图的大标题由数据自动生成一句结论（如"黄金累计上涨 28.6%，美元指数下跌 2.2%"），上方小字是图表类别，下方一行写单位与期间。想自己写标题，在元数据加 `"titles": {"trends": "……"}`（每条 1–30 字）。
- **要点（Takeaway）**：周报里每张图下方的要点也由数据生成，只写事实和数字，不加判断。要写自己的观点，用 `"takeaways": {"trends": {"heading": "黄金领先", "text": "……"}}`（正文 1–120 字）。
- **数字**：涨跌幅 1 位小数，价格和指数水平 2 位，收益率 2 位，bp 0 位；千分位分隔；负号用真正的减号「−」；变动值带正负号，水平值不带；缺失值显示「–」。日期写作「2026年10月23日」，坐标轴写「1月 / 4月」。
- **单图版式**：每张图上方一条粗细线，没有边框、卡片和阴影；只保留横向网格；来源和时间在图下方。
- **周报版式**（`weekly-report.pdf`，按设计系统的 Weekly Commentary）：
  - **首页**：顶部是品牌深绿 `#102820` 报头（全刊唯一一处大面积绿色），下面一排三个概览指标（重点资产、本周涨幅第一、10Y 收益率），再往下是图表。
  - **论点页**（第二页，每期一页）：本周主要结论用 36 pt 大标题，一张大图占两栏，第三栏放"证据"（要点 + 关键数值表）。默认用所选的第一张图，元数据 `"thesis": "curve"` 可指定，`false` 关闭；少于 4 张图时不出论点页。
  - **数据页**：三栏，栏间细线，图跨栏的位置断开；每张图按内容占 1–3 栏，自动排版、尽量填满每页。每张图下方紧跟一段要点（加粗小标题 + 一两句数字），再下面是来源。
  - **页眉**写报名（品牌绿）和日期、周次；**页脚**写数据更新时间、DEMO 标记和页码。
  - 设计系统的报告页是 US Letter，这里保留 A4 以便国内打印。
- **字体**：标题用衬线体 Newsreader（英文与数字）+ Noto Serif SC（中文）；其余用 Public Sans（英文与数字）+ Noto Sans SC（中文）。Public Sans 已固化等宽数字（文件名带 TF），保证数字列对齐。全部字体随项目提供，均为 SIL Open Font License，许可证见 `assets/fonts/`。中文字体按 GB2312 常用字子集化（6,763 个汉字），标题、要点或资产名里出现字体没有的字时会直接报错，不会印成方框。

## 验证

```bash
python3 -m unittest discover -s pipeline/report/tests -t .
```

覆盖归一化、缺失值、百分比/bp 计算、期限排序、非法输入、截点日期规则、最新版本取数、代理与观察日说明、未列入序列、存储权限与上传顺序、PNG 分辨率、A4 页面尺寸及完整/选择性导出。测试全部离线，用 SQLite 假数据库，不访问网络。交付前用 Poppler 渲染 PDF 检查排版和字体嵌入。

## Street 扩展数据规范

金融计算图要求按交易观察日排列的**日频收盘价格/指数**，`annualization` 默认 252。程序不猜交易所日历；输入端必须提供完整观察日序列，缺失价格显式留空，不能删掉整日行后当作连续日收益。收益由相邻行计算，缺失值不会填充。年度交易日不同可显式配置年化因子。

```json
{
  "focus_asset": "美国股票",
  "benchmark": "美国股票",
  "highlight": ["美国股票", "黄金"],
  "market_colors": "global",
  "titles": {},
  "takeaways": {},
  "thesis": "trends",
  "correlation_pair": ["美国股票", "美国国债"],
  "annualization": 252,
  "chart_units": {
    "candlestick": "USD / 股；成交量：股",
    "flows": "USD bn",
    "valuation": "远期 P/E（倍）",
    "football": "USD / 股",
    "waterfall": "USD mn",
    "sensitivity": "USD / 股；列为 WACC"
  }
}
```

将这些字段合并到现有 metadata 中。`highlight` 为 1–2 个需要突出的资产名称（第一个钴蓝、第二个深灰），必须是资产列之一；不填时默认突出 `focus_asset`。`market_colors` 为 `"global"`（默认，青涨橙红跌）或 `"cn"`（红涨绿跌）。`titles` 可按图表名覆盖自动生成的结论标题，`takeaways` 覆盖周报里的要点，`thesis` 指定论点页用哪张图（`false` 关闭）。前两个资产选项默认首列，滚动相关性默认前两列。读取附加表格时，在 `chart_units` 中填写选中图表的真实单位。`source` 和 `updated_at` 描述本次整批数据；有不同来源/更新时间应分次导出，不能沿用示例元数据。

- 波动率：21 个完整收益观察值，样本标准差（ddof=1），乘年化因子平方根。
- 滚动相关性：60 个完整收益观察值，Pearson r；资产收益为常数时无定义，不伪造为零。
- 相关性矩阵与风险收益散点：至少20个所有资产共同有效的收益观察值。散点纵轴为算术日收益均值乘年化因子，**不是 CAGR**。
- 回撤：相对输入历史中的累计前高，不包含输入之前的峰值。
- 相对表现：资产/基准价格比值，再将共同起点设为100；不是 RSI，也不是专有 JdK RRG。
- 月度日历：取每月最后一行观察值，与上月末比较；不填充缺失月。首个观察月无上月基准，与样本外月份一样留空；样本内缺失显示 –；当前月为月内至今。最多显示最近8年，不把单年数据称作季节性规律。

附加文件都放在 `--bundle` 指定目录，包含需要的文件即可。所有日期表会先按 `as_of` 截断；日期必须唯一，数字不能缺失或无穷，CSV 列名不能为空或重复。

| 文件 | 必需列 | 约束 |
| --- | --- | --- |
| `candlestick.csv` | date, open, high, low, close, volume | OHLC 为正且 low≤open/close≤high；volume≥0。成交量输入原始单位，轴除以一百万显示。最近60行。 |
| `flows.csv` | date, 1–4个类别列 | 每类同一金额单位；最多24期。正负分别堆叠，黑点表示净和。 |
| `valuation.csv` | date, actual, lower, upper | lower≤upper；参考带直接读入，不计算置信区间。 |
| `football.csv` | label, low, high | 1–8个方法；low≤high；统一 EV、股权价值或每股价值口径。 |
| `waterfall.csv` | label, value, kind | 3–8行；首尾 kind=total，中间=change；严格核对期初+变动=期末。 |
| `sensitivity.csv` | scenario, 各列假设 | 1–8行、1–7数值列；输入已有模型输出，不运行 DCF。 |

表格标签须唯一，长度1–12。目录 `examples/` 提供所有格式的模拟实例。真实估值图中的低/高端范围、增长率和折现率结果由你的模型提供；程序只负责校验与展示。

只画投行类图表：

```bash
python3 -m pipeline.report --bundle pipeline/report/examples --metadata pipeline/report/examples/metadata.json --charts football waterfall sensitivity --output-dir outputs/banking
```

只画风险图：

```bash
python3 -m pipeline.report --csv pipeline/report/examples/levels.csv --metadata pipeline/report/examples/metadata.json --charts drawdown volatility rolling_correlation correlation risk_return --output-dir outputs/risk
```

敏感性矩阵默认保留两位小数；可在元数据中设置 `sensitivity_decimals`（0–6）调整精度。表头与数值按同一列顺序绘制，`scenario` 列不必位于第一列。
