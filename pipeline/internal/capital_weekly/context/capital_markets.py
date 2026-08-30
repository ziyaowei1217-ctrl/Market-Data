from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, time
from html.parser import HTMLParser
from typing import Any, Iterable
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from .fundamentals import make_company_fundamental_row


HONG_KONG = ZoneInfo("Asia/Hong_Kong")
EASTERN = ZoneInfo("America/New_York")
SEC_ARCHIVES = "https://www.sec.gov/Archives/"
CAPITAL_MARKET_FIELDS = (
    "record_id",
    "event_date",
    "known_as_of",
    "market",
    "event_type",
    "company_name",
    "ticker",
    "cik",
    "form",
    "accession_number",
    "value",
    "unit",
    "source",
    "source_url",
    "source_tier",
    "proxy_type",
    "qc_flag",
    "notes",
)


def _record_id(*parts: Any) -> str:
    return hashlib.sha256(
        "|".join("" if value is None else str(value) for value in parts).encode("utf-8")
    ).hexdigest()


def _known_on_day(day: date) -> str:
    return datetime.combine(day, time(16), tzinfo=EASTERN).isoformat()


def _known_by(known_as_of: str, as_of_date: date) -> bool:
    known = datetime.fromisoformat(known_as_of)
    if known.tzinfo is None or known.utcoffset() is None:
        raise ValueError("known_as_of must include a UTC offset")
    cutoff = datetime.combine(as_of_date, time.max, tzinfo=HONG_KONG)
    return known.astimezone(HONG_KONG) <= cutoff


def _capital_row(**values: Any) -> dict[str, Any]:
    row = {field: "" for field in CAPITAL_MARKET_FIELDS}
    row.update(values)
    row["source_tier"] = row.get("source_tier") or "public"
    row["qc_flag"] = row.get("qc_flag") or "OK"
    row["record_id"] = row.get("record_id") or _record_id(
        row["market"],
        row["event_type"],
        row["event_date"],
        row["cik"],
        row["form"],
        row["accession_number"],
        row["value"],
    )
    return row


def parse_sec_master_index(text: str) -> list[dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines()]
    try:
        header_index = lines.index("Company Name|Form Type|CIK|Date Filed|File Name")
    except ValueError as error:
        raise ValueError("SEC master index header was not found") from error
    rows = []
    for line in lines[header_index + 1 :]:
        if not line:
            continue
        columns = line.split("|")
        if len(columns) != 5:
            raise ValueError("SEC master index row has an unexpected column count")
        company, form, cik, filed, filename = columns
        rows.append(
            {
                "company_name": company,
                "form": form,
                "cik": str(int(cik)).zfill(10),
                "event_date": date.fromisoformat(filed),
                "source_url": urljoin(SEC_ARCHIVES, filename),
                "accession_number": filename.rsplit("/", 1)[-1].removesuffix(".txt"),
            }
        )
    return rows


def build_sec_ipo_rows(
    records: Iterable[dict[str, Any]], *, as_of_date: date
) -> list[dict[str, Any]]:
    eligible_forms = {"S-1", "F-1", "424B4"}
    rows = []
    for record in records:
        event_date = record["event_date"]
        if event_date > as_of_date or record["form"] not in eligible_forms:
            continue
        event_type = (
            "ipo_prospectus_filing" if record["form"] == "424B4" else "ipo_registration_filing"
        )
        rows.append(
            _capital_row(
                event_date=event_date.isoformat(),
                known_as_of=_known_on_day(event_date),
                market="US",
                event_type=event_type,
                company_name=record["company_name"],
                cik=record["cik"],
                form=record["form"],
                accession_number=record["accession_number"],
                value=1,
                unit="filing",
                source="SEC EDGAR daily master index",
                source_url=record["source_url"],
                proxy_type="official_filing_activity",
                notes="Official filing activity; not a completed IPO or offering-size record.",
            )
        )
    rows.sort(key=lambda row: (row["form"], row["company_name"]))
    if rows:
        latest = max(row["event_date"] for row in rows)
        rows.append(
            _capital_row(
                event_date=latest,
                known_as_of=max(row["known_as_of"] for row in rows),
                market="US",
                event_type="ipo_filing_count_proxy",
                company_name="SEC IPO filing activity",
                value=len(rows),
                unit="filings",
                source="SEC EDGAR daily master index",
                source_url=SEC_ARCHIVES,
                proxy_type="sec_filing_count_not_issuance_volume",
                notes=(
                    "Count of S-1, F-1, and 424B4 filings in the captured window; "
                    "not issuance dollars, completed IPO count, or a comprehensive deal database."
                ),
            )
        )
    return rows


