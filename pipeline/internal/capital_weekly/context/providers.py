from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import zipfile
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pipeline.internal.common import load_config_rows, sanitize_audit_text
from pipeline.internal.capital_weekly.official_http import (
    OfficialHttpError,
    OfficialHttpPolicy,
    official_get,
)

try:
    import yfinance as yf
except ImportError:
    yf = None

from .provider_contracts import (
    ContextProvider,
    PointInTimeUnavailable,
    ProviderResult,
    ProviderPhaseError,
    ProviderSpec,
    filter_known_as_of,
)
from .common import COMMODITY_METRIC_FIELDS
from .commodities import (
    EIA_SOURCE_URL,
    calculate_weekly_change,
    eia_not_configured_result,
    parse_eia_series,
)
from .eia_commodities import (
    CommodityHttpSpec,
    EiaBatchError,
    EIA_PROVIDERS,
    build_eia_batch_specs,
    eia_metadata_facet_ids,
    eia_response_total,
    fetch_eia_batches,
    latest_and_changes,
    load_commodity_http_policies,
    parse_eia_metric_series,
    period_date,
    validate_eia_spec,
)
from .company_events import load_company_watchlist, parse_sec_submissions
from .capital_markets import (
    build_guidance_proxy_rows,
    build_hkex_ipo_rows,
    build_ma_rows,
    build_sec_ipo_rows,
    parse_hkex_listing_table,
    parse_sec_master_index,
)
from .economic_sources import (
    build_bea_provider,
    build_bls_provider,
    build_census_provider,
    build_census_durable_goods_provider,
    build_census_housing_provider,
)
from .events import (
    parse_bls_calendar,
    parse_census_calendar,
    parse_fed_calendar,
    parse_fomc_calendar,
    parse_fomc_statement,
    select_event_window,
)
from .financial_conditions import (
    calculate_financial_conditions,
    parse_fred_components_csv,
)
from .fundamentals import build_company_fundamentals
from .market_internals import (
    calculate_registered_universe_state,
    calculate_style_relative_windows,
    extract_yahoo_market_history,
    parse_nasdaq_market_summary,
    serialize_yahoo_market_history,
)
from .metal_inventories import (
    comex_schema_signature,
    parse_comex_stocks,
    parse_usgs_mcs_pdf,
)
from .microstructure import (
    ensure_fresh_market_date,
    parse_hkex_market_highlights,
    parse_hkex_short_selling,
    parse_sse_daily_overview,
    parse_szse_daily_overview,
)
from .positioning import (
    DISAGGREGATED_PARTICIPANTS,
    parse_cftc_disaggregated_csv,
    parse_cftc_tff_csv,
    parse_finra_margin_table,
)
from .public_flows import parse_hkex_stock_connect_daily, parse_ishares_fund_page
from .usda_commodities import (
    calculate_stock_to_use,
    parse_esr_records,
    parse_psd_records,
    parse_usda_lookup,
)
from .volatility import (
    calculate_yahoo_volatility_metrics,
    extract_yahoo_close_histories,
    load_yahoo_volatility_config,
    serialize_yahoo_close_histories,
)


BLS_URL = "https://www.bls.gov/schedule/{year}/home.htm"
FED_URL = "https://www.federalreserve.gov/newsevents/calendar.htm"
FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
CENSUS_URL = "https://www.census.gov/economic-indicators/calendar-listview.html"
ISM_URL = (
    "https://www.ismworld.org/supply-management-news-and-reports/"
    "reports/ism-pmi-reports/"
)
NASDAQ_URL = "https://www.nasdaqtrader.com/Trader.aspx?id=DailyMarketSummary"
FINRA_URL = "https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
CFTC_TFF_URL = "https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip"
CFTC_DISAGGREGATED_URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.csv"
SEC_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_DAILY_INDEX_URL = (
    "https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{quarter}/"
    "master.{stamp}.idx"
)
HKEX_NEW_LISTINGS_URL = "https://www.hkex.com.hk/Listing/IPO/Newly-Listed-Companies"
HKEX_URL = "https://www.hkex.com.hk/eng/stat/smstat/dayquot/d{stamp}e.htm"
HKEX_STOCK_CONNECT_URL = (
    "https://www.hkex.com.hk/eng/csm/DailyStat/"
    "data_tab_daily_{stamp}e.js"
)
ISHARES_IVV_URL = (
    "https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf"
)
SSE_URL = "https://query.sse.com.cn/commonQuery.do"
SZSE_URL = "https://www.szse.cn/api/report/ShowReport/data"
YAHOO_FINANCE_URL = "https://finance.yahoo.com/"
YAHOO_VOLATILITY_SOURCE = "Yahoo Finance (Cboe indices)"
COMEX_COPPER_STOCKS_URL = (
    "https://www.cmegroup.com/delivery_reports/Copper_Stocks.xls"
)
COMEX_GOLD_STOCKS_URL = (
    "https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls"
)
USGS_COPPER_MCS_URL = (
    "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-copper.pdf"
)
USGS_GOLD_MCS_URL = (
    "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-gold.pdf"
)
USDA_FAS_API_URL = "https://api.fas.usda.gov"
USDA_FAS_PORTAL_URL = "https://apps.fas.usda.gov/opendatawebV2/"
CHICAGO = ZoneInfo("America/Chicago")
EASTERN = ZoneInfo("America/New_York")


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


def _official_bytes(
    session: requests.Session,
    url: str,
    policy: OfficialHttpPolicy,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    audit_secrets: tuple[str, ...] = (),
) -> tuple[bytes, int]:
    response = official_get(
        session,
        url,
        policy=policy,
        params=params,
        headers=headers,
        audit_secrets=audit_secrets,
    )
    return response.body, response.trace.attempts


def _official_text(
    session: requests.Session,
    url: str,
    policy: OfficialHttpPolicy,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    audit_secrets: tuple[str, ...] = (),
) -> tuple[str, int]:
    body, attempts = _official_bytes(
        session,
        url,
        policy,
        params=params,
        headers=headers,
        audit_secrets=audit_secrets,
    )
    try:
        return body.decode("utf-8-sig"), attempts
    except UnicodeDecodeError as error:
        raise ValueError(f"Official response is not UTF-8 text: {url}") from error


def _official_provider_result(fetch: Callable[[], ProviderResult]) -> ProviderResult:
    try:
        return fetch()
    except OfficialHttpError as error:
        failure_phase = "raw" if error.phase == "schema" else "retrieve"
        raise ProviderPhaseError(
            error.code,
            failure_phase,
            error.safe_message,
            error.attempts,
        ) from None


def _config(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _validated_breadth_universe(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    symbols = [str(row.get("symbol", "")).strip() for row in rows]
    if any(not symbol for symbol in symbols) or len(set(symbols)) != len(symbols):
        raise ValueError("breadth symbols must be nonblank and unique")
    invalid_enabled = sorted(
        {
            str(row.get("enabled", "")).strip()
            for row in rows
            if str(row.get("enabled", "")).strip() not in {"0", "1"}
        }
    )
    if invalid_enabled:
        raise ValueError(
            "Breadth config enabled values must be 0 or 1: "
            + ", ".join(invalid_enabled)
        )
    return [dict(row) for row in rows]


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
    metadata: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    commodity_metadata = {
        field: (metadata or {}).get(field)
        for field in COMMODITY_METRIC_FIELDS
    }
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
            **commodity_metadata,
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


def _usda_json_value(value: Any, field: str, expected_type: type) -> Any:
    if isinstance(value, expected_type):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(f"USDA config {field} must be valid JSON") from error
        if isinstance(parsed, expected_type):
            return parsed
    raise ValueError(f"USDA config {field} must be a {expected_type.__name__}")


def _validated_usda_config(
    rows: list[dict[str, Any]],
    *,
    provider: str,
) -> list[dict[str, Any]]:
    fields = (
        (
            "commodity_code",
            "commodity_family",
            "commodity_name",
            "country_names",
            "market_year_offsets",
            "attributes",
            "unit_names",
        )
        if provider == "usda_psd"
        else (
            "commodity_code",
            "commodity_family",
            "commodity_name",
            "route",
            "market_year_offsets",
            "unit_name",
        )
    )
    fields = (*fields, "freshness_days")
    if not rows:
        raise ValueError(f"{provider} requires a configured eligible subset")
    validated = []
    seen = set()
    for raw in rows:
        item = dict(raw)
        missing = [field for field in fields if item.get(field) in (None, "")]
        if missing:
            raise ValueError(f"{provider} config missing: {', '.join(missing)}")
        code = str(item["commodity_code"]).strip()
        family = str(item["commodity_family"]).strip()
        if family not in {"grains_oilseeds", "softs", "livestock"}:
            raise ValueError(f"{provider} unsupported agriculture family: {family}")
        if code in seen:
            raise ValueError(f"{provider} duplicate commodity_code: {code}")
        seen.add(code)
        item["commodity_code"] = code
        item["commodity_family"] = family
        item["commodity_name"] = str(item["commodity_name"]).strip()
        try:
            freshness_days = int(str(item["freshness_days"]).strip())
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{provider} freshness_days must be a positive integer"
            ) from error
        if freshness_days <= 0:
            raise ValueError(f"{provider} freshness_days must be a positive integer")
        item["freshness_days"] = freshness_days
        offsets = _usda_json_value(
            item["market_year_offsets"], "market_year_offsets", list
        )
        try:
            normalized_offsets = [int(value) for value in offsets]
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{provider} market_year_offsets must contain integers"
            ) from error
        if (
            not normalized_offsets
            or len(set(normalized_offsets)) != len(normalized_offsets)
            or any(abs(value) > 5 for value in normalized_offsets)
        ):
            raise ValueError(f"{provider} market_year_offsets are invalid")
        item["market_year_offsets"] = normalized_offsets
        if provider == "usda_psd":
            countries = _usda_json_value(item["country_names"], "country_names", list)
            units = _usda_json_value(item["unit_names"], "unit_names", list)
            attributes = _usda_json_value(item["attributes"], "attributes", dict)
            if (
                not countries
                or "World" not in countries
                or len(countries) > 4
                or len(set(countries)) != len(countries)
                or not units
                or len(set(units)) != len(units)
                or not attributes
            ):
                raise ValueError(f"{provider} countries, attributes, or units are invalid")
            required_attributes = {"production", "imports", "exports", "domestic_use"}
            if not required_attributes <= set(attributes):
                raise ValueError(
                    f"{provider} {code} missing core configured attributes"
                )
            item["country_names"] = [str(value).strip() for value in countries]
            item["unit_names"] = [str(value).strip() for value in units]
            item["attributes"] = {
                str(name).strip(): str(display).strip()
                for name, display in attributes.items()
            }
        else:
            item["route"] = str(item["route"]).strip()
            if item["route"] != "allCountries":
                raise ValueError("usda_esr route must be allCountries")
            item["unit_name"] = str(item["unit_name"]).strip()
        validated.append(item)
    return validated


