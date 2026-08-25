from datetime import date
import io
import re
import unittest

import pandas as pd

from pipeline.internal.capital_weekly.context.economic_releases import select_latest_vintages
from pipeline.internal.capital_weekly.context.economic_sources.bea import (
    BEA_ARCHIVE,
    build_bea_provider,
    parse_gdp_release,
    parse_pio_release,
)


ADVANCE_NEWS_URL = (
    "https://www.bea.gov/news/2025/"
    "gross-domestic-product-2nd-quarter-2025-advance-estimate"
)
SECOND_NEWS_URL = (
    "https://www.bea.gov/news/2025/"
    "gross-domestic-product-2nd-quarter-2025-second-estimate-and-"
    "corporate-profits-preliminary"
)
PIO_NEWS_URL = "https://www.bea.gov/news/2025/personal-income-and-outlays-august-2025"
GDP_ADVANCE_XLSX_URL = (
    "https://www.bea.gov/sites/default/files/2025-07/gdp2q25-adv.xlsx"
)
GDP_SECOND_XLSX_URL = (
    "https://www.bea.gov/sites/default/files/2025-08/gdp2q25-2nd.xlsx"
)
PIO_XLSX_URL = "https://www.bea.gov/sites/default/files/2025-09/pi0825.xlsx"
PIO_PDF_URL = "https://www.bea.gov/sites/default/files/2025-09/pi0825.pdf"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _release_page(title, released, *attachments):
    links = "".join(
        f'<h3><a href="{url}">{label}</a></h3>' for label, url in attachments
    )
    return f"""
    <html><body>
      <div class="field field--name-field-release-date">
        EMBARGOED UNTIL RELEASE AT 8:30 a.m. {released}
      </div>
      <h1>{title}</h1>
      <div id="related-materials">{links}</div>
    </body></html>
    """


GDP_ADVANCE_NEWS_HTML = _release_page(
    "Gross Domestic Product, 2nd Quarter 2025 (Advance Estimate)",
    "EDT, Wednesday, July 30, 2025",
    ("Full Release & Tables", "/sites/default/files/2025-07/gdp2q25-adv.pdf"),
    ("Tables Only", "/sites/default/files/2025-07/gdp2q25-adv.xlsx"),
)
GDP_SECOND_NEWS_HTML = _release_page(
    "Gross Domestic Product, 2nd Quarter 2025 (Second Estimate) and Corporate Profits (Preliminary)",
    "EDT, Thursday, August 28, 2025",
    ("key source data and assumptions", "/sites/default/files/2025-08/gdpkeysource-2q25-2nd.xlsx"),
    ("Full Release & Tables", "/sites/default/files/2025-08/gdp2q25-2nd.pdf"),
    ("Tables Only", "/sites/default/files/2025-08/gdp2q25-2nd.xlsx"),
)
PIO_NEWS_HTML = _release_page(
    "Personal Income and Outlays, August 2025",
    "EDT, Friday, September 26, 2025",
    ("Full Release & Tables", "/sites/default/files/2025-09/pi0825.pdf"),
    ("Tables Only", "/sites/default/files/2025-09/pi0825.xlsx"),
)


GDP_ARCHIVED_TABLE_HTML = """
<html><body>
  <p>EMBARGOED UNTIL RELEASE AT 8:30 a.m. EDT, Thursday, August 28, 2025</p>
  <h1>Gross Domestic Product, 2nd Quarter 2025 (Second Estimate)</h1>
  <table>
    <caption>Table 3. Gross Domestic Product: Level and Change from Preceding Period</caption>
    <thead>
      <tr><th rowspan="3">Line</th><th rowspan="3"></th>
        <th colspan="3">Billions of chained (2017) dollars</th></tr>
      <tr><th colspan="3">Seasonally adjusted at annual rates</th></tr>
      <tr><th>2024 Q2</th><th>2025 Q1</th><th>2025 Q2 r</th></tr>
    </thead>
    <tbody><tr><td>1</td><th>Gross domestic product (GDP)</th>
      <td>23223.9</td><td>23512.7</td><td>23703.8</td></tr></tbody>
  </table>
</body></html>
"""


