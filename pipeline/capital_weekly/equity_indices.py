from __future__ import annotations

import io
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pipeline.common import load_config_rows

from .history import truncate_history_as_of
from .returns import calculate_return_snapshot


DEFAULT_UNIVERSE_PATH = None
FTSE_RUSSELL_2000_YTD_URL = (
    "https://research.ftserussell.com/products/russell-index-values/home/"
    "getfile?id=valuesytd_US2000.csv"
)


@dataclass(frozen=True)
class IndexConfig:
    region: str
    index_name_cn: str
    index_name_en: str
    ticker: str
    currency: str
    provider: str
    provider_symbol: str
    source: str
    notes: str = ""


def load_index_universe(path: str | Path | None = DEFAULT_UNIVERSE_PATH) -> list[IndexConfig]:
    configs = [IndexConfig(**row) for row in load_config_rows("indices", path)]
    seen: set[str] = set()
    for config in configs:
        if config.ticker in seen:
            raise ValueError(f"Duplicate index ticker: {config.ticker}")
        seen.add(config.ticker)
    return configs


def source_url(config: IndexConfig) -> str:
    symbol = requests.utils.quote(config.provider_symbol, safe="")
    if config.provider == "yahoo_ftse_russell":
        yahoo_url = (
            "https://query2.finance.yahoo.com/v8/finance/chart/"
            f"{symbol}?range=2y&interval=1d&events=history"
        )
        return f"{yahoo_url} | {FTSE_RUSSELL_2000_YTD_URL}"
    if config.provider == "hsi_chart":
        return f"https://www.hsi.com.hk/data/eng/indexes/{symbol}/chart.json"
    if config.provider == "sina_us":
        return (
            "https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var_usdaily="
            f"/US_MinKService.getDailyK?symbol={symbol}&___qn=3"
        )
    if config.provider == "sina_global":
        return f"https://gi.finance.sina.com.cn/hq/daily?symbol={symbol}&num=1000"
    if config.provider == "tencent_kline":
        return f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,400,qfq"
    if config.provider == "eastmoney_kline":
        return (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get?"
            f"secid={symbol}&klt=101&fqt=1&lmt=1000&end=20500000&iscca=1&"
            "fields1=f1,f2,f3,f4,f5,f6,f7,f8&"
            "fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        )
    raise ValueError(f"Unsupported provider: {config.provider}")


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.25,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.sina.com.cn/",
        }
    )
    return session


def _fetch_text(session: requests.Session, url: str, timeout: int = 25) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def _parse_sina_us(text: str) -> pd.DataFrame:
    match = re.search(r"var_usdaily=\((.*)\);?\s*$", text, flags=re.S)
    if not match or match.group(1) == "null":
        raise ValueError("Sina US response did not contain daily data")
    raw = json.loads(match.group(1))
    rows = [
        {
            "date": item["d"],
            "open": item.get("o"),
            "high": item.get("h"),
            "low": item.get("l"),
            "close": item.get("c"),
            "volume": item.get("v", 0),
        }
        for item in raw
    ]
    return _normalize_ohlcv(rows)


def _parse_sina_global(text: str) -> pd.DataFrame:
    raw = json.loads(text)
    data = raw.get("result", {}).get("data")
    if not isinstance(data, list):
        raise ValueError("Sina global response did not contain daily data")
    rows = [
        {
            "date": item["d"],
            "open": item.get("o"),
            "high": item.get("h"),
            "low": item.get("l"),
            "close": item.get("c"),
            "volume": item.get("v", 0),
        }
        for item in data
    ]
    return _normalize_ohlcv(rows)


def _parse_tencent_kline(text: str, symbol: str) -> pd.DataFrame:
    raw = json.loads(text)
    data = raw.get("data", {}).get(symbol, {})
    rows = data.get("qfqday") or data.get("day")
    if not isinstance(rows, list):
        raise ValueError("Tencent response did not contain daily data")
    parsed = [
        {
            "date": item[0],
            "open": item[1],
            "close": item[2],
            "high": item[3],
            "low": item[4],
            "volume": item[5] if len(item) > 5 else 0,
        }
        for item in rows
    ]
    return _normalize_ohlcv(parsed)