def _plain_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def build_guidance_proxy_rows(
    filing_text: str,
    event: dict[str, Any],
    *,
    as_of_date: date,
) -> list[dict[str, Any]]:
    known_as_of = str(event.get("accepted_at") or "")
    if not known_as_of or not _known_by(known_as_of, as_of_date):
        return []
    text = _plain_text(filing_text).lower()
    has_context = bool(re.search(r"\b(guidance|outlook|forecast|expects?)\b", text))
    if not has_context:
        return []
    raised = bool(re.search(r"\b(raise[sd]?|increase[sd]?|boost(?:s|ed)?)\b.{0,80}\b(guidance|outlook|forecast)", text))
    lowered = bool(re.search(r"\b(lower[sed]*|reduce[sd]?|cut[st]?)\b.{0,80}\b(guidance|outlook|forecast)", text))
    reaffirmed = bool(re.search(r"\b(reaffirm[sed]*|reiterate[sd]?|maintain[sed]*)\b.{0,80}\b(guidance|outlook|forecast)", text))
    provided = bool(re.search(r"\b(provide[sd]?|issue[sd]?|expects?|forecast[sed]*)\b.{0,80}\b(guidance|outlook|growth)", text))
    if raised and lowered:
        value, direction = 0.0, "MIXED"
    elif raised:
        value, direction = 1.0, "RAISED"
    elif lowered:
        value, direction = -1.0, "LOWERED"
    elif reaffirmed:
        value, direction = 0.0, "REAFFIRMED"
    elif provided:
        value, direction = 0.0, "PROVIDED"
    else:
        return []
    event_date = event["event_date"]
    if isinstance(event_date, date):
        event_date = event_date.isoformat()
    ticker = str(event.get("ticker") or "").upper()
    cik = str(event.get("cik") or "0")
    source_url = str(event.get("source_url") or "")
    evidence = make_company_fundamental_row(
        ticker=ticker,
        cik=cik,
        company_name=str(event.get("company_name") or ticker),
        metric_code="guidance_filing_evidence",
        metric_name="Guidance filing evidence",
        observation_date=event_date,
        filing_date=event_date,
        known_as_of=known_as_of,
        accession_number=str(event.get("accession_number") or ""),
        value=1,
        unit="document",
        frequency="event",
        source="SEC EDGAR filing document",
        source_url=source_url,
        notes="Eligible public filing text used by the rules-based guidance classifier.",
    )
    proxy = make_company_fundamental_row(
        ticker=ticker,
        cik=cik,
        company_name=str(event.get("company_name") or ticker),
        metric_code="guidance_direction_proxy",
        metric_name="Guidance direction proxy",
        observation_date=event_date,
        filing_date=event_date,
        known_as_of=known_as_of,
        accession_number=str(event.get("accession_number") or ""),
        value=value,
        unit="direction_score",
        frequency="event",
        source="Rules-based classification of SEC filing text",
        source_url=source_url,
        proxy_type="rules_based_filing_text_proxy",
        calculation_id="guidance_text_direction_proxy",
        formula_version="guidance-proxy-v1",
        input_record_ids=(evidence["record_id"],),
        guidance_direction=direction,
        notes=(
            "Rules-based filing text proxy; not consensus, earnings surprise, "
            "revision breadth, or a complete management-guidance database."
        ),
    )
    return [evidence, proxy]


