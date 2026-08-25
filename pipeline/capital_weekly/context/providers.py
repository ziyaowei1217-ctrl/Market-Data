from __future__ import annotations

import csv
import io
import os
import re
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pipeline.common import load_config_rows

try:
    import yfinance as yf
except ImportError:
    yf = None

from .provider_contracts import ContextProvider, ProviderResult, ProviderSpec
from .commodities import (
    EIA_SOURCE_URL,
    calculate_weekly_change,
    eia_not_configured_result,
    parse_eia_series,
)
from .company_events import load_company_watchlist, parse_sec_submissions
from .events import (
    parse_bls_calendar,
    parse_census_calendar,
    parse_fed_calendar,
    select_event_window,
)
from .financial_conditions import (
    calculate_financial_conditions,
    parse_fred_components_csv,
)
from .market_internals import parse_nasdaq_market_summary
from .microstructure import (
    ensure_fresh_market_date,
    parse_hkex_market_highlights,
    parse_hkex_short_selling,
    parse_sse_daily_overview,
    parse_szse_daily_overview,
)
from .positioning import parse_cftc_tff_csv, parse_finra_margin_table
from .volatility import (
    calculate_yahoo_volatility_metrics,
    extract_yahoo_close_histories,
    load_yahoo_volatility_config,
    serialize_yahoo_close_histories,
)


BLS_URL = "https://www.bls.gov/schedule/{year}/home.htm"
FED_URL = "https://www.federalreserve.gov/newsevents/calendar.htm"
CENSUS_URL = "https://www.census.gov/economic-indicators/calendar-listview.html"
NASDAQ_URL = "https://www.nasdaqtrader.com/Trader.aspx?id=DailyMarketSummary"
FINRA_URL = "https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
CFTC_URL = "https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip"
SEC_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
HKEX_URL = "https://www.hkex.com.hk/eng/stat/smstat/dayquot/d{stamp}e.htm"
SSE_URL = "https://query.sse.com.cn/commonQuery.do"
SZSE_URL = "https://www.szse.cn/api/report/ShowReport/data"
YAHOO_FINANCE_URL = "https://finance.yahoo.com/"
YAHOO_VOLATILITY_SOURCE = "Yahoo Finance (Cboe indices)"


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; capital-weekly-public-data/1.0; "
                "+https://example.com)"
            ),
            "Accept": "text/html,application/json,text/csv,*/*",
        }
    )
    return session