def _parse_eastmoney_kline(text: str) -> pd.DataFrame:
    raw = json.loads(text)
    klines = raw.get("data", {}).get("klines")
    if not isinstance(klines, list) or not klines:
        raise ValueError("Eastmoney response did not contain daily data")
    rows = []
    for line in klines:
        parts = line.split(",")
        rows.append(
            {
                "date": parts[0],
                "open": parts[1],
                "close": parts[2],
                "high": parts[3],
                "low": parts[4],
                "volume": parts[5],
            }
        )
    return _normalize_ohlcv(rows)


def _parse_yahoo_chart_ohlcv(text: str) -> pd.DataFrame:
    try:
        raw = json.loads(text)
        result = raw["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
        raise ValueError("Yahoo Finance response did not contain daily data") from error
    rows = []
    for index, timestamp in enumerate(timestamps):
        rows.append(
            {
                "date": datetime.fromtimestamp(timestamp, tz=ZoneInfo("UTC")).date(),
                "open": quote.get("open", [None] * len(timestamps))[index],
                "high": quote.get("high", [None] * len(timestamps))[index],
                "low": quote.get("low", [None] * len(timestamps))[index],
                "close": quote.get("close", [None] * len(timestamps))[index],
                "volume": quote.get("volume", [0] * len(timestamps))[index],
            }
        )
    history = _normalize_ohlcv(rows)
    if history.empty:
        raise ValueError("Yahoo Finance response did not contain usable daily data")
    return history


def _parse_ftse_russell_csv(text: str) -> pd.DataFrame:
    try:
        raw = pd.read_csv(io.StringIO(text.lstrip("\ufeff")))
    except Exception as error:
        raise ValueError("FTSE Russell response was not valid CSV") from error
    required = {"Date", "Value_Without_Dividends__USD_"}
    if not required.issubset(raw.columns):
        raise ValueError("FTSE Russell response did not contain price index data")
    rows = [
        {
            "date": item.Date,
            "open": item.Value_Without_Dividends__USD_,
            "high": item.Value_Without_Dividends__USD_,
            "low": item.Value_Without_Dividends__USD_,
            "close": item.Value_Without_Dividends__USD_,
            "volume": 0,
        }
        for item in raw.itertuples(index=False)
    ]
    history = _normalize_ohlcv(rows)
    if history.empty:
        raise ValueError("FTSE Russell response did not contain usable daily data")
    return history


def _merge_rut_history(
    yahoo: pd.DataFrame,
    ftse: pd.DataFrame,
    ratio_tolerance: float = 1e-4,
) -> pd.DataFrame:
    overlap = yahoo[["date", "close"]].merge(
        ftse[["date", "close"]], on="date", suffixes=("_yahoo", "_ftse")
    ).sort_values("date").tail(20)
    if len(overlap) < 2:
        raise ValueError("RUT sources did not have enough overlapping dates")
    ratios = overlap["close_yahoo"] / overlap["close_ftse"]
    scale = float(ratios.median())
    if (
        not math.isfinite(scale)
        or scale <= 0
        or float((ratios.max() - ratios.min()) / scale) > ratio_tolerance
    ):
        raise ValueError("RUT source scale ratio was unstable")

    yahoo_latest = yahoo["date"].max()
    extension = ftse[ftse["date"] > yahoo_latest].copy()
    for column in ("open", "high", "low", "close"):
        extension[column] = extension[column] * scale
    merged = pd.concat([yahoo, extension], ignore_index=True)
    return merged.sort_values("date").drop_duplicates("date", keep="first").reset_index(drop=True)


def _parse_hsi_chart(text: str, expected_code: str) -> pd.DataFrame:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("Hang Seng Indexes response was not valid JSON") from error
    if raw.get("indexCode") != expected_code:
        raise ValueError("Hang Seng Indexes response had an unexpected index code")
    levels = raw.get("indexLevels-1y")
    if not isinstance(levels, list) or not levels:
        raise ValueError("Hang Seng Indexes response did not contain one-year daily data")
    rows = []
    for item in levels:
        if not isinstance(item, list) or len(item) < 2:
            raise ValueError("Hang Seng Indexes response contained an invalid daily record")
        value = item[1]
        rows.append(
            {
                "date": datetime.fromtimestamp(
                    item[0] / 1000, tz=ZoneInfo("Asia/Hong_Kong")
                ).date(),
                "open": value,
                "high": value,
                "low": value,
                "close": value,
                "volume": 0,
            }
        )
    history = _normalize_ohlcv(rows)
    if history.empty:
        raise ValueError("Hang Seng Indexes response did not contain usable daily data")
    return history


def _normalize_ohlcv(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    for column in ["open", "high", "low", "close", "volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["date", "close"]).sort_values("date")
    return frame[["date", "open", "high", "low", "close", "volume"]]


def fetch_history(config: IndexConfig, session: requests.Session | None = None) -> tuple[pd.DataFrame, str]:
    active_session = session or _session()
    url = source_url(config)
    if config.provider == "yahoo_ftse_russell":
        yahoo_url, ftse_url = url.split(" | ", maxsplit=1)
        yahoo_text = _fetch_text(active_session, yahoo_url)
        ftse_text = _fetch_text(active_session, ftse_url)
        history = _merge_rut_history(
            _parse_yahoo_chart_ohlcv(yahoo_text),
            _parse_ftse_russell_csv(ftse_text),
        )
        raw_text = (
            "=== Yahoo Finance ===\n"
            f"{yahoo_text}\n"
            "=== FTSE Russell ===\n"
            f"{ftse_text}"
        )
        return history, raw_text
    text = _fetch_text(active_session, url)
    if config.provider == "sina_us":
        return _parse_sina_us(text), text
    if config.provider == "sina_global":
        return _parse_sina_global(text), text
    if config.provider == "tencent_kline":
        return _parse_tencent_kline(text, config.provider_symbol), text
    if config.provider == "eastmoney_kline":
        return _parse_eastmoney_kline(text), text
    if config.provider == "hsi_chart":
        return _parse_hsi_chart(text, config.provider_symbol), text
    raise ValueError(f"Unsupported provider: {config.provider}")


def _market_close_context(config: IndexConfig) -> tuple[ZoneInfo, time] | None:
    if config.provider == "yahoo_ftse_russell":
        return ZoneInfo("America/New_York"), time(16, 15)
    if config.provider == "hsi_chart":
        return ZoneInfo("Asia/Hong_Kong"), time(16, 15)
    if (
        config.provider == "eastmoney_kline"
        and config.provider_symbol.startswith("124.")
    ):
        return ZoneInfo("Asia/Hong_Kong"), time(16, 15)
    if config.provider != "tencent_kline":
        return None
    if config.provider_symbol.startswith("hk"):
        return ZoneInfo("Asia/Hong_Kong"), time(16, 15)
    if config.provider_symbol.startswith(("sh", "sz")):
        return ZoneInfo("Asia/Hong_Kong"), time(15, 10)
    return None


def _drop_unfinished_current_day(
    history: pd.DataFrame,
    config: IndexConfig,
    now_hkt: datetime | None = None,
) -> pd.DataFrame:
    close_context = _market_close_context(config)
    if close_context is None or history.empty:
        return history

    now_hkt = now_hkt or datetime.now(ZoneInfo("Asia/Hong_Kong"))
    if now_hkt.tzinfo is None:
        now_hkt = now_hkt.replace(tzinfo=ZoneInfo("Asia/Hong_Kong"))
    market_timezone, close_buffer = close_context
    market_now = now_hkt.astimezone(market_timezone)
    latest_date = history["date"].max()
    if latest_date == market_now.date() and market_now.time() < close_buffer:
        return history[history["date"] < latest_date].copy()
    return history


def _series_for_returns(history: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {"date": row.date, "value": float(row.close)}
        for row in history.itertuples(index=False)
    ]


def _snapshot_row(config: IndexConfig, snapshot: Any, source: str, url: str) -> dict[str, Any]:
    row = asdict(config)
    row.update(
        {
            "latest_date": snapshot.latest_date.isoformat(),
            "latest_value": snapshot.latest_value,
            "daily_base_value": snapshot.daily_base_value,
            "daily_change": snapshot.daily_change,
            "weekly_base_value": snapshot.weekly_base_value,
            "weekly_change": snapshot.weekly_change,
            "mtd_base_value": snapshot.mtd_base_value,
            "mtd_change": snapshot.mtd_change,
            "ytd_base_value": snapshot.ytd_base_value,
            "ytd_change": snapshot.ytd_change,
            "change_unit": snapshot.change_unit,
            "daily_base_date": snapshot.daily_base_date.isoformat()
            if snapshot.daily_base_date
            else None,
            "weekly_base_date": snapshot.weekly_base_date.isoformat()
            if snapshot.weekly_base_date
            else None,
            "mtd_base_date": snapshot.mtd_base_date.isoformat()
            if snapshot.mtd_base_date
            else None,
            "ytd_base_date": snapshot.ytd_base_date.isoformat()
            if snapshot.ytd_base_date
            else None,
            "qc_flag": snapshot.qc_flag,
            "source": source,
            "source_url": url,
        }
    )
    return row


def fetch_equity_indices(
    universe_path: str | Path | None = DEFAULT_UNIVERSE_PATH,
    raw_dir: str | Path | None = None,
    as_of_date: date | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    session = _session()
    rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    raw_path = Path(raw_dir) if raw_dir else None
    if raw_path:
        raw_path.mkdir(parents=True, exist_ok=True)

    for config in load_index_universe(universe_path):
        url = source_url(config)
        started_at = datetime.now()
        try:
            history, raw_text = fetch_history(config, session=session)
            history = _drop_unfinished_current_day(history, config)
            history = truncate_history_as_of(history, as_of_date)
            if raw_path:
                (raw_path / f"{config.ticker.replace('.', '_')}.txt").write_text(
                    raw_text, encoding="utf-8"
                )
            snapshot = calculate_return_snapshot(_series_for_returns(history), "pct")
            rows.append(_snapshot_row(config, snapshot, config.source, url))
            source_rows.append(
                {
                    "ticker": config.ticker,
                    "source": config.source,
                    "status": "OK",
                    "observations": len(history),
                    "latest_date": snapshot.latest_date.isoformat(),
                    "latest_value": snapshot.latest_value,
                    "daily_base_date": snapshot.daily_base_date.isoformat(),
                    "daily_base_value": snapshot.daily_base_value,
                    "weekly_base_date": snapshot.weekly_base_date.isoformat()
                    if snapshot.weekly_base_date
                    else None,
                    "weekly_base_value": snapshot.weekly_base_value,
                    "mtd_base_date": snapshot.mtd_base_date.isoformat()
                    if snapshot.mtd_base_date
                    else None,
                    "mtd_base_value": snapshot.mtd_base_value,
                    "ytd_base_date": snapshot.ytd_base_date.isoformat()
                    if snapshot.ytd_base_date
                    else None,
                    "ytd_base_value": snapshot.ytd_base_value,
                    "elapsed_ms": int((datetime.now() - started_at).total_seconds() * 1000),
                    "source_url": url,
                    "notes": config.notes,
                }
            )
        except Exception as error:
            failed = asdict(config)
            failed.update(
                {
                    "latest_date": None,
                    "latest_value": None,
                    "daily_base_value": None,
                    "daily_change": None,
                    "weekly_base_value": None,
                    "weekly_change": None,
                    "mtd_base_value": None,
                    "mtd_change": None,
                    "ytd_base_value": None,
                    "ytd_change": None,
                    "change_unit": "pct",
                    "daily_base_date": None,
                    "weekly_base_date": None,
                    "mtd_base_date": None,
                    "ytd_base_date": None,
                    "qc_flag": "FETCH_FAILED",
                    "source_url": url,
                }
            )
            rows.append(failed)
            source_rows.append(
                {
                    "ticker": config.ticker,
                    "source": config.source,
                    "status": "FETCH_FAILED",
                    "observations": 0,
                    "latest_date": None,
                    "latest_value": None,
                    "daily_base_date": None,
                    "daily_base_value": None,
                    "weekly_base_date": None,
                    "weekly_base_value": None,
                    "mtd_base_date": None,
                    "mtd_base_value": None,
                    "ytd_base_date": None,
                    "ytd_base_value": None,
                    "elapsed_ms": int((datetime.now() - started_at).total_seconds() * 1000),
                    "source_url": url,
                    "notes": str(error),
                }
            )

    return pd.DataFrame(rows), pd.DataFrame(source_rows)
