# Capital Weekly 数据后端结构指南

## 1. 仓库边界

本仓库只负责市场数据，不负责网页界面。顶层只有两个可见业务目录：

```text
market data/
├── pipeline/
│   ├── internal/         # 实现、脚本、测试与历史工程文档
│   ├── config.json       # 五条管线的统一配置
│   ├── indices.py        # 股指公开入口
│   ├── sectors.py        # 跨市场行业公开入口
│   ├── gics.py           # GICS 公开入口
│   ├── macro.py          # 宏观资产公开入口
│   ├── context.py        # 周度背景公开入口
│   ├── refresh.py        # 唯一协调发布入口
│   └── requirements.txt  # Python 依赖
└── output/
    ├── indices.json
    ├── sectors.json
    ├── gics.json
    ├── macro.json
    ├── context.json
    └── release.json
```

未来前端必须放在独立仓库，通过六个固定 JSON 文件消费数据。本仓库内
不得重新创建前端、历史周选择器或日期命名的发布目录。

## 2. 数据与发布原则

- 正式窗口为周一至周日，时区为 `Asia/Hong_Kong`。
- 任何快照收益或派生值都必须先应用 `as_of_date`。
- 五条管线全部成功并通过源表校验后，才构建稳定 JSON。
- `release.json` 最后写入，并哈希五个业务文件。
- `output/` 与 `pipeline/.cache/` 作为一个回滚单元替换。
- 失败刷新不改变当前输出，也不改变最近成功缓存。
- 缺失 JSON 数据使用 `null`；拒绝 `NaN`、`Infinity` 和 `-Infinity`。
- 可选 context 表可为空，但集合名称和标准结构不能消失。
- 每条业务记录保留来源 URL、观测日期、单位和 QC/来源状态。
- 测试不运行真实网络刷新。

## 3. 核心实现

### 市场数据模块

| 模块 | 职责 |
| --- | --- |
| `internal/capital_weekly/equity_indices.py` | 多提供方全球股指历史、时间截断和收益快照。 |
| `internal/capital_weekly/equity_sectors.py` | A 股、港股、美股行业数据和抓取审计。 |
| `internal/capital_weekly/gics_sectors.py` | 美国 GICS 行业 ETF 代理。 |
| `internal/capital_weekly/macro_assets.py` | 固收、政策利率、货币市场、外汇、商品和登记派生序列。 |
| `internal/capital_weekly/sector_divergence.py` | 行业排名、广度和分化。 |
| `internal/capital_weekly/macro_divergence.py` | 宏观分组排名和分化。 |
| `internal/capital_weekly/history.py` | `as_of_date` 历史截断。 |
| `internal/capital_weekly/returns.py` | 日、周、MTD、YTD 变化。 |

### 周度背景模块

`internal/capital_weekly/weekly_context.py` 协调提供方并保留空表标准结构。
`internal/capital_weekly/context/` 将事件、经济发布、金融条件、波动率、市场内部、
交易所微观结构、持仓、公司事件和商品基本面分成职责单一的模块。

提供方通过 `provider_contracts.py` 和 `providers.py` 注册。新增提供方时，
不要把解析逻辑堆进协调器；应创建聚焦模块，并同时更新来源状态契约和
确定性测试。

### 发布模块

`internal/capital_weekly/weekly_release.py` 是发布契约的单一事实来源，负责：

1. 计算最近已结束的周窗口。
2. 生成五条公开模块命令。
3. 校验中间 CSV 的表头、日期、数值、来源、QC 与状态。
4. 将 CSV 转成严格类型的五个 JSON envelope。
5. 构建并校验 `release.json` 的身份、文件大小和 SHA-256。
6. 成对替换 `output/` 与 `pipeline/.cache/`，失败时同时回滚。

`pipeline/refresh.py` 是正式入口。单管线模块只用于诊断，不能独立发布。

## 4. 统一配置

`pipeline/config.json` 是唯一配置文件，包含：

- `indices`
- `sectors`
- `gics`
- `macro`
- `context.cftc_contracts`
- `context.company_watchlist`
- `context.eia_series`
- `context.financial_conditions`
- `context.yahoo_volatility`

配置行保持字符串、字段名和顺序。各领域加载器只在使用时转换
`sort_order` 等类型。`pipeline/internal/common.py` 保留显式临时 CSV 路径兼容，
用于测试和单次诊断，不代表生产配置可以重新分散成 CSV。

## 5. 稳定输出契约

五个业务文件都包含：

```json
{
  "schema_version": "1.0",
  "release_id": "...",
  "as_of_date": "2026-08-09",
  "pipeline": "indices",
  "status": "complete",
  "tables": {},
  "source_log": []
}
```

| 文件 | `tables` 集合 |
| --- | --- |
| `indices.json` | `indices` |
| `sectors.json` | `sectors`, `divergence` |
| `gics.json` | `sectors` |
| `macro.json` | `fixed_income`, `policy_rates`, `money_market`, `foreign_exchange`, `commodities`, `divergence` |
| `context.json` | `events`, `economic_releases`, `financial_conditions`, `market_internals`, `positioning_flows`, `company_events`, `commodity_fundamentals` |

`source_log` 始终在 envelope 的顶层。`release.json` 包含五个文件的行数、
字节数和 SHA-256，不包含自身哈希。

