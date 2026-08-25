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
TERM_ROLES = ("vix_9d", "vix_1m", "vix_3m", "vix_6m")
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
    raise ValueError(f"Yahoo volatility history is missing Close for {ticker}")


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
        history = pd.Series(
            frame[column].to_numpy(),
            index=pd.Index(normalized_dates),
            dtype="float64",
        )
        history = history.loc[history.index <= as_of_date].dropna().sort_index()
        if history.empty:
            raise ValueError(f"Yahoo volatility history is empty for {item.ticker}")
        if not all(math.isfinite(float(value)) for value in history):
            raise ValueError(
                f"Yahoo volatility history contains a non-finite value for {item.ticker}"
            )
        histories[item.role] = history
    return histories


def calculate_yahoo_volatility_metrics(
    histories: Mapping[str, pd.Series],
    series: Iterable[YahooVolatilitySeries],
    as_of_date: date,
    max_lag_days: int = 7,
) -> list[dict[str, Any]]:
    configured = tuple(series)
    role_map = {item.role: item for item in configured}
    common_dates = set(histories[TERM_ROLES[0]].index)
    for role in TERM_ROLES[1:]:
        common_dates &= set(histories[role].index)
    if not common_dates:
        raise ValueError("Yahoo volatility term indices have no common date")
    term_date = max(common_dates)
    skew_date = max(histories["skew"].index)
    for label, observed in (("term structure", term_date), ("SKEW", skew_date)):
        lag = (as_of_date - observed).days
        if lag < 0 or lag > max_lag_days:
            raise ValueError(
                f"Yahoo {label} date {observed.isoformat()} has lag {lag} days "
                f"versus target Sunday {as_of_date.isoformat()}; allowed range "
                f"is 0..{max_lag_days} days"
            )

    observed_dates = {role: term_date for role in TERM_ROLES}
    observed_dates["skew"] = skew_date
    rows = []
    for item in configured:
        observed = observed_dates[item.role]
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

    vix_9d = float(histories["vix_9d"].loc[term_date])
    vix_1m = float(histories["vix_1m"].loc[term_date])
    vix_3m = float(histories["vix_3m"].loc[term_date])
    if vix_3m == 0:
        raise ValueError("Yahoo VIX3M denominator must not be zero")
    rows.extend(
        [
            {
                "metric_code": "vix_1m_3m_spread",
                "metric_name": "VIX 1M minus 3M spread",
                "as_of_date": term_date,
                "value": vix_1m - vix_3m,
                "unit": "index_points",
                "source_url": yahoo_history_url(role_map["vix_3m"].ticker),
            },
            {
                "metric_code": "vix_1m_3m_ratio",
                "metric_name": "VIX 1M to 3M ratio",
                "as_of_date": term_date,
                "value": vix_1m / vix_3m,
                "unit": "ratio",
                "source_url": yahoo_history_url(role_map["vix_3m"].ticker),
            },
            {
                "metric_code": "vix_9d_1m_spread",
                "metric_name": "VIX 9D minus 1M spread",
                "as_of_date": term_date,
                "value": vix_9d - vix_1m,
                "unit": "index_points",
                "source_url": yahoo_history_url(role_map["vix_1m"].ticker),
            },
        ]
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
