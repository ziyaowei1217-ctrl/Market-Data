# 市场一周（pipeline/report）

把 Capital Weekly 数据库画成每周的《市场一周》A4 周报。版式完全按 Richard Wei Finance 设计系统：周报直接用设计系统自带的页面与图表组件（`ds/`）在无头 Chromium 里排版、打印成 PDF。每周六数据库更新成功后，GitHub Actions 自动出刊，存进 Supabase 的私有存储，只有读者名单内的账号能下载；读者的 AI 助手也能通过数据库连接器直接拿到本期 PDF 和单图。

同一套计算也能离线使用：给本地 CSV（或 `--demo` 模拟数据）就能出周报和单张图表，不需要网络和账号。

## 每周自动出刊

```
周六 13:17 UTC  warehouse 工作流取数 ──成功──▶ report 工作流
                                              ├─ python -m pipeline.report build    从数据库取数、画图、排版
                                              └─ python -m pipeline.report publish  上传到 Storage 的 reports 桶
读者：python3 -m pipeline.report latest  或在 AI 助手里用连接器的 weekly_report 工具
```

**每期的结构**（设计系统 Weekly Commentary 的固定顺序，栏目页标题不变、栏目内标题陈述发现）：

| 页 | 栏目 | 内容 |
| --- | --- | --- |
| 01 | 封面 | 两行标题（引题 + 深绯主标题）与导语；本周要点、本周走势图对、年初至今；右栏关键数字、数据口径、本期内容 |
| 02 | 市场仪表盘 | 资产表现柱状图（年初至今、近 1 个月、本周）、两组一年走势、各期涨跌幅表 |
| 03 | 风险与相关 | 距一年高点回撤、21 日年化波动率、60 日滚动相关系数，每段文字在左、图在右 |
| 04 | 固定收益 | 收益率曲线、10Y−2Y 利差、各期限变动表（无收益率数据时省略本栏） |
| 05 | 来源与方法 | 覆盖范围、每个序列的来源与最新观察日、日期规则、缺口，发布方、发布时间、信息来源与风险提示 |

每张图下写「来源：…；截至某日。」，含代理序列的图提示见「来源与方法」；有业绩数字的页面底部以正文字号写「过往业绩并不预示未来表现。市场有风险，投资需谨慎。」。全刊只陈述数据，不写观点或预测；需要写自己的封面标题时，在元数据里加 `"cover": {"lead": "引题", "title": "主标题", "lede": "导语"}`。

**本期画什么**写在 `issue.json`：六个资产（名称、序列、来源说明、是否代理、是否有市场报价）、五个美债期限，以及样式（重点资产、相关性对象、两组走势面板、红涨绿跌）。改资产只改这个文件；序列键必须在 `pipeline/warehouse/catalog/series.csv` 里，代理序列的 `note` 必须以「代理」结尾，测试会检查。

**日期规则**（元数据 `date_rule: "asof"`）：周度截点为周五，与数据库一致。每个序列取截点当天或之前最近的一个观察值，最多往前找 6 天；节假日沿用前一交易日收盘（最多 3 个工作日），序列末端不往后补。所以 FRED 收益率只到周四时，图里用周四的值，并注明「截至10月22日」。离线 CSV 仍要求两个日期都存在（`exact`）。

**数据说明**：用了代理序列、或者没更新到周五的序列，会写进周报最后的「数据说明」，周报里每张相关的图在来源行提示「代理与观察日见末页数据说明」；单独导出的 PNG/PDF 则把说明直接写在图下。离截点超过 6 天都没有数据的序列这一期不画，首页页脚和数据说明里写明「本期未列入：黄金（最新数据为10月9日）」。

**自己出一期**（需要数据库连接串，或读者账号）：

```bash
pip install -r pipeline/report/requirements.txt
export WAREHOUSE_DB_URL=...            # 或者 WAREHOUSE_EMAIL / WAREHOUSE_PASSWORD（读者账号，走 REST）
python3 -m pipeline.report build --week 2026-10-23 --output-dir outputs/weekly
```

输出目录里有 `weekly-report.pdf`、每个图表块一张 PNG（标题、图、来源一起，3 倍分辨率），以及 `issue.json`（截点、页数、图表、未列入、数据说明）。不连数据库也能出一期样张：`python3 -m pipeline.report build --demo --output-dir outputs/demo`。

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
| 周涨跌幅排名 `returns` | 两日期价格比值 − 1 | 其余为灰、重点资产深绯，涨跌带符号与三角 |
| 收益率曲线 `curve` | 两日各期限收益率，单位 % | 本周与上周曲线；期限等距排列 |
| 期限利差 `spread` | (10Y − 2Y) × 100 | 单位 bp，橙色标出倒挂区间 |
| 表现热力图 `heatmap` | 指定基准日至截止日的累计涨跌幅 | 最多四个区间，缺失数据为 – |
| 利率哑铃图 `comparison` | 两日各期限收益率 | 两端点、原始数值、变动 bp |

