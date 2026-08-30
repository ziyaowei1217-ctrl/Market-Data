from __future__ import annotations

from datetime import date
import unittest

from pipeline.internal.capital_weekly.context.economic_sources.census_durable_goods import (
    CENSUS_DURABLE_RELEASES,
    build_census_durable_goods_provider,
    parse_durable_goods_release,
)
from pipeline.internal.tests.test_capital_weekly_economic_census_housing import (
    FakeResponse,
    FakeSession,
    _pdf_bytes,
)


JUNE_URL = "https://www.census.gov/manufacturing/m3/historical_data/pressreleases/adv/2026/jun26adv.pdf"
MAY_URL = "https://www.census.gov/manufacturing/m3/historical_data/pressreleases/adv/2026/may26adv.pdf"
JUNE_TEXT = """
FOR RELEASE AT 8:30 AM EDT, MONDAY, JULY 27, 2026
MONTHLY ADVANCE REPORT ON DURABLE GOODS MANUFACTURERS' SHIPMENTS, INVENTORIES AND ORDERS, JUNE 2026
New orders for manufactured durable goods in June, up three of the last four months, increased $1.1 billion or 0.3 percent to $334.8 billion. This followed a 4.0 percent May decrease. Excluding transportation, new orders increased 0.6 percent. Excluding defense, new orders increased 0.3 percent.
"""


class CensusDurableGoodsTests(unittest.TestCase):
    def test_release_emits_headline_and_official_exclusion_changes(self):
        rows = parse_durable_goods_release(JUNE_TEXT, JUNE_URL, date(2026, 8, 2))

        by_code = {row["indicator_code"]: row for row in rows}
        headline = by_code["DURABLE_GOODS_NEW_ORDERS_MOM"]
        self.assertEqual(headline["value"], 0.3)
        self.assertEqual(headline["previous_value"], -4.0)
        self.assertEqual(headline["observation_period"], "2026-06")
        self.assertEqual(headline["known_as_of"], "2026-07-27T08:30:00-04:00")
        self.assertEqual(by_code["DURABLE_GOODS_NEW_ORDERS_EX_TRANSPORTATION_MOM"]["value"], 0.6)
        self.assertEqual(by_code["DURABLE_GOODS_NEW_ORDERS_EX_DEFENSE_MOM"]["value"], 0.3)
        self.assertTrue(all(row["unit"] == "percent" for row in rows))
        self.assertTrue(all(row["source_url"] == JUNE_URL for row in rows))

    def test_release_accepts_an_before_prior_month_change(self):
        rows = parse_durable_goods_release(
            JUNE_TEXT.replace(
                "This followed a 4.0 percent May decrease",
                "This followed an 8.5 percent May increase",
            ),
            JUNE_URL,
            date(2026, 8, 2),
        )

        headline = next(row for row in rows if row["indicator_code"] == "DURABLE_GOODS_NEW_ORDERS_MOM")
        self.assertEqual(headline["previous_value"], 8.5)

    def test_release_binds_prior_change_to_new_orders_section(self):
        rows = parse_durable_goods_release(
            JUNE_TEXT + "\nShipments increased 1.0 percent. This followed a 0.7 percent May increase.",
            JUNE_URL,
            date(2026, 8, 2),
        )

        headline = next(row for row in rows if row["indicator_code"] == "DURABLE_GOODS_NEW_ORDERS_MOM")
        self.assertEqual(headline["previous_value"], -4.0)

    def test_release_rejects_prior_change_for_the_wrong_month(self):
        with self.assertRaisesRegex(ValueError, "previous month"):
            parse_durable_goods_release(
                JUNE_TEXT.replace(
                    "This followed a 4.0 percent May decrease",
                    "This followed a 4.0 percent April decrease",
                ),
                JUNE_URL,
                date(2026, 8, 2),
            )

    def test_post_sunday_release_is_excluded(self):
        self.assertEqual(parse_durable_goods_release(JUNE_TEXT, JUNE_URL, date(2026, 7, 26)), [])

    def test_provider_discovers_only_official_historical_advance_pdfs(self):
        index = f'<a href="{JUNE_URL}">June 2026</a><a href="{MAY_URL}">May 2026</a>'
        session = FakeSession({
            CENSUS_DURABLE_RELEASES: FakeResponse(CENSUS_DURABLE_RELEASES, text=index),
            JUNE_URL: FakeResponse(JUNE_URL, content=_pdf_bytes(JUNE_TEXT), content_type="application/pdf"),
        })

        result = build_census_durable_goods_provider(date(2026, 7, 27), date(2026, 8, 2), session).fetch()

        self.assertEqual([url for url, _ in session.calls], [CENSUS_DURABLE_RELEASES, JUNE_URL])
        self.assertEqual(len(result.rows), 3)
        self.assertIn("selected artifact", result.notes)

    def test_parser_rejects_ambiguous_headline_values(self):
        duplicate = JUNE_TEXT + "\nNew orders for manufactured durable goods in June decreased $1.0 billion or 0.3 percent to $333.8 billion."

        with self.assertRaisesRegex(ValueError, "exactly one headline"):
            parse_durable_goods_release(duplicate, JUNE_URL, date(2026, 8, 2))

    def test_parser_rejects_external_or_mismatched_artifact_identity(self):
        with self.assertRaisesRegex(ValueError, "official Census durable-goods archive"):
            parse_durable_goods_release(
                JUNE_TEXT,
                "https://example.test/jun26adv.pdf",
                date(2026, 8, 2),
            )

        with self.assertRaisesRegex(ValueError, "filename.*observation period"):
            parse_durable_goods_release(JUNE_TEXT, MAY_URL, date(2026, 8, 2))


if __name__ == "__main__":
    unittest.main()
