from __future__ import annotations

import io
import json
import math
import os
import tempfile
import re
import html
from urllib.parse import urljoin, urlparse
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Mapping

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pipeline.internal.common import (
    load_config_rows,
    sanitize_audit_bytes,
    sanitize_audit_text,
)

from pipeline.internal.capital_weekly.commodity_prices import (
    parse_eia_price_series,
    parse_world_bank_monthly_prices,
)
from pipeline.internal.capital_weekly.commodity_research import (
    PRICE_HISTORY_FIELDS,
    bounded_price_history,
    load_history_limits,
)
from pipeline.internal.capital_weekly.context.eia_commodities import (
    CommodityHttpSpec,
    build_eia_batch_specs,
    eia_response_total,
    fetch_eia_batches,
    load_commodity_http_policies,
)
from pipeline.internal.capital_weekly.official_http import official_get
from pipeline.internal.capital_weekly.returns import calculate_macro_snapshot, parse_date


DEFAULT_UNIVERSE_PATH = None
MAX_PROVIDER_PAGES = 100


class RecognizedNonSevenDayOperation(ValueError):
    """A valid official OMO announcement that contains no 7-day operation."""


@dataclass(frozen=True)
class MacroAssetConfig:
    asset_class: str
    group: str
    series_code: str
    name_cn: str
    name_en: str
    provider: str
    provider_symbol: str
    source: str
    source_url: str
    frequency: str
    level_unit: str
    change_unit: str
    sort_order: int
    notes: str = ""
    calculation_id: str = ""
    formula_version: str = ""
    input_series_codes: str = ""
    commodity_code: str = ""
    commodity_family: str = ""
    price_kind: str = ""
    known_as_of: str = ""
    provider_route: str = ""
    freshness_days: str = ""
    source_description: str = ""


@dataclass(frozen=True)
class MacroAssetBundle:
    detail: pd.DataFrame
    source_log: pd.DataFrame
    commodity_price_history: pd.DataFrame


def load_macro_asset_universe(
    path: str | Path | None = DEFAULT_UNIVERSE_PATH,
) -> list[MacroAssetConfig]:
    return [
        MacroAssetConfig(
            **{**row, "sort_order": int(row["sort_order"])},
        )
        for row in load_config_rows("macro", path)
    ]


def _normalized_values(
    history: Iterable[dict],
) -> dict[date, float]:
    values: dict[date, float] = {}
    for point in history:
        values[parse_date(point["date"])] = float(point["value"])
    return values


def align_series_histories(
    histories: Mapping[str, Iterable[dict]],
    input_codes: tuple[str, ...],
    calculator: Callable[..., float],
) -> list[dict[str, date | float]]:
    if not input_codes:
        raise ValueError("Calculated series must declare at least one input")
    try:
        values_by_code = {
            code: _normalized_values(histories[code])
            for code in input_codes
        }
    except KeyError as error:
        raise ValueError(f"Calculated series is missing input: {error.args[0]}") from error
    shared_dates = set.intersection(
        *(set(values) for values in values_by_code.values())
    )
    aligned = []
    for observation_date in sorted(shared_dates):
        value = float(
            calculator(
                *(values_by_code[code][observation_date] for code in input_codes)
            )
        )
        if not math.isfinite(value):
            raise ValueError("Calculated series produced a non-finite value")
        aligned.append({"date": observation_date, "value": value})
    return aligned


def calculate_five_year_five_year(be5: float, be10: float) -> float:
    if not math.isfinite(be5) or not math.isfinite(be10):
        raise ValueError("Breakeven inputs must be finite")
    if be5 <= -100.0 or be10 <= -100.0:
        raise ValueError("Breakeven inputs must be greater than -100 percent")
    return (
        ((1.0 + be10 / 100.0) ** 2) / (1.0 + be5 / 100.0) - 1.0
    ) * 100.0


CALCULATED_SERIES = {
    "UST10Y2Y": (
        ("UST10Y", "UST2Y"),
        lambda ten, two: ten - two,
        "curve-spread-v1",
    ),
    "US_BE5Y": (
        ("UST5Y", "UST_REAL5Y"),
        lambda nominal, real: nominal - real,
        "breakeven-v1",
    ),
    "US_BE10Y": (
        ("UST10Y", "UST_REAL10Y"),
        lambda nominal, real: nominal - real,
        "breakeven-v1",
    ),
    "US_5Y5Y": (
        ("US_BE5Y", "US_BE10Y"),
        calculate_five_year_five_year,
        "forward-inflation-v1",
    ),
}
CALCULATION_IDS = {
    "UST10Y2Y": "curve_spread",
    "US_BE5Y": "breakeven",
    "US_BE10Y": "breakeven",
    "US_5Y5Y": "five_year_five_year",
}
CALCULATED_SOURCE_REFERENCES = {
    "UST10Y2Y": (
        "calculated:UST10Y-UST2Y (shared Treasury observation dates)"
    ),
    "US_BE5Y": (
        "calculated:UST5Y-UST_REAL5Y (shared Treasury observation dates)"
    ),
    "US_BE10Y": (
        "calculated:UST10Y-UST_REAL10Y (shared Treasury observation dates)"
    ),
    "US_5Y5Y": (
        "calculated:5Y5Y from US_BE5Y and US_BE10Y "
        "(shared Treasury observation dates)"
    ),
}


def align_curve_spread(
    ten_year: Iterable[dict],
    two_year: Iterable[dict],
) -> list[dict[str, date | float]]:
    """Inner-join Treasury histories by date and calculate 10Y minus 2Y."""
    return align_series_histories(
        {"UST10Y": ten_year, "UST2Y": two_year},
        ("UST10Y", "UST2Y"),
        lambda ten, two: ten - two,
    )


def _parse_treasury_csv(text: str, field: str) -> list[dict]:
    frame = pd.read_csv(io.StringIO(text), dtype=str)
    return _normalize_frame(frame, "Date", field)


def _parse_fred_csv(text: str, symbol: str) -> list[dict]:
    frame = pd.read_csv(io.StringIO(text), dtype=str)
    return _normalize_frame(frame, "observation_date", symbol)


def _normalize_frame(frame: pd.DataFrame, date_field: str, value_field: str) -> list[dict]:
    if date_field not in frame or value_field not in frame:
        raise ValueError(f"Response missing required columns: {date_field}, {value_field}")
    dates = pd.to_datetime(frame[date_field], errors="coerce")
    values = pd.to_numeric(frame[value_field].replace(".", None), errors="coerce")
    rows = [
        {"date": dt.date(), "value": float(value)}
        for dt, value in zip(dates, values)
        if not pd.isna(dt) and not pd.isna(value)
    ]
    return sorted(rows, key=lambda row: row["date"])


def _parse_yahoo_chart(text: str) -> list[dict]:
    """Parse non-null daily closes shared by commodity, FX, and crypto proxies."""
    root = json.loads(text)
    try:
        result = root["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError("Yahoo response did not contain chart history") from error
    if len(timestamps) != len(closes):
        raise ValueError(
            "Yahoo response timestamp/close arrays have different lengths: "
            f"{len(timestamps)} != {len(closes)}"
        )
    return [
        {
            "date": datetime.fromtimestamp(timestamp, timezone.utc).date(),
            "value": float(close),
        }
        for timestamp, close in zip(timestamps, closes)
        if timestamp is not None and close is not None
    ]


def _parse_sina_fx_day_kline(text: str, symbol: str) -> list[dict]:
    variable = f"var_{symbol}"
    match = re.fullmatch(
        rf"\s*(?:/\*<script>location\.href='//sina\.com';</script>\*/\s*)?"
        rf"{re.escape(variable)}=\(\"(?P<data>.*)\"\);\s*",
        text,
        flags=re.S,
    )
    if not match:
        raise ValueError(f"Sina FX response did not contain expected variable {variable}")
    rows = []
    seen_dates: set[date] = set()
    for record in match.group("data").split("|"):
        if not record.strip():
            continue
        parts = record.rstrip(",").split(",")
        if len(parts) < 5:
            raise ValueError("Sina FX response contained a malformed daily record")
        observation_date = parse_date(parts[0])
        if observation_date in seen_dates:
            raise ValueError("Sina FX response contained a duplicate date")
        close = float(parts[4])
        if not math.isfinite(close) or close <= 0:
            raise ValueError("Sina FX close must be a positive finite number")
        seen_dates.add(observation_date)
        rows.append({"date": observation_date, "value": close})
    if not rows:
        raise ValueError("Sina FX response did not contain daily data")
    return sorted(rows, key=lambda row: row["date"])


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3, connect=3, read=3, backoff_factor=0.25,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "Mozilla/5.0 (capital-weekly research)"})
    return session


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as file:
            temp_path = Path(file.name)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _response_bytes(response) -> bytes:
    return response.content if hasattr(response, "content") else response.text.encode("utf-8")


