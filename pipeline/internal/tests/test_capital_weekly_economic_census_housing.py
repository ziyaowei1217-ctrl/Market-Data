from __future__ import annotations

from datetime import date
import unittest

from pipeline.internal.capital_weekly.context.economic_sources.census_housing import (
    CENSUS_HOUSING_RELEASES,
    build_census_housing_provider,
    parse_housing_release,
)


JULY_URL = "https://www.census.gov/construction/nrc/pdf/newresconst_202607.pdf"
JUNE_URL = "https://www.census.gov/construction/nrc/pdf/newresconst_202606.pdf"
JULY_TEXT = """
FOR RELEASE AT 8:30 AM EDT, TUESDAY, AUGUST 18, 2026
NEW RESIDENTIAL CONSTRUCTION, JULY 2026
Building Permits
Privately-owned housing units authorized by building permits in July were at a seasonally adjusted annual rate of 1,354,000. This is 0.5 percent above the revised June rate of 1,347,000.
Housing Starts
Privately-owned housing starts in July were at a seasonally adjusted annual rate of 1,428,000. This is 5.2 percent above the revised June estimate of 1,357,000.
Housing Completions
Privately-owned housing completions in July were at a seasonally adjusted annual rate of 1,420,000. This is 6.8 percent below the revised June estimate of 1,524,000.
"""
JUNE_TEXT = JULY_TEXT.replace(
    "TUESDAY, AUGUST 18, 2026", "FRIDAY, JULY 17, 2026"
).replace("JULY 2026", "JUNE 2026").replace(" in July ", " in June ").replace(
    "revised June", "revised May"
)


def _pdf_bytes(text: str) -> bytes:
    commands = ["BT", "/F1 7 Tf", "9 TL", "24 760 Td"]
    for line in text.strip().splitlines():
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.extend((f"({escaped}) Tj", "T*"))
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)


class FakeResponse:
    def __init__(self, url: str, *, text: str = "", content: bytes = b"", content_type: str = "text/html"):
        self.url = url
        self.text = text
        self.content = content or text.encode("utf-8")
        self.headers = {"Content-Type": content_type}
        self.status_code = 200
        self.history = []

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses[url]


