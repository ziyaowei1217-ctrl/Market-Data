"""Indicator → source mapping for the warehouse.

Run ``python3 -m pipeline.warehouse.catalog.mapping`` to regenerate
``series.csv`` (raw series registry) and ``mapping.csv`` (per-indicator method,
formula and coverage note). Both CSVs are committed so changes are reviewable.

method values
-------------
api       formula over free official / free market feeds (this module)
report    weekly snapshot parsed from an institution's free weekly report
manual    maintained by hand in catalog/manual (events, dates, decisions)
excluded  out of scope by request (institution forecasts / CMAs)
pending   no free source wired yet; see coverage_note
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .build_catalog import load_catalog

CATALOG_DIR = Path(__file__).resolve().parent
SERIES_CSV = CATALOG_DIR / "series.csv"
MAPPING_CSV = CATALOG_DIR / "mapping.csv"

EXCLUDED_MODULES = {"分机构年度增长预测", "长期资本市场假设"}
REPORT_SOURCES = {
    "am.gs.com": "高盛 Market Monitor Weekly",
    "am.jpmorgan.com": "摩根 Weekly Market Recap",
    "www.assetmanagement.hsbc.co.uk": "汇丰 Investment Weekly（英国）",
    "www.assetmanagement.hsbc.com.au": "汇丰 Investment Weekly（澳洲）",
    "insight.factset.com": "FactSet Earnings Insight",
}


@dataclass
class Series:
    key: str
    provider: str
    code: str
    title: str
    frequency: str
    unit: str
    release_lag_days: int
    source_url: str = ""
    params: dict = field(default_factory=dict)
    vintages: bool = False
    runner: str = "cloud"


SERIES: dict[str, Series] = {}
MAP: dict[str, dict] = {}


def series(provider, code, title, freq, unit, lag, url="", params=None, vintages=False, runner="cloud", key=None) -> str:
    key = key or f"{provider}:{code}"
    if key not in SERIES:
        SERIES[key] = Series(key, provider, code, title, freq, unit, lag, url, params or {}, vintages, runner)
    elif SERIES[key].params != (params or {}) or SERIES[key].frequency != freq:
        raise ValueError(f"series {key} registered twice with different params/frequency")
    return "{" + key + "}"


def api(iid: str, formula: str, note: str = "") -> None:
    """Map an indicator to a formula. A later api() may upgrade an earlier
    report/pending placeholder, but two api() mappings for one id are an error."""
    if iid in MAP and MAP[iid]["method"] == "api":
        raise ValueError(f"{iid} mapped twice")
    MAP[iid] = {"method": "api", "phase": "P1", "formula": formula, "coverage_note": note}


def other(iid: str, method: str, note: str, phase: str = "P2") -> None:
    if iid in MAP:
        raise ValueError(f"{iid} mapped twice")
    MAP[iid] = {"method": method, "phase": phase, "formula": "", "coverage_note": note}


def ids(prefix: str, start: int, end: int) -> list[str]:
    return [f"{prefix}-{i:03d}" for i in range(start, end + 1)]


# ---------------------------------------------------------------- series helpers

def fred(code, title, freq="D", unit="", lag=1, vintages=False):
    return series("FRED", code, title, freq, unit, lag, f"https://fred.stlouisfed.org/series/{code}", vintages=vintages)


def bls(code, title, freq="M", unit="", lag=45):
    return series("BLS", code, title, freq, unit, lag, f"https://data.bls.gov/timeseries/{code}")


def yahoo(ticker, title, note_url=""):
    return series("YAHOO", ticker, title, "D", "点", 1, note_url or f"https://finance.yahoo.com/quote/{ticker}")


def cboe(sym, title):
    return series("CBOE", sym, title, "D", "指数点", 1, "https://www.cboe.com/tradable-products/vix/vix-historical-data")


def eia(code, title, freq="W", unit="", lag=5):
    return series("EIA", code, title, freq, unit, lag, "https://www.eia.gov/opendata/")


def ecb(code, title, freq="D", unit="", lag=1):
    return series("ECB", code, title, freq, unit, lag, f"https://data.ecb.europa.eu/data/datasets/{code.split('/')[0]}")


# ---------------------------------------------------------------- formula helpers

WINDOWS = {"周回报": "W", "月初至今回报": "MTD", "季初至今回报": "QTD", "年初至今回报": "YTD", "过去一年回报": "1Y"}


def ret(x, w):
    return f'ret({x}, "{w}")'


def chg_bp(x):
    return f'chg({x}, "W") * 100'


def pct(x, w="3Y"):
    return f'pctile({x}, "{w}")'


# =================================================================== mappings


def build() -> None:
    # ---------------------------------------------------------- 01 美股主要指数 (FRED)
    for base, code, title in [(1, "SP500", "S&P 500"), (6, "NASDAQCOM", "Nasdaq Composite"), (11, "DJIA", "Dow Jones Industrial Average")]:
        x = fred(code, title, "D", "点")
        api(f"01-{base:03d}", x, "FRED 价格指数（S&P 授权，FRED 免费历史约 10 年）")
        for k, w in enumerate(["W", "MTD", "YTD", "1Y"], start=1):
            api(f"01-{base + k:03d}", ret(x, w), "价格回报，不含股息")

    # ---------------------------------------------------------- 02 全球宽基
    stoxx600 = yahoo("^STOXX", "STOXX Europe 600")
    api("02-021", stoxx600, "Yahoo Finance 免费延迟行情（非官方接口），价格指数")
    for k, w in enumerate(["W", "MTD", "YTD", "1Y"], start=22):
        api(f"02-{k:03d}", ret(stoxx600, w), "Yahoo Finance 免费行情，价格回报")
    for iid in ids("02", 1, 20) + ids("02", 26, 40):
        other(iid, "report", "MSCI/TOPIX 指数历史需授权；取汇丰 Investment Weekly（澳洲）每周市场表快照", "P1b")

    # ---------------------------------------------------------- 03 S&P 500 行业 (Yahoo S&P sector indices)
    sp500 = fred("SP500", "S&P 500", "D", "点")
    sectors = [
        ("通讯服务", "^SP500-50"), ("能源", "^GSPE"), ("信息技术", "^SP500-45"), ("公用事业", "^SP500-55"),
        ("金融", "^SP500-40"), ("必需消费", "^SP500-30"), ("房地产", "^SP500-60"), ("工业", "^SP500-20"),
        ("可选消费", "^SP500-25"), ("医疗保健", "^SP500-35"), ("材料", "^SP500-15"),
    ]
    note = "S&P 500 行业价格指数（Yahoo 免费行情）；摩根周报为总回报口径，二者可能有股息差"
    for i, (name, ticker) in enumerate(sectors):
        x = yahoo(ticker, f"S&P 500 {name}行业指数")
        b = 1 + 4 * i
        api(f"03-{b:03d}", ret(x, "W"), note)
        api(f"03-{b + 1:03d}", f"{ret(x, 'W')} - {ret(sp500, 'W')}", note)
        api(f"03-{b + 2:03d}", ret(x, "YTD"), note)
        api(f"03-{b + 3:03d}", f"{ret(x, 'YTD')} - {ret(sp500, 'YTD')}", note)
        api(f"95-{23 + i:03d}", ret(x, "MTD"), note)

    # ---------------------------------------------------------- 04 Russell 风格
    russell = [
        ("Russell 1000 Value", "^RLV"), ("Russell 1000", "^RUI"), ("Russell 1000 Growth", "^RLG"),
        ("Russell Midcap Value", "^RMCCV"), ("Russell Midcap", "^RMCC"), ("Russell Midcap Growth", "^RMCCG"),
        ("Russell 2000 Value", "^RUJ"), ("Russell 2000", "^RUT"), ("Russell 2000 Growth", "^RUO"),
    ]
    rx = [yahoo(t, n) for n, t in russell]
    rnote = "Russell 价格指数（Yahoo 免费行情）；摩根周报为总回报口径"
    for i, x in enumerate(rx):
        api(f"04-{1 + 2 * i:03d}", ret(x, "W"), rnote)
        api(f"04-{2 + 2 * i:03d}", ret(x, "YTD"), rnote)
        api(f"95-{56 + i:03d}", ret(x, "MTD"), rnote)
    for k, (g, v) in enumerate([(2, 0), (5, 3), (8, 6)]):
        api(f"04-{19 + k:03d}", f"{ret(rx[g], 'W')} - {ret(rx[v], 'W')}", rnote)

    # ---------------------------------------------------------- 05-10 估值/盈利 (FactSet / 摩根)
    for iid in ids("05", 1, 9):
        other(iid, "report", "FactSet Earnings Insight（S&P 500）/ 摩根周报估值页快照", "P1b")
    for iid in ids("06", 1, 27):
        other(iid, "report", "摩根 Weekly Market Recap 指数特征表快照", "P1b")
    for iid in ids("07", 1, 3):
        other(iid, "pending", "成分权重需指数商 factsheet（月度 PDF），待接入")
    spew = yahoo("^SPXEW", "S&P 500 Equal Weight")
    api("07-004", f"{ret(spew, 'W')} - {ret(sp500, 'W')}", "等权与市值加权价格指数（Yahoo/FRED），价格回报差")
    api("07-005", f"{ret(spew, 'YTD')} - {ret(sp500, 'YTD')}", "等权与市值加权价格指数（Yahoo/FRED），价格回报差")
    for iid in ids("08", 1, 40) + ids("09", 1, 6) + ids("10", 1, 4):
        other(iid, "report", "FactSet Earnings Insight 每周 PDF 快照", "P1b")

    # ---------------------------------------------------------- 12-14 美债收益率
    for k, (code, title) in enumerate([("DGS3MO", "3M"), ("DGS2", "2Y"), ("DGS5", "5Y"), ("DGS10", "10Y"), ("DGS30", "30Y")]):
        x = fred(code, f"US Treasury {title} CMT yield", "D", "%")
        api(f"12-{1 + 2 * k:03d}", x, "财政部常数期限收益率（FRED 镜像）")
        api(f"12-{2 + 2 * k:03d}", chg_bp(x), "本周末减上周末，%→bp")
    for k, code in enumerate(["T10Y2Y", "T10Y3M"]):
        x = fred(code, code, "D", "%")
        api(f"13-{1 + 2 * k:03d}", f"{x} * 100", "FRED 原值为 %，×100→bp")
        api(f"13-{2 + 2 * k:03d}", chg_bp(x))
    for k, code in enumerate(["DFII5", "T5YIE", "DFII10", "T10YIE"]):
        x = fred(code, code, "D", "%")
        api(f"14-{1 + 2 * k:03d}", x)
        api(f"14-{2 + 2 * k:03d}", chg_bp(x))
    dfii30 = fred("DFII30", "US 30Y TIPS real yield", "D", "%")
    dgs30 = fred("DGS30", "US Treasury 30Y CMT yield", "D", "%")
    api("112-301", dfii30)
    api("112-302", f"{dgs30} - {dfii30}", "同日名义减实际收益率")

    # ---------------------------------------------------------- 15 欧日国债
    jgb2 = series("MOFJP", "2Y", "JGB 2Y yield (MOF)", "D", "%", 1, "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/")
    jgb10 = series("MOFJP", "10Y", "JGB 10Y yield (MOF)", "D", "%", 1, "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/")
    jgb30 = series("MOFJP", "30Y", "JGB 30Y yield (MOF)", "D", "%", 1, "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/")
    api("15-009", jgb2, "日本财务省 JGB 常数期限收益率")
    api("15-010", jgb10, "日本财务省 JGB 常数期限收益率")
    for iid in ids("15", 1, 8) + ["15-011", "15-012"]:
        other(iid, "report", "欧洲国债无统一免费日频官方接口；取高盛/摩根周报利率表快照", "P1b")
    api("99-009", jgb30, "日本财务省 JGB 常数期限收益率")
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"99-{10 + k:03d}", f'snap({jgb30}, "{w}")')

    # ---------------------------------------------------------- 16-17, 73 ICE BofA OAS (FRED, Percent→bp)
    ice_note = "ICE BofA via FRED（FRED 仅提供约 3 年日频历史，之后本库逐周累积）"
    for prefix, code in [("16", "BAMLC0A0CM"), ("17", "BAMLH0A0HYM2")]:
        x = fred(code, code, "D", "%")
        api(f"{prefix}-001", f"{x} * 100", ice_note + "；%×100→bp")
        api(f"{prefix}-002", chg_bp(x), ice_note)
        api(f"{prefix}-003", pct(x, "3Y"), ice_note + "；周度采样 3 年分位")
    for k, code in enumerate(["BAMLC0A4CBBB", "BAMLH0A1HYBB", "BAMLH0A2HYB", "BAMLH0A3HYC"]):
        api(f"73-{1 + k:03d}", f"{fred(code, code, 'D', '%')} * 100", ice_note)
    for iid in ["73-005", "73-006", "73-007"]:
        other(iid, "pending", "行业 OAS 需 ICE 授权")
    hy = fred("BAMLH0A0HYM2", "BAMLH0A0HYM2", "D", "%")
    ig = fred("BAMLC0A0CM", "BAMLC0A0CM", "D", "%")
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"99-{86 + k:03d}", f'snap({hy}, "{w}") * 100', ice_note)
        api(f"99-{89 + k:03d}", f'snap({ig}, "{w}") * 100', ice_note)
    ehy = fred("BAMLHE00EHYIOAS", "ICE BofA Euro HY OAS", "D", "%")
    api("99-017", f"{ehy} * 100", ice_note)
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"99-{18 + k:03d}", f'snap({ehy}, "{w}") * 100', ice_note)

    # ---------------------------------------------------------- 18-19 EM 利差 / 债券指数回报
    for iid in ids("18", 1, 3):
        other(iid, "report", "JPM EMBI 需授权；取周报快照", "P1b")
    igtr = fred("BAMLCC0A0CMTRIV", "ICE BofA US Corporate Index Total Return", "D", "指数点")
    hytr = fred("BAMLHYH0A0HYM2TRIV", "ICE BofA US High Yield Index Total Return", "D", "指数点")
    api("19-005", ret(igtr, "W"), ice_note + "；总回报指数")
    api("19-006", ret(igtr, "YTD"), ice_note + "；总回报指数")
    api("19-009", ret(hytr, "W"), ice_note + "；总回报指数")
    api("19-010", ret(hytr, "YTD"), ice_note + "；总回报指数")
    for iid in ["19-001", "19-002", "19-003", "19-004", "19-007", "19-008", "19-011", "19-012", "19-013", "19-014", "19-015", "19-016"]:
        other(iid, "report", "Bloomberg 指数/YTW/久期需授权；取摩根周报固定收益表快照", "P1b")

    # ---------------------------------------------------------- 20 政策利率
    fl = fred("DFEDTARL", "Fed funds target range lower", "D", "%", lag=0)
    fu = fred("DFEDTARU", "Fed funds target range upper", "D", "%", lag=0)
    dfr = fred("ECBDFR", "ECB deposit facility rate", "D", "%", lag=0)
    boe = series("BOE", "IUDBEDR", "Bank Rate", "D", "%", 0, "https://www.bankofengland.co.uk/boeapps/database/")
    api("20-001", fl)
    api("20-002", fu)
    api("20-003", dfr)
    api("20-004", boe, "英格兰银行统计数据库 IADB")
    other("20-005", "manual", "BoJ 政策利率：按决议公告人工维护（catalog/manual）", "P1")
    api("102-086", f"before_change({fu})", "上一次调整前的目标上限")
    api("102-089", f"before_change({boe})", "上一次调整前的 Bank Rate")
    api("102-095", f"before_change({dfr})", "上一次调整前的存款便利利率")
    other("102-092", "manual", "BoJ 政策利率前值：随人工维护表", "P1")

    # ---------------------------------------------------------- 21 SOFR/EFFR
    nyurl = "https://www.newyorkfed.org/markets/reference-rates/sofr"
    def ny(path, field, title, unit):
        return series("NYFED", f"{path}:{field}", title, "D", unit, 1, nyurl)
    sofr = ny("secured/sofr", "percentRate", "SOFR", "%")
    effr = ny("unsecured/effr", "percentRate", "EFFR", "%")
    iorb = fred("IORB", "Interest rate on reserve balances", "D", "%", lag=0)
    api("21-001", sofr, "纽约联储参考利率 API")
    api("21-002", ny("secured/sofr", "volumeInBillions", "SOFR volume", "十亿美元"))
    api("21-003", ny("secured/sofr", "percentPercentile25", "SOFR p25", "%"))
    api("21-004", ny("secured/sofr", "percentPercentile75", "SOFR p75", "%"))
    api("21-005", effr)
    api("21-006", ny("unsecured/effr", "volumeInBillions", "EFFR volume", "十亿美元"))
    api("21-007", ny("unsecured/effr", "percentPercentile25", "EFFR p25", "%"))
    api("21-008", ny("unsecured/effr", "percentPercentile75", "EFFR p75", "%"))
    api("21-009", f"({sofr} - {iorb}) * 100", "同一参考日")
    api("21-010", f"({effr} - {iorb}) * 100", "同一参考日")
    api("21-011", iorb)
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"99-{53 + k:03d}", f'snap({effr}, "{w}")')
        api(f"99-{56 + k:03d}", f'snap({dfr}, "{w}")')

    for iid in ids("22", 1, 10):
        other(iid, "pending", "FedWatch 概率需 CME 授权；可由联邦基金期货自算，待做")

    # ---------------------------------------------------------- 23-24 外汇
    eur_usd = ecb("EXR/D.USD.EUR.SP00.A", "USD per EUR (ECB reference)", unit="美元/欧元")
    eur_jpy = ecb("EXR/D.JPY.EUR.SP00.A", "JPY per EUR (ECB reference)", unit="日元/欧元")
    eur_gbp = ecb("EXR/D.GBP.EUR.SP00.A", "GBP per EUR (ECB reference)", unit="英镑/欧元")
    eur_cny = ecb("EXR/D.CNY.EUR.SP00.A", "CNY per EUR (ECB reference)", unit="人民币/欧元")
    eur_chf = ecb("EXR/D.CHF.EUR.SP00.A", "CHF per EUR (ECB reference)", unit="瑞郎/欧元")
    usd_jpy = f"({eur_jpy} / {eur_usd})"
    gbp_usd = f"({eur_usd} / {eur_gbp})"
    usd_cny = f"({eur_cny} / {eur_usd})"
    fx_note = "ECB 欧元参考汇率；非欧元货币对由同日参考汇率交叉计算"
    for k, x in enumerate([eur_usd, usd_jpy, gbp_usd, usd_cny]):
        api(f"23-{1 + 2 * k:03d}", x, fx_note)
        api(f"23-{2 + 2 * k:03d}", ret(x, "W"), fx_note)
    api("99-025", eur_chf, fx_note)
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"99-{26 + k:03d}", f'snap({eur_chf}, "{w}")', fx_note)
        api(f"99-{104 + k:03d}", f'snap({eur_usd}, "{w}")', fx_note)
        api(f"99-{107 + k:03d}", f'snap({gbp_usd}, "{w}")', fx_note)
        api(f"99-{110 + k:03d}", f'snap({usd_jpy}, "{w}")', fx_note)
        api(f"99-{113 + k:03d}", f'snap({usd_cny}, "{w}")', fx_note)
    dxy = yahoo("DX-Y.NYB", "ICE US Dollar Index")
    broad = fred("DTWEXBGS", "Nominal broad USD index", "D", "指数点")
    api("24-001", dxy, "ICE DXY 免费延迟行情（Yahoo），完整授权历史需 ICE")
    api("24-002", ret(dxy, "W"), "Yahoo 免费行情")
    api("24-003", broad, "美联储 H.10 广义美元指数（FRED）")
    api("24-004", ret(broad, "W"))
    api("99-051", ret(dxy, "QTD"), "Yahoo 免费行情")

    # ---------------------------------------------------------- 25-28 商品
    wti = fred("DCOILWTICO", "WTI spot (EIA)", "D", "美元/桶", lag=7)
    brent = fred("DCOILBRENTEU", "Brent spot (EIA)", "D", "美元/桶", lag=7)
    api("25-001", wti, "EIA 现货价格（FRED 镜像），发布滞后约一周")
    api("25-002", ret(wti, "W"))
    api("25-003", brent, "EIA 现货价格（FRED 镜像），发布滞后约一周")
    api("25-004", ret(brent, "W"))
    api("25-005", f"{brent} - {wti}", "同日现货价差")
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"99-{95 + k:03d}", f'snap({wti}, "{w}")')
        api(f"99-{98 + k:03d}", f'snap({brent}, "{w}")')
    hh = fred("DHHNGSP", "Henry Hub natural gas spot", "D", "美元/MMBtu", lag=7)
    api("99-021", hh, "EIA Henry Hub 现货（FRED 镜像）")
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"99-{22 + k:03d}", f'snap({hh}, "{w}")')

    eia_codes = [
        ("26-001", "PET.WCESTUS1.W", "Commercial crude stocks ex SPR", "千桶", 1 / 1000),
        ("26-002", "PET.WGTSTUS1.W", "Total motor gasoline stocks", "千桶", 1 / 1000),
        ("26-003", "PET.WDISTUS1.W", "Distillate fuel oil stocks", "千桶", 1 / 1000),
        ("26-007", "PET.WCRFPUS2.W", "Crude oil field production", "千桶/日", 1),
        ("26-008", "PET.WCRIMUS2.W", "Crude oil imports", "千桶/日", 1),
        ("26-009", "PET.WCREXUS2.W", "Crude oil exports", "千桶/日", 1),
        ("26-010", "PET.WGFUPUS2.W", "Gasoline product supplied", "千桶/日", 1),
        ("26-011", "PET.WDIUPUS2.W", "Distillate product supplied", "千桶/日", 1),
        ("26-012", "PET.WPULEUS3.W", "Refinery utilization", "%", 1),
    ]
    stocks = {}
    for iid, code, title, unit, scale in eia_codes:
        x = eia(code, title, unit=unit)
        api(iid, x if scale == 1 else f"{x} / 1000", "EIA 周度石油状况报告" + ("；千桶→百万桶" if scale != 1 else ""))
        stocks[iid] = x
    for src, dst in [("26-001", "26-004"), ("26-002", "26-005"), ("26-003", "26-006")]:
        api(dst, f"diff({stocks[src]}) / 1000", "本周减上周；千桶→百万桶")
    for iid in ids("27", 1, 3) + ids("28", 1, 3):
        other(iid, "report", "LBMA/LME 价格需授权；取摩根周报商品快照", "P1b")
    for iid in ["99-101", "99-102", "99-103"]:
        other(iid, "report", "LBMA 黄金需授权；取周报快照", "P1b")

    # ---------------------------------------------------------- 29 CPI (BLS)
    cpi = [
        ("SA0", "总体"), ("SA0L1E", "核心"), ("SAF1", "食品"), ("SA0E", "能源"), ("SAH1", "住房"), ("SACL1E", "核心商品"),
    ]
    sa = {c: bls(f"CUSR0000{c}", f"CPI {n} SA") for c, n in cpi}
    nsa = {c: bls(f"CUUR0000{c}", f"CPI {n} NSA") for c, n in cpi}
    cpi_note = "BLS CPI；环比用季调指数，同比用未季调指数（BLS 官方口径）"
    api("29-001", sa["SA0"], cpi_note)
    api("29-002", f"yoy({nsa['SA0']})", cpi_note)
    api("29-003", f"pop({sa['SA0']})", cpi_note)
    api("29-004", sa["SA0L1E"], cpi_note)
    api("29-005", f"yoy({nsa['SA0L1E']})", cpi_note)
    api("29-006", f"pop({sa['SA0L1E']})", cpi_note)
    for k, c in enumerate(["SAF1", "SA0E", "SAH1", "SACL1E"]):
        api(f"29-{7 + 2 * k:03d}", f"pop({sa[c]})", cpi_note)
        api(f"29-{8 + 2 * k:03d}", f"yoy({nsa[c]})", cpi_note)
    for iid in ["29-015", "29-016"]:
        other(iid, "pending", "非住房核心服务需 BLS 分项与相对权重自建，待做")
    api("60-001", f"ann({sa['SA0L1E']}, 3)", "季调核心 CPI 指数 3 个月年化")
    api("60-002", f"ann({sa['SA0L1E']}, 6)", "季调核心 CPI 指数 6 个月年化")

    # ---------------------------------------------------------- 30 PCE (BEA via FRED)
    pce = fred("PCEPI", "PCE price index", "M", "指数点", lag=60)
    core = fred("PCEPILFE", "Core PCE price index", "M", "指数点", lag=60)
    goods = fred("DGDSRG3M086SBEA", "PCE goods price index", "M", "指数点", lag=60)
    serv = fred("DSERRG3M086SBEA", "PCE services price index", "M", "指数点", lag=60)
    housing = series("BEA", "NIUnderlyingDetail:U20404:DHSGRG", "PCE housing price index (monthly)", "M", "指数点", 60,
                     "https://apps.bea.gov/iTable/?reqid=19&step=2&isuri=1&categories=underlying")
    supercore = fred("IA001260M", "PCE services ex energy and housing price index", "M", "指数点", lag=60)
    pce_note = "BEA 个人收入与支出（FRED 镜像）"
    api("30-001", pce, pce_note)
    api("30-002", f"yoy({pce})", pce_note)
    api("30-003", f"pop({pce})", pce_note)
    api("30-004", core, pce_note)
    api("30-005", f"yoy({core})", pce_note)
    api("30-006", f"pop({core})", pce_note)
    api("30-007", f"pop({goods})", pce_note)
    api("30-009", f"pop({serv})", pce_note)
    api("30-011", f"pop({housing})", pce_note)
    api("30-013", f"pop({supercore})", pce_note)
    for iid in ["30-008", "30-010", "30-012", "30-014"]:
        other(iid, "pending", "PCE 通胀贡献需 BEA 贡献表（NIPA API），待接入")
    api("60-003", f"ann({core}, 3)", "季调核心 PCE 指数 3 个月年化")
    api("60-004", f"ann({core}, 6)", "季调核心 PCE 指数 6 个月年化")

    # ---------------------------------------------------------- 31 GDP
    gdp_note = "BEA GDP（FRED 镜像），季环比折年率及贡献"
    api("31-001", fred("A191RL1Q225SBEA", "Real GDP % change SAAR", "Q", "%", lag=120), gdp_note)
    for k, code in enumerate(["DPCERY2Q224SBEA", "A007RY2Q224SBEA", "A014RY2Q224SBEA", "A822RY2Q224SBEA", "A019RY2Q224SBEA"]):
        api(f"31-{2 + k:03d}", fred(code, code, "Q", "百分点", lag=120), gdp_note)
    api("110-003", f"yoy({fred('GDP', 'Nominal GDP', 'Q', '十亿美元', lag=120)})", gdp_note)

    # ---------------------------------------------------------- 32-34 就业
    payems = fred("PAYEMS", "Nonfarm payrolls", "M", "千人", lag=37, vintages=True)
    emp_note = "BLS 就业形势（FRED/ALFRED）；修订值需 ALFRED 发布版本（配置 FRED_API_KEY）"
    api("32-001", f"diff({payems})", emp_note)
    api("32-002", f"rev(diff({payems}), 1)", emp_note)
    api("32-003", f"rev(diff({payems}), 2)", emp_note)
    api("32-004", fred("UNRATE", "Unemployment rate", "M", "%", lag=37))
    api("32-005", fred("CIVPART", "Labor force participation", "M", "%", lag=37))
    api("32-006", fred("EMRATIO", "Employment-population ratio", "M", "%", lag=37))
    ahe = fred("CES0500000003", "Average hourly earnings, private", "M", "美元", lag=37)
    api("32-007", f"yoy({ahe})")
    api("32-008", f"pop({ahe})")
    api("32-009", fred("AWHAETP", "Average weekly hours, private", "M", "小时", lag=37))
    api("32-010", bls("CES0500000021", "Diffusion index, 1-month, total private", lag=37), "BLS CES 扩散指数（1个月）")
    api("101-015", f"ma(diff({payems}), 12)", "非农新增 12 个月移动平均")
    api("33-001", fred("ICSA", "Initial claims", "W", "人", lag=5))
    api("33-002", fred("CCSA", "Continued claims", "W", "人", lag=12))
    api("33-003", fred("IC4WSA", "Initial claims 4wk avg", "W", "人", lag=5))
    api("33-004", fred("CC4WSA", "Continued claims 4wk avg", "W", "人", lag=12))
    api("34-001", fred("JTSJOL", "JOLTS job openings", "M", "千人", lag=67))
    api("34-002", fred("JTSJOR", "JOLTS job openings rate", "M", "%", lag=67))
    api("34-003", fred("JTSQUR", "JOLTS quits rate", "M", "%", lag=67))

    for iid in ids("35", 1, 44):
        other(iid, "pending", "S&P Global PMI 历史需授权；可解析公开新闻稿，待做")
    for iid in ids("36", 1, 12):
        other(iid, "pending", "ISM 数据无免费接口；可解析公开月报，待做")

    # ---------------------------------------------------------- 37-39 消费与生产
    rsafs = fred("RSAFS", "Advance retail sales and food services", "M", "百万美元", lag=45, vintages=True)
    rsfsxmv = fred("RSFSXMV", "Retail sales ex motor vehicles", "M", "百万美元", lag=45)
    control = (
        f"({fred('RSXFS', 'Retail trade', 'M', '百万美元', lag=45)} - {fred('RSMVPD', 'Motor vehicle & parts dealers', 'M', '百万美元', lag=45)}"
        f" - {fred('RSGASS', 'Gasoline stations', 'M', '百万美元', lag=45)} - {fred('RSBMGESD', 'Building materials dealers', 'M', '百万美元', lag=45)})"
    )
    rnote = "Census 零售（FRED）；控制组=零售业−汽车−加油站−建材（不含餐饮）"
    api("37-001", rsafs, rnote)
    api("37-002", rsfsxmv, rnote)
    api("37-003", control, rnote)
    api("37-004", f"pop({rsafs})", rnote)
    api("37-005", f"pop({rsfsxmv})", rnote)
    api("37-006", f"pop({control})", rnote)
    api("102-074", f"prior(pop({rsafs}))", "本次发布所列前值（ALFRED 版本，需 FRED_API_KEY）")
    indpro = fred("INDPRO", "Industrial production", "M", "指数点", lag=46, vintages=True)
    ipman = fred("IPMAN", "Manufacturing production", "M", "指数点", lag=46)
    api("38-001", indpro)
    api("38-002", ipman)
    api("38-003", f"pop({indpro})")
    api("38-004", f"pop({ipman})")
    api("38-005", fred("TCU", "Capacity utilization", "M", "%", lag=46))
    api("102-083", f"prior(pop({indpro}))", "本次发布所列前值（ALFRED 版本，需 FRED_API_KEY）")
    houst = fred("HOUST", "Housing starts", "M", "千套/年", lag=48)
    permit = fred("PERMIT", "Building permits", "M", "千套/年", lag=48)
    api("39-001", houst)
    api("39-002", permit)
    api("39-003", f"pop({houst})")
    api("39-004", f"pop({permit})")

    # ---------------------------------------------------------- 40-43 海外宏观
    hicp_url = "https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/"
    hicp = series("EUROSTAT", "prc_hicp_minr:EA:TOTAL", "Euro area HICP annual rate (ECOICOP 2)", "M", "%", 47, hicp_url,
                  params={"dataset": "prc_hicp_minr", "geo": "EA", "unit": "RCH_A", "coicop18": "TOTAL", "sinceTimePeriod": "2019-01"})
    hicp_core = series("EUROSTAT", "prc_hicp_minr:EA:TOT_X_NRG_FOOD", "Euro area HICP ex energy, food, alcohol, tobacco annual rate", "M", "%", 47, hicp_url,
                       params={"dataset": "prc_hicp_minr", "geo": "EA", "unit": "RCH_A", "coicop18": "TOT_X_NRG_FOOD", "sinceTimePeriod": "2019-01"})
    api("40-001", hicp, "Eurostat HICP（2026 年起 ECOICOP 第 2 版数据集 prc_hicp_minr）")
    api("40-002", hicp_core, "Eurostat HICP（2026 年起 ECOICOP 第 2 版数据集 prc_hicp_minr）")
    ea_q = series("EUROSTAT", "namq_10_gdp:qoq", "Euro area real GDP q/q", "Q", "%", 120,
                  "https://ec.europa.eu/eurostat/databrowser/view/namq_10_gdp/",
                  params={"dataset": "namq_10_gdp", "geo": "EA", "unit": "CLV_PCH_PRE", "s_adj": "SCA", "na_item": "B1GQ", "sinceTimePeriod": "2019-Q1"})
    ea_y = series("EUROSTAT", "namq_10_gdp:yoy", "Euro area real GDP y/y", "Q", "%", 120,
                  "https://ec.europa.eu/eurostat/databrowser/view/namq_10_gdp/",
                  params={"dataset": "namq_10_gdp", "geo": "EA", "unit": "CLV_PCH_SM", "s_adj": "SCA", "na_item": "B1GQ", "sinceTimePeriod": "2019-Q1"})
    api("40-003", ea_q, "Eurostat 季度国民账户")
    api("40-004", ea_y, "Eurostat 季度国民账户")
    def ons(cdid, uri, title, period="months", lag=45):
        return series("ONS", cdid, title, {"months": "M", "quarters": "Q"}[period], "%", lag,
                      "https://www.ons.gov.uk" + uri, params={"uri": uri, "period": period})
    uk_cpi = ons("D7G7", "/economy/inflationandpriceindices/timeseries/d7g7/mm23", "UK CPI annual rate")
    uk_core = ons("DKO8", "/economy/inflationandpriceindices/timeseries/dko8/mm23", "UK core CPI annual rate")
    uk_mgdp = ons("ECY2", "/economy/grossdomesticproductgdp/timeseries/ecy2/mgdp", "UK monthly GDP index")
    uk_q = ons("IHYQ", "/economy/grossdomesticproductgdp/timeseries/ihyq/qna", "UK GDP q/q", "quarters", 135)
    api("41-001", uk_cpi, "ONS 时间序列")
    api("41-002", uk_core, "ONS 时间序列")
    api("41-003", f"pop({uk_mgdp})", "ONS 月度 GDP 指数计算环比")
    api("41-004", uk_q, "ONS 时间序列")
    api("101-012", f"(msum({uk_mgdp}, 3) / lag(msum({uk_mgdp}, 3), 3) - 1) * 100", "三个月对前三个月")
    api("102-077", f"prior({uk_cpi})", "本次发布所列前值（本库逐次留存版本）")
    api("102-026", f"prior(pop({uk_mgdp}))", "本次发布所列前值（本库逐次留存版本）")
    api("102-029", f"prior((msum({uk_mgdp}, 3) / lag(msum({uk_mgdp}, 3), 3) - 1) * 100)", "本次发布所列前值（本库逐次留存版本）")
    jp_gdp = fred("JPNRGDPEXP", "Japan real GDP", "Q", "十亿日元", lag=60)
    api("42-003", f"pop({jp_gdp})", "日本实际 GDP（FRED 镜像）季环比")
    api("42-004", f"ann({jp_gdp}, 1)", "季环比折年")
    for iid in ["42-001", "42-002", "102-080"]:
        other(iid, "pending", "日本 CPI 需 e-Stat API（需注册 appId），待接入")
    for iid in ids("43", 1, 6) + ["102-068", "102-071"]:
        other(iid, "pending", "国家统计局数据库对境外 IP 不稳定，计划用本地电脑补抓")

    # ---------------------------------------------------------- 44-45 ICI, 47 CFTC
    for iid in ids("44", 1, 18) + ids("45", 1, 8):
        other(iid, "pending", "ICI 周度 Excel 发布链接每周变化，待写解析")
    tff = "gpe5-46if"
    dis = "72hh-3qpy"
    cftc_url = "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"
    def cot(dataset, contract, field, title):
        return series("CFTC", f"{dataset}:{contract}:{field}", title, "W", "张", 3, cftc_url)
    tff_contracts = [("13874A", "E-mini S&P 500"), ("043602", "UST 10Y note"), ("099741", "Euro FX"), ("097741", "Japanese yen")]
    for c, (code, name) in enumerate(tff_contracts):
        oi = cot(tff, code, "open_interest_all", f"{name} open interest")
        for g, (prefix, label) in enumerate([("asset_mgr", "Asset Manager"), ("lev_money", "Leveraged Funds")]):
            long_ = cot(tff, code, f"{prefix}_positions_long", f"{name} {label} long")
            short = cot(tff, code, f"{prefix}_positions_short", f"{name} {label} short")
            net = f"({long_} - {short})"
            b = 1 + 12 * c + 6 * g
            note = f"CFTC TFF 期货单独口径，合约 {code}，周二持仓"
            api(f"47-{b:03d}", long_, note)
            api(f"47-{b + 1:03d}", short, note)
            api(f"47-{b + 2:03d}", net, note)
            api(f"47-{b + 3:03d}", f"{net} / {oi} * 100", note)
            api(f"47-{b + 4:03d}", f"diff({net})", note)
            api(f"47-{b + 5:03d}", pct(net, "3Y"), note)
        api(f"47-{55 + c:03d}", oi, f"CFTC TFF，合约 {code}")
    for k, (code, name) in enumerate([("067651", "WTI crude"), ("088691", "COMEX gold")]):
        note = f"CFTC Disaggregated 期货单独口径，合约 {code}"
        long_ = cot(dis, code, "m_money_positions_long_all", f"{name} managed money long")
        short = cot(dis, code, "m_money_positions_short_all", f"{name} managed money short")
        api(f"47-{49 + 3 * k:03d}", long_, note)
        api(f"47-{50 + 3 * k:03d}", short, note)
        api(f"47-{51 + 3 * k:03d}", f"({long_} - {short})", note)
        api(f"47-{59 + k:03d}", cot(dis, code, "open_interest_all", f"{name} open interest"), note)

    # ---------------------------------------------------------- 48-51 波动与风险
    vix, vix9d, vvix = cboe("VIX", "Cboe VIX"), cboe("VIX9D", "Cboe VIX9D"), cboe("VVIX", "Cboe VVIX")
    for k, x in enumerate([vix, vix9d, vvix]):
        api(f"48-{1 + 2 * k:03d}", x, "Cboe 官方日收盘历史 CSV")
        api(f"48-{2 + 2 * k:03d}", f'chg({x}, "W")', "本周末减上周末，指数点")
    api("48-007", f"{vix9d} - {vix}", "同日差值")
    api("85-001", cboe("OVX", "Cboe Crude Oil Volatility Index"), "Cboe 官方日收盘历史 CSV")
    move = yahoo("^MOVE", "ICE BofA MOVE Index")
    api("49-001", move, "MOVE 免费延迟行情（Yahoo），完整授权历史需 ICE")
    api("49-002", f'chg({move}, "W")', "Yahoo 免费行情")
    for k, w in enumerate(["W", "MTD", "QTD", "YTD"]):
        api(f"99-{45 + k:03d}", ret(vix, w), "VIX 指数百分比变化，不是可投资回报")
    for iid in ["50-001", "50-002"]:
        other(iid, "pending", "需美国国债总回报指数（授权），待定替代口径")
    api("51-001", f'vol({sp500}, "52W")', "周五采样周收益标准差×√52（价格指数）")
    api("51-002", f"drawdown({sp500})", "相对本库已存历史最高点（FRED 历史约 10 年）")
    api("51-003", f'maxdd({sp500}, "YTD")', "年内最大回撤（日频路径）")
    for iid in ids("51", 4, 14):
        other(iid, "pending", "MSCI World/国债总回报/LBMA 黄金需授权数据")

    for iid in ids("52", 1, 20):
        other(iid, "report", "发布前调查中位数：取汇丰 Investment Weekly 日历表（公开项）", "P1b")
    for iid in ids("53", 1, 8):
        other(iid, "manual", "央行会议日程：按官方日历人工维护（catalog/manual）", "P1")
    for iid in ids("54", 1, 10) + ids("55", 1, 10):
        other(iid, "pending", "意外值需发布前调查中位数（授权/周报日历），实际值已入库，调查接入后自动计算")
    for iid in ids("56", 1, 8):
        other(iid, "pending", "需宏观发布日历与日内行情；日内数据需授权")

    # ---------------------------------------------------------- 57-63 美国宏观补充
    gdpnow = fred("GDPNOW", "Atlanta Fed GDPNow", "Q", "%", lag=0, vintages=True)
    api("57-001", gdpnow, "亚特兰大联储 GDPNow（FRED/ALFRED）")
    api("57-002", f"prev_vintage({gdpnow})", "上一次模型更新值（需 FRED_API_KEY 取版本）")
    api("57-003", f"{gdpnow} - prev_vintage({gdpnow})", "本次减上次（需 FRED_API_KEY 取版本）")
    dspi = fred("DSPIC96", "Real disposable personal income", "M", "十亿2017链式美元", lag=60)
    rpce = fred("PCEC96", "Real PCE", "M", "十亿2017链式美元", lag=60)
    api("58-001", dspi, pce_note)
    api("58-002", rpce, pce_note)
    api("58-003", fred("DGDSRX1", "Real PCE goods", "M", "十亿2017链式美元", lag=60), pce_note)
    api("58-004", fred("PCESC96", "Real PCE services", "M", "十亿2017链式美元", lag=60), pce_note)
    api("58-005", f"pop({dspi})", pce_note)
    api("58-006", f"pop({rpce})", pce_note)
    api("58-007", fred("PSAVERT", "Personal saving rate", "M", "%", lag=60), pce_note)
    api("59-001", f"{fred('COE', 'Compensation of employees, received', 'Q', '十亿美元', lag=120)} / {fred('GDI', 'Gross domestic income', 'Q', '十亿美元', lag=150)} * 100",
        "BEA 劳动报酬（received 口径）/GDI")
    api("59-002", fred("PRS85006173", "Nonfarm business labor share", "Q", "指数(2017=100)", lag=40), "BLS 劳动收入份额指数（2017=100）")
    for code, title, (a, b) in [
        ("MEDCPIM158SFRBCLE", "Median CPI y/y", ("61-001", None)), ("MEDCPIM094SFRBCLE", "Median CPI m/m annualized", ("61-002", None)),
        ("TRMMEANCPIM158SFRBCLE", "Trimmed-mean CPI y/y", ("61-003", None)), ("TRMMEANCPIM094SFRBCLE", "Trimmed-mean CPI m/m annualized", ("61-004", None)),
    ]:
        api(a, fred(code, title, "M", "%", lag=45), "克利夫兰联储（FRED 镜像）")
    other("61-005", "pending", "需 BLS 分项与权重自建，待做")
    eci_note = "BLS ECI；季环比为未折年 3 个月变化"
    api("62-001", bls("CIU2020000000000A", "ECI wages private 12m % (NSA)", "Q", lag=30), eci_note)
    api("62-002", bls("CIS2020000000000Q", "ECI wages private 3m % (SA)", "Q", lag=30), eci_note)
    api("62-003", bls("CIU2030000000000A", "ECI benefits private 12m % (NSA)", "Q", lag=30), eci_note)
    api("62-004", bls("CIS2030000000000Q", "ECI benefits private 3m % (SA)", "Q", lag=30), eci_note)
    prod = fred("OPHNFB", "Nonfarm business output per hour", "Q", "指数", lag=40)
    ulc = fred("ULCNFB", "Nonfarm business unit labor costs", "Q", "指数", lag=40)
    api("62-005", f"yoy({prod})", "BLS 生产率指数计算同比")
    api("62-006", f"ann({prod}, 1)", "季环比折年（BLS 口径）")
    api("62-007", f"yoy({ulc})", "BLS 单位劳动成本指数计算同比")
    api("62-008", f"ann({ulc}, 1)", "季环比折年（BLS 口径）")
    for iid in ["63-001", "63-002"]:
        other(iid, "pending", "BoE DMP 月度 Excel，待写解析")
    for iid in ids("63", 3, 8):
        other(iid, "pending", "纽约联储 SCE 数据 Excel，待写解析")
    for iid in ids("64", 1, 19):
        other(iid, "pending", "OIS 曲线需授权")
    sep = fred("FEDTARMD", "FOMC SEP fed funds median", "A", "%", lag=0)
    for k, iid in enumerate(["65-001", "65-004", "65-007"]):
        api(iid, f"at_year({sep}, {k})", "FOMC 经济预测摘要中位数（FRED）")
    for iid in ["65-002", "65-003", "65-005", "65-006", "65-008", "65-009"]:
        other(iid, "pending", "市场隐含路径需 OIS/期货，待做")

    # ---------------------------------------------------------- 66-67 ACM
    acm_url = "https://www.newyorkfed.org/research/data_indicators/term-premia-tabs"
    def acm(col, title):
        return series("ACM", col, title, "D", "%", 35, acm_url)  # workbook is refreshed with a lag of weeks
    for n in range(1, 11):
        base = 1 + 3 * (n - 1)
        api(f"66-{base:03d}", acm(f"ACMTP{n:02d}", f"ACM {n}y term premium"), "纽约联储 ACM 模型")
        api(f"66-{base + 1:03d}", acm(f"ACMRNY{n:02d}", f"ACM {n}y expected avg short rate"), "纽约联储 ACM 模型")
        api(f"66-{base + 2:03d}", acm(f"ACMY{n:02d}", f"ACM {n}y fitted yield"), "纽约联储 ACM 模型")
    dgs5 = fred("DGS5", "US Treasury 5Y CMT yield", "D", "%")
    dgs10 = fred("DGS10", "US Treasury 10Y CMT yield", "D", "%")
    for n, actual, (a, b, c) in [(5, dgs5, ("67-004", "67-005", "67-006")), (10, dgs10, ("67-010", "67-011", "67-012"))]:
        api(a, chg_bp(acm(f"ACMRNY{n:02d}", "")), "ACM 预期短率周变动")
        api(b, chg_bp(acm(f"ACMTP{n:02d}", "")), "ACM 期限溢价周变动")
        api(c, f'(chg({acm(f"ACMY{n:02d}", "")}, "W") - chg({actual}, "W")) * 100', "拟合收益率变动减实测收益率变动")

    # ---------------------------------------------------------- 68 财政
    rcpt = fred("MTSR133FMS", "MTS receipts", "M", "百万美元", lag=12)
    outl = fred("MTSO133FMS", "MTS outlays", "M", "百万美元", lag=12)
    surplus = fred("MTSDS133FMS", "MTS surplus/deficit", "M", "百万美元", lag=12)
    interest = series("TSY", "mts9:net_interest", "MTS net interest outlays", "M", "百万美元", 12,
                      "https://fiscaldata.treasury.gov/datasets/monthly-treasury-statement/",
                      params={"endpoint": "v1/accounting/mts/mts_table_9", "filter": "classification_desc:eq:Net Interest",
                              "date_field": "record_date", "value_field": "current_month_rcpt_outly_amt", "scale": 1e-6,
                              "align": "month_start"})
    mts_note = "财政部 MTS（FRED 镜像）；赤字记为正数"
    api("68-001", rcpt, mts_note)
    api("68-002", outl, mts_note)
    api("68-003", f"-1 * {surplus}", mts_note)
    api("68-004", interest, "财政部 MTS 表 9 净利息（Fiscal Data API）")
    api("68-005", f"fytd({rcpt})", "财年（10月起）累计")
    api("68-006", f"fytd({outl})", "财年（10月起）累计")
    api("68-007", f"-1 * fytd({surplus})", "财年累计，赤字记为正数")
    api("68-008", f"fytd({interest})", "财年累计")
    api("68-009", f"fytd({interest}) / fytd({rcpt}) * 100", "财年累计净利息/财年累计收入")
    api("68-010", fred("FYGFGDQ188S", "Federal debt held by public % GDP", "Q", "%", lag=180), "FRED 季度，发布滞后约半年")
    for iid in ids("69", 1, 17):
        other(iid, "pending", "季度再融资与发行到期需解析财政部公告/MSPD，待做")

    # ---------------------------------------------------------- 70 国债拍卖 (Fiscal Data)
    auction_url = "https://fiscaldata.treasury.gov/datasets/treasury-securities-auctions-data/"
    for k, (term, sec_type) in enumerate([("2-Year", "Note"), ("5-Year", "Note"), ("10-Year", "Note"), ("30-Year", "Bond")]):
        flt = f"original_security_term:eq:{term},security_type:eq:{sec_type},inflation_index_security:eq:No,floating_rate:eq:No"
        def auc(field, title, unit, scale=1.0):
            return series("TSY", f"auction:{term}:{field}", f"{term} auction {title}", "E", unit, 0, auction_url,
                          params={"endpoint": "v1/accounting/od/auctions_query", "filter": flt, "date_field": "auction_date",
                                  "value_field": field, "scale": scale})
        direct = auc("direct_bidder_accepted", "direct accepted", "美元")
        indirect = auc("indirect_bidder_accepted", "indirect accepted", "美元")
        dealer = auc("primary_dealer_accepted", "primary dealer accepted", "美元")
        comp = f"({direct} + {indirect} + {dealer})"
        b = 1 + 7 * k
        note = "财政部拍卖结果（Fiscal Data API），含增发；占比分母为三类竞争性获配合计"
        api(f"70-{b:03d}", auc("offering_amt", "offering amount", "百万美元", 1e-6), note)
        api(f"70-{b + 1:03d}", auc("high_yield", "high yield", "%"), note)
        api(f"70-{b + 2:03d}", auc("bid_to_cover_ratio", "bid-to-cover", "倍"), note)
        api(f"70-{b + 3:03d}", f"{direct} / {comp} * 100", note)
        api(f"70-{b + 4:03d}", f"{indirect} / {comp} * 100", note)
        api(f"70-{b + 5:03d}", f"{dealer} / {comp} * 100", note)
        other(f"70-{b + 6:03d}", "pending", "尾差需拍卖前 when-issued 收益率（授权行情）")
    for iid in ids("71", 1, 4):
        other(iid, "manual", "财政截止日期：按 Congress.gov / 财政部公告人工维护", "P1")

    # ---------------------------------------------------------- 72 美联储资产负债表
    h41 = "美联储 H.4.1（FRED），周三值；百万→十亿美元"
    for iid, code, title in [("72-001", "WALCL", "Fed total assets"), ("72-002", "TREAST", "Fed Treasury holdings"),
                             ("72-003", "WSHOMCB", "Fed MBS holdings"), ("72-004", "WRESBAL", "Reserve balances"),
                             ("72-005", "WTREGEN", "Treasury General Account")]:
        api(iid, f"{fred(code, title, 'W', '百万美元', lag=1)} / 1000", h41)
    api("72-006", fred("RRPONTSYD", "ON RRP", "D", "十亿美元", lag=1), "纽约联储 ON RRP 日值（FRED）")
    for iid in ["74-001", "74-004", "74-007", "74-010"]:
        other(iid, "pending", "公司债发行/到期需授权数据")

    # ---------------------------------------------------------- 75-77 信贷
    for iid, code in [("75-001", "DRTSCILM"), ("75-002", "DRSDCILM"), ("75-003", "DRTSCIS"), ("75-004", "DRSDCIS"),
                      ("75-005", "DRTSCLCC"), ("75-006", "DEMCC"), ("75-007", "STDSAUTO"), ("75-008", "DEMAUTO")]:
        api(iid, fred(code, code, "Q", "%", lag=40), "美联储 SLOOS（FRED）")
    api("75-009", fred("TOTCI", "C&I loans, all commercial banks", "W", "十亿美元", lag=9), "美联储 H.8 周度季调")
    api("75-010", fred("CLSACBW027SBOG", "Consumer loans, all commercial banks", "W", "十亿美元", lag=9), "美联储 H.8 周度季调")
    api("75-011", fred("DPSACBW027SBOG", "Deposits, all commercial banks", "W", "十亿美元", lag=9), "美联储 H.8 周度季调")
    for iid in ["76-001", "76-002", "76-003"]:
        other(iid, "pending", "违约率/评级迁移需评级机构授权")
    for iid, code in [("76-004", "DRBLACBS"), ("76-005", "CORBLACBS"), ("76-006", "DRCCLACBS"),
                      ("76-007", "CORCCACBS"), ("76-008", "DRSFRMACBS"), ("76-009", "CORSFRMACBS")]:
        api(iid, fred(code, code, "Q", "%", lag=55), "美联储逾期与核销率（FRED）")
    for iid in ids("77", 1, 7):
        other(iid, "pending", "AAII 历史文件需会员；机构调查需授权")
    bnote = "自算：维基百科 S&P 500 当前成分股 + Yahoo 日线（历史含幸存者偏差）"
    burl = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    def br(code, title, unit="%"):
        return series("BREADTH", code, f"S&P 500 breadth: {title}", "D", unit, 1, burl)
    groups = [("", "S&P 500"), ("Communication Services", "通讯服务"), ("Energy", "能源"), ("Information Technology", "信息技术"),
              ("Utilities", "公用事业"), ("Financials", "金融"), ("Consumer Staples", "必需消费"), ("Real Estate", "房地产"),
              ("Industrials", "工业"), ("Consumer Discretionary", "可选消费"), ("Health Care", "医疗保健"), ("Materials", "材料")]
    for g, (sector, label) in enumerate(groups):
        for k, n in enumerate((20, 50, 200)):
            code = f"pct_above_{n}dma" + (f":{sector}" if sector else "")
            api(f"78-{1 + 3 * g + k:03d}", br(code, f"{label} above {n}DMA"), bnote)
    api("78-037", br("advancers", "advancers", "家"), bnote)
    api("78-038", br("decliners", "decliners", "家"), bnote)
    api("78-039", br("median_drawdown_52w", "median drawdown from 52w high"), bnote)
    for iid in ids("80", 1, 18) + ids("81", 1, 10):
        other(iid, "pending", "期权隐波/成交需 Cboe 授权数据")

    # ---------------------------------------------------------- 82-85 能源
    def fut(n):
        return eia(f"PET.RCLC{n}.D", f"NYMEX WTI futures contract {n}", "D", "美元/桶", lag=7)
    api("82-001", fut(1), "EIA 公布的 NYMEX 第 n 近月合约结算价")
    api("82-002", fut(2), "EIA 公布的 NYMEX 第 n 近月合约结算价")
    api("82-003", fut(3), "EIA 公布的 NYMEX 第 n 近月合约结算价")
    api("82-006", f"{fut(1)} - {fut(2)}", "同日近月价差")
    for iid in ["82-004", "82-005", "82-007", "82-008"] + ids("82", 9, 16):
        other(iid, "pending", "远月/Brent 期货曲线需 CME/ICE 授权")
    gas = eia("PET.EER_EPMRU_PF4_RGC_DPG.D", "Gulf Coast conventional gasoline spot", "D", "美元/加仑", lag=7)
    ulsd = eia("PET.EER_EPD2DXL0_PF4_RGC_DPG.D", "Gulf Coast ULSD spot", "D", "美元/加仑", lag=7)
    api("83-001", f"{gas} * 42 - {wti}", "美元/加仑×42 减 WTI 现货（地域不一致，非炼油利润）")
    api("83-002", f"{ulsd} * 42 - {wti}", "美元/加仑×42 减 WTI 现货（地域不一致，非炼油利润）")
    for iid in ids("84", 1, 6):
        other(iid, "manual", "事件型能源供应数据：按官方公告人工维护", "P2")
    for iid in ids("85", 2, 7):
        other(iid, "pending", "原油期权隐波需 CME/ICE 授权")
    for iid in ids("86", 1, 14) + ids("88", 1, 4):
        other(iid, "manual", "民调/政策事件：人工维护", "P2")

    # ---------------------------------------------------------- 90-96 估值、全球指数
    for iid in ids("90", 1, 6):
        other(iid, "report", "由 FactSet/周报远期 PE 快照派生（1/PE），PE 入库后自动计算", "P1b")
    for iid in ids("91", 1, 20):
        other(iid, "pending", "情景参数未在清单中固定，且公司债指数久期需授权")
    for iid in ids("94", 1, 14):
        other(iid, "report", "一致预期 EPS：取 FactSet/周报快照", "P1b")
    for iid in ids("95", 1, 22):
        other(iid, "pending", "MSCI 行业权重：月度 factsheet PDF，待做")
    for iid in ids("95", 34, 55) + ids("95", 65, 82):
        other(iid, "report", "MSCI 行业/风格回报需授权；取高盛 Market Monitor 表格快照", "P1b")

    gidx = [
        ("96-001", "^SP400", "S&P MidCap 400"), ("96-006", "^RUT", "Russell 2000"), ("96-011", "^SPXEW", "S&P 500 Equal Weight"),
        ("96-026", "^FTSE", "FTSE 100"), ("96-031", "FTSEMIB.MI", "FTSE MIB"), ("96-036", "^FCHI", "CAC 40"),
        ("96-041", "^GDAXI", "DAX (performance index)"), ("96-046", "^SSMI", "Swiss Market Index"),
        ("96-051", "^NSEI", "Nifty 50"), ("96-056", "^HSI", "Hang Seng"),
    ]
    snap_base = {"96-001": 107, "96-006": 110, "96-011": 113, "96-026": 122, "96-031": 125, "96-036": 128,
                 "96-041": 131, "96-046": 134, "96-051": 137, "96-056": 140}
    yn = "Yahoo Finance 免费行情（非官方接口），本币价格指数；DAX 为含红利绩效指数"
    for iid, ticker, title in gidx:
        x = yahoo(ticker, title)
        n = int(iid.split("-")[1])
        api(iid, x, yn)
        for k, w in enumerate(["W", "MTD", "QTD", "YTD"], start=1):
            tid = f"96-{n + k:03d}"
            if tid in ("96-007", "96-010"):  # not in the list (removed IDs)
                continue
            api(tid, ret(x, w), yn)
        for k, w in enumerate(["ME", "QE", "YE"]):
            api(f"96-{snap_base[iid] + k:03d}", f'snap({x}, "{w}")', yn)
    for iid in ids("96", 16, 25) + ids("96", 61, 85) + ["96-089", "96-094"] + ids("96", 99, 102) + ["96-104"]:
        other(iid, "report", "MSCI/STOXX 50/TOPIX 需授权；取高盛 Market Monitor 表格快照", "P1b")
    for iid in ids("96", 116, 121) + ids("96", 143, 163) + ids("96", 173, 184) + ids("96", 188, 190):
        other(iid, "report", "期末快照：从高盛周报快照历史序列生成", "P1b")
    nasdaq = fred("NASDAQCOM", "Nasdaq Composite", "D", "点")
    djia = fred("DJIA", "Dow Jones Industrial Average", "D", "点")
    api("96-096", ret(sp500, "QTD"))
    api("96-097", ret(nasdaq, "QTD"))
    api("96-098", ret(djia, "QTD"))
    api("96-103", ret(stoxx600, "QTD"), "Yahoo 免费行情")
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"96-{164 + k:03d}", f'snap({sp500}, "{w}")')
        api(f"96-{167 + k:03d}", f'snap({nasdaq}, "{w}")')
        api(f"96-{170 + k:03d}", f'snap({djia}, "{w}")')
        api(f"96-{185 + k:03d}", f'snap({stoxx600}, "{w}")', "Yahoo 免费行情")

    # ---------------------------------------------------------- 97 跨资产历史图
    btc = yahoo("BTC-USD", "Bitcoin USD")
    for iid, x, note in [("97-081", btc, "Yahoo 免费行情，USD 价格"), ]:
        api(iid, x, note)
    api("97-082", f'ret({btc}, "1Y") + 100', "当日水平÷一年前水平×100")
    api("97-083", f"year_ret({btc}, 2025)", "2025 年末÷2024 年末−1")
    api("97-084", ret(btc, "MTD"))
    api("97-085", ret(btc, "YTD"))
    wti_cols = {"97-097": f'ret({wti}, "1Y") + 100', "97-098": f"year_ret({wti}, 2025)",
                "97-099": ret(wti, "MTD"), "97-100": ret(wti, "YTD")}
    for iid, f in wti_cols.items():
        api(iid, f, "EIA WTI 现货（FRED）")
    for k, w in enumerate(["W", "QTD"]):
        api(f"99-{41 + 2 * k:03d}", ret(btc, w), "Yahoo 免费行情，USD 价格回报")

    # ---------------------------------------------------------- 99 历史基准快照（其余）
    dgs2 = fred("DGS2", "US Treasury 2Y CMT yield", "D", "%")
    t10y2y = fred("T10Y2Y", "T10Y2Y", "D", "%")
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"99-{59 + k:03d}", f'snap({dgs2}, "{w}")')
        api(f"99-{62 + k:03d}", f'snap({dgs10}, "{w}")')
        api(f"99-{65 + k:03d}", f'snap({t10y2y}, "{w}") * 100', "%→bp")
        api(f"99-{74 + k:03d}", f'snap({jgb10}, "{w}")', "日本财务省")
    for iid in ids("99", 68, 73) + ids("99", 77, 85) + ids("99", 92, 94):
        other(iid, "report", "欧洲国债/EMBI 期末快照：从周报快照历史生成", "P1b")
    for iid in ["99-001", "99-002", "99-003", "99-005", "99-006", "99-007", "99-008", "99-013", "99-014", "99-015", "99-016"]:
        other(iid, "report", "瑞士/中国国债与欧元 IG 利差：取高盛周报快照（中债可本地补抓）", "P1b")
    for iid in ["99-029", "99-031", "99-033", "99-035", "99-037", "99-038", "99-039", "99-040"]:
        other(iid, "report", "指数需授权；取高盛周报另类资产表快照", "P1b")

    # ---------------------------------------------------------- 101-102 全球宏观补充
    other("101-001", "pending", "NFIB 无公开接口，月报 PDF 待解析")
    ppi_sa = bls("WPSFD4", "PPI final demand SA", lag=45)
    ppi_nsa = bls("WPUFD4", "PPI final demand NSA", lag=45)
    ppi_core = bls("WPSFD49104", "PPI final demand less foods & energy SA", lag=45)
    ppi_note = "BLS PPI；环比季调、同比未季调"
    api("101-002", ppi_sa, ppi_note)
    api("101-003", f"pop({ppi_sa})", ppi_note)
    api("101-004", f"yoy({ppi_nsa})", ppi_note)
    api("101-005", f"pop({ppi_core})", ppi_note)
    api("102-002", f"prior(pop({ppi_sa}))", "本次发布所列前值（本库逐次留存版本）")
    api("102-005", f"prior(yoy({ppi_nsa}))", "本次发布所列前值（本库逐次留存版本）")
    api("102-008", f"prior(pop({ppi_core}))", "本次发布所列前值（本库逐次留存版本）")
    for iid in ids("101", 6, 10) + ["102-011", "102-014", "102-017", "102-020", "102-023"]:
        other(iid, "pending", "中国海关统计对境外 IP 不稳定，计划本地补抓")
    for iid in ["101-013", "102-032"]:
        other(iid, "pending", "厚生劳动省每月勤劳统计 Excel，待写解析")
    other("101-014", "pending", "BoE DMP 月度 Excel，待写解析")
    for iid in ["101-016", "102-035"]:
        other(iid, "pending", "MoSPI 接口待接入")
    ipca = series("BCB", "13522", "IPCA 12-month accumulated", "M", "%", 12, "https://www3.bcb.gov.br/sgspub/")
    api("101-017", ipca, "巴西央行 SGS 13522（IBGE IPCA 12 个月累计）")
    api("102-038", f"prior({ipca})", "本次发布所列前值（本库逐次留存版本）")
    sc = "https://www150.statcan.gc.ca/"
    ca_cpi = series("STATCAN", "41690973", "Canada CPI all-items NSA", "M", "指数点", 20, sc)
    ca_gdp = series("STATCAN", "65201210", "Canada real GDP monthly", "M", "百万加元", 60, sc)
    ca_emp = series("STATCAN", "2062811", "Canada LFS employment SA", "M", "千人", 8, sc)
    ca_ur = series("STATCAN", "2062815", "Canada unemployment rate SA", "M", "%", 8, sc)
    ca_rt = series("STATCAN", "1446859483", "Canada retail trade sales SA", "M", "千加元", 52, sc)
    can = [("101-018", "102-041", f"yoy({ca_cpi})"), ("101-019", "102-044", f"pop({ca_gdp})"),
           ("101-020", "102-047", f"diff({ca_emp})"), ("101-021", "102-050", ca_ur), ("101-022", "102-053", f"pop({ca_rt})")]
    for a, p, f in can:
        api(a, f, "加拿大统计局 WDS 向量")
        api(p, f"prior({f})", "本次发布所列前值（本库逐次留存版本）")
    for iid in ["101-023", "102-056", "101-024", "102-059"]:
        other(iid, "manual", "智利/土耳其央行接口需注册凭证；按决议人工维护", "P1")
    selic = series("BCB", "432", "Selic target", "D", "%", 0, "https://www3.bcb.gov.br/sgspub/")
    boc = series("BOC", "V39079", "BoC target overnight rate", "D", "%", 0, "https://www.bankofcanada.ca/rates/interest-rates/")
    api("101-025", selic, "巴西央行 SGS 432")
    api("102-062", f"before_change({selic})", "上一次调整前的目标利率")
    api("101-026", boc, "加拿大央行 Valet API")
    api("102-065", f"before_change({boc})", "上一次调整前的目标利率")
    for iid in ["102-003", "102-006", "102-009", "102-012", "102-015", "102-018", "102-021", "102-024", "102-027", "102-030",
                "102-033", "102-036", "102-039", "102-042", "102-045", "102-048", "102-051", "102-054", "102-057", "102-060",
                "102-063", "102-066", "102-069", "102-072", "102-081", "102-084", "102-087", "102-090", "102-093", "102-096"]:
        other(iid, "pending", "首次值已入库；事前调查中位数需授权日历或周报，接入后自动计算")
    for iid in [f"102-{n:03d}" for n in (1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34, 37, 40, 43, 46, 49, 52, 55, 58, 61, 64, 67, 70, 79, 82, 85, 88, 91, 94)]:
        other(iid, "report", "发布前调查中位数：取汇丰周报日历表公开项", "P1b")

    # ---------------------------------------------------------- 105-110
    for iid in ids("105", 1, 20):
        other(iid, "pending", "BEA 直接投资（MNE/ITA API，需 BEA_API_KEY），待接入")
    for iid in ids("106", 1, 17) + ["106-023"]:
        other(iid, "pending", "Fed Z.1 数据下载程序 CSV，待接入")
    for iid in ["106-018", "106-020"]:
        other(iid, "pending", "TIC 文本表，待写解析")
    for iid in ids("107", 1, 13):
        other(iid, "pending", "Preqin/MSCI 需授权")
    countries = [("ES", 2), ("EE", 9), ("FR", 16), ("FI", 23), ("EL", 30), ("SK", 37), ("PL", 44), ("IT", 51)]
    es = "https://ec.europa.eu/eurostat/databrowser/"
    def estat(code, title, unit, params):
        return series("EUROSTAT", code, title, "A", unit, 120, es, params=params)
    eu_gdp = estat("nama_10_gdp:EU27_2020", "EU27 nominal GDP", "百万欧元",
                   {"dataset": "nama_10_gdp", "geo": "EU27_2020", "unit": "CP_MEUR", "na_item": "B1GQ", "sinceTimePeriod": "2015"})
    eu_pop = estat("demo_pjan:EU27_2020", "EU27 population", "人",
                   {"dataset": "demo_pjan", "geo": "EU27_2020", "age": "TOTAL", "sex": "T", "unit": "NR", "sinceTimePeriod": "2015"})
    for geo, b in countries:
        g = estat(f"nama_10_gdp:{geo}", f"{geo} nominal GDP", "百万欧元",
                  {"dataset": "nama_10_gdp", "geo": geo, "unit": "CP_MEUR", "na_item": "B1GQ", "sinceTimePeriod": "2015"})
        p = estat(f"demo_pjan:{geo}", f"{geo} population", "人",
                  {"dataset": "demo_pjan", "geo": geo, "age": "TOTAL", "sex": "T", "unit": "NR", "sinceTimePeriod": "2015"})
        debt = estat(f"gov_10dd_edpt1:GD:{geo}", f"{geo} government debt % GDP", "%",
                     {"dataset": "gov_10dd_edpt1", "geo": geo, "unit": "PC_GDP", "sector": "S13", "na_item": "GD", "sinceTimePeriod": "2015"})
        bal = estat(f"gov_10dd_edpt1:B9:{geo}", f"{geo} government balance % GDP", "%",
                    {"dataset": "gov_10dd_edpt1", "geo": geo, "unit": "PC_GDP", "sector": "S13", "na_item": "B9", "sinceTimePeriod": "2015"})
        note = "Eurostat 年度数据"
        api(f"108-{b:03d}", g, note)
        api(f"108-{b + 1:03d}", p, note)
        api(f"108-{b + 2:03d}", f"{g} / {eu_gdp} * 100", note + "；占 EU27")
        api(f"108-{b + 3:03d}", f"{p} / {eu_pop} * 100", note + "；占 EU27")
        api(f"108-{b + 4:03d}", debt, note)
        api(f"108-{b + 5:03d}", bal, note)
    for n in (1, 8, 15, 22, 29, 36, 43, 50):
        other(f"108-{n:03d}", "manual", "选举日期：以本国选举机关公告为准，人工维护", "P1")
    other("110-001", "pending", "NAR 数据需授权")
    other("110-002", "manual", "BoJ 加息生效日：人工维护", "P1")
    for iid in ["110-004", "110-005"]:
        other(iid, "report", "需希腊/法国/意大利 10 年国债收益率，取周报快照后派生", "P1b")
    for iid in ["110-006", "110-007"]:
        other(iid, "pending", "Eurostat 国际贸易数据集（Comext），待接入")
    for iid in ids("111", 1, 7):
        other(iid, "excluded", "机构历史增长参考值（Amundi 报告固定版本），随机构预测一并排除", "excluded")
    curve_url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates"
    for label in ["6 Mo", "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr"]:
        series("TSYCURVE", label, f"Treasury par yield curve {label}", "D", "%", 1, curve_url,
               params={"type": "daily_treasury_yield_curve"})
    pnote = "按清单定义自算：财政部平价收益率曲线合成平价券（半年付息、线性插值），前6个月平行移动后保持，持有1年"
    for i, tenor in enumerate([1, 2, 3, 5, 7, 10, 20, 30]):
        for k, shift in enumerate([-50, 0, 50]):
            api(f"109-{1 + 3 * i + k:03d}", f'parbond("tr", {tenor}, {shift})', pnote)
        for k, metric in enumerate(["yield", "coupon", "duration", "convexity"]):
            api(f"109-{25 + 4 * i + k:03d}", f'parbond("{metric}", {tenor}, 0)', pnote)


def build_publishers() -> None:
    """Original index publishers found for indicators previously routed to reports."""
    # ---------------------------------------------------------- MSCI end-of-day levels
    msci_url = "https://www.msci.com/end-of-day-data-search"
    mnote = "MSCI 官网日收盘指数（net total return，非官方公开接口；MSCI 条款限非商业用途）"

    def msci(code, title, variant="NETR", ccy="USD", **params):
        key_code = f"{code}:{variant}:{ccy}"
        monthly = params.get("frequency") == "END_OF_MONTH"
        return series("MSCI", key_code, f"MSCI {title} ({variant}, {ccy})", "M" if monthly else "D", "点", 1, msci_url,
                      params=params, key=f"MSCI:{key_code}" + (":EOM" if monthly else ""))

    def level_block(x, ids_windows):
        for iid, w in ids_windows:
            if w == "level":
                api(iid, x, mnote)
            elif w in ("ME", "QE", "YE"):
                api(iid, f'snap({x}, "{w}")', mnote)
            elif w == "NORM1Y":
                api(iid, f'ret({x}, "1Y") + 100', mnote + "；一年前归一100")
            elif w == "Y2025":
                api(iid, f"year_ret({x}, 2025)", mnote)
            else:
                api(iid, ret(x, w), mnote)

    acwi = msci("892400", "ACWI")
    world = msci("990100", "World")
    eafe = msci("990300", "EAFE")
    em = msci("891800", "EM")
    china = msci("302400", "China")
    india_inr = msci("935600", "India", ccy="INR")
    india_usd = msci("935600", "India")
    brazil_brl = msci("907600", "Brazil", ccy="BRL")
    brazil_usd = msci("907600", "Brazil")
    usa = msci("984000", "USA")
    europe = msci("990500", "Europe")
    japan = msci("939200", "Japan")
    eafe_sc = msci("106232", "EAFE Small Cap")
    five = ["level", "W", "MTD", "YTD", "1Y"]
    for base, x in [(1, acwi), (6, world), (11, eafe), (16, em), (31, china), (36, india_inr)]:
        level_block(x, [(f"02-{base + k:03d}", w) for k, w in enumerate(five)])
    for iid, x in [("96-099", acwi), ("96-100", world), ("96-101", eafe), ("96-102", em), ("96-089", china), ("96-094", india_inr)]:
        level_block(x, [(iid, "QTD")])
    for base, x in [(173, acwi), (176, world), (179, eafe), (182, em), (158, china), (161, india_inr),
                    (119, eafe_sc), (143, china), (146, brazil_brl), (149, usa), (152, europe), (155, japan)]:
        level_block(x, [(f"96-{base + k:03d}", w) for k, w in enumerate(["ME", "QE", "YE"])])
    for base, x in [(21, eafe_sc), (61, china), (66, brazil_brl), (71, usa), (76, europe), (81, japan)]:
        level_block(x, [(f"96-{base + k:03d}", w) for k, w in enumerate(["level", "W", "MTD", "QTD", "YTD"])])
    # HSBC cross-asset chart rows (USD net total return)
    level_block(usa, [("97-002", "NORM1Y"), ("97-003", "Y2025")])
    level_block(europe, [("97-007", "NORM1Y"), ("97-008", "Y2025")])
    level_block(japan, [("97-012", "NORM1Y"), ("97-013", "Y2025")])
    level_block(india_usd, [("97-016", "level"), ("97-017", "NORM1Y"), ("97-018", "Y2025"), ("97-019", "MTD"), ("97-020", "YTD")])
    level_block(china, [("97-022", "NORM1Y"), ("97-023", "Y2025")])
    level_block(brazil_usd, [("97-026", "level"), ("97-027", "NORM1Y"), ("97-028", "Y2025"), ("97-029", "MTD"), ("97-030", "YTD")])
    level_block(world, [("97-032", "NORM1Y"), ("97-033", "Y2025")])
    level_block(em, [("97-037", "NORM1Y"), ("97-038", "Y2025")])
    # World GICS sectors (catalog order) and 3x3 style box
    sector_codes = [("通讯服务", "106804"), ("能源", "106796"), ("信息技术", "106803"), ("公用事业", "106805"),
                    ("金融", "106802"), ("必需消费", "106800"), ("房地产", "132085"), ("工业", "106798"),
                    ("可选消费", "106799"), ("医疗保健", "106801"), ("材料", "106797")]
    for i, (name, code) in enumerate(sector_codes):
        x = msci(code, f"World {name}")
        level_block(x, [(f"95-{34 + 2 * i:03d}", "MTD"), (f"95-{35 + 2 * i:03d}", "YTD")])
    style_codes = ["650143", "650038", "650248", "652660", "652555", "652765", "655131", "106230", "655236"]
    for i, code in enumerate(style_codes):
        x = msci(code, f"World style box {code}")
        level_block(x, [(f"95-{65 + 2 * i:03d}", "MTD"), (f"95-{66 + 2 * i:03d}", "YTD")])
    # ACWI quarterly long-horizon statistics (month-end history since 2000-12)
    acwi_m = msci("892400", "ACWI month-end", frequency="END_OF_MONTH", start="2000-12-01")
    q = f"qe({acwi_m})"
    roll10 = f"ann({q}, 40)"
    lnote = "MSCI ACWI 净总回报月末序列（2000-12 起），滚动十年窗口自 2010-12 起"
    api("107-007", f"latest({q})", lnote)
    api("107-008", f"pop({q})", lnote)
    api("107-009", roll10, lnote)
    api("107-010", f"hist_mean({roll10})", lnote)
    api("107-011", f"hist_share({roll10}, 0)", lnote)
    api("107-012", f"hist_share({roll10}, 10)", lnote)

    # ---------------------------------------------------------- STOXX Europe 50 (guest 3-month files, accumulated)
    sx5p = series("STOXX", "sx5p", "STOXX Europe 50 (price, EUR)", "D", "点", 1,
                  "https://www.stoxx.com/index/sx5p/")
    snote = "STOXX 官网（访客仅提供近 3 个月，本库逐周累积；更早的年初基点待补）"
    for k, w in enumerate(["level", "W", "MTD", "QTD", "YTD"]):
        iid = f"96-{16 + k:03d}"
        api(iid, sx5p if w == "level" else ret(sx5p, w), snote)
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"96-{116 + k:03d}", f'snap({sx5p}, "{w}")', snote)

    # ---------------------------------------------------------- TOPIX (JPX daily snapshot, accumulated)
    topix = series("JPX", "TOPIX", "TOPIX (price, JPY)", "D", "点", 0, "https://www.jpx.co.jp/english/markets/indices/topix/")
    tnote = "日本交易所集团每日快照（无历史接口，本库从 2026-10 起逐周累积）"
    for k, w in enumerate(["level", "W", "MTD", "YTD", "1Y"]):
        api(f"02-{26 + k:03d}", topix if w == "level" else ret(topix, w), tnote)
    api("96-104", ret(topix, "QTD"), tnote)
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"96-{188 + k:03d}", f'snap({topix}, "{w}")', tnote)

    # ---------------------------------------------------------- S&P DJI month-end characteristics
    spdji = "https://www.spglobal.com/spdji/en/indices/equity/sp-500/"
    api("06-003", series("SPDJI", "340:marketCap", "S&P 500 total market cap (month-end)", "M", "十亿美元", 5, spdji, runner="local"),
        "S&P 道琼斯指数公司官网，月末值；美元→十亿美元（该站屏蔽数据中心 IP，由本地电脑抓取）")
    api("07-001", series("SPDJI", "340:topNConstituentWeight", "S&P 500 top-10 weight (month-end)", "M", "%", 5, spdji, runner="local"),
        "S&P 道琼斯指数公司官网，月末值（由本地电脑抓取）")


def build_batch2() -> None:
    """Verified official sources from the second research round."""
    # ---------------------------------------------------------- German / UK yields
    bbk = "https://www.bundesbank.de/en/statistics/money-and-capital-markets/interest-rates-and-yields"
    de2 = series("BBK", "BBSSY/D.REN.EUR.A610.000000WT0202.A", "Bund current 2Y (Schatz) yield", "D", "%", 0, bbk)
    de10 = series("BBK", "BBSSY/D.REN.EUR.A630.000000WT1010.A", "Bund current 10Y yield", "D", "%", 0, bbk)
    bnote = "德国央行：当期基准券日收益率（非常数期限，随新券滚动）"
    api("15-001", de2, bnote)
    api("15-002", de10, bnote)
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"99-{68 + k:03d}", f'snap({de2}, "{w}")', bnote)
        api(f"99-{71 + k:03d}", f'snap({de10}, "{w}")', bnote)
    uk10 = series("BOE", "IUDMNZC", "UK 10Y nominal zero-coupon yield (BoE fitted curve)", "D", "%", 1,
                  "https://www.bankofengland.co.uk/statistics/yield-curves")
    unote = "英格兰银行拟合名义零息曲线 10 年点（与基准券报价可能差几个 bp）"
    api("15-008", uk10, unote)
    for k, w in enumerate(["ME", "QE", "YE"]):
        api(f"99-{77 + k:03d}", f'snap({uk10}, "{w}")', unote)

    # ---------------------------------------------------------- policy rates via BIS
    bis = "https://data.bis.org/topics/CBPOL"
    def cbpol(cc, title):
        return series("BIS", f"WS_CBPOL/D.{cc}", f"{title} policy rate (BIS)", "D", "%", 3, bis)
    jp, cl, tr = cbpol("JP", "Bank of Japan"), cbpol("CL", "Banco Central de Chile"), cbpol("TR", "CBRT one-week repo")
    pnote = "国际清算银行央行政策利率库（各央行官方利率汇总，滞后约 3 个工作日）"
    for level_id, prior_id, x in [("20-005", "102-092", jp), ("101-023", "102-056", cl), ("101-024", "102-059", tr)]:
        api(level_id, x, pnote)
        api(prior_id, f"before_change({x})", "上一次调整前的政策利率（BIS）")

    # ---------------------------------------------------------- FRED additions
    api("19-007", fred("BAMLC0A0CMSYTW", "ICE BofA US Corporate yield to worst", "D", "%"), ice_note_text())
    api("19-011", fred("BAMLH0A0HYM2SYTW", "ICE BofA US High Yield yield to worst", "D", "%"), ice_note_text())
    api("110-001", f"{fred('EXHOSLUSM495S', 'Existing home sales SAAR (NAR)', 'M', '套', lag=25)} / 10000",
        "NAR 成屋销售（FRED 仅保留约 13 个月，本库逐月累积）；套→万套")
    fdi = fred("IEAIDI", "Direct investment liabilities incurred (BEA ITA)", "Q", "百万美元", lag=90)
    api("105-019", fdi, "BEA 国际交易账户直接投资负债流入（FRED）")
    api("105-020", f"msum({fdi}, 4)", "过去四季合计")

    # ---------------------------------------------------------- Fed Z.1 holders of Treasuries (FRED mirror)
    def z1(code):
        return fred(f"BOGZ1{code}Q", f"Z.1 {code}", "Q", "百万美元", lag=75)
    total = z1("FL893061105")
    holders = {
        "106-001": [z1("LM153061105")],
        "106-003": [z1("LM763061100"), z1("LM753061103"), z1("LM743061103"), z1("LM473061105")],
        "106-005": [z1("LM653061105")],
        "106-007": [z1("FL633061105")],
        "106-009": [z1("LM563061103")],
        "106-011": [z1("LM573061105")],
        "106-013": [z1("LM223061143")],
        "106-015": [z1("LM513061105"), z1("LM543061105")],
    }
    znote = "美联储 Z.1 表 F3.2.s（FRED 镜像，季度）；市值口径分子 / 总额 FL893061105"
    for level_id, parts in holders.items():
        num = "(" + " + ".join(parts) + ")" if len(parts) > 1 else parts[0]
        share_id = f"106-{int(level_id.split('-')[1]) + 1:03d}"
        api(level_id, f"{num} / 1000", znote + "；百万→十亿美元")
        api(share_id, f"{num} / {total} * 100", znote)
    api("106-017", f"{z1('LM713061103')} / {total} * 100", znote)
    residual = " - ".join([total, z1("LM713061103"), z1("LM263061105"), z1("LM213061103"), z1("LM343061105"), z1("LM403061105")])
    api("106-023", f"({residual}) / {total} * 100", znote + "；残差法")

    # ---------------------------------------------------------- MSCI World risk statistics
    world = "{MSCI:990100:NETR:USD}"
    mnote = "MSCI World 净总回报（官网日收盘）"
    api("51-004", f'vol({world}, "52W")', mnote + "；周五采样周收益标准差×√52")
    api("51-005", f"drawdown({world})", mnote + "；相对本库已存历史高点（2020-10 起）")
    api("51-006", f'maxdd({world}, "YTD")', mnote)
    api("51-013", f'ret({world}, "W") - ret({{FRED:SP500}}, "W")', "MSCI World 净总回报减 S&P 500 价格回报（口径不同，含股息差）")

    # ---------------------------------------------------------- BEA official PCE price contributions
    bea_url = "https://apps.bea.gov/iTable/?reqid=19&step=2&isuri=1&categories=survey"
    api("30-008", series("BEA", "NIPA:T20808:line=2", "Contribution of goods to PCE price change (T2.8.8)", "M", "百分点", 60, bea_url),
        "BEA 官方表 2.8.8 月度贡献（商品）")
    api("30-010", series("BEA", "NIPA:T20808:line=13", "Contribution of services to PCE price change (T2.8.8)", "M", "百分点", 60, bea_url),
        "BEA 官方表 2.8.8 月度贡献（服务）")


def build_factset() -> None:
    url = "https://insight.factset.com/topic/earnings"
    note = "FactSet Earnings Insight 每周 PDF 正文（FactSet 为原始发布方）；按期留存"
    def fs(metric, title, unit="%"):
        return series("FACTSET", metric, f"FactSet Earnings Insight: {title}", "W", unit, 0, url)
    pe = fs("forward_pe", "S&P 500 forward 12M P/E", "倍")
    api("05-001", pe, note)
    for iid, metric, title in [
        ("08-001", "eps_growth_blended", "blended EPS growth y/y"), ("08-002", "revenue_growth_blended", "blended revenue growth y/y"),
        ("08-003", "net_margin_blended", "blended net profit margin"), ("08-037", "pct_reported", "% of companies reported"),
        ("08-038", "cy_eps_growth_0", "current CY EPS growth"), ("08-039", "cy_eps_growth_1", "next CY EPS growth"),
        ("08-040", "cy_eps_growth_2", "second CY EPS growth"), ("09-001", "pct_eps_beat", "% beating EPS"),
        ("09-002", "pct_revenue_beat", "% beating revenue"), ("09-003", "eps_surprise_aggregate", "aggregate EPS surprise"),
        ("09-004", "revenue_surprise_aggregate", "aggregate revenue surprise"),
    ]:
        api(iid, fs(metric, title), note)
    api("09-005", fs("guidance_positive_next_q", "positive EPS guidance (next quarter)", "家"), note + "；下一季度指引口径")
    api("09-006", fs("guidance_negative_next_q", "negative EPS guidance (next quarter)", "家"), note + "；下一季度指引口径")
    api("90-001", f"100 / {pe}", "1 / FactSet 远期 P/E")
    api("90-002", f"100 / {pe} - {{FRED:DGS10}}", "1 / FactSet 远期 P/E 减美国 10 年国债收益率")


def build_batch3() -> None:
    """Parsers written against real file samples: TIC, Japan CPI, NY Fed SCE, ISM, consensus calendar."""
    # ---------------------------------------------------------- TIC
    tic_url = "https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table5.txt"
    total = series("TIC", "Grand Total", "Foreign holdings of Treasuries, total (TIC)", "M", "十亿美元", 50, tic_url)
    official = series("TIC", "Of Which: Foreign Official", "Foreign official holdings of Treasuries (TIC)", "M", "十亿美元", 50, tic_url)
    tnote = "美国财政部 TIC 表 5（文件只含近 13 个月，本库逐月累积）"
    api("106-018", official, tnote)
    api("106-020", f"{total} - {official}", tnote + "；外国私人 = 合计 − 官方")

    # ---------------------------------------------------------- Japan CPI
    jp_url = "https://www.stat.go.jp/data/cpi/"
    jp_head = series("JPCPI", "headline_yoy", "Japan CPI all items y/y", "M", "%", 25, jp_url)
    jp_core = series("JPCPI", "ex_fresh_yoy", "Japan CPI ex fresh food y/y", "M", "%", 25, jp_url)
    jnote = "日本总务省统计局 CPI 指数 CSV，同一基期内计算同比（2026 年起为 2025 年基期）"
    api("42-001", jp_head, jnote)
    api("42-002", jp_core, jnote)
    api("102-080", f"prior({jp_head})", "本次发布所列前值（本库逐次留存版本）")

    # ---------------------------------------------------------- NY Fed SCE
    sce_url = "https://www.newyorkfed.org/microeconomics/sce"
    def sce(code, title, unit):
        return series("SCE", code, f"NY Fed SCE: {title}", "M", unit, 12, sce_url)
    snote = "纽约联储消费者预期调查（官方图表数据 Excel）"
    for k, horizon in enumerate(["one", "three", "five"]):
        med = sce(f"Median {horizon}-year ahead expected inflation rate", f"median {horizon}-year inflation expectation", "%")
        spread = sce(f"75th Percentile {horizon}-year ahead expected inflation rate - 25th Percentile {horizon}-year ahead expected inflation rate",
                     f"{horizon}-year P75-P25", "百分点")
        api(f"63-{3 + 2 * k:03d}", med, snote)
        api(f"63-{4 + 2 * k:03d}", spread, snote + "；75 分位减 25 分位")

    # ---------------------------------------------------------- ISM manufacturing
    ism_url = "https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/"
    def ism(code, title):
        return series("ISM", code, f"ISM Manufacturing {title}", "M", "指数点", 3, ism_url)
    inote = "ISM 制造业报告 PDF（个人非商业使用条款）；每期同时给出上月值"
    for iid, code, title in [("36-001", "pmi", "PMI"), ("36-002", "new_orders", "New Orders"), ("36-003", "employment", "Employment"),
                             ("36-004", "prices", "Prices"), ("36-005", "inventories", "Inventories")]:
        api(iid, ism(code, title), inote)
    api("36-011", f"{ism('new_orders', 'New Orders')} - {ism('inventories', 'Inventories')}", inote)

    # ---------------------------------------------------------- consensus (Forex Factory calendar)
    ff_url = "https://www.forexfactory.com/calendar"
    def ff(country, title, field="forecast", unit="%", scale=1):
        return series("FFCAL", f"{country}|{title}|{field}", f"Consensus {country} {title} ({field})", "E", unit, 0, ff_url,
                      params={"scale": scale} if scale != 1 else None)
    fnote = "Forex Factory 经济日历的市场预期（第三方汇编的一致预期，非原调查机构中位数；本库从 2026-10 起逐周留存）"
    gdp_cons = [ff("USD", t) for t in ("Advance GDP q/q", "Prelim GDP q/q", "Final GDP q/q")]
    consensus = {
        "52-001": ff("USD", "CPI y/y"), "52-003": ff("USD", "Core CPI m/m"), "52-005": ff("USD", "Core PCE Price Index m/m"),
        "52-007": ff("USD", "Non-Farm Employment Change", unit="千人", scale=1000), "52-009": ff("USD", "Retail Sales m/m"),
        "52-013": ff("EUR", "CPI Flash Estimate y/y"), "52-015": ff("GBP", "CPI y/y"), "52-017": ff("JPY", "National Core CPI y/y"),
        "52-019": ff("CNY", "GDP q/y"),
        "102-001": ff("USD", "PPI m/m"), "102-007": ff("USD", "Core PPI m/m"),
        "102-016": ff("CNY", "Trade Balance", unit="亿美元", scale=1e8), "102-025": ff("GBP", "GDP m/m"),
        "102-043": ff("CAD", "GDP m/m"), "102-046": ff("CAD", "Employment Change", unit="千人", scale=1000),
        "102-049": ff("CAD", "Unemployment Rate"), "102-052": ff("CAD", "Retail Sales m/m"), "102-064": ff("CAD", "Overnight Rate"),
        "102-067": ff("CNY", "Industrial Production y/y"), "102-070": ff("CNY", "Retail Sales y/y"),
        "102-082": ff("USD", "Industrial Production m/m"), "102-085": ff("USD", "Federal Funds Rate"),
        "102-088": ff("GBP", "Official Bank Rate"), "102-091": ff("JPY", "BOJ Policy Rate"),
    }
    for iid, x in consensus.items():
        api(iid, x, fnote)
    api("52-011", f"newest({', '.join(gdp_cons)})", fnote + "；取最近一次（初值/修正/终值）")
    api("102-094", f"{ff('EUR', 'Main Refinancing Rate')} - 0.15", fnote + "；DFR 预期 = MRO 预期 − 0.15（2024-09 起固定利差，推算）")
    for iid, title, unit, scale in [("102-017", "Trade Balance", "亿美元", 1e8), ("102-068", "Industrial Production y/y", "%", 1),
                                    ("102-071", "Retail Sales y/y", "%", 1)]:
        api(iid, ff("CNY", title, "previous", unit, scale), "Forex Factory 日历所列前值（第三方）")

    # ---------------------------------------------------------- surprises: first print − consensus snapshot
    snote2 = "首次公布值（本库留存版本/ALFRED）减当次发布前的 Forex Factory 预期；从开始留存预期之日起可算"
    surprises = {
        "54-001": ("yoy({BLS:CUUR0000SA0})", [consensus["52-001"]]),
        "54-002": ("pop({BLS:CUSR0000SA0L1E})", [consensus["52-003"]]),
        "54-003": ("pop({FRED:PCEPILFE})", [consensus["52-005"]]),
        "54-004": ("diff({FRED:PAYEMS})", [consensus["52-007"]]),
        "54-005": ("pop({FRED:RSAFS})", [consensus["52-009"]]),
        "54-006": ("{FRED:A191RL1Q225SBEA}", gdp_cons),
        "54-007": ("{EUROSTAT:prc_hicp_minr:EA:TOTAL}", [consensus["52-013"]]),
        "54-008": ("{ONS:D7G7}", [consensus["52-015"]]),
        "54-009": ("{JPCPI:ex_fresh_yoy}", [consensus["52-017"]]),
        "102-003": ("pop({BLS:WPSFD4})", [consensus["102-001"]]),
        "102-009": ("pop({BLS:WPSFD49104})", [consensus["102-007"]]),
        "102-027": ("pop({ONS:ECY2})", [consensus["102-025"]]),
        "102-045": ("pop({STATCAN:65201210})", [consensus["102-043"]]),
        "102-048": ("diff({STATCAN:2062811})", [consensus["102-046"]]),
        "102-051": ("{STATCAN:2062815}", [consensus["102-049"]]),
        "102-054": ("pop({STATCAN:1446859483})", [consensus["102-052"]]),
        "102-084": ("pop({FRED:INDPRO})", [consensus["102-082"]]),
    }
    for iid, (actual, cons) in surprises.items():
        api(iid, f"surprise({actual}, {', '.join(cons)})", snote2)


def ice_note_text() -> str:
    return "ICE BofA via FRED（FRED 仅提供约 3 年日频历史，之后本库逐周累积）"


def write() -> tuple[int, int]:
    build()
    build_publishers()
    build_batch2()
    build_factset()
    build_batch3()
    catalog = load_catalog()
    by_id = {r["indicator_id"]: r for r in catalog}
    unknown = sorted(set(MAP) - set(by_id))
    if unknown:
        raise ValueError(f"mapping references ids not in catalog: {unknown[:20]}")
    rows = []
    for r in catalog:
        iid = r["indicator_id"]
        if iid in MAP:
            m = MAP[iid]
        elif r["module"] in EXCLUDED_MODULES:
            m = {"method": "excluded", "phase": "excluded", "formula": "", "coverage_note": "按需求排除机构预测"}
        else:
            host = r["source_url"].split("/")[2] if r["source_url"].count("/") >= 2 else ""
            if host in REPORT_SOURCES:
                m = {"method": "report", "phase": "P1b", "formula": "", "coverage_note": f"取{REPORT_SOURCES[host]}快照"}
            else:
                m = {"method": "pending", "phase": "P2", "formula": "", "coverage_note": "未接入免费来源"}
        rows.append({"indicator_id": iid, **m})
    with MAPPING_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["indicator_id", "method", "phase", "formula", "coverage_note"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with SERIES_CSV.open("w", newline="", encoding="utf-8") as fh:
        cols = ["key", "provider", "code", "title", "frequency", "unit", "release_lag_days", "source_url", "params", "vintages", "runner"]
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for s in sorted(SERIES.values(), key=lambda s: s.key):
            d = asdict(s)
            d["params"] = json.dumps(d["params"], ensure_ascii=False, sort_keys=True) if d["params"] else ""
            w.writerow(d)
    return len(rows), len(SERIES)


def load_series() -> list[dict]:
    with SERIES_CSV.open(newline="", encoding="utf-8") as fh:
        out = []
        for r in csv.DictReader(fh):
            r["params"] = json.loads(r["params"]) if r["params"] else {}
            r["release_lag_days"] = int(r["release_lag_days"])
            r["vintages"] = r["vintages"] == "True"
            out.append(r)
        return out


def load_mapping() -> dict[str, dict]:
    with MAPPING_CSV.open(newline="", encoding="utf-8") as fh:
        return {r["indicator_id"]: r for r in csv.DictReader(fh)}


if __name__ == "__main__":
    n_ind, n_ser = write()
    print(f"mapping.csv: {n_ind} indicators; series.csv: {n_ser} raw series")
