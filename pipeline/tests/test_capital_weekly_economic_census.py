from __future__ import annotations

from datetime import date
import unittest

from pipeline.capital_weekly.context.economic_sources.census import (
    CENSUS_DATA_PAGE,
    CENSUS_HISTORICAL_RELEASES,
    CENSUS_SALES_PAGE,
    CURRENT_RELEASE_PDF,
    build_census_provider,
    parse_retail_sales_release,
)


JUNE_2026_PDF_TEXT = """
Data Inquiries Media Inquiries
Percent Change in Retail and Food Services Sales from Previous Month
Data adjusted for seasonal variation and holiday and trading-day differences but not for price changes.
FOR RELEASE AT 8:30 AM EDT, THURSDAY, JULY 16, 2026
ADVANCE MONTHLY SALES FOR RETAIL AND FOOD SERVICES, JUNE 2026
Release Number: CB26-113
Advance estimates of U.S. retail and food services sales for June 2026, adjusted for seasonal variation and holiday and trading-day differences, but not for price changes, were $768.6 billion, up 0.2 percent from the previous month, and up 6.7 percent from June 2025.
The April 2026 to May 2026 percent change was revised from up 0.9 percent to up 1.0 percent.
Table 1. Estimated Monthly Sales for Retail and Food Services, by Kind of Business
(Total sales estimates are shown in millions of dollars and are based on data from the Advance Monthly Retail Trade Survey, Monthly Retail Trade Survey, and administrative records.)
NAICS code % Chg. Jun. May Apr. Jun. May Jun. May Apr. Jun. May
2026 2025 (a) (p) (r) (a) (p) (r) (r) (r)
Kind of Business Not Adjusted 6 Month Total Adjusted
Retail & food services, total 4,420,287 5.1 776,915 796,039 755,742 716,698 753,313 768,553 766,876 759,097 720,164 714,513
(NA) Not available (a) Advance estimate (p) Preliminary estimate (r) Revised estimate
Table 2. Estimated Change in Monthly Sales for Retail and Food Services, by Kind of Business
(Estimates are shown as percents and are based on data from the Advance Monthly Retail Trade Survey, Monthly Retail Trade Survey, and administrative records.)
Jun. 2026 Advance from May 2026 and Jun. 2025; May 2026 Preliminary from Apr. 2026 and May 2025
Retail & food services, total 0.2 6.7 1.0 7.3 2.9 6.4
Table 3. Estimated Measures of Sampling Variability and Revision to Advance Estimates Jun. 2026
"""


MAY_2026_PDF_TEXT = """
Data Inquiries Media Inquiries
Percent Change in Retail and Food Services Sales from Previous Month
Data adjusted for seasonal variation and holiday and trading-day differences but not for price changes.
FOR RELEASE AT 8:30 AM EDT, WEDNESDAY, JUNE 17, 2026
ADVANCE MONTHLY SALES FOR RETAIL AND FOOD SERVICES, MAY 2026
Release Number: CB26-97
Advance estimates of U.S. retail and food services sales for May 2026, adjusted for seasonal variation and holiday and trading-day differences, but not for price changes, were $763.7 billion, up 0.9 percent from the previous month, and up 6.9 percent from May 2025.
The March 2026 to April 2026 percent change was revised from up 0.5 percent to up 0.4 percent.
Table 1. Estimated Monthly Sales for Retail and Food Services, by Kind of Business
(Total sales estimates are shown in millions of dollars and are based on data from the Advance Monthly Retail Trade Survey, Monthly Retail Trade Survey, and administrative records.)
NAICS code % Chg. May Apr. Mar. May Apr. May Apr. Mar. May Apr.
2026 2025 (a) (p) (r) (a) (p) (r) (r) (r)
Kind of Business Not Adjusted 5 Month Total Adjusted
Retail & food services, total 3,639,171 4.3 792,825 754,755 761,135 753,313 722,319 763,705 757,036 754,013 714,568 722,442
(NA) Not available (a) Advance estimate (p) Preliminary estimate (r) Revised estimate
Table 2. Estimated Change in Monthly Sales for Retail and Food Services, by Kind of Business
(Estimates are shown as percents and are based on data from the Advance Monthly Retail Trade Survey, Monthly Retail Trade Survey, and administrative records.)
May 2026 Advance from Apr. 2026 and May 2025; Apr. 2026 Preliminary from Mar. 2026 and Apr. 2025
Retail & food services, total 0.9 6.9 0.4 4.8 2.9 5.3
Table 3. Estimated Measures of Sampling Variability and Revision to Advance Estimates May 2026
"""


ARCHIVED_MAY_PDF = (
    "https://www2.census.gov/retail/releases/historical/marts/adv2605.pdf"
)
ARCHIVED_MAY_XLSX = (
    "https://www2.census.gov/retail/releases/historical/marts/rs2605.xlsx"
)
CURRENT_TABLES_XLSX = "https://www.census.gov/retail/marts/www/marts_current.xlsx"
CURRENT_TIMESERIES = (
    "https://www.census.gov/retail/marts/www/mrtssales92-present.xlsx"
)


