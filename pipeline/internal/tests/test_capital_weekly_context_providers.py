from datetime import date
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from unittest.mock import patch

import pandas as pd

from pipeline.internal.capital_weekly.context import providers as providers_module
from pipeline.internal.capital_weekly.context.providers import (
    COMEX_COPPER_STOCKS_URL,
    CFTC_DISAGGREGATED_URL,
    build_default_providers,
    metric_rows,
    not_configured_result,
)
from pipeline.internal.capital_weekly.context.common import METRIC_FIELDS
from pipeline.internal.capital_weekly.context.eia_commodities import EiaBatchSpec
from pipeline.internal.capital_weekly.context.provider_contracts import (
    ContextProvider,
    ProviderPhaseError,
    ProviderResult,
    ProviderSpec,
)
from pipeline.internal.capital_weekly.official_http import (
    OfficialHttpError,
    OfficialHttpResponse,
    OfficialHttpTrace,
)
from pipeline.internal.capital_weekly.macro_assets import (
    load_commodity_research_config,
)
from pipeline.internal.capital_weekly.weekly_context import run_weekly_context
from pipeline.internal.common import load_config_rows
from pipeline.internal.tests.test_capital_weekly_metal_inventories import (
    COPPER_BIFF8,
    USGS_GOLD_PDF,
)


EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
COMMODITY_RESEARCH_CONFIG = load_commodity_research_config()


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
    status_code = 200
    headers = {}

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
    status_code = 200
    headers = {}

    def __init__(self, payload, raw_bytes=None):
        self.payload = payload
        self.content = raw_bytes or json.dumps(
            payload, separators=(",", ":")
        ).encode("utf-8")
        self.text = self.content.decode("utf-8")

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
        if isinstance(response, tuple):
            return JsonResponse(*response)
        return JsonResponse(response)


class BinaryResponse:
    status_code = 200
    headers = {}

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


