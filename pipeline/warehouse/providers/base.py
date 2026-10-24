"""Provider interface and shared HTTP helper."""

from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, ClassVar, Iterable, Mapping, Sequence

import pandas as pd
import requests

from pipeline.internal.capital_weekly.official_http import OfficialHttpError, OfficialHttpPolicy, official_get

from ..db.store import Observation

USER_AGENT = "CapitalWeekly-Warehouse/1.0 (student research database; github.com/ziyaowei1217-ctrl/Market-Data)"
POLICY = OfficialHttpPolicy(
    connect_timeout=15, read_timeout=90, total_timeout=240, max_attempts=4,
    backoff_seconds=(2, 5, 15), retry_after_cap=60,
)


@dataclass(frozen=True)
class SeriesDef:
    key: str
    provider: str
    code: str
    params: Mapping[str, Any] = field(default_factory=dict)
    title: str = ""
    frequency: str = ""
    unit: str = ""
    source_url: str = ""
    release_lag_days: int = 0
    vintages: bool = False
    runner: str = "cloud"  # cloud | local (sources that block datacenter IPs)


@dataclass
class FetchResult:
    key: str
    observations: list[Observation]
    status: str = "ok"  # ok | error | not_configured | empty
    message: str = ""


class ProviderError(RuntimeError):
    pass


class Provider:
    name: ClassVar[str]
    env_keys: ClassVar[tuple[str, ...]] = ()  # required credentials
    batch: ClassVar[bool] = False  # fetch_many instead of fetch_one

    def __init__(self, session: requests.Session | None = None, env: Mapping[str, str] | None = None):
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)
        self.env = dict(os.environ if env is None else env)

    # -- credentials
    def missing_credentials(self) -> list[str]:
        return [k for k in self.env_keys if not self.env.get(k)]

    @property
    def secrets(self) -> tuple[str, ...]:
        return tuple(v for k, v in self.env.items() if k.endswith(("_KEY", "_TOKEN", "_APP_ID")) and v)

    # -- http
    def get(self, url: str, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None) -> bytes:
        try:
            response = official_get(
                self.session, url, policy=POLICY, params=params, headers=headers, audit_secrets=self.secrets
            )
        except OfficialHttpError as error:
            raise ProviderError(f"{error.code}: {error.safe_message}") from None
        return response.body

    def get_json(self, url: str, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None) -> Any:
        return json.loads(self.get(url, params, headers).decode("utf-8-sig"))

    def get_csv(self, url: str, params: Mapping[str, Any] | None = None, **read_kwargs) -> pd.DataFrame:
        return pd.read_csv(io.BytesIO(self.get(url, params)), **read_kwargs)

    # -- fetching
    def fetch(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        missing = self.missing_credentials()
        if missing:
            return [FetchResult(d.key, [], "not_configured", f"missing {', '.join(missing)}") for d in defs]
        if self.batch:
            try:
                return self.fetch_many(defs, start)
            except Exception as error:  # noqa: BLE001
                return [FetchResult(d.key, [], "error", _safe(error, self.secrets)) for d in defs]
        results = []
        for d in defs:
            try:
                obs = self.fetch_one(d, start)
                results.append(FetchResult(d.key, obs, "ok" if obs else "empty", "" if obs else "no observations"))
            except Exception as error:  # noqa: BLE001
                results.append(FetchResult(d.key, [], "error", _safe(error, self.secrets)))
        return results

    def fetch_one(self, d: SeriesDef, start: date) -> list[Observation]:
        raise NotImplementedError

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        raise NotImplementedError


def _safe(error: Exception, secrets: Iterable[str]) -> str:
    text = f"{type(error).__name__}: {error}"
    for secret in secrets:
        text = text.replace(secret, "***")
    return text[:500]


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text in ("", ".", "NA", "N/A", "n/a", "ND", "--", "-", "nan", "NaN", ":", "null", "None"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def obs_from_pairs(pairs: Iterable[tuple[Any, Any]], start: date | None = None) -> list[Observation]:
    out: list[Observation] = []
    for when, value in pairs:
        d = pd.Timestamp(when).date()
        if start and d < start:
            continue
        v = to_float(value)
        if v is None:
            continue
        out.append(Observation(d, v))
    return out


REGISTRY: dict[str, type[Provider]] = {}


def register(cls: type[Provider]) -> type[Provider]:
    REGISTRY[cls.name] = cls
    return cls
