from datetime import date, datetime
import unittest
from zoneinfo import ZoneInfo

from pipeline.internal.capital_weekly.context.events import (
    parse_bls_calendar,
    parse_census_calendar,
    parse_fed_calendar,
    parse_fomc_calendar,
    parse_fomc_statement,
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

    def test_fomc_calendar_uses_policy_day_and_identifies_sep_meetings(self):
        html = """
        <div class="panel panel-default">
          <div class="panel-heading"><h4><a id="fixture">2026 FOMC Meetings</a></h4></div>
          <div class="row fomc-meeting">
            <div class="fomc-meeting__month col-xs-5"><strong>March</strong></div>
            <div class="fomc-meeting__date col-xs-4">17-18*</div>
          </div>
          <div class="row fomc-meeting">
            <div class="fomc-meeting__month col-xs-5"><strong>Apr/May</strong></div>
            <div class="fomc-meeting__date col-xs-4">30-1</div>
          </div>
        </div>
        """

        rows = parse_fomc_calendar(html)

        self.assertEqual(
            [row["event_date"] for row in rows],
            [date(2026, 3, 18), date(2026, 5, 1)],
        )
        self.assertEqual(rows[0]["release_time_bjt"], "02:00")
        self.assertEqual(
            rows[0]["release_datetime_bjt"], "2026-03-19T02:00:00+08:00"
        )
        self.assertEqual(rows[0]["event_type"], "central_bank")
        self.assertIn("SEP", rows[0]["event_name"])
        self.assertNotIn("SEP", rows[1]["event_name"])
        self.assertEqual(rows[0]["reference_period"], "March 17-18, 2026")

    def test_fomc_statement_parses_action_and_fractional_target_range(self):
        maintained = parse_fomc_statement(
            """
            <p>July 29, 2026</p><p>For release at 2:00 p.m. EDT</p>
            <p>The Committee decided to maintain the target range for the
            federal funds rate at 3-1/2 to 3-3/4 percent.</p>
            """,
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm",
            date(2026, 7, 29),
        )

        self.assertEqual(
            maintained,
            {
                "action": "maintain",
                "target_lower": 3.5,
                "target_upper": 3.75,
                "released_at": "2026-07-29T14:00:00-04:00",
                "source_url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm",
            },
        )

        raised = parse_fomc_statement(
            "<p>March 18, 2026</p><p>For release at 2:00 p.m. EDT</p>"
            "<p>The Committee decided to raise the target range for the federal funds rate to 4 to 4-1/4 percent.</p>",
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260318a.htm",
            date(2026, 3, 18),
        )
        lowered = parse_fomc_statement(
            "<p>January 28, 2026</p><p>For release at 2:00 p.m. EST</p>"
            "<p>The Committee decided to lower the target range for the federal funds rate to 3-3/4 to 4 percent.</p>",
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260128a.htm",
            date(2026, 1, 28),
        )
        zero_bound = parse_fomc_statement(
            "<p>April 29, 2020</p><p>For release at 2:00 p.m. EDT</p>"
            "<p>The Committee decided to maintain the target range for the federal funds rate at 0 to 1/4 percent.</p>",
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary20200429a.htm",
            date(2020, 4, 29),
        )
        self.assertEqual(
            (raised["action"], raised["target_lower"], raised["target_upper"]),
            ("raise", 4.0, 4.25),
        )
        self.assertEqual(
            (lowered["action"], lowered["target_lower"], lowered["target_upper"]),
            ("lower", 3.75, 4.0),
        )
        self.assertEqual(
            (
                zero_bound["action"],
                zero_bound["target_lower"],
                zero_bound["target_upper"],
            ),
            ("maintain", 0.0, 0.25),
        )

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