class CensusHousingTests(unittest.TestCase):
    def test_release_emits_permits_starts_and_completions_with_vintage(self):
        rows = parse_housing_release(JULY_TEXT, JULY_URL, date(2026, 8, 23))

        by_code = {row["indicator_code"]: row for row in rows}
        self.assertEqual(by_code["HOUSING_PERMITS_SAAR"]["value"], 1_354_000.0)
        self.assertEqual(by_code["HOUSING_PERMITS_SAAR"]["previous_value"], 1_347_000.0)
        self.assertEqual(by_code["HOUSING_STARTS_SAAR"]["value"], 1_428_000.0)
        self.assertEqual(by_code["HOUSING_COMPLETIONS_SAAR"]["value"], 1_420_000.0)
        self.assertTrue(all(row["unit"] == "units_saar" for row in rows))
        self.assertTrue(all(row["observation_period"] == "2026-07" for row in rows))
        self.assertTrue(all(row["known_as_of"] == "2026-08-18T08:30:00-04:00" for row in rows))
        self.assertTrue(all(row["source_url"] == JULY_URL for row in rows))

    def test_release_accepts_published_margin_of_error_asterisk(self):
        rows = parse_housing_release(
            JULY_TEXT.replace("6.8 percent below", "6.8 percent (±13.7 percent)* below"),
            JULY_URL,
            date(2026, 8, 23),
        )

        completions = next(row for row in rows if row["indicator_code"] == "HOUSING_COMPLETIONS_SAAR")
        self.assertEqual(completions["value"], 1_420_000.0)

    def test_release_rejects_revised_value_for_the_wrong_month(self):
        with self.assertRaisesRegex(ValueError, "previous month"):
            parse_housing_release(
                JULY_TEXT.replace("revised June estimate", "revised May estimate"),
                JULY_URL,
                date(2026, 8, 23),
            )

    def test_post_sunday_release_is_excluded(self):
        self.assertEqual(parse_housing_release(JULY_TEXT, JULY_URL, date(2026, 8, 16)), [])

    def test_provider_selects_latest_eligible_official_archive_pdf(self):
        index = f'<a href="{JULY_URL}">July 2026</a><a href="{JUNE_URL}">June 2026</a>'
        session = FakeSession({
            CENSUS_HOUSING_RELEASES: FakeResponse(CENSUS_HOUSING_RELEASES, text=index),
            JULY_URL: FakeResponse(JULY_URL, content=_pdf_bytes(JULY_TEXT), content_type="application/pdf"),
            JUNE_URL: FakeResponse(JUNE_URL, content=_pdf_bytes(JUNE_TEXT), content_type="application/pdf"),
        })

        result = build_census_housing_provider(date(2026, 8, 17), date(2026, 8, 23), session).fetch()

        self.assertEqual(result.category, "economic_releases")
        self.assertEqual([url for url, _ in session.calls], [CENSUS_HOUSING_RELEASES, JULY_URL])
        self.assertEqual(
            {row["indicator_code"] for row in result.rows},
            {"HOUSING_PERMITS_SAAR", "HOUSING_STARTS_SAAR", "HOUSING_COMPLETIONS_SAAR"},
        )

    def test_provider_ignores_malformed_old_link_when_latest_link_is_official(self):
        index = (
            f'<a href="{JULY_URL}">July 2026</a>'
            '<a href="fhttps://www.census.gov/construction/nrc/pdf/newresconst_200904.pdf">April 2009</a>'
        )
        session = FakeSession({
            CENSUS_HOUSING_RELEASES: FakeResponse(CENSUS_HOUSING_RELEASES, text=index),
            JULY_URL: FakeResponse(JULY_URL, content=_pdf_bytes(JULY_TEXT), content_type="application/pdf"),
        })

        result = build_census_housing_provider(date(2026, 8, 17), date(2026, 8, 23), session).fetch()

        self.assertEqual([url for url, _ in session.calls], [CENSUS_HOUSING_RELEASES, JULY_URL])
        self.assertEqual(len(result.rows), 3)

    def test_provider_rejects_external_archive_artifacts(self):
        session = FakeSession({
            CENSUS_HOUSING_RELEASES: FakeResponse(
                CENSUS_HOUSING_RELEASES,
                text='<a href="https://example.test/newresconst.pdf">July 2026</a>',
            )
        })

        with self.assertRaisesRegex(ValueError, "official Census housing archive"):
            build_census_housing_provider(date(2026, 8, 17), date(2026, 8, 23), session).fetch()

    def test_parser_rejects_external_or_mismatched_artifact_identity(self):
        with self.assertRaisesRegex(ValueError, "official Census housing archive"):
            parse_housing_release(
                JULY_TEXT,
                "https://example.test/newresconst_202607.pdf",
                date(2026, 8, 23),
            )

        with self.assertRaisesRegex(ValueError, "filename.*observation period"):
            parse_housing_release(JULY_TEXT, JUNE_URL, date(2026, 8, 23))

    def test_provider_rejects_archive_label_that_conflicts_with_pdf_period(self):
        session = FakeSession({
            CENSUS_HOUSING_RELEASES: FakeResponse(CENSUS_HOUSING_RELEASES, text=f'<a href="{JUNE_URL}">July 2026</a>'),
            JUNE_URL: FakeResponse(JUNE_URL, content=_pdf_bytes(JUNE_TEXT), content_type="application/pdf"),
        })

        with self.assertRaisesRegex(ValueError, "archive label.*observation period"):
            build_census_housing_provider(date(2026, 8, 17), date(2026, 8, 23), session).fetch()


if __name__ == "__main__":
    unittest.main()
