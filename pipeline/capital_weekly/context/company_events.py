from __future__ import annotations

import csv
import io
import json
from datetime import date
from typing import Any, Iterable, Mapping


MATERIAL_FORMS = {"8-K", "10-Q", "10-K", "6-K", "20-F"}
RECENT_FIELDS = (
    "accessionNumber",
    "filingDate",
    "reportDate",
    "acceptanceDateTime",
    "form",
    "primaryDocument",
    "items",
)


def _classify_filing(form: str, items: str) -> str:
    if form == "8-K" and "2.02" in items.replace(" ", "").split(","):
        return "earnings_release"
    if form in {"10-Q", "10-K", "20-F"}:
        return "periodic_filing"
    if form == "6-K":
        return "foreign_issuer_update"
    return "material_filing"


def parse_sec_submissions(
    text: str,
    *,
    cik: str,
    ticker: str,
    start: date | None = None,
    end: date | None = None,
) -> list[dict[str, Any]]:
    payload = json.loads(text)
    recent = payload.get("filings", {}).get("recent")
    if not isinstance(recent, dict):
        raise ValueError("SEC submissions payload has no filings.recent object")
    missing = [field for field in RECENT_FIELDS if field not in recent]
    if missing:
        raise ValueError(f"SEC recent filings missing fields: {', '.join(missing)}")
    lengths = {len(recent[field]) for field in RECENT_FIELDS}
    if len(lengths) != 1:
        raise ValueError("SEC recent filing arrays must be aligned")

    normalized_cik = str(int(str(cik)))
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index in range(next(iter(lengths), 0)):
        form = str(recent["form"][index]).strip()
        if form not in MATERIAL_FORMS:
            continue
        filing_date = date.fromisoformat(str(recent["filingDate"][index]))
        if start and filing_date < start:
            continue
        if end and filing_date > end:
            continue
        accession = str(recent["accessionNumber"][index]).strip()
        if accession in seen:
            continue
        seen.add(accession)
        document = str(recent["primaryDocument"][index]).strip()
        archive_accession = accession.replace("-", "")
        source_url = (
            f"https://www.sec.gov/Archives/edgar/data/{normalized_cik}/"
            f"{archive_accession}/{document}"
        )
        items = str(recent["items"][index] or "").strip()
        report_date = str(recent["reportDate"][index] or "").strip()
        rows.append(
            {
                "event_date": filing_date,
                "ticker": ticker.upper(),
                "cik": normalized_cik.zfill(10),
                "form": form,
                "event_type": _classify_filing(form, items),
                "accession_number": accession,
                "report_date": report_date or None,
                "accepted_at": str(recent["acceptanceDateTime"][index] or "") or None,
                "items": items or None,
                "source": "SEC EDGAR submissions",
                "source_url": source_url,
                "evidence_status": "CONFIRMED",
            }
        )
    rows.sort(key=lambda row: (row["event_date"], row["ticker"], row["form"]))
    return rows


def load_company_watchlist(
    source: str | Iterable[Mapping[str, str]],
) -> list[dict[str, str]]:
    required = {"ticker", "cik", "company_name", "enabled"}
    if isinstance(source, str):
        reader = csv.DictReader(io.StringIO(source))
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("Company watchlist missing required columns")
        configured_rows = reader
    else:
        configured_rows = [dict(row) for row in source]
        if configured_rows and not required.issubset(configured_rows[0]):
            raise ValueError("Company watchlist missing required columns")
    rows = []
    for raw in configured_rows:
        if str(raw["enabled"]).strip().lower() not in {"1", "true", "yes", "y"}:
            continue
        rows.append(
            {
                "ticker": str(raw["ticker"]).strip().upper(),
                "cik": str(int(str(raw["cik"]).strip())).zfill(10),
                "company_name": str(raw["company_name"]).strip(),
            }
        )
    return rows


__all__ = ["load_company_watchlist", "parse_sec_submissions"]