def _text(
    session: requests.Session,
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> str:
    response = session.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    if not response.encoding:
        response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def _bytes(session: requests.Session, url: str) -> bytes:
    response = session.get(url, timeout=45)
    response.raise_for_status()
    return response.content


def _config(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def metric_rows(
    *,
    as_of_date: date,
    category: str,
    market: str,
    source: str,
    source_url: str,
    frequency: str,
    values: Mapping[str, Any],
    units: Mapping[str, str],
    names: Mapping[str, str] | None = None,
    qc_flag: str = "OK",
) -> list[dict[str, Any]]:
    return [
        {
            "as_of_date": as_of_date,
            "category": category,
            "metric_code": code,
            "metric_name": (names or {}).get(code, code.replace("_", " ")),
            "value": value,
            "unit": units.get(code, "value"),
            "frequency": frequency,
            "market": market,
            "source": source,
            "source_url": source_url,
            "qc_flag": qc_flag,
        }
        for code, value in values.items()
    ]


def not_configured_result(
    *,
    category: str,
    source: str,
    source_url: str,
    notes: str,
) -> ProviderResult:
    return ProviderResult(
        category=category,
        rows=[],
        raw_text="",
        source=source,
        source_url=source_url,
        status="NOT_CONFIGURED",
        notes=notes,
    )


def _event_provider(
    session: requests.Session,
    *,
    url: str,
    parser: Callable[[str], list[dict]],
    start: date,
    end: date,
    source: str,
) -> ProviderResult:
    text = _text(session, url)
    return ProviderResult(
        category="events",
        rows=select_event_window(parser(text), start, end),
        raw_text=text,
        source=source,
        source_url=url,
    )


def _bls_provider(
    session: requests.Session, start: date, end: date
) -> ProviderResult:
    raw = []
    events = []
    for year in range(start.year, end.year + 1):
        url = BLS_URL.format(year=year)
        text = _text(session, url)
        raw.append(text)
        events.extend(parse_bls_calendar(text))
    return ProviderResult(
        category="events",
        rows=select_event_window(events, start, end),
        raw_text="\n".join(raw),
        source="U.S. Bureau of Labor Statistics",
        source_url=BLS_URL.format(year=end.year),
    )


def _fed_provider(
    session: requests.Session, start: date, end: date
) -> ProviderResult:
    index = _text(session, FED_URL)
    raw = [index]
    events = []
    cursor = start.replace(day=1)
    final_month = end.replace(day=1)
    while cursor <= final_month:
        label = cursor.strftime("%B %Y")
        match = re.search(
            rf'href=["\']([^"\']+)["\'][^>]*>\s*{re.escape(label)}\s*</a>',
            index,
            flags=re.IGNORECASE,
        )
        if not match:
            raise ValueError(f"Federal Reserve calendar index missing {label}")
        url = urljoin(FED_URL, match.group(1))
        text = _text(session, url)
        raw.append(text)
        events.extend(parse_fed_calendar(text))
        cursor = (
            cursor.replace(year=cursor.year + 1, month=1)
            if cursor.month == 12
            else cursor.replace(month=cursor.month + 1)
        )
    return ProviderResult(
        category="events",
        rows=select_event_window(events, start, end),
        raw_text="\n".join(raw),
        source="Federal Reserve Board",
        source_url=FED_URL,
    )


def _nasdaq_provider(
    session: requests.Session, start: date, end: date
) -> ProviderResult:
    text = _text(session, NASDAQ_URL)
    rows = []
    units = {
        "share_volume": "shares",
        "dollar_volume": "USD",
        "block_volume": "shares",
        "issue_count": "count",
        "trade_count": "count",
        "block_trade_count": "count",
        "block_volume_ratio": "ratio",
    }
    for observation in parse_nasdaq_market_summary(text):
        if start <= observation["date"] <= end:
            values = {key: value for key, value in observation.items() if key != "date"}
            rows.extend(
                metric_rows(
                    as_of_date=observation["date"],
                    category="market_internals",
                    market="NASDAQ",
                    source="Nasdaq Trader",
                    source_url=NASDAQ_URL,
                    frequency="daily",
                    values=values,
                    units=units,
                )
            )
    return ProviderResult(
        category="market_internals",
        rows=rows,
        raw_text=text,
        source="Nasdaq Trader",
        source_url=NASDAQ_URL,
    )


def _finra_provider(session: requests.Session, end: date) -> ProviderResult:
    text = _text(session, FINRA_URL)
    parsed = [row for row in parse_finra_margin_table(text) if row["date"] <= end]
    if not parsed:
        raise ValueError("FINRA returned no observation on or before the report end")
    latest = parsed[-1]
    values = {key: value for key, value in latest.items() if key != "date"}
    rows = metric_rows(
        as_of_date=latest["date"],
        category="positioning_flows",
        market="US",
        source="FINRA",
        source_url=FINRA_URL,
        frequency="monthly",
        values=values,
        units={key: "USD millions" for key in values},
    )
    return ProviderResult(
        category="positioning_flows",
        rows=rows,
        raw_text=text,
        source="FINRA",
        source_url=FINRA_URL,
    )


def _cftc_provider(
    session: requests.Session,
    start: date,
    end: date,
    contract_codes: dict[str, str],
) -> ProviderResult:
    parsed = []
    raw_archives = []
    source_url = CFTC_URL.format(year=end.year)
    for year in range(start.year, end.year + 1):
        source_url = CFTC_URL.format(year=year)
        content = _bytes(session, source_url)
        raw_archives.append(content)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = [
                name for name in archive.namelist() if name.lower().endswith((".txt", ".csv"))
            ]
            if not members:
                raise ValueError("CFTC archive contained no text data")
            text = archive.read(members[0]).decode("utf-8-sig", errors="replace")
        parsed.extend(parse_cftc_tff_csv(text, contract_codes))
    selected = [row for row in parsed if start <= row["report_date"] <= end]
    rows = []
    for observation in selected:
        values = {
            key: observation[key]
            for key in (
                "open_interest",
                "asset_manager_net",
                "leveraged_fund_net",
                "asset_manager_net_change",
                "leveraged_fund_net_change",
                "asset_manager_percentile",
            )
        }
        code = observation["metric_code"]
        rows.extend(
            metric_rows(
                as_of_date=observation["report_date"],
                category="positioning_flows",
                market=code,
                source="U.S. Commodity Futures Trading Commission",
                source_url=source_url,
                frequency="weekly",
                values={f"{code}_{key}": value for key, value in values.items()},
                units={
                    f"{code}_{key}": (
                        "ratio" if key.endswith("percentile") else "contracts"
                    )
                    for key in values
                },
            )
        )
    return ProviderResult(
        category="positioning_flows",
        rows=rows,
        raw_text=b"".join(raw_archives),
        source="U.S. Commodity Futures Trading Commission",
        source_url=source_url,
    )


def _sec_provider(
    session: requests.Session,
    start: date,
    end: date,
    watchlist: list[dict[str, str]],
    user_agent: str | None,
) -> ProviderResult:
    if not watchlist:
        return not_configured_result(
            category="company_events",
            source="SEC EDGAR",
            source_url="https://data.sec.gov/submissions/",
            notes="Company watchlist is empty; add enabled CIK rows to fetch filings.",
        )
    if not user_agent:
        return not_configured_result(
            category="company_events",
            source="SEC EDGAR",
            source_url="https://data.sec.gov/submissions/",
            notes="Set SEC_USER_AGENT before fetching configured company filings.",
        )
    rows = []
    raw = []
    for company in watchlist:
        url = SEC_URL.format(cik=company["cik"])
        text = _text(session, url, headers={"User-Agent": user_agent})
        raw.append(text)
        for event in parse_sec_submissions(
            text,
            cik=company["cik"],
            ticker=company["ticker"],
            start=start,
            end=end,
        ):
            base = metric_rows(
                as_of_date=event["event_date"],
                category="company_events",
                market=event["ticker"],
                source=event["source"],
                source_url=event["source_url"],
                frequency="event",
                values={f"sec_{event['form'].lower().replace('-', '_')}": 1},
                units={f"sec_{event['form'].lower().replace('-', '_')}": "event"},
            )[0]
            base.update(event)
            base["as_of_date"] = event["event_date"]
            base["category"] = "company_events"
            rows.append(base)
    return ProviderResult(
        category="company_events",
        rows=rows,
        raw_text="\n".join(raw),
        source="SEC EDGAR",
        source_url="https://data.sec.gov/submissions/",
    )


def _eia_provider(
    session: requests.Session,
    end: date,
    series_config: list[dict[str, str]],
    api_key: str | None,
) -> ProviderResult:
    if not api_key:
        return eia_not_configured_result()
    rows = []
    raw = []
    for item in series_config:
        url = f"{EIA_SOURCE_URL}{item['route']}/data/"
        text = _text(
            session,
            url,
            params={
                "api_key": api_key,
                "frequency": item["frequency"],
                "data[0]": "value",
                "facets[series][]": item["series"],
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 8,
            },
        )
        raw.append(text)
        parsed = [
            row
            for row in parse_eia_series(
                text,
                metric_code=item["metric_code"],
                expected_unit=item["expected_unit"],
            )
            if date.fromisoformat(row["period"]) <= end
        ]
        if len(parsed) < 2:
            raise ValueError(f"EIA series {item['metric_code']} has fewer than two observations")
        latest = parsed[-1]
        change = calculate_weekly_change(parsed)
        values = {
            item["metric_code"]: latest["value"],
            f"{item['metric_code']}_weekly_change": change["change"],
            f"{item['metric_code']}_weekly_change_pct": change["change_pct"],
        }
        rows.extend(
            metric_rows(
                as_of_date=date.fromisoformat(latest["period"]),
                category="commodity_fundamentals",
                market="US",
                source="U.S. Energy Information Administration",
                source_url=url,
                frequency=item["frequency"],
                values=values,
                units={
                    item["metric_code"]: latest["unit"],
                    f"{item['metric_code']}_weekly_change": latest["unit"],
                    f"{item['metric_code']}_weekly_change_pct": "ratio",
                },
            )
        )
    return ProviderResult(
        category="commodity_fundamentals",
        rows=rows,
        raw_text="\n".join(raw),
        source="U.S. Energy Information Administration",
        source_url=EIA_SOURCE_URL,
    )


def _fred_provider(
    session: requests.Session,
    end: date,
    config: list[dict[str, str]],
) -> ProviderResult:
    start = end - timedelta(days=550)
    raw = []
    components = []
    for item in config:
        text = _text(
            session,
            FRED_URL,
            params={
                "id": item["series_id"],
                "cosd": start.isoformat(),
                "coed": end.isoformat(),
            },
        )
        raw.append(text)
        components.extend(
            parse_fred_components_csv(
                text,
                [item],
                expected_end=end,
                minimum_observations=60,
            )
        )
    result = calculate_financial_conditions(
        components,
        expected_components=len(config),
        expected_end=end,
    )
    rows = metric_rows(
        as_of_date=end,
        category="financial_conditions",
        market="US",
        source="Federal Reserve Economic Data",
        source_url=FRED_URL,
        frequency="daily",
        values={
            "financial_conditions_score": result["score"],
            "financial_conditions_coverage": result["coverage"],
        },
        units={
            "financial_conditions_score": "z-score",
            "financial_conditions_coverage": "ratio",
        },
        qc_flag=result["qc_flag"],
    )
    for component in result["components"]:
        rows.extend(
            metric_rows(
                as_of_date=component["as_of_date"],
                category="financial_conditions",
                market="US",
                source="Federal Reserve Economic Data",
                source_url=FRED_URL,
                frequency="daily",
                values={f"{component['metric_code']}_risk_z": component["z_score"]},
                units={f"{component['metric_code']}_risk_z": "z-score"},
            )
        )
    return ProviderResult(
        category="financial_conditions",
        rows=rows,
        raw_text="\n".join(raw),
        source="Federal Reserve Economic Data",
        source_url=FRED_URL,
        status=result["qc_flag"],
        notes=f"regime={result['regime']}; excluded={result['excluded']}",
    )


def _default_yahoo_download(**kwargs):
    if yf is None:
        raise RuntimeError(
            "yfinance is unavailable; install the declared Python requirements"
        )
    return yf.download(**kwargs)


def _yahoo_volatility_provider(
    downloader: Callable[..., Any],
    end: date,
    config,
) -> ProviderResult:
    raw_text = ""
    try:
        frame = downloader(
            tickers=[item.ticker for item in config],
            start=(end - timedelta(days=550)).isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=False,
            group_by="ticker",
            threads=False,
            progress=False,
        )
        histories = extract_yahoo_close_histories(frame, config, end)
        raw_text = serialize_yahoo_close_histories(histories, config)
        metrics = calculate_yahoo_volatility_metrics(histories, config, end)
        published_codes = {metric["metric_code"] for metric in metrics}
        unavailable_roles = [
            item.role
            for item in config
            if item.metric_code not in published_codes
        ]
        unavailable_calculations = [
            code
            for code in (
                "vix_1m_3m_spread",
                "vix_1m_3m_ratio",
                "vix_9d_1m_spread",
            )
            if code not in published_codes
        ]
        notes = []
        if unavailable_roles:
            notes.append(
                "missing or stale roles: " + ", ".join(unavailable_roles)
            )
        if unavailable_calculations:
            notes.append(
                "omitted calculations due to missing inputs or no fresh common "
                "date: " + ", ".join(unavailable_calculations)
            )
        rows = [
            {
                "as_of_date": metric["as_of_date"],
                "category": "financial_conditions",
                "metric_code": metric["metric_code"],
                "metric_name": metric["metric_name"],
                "value": metric["value"],
                "unit": metric["unit"],
                "frequency": "daily",
                "market": "US",
                "source": YAHOO_VOLATILITY_SOURCE,
                "source_url": metric["source_url"],
                "qc_flag": "OK",
            }
            for metric in metrics
        ]
        return ProviderResult(
            category="financial_conditions",
            rows=rows,
            raw_text=raw_text,
            source=YAHOO_VOLATILITY_SOURCE,
            source_url=YAHOO_FINANCE_URL,
            notes="; ".join(notes),
        )
    except Exception as error:
        return ProviderResult(
            category="financial_conditions",
            rows=[],
            raw_text=raw_text,
            source=YAHOO_VOLATILITY_SOURCE,
            source_url=YAHOO_FINANCE_URL,
            status="FETCH_FAILED",
            notes=str(error),
        )


def _hkex_provider(
    session: requests.Session, end: date
) -> ProviderResult:
    failures = []
    for lag in range(8):
        candidate = end - timedelta(days=lag)
        url = HKEX_URL.format(stamp=candidate.strftime("%y%m%d"))
        try:
            text = _text(session, url)
            highlights = parse_hkex_market_highlights(text)
            ensure_fresh_market_date(
                highlights["as_of_date"], expected_end=end, max_lag_days=4
            )
            short = parse_hkex_short_selling(text)
            values = {
                key: value
                for key, value in {**highlights, **short}.items()
                if key not in {"as_of_date", "market", "market_turnover"}
            }
            units = {
                "volume": "shares",
                "turnover": "HKD",
                "trades": "count",
                "advancers": "count",
                "decliners": "count",
                "unchanged": "count",
                "advance_ratio": "ratio",
                "advance_decline": "count",
                "short_turnover": "HKD",
                "short_turnover_ratio": "ratio",
            }
            rows = metric_rows(
                as_of_date=highlights["as_of_date"],
                category="market_internals",
                market="HKEX",
                source="Hong Kong Exchanges and Clearing",
                source_url=url,
                frequency="daily",
                values=values,
                units=units,
            )
            return ProviderResult(
                category="market_internals",
                rows=rows,
                raw_text=text,
                source="Hong Kong Exchanges and Clearing",
                source_url=url,
            )
        except Exception as error:
            failures.append(f"{candidate}: {error}")
    raise ValueError("No recent HKEX Daily Quotations report: " + "; ".join(failures))


def _exchange_provider(
    session: requests.Session,
    *,
    url: str | None,
    market: str,
    parser: Callable[[str], dict[str, Any]],
    end: date,
) -> ProviderResult:
    source_url = url or (
        "https://www.sse.com.cn/" if market == "SSE" else "https://www.szse.cn/"
    )


def _sse_provider(session: requests.Session, end: date) -> ProviderResult:
    failures = []
    for lag in range(8):
        candidate = end - timedelta(days=lag)
        try:
            text = _text(
                session,
                SSE_URL,
                params={
                    "jsonCallBack": "capitalWeeklyCallback",
                    "sqlId": "COMMON_SSE_SJ_GPSJ_CJGK_MRGK_C",
                    "PRODUCT_CODE": "01,02,03,11,17",
                    "type": "inParams",
                    "SEARCH_DATE": candidate.isoformat(),
                },
                headers={
                    "Referer": "https://www.sse.com.cn/market/stockdata/overview/day/"
                },
            )
            observation = parse_sse_daily_overview(text)
            ensure_fresh_market_date(
                observation["as_of_date"], expected_end=end, max_lag_days=4
            )
            values = {
                key: value
                for key, value in observation.items()
                if key not in {"as_of_date", "market"}
            }
            return ProviderResult(
                category="market_internals",
                rows=metric_rows(
                    as_of_date=observation["as_of_date"],
                    category="market_internals",
                    market="SSE",
                    source="Shanghai Stock Exchange",
                    source_url=SSE_URL,
                    frequency="daily",
                    values=values,
                    units={
                        "turnover": "CNY",
                        "volume": "shares",
                        "turnover_rate": "ratio",
                        "listed_count": "count",
                    },
                ),
                raw_text=text,
                source="Shanghai Stock Exchange",
                source_url=SSE_URL,
            )
        except Exception as error:
            failures.append(f"{candidate}: {error}")
    raise ValueError("No recent SSE daily overview: " + "; ".join(failures))


def _szse_provider(session: requests.Session, end: date) -> ProviderResult:
    failures = []
    for lag in range(8):
        candidate = end - timedelta(days=lag)
        try:
            text = _text(
                session,
                SZSE_URL,
                params={
                    "SHOWTYPE": "JSON",
                    "CATALOGID": "1803_after",
                    "TABKEY": "tab1",
                    "txtQueryDate": candidate.isoformat(),
                },
                headers={
                    "Referer": "https://www.szse.cn/market/stock/indicator/index.html"
                },
            )
            observation = parse_szse_daily_overview(text)
            ensure_fresh_market_date(
                observation["as_of_date"], expected_end=end, max_lag_days=4
            )
            values = {
                key: value
                for key, value in observation.items()
                if key not in {"as_of_date", "market"}
            }
            return ProviderResult(
                category="market_internals",
                rows=metric_rows(
                    as_of_date=observation["as_of_date"],
                    category="market_internals",
                    market="SZSE",
                    source="Shenzhen Stock Exchange",
                    source_url=SZSE_URL,
                    frequency="daily",
                    values=values,
                    units={
                        "turnover": "CNY",
                        "turnover_rate": "ratio",
                        "listed_companies": "count",
                        "listed_securities": "count",
                    },
                ),
                raw_text=text,
                source="Shenzhen Stock Exchange",
                source_url=SZSE_URL,
            )
        except Exception as error:
            failures.append(f"{candidate}: {error}")
    raise ValueError("No recent SZSE daily overview: " + "; ".join(failures))
    if not url:
        return not_configured_result(
            category="market_internals",
            source=market,
            source_url=source_url,
            notes=(
                f"Set CAPITAL_WEEKLY_{market}_OVERVIEW_URL to the official "
                "daily-overview JSON endpoint."
            ),
        )
    text = _text(session, url)
    observation = parser(text)
    ensure_fresh_market_date(observation["as_of_date"], expected_end=end)
    values = {
        key: value
        for key, value in observation.items()
        if key not in {"as_of_date", "market"}
    }
    units = {
        "turnover": "CNY",
        "volume": "shares",
        "advancers": "count",
        "decliners": "count",
        "unchanged": "count",
        "limit_up": "count",
        "limit_down": "count",
        "advance_ratio": "ratio",
        "advance_decline": "count",
    }
    return ProviderResult(
        category="market_internals",
        rows=metric_rows(
            as_of_date=observation["as_of_date"],
            category="market_internals",
            market=market,
            source=market,
            source_url=url,
            frequency="daily",
            values=values,
            units=units,
        ),
        raw_text=text,
        source=market,
        source_url=url,
    )


def build_default_providers(
    *,
    start: date,
    end: date,
    data_dir: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
    session: requests.Session | None = None,
    yahoo_downloader: Callable[..., Any] | None = None,
) -> dict[str, ContextProvider]:
    if end < start:
        raise ValueError("Report end must not precede start")
    settings = dict(os.environ if environ is None else environ)
    client = session or _session()
    if data_dir is None:
        cftc_rows = load_config_rows("context.cftc_contracts")
        watchlist_rows = load_config_rows("context.company_watchlist")
        eia_config = load_config_rows("context.eia_series")
        financial_config = load_config_rows("context.financial_conditions")
        yahoo_rows = load_config_rows("context.yahoo_volatility")
    else:
        root = Path(data_dir)
        cftc_rows = _config(root / "capital_weekly_cftc_contracts.csv")
        watchlist_rows = _config(root / "capital_weekly_company_watchlist.csv")
        eia_config = _config(root / "capital_weekly_eia_series.csv")
        financial_config = _config(root / "capital_weekly_financial_conditions.csv")
        yahoo_rows = _config(root / "capital_weekly_yahoo_volatility.csv")
    cftc_config = {
        row["contract_code"]: row["metric_code"] for row in cftc_rows
    }
    watchlist = load_company_watchlist(watchlist_rows)
    yahoo_volatility_config = load_yahoo_volatility_config(yahoo_rows)
    yahoo_download = yahoo_downloader or _default_yahoo_download

    fetchers: dict[str, Callable[[], ProviderResult]] = {
        "bls_calendar": lambda: _bls_provider(client, start, end),
        "federal_reserve_calendar": lambda: _fed_provider(client, start, end),
        "census_calendar": lambda: _event_provider(
            client,
            url=CENSUS_URL,
            parser=parse_census_calendar,
            start=start,
            end=end,
            source="U.S. Census Bureau",
        ),
        "nasdaq_market_summary": lambda: _nasdaq_provider(client, start, end),
        "cftc_tff": lambda: _cftc_provider(
            client, start, end, cftc_config
        ),
        "finra_margin": lambda: _finra_provider(client, end),
        "sec_company_events": lambda: _sec_provider(
            client,
            start,
            end,
            watchlist,
            settings.get("SEC_USER_AGENT"),
        ),
        "eia_commodities": lambda: _eia_provider(
            client, end, eia_config, settings.get("EIA_API_KEY")
        ),
        "fred_financial_conditions": lambda: _fred_provider(
            client, end, financial_config
        ),
        "yahoo_volatility_signals": lambda: _yahoo_volatility_provider(
            yahoo_download, end, yahoo_volatility_config
        ),
        "hkex_microstructure": lambda: _hkex_provider(client, end),
        "sse_microstructure": lambda: _sse_provider(client, end),
        "szse_microstructure": lambda: _szse_provider(client, end),
    }
    definitions = {
        "bls_calendar": ("events", "event", "required"),
        "federal_reserve_calendar": ("events", "event", "required"),
        "census_calendar": ("events", "event", "required"),
        "nasdaq_market_summary": ("market_internals", "daily", "required"),
        "cftc_tff": ("positioning_flows", "weekly", "required"),
        "finra_margin": ("positioning_flows", "monthly", "required"),
        "sec_company_events": ("company_events", "event", "optional"),
        "eia_commodities": ("commodity_fundamentals", "weekly", "optional"),
        "fred_financial_conditions": (
            "financial_conditions",
            "daily",
            "optional",
        ),
        "yahoo_volatility_signals": (
            "financial_conditions",
            "daily",
            "optional",
        ),
        "hkex_microstructure": ("market_internals", "daily", "required"),
        "sse_microstructure": ("market_internals", "daily", "required"),
        "szse_microstructure": ("market_internals", "daily", "required"),
    }
    return {
        name: ContextProvider(
            spec=ProviderSpec(
                name=name,
                category=category,
                source_tier="public",
                requiredness=requiredness,
                provider_version="1.0.0",
                schema_version="context-metric-v1",
                frequency=frequency,
                freshness_days=7 if name == "yahoo_volatility_signals" else None,
            ),
            fetch=fetchers[name],
        )
        for name, (category, frequency, requiredness) in definitions.items()
    }


__all__ = [
    "build_default_providers",
    "metric_rows",
    "not_configured_result",
]
