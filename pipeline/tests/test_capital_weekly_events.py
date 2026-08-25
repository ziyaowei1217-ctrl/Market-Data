from datetime import date, datetime
import unittest
from zoneinfo import ZoneInfo

from pipeline.capital_weekly.context.events import (
    parse_bls_calendar,
    parse_census_calendar,
    parse_fed_calendar,
    select_event_window,
)


class WeeklyEventTests(unittest.TestCase):
    def test_bls_calendar_converts_confirmed_eastern_time_to_hong_kong(self):
        html = """
        <table><tr><th>Date</th><th>Time</th><th>Release</th></tr>
        <tr><td>Tuesday, July 14, 2026</td><td>08:30 AM</td>
        <td>Consumer Price Index for June 2026</td></tr></table>
        """

        rows = parse_bls_calendar(html)

        self.assertEqual(rows[0]["event_date"], date(2026, 7, 14))
        self.assertEqual(rows[0]["release_time_bjt"], "20:30")
        self.assertEqual(rows[0]["reference_period"], "June 2026")
        self.assertEqual(rows[0]["evidence_status"], "CONFIRMED")

    def test_fed_calendar_keeps_missing_time_visible(self):
        html = """
        <table><tr><td>July 29, 2026</td><td></td>
        <td>FOMC Statement</td></tr></table>
        """

        rows = parse_fed_calendar(html)

        self.assertIsNone(rows[0]["release_time_bjt"])
        self.assertEqual(rows[0]["event_type"], "central_bank")

    def test_fed_calendar_parses_official_month_page_columns(self):
        html = """
        <title>Federal Reserve Board - Calendar: July 2026</title>
        <div class="panel-body"><div class="row">
          <div class="col-xs-2"><p>2:00 p.m.</p></div>
          <div class="col-xs-7"><p>FOMC Minutes</p>
            <p>Meeting of June 16-17</p></div>
          <div class="col-xs-3"><p>8</p></div>
        </div></div>
        """

        rows = parse_fed_calendar(html)

        self.assertEqual(rows[0]["event_date"], date(2026, 7, 8))
        self.assertEqual(rows[0]["release_time_bjt"], "02:00")
        self.assertIn("FOMC Minutes", rows[0]["event_name"])

    def test_census_calendar_parses_reference_period_and_deduplicates_rows(self):
        row = (
            "<tr><td>Advance Economic Indicators Report</td>"
            "<td>July 28, 2026</td><td>8:30 AM</td><td>June 2026</td></tr>"
        )

        rows = parse_census_calendar(f"<table>{row}{row}</table>")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reference_period"], "June 2026")
        self.assertEqual(rows[0]["release_time_bjt"], "20:30")

    def test_event_window_includes_boundaries_and_excludes_outside_dates(self):
        events = [
            {"event_date": date(2026, 7, 19), "event_name": "before"},
            {"event_date": date(2026, 7, 20), "event_name": "start"},
            {"event_date": date(2026, 7, 26), "event_name": "end"},
            {"event_date": date(2026, 7, 27), "event_name": "after"},
        ]

        selected = select_event_window(
            events,
            start=date(2026, 7, 20),
            end=date(2026, 7, 26),
        )

        self.assertEqual([row["event_name"] for row in selected], ["start", "end"])


if __name__ == "__main__":
    unittest.main()
