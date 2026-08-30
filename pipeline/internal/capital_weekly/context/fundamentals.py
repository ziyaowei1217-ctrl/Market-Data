from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo


HONG_KONG = ZoneInfo("Asia/Hong_Kong")
EASTERN = ZoneInfo("America/New_York")
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
YAHOO_FINANCE_URL = "https://finance.yahoo.com/quote/{ticker}/history/"
FORMULA_VERSION = "fundamentals-v1"
MIN_PERCENTILE_HISTORY = 4

COMPANY_FUNDAMENTAL_FIELDS = (
    "record_id",
    "ticker",
    "cik",
    "company_name",
    "metric_code",
    "metric_name",
    "observation_date",
    "period_start",
    "period_end",
    "filing_date",
    "known_as_of",
    "accession_number",
    "value",
    "unit",
    "frequency",
    "source",
    "source_url",
    "source_tier",
    "proxy_type",
    "calculation_id",
    "formula_version",
    "input_record_ids",
    "guidance_direction",
    "qc_flag",
    "notes",
)

CONCEPTS = {
    "RevenueFromContractWithCustomerExcludingAssessedTax": (
        "revenue",
        "Revenue",
        ("USD",),
        "duration",
    ),
    "Revenues": ("revenue", "Revenue", ("USD",), "duration"),
    "SalesRevenueNet": ("revenue", "Revenue", ("USD",), "duration"),
    "GrossProfit": ("gross_profit", "Gross profit", ("USD",), "duration"),
    "OperatingIncomeLoss": (
        "operating_income",
        "Operating income",
        ("USD",),
        "duration",
    ),
    "NetIncomeLoss": ("net_income", "Net income", ("USD",), "duration"),
    "ProfitLoss": ("net_income", "Net income", ("USD",), "duration"),
    "NetCashProvidedByUsedInOperatingActivities": (
        "operating_cash_flow",
        "Operating cash flow",
        ("USD",),
        "duration",
    ),
    "PaymentsToAcquirePropertyPlantAndEquipment": (
        "capital_expenditure",
        "Capital expenditure",
        ("USD",),
        "duration",
    ),
    "DepreciationDepletionAndAmortization": (
        "depreciation_and_amortization",
        "Depreciation and amortization",
        ("USD",),
        "duration",
    ),
    "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment": (
        "depreciation_and_amortization",
        "Depreciation and amortization",
        ("USD",),
        "duration",
    ),
    "EarningsPerShareDiluted": (
        "diluted_eps",
        "Diluted EPS",
        ("USD/shares", "USD / shares"),
        "duration",
    ),
    "EntityCommonStockSharesOutstanding": (
        "shares_outstanding",
        "Shares outstanding",
        ("shares",),
        "instant",
    ),
    "CommonStocksIncludingAdditionalPaidInCapital": (
        "stockholders_equity",
        "Stockholders' equity",
        ("USD",),
        "instant",
    ),
    "StockholdersEquity": (
        "stockholders_equity",
        "Stockholders' equity",
        ("USD",),
        "instant",
    ),
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": (
        "stockholders_equity",
        "Stockholders' equity",
        ("USD",),
        "instant",
    ),
    "CashAndCashEquivalentsAtCarryingValue": (
        "cash_and_equivalents",
        "Cash and equivalents",
        ("USD",),
        "instant",
    ),
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents": (
        "cash_and_equivalents",
        "Cash and equivalents",
        ("USD",),
        "instant",
    ),
    "LongTermDebtCurrent": (
        "debt_current",
        "Current debt",
        ("USD",),
        "instant",
    ),
    "LongTermDebtNoncurrent": (
        "debt_noncurrent",
        "Noncurrent debt",
        ("USD",),
        "instant",
    ),
    "LongTermDebtAndFinanceLeaseObligationsCurrent": (
        "debt_current",
        "Current debt",
        ("USD",),
        "instant",
    ),
    "LongTermDebtAndFinanceLeaseObligationsNoncurrent": (
        "debt_noncurrent",
        "Noncurrent debt",
        ("USD",),
        "instant",
    ),
}

