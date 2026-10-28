"""Nth-nearby futures settlements built from individual contracts (Yahoo delayed closes).

EIA stopped publishing NYMEX contract 1-4 prices in April 2024, so the curve is rebuilt
from the listed contracts themselves: on each trading day the contracts are ordered by
expiry and the nth one that has not yet expired is "contract n" (a contract still counts
on its last trading day, as EIA's series did). Expired contracts are no longer served by
Yahoo, so history only reaches back as far as the contracts still listed; it accumulates
week by week from here.

code = "<root>:<n>", root CL (NYMEX WTI) or BZ (NYMEX Brent last-day financial, cash-settled
on the ICE Brent settlement).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Sequence

from .base import FetchResult, Provider, ProviderError, SeriesDef, register
from .official import Yahoo
from ..db.store import Observation

MONTH_CODES = "FGHJKMNQUVXZ"
HISTORY_DAYS = 400  # look for contracts that expired up to about a year ago (Yahoo may still serve them)


def _weekday_on_or_before(d: date) -> date:
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _business_days_before(d: date, n: int) -> date:
    while n:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def _add_months(year: int, month: int, k: int) -> tuple[int, int]:
    i = year * 12 + (month - 1) + k
    return i // 12, i % 12 + 1


def expiry(root: str, year: int, month: int) -> date:
    """Last trading day (weekends only; exchange holidays are ignored)."""
    if root == "CL":  # 3 business days before the 25th of the prior month (or before the business day preceding it)
        py, pm = _add_months(year, month, -1)
        return _business_days_before(_weekday_on_or_before(date(py, pm, 25)), 3)
    if root == "BZ":  # last business day of the second month preceding the contract month
        py, pm = _add_months(year, month, -1)
        return _weekday_on_or_before(date(py, pm, 1) - timedelta(days=1))
    raise ValueError(f"unknown futures root {root}")


def ticker(root: str, year: int, month: int) -> str:
    return f"{root}{MONTH_CODES[month - 1]}{year % 100:02d}.NYM"


def front(root: str, day: date) -> tuple[int, int]:
    """The first contract whose last trading day is on or after ``day``."""
    y, m = day.year, day.month
    while expiry(root, y, m) < day:
        y, m = _add_months(y, m, 1)
    return y, m


def nth_nearby(root: str, closes: dict[tuple[str, int, int], dict[date, float]], n: int) -> dict[date, float]:
    days = sorted({d for (r, _, _), series in closes.items() if r == root for d in series})
    out = {}
    for day in days:
        y, m = _add_months(*front(root, day), n - 1)
        value = closes.get((root, y, m), {}).get(day)
        if value is not None:
            out[day] = value
    return out


@register
class FuturesCurve(Provider):
    name = "FUTC"
    batch = True

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        today = datetime.now(timezone.utc).date()
        depth: dict[str, int] = defaultdict(int)
        for d in defs:
            root, n = d.code.split(":")
            depth[root] = max(depth[root], int(n))
        yahoo = Yahoo(session=self.session, env=self.env)
        closes: dict[tuple[str, int, int], dict[date, float]] = {}
        missing: dict[str, int] = defaultdict(int)
        for root, n_max in depth.items():
            y, m = front(root, max(start, today - timedelta(days=HISTORY_DAYS)))
            last = _add_months(*front(root, today), n_max)
            while (y, m) <= last:
                code = ticker(root, y, m)
                try:
                    obs = yahoo.fetch_one(SeriesDef(key=f"YAHOO:{code}", provider="YAHOO", code=code, frequency="D"), start)
                    closes[(root, y, m)] = {o.obs_date: o.value for o in obs if o.obs_date <= expiry(root, y, m)}
                except ProviderError:
                    missing[root] += 1  # expired and no longer served, or not listed
                y, m = _add_months(y, m, 1)
        out = []
        for d in defs:
            root, n = d.code.split(":")
            series = nth_nearby(root, closes, int(n))
            obs = [Observation(k, v) for k, v in sorted(series.items()) if k >= start]
            loaded = sum(1 for (r, _, _) in closes if r == root)
            out.append(FetchResult(d.key, obs, "ok" if obs else "empty",
                                   f"{len(obs)} obs from {loaded} contracts ({missing[root]} unavailable)"))
        return out
