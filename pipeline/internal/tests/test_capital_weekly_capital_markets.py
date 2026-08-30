from datetime import date
import unittest

from pipeline.internal.capital_weekly.context.capital_markets import (
    build_guidance_proxy_rows,
    build_ma_rows,
    build_sec_ipo_rows,
    parse_hkex_listing_table,
    parse_sec_master_index,
)


SEC_INDEX = """Description: Daily Index of EDGAR Dissemination Feed
Last Data Received: August 07, 2026
Comments: webmaster@sec.gov

Company Name|Form Type|CIK|Date Filed|File Name
Example IPO Inc.|S-1|1234567|2026-08-07|edgar/data/1234567/filing.txt
Foreign Newco Ltd.|F-1|7654321|2026-08-07|edgar/data/7654321/filing.txt
Priced Co.|424B4|2468101|2026-08-07|edgar/data/2468101/prospectus.txt
Routine Co.|10-Q|1357911|2026-08-07|edgar/data/1357911/quarterly.txt
"""


class CapitalMarketsTests(unittest.TestCase):
    def test_sec_master_index_emits_filing_rows_and_an_explicit_count_proxy(self):
        records = parse_sec_master_index(SEC_INDEX)
        rows = build_sec_ipo_rows(records, as_of_date=date(2026, 8, 9))

        self.assertEqual([row["form"] for row in rows if row["form"]], ["424B4", "F-1", "S-1"])
        aggregate = next(row for row in rows if row["event_type"] == "ipo_filing_count_proxy")
        self.assertEqual(aggregate["value"], 3)
        self.assertEqual(aggregate["unit"], "filings")
        self.assertEqual(aggregate["proxy_type"], "sec_filing_count_not_issuance_volume")
        self.assertIn("not issuance", aggregate["notes"].lower())

    def test_sec_ipo_cutoff_excludes_post_sunday_filing(self):
        records = parse_sec_master_index(
            SEC_INDEX
            + "Monday Co.|S-1|1111111|2026-08-10|edgar/data/1111111/monday.txt\n"
        )
        rows = build_sec_ipo_rows(records, as_of_date=date(2026, 8, 9))
        self.assertNotIn("Monday Co.", {row["company_name"] for row in rows})

    def test_guidance_proxy_is_rules_based_and_requires_guidance_language(self):
        event = {
            "event_date": date(2026, 8, 7),
            "accepted_at": "2026-08-07T16:05:00-04:00",
            "ticker": "AAPL",
            "cik": "0000320193",
            "form": "8-K",
            "accession_number": "0000320193-26-000081",
            "source_url": "https://www.sec.gov/Archives/example.htm",
        }
        scenarios = {
            "raises its full-year revenue outlook": (1.0, "RAISED"),
            "lowers its full-year revenue guidance": (-1.0, "LOWERED"),
            "reaffirms its full-year outlook": (0.0, "REAFFIRMED"),
            "provides full-year guidance and expects growth": (0.0, "PROVIDED"),
            "raises revenue guidance but lowers margin outlook": (0.0, "MIXED"),
        }
        for text, (value, direction) in scenarios.items():
            with self.subTest(text=text):
                rows = build_guidance_proxy_rows(text, event, as_of_date=date(2026, 8, 9))
                proxy = next(row for row in rows if row["metric_code"] == "guidance_direction_proxy")
                self.assertEqual(proxy["value"], value)
                self.assertEqual(proxy["guidance_direction"], direction)
                self.assertEqual(proxy["proxy_type"], "rules_based_filing_text_proxy")
                self.assertIn("not consensus", proxy["notes"].lower())
        self.assertEqual(
            build_guidance_proxy_rows(
                "Quarterly results were filed.", event, as_of_date=date(2026, 8, 9)
            ),
            [],
        )

    def test_guidance_proxy_excludes_filing_known_after_cutoff(self):
        event = {
            "event_date": date(2026, 8, 10),
            "accepted_at": "2026-08-10T08:00:00-04:00",
            "ticker": "AAPL",
            "cik": "0000320193",
            "form": "8-K",
            "accession_number": "monday",
            "source_url": "https://www.sec.gov/Archives/monday.htm",
        }
        self.assertEqual(
            build_guidance_proxy_rows(
                "raises full-year guidance", event, as_of_date=date(2026, 8, 9)
            ),
            [],
        )

    def test_ma_rows_require_both_filing_item_and_transaction_language(self):
        eligible = {
            "event_date": date(2026, 8, 7),
            "accepted_at": "2026-08-07T09:00:00-04:00",
            "ticker": "BUY",
            "cik": "0000000123",
            "form": "8-K",
            "items": "1.01,2.01",
            "accession_number": "deal",
            "source_url": "https://www.sec.gov/Archives/deal.htm",
        }
        rows = build_ma_rows(
            [(eligible, "entered into a definitive merger agreement to acquire Target")],
            as_of_date=date(2026, 8, 9),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_type"], "ma_filing_announcement")
        self.assertEqual(rows[0]["proxy_type"], "watchlist_sec_filing_text_classification")
        self.assertIn("not comprehensive", rows[0]["notes"].lower())
        self.assertEqual(
            build_ma_rows(
                [({**eligible, "items": "2.02"}, "entered into a merger agreement")],
                as_of_date=date(2026, 8, 9),
            ),
            [],
        )
        self.assertEqual(
            build_ma_rows(
                [(eligible, "entered into an ordinary supplier agreement")],
                as_of_date=date(2026, 8, 9),
            ),
            [],
        )

    def test_hkex_listing_parser_preserves_official_links(self):
        html = """
        <table>
          <tr><th>Stock Code</th><th>Company</th><th>Listing Date</th><th>Listing Document</th></tr>
          <tr><td>09999</td><td>Example HK Ltd.</td><td>7 Aug 2026</td>
              <td><a href="/listing/example.pdf">Prospectus</a></td></tr>
        </table>
        """
        rows = parse_hkex_listing_table(
            html,
            source_url="https://www.hkex.com.hk/Listing/New-Listings",
        )
        self.assertEqual(rows[0]["ticker"], "09999")
        self.assertEqual(rows[0]["event_date"], date(2026, 8, 7))
        self.assertEqual(
            rows[0]["source_url"],
            "https://www.hkex.com.hk/listing/example.pdf",
        )


if __name__ == "__main__":
    unittest.main()