METRIC_NAMES = {
    "revenue_ttm": "Revenue (TTM)",
    "gross_profit_ttm": "Gross profit (TTM)",
    "operating_income_ttm": "Operating income (TTM)",
    "net_income_ttm": "Net income (TTM)",
    "operating_cash_flow_ttm": "Operating cash flow (TTM)",
    "capital_expenditure_ttm": "Capital expenditure (TTM)",
    "depreciation_and_amortization_ttm": "Depreciation and amortization (TTM)",
    "diluted_eps_ttm": "Diluted EPS (TTM)",
    "free_cash_flow_ttm": "Free cash flow (TTM)",
    "gross_margin_ttm": "Gross margin (TTM)",
    "operating_margin_ttm": "Operating margin (TTM)",
    "net_margin_ttm": "Net margin (TTM)",
    "total_debt": "Total debt",
    "share_price": "Share price",
    "trailing_pe": "Trailing P/E",
    "price_to_book": "Price to book",
    "price_to_sales": "Price to sales",
    "ev_to_ebitda": "EV / EBITDA",
    "trailing_pe_percentile": "Trailing P/E historical percentile",
    "price_to_book_percentile": "P/B historical percentile",
    "price_to_sales_percentile": "P/S historical percentile",
    "ev_to_ebitda_percentile": "EV/EBITDA historical percentile",
}