离线工具里每张图导出 170 × 112 mm 的 **300 dpi PNG 和矢量 PDF**（matplotlib，配色与字体取自同一设计系统）；资产不少于两个时，同一目录还会生成上面那份 A4 周报（`weekly-report.pdf`）。中文字体已嵌入。图注标明单位、来源、观察截止日和数据更新时间。`examples/` 和 `--demo` 的数据都是模拟数据。

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
python -m playwright install chromium        # 周报排版用；只出单图可以不装
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

`charts.py` 管理颜色、字号、毫米排版及导出；`extra_charts.py` 是利率与热力图面板；`data.py` 和 `rates.py` 分别负责价格与利率/区间计算；`street_data.py` 和 `street_charts.py` 管理 Street 扩展；`issue.py` 生成周报内容（数据与中文文字），`render.py` 用 `ds/` 里的设计系统组件在 Chromium 中排版并打印；`source.py` 从数据库取数，`build.py` 出刊，`publish.py` 上传与下载；`cli.py` 是命令行入口。`ds/README.md` 记录组件的来源版本和三处本地修补。

视觉参考：Python Graph Gallery 的[线末直接标注](https://python-graph-gallery.com/web-line-chart-with-labels-at-line-end/)。全部绘图与排版在本地重新实现。

## 视觉规范

全部取自 Richard Wei Finance 设计系统（weekly.md、charts.md、writing.md、tokens.css）：

- **页面**：A4 竖版，左右页边 0.51 in，正文宽 7.25 in；页眉左为刊名「市场一周」（深绯），右为日期 · 栏目，下压 0.75 pt 细线；封面在细线左端加一段深绯短线。正文从 1.567 in 起、排到 10.85 in 的底线；页码两位数，奇数页靠右、偶数页靠左。没有色块、卡片、阴影和竖分隔线，栏与栏之间只留白。
- **颜色**：白底，正文炭黑 `#312f2a`，次级文字 `#56534d`，三种粗细的线。深绯 `#8d303a` 只用于小处：刊名、封面主标题第二行、小标签、目录页码，以及每张图唯一的主角序列和它的末端数值。第一条对比序列灰 `#8d8a83`，第三条墨色细线。涨跌只出现在带正负号和三角的数字上：中文版红涨绿跌（`market_colors: "cn"`），美股习惯为青涨朱跌。霁蓝 `#234993` 只用于链接，浅霁蓝底标出表格中的重点行。
- **标题**：栏目页标题是固定栏目名；每个分段（band）的标题陈述发现；图表标题写度量（加粗），逗号后写期间与单位（次级色）。
- **字体**：标题 Newsreader + Noto Serif SC（粗体），其余 Public Sans + Noto Sans SC；正文 9.5/12 pt，图表标题 8.75 pt，表格与来源 7.5/10.75 pt，页眉与小标签 7 pt 粗体。全部字体随项目提供（SIL Open Font License，见 `assets/fonts/`）。中文字体按 GB2312 常用字子集化（6,763 个汉字），资产名或标题里出现字体没有的字时直接报错，不会印成方框。
- **填满版面**：每页先让可伸缩的图表长高，再把分段间距均分到 23–67 px，使内容结束在底线；放不下的分段移到下一页，栏目标题不变。

## 验证

```bash
python3 -m unittest discover -s pipeline/report/tests -t .
```

覆盖归一化、缺失值、百分比/bp 计算、期限排序、非法输入、截点日期规则、最新版本取数、代理与观察日说明、未列入序列、周报结构与数字核对、每张图的来源与唯一主角、风险提示、A4 页面不溢出、存储权限与上传顺序、PNG 分辨率及完整/选择性导出。测试全部离线（用 SQLite 假数据库，排版用本机 Chromium），不访问网络。交付前用 Poppler 渲染 PDF 逐页检查。

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

将这些字段合并到现有 metadata 中。`highlight` 为 1–2 个需要突出的资产名称（第一个深绯、第二个墨色），必须是资产列之一；不填时默认突出 `focus_asset`。`market_colors` 为 `"global"`（默认，青涨橙红跌）或 `"cn"`（红涨绿跌）。`titles` 可按图表名覆盖单图自动生成的结论标题；`cover` 覆盖周报封面的引题、主标题和导语。前两个资产选项默认首列，滚动相关性默认前两列。读取附加表格时，在 `chart_units` 中填写选中图表的真实单位。`source` 和 `updated_at` 描述本次整批数据；有不同来源/更新时间应分次导出，不能沿用示例元数据。

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