def _get(
    session,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, object] | None = None,
):
    attempt = {"method": "GET", "url": url, "status": "attempting"}
    session._macro_attempt_trace.append(attempt)
    request_options = {"timeout": (5, 25)}
    if headers is not None:
        request_options["headers"] = headers
    if params is not None:
        request_options["params"] = params
    response = session.get(url, **request_options)
    session._macro_raw_parts.append(_response_bytes(response))
    response.raise_for_status()
    attempt["status"] = "completed"
    return response


def _macro_http_spec(session, provider: str) -> CommodityHttpSpec:
    policies = getattr(session, "_macro_commodity_http", None)
    if not isinstance(policies, dict):
        policies = load_commodity_http_policies()
        session._macro_commodity_http = policies
    try:
        return policies[provider]
    except KeyError as error:
        raise ValueError(f"Missing commodity HTTP policy: {provider}") from error


def _official_macro_get(
    session,
    url: str,
    provider: str,
    *,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, object] | None = None,
    audit_secrets: tuple[str, ...] = (),
) -> bytes:
    attempt = {"method": "GET", "url": url, "status": "attempting"}
    session._macro_attempt_trace.append(attempt)
    transport_session = getattr(session, "__dict__", {}).get(
        "_macro_official_session", session
    )
    response = official_get(
        transport_session,
        url,
        policy=_macro_http_spec(session, provider).policy,
        headers=headers,
        params=params,
        audit_secrets=audit_secrets,
    )
    session._macro_raw_parts.append(response.body)
    attempt["status"] = "completed"
    attempt["attempts"] = response.trace.attempts
    return response.body