Commodity Research V2 使用 `dataset_contract_version: 3`，但仍只发布以上六个
固定文件。它增加三个由后端校验的表：

- `macro.json.tables.commodity_price_history`
- `context.json.tables.commodity_metric_history`
- `context.json.tables.commodity_research_facts`

三个表分别保存有界的官方价格历史、实物/持仓指标历史，以及可由已发布
`input_record_ids` 复算的登记事实。当前 contract 2 发布仍可读取；协调刷新只会在
三个 V2 表、19 个商品代码、七个商品家族和跨表关系全部通过校验后发布 contract 3。

## 6. 运行时目录

运行时内部状态全部隐藏在 `pipeline/`：

| 路径 | 内容 |
| --- | --- |
| `pipeline/.state/refresh.lock` | 单飞锁。 |
| `pipeline/.state/status.json` | 原子更新的运行状态。 |
| `pipeline/.staging/<job>/` | 当前任务的周源表、输出和缓存 staging。 |
| `pipeline/.cache/` | 最近一次成功发布的原始响应，仅保留一代。 |

成功或回滚后不得留下 staging 或 backup 目录。不要在仓库顶层新建
`outputs/`、`tmp/`、`deploy/`、手工导出或前端目录。

每次成功刷新会整体替换 `.cache/`：根目录只有 `cache.json` 与
`indices/`、`sectors/`、`gics/`、`macro/`、`context/` 五个领域目录，
不保留日期目录、历史目录或上一代文件。任何必需来源失败都会保留旧 output 与
旧 cache 的字节内容，并删除本次 staging。

所有配置的官方商品 HTTP GET 使用同一有界执行器。连接、读取、总时限、最大尝试
次数、退避和 `Retry-After` 上限都来自 `pipeline/config.json`；只重试传输错误、
HTTP 408/425/429 和 5xx，不重试 schema、身份、单位、新鲜度、时间点或覆盖校验。
刷新状态始终保留失败的 pipeline；只有可信的必需 `weekly_context`
`source_log` 失败才会保留 provider、phase、实际 attempts 与稳定
`error_code`。宏观子进程失败不会猜测这些来源字段，而是保持为 `null`。
状态不写入凭证、原始响应正文或不受控诊断文本。

## 7. 命令

安装与正式刷新：

```bash
python3 -m pip install -r pipeline/requirements.txt
python3 -m pipeline.refresh
python3 -m pipeline.refresh --as-of-date 2026-08-23
```

从旧数据做一次无网络初始化：

```bash
python3 -m pipeline.refresh --from-existing /path/to/legacy/outputs
```

单管线诊断：

```bash
python3 -m pipeline.indices --as-of-date 2026-08-23 --output-dir /tmp/indices
python3 -m pipeline.sectors --as-of-date 2026-08-23 --output-dir /tmp/sectors
python3 -m pipeline.gics --as-of-date 2026-08-23 --output-dir /tmp/gics
python3 -m pipeline.macro --as-of-date 2026-08-23 --output-dir /tmp/macro
python3 -m pipeline.context --start-date 2026-08-17 --end-date 2026-08-23 --output-dir /tmp/context
```

只读 EIA 官方来源探针：

```bash
python3 -m pipeline.internal.scripts.probe_commodity_sources \
  --config pipeline/config.json --as-of 2026-08-23 --provider eia
```

探针只检查官方 metadata、配置身份与最近可用页，输出经过清理的 JSON，不调用
协调器，也不写 `output/`、`.cache/`、`.staging/` 或状态文件。World Bank
workbook/page、CFTC TFF/Disaggregated、CME metals、USGS 与 USDA 文档/凭证检查
复用各自现有官方传输和解析器；它们同样是发布前只读诊断，不能替代完整协调刷新。

## 8. Commodity Research V2 消费契约

未来独立前端把新增表组合为六个界面：Overview、Natural Gas、Refined Products、
Copper、Gold 和 Agriculture。界面只能按明确的 `commodity_code`、
`commodity_family`、series/metric/fact 字段组合数据；不得解析标签、在浏览器重算
研究公式、发明信号或用旧数据填补缺口。价格、实物和持仓各自显示观测日期、
`known_as_of`、来源 URL、QC/来源状态与 release 身份。每个图表必须有等价表格，
缺失、未配置、抓取失败、过期与筛选无结果保持不同事实状态。

## 9. 测试与修改位置

```bash
python3 -m unittest -v
node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs
python3 -c 'from pathlib import Path; from pipeline.internal.capital_weekly.weekly_release import validate_output_bundle; validate_output_bundle(Path("output"))'
```

常见修改位置：

- 资产或提供方范围：`pipeline/config.json` 与 `test_pipeline_config.py`。
- 单一数据源解析：对应领域模块和同名测试。
- 收益与分化：`returns.py`、`sector_divergence.py`、
  `macro_divergence.py`。
- JSON 表或发布身份：`weekly_release.py`、
  `test_latest_json_output.py` 和 `test_capital_weekly_weekly_release.py`。
- 离线初始化：`refresh.py` 与 `test_offline_output_migration.py`。
- 顶层结构：`test_workspace_layout.py`。

修改行为时先写失败测试，再实现，先跑聚焦模块，最后跑全套。正式网络
刷新需要明确授权；常规验证只使用假运行器和本地夹具。