def _usda_get_json(
    session: requests.Session,
    path: str,
    api_key: str,
    policy: OfficialHttpPolicy,
    trace: dict[str, int],
) -> tuple[str, Any, bytes, int]:
    url = f"{USDA_FAS_API_URL}{path}"
    try:
        content, attempts = _official_bytes(
            session,
            url,
            policy,
            headers={"API_KEY": api_key, "Accept": "application/json"},
            audit_secrets=(api_key,),
        )
        trace["attempts"] = max(trace["attempts"], attempts)
        trace["requests"] += 1
        payload = json.loads(content.decode("utf-8"))
    except OfficialHttpError:
        raise
    except Exception as error:
        safe = sanitize_audit_text(error, secrets=(api_key,))
        raise ValueError(safe) from None
    if not isinstance(payload, (list, dict)):
        raise ValueError(f"USDA endpoint returned non-record JSON: {path}")
    return url, payload, content, attempts


def _usda_raw_archive(responses: list[tuple[str, bytes]]) -> bytes:
    """Package exact USDA response bytes without normalized record rewrites."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for index, (url, content) in enumerate(responses, start=1):
            path = urlparse(url).path.strip("/") or "root"
            safe_path = re.sub(r"[^A-Za-z0-9._-]+", "_", path)
            info = zipfile.ZipInfo(f"{index:03d}_{safe_path}.json")
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, content)
    return buffer.getvalue()


def _explicit_vintage_records(
    records: list[Any],
    *,
    selected_release: str,
    label: str,
) -> list[dict[str, Any]]:
    try:
        selected_at = datetime.fromisoformat(selected_release.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("USDA selected release must be an ISO timestamp") from error
    matching = []
    for raw_record in records:
        if not isinstance(raw_record, Mapping):
            raise ValueError(f"USDA {label} data record must be an object")
        raw_vintage = str(raw_record.get("releaseDate") or "").strip()
        if not raw_vintage:
            raise PointInTimeUnavailable(
                f"USDA {label} row lacks an explicit record vintage"
            )
        try:
            record_at = datetime.fromisoformat(raw_vintage.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(
                f"USDA {label} record releaseDate must be an ISO timestamp"
            ) from error
        if record_at.tzinfo is None or record_at.utcoffset() is None:
            raise ValueError(
                f"USDA {label} record releaseDate must include a UTC offset"
            )
        if record_at == selected_at:
            matching.append(dict(raw_record))
    if not matching:
        raise PointInTimeUnavailable(
            f"USDA {label} explicit record vintage does not match latest eligible release"
        )
    return matching


def _usda_point_in_time_unavailable(
    *,
    label: str,
    raw_responses: list[tuple[str, bytes]],
    detail: str,
    attempts: int,
) -> ProviderResult:
    return ProviderResult(
        category="commodity_fundamentals",
        rows=[],
        raw_text=_usda_raw_archive(raw_responses),
        source="USDA Foreign Agricultural Service",
        source_url=USDA_FAS_PORTAL_URL,
        status="POINT_IN_TIME_UNAVAILABLE",
        notes=f"{label} point-in-time unavailable: {detail}",
        attempts=attempts,
    )


def _psd_measurement_kind(attribute: str) -> str:
    if attribute in {"beginning_stocks", "ending_stocks"}:
        return "inventory"
    if attribute == "production":
        return "supply"
    if attribute in {"imports", "exports"}:
        return "trade"
    if attribute in {"feed_use", "industrial_use", "crush", "domestic_use"}:
        return "demand"
    if attribute == "stock_to_use":
        return "structural"
    raise ValueError(f"Unsupported USDA PSD attribute semantic: {attribute}")


def _exact_lookup_code(lookup: Mapping[str, str], display: str, kind: str) -> str:
    if display not in lookup:
        raise ValueError(f"USDA {kind} lookup has no exact match for {display!r}")
    return lookup[display]


def _eligible_release(
    payload: Any,
    *,
    commodity_code: str,
    market_year: int,
    cutoff: datetime,
) -> str:
    matching: list[tuple[datetime, str]] = []
    records = payload if isinstance(payload, list) else payload.get("data", [])
    if not isinstance(records, list):
        raise ValueError("USDA release payload must contain records")
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("USDA release record must be an object")
        if str(record.get("commodityCode") or "") != commodity_code:
            continue
        try:
            record_year = int(record.get("marketYear"))
        except (TypeError, ValueError) as error:
            raise ValueError("USDA release marketYear must be an integer") from error
        if record_year != market_year:
            continue
        raw = str(record.get("releaseDate") or "").strip()
        try:
            released_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("USDA releaseDate must be an ISO timestamp") from error
        if released_at.tzinfo is None or released_at.utcoffset() is None:
            raise ValueError("USDA releaseDate must include a UTC offset")
        matching.append((released_at, released_at.isoformat()))
    if not matching:
        raise ValueError(
            f"USDA release lookup missing commodity {commodity_code} market year {market_year}"
        )
    hong_kong = ZoneInfo("Asia/Hong_Kong")
    eligible = [
        item
        for item in matching
        if item[0].astimezone(hong_kong) <= cutoff.astimezone(hong_kong)
    ]
    if not eligible:
        raise ValueError(
            f"USDA release lookup has no eligible vintage for "
            f"{commodity_code} {market_year}"
        )
    return max(eligible, key=lambda item: item[0])[1]


def _release_is_fresh(
    release_timestamp: str,
    *,
    cutoff: datetime,
    freshness_days: int,
) -> bool:
    released_at = datetime.fromisoformat(release_timestamp.replace("Z", "+00:00"))
    if released_at.tzinfo is None or released_at.utcoffset() is None:
        raise ValueError("USDA releaseDate must include a UTC offset")
    zone = ZoneInfo("Asia/Hong_Kong")
    return (
        cutoff.astimezone(zone).date() - released_at.astimezone(zone).date()
    ).days <= freshness_days


def _usda_not_configured(provider: str) -> ProviderResult:
    label = "PSD" if provider == "usda_psd" else "ESR"
    return not_configured_result(
        category="commodity_fundamentals",
        source="USDA Foreign Agricultural Service",
        source_url=USDA_FAS_PORTAL_URL,
        notes=(
            f"{label} capability NOT_CONFIGURED: USDA_API_KEY is absent; "
            "obtain a free API key through API.Data.Gov."
        ),
    )


def _usda_psd_provider(
    session: requests.Session,
    end: date,
    config: list[dict[str, Any]],
    api_key: str | None,
    http: CommodityHttpSpec,
) -> ProviderResult:
    trace = {"attempts": 1, "requests": 0}
    try:
        return _usda_psd_provider_impl(
            session, end, config, api_key, http, trace
        )
    except (OfficialHttpError, ProviderPhaseError):
        raise
    except ValueError as error:
        phase = "parse" if trace["requests"] else "config"
        raise ProviderPhaseError(
            f"USDA_PSD_{phase.upper()}_FAILED",
            phase,
            sanitize_audit_text(error, secrets=(api_key,) if api_key else ()),
            trace["attempts"],
        ) from error


def _usda_psd_provider_impl(
    session: requests.Session,
    end: date,
    config: list[dict[str, Any]],
    api_key: str | None,
    http: CommodityHttpSpec,
    trace: dict[str, int],
) -> ProviderResult:
    if not api_key:
        return _usda_not_configured("usda_psd")
    specs = _validated_usda_config(config, provider="usda_psd")
    raw_responses: list[tuple[str, bytes]] = []
    transport_attempts = 1

    def fetch(path: str) -> tuple[str, Any]:
        nonlocal transport_attempts
        url, payload, content, attempts = _usda_get_json(
            session, path, api_key, http.policy, trace
        )
        transport_attempts = max(transport_attempts, attempts)
        raw_responses.append((url, content))
        return url, payload

    lookup_paths = {
        "commodities": ("/api/psd/commodities", ("commodityName", "commodityCode")),
        "attributes": (
            "/api/psd/commodityAttributes",
            ("attributeName", "attributeId"),
        ),
        "countries": ("/api/psd/countries", ("countryName", "countryCode")),
        "units": ("/api/psd/unitsOfMeasure", ("unitDescription", "unitId")),
    }
    lookups: dict[str, dict[str, str]] = {}
    for kind, (path, fields) in lookup_paths.items():
        _url, payload = fetch(path)
        lookups[kind] = parse_usda_lookup(payload, fields)
    cutoff = datetime.combine(end, time.max, tzinfo=ZoneInfo("Asia/Hong_Kong"))
    rows: list[dict[str, Any]] = []
    for config_item in specs:
        api_commodity = _exact_lookup_code(
            lookups["commodities"], config_item["commodity_name"], "commodity"
        )
        attributes = {
            name: _exact_lookup_code(lookups["attributes"], display, "attribute")
            for name, display in config_item["attributes"].items()
        }
        units_by_code = {
            _exact_lookup_code(lookups["units"], display, "unit"): display
            for display in config_item["unit_names"]
        }
        countries = {
            display: _exact_lookup_code(lookups["countries"], display, "country")
            for display in config_item["country_names"]
        }
        release_path = f"/api/psd/commodity/{api_commodity}/dataReleaseDates"
        _release_url, release_payload = fetch(release_path)
        for market_year in (
            end.year + offset for offset in config_item["market_year_offsets"]
        ):
            release_date = _eligible_release(
                release_payload,
                commodity_code=api_commodity,
                market_year=market_year,
                cutoff=cutoff,
            )
            if not _release_is_fresh(
                release_date,
                cutoff=cutoff,
                freshness_days=config_item["freshness_days"],
            ):
                return _usda_point_in_time_unavailable(
                    label="PSD",
                    raw_responses=raw_responses,
                    detail=(
                        f"latest eligible release is older than configured "
                        f"{config_item['freshness_days']} calendar days"
                    ),
                    attempts=transport_attempts,
                )
            for country_name, country_code in countries.items():
                if country_name == "World":
                    data_path = (
                        f"/api/psd/commodity/{api_commodity}/world/year/{market_year}"
                    )
                else:
                    data_path = (
                        f"/api/psd/commodity/{api_commodity}/country/"
                        f"{country_code}/year/{market_year}"
                    )
                source_url, payload = fetch(data_path)
                data_records = payload if isinstance(payload, list) else payload.get("data", [])
                if not isinstance(data_records, list):
                    raise ValueError("USDA PSD data payload must contain records")
                try:
                    vintage_records = _explicit_vintage_records(
                        data_records,
                        selected_release=release_date,
                        label="PSD",
                    )
                except PointInTimeUnavailable as error:
                    return _usda_point_in_time_unavailable(
                        label="PSD",
                        raw_responses=raw_responses,
                        detail=str(error),
                        attempts=transport_attempts,
                    )
                parsed = parse_psd_records(
                    vintage_records,
                    {
                        "commodity_code": config_item["commodity_code"],
                        "commodity_family": config_item["commodity_family"],
                        "commodity_api_code": api_commodity,
                        "country_code": country_code,
                        "country_name": country_name,
                        "market_year": market_year,
                        "attributes": attributes,
                        "units": units_by_code,
                    },
                    cutoff,
                )
                if not parsed:
                    raise ValueError(
                        f"USDA PSD has no eligible rows for {api_commodity} "
                        f"{country_code} {market_year}"
                    )
                ratio = calculate_stock_to_use(parsed)
                if ratio is not None:
                    parsed.append(ratio)
                for record in parsed:
                    metric_code = (
                        "usda_psd_"
                        f"{record['commodity_code'].lower()}_"
                        f"{record['country_code'].lower()}_"
                        f"{record['market_year']}_{record['attribute']}"
                    )
                    rows.extend(metric_rows(
                        as_of_date=date.fromisoformat(record["release_date"][:10]),
                        category="commodity_fundamentals",
                        market=record["country_name"],
                        source="USDA Foreign Agricultural Service",
                        source_url=source_url,
                        frequency="monthly",
                        values={metric_code: record["value"]},
                        units={metric_code: record["unit"]},
                        names={metric_code: record["attribute"].replace("_", " ")},
                        metadata={
                            "commodity_code": record["commodity_code"],
                            "commodity_family": record["commodity_family"],
                            "metric_role": "physical_fundamental",
                            "measurement_kind": _psd_measurement_kind(
                                record["attribute"]
                            ),
                            "participant_class": None,
                            "known_as_of": record["release_date"],
                            "reference_period": str(record["market_year"]),
                        },
                    ))
    return ProviderResult(
        category="commodity_fundamentals",
        rows=rows,
        raw_text=_usda_raw_archive(raw_responses),
        source="USDA Foreign Agricultural Service",
        source_url=USDA_FAS_PORTAL_URL,
        notes=(
            "PSD capability ACTIVE; official lookup identities resolved exactly; "
            "source-native units preserved; NASS cattle/hog inventory detail unavailable."
        ),
        attempts=transport_attempts,
    )


def _usda_esr_provider(
    session: requests.Session,
    end: date,
    config: list[dict[str, Any]],
    api_key: str | None,
    http: CommodityHttpSpec,
) -> ProviderResult:
    trace = {"attempts": 1, "requests": 0}
    try:
        return _usda_esr_provider_impl(
            session, end, config, api_key, http, trace
        )
    except (OfficialHttpError, ProviderPhaseError):
        raise
    except ValueError as error:
        phase = "parse" if trace["requests"] else "config"
        raise ProviderPhaseError(
            f"USDA_ESR_{phase.upper()}_FAILED",
            phase,
            sanitize_audit_text(error, secrets=(api_key,) if api_key else ()),
            trace["attempts"],
        ) from error


def _usda_esr_provider_impl(
    session: requests.Session,
    end: date,
    config: list[dict[str, Any]],
    api_key: str | None,
    http: CommodityHttpSpec,
    trace: dict[str, int],
) -> ProviderResult:
    if not api_key:
        return _usda_not_configured("usda_esr")
    specs = _validated_usda_config(config, provider="usda_esr")
    raw_responses: list[tuple[str, bytes]] = []
    transport_attempts = 1

    def fetch(path: str) -> tuple[str, Any]:
        nonlocal transport_attempts
        url, payload, content, attempts = _usda_get_json(
            session, path, api_key, http.policy, trace
        )
        transport_attempts = max(transport_attempts, attempts)
        raw_responses.append((url, content))
        return url, payload

    lookup_paths = {
        "commodities": ("/api/esr/commodities", ("commodityName", "commodityCode")),
        "countries": ("/api/esr/countries", ("countryName", "countryCode")),
        "units": ("/api/esr/unitsOfMeasure", ("unitNames", "unitId")),
    }
    lookups: dict[str, dict[str, str]] = {}
    for kind, (path, fields) in lookup_paths.items():
        _url, payload = fetch(path)
        lookups[kind] = parse_usda_lookup(payload, fields)
    _release_url, release_payload = fetch("/api/esr/datareleasedates")
    cutoff = datetime.combine(end, time.max, tzinfo=ZoneInfo("Asia/Hong_Kong"))
    rows: list[dict[str, Any]] = []
    for config_item in specs:
        api_commodity = _exact_lookup_code(
            lookups["commodities"], config_item["commodity_name"], "commodity"
        )
        unit_code = _exact_lookup_code(
            lookups["units"], config_item["unit_name"], "unit"
        )
        official_country_codes = frozenset(lookups["countries"].values())
        for market_year in (
            end.year + offset for offset in config_item["market_year_offsets"]
        ):
            release_date = _eligible_release(
                release_payload,
                commodity_code=api_commodity,
                market_year=market_year,
                cutoff=cutoff,
            )
            if not _release_is_fresh(
                release_date,
                cutoff=cutoff,
                freshness_days=config_item["freshness_days"],
            ):
                return _usda_point_in_time_unavailable(
                    label="ESR",
                    raw_responses=raw_responses,
                    detail=(
                        f"latest eligible release is older than configured "
                        f"{config_item['freshness_days']} calendar days"
                    ),
                    attempts=transport_attempts,
                )
            data_path = (
                f"/api/esr/exports/commodityCode/{api_commodity}/"
                f"allCountries/marketYear/{market_year}"
            )
            source_url, payload = fetch(data_path)
            data_records = payload if isinstance(payload, list) else payload.get("data", [])
            if not isinstance(data_records, list):
                raise ValueError("USDA ESR data payload must contain records")
            try:
                vintage_records = _explicit_vintage_records(
                    data_records,
                    selected_release=release_date,
                    label="ESR",
                )
            except PointInTimeUnavailable as error:
                return _usda_point_in_time_unavailable(
                    label="ESR",
                    raw_responses=raw_responses,
                    detail=str(error),
                    attempts=transport_attempts,
                )
            vintage_records = [
                {
                    **record,
                    "marketYear": record.get("marketYear")
                    if record.get("marketYear") is not None
                    else market_year,
                }
                for record in vintage_records
            ]
            parsed = parse_esr_records(
                vintage_records,
                {
                    "commodity_code": config_item["commodity_code"],
                    "commodity_family": config_item["commodity_family"],
                    "commodity_api_code": api_commodity,
                    "country_name": "All destinations",
                    "aggregate_all_countries": True,
                    "market_year": market_year,
                    "unit_code": unit_code,
                    "unit": config_item["unit_name"],
                    "allowed_country_codes": official_country_codes,
                },
                cutoff,
            )
            if not parsed:
                raise ValueError(
                    f"USDA ESR has no eligible rows for {api_commodity} {market_year}"
                )
            for record in parsed:
                metric_code = (
                    "usda_esr_"
                    f"{record['commodity_code'].lower()}_"
                    f"{record['market_year']}_{record['metric']}"
                )
                rows.extend(metric_rows(
                    as_of_date=date.fromisoformat(record["week_ending_date"]),
                    category="commodity_fundamentals",
                    market="United States export sales (all destinations)",
                    source="USDA Foreign Agricultural Service",
                    source_url=source_url,
                    frequency="weekly",
                    values={metric_code: record["value"]},
                    units={metric_code: record["unit"]},
                    names={metric_code: record["metric"].replace("_", " ")},
                    metadata={
                        "commodity_code": record["commodity_code"],
                        "commodity_family": record["commodity_family"],
                        "metric_role": "physical_fundamental",
                        "measurement_kind": "trade",
                        "participant_class": None,
                        "known_as_of": record["release_date"],
                        "reference_period": record["week_ending_date"],
                    },
                ))
    return ProviderResult(
        category="commodity_fundamentals",
        rows=rows,
        raw_text=_usda_raw_archive(raw_responses),
        source="USDA Foreign Agricultural Service",
        source_url=USDA_FAS_PORTAL_URL,
        notes=(
            "ESR capability ACTIVE; only exact lookup-eligible commodities emitted; "
            "source-native units preserved."
        ),
        attempts=transport_attempts,
    )


def _metal_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    item = dict(spec)
    provider = str(item.get("provider") or "").strip()
    source_url = str(item.get("source_url") or "").strip()
    parsed_url = urlparse(source_url)
    if provider.startswith("comex_"):
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != "www.cmegroup.com"
            or not parsed_url.path.startswith("/delivery_reports/")
        ):
            raise ValueError(f"{provider} requires an official CME delivery report URL")
        required = (
            "freshness_basis",
            "holiday_calendar",
            "expected_sheet",
            "commodity_title",
            "expected_unit",
            "location_header",
            "registered_total_label",
            "eligible_total_label",
            "combined_total_label",
        )
    elif provider.startswith("usgs_"):
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != "pubs.usgs.gov"
            or not parsed_url.path.startswith("/periodicals/mcs")
            or not parsed_url.path.endswith(".pdf")
        ):
            raise ValueError(f"{provider} requires an official USGS MCS PDF URL")
        required = (
            "freshness_basis",
            "holiday_calendar",
            "commodity_title",
            "expected_unit",
            "table_kind",
            "reference_year",
            "publication_date",
            "publication_month",
        )
    else:
        raise ValueError(f"Unsupported metals provider: {provider or 'blank'}")
    common = (
        "source",
        "commodity_code",
        "commodity_family",
        "market",
        "frequency",
        "freshness_days",
        "limitation_note",
    )
    missing = [
        key
        for key in (*common, *required)
        if not str(item.get(key) or "").strip()
    ]
    if missing:
        raise ValueError(f"{provider} metals config missing: {', '.join(missing)}")
    freshness_basis = str(item["freshness_basis"]).strip()
    holiday_calendar = str(item["holiday_calendar"]).strip()
    if provider.startswith("comex_"):
        if freshness_basis != "trading_days" or holiday_calendar != "CME_US":
            raise ValueError(f"{provider} requires CME_US trading-day freshness")
    elif freshness_basis != "calendar_days" or holiday_calendar != "NONE":
        raise ValueError(
            f"{provider} requires calendar-day freshness with holiday_calendar NONE"
        )
    try:
        freshness_days = int(str(item["freshness_days"]))
    except (TypeError, ValueError) as error:
        raise ValueError(f"{provider} freshness_days must be an integer") from error
    if freshness_days <= 0:
        raise ValueError(f"{provider} freshness_days must be positive")
    item["provider"] = provider
    item["source_url"] = source_url
    item["freshness_days"] = freshness_days
    item["freshness_basis"] = freshness_basis
    item["holiday_calendar"] = holiday_calendar
    return item


def _observed_fixed_holiday(value: date) -> date:
    if value.weekday() == 5:
        return value - timedelta(days=1)
    if value.weekday() == 6:
        return value + timedelta(days=1)
    return value


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (occurrence - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    candidate = next_month - timedelta(days=1)
    return candidate - timedelta(days=(candidate.weekday() - weekday) % 7)


def _easter_sunday(year: int) -> date:
    """Gregorian Easter calculation used by the CME_US holiday calendar."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    leap_adjustment = (32 + 2 * e + 2 * i - h - k) % 7
    month_adjustment = (a + 11 * h + 22 * leap_adjustment) // 451
    month = (h + leap_adjustment - 7 * month_adjustment + 114) // 31
    day = (h + leap_adjustment - 7 * month_adjustment + 114) % 31 + 1
    return date(year, month, day)