class _MacroEiaClient:
    def __init__(self, session, api_key: str, http: CommodityHttpSpec):
        self.session = session
        self.api_key = api_key
        self.http = http
        self.raw_bodies: list[bytes] = []

    def _get(self, url: str, params: Mapping[str, object]) -> bytes:
        body = _official_macro_get(
            self.session,
            url,
            "eia",
            params=params,
            audit_secrets=(self.api_key,),
        )
        self.raw_bodies.append(body)
        return body

    def fetch_metadata(self, spec, expected):
        required = set(expected)
        identifiers: set[str] = set()
        offset = 0
        expected_total: int | None = None
        while not required <= identifiers:
            body = self._get(
                f"https://api.eia.gov/v2/{spec.route}/facet/series/",
                {
                    "api_key": self.api_key,
                    "offset": offset,
                    "length": spec.page_length,
                },
            )
            payload = json.loads(body.decode("utf-8"))
            values = payload.get("response", {}).get("facets")
            if not isinstance(values, list):
                raise ValueError(
                    f"EIA facet metadata is missing for {spec.route}/series"
                )
            identifiers.update(
                str(item.get("id") or "").strip()
                for item in values
                if isinstance(item, Mapping)
            )
            response = payload.get("response", {})
            total = eia_response_total(
                response,
                offset=offset,
                page_count=len(values),
                requested_length=spec.page_length,
                prior_total=expected_total,
            )
            expected_total = total
            offset += len(values)
            if offset >= total:
                break
            if not values:
                raise ValueError("EIA facet metadata pagination made no progress")
        missing = sorted(required - identifiers)
        if missing:
            raise ValueError(
                f"EIA configured facet is unavailable for {spec.route}/series: "
                + ", ".join(missing)
            )

    def fetch_page(self, spec, *, offset: int, length: int):
        params: dict[str, object] = {
            "api_key": self.api_key,
            "frequency": spec.frequency,
            "data[0]": "value",
            "start": spec.start,
            "end": spec.end,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": offset,
            "length": length,
        }
        for facet, values in spec.facets.items():
            params[f"facets[{facet}][]"] = list(values)
        body = self._get(
            f"https://api.eia.gov/v2/{spec.route}/data/",
            params,
        )
        payload = json.loads(body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("EIA price response must be a JSON object")
        return payload


def _is_official_world_bank_https(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return (
        parsed.scheme.lower() == "https"
        and (host == "worldbank.org" or host.endswith(".worldbank.org"))
        and parsed.username is None
        and parsed.password is None
    )


def _discover_world_bank_monthly_url(text: str, page_url: str) -> str:
    if not _is_official_world_bank_https(page_url):
        raise ValueError("World Bank commodity page must use an official HTTPS host")
    candidates = []
    for href, raw_label in re.findall(
        r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        text,
        flags=re.I | re.S,
    ):
        label = " ".join(_plain_html(raw_label).casefold().split())
        indicates_monthly_prices = (
            label == "monthly prices"
            or all(term in label for term in ("monthly", "historical", "price"))
        )
        if not indicates_monthly_prices:
            continue
        candidate = urljoin(page_url, html.unescape(href).strip())
        parsed = urlparse(candidate)
        if (
            _is_official_world_bank_https(candidate)
            and parsed.path.lower().endswith(".xlsx")
        ):
            candidates.append(candidate)
    unique = list(dict.fromkeys(candidates))
    if len(unique) != 1:
        raise ValueError(
            "World Bank commodity page did not expose one official monthly workbook link"
        )
    return unique[0]


def _post(session, url: str, data=b""):
    attempt = {"method": "POST", "url": url, "status": "attempting"}
    session._macro_attempt_trace.append(attempt)
    response = session.post(url, data=data, timeout=(5, 25))
    session._macro_raw_parts.append(_response_bytes(response))
    response.raise_for_status()
    attempt["status"] = "completed"
    return response


def _parse_chinabond_json(text: str, field: str) -> list[dict]:
    raw = json.loads(text)
    if not isinstance(raw, list):
        raise ValueError("ChinaBond response was not a JSON array")
    return _normalize_frame(pd.DataFrame(raw), "workTime", field)


def _parse_hibor_json(text: str, field: str) -> list[dict]:
    raw = json.loads(text)
    if raw.get("isHoliday") or raw.get(field) in (None, ""):
        return []
    return [{"date": parse_date(raw["date"]), "value": float(raw[field])}]


def _parse_hkma_daily_page(text: str, expected_date: date) -> dict:
    published_dates = re.findall(
        r"Date and Time\s*\([^<]*\)\s*:\s*\d{1,2}:\d{2},\s*"
        r"(\d{2}/\d{2}/\d{4})",
        text,
        flags=re.I,
    )
    expected_display = expected_date.strftime("%d/%m/%Y")
    if expected_display not in published_dates:
        raise ValueError(
            f"HKMA daily page did not publish data for {expected_date.isoformat()}"
        )
    rate_matches = re.findall(
        r"Base Rate\s*\([^<]*\)\s*:</div>\s*"
        r"<div>\s*([0-9]+(?:\.[0-9]+)?)%\s*</div>",
        text,
        flags=re.I,
    )
    if len(rate_matches) != 1:
        raise ValueError("HKMA daily page did not contain one Base Rate")
    value = float(rate_matches[0])
    if not math.isfinite(value) or value < 0:
        raise ValueError("HKMA daily page Base Rate must be finite and non-negative")
    return {"date": expected_date, "value": value}


def _hkma_daily_page_url(day: date) -> str:
    return (
        "https://www.hkma.gov.hk/eng/data-publications-and-research/"
        "data-and-statistics/daily-monetary-statistics/"
        f"{day.year}/{day.month:02d}/ms-{day.strftime('%Y%m%d')}/"
    )


def _fetch_hkma_daily_page_history(
    session: requests.Session,
    today: date,
    failed_api_url: str,
) -> tuple[list[dict], bytes, str]:
    page_urls = []

    def latest_on_or_before(target: date) -> dict:
        for days_back in range(11):
            candidate = target - timedelta(days=days_back)
            url = _hkma_daily_page_url(candidate)
            response = _get(session, url)
            try:
                point = _parse_hkma_daily_page(response.text, candidate)
            except ValueError:
                continue
            page_urls.append(url)
            return point
        raise ValueError(
            "HKMA daily pages did not contain a published value on or before "
            f"{target.isoformat()}"
        )

    latest = latest_on_or_before(today)
    latest_date = latest["date"]
    anchors = [
        latest,
        latest_on_or_before(latest_date - timedelta(days=1)),
        latest_on_or_before(latest_date - timedelta(days=7)),
        latest_on_or_before(latest_date.replace(day=1) - timedelta(days=1)),
        latest_on_or_before(
            latest_date.replace(month=1, day=1) - timedelta(days=1)
        ),
    ]
    history = sorted(
        {point["date"]: point for point in anchors}.values(),
        key=lambda point: point["date"],
    )
    return (
        history,
        b"\n".join(session._macro_raw_parts),
        " | ".join([f"{failed_api_url} [failed]", *page_urls]),
    )


def _parse_lpr_xlsx(content: bytes, field: str) -> list[dict]:
    if not content.startswith(b"PK"):
        raise ValueError("ChinaMoney LPR response was not an OOXML workbook")
    frame = pd.read_excel(io.BytesIO(content), dtype=str)
    return _normalize_frame(frame, "日期", field)


def _parse_nyfed_json(text: str, symbol: str) -> list[dict]:
    raw = json.loads(text)
    rates = raw.get("refRates") or raw.get("rates") or []
    rows = [{"date": parse_date(row["effectiveDate"]), "value": float(row["percentRate"])}
            for row in rates if row.get("type") == symbol and row.get("percentRate") not in (None, "")]
    if not rows:
        raise ValueError(f"NY Fed response contained no {symbol} observations")
    return sorted(rows, key=lambda row: row["date"])


def _parse_ecb_csv(text: str) -> list[dict]:
    return _normalize_frame(pd.read_csv(io.StringIO(text), dtype=str), "TIME_PERIOD", "OBS_VALUE")


def _parse_boe_csv(text: str, symbol: str) -> list[dict]:
    return _normalize_frame(pd.read_csv(io.StringIO(text), dtype=str), "DATE", symbol)


def _parse_hkma_json(text: str, field: str) -> list[dict]:
    raw = json.loads(text)
    if not raw.get("header", {}).get("success"):
        raise ValueError("HKMA response did not report success")
    records = raw.get("result", {}).get("records", [])
    return _normalize_frame(pd.DataFrame(records), "end_of_date", field)


def _parse_boc_json(text: str, symbol: str) -> list[dict]:
    raw = json.loads(text)
    rows = []
    for item in raw.get("observations", []):
        value = item.get(symbol, {}).get("v")
        if value not in (None, ""):
            rows.append({"date": parse_date(item["d"]), "value": float(value)})
    return sorted(rows, key=lambda row: row["date"])


def _parse_snb_csv(text: str, dimension: str) -> list[dict]:
    lines = text.lstrip("\ufeff").splitlines()
    header = next((i for i, line in enumerate(lines) if line.lstrip('"').startswith("Date")), None)
    if header is None:
        raise ValueError("SNB response missing Date header")
    frame = pd.read_csv(io.StringIO("\n".join(lines[header:])), sep=";", dtype=str)
    if "D0" not in frame:
        raise ValueError("SNB response missing D0 selector column")
    frame = frame[frame["D0"] == dimension]
    if frame.empty:
        raise ValueError(f"SNB response contained no exact D0={dimension} rows")
    value_field = "Value" if "Value" in frame else "OBS_VALUE"
    return _normalize_frame(frame, "Date", value_field)


def _parse_boj_json(text: str) -> list[dict]:
    raw = json.loads(text)
    result = raw.get("RESULTSET", raw.get("result", []))
    if isinstance(result, list) and result:
        series = result[0]
        values_block = series.get("VALUES", {})
        if isinstance(values_block, dict) and "SURVEY_DATES" in values_block:
            dates, values = values_block["SURVEY_DATES"], values_block.get("VALUES", [])
        else:
            dates, values = series.get("SURVEY_DATES"), series.get("VALUES")
        if isinstance(dates, list) and isinstance(values, list):
            if len(dates) != len(values):
                raise ValueError("BOJ response had mismatched date and value arrays")
            return [{
                "date": (datetime.strptime(str(day), "%Y%m%d").date()
                         if re.fullmatch(r"\d{8}", str(day)) else parse_date(str(day))),
                "value": float(value),
            } for day, value in zip(dates, values) if value not in (None, "")]
    raise ValueError("BOJ response missing time-series arrays")


def _parse_chinamoney_frr(text: str, symbol: str) -> list[dict]:
    raw = json.loads(text)
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    records = raw.get("records") or data.get("records") or data.get("resultList") or []
    rows = []
    for item in records:
        value = (item.get("frValueMap") or {}).get(symbol)
        if value not in (None, ""):
            rows.append({"date": parse_date(item["lfiProducDate"]), "value": float(value)})
    return sorted(rows, key=lambda row: row["date"])


def _plain_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def _single_iso_date(text: str, provider: str) -> date:
    dates = {parse_date(value) for value in re.findall(r"20\d{2}-\d{1,2}-\d{1,2}", text)}
    for value in re.findall(r"[A-Z][a-z]+ \d{1,2}, 20\d{2}", text):
        dates.add(datetime.strptime(value, "%B %d, %Y").date())
    if len(dates) != 1:
        raise ValueError(f"{provider} announcement did not contain one unambiguous date")
    return dates.pop()


def _parse_boj_policy_announcement(text: str) -> dict:
    plain = _plain_html(text)
    observation_date = _single_iso_date(plain, "BOJ")
    matches = re.findall(
        r"uncollateralized overnight call rate.{0,120}?around\s+(\d+(?:\.\d+)?)\s+percent",
        plain, re.I,
    )
    if len(matches) != 1:
        raise ValueError("BOJ decision did not contain one unambiguous policy target")
    return {"date": observation_date, "value": float(matches[0])}


def _parse_boj_policy_statement_html(text: str, release_date: date | None = None) -> dict:
    # BOJ puts dissenting alternative targets after the first horizontal rule;
    # only the statement body before that boundary is the adopted guideline.
    primary = re.split(r"<hr\b", text, maxsplit=1, flags=re.I)[0]
    plain = _plain_html(primary)
    try:
        return _parse_boj_policy_text(plain)
    except ValueError:
        if release_date is None:
            return _parse_boj_policy_announcement(primary)
        matches = re.findall(
            r"uncollateralized overnight call rate.{0,120}?around\s+(\d+(?:\.\d+)?)\s+percent",
            plain, re.I,
        )
        if len(matches) != 1:
            raise ValueError("BOJ statement body did not contain one adopted target")
        return {"date": release_date, "value": float(matches[0])}


def _parse_boj_policy_text(text: str) -> dict:
    plain = re.sub(r"\s+", " ", text).strip()
    matches = re.findall(
        r"uncollateralized.{0,80}?call rate.{0,160}?around\s+(\d+(?:\.\d+)?)\s+percent",
        plain, re.I,
    )
    effective_dates = set(re.findall(
        r"guideline for money market operations will be effective from\s+([A-Z][a-z]+\s+\d{1,2},\s+20\d{2})",
        plain, re.I,
    ))
    if len(matches) != 1 or len(effective_dates) != 1:
        raise ValueError("BOJ policy PDF did not contain one target and effective date")
    return {
        "date": datetime.strptime(next(iter(effective_dates)).title(), "%B %d, %Y").date(),
        "value": float(matches[0]),
    }


def _parse_boj_policy_pdf(content: bytes) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return _parse_boj_policy_text(text)


def _parse_boj_policy_summary_text(text: str, release_date: date) -> dict:
    plain = re.sub(r"\s+", " ", text).strip()
    matches = re.findall(
        r"Short-term interest rate.{0,160}?around\s+(\d+(?:\.\d+)?)\s*%",
        plain, re.I,
    )
    if len(matches) != 1:
        raise ValueError("BOJ policy summary did not contain one short-term target")
    return {"date": release_date, "value": float(matches[0])}


def _parse_boj_policy_summary_pdf(content: bytes, release_date: date) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return _parse_boj_policy_summary_text(text, release_date)


def _parse_boj_policy_candidates(candidates: list[tuple[str, bytes]]) -> list[dict]:
    history = []
    for url, content in sorted(candidates, key=lambda item: item[0]):
        match = re.search(r"/k(\d{2})(\d{2})(\d{2})b\.pdf$", url)
        if not match:
            raise ValueError(f"BOJ decision candidate had unrecognized filename: {url}")
        release_date = date(2000 + int(match.group(1)), int(match.group(2)), int(match.group(3)))
        try:
            history.append(_parse_boj_policy_summary_pdf(content, release_date))
        except ValueError as error:
            raise ValueError(f"BOJ decision candidate could not be parsed: {url}") from error
    return history


def _parse_pboc_omo_announcement(text: str) -> dict:
    description = re.search(
        r'<meta\b(?=[^>]*\bname\s*=\s*["\']Description["\'])(?=[^>]*\bcontent\s*=\s*["\']([^"\']+)["\'])[^>]*>',
        text,
        re.I,
    )
    plain = html.unescape(description.group(1)) if description else _plain_html(text)
    dates = re.findall(r"(20\d{2})年(\d{1,2})月(\d{1,2})日", plain)
    tenors = re.findall(r"期限\s*(\d+)天", plain)
    rates = re.findall(r"操作利率\s*(\d+(?:\.\d+)?)\s*%", plain)
    if not tenors or not rates:
        bound_rows = re.findall(
            r"期限\s*操作\s*利率.*?(\d+)\s*天\s*(\d+(?:\.\d+)?)\s*%",
            plain,
            re.I,
        )
        if len(bound_rows) == 1:
            tenors, rates = [bound_rows[0][0]], [bound_rows[0][1]]
    if len(dates) != 1 or len(tenors) != 1 or len(rates) != 1:
        raise ValueError("PBOC OMO announcement did not contain one bound operation record")
    if tenors[0] != "7":
        raise RecognizedNonSevenDayOperation("PBOC OMO announcement was not a 7-day operation")
    year, month, day = map(int, dates[0])
    return {"date": date(year, month, day), "value": float(rates[0])}


def _parse_rbi_current_rate(text: str) -> dict:
    plain = _plain_html(text)
    date_matches = re.findall(r"As on (\d{1,2} [A-Za-z]+ 20\d{2})", plain, re.I)
    rate_matches = re.findall(r"Policy Repo Rate\s*(\d+(?:\.\d+)?)\s*%", plain, re.I)
    if len(date_matches) != 1 or len(rate_matches) != 1:
        raise ValueError("RBI current-rates page did not contain one dated repo rate")
    return {"date": datetime.strptime(date_matches[0], "%d %B %Y").date(), "value": float(rate_matches[0])}


def _parse_rbi_history(text: str) -> list[dict]:
    try:
        tables = pd.read_html(io.StringIO(text))
    except ValueError as error:
        raise ValueError("RBI history contained no tables") from error
    for frame in tables:
        frame.columns = [str(value).strip() for value in frame.columns]
        date_field = next((value for value in frame.columns if "effective date" in value.lower()), None)
        rate_field = next((value for value in frame.columns if value.lower() in {"repo", "policy repo rate"}), None)
        if date_field and rate_field:
            dates = pd.to_datetime(frame[date_field], errors="coerce", dayfirst=True)
            values = pd.to_numeric(frame[rate_field], errors="coerce")
            rows = sorted(
                [{"date": day.date(), "value": float(value)} for day, value in zip(dates, values)
                 if not pd.isna(day) and not pd.isna(value)], key=lambda row: row["date"]
            )
            if rows:
                return rows
    raise ValueError("RBI history missing Effective Date and Repo columns")


def _official_links(text: str, base_url: str, pattern: str) -> list[str]:
    links = [urljoin(base_url, href) for href in re.findall(r'href=["\']([^"\']+)["\']', text, re.I)]
    return list(dict.fromkeys(link for link in links if re.search(pattern, link)))


def _parse_rate_xlsx(content: bytes, symbol: str) -> list[dict]:
    if not content.startswith(b"PK"):
        raise ValueError("Official rate response was not an OOXML workbook")
    sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, header=None)
    for raw in sheets.values():
        for row_index in range(min(20, len(raw))):
            labels = [str(value).strip() for value in raw.iloc[row_index].tolist()]
            if symbol in labels:
                frame = raw.iloc[row_index + 1:].copy(); frame.columns = labels
                date_field = next((name for name in labels if "date" in name.lower()), labels[0])
                return _normalize_frame(frame, date_field, symbol)
        # RBA tables put series identifiers in a metadata row and dates in column A.
        for column in raw.columns:
            if raw[column].astype(str).str.strip().eq(symbol).any():
                values = pd.to_numeric(raw[column], errors="coerce")
                dates = pd.to_datetime(raw.iloc[:, 0], errors="coerce")
                return sorted([{"date": day.date(), "value": float(value)} for day, value in zip(dates, values)
                               if not pd.isna(day) and not pd.isna(value)], key=lambda row: row["date"])
    raise ValueError(f"Official workbook missing series {symbol}")


def _carry_forward_business_daily(history: list[dict], end_date: date) -> list[dict]:
    points = sorted(
        ((parse_date(row["date"]), float(row["value"])) for row in history),
        key=lambda item: item[0],
    )
    if not points:
        return []
    result = []
    point_index = 0
    current_value = None
    day = points[0][0]
    while day <= end_date:
        while point_index < len(points) and points[point_index][0] <= day:
            current_value = points[point_index][1]
            point_index += 1
        if day.weekday() < 5 and current_value is not None:
            result.append({"date": day, "value": current_value})
        day += timedelta(days=1)
    return result


def _fetch_config_history(
    config: MacroAssetConfig,
    session: requests.Session,
    as_of_date: date | None = None,
):
    today = as_of_date or date.today()
    start = today - timedelta(days=550)
    shared = getattr(session, "_macro_payload_cache", None)
    if not isinstance(shared, dict):
        shared = session._macro_payload_cache = {}

    def cached(method: str, url: str):
        key = (method, url)
        if key not in shared:
            response = _get(session, url) if method == "GET" else _post(session, url)
            shared[key] = (_response_bytes(response), response.text)
        else:
            session._macro_attempt_trace.append(
                {"method": method, "url": url, "status": "cache_hit"}
            )
            session._macro_raw_parts.append(shared[key][0])
        return shared[key]
    if config.provider in {"us_treasury", "us_treasury_real"}:
        if config.provider == "us_treasury":
            fields = {
                "2-year": "2 Yr",
                "5-year": "5 Yr",
                "10-year": "10 Yr",
                "30-year": "30 Yr",
            }
            curve_type = "daily_treasury_yield_curve"
        else:
            fields = {"5-year": "5 YR", "10-year": "10 YR"}
            curve_type = "daily_treasury_real_yield_curve"
        try:
            field = fields[config.provider_symbol]
        except KeyError as error:
            raise ValueError(
                f"Unsupported {config.provider} symbol: {config.provider_symbol}"
            ) from error
        responses = []
        history = []
        urls = []
        for year in (today.year - 1, today.year):
            url = (
                f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                f"daily-treasury-rates.csv/{year}/all?type={curve_type}&"
                f"field_tdr_date_value={year}&page&_format=csv"
            )
            response = _get(session, url)
            history.extend(_parse_treasury_csv(response.text, field))
            responses.append(_response_bytes(response))
            urls.append(url)
        return history, b"\n".join(responses), " | ".join(urls)
    if config.provider == "fred":
        url = (f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={config.provider_symbol}"
               f"&cosd={start.isoformat()}&coed={today.isoformat()}")
        response = _get(
            session,
            url,
            headers={"User-Agent": requests.utils.default_user_agent()},
        )
        return _parse_fred_csv(response.text, config.provider_symbol), _response_bytes(response), url
    if config.provider == "eia_v2":
        if not re.fullmatch(r"[a-z0-9][a-z0-9/_-]*", config.provider_route):
            raise ValueError(f"Invalid EIA v2 provider route: {config.provider_route}")
        api_key = os.environ.get("EIA_API_KEY", "").strip()
        if not api_key:
            raise ValueError("EIA_API_KEY is required for official EIA prices")
        if not config.source_description.strip():
            raise ValueError(f"{config.series_code} requires source_description")
        cached_eia = getattr(session, "_macro_eia_prices", None)
        if not isinstance(cached_eia, dict):
            cached_eia = {}
        if config.provider_symbol not in cached_eia:
            price_configs = getattr(session, "_macro_eia_configs", None)
            if not isinstance(price_configs, list) or not price_configs:
                price_configs = [config]
            price_configs = [
                item
                for item in price_configs
                if item.provider_route == config.provider_route
                and item.frequency == config.frequency
            ]
            http = _macro_http_spec(session, "eia")
            if http.request_batch_size is None or http.page_length is None:
                raise ValueError("EIA HTTP policy requires batching and pagination")
            batch_rows = [
                {
                    "route": item.provider_route,
                    "frequency": item.frequency,
                    "facets": {"series": item.provider_symbol},
                }
                for item in price_configs
            ]
            specs = build_eia_batch_specs(
                batch_rows,
                request_batch_size=http.request_batch_size,
                page_length=http.page_length,
                start=start.isoformat(),
                end=today.isoformat(),
            )
            expected = {
                item.provider_symbol: {
                    "facets": {"series": item.provider_symbol},
                    "source_description": item.source_description,
                    "expected_unit": item.level_unit,
                }
                for item in price_configs
            }
            client = _MacroEiaClient(session, api_key, http)
            pages = fetch_eia_batches(client, specs, expected_metadata=expected)
            all_rows = [
                row
                for payload in pages
                for row in payload["response"]["data"]
            ]
            fetched = {
                item.provider_symbol: (
                    json.dumps(
                        {"response": {"data": [
                            row
                            for row in all_rows
                            if str(row.get("series") or "") == item.provider_symbol
                        ]}},
                        separators=(",", ":"),
                    ),
                    b"\n".join(client.raw_bodies),
                )
                for item in price_configs
            }
            cached_eia.update(fetched)
            session._macro_eia_prices = cached_eia
        try:
            text, raw = cached_eia[config.provider_symbol]
        except KeyError as error:
            raise ValueError(
                f"EIA batch did not cache configured series: {config.provider_symbol}"
            ) from error
        url = f"https://api.eia.gov/v2/{config.provider_route.strip('/')}/data/"
        return (
            parse_eia_price_series(
                text,
                config.provider_symbol,
                config.level_unit,
                expected_description=config.source_description,
            ),
            raw,
            url,
        )
    if config.provider == "world_bank_pink_sheet":
        def official_cached(url: str) -> tuple[bytes, str]:
            key = ("OFFICIAL_GET", url)
            if key not in shared:
                body = _official_macro_get(
                    session, url, "world_bank_pink_sheet"
                )
                shared[key] = (body, body.decode("utf-8", errors="strict"))
            else:
                session._macro_attempt_trace.append(
                    {"method": "GET", "url": url, "status": "cache_hit"}
                )
                session._macro_raw_parts.append(shared[key][0])
            return shared[key]

        page_content, page_text = official_cached(config.source_url)
        del page_content
        workbook_url = _discover_world_bank_monthly_url(
            page_text,
            config.source_url,
        )
        key = ("OFFICIAL_GET", workbook_url)
        if key not in shared:
            workbook_content = _official_macro_get(
                session, workbook_url, "world_bank_pink_sheet"
            )
            shared[key] = (workbook_content, "")
        else:
            workbook_content = shared[key][0]
            session._macro_attempt_trace.append(
                {"method": "GET", "url": workbook_url, "status": "cache_hit"}
            )
            session._macro_raw_parts.append(workbook_content)
        parsed = getattr(session, "_macro_world_bank_prices", None)
        if not isinstance(parsed, dict):
            requested_columns = getattr(
                session,
                "_macro_world_bank_columns",
                {config.provider_symbol: config.level_unit},
            )
            parsed = parse_world_bank_monthly_prices(
                workbook_content,
                requested_columns,
            )
            session._macro_world_bank_prices = parsed
        try:
            history = parsed[config.provider_symbol]
        except KeyError as error:
            raise ValueError(
                "World Bank workbook was not parsed for requested column: "
                f"{config.provider_symbol}"
            ) from error
        return history, workbook_content, workbook_url
    if config.provider == "yahoo_chart":
        symbol = requests.utils.quote(config.provider_symbol, safe="")
        period1 = int(datetime.combine(today - timedelta(days=550), datetime.min.time(), tzinfo=timezone.utc).timestamp())
        period2 = int(datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp())
        url = (
            f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1={period1}"
            f"&period2={period2}&interval=1d&events=history"
        )
        response = _get(session, url)
        return _parse_yahoo_chart(response.text), _response_bytes(response), url
    if config.provider == "sina_fx":
        symbol = requests.utils.quote(config.provider_symbol, safe="")
        url = (
            "https://vip.stock.finance.sina.com.cn/forex/api/jsonp.php/"
            f"var_{symbol}=/NewForexService.getDayKLine?symbol={symbol}"
        )
        response = _get(session, url)
        history = _parse_sina_fx_day_kline(response.text, config.provider_symbol)
        return history, _response_bytes(response), url
    if config.provider == "china_bond":
        field = {"2Y": "twoYear", "5Y": "fiveYear", "10Y": "tenYear", "30Y": "thirtyYear"}[config.provider_symbol]
        start = today - timedelta(days=550)
        history, contents, urls = [], [], []
        while start <= today:
            end = min(start + timedelta(days=364), today)
            url = (
                "https://yield.chinabond.com.cn/cbweb-mn/pgxh/historyQuery?"
                f"startDate={start.isoformat()}&&endDate={end.isoformat()}&&gjqx=2,5,10,30&&locale=en_US"
            )
            response = _post(session, url)
            history.extend(_parse_chinabond_json(response.text, field))
            contents.append(_response_bytes(response)); urls.append(f"POST {url}")
            start = end + timedelta(days=1)
        return history, b"\n".join(contents), " | ".join(urls)
    if config.provider == "pboc_lpr":
        fields = {"1Y": "1Y", "5Y+": "5Y"}
        if config.provider_symbol not in fields:
            raise ValueError(f"Unsupported pboc_lpr symbol: {config.provider_symbol}")
        field = fields[config.provider_symbol]
        start = today - timedelta(days=550)
        url = (
            "https://www.chinamoney.com.cn/dqs/rest/cm-u-bk-currency/LprHisExcel?lang=CN"
            f"&strStartDate={start.isoformat()}&strEndDate={today.isoformat()}"
        )
        response = _post(session, url)
        content = _response_bytes(response)
        history = _parse_lpr_xlsx(content, field)
        return _carry_forward_business_daily(history, today), content, f"POST {url}"
    if config.provider == "hkab_hibor":
        fields = {"1M": "1 Month", "3M": "3 Months"}
        if config.provider_symbol not in fields:
            raise ValueError(f"Unsupported hkab_hibor symbol: {config.provider_symbol}")
        field = fields[config.provider_symbol]
        history, contents, urls = [], [], []
        start_of_week = today - timedelta(days=today.weekday())
        cutoffs = (today + timedelta(days=1), start_of_week, today.replace(day=1), today.replace(month=1, day=1))
        days = sorted({
            cutoff - timedelta(days=offset)
            for cutoff in cutoffs
            for offset in range(1, 15)
        })
        cache = getattr(session, "_macro_hkab_cache", None)
        if not isinstance(cache, dict):
            cache = session._macro_hkab_cache = {}
        for day in days:
            url = f"https://www.hkab.org.hk/api/hibor?year={day.year}&month={day.month}&day={day.day}"
            if day not in cache:
                response = _get(session, url)
                cache[day] = _response_bytes(response)
            content = cache[day]
            history.extend(_parse_hibor_json(content.decode("utf-8"), field))
            contents.append(content); urls.append(url)
        return history, b"\n".join(contents), " | ".join(urls)
    if config.provider == "nyfed_rates":
        market = {"EFFR": "unsecured/effr", "SOFR": "secured/sofr"}.get(config.provider_symbol)
        if market is None:
            raise ValueError(f"Unsupported nyfed_rates symbol: {config.provider_symbol}")
        url = (f"https://markets.newyorkfed.org/api/rates/{market}/search.json?"
               f"startDate={start.isoformat()}&endDate={today.isoformat()}&type=rate")
        content, text = cached("GET", url)
        return _parse_nyfed_json(text, config.provider_symbol), content, url
    if config.provider == "ecb":
        flow, key = config.provider_symbol.split(".", 1)
        url = (f"https://data-api.ecb.europa.eu/service/data/{flow}/{key}?"
               f"startPeriod={start.isoformat()}&endPeriod={today.isoformat()}&format=csvdata")
        content, text = cached("GET", url)
        return _parse_ecb_csv(text), content, url
    if config.provider == "boe_iadb":
        symbols = "IUDBEDR,IUDSOIA"
        url = ("https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes"
               f"&Datefrom={start.strftime('%d/%b/%Y')}&Dateto={today.strftime('%d/%b/%Y')}"
               f"&SeriesCodes={symbols}&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N")
        content, text = cached("GET", url)
        return _parse_boe_csv(text, config.provider_symbol), content, url
    if config.provider == "hkma":
        base = ("https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/"
                "daily-figures-interbank-liquidity")
        page_size = 1000
        history, contents, urls, offset = [], [], [], 0
        seen_offsets = set()
        try:
            for _ in range(MAX_PROVIDER_PAGES):
                if offset in seen_offsets:
                    raise ValueError(f"HKMA pagination repeated offset {offset}")
                seen_offsets.add(offset)
                url = (
                    f"{base}?from={start.isoformat()}&to={today.isoformat()}"
                    f"&pagesize={page_size}&offset={offset}"
                )
                content, text = cached("GET", url)
                raw = json.loads(text); records = raw.get("result", {}).get("records", [])
                history.extend(_parse_hkma_json(text, config.provider_symbol))
                contents.append(content); urls.append(url)
                total = raw.get("header", {}).get("total_count")
                if not records or (total is not None and offset + len(records) >= int(total)):
                    break
                if total is None and len(records) < page_size:
                    break
                next_offset = raw.get("header", {}).get("next_offset", offset + len(records))
                if int(next_offset) <= offset:
                    raise ValueError(f"HKMA pagination repeated offset {next_offset}")
                offset = int(next_offset)
            else:
                raise ValueError(f"HKMA pagination exceeded {MAX_PROVIDER_PAGES} pages")
        except requests.RequestException:
            return _fetch_hkma_daily_page_history(session, today, url)
        return _carry_forward_business_daily(history, today), b"\n".join(contents), " | ".join(urls)
    if config.provider == "boc_valet":
        symbols = "V39079,AVG.INTWO"
        url = f"https://www.bankofcanada.ca/valet/observations/{symbols}/json?start_date={start.isoformat()}&end_date={today.isoformat()}"
        content, text = cached("GET", url)
        history = _parse_boc_json(text, config.provider_symbol)
        if config.provider_symbol == "V39079":
            history = _carry_forward_business_daily(history, today)
        return history, content, url
    if config.provider == "snb_cube":
        cube, selector = config.provider_symbol.split(":", 1)
        dimension = selector.split("=", 1)[1]
        url = f"https://data.snb.ch/api/cube/{cube}/data/csv/en"
        content, text = cached("GET", url)
        return _carry_forward_business_daily(_parse_snb_csv(text, dimension), today), content, url
    if config.provider in {"rba_xlsx", "rbnz_xlsx"}:
        url = ("https://www.rba.gov.au/statistics/tables/xls/f01hist.xlsx" if config.provider == "rba_xlsx"
               else "https://www.rbnz.govt.nz/-/media/project/sites/rbnz/files/statistics/series/b/b2/hb2-daily-close.xlsx")
        content, _ = cached("GET", url)
        history = _parse_rate_xlsx(content, config.provider_symbol)
        if config.provider == "rbnz_xlsx" or config.provider_symbol == "FIRMMCRT":
            history = _carry_forward_business_daily(history, today)
        return history, content, url
    if config.provider == "boj_api":
        database, symbol = config.provider_symbol.split(":", 1)
        base = (f"https://www.stat-search.boj.or.jp/api/v1/getDataCode?lang=en&db={database}"
                f"&code={symbol}&startDate={start.strftime('%Y%m')}&endDate={today.strftime('%Y%m')}")
        history, contents, urls, next_position = [], [], [], None
        seen_positions = set()
        for _ in range(MAX_PROVIDER_PAGES):
            url = base + (f"&startPosition={next_position}" if next_position else "")
            content, text = cached("GET", url)
            history.extend(_parse_boj_json(text)); contents.append(content); urls.append(url)
            raw = json.loads(text); next_position = raw.get("NEXTPOSITION")
            if not next_position:
                break
            if next_position in seen_positions:
                raise ValueError(f"BOJ pagination repeated next position {next_position}")
            seen_positions.add(next_position)
        else:
            raise ValueError(f"BOJ pagination exceeded {MAX_PROVIDER_PAGES} pages")
        return history, b"\n".join(contents), " | ".join(urls)
    if config.provider == "chinamoney_frr":
        if config.provider_symbol != "FDR007":
            raise ValueError(f"Unsupported chinamoney_frr symbol: {config.provider_symbol}")
        url = "https://www.chinamoney.com.cn/ags/ms/cm-u-bk-currency/FrrHis"
        # The official endpoint rejects (with HTTP 200 and records=[]) ranges
        # starting more than one year ago.
        frr_start = max(start, today - timedelta(days=364))
        response = _post(session, url, data={
            "lang": "CN", "startDate": frr_start.isoformat(), "endDate": today.isoformat()
        })
        content, text = _response_bytes(response), response.text
        return _parse_chinamoney_frr(text, "FDR007"), content, f"POST {url}"
    if config.provider == "boj_policy":
        index_url = "https://www.boj.or.jp/en/mopo/mpmdeci/index.htm"
        index_content, index_text = cached("GET", index_url)
        archive_url = "https://www.boj.or.jp/en/mopo/mpmdeci/state_all/index.htm"
        archive_content, archive_text = cached("GET", archive_url)
        # BOJ's archive page is occasionally served without its content links;
        # yearly official archive URLs are stable and bounded by the requested period.
        year_links = [
            f"https://www.boj.or.jp/en/mopo/mpmdeci/state_{year}/index.htm"
            for year in range(start.year, today.year + 1)
        ]
        history, contents, urls = [], [index_content, archive_content], [index_url, archive_url]
        links, pdf_links = [], []
        for year_url in year_links:
            content, text = cached("GET", year_url); contents.append(content); urls.append(year_url)
            links.extend(_official_links(text, year_url, r"/mopo/mpmdeci/state_\d{4}/k\d{6}a\.htm$"))
            for href, label in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, re.I | re.S):
                if re.search(r"Change in the Guideline|Decision at the", _plain_html(label), re.I):
                    candidate_url = urljoin(year_url, href)
                    if candidate_url.lower().endswith(".pdf"):
                        pdf_links.append(candidate_url)
        candidates = []
        for url in dict.fromkeys(links):
            content, text = cached("GET", url); contents.append(content); urls.append(url)
            filename_date = re.search(r"/k(\d{2})(\d{2})(\d{2})a\.htm$", url)
            release_date = (date(2000 + int(filename_date.group(1)), int(filename_date.group(2)), int(filename_date.group(3)))
                            if filename_date else None)
            try:
                candidates.append(_parse_boj_policy_statement_html(text, release_date))
            except ValueError as error:
                raise ValueError(f"BOJ decision candidate could not be parsed: {url}") from error
        for url in dict.fromkeys(pdf_links):
            content, _ = cached("GET", url); contents.append(content); urls.append(url)
            filename_date = re.search(r"/k(\d{2})(\d{2})(\d{2})[a-z]\.pdf$", url)
            if not filename_date:
                raise ValueError(f"BOJ decision candidate had unrecognized filename: {url}")
            release_date = date(2000 + int(filename_date.group(1)), int(filename_date.group(2)), int(filename_date.group(3)))
            try:
                try:
                    candidates.append(_parse_boj_policy_pdf(content))
                except ValueError:
                    candidates.append(_parse_boj_policy_summary_pdf(content, release_date))
            except ValueError as error:
                raise ValueError(f"BOJ decision candidate could not be parsed: {url}") from error
        if not candidates:
            raise ValueError("BOJ decision archive yielded no policy-statement candidates")
        for point in candidates:
            if start <= point["date"] <= today:
                history.append(point)
        if not history:
            raise ValueError("BOJ decision archive yielded no unambiguous policy targets")
        return _carry_forward_business_daily(history, today), b"\n".join(contents), " | ".join(urls)
    if config.provider == "pboc_omo":
        base = "https://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/"
        history, contents, urls, links = [], [], [], []
        covered_start = False
        list_url = urljoin(base, "index.html")
        archive_page = 1
        for page in range(MAX_PROVIDER_PAGES):
            try:
                content, text = cached("GET", list_url)
            except requests.RequestException:
                if not covered_start:
                    raise ValueError(f"PBOC OMO archive request failed before covering {start}: {list_url}")
                raise
            contents.append(content); urls.append(list_url)
            page_links = _official_links(text, list_url, r"/125475/\d+/index\.html$")
            if not page_links:
                raise ValueError(f"PBOC OMO archive page had no recognized links before covering {start}: {list_url}")
            links.extend(page_links)
            plain = _plain_html(text)
            page_dates = [date(*map(int, match)) for match in re.findall(
                r"(20\d{2})年(\d{1,2})月(\d{1,2})日", plain
            )]
            page_dates.extend(parse_date(value) for value in re.findall(r"20\d{2}-\d{2}-\d{2}", plain))
            if page_dates and min(page_dates) <= start:
                covered_start = True
                break
            pager_links = re.findall(r"(/[^\"']*/125475/\d+-(\d+)\.html)", text)
            next_match = next((path for path, number in pager_links if int(number) == archive_page + 1), None)
            if next_match:
                archive_page += 1
                list_url = urljoin(list_url, next_match)
            else:
                # Compatibility with older/static mirrors that omit the live archive pager.
                list_url = urljoin(base, f"index{page + 1}.html")
        if not covered_start:
            raise ValueError(f"PBOC OMO pagination exceeded {MAX_PROVIDER_PAGES} pages before covering {start}")
        for url in dict.fromkeys(links):
            content, text = cached("GET", url); contents.append(content); urls.append(url)
            try:
                point = _parse_pboc_omo_announcement(content.decode("utf-8"))
            except RecognizedNonSevenDayOperation:
                continue
            except (UnicodeDecodeError, ValueError) as error:
                raise ValueError(f"PBOC OMO announcement could not be parsed: {url}") from error
            if start <= point["date"] <= today:
                history.append(point)
        if not history:
            raise ValueError("PBOC OMO archive yielded no unambiguous 7-day operations")
        return _carry_forward_business_daily(history, today), b"\n".join(contents), " | ".join(urls)
    if config.provider == "rbi_policy":
        current_url = "https://www.rbi.org.in/home.aspx"
        history_url = "https://www.rbi.org.in/Scripts/PublicationsView.aspx?Id=22517"
        current_content, current_text = cached("GET", current_url)
        history_content, history_text = cached("GET", history_url)
        history = _parse_rbi_history(history_text)
        current = _parse_rbi_current_rate(current_text)
        history = list({point["date"]: point for point in history + [current]}.values())
        history = [point for point in history if point["date"] <= today]
        return (_carry_forward_business_daily(history, today),
                current_content + b"\n" + history_content, current_url + " | " + history_url)
    raise ValueError(f"Unsupported provider: {config.provider}")