PIO_ARCHIVED_TABLE_HTML = """
<html><body>
  <p>EMBARGOED UNTIL RELEASE AT 8:30 a.m. EDT, Friday, September 26, 2025</p>
  <h1>Personal Income and Outlays, August 2025</h1>
  <table>
    <caption>Table 5. Price Indexes for Personal Consumption Expenditures:
      Level and Percent Change from Preceding Period (Months)</caption>
    <thead><tr><th>Line</th><th></th><th>2024 Aug.</th><th>2025 May</th>
      <th>2025 July</th><th>2025 Aug. p</th></tr></thead>
    <tbody>
      <tr><th colspan="6">Chain-type price indexes (2017=100), seasonally adjusted</th></tr>
      <tr><td>1</td><th>Personal consumption expenditures (PCE)</th>
        <td>123.93865628042843</td><td>126.150</td><td>126.949</td><td>127.285</td></tr>
      <tr><td>6</td><th>PCE excluding food and energy</th>
        <td>123.13411078717202</td><td>125.502</td><td>126.418</td><td>126.705</td></tr>
    </tbody>
  </table>
  <table>
    <caption>Table 7. Price Indexes for Personal Consumption Expenditures:
      Percent Change from Month One Year Ago</caption>
    <thead><tr><th>Line</th><th></th><th>2025 Aug. p</th></tr></thead>
    <tbody>
      <tr><td>1</td><th>Personal consumption expenditures (PCE)</th><td>2.7</td></tr>
      <tr><td>6</td><th>PCE excluding food and energy</th><td>2.9</td></tr>
    </tbody>
  </table>
</body></html>
"""


def _gdp_xlsx(current_level=23703.8):
    table3 = pd.DataFrame(
        [
            ["Table 3. Gross Domestic Product: Level and Change from Preceding Period"],
            ["Line", None, "Billions of dollars", "Billions of chained (2017) dollars", "Billions of chained (2017) dollars", "Billions of chained (2017) dollars"],
            ["Line", None, 2024, "Seasonally adjusted at annual rates", "Seasonally adjusted at annual rates", "Seasonally adjusted at annual rates"],
            ["Line", None, 2024, 2024, 2025, 2025],
            ["Line", None, 2024, "Q2", "Q1", "Q2 r"],
            [1, "Gross domestic product (GDP)", 29184.9, 23223.9, 23512.7, current_level],
        ]
    )
    return _xlsx_bytes({"Contents": pd.DataFrame([["Release Date", None, "August 28, 2025"]]), "Table 3": table3})


def _pio_xlsx():
    table5 = pd.DataFrame(
        [
            [None],
            ["Table 5. Price Indexes for Personal Consumption Expenditures: Level and Percent Change from Preceding Period (Months)"],
            [None],
            ["Line", None, 2024, 2025, 2025, 2025],
            ["Line", None, "Aug.", "May", "July", "Aug. p"],
            [None, "Chain-type price indexes (2017=100), seasonally adjusted"],
            [1, "Personal consumption expenditures (PCE)", 123.93865628042843, 126.150, 126.949, 127.285],
            [6, "PCE excluding food and energy", 123.13411078717202, 125.502, 126.418, 126.705],
            [None, "Percent change from preceding period in price indexes, seasonally adjusted at monthly rates"],
            [11, "Personal consumption expenditures (PCE)", 0.4, 0.2, 0.2, 0.3],
            [16, "PCE excluding food and energy", 0.3, 0.2, 0.2, 0.2],
        ]
    )
    table7 = pd.DataFrame(
        [
            [None],
            ["Table 7. Price Indexes for Personal Consumption Expenditures: Percent Change from Month One Year Ago"],
            ["Line", None, 2025, 2025],
            ["Line", None, "July", "Aug. p"],
            [1, "Personal consumption expenditures (PCE)", 2.6, 2.7],
            [6, "PCE excluding food and energy", 2.9, 2.9],
        ]
    )
    return _xlsx_bytes({"Contents": pd.DataFrame([["Release date:", None, "September 26, 2025"]]), "Table 5": table5, "Table 7": table7})