def _cme_us_holidays(year: int) -> frozenset[date]:
    holidays = {
        _observed_fixed_holiday(date(year, 1, 1)),
        _nth_weekday(year, 1, 0, 3),
        _nth_weekday(year, 2, 0, 3),
        _easter_sunday(year) - timedelta(days=2),
        _last_weekday(year, 5, 0),
        _observed_fixed_holiday(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1),
        _nth_weekday(year, 11, 3, 4),
        _observed_fixed_holiday(date(year, 12, 25)),
    }
    if year >= 2022:
        holidays.add(_observed_fixed_holiday(date(year, 6, 19)))
    return frozenset(holidays)


def _cme_trading_days_elapsed(report_date: date, end: date) -> int:
    if report_date > end:
        return 0
    holidays = frozenset().union(
        *(_cme_us_holidays(year) for year in range(report_date.year, end.year + 2))
    )
    elapsed = 0
    candidate = report_date + timedelta(days=1)
    while candidate <= end:
        if candidate.weekday() < 5 and candidate not in holidays:
            elapsed += 1
        candidate += timedelta(days=1)
    return elapsed


def _provenance_notes(
    content: bytes,
    *,
    schema_signature: str,
    limitation_note: str,
) -> str:
    return (
        f"bytes={len(content)}; sha256={hashlib.sha256(content).hexdigest()}; "
        f"schema_signature={schema_signature}; {limitation_note}"
    )


