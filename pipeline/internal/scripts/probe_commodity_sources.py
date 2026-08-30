"""Read-only diagnostics for configured official commodity sources."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

import requests

from pipeline.internal.capital_weekly.context.commodities import EIA_SOURCE_URL
from pipeline.internal.capital_weekly.context.eia_commodities import (
    EiaBatchSpec,
    build_eia_batch_specs,
    fetch_eia_batches,
    load_commodity_http_policies,
    period_date,
)
from pipeline.internal.capital_weekly.official_http import (
    OfficialHttpError,
    OfficialHttpPolicy,
    official_get,
)
from pipeline.internal.common import sanitize_audit_text


class _ProbeEiaClient:
    def __init__(self, session: requests.Session, policy: OfficialHttpPolicy, api_key: str):
        self.session = session
        self.policy = policy
        self.api_key = api_key
        self.attempts = 1

    def _get(self, url: str, params: Mapping[str, Any]) -> bytes:
        response = official_get(
            self.session,
            url,
            policy=self.policy,
            params=params,
            audit_secrets=(self.api_key,),
        )
        self.attempts = max(self.attempts, response.trace.attempts)
        return response.body

    def fetch_metadata(
        self,
        spec: EiaBatchSpec,
        expected: Mapping[str, Mapping[str, Any]],
    ) -> None:
        wanted: dict[str, set[str]] = {}
        for item in expected.values():
            for facet, selected in dict(item["facets"]).items():
                wanted.setdefault(str(facet), set()).add(str(selected))
        for facet, required in sorted(wanted.items()):
            identifiers: set[str] = set()
            offset = 0
            while not required <= identifiers:
                body = self._get(
                    f"{EIA_SOURCE_URL}{spec.route}/facet/{facet}/",
                    {
                        "api_key": self.api_key,
                        "offset": offset,
                        "length": spec.page_length,
                    },
                )
                payload = json.loads(body.decode("utf-8"))
                values = payload.get("response", {}).get("facets")
                if not isinstance(values, list):
                    raise ValueError(
                        f"EIA facet metadata is missing for {spec.route}/{facet}"
                    )
                identifiers.update(
                    str(item.get("id") or "").strip()
                    for item in values
                    if isinstance(item, Mapping)
                )
                total = int(payload.get("response", {}).get("total", len(values)))
                offset += len(values)
                if offset >= total:
                    break
                if not values:
                    raise ValueError("EIA facet metadata pagination made no progress")
            missing = sorted(required - identifiers)
            if missing:
                raise ValueError(
                    f"EIA configured facet is unavailable for {spec.route}/{facet}: "
                    + ", ".join(missing)
                )

    def fetch_page(self, spec: EiaBatchSpec, *, offset: int, length: int) -> dict:
        params: dict[str, Any] = {
            "api_key": self.api_key,
            "frequency": spec.frequency,
            "data[0]": "value",
            "start": spec.start,
            "end": spec.end,
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "offset": offset,
            "length": length,
        }
        for facet, values in spec.facets.items():
            params[f"facets[{facet}][]"] = list(values)
        body = self._get(f"{EIA_SOURCE_URL}{spec.route}/data/", params)
        payload = json.loads(body.decode("utf-8"))
        data = payload.get("response", {}).get("data", [])
        if isinstance(data, list):
            payload["response"]["total"] = len(data)
        return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--provider", choices=("eia",), required=True)
    return parser


def _config_rows(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document.get("context", {}).get("eia_series")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("config context.eia_series must be a row list")
    return [dict(row) for row in rows]


def main(
    argv: Sequence[str] | None = None,
    *,
    client: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    args = _parser().parse_args(argv)
    settings = dict(os.environ if environ is None else environ)
    api_key = str(settings.get("EIA_API_KEY") or "").strip()
    attempts = 1
    try:
        if not api_key:
            raise ValueError("EIA_API_KEY is required for the EIA probe")
        config_path = Path(args.config)
        as_of = date.fromisoformat(args.as_of)
        rows = _config_rows(config_path)
        http = load_commodity_http_policies(config_path)["eia"]
        assert http.request_batch_size is not None
        assert http.page_length is not None
        specs = build_eia_batch_specs(
            rows,
            request_batch_size=http.request_batch_size,
            page_length=http.page_length,
            start=(as_of - timedelta(days=400)).isoformat(),
            end=as_of.isoformat(),
        )
        expected = {
            str(row["facets"]["series"]): row
            for row in rows
        }
        active_client = client or _ProbeEiaClient(requests.Session(), http.policy, api_key)
        pages = fetch_eia_batches(active_client, specs, expected_metadata=expected)
        attempts = int(getattr(active_client, "attempts", 1))
        eligible = [
            period_date(str(row["period"]))
            for page in pages
            for row in page["response"]["data"]
            if period_date(str(row["period"])) <= as_of
        ]
        if not eligible:
            raise ValueError("EIA probe returned no eligible observations")
        output = {
            "provider": "eia",
            "phase": "normalized",
            "attempts": attempts,
            "series_count": len(expected),
            "latest_eligible_date": max(eligible).isoformat(),
            "routes": sorted({spec.route for spec in specs}),
        }
        print(json.dumps(output, sort_keys=True, separators=(",", ":")))
        return 0
    except OfficialHttpError as error:
        failure_phase = "raw" if error.phase == "schema" else "retrieve"
        output = {
            "provider": "eia",
            "phase": failure_phase,
            "attempts": error.attempts,
            "error_code": error.code,
            "error": sanitize_audit_text(error.safe_message, secrets=(api_key,)),
        }
    except Exception as error:
        output = {
            "provider": "eia",
            "phase": "metadata",
            "attempts": attempts,
            "error_code": "EIA_PROBE_FAILED",
            "error": sanitize_audit_text(error, secrets=(api_key,)),
        }
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