DATA_HTML = f"""
<html><body>
<a href="/retail/marts/historic_releases.html">
  Advance Monthly Retail Trade Reports View all of the prior reports.
</a>
</body></html>
"""


SALES_HTML = f"""
<html><body>
<h4>FOR IMMEDIATE RELEASE: Thursday, July 16, 2026</h4>
<h2>Advance Monthly Sales for Retail and Food Services</h2>
<h3>Additional Release Tables - June 2026</h3>
<a href="/retail/marts/www/marts_current.pdf">Advance Monthly Retail Trade Report</a>
<a href="/retail/marts/www/marts_current.xlsx">Advance Monthly Retail Trade Report Tables</a>
<a href="/retail/marts/www/mrtssales92-present.xlsx">MARTS Time Series (Adjusted Sales Data/Seasonal Factors—1992 to present)</a>
</body></html>
"""


HISTORICAL_HTML = f"""
<html><body>
<h2>Advance Monthly Retail Trade Survey Historical Data</h2>
<p>The MARTS releases below do not contain the most current data.</p>
<h3>2026 Press Releases</h3>
<p>Files are available as Excel or Adobe PDF.</p>
<a href="{ARCHIVED_MAY_PDF}">May 2026</a>
<a href="{ARCHIVED_MAY_XLSX}">May 2026</a>
</body></html>
"""


def _pdf_bytes(text: str) -> bytes:
    """Build a tiny real PDF so provider tests exercise pypdf extraction."""
    commands = ["BT", "/F1 7 Tf", "9 TL", "24 760 Td"]
    for line in text.strip().splitlines():
        escaped = (
            line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        )
        commands.extend((f"({escaped}) Tj", "T*"))
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream
        + b"\nendstream",
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
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


