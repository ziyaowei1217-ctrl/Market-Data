# Capital Weekly Market Data

这是 Capital Weekly 的市场数据后端。工作区只保留两个可见业务目录：

```text
market data/
├── pipeline/   # 五条公开管线入口；维护文件集中在 internal/
└── output/     # 最近一次完整成功发布的固定 JSON 文件
```

本仓库不包含前端。未来前端应作为独立的相邻仓库创建，并只读取
`output/` 的稳定契约。

## 五条管线与固定产出

| 管线入口 | 固定产出 | 主要内容 |
| --- | --- | --- |
| `python3 -m pipeline.indices` | `output/indices.json` | 20 个全球股指与来源日志 |
| `python3 -m pipeline.sectors` | `output/sectors.json` | 34 个 A/H/美股行业、分化与来源日志 |
| `python3 -m pipeline.gics` | `output/gics.json` | 11 个美国 GICS 行业代理与来源日志 |
| `python3 -m pipeline.macro` | `output/macro.json` | 固收、政策利率、货币市场、外汇、商品与分化 |
| `python3 -m pipeline.context` | `output/context.json` | 事件、经济发布、金融条件、市场内部、持仓与可选背景 |

`output/release.json` 最后写入，记录共同的 `release_id`、截止日期、
五条管线状态，以及五个业务 JSON 的 SHA-256。消费者只有在六个文件
齐全、发布身份一致且哈希全部匹配时才能接受这一代数据。

刷新不会创建带日期的新目录。完整验证成功后，它会覆盖同名的六个
文件；任何抓取、清洗、验证、输出替换、缓存替换或最终状态写入失败，
都会保留上一代 `output/` 和上一代缓存不变。

## 安装与配置

要求 Python 3.10 或更新版本。Node.js 只用于保留的工作簿兼容测试。

```bash
python3 -m pip install -r pipeline/requirements.txt
```

所有资产范围和提供方设置已合并到 `pipeline/config.json`。JSON 中的
配置值保留为字符串，由各管线在读取后转换所需类型。不要重新拆成多份
CSV；新增配置时应同时保留唯一身份、单位、提供方和来源元数据。

可选环境变量：

- `EIA_API_KEY`：启用 EIA 商品基本面提供方；缺失时记录
  `NOT_CONFIGURED`。
- `SEC_USER_AGENT`：启用公司 watchlist 的 SEC 请求；值应包含机构和
  联系方式。

凭证不得写入仓库。Yahoo 波动率信号属于可选的本地研究数据源，失败会
进入来源日志，但不会静默伪造数据。

## 正式刷新

运行五条管线，应用最近一个已结束周日的时间截断，清洗、验证并原位发布：

```bash
python3 -m pipeline.refresh
```

重现一个已经结束的周日：

```bash
python3 -m pipeline.refresh --as-of-date 2026-08-23
```

正式刷新会访问公开数据源。除非明确需要，不要为了测试运行真实刷新。
自动化测试全部使用确定性夹具、假历史和假运行器。

运行状态位于 `pipeline/.state/status.json`，单飞锁位于
`pipeline/.state/refresh.lock`。中间数据只出现在
`pipeline/.staging/`，成功后会清理。最近一次成功的原始响应保存在
`pipeline/.cache/`，下一次成功刷新会整体替换它，不累计历史缓存。

## 无网络离线初始化

仅在从旧工作区一次性初始化时使用：

```bash
python3 -m pipeline.refresh --from-existing /path/to/legacy/outputs
```

该命令只扫描名称严格匹配 `week_YYYYMMDD-YYYYMMDD` 的直接子目录，
要求 manifest 完整、日期自洽、源文件哈希一致，并重新运行发布校验。
它跳过失败周、草稿、临时导出、损坏目录和符号链接，不调用任何数据
提供方，也不联网。

## 单管线诊断

单管线入口用于定位某一数据域的问题，不能直接替换正式 `output/`。
诊断时应把临时结果写到系统临时目录或 `pipeline/.staging/`：

```bash
python3 -m pipeline.indices \
  --as-of-date 2026-08-23 \
  --output-dir /tmp/capital-weekly-indices
```

其余入口为 `pipeline.sectors`、`pipeline.gics`、`pipeline.macro` 和
`pipeline.context`。这些命令可能访问真实公开数据源。

## 验证

```bash
python3 -m unittest -v
node --test pipeline/internal/tests/test_verify_weekly_workbooks.mjs
python3 -c 'from pathlib import Path; from pipeline.internal.capital_weekly.weekly_release import validate_output_bundle; validate_output_bundle(Path("output"))'
```

发布数据遵循以下原则：先应用 `as_of_date`，缺失值使用 `null`，拒绝
`NaN` 和无穷值，保留单位、观测日期、来源 URL 与 QC/来源状态。可选
context 集合即使为空也保留其数组名称。

公开提供方可能改变结构、延迟观测或限制自动请求。GICS 行业使用可交易
ETF 代理，不等同于官方指数值。使用或再分发前应确认来源许可。本项目是
研究数据工具，不构成投资建议。

## License

MIT，见 `LICENSE`。
