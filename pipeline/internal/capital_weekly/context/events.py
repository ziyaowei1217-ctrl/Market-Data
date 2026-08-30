from __future__ import annotations

import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urlparse
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


class _FomcMeetingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meetings: list[tuple[int, str, str]] = []
        self._year: int | None = None
        self._month = ""
        self._anchor_parts: list[str] | None = None
        self._div_depth = 0
        self._capture_kind: str | None = None
        self._capture_depth: int | None = None
        self._capture_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "a":
            self._anchor_parts = []
        if tag.lower() != "div":
            return
        self._div_depth += 1
        classes = set(dict(attrs).get("class", "").split())
        kind = (
            "month"
            if "fomc-meeting__month" in classes
            else "date"
            if "fomc-meeting__date" in classes
            else None
        )
        if kind is not None and self._capture_kind is None:
            self._capture_kind = kind
            self._capture_depth = self._div_depth
            self._capture_parts = []

    def handle_data(self, data: str) -> None:
        if self._anchor_parts is not None:
            self._anchor_parts.append(data)
        if self._capture_kind is not None:
            self._capture_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._anchor_parts is not None:
            text = re.sub(r"\s+", " ", " ".join(self._anchor_parts)).strip()
            match = re.fullmatch(r"(\d{4})\s+FOMC\s+Meetings", text, re.I)
            if match:
                self._year = int(match.group(1))
            self._anchor_parts = None
        if tag.lower() != "div":
            return
        if self._capture_kind is not None and self._capture_depth == self._div_depth:
            text = re.sub(r"\s+", " ", " ".join(self._capture_parts)).strip()
            if self._capture_kind == "month":
                self._month = text
            elif self._year is not None and self._month:
                self.meetings.append((self._year, self._month, text))
                self._month = ""
            self._capture_kind = None
            self._capture_depth = None
            self._capture_parts = []
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


def parse_fomc_calendar(text: str) -> list[dict]:
    parser = _FomcMeetingParser()
    parser.feed(text)
    parsed = []
    for year, raw_month, raw_dates in parser.meetings:
        months = [_month_number(part) for part in raw_month.split("/")]
        day_numbers = [int(value) for value in re.findall(r"\d{1,2}", raw_dates)]
        if not months or not day_numbers:
            raise ValueError(
                f"FOMC calendar contained an invalid meeting date: {raw_month} {raw_dates}"
            )
        end_month = months[-1]
        end_year = year + (1 if end_month < months[0] else 0)
        event_date = date(end_year, end_month, day_numbers[-1])
        notation_vote = "notation vote" in raw_dates.lower()
        sep = "*" in raw_dates
        event_name = (
            "FOMC notation vote"
            if notation_vote
            else "FOMC policy decision (SEP)"
            if sep
            else "FOMC policy decision"
        )
        parsed.append(
            _event_row(
                source="Federal Reserve Board",
                source_url=(
                    "https://www.federalreserve.gov/monetarypolicy/"
                    "fomccalendars.htm"
                ),
                region="US",
                event_type="central_bank",
                event_date=event_date,
                event_time="" if notation_vote else "2:00 PM",
                event_name=event_name,
                reference_period=_fomc_reference_period(year, months, day_numbers),
            )
        )
    if not parsed:
        raise ValueError("FOMC calendar contained no confirmed meeting rows")
    return _deduplicate(parsed)


def parse_fomc_statement(
    text: str,
    source_url: str,
    event_date: date,
) -> dict[str, object]:
    parsed_url = urlparse(source_url)
    expected_path = (
        "/newsevents/pressreleases/"
        f"monetary{event_date.strftime('%Y%m%d')}a.htm"
    )
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname != "www.federalreserve.gov"
        or parsed_url.path != expected_path
    ):
        raise ValueError(f"URL is not the official dated FOMC statement: {source_url}")
    normalized = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()
    raw_date = event_date.strftime("%B %d, %Y").replace(" 0", " ")
    if not re.search(re.escape(raw_date), normalized, flags=re.IGNORECASE):
        raise ValueError("FOMC statement date does not match the meeting decision date")
    timestamp_matches = re.findall(
        r"For release at (\d{1,2}):(\d{2})\s*([ap])\.?m\.?\s*(EST|EDT)",
        normalized,
        flags=re.IGNORECASE,
    )
    if len(timestamp_matches) != 1:
        raise ValueError("FOMC statement requires exactly one release timestamp")
    raw_hour, raw_minute, meridiem, zone = timestamp_matches[0]
    hour = int(raw_hour) % 12 + (12 if meridiem.lower() == "p" else 0)
    released = datetime(
        event_date.year,
        event_date.month,
        event_date.day,
        hour,
        int(raw_minute),
        tzinfo=ZoneInfo("America/New_York"),
    )
    expected_zone = "EDT" if released.dst() else "EST"
    if zone.upper() != expected_zone:
        raise ValueError("FOMC statement timezone conflicts with the decision date")
    rate_pattern = (
        r"(?:[0-9]+-[0-9]+/[0-9]+|[0-9]+/[0-9]+|[0-9]+(?:\.[0-9]+)?)"
    )
    decisions = re.findall(
        r"decided to (maintain|raise|lower) the target range for the federal "
        r"funds rate (?:at|(?:by [^.]{1,60} )?to) "
        rf"({rate_pattern}) to ({rate_pattern}) percent",
        normalized,
        flags=re.IGNORECASE,
    )
    if len(decisions) != 1:
        raise ValueError("FOMC statement requires exactly one target-range decision")
    action, raw_lower, raw_upper = decisions[0]
    lower, upper = _fomc_rate(raw_lower), _fomc_rate(raw_upper)
    if lower > upper:
        raise ValueError("FOMC target range lower bound exceeds upper bound")
    return {
        "action": action.lower(),
        "target_lower": lower,
        "target_upper": upper,
        "released_at": released.isoformat(),
        "source_url": source_url,
    }


def _fomc_rate(value: str) -> float:
    if "/" not in value:
        return float(value)
    whole, fraction = value.split("-", 1) if "-" in value else ("0", value)
    numerator, denominator = fraction.split("/", 1)
    if int(denominator) == 0:
        raise ValueError("FOMC target range has a zero fraction denominator")
    return float(whole) + int(numerator) / int(denominator)


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


def _month_number(value: str) -> int:
    normalized = value.strip()
    for pattern in ("%B", "%b"):
        try:
            return datetime.strptime(normalized, pattern).month
        except ValueError:
            continue
    raise ValueError(f"FOMC calendar contained an invalid month: {value}")


def _fomc_reference_period(year: int, months: list[int], days: list[int]) -> str:
    first_month = datetime(2000, months[0], 1).strftime("%B")
    last_month = datetime(2000, months[-1], 1).strftime("%B")
    if len(days) == 1:
        return f"{last_month} {days[0]}, {year}"
    if months[0] == months[-1]:
        return f"{first_month} {days[0]}-{days[-1]}, {year}"
    return f"{first_month} {days[0]}-{last_month} {days[-1]}, {year}"