def build_ma_rows(
    filings: Iterable[tuple[dict[str, Any], str]], *, as_of_date: date
) -> list[dict[str, Any]]:
    rows = []
    for event, filing_text in filings:
        if str(event.get("form") or "") != "8-K":
            continue
        items = {part.strip() for part in str(event.get("items") or "").split(",")}
        if not items.intersection({"1.01", "2.01"}):
            continue
        text = _plain_text(filing_text).lower()
        if not re.search(r"\b(merger|acqui(?:re|red|sition)|business combination)\b", text):
            continue
        known_as_of = str(event.get("accepted_at") or "")
        if not known_as_of or not _known_by(known_as_of, as_of_date):
            continue
        event_date = event["event_date"]
        if isinstance(event_date, date):
            event_date = event_date.isoformat()
        rows.append(
            _capital_row(
                event_date=event_date,
                known_as_of=known_as_of,
                market="US",
                event_type="ma_filing_announcement",
                company_name=str(event.get("company_name") or event.get("ticker") or ""),
                ticker=str(event.get("ticker") or "").upper(),
                cik=str(event.get("cik") or ""),
                form="8-K",
                accession_number=str(event.get("accession_number") or ""),
                value=1,
                unit="filing_event",
                source="SEC EDGAR filing document",
                source_url=str(event.get("source_url") or ""),
                proxy_type="watchlist_sec_filing_text_classification",
                notes=(
                    "Eligible 8-K item plus transaction-language classification; "
                    "not comprehensive M&A announcement-database coverage."
                ),
            )
        )
    return rows


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[dict[str, str]]] = []
        self._row: list[dict[str, str]] | None = None
        self._cell: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = {"text": "", "href": ""}
        elif tag == "a" and self._cell is not None:
            self._cell["href"] = dict(attrs).get("href") or ""

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._row is not None and self._cell is not None:
            self._cell["text"] = re.sub(r"\s+", " ", self._cell["text"]).strip()
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def parse_hkex_listing_table(text: str, *, source_url: str) -> list[dict[str, Any]]:
    parser = _TableParser()
    parser.feed(text)
    if not parser.rows:
        raise ValueError("HKEX listing table was not found")
    headers = [cell["text"].lower() for cell in parser.rows[0]]
    aliases = {
        "ticker": ("stock code", "code"),
        "company_name": ("company", "company name"),
        "event_date": ("listing date", "date of listing"),
        "source_url": ("listing document", "prospectus"),
    }
    indexes = {}
    for key, names in aliases.items():
        indexes[key] = next((headers.index(name) for name in names if name in headers), None)
    if any(index is None for index in indexes.values()):
        raise ValueError("HKEX listing table is missing required columns")
    rows = []
    for cells in parser.rows[1:]:
        if len(cells) < len(headers):
            continue
        raw_date = cells[indexes["event_date"]]["text"]
        parsed_date = None
        for pattern in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d"):
            try:
                parsed_date = datetime.strptime(raw_date, pattern).date()
                break
            except ValueError:
                continue
        if parsed_date is None:
            continue
        link = cells[indexes["source_url"]]["href"] or source_url
        rows.append(
            {
                "ticker": cells[indexes["ticker"]]["text"].zfill(5),
                "company_name": cells[indexes["company_name"]]["text"],
                "event_date": parsed_date,
                "source_url": urljoin(source_url, link),
            }
        )
    return rows


def build_hkex_ipo_rows(
    records: Iterable[dict[str, Any]], *, as_of_date: date
) -> list[dict[str, Any]]:
    return [
        _capital_row(
            event_date=record["event_date"].isoformat(),
            known_as_of=datetime.combine(record["event_date"], time(20), tzinfo=HONG_KONG).isoformat(),
            market="HK",
            event_type="hkex_new_listing",
            company_name=record["company_name"],
            ticker=record["ticker"],
            value=1,
            unit="listing",
            source="Hong Kong Exchanges and Clearing",
            source_url=record["source_url"],
            proxy_type="official_listing_record",
            notes="Official HKEX listing record; no inferred offer size.",
        )
        for record in records
        if record["event_date"] <= as_of_date
    ]


def normalize_capital_market_rows(
    rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized = []
    seen = set()
    for raw in rows:
        missing = [field for field in CAPITAL_MARKET_FIELDS if field not in raw]
        if missing:
            raise ValueError("Capital market row missing required fields: " + ", ".join(missing))
        row = {field: raw[field] for field in CAPITAL_MARKET_FIELDS}
        if not row["record_id"] or row["record_id"] in seen:
            raise ValueError(f"Duplicate or blank capital market record_id: {row['record_id']}")
        seen.add(row["record_id"])
        known = datetime.fromisoformat(str(row["known_as_of"]))
        if known.tzinfo is None or known.utcoffset() is None:
            raise ValueError("Capital market known_as_of must include a UTC offset")
        event_date = date.fromisoformat(str(row["event_date"]))
        if event_date > known.astimezone(HONG_KONG).date():
            raise ValueError("Capital market event_date cannot follow known_as_of")
        normalized.append(row)
    return sorted(normalized, key=lambda row: (row["event_date"], row["market"], row["event_type"], row["company_name"]))


__all__ = [
    "CAPITAL_MARKET_FIELDS",
    "build_guidance_proxy_rows",
    "build_hkex_ipo_rows",
    "build_ma_rows",
    "build_sec_ipo_rows",
    "normalize_capital_market_rows",
    "parse_hkex_listing_table",
    "parse_sec_master_index",
]