def _record_id(*parts: Any) -> str:
    payload = "|".join("" if value is None else str(value) for value in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _known_at(filed: str) -> str:
    return datetime.combine(
        date.fromisoformat(filed), time(23, 59, 59), tzinfo=EASTERN
    ).isoformat()


def _price_known_at(observation: str) -> str:
    return datetime.combine(
        date.fromisoformat(observation), time(16), tzinfo=EASTERN
    ).isoformat()


def _cutoff(as_of_date: date) -> datetime:
    return datetime.combine(as_of_date, time.max, tzinfo=HONG_KONG)


def _empty_row(**values: Any) -> dict[str, Any]:
    row = {field: "" for field in COMPANY_FUNDAMENTAL_FIELDS}
    row.update(values)
    return row


def make_company_fundamental_row(
    *,
    ticker: str,
    cik: str,
    company_name: str,
    metric_code: str,
    observation_date: str,
    known_as_of: str,
    value: float | int | None,
    unit: str,
    frequency: str,
    source: str,
    source_url: str,
    period_start: str = "",
    period_end: str = "",
    filing_date: str = "",
    accession_number: str = "",
    proxy_type: str = "",
    calculation_id: str = "",
    formula_version: str = "",
    input_record_ids: Iterable[str] = (),
    guidance_direction: str = "",
    notes: str = "",
    metric_name: str | None = None,
) -> dict[str, Any]:
    normalized_cik = str(int(str(cik))).zfill(10)
    inputs = tuple(input_record_ids)
    record = _empty_row(
        ticker=ticker.upper(),
        cik=normalized_cik,
        company_name=company_name,
        metric_code=metric_code,
        metric_name=metric_name or METRIC_NAMES.get(metric_code, metric_code.replace("_", " ").title()),
        observation_date=observation_date,
        period_start=period_start,
        period_end=period_end or observation_date,
        filing_date=filing_date,
        known_as_of=known_as_of,
        accession_number=accession_number,
        value=value,
        unit=unit,
        frequency=frequency,
        source=source,
        source_url=source_url,
        source_tier="public",
        proxy_type=proxy_type,
        calculation_id=calculation_id,
        formula_version=formula_version,
        input_record_ids="|".join(inputs),
        guidance_direction=guidance_direction,
        qc_flag="OK",
        notes=notes,
    )
    record["record_id"] = _record_id(
        normalized_cik,
        metric_code,
        observation_date,
        known_as_of,
        accession_number,
        value,
        calculation_id,
        record["input_record_ids"],
    )
    return record


def _fact_rows(
    payload: dict[str, Any],
    *,
    ticker: str,
    cik: str,
    company_name: str,
    as_of_date: date,
) -> list[dict[str, Any]]:
    namespaces = payload.get("facts", {})
    if not isinstance(namespaces, dict) or not any(
        isinstance(namespaces.get(namespace), dict)
        for namespace in ("us-gaap", "dei")
    ):
        raise ValueError("SEC Company Facts payload has no supported fact namespace")
    selected_by_identity: dict[tuple[str, str, str], dict[str, Any]] = {}
    claimed_metric_identities: set[tuple[str, str, str]] = set()
    source_url = SEC_COMPANY_FACTS_URL.format(cik=str(int(str(cik))).zfill(10))
    for priority, (concept, definition) in enumerate(CONCEPTS.items()):
        metric_code, metric_name, units, kind = definition
        concept_payload = next(
            (
                namespaces[namespace][concept]
                for namespace in ("us-gaap", "dei")
                if isinstance(namespaces.get(namespace), dict)
                and isinstance(namespaces[namespace].get(concept), dict)
            ),
            None,
        )
        if not isinstance(concept_payload, dict):
            continue
        unit_map = concept_payload.get("units", {})
        observations = next(
            (unit_map[unit] for unit in units if isinstance(unit_map.get(unit), list)),
            [],
        )
        for raw in observations:
            if not isinstance(raw, dict):
                continue
            form = str(raw.get("form") or "")
            if form not in {"10-Q", "10-K", "20-F", "6-K"}:
                continue
            filed = str(raw.get("filed") or "")
            end = str(raw.get("end") or "")
            start = str(raw.get("start") or "")
            if not filed or not end:
                continue
            try:
                filed_date = date.fromisoformat(filed)
                end_date = date.fromisoformat(end)
                start_date = date.fromisoformat(start) if start else None
                value = float(raw["val"])
            except (KeyError, TypeError, ValueError):
                continue
            if (
                filed_date > as_of_date
                or end_date > as_of_date
                or datetime.fromisoformat(_known_at(filed)).astimezone(HONG_KONG)
                > _cutoff(as_of_date)
                or not math.isfinite(value)
            ):
                continue
            if kind == "duration" and start_date is None:
                continue
            frame = str(raw.get("frame") or "")
            identity = (metric_code, start, end)
            existing = selected_by_identity.get(identity)
            candidate = {
                "metric_code": metric_code,
                "metric_name": metric_name,
                "start": start,
                "end": end,
                "filed": filed,
                "form": form,
                "frame": frame,
                "accession": str(raw.get("accn") or ""),
                "value": value,
                "unit": units[0],
                "kind": kind,
                "priority": priority,
            }
            if existing is None or candidate["priority"] < existing["priority"] or (
                candidate["priority"] == existing["priority"]
                and (candidate["filed"], candidate["accession"])
                > (existing["filed"], existing["accession"])
            ):
                selected_by_identity[identity] = candidate

    rows = []
    # Prefer the first registered SEC concept when multiple concepts represent the
    # same metric and period. The concept order above is the explicit fallback order.
    for observation in selected_by_identity.values():
        identity = (
            observation["metric_code"],
            observation["start"],
            observation["end"],
        )
        if identity in claimed_metric_identities:
            continue
        claimed_metric_identities.add(identity)
        rows.append(
            make_company_fundamental_row(
                ticker=ticker,
                cik=cik,
                company_name=company_name,
                metric_code=observation["metric_code"],
                metric_name=observation["metric_name"],
                observation_date=observation["end"],
                period_start=observation["start"],
                period_end=observation["end"],
                filing_date=observation["filed"],
                known_as_of=_known_at(observation["filed"]),
                accession_number=observation["accession"],
                value=observation["value"],
                unit=observation["unit"],
                frequency=(
                    "annual"
                    if observation["form"] in {"10-K", "20-F"}
                    else "quarterly"
                    if observation["kind"] == "duration"
                    and observation["start"]
                    and (
                        date.fromisoformat(observation["end"])
                        - date.fromisoformat(observation["start"])
                    ).days
                    <= 120
                    else "year_to_date"
                    if observation["kind"] == "duration"
                    else "reported"
                ),
                source="SEC EDGAR Company Facts",
                source_url=source_url,
                notes=f"SEC concept normalized from {observation['form']} filing.",
            )
        )
    return sorted(rows, key=lambda row: (row["metric_code"], row["observation_date"], row["known_as_of"]))


def _latest(rows: Iterable[dict[str, Any]], code: str) -> dict[str, Any] | None:
    candidates = [row for row in rows if row["metric_code"] == code]
    return max(candidates, key=lambda row: (row["observation_date"], row["known_as_of"]), default=None)


def _quarterly(rows: Iterable[dict[str, Any]], code: str) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in rows
        if row["metric_code"] == code
        and row["frequency"] in {"quarterly", "quarterly_derived"}
    ]
    latest_by_end: dict[str, dict[str, Any]] = {}
    for row in candidates:
        current = latest_by_end.get(row["period_end"])
        if current is None or row["known_as_of"] > current["known_as_of"]:
            latest_by_end[row["period_end"]] = row
    return sorted(latest_by_end.values(), key=lambda row: row["period_end"])[-4:]