def _unverified_provenance_notes(
    content: bytes,
    *,
    limitation_note: str,
    detail: str,
) -> str:
    signature = "unverified:parse-failed" if content else "unverified:no-content"
    notes = "; ".join(
        value for value in (limitation_note, detail) if value
    )
    return _provenance_notes(
        content,
        schema_signature=signature,
        limitation_note=notes,
    )


def _known_at_end_of_day(value: date, zone: ZoneInfo) -> str:
    return datetime.combine(value, time.max, tzinfo=zone).isoformat()


def _comex_stocks_provider(
    session: requests.Session,
    end: date,
    raw_spec: Mapping[str, Any],
    http: CommodityHttpSpec,
) -> ProviderResult:
    source = str(raw_spec.get("source") or "CME Group").strip()
    source_url = str(raw_spec.get("source_url") or "").strip()
    limitation_note = str(raw_spec.get("limitation_note") or "").strip()
    content = b""
    attempts = 1
    completed_phase = "config"
    try:
        spec = _metal_spec(raw_spec)
        content, attempts = _official_bytes(
            session, spec["source_url"], http.policy
        )
        completed_phase = "parse"
        parsed = parse_comex_stocks(content, spec)
        signature = comex_schema_signature(content, spec)
        notes = _provenance_notes(
            content,
            schema_signature=signature,
            limitation_note=str(spec["limitation_note"]),
        )
        report_dates = {row["report_date"] for row in parsed}
        if len(report_dates) != 1:
            raise ValueError("COMEX workbook has inconsistent report dates")
        report_date = report_dates.pop()
        age = _cme_trading_days_elapsed(report_date, end)
        if report_date > end or age > spec["freshness_days"]:
            cutoff_note = (
                f"No COMEX report at or before target within "
                f"{spec['freshness_days']} trading days; "
                f"report_date={report_date.isoformat()}"
            )
            return ProviderResult(
                category="commodity_fundamentals",
                rows=[],
                raw_text=content,
                source=str(spec["source"]),
                source_url=spec["source_url"],
                status="POINT_IN_TIME_UNAVAILABLE",
                notes=f"{notes}; {cutoff_note}",
                attempts=attempts,
            )
        rows: list[dict[str, Any]] = []
        for observation in parsed:
            if observation["scope"] != "exchange":
                continue
            inventory_type = str(observation["inventory_type"])
            metric_code = (
                f"{str(spec['commodity_code']).lower()}_{inventory_type}_inventory"
            )
            rows.extend(
                metric_rows(
                    as_of_date=report_date,
                    category="commodity_fundamentals",
                    market=str(spec["market"]),
                    source=str(spec["source"]),
                    source_url=spec["source_url"],
                    frequency=str(spec["frequency"]),
                    values={metric_code: observation["value"]},
                    units={metric_code: observation["unit"]},
                    names={
                        metric_code: (
                            f"COMEX {spec['commodity_family']} "
                            f"{inventory_type} inventory"
                        )
                    },
                    metadata={
                        "commodity_code": spec["commodity_code"],
                        "commodity_family": spec["commodity_family"],
                        "metric_role": "physical_fundamental",
                        "measurement_kind": "inventory",
                        "participant_class": None,
                        "known_as_of": _known_at_end_of_day(report_date, CHICAGO),
                        "reference_period": report_date.isoformat(),
                    },
                )
            )
        if len(rows) != 3:
            raise ValueError("COMEX parser did not produce all three exchange totals")
        return ProviderResult(
            category="commodity_fundamentals",
            rows=rows,
            raw_text=content,
            source=str(spec["source"]),
            source_url=spec["source_url"],
            notes=notes,
            attempts=attempts,
        )
    except Exception as error:
        if isinstance(error, OfficialHttpError):
            notes = _unverified_provenance_notes(
                content,
                limitation_note=limitation_note,
                detail=error.safe_message,
            )
            failure_phase = "raw" if error.phase == "schema" else "retrieve"
            raise ProviderPhaseError(
                error.code,
                failure_phase,
                notes,
                error.attempts,
            ) from None
        else:
            detail = str(error)
        notes = _unverified_provenance_notes(
            content,
            limitation_note=limitation_note,
            detail=detail,
        )
        return ProviderResult(
            category="commodity_fundamentals",
            rows=[],
            raw_text=content,
            source=source,
            source_url=source_url,
            status="FETCH_FAILED",
            notes=notes,
            attempts=attempts,
            completed_phase=completed_phase,
        )


