from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import quote

import pandas as pd


REQUIRED_ROLES = frozenset({"vix_9d", "vix_1m", "vix_3m", "vix_6m", "skew"})
CONFIG_FIELDS = ("metric_code", "metric_name", "ticker", "unit", "role")


@dataclass(frozen=True)
class YahooVolatilitySeries:
    metric_code: str
    metric_name: str
    ticker: str
    unit: str
    role: str


def yahoo_history_url(ticker: str) -> str:
    return f"https://finance.yahoo.com/quote/{quote(ticker, safe='')}/history/"


def load_yahoo_volatility_config(
    source: str | Path | Iterable[Mapping[str, str]],
) -> tuple[YahooVolatilitySeries, ...]:
    if isinstance(source, (str, Path)):
        with Path(source).open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != CONFIG_FIELDS:
                raise ValueError("Yahoo volatility config has an invalid header")
            configured_rows = [dict(row) for row in reader]
    else:
        configured_rows = [dict(row) for row in source]
        if configured_rows and tuple(configured_rows[0]) != CONFIG_FIELDS:
            raise ValueError("Yahoo volatility config has an invalid header")
    rows = tuple(YahooVolatilitySeries(**row) for row in configured_rows)

    if {row.role for row in rows} != REQUIRED_ROLES or len(rows) != len(
        REQUIRED_ROLES
    ):
        raise ValueError("Yahoo volatility config must define each required role once")
    if any(not value.strip() for row in rows for value in vars(row).values()):
        raise ValueError("Yahoo volatility config fields must not be blank")
    if len({row.ticker for row in rows}) != len(rows):
        raise ValueError("Yahoo volatility config tickers must be unique")
    if len({row.metric_code for row in rows}) != len(rows):
        raise ValueError("Yahoo volatility config metric codes must be unique")
    if any(row.unit != "index_points" for row in rows):
        raise ValueError("Yahoo volatility config units must be index_points")
    return rows


def _close_column(frame: pd.DataFrame, ticker: str, configured_count: int):
    for candidate in ((ticker, "Close"), ("Close", ticker)):
        if candidate in frame.columns:
            return candidate
    if configured_count == 1 and "Close" in frame.columns:
        return "Close"
    return None


def extract_yahoo_close_histories(
    frame: pd.DataFrame,
    series: Iterable[YahooVolatilitySeries],
    as_of_date: date,
) -> dict[str, pd.Series]:
    configured = tuple(series)
    normalized_dates = pd.to_datetime(frame.index, errors="raise").date
    if pd.Index(normalized_dates).duplicated().any():
        raise ValueError("Yahoo volatility history contains duplicate dates")

    histories: dict[str, pd.Series] = {}
    for item in configured:
        column = _close_column(frame, item.ticker, len(configured))
        if column is None:
            continue
        history = pd.Series(
            frame[column].to_numpy(),
            index=pd.Index(normalized_dates),
            dtype="float64",
        )
        history = history.loc[history.index <= as_of_date].dropna().sort_index()
        if history.empty:
            continue
        if not all(math.isfinite(float(value)) for value in history):
            raise ValueError(
                f"Yahoo volatility history contains a non-finite value for {item.ticker}"
            )
        histories[item.role] = history
    if not histories:
        raise ValueError("Yahoo volatility history has no usable configured series")
    return histories


def calculate_yahoo_volatility_metrics(
    histories: Mapping[str, pd.Series],
    series: Iterable[YahooVolatilitySeries],
    as_of_date: date,
    max_lag_days: int = 7,
) -> list[dict[str, Any]]:
    configured = tuple(series)
    role_map = {item.role: item for item in configured}

    def is_fresh(observed: date) -> bool:
        lag = (as_of_date - observed).days
        return 0 <= lag <= max_lag_days

    rows = []
    for item in configured:
        history = histories.get(item.role)
        if history is None or history.empty:
            continue
        observed = max(history.index)
        if not is_fresh(observed):
            continue
        value = float(histories[item.role].loc[observed])
        rows.append(
            {
                "metric_code": item.metric_code,
                "metric_name": item.metric_name,
                "ticker": item.ticker,
                "as_of_date": observed,
                "value": value,
                "unit": item.unit,
                "source_url": yahoo_history_url(item.ticker),
            }
        )

    def common_date(left: str, right: str) -> date | None:
        if left not in histories or right not in histories:
            return None
        matched = set(histories[left].index) & set(histories[right].index)
        if not matched:
            return None
        observed = max(matched)
        return observed if is_fresh(observed) else None

    one_three_date = common_date("vix_1m", "vix_3m")
    if one_three_date is not None:
        vix_1m = float(histories["vix_1m"].loc[one_three_date])
        vix_3m = float(histories["vix_3m"].loc[one_three_date])
        if vix_3m == 0:
            raise ValueError("Yahoo VIX3M denominator must not be zero")
        rows.extend(
            [
                {
                    "metric_code": "vix_1m_3m_spread",
                    "metric_name": "VIX 1M minus 3M spread",
                    "as_of_date": one_three_date,
                    "value": vix_1m - vix_3m,
                    "unit": "index_points",
                    "source_url": yahoo_history_url(role_map["vix_3m"].ticker),
                },
                {
                    "metric_code": "vix_1m_3m_ratio",
                    "metric_name": "VIX 1M to 3M ratio",
                    "as_of_date": one_three_date,
                    "value": vix_1m / vix_3m,
                    "unit": "ratio",
                    "source_url": yahoo_history_url(role_map["vix_3m"].ticker),
                },
            ]
        )

    nine_one_date = common_date("vix_9d", "vix_1m")
    if nine_one_date is not None:
        vix_9d = float(histories["vix_9d"].loc[nine_one_date])
        vix_1m = float(histories["vix_1m"].loc[nine_one_date])
        rows.append(
            {
                "metric_code": "vix_9d_1m_spread",
                "metric_name": "VIX 9D minus 1M spread",
                "as_of_date": nine_one_date,
                "value": vix_9d - vix_1m,
                "unit": "index_points",
                "source_url": yahoo_history_url(role_map["vix_1m"].ticker),
            }
        )
    if not rows:
        raise ValueError(
            "Yahoo volatility history has no fresh observations on or before "
            f"{as_of_date.isoformat()}"
        )
    if any(not math.isfinite(float(row["value"])) for row in rows):
        raise ValueError("Yahoo volatility calculation produced a non-finite value")
    return rows


def serialize_yahoo_close_histories(
    histories: Mapping[str, pd.Series],
    series: Iterable[YahooVolatilitySeries],
) -> str:
    role_map = {item.role: item for item in series}
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("date", "ticker", "close"))
    for role in ("vix_9d", "vix_1m", "vix_3m", "vix_6m", "skew"):
        if role not in histories:
            continue
        ticker = role_map[role].ticker
        for observed, value in histories[role].sort_index().items():
            writer.writerow((observed.isoformat(), ticker, repr(float(value))))
    return output.getvalue()


__all__ = [
    "YahooVolatilitySeries",
    "calculate_yahoo_volatility_metrics",
    "extract_yahoo_close_histories",
    "load_yahoo_volatility_config",
    "serialize_yahoo_close_histories",
    "yahoo_history_url",
]
