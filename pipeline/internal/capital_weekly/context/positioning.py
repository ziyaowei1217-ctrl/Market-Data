from __future__ import annotations

import csv
import io
from datetime import date, datetime, time, timedelta
from typing import Iterable, Mapping
from zoneinfo import ZoneInfo

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
CFTC_NEW_YORK = ZoneInfo("America/New_York")
CFTC_DISAGGREGATED_COLUMN_ALIASES = {
    "market_name": (
        "Market_and_Exchange_Names",
        "market_and_exchange_names",
    ),
    "contract_code": (
        "CFTC_Contract_Market_Code",
        "cftc_contract_market_code",
    ),
    "report_date": (
        "Report_Date_as_YYYY-MM-DD",
        "Report_Date_as_YYYY_MM_DD",
        "report_date_as_yyyy_mm_dd",
    ),
    "open_interest": (
        "Open_Interest_All",
        "open_interest_all",
    ),
    "producer_long": (
        "Prod_Merc_Positions_Long_All",
        "prod_merc_positions_long",
    ),
    "producer_short": (
        "Prod_Merc_Positions_Short_All",
        "prod_merc_positions_short",
    ),
    "swap_dealer_long": (
        "Swap_Positions_Long_All",
        "swap_positions_long_all",
    ),
    "swap_dealer_short": (
        "Swap_Positions_Short_All",
        "Swap__Positions_Short_All",
        "swap_positions_short_all",
        "swap__positions_short_all",
    ),
    "managed_money_long": (
        "M_Money_Positions_Long_All",
        "m_money_positions_long_all",
    ),
    "managed_money_short": (
        "M_Money_Positions_Short_All",
        "m_money_positions_short_all",
    ),
    "other_reportable_long": (
        "Other_Rept_Positions_Long_All",
        "other_rept_positions_long",
    ),
    "other_reportable_short": (
        "Other_Rept_Positions_Short_All",
        "other_rept_positions_short",
    ),
}
DISAGGREGATED_PARTICIPANTS = (
    "producer",
    "swap_dealer",
    "managed_money",
    "other_reportable",
)

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


def cftc_known_as_of(report_date: date) -> str:
    released = datetime.combine(
        report_date + timedelta(days=3),
        time(15, 30),
        tzinfo=CFTC_NEW_YORK,
    )
    return released.isoformat()


def _disaggregated_columns(fieldnames: Iterable[str]) -> dict[str, str]:
    available = set(fieldnames)
    resolved = {}
    missing = []
    for semantic_name, aliases in CFTC_DISAGGREGATED_COLUMN_ALIASES.items():
        matches = [alias for alias in aliases if alias in available]
        if not matches:
            missing.append(semantic_name)
        elif len(matches) > 1:
            raise ValueError(
                "CFTC response contains ambiguous columns for "
                f"{semantic_name}: {', '.join(matches)}"
            )
        else:
            resolved[semantic_name] = matches[0]
    if missing:
        raise ValueError(f"CFTC response missing columns: {', '.join(sorted(missing))}")
    return resolved


def _disaggregated_contracts(
    contracts: Iterable[Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    configured = {}
    required = {
        "contract_code",
        "commodity_code",
        "commodity_family",
        "market_name",
        "percentile_window",
        "percentile_min_observations",
    }
    for raw in contracts:
        missing = sorted(
            key
            for key in required
            if raw.get(key) is None or not str(raw.get(key, "")).strip()
        )
        if missing:
            raise ValueError(
                "CFTC contract configuration missing fields: " + ", ".join(missing)
            )
        spec = dict(raw)
        code = str(spec["contract_code"]).strip()
        if code in configured:
            raise ValueError(f"Duplicate CFTC contract code: {code}")
        window = int(str(spec["percentile_window"]).strip())
        minimum = int(str(spec["percentile_min_observations"]).strip())
        if window <= 0 or minimum <= 0 or minimum > window:
            raise ValueError(
                f"Invalid CFTC percentile configuration for contract {code}"
            )
        spec["contract_code"] = code
        spec["commodity_code"] = str(spec["commodity_code"]).strip()
        spec["commodity_family"] = str(spec["commodity_family"]).strip()
        spec["market_name"] = str(spec["market_name"]).strip()
        spec["percentile_window"] = window
        spec["percentile_min_observations"] = minimum
        configured[code] = spec
    return configured


def parse_cftc_disaggregated_csv(
    text: str,
    contracts: Iterable[Mapping[str, object]] | Mapping[str, str],
) -> list[dict]:
    if isinstance(contracts, Mapping):
        return _parse_legacy_cftc_disaggregated_csv(text, contracts)
    configured = _disaggregated_contracts(contracts)
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    columns = _disaggregated_columns(reader.fieldnames or [])
    rows = []
    seen_codes = set()
    for raw in reader:
        code = str(raw[columns["contract_code"]]).strip().strip('"')
        spec = configured.get(code)
        if spec is None:
            continue
        market_name = str(raw[columns["market_name"]]).strip()
        if market_name != spec["market_name"]:
            raise ValueError(
                f"CFTC market name mismatch for contract {code}: "
                f"expected {spec['market_name']!r}, received {market_name!r}"
            )
        report_date = date.fromisoformat(
            str(raw[columns["report_date"]]).strip()[:10]
        )
        observation = {
            "contract_code": code,
            "commodity_code": spec["commodity_code"],
            "commodity_family": spec["commodity_family"],
            "market_name": market_name,
            "report_date": report_date,
            "known_as_of": cftc_known_as_of(report_date),
            "open_interest": _number(raw[columns["open_interest"]]),
            "percentile_window": spec["percentile_window"],
            "percentile_min_observations": spec[
                "percentile_min_observations"
            ],
        }
        for participant in DISAGGREGATED_PARTICIPANTS:
            observation[f"{participant}_net"] = _number(
                raw[columns[f"{participant}_long"]]
            ) - _number(raw[columns[f"{participant}_short"]])
        rows.append(observation)
        seen_codes.add(code)
    if not rows:
        raise ValueError("CFTC response contained no configured contracts")
    missing_codes = sorted(set(configured) - seen_codes)
    if missing_codes:
        raise ValueError(
            "CFTC response missing configured contracts: " + ", ".join(missing_codes)
        )
    rows.sort(key=lambda row: (row["contract_code"], row["report_date"]))
    previous_by_code: dict[str, dict] = {}
    histories: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        code = str(row["contract_code"])
        previous = previous_by_code.get(code)
        participant_histories = histories.setdefault(code, {})
        for participant in DISAGGREGATED_PARTICIPANTS:
            net_key = f"{participant}_net"
            row[f"{net_key}_change"] = (
                row[net_key] - previous[net_key] if previous is not None else None
            )
            history = participant_histories.setdefault(participant, [])
            history.append(row[net_key])
            windowed = history[-int(row["percentile_window"]) :]
            row[f"{participant}_percentile"] = (
                calculate_positioning_percentile(windowed, row[net_key])
                if len(windowed) >= int(row["percentile_min_observations"])
                else None
            )
        previous_by_code[code] = row
    return rows


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


def _parse_legacy_cftc_disaggregated_csv(
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