def _iso(value):
    return value.isoformat() if value else None


def _snapshot_fields(snapshot) -> dict:
    return {
        "latest_date": _iso(snapshot.latest_date), "latest_value": snapshot.latest_value,
        "daily_base_date": _iso(snapshot.daily_base_date), "daily_base_value": snapshot.daily_base_value,
        "daily_change": snapshot.daily_change,
        "weekly_base_date": _iso(snapshot.weekly_base_date), "weekly_base_value": snapshot.weekly_base_value,
        "weekly_change": snapshot.weekly_change,
        "mtd_base_date": _iso(snapshot.mtd_base_date), "mtd_base_value": snapshot.mtd_base_value,
        "mtd_change": snapshot.mtd_change,
        "ytd_base_date": _iso(snapshot.ytd_base_date), "ytd_base_value": snapshot.ytd_base_value,
        "ytd_change": snapshot.ytd_change, "change_unit": snapshot.change_unit,
        "qc_flag": snapshot.qc_flag,
    }


def _attempt_provenance(trace: list[dict], fallback: str) -> str:
    if not trace:
        return sanitize_audit_text(fallback)
    return " | ".join(
        sanitize_audit_text(
            f'{attempt["method"]} {attempt["url"]} [{attempt["status"]}]'
        )
        for attempt in trace
    )


