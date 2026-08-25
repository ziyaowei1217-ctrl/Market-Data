from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any


def _number(value: Any) -> float:
    cleaned = re.sub(r"[^\d.+-]", "", str(value))
    if not cleaned:
        raise ValueError(f"Missing numeric value: {value!r}")
    number = float(cleaned)
    return int(number) if number.is_integer() else number


def _label_number(text: str, labels: list[str]) -> float:
    for label in labels:
        match = re.search(
            rf"{label}\s*:\s*(?:(?:HK\$|HKD)\s*)?([\d,.]+)",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return _number(match.group(1))
    raise ValueError(f"Missing market field: {labels[0]}")


def _parse_date(value: Any) -> date:
    raw = str(value).strip()
    for pattern in ("%d/%m/%Y", "%Y-%m-%d", "%Y%m%d", "%d %b %Y"):
        try:
            return datetime.strptime(raw, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported market date: {raw!r}")


def _breadth(result: dict[str, Any]) -> dict[str, Any]:
    directional = result["advancers"] + result["decliners"]
    result["advance_ratio"] = (
        result["advancers"] / directional if directional else None
    )
    result["advance_decline"] = result["advancers"] - result["decliners"]
    return result


def parse_hkex_market_highlights(text: str) -> dict[str, Any]:
    date_match = re.search(
        r"(?:Trading\s+Date|Date)\s*:\s*"
        r"(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Z]{3}\s+\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if not date_match:
        raise ValueError("Missing HKEX trading date")
    return _breadth(
        {
            "as_of_date": _parse_date(date_match.group(1)),
            "market": "HKEX",
            "volume": _label_number(
                text,
                ["Shares Traded", "Share Volume", r"\(Shares\)"],
            ),
            "turnover": _label_number(
                text,
                [
                    r"Today's Turnover:\s*\(HK\$\)",
                    r"Turnover\s*\(HK\$\)",
                    r"\(HK\$\)",
                    "Turnover",
                ],
            ),
            "trades": _label_number(text, ["Number of Trades", r"\(Deals\)", "Deals"]),
            "advancers": _label_number(text, ["Advanced", "Advancers"]),
            "decliners": _label_number(text, ["Declined", "Decliners"]),
            "unchanged": _label_number(text, ["Unchanged"]),
        }
    )


def parse_hkex_short_selling(text: str) -> dict[str, Any]:
    date_match = re.search(
        r"Date\s*:\s*"
        r"(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Z]{3}\s+\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if not date_match:
        raise ValueError("Missing HKEX short-selling date")
    short_turnover = _label_number(
        text,
        [
            "Total Short Selling Turnover",
            r"Short Selling Turnover Total Value \(\$\)",
        ],
    )
    market_turnover = _label_number(text, ["Total Market Turnover"])
    return {
        "as_of_date": _parse_date(date_match.group(1)),
        "market": "HKEX",
        "short_turnover": short_turnover,
        "market_turnover": market_turnover,
        "short_turnover_ratio": (
            short_turnover / market_turnover if market_turnover else None
        ),
    }


def _json_payload(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped.startswith("{"):
        match = re.match(r"^[^(]+\((.*)\)\s*;?\s*$", stripped, flags=re.S)
        if not match:
            raise ValueError("Exchange response is neither JSON nor JSONP")
        stripped = match.group(1)
    return json.loads(stripped)


def _first_record(text: str) -> dict[str, Any]:
    payload = _json_payload(text)
    for key in ("result", "data"):
        records = payload.get(key)
        if isinstance(records, list) and records:
            return records[0]
    raise ValueError("Exchange response has no daily overview record")


def _pick(record: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in record and record[name] not in (None, ""):
            return record[name]
    raise ValueError(f"Exchange daily overview missing {names[0]}")


def _parse_exchange_overview(
    text: str,
    *,
    market: str,
    fields: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    record = _first_record(text)
    result = {"market": market}
    result["as_of_date"] = _parse_date(_pick(record, fields["as_of_date"]))
    for target in (
        "turnover",
        "volume",
        "advancers",
        "decliners",
        "unchanged",
        "limit_up",
        "limit_down",
    ):
        result[target] = _number(_pick(record, fields[target]))
    return _breadth(result)


def parse_sse_daily_overview(text: str) -> dict[str, Any]:
    payload = _json_payload(text)
    records = payload.get("result")
    if (
        isinstance(records, list)
        and records
        and "PRODUCT_CODE" in records[0]
    ):
        record = next(
            (row for row in records if str(row.get("PRODUCT_CODE")) == "17"),
            None,
        )
        if record is None:
            raise ValueError("SSE response missing aggregate stock row")
        return {
            "as_of_date": _parse_date(record["TRADE_DATE"]),
            "market": "SSE",
            "turnover": int(round(float(record["TRADE_AMT"]) * 100_000_000)),
            "volume": int(round(float(record["TRADE_VOL"]) * 100_000_000)),
            "turnover_rate": float(record["TOTAL_TO_RATE"]) / 100,
            "listed_count": int(record["LIST_NUM"]),
        }
    return _parse_exchange_overview(
        text,
        market="SSE",
        fields={
            "as_of_date": ("tradeDate", "date"),
            "turnover": ("turnover", "amount"),
            "volume": ("volume",),
            "advancers": ("up", "riseCount"),
            "decliners": ("down", "fallCount"),
            "unchanged": ("flat", "unchangedCount"),
            "limit_up": ("limitUp", "limitUpCount"),
            "limit_down": ("limitDown", "limitDownCount"),
        },
    )


def parse_szse_daily_overview(text: str) -> dict[str, Any]:
    payload = json.loads(text)
    if isinstance(payload, list):
        section = next(
            (
                item
                for item in payload
                if item.get("metadata", {}).get("tabkey") == "tab1"
                and item.get("data")
            ),
            None,
        )
        if section is None:
            raise ValueError("SZSE response missing Shenzhen market section")
        values = {
            str(row.get("zbmc", "")).strip(): str(row.get("brsz", "")).strip()
            for row in section["data"]
        }
        required = (
            "上市公司数",
            "上市证券数",
            "股票成交金额（亿元）",
            "股票平均换手率",
        )
        missing = [label for label in required if label not in values]
        if missing:
            raise ValueError(f"SZSE response missing indicators: {', '.join(missing)}")
        return {
            "as_of_date": _parse_date(section["metadata"]["subname"]),
            "market": "SZSE",
            "turnover": int(
                round(_number(values["股票成交金额（亿元）"]) * 100_000_000)
            ),
            "turnover_rate": _number(values["股票平均换手率"]) / 100,
            "listed_companies": _number(values["上市公司数"]),
            "listed_securities": _number(values["上市证券数"]),
        }
    return _parse_exchange_overview(
        text,
        market="SZSE",
        fields={
            "as_of_date": ("date", "tradeDate"),
            "turnover": ("amount", "turnover"),
            "volume": ("volume",),
            "advancers": ("riseCount", "up"),
            "decliners": ("fallCount", "down"),
            "unchanged": ("unchangedCount", "flat"),
            "limit_up": ("limitUpCount", "limitUp"),
            "limit_down": ("limitDownCount", "limitDown"),
        },
    )


def ensure_fresh_market_date(
    as_of_date: date,
    *,
    expected_end: date,
    max_lag_days: int = 3,
) -> None:
    lag = (expected_end - as_of_date).days
    if lag > max_lag_days:
        raise ValueError(
            f"Market observation is stale by {lag} days; maximum is {max_lag_days}"
        )
    if lag < 0:
        raise ValueError("Market observation falls after the expected period")


__all__ = [
    "ensure_fresh_market_date",
    "parse_hkex_market_highlights",
    "parse_hkex_short_selling",
    "parse_sse_daily_overview",
    "parse_szse_daily_overview",
]