def _derived(
    rows: list[dict[str, Any]],
    *,
    code: str,
    value: float,
    unit: str,
    inputs: Iterable[dict[str, Any]],
    calculation_id: str,
    frequency: str = "trailing",
    proxy_type: str = "",
    notes: str = "",
    observation_date: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, Any]:
    input_rows = tuple(inputs)
    if not input_rows:
        raise ValueError(f"Derived fundamental {code} requires inputs")
    latest_observation = observation_date or max(row["observation_date"] for row in input_rows)
    known_as_of = max(input_rows, key=lambda row: datetime.fromisoformat(row["known_as_of"]))["known_as_of"]
    filing_dates = [row["filing_date"] for row in input_rows if row["filing_date"]]
    return make_company_fundamental_row(
        ticker=input_rows[0]["ticker"],
        cik=input_rows[0]["cik"],
        company_name=input_rows[0]["company_name"],
        metric_code=code,
        observation_date=latest_observation,
        period_start=period_start
        if period_start is not None
        else min((row["period_start"] for row in input_rows if row["period_start"]), default=""),
        period_end=period_end
        if period_end is not None
        else max((row["period_end"] for row in input_rows if row["period_end"]), default=latest_observation),
        filing_date=max(filing_dates, default=""),
        known_as_of=known_as_of,
        value=value,
        unit=unit,
        frequency=frequency,
        source="Registered calculation from public inputs",
        source_url=input_rows[0]["source_url"],
        proxy_type=proxy_type,
        calculation_id=calculation_id,
        formula_version=FORMULA_VERSION,
        input_record_ids=(row["record_id"] for row in input_rows),
        notes=notes,
    )


def _derive_standalone_quarters(rows: list[dict[str, Any]]) -> None:
    duration_codes = {
        "revenue",
        "gross_profit",
        "operating_income",
        "net_income",
        "operating_cash_flow",
        "capital_expenditure",
        "depreciation_and_amortization",
        "diluted_eps",
    }
    derived = []
    for code in duration_codes:
        annuals = [
            row
            for row in rows
            if row["metric_code"] == code and row["frequency"] == "annual"
        ]
        for annual in annuals:
            cumulative = sorted(
                (
                    row
                    for row in rows
                    if row["metric_code"] == code
                    and row["period_start"] == annual["period_start"]
                    and row["period_end"] < annual["period_end"]
                    and row["frequency"] in {"quarterly", "year_to_date"}
                ),
                key=lambda row: row["period_end"],
            )
            if not cumulative:
                continue
            previous_cumulative = cumulative[0]
            for current in cumulative[1:]:
                if any(
                    row["metric_code"] == code
                    and row["period_end"] == current["period_end"]
                    and row["frequency"] == "quarterly"
                    for row in rows
                ):
                    previous_cumulative = current
                    continue
                quarter_start = (
                    date.fromisoformat(previous_cumulative["period_end"])
                    + timedelta(days=1)
                ).isoformat()
                derived.append(
                    _derived(
                        rows,
                        code=code,
                        value=float(current["value"])
                        - float(previous_cumulative["value"]),
                        unit=current["unit"],
                        inputs=(current, previous_cumulative),
                        calculation_id="year_to_date_difference",
                        frequency="quarterly_derived",
                        observation_date=current["period_end"],
                        period_start=quarter_start,
                        period_end=current["period_end"],
                        notes="Standalone quarter derived from consecutive SEC year-to-date facts.",
                    )
                )
                previous_cumulative = current
            if not any(
                row["metric_code"] == code
                and row["period_end"] == annual["period_end"]
                and row["frequency"] == "quarterly"
                for row in rows
            ):
                latest_cumulative = cumulative[-1]
                quarter_start = (
                    date.fromisoformat(latest_cumulative["period_end"])
                    + timedelta(days=1)
                ).isoformat()
                derived.append(
                    _derived(
                        rows,
                        code=code,
                        value=float(annual["value"])
                        - float(latest_cumulative["value"]),
                        unit=annual["unit"],
                        inputs=(annual, latest_cumulative),
                        calculation_id="annual_minus_year_to_date",
                        frequency="quarterly_derived",
                        observation_date=annual["period_end"],
                        period_start=quarter_start,
                        period_end=annual["period_end"],
                        notes="Fourth quarter derived from annual SEC fact minus the latest year-to-date fact.",
                    )
                )
    rows.extend(derived)