def _usgs_structural_provider(
    session: requests.Session,
    end: date,
    raw_spec: Mapping[str, Any],
    http: CommodityHttpSpec,
) -> ProviderResult:
    source = str(raw_spec.get("source") or "U.S. Geological Survey").strip()
    source_url = str(raw_spec.get("source_url") or "").strip()
    limitation_note = str(raw_spec.get("limitation_note") or "").strip()
    content = b""
    attempts = 1
    completed_phase = "config"
    try:
        spec = _metal_spec(raw_spec)
        publication_date = date.fromisoformat(str(spec["publication_date"]))
        age = (end - publication_date).days
        if publication_date > end or age > spec["freshness_days"]:
            detail = (
                f"Official USGS table publication {publication_date.isoformat()} "
                f"is unavailable or more than {spec['freshness_days']} days before "
                f"target Sunday {end.isoformat()}"
            )
            return ProviderResult(
                category="commodity_fundamentals",
                rows=[],
                raw_text=b"",
                source=str(spec["source"]),
                source_url=spec["source_url"],
                status="POINT_IN_TIME_UNAVAILABLE",
                notes=_unverified_provenance_notes(
                    b"",
                    limitation_note=str(spec["limitation_note"]),
                    detail=detail,
                ),
            )
        content, attempts = _official_bytes(
            session, spec["source_url"], http.policy
        )
        completed_phase = "parse"
        parsed = parse_usgs_mcs_pdf(content, spec)
        schema_payload = {
            key: spec[key]
            for key in (
                "commodity_title",
                "expected_unit",
                "table_kind",
                "reference_year",
                "publication_month",
            )
        }
        schema_hash = hashlib.sha256(
            json.dumps(
                schema_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        notes = _provenance_notes(
            content,
            schema_signature=f"pdf-usgs-mcs-v1:sha256:{schema_hash}",
            limitation_note=str(spec["limitation_note"]),
        )
        reference_date = date(int(str(spec["reference_year"])), 12, 31)
        if reference_date > end:
            raise ValueError("USGS reference period exceeds target Sunday")
        rows: list[dict[str, Any]] = []
        names = {
            "mine_production": "world mine production",
            "reserves": "world reserves",
        }
        for observation in parsed:
            measurement = str(observation["measurement"])
            metric_code = f"usgs_{spec['commodity_family']}_world_{measurement}"
            rows.extend(
                metric_rows(
                    as_of_date=reference_date,
                    category="commodity_fundamentals",
                    market=str(spec["market"]),
                    source=str(spec["source"]),
                    source_url=spec["source_url"],
                    frequency=str(spec["frequency"]),
                    values={metric_code: observation["value"]},
                    units={metric_code: observation["unit"]},
                    names={
                        metric_code: (
                            f"USGS {spec['commodity_family']} {names[measurement]}"
                        )
                    },
                    metadata={
                        "commodity_code": spec["commodity_code"],
                        "commodity_family": spec["commodity_family"],
                        "metric_role": "physical_fundamental",
                        "measurement_kind": "structural",
                        "participant_class": None,
                        "known_as_of": _known_at_end_of_day(
                            publication_date,
                            EASTERN,
                        ),
                        "reference_period": observation["reference_period"],
                    },
                )
            )
        if len(rows) != 2:
            raise ValueError("USGS parser did not produce production and reserves")
        return ProviderResult(
            category="commodity_fundamentals",
            rows=rows,
            raw_text=content,
            source=str(spec["source"]),
            source_url=spec["source_url"],
            notes=notes,
            attempts=attempts,
        )
    except Exception as error:
        if isinstance(error, OfficialHttpError):
            notes = _unverified_provenance_notes(
                content,
                limitation_note=limitation_note,
                detail=error.safe_message,
            )
            failure_phase = "raw" if error.phase == "schema" else "retrieve"
            raise ProviderPhaseError(
                error.code,
                failure_phase,
                notes,
                error.attempts,
            ) from None
        else:
            detail = str(error)
        notes = _unverified_provenance_notes(
            content,
            limitation_note=limitation_note,
            detail=detail,
        )
        return ProviderResult(
            category="commodity_fundamentals",
            rows=[],
            raw_text=content,
            source=source,
            source_url=source_url,
            status="FETCH_FAILED",
            notes=notes,
            attempts=attempts,
            completed_phase=completed_phase,
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


def _fomc_provider(
    session: requests.Session, start: date, end: date
) -> ProviderResult:
    calendar = _text(session, FOMC_URL)
    events = select_event_window(parse_fomc_calendar(calendar), start, end)
    raw = [calendar]
    enriched = []
    for event in events:
        if "notation vote" in str(event["event_name"]).lower():
            enriched.append(event)
            continue
        event_date = event["event_date"]
        statement_url = (
            "https://www.federalreserve.gov/newsevents/pressreleases/"
            f"monetary{event_date.strftime('%Y%m%d')}a.htm"
        )
        statement = _text(session, statement_url)
        raw.append(statement)
        decision = parse_fomc_statement(statement, statement_url, event_date)
        row = dict(event)
        row.update(
            {
                "event_type": "fomc_policy_decision",
                "actual": (
                    f"{decision['action']} {decision['target_lower']:g}%-"
                    f"{decision['target_upper']:g}%"
                ),
                "source_url": statement_url,
            }
        )
        enriched.append(row)
    return ProviderResult(
        category="events",
        rows=enriched,
        raw_text="\n".join(raw),
        source="Federal Reserve Board",
        source_url=FOMC_URL,
    )


def _ism_licensed_provider() -> ContextProvider:
    def fetch() -> ProviderResult:
        return ProviderResult(
            category="economic_releases",
            rows=[],
            raw_text="",
            source="Institute for Supply Management",
            source_url=ISM_URL,
            status="UNAVAILABLE_LICENSED",
            notes=(
                "ISM PMI time-series reproduction requires permission; no value "
                "or substitute series is published."
            ),
        )

    return ContextProvider(
        spec=ProviderSpec(
            name="ism_manufacturing_pmi",
            category="economic_releases",
            source_tier="licensed",
            requiredness="optional",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="monthly",
            freshness_days=None,
        ),
        fetch=fetch,
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


def _cftc_tff_provider(
    session: requests.Session,
    start: date,
    end: date,
    contract_codes: dict[str, str],
    freshness_days: int,
    http: CommodityHttpSpec,
) -> ProviderResult:
    raw_archives = []
    archive_texts = []
    transport_attempts = 1
    source_url = CFTC_TFF_URL.format(year=end.year)
    for year in range(end.year - 4, end.year + 1):
        source_url = CFTC_TFF_URL.format(year=year)
        content, attempts = _official_bytes(session, source_url, http.policy)
        transport_attempts = max(transport_attempts, attempts)
        raw_archives.append(content)
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                members = [
                    name
                    for name in archive.namelist()
                    if name.lower().endswith((".txt", ".csv"))
                ]
                if not members:
                    raise ValueError("CFTC archive contained no text data")
                text = archive.read(members[0]).decode(
                    "utf-8-sig", errors="replace"
                )
            archive_texts.append(text)
        except (ValueError, zipfile.BadZipFile) as error:
            raise ProviderPhaseError(
                "CFTC_TFF_PARSE_FAILED", "parse", str(error), transport_attempts
            ) from error
    combined = archive_texts[0].rstrip("\r\n")
    for text in archive_texts[1:]:
        lines = text.splitlines()
        combined += "\n" + "\n".join(lines[1:])
    try:
        parsed = parse_cftc_tff_csv(combined, contract_codes)
    except ValueError as error:
        raise ProviderPhaseError(
            "CFTC_TFF_PARSE_FAILED", "parse", str(error), transport_attempts
        ) from error
    eligible = [
        row
        for row in parsed
        if row["expected_release_date"] <= end
        and row["report_date"] <= end
    ]
    latest_by_code: dict[str, dict[str, Any]] = {}
    for row in eligible:
        code = str(row["contract_code"])
        if code not in latest_by_code or row["report_date"] > latest_by_code[code]["report_date"]:
            latest_by_code[code] = row
    missing = sorted(set(contract_codes) - set(latest_by_code))
    if missing:
        raise ProviderPhaseError(
            "CFTC_TFF_COVERAGE_FAILED",
            "coverage",
            "CFTC response missing eligible configured contracts: " + ", ".join(missing),
            transport_attempts,
        )
    stale = sorted(
        code
        for code, row in latest_by_code.items()
        if (end - row["expected_release_date"]).days > freshness_days
    )
    if stale:
        raise ProviderPhaseError(
            "CFTC_TFF_FRESHNESS_FAILED",
            "freshness",
            f"CFTC release is stale beyond configured {freshness_days} days: "
            + ", ".join(stale),
            transport_attempts,
        )
    selected = list(latest_by_code.values())
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
                "leveraged_fund_percentile",
            )
        }
        code = observation["metric_code"]
        observation_source_url = CFTC_TFF_URL.format(
            year=observation["report_date"].year
        )
        rows.extend(
            metric_rows(
                as_of_date=observation["report_date"],
                category="positioning_flows",
                market=code,
                source="U.S. Commodity Futures Trading Commission",
                source_url=observation_source_url,
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
        notes=(
            "Net-position percentiles use up to five calendar years of the "
            "configured official archive; eligibility uses the expected "
            "three-day publication lag."
        ),
        attempts=transport_attempts,
    )


def _cftc_disaggregated_provider(
    session: requests.Session,
    start: date,
    end: date,
    contracts: list[dict[str, str]],
    freshness_days: int,
    http: CommodityHttpSpec,
) -> ProviderResult:
    max_window = max(int(spec["percentile_window"]) for spec in contracts)
    history_start = start - timedelta(weeks=max_window)
    quoted_codes = ",".join(
        f"'{spec['contract_code']}'" for spec in sorted(
            contracts, key=lambda item: item["contract_code"]
        )
    )
    params = {
        "$where": (
            f"report_date_as_yyyy_mm_dd >= '{history_start.isoformat()}T00:00:00.000' "
            f"AND report_date_as_yyyy_mm_dd <= '{end.isoformat()}T23:59:59.999' "
            f"AND cftc_contract_market_code in ({quoted_codes})"
        ),
        "$order": "cftc_contract_market_code,report_date_as_yyyy_mm_dd",
        "$limit": 50000,
    }
    content, transport_attempts = _official_bytes(
        session, CFTC_DISAGGREGATED_URL, http.policy, params=params
    )
    try:
        text = content.decode("utf-8-sig")
        parsed = parse_cftc_disaggregated_csv(text, contracts)
        eligible = filter_known_as_of(
            [row for row in parsed if row["report_date"] <= end],
            end,
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise ProviderPhaseError(
            "CFTC_DISAGGREGATED_PARSE_FAILED",
            "parse",
            str(error),
            transport_attempts,
        ) from error
    latest_by_code: dict[str, dict[str, Any]] = {}
    for row in eligible:
        code = str(row["contract_code"])
        if code not in latest_by_code or row["report_date"] > latest_by_code[code]["report_date"]:
            latest_by_code[code] = row
    selected = list(latest_by_code.values())
    configured_codes = {
        str(spec["contract_code"]).strip() for spec in contracts
    }
    selected_codes = {str(row["contract_code"]) for row in selected}
    missing_codes = sorted(configured_codes - selected_codes)
    if missing_codes:
        raise ProviderPhaseError(
            "CFTC_DISAGGREGATED_COVERAGE_FAILED",
            "coverage",
            "CFTC response missing configured contracts for requested window: "
            + ", ".join(missing_codes),
            transport_attempts,
        )
    stale_codes = sorted(
        code
        for code, row in latest_by_code.items()
        if (end - (row["report_date"] + timedelta(days=3))).days
        > freshness_days
    )
    if stale_codes:
        raise ProviderPhaseError(
            "CFTC_DISAGGREGATED_FRESHNESS_FAILED",
            "freshness",
            f"CFTC release is stale beyond configured {freshness_days} days: "
            + ", ".join(stale_codes),
            transport_attempts,
        )
    rows = []
    measurements = [("open_interest", "open_interest", None)]
    for participant in DISAGGREGATED_PARTICIPANTS:
        measurements.extend(
            (
                (f"{participant}_net", "net_position", participant),
                (f"{participant}_net_change", "net_position", participant),
                (f"{participant}_percentile", "percentile", participant),
            )
        )
    for observation in selected:
        commodity_code = str(observation["commodity_code"])
        for value_key, measurement_kind, participant_class in measurements:
            metric_code = f"{commodity_code}_{value_key}"
            rows.extend(
                metric_rows(
                    as_of_date=observation["report_date"],
                    category="positioning_flows",
                    market=observation["market_name"],
                    source="U.S. Commodity Futures Trading Commission",
                    source_url=CFTC_DISAGGREGATED_URL,
                    frequency="weekly",
                    values={metric_code: observation[value_key]},
                    units={
                        metric_code: (
                            "ratio" if value_key.endswith("percentile") else "contracts"
                        )
                    },
                    metadata={
                        "commodity_code": commodity_code,
                        "commodity_family": observation["commodity_family"],
                        "metric_role": "positioning",
                        "measurement_kind": measurement_kind,
                        "participant_class": participant_class,
                        "known_as_of": observation["known_as_of"],
                        "reference_period": observation["report_date"].isoformat(),
                    },
                )
            )
    return ProviderResult(
        category="positioning_flows",
        rows=rows,
        raw_text=text,
        source="U.S. Commodity Futures Trading Commission",
        source_url=CFTC_DISAGGREGATED_URL,
        attempts=transport_attempts,
    )


def _yahoo_market_state_provider(
    downloader: Callable[..., Any],
    end: date,
    universe: list[dict[str, str]],
) -> ProviderResult:
    source = "Yahoo Finance (registered sector ETF proxy universe)"
    symbols = tuple(row["symbol"] for row in universe if row.get("enabled") == "1")
    if not symbols:
        return not_configured_result(
            category="market_internals",
            source=source,
            source_url=YAHOO_FINANCE_URL,
            notes="Registered breadth proxy universe is empty.",
        )
    tickers = tuple(dict.fromkeys((*symbols, "RSP", "SPY")))
    raw_text = ""
    try:
        frame = downloader(
            tickers=list(tickers),
            start=(end - timedelta(days=550)).isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=False,
            group_by="ticker",
            threads=False,
            progress=False,
        )
        history = extract_yahoo_market_history(frame, tickers, end)
        raw_text = serialize_yahoo_market_history(history)
        breadth = calculate_registered_universe_state(
            history.loc[history["symbol"].isin(symbols)],
            as_of_date=end,
        )
        lag = (end - breadth["as_of_date"]).days
        if lag < 0 or lag > 7:
            raise ValueError(
                f"Yahoo market-state date {breadth['as_of_date']} has lag {lag} days "
                f"versus target Sunday {end}; allowed range is 0..7 days"
            )
        relative = calculate_style_relative_windows(
            history,
            style_symbol="RSP",
            benchmark_symbol="SPY",
        )
        values = {
            "us_sector_etf_proxy_constituent_count": breadth["constituent_count"],
            "us_sector_etf_proxy_advancers": breadth["advancers"],
            "us_sector_etf_proxy_decliners": breadth["decliners"],
            "us_sector_etf_proxy_unchanged": breadth["unchanged"],
            "us_sector_etf_proxy_advance_ratio": breadth["advance_ratio"],
            "us_sector_etf_proxy_advance_decline_ratio": breadth[
                "advance_decline_ratio"
            ],
            "us_sector_etf_proxy_net_advances": breadth["net_advances"],
            "us_sector_etf_proxy_new_highs": breadth["new_highs"],
            "us_sector_etf_proxy_new_lows": breadth["new_lows"],
        }
        for window in (20, 50, 200):
            values[f"us_sector_etf_proxy_pct_above_{window}d_ma"] = breadth[
                f"pct_above_{window}d_ma"
            ]
            values[f"us_sector_etf_proxy_{window}d_coverage"] = breadth[
                f"coverage_above_{window}d_ma"
            ]
        values.update(
            {
                "rsp_spy_relative_return_5d": relative["relative_return_5d"],
                "rsp_spy_relative_return_20d": relative["relative_return_20d"],
            }
        )
        units = {
            code: (
                "ratio"
                if code.endswith(("ratio", "ma", "return_5d", "return_20d"))
                else "count"
            )
            for code in values
        }
        return ProviderResult(
            category="market_internals",
            rows=metric_rows(
                as_of_date=breadth["as_of_date"],
                category="market_internals",
                market="US_PROXY",
                source=source,
                source_url=YAHOO_FINANCE_URL,
                frequency="daily",
                values=values,
                units=units,
            ),
            raw_text=raw_text,
            source=source,
            source_url=YAHOO_FINANCE_URL,
            notes=(
                f"registered {len(symbols)}-instrument sector ETF proxy universe; "
                "not official constituent-level index breadth"
            ),
        )
    except Exception as error:
        return ProviderResult(
            category="market_internals",
            rows=[],
            raw_text=raw_text,
            source=source,
            source_url=YAHOO_FINANCE_URL,
            status="FETCH_FAILED",
            notes=str(error),
        )


def _ishares_ivv_provider(session: requests.Session, end: date) -> ProviderResult:
    text = _text(session, ISHARES_IVV_URL)
    observation = parse_ishares_fund_page(text, ticker="IVV")
    if observation["date"] > end:
        return ProviderResult(
            category="fund_flows",
            rows=[],
            raw_text=text,
            source="iShares",
            source_url=ISHARES_IVV_URL,
            status="POINT_IN_TIME_UNAVAILABLE",
            notes=(
                f"Issuer observation {observation['date']} is after target Sunday {end}."
            ),
        )
    values = {
        "ivv_nav": observation["nav"],
        "ivv_net_assets": observation["net_assets"],
        "ivv_shares_outstanding": observation["shares_outstanding"],
    }
    return ProviderResult(
        category="fund_flows",
        rows=metric_rows(
            as_of_date=observation["date"],
            category="fund_flows",
            market="IVV",
            source="iShares",
            source_url=ISHARES_IVV_URL,
            frequency="daily",
            values=values,
            units={
                "ivv_nav": "USD_per_share",
                "ivv_net_assets": "USD",
                "ivv_shares_outstanding": "shares",
            },
        ),
        raw_text=text,
        source="iShares",
        source_url=ISHARES_IVV_URL,
        notes=(
            "Issuer AUM and shares are observed; implied flow requires a prior "
            "dated issuer observation and is not inferred from price returns."
        ),
    )


def _hkex_stock_connect_provider(
    session: requests.Session,
    end: date,
) -> ProviderResult:
    failures = []
    for lag in range(8):
        candidate = end - timedelta(days=lag)
        url = HKEX_STOCK_CONNECT_URL.format(stamp=candidate.strftime("%Y%m%d"))
        try:
            text = _text(session, url)
            observation = parse_hkex_stock_connect_daily(text)
            ensure_fresh_market_date(
                observation["date"], expected_end=end, max_lag_days=4
            )
            values = {
                f"hkex_{key}": value
                for key, value in observation.items()
                if key != "date"
            }
            units = {
                code: (
                    "count"
                    if code.endswith("trade_count")
                    else "HKD_millions"
                    if "southbound" in code
                    else "RMB_millions"
                )
                for code in values
            }
            return ProviderResult(
                category="fund_flows",
                rows=metric_rows(
                    as_of_date=observation["date"],
                    category="fund_flows",
                    market="HKEX_STOCK_CONNECT",
                    source="Hong Kong Exchanges and Clearing",
                    source_url=url,
                    frequency="daily",
                    values=values,
                    units=units,
                ),
                raw_text=text,
                source="Hong Kong Exchanges and Clearing",
                source_url=url,
                notes=(
                    "Southbound net buy is official Buy Turnover minus Sell "
                    "Turnover; Northbound net flow is intentionally unavailable."
                ),
            )
        except Exception as error:
            failures.append(f"{candidate}: {error}")
    raise ValueError(
        "No recent HKEX Stock Connect daily statistics: " + "; ".join(failures)
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


def _company_price_histories(
    downloader: Callable[..., Any],
    *,
    tickers: tuple[str, ...],
    end: date,
) -> tuple[dict[str, list[dict[str, Any]]], str]:
    frame = downloader(
        tickers=list(tickers),
        start=(end - timedelta(days=365 * 7)).isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        interval="1d",
        auto_adjust=False,
        actions=False,
        group_by="ticker",
        threads=False,
        progress=False,
    )
    history = extract_yahoo_market_history(frame, tickers, end)
    serialized = serialize_yahoo_market_history(history)
    return (
        {
            ticker: [
                {"date": row.date.isoformat(), "close": float(row.close)}
                for row in history.loc[history["symbol"] == ticker].itertuples(index=False)
            ]
            for ticker in tickers
        },
        serialized,
    )


def _sec_company_fundamentals_provider(
    session: requests.Session,
    end: date,
    watchlist: list[dict[str, str]],
    user_agent: str | None,
    downloader: Callable[..., Any],
) -> ProviderResult:
    source_url = "https://data.sec.gov/api/xbrl/companyfacts/"
    if not watchlist:
        return not_configured_result(
            category="company_fundamentals",
            source="SEC EDGAR Company Facts",
            source_url=source_url,
            notes="Company watchlist is empty; no production companies are invented.",
        )
    if not user_agent:
        return not_configured_result(
            category="company_fundamentals",
            source="SEC EDGAR Company Facts",
            source_url=source_url,
            notes="Set SEC_USER_AGENT before fetching the enabled company watchlist.",
        )
    tickers = tuple(company["ticker"] for company in watchlist)
    price_histories, price_raw = _company_price_histories(
        downloader, tickers=tickers, end=end
    )
    rows = []
    raw = [price_raw]
    for company in watchlist:
        url = SEC_COMPANY_FACTS_URL.format(cik=company["cik"])
        text = _text(session, url, headers={"User-Agent": user_agent})
        raw.append(text)
        company_rows = build_company_fundamentals(
            text,
            ticker=company["ticker"],
            cik=company["cik"],
            company_name=company["company_name"],
            as_of_date=end,
            price_history=price_histories[company["ticker"]],
        )
        if not company_rows:
            raise ValueError(
                f"SEC Company Facts produced no eligible rows for {company['ticker']}"
            )
        rows.extend(company_rows)
    return ProviderResult(
        category="company_fundamentals",
        rows=rows,
        raw_text="\n".join(raw),
        source="SEC EDGAR Company Facts and Yahoo Finance historical close",
        source_url=source_url,
        notes=(
            "SEC facts and public-vendor prices are cutoff before all registered "
            "fundamental and trailing-valuation calculations."
        ),
    )


def _sec_document_candidates(
    session: requests.Session,
    *,
    start: date,
    end: date,
    watchlist: list[dict[str, str]],
    user_agent: str,
) -> tuple[list[tuple[dict[str, Any], str]], list[str]]:
    documents = []
    raw = []
    for company in watchlist:
        submissions_url = SEC_URL.format(cik=company["cik"])
        submissions = _text(
            session, submissions_url, headers={"User-Agent": user_agent}
        )
        raw.append(submissions)
        events = parse_sec_submissions(
            submissions,
            cik=company["cik"],
            ticker=company["ticker"],
            start=start,
            end=end,
        )
        for event in events:
            if event["form"] != "8-K":
                continue
            filing_text = _text(
                session,
                event["source_url"],
                headers={"User-Agent": user_agent},
            )
            raw.append(filing_text)
            event = {**event, "company_name": company["company_name"]}
            documents.append((event, filing_text))
    return documents, raw


def _sec_guidance_provider(
    session: requests.Session,
    start: date,
    end: date,
    watchlist: list[dict[str, str]],
    user_agent: str | None,
) -> ProviderResult:
    source_url = "https://www.sec.gov/edgar/search/"
    if not watchlist:
        return not_configured_result(
            category="company_fundamentals",
            source="SEC EDGAR filing documents",
            source_url=source_url,
            notes="Company watchlist is empty; guidance proxy is disabled.",
        )
    if not user_agent:
        return not_configured_result(
            category="company_fundamentals",
            source="SEC EDGAR filing documents",
            source_url=source_url,
            notes="Set SEC_USER_AGENT before classifying watchlist filing text.",
        )
    documents, raw = _sec_document_candidates(
        session,
        start=start,
        end=end,
        watchlist=watchlist,
        user_agent=user_agent,
    )
    rows = []
    for event, filing_text in documents:
        if event["event_type"] == "earnings_release":
            rows.extend(
                build_guidance_proxy_rows(
                    filing_text, event, as_of_date=end
                )
            )
    return ProviderResult(
        category="company_fundamentals",
        rows=rows,
        raw_text="\n".join(raw),
        source="SEC EDGAR filing documents",
        source_url=source_url,
        notes=(
            "Rules-based guidance direction proxy; no consensus or revision "
            "breadth is inferred."
        ),
    )


def _sec_capital_markets_provider(
    session: requests.Session,
    start: date,
    end: date,
    watchlist: list[dict[str, str]],
    user_agent: str | None,
) -> ProviderResult:
    source_url = "https://www.sec.gov/Archives/edgar/daily-index/"
    if not user_agent:
        return not_configured_result(
            category="capital_markets",
            source="SEC EDGAR daily index and filing documents",
            source_url=source_url,
            notes="Set SEC_USER_AGENT before fetching SEC capital-markets filings.",
        )
    raw = []
    index_records = []
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            quarter = (cursor.month - 1) // 3 + 1
            url = SEC_DAILY_INDEX_URL.format(
                year=cursor.year,
                quarter=quarter,
                stamp=cursor.strftime("%Y%m%d"),
            )
            text = _text(session, url, headers={"User-Agent": user_agent})
            raw.append(text)
            index_records.extend(parse_sec_master_index(text))
        cursor += timedelta(days=1)
    rows = build_sec_ipo_rows(index_records, as_of_date=end)
    if watchlist:
        documents, document_raw = _sec_document_candidates(
            session,
            start=start,
            end=end,
            watchlist=watchlist,
            user_agent=user_agent,
        )
        raw.extend(document_raw)
        rows.extend(build_ma_rows(documents, as_of_date=end))
    return ProviderResult(
        category="capital_markets",
        rows=rows,
        raw_text="\n".join(raw),
        source="SEC EDGAR daily index and filing documents",
        source_url=source_url,
        notes=(
            "IPO values are filing activity, not issuance dollars; M&A rows are "
            "watchlist filing-text classifications, not comprehensive coverage."
        ),
    )


def _hkex_capital_markets_provider(
    session: requests.Session, start: date, end: date
) -> ProviderResult:
    text = _text(session, HKEX_NEW_LISTINGS_URL)
    parsed = [
        row
        for row in parse_hkex_listing_table(text, source_url=HKEX_NEW_LISTINGS_URL)
        if start <= row["event_date"] <= end
    ]
    return ProviderResult(
        category="capital_markets",
        rows=build_hkex_ipo_rows(parsed, as_of_date=end),
        raw_text=text,
        source="Hong Kong Exchanges and Clearing",
        source_url=HKEX_NEW_LISTINGS_URL,
        notes="Official HKEX listing records; no inferred offering size.",
    )


def _legacy_eia_provider(
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


class _OfficialEiaClient:
    def __init__(
        self,
        session: requests.Session,
        api_key: str,
        policy: OfficialHttpPolicy,
    ) -> None:
        self.session = session
        self.api_key = api_key
        self.policy = policy
        self.raw_bodies: list[bytes] = []
        self.attempts = 1

    def _get(self, url: str, params: Mapping[str, Any]) -> bytes:
        body, attempts = _official_bytes(
            self.session,
            url,
            self.policy,
            params=params,
            audit_secrets=(self.api_key,),
        )
        self.raw_bodies.append(body)
        self.attempts = max(self.attempts, attempts)
        return body

    def fetch_metadata(
        self,
        spec,
        expected: Mapping[str, Mapping[str, Any]],
    ) -> None:
        wanted: dict[str, set[str]] = {}
        for item in expected.values():
            for facet, selected in item["facets"].items():
                wanted.setdefault(str(facet), set()).add(str(selected))
        for facet, required in sorted(wanted.items()):
            body = self._get(
                f"{EIA_SOURCE_URL}{spec.route}/facet/{facet}/",
                {
                    "api_key": self.api_key,
                    "offset": 0,
                    "length": spec.page_length,
                },
            )
            try:
                payload = json.loads(body.decode("utf-8"))
                response = payload.get("response", {})
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError(
                    f"EIA facet metadata is invalid for {spec.route}/{facet}"
                ) from error
            identifiers = eia_metadata_facet_ids(response)
            missing = sorted(required - identifiers)
            if missing:
                raise ValueError(
                    f"EIA configured facet is unavailable for {spec.route}/{facet}: "
                    + ", ".join(missing)
                )

    def fetch_page(self, spec, *, offset: int, length: int) -> dict[str, Any]:
        params: dict[str, Any] = {
            "api_key": self.api_key,
            "frequency": spec.frequency,
            "data[0]": "value",
            "start": spec.start,
            "end": spec.end,
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "offset": offset,
            "length": length,
        }
        for facet, values in spec.facets.items():
            params[f"facets[{facet}][]"] = list(values)
        body = self._get(f"{EIA_SOURCE_URL}{spec.route}/data/", params)
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("EIA data response is not valid UTF-8 JSON") from error
        if not isinstance(payload, dict):
            raise ValueError("EIA data response must be a JSON object")
        return payload


def _eia_provider(
    session: requests.Session,
    end: date,
    series_config: list[dict[str, Any]],
    api_key: str | None,
    provider_name: str,
    http: CommodityHttpSpec,
) -> ProviderResult:
    if not api_key:
        return eia_not_configured_result()
    configured_series = [validate_eia_spec(item) for item in series_config]
    if not configured_series:
        raise ValueError(f"EIA provider {provider_name} has no configured series")
    for item in configured_series:
        if item["provider"] != provider_name:
            raise ValueError(
                f"EIA family provider {provider_name} received "
                f"{item['provider']} config"
            )
    if http.request_batch_size is None or http.page_length is None:
        raise ValueError("EIA HTTP policy requires request_batch_size and page_length")
    batch_specs = build_eia_batch_specs(
        configured_series,
        request_batch_size=http.request_batch_size,
        page_length=http.page_length,
        start=(end - timedelta(days=550)).isoformat(),
        end=end.isoformat(),
    )
    expected = {
        str(item["facets"]["series"]): item for item in configured_series
    }
    client = _OfficialEiaClient(session, api_key, http.policy)
    try:
        pages = fetch_eia_batches(client, batch_specs, expected_metadata=expected)
    except OfficialHttpError as error:
        failure_phase = "raw" if error.phase == "schema" else "retrieve"
        raise ProviderPhaseError(
            error.code,
            failure_phase,
            error.safe_message,
            error.attempts,
        ) from None
    except EiaBatchError as error:
        raise ProviderPhaseError(
            f"EIA_{error.phase.upper()}_FAILED",
            error.phase,
            str(error),
            client.attempts,
        ) from error

    raw_rows = [
        row
        for payload in pages
        for row in payload["response"]["data"]
    ]
    rows: list[dict[str, Any]] = []
    for item in configured_series:
        series = str(item["facets"]["series"])
        text = json.dumps(
            {
                "response": {
                    "data": [
                        row for row in raw_rows if str(row.get("series") or "") == series
                    ]
                }
            },
            separators=(",", ":"),
        )
        try:
            parsed = parse_eia_metric_series(text, item)
        except ValueError as error:
            raise ProviderPhaseError(
                "EIA_PARSE_FAILED", "parse", str(error), client.attempts
            ) from error
        try:
            metrics = latest_and_changes(parsed, end)
        except ValueError as error:
            raise ProviderPhaseError(
                "EIA_COVERAGE_FAILED", "coverage", str(error), client.attempts
            ) from error
        latest_date = period_date(metrics[0]["period"])
        if (end - latest_date).days > item["freshness_days"]:
            raise ProviderPhaseError(
                "EIA_FRESHNESS_FAILED",
                "freshness",
                f"EIA series {item['metric_code']} is stale at "
                f"{metrics[0]['period']}",
                client.attempts,
            )
        for metric in metrics:
            rows.extend(
                metric_rows(
                    as_of_date=period_date(metric["period"]),
                    category="commodity_fundamentals",
                    market="US",
                    source="U.S. Energy Information Administration",
                    source_url=f"{EIA_SOURCE_URL}{item['route']}/data/",
                    frequency=item["frequency"],
                    values={metric["metric_code"]: metric["value"]},
                    units={metric["metric_code"]: metric["unit"]},
                    names={metric["metric_code"]: metric["metric_name"]},
                    metadata={
                        "commodity_code": item["commodity_code"],
                        "commodity_family": item["commodity_family"],
                        "metric_role": "physical_fundamental",
                        "measurement_kind": metric["measurement_kind"],
                        "participant_class": None,
                        "known_as_of": metric.get("known_as_of"),
                        "reference_period": metric.get("reference_period"),
                    },
                )
            )
    return ProviderResult(
        category="commodity_fundamentals",
        rows=rows,
        raw_text=b"\n".join(client.raw_bodies),
        source="U.S. Energy Information Administration",
        source_url=EIA_SOURCE_URL,
        attempts=client.attempts,
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
                **{field: None for field in COMMODITY_METRIC_FIELDS},
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
    if session is None:
        official_client = requests.Session()
        official_client.headers.update(client.headers)
    else:
        official_client = client
    commodity_http = load_commodity_http_policies()
    if data_dir is None:
        cftc_rows = load_config_rows("context.cftc_contracts")
        breadth_rows = load_config_rows("context.breadth_universe")
        watchlist_rows = load_config_rows("context.company_watchlist")
        eia_config = load_config_rows("context.eia_series")
        usda_psd_config = load_config_rows("context.usda_psd")
        usda_esr_config = load_config_rows("context.usda_esr")
        metal_config = load_config_rows("context.metals")
        financial_config = load_config_rows("context.financial_conditions")
        yahoo_rows = load_config_rows("context.yahoo_volatility")
    else:
        root = Path(data_dir)
        cftc_rows = _config(root / "capital_weekly_cftc_contracts.csv")
        breadth_rows = _config(root / "capital_weekly_breadth_universe.csv")
        watchlist_rows = _config(root / "capital_weekly_company_watchlist.csv")
        eia_config = _config(root / "capital_weekly_eia_series.csv")
        usda_psd_path = root / "capital_weekly_usda_psd.csv"
        usda_esr_path = root / "capital_weekly_usda_esr.csv"
        usda_psd_config = _config(usda_psd_path) if usda_psd_path.exists() else []
        usda_esr_config = _config(usda_esr_path) if usda_esr_path.exists() else []
        metal_path = root / "capital_weekly_metals.csv"
        metal_config = _config(metal_path) if metal_path.exists() else []
        financial_config = _config(root / "capital_weekly_financial_conditions.csv")
        yahoo_rows = _config(root / "capital_weekly_yahoo_volatility.csv")
    breadth_universe = _validated_breadth_universe(breadth_rows)
    unknown_report_families = sorted(
        {
            str(row.get("report_family", "")).strip()
            for row in cftc_rows
        }
        - {"tff", "disaggregated"}
    )
    if unknown_report_families:
        raise ValueError(
            "Unsupported CFTC report families: " + ", ".join(unknown_report_families)
        )

    def cftc_freshness(report_family: str) -> int:
        relevant = [
            row for row in cftc_rows if row["report_family"] == report_family
        ]
        try:
            values = {
                int(str(row.get("freshness_days") or "").strip())
                for row in relevant
            }
        except ValueError as error:
            raise ValueError(
                f"cftc_{report_family} freshness_days must be a positive integer"
            ) from error
        if len(values) != 1 or next(iter(values), 0) <= 0:
            raise ValueError(
                f"cftc_{report_family} requires one positive configured freshness_days"
            )
        return next(iter(values))

    cftc_tff_config = {
        row["contract_code"]: row["metric_code"]
        for row in cftc_rows
        if row["report_family"] == "tff"
    }
    cftc_disaggregated_config = [
        row for row in cftc_rows if row["report_family"] == "disaggregated"
    ]
    cftc_tff_freshness = cftc_freshness("tff") if cftc_tff_config else 0
    cftc_disaggregated_freshness = (
        cftc_freshness("disaggregated") if cftc_disaggregated_config else 0
    )

    def uniform_freshness(rows: list[dict], label: str) -> int | None:
        if not rows:
            return None
        try:
            values = {
                int(str(row.get("freshness_days") or "").strip()) for row in rows
            }
        except ValueError as error:
            raise ValueError(
                f"{label} freshness_days must be a positive integer"
            ) from error
        if len(values) != 1 or next(iter(values), 0) <= 0:
            raise ValueError(
                f"{label} requires one positive configured freshness_days"
            )
        return next(iter(values))

    provider_freshness: dict[str, int] = {}
    if cftc_tff_config:
        provider_freshness["cftc_tff"] = cftc_tff_freshness
    if cftc_disaggregated_config:
        provider_freshness["cftc_disaggregated"] = cftc_disaggregated_freshness
    watchlist = load_company_watchlist(watchlist_rows)
    yahoo_volatility_config = load_yahoo_volatility_config(yahoo_rows)
    yahoo_download = yahoo_downloader or _default_yahoo_download
    legacy_eia_config = [
        row
        for row in eia_config
        if str(row.get("provider") or "").strip() == "eia_commodities"
    ]
    eia_by_provider = {
        name: [
            row
            for row in eia_config
            if str(row.get("provider") or "").strip() == name
        ]
        for name in EIA_PROVIDERS
    }
    eia_key = settings.get("EIA_API_KEY")
    usda_key = settings.get("USDA_API_KEY")
    for name, rows in eia_by_provider.items():
        freshness = uniform_freshness(rows, name) if eia_key else None
        if freshness is not None:
            provider_freshness[name] = freshness
    for name, rows in (
        ("usda_psd", usda_psd_config),
        ("usda_esr", usda_esr_config),
    ):
        freshness = uniform_freshness(rows, name) if usda_key else None
        if freshness is not None:
            provider_freshness[name] = freshness

    fetchers: dict[str, Callable[[], ProviderResult]] = {
        "bls_calendar": lambda: _bls_provider(client, start, end),
        "federal_reserve_calendar": lambda: _fed_provider(client, start, end),
        "fomc_calendar": lambda: _fomc_provider(client, start, end),
        "census_calendar": lambda: _event_provider(
            client,
            url=CENSUS_URL,
            parser=parse_census_calendar,
            start=start,
            end=end,
            source="U.S. Census Bureau",
        ),
        "nasdaq_market_summary": lambda: _nasdaq_provider(client, start, end),
        "finra_margin": lambda: _finra_provider(client, end),
        "sec_company_events": lambda: _sec_provider(
            client,
            start,
            end,
            watchlist,
            settings.get("SEC_USER_AGENT"),
        ),
        "sec_company_fundamentals": lambda: _sec_company_fundamentals_provider(
            client,
            end,
            watchlist,
            settings.get("SEC_USER_AGENT"),
            yahoo_download,
        ),
        "sec_guidance_proxy": lambda: _sec_guidance_provider(
            client,
            start,
            end,
            watchlist,
            settings.get("SEC_USER_AGENT"),
        ),
        "sec_capital_markets": lambda: _sec_capital_markets_provider(
            client,
            start,
            end,
            watchlist,
            settings.get("SEC_USER_AGENT"),
        ),
        "hkex_capital_markets": lambda: _hkex_capital_markets_provider(
            client, start, end
        ),
        "eia_commodities": lambda: _legacy_eia_provider(
            client, end, legacy_eia_config, eia_key
        ),
        "eia_natural_gas": lambda: _official_provider_result(
            lambda: _eia_provider(
                official_client,
                end,
                eia_by_provider["eia_natural_gas"],
                eia_key,
                "eia_natural_gas",
                commodity_http["eia"],
            )
        ),
        "eia_refined_products": lambda: _official_provider_result(
            lambda: _eia_provider(
                official_client,
                end,
                eia_by_provider["eia_refined_products"],
                eia_key,
                "eia_refined_products",
                commodity_http["eia"],
            )
        ),
        "usda_psd": lambda: _official_provider_result(
            lambda: _usda_psd_provider(
                official_client,
                end,
                usda_psd_config,
                usda_key,
                commodity_http["usda_psd"],
            )
        ),
        "usda_esr": lambda: _official_provider_result(
            lambda: _usda_esr_provider(
                official_client,
                end,
                usda_esr_config,
                usda_key,
                commodity_http["usda_esr"],
            )
        ),
        "fred_financial_conditions": lambda: _fred_provider(
            client, end, financial_config
        ),
        "yahoo_volatility_signals": lambda: _yahoo_volatility_provider(
            yahoo_download, end, yahoo_volatility_config
        ),
        "yahoo_market_state": lambda: _yahoo_market_state_provider(
            yahoo_download, end, breadth_universe
        ),
        "ishares_ivv_fund": lambda: _ishares_ivv_provider(client, end),
        "hkex_stock_connect_flows": lambda: _hkex_stock_connect_provider(
            client, end
        ),
        "hkex_microstructure": lambda: _hkex_provider(client, end),
        "sse_microstructure": lambda: _sse_provider(client, end),
        "szse_microstructure": lambda: _szse_provider(client, end),
    }
    definitions = {
        "bls_calendar": ("events", "event", "required"),
        "federal_reserve_calendar": ("events", "event", "required"),
        "fomc_calendar": ("events", "event", "required"),
        "census_calendar": ("events", "event", "required"),
        "nasdaq_market_summary": ("market_internals", "daily", "required"),
        "finra_margin": ("positioning_flows", "monthly", "required"),
        "sec_company_events": ("company_events", "event", "optional"),
        "sec_company_fundamentals": (
            "company_fundamentals",
            "quarterly",
            "required" if watchlist else "optional",
        ),
        "sec_guidance_proxy": ("company_fundamentals", "event", "optional"),
        "sec_capital_markets": ("capital_markets", "event", "optional"),
        "hkex_capital_markets": ("capital_markets", "event", "optional"),
        "eia_commodities": ("commodity_fundamentals", "weekly", "optional"),
        "eia_natural_gas": (
            "commodity_fundamentals",
            "mixed",
            "required" if eia_key else "optional",
        ),
        "eia_refined_products": (
            "commodity_fundamentals",
            "weekly",
            "required" if eia_key else "optional",
        ),
        "usda_psd": (
            "commodity_fundamentals",
            "monthly",
            "required" if usda_key else "optional",
        ),
        "usda_esr": (
            "commodity_fundamentals",
            "weekly",
            "required" if usda_key else "optional",
        ),
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
        "yahoo_market_state": ("market_internals", "daily", "optional"),
        "ishares_ivv_fund": ("fund_flows", "daily", "optional"),
        "hkex_stock_connect_flows": ("fund_flows", "daily", "optional"),
        "hkex_microstructure": ("market_internals", "daily", "required"),
        "sse_microstructure": ("market_internals", "daily", "required"),
        "szse_microstructure": ("market_internals", "daily", "required"),
    }
    failure_sources = {
        "sec_guidance_proxy": (
            "SEC EDGAR filing documents",
            "https://www.sec.gov/edgar/search/",
        ),
        "sec_capital_markets": (
            "SEC EDGAR daily index and filing documents",
            "https://www.sec.gov/Archives/edgar/daily-index/",
        ),
        "hkex_capital_markets": (
            "Hong Kong Exchanges and Clearing",
            HKEX_NEW_LISTINGS_URL,
        ),
        "eia_commodities": (
            "U.S. Energy Information Administration",
            EIA_SOURCE_URL,
        ),
        "yahoo_volatility_signals": (
            YAHOO_VOLATILITY_SOURCE,
            YAHOO_FINANCE_URL,
        ),
        "yahoo_market_state": (
            "Yahoo Finance (registered sector ETF proxy universe)",
            YAHOO_FINANCE_URL,
        ),
        "ishares_ivv_fund": ("iShares", ISHARES_IVV_URL),
        "hkex_stock_connect_flows": (
            "Hong Kong Exchanges and Clearing",
            "https://www.hkex.com.hk/Mutual-Market/Stock-Connect/Statistics/",
        ),
    }
    if cftc_tff_config:
        fetchers["cftc_tff"] = lambda: _official_provider_result(
            lambda: _cftc_tff_provider(
                official_client, start, end, cftc_tff_config, cftc_tff_freshness,
                commodity_http["cftc_tff"]
            )
        )
        definitions["cftc_tff"] = (
            "positioning_flows",
            "weekly",
            "required",
        )
    if cftc_disaggregated_config:
        fetchers["cftc_disaggregated"] = lambda: _official_provider_result(
            lambda: _cftc_disaggregated_provider(
                official_client,
                start,
                end,
                cftc_disaggregated_config,
                cftc_disaggregated_freshness,
                commodity_http["cftc_disaggregated"],
            )
        )
        definitions["cftc_disaggregated"] = (
            "positioning_flows",
            "weekly",
            "required",
        )
    metal_freshness: dict[str, int] = {}
    for raw_item in metal_config:
        item = dict(raw_item)
        name = str(item.get("provider") or "").strip()
        if not name.startswith(("comex_", "usgs_")):
            raise ValueError(f"Unsupported metals provider: {name or 'blank'}")
        if name in definitions:
            raise ValueError(f"Duplicate context provider name: {name}")
        if name.startswith("comex_"):
            fetchers[name] = lambda item=item: _comex_stocks_provider(
                official_client,
                end,
                item,
                commodity_http[str(item["provider"])],
            )
        else:
            fetchers[name] = lambda item=item: _usgs_structural_provider(
                official_client,
                end,
                item,
                commodity_http[str(item["provider"])],
            )
        definitions[name] = (
            "commodity_fundamentals",
            str(item.get("frequency") or "mixed"),
            "optional",
        )
        failure_sources[name] = (
            str(item.get("source") or "").strip(),
            str(item.get("source_url") or "").strip(),
        )
        try:
            metal_freshness[name] = int(str(item.get("freshness_days") or ""))
        except ValueError:
            pass
    providers = {
        name: ContextProvider(
            spec=ProviderSpec(
                name=name,
                category=category,
                source_tier="public",
                requiredness=requiredness,
                provider_version="1.0.0",
                schema_version=(
                    "company-fundamental-v1"
                    if category == "company_fundamentals"
                    else "capital-market-v1"
                    if category == "capital_markets"
                    else "context-metric-v1"
                ),
                frequency=frequency,
                freshness_days=(
                    metal_freshness[name]
                    if name in metal_freshness
                    else provider_freshness[name]
                    if name in provider_freshness
                    else 7
                    if name in {
                        "yahoo_volatility_signals",
                        "yahoo_market_state",
                        "ishares_ivv_fund",
                        "hkex_stock_connect_flows",
                    }
                    else None
                ),
                failure_source=failure_sources.get(name, ("", ""))[0],
                failure_source_url=failure_sources.get(name, ("", ""))[1],
            ),
            fetch=fetchers[name],
        )
        for name, (category, frequency, requiredness) in definitions.items()
    }
    providers.update(
        {
            "bls_economic_releases": build_bls_provider(start, end, client),
            "bea_economic_releases": build_bea_provider(start, end, client),
            "census_retail_sales": build_census_provider(start, end, client),
            "census_housing": build_census_housing_provider(start, end, client),
            "census_durable_goods": build_census_durable_goods_provider(
                start, end, client
            ),
            "ism_manufacturing_pmi": _ism_licensed_provider(),
        }
    )
    return providers


__all__ = [
    "COMEX_COPPER_STOCKS_URL",
    "COMEX_GOLD_STOCKS_URL",
    "USGS_COPPER_MCS_URL",
    "USGS_GOLD_MCS_URL",
    "USDA_FAS_API_URL",
    "USDA_FAS_PORTAL_URL",
    "build_default_providers",
    "metric_rows",
    "not_configured_result",
]
