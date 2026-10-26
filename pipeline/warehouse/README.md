# Capital Weekly 数据库（warehouse）

把《全球资管周报｜数据采集清单》变成一个能共享、能让 agent 直接查询画图的数据库。
数据存在 Supabase（Postgres），每周六由 GitHub Actions 自动抓取和计算。

和现有五条管线（`pipeline.indices` 等，输出 `output/*.json`）互不影响：
那边每周覆盖最新一期 JSON；这里按发布版本保存历史，并累积周度序列。

## 数据在哪、怎么查

| 表/视图 | 内容 |
| --- | --- |
| `catalog` | 指标目录 + 采集方式（`method`）+ 覆盖范围（`first_week`/`last_week`） |
| `weekly` | 每周五截点的指标值，含名称、单位、`obs_date`（实际观察期）、`status` |
| `latest_week` | 最近一周的全部指标 |
| `obs_latest` | 原始序列最新版本（日/周/月/季原始频率） |
| `observations` | 原始序列全部版本：`realtime_start` 为该值开始可知的日期 |
| `series` | 原始序列登记：数据源、代码、单位、最近抓取状态 |
| `fetch_log` | 每次抓取的逐条结果 |

常用查询：

```sql
-- 某个指标近两年的周度序列（画图）
select week_cutoff, value from weekly
where indicator_id = '12-007' and status = 'ok' and week_cutoff >= current_date - 730
order by week_cutoff;

-- 本周所有利率信用类指标
select indicator_id, name, value, unit, obs_date from latest_week where module = '利率信用';

-- 找指标
select indicator_id, name, unit, method, coverage_note from catalog where name ilike '%CPI%';
```

`status` 含义：`ok` 正常；`missing_input` 原始数据缺失；`insufficient_history`
历史不够（如 3 年分位）；`no_vintage` 需要发布版本但尚未记录（"前值""修订"类指标，
本库从开始运行起逐次留存，或配置 `FRED_API_KEY` 后由 ALFRED 补齐）；`error` 计算出错。
缺失一律为 NULL，不用 0 代替。

## 采集方式（`indicators.method`）

| method | 数量 | 说明 |
| --- | ---: | --- |
| `api` | 1066 | 免费官方/行情接口直取或派生（FRED、财政部、纽约联储、BLS、BEA、EIA、CFTC、ECB、Eurostat、ONS、加拿大统计局、德国央行、BIS、瑞士央行、日本财务省/统计局、中国国家统计局、LBMA、MSCI、FactSet、ISM、Cboe、Yahoo 等） |
| `proxy` | 139 | 同样按公式计算，但用替代来源：跟踪该指数的 ETF 总回报（股息再投资，2020-10-01=100）或同类指数（如 ICE BofA 代替 Bloomberg 高收益）；`coverage_note` 以「代理：」开头写明替代品 |
| `report` | 249 | 只在机构周报里出现的数字（如高盛估值图、FactSet 未覆盖的一致预期），每周归档原文（私有表），解析器建设中 |
| `manual` | 45 | 事件、日期、央行决议等，人工维护 |
| `pending` | 326 | 暂无免费来源或待接入，原因写在 `coverage_note` |
| `excluded` | 134 | 机构预测与长期资本市场假设，按需求排除 |

画图或比较时，`proxy` 指标与原指数在费率、成分上限、对冲口径上可能有差异，必要时在图注里写明。

Yahoo Finance 是免费延迟行情（非官方接口），只用于没有免费官方来源的指数点位，
`coverage_note` 中逐条注明。ICE BofA 利差在 FRED 只有约 3 年日频历史，此后本库逐周累积。

## 时间口径（清单「四个时点」）

* `obs_date`：观察期；`realtime_start`：可知日期（数据源发布版本，或本库首次采集日；
  初次回填按各序列 `release_lag_days` 估计，标记 `backfill_estimate`）；
  `fetched_at`：采集时间；`week_cutoff`：周报截点（周五）。
* 历史周度值只使用截点后周日之前已可知的数据；最新一周使用运行时已入库的全部数据。
* 回填起点：原始数据 2020-10-01，周度值 2021-10-01（约 5 年）。

## 公式

`catalog/mapping.py` 生成 `mapping.csv`（每个指标的公式）和 `series.csv`（原始序列）。
公式语法见 `engine/formula.py` 顶部说明，例如：

```text
ret({FRED:SP500}, "YTD")             年初至今回报 %
chg({FRED:DGS10}, "W") * 100         周变动 bp
pctile({FRED:BAMLC0A0CM}, "3Y")      3 年历史分位
yoy({BLS:CUUR0000SA0})               同比 %
prior(pop({FRED:RSAFS}))             本次发布所列前值
```

## 运行

```bash
pip install -r pipeline/warehouse/requirements.txt
export WAREHOUSE_DB_URL='postgresql://...'      # 或 sqlite:///local.db 本地试跑
python3 -m pipeline.warehouse init-db
python3 -m pipeline.warehouse weekly            # 同步目录 + 抓取 + 计算（首次自动回填 5 年）
python3 -m pipeline.warehouse probe --provider FRED   # 只抓不写，检查数据源
python3 -m pipeline.warehouse derive --backfill-from 2021-10-01   # 重算历史周度值
```

更新清单：替换 Excel 后运行
`python3 -m pipeline.warehouse.catalog.build_catalog 清单.xlsx` 和
`python3 -m pipeline.warehouse.catalog.mapping`，提交两个 CSV 的变更。

GitHub Actions（`.github/workflows/warehouse.yml`）每周六 13:17 UTC 运行，也可手动触发。
需要的 Secrets：`WAREHOUSE_DB_URL`（必需）、`FRED_API_KEY`、`BLS_API_KEY`、`EIA_API_KEY`。

## 测试

```bash
python3 -m unittest discover -s pipeline/warehouse/tests -t .
```