def _xlsx_bytes(sheets):
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False, header=False)
    return stream.getvalue()


PIO_PDF_LAYOUT = """
Table 5. Price Indexes for Personal Consumption Expenditures: Level and Percent Change from Preceding Period (Months)
                                                                    2025
Line                                   Aug.       May      July     Aug. p
                 Chain-type price indexes (2017=100), seasonally adjusted
1 Personal consumption expenditures (PCE) 123.93865628042843 126.150 126.949 127.285 1
6 PCE excluding food and energy             123.13411078717202 125.502 126.418 126.705 6
Table 7. Price Indexes for Personal Consumption Expenditures: Percent Change from Month One Year Ago
                                                                    2025
Line                                   July      Aug. p
1 Personal consumption expenditures (PCE) 2.6 2.7 1
6 PCE excluding food and energy             2.9 2.9 6
"""


def _pdf_bytes(text):
    escaped_lines = [
        line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        for line in text.strip().splitlines()
    ]
    commands = ["BT", "/F1 8 Tf", "36 756 Td", "10 TL"]
    for line in escaped_lines:
        commands.extend([f"({line}) Tj", "T*"])
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, payload in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(payload)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)


def _tables_from_html(text):
    return "".join(re.findall(r"<table\b.*?</table>", text, flags=re.I | re.S))


class FakeResponse:
    def __init__(self, body, url, *, content_type="text/html; charset=UTF-8", status_code=200, history=()):
        self.content = body.encode() if isinstance(body, str) else body
        self.text = self.content.decode("utf-8", errors="replace") if content_type.startswith("text/") else ""
        self.url = url
        self.status_code = status_code
        self.history = list(history)
        self.headers = {"Content-Type": content_type}

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


def _archive_page(entries, next_url=None):
    rows = "".join(
        '<tr class="release-row"><td class="views-field views-field-title">'
        f'<a href="{url}">{title}</a></td>'
        '<td class="views-field views-field-created">'
        f'<time datetime="{published}">{published}</time></td></tr>'
        for url, title, published in entries
    )
    next_link = f'<a rel="next" href="{next_url}">Next</a>' if next_url else ""
    return f"<html><body><table><tbody>{rows}</tbody></table>{next_link}</body></html>"


