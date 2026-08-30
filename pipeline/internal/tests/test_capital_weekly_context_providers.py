from datetime import date
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from pipeline.internal.capital_weekly.context.providers import (
    COMEX_COPPER_STOCKS_URL,
    CFTC_DISAGGREGATED_URL,
    build_default_providers,
    metric_rows,
    not_configured_result,
)
from pipeline.internal.capital_weekly.context.common import METRIC_FIELDS
from pipeline.internal.capital_weekly.context.provider_contracts import (
    ContextProvider,
    ProviderResult,
    ProviderSpec,
)
from pipeline.internal.capital_weekly.weekly_context import run_weekly_context
from pipeline.internal.tests.test_capital_weekly_metal_inventories import (
    COPPER_BIFF8,
    USGS_GOLD_PDF,
)


EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


YAHOO_CONFIG = (
    "metric_code,metric_name,ticker,unit,role\n"
    "vix_9d_level,Cboe S&P 500 9-Day Volatility Index,^VIX9D,index_points,vix_9d\n"
    "vix_1m_level,Cboe VIX 30-Day Volatility Index,^VIX,index_points,vix_1m\n"
    "vix_3m_level,Cboe S&P 500 3-Month Volatility Index,^VIX3M,index_points,vix_3m\n"
    "vix_6m_level,Cboe S&P 500 6-Month Volatility Index,^VIX6M,index_points,vix_6m\n"
    "cboe_skew_level,Cboe SKEW Index,^SKEW,index_points,skew\n"
)
CFTC_COLUMNS = (
    "market_and_exchange_names,cftc_contract_market_code,"
    "report_date_as_yyyy_mm_dd,open_interest_all,"
    "prod_merc_positions_long,prod_merc_positions_short,"
    "swap_positions_long_all,swap__positions_short_all,"
    "m_money_positions_long_all,m_money_positions_short_all,"
    "other_rept_positions_long,other_rept_positions_short\n"
)


class TextResponse:
    encoding = "utf-8"
    apparent_encoding = "utf-8"

    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class TextSession:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return TextResponse(self.text)


class JsonResponse:
    encoding = "utf-8"
    apparent_encoding = "utf-8"

    def __init__(self, payload):
        self.payload = payload
        self.text = json.dumps(payload, separators=(",", ":"))

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class JsonSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return JsonResponse(response)


class BinaryResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None


class BinarySession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return BinaryResponse(response)


def write_provider_configs(data_dir):
    (data_dir / "capital_weekly_company_watchlist.csv").write_text(
        "ticker,cik,company_name,enabled\n", encoding="utf-8"
    )
    (data_dir / "capital_weekly_cftc_contracts.csv").write_text(
        "contract_code,metric_code,report_family,market_name,commodity_code,"
        "commodity_family,percentile_window,percentile_min_observations\n"
        "13874A,sp500,tff,S&P 500 Consolidated,,,,\n"
        "088691,GOLD_COT,disaggregated,GOLD - COMMODITY EXCHANGE INC.,"
        "GOLD_COMEX,gold,156,52\n",
        encoding="utf-8",
    )
    (data_dir / "capital_weekly_eia_series.csv").write_text(
        "provider,commodity_code,commodity_family,route,frequency,facets,"
        "metric_code,metric_name,measurement_kind,source_description,"
        "expected_unit,freshness_days\n",
        encoding="utf-8",
    )
    (data_dir / "capital_weekly_financial_conditions.csv").write_text(
        "metric_code,metric_name,series_id,risk_direction\n"
        "vix,VIX,VIXCLS,1\n",
        encoding="utf-8",
    )
    (data_dir / "capital_weekly_yahoo_volatility.csv").write_text(
        YAHOO_CONFIG, encoding="utf-8"
    )
    (data_dir / "capital_weekly_usda_psd.csv").write_text(
        "commodity_code,commodity_family,commodity_name,country_names,"
        "market_year_offsets,attributes,unit_names\n",
        encoding="utf-8",
    )
    (data_dir / "capital_weekly_usda_esr.csv").write_text(
        "commodity_code,commodity_family,commodity_name,route,"
        "market_year_offsets,unit_name\n",
        encoding="utf-8",
    )


