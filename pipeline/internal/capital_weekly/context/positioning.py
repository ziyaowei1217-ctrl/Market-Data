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

CFTC_DISAGGREGATED_REQUIRED_COLUMNS = {
    "Market_and_Exchange_Names",
    "CFTC_Contract_Market_Code",
    "Open_Interest_All",
    "M_Money_Positions_Long_All",
    "M_Money_Positions_Short_All",
    "Swap_Positions_Long_All",
    "Swap__Positions_Short_All",
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
        rows.append(
            {
                "contract_code": code,
                "metric_code": contract_codes.get(code, code),
                "market_name": raw["Market_and_Exchange_Names"].strip(),
                "report_date": report_date,
                "expected_release_date": report_date + timedelta(days=3),
                "release_lag_days": 3,
                "open_interest": _number(raw["Open_Interest_All"]),
                "asset_manager_net": _number(
                    raw["Asset_Mgr_Positions_Long_All"]
                )
                - _number(raw["Asset_Mgr_Positions_Short_All"]),
                "leveraged_fund_net": _number(
                    raw["Lev_Money_Positions_Long_All"]
                )
                - _number(raw["Lev_Money_Positions_Short_All"]),
            }
        )
    return _decorate_positioning_history(
        rows,
        participants=("asset_manager", "leveraged_fund"),
    )


def parse_cftc_disaggregated_csv(
    text: str,
    contract_codes: dict[str, str],
) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    missing = CFTC_DISAGGREGATED_REQUIRED_COLUMNS - set(reader.fieldnames or [])
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
        report_date = _report_date(raw)
        rows.append(
            {
                "contract_code": code,
                "metric_code": contract_codes.get(code, code),
                "market_name": raw["Market_and_Exchange_Names"].strip(),
                "report_date": report_date,
                "expected_release_date": report_date + timedelta(days=3),
                "release_lag_days": 3,
                "open_interest": _number(raw["Open_Interest_All"]),
                "managed_money_net": _number(
                    raw["M_Money_Positions_Long_All"]
                )
                - _number(raw["M_Money_Positions_Short_All"]),
                "swap_dealer_net": _number(raw["Swap_Positions_Long_All"])
                - _number(raw["Swap__Positions_Short_All"]),
            }
        )
    return _decorate_positioning_history(
        rows,
        participants=("managed_money", "swap_dealer"),
    )


def _report_date(raw: dict[str, str]) -> date:
    if raw.get("Report_Date_as_YYYY-MM-DD"):
        return datetime.strptime(raw["Report_Date_as_YYYY-MM-DD"], "%Y-%m-%d").date()
    return datetime.strptime(raw["Report_Date_as_MM_DD_YYYY"], "%m/%d/%Y").date()


def _decorate_positioning_history(
    rows: list[dict],
    *,
    participants: tuple[str, ...],
) -> list[dict]:
    rows.sort(key=lambda row: (row["metric_code"], row["report_date"]))
    previous_by_code: dict[str, dict] = {}
    histories: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        code = row["metric_code"]
        previous = previous_by_code.get(code)
        for participant in participants:
            net_key = f"{participant}_net"
            row[f"{participant}_net_change"] = (
                row[net_key] - previous[net_key] if previous else None
            )
            history = histories.setdefault((code, participant), [])
            history.append(row[net_key])
            row[f"{participant}_percentile"] = calculate_positioning_percentile(
                history,
                row[net_key],
            )
        previous_by_code[code] = row
    if not rows:
        raise ValueError("CFTC response contained no configured contracts")
    return rows


def select_released_cftc_rows(
    rows: Iterable[dict],
    *,
    start: date,
    end: date,
) -> list[dict]:
    return [
        dict(row)
        for row in rows
        if start <= row["expected_release_date"] <= end
    ]


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