def _ttm_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for code in (
        "revenue",
        "gross_profit",
        "operating_income",
        "net_income",
        "operating_cash_flow",
        "capital_expenditure",
        "depreciation_and_amortization",
        "diluted_eps",
    ):
        quarters = _quarterly(rows, code)
        if len(quarters) != 4:
            continue
        end_dates = [date.fromisoformat(row["period_end"]) for row in quarters]
        if any((right - left).days > 120 for left, right in zip(end_dates, end_dates[1:])):
            continue
        derived = _derived(
            rows,
            code=f"{code}_ttm",
            value=sum(float(row["value"]) for row in quarters),
            unit=quarters[0]["unit"],
            inputs=quarters,
            calculation_id="four_quarter_sum",
            notes="Sum of the latest four eligible standalone quarterly SEC facts.",
        )
        rows.append(derived)
        result[code] = derived
    return result


def _price_rows(
    price_history: Iterable[dict[str, Any]],
    *,
    ticker: str,
    cik: str,
    company_name: str,
    as_of_date: date,
) -> list[dict[str, Any]]:
    by_date: dict[str, float] = {}
    for raw in price_history:
        observation = str(raw.get("date") or "")
        try:
            observed = date.fromisoformat(observation)
            value = float(raw["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if observed > as_of_date or not math.isfinite(value) or value <= 0:
            continue
        by_date[observation] = value
    return [
        make_company_fundamental_row(
            ticker=ticker,
            cik=cik,
            company_name=company_name,
            metric_code="share_price",
            observation_date=observation,
            known_as_of=_price_known_at(observation),
            value=value,
            unit="USD_per_share",
            frequency="daily",
            source="Yahoo Finance historical close",
            source_url=YAHOO_FINANCE_URL.format(ticker=ticker.upper()),
            notes="Public-vendor close; observation date is bounded by target Sunday.",
        )
        for observation, value in sorted(by_date.items())
    ]


def _price_on_or_before(price_rows: list[dict[str, Any]], cutoff_date: str) -> dict[str, Any] | None:
    return max(
        (row for row in price_rows if row["observation_date"] <= cutoff_date),
        key=lambda row: row["observation_date"],
        default=None,
    )


def _same_period(rows: list[dict[str, Any]], code: str, period_end: str) -> dict[str, Any] | None:
    return max(
        (
            row
            for row in rows
            if row["metric_code"] == code and row["period_end"] == period_end
        ),
        key=lambda row: row["known_as_of"],
        default=None,
    )


def _multiple_rows(
    rows: list[dict[str, Any]],
    *,
    price: dict[str, Any],
    shares: dict[str, Any] | None,
    revenue: dict[str, Any] | None,
    net_income: dict[str, Any] | None,
    equity: dict[str, Any] | None,
    operating_income: dict[str, Any] | None,
    depreciation: dict[str, Any] | None,
    cash: dict[str, Any] | None,
    debt_current: dict[str, Any] | None,
    debt_noncurrent: dict[str, Any] | None,
    frequency: str,
) -> list[dict[str, Any]]:
    if shares is None or float(shares["value"]) <= 0:
        return []
    market_cap = float(price["value"]) * float(shares["value"])
    output = []
    if net_income is not None and float(net_income["value"]) > 0:
        output.append(
            _derived(
                rows,
                code="trailing_pe",
                value=market_cap / float(net_income["value"]),
                unit="multiple",
                inputs=(price, shares, net_income),
                calculation_id="market_cap_divided_by_net_income",
                frequency=frequency,
                notes="Trailing public-input multiple; not forward consensus P/E.",
                observation_date=price["observation_date"],
            )
        )
    if equity is not None and float(equity["value"]) > 0:
        output.append(
            _derived(
                rows,
                code="price_to_book",
                value=market_cap / float(equity["value"]),
                unit="multiple",
                inputs=(price, shares, equity),
                calculation_id="market_cap_divided_by_book_equity",
                frequency=frequency,
                observation_date=price["observation_date"],
            )
        )
    if revenue is not None and float(revenue["value"]) > 0:
        output.append(
            _derived(
                rows,
                code="price_to_sales",
                value=market_cap / float(revenue["value"]),
                unit="multiple",
                inputs=(price, shares, revenue),
                calculation_id="market_cap_divided_by_revenue",
                frequency=frequency,
                observation_date=price["observation_date"],
            )
        )
    if all(item is not None for item in (operating_income, depreciation, cash, debt_current, debt_noncurrent)):
        ebitda = float(operating_income["value"]) + float(depreciation["value"])
        if ebitda > 0:
            enterprise_value = (
                market_cap
                + float(debt_current["value"])
                + float(debt_noncurrent["value"])
                - float(cash["value"])
            )
            output.append(
                _derived(
                    rows,
                    code="ev_to_ebitda",
                    value=enterprise_value / ebitda,
                    unit="multiple",
                    inputs=(
                        price,
                        shares,
                        debt_current,
                        debt_noncurrent,
                        cash,
                        operating_income,
                        depreciation,
                    ),
                    calculation_id="enterprise_value_divided_by_ebitda",
                    frequency=frequency,
                    observation_date=price["observation_date"],
                    notes="EBITDA equals operating income plus available D&A facts.",
                )
            )
    return output


def _historical_multiples(
    rows: list[dict[str, Any]], price_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    output = []
    annual_revenue = [
        row
        for row in rows
        if row["metric_code"] == "revenue" and row["frequency"] == "annual"
    ]
    for revenue in annual_revenue:
        end = revenue["period_end"]
        inputs = {
            code: _same_period(rows, code, end)
            for code in (
                "shares_outstanding",
                "net_income",
                "stockholders_equity",
                "operating_income",
                "depreciation_and_amortization",
                "cash_and_equivalents",
                "debt_current",
                "debt_noncurrent",
            )
        }
        available = [revenue, *(row for row in inputs.values() if row is not None)]
        known_date = max(row["known_as_of"][:10] for row in available)
        price = _price_on_or_before(price_rows, known_date)
        if price is None:
            continue
        output.extend(
            _multiple_rows(
                rows,
                price=price,
                shares=inputs["shares_outstanding"],
                revenue=revenue,
                net_income=inputs["net_income"],
                equity=inputs["stockholders_equity"],
                operating_income=inputs["operating_income"],
                depreciation=inputs["depreciation_and_amortization"],
                cash=inputs["cash_and_equivalents"],
                debt_current=inputs["debt_current"],
                debt_noncurrent=inputs["debt_noncurrent"],
                frequency="annual_point_in_time",
            )
        )
    return output


def normalize_company_fundamental_rows(
    rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized = []
    seen = set()
    for raw in rows:
        missing = [field for field in COMPANY_FUNDAMENTAL_FIELDS if field not in raw]
        if missing:
            raise ValueError(
                "Company fundamental row missing required fields: " + ", ".join(missing)
            )
        row = {field: raw[field] for field in COMPANY_FUNDAMENTAL_FIELDS}
        if not row["record_id"] or row["record_id"] in seen:
            raise ValueError(f"Duplicate or blank company fundamental record_id: {row['record_id']}")
        seen.add(row["record_id"])
        if row["value"] not in (None, ""):
            try:
                value = float(row["value"])
            except (TypeError, ValueError) as error:
                raise ValueError("Company fundamental value must be numeric") from error
            if not math.isfinite(value):
                raise ValueError("Company fundamental value must be finite")
        known = datetime.fromisoformat(str(row["known_as_of"]))
        if known.tzinfo is None or known.utcoffset() is None:
            raise ValueError("Company fundamental known_as_of must include a UTC offset")
        normalized.append(row)
    return sorted(normalized, key=lambda row: (row["ticker"], row["metric_code"], row["observation_date"], row["known_as_of"]))


def validate_company_fundamental_input_references(
    rows: Iterable[dict[str, Any]],
) -> None:
    records = list(rows)
    identities = {str(row["record_id"]) for row in records}
    for row in records:
        calculation = str(row.get("calculation_id") or "")
        inputs = [value for value in str(row.get("input_record_ids") or "").split("|") if value]
        if calculation:
            if not row.get("formula_version") or not inputs:
                raise ValueError(
                    f"Calculated company fundamental {row.get('record_id')} lacks formula lineage"
                )
            missing = [record_id for record_id in inputs if record_id not in identities]
            if missing:
                raise ValueError(
                    f"Calculated company fundamental input {missing[0]} does not resolve"
                )
        elif inputs or row.get("formula_version"):
            raise ValueError(
                f"Observed company fundamental {row.get('record_id')} declares calculation lineage"
            )


def build_company_fundamentals(
    text: str,
    *,
    ticker: str,
    cik: str,
    company_name: str,
    as_of_date: date,
    price_history: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    payload = json.loads(text)
    rows = _fact_rows(
        payload,
        ticker=ticker,
        cik=cik,
        company_name=company_name,
        as_of_date=as_of_date,
    )
    _derive_standalone_quarters(rows)
    ttm = _ttm_rows(rows)

    if "operating_cash_flow" in ttm and "capital_expenditure" in ttm:
        rows.append(
            _derived(
                rows,
                code="free_cash_flow_ttm",
                value=float(ttm["operating_cash_flow"]["value"])
                - float(ttm["capital_expenditure"]["value"]),
                unit="USD",
                inputs=(ttm["operating_cash_flow"], ttm["capital_expenditure"]),
                calculation_id="operating_cash_flow_minus_capex",
            )
        )
    margin_specs = (
        ("gross_margin_ttm", "gross_profit"),
        ("operating_margin_ttm", "operating_income"),
        ("net_margin_ttm", "net_income"),
    )
    revenue_ttm = ttm.get("revenue")
    if revenue_ttm is not None and float(revenue_ttm["value"]) != 0:
        for code, numerator_code in margin_specs:
            numerator = ttm.get(numerator_code)
            if numerator is None:
                continue
            rows.append(
                _derived(
                    rows,
                    code=code,
                    value=float(numerator["value"]) / float(revenue_ttm["value"]),
                    unit="ratio",
                    inputs=(numerator, revenue_ttm),
                    calculation_id="ttm_metric_divided_by_ttm_revenue",
                )
            )

    price_rows = _price_rows(
        price_history,
        ticker=ticker,
        cik=cik,
        company_name=company_name,
        as_of_date=as_of_date,
    )
    historical = _historical_multiples(rows, price_rows)

    current_price = _price_on_or_before(price_rows, as_of_date.isoformat())
    current_multiples = []
    if current_price is not None:
        current_multiples = _multiple_rows(
            rows,
            price=current_price,
            shares=_latest(rows, "shares_outstanding"),
            revenue=ttm.get("revenue"),
            net_income=ttm.get("net_income"),
            equity=_latest(rows, "stockholders_equity"),
            operating_income=ttm.get("operating_income"),
            depreciation=ttm.get("depreciation_and_amortization"),
            cash=_latest(rows, "cash_and_equivalents"),
            debt_current=_latest(rows, "debt_current"),
            debt_noncurrent=_latest(rows, "debt_noncurrent"),
            frequency="trailing",
        )
    used_price_ids = {
        input_id
        for multiple in (*historical, *current_multiples)
        for input_id in str(multiple["input_record_ids"]).split("|")
    }
    rows.extend(
        row for row in price_rows if row["record_id"] in used_price_ids
    )
    rows.extend(historical)
    rows.extend(current_multiples)

    for current in current_multiples:
        history = [
            row
            for row in historical
            if row["metric_code"] == current["metric_code"]
            and row["observation_date"] < current["observation_date"]
        ]
        if len(history) < MIN_PERCENTILE_HISTORY:
            continue
        percentile = 100.0 * sum(
            float(row["value"]) <= float(current["value"]) for row in history
        ) / len(history)
        rows.append(
            _derived(
                rows,
                code=f"{current['metric_code']}_percentile",
                value=percentile,
                unit="percentile",
                inputs=(current, *history),
                calculation_id="historical_percentile_rank",
                proxy_type="historical_point_in_time_percentile",
                notes=(
                    f"Percentile versus {len(history)} historical point-in-time "
                    "annual valuation observations."
                ),
                observation_date=current["observation_date"],
            )
        )

    normalized = normalize_company_fundamental_rows(rows)
    validate_company_fundamental_input_references(normalized)
    cutoff = _cutoff(as_of_date)
    if any(datetime.fromisoformat(row["known_as_of"]).astimezone(HONG_KONG) > cutoff for row in normalized):
        raise ValueError("Company fundamental row exceeds target-Sunday cutoff")
    return normalized


__all__ = [
    "COMPANY_FUNDAMENTAL_FIELDS",
    "build_company_fundamentals",
    "make_company_fundamental_row",
    "normalize_company_fundamental_rows",
    "validate_company_fundamental_input_references",
]
