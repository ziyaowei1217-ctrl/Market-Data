from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from typing import Iterable

from .events import _table_rows


CFTC_REQUIRED_COLUMNS = {
    "Market_and_Exchange_Names",
    "CFTC_Contract_Market_Code",
    "Open_Interest_All",
    "Asset_Mgr_Positions_Long_All",
    "Asset_Mgr_Positions_Short_All",
    "Lev_Money_Positions_Long_All",
    "Lev_Money_Positions_Short_All",
}


def _number(value: str) -> int:
    return int(str(value).replace(",", "").strip())


def calculate_positioning_percentile(
    history: Iterable[float],
    current: float,
) -> float:
    values = [float(value) for value in history]
    if not values:
        raise ValueError("Positioning percentile requires observed history")
    return sum(value <= current for value in values) / len(values)


def parse_cftc_tff_csv(
    text: str,
    contract_codes: dict[str, str],
) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    missing = CFTC_REQUIRED_COLUMNS - set(reader.fieldnames or [])
    date_columns = {
        "Report_Date_as_MM_DD_YYYY",
        "Report_Date_as_YYYY-MM-DD",
    }
    if not date_columns.intersection(reader.fieldnames or []):
        missing.add("report date")
    if missing:
        raise ValueError(f"CFTC response missing columns: {', '.join(sorted(missing))}")
    rows = []
    for raw in reader:
        code = raw["CFTC_Contract_Market_Code"].strip().strip('"')
        if contract_codes and code not in contract_codes:
            continue
        if raw.get("Report_Date_as_YYYY-MM-DD"):
            report_date = datetime.strptime(
                raw["Report_Date_as_YYYY-MM-DD"], "%Y-%m-%d"
            ).date()
        else:
            report_date = datetime.strptime(
                raw["Report_Date_as_MM_DD_YYYY"], "%m/%d/%Y"
            ).date()
        asset_net = _number(raw["Asset_Mgr_Positions_Long_All"]) - _number(
            raw["Asset_Mgr_Positions_Short_All"]
        )
        leverage_net = _number(raw["Lev_Money_Positions_Long_All"]) - _number(
            raw["Lev_Money_Positions_Short_All"]
        )
        rows.append(
            {
                "contract_code": code,
                "metric_code": contract_codes.get(code, code),
                "market_name": raw["Market_and_Exchange_Names"].strip(),
                "report_date": report_date,
                "expected_release_date": report_date + timedelta(days=3),
                "release_lag_days": 3,
                "open_interest": _number(raw["Open_Interest_All"]),
                "asset_manager_net": asset_net,
                "leveraged_fund_net": leverage_net,
            }
        )
    rows.sort(key=lambda row: (row["metric_code"], row["report_date"]))
    previous_by_code: dict[str, dict] = {}
    histories: dict[str, list[float]] = {}
    for row in rows:
        code = row["metric_code"]
        previous = previous_by_code.get(code)
        row["asset_manager_net_change"] = (
            row["asset_manager_net"] - previous["asset_manager_net"]
            if previous
            else None
        )
        row["leveraged_fund_net_change"] = (
            row["leveraged_fund_net"] - previous["leveraged_fund_net"]
            if previous
            else None
        )
        asset_history = histories.setdefault(code, [])
        asset_history.append(row["asset_manager_net"])
        row["asset_manager_percentile"] = calculate_positioning_percentile(
            asset_history, row["asset_manager_net"]
        )
        previous_by_code[code] = row
    if not rows:
        raise ValueError("CFTC response contained no configured contracts")
    return rows


def parse_finra_margin_table(text: str) -> list[dict]:
    table = _table_rows(text)
    header_index = next(
        (
            index
            for index, cells in enumerate(table)
            if cells and cells[0].strip().lower() == "month/year"
        ),
        None,
    )
    if header_index is None:
        raise ValueError("FINRA page missing margin statistics header")
    rows = []
    for cells in table[header_index + 1 :]:
        if len(cells) < 4:
            continue
        try:
            observation_date = datetime.strptime(cells[0], "%b-%y").date().replace(day=1)
            debit = _number(cells[1])
            cash_credit = _number(cells[2])
            margin_credit = _number(cells[3])
        except (ValueError, TypeError):
            continue
        rows.append(
            {
                "date": observation_date,
                "margin_debit_millions": debit,
                "cash_free_credit_millions": cash_credit,
                "margin_free_credit_millions": margin_credit,
                "free_credit_total_millions": cash_credit + margin_credit,
            }
        )
    if not rows:
        raise ValueError("FINRA page contained no monthly margin observations")
    return sorted(rows, key=lambda row: row["date"])
