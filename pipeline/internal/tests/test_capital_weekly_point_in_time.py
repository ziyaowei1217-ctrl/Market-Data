from datetime import date
from pathlib import Path
import unittest

from pipeline.internal.capital_weekly.context.provider_contracts import (
    CaptureMetadata,
    PointInTimeUnavailable,
    filter_known_as_of,
    select_capture_at_or_before,
    target_sunday_cutoff,
)


class PointInTimeTests(unittest.TestCase):
    def test_target_sunday_cutoff_is_the_final_hong_kong_instant(self):
        cutoff = target_sunday_cutoff(date(2026, 8, 9))

        self.assertEqual(cutoff.isoformat(), "2026-08-09T23:59:59.999999+08:00")

    def test_filter_known_as_of_excludes_a_monday_revision(self):
        rows = [
            {"record_id": "old", "known_as_of": "2026-08-07T08:30:00-04:00"},
            {"record_id": "new", "known_as_of": "2026-08-10T08:30:00-04:00"},
        ]

        self.assertEqual(
            [row["record_id"] for row in filter_known_as_of(rows, date(2026, 8, 9))],
            ["old"],
        )

    def test_filter_known_as_of_rejects_a_naive_timestamp(self):
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            filter_known_as_of(
                [{"record_id": "naive", "known_as_of": "2026-08-09T12:00:00"}],
                date(2026, 8, 9),
            )

    def test_capture_selection_refuses_a_capture_created_after_sunday(self):
        captures = [
            CaptureMetadata(
                provider="ism_manufacturing",
                captured_at="2026-08-10T09:00:00+08:00",
                path=Path("monday.raw"),
                sha256="a" * 64,
                source_url="https://www.ismworld.org/",
            )
        ]

        with self.assertRaises(PointInTimeUnavailable):
            select_capture_at_or_before(captures, date(2026, 8, 9))

    def test_capture_selection_uses_the_latest_capture_before_the_cutoff(self):
        earlier = CaptureMetadata(
            provider="ism_manufacturing",
            captured_at="2026-08-09T09:00:00+08:00",
            path=Path("morning.raw"),
            sha256="a" * 64,
            source_url="https://www.ismworld.org/",
        )
        later = CaptureMetadata(
            provider="ism_manufacturing",
            captured_at="2026-08-09T22:00:00+08:00",
            path=Path("evening.raw"),
            sha256="b" * 64,
            source_url="https://www.ismworld.org/",
        )

        self.assertEqual(
            select_capture_at_or_before([earlier, later], date(2026, 8, 9)),
            later,
        )


if __name__ == "__main__":
    unittest.main()