class ContextProviderTests(unittest.TestCase):
    def test_usda_families_are_independently_not_configured_before_validation(self):
        class NoNetworkSession:
            calls = []

            def get(self, *_args, **_kwargs):
                raise AssertionError("missing USDA key must not call transport")

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            (data_dir / "capital_weekly_usda_psd.csv").write_text(
                "bad,columns\ninvalid,row\n", encoding="utf-8"
            )
            (data_dir / "capital_weekly_usda_esr.csv").write_text(
                "also,bad\ninvalid,row\n", encoding="utf-8"
            )
            session = NoNetworkSession()
            providers = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={},
                session=session,
            )

            psd = providers["usda_psd"].fetch()
            esr = providers["usda_esr"].fetch()

        self.assertEqual(psd.status, "NOT_CONFIGURED")
        self.assertEqual(esr.status, "NOT_CONFIGURED")
        self.assertEqual(psd.rows, [])
        self.assertEqual(esr.rows, [])
        self.assertEqual(session.calls, [])
        self.assertEqual(providers["usda_psd"].spec.requiredness, "optional")
        self.assertEqual(providers["usda_esr"].spec.requiredness, "optional")
        self.assertNotEqual(psd.notes, esr.notes)

    def test_keyed_usda_families_use_lookups_native_units_and_secretless_audits(self):
        fixture_root = Path(__file__).with_name("fixtures") / "usda"
        lookups = json.loads(
            (fixture_root / "psd_lookups.json").read_text(encoding="utf-8")
        )
        psd_records = json.loads(
            (fixture_root / "psd_records.json").read_text(encoding="utf-8")
        )
        esr_records = json.loads(
            (fixture_root / "esr_records.json").read_text(encoding="utf-8")
        )
        base = "https://api.fas.usda.gov"
        responses = {
            f"{base}/api/psd/commodities": lookups["commodities"],
            f"{base}/api/psd/commodityAttributes": lookups["attributes"],
            f"{base}/api/psd/countries": lookups["countries"],
            f"{base}/api/psd/unitsOfMeasure": lookups["units"],
            f"{base}/api/psd/commodity/0440000/dataReleaseDates": [
                {
                    "commodityCode": "0440000",
                    "marketYear": 2026,
                    "releaseDate": "2026-08-12T12:00:00-04:00",
                }
            ],
            f"{base}/api/psd/commodity/0440000/world/year/2026": psd_records,
            f"{base}/api/esr/commodities": [
                {"commodityCode": 101, "commodityName": "Corn"}
            ],
            f"{base}/api/esr/countries": [
                {"countryCode": 1220, "countryName": "Canada"},
                {"countryCode": 2010, "countryName": "Mexico"},
            ],
            f"{base}/api/esr/unitsOfMeasure": [
                {"unitId": 1, "unitNames": "Metric Tons"}
            ],
            f"{base}/api/esr/datareleasedates": [
                {
                    "commodityCode": 101,
                    "marketYear": 2026,
                    "releaseDate": "2026-08-27T08:30:00-04:00",
                }
            ],
            f"{base}/api/esr/exports/commodityCode/101/allCountries/marketYear/2026": esr_records,
        }
        secret = "usda-secret-test-key"

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            psd_row = {
                "commodity_code": "CORN",
                "commodity_family": "grains_oilseeds",
                "commodity_name": "Corn",
                "country_names": json.dumps(["World"]),
                "market_year_offsets": json.dumps([0]),
                "attributes": json.dumps({
                    "beginning_stocks": "Beginning Stocks",
                    "production": "Production",
                    "imports": "MY Imports",
                    "exports": "MY Exports",
                    "feed_use": "Feed Dom. Consumption",
                    "industrial_use": "Industrial Dom. Consumption",
                    "domestic_use": "Total Dom. Consumption",
                    "ending_stocks": "Ending Stocks",
                }),
                "unit_names": json.dumps(["1000 MT"]),
            }
            with (data_dir / "capital_weekly_usda_psd.csv").open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=list(psd_row))
                writer.writeheader()
                writer.writerow(psd_row)
            esr_row = {
                "commodity_code": "CORN",
                "commodity_family": "grains_oilseeds",
                "commodity_name": "Corn",
                "route": "allCountries",
                "market_year_offsets": json.dumps([0]),
                "unit_name": "Metric Tons",
            }
            with (data_dir / "capital_weekly_usda_esr.csv").open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=list(esr_row))
                writer.writeheader()
                writer.writerow(esr_row)
            session = JsonSession(responses)
            providers = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={"USDA_API_KEY": secret},
                session=session,
            )
            raw_dir = data_dir / "raw"
            tables = run_weekly_context(
                {
                    "usda_psd": providers["usda_psd"],
                    "usda_esr": providers["usda_esr"],
                },
                raw_dir=raw_dir,
                as_of_date=date(2026, 8, 30),
            )

            raw_content = b"".join(path.read_bytes() for path in raw_dir.iterdir())

        audits = {row["provider"]: row for row in tables["source_log"]}
        self.assertEqual(audits["usda_psd"]["status"], "OK", audits)
        self.assertEqual(audits["usda_esr"]["status"], "OK", audits)
        self.assertEqual(audits["usda_psd"]["requiredness"], "required")
        self.assertEqual(audits["usda_esr"]["requiredness"], "required")
        self.assertEqual(len(tables["commodity_fundamentals"]), 12)
        self.assertEqual(
            {row["unit"] for row in tables["commodity_fundamentals"]},
            {"1000 MT", "Metric Tons", "ratio"},
        )
        self.assertTrue(all(
            row["source"] == "USDA Foreign Agricultural Service"
            for row in tables["commodity_fundamentals"]
        ))
        self.assertNotIn(secret.encode(), raw_content)
        self.assertNotIn(secret, json.dumps(tables))
        self.assertTrue(all(secret not in url for url, _kwargs in session.calls))
        self.assertTrue(all(
            kwargs["headers"]["API_KEY"] == secret
            for _url, kwargs in session.calls
        ))

    def test_comex_copper_keeps_exact_bytes_and_auditable_provenance(self):
        metal_header = (
            "provider,source_url,source,commodity_code,commodity_family,market,"
            "frequency,freshness_days,expected_sheet,commodity_title,expected_unit,"
            "location_header,registered_total_label,eligible_total_label,"
            "combined_total_label,table_kind,reference_year,publication_date,"
            "publication_month,limitation_note\n"
        )
        metal_row = (
            "comex_copper_stocks,https://www.cmegroup.com/delivery_reports/"
            "Copper_Stocks.xls,CME Group,COPPER_COMEX,copper,COMEX,daily,7,"
            "Daily Metal Stocks Report,COPPER - HIGH GRADE,Short Tons,"
            "DELIVERY POINT,Total Registered (warranted),"
            "Total Eligible (non-warranted),TOTAL COPPER,,,,,"
            "deliverable_inventory_proxy; LME not included\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            (data_dir / "capital_weekly_metals.csv").write_text(
                metal_header + metal_row,
                encoding="utf-8",
            )
            session = BinarySession({COMEX_COPPER_STOCKS_URL: COPPER_BIFF8})
            provider = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={},
                session=session,
            )["comex_copper_stocks"]
            raw_dir = data_dir / "raw"
            tables = run_weekly_context(
                {"comex_copper_stocks": provider},
                raw_dir=raw_dir,
                as_of_date=date(2026, 8, 30),
            )

            self.assertEqual(
                (raw_dir / "comex_copper_stocks.raw").read_bytes(),
                COPPER_BIFF8,
            )

        self.assertEqual(provider.spec.requiredness, "optional")
        self.assertEqual(
            [row["measurement_kind"] for row in tables["commodity_fundamentals"]],
            ["inventory", "inventory", "inventory"],
        )
        self.assertEqual(
            [row["value"] for row in tables["commodity_fundamentals"]],
            [15.0, 35.0, 50.0],
        )
        audit = tables["source_log"][0]
        self.assertEqual(audit["source_url"], COMEX_COPPER_STOCKS_URL)
        self.assertIn(f"bytes={len(COPPER_BIFF8)}", audit["notes"])
        self.assertIn(
            f"sha256={hashlib.sha256(COPPER_BIFF8).hexdigest()}",
            audit["notes"],
        )
        self.assertRegex(
            audit["notes"],
            r"schema_signature=ole2-biff8:sha256:[0-9a-f]{64}",
        )
        self.assertIn("deliverable_inventory_proxy; LME not included", audit["notes"])

    def test_outdated_usgs_table_is_visible_without_transport_or_rows(self):
        metal_header = (
            "provider,source_url,source,commodity_code,commodity_family,market,"
            "frequency,freshness_days,expected_sheet,commodity_title,expected_unit,"
            "location_header,registered_total_label,eligible_total_label,"
            "combined_total_label,table_kind,reference_year,publication_date,"
            "publication_month,limitation_note\n"
        )
        metal_row = (
            "usgs_gold_structural,https://pubs.usgs.gov/periodicals/mcs2026/"
            "mcs2026-gold.pdf,U.S. Geological Survey,GOLD_COMEX,gold,World,annual,"
            "400,,GOLD,\"metric tons, gold content\",,,,,mine_reserves,2025,"
            "2026-02-06,February 2026,monthly Mineral Industry Survey paused\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            (data_dir / "capital_weekly_metals.csv").write_text(
                metal_header + metal_row,
                encoding="utf-8",
            )
            session = BinarySession({})
            provider = build_default_providers(
                start=date(2027, 3, 22),
                end=date(2027, 3, 28),
                data_dir=data_dir,
                environ={},
                session=session,
            )["usgs_gold_structural"]
            result = provider.fetch()

        self.assertEqual(session.calls, [])
        self.assertEqual(result.status, "POINT_IN_TIME_UNAVAILABLE")
        self.assertEqual(result.rows, [])
        self.assertIn("more than 400 days", result.notes)
        self.assertIn("bytes=0", result.notes)
        self.assertIn(f"sha256={EMPTY_SHA256}", result.notes)
        self.assertIn("schema_signature=unverified:no-content", result.notes)

    def test_current_usgs_table_emits_annual_structural_rows(self):
        url = "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-gold.pdf"
        metal_header = (
            "provider,source_url,source,commodity_code,commodity_family,market,"
            "frequency,freshness_days,expected_sheet,commodity_title,expected_unit,"
            "location_header,registered_total_label,eligible_total_label,"
            "combined_total_label,table_kind,reference_year,publication_date,"
            "publication_month,limitation_note\n"
        )
        metal_row = (
            f"usgs_gold_structural,{url},U.S. Geological Survey,GOLD_COMEX,gold,"
            "World,annual,400,,GOLD,\"metric tons, gold content\",,,,,mine_reserves,"
            "2025,2026-02-06,February 2026,"
            "monthly Mineral Industry Survey paused\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            (data_dir / "capital_weekly_metals.csv").write_text(
                metal_header + metal_row,
                encoding="utf-8",
            )
            session = BinarySession({url: USGS_GOLD_PDF})
            provider = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={},
                session=session,
            )["usgs_gold_structural"]
            result = provider.fetch()

        self.assertEqual(result.status, "OK")
        self.assertEqual([row["value"] for row in result.rows], [3300.0, 66000.0])
        self.assertTrue(all(row["measurement_kind"] == "structural" for row in result.rows))
        self.assertTrue(all(row["as_of_date"] == date(2025, 12, 31) for row in result.rows))
        self.assertTrue(
            all(row["known_as_of"].startswith("2026-02-06T23:59:59") for row in result.rows)
        )
        self.assertEqual(result.raw_text, USGS_GOLD_PDF)
        self.assertRegex(
            result.notes,
            r"schema_signature=pdf-usgs-mcs-v1:sha256:[0-9a-f]{64}",
        )

    def test_failed_comex_provider_publishes_no_partial_rows_or_suppresses_usgs(self):
        copper_url = COMEX_COPPER_STOCKS_URL
        gold_url = "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-gold.pdf"
        metal_header = (
            "provider,source_url,source,commodity_code,commodity_family,market,"
            "frequency,freshness_days,expected_sheet,commodity_title,expected_unit,"
            "location_header,registered_total_label,eligible_total_label,"
            "combined_total_label,table_kind,reference_year,publication_date,"
            "publication_month,limitation_note\n"
        )
        copper_row = (
            f"comex_copper_stocks,{copper_url},CME Group,COPPER_COMEX,copper,"
            "COMEX,daily,7,Daily Metal Stocks Report,COPPER - HIGH GRADE,"
            "Short Tons,DELIVERY POINT,Total Registered (warranted),"
            "Total Eligible (non-warranted),TOTAL COPPER,,,,,"
            "deliverable_inventory_proxy; LME not included\n"
        )
        gold_row = (
            f"usgs_gold_structural,{gold_url},U.S. Geological Survey,GOLD_COMEX,"
            "gold,World,annual,400,,GOLD,\"metric tons, gold content\",,,,,"
            "mine_reserves,2025,2026-02-06,February 2026,monthly survey paused\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            (data_dir / "capital_weekly_metals.csv").write_text(
                metal_header + copper_row + gold_row,
                encoding="utf-8",
            )
            session = BinarySession(
                {copper_url: b"not a workbook", gold_url: USGS_GOLD_PDF}
            )
            providers = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={},
                session=session,
            )
            tables = run_weekly_context(
                {
                    name: providers[name]
                    for name in ("comex_copper_stocks", "usgs_gold_structural")
                },
                as_of_date=date(2026, 8, 30),
            )

        audits = {row["provider"]: row for row in tables["source_log"]}
        self.assertEqual(audits["comex_copper_stocks"]["status"], "FETCH_FAILED")
        self.assertEqual(audits["comex_copper_stocks"]["observations"], 0)
        self.assertIn("bytes=14", audits["comex_copper_stocks"]["notes"])
        self.assertIn(
            f"sha256={hashlib.sha256(b'not a workbook').hexdigest()}",
            audits["comex_copper_stocks"]["notes"],
        )
        self.assertIn(
            "schema_signature=unverified:parse-failed",
            audits["comex_copper_stocks"]["notes"],
        )
        self.assertEqual(audits["usgs_gold_structural"]["status"], "OK")
        self.assertEqual(len(tables["commodity_fundamentals"]), 2)
        self.assertTrue(
            all(
                row["commodity_code"] == "GOLD_COMEX"
                for row in tables["commodity_fundamentals"]
            )
        )

    def test_bad_comex_config_fails_only_that_supplemental_provider(self):
        bad_url = "https://example.test/Copper_Stocks.xls"
        gold_url = "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-gold.pdf"
        header = (
            "provider,source_url,source,commodity_code,commodity_family,market,"
            "frequency,freshness_days,expected_sheet,commodity_title,expected_unit,"
            "location_header,registered_total_label,eligible_total_label,"
            "combined_total_label,table_kind,reference_year,publication_date,"
            "publication_month,limitation_note\n"
        )
        rows = (
            f"comex_copper_stocks,{bad_url},CME Group,COPPER_COMEX,copper,COMEX,"
            "daily,7,Daily Metal Stocks Report,COPPER - HIGH GRADE,Short Tons,"
            "DELIVERY POINT,Total Registered (warranted),"
            "Total Eligible (non-warranted),TOTAL COPPER,,,,,limitation\n"
            f"usgs_gold_structural,{gold_url},U.S. Geological Survey,GOLD_COMEX,"
            "gold,World,annual,400,,GOLD,\"metric tons, gold content\",,,,,"
            "mine_reserves,2025,2026-02-06,February 2026,monthly survey paused\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            (data_dir / "capital_weekly_metals.csv").write_text(
                header + rows,
                encoding="utf-8",
            )
            session = BinarySession({gold_url: USGS_GOLD_PDF})
            providers = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={},
                session=session,
            )
            tables = run_weekly_context(
                {
                    name: providers[name]
                    for name in ("comex_copper_stocks", "usgs_gold_structural")
                },
                as_of_date=date(2026, 8, 30),
            )

        audits = {row["provider"]: row for row in tables["source_log"]}
        self.assertEqual(audits["comex_copper_stocks"]["status"], "FETCH_FAILED")
        self.assertEqual(audits["usgs_gold_structural"]["status"], "OK")
        self.assertEqual(len(tables["commodity_fundamentals"]), 2)
        self.assertIn("bytes=0", audits["comex_copper_stocks"]["notes"])
        self.assertIn(
            f"sha256={EMPTY_SHA256}",
            audits["comex_copper_stocks"]["notes"],
        )
        self.assertIn(
            "schema_signature=unverified:no-content",
            audits["comex_copper_stocks"]["notes"],
        )

    def test_transport_and_zero_byte_failures_report_empty_provenance(self):
        copper_url = COMEX_COPPER_STOCKS_URL
        gold_url = "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-gold.pdf"
        header = (
            "provider,source_url,source,commodity_code,commodity_family,market,"
            "frequency,freshness_days,expected_sheet,commodity_title,expected_unit,"
            "location_header,registered_total_label,eligible_total_label,"
            "combined_total_label,table_kind,reference_year,publication_date,"
            "publication_month,limitation_note\n"
        )
        rows = (
            f"comex_copper_stocks,{copper_url},CME Group,COPPER_COMEX,copper,"
            "COMEX,daily,7,Daily Metal Stocks Report,COPPER - HIGH GRADE,"
            "Short Tons,DELIVERY POINT,Total Registered (warranted),"
            "Total Eligible (non-warranted),TOTAL COPPER,,,,,"
            "deliverable_inventory_proxy; LME not included\n"
            f"usgs_gold_structural,{gold_url},U.S. Geological Survey,GOLD_COMEX,"
            "gold,World,annual,400,,GOLD,\"metric tons, gold content\",,,,,"
            "mine_reserves,2025,2026-02-06,February 2026,monthly survey paused\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            (data_dir / "capital_weekly_metals.csv").write_text(
                header + rows,
                encoding="utf-8",
            )
            session = BinarySession(
                {
                    copper_url: RuntimeError("transport unavailable"),
                    gold_url: b"",
                }
            )
            providers = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={},
                session=session,
            )
            tables = run_weekly_context(
                {
                    name: providers[name]
                    for name in ("comex_copper_stocks", "usgs_gold_structural")
                },
                as_of_date=date(2026, 8, 30),
            )

        audits = {row["provider"]: row for row in tables["source_log"]}
        for name, audit in audits.items():
            with self.subTest(provider=name):
                self.assertEqual(audit["status"], "FETCH_FAILED")
                self.assertEqual(audit["observations"], 0)
                self.assertIn("bytes=0", audit["notes"])
                self.assertIn(f"sha256={EMPTY_SHA256}", audit["notes"])
                self.assertIn(
                    "schema_signature=unverified:no-content",
                    audit["notes"],
                )

    def test_eia_families_are_independently_not_configured_without_key(self):
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            (data_dir / "capital_weekly_eia_series.csv").write_text(
                "provider,commodity_family,route\n"
                "misspelled_natural,natural_gas,not-queried-without-a-key\n"
                "misspelled_refined,refined_products,not-queried-without-a-key\n",
                encoding="utf-8",
            )
            providers = build_default_providers(
                start=date(2026, 8, 17),
                end=date(2026, 8, 23),
                data_dir=data_dir,
                environ={},
            )

        for name in ("eia_natural_gas", "eia_refined_products"):
            with self.subTest(provider=name):
                self.assertIn(name, providers)
                self.assertEqual(providers[name].spec.requiredness, "optional")
                result = providers[name].fetch()
                self.assertEqual(result.status, "NOT_CONFIGURED")
                self.assertEqual(result.rows, [])

    def test_eia_families_use_exact_routes_facets_and_isolate_transport_failure(self):
        natural = {
            "provider": "eia_natural_gas",
            "commodity_code": "NATGAS_HH",
            "commodity_family": "natural_gas",
            "route": "natural-gas/stor/wkly",
            "frequency": "weekly",
            "facets": json.dumps({
                "duoarea": "R48",
                "process": "SWO",
                "series": "NW2_EPG0_SWO_R48_BCF",
            }),
            "metric_code": "eia_ng_storage_lower48",
            "metric_name": "Lower 48 working gas",
            "measurement_kind": "physical_level",
            "source_description": "Lower 48 storage",
            "expected_unit": "BCF",
            "freshness_days": "10",
        }
        refined = {
            "provider": "eia_refined_products",
            "commodity_code": "WTI",
            "commodity_family": "refined_products",
            "route": "petroleum/sum/sndw",
            "frequency": "weekly",
            "facets": json.dumps({"series": "A&B"}),
            "metric_code": "eia_crude_stocks_ex_spr",
            "metric_name": "Crude stocks excluding SPR",
            "measurement_kind": "physical_level",
            "source_description": "Crude stocks excluding SPR",
            "expected_unit": "MBBL",
            "freshness_days": "10",
        }

        class EiaSession:
            def __init__(self):
                self.calls = []

            def get(self, url, **kwargs):
                self.calls.append((url, kwargs))
                if "natural-gas" in url:
                    raise RuntimeError("natural gas transport failed")
                if "/facet/series/" in url:
                    return TextResponse(json.dumps({
                        "response": {"facets": [{"id": "A&B", "name": "Crude"}]}
                    }))
                return TextResponse(json.dumps({
                    "response": {"data": [
                        {
                            "period": "2026-08-21",
                            "series": "A&B",
                            "series-description": "Crude stocks excluding SPR",
                            "units": "MBBL",
                            "value": "425000",
                        },
                        {
                            "period": "2026-08-14",
                            "series": "A&B",
                            "series-description": "Crude stocks excluding SPR",
                            "units": "MBBL",
                            "value": "420000",
                        },
                    ]}
                }))

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            fields = list(natural)
            with (data_dir / "capital_weekly_eia_series.csv").open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows([natural, refined])
            session = EiaSession()
            providers = build_default_providers(
                start=date(2026, 8, 17),
                end=date(2026, 8, 23),
                data_dir=data_dir,
                environ={"EIA_API_KEY": "dummy-key"},
                session=session,
            )
            tables = run_weekly_context(
                {
                    "eia_natural_gas": providers["eia_natural_gas"],
                    "eia_refined_products": providers["eia_refined_products"],
                },
                as_of_date=date(2026, 8, 23),
            )

        audits = {row["provider"]: row for row in tables["source_log"]}
        self.assertEqual(audits["eia_natural_gas"]["status"], "FETCH_FAILED")
        self.assertEqual(audits["eia_natural_gas"]["requiredness"], "required")
        self.assertEqual(audits["eia_refined_products"]["status"], "OK")
        self.assertEqual(len(tables["commodity_fundamentals"]), 3)
        refined_calls = [call for call in session.calls if "petroleum" in call[0]]
        self.assertEqual(
            [call[0] for call in refined_calls],
            [
                "https://api.eia.gov/v2/petroleum/sum/sndw/facet/series/",
                "https://api.eia.gov/v2/petroleum/sum/sndw/data/",
            ],
        )
        self.assertEqual(
            refined_calls[1][1]["params"]["facets[series][]"],
            "A&B",
        )
        self.assertNotIn("dummy-key", str(audits))

    def test_bad_keyed_family_config_fails_only_that_family(self):
        bad_natural = {
            "provider": "misspelled_natural",
            "commodity_code": "NATGAS_HH",
            "commodity_family": "natural_gas",
            "route": "natural-gas/stor/wkly",
            "frequency": "weekly",
            "facets": json.dumps({
                "duoarea": "R48",
                "process": "SWO",
                "series": "NW2_EPG0_SWO_R48_BCF",
            }),
            "metric_code": "eia_ng_storage_lower48",
            "metric_name": "Lower 48 working gas",
            "measurement_kind": "physical_level",
            "source_description": "Lower 48 storage",
            "expected_unit": "BCF",
            "freshness_days": "10",
        }
        refined = {
            "provider": "eia_refined_products",
            "commodity_code": "WTI",
            "commodity_family": "refined_products",
            "route": "petroleum/sum/sndw",
            "frequency": "weekly",
            "facets": json.dumps({"series": "WCESTUS1"}),
            "metric_code": "eia_crude_stocks_ex_spr",
            "metric_name": "Crude stocks excluding SPR",
            "measurement_kind": "physical_level",
            "source_description": "Crude stocks excluding SPR",
            "expected_unit": "MBBL",
            "freshness_days": "10",
        }

        class FamilySession:
            def get(self, url, **_kwargs):
                if "natural-gas" in url:
                    raise AssertionError("bad natural config must fail before transport")
                if "/facet/series/" in url:
                    return TextResponse(json.dumps({
                        "response": {
                            "facets": [{"id": "WCESTUS1", "name": "Crude"}]
                        }
                    }))
                return TextResponse(json.dumps({
                    "response": {"data": [
                        {
                            "period": "2026-08-21",
                            "series": "WCESTUS1",
                            "series-description": "Crude stocks excluding SPR",
                            "units": "MBBL",
                            "value": "425000",
                        },
                        {
                            "period": "2026-08-14",
                            "series": "WCESTUS1",
                            "series-description": "Crude stocks excluding SPR",
                            "units": "MBBL",
                            "value": "420000",
                        },
                    ]}
                }))

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            fields = list(refined)
            with (data_dir / "capital_weekly_eia_series.csv").open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows([bad_natural, refined])
            providers = build_default_providers(
                start=date(2026, 8, 17),
                end=date(2026, 8, 23),
                data_dir=data_dir,
                environ={"EIA_API_KEY": "dummy-key"},
                session=FamilySession(),
            )
            tables = run_weekly_context(
                {
                    "eia_natural_gas": providers["eia_natural_gas"],
                    "eia_refined_products": providers["eia_refined_products"],
                },
                as_of_date=date(2026, 8, 23),
            )

        audits = {row["provider"]: row for row in tables["source_log"]}
        self.assertEqual(audits["eia_natural_gas"]["status"], "FETCH_FAILED")
        self.assertIn("misspelled_natural", audits["eia_natural_gas"]["notes"])
        self.assertEqual(audits["eia_refined_products"]["status"], "OK")
        self.assertEqual(len(tables["commodity_fundamentals"]), 3)

    def test_disaggregated_provider_uses_official_dataset_and_emits_commodity_metadata(self):
        text = CFTC_COLUMNS + (
            "GOLD - COMMODITY EXCHANGE INC.,088691,2026-08-18,500000,"
            "100000,200000,120000,70000,250000,100000,30000,20000\n"
        )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            session = TextSession(text)
            provider = build_default_providers(
                start=date(2026, 8, 17),
                end=date(2026, 8, 23),
                data_dir=data_dir,
                environ={},
                session=session,
            )["cftc_disaggregated"]

            result = provider.fetch()

        self.assertEqual(session.calls[0][0], CFTC_DISAGGREGATED_URL)
        self.assertEqual(provider.spec.requiredness, "required")
        self.assertEqual(len(result.rows), 13)
        managed = next(
            row for row in result.rows if row["metric_code"] == "GOLD_COMEX_managed_money_net"
        )
        self.assertEqual(managed["value"], 150_000)
        self.assertEqual(managed["commodity_code"], "GOLD_COMEX")
        self.assertEqual(managed["commodity_family"], "gold")
        self.assertEqual(managed["metric_role"], "positioning")
        self.assertEqual(managed["measurement_kind"], "net_position")
        self.assertEqual(managed["participant_class"], "managed_money")
        self.assertEqual(managed["known_as_of"], "2026-08-21T15:30:00-04:00")
        self.assertEqual(managed["reference_period"], "2026-08-18")
        self.assertFalse(any("asset_manager" in row["metric_code"] for row in result.rows))
        change = next(
            row
            for row in result.rows
            if row["metric_code"] == "GOLD_COMEX_managed_money_net_change"
        )
        self.assertEqual(change["measurement_kind"], "weekly_change")

    def test_disaggregated_provider_rejects_contract_present_only_in_history(self):
        text = CFTC_COLUMNS + (
            "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE,067651,2026-08-11,"
            "490000,100000,200000,120000,70000,200000,100000,30000,20000\n"
            "GOLD - COMMODITY EXCHANGE INC.,088691,2026-08-18,500000,"
            "100000,200000,120000,70000,250000,100000,30000,20000\n"
        )
        cftc_config = (
            "contract_code,metric_code,report_family,market_name,commodity_code,"
            "commodity_family,percentile_window,percentile_min_observations\n"
            "088691,GOLD_COT,disaggregated,GOLD - COMMODITY EXCHANGE INC.,"
            "GOLD_COMEX,gold,156,52\n"
            "067651,WTI_COT,disaggregated,"
            "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE,"
            "WTI,refined_products,156,52\n"
        )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            (data_dir / "capital_weekly_cftc_contracts.csv").write_text(
                cftc_config, encoding="utf-8"
            )
            provider = build_default_providers(
                start=date(2026, 8, 17),
                end=date(2026, 8, 23),
                data_dir=data_dir,
                environ={},
                session=TextSession(text),
            )["cftc_disaggregated"]

            with self.assertRaisesRegex(
                ValueError,
                "^CFTC response missing configured contracts for requested window: 067651$",
            ):
                provider.fetch()

    def test_disaggregated_provider_excludes_pre_release_tuesday_row(self):
        text = CFTC_COLUMNS + (
            "GOLD - COMMODITY EXCHANGE INC.,088691,2026-08-18,500000,"
            "100000,200000,120000,70000,250000,100000,30000,20000\n"
        )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            provider = build_default_providers(
                start=date(2026, 8, 17),
                end=date(2026, 8, 20),
                data_dir=data_dir,
                environ={},
                session=TextSession(text),
            )["cftc_disaggregated"]

            with self.assertRaisesRegex(
                ValueError,
                "^CFTC response missing configured contracts for requested window: 088691$",
            ):
                provider.fetch()

    def test_metric_rows_emit_shared_contract(self):
        rows = metric_rows(
            as_of_date=date(2026, 7, 24),
            category="market_internals",
            market="HKEX",
            source="HKEX",
            source_url="https://www.hkex.com.hk/",
            frequency="daily",
            values={"turnover": 100.0, "advance_ratio": 0.55},
            units={"turnover": "HKD", "advance_ratio": "ratio"},
        )

        self.assertEqual(len(rows), 2)
        self.assertTrue(set(METRIC_FIELDS).issubset(rows[0]))
        self.assertEqual(rows[0]["category"], "market_internals")

    def test_not_configured_provider_keeps_status_visible(self):
        result = not_configured_result(
            category="company_events",
            source="SEC",
            source_url="https://data.sec.gov/",
            notes="watchlist is empty",
        )

        self.assertEqual(result.status, "NOT_CONFIGURED")
        self.assertEqual(result.rows, [])
        self.assertIn("watchlist", result.notes)

    def test_default_registry_includes_both_stable_and_dynamic_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)

            providers = build_default_providers(
                start=date(2026, 7, 20),
                end=date(2026, 7, 26),
                data_dir=data_dir,
                environ={},
            )

        self.assertTrue(
            {
                "bls_calendar",
                "federal_reserve_calendar",
                "census_calendar",
                "nasdaq_market_summary",
                "cftc_tff",
                "cftc_disaggregated",
                "finra_margin",
                "sec_company_events",
                "eia_natural_gas",
                "eia_refined_products",
                "fred_financial_conditions",
                "yahoo_volatility_signals",
                "hkex_microstructure",
                "sse_microstructure",
                "szse_microstructure",
            }.issubset(providers)
        )
        self.assertTrue(all(isinstance(provider, ContextProvider) for provider in providers.values()))
        self.assertEqual(providers["sec_company_events"].spec.requiredness, "optional")
        self.assertEqual(providers["eia_natural_gas"].spec.requiredness, "optional")
        self.assertEqual(
            providers["eia_refined_products"].spec.requiredness,
            "optional",
        )
        self.assertEqual(
            providers["fred_financial_conditions"].spec.requiredness, "optional"
        )
        self.assertEqual(
            providers["yahoo_volatility_signals"].spec.requiredness, "optional"
        )
        self.assertEqual(providers["bls_calendar"].spec.requiredness, "required")
        self.assertEqual(providers["nasdaq_market_summary"].spec.source_tier, "public")
        self.assertEqual(providers["nasdaq_market_summary"].spec.provider_version, "1.0.0")
        self.assertEqual(
            providers["nasdaq_market_summary"].spec.schema_version,
            "context-metric-v1",
        )

    def test_yahoo_volatility_provider_uses_bounded_deterministic_download(self):
        calls = []

        def fake_download(**kwargs):
            calls.append(kwargs)
            return pd.DataFrame(
                {
                    ("^VIX9D", "Close"): [14.0, 99.0],
                    ("^VIX", "Close"): [16.0, 99.0],
                    ("^VIX3M", "Close"): [20.0, 99.0],
                    ("^VIX6M", "Close"): [22.0, 99.0],
                    ("^SKEW", "Close"): [145.0, 199.0],
                },
                index=pd.to_datetime(["2026-08-07", "2026-08-10"]),
            )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            providers = build_default_providers(
                start=date(2026, 8, 3),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=fake_download,
            )
            provider = providers["yahoo_volatility_signals"]
            result = provider.fetch()

        self.assertEqual(provider.spec.category, "financial_conditions")
        self.assertEqual(provider.spec.requiredness, "optional")
        self.assertEqual(provider.spec.source_tier, "public")
        self.assertEqual(provider.spec.freshness_days, 7)
        self.assertEqual(result.status, "OK")
        self.assertEqual(len(result.rows), 8)
        self.assertEqual(
            [row["metric_code"] for row in result.rows],
            [
                "vix_9d_level",
                "vix_1m_level",
                "vix_3m_level",
                "vix_6m_level",
                "cboe_skew_level",
                "vix_1m_3m_spread",
                "vix_1m_3m_ratio",
                "vix_9d_1m_spread",
            ],
        )
        self.assertTrue(all(set(METRIC_FIELDS).issubset(row) for row in result.rows))
        self.assertTrue(all(row["qc_flag"] == "OK" for row in result.rows))
        self.assertEqual(
            calls,
            [
                {
                    "tickers": ["^VIX9D", "^VIX", "^VIX3M", "^VIX6M", "^SKEW"],
                    "start": "2025-02-05",
                    "end": "2026-08-10",
                    "interval": "1d",
                    "auto_adjust": False,
                    "actions": False,
                    "group_by": "ticker",
                    "threads": False,
                    "progress": False,
                }
            ],
        )
        self.assertIn("date,ticker,close", result.raw_text)
        self.assertNotIn("2026-08-10", result.raw_text)
        self.assertEqual(result.source, "Yahoo Finance (Cboe indices)")
        self.assertEqual(result.source_url, "https://finance.yahoo.com/")

    def test_yahoo_volatility_provider_keeps_fresh_independent_series(self):
        def partial_download(**_kwargs):
            return pd.DataFrame(
                {
                    ("^VIX9D", "Close"): [float("nan")],
                    ("^VIX", "Close"): [16.0],
                    ("^VIX3M", "Close"): [float("nan")],
                    ("^VIX6M", "Close"): [float("nan")],
                    ("^SKEW", "Close"): [145.0],
                },
                index=pd.to_datetime(["2026-08-07"]),
            )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            result = build_default_providers(
                start=date(2026, 8, 3),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=partial_download,
            )["yahoo_volatility_signals"].fetch()

        self.assertEqual(result.status, "OK")
        self.assertEqual(
            [row["metric_code"] for row in result.rows],
            ["vix_1m_level", "cboe_skew_level"],
        )
        self.assertIn("vix_9d", result.notes)
        self.assertIn("vix_3m", result.notes)
        self.assertIn("vix_6m", result.notes)

    def test_yahoo_volatility_provider_audits_omitted_pair_calculations(self):
        def disjoint_download(**_kwargs):
            return pd.DataFrame(
                {
                    ("^VIX9D", "Close"): [14.0, None, None, None, None],
                    ("^VIX", "Close"): [None, 16.0, None, None, None],
                    ("^VIX3M", "Close"): [None, None, 20.0, None, None],
                    ("^VIX6M", "Close"): [None, None, None, 22.0, None],
                    ("^SKEW", "Close"): [None, None, None, None, 145.0],
                },
                index=pd.to_datetime(
                    [
                        "2026-08-03", "2026-08-04", "2026-08-05",
                        "2026-08-06", "2026-08-07",
                    ]
                ),
            )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            result = build_default_providers(
                start=date(2026, 8, 3),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=disjoint_download,
            )["yahoo_volatility_signals"].fetch()

        self.assertEqual(result.status, "OK")
        self.assertEqual(len(result.rows), 5)
        self.assertIn("vix_1m_3m_spread", result.notes)
        self.assertIn("vix_1m_3m_ratio", result.notes)
        self.assertIn("vix_9d_1m_spread", result.notes)
        self.assertIn("no fresh common date", result.notes)

    def test_yahoo_failure_returns_auditable_optional_result(self):
        def unavailable(**_kwargs):
            raise RuntimeError("Yahoo unavailable")

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            provider = build_default_providers(
                start=date(2026, 8, 3),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=unavailable,
            )["yahoo_volatility_signals"]

            result = provider.fetch()

        self.assertEqual(result.status, "FETCH_FAILED")
        self.assertEqual(result.rows, [])
        self.assertEqual(result.source, "Yahoo Finance (Cboe indices)")
        self.assertEqual(result.source_url, "https://finance.yahoo.com/")
        self.assertIn("Yahoo unavailable", result.notes)

    def test_yahoo_stale_legs_preserve_fresh_rows_and_normalized_raw_history(self):
        def stale_download(**_kwargs):
            return pd.DataFrame(
                {
                    ("^VIX9D", "Close"): [14.0, float("nan")],
                    ("^VIX", "Close"): [16.0, 15.0],
                    ("^VIX3M", "Close"): [20.0, float("nan")],
                    ("^VIX6M", "Close"): [22.0, float("nan")],
                    ("^SKEW", "Close"): [144.0, 145.0],
                },
                index=pd.to_datetime(["2026-07-17", "2026-08-07"]),
            )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            provider = build_default_providers(
                start=date(2026, 8, 3),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=stale_download,
            )["yahoo_volatility_signals"]

            result = provider.fetch()

        self.assertEqual(result.status, "OK")
        self.assertEqual(
            [row["metric_code"] for row in result.rows],
            ["vix_1m_level", "cboe_skew_level"],
        )
        self.assertIn("2026-07-17,^VIX9D,14.0", result.raw_text)
        self.assertIn("2026-08-07,^SKEW,145.0", result.raw_text)
        self.assertIn("vix_9d", result.notes)
        self.assertIn("vix_3m", result.notes)
        self.assertIn("vix_6m", result.notes)

    def test_yahoo_failure_preserves_unrelated_context_rows_and_audit(self):
        def unavailable(**_kwargs):
            raise RuntimeError("Yahoo unavailable")

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            yahoo = build_default_providers(
                start=date(2026, 8, 3),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                yahoo_downloader=unavailable,
            )["yahoo_volatility_signals"]

            required = ContextProvider(
                spec=ProviderSpec(
                    name="required_fixture",
                    category="financial_conditions",
                    source_tier="public",
                    requiredness="required",
                    provider_version="fixture-v1",
                    schema_version="context-metric-v1",
                    frequency="daily",
                    freshness_days=None,
                ),
                fetch=lambda: ProviderResult(
                    category="financial_conditions",
                    rows=metric_rows(
                        as_of_date=date(2026, 8, 8),
                        category="financial_conditions",
                        market="US",
                        source="Fixture",
                        source_url="https://example.test/fixture",
                        frequency="daily",
                        values={"fixture_metric": 1.0},
                        units={"fixture_metric": "ratio"},
                    ),
                    raw_text="fixture",
                    source="Fixture",
                    source_url="https://example.test/fixture",
                ),
            )

            tables = run_weekly_context(
                {
                    "required_fixture": required,
                    "yahoo_volatility_signals": yahoo,
                },
                as_of_date=date(2026, 8, 9),
            )

        self.assertEqual(
            [row["metric_code"] for row in tables["financial_conditions"]],
            ["fixture_metric"],
        )
        self.assertEqual(
            {row["provider"]: row["status"] for row in tables["source_log"]},
            {
                "required_fixture": "OK",
                "yahoo_volatility_signals": "FETCH_FAILED",
            },
        )
        yahoo_audit = next(
            row
            for row in tables["source_log"]
            if row["provider"] == "yahoo_volatility_signals"
        )
        self.assertEqual(yahoo_audit["observations"], 0)
        self.assertEqual(yahoo_audit["requiredness"], "optional")
        self.assertEqual(yahoo_audit["source_url"], "https://finance.yahoo.com/")


if __name__ == "__main__":
    unittest.main()
