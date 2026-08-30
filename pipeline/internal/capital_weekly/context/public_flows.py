from __future__ import annotations

import html
import json
import re
from datetime import date, datetime
from typing import Any


def _number(value: str) -> float:
    return float(value.replace("$", "").replace(",", "").strip())


def _dated_property(text: str, name: str) -> tuple[float, date]:
    pattern = (
        rf'"name"\s*:\s*"{re.escape(name)}"\s*,\s*'
        rf'"value"\s*:\s*"([^"]+)".*?'
        rf'"valueReference"\s*:\s*\{{.*?"value"\s*:\s*"([^"]+)"'
    )
    match = re.search(pattern, text, flags=re.S)
    if match is None:
        raise ValueError(f"iShares page missing {name}")
    return _number(match.group(1)), datetime.strptime(match.group(2), "%b %d, %Y").date()


def parse_ishares_fund_page(text: str, *, ticker: str) -> dict[str, Any]:
    decoded = html.unescape(text)
    nav, nav_date = _dated_property(decoded, "NAV as of")
    net_assets, assets_date = _dated_property(decoded, "Net Assets of Fund")
    shares_match = re.search(
        r'"sharesOutstanding"\s*:\s*\{.*?'
        r'"formattedValue"\s*:\s*"([^"]+)".*?'
        r'"formattedAsOfDate"\s*:\s*"([^"]+)"',
        decoded,
        flags=re.S,
    )
    if shares_match is None:
        raise ValueError("iShares page missing Shares Outstanding")
    shares = _number(shares_match.group(1))
    shares_date = datetime.strptime(shares_match.group(2), "%b %d, %Y").date()
    if len({nav_date, assets_date, shares_date}) != 1:
        raise ValueError("iShares fund facts do not share one as-of date")
    return {
        "date": nav_date,
        "ticker": ticker,
        "nav": nav,
        "net_assets": int(net_assets),
        "shares_outstanding": int(shares),
    }


def calculate_etf_implied_flow(current: dict, previous: dict) -> float:
    if previous["date"] >= current["date"]:
        raise ValueError("ETF implied flow requires a prior issuer observation")
    return float(
        (current["shares_outstanding"] - previous["shares_outstanding"])
        * current["nav"]
    )


def _table_values(entry: dict) -> dict[str, float]:
    trading_tables = [
        item["table"]
        for item in entry.get("content", [])
        if item.get("style") == 1 and isinstance(item.get("table"), dict)
    ]
    if len(trading_tables) != 1:
        raise ValueError(f"HKEX {entry.get('market')} missing trading table")
    table = trading_tables[0]
    labels = table.get("schema", [[]])[0]
    raw_rows = table.get("tr", [])
    if len(labels) != len(raw_rows):
        raise ValueError(f"HKEX {entry.get('market')} schema/value mismatch")
    values = []
    for row in raw_rows:
        try:
            values.append(_number(row["td"][0][0]))
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ValueError(f"HKEX {entry.get('market')} has invalid numeric data") from error
    return dict(zip(labels, values))


def parse_hkex_stock_connect_daily(text: str) -> dict[str, Any]:
    match = re.search(r"tabData\s*=\s*(\[.*\])\s*;?\s*$", text, flags=re.S)
    if match is None:
        raise ValueError("HKEX Stock Connect response missing tabData")
    try:
        entries = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise ValueError("HKEX Stock Connect tabData is invalid JSON") from error
    active = [entry for entry in entries if int(entry.get("tradingDay", 0)) == 1]
    dates = {entry.get("date") for entry in active}
    if len(dates) != 1:
        raise ValueError("HKEX Stock Connect response does not contain one trading date")
    southbound = [entry for entry in active if "Southbound" in entry.get("market", "")]
    northbound = [entry for entry in active if "Northbound" in entry.get("market", "")]
    if len(southbound) != 2 or len(northbound) != 2:
        raise ValueError("HKEX Stock Connect response requires SH and SZ channels")
    south_values = [_table_values(entry) for entry in southbound]
    north_values = [_table_values(entry) for entry in northbound]

    def total(rows: list[dict[str, float]], field: str) -> float:
        if any(field not in row for row in rows):
            raise ValueError(f"HKEX Stock Connect response missing {field}")
        return sum(row[field] for row in rows)

    buy = total(south_values, "Buy Turnover")
    sell = total(south_values, "Sell Turnover")
    return {
        "date": date.fromisoformat(next(iter(dates))),
        "southbound_total_turnover": total(south_values, "Total Turnover"),
        "southbound_buy_turnover": buy,
        "southbound_sell_turnover": sell,
        "southbound_net_buy": buy - sell,
        "southbound_total_trade_count": int(total(south_values, "Total Trade Count")),
        "southbound_etf_turnover": total(south_values, "ETF Turnover"),
        "northbound_total_turnover": total(north_values, "Total Turnover"),
        "northbound_total_trade_count": int(total(north_values, "Total Trade Count")),
        "northbound_etf_turnover": total(north_values, "ETF Turnover"),
    }


__all__ = [
    "calculate_etf_implied_flow",
    "parse_hkex_stock_connect_daily",
    "parse_ishares_fund_page",
]