class CommodityProbeTests(unittest.TestCase):
    def test_eia_probe_failure_reports_live_phase_and_attempts(self):
        from pipeline.internal.scripts import probe_commodity_sources

        series = "NW2_EPG0_SWO_R48_BCF"
        valid_row = {
            "period": "2026-08-21",
            "series": series,
            "duoarea": "R48",
            "process": "SWO",
            "series-description": "Lower 48 storage",
            "units": "BCF",
            "value": "3125",
        }

        class Client:
            def __init__(self, kind, attempts=2, error_attempts=2):
                self.kind = kind
                self.attempts = attempts
                self.error_attempts = error_attempts

            def fetch_metadata(self, _spec, _expected):
                if self.kind == "metadata_transport":
                    raise OfficialHttpError(
                        "HTTP_RETRY_EXHAUSTED",
                        "retrieve",
                        True,
                        self.error_attempts,
                        "metadata transport exhausted",
                    )
                if self.kind == "metadata":
                    raise ValueError("metadata identity mismatch")

            def fetch_page(self, _spec, *, offset, length):
                self.request = (offset, length)
                if self.kind == "parse":
                    return {
                        "response": {
                            "total": 1,
                            "data": [{**valid_row, "units": "WRONG"}],
                        }
                    }
                if self.kind == "coverage":
                    return {"response": {"total": 0, "data": []}}
                return {"response": {"total": 1, "data": [valid_row]}}

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document = json.loads(
                (Path(__file__).resolve().parents[2] / "config.json").read_text(
                    encoding="utf-8"
                )
            )
            document["context"]["eia_series"] = [{
                "provider": "eia_natural_gas",
                "commodity_code": "NATGAS_HH",
                "commodity_family": "natural_gas",
                "route": "natural-gas/stor/wkly",
                "frequency": "weekly",
                "facets": {
                    "duoarea": "R48", "process": "SWO", "series": series,
                },
                "metric_code": "eia_ng_storage_lower48",
                "metric_name": "Lower 48 storage",
                "measurement_kind": "inventory",
                "source_description": "Lower 48 storage",
                "expected_unit": "BCF",
                "freshness_days": "10",
            }]
            config_path = root / "config.json"
            config_path.write_text(json.dumps(document), encoding="utf-8")

            for kind, expected_phase in (
                ("metadata_transport", "metadata"),
                ("metadata", "metadata"),
                ("parse", "parse"),
                ("coverage", "coverage"),
            ):
                with self.subTest(kind=kind):
                    output = io.StringIO()
                    with redirect_stdout(output):
                        exit_code = probe_commodity_sources.main(
                            [
                                "--config", str(config_path),
                                "--as-of", "2026-08-23",
                                "--provider", "eia",
                            ],
                            client=Client(kind),
                            environ={"EIA_API_KEY": "probe-secret"},
                        )
                    payload = json.loads(output.getvalue())
                    self.assertEqual(exit_code, 1)
                    self.assertEqual(payload["phase"], expected_phase)
                    self.assertEqual(payload["attempts"], 2)

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = probe_commodity_sources.main(
                    [
                        "--config", str(config_path),
                        "--as-of", "2026-08-23",
                        "--provider", "eia",
                    ],
                    client=Client("success", attempts=1.5),
                    environ={"EIA_API_KEY": "probe-secret"},
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["phase"], "config")
            self.assertEqual(payload["error_code"], "EIA_PROBE_ATTEMPTS_INVALID")

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = probe_commodity_sources.main(
                    [
                        "--config", str(config_path),
                        "--as-of", "2026-08-23",
                        "--provider", "eia",
                    ],
                    client=Client("metadata", attempts=0),
                    environ={"EIA_API_KEY": "probe-secret"},
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["phase"], "config")
            self.assertEqual(payload["attempts"], 1)
            self.assertEqual(payload["error_code"], "EIA_PROBE_ATTEMPTS_INVALID")

            for invalid_attempts in (0, -1, 1.5, True):
                with self.subTest(official_http_attempts=invalid_attempts):
                    output = io.StringIO()
                    with redirect_stdout(output):
                        exit_code = probe_commodity_sources.main(
                            [
                                "--config", str(config_path),
                                "--as-of", "2026-08-23",
                                "--provider", "eia",
                            ],
                            client=Client(
                                "metadata_transport",
                                error_attempts=invalid_attempts,
                            ),
                            environ={"EIA_API_KEY": "probe-secret"},
                        )
                    payload = json.loads(output.getvalue())
                    self.assertEqual(exit_code, 1)
                    self.assertEqual(payload["phase"], "config")
                    self.assertEqual(payload["attempts"], 1)
                    self.assertEqual(
                        payload["error_code"],
                        "EIA_PROBE_ATTEMPTS_INVALID",
                    )

    def test_eia_probe_is_sanitized_and_leaves_every_product_tree_byte_identical(self):
        from pipeline.internal.scripts import probe_commodity_sources

        class Client:
            attempts = 1

            def fetch_metadata(self, spec, expected):
                self.route = spec.route

            def fetch_page(self, spec, *, offset, length):
                self.page = (offset, length)
                return {
                    "response": {
                        "total": 1,
                        "data": [{
                            "period": "2026-08-21",
                            "series": "NW2_EPG0_SWO_R48_BCF",
                            "duoarea": "R48",
                            "process": "SWO",
                            "series-description": "Lower 48 storage",
                            "units": "BCF",
                            "value": "3125",
                        }],
                    }
                }

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                name: root / name
                for name in ("output", "cache", "staging", "status")
            }
            for name, path in paths.items():
                path.mkdir()
                (path / "sentinel.bin").write_bytes((name + "\x00\xff").encode("latin1"))
            before = {
                str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            document = json.loads(
                (Path(__file__).resolve().parents[2] / "config.json").read_text(
                    encoding="utf-8"
                )
            )
            document["context"]["eia_series"] = [{
                "provider": "eia_natural_gas",
                "commodity_code": "NATGAS_HH",
                "commodity_family": "natural_gas",
                "route": "natural-gas/stor/wkly",
                "frequency": "weekly",
                "facets": {
                    "duoarea": "R48",
                    "process": "SWO",
                    "series": "NW2_EPG0_SWO_R48_BCF",
                },
                "metric_code": "eia_ng_storage_lower48",
                "metric_name": "Lower 48 storage",
                "measurement_kind": "inventory",
                "source_description": "Lower 48 storage",
                "expected_unit": "BCF",
                "freshness_days": "10",
            }]
            document["runtime_paths"] = {name: str(path) for name, path in paths.items()}
            config_path = root / "probe-config.json"
            config_path.write_text(json.dumps(document), encoding="utf-8")
            output = io.StringIO()

            with redirect_stdout(output):
                exit_code = probe_commodity_sources.main(
                    [
                        "--config", str(config_path),
                        "--as-of", "2026-08-23",
                        "--provider", "eia",
                    ],
                    client=Client(),
                    environ={"EIA_API_KEY": "probe-secret"},
                )

            after = {
                str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            comparable_after = {
                key: value for key, value in after.items() if key != "probe-config.json"
            }

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["provider"], "eia")
        self.assertEqual(payload["phase"], "normalized")
        self.assertEqual(payload["attempts"], 1)
        self.assertEqual(payload["series_count"], 1)
        self.assertEqual(payload["latest_eligible_date"], "2026-08-21")
        self.assertEqual(payload["routes"], ["natural-gas/stor/wkly"])
        self.assertNotIn("probe-secret", output.getvalue())
        self.assertEqual(before, comparable_after)


def write_provider_configs(data_dir):
    (data_dir / "capital_weekly_company_watchlist.csv").write_text(
        "ticker,cik,company_name,enabled\n", encoding="utf-8"
    )
    (data_dir / "capital_weekly_cftc_contracts.csv").write_text(
        "contract_code,metric_code,report_family,market_name,commodity_code,"
        "commodity_family,percentile_window,percentile_min_observations,"
        "freshness_days\n"
        "13874A,sp500,tff,S&P 500 Consolidated,,,,,10\n"
        "088691,GOLD_COT,disaggregated,GOLD - COMMODITY EXCHANGE INC.,"
        "GOLD_COMEX,gold,156,52,10\n",
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
        "market_year_offsets,attributes,unit_names,freshness_days\n",
        encoding="utf-8",
    )
    (data_dir / "capital_weekly_usda_esr.csv").write_text(
        "commodity_code,commodity_family,commodity_name,route,"
        "market_year_offsets,unit_name,freshness_days\n",
        encoding="utf-8",
    )


def write_single_config_row(path: Path, row: dict) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def corn_psd_config() -> dict:
    return {
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
        "freshness_days": "45",
    }


def corn_esr_config() -> dict:
    return {
        "commodity_code": "CORN",
        "commodity_family": "grains_oilseeds",
        "commodity_name": "Corn",
        "route": "allCountries",
        "market_year_offsets": json.dumps([0]),
        "unit_name": "Metric Tons",
        "freshness_days": "14",
    }


class ContextProviderTests(unittest.TestCase):
    def test_cftc_and_usda_transport_boundaries_preserve_policy_secret_and_parse_trace(self):
        policies = providers_module.load_commodity_http_policies()

        archive_buffer = io.BytesIO()
        with zipfile.ZipFile(archive_buffer, "w") as archive:
            archive.writestr("fixture.txt", "header\n")

        cftc_cases = (
            (
                "cftc_tff",
                providers_module.parse_cftc_tff_csv,
                lambda http: providers_module._cftc_tff_provider(
                    object(), date(2026, 1, 1), date(2026, 1, 4),
                    {"13874A": "sp500"}, 10, http,
                ),
                archive_buffer.getvalue(),
            ),
            (
                "cftc_disaggregated",
                providers_module.parse_cftc_disaggregated_csv,
                lambda http: providers_module._cftc_disaggregated_provider(
                    object(), date(2026, 1, 1), date(2026, 1, 4),
                    [{
                        "contract_code": "088691",
                        "market_name": "GOLD - COMMODITY EXCHANGE INC.",
                        "commodity_code": "GOLD_COMEX",
                        "commodity_family": "gold",
                        "percentile_window": "156",
                        "percentile_min_observations": "52",
                    }],
                    10,
                    http,
                ),
                b"malformed,csv\n",
            ),
        )
        for provider, parser, invoke, body in cftc_cases:
            with self.subTest(provider=provider):
                calls = []

                def fake_get(_session, url, **kwargs):
                    calls.append((url, kwargs))
                    return OfficialHttpResponse(
                        body=body,
                        url=url,
                        headers={},
                        trace=OfficialHttpTrace(2, 1, [503, 200], url),
                    )

                with patch.object(providers_module, "official_get", side_effect=fake_get), patch.object(
                    providers_module,
                    parser.__name__,
                    side_effect=ValueError(f"{provider} parser rejected fixture"),
                ):
                    with self.assertRaises(ProviderPhaseError) as raised:
                        invoke(policies[provider])

                self.assertEqual(raised.exception.failure_phase, "parse")
                self.assertEqual(raised.exception.attempts, 2)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][1]["policy"], policies[provider].policy)
                self.assertEqual(calls[0][1]["audit_secrets"], ())

        for provider, invoke in (
            (
                "usda_psd",
                lambda http: providers_module._usda_psd_provider(
                    object(), date(2026, 8, 30), [corn_psd_config()],
                    "usda-secret", http,
                ),
            ),
            (
                "usda_esr",
                lambda http: providers_module._usda_esr_provider(
                    object(), date(2026, 8, 30), [corn_esr_config()],
                    "usda-secret", http,
                ),
            ),
        ):
            with self.subTest(provider=provider):
                calls = []

                def fake_get(_session, url, **kwargs):
                    calls.append((url, kwargs))
                    body = json.dumps([{"fixture": "identity"}]).encode()
                    return OfficialHttpResponse(
                        body=body,
                        url=url,
                        headers={},
                        trace=OfficialHttpTrace(2, 1, [503, 200], url),
                    )

                with patch.object(providers_module, "official_get", side_effect=fake_get), patch.object(
                    providers_module,
                    "parse_usda_lookup",
                    side_effect=ValueError(f"{provider} lookup rejected fixture"),
                ):
                    with self.assertRaises(ProviderPhaseError) as raised:
                        invoke(policies[provider])

                self.assertEqual(raised.exception.failure_phase, "parse")
                self.assertEqual(raised.exception.attempts, 2)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][1]["policy"], policies[provider].policy)
                self.assertEqual(calls[0][1]["audit_secrets"], ("usda-secret",))
                self.assertEqual(calls[0][1]["headers"]["API_KEY"], "usda-secret")

    def test_cme_and_usgs_binary_boundaries_preserve_each_provider_bytes_and_policy(self):
        policies = providers_module.load_commodity_http_policies()
        metal_specs = {
            row["provider"]: row for row in load_config_rows("context.metals")
        }

        for provider in ("comex_copper_stocks", "comex_gold_stocks"):
            with self.subTest(provider=provider):
                raw = (provider + "\x00\xff").encode("latin1")
                calls = []

                def fake_get(_session, url, **kwargs):
                    calls.append((url, kwargs))
                    return OfficialHttpResponse(
                        body=raw,
                        url=url,
                        headers={},
                        trace=OfficialHttpTrace(2, 1, [503, 200], url),
                    )

                unit = str(metal_specs[provider]["expected_unit"])
                parsed = [
                    {
                        "report_date": date(2026, 8, 28),
                        "scope": "exchange",
                        "inventory_type": kind,
                        "value": value,
                        "unit": unit,
                    }
                    for kind, value in (
                        ("registered", 1.0), ("eligible", 2.0), ("total", 3.0)
                    )
                ]
                with patch.object(providers_module, "official_get", side_effect=fake_get), patch.object(
                    providers_module, "parse_comex_stocks", return_value=parsed
                ), patch.object(
                    providers_module, "comex_schema_signature", return_value="fixture"
                ):
                    result = providers_module._comex_stocks_provider(
                        object(), date(2026, 8, 30), metal_specs[provider],
                        policies[provider],
                    )

                self.assertEqual(result.raw_text, raw)
                self.assertEqual(result.attempts, 2)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][1]["policy"], policies[provider].policy)
                self.assertEqual(calls[0][1]["audit_secrets"], ())

                calls.clear()
                with patch.object(providers_module, "official_get", side_effect=fake_get), patch.object(
                    providers_module,
                    "parse_comex_stocks",
                    side_effect=ValueError(f"{provider} parser rejected fixture"),
                ):
                    rejected = providers_module._comex_stocks_provider(
                        object(), date(2026, 8, 30), metal_specs[provider],
                        policies[provider],
                    )
                self.assertEqual(rejected.status, "FETCH_FAILED")
                self.assertEqual(rejected.attempts, 2)
                self.assertEqual(rejected.completed_phase, "parse")
                self.assertEqual(rejected.raw_text, raw)
                self.assertEqual(len(calls), 1)

        for provider in ("usgs_copper_structural", "usgs_gold_structural"):
            with self.subTest(provider=provider):
                raw = (provider + "\x00\xff").encode("latin1")
                calls = []

                def fake_get(_session, url, **kwargs):
                    calls.append((url, kwargs))
                    return OfficialHttpResponse(
                        body=raw,
                        url=url,
                        headers={},
                        trace=OfficialHttpTrace(2, 1, [503, 200], url),
                    )

                unit = str(metal_specs[provider]["expected_unit"])
                parsed = [
                    {
                        "measurement": measurement,
                        "value": value,
                        "unit": unit,
                        "reference_period": "2025",
                    }
                    for measurement, value in (
                        ("mine_production", 1.0), ("reserves", 2.0)
                    )
                ]
                with patch.object(providers_module, "official_get", side_effect=fake_get), patch.object(
                    providers_module, "parse_usgs_mcs_pdf", return_value=parsed
                ):
                    result = providers_module._usgs_structural_provider(
                        object(), date(2026, 8, 30), metal_specs[provider],
                        policies[provider],
                    )

                self.assertEqual(result.raw_text, raw)
                self.assertEqual(result.attempts, 2)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][1]["policy"], policies[provider].policy)
                self.assertEqual(calls[0][1]["audit_secrets"], ())

                calls.clear()
                with patch.object(providers_module, "official_get", side_effect=fake_get), patch.object(
                    providers_module,
                    "parse_usgs_mcs_pdf",
                    side_effect=ValueError(f"{provider} parser rejected fixture"),
                ):
                    rejected = providers_module._usgs_structural_provider(
                        object(), date(2026, 8, 30), metal_specs[provider],
                        policies[provider],
                    )
                self.assertEqual(rejected.status, "FETCH_FAILED")
                self.assertEqual(rejected.attempts, 2)
                self.assertEqual(rejected.completed_phase, "parse")
                self.assertEqual(rejected.raw_text, raw)
                self.assertEqual(len(calls), 1)

    def test_usda_invalid_json_preserves_retry_trace_as_parse_failure(self):
        policies = providers_module.load_commodity_http_policies()

        for provider, invoke in (
            (
                "usda_psd",
                lambda http: providers_module._usda_psd_provider(
                    object(), date(2026, 8, 30), [corn_psd_config()],
                    "usda-secret", http,
                ),
            ),
            (
                "usda_esr",
                lambda http: providers_module._usda_esr_provider(
                    object(), date(2026, 8, 30), [corn_esr_config()],
                    "usda-secret", http,
                ),
            ),
        ):
            with self.subTest(provider=provider):
                calls = []

                def fake_get(_session, url, **kwargs):
                    calls.append((url, kwargs))
                    return OfficialHttpResponse(
                        body=b"not-json\x00\xff",
                        url=url,
                        headers={},
                        trace=OfficialHttpTrace(2, 1, [503, 200], url),
                    )

                with patch.object(
                    providers_module, "official_get", side_effect=fake_get
                ):
                    with self.assertRaises(ProviderPhaseError) as raised:
                        invoke(policies[provider])

                self.assertEqual(raised.exception.failure_phase, "parse")
                self.assertEqual(raised.exception.attempts, 2)
                self.assertEqual(len(calls), 1)

    def test_context_eia_metadata_requires_explicit_total(self):
        spec = EiaBatchSpec(
            route="natural-gas/stor/wkly",
            facets={"series": ("SERIES",)},
            frequency="weekly",
            start="2026-08-01",
            end="2026-08-23",
            page_length=1,
        )
        policy = providers_module.load_commodity_http_policies()["eia"].policy
        client = providers_module._OfficialEiaClient(object(), "fixture-key", policy)
        body = json.dumps(
            {"response": {"facets": [{"id": "SERIES"}]}}
        ).encode()
        response = OfficialHttpResponse(
            body=body,
            url="https://api.eia.gov/v2/facet/series/",
            headers={},
            trace=OfficialHttpTrace(1, 1, [200], "fixture"),
        )

        with patch.object(providers_module, "official_get", return_value=response):
            with self.assertRaisesRegex(ValueError, "total"):
                client.fetch_metadata(
                    spec,
                    {"SERIES": {"facets": {"series": "SERIES"}}},
                )

    def test_eia_retry_trace_survives_post_transport_parse_and_coverage_failures(self):
        series = "NW2_EPG0_SWO_R48_BCF"
        configured = [{
            "provider": "eia_natural_gas",
            "commodity_code": "NATGAS_HH",
            "commodity_family": "natural_gas",
            "route": "natural-gas/stor/wkly",
            "frequency": "weekly",
            "facets": {"duoarea": "R48", "process": "SWO", "series": series},
            "metric_code": "eia_ng_storage_lower48",
            "metric_name": "Lower 48 storage",
            "measurement_kind": "inventory",
            "source_description": "Lower 48 storage",
            "expected_unit": "BCF",
            "freshness_days": "10",
        }]
        policy = providers_module.load_commodity_http_policies()["eia"]

        def response(body, url):
            return OfficialHttpResponse(
                body=json.dumps(body).encode(),
                url=url,
                headers={},
                trace=OfficialHttpTrace(2, 1, [503, 200], url),
            )

        for label, row, phase in (
            (
                "parse",
                {
                    "period": "2026-08-21", "series": series,
                    "duoarea": "R48", "process": "SWO",
                    "series-description": "Lower 48 storage",
                    "units": "WRONG", "value": "3125",
                },
                "parse",
            ),
            (
                "coverage",
                None,
                "coverage",
            ),
        ):
            with self.subTest(label=label):
                def fake_get(_session, url, **_kwargs):
                    if "/facet/" in url:
                        facet = url.rstrip("/").split("/")[-1]
                        identifiers = {
                            "duoarea": "R48", "process": "SWO", "series": series,
                        }
                        return response(
                            {"response": {"totalFacets": 1, "facets": [
                                {"id": identifiers[facet]}
                            ]}},
                            url,
                        )
                    rows = [] if row is None else [row]
                    return response(
                        {"response": {"total": len(rows), "data": rows}},
                        url,
                    )

                with patch.object(providers_module, "official_get", side_effect=fake_get):
                    with self.assertRaises(ProviderPhaseError) as raised:
                        providers_module._eia_provider(
                            object(), date(2026, 8, 23), configured, "fixture-key",
                            "eia_natural_gas", policy,
                        )

                self.assertEqual(raised.exception.failure_phase, phase)
                self.assertEqual(raised.exception.attempts, 2)

    def test_eia_official_transport_uses_config_policy_secret_audit_and_propagates_retry_attempts(self):
        series = "NW2_EPG0_SWO_R48_BCF"
        configured = [{
            "provider": "eia_natural_gas",
            "commodity_code": "NATGAS_HH",
            "commodity_family": "natural_gas",
            "route": "natural-gas/stor/wkly",
            "frequency": "weekly",
            "facets": {"duoarea": "R48", "process": "SWO", "series": series},
            "metric_code": "eia_ng_storage_lower48",
            "metric_name": "Lower 48 storage",
            "measurement_kind": "inventory",
            "source_description": "Lower 48 storage",
            "expected_unit": "BCF",
            "freshness_days": "10",
        }]
        policy = providers_module.load_commodity_http_policies()["eia"]
        secret = "retry-audit-secret"
        calls = []

        def fake_get(session, url, **kwargs):
            del session
            calls.append((url, kwargs))
            if "/facet/" in url:
                selected = url.rstrip("/").split("/")[-1]
                ids = {"duoarea": "R48", "process": "SWO", "series": series}
                body = json.dumps(
                    {"response": {
                        "totalFacets": 1,
                        "facets": [{"id": ids[selected]}],
                    }}
                ).encode()
                attempts = 1
            else:
                body = json.dumps({"response": {"total": 2, "data": [
                    {
                        "period": "2026-08-21", "series": series,
                        "duoarea": "R48", "process": "SWO",
                        "series-description": "Lower 48 storage",
                        "units": "BCF", "value": "3125",
                    },
                    {
                        "period": "2026-08-14", "series": series,
                        "duoarea": "R48", "process": "SWO",
                        "series-description": "Lower 48 storage",
                        "units": "BCF", "value": "3100",
                    },
                ]}}).encode()
                attempts = 2
            return OfficialHttpResponse(
                body=body,
                url=url,
                headers={},
                trace=OfficialHttpTrace(attempts, 1, [200], url),
            )

        with patch.object(providers_module, "official_get", side_effect=fake_get):
            result = providers_module._eia_provider(
                object(), date(2026, 8, 23), configured, secret,
                "eia_natural_gas", policy,
            )

        self.assertEqual(result.attempts, 2)
        self.assertEqual(len(result.rows), 3)
        self.assertTrue(all(kwargs["policy"] == policy.policy for _, kwargs in calls))
        self.assertTrue(all(kwargs["audit_secrets"] == (secret,) for _, kwargs in calls))
        data_kwargs = next(kwargs for url, kwargs in calls if url.endswith("/data/"))
        self.assertEqual(data_kwargs["params"]["offset"], 0)
        self.assertEqual(data_kwargs["params"]["length"], 400)

    def test_metal_specs_require_explicit_freshness_basis_and_holiday_calendar(self):
        configured = {
            row["provider"]: row for row in load_config_rows("context.metals")
        }

        for provider_name, spec in configured.items():
            for field in ("freshness_basis", "holiday_calendar"):
                with self.subTest(provider=provider_name, field=field):
                    mutated = dict(spec)
                    mutated.pop(field, None)
                    with self.assertRaisesRegex(ValueError, field):
                        providers_module._metal_spec(mutated)

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

    def test_keyed_psd_provider_selects_latest_release_at_or_before_cutoff(self):
        fixture_root = Path(__file__).with_name("fixtures") / "usda"
        lookups = json.loads(
            (fixture_root / "psd_lookups.json").read_text(encoding="utf-8")
        )
        psd_records = json.loads(
            (fixture_root / "psd_records.json").read_text(encoding="utf-8")
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
                },
                {
                    "commodityCode": "0440000",
                    "marketYear": 2026,
                    "releaseDate": "2026-09-12T12:00:00-04:00",
                },
            ],
            f"{base}/api/psd/commodity/0440000/world/year/2026": psd_records,
        }

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            write_single_config_row(
                data_dir / "capital_weekly_usda_psd.csv",
                corn_psd_config(),
            )
            provider = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={"USDA_API_KEY": "fixture-key"},
                session=JsonSession(responses),
            )["usda_psd"]
            tables = run_weekly_context(
                {"usda_psd": provider},
                raw_dir=data_dir / "raw",
                as_of_date=date(2026, 8, 30),
                history_limits=COMMODITY_RESEARCH_CONFIG.history_limits,
                commodity_registry=COMMODITY_RESEARCH_CONFIG.commodity_registry,
            )

        self.assertEqual(tables["source_log"][0]["status"], "OK")
        self.assertEqual(
            {row["known_as_of"] for row in tables["commodity_fundamentals"]},
            {"2026-08-12T12:00:00-04:00"},
        )

    def test_keyed_psd_fails_closed_without_explicit_matching_record_vintage(self):
        fixture_root = Path(__file__).with_name("fixtures") / "usda"
        lookups = json.loads(
            (fixture_root / "psd_lookups.json").read_text(encoding="utf-8")
        )
        records = json.loads(
            (fixture_root / "psd_records.json").read_text(encoding="utf-8")
        )
        unversioned = [
            {key: value for key, value in record.items() if key != "releaseDate"}
            for record in records
        ]
        original_bytes = json.dumps(unversioned, indent=2).encode("utf-8")
        base = "https://api.fas.usda.gov"
        data_url = f"{base}/api/psd/commodity/0440000/world/year/2026"
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
            data_url: (unversioned, original_bytes),
        }

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            write_single_config_row(
                data_dir / "capital_weekly_usda_psd.csv",
                corn_psd_config(),
            )
            provider = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={"USDA_API_KEY": "fixture-key"},
                session=JsonSession(responses),
            )["usda_psd"]

            result = provider.fetch()

        self.assertEqual(result.status, "POINT_IN_TIME_UNAVAILABLE")
        self.assertEqual(result.rows, [])
        self.assertIn("explicit record vintage", result.notes)
        with zipfile.ZipFile(io.BytesIO(result.raw_text)) as archive:
            self.assertIn(original_bytes, [archive.read(name) for name in archive.namelist()])

    def test_keyed_psd_stale_release_uses_configured_45_day_cutoff(self):
        fixture_root = Path(__file__).with_name("fixtures") / "usda"
        lookups = json.loads(
            (fixture_root / "psd_lookups.json").read_text(encoding="utf-8")
        )
        base = "https://api.fas.usda.gov"
        data_url = f"{base}/api/psd/commodity/0440000/world/year/2026"
        responses = {
            f"{base}/api/psd/commodities": lookups["commodities"],
            f"{base}/api/psd/commodityAttributes": lookups["attributes"],
            f"{base}/api/psd/countries": lookups["countries"],
            f"{base}/api/psd/unitsOfMeasure": lookups["units"],
            f"{base}/api/psd/commodity/0440000/dataReleaseDates": [
                {
                    "commodityCode": "0440000",
                    "marketYear": 2026,
                    "releaseDate": "2026-07-14T12:00:00-04:00",
                }
            ],
        }
        session = JsonSession(responses)
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            write_single_config_row(
                data_dir / "capital_weekly_usda_psd.csv",
                corn_psd_config(),
            )
            provider = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={"USDA_API_KEY": "fixture-key"},
                session=session,
            )["usda_psd"]
            def retrying_get(active_session, url, **kwargs):
                response = active_session.get(url, **kwargs)
                return OfficialHttpResponse(
                    body=response.content,
                    url=url,
                    headers={},
                    trace=OfficialHttpTrace(2, 1, [503, 200], url),
                )

            with patch.object(providers_module, "official_get", side_effect=retrying_get):
                result = provider.fetch()

        self.assertEqual(result.status, "POINT_IN_TIME_UNAVAILABLE")
        self.assertEqual(result.attempts, 2)
        self.assertEqual(result.rows, [])
        self.assertIn("45 calendar days", result.notes)
        self.assertNotIn(data_url, [url for url, _kwargs in session.calls])

    def test_keyed_esr_fails_closed_when_records_do_not_match_latest_release(self):
        fixture_root = Path(__file__).with_name("fixtures") / "usda"
        records = json.loads(
            (fixture_root / "esr_records.json").read_text(encoding="utf-8")
        )
        mismatched = [
            {**record, "releaseDate": "2026-08-20T08:30:00-04:00"}
            for record in records[:2]
        ]
        original_bytes = json.dumps(mismatched, indent=2).encode("utf-8")
        base = "https://api.fas.usda.gov"
        data_url = (
            f"{base}/api/esr/exports/commodityCode/101/"
            "allCountries/marketYear/2026"
        )
        responses = {
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
            data_url: (mismatched, original_bytes),
        }

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            write_single_config_row(
                data_dir / "capital_weekly_usda_esr.csv",
                corn_esr_config(),
            )
            provider = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={"USDA_API_KEY": "fixture-key"},
                session=JsonSession(responses),
            )["usda_esr"]

            result = provider.fetch()

        self.assertEqual(result.status, "POINT_IN_TIME_UNAVAILABLE")
        self.assertEqual(result.rows, [])
        self.assertIn("does not match latest eligible release", result.notes)
        with zipfile.ZipFile(io.BytesIO(result.raw_text)) as archive:
            self.assertIn(original_bytes, [archive.read(name) for name in archive.namelist()])

    def test_keyed_esr_ignores_future_unknown_country_and_unit_after_cutoff(self):
        fixture_root = Path(__file__).with_name("fixtures") / "usda"
        records = json.loads(
            (fixture_root / "esr_records.json").read_text(encoding="utf-8")
        )
        future_invalid = {
            **records[-1],
            "countryCode": 9999,
            "unitId": 999,
        }
        base = "https://api.fas.usda.gov"
        responses = {
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
            f"{base}/api/esr/exports/commodityCode/101/allCountries/marketYear/2026": [
                *records,
                future_invalid,
            ],
        }

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            write_single_config_row(
                data_dir / "capital_weekly_usda_esr.csv",
                corn_esr_config(),
            )
            provider = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={"USDA_API_KEY": "fixture-key"},
                session=JsonSession(responses),
            )["usda_esr"]
            tables = run_weekly_context(
                {"usda_esr": provider},
                raw_dir=data_dir / "raw",
                as_of_date=date(2026, 8, 30),
                history_limits=COMMODITY_RESEARCH_CONFIG.history_limits,
                commodity_registry=COMMODITY_RESEARCH_CONFIG.commodity_registry,
            )

        self.assertEqual(tables["source_log"][0]["status"], "OK")
        self.assertEqual(
            [(row["measurement_kind"], row["value"]) for row in tables["commodity_fundamentals"]],
            [
                ("trade", 210_000),
                ("trade", 340_000),
                ("trade", 4_600_000),
            ],
        )

    def test_keyed_esr_rejects_selected_unknown_country(self):
        fixture_root = Path(__file__).with_name("fixtures") / "usda"
        records = json.loads(
            (fixture_root / "esr_records.json").read_text(encoding="utf-8")
        )
        selected_unknown = {**records[0], "countryCode": 9999}
        base = "https://api.fas.usda.gov"
        responses = {
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
            f"{base}/api/esr/exports/commodityCode/101/allCountries/marketYear/2026": [
                records[1],
                selected_unknown,
            ],
        }

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            write_single_config_row(
                data_dir / "capital_weekly_usda_esr.csv",
                corn_esr_config(),
            )
            provider = build_default_providers(
                start=date(2026, 8, 24),
                end=date(2026, 8, 30),
                data_dir=data_dir,
                environ={"USDA_API_KEY": "fixture-key"},
                session=JsonSession(responses),
            )["usda_esr"]
            tables = run_weekly_context(
                {"usda_esr": provider},
                raw_dir=data_dir / "raw",
                as_of_date=date(2026, 8, 30),
            )

        self.assertEqual(tables["source_log"][0]["status"], "FETCH_FAILED")
        self.assertEqual(tables["commodity_fundamentals"], [])

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
                "freshness_days": "45",
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
                "freshness_days": "14",
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
                history_limits=COMMODITY_RESEARCH_CONFIG.history_limits,
                commodity_registry=COMMODITY_RESEARCH_CONFIG.commodity_registry,
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

    def test_cme_five_trading_day_cutoff_counts_holiday_and_weekend_boundaries(self):
        spec = {
            "provider": "comex_copper_stocks",
            "source_url": COMEX_COPPER_STOCKS_URL,
            "source": "CME Group",
            "commodity_code": "COPPER_COMEX",
            "commodity_family": "copper",
            "market": "COMEX",
            "frequency": "daily",
            "freshness_days": "5",
            "freshness_basis": "trading_days",
            "holiday_calendar": "CME_US",
            "expected_sheet": "Daily Metal Stocks Report",
            "commodity_title": "COPPER - HIGH GRADE",
            "expected_unit": "Short Tons",
            "location_header": "DELIVERY POINT",
            "registered_total_label": "Total Registered (warranted)",
            "eligible_total_label": "Total Eligible (non-warranted)",
            "combined_total_label": "TOTAL COPPER",
            "limitation_note": "deliverable_inventory_proxy; LME not included",
        }
        parsed = [
            {
                "report_date": date(2026, 6, 25),
                "scope": "exchange",
                "inventory_type": inventory_type,
                "value": value,
                "unit": "Short Tons",
            }
            for inventory_type, value in (
                ("registered", 15.0),
                ("eligible", 35.0),
                ("total", 50.0),
            )
        ]
        with patch.object(providers_module, "_official_bytes", return_value=(b"fixture", 2)), patch.object(
            providers_module, "parse_comex_stocks", return_value=parsed
        ), patch.object(
            providers_module,
            "comex_schema_signature",
            return_value="fixture",
        ):
            boundary = providers_module._comex_stocks_provider(
                BinarySession({COMEX_COPPER_STOCKS_URL: b"fixture"}),
                date(2026, 7, 5),
                spec,
                providers_module.load_commodity_http_policies()[
                    "comex_copper_stocks"
                ],
            )
            stale = providers_module._comex_stocks_provider(
                BinarySession({COMEX_COPPER_STOCKS_URL: b"fixture"}),
                date(2026, 7, 6),
                spec,
                providers_module.load_commodity_http_policies()[
                    "comex_copper_stocks"
                ],
            )

        self.assertEqual(boundary.status, "OK")
        self.assertEqual(len(boundary.rows), 3)
        self.assertEqual(stale.status, "POINT_IN_TIME_UNAVAILABLE")
        self.assertEqual(stale.attempts, 2)
        self.assertEqual(stale.rows, [])
        self.assertIn("5 trading days", stale.notes)

    def test_comex_copper_keeps_exact_bytes_and_auditable_provenance(self):
        metal_header = (
            "provider,source_url,source,commodity_code,commodity_family,market,"
            "frequency,freshness_days,freshness_basis,holiday_calendar,"
            "expected_sheet,commodity_title,expected_unit,"
            "location_header,registered_total_label,eligible_total_label,"
            "combined_total_label,table_kind,reference_year,publication_date,"
            "publication_month,limitation_note\n"
        )
        metal_row = (
            "comex_copper_stocks,https://www.cmegroup.com/delivery_reports/"
            "Copper_Stocks.xls,CME Group,COPPER_COMEX,copper,COMEX,daily,7,"
            "trading_days,CME_US,"
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
                history_limits=COMMODITY_RESEARCH_CONFIG.history_limits,
                commodity_registry=COMMODITY_RESEARCH_CONFIG.commodity_registry,
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
            "frequency,freshness_days,freshness_basis,holiday_calendar,"
            "expected_sheet,commodity_title,expected_unit,"
            "location_header,registered_total_label,eligible_total_label,"
            "combined_total_label,table_kind,reference_year,publication_date,"
            "publication_month,limitation_note\n"
        )
        metal_row = (
            "usgs_gold_structural,https://pubs.usgs.gov/periodicals/mcs2026/"
            "mcs2026-gold.pdf,U.S. Geological Survey,GOLD_COMEX,gold,World,annual,"
            "400,calendar_days,NONE,,GOLD,\"metric tons, gold content\",,,,,"
            "mine_reserves,2025,"
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
            "frequency,freshness_days,freshness_basis,holiday_calendar,"
            "expected_sheet,commodity_title,expected_unit,"
            "location_header,registered_total_label,eligible_total_label,"
            "combined_total_label,table_kind,reference_year,publication_date,"
            "publication_month,limitation_note\n"
        )
        metal_row = (
            f"usgs_gold_structural,{url},U.S. Geological Survey,GOLD_COMEX,gold,"
            "World,annual,400,calendar_days,NONE,,GOLD,"
            "\"metric tons, gold content\",,,,,mine_reserves,"
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
            "frequency,freshness_days,freshness_basis,holiday_calendar,"
            "expected_sheet,commodity_title,expected_unit,"
            "location_header,registered_total_label,eligible_total_label,"
            "combined_total_label,table_kind,reference_year,publication_date,"
            "publication_month,limitation_note\n"
        )
        copper_row = (
            f"comex_copper_stocks,{copper_url},CME Group,COPPER_COMEX,copper,"
            "COMEX,daily,7,trading_days,CME_US,Daily Metal Stocks Report,"
            "COPPER - HIGH GRADE,"
            "Short Tons,DELIVERY POINT,Total Registered (warranted),"
            "Total Eligible (non-warranted),TOTAL COPPER,,,,,"
            "deliverable_inventory_proxy; LME not included\n"
        )
        gold_row = (
            f"usgs_gold_structural,{gold_url},U.S. Geological Survey,GOLD_COMEX,"
            "gold,World,annual,400,calendar_days,NONE,,GOLD,"
            "\"metric tons, gold content\",,,,,"
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
                history_limits=COMMODITY_RESEARCH_CONFIG.history_limits,
                commodity_registry=COMMODITY_RESEARCH_CONFIG.commodity_registry,
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
            "frequency,freshness_days,freshness_basis,holiday_calendar,"
            "expected_sheet,commodity_title,expected_unit,"
            "location_header,registered_total_label,eligible_total_label,"
            "combined_total_label,table_kind,reference_year,publication_date,"
            "publication_month,limitation_note\n"
        )
        rows = (
            f"comex_copper_stocks,{bad_url},CME Group,COPPER_COMEX,copper,COMEX,"
            "daily,7,trading_days,CME_US,Daily Metal Stocks Report,"
            "COPPER - HIGH GRADE,Short Tons,"
            "DELIVERY POINT,Total Registered (warranted),"
            "Total Eligible (non-warranted),TOTAL COPPER,,,,,limitation\n"
            f"usgs_gold_structural,{gold_url},U.S. Geological Survey,GOLD_COMEX,"
            "gold,World,annual,400,calendar_days,NONE,,GOLD,"
            "\"metric tons, gold content\",,,,,"
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
                history_limits=COMMODITY_RESEARCH_CONFIG.history_limits,
                commodity_registry=COMMODITY_RESEARCH_CONFIG.commodity_registry,
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
            "frequency,freshness_days,freshness_basis,holiday_calendar,"
            "expected_sheet,commodity_title,expected_unit,"
            "location_header,registered_total_label,eligible_total_label,"
            "combined_total_label,table_kind,reference_year,publication_date,"
            "publication_month,limitation_note\n"
        )
        rows = (
            f"comex_copper_stocks,{copper_url},CME Group,COPPER_COMEX,copper,"
            "COMEX,daily,7,trading_days,CME_US,Daily Metal Stocks Report,"
            "COPPER - HIGH GRADE,"
            "Short Tons,DELIVERY POINT,Total Registered (warranted),"
            "Total Eligible (non-warranted),TOTAL COPPER,,,,,"
            "deliverable_inventory_proxy; LME not included\n"
            f"usgs_gold_structural,{gold_url},U.S. Geological Survey,GOLD_COMEX,"
            "gold,World,annual,400,calendar_days,NONE,,GOLD,"
            "\"metric tons, gold content\",,,,,"
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
            "measurement_kind": "inventory",
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
            "measurement_kind": "inventory",
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
                        "response": {
                            "totalFacets": 1,
                            "facets": [{"id": "A&B", "name": "Crude"}],
                        }
                    }))
                return TextResponse(json.dumps({
                    "response": {"total": 2, "data": [
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
                history_limits=COMMODITY_RESEARCH_CONFIG.history_limits,
                commodity_registry=COMMODITY_RESEARCH_CONFIG.commodity_registry,
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
            ["A&B"],
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
            "measurement_kind": "inventory",
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
            "measurement_kind": "inventory",
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
                            "totalFacets": 1,
                            "facets": [{"id": "WCESTUS1", "name": "Crude"}]
                        }
                    }))
                return TextResponse(json.dumps({
                    "response": {"total": 2, "data": [
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
                history_limits=COMMODITY_RESEARCH_CONFIG.history_limits,
                commodity_registry=COMMODITY_RESEARCH_CONFIG.commodity_registry,
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
        self.assertEqual(change["measurement_kind"], "net_position")

    def test_disaggregated_provider_rejects_release_older_than_configured_10_days(self):
        text = CFTC_COLUMNS + (
            "GOLD - COMMODITY EXCHANGE INC.,088691,2026-07-21,500000,"
            "100000,200000,120000,70000,250000,100000,30000,20000\n"
        )

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            write_provider_configs(data_dir)
            provider = build_default_providers(
                start=date(2026, 7, 20),
                end=date(2026, 8, 9),
                data_dir=data_dir,
                environ={},
                session=TextSession(text),
            )["cftc_disaggregated"]

            with patch.object(
                providers_module,
                "_official_text",
                return_value=(text, 2),
            ):
                with self.assertRaises(ProviderPhaseError) as raised:
                    provider.fetch()

        self.assertEqual(raised.exception.failure_phase, "freshness")
        self.assertEqual(raised.exception.attempts, 2)
        self.assertRegex(raised.exception.safe_message, "stale.*10.*088691")

    def test_disaggregated_provider_accepts_contract_within_freshness_window(self):
        text = CFTC_COLUMNS + (
            "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE,067651,2026-08-11,"
            "490000,100000,200000,120000,70000,200000,100000,30000,20000\n"
            "GOLD - COMMODITY EXCHANGE INC.,088691,2026-08-18,500000,"
            "100000,200000,120000,70000,250000,100000,30000,20000\n"
        )
        cftc_config = (
            "contract_code,metric_code,report_family,market_name,commodity_code,"
            "commodity_family,percentile_window,percentile_min_observations,"
            "freshness_days\n"
            "088691,GOLD_COT,disaggregated,GOLD - COMMODITY EXCHANGE INC.,"
            "GOLD_COMEX,gold,156,52,10\n"
            "067651,WTI_COT,disaggregated,"
            "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE,"
            "WTI,refined_products,156,52,10\n"
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

            result = provider.fetch()

        self.assertEqual(
            {row["commodity_code"] for row in result.rows},
            {"WTI", "GOLD_COMEX"},
        )

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

            with self.assertRaises(ProviderPhaseError) as raised:
                provider.fetch()

        self.assertEqual(raised.exception.failure_phase, "coverage")
        self.assertEqual(raised.exception.attempts, 1)
        self.assertEqual(
            raised.exception.safe_message,
            "CFTC response missing configured contracts for requested window: 088691",
        )

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
