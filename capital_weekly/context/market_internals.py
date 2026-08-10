from __future__ import annotations

import math
import re
from datetime import datetime

import pandas as pd


def _require_columns(frame: pd.DataFrame, columns: set[str]) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"Market data missing columns: {', '.join(sorted(missing))}")


def calculate_liquidity_metrics(
    history: pd.DataFrame,
    window: int = 20,
) -> dict[str, float | None]:
    _require_columns(history, {"date", "close", "volume", "turnover_value"})
    frame = history.copy().sort_values("date").tail(window)
    for column in ("close", "volume", "turnover_value"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["close", "turnover_value"])
    if len(frame) < 2:
        raise ValueError("At least two market observations are required")

    returns = frame["close"].pct_change().dropna()
    realized = (
        float(returns.std(ddof=1) * math.sqrt(252))
        if len(returns) >= 2
        else None
    )
    peak = float(frame["close"].max())
    drawdown = float(frame["close"].iloc[-1] / peak - 1) if peak > 0 else None
    turnover_mean = float(frame["turnover_value"].mean())
    relative_turnover = (
        float(frame["turnover_value"].iloc[-1] / turnover_mean)
        if turnover_mean > 0
        else None
    )
    aligned_turnover = frame["turnover_value"].iloc[1:].reset_index(drop=True)
    aligned_returns = returns.abs().reset_index(drop=True)
    valid = aligned_turnover > 0
    amihud = (
        float((aligned_returns[valid] / aligned_turnover[valid]).mean())
        if valid.any()
        else None
    )
    volume_changes = frame["volume"].pct_change()
    aligned_volume_changes = volume_changes.loc[returns.index]
    price_volume = (
        returns.corr(aligned_volume_changes)
        if returns.std(ddof=0) > 0 and aligned_volume_changes.std(ddof=0) > 0
        else None
    )
    return {
        "realized_volatility": realized,
        "drawdown": drawdown,
        "relative_turnover": relative_turnover,
        "amihud": amihud,
        "price_volume_correlation": (
            float(price_volume) if price_volume is not None and pd.notna(price_volume) else None
        ),
    }


def calculate_breadth(
    constituent_history: pd.DataFrame,
    moving_average_windows: tuple[int, ...] = (20, 50, 200),
) -> dict[str, float | int | None]:
    _require_columns(constituent_history, {"symbol", "date", "close"})
    frame = constituent_history.copy().sort_values(["symbol", "date"])
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["symbol", "date", "close"])
    if frame.empty:
        raise ValueError("Constituent history is empty")

    grouped = frame.groupby("symbol", sort=False)
    latest = grouped.tail(1).set_index("symbol")
    previous = grouped.tail(2).groupby("symbol", sort=False).head(1).set_index("symbol")
    joined = latest[["close"]].join(
        previous[["close"]], how="inner", lsuffix="_latest", rsuffix="_previous"
    )
    returns = joined["close_latest"] / joined["close_previous"] - 1
    advancers = int((returns > 0).sum())
    decliners = int((returns < 0).sum())
    unchanged = int((returns == 0).sum())
    moving = advancers + decliners
    metrics: dict[str, float | int | None] = {
        "advancers": advancers,
        "decliners": decliners,
        "unchanged": unchanged,
        "advance_ratio": advancers / moving if moving else None,
        "advance_decline_ratio": advancers / decliners if decliners else None,
        "net_advances": advancers - decliners,
        "median_return": float(returns.median()) if not returns.empty else None,
    }

    for window in moving_average_windows:
        averages = grouped["close"].rolling(window, min_periods=window).mean()
        current_average = averages.groupby(level=0).tail(1)
        average_by_symbol = current_average.droplevel(1)
        comparison = latest["close"].reindex(average_by_symbol.index) > average_by_symbol
        metrics[f"pct_above_{window}d_ma"] = (
            float(comparison.mean()) if len(comparison) else None
        )

    prior_extremes = grouped["close"].agg(
        prior_high=lambda values: values.iloc[:-1].max(),
        prior_low=lambda values: values.iloc[:-1].min(),
    )
    current = latest["close"].reindex(prior_extremes.index)
    metrics["new_highs"] = int((current > prior_extremes["prior_high"]).sum())
    metrics["new_lows"] = int((current < prior_extremes["prior_low"]).sum())
    return metrics


def calculate_style_relative_return(
    style: pd.Series,
    benchmark: pd.Series,
) -> float:
    if len(style) < 2 or len(benchmark) < 2:
        raise ValueError("Style and benchmark series require at least two values")
    style_return = float(style.iloc[-1] / style.iloc[0] - 1)
    benchmark_return = float(benchmark.iloc[-1] / benchmark.iloc[0] - 1)
    return style_return - benchmark_return


def _plain_text(fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment)).strip()


def _integer(text: str) -> int:
    match = re.search(r"\$?([\d,]+)", text)
    if not match:
        raise ValueError(f"Nasdaq summary value was not numeric: {text}")
    return int(match.group(1).replace(",", ""))


def parse_nasdaq_market_summary(text: str) -> list[dict]:
    sections = re.findall(
        r"<h2[^>]*>\s*For\s+([^<]+)</h2>(.*?)(?=<h2|\Z)",
        text,
        flags=re.I | re.S,
    )
    rows = []
    for date_text, body in sections:
        observation_date = datetime.strptime(
            _plain_text(date_text), "%b %d, %Y"
        ).date()
        table_rows = {
            _plain_text(label).rstrip(":"): [_plain_text(cell) for cell in cells]
            for label, cells in re.findall(
                r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>((?:\s*<td[^>]*>.*?</td>)+)\s*</tr>",
                body,
                flags=re.I | re.S,
            )
            for cells in [
                re.findall(r"<td[^>]*>(.*?)</td>", cells, flags=re.I | re.S)
            ]
        }
        required = {
            "Total Volume",
            "Block Volume",
            "Number of Issues",
            "Total Trades",
            "Block Trades",
        }
        if not required.issubset(table_rows):
            raise ValueError("Nasdaq summary did not contain required market fields")
        total_cells = table_rows["Total Volume"]
        share_volume = _integer(total_cells[0])
        block_volume = _integer(table_rows["Block Volume"][0])
        rows.append(
            {
                "date": observation_date,
                "share_volume": share_volume,
                "dollar_volume": _integer(total_cells[1]),
                "block_volume": block_volume,
                "issue_count": _integer(table_rows["Number of Issues"][0]),
                "trade_count": _integer(table_rows["Total Trades"][0]),
                "block_trade_count": _integer(table_rows["Block Trades"][0]),
                "block_volume_ratio": block_volume / share_volume,
            }
        )
    if not rows:
        raise ValueError("Nasdaq summary did not contain dated market sections")
    return sorted(rows, key=lambda row: row["date"])
