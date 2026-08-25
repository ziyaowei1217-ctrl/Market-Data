import json
from datetime import date
import unittest

from pipeline.internal.capital_weekly.context.company_events import (
    load_company_watchlist,
    parse_sec_submissions,
)


class CompanyEventTests(unittest.TestCase):
    def test_sec_submissions_filters_material_forms_and_builds_archive_url(self):
        payload = {
            "filings": {
                "recent": {
                    "accessionNumber": [
                        "0000320193-26-000081",
                        "0000320193-26-000080",
                        "0000320193-26-000079",
                    ],
                    "filingDate": ["2026-07-24", "2026-07-23", "2026-07-22"],
                    "reportDate": ["2026-06-27", "", ""],
                    "acceptanceDateTime": [
                        "2026-07-24T16:05:00.000Z",
                        "2026-07-23T10:00:00.000Z",
                        "2026-07-22T09:00:00.000Z",
                    ],
                    "form": ["10-Q", "8-K", "4"],
                    "primaryDocument": ["aapl-20260627.htm", "event.htm", "form4.xml"],
                    "items": ["", "2.02,9.01", ""],
                }
            }
        }

        rows = parse_sec_submissions(
            json.dumps(payload),
            cik="0000320193",
            ticker="AAPL",
            start=date(2026, 7, 20),
            end=date(2026, 7, 26),
        )

        self.assertEqual([row["form"] for row in rows], ["8-K", "10-Q"])
        self.assertEqual(rows[0]["event_type"], "earnings_release")
        self.assertEqual(rows[1]["event_type"], "periodic_filing")
        self.assertEqual(rows[0]["evidence_status"], "CONFIRMED")
        self.assertEqual(
            rows[1]["source_url"],
            "https://www.sec.gov/Archives/edgar/data/320193/"
            "000032019326000081/aapl-20260627.htm",
        )

    def test_sec_submissions_rejects_misaligned_recent_arrays(self):
        payload = {
            "filings": {
                "recent": {
                    "accessionNumber": ["one"],
                    "filingDate": ["2026-07-24", "2026-07-25"],
                    "reportDate": [""],
                    "acceptanceDateTime": [""],
                    "form": ["8-K"],
                    "primaryDocument": ["event.htm"],
                    "items": [""],
                }
            }
        }

        with self.assertRaisesRegex(ValueError, "aligned"):
            parse_sec_submissions(json.dumps(payload), cik="1", ticker="TEST")

    def test_watchlist_loader_normalizes_cik_and_skips_disabled_rows(self):
        text = (
            "ticker,cik,company_name,enabled\n"
            "AAPL,320193,Apple Inc.,true\n"
            "MSFT,789019,Microsoft Corporation,false\n"
        )

        rows = load_company_watchlist(text)

        self.assertEqual(
            rows,
            [
                {
                    "ticker": "AAPL",
                    "cik": "0000320193",
                    "company_name": "Apple Inc.",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
