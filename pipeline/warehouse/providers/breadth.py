"""S&P 500 market breadth computed from constituent prices.

Constituents: the Wikipedia "List of S&P 500 companies" table (compiled from
S&P DJI announcements; current members only, so history carries survivorship
bias — recorded in the catalog note). Prices: Yahoo Finance daily closes.

Series codes (all daily):
  pct_above_{20,50,200}dma[:<GICS sector>]   share of members above their n-day average, %
  advancers / decliners                      members up / down on the day
  median_drawdown_52w                        median of (close / 52-week high - 1), %
"""

from __future__ import annotations

import io
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Sequence

import numpy as np
import pandas as pd

from ..db.store import Observation
from .base import FetchResult, Provider, ProviderError, SeriesDef, register

WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
CHART = "https://query{n}.finance.yahoo.com/v8/finance/chart/{ticker}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko)"


def constituents(html: str) -> pd.DataFrame:
    tables = pd.read_html(io.StringIO(html))
    for table in tables:
        cols = [str(c) for c in table.columns]
        if "Symbol" in cols and "GICS Sector" in cols:
            out = table[["Symbol", "GICS Sector"]].copy()
            out["Symbol"] = out["Symbol"].astype(str).str.replace(".", "-", regex=False).str.strip()
            return out
    raise ProviderError("Wikipedia S&P 500 table not found")


def compute(closes: pd.DataFrame, sectors: dict[str, str], start: date) -> dict[str, pd.Series]:
    """closes: index=date, columns=tickers."""
    closes = closes.sort_index()
    out: dict[str, pd.Series] = {}
    groups = {"": list(closes.columns)}
    by_sector = defaultdict(list)
    for t in closes.columns:
        by_sector[sectors.get(t, "")].append(t)
    groups.update({s: ts for s, ts in by_sector.items() if s})
    for n in (20, 50, 200):
        ma = closes.rolling(n, min_periods=n).mean()
        above = (closes > ma).astype("float64").where(ma.notna() & closes.notna())
        for name, tickers in groups.items():
            sub = above[tickers]
            valid = sub.notna().sum(axis=1).astype("float64")
            share = (sub.sum(axis=1) / valid.replace(0.0, np.nan) * 100).where(valid >= max(5, 0.8 * len(tickers)))
            out[f"pct_above_{n}dma" + (f":{name}" if name else "")] = share
    change = closes.diff()
    counted = change.notna().sum(axis=1) >= 0.8 * closes.shape[1]
    out["advancers"] = (change > 0).sum(axis=1).where(counted)
    out["decliners"] = (change < 0).sum(axis=1).where(counted)
    high = closes.rolling(252, min_periods=200).max()
    dd = (closes / high - 1) * 100
    out["median_drawdown_52w"] = dd.median(axis=1, skipna=True).where(dd.notna().sum(axis=1) >= 0.8 * closes.shape[1])
    cutoff = pd.Timestamp(start)
    return {k: v[v.index >= cutoff].dropna() for k, v in out.items()}


@register
class Breadth(Provider):
    name = "BREADTH"
    batch = True

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        html = self.get(WIKI, headers={"User-Agent": UA}).decode("utf-8", errors="replace")
        members = constituents(html)
        sectors = dict(zip(members["Symbol"], members["GICS Sector"]))
        closes: dict[str, pd.Series] = {}
        failures = 0
        for i, ticker in enumerate(members["Symbol"]):
            series = self._closes(ticker, i)
            if series is None or series.empty:
                failures += 1
                continue
            closes[ticker] = series
        if len(closes) < 0.9 * len(members):
            raise ProviderError(f"only {len(closes)} of {len(members)} constituent price histories")
        frame = pd.DataFrame(closes)
        metrics = compute(frame, sectors, start)
        note = f"{len(closes)}/{len(members)} members; current constituents (survivorship bias)"
        out = []
        for d in defs:
            s = metrics.get(d.code)
            obs = [Observation(ts.date(), float(v)) for ts, v in s.items()] if s is not None else []
            out.append(FetchResult(d.key, obs, "ok" if obs else "error", note if obs else f"metric {d.code} not computed"))
        return out

    def _closes(self, ticker: str, i: int) -> pd.Series | None:
        url = CHART.format(n=1 + i % 2, ticker=ticker)
        for attempt in range(3):
            try:
                r = self.session.get(url, params={"range": "2y", "interval": "1d"}, headers={"User-Agent": UA}, timeout=(10, 30))
            except Exception:  # noqa: BLE001
                time.sleep(2)
                continue
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code != 200:
                return None
            result = (r.json().get("chart", {}).get("result") or [None])[0]
            time.sleep(0.25)
            if not result or not result.get("timestamp"):
                return None
            offset = int(result.get("meta", {}).get("gmtoffset", 0))
            quote = (result.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose") \
                or (result.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
            idx = [datetime.fromtimestamp(t + offset, tz=timezone.utc).date() for t in result["timestamp"]]
            s = pd.Series(quote, index=pd.to_datetime(idx), dtype="float64").dropna()
            return s[~s.index.duplicated(keep="last")]
        return None