class FakeResponse:
    def __init__(
        self,
        *,
        url: str,
        text: str = "",
        content: bytes = b"",
        content_type: str = "text/html; charset=UTF-8",
        status_code: int = 200,
        history=(),
    ):
        self.url = url
        self.text = text
        self.content = content or text.encode("utf-8")
        self.headers = {"Content-Type": content_type}
        self.status_code = status_code
        self.history = list(history)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.responses = dict(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response


def _html_response(url: str, text: str) -> FakeResponse:
    return FakeResponse(url=url, text=text)


def _pdf_response(url: str, text: str, *, final_url: str | None = None) -> FakeResponse:
    return FakeResponse(
        url=final_url or url,
        content=_pdf_bytes(text),
        content_type="application/pdf",
    )


def _session(*, current_text=JUNE_2026_PDF_TEXT, current_final_url=None):
    return FakeSession(
        {
            CENSUS_DATA_PAGE: _html_response(CENSUS_DATA_PAGE, DATA_HTML),
            CENSUS_SALES_PAGE: _html_response(CENSUS_SALES_PAGE, SALES_HTML),
            CENSUS_HISTORICAL_RELEASES: _html_response(
                CENSUS_HISTORICAL_RELEASES, HISTORICAL_HTML
            ),
            CURRENT_RELEASE_PDF: _pdf_response(
                CURRENT_RELEASE_PDF,
                current_text,
                final_url=current_final_url,
            ),
            ARCHIVED_MAY_PDF: _pdf_response(ARCHIVED_MAY_PDF, MAY_2026_PDF_TEXT),
            ARCHIVED_MAY_XLSX: RuntimeError("release-specific XLSX must not be fetched"),
            CURRENT_TABLES_XLSX: RuntimeError("current tables must not be fetched"),
            CURRENT_TIMESERIES: RuntimeError("current time series must not be fetched"),
        }
    )


class CensusEconomicReleaseTests(unittest.TestCase):
    def test_release_pdf_keeps_revision_and_release_specific_adjusted_levels(self):
        rows = parse_retail_sales_release(
            JUNE_2026_PDF_TEXT, CURRENT_RELEASE_PDF, date(2026, 8, 9)
        )

        monthly = next(
            row
            for row in rows
            if row["indicator_code"] == "RETAIL_SALES_MOM"
            and row["observation_period"] == "2026-06"
        )
        self.assertEqual(monthly["value"], 0.2)
        self.assertEqual(monthly["previous_value"], 0.9)
        self.assertEqual(monthly["revised_previous"], 1.0)
        self.assertEqual(monthly["known_as_of"], "2026-07-16T08:30:00-04:00")
        self.assertEqual(monthly["release_at_bjt"], "2026-07-16T20:30:00+08:00")

        levels = {
            row["observation_period"]: row
            for row in rows
            if row["indicator_code"] == "RETAIL_SALES_LEVEL_SA"
        }
        self.assertEqual(levels["2026-06"]["value"], 768553.0)
        self.assertEqual(levels["2026-05"]["value"], 766876.0)
        self.assertEqual(levels["2025-06"]["value"], 720164.0)
        self.assertEqual(levels["2026-06"]["unit"], "millions_current_dollars")
        self.assertEqual(levels["2026-06"]["source_url"], CURRENT_RELEASE_PDF)
        yoy = next(
            row
            for row in rows
            if row["indicator_code"] == "RETAIL_SALES_YOY_PCT"
            and row["observation_period"] == "2026-06"
        )
        self.assertAlmostEqual(yoy["value"], (768553 / 720164 - 1) * 100, places=12)
        self.assertEqual(yoy["formula_version"], "economic-v1")
        self.assertEqual(
            set(yoy["input_record_ids"].split("|")),
            {levels["2026-06"]["record_id"], levels["2025-06"]["record_id"]},
        )

    def test_release_after_target_sunday_is_not_visible(self):
        monday = JUNE_2026_PDF_TEXT.replace(
            "THURSDAY, JULY 16, 2026", "MONDAY, AUGUST 10, 2026"
        )

        self.assertEqual(
            parse_retail_sales_release(
                monday, CURRENT_RELEASE_PDF, date(2026, 8, 9)
            ),
            [],
        )

    def test_release_requires_unique_total_rows_and_millions_of_current_dollars(self):
        total_row = (
            "Retail & food services, total 4,420,287 5.1 776,915 796,039 "
            "755,742 716,698 753,313 768,553 766,876 759,097 720,164 714,513"
        )
        duplicate = JUNE_2026_PDF_TEXT.replace(
            "(NA) Not available", total_row + "\n(NA) Not available"
        )
        with self.assertRaisesRegex(ValueError, "exactly one Table 1 total row"):
            parse_retail_sales_release(
                duplicate, CURRENT_RELEASE_PDF, date(2026, 8, 9)
            )

        wrong_units = JUNE_2026_PDF_TEXT.replace(
            "millions of dollars", "thousands of dollars"
        )
        with self.assertRaisesRegex(ValueError, "millions of current dollars"):
            parse_retail_sales_release(
                wrong_units, CURRENT_RELEASE_PDF, date(2026, 8, 9)
            )

    def test_provider_follows_official_pages_and_uses_only_release_pdf(self):
        session = _session()

        result = build_census_provider(
            date(2026, 8, 3), date(2026, 8, 9), session
        ).fetch()

        self.assertEqual(result.category, "economic_releases")
        self.assertEqual(result.source_url, CENSUS_DATA_PAGE)
        current = next(
            row
            for row in result.rows
            if row["indicator_code"] == "RETAIL_SALES_MOM"
            and row["observation_period"] == "2026-06"
        )
        self.assertEqual(current["source_url"], CURRENT_RELEASE_PDF)
        called_urls = [url for url, _ in session.calls]
        self.assertEqual(
            called_urls,
            [
                CENSUS_DATA_PAGE,
                CENSUS_SALES_PAGE,
                CENSUS_HISTORICAL_RELEASES,
                CURRENT_RELEASE_PDF,
            ],
        )
        for _, kwargs in session.calls:
            self.assertEqual(kwargs, {"timeout": 30, "allow_redirects": False})
        self.assertNotIn(CURRENT_TABLES_XLSX, called_urls)
        self.assertNotIn(CURRENT_TIMESERIES, called_urls)

    def test_provider_uses_latest_eligible_archived_pdf_not_post_cutoff_current(self):
        session = _session()

        result = build_census_provider(
            date(2026, 7, 6), date(2026, 7, 12), session
        ).fetch()

        monthly = next(
            row
            for row in result.rows
            if row["indicator_code"] == "RETAIL_SALES_MOM"
            and row["observation_period"] == "2026-05"
        )
        self.assertEqual(monthly["value"], 0.9)
        self.assertEqual(monthly["previous_value"], 0.5)
        self.assertEqual(monthly["revised_previous"], 0.4)
        self.assertEqual(monthly["source_url"], ARCHIVED_MAY_PDF)
        self.assertEqual(
            [url for url, _ in session.calls],
            [
                CENSUS_DATA_PAGE,
                CENSUS_SALES_PAGE,
                CENSUS_HISTORICAL_RELEASES,
                CURRENT_RELEASE_PDF,
                ARCHIVED_MAY_PDF,
            ],
        )

    def test_provider_rejects_external_discovery_and_redirected_artifacts(self):
        external = _session()
        external.responses[CENSUS_DATA_PAGE] = _html_response(
            CENSUS_DATA_PAGE,
            '<a href="https://example.test/retail/marts/historic_releases.html">'
            "Advance Monthly Retail Trade Reports</a>",
        )
        with self.assertRaisesRegex(ValueError, "official Census historical index"):
            build_census_provider(
                date(2026, 8, 3), date(2026, 8, 9), external
            ).fetch()

        redirected = _session(current_final_url="https://example.test/release.pdf")
        with self.assertRaisesRegex(ValueError, "must not redirect"):
            build_census_provider(
                date(2026, 8, 3), date(2026, 8, 9), redirected
            ).fetch()


if __name__ == "__main__":
    unittest.main()