class BeaEconomicReleaseTests(unittest.TestCase):
    def test_release_specific_html_artifacts_keep_public_parser_interfaces(self):
        gdp = parse_gdp_release(GDP_ARCHIVED_TABLE_HTML, GDP_SECOND_XLSX_URL, date(2025, 8, 31))
        pio = parse_pio_release(PIO_ARCHIVED_TABLE_HTML, PIO_XLSX_URL, date(2025, 9, 28))

        gdp_values = {row["indicator_code"]: row["value"] for row in gdp}
        pio_values = {row["indicator_code"]: row["value"] for row in pio if row["observation_period"] == "2025-08"}
        self.assertAlmostEqual(gdp_values["REAL_GDP_QOQ_SAAR"], 3.290858190093, places=10)
        self.assertAlmostEqual(gdp_values["REAL_GDP_YOY_PCT"], 2.066405728581, places=10)
        self.assertAlmostEqual(pio_values["PCE_PRICE_INDEX_MOM_PCT"], 0.264673215228, places=10)
        self.assertAlmostEqual(pio_values["PCE_PRICE_INDEX_YOY_PCT"], 2.7, places=12)
        self.assertAlmostEqual(pio_values["PCE_PRICE_INDEX_3M_ANN_PCT"], 3.647752236053, places=10)
        self.assertAlmostEqual(pio_values["CORE_PCE_PRICE_INDEX_MOM_PCT"], 0.227024632568, places=10)
        self.assertAlmostEqual(pio_values["CORE_PCE_PRICE_INDEX_YOY_PCT"], 2.9, places=12)
        self.assertAlmostEqual(pio_values["CORE_PCE_PRICE_INDEX_3M_ANN_PCT"], 3.889684122580, places=10)
        self._assert_inputs_resolve_within_artifact(gdp, "REAL_GDP_QOQ_SAAR")
        self._assert_inputs_resolve_within_artifact(pio, "PCE_PRICE_INDEX_3M_ANN_PCT")

    def test_provider_follows_archive_pagination_and_parses_tables_only_xlsx(self):
        page_1 = BEA_ARCHIVE + "?page=1"
        page_0 = _archive_page(
            [("/news/2026/newer-release", "GDP (Advance Estimate), 1st Quarter 2026", "2026-04-30T08:30:00-04:00")],
            "?page=1",
        )
        page_1_html = _archive_page(
            [
                (SECOND_NEWS_URL, "GDP (Second Estimate), 2nd Quarter 2025", "2025-08-28T08:30:00-04:00"),
                (PIO_NEWS_URL, "Personal Income and Outlays, August 2025", "2025-09-26T08:30:00-04:00"),
                (ADVANCE_NEWS_URL, "GDP (Advance Estimate), 2nd Quarter 2025", "2025-07-30T08:30:00-04:00"),
            ],
            "?page=2",
        )
        session = FakeSession(
            {
                BEA_ARCHIVE: FakeResponse(page_0, BEA_ARCHIVE),
                page_1: FakeResponse(page_1_html, page_1),
                SECOND_NEWS_URL: FakeResponse(GDP_SECOND_NEWS_HTML, SECOND_NEWS_URL),
                PIO_NEWS_URL: FakeResponse(PIO_NEWS_HTML, PIO_NEWS_URL),
                GDP_SECOND_XLSX_URL: FakeResponse(_gdp_xlsx(), GDP_SECOND_XLSX_URL, content_type=XLSX_TYPE),
                PIO_XLSX_URL: FakeResponse(_pio_xlsx(), PIO_XLSX_URL, content_type=XLSX_TYPE),
            }
        )

        result = build_bea_provider(date(2025, 9, 22), date(2025, 9, 28), session).fetch()

        called = [url for url, _ in session.calls]
        self.assertEqual(called, [BEA_ARCHIVE, page_1, SECOND_NEWS_URL, GDP_SECOND_XLSX_URL, PIO_NEWS_URL, PIO_XLSX_URL])
        self.assertNotIn(BEA_ARCHIVE + "?page=2", called)
        gdp_row = next(row for row in result.rows if row["indicator_code"] == "REAL_GDP_QOQ_SAAR")
        pce_row = next(row for row in result.rows if row["indicator_code"] == "PCE_PRICE_INDEX_MOM_PCT")
        self.assertEqual(gdp_row["source_url"], GDP_SECOND_XLSX_URL)
        self.assertEqual(pce_row["source_url"], PIO_XLSX_URL)
        self.assertEqual(gdp_row["vintage_date"], "second")
        self.assertTrue(
            all(
                row["source_url"]
                in {GDP_SECOND_XLSX_URL, PIO_XLSX_URL}
                for row in result.rows
            )
        )

    def test_second_estimate_is_not_visible_before_release(self):
        advance = parse_gdp_release(GDP_ARCHIVED_TABLE_HTML.replace("Second Estimate", "Advance Estimate").replace("August 28", "July 30"), GDP_ADVANCE_XLSX_URL, date(2025, 8, 24))
        second = parse_gdp_release(GDP_ARCHIVED_TABLE_HTML, GDP_SECOND_XLSX_URL, date(2025, 8, 31))
        selected = select_latest_vintages(advance + second, date(2025, 8, 24))
        self.assertEqual(next(row for row in selected if row["indicator_code"] == "REAL_GDP_QOQ_SAAR")["vintage_date"], "advance")

    def test_malformed_estimate_duplicate_and_post_sunday_update_fail_closed(self):
        missing_estimate = GDP_ARCHIVED_TABLE_HTML.replace(
            " (Second Estimate)", ""
        )
        with self.assertRaisesRegex(ValueError, "estimate label"):
            parse_gdp_release(
                missing_estimate, GDP_SECOND_XLSX_URL, date(2025, 8, 31)
            )

        duplicate = GDP_ARCHIVED_TABLE_HTML.replace(
            "</tbody>",
            "<tr><td>1</td><th>Gross domestic product (GDP)</th>"
            "<td>23223.9</td><td>23512.7</td><td>99999.9</td></tr></tbody>",
            1,
        )
        with self.assertRaisesRegex(ValueError, "Duplicate BEA table value"):
            parse_gdp_release(duplicate, GDP_SECOND_XLSX_URL, date(2025, 8, 31))

        post_sunday = GDP_ARCHIVED_TABLE_HTML.replace(
            "Second Estimate", "Annual Update"
        ).replace(
            "Thursday, August 28, 2025", "Monday, September 1, 2025"
        )
        self.assertEqual(
            parse_gdp_release(
                post_sunday, GDP_SECOND_XLSX_URL, date(2025, 8, 31)
            ),
            [],
        )

    def test_pio_published_yoy_conflict_with_release_levels_fails(self):
        conflicting = PIO_ARCHIVED_TABLE_HTML.replace(
            "<td>6</td><th>PCE excluding food and energy</th><td>2.9</td>",
            "<td>6</td><th>PCE excluding food and energy</th><td>9.9</td>",
        )
        with self.assertRaisesRegex(ValueError, "conflicts with published"):
            parse_pio_release(conflicting, PIO_XLSX_URL, date(2025, 9, 28))

    def test_provider_falls_back_to_release_pdf_when_no_tables_xlsx_exists(self):
        archive = _archive_page(
            [
                (ADVANCE_NEWS_URL, "GDP (Advance Estimate), 2nd Quarter 2025", "2025-07-30T08:30:00-04:00"),
                (PIO_NEWS_URL, "Personal Income and Outlays, August 2025", "2025-09-26T08:30:00-04:00"),
            ]
        )
        pio_pdf_page = _release_page(
            "Personal Income and Outlays, August 2025",
            "EDT, Friday, September 26, 2025",
            ("Full Release & Tables", "/sites/default/files/2025-09/pi0825.pdf"),
        )
        session = FakeSession(
            {
                BEA_ARCHIVE: FakeResponse(archive, BEA_ARCHIVE),
                ADVANCE_NEWS_URL: FakeResponse(GDP_ADVANCE_NEWS_HTML, ADVANCE_NEWS_URL),
                GDP_ADVANCE_XLSX_URL: FakeResponse(_gdp_xlsx(), GDP_ADVANCE_XLSX_URL, content_type=XLSX_TYPE),
                PIO_NEWS_URL: FakeResponse(pio_pdf_page, PIO_NEWS_URL),
                PIO_PDF_URL: FakeResponse(
                    _pdf_bytes(
                        "Unrelated prose before the official tables\n"
                        "Line Jan. May July Aug. p\n"
                        "1 Personal consumption expenditures (PCE) 999 999 999 999 1\n"
                        + PIO_PDF_LAYOUT
                        + "\nUnrelated appendix after Table 7"
                    ),
                    PIO_PDF_URL,
                    content_type="application/pdf",
                ),
            }
        )
        result = build_bea_provider(
            date(2025, 9, 22), date(2025, 9, 28), session
        ).fetch()

        pce = next(row for row in result.rows if row["indicator_code"] == "PCE_PRICE_INDEX_YOY_PCT")
        self.assertAlmostEqual(pce["value"], 2.7, places=12)
        self.assertEqual(pce["source_url"], PIO_PDF_URL)

    def test_news_page_tables_cannot_substitute_for_missing_artifact_tables(self):
        session = self._single_page_session()
        session.responses[ADVANCE_NEWS_URL] = FakeResponse(
            GDP_ADVANCE_NEWS_HTML + _tables_from_html(GDP_ARCHIVED_TABLE_HTML),
            ADVANCE_NEWS_URL,
        )
        session.responses[GDP_ADVANCE_XLSX_URL] = FakeResponse(
            _pio_xlsx(), GDP_ADVANCE_XLSX_URL, content_type=XLSX_TYPE
        )

        with self.assertRaisesRegex(ValueError, "GDP artifact"):
            build_bea_provider(
                date(2025, 9, 22), date(2025, 9, 28), session
            ).fetch()

        session = self._single_page_session()
        session.responses[PIO_NEWS_URL] = FakeResponse(
            PIO_NEWS_HTML + _tables_from_html(PIO_ARCHIVED_TABLE_HTML),
            PIO_NEWS_URL,
        )
        session.responses[PIO_XLSX_URL] = FakeResponse(
            _gdp_xlsx(), PIO_XLSX_URL, content_type=XLSX_TYPE
        )

        with self.assertRaisesRegex(ValueError, "PIO artifact"):
            build_bea_provider(
                date(2025, 9, 22), date(2025, 9, 28), session
            ).fetch()

    def test_cross_family_attachment_links_fail_closed(self):
        session = self._single_page_session()
        session.responses[ADVANCE_NEWS_URL] = FakeResponse(
            GDP_ADVANCE_NEWS_HTML.replace(GDP_ADVANCE_XLSX_URL.replace("https://www.bea.gov", ""), PIO_XLSX_URL),
            ADVANCE_NEWS_URL,
        )
        with self.assertRaisesRegex(ValueError, "GDP attachment identity"):
            build_bea_provider(
                date(2025, 9, 22), date(2025, 9, 28), session
            ).fetch()

        session = self._single_page_session()
        session.responses[PIO_NEWS_URL] = FakeResponse(
            PIO_NEWS_HTML.replace(PIO_XLSX_URL.replace("https://www.bea.gov", ""), GDP_ADVANCE_XLSX_URL),
            PIO_NEWS_URL,
        )
        with self.assertRaisesRegex(ValueError, "PIO attachment identity"):
            build_bea_provider(
                date(2025, 9, 22), date(2025, 9, 28), session
            ).fetch()

    def test_pdf_requires_unique_table_markers_headers_and_series(self):
        malformed_layouts = (
            PIO_PDF_LAYOUT.replace("Table 7.", "Appendix 7."),
            PIO_PDF_LAYOUT + "\nTable 7. duplicate marker",
            PIO_PDF_LAYOUT.replace(
                "Line                                   July      Aug. p",
                "Line                                   July      Aug. p\n"
                "Line                                   July      Aug. p",
            ),
            PIO_PDF_LAYOUT.replace(
                "6 PCE excluding food and energy             2.9 2.9 6",
                "6 PCE excluding food and energy             2.9 2.9 6\n"
                "6 PCE excluding food and energy             9.9 9.9 6",
            ),
        )
        for layout in malformed_layouts:
            with self.subTest(layout=layout[-50:]):
                session = self._pdf_session(_pdf_bytes(layout))
                with self.assertRaisesRegex(ValueError, "unique|duplicate|ambiguous"):
                    build_bea_provider(
                        date(2025, 9, 22), date(2025, 9, 28), session
                    ).fetch()

    def test_wrong_content_type_or_signature_fails_closed(self):
        session = self._single_page_session()
        session.responses[GDP_ADVANCE_XLSX_URL] = FakeResponse(b"not-a-zip", GDP_ADVANCE_XLSX_URL, content_type=XLSX_TYPE)
        with self.assertRaisesRegex(ValueError, "XLSX signature"):
            build_bea_provider(date(2025, 9, 22), date(2025, 9, 28), session).fetch()

        session = self._single_page_session()
        session.responses[GDP_ADVANCE_XLSX_URL] = FakeResponse(_gdp_xlsx(), GDP_ADVANCE_XLSX_URL, content_type="text/html")
        with self.assertRaisesRegex(ValueError, "content type"):
            build_bea_provider(date(2025, 9, 22), date(2025, 9, 28), session).fetch()

    def test_external_redirected_or_missing_release_artifacts_fail_closed(self):
        external_page = GDP_ADVANCE_NEWS_HTML.replace(GDP_ADVANCE_XLSX_URL.replace("https://www.bea.gov", ""), "https://example.test/gdp.xlsx")
        session = self._single_page_session()
        session.responses[ADVANCE_NEWS_URL] = FakeResponse(external_page, ADVANCE_NEWS_URL)
        with self.assertRaisesRegex(ValueError, "official BEA attachment"):
            build_bea_provider(date(2025, 9, 22), date(2025, 9, 28), session).fetch()

        session = self._single_page_session()
        session.responses[GDP_ADVANCE_XLSX_URL] = FakeResponse(_gdp_xlsx(), "https://www.bea.gov/redirected.xlsx", content_type=XLSX_TYPE)
        with self.assertRaisesRegex(ValueError, "redirect"):
            build_bea_provider(date(2025, 9, 22), date(2025, 9, 28), session).fetch()

        session = self._single_page_session()
        session.responses[PIO_NEWS_URL] = FakeResponse(_release_page("Personal Income and Outlays, August 2025", "EDT, Friday, September 26, 2025"), PIO_NEWS_URL)
        with self.assertRaisesRegex(ValueError, "trustworthy release-specific artifact"):
            build_bea_provider(date(2025, 9, 22), date(2025, 9, 28), session).fetch()

    def test_archive_pagination_cycle_and_external_next_link_fail(self):
        cycle = _archive_page([], "?page=1")
        session = FakeSession({BEA_ARCHIVE: FakeResponse(cycle, BEA_ARCHIVE), BEA_ARCHIVE + "?page=1": FakeResponse(cycle, BEA_ARCHIVE + "?page=1")})
        with self.assertRaisesRegex(ValueError, "cycle"):
            build_bea_provider(date(2020, 1, 1), date(2020, 1, 5), session).fetch()

        external = FakeSession({BEA_ARCHIVE: FakeResponse(_archive_page([], "https://example.test/page=1"), BEA_ARCHIVE)})
        with self.assertRaisesRegex(ValueError, "official BEA archive"):
            build_bea_provider(date(2020, 1, 1), date(2020, 1, 5), external).fetch()

    def _single_page_session(self):
        archive = _archive_page(
            [
                (ADVANCE_NEWS_URL, "GDP (Advance Estimate), 2nd Quarter 2025", "2025-07-30T08:30:00-04:00"),
                (PIO_NEWS_URL, "Personal Income and Outlays, August 2025", "2025-09-26T08:30:00-04:00"),
            ]
        )
        return FakeSession(
            {
                BEA_ARCHIVE: FakeResponse(archive, BEA_ARCHIVE),
                ADVANCE_NEWS_URL: FakeResponse(GDP_ADVANCE_NEWS_HTML, ADVANCE_NEWS_URL),
                GDP_ADVANCE_XLSX_URL: FakeResponse(_gdp_xlsx(), GDP_ADVANCE_XLSX_URL, content_type=XLSX_TYPE),
                PIO_NEWS_URL: FakeResponse(PIO_NEWS_HTML, PIO_NEWS_URL),
                PIO_XLSX_URL: FakeResponse(_pio_xlsx(), PIO_XLSX_URL, content_type=XLSX_TYPE),
            }
        )

    def _pdf_session(self, pdf):
        session = self._single_page_session()
        session.responses[PIO_NEWS_URL] = FakeResponse(
            _release_page(
                "Personal Income and Outlays, August 2025",
                "EDT, Friday, September 26, 2025",
                (
                    "Full Release & Tables",
                    "/sites/default/files/2025-09/pi0825.pdf",
                ),
            ),
            PIO_NEWS_URL,
        )
        session.responses[PIO_PDF_URL] = FakeResponse(
            pdf, PIO_PDF_URL, content_type="application/pdf"
        )
        return session

    def _assert_inputs_resolve_within_artifact(self, rows, indicator_code):
        row = next(item for item in rows if item["indicator_code"] == indicator_code)
        self.assertEqual(row["formula_version"], "economic-v1")
        inputs = row["input_record_ids"].split("|")
        by_id = {item["record_id"]: item for item in rows}
        self.assertTrue(all(record_id in by_id for record_id in inputs))
        self.assertTrue(
            all(
                by_id[record_id]["source_url"] == row["source_url"]
                for record_id in inputs
            )
        )
        self.assertTrue(
            all(
                by_id[record_id]["vintage_date"] == row["vintage_date"]
                for record_id in inputs
            )
        )


if __name__ == "__main__":
    unittest.main()
