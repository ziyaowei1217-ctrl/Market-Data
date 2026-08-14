from datetime import date
import unittest

from capital_weekly.context.economic_sources.bls import (
    CPI_ARCHIVE,
    EMPLOYMENT_ARCHIVE,
    build_bls_provider,
    parse_cpi_release,
    parse_employment_release,
)


CPI_ARCHIVE_HTML = """
<html><body>
<p>Transmission of material in this release is embargoed until
8:30 a.m. (ET) Tuesday, July 14, 2026.</p>
<table>
  <caption>Table A. Percent changes in CPI for All Urban Consumers (CPI-U): U.S. city average</caption>
  <thead>
    <tr><th rowspan="2"></th><th colspan="3">Seasonally adjusted changes from preceding month</th><th rowspan="2">Unadjusted 12-mos. ended July 2026</th></tr>
    <tr><th>May 2026</th><th>June 2026</th><th>July 2026</th></tr>
  </thead>
  <tbody>
    <tr><th>All items</th><td>0.2</td><td>0.3</td><td>0.4</td><td>3.1</td></tr>
    <tr><th>All items less food and energy</th><td>0.2</td><td>0.2</td><td>0.3</td><td>2.8</td></tr>
  </tbody>
</table>
<table>
  <caption>Table 1. Consumer Price Index for All Urban Consumers (CPI-U): U.S. city average, by expenditure category, July 2026 [1982-84=100, unless otherwise noted]</caption>
  <thead>
    <tr>
      <th rowspan="2">Expenditure category</th>
      <th rowspan="2">Relative importance June 2026</th>
      <th colspan="3">Unadjusted indexes</th>
      <th colspan="2">Unadjusted percent change</th>
      <th colspan="3">Seasonally adjusted percent change</th>
    </tr>
    <tr>
      <th>July 2025</th><th>June 2026</th><th>July 2026</th>
      <th>July 2025-July 2026</th><th>June 2026-July 2026</th>
      <th>April 2026-May 2026</th><th>May 2026-June 2026</th><th>June 2026-July 2026</th>
    </tr>
  </thead>
  <tbody>
    <tr><th>All items</th><td>100.000</td><td>317.000</td><td>326.000</td><td>327.000</td><td>3.1</td><td>0.3</td><td>0.2</td><td>0.3</td><td>0.4</td></tr>
    <tr><th>All items less food and energy</th><td>80.000</td><td>322.000</td><td>332.000</td><td>333.000</td><td>3.4</td><td>0.3</td><td>0.2</td><td>0.2</td><td>0.3</td></tr>
  </tbody>
</table>
</body></html>
"""

EMPLOYMENT_ARCHIVE_HTML = """
<html><body>
<p>Transmission of material in this news release is embargoed until
8:30 a.m. (ET) Friday, June 5, 2026.</p>
<p>Total nonfarm payroll employment increased by 172,000 in May, and the unemployment rate was unchanged at 4.3 percent.</p>
<p>The change in total nonfarm payroll employment for March was revised up by 29,000, from +185,000 to +214,000, and the change for April was revised up by 64,000, from +115,000 to +179,000. With these revisions, employment in March and April combined is 93,000 higher than previously reported.</p>
<table>
  <caption>Summary table A. Household data, seasonally adjusted [Numbers in thousands]</caption>
  <thead>
    <tr><th rowspan="2">Category</th><th rowspan="2">May 2025</th><th rowspan="2">Mar. 2026</th><th rowspan="2">Apr. 2026</th><th rowspan="2">May 2026</th><th>Change from:</th></tr>
    <tr><th>Apr. 2026-May 2026</th></tr>
  </thead>
  <tbody>
    <tr><th colspan="6">Employment status</th></tr>
    <tr><th>Unemployment rate</th><td>4.3</td><td>4.3</td><td>4.3</td><td>4.3</td><td>0.0</td></tr>
  </tbody>
</table>
<table>
  <caption>Summary table B. Establishment data, seasonally adjusted</caption>
  <thead>
    <tr><th>Category</th><th>May 2025</th><th>Mar. 2026</th><th>Apr. 2026<sup>p</sup></th><th>May 2026<sup>p</sup></th></tr>
  </thead>
  <tbody>
    <tr><th colspan="5">EMPLOYMENT BY SELECTED INDUSTRY</th></tr>
    <tr><th colspan="5">(Over-the-month change, in thousands)</th></tr>
    <tr><th>Total nonfarm</th><td>13</td><td>214</td><td>179</td><td>172</td></tr>
    <tr><th colspan="5">(3-month average change, in thousands)</th></tr>
    <tr><th>Total nonfarm</th><td>63</td><td>73</td><td>79</td><td>188</td></tr>
  </tbody>
  <tfoot><tr><td colspan="5">(p) Preliminary</td></tr></tfoot>
</table>
</body></html>
"""


class FakeResponse:
    def __init__(self, text, url, *, status_code=200, history=()):
        self.text = text
        self.url = url
        self.status_code = status_code
        self.history = list(history)
        self.encoding = "utf-8"

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


