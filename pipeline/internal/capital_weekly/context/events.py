from __future__ import annotations

import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Iterable
from zoneinfo import ZoneInfo


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "tr":
            self._row = []
        elif tag.lower() in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"td", "th"} and self._cell is not None:
            assert self._row is not None
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif tag.lower() == "tr" and self._row is not None:
            if any(self._row):
                self.rows.append(self._row)
            self._row = None


class _FedColumnParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.columns: list[tuple[str, str]] = []
        self._in_title = False
        self._div_depth = 0
        self._capture_class: str | None = None
        self._capture_depth: int | None = None
        self._capture_text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() != "div":
            return
        self._div_depth += 1
        classes = dict(attrs).get("class", "").split()
        target = next(
            (
                name
                for name in ("col-xs-2", "col-xs-7", "col-xs-3")
                if name in classes
            ),
            None,
        )
        if target and self._capture_class is None:
            self._capture_class = target
            self._capture_depth = self._div_depth
            self._capture_text = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._capture_class is not None:
            self._capture_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        if tag.lower() != "div":
            return
        if (
            self._capture_class is not None
            and self._capture_depth == self._div_depth
        ):
            text = re.sub(r"\s+", " ", " ".join(self._capture_text)).strip()
            self.columns.append((self._capture_class, text))
            self._capture_class = None
            self._capture_depth = None
            self._capture_text = []
        self._div_depth -= 1


def _table_rows(text: str) -> list[list[str]]:
    parser = _TableParser()
    parser.feed(text)
    return parser.rows


def _parse_date(value: str) -> date | None:
    for pattern in (
        "%A, %B %d, %Y",
        "%a, %b %d, %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%m/%d/%Y",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(value.strip(), pattern).date()
        except ValueError:
            continue
    return None


def _bjt_time(observation_date: date, value: str) -> tuple[str | None, str | None]:
    if not value.strip():
        return None, None
    normalized = re.sub(r"\.", "", value.strip()).upper()
    for pattern in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            local_time = datetime.strptime(normalized, pattern).time()
            eastern = datetime.combine(
                observation_date, local_time, tzinfo=ZoneInfo("America/New_York")
            )
            bjt = eastern.astimezone(ZoneInfo("Asia/Hong_Kong"))
            return bjt.strftime("%H:%M"), bjt.isoformat()
        except ValueError:
            continue
    raise ValueError(f"Official calendar contained an invalid release time: {value}")


def _event_row(
    *,
    source: str,
    source_url: str,
    region: str,
    event_type: str,
    event_date: date,
    event_time: str,
    event_name: str,
    reference_period: str | None = None,
) -> dict:
    release_time_bjt, release_datetime_bjt = _bjt_time(event_date, event_time)
    return {
        "event_date": event_date,
        "release_time_bjt": release_time_bjt,
        "release_datetime_bjt": release_datetime_bjt,
        "region": region,
        "event_type": event_type,
        "event_name": event_name,
        "reference_period": reference_period,
        "actual": None,
        "previous": None,
        "revised_previous": None,
        "evidence_status": "CONFIRMED",
        "source": source,
        "source_url": source_url,
        "qc_flag": "OK",
    }


def _deduplicate(rows: Iterable[dict]) -> list[dict]:
    result = []
    seen = set()
    for row in rows:
        key = (
            row["source"],
            row["event_date"],
            row["release_time_bjt"],
            row["event_name"],
        )
        if key not in seen:
            seen.add(key)
            result.append(row)
    return sorted(result, key=lambda row: (row["event_date"], row["release_time_bjt"] or ""))


def parse_bls_calendar(text: str) -> list[dict]:
    parsed = []
    for cells in _table_rows(text):
        if len(cells) < 3:
            continue
        event_date = _parse_date(cells[0])
        if event_date is None:
            continue
        name = cells[2]
        period_match = re.search(
            r"\bfor\s+((?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\s+\d{4})\b",
            name,
            flags=re.I,
        )
        parsed.append(
            _event_row(
                source="U.S. Bureau of Labor Statistics",
                source_url="https://www.bls.gov/schedule/",
                region="US",
                event_type="macro_release",
                event_date=event_date,
                event_time=cells[1],
                event_name=name,
                reference_period=period_match.group(1) if period_match else None,
            )
        )
    if not parsed:
        raise ValueError("BLS calendar contained no confirmed release rows")
    return _deduplicate(parsed)


def parse_fed_calendar(text: str) -> list[dict]:
    parsed = []
    for cells in _table_rows(text):
        if len(cells) < 3:
            continue
        event_date = _parse_date(cells[0])
        if event_date is None:
            continue
        parsed.append(
            _event_row(
                source="Federal Reserve Board",
                source_url="https://www.federalreserve.gov/newsevents/calendar.htm",
                region="US",
                event_type="central_bank",
                event_date=event_date,
                event_time=cells[1],
                event_name=cells[2],
            )
        )
    if not parsed:
        parser = _FedColumnParser()
        parser.feed(text)
        month_match = re.search(
            r"Calendar:\s*([A-Za-z]+)\s+(\d{4})", parser.title
        )
        if month_match:
            month = datetime.strptime(month_match.group(1), "%B").month
            year = int(month_match.group(2))
            current: dict[str, str] = {}
            for column, value in parser.columns:
                if column == "col-xs-2":
                    current = {"time": value}
                elif column == "col-xs-7" and current:
                    current["name"] = value
                elif column == "col-xs-3" and current:
                    day_match = re.fullmatch(r"\d{1,2}", value)
                    if day_match and current.get("name"):
                        parsed.append(
                            _event_row(
                                source="Federal Reserve Board",
                                source_url=(
                                    "https://www.federalreserve.gov/newsevents/"
                                    f"{year}-{month_match.group(1).lower()}.htm"
                                ),
                                region="US",
                                event_type="central_bank",
                                event_date=date(year, month, int(value)),
                                event_time=current.get("time", ""),
                                event_name=current["name"],
                            )
                        )
                    current = {}
    if not parsed:
        raise ValueError("Federal Reserve calendar contained no confirmed rows")
    return _deduplicate(parsed)


def parse_census_calendar(text: str) -> list[dict]:
    parsed = []
    for cells in _table_rows(text):
        if len(cells) < 4:
            continue
        event_date = _parse_date(cells[1])
        if event_date is None:
            continue
        parsed.append(
            _event_row(
                source="U.S. Census Bureau",
                source_url="https://www.census.gov/economic-indicators/calendar-listview.html",
                region="US",
                event_type="macro_release",
                event_date=event_date,
                event_time=cells[2],
                event_name=cells[0],
                reference_period=cells[3] or None,
            )
        )
    if not parsed:
        raise ValueError("Census calendar contained no confirmed release rows")
    return _deduplicate(parsed)


def select_event_window(
    events: Iterable[dict],
    start: date,
    end: date,
) -> list[dict]:
    if end < start:
        raise ValueError("Event window end must not precede start")
    return sorted(
        (
            dict(row)
            for row in events
            if start <= row["event_date"] <= end
        ),
        key=lambda row: (row["event_date"], row.get("release_time_bjt") or ""),
    )