def _cache_raw_failure(raw_path, config, raw_parts):
    if raw_path is None or not raw_parts:
        return "NOT_WRITTEN", ""
    try:
        _atomic_write_bytes(
            raw_path / f"{config.series_code}.raw",
            sanitize_audit_bytes(b"\n".join(raw_parts)),
        )
        return "OK", ""
    except Exception as cache_error:
        return "CACHE_WRITE_FAILED", sanitize_audit_text(cache_error)


def _source_audit_metadata(
    config: MacroAssetConfig,
    known_as_of: str | None,
    *,
    warnings: str = "",
) -> dict:
    if str(config.freshness_days).strip():
        try:
            freshness_days = int(str(config.freshness_days).strip())
        except ValueError as error:
            raise ValueError(
                f"{config.series_code} freshness_days must be a positive integer"
            ) from error
        if freshness_days <= 0:
            raise ValueError(
                f"{config.series_code} freshness_days must be a positive integer"
            )
    else:
        freshness_days = {
            "daily": 7,
            "weekly": 14,
            "monthly": 45,
            "quarterly": 120,
            "event": 365,
        }.get(config.frequency)
    return {
        "provider": config.provider,
        "provider_symbol": config.provider_symbol,
        "source_tier": "public",
        "requiredness": "required",
        "provider_version": "1.0.0",
        "schema_version": "macro-asset-v2",
        "frequency": config.frequency,
        "freshness_days": freshness_days,
        "known_as_of": known_as_of,
        "warnings": sanitize_audit_text(warnings),
        "calculation_id": config.calculation_id,
        "formula_version": config.formula_version,
        "input_series_codes": config.input_series_codes,
    }