def archive_index(*links):
    return "<html><body>" + "".join(
        f'<a href="{link}">release</a>' for link in links
    ) + "</body></html>"


class BlsEconomicReleaseTests(unittest.TestCase):
    def test_cpi_official_layout_selects_unadjusted_index_columns_not_percent_table(self):
        rows = parse_cpi_release(
            CPI_ARCHIVE_HTML,
            "https://www.bls.gov/news.release/archives/cpi_07142026.htm",
            date(2026, 7, 19),
        )

        observed = {
            row["indicator_code"]: row
            for row in rows
            if row["calculation_id"] == "observed"
            and row["observation_period"] == "2026-07"
        }
        self.assertEqual(observed["CPI_INDEX_NSA"]["value"], 327.0)
        self.assertEqual(observed["CORE_CPI_INDEX_NSA"]["value"], 333.0)
        self.assertEqual(observed["CPI_INDEX_NSA"]["unit"], "index")
        self.assertEqual(
            observed["CPI_INDEX_NSA"]["seasonal_adjustment"],
            "not seasonally adjusted",
        )
        self.assertNotIn(0.4, [row["value"] for row in observed.values()])
        codes = {row["indicator_code"] for row in rows}
        self.assertIn("CPI_INDEX_NSA_MOM_PCT", codes)
        self.assertIn("CPI_INDEX_NSA_YOY_PCT", codes)

    def test_cpi_requires_headline_and_core_for_the_same_latest_period(self):
        stale_core = CPI_ARCHIVE_HTML.replace(
            "<td>333.000</td><td>3.4</td>", "<td>--</td><td>3.4</td>"
        )

        with self.assertRaisesRegex(ValueError, "same latest observation period"):
            parse_cpi_release(
                stale_core,
                "https://www.bls.gov/news.release/archives/cpi_07142026.htm",
                date(2026, 7, 19),
            )

    def test_employment_official_layout_uses_separate_tables_and_revision_disclosure(self):
        rows = parse_employment_release(
            EMPLOYMENT_ARCHIVE_HTML,
            "https://www.bls.gov/news.release/archives/empsit_06052026.htm",
            date(2026, 6, 7),
        )

        nfp = next(
            row
            for row in rows
            if row["indicator_code"] == "NFP_CHANGE"
            and row["observation_period"] == "2026-05"
        )
        self.assertEqual(nfp["known_as_of"], "2026-06-05T08:30:00-04:00")
        self.assertEqual(nfp["value"], 172000.0)
        self.assertEqual(nfp["previous_value"], 115000.0)
        self.assertEqual(nfp["revised_previous"], 179000.0)
        revisions = {
            row["observation_period"]: (
                row["value"],
                row["previous_value"],
                row["revised_previous"],
            )
            for row in rows
            if row["indicator_code"] == "NFP_CHANGE"
            and row["observation_period"] != "2026-05"
        }
        self.assertEqual(
            revisions,
            {
                "2026-04": (179000.0, 115000.0, None),
                "2026-03": (214000.0, 185000.0, None),
            },
        )
        unemployment = next(
            row for row in rows if row["indicator_code"] == "UNEMPLOYMENT_RATE"
        )
        self.assertEqual(unemployment["observation_period"], "2026-05")
        self.assertEqual(unemployment["value"], 4.3)
        self.assertEqual(unemployment["previous_value"], 4.3)

    def test_monday_release_is_excluded_from_the_prior_sunday(self):
        monday = EMPLOYMENT_ARCHIVE_HTML.replace(
            "Friday, June 5, 2026", "Monday, June 8, 2026"
        )

        rows = parse_employment_release(
            monday,
            "https://www.bls.gov/news.release/archives/empsit_06082026.htm",
            date(2026, 6, 7),
        )

        self.assertEqual(rows, [])

    def test_conflicting_duplicate_cpi_index_cells_are_rejected(self):
        conflicting = CPI_ARCHIVE_HTML.replace(
            "</tbody>\n</table>\n</body>",
            "<tr><th>All items</th><td>100.000</td><td>317.000</td>"
            "<td>326.000</td><td>999.000</td><td>3.1</td><td>0.3</td>"
            "<td>0.2</td><td>0.3</td><td>0.4</td></tr></tbody></table></body>",
        )

        with self.assertRaisesRegex(ValueError, "Conflicting duplicate"):
            parse_cpi_release(
                conflicting,
                "https://www.bls.gov/news.release/archives/cpi_07142026.htm",
                date(2026, 7, 19),
            )

    def test_provider_fetches_only_latest_filename_candidates(self):
        cpi_url = "https://www.bls.gov/news.release/archives/cpi_07142026.htm"
        jobs_url = "https://www.bls.gov/news.release/archives/empsit_06052026.htm"
        old_cpi = "https://www.bls.gov/news.release/archives/cpi_01012020.htm"
        old_jobs = "https://www.bls.gov/news.release/archives/empsit_01012020.htm"
        monday_cpi = "https://www.bls.gov/news.release/archives/cpi_07202026.htm"
        session = FakeSession(
            {
                CPI_ARCHIVE: FakeResponse(
                    archive_index(old_cpi, monday_cpi, cpi_url), CPI_ARCHIVE
                ),
                EMPLOYMENT_ARCHIVE: FakeResponse(
                    archive_index(old_jobs, jobs_url), EMPLOYMENT_ARCHIVE
                ),
                old_cpi: RuntimeError("irrelevant old CPI is unavailable"),
                old_jobs: RuntimeError("irrelevant old employment is unavailable"),
                monday_cpi: RuntimeError("post-cutoff CPI must not be fetched"),
                cpi_url: FakeResponse(CPI_ARCHIVE_HTML, cpi_url),
                jobs_url: FakeResponse(EMPLOYMENT_ARCHIVE_HTML, jobs_url),
            }
        )

        result = build_bls_provider(
            date(2026, 7, 13), date(2026, 7, 19), session
        ).fetch()

        called_urls = [url for url, _ in session.calls]
        self.assertEqual(
            called_urls, [CPI_ARCHIVE, cpi_url, EMPLOYMENT_ARCHIVE, jobs_url]
        )
        self.assertTrue(any(row["indicator_code"] == "CPI_INDEX_NSA" for row in result.rows))
        self.assertTrue(all(kwargs["allow_redirects"] is False for _, kwargs in session.calls))

    def test_malformed_latest_filename_candidate_fails_instead_of_falling_back(self):
        latest = "https://www.bls.gov/news.release/archives/cpi_07142026.htm"
        old = "https://www.bls.gov/news.release/archives/cpi_06102026.htm"
        session = FakeSession(
            {
                CPI_ARCHIVE: FakeResponse(archive_index(old, latest), CPI_ARCHIVE),
                latest: FakeResponse("<html>missing release contract</html>", latest),
                old: FakeResponse(CPI_ARCHIVE_HTML, old),
            }
        )

        with self.assertRaisesRegex(ValueError, "embargo timestamp"):
            build_bls_provider(
                date(2026, 7, 13), date(2026, 7, 19), session
            ).fetch()
        self.assertNotIn(old, [url for url, _ in session.calls])

    def test_equal_latest_artifacts_with_conflicting_identity_are_rejected(self):
        first = "https://www.bls.gov/news.release/archives/cpi_07142026.htm?v=1"
        second = "https://www.bls.gov/news.release/archives/cpi_07142026.htm?v=2"
        conflict = CPI_ARCHIVE_HTML.replace("<td>327.000</td>", "<td>999.000</td>", 1)
        session = FakeSession(
            {
                CPI_ARCHIVE: FakeResponse(archive_index(first, second), CPI_ARCHIVE),
                first: FakeResponse(CPI_ARCHIVE_HTML, first),
                second: FakeResponse(conflict, second),
            }
        )

        with self.assertRaisesRegex(ValueError, "Conflicting BLS artifacts"):
            build_bls_provider(
                date(2026, 7, 13), date(2026, 7, 19), session
            ).fetch()

    def test_missing_core_cpi_fails_the_required_provider(self):
        cpi_url = "https://www.bls.gov/news.release/archives/cpi_07142026.htm"
        jobs_url = "https://www.bls.gov/news.release/archives/empsit_06052026.htm"
        missing_core = CPI_ARCHIVE_HTML.replace(
            "<tr><th>All items less food and energy</th><td>80.000</td>"
            "<td>322.000</td><td>332.000</td><td>333.000</td><td>3.4</td>"
            "<td>0.3</td><td>0.2</td><td>0.2</td><td>0.3</td></tr>",
            "",
        )
        session = FakeSession(
            {
                CPI_ARCHIVE: FakeResponse(archive_index(cpi_url), CPI_ARCHIVE),
                EMPLOYMENT_ARCHIVE: FakeResponse(archive_index(jobs_url), EMPLOYMENT_ARCHIVE),
                cpi_url: FakeResponse(missing_core, cpi_url),
                jobs_url: FakeResponse(EMPLOYMENT_ARCHIVE_HTML, jobs_url),
            }
        )

        with self.assertRaisesRegex(ValueError, "Core CPI"):
            build_bls_provider(
                date(2026, 7, 13), date(2026, 7, 19), session
            ).fetch()

    def test_provider_rejects_redirects_and_external_archive_links(self):
        redirected = FakeSession(
            {
                CPI_ARCHIVE: FakeResponse(
                    "", CPI_ARCHIVE, status_code=302, history=(object(),)
                )
            }
        )
        with self.assertRaisesRegex(ValueError, "redirect"):
            build_bls_provider(
                date(2026, 7, 13), date(2026, 7, 19), redirected
            ).fetch()

        external = "https://example.test/news.release/archives/cpi_07142026.htm"
        offsite = FakeSession(
            {CPI_ARCHIVE: FakeResponse(archive_index(external), CPI_ARCHIVE)}
        )
        with self.assertRaisesRegex(ValueError, "official BLS archive"):
            build_bls_provider(
                date(2026, 7, 13), date(2026, 7, 19), offsite
            ).fetch()


if __name__ == "__main__":
    unittest.main()