def fetch_macro_asset_bundle(
    universe_path: str | Path | None = DEFAULT_UNIVERSE_PATH,
    raw_dir: str | Path | None = None,
    as_of_date: date | None = None,
    *,
    allow_partial: bool = False,
) -> MacroAssetBundle:
    session = _session()
    session._macro_official_session = requests.Session()
    if isinstance(getattr(session, "headers", None), Mapping):
        session._macro_official_session.headers.update(session.headers)
    detail_rows = []
    source_rows = []
    histories = {}
    price_histories = {}
    raw_path = Path(raw_dir) if raw_dir is not None else None
    universe = load_macro_asset_universe(universe_path)
    session._macro_commodity_http = load_commodity_http_policies(
        universe_path if universe_path is not None and Path(universe_path).suffix == ".json" else None
    )
    session._macro_eia_configs = [
        config for config in universe if config.provider == "eia_v2"
    ]
    session._macro_world_bank_columns = {
        config.provider_symbol: config.level_unit
        for config in universe
        if config.provider == "world_bank_pink_sheet"
    }
    for config in universe:
        started = datetime.now()
        url = config.source_url
        raw = None
        session._macro_attempt_trace = []
        session._macro_raw_parts = []
        try:
            if config.provider == "calculated":
                definition = CALCULATED_SERIES.get(config.series_code)
                if definition is None:
                    raise ValueError(
                        f"Unknown calculated macro series: {config.series_code}"
                    )
                input_codes, calculator, formula_version = definition
                declared_inputs = tuple(
                    code
                    for code in config.input_series_codes.split("|")
                    if code
                )
                if config.calculation_id != CALCULATION_IDS[config.series_code]:
                    raise ValueError(
                        f"{config.series_code} calculation_id does not match registry"
                    )
                if config.formula_version != formula_version:
                    raise ValueError(
                        f"{config.series_code} formula_version does not match registry"
                    )
                if declared_inputs != input_codes:
                    raise ValueError(
                        f"{config.series_code} input_series_codes do not match registry"
                    )
                history = align_series_histories(
                    histories,
                    input_codes,
                    calculator,
                )
                raw = json.dumps(history, default=str).encode("utf-8")
                url = CALCULATED_SOURCE_REFERENCES[config.series_code]
            else:
                if any(
                    (
                        config.calculation_id,
                        config.formula_version,
                        config.input_series_codes,
                    )
                ):
                    raise ValueError(
                        f"Observed series {config.series_code} must not declare a calculation"
                    )
                if as_of_date is None:
                    history, raw, url = _fetch_config_history(config, session)
                else:
                    history, raw, url = _fetch_config_history(
                        config, session, as_of_date=as_of_date
                    )
            if as_of_date is not None:
                history = [
                    point
                    for point in history
                    if parse_date(point["date"]) <= as_of_date
                ]
            snapshot = calculate_macro_snapshot(history, config.change_unit)
            if config.provider == "world_bank_pink_sheet":
                if not str(config.freshness_days).strip():
                    raise ValueError(
                        f"{config.series_code} requires configured freshness_days"
                    )
                freshness_days = int(str(config.freshness_days).strip())
                target_date = as_of_date or date.today()
                if (target_date - snapshot.latest_date).days > freshness_days:
                    raise ValueError(
                        f"{config.series_code} is stale beyond configured "
                        f"{freshness_days} calendar days"
                    )
            histories[config.series_code] = history
            price_histories[config.series_code] = [
                {
                    **point,
                    "known_as_of": point.get("known_as_of")
                    or config.known_as_of
                    or None,
                    "source": config.source,
                    "source_url": sanitize_audit_text(url),
                    "qc_flag": "OK",
                }
                for point in history
            ]
            raw_cache_status = "DISABLED"
            raw_cache_error = ""
            if raw_path is not None:
                try:
                    _atomic_write_bytes(
                        raw_path / f"{config.series_code}.raw",
                        sanitize_audit_bytes(raw),
                    )
                    raw_cache_status = "OK"
                except Exception as cache_error:
                    raw_cache_status = "CACHE_WRITE_FAILED"
                    raw_cache_error = sanitize_audit_text(cache_error)
            detail = asdict(config)
            detail.pop("freshness_days", None)
            detail.pop("source_description", None)
            detail.update(_snapshot_fields(snapshot))
            detail["source_url"] = sanitize_audit_text(url)
            detail_rows.append(detail)
            source_rows.append({
                "series_code": config.series_code, "sort_order": config.sort_order,
                "source": config.source, "status": "OK", "error": "",
                "observations": len(history), "latest_date": _iso(snapshot.latest_date),
                "latest_value": snapshot.latest_value,
                "source_url": sanitize_audit_text(url),
                "elapsed_ms": int((datetime.now() - started).total_seconds() * 1000),
                "raw_cache_status": raw_cache_status, "raw_cache_error": raw_cache_error,
                **_source_audit_metadata(
                    config,
                    _iso(snapshot.latest_date),
                    warnings=raw_cache_error,
                ),
            })
        except Exception as error:
            url = _attempt_provenance(session._macro_attempt_trace, url)
            raw_parts = [raw] if raw is not None else session._macro_raw_parts
            raw_cache_status, raw_cache_error = _cache_raw_failure(
                raw_path, config, raw_parts
            )
            detail = asdict(config)
            detail.pop("freshness_days", None)
            for field in (
                "latest_date", "latest_value", "daily_base_date", "daily_base_value", "daily_change",
                "weekly_base_date", "weekly_base_value", "weekly_change", "mtd_base_date",
                "mtd_base_value", "mtd_change", "ytd_base_date", "ytd_base_value", "ytd_change",
            ):
                detail[field] = None
            safe_error = sanitize_audit_text(error)
            safe_url = sanitize_audit_text(url)
            detail.update({"qc_flag": "FETCH_FAILED", "source_url": safe_url})
            detail_rows.append(detail)
            source_rows.append({
                "series_code": config.series_code, "sort_order": config.sort_order,
                "source": config.source, "status": "FETCH_FAILED", "error": safe_error,
                "observations": 0, "latest_date": None, "latest_value": None,
                "source_url": safe_url,
                "elapsed_ms": int((datetime.now() - started).total_seconds() * 1000),
                "raw_cache_status": raw_cache_status,
                "raw_cache_error": raw_cache_error,
                **_source_audit_metadata(
                    config,
                    None,
                    warnings=raw_cache_error,
                ),
            })
    detail = pd.DataFrame(detail_rows)
    source_log = pd.DataFrame(source_rows)
    failures = source_log.loc[
        source_log["status"].eq("FETCH_FAILED"), "series_code"
    ].tolist()
    if failures and not allow_partial:
        raise ValueError(
            "Required macro source failure(s) block partial publication: "
            + ", ".join(failures)
        )
    config_path = (
        universe_path
        if universe_path is not None and Path(universe_path).suffix.lower() == ".json"
        else None
    )
    history_universe = (
        [
            config
            for config in universe
            if any(
                (
                    config.commodity_code,
                    config.commodity_family,
                    config.price_kind,
                )
            )
        ]
        if universe_path is not None
        and Path(universe_path).suffix.lower() == ".csv"
        else universe
    )
    history_rows = bounded_price_history(
        price_histories,
        history_universe,
        as_of_date or date.today(),
        load_history_limits(config_path),
    )
    return MacroAssetBundle(
        detail=detail,
        source_log=source_log,
        commodity_price_history=pd.DataFrame(
            history_rows,
            columns=PRICE_HISTORY_FIELDS,
        ),
    )


def fetch_macro_assets(
    universe_path: str | Path | None = DEFAULT_UNIVERSE_PATH,
    raw_dir: str | Path | None = None,
    as_of_date: date | None = None,
    *,
    allow_partial: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    bundle = fetch_macro_asset_bundle(
        universe_path,
        raw_dir=raw_dir,
        as_of_date=as_of_date,
        allow_partial=allow_partial,
    )
    return bundle.detail, bundle.source_log
