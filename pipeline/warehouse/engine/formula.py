"""Formula engine for weekly indicator values.

Every catalog indicator is either a raw series or a formula over raw series,
for example::

    {FRED:SP500}                       level (last value on/before the cutoff)
    ret({FRED:SP500}, "YTD")           percent return since previous year end
    chg({FRED:DGS10}, "W") * 100       weekly change, percent -> bp
    pctile({FRED:BAMLC0A0CM}, "3Y")    percentile of current value within 3 years
    yoy({BLS:CUUR0000SA0})             year-over-year percent change
    prior(pop({FRED:PPIFIS}))          prior period as listed in the latest release

Two clocks are applied before anything is calculated (清单「四个时点」):

* ``obs_cutoff``   – the weekly cut-off (Friday). Observations dated later are ignored.
* ``known_cutoff`` – what was knowable. Each stored value carries ``realtime_start``;
  values that were not yet published at ``known_cutoff`` are ignored.

Series-valued expressions (``TS``) are transformed in their native frequency.
Window functions (``ret``, ``chg``, ``snap``, ``pctile`` ...) turn a series into a
``Scalar`` at the cut-off. Missing data stays ``None`` with an explicit status;
nothing is ever filled with zero.
"""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd

DAY = pd.Timedelta(days=1)
SERIES_REF = re.compile(r"\{([A-Za-z0-9_]+:[^{}]+)\}")


# --------------------------------------------------------------------------- values


@dataclass
class Scalar:
    value: float | None
    obs_date: pd.Timestamp | None = None
    status: str = "ok"
    detail: str = ""

    @classmethod
    def missing(cls, status: str, detail: str = "") -> "Scalar":
        return cls(None, None, status, detail)


class TS:
    """A time series: index=obs_date, columns value/known (date first knowable)."""

    __slots__ = ("frame",)

    def __init__(self, frame: pd.DataFrame):
        self.frame = frame

    @classmethod
    def from_arrays(cls, index, value, known) -> "TS":
        frame = pd.DataFrame(
            {"value": np.asarray(value, dtype=float), "known": pd.to_datetime(known)},
            index=pd.DatetimeIndex(index, name="obs_date"),
        )
        frame = frame[~frame.index.duplicated(keep="last")].sort_index()
        frame = frame[np.isfinite(frame["value"].to_numpy())]
        return cls(frame)

    @property
    def empty(self) -> bool:
        return self.frame.empty

    def with_values(self, values: pd.Series, known: pd.Series | None = None) -> "TS":
        frame = pd.DataFrame(
            {"value": values.astype(float), "known": self.frame["known"] if known is None else known}
        )
        frame = frame[np.isfinite(frame["value"].to_numpy())]
        return TS(frame)


class FormulaError(ValueError):
    pass


# --------------------------------------------------------------------------- context


@dataclass
class RawSeries:
    """All stored versions of one series."""

    obs_date: np.ndarray  # datetime64[ns], sorted by (obs_date, realtime_start)
    realtime_start: np.ndarray
    value: np.ndarray
    vintage_source: np.ndarray

    @classmethod
    def from_frame(cls, frame: pd.DataFrame) -> "RawSeries":
        frame = frame.sort_values(["obs_date", "realtime_start"], kind="mergesort")
        return cls(
            pd.to_datetime(frame["obs_date"]).to_numpy(),
            pd.to_datetime(frame["realtime_start"]).to_numpy(),
            frame["value"].to_numpy(dtype=float),
            frame["vintage_source"].astype(str).to_numpy(),
        )

    def as_of(self, known_cutoff: pd.Timestamp) -> TS:
        mask = self.realtime_start <= np.datetime64(known_cutoff)
        obs, rts, val = self.obs_date[mask], self.realtime_start[mask], self.value[mask]
        if len(obs) == 0:
            return TS.from_arrays([], [], [])
        last = np.r_[obs[1:] != obs[:-1], True]  # last version of each obs_date
        return TS.from_arrays(obs[last], val[last], rts[last])

    def latest_first_known(self) -> TS:
        """Latest value of each observation, dated by when it was first knowable."""
        if len(self.obs_date) == 0:
            return TS.from_arrays([], [], [])
        obs = self.obs_date
        first = np.r_[True, obs[1:] != obs[:-1]]
        last = np.r_[obs[1:] != obs[:-1], True]
        return TS.from_arrays(obs[last], self.value[last], self.realtime_start[first])

    def versions(self, obs_date: pd.Timestamp, known_cutoff: pd.Timestamp) -> tuple[np.ndarray, np.ndarray]:
        mask = (self.obs_date == np.datetime64(obs_date)) & (
            self.realtime_start <= np.datetime64(known_cutoff)
        )
        return self.realtime_start[mask], self.vintage_source[mask]


@dataclass
class Context:
    raw: dict[str, RawSeries]
    obs_cutoff: pd.Timestamp
    known_cutoff: pd.Timestamp
    fast: bool = False
    shared_cache: dict[str, Any] = field(default_factory=dict)
    cache: dict[str, Any] = field(default_factory=dict)

    def base(self, key: str) -> TS:
        raw = self.raw.get(key)
        if raw is None:
            raise MissingSeries(key)
        if self.fast:
            cache_key = f"base:{key}"
            if cache_key not in self.shared_cache:
                self.shared_cache[cache_key] = raw.latest_first_known()
            return self.shared_cache[cache_key]
        cache_key = f"base:{key}"
        if cache_key not in self.cache:
            self.cache[cache_key] = raw.as_of(self.known_cutoff)
        return self.cache[cache_key]

    def at_vintage(self, known_cutoff: pd.Timestamp) -> "Context":
        return Context(self.raw, self.obs_cutoff, known_cutoff, fast=False)

    def visible(self, ts: TS) -> pd.DataFrame:
        frame = ts.frame
        if frame.empty:
            return frame
        mask = (frame.index <= self.obs_cutoff) & (frame["known"] <= self.known_cutoff)
        return frame[mask]


class MissingSeries(KeyError):
    pass


# --------------------------------------------------------------------------- helpers


def infer_freq(index: pd.DatetimeIndex) -> str:
    if len(index) < 3:
        return "M"
    gaps = np.diff(index.values).astype("timedelta64[D]").astype(float)
    median = float(np.median(gaps))
    if median <= 4:
        return "D"
    if median <= 10:
        return "W"
    if median <= 45:
        return "M"
    if median <= 120:
        return "Q"
    return "A"


PERIODS_PER_YEAR = {"D": 252, "W": 52, "M": 12, "Q": 4, "A": 1}


def window_anchor(t: pd.Timestamp, window: str) -> pd.Timestamp:
    w = window.upper()
    if w == "W":
        return t - pd.Timedelta(days=7)
    if w in ("MTD", "ME"):
        return t.replace(day=1) - DAY
    if w in ("QTD", "QE"):
        first_month = 3 * ((t.month - 1) // 3) + 1
        return t.replace(month=first_month, day=1) - DAY
    if w in ("YTD", "YE"):
        return pd.Timestamp(year=t.year - 1, month=12, day=31)
    match = re.fullmatch(r"(\d+)([DWMY])", w)
    if not match:
        raise FormulaError(f"unknown window {window!r}")
    n, unit = int(match.group(1)), match.group(2)
    if unit == "D":
        return t - pd.Timedelta(days=n)
    if unit == "W":
        return t - pd.Timedelta(weeks=n)
    if unit == "M":
        return t - pd.DateOffset(months=n)
    return t - pd.DateOffset(years=n)


def _asof(frame: pd.DataFrame, when: pd.Timestamp) -> tuple[float, pd.Timestamp] | None:
    if frame.empty:
        return None
    pos = frame.index.searchsorted(when, side="right") - 1
    if pos < 0:
        return None
    return float(frame["value"].iat[pos]), frame.index[pos]


def _last(frame: pd.DataFrame) -> tuple[float, pd.Timestamp] | None:
    if frame.empty:
        return None
    return float(frame["value"].iat[-1]), frame.index[-1]


def _fridays(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.date_range(start, end, freq="W-FRI")


def _sample_weekly(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, stale_days: int) -> np.ndarray:
    fridays = _fridays(start, end)
    if frame.empty or len(fridays) == 0:
        return np.array([])
    pos = frame.index.searchsorted(fridays, side="right") - 1
    out = np.full(len(fridays), np.nan)
    ok = pos >= 0
    idx = frame.index.values
    values = frame["value"].to_numpy()
    for i in np.nonzero(ok)[0]:
        p = pos[i]
        if (fridays.values[i] - idx[p]) <= np.timedelta64(stale_days, "D"):
            out[i] = values[p]
    return out


# --------------------------------------------------------------------------- series transforms


def _require_ts(x: Any, fn: str) -> TS:
    if not isinstance(x, TS):
        raise FormulaError(f"{fn}() needs a series argument")
    return x


def f_level(ctx: Context, x: TS) -> TS:
    return _require_ts(x, "level")


def f_pop(ctx: Context, x: TS, n: int = 1) -> TS:
    """Percent change over n native periods (MoM for monthly, QoQ for quarterly)."""
    s = _require_ts(x, "pop").frame["value"]
    return x.with_values((s / s.shift(int(n)) - 1.0) * 100.0)


def f_diff(ctx: Context, x: TS, n: int = 1) -> TS:
    s = _require_ts(x, "diff").frame["value"]
    return x.with_values(s - s.shift(int(n)))


def f_lag(ctx: Context, x: TS, n: int = 1) -> TS:
    s = _require_ts(x, "lag").frame["value"]
    return x.with_values(s.shift(int(n)))


def f_ma(ctx: Context, x: TS, n: int) -> TS:
    s = _require_ts(x, "ma").frame["value"]
    return x.with_values(s.rolling(int(n), min_periods=int(n)).mean())


def f_msum(ctx: Context, x: TS, n: int) -> TS:
    s = _require_ts(x, "msum").frame["value"]
    return x.with_values(s.rolling(int(n), min_periods=int(n)).sum())


def f_ann(ctx: Context, x: TS, n: int = 1) -> TS:
    """Annualized percent change over n native periods: ((x/x[-n])^(ppy/n) - 1)*100."""
    frame = _require_ts(x, "ann").frame
    ppy = PERIODS_PER_YEAR[infer_freq(frame.index)]
    s = frame["value"]
    ratio = s / s.shift(int(n))
    return x.with_values((ratio ** (ppy / int(n)) - 1.0) * 100.0)


def f_yoy(ctx: Context, x: TS) -> TS:
    """Percent change versus the observation one calendar year earlier."""
    frame = _require_ts(x, "yoy").frame
    if frame.empty:
        return x
    freq = infer_freq(frame.index)
    tolerance = pd.Timedelta(days=7 if freq in ("D", "W") else 3)
    idx = frame.index
    target = idx - pd.DateOffset(years=1)
    pos = idx.searchsorted(target, side="right") - 1
    values = frame["value"].to_numpy()
    prev = np.full(len(idx), np.nan)
    for i, p in enumerate(pos):
        if p >= 0 and idx[p] >= target[i] - tolerance:
            prev[i] = values[p]
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (values / prev - 1.0) * 100.0
    return x.with_values(pd.Series(out, index=idx))


def f_fytd(ctx: Context, x: TS, start_month: int = 10) -> TS:
    """Fiscal-year-to-date cumulative sum (US federal fiscal year starts in October)."""
    frame = _require_ts(x, "fytd").frame
    idx = frame.index
    fiscal_year = idx.year + (idx.month >= int(start_month)).astype(int)
    return x.with_values(frame["value"].groupby(fiscal_year).cumsum())


def f_ytd_sum(ctx: Context, x: TS) -> TS:
    return f_fytd(ctx, x, 1)


def f_qe(ctx: Context, x: TS) -> TS:
    """Quarter-end sampling: last observation in each calendar quarter."""
    frame = _require_ts(x, "qe").frame
    if frame.empty:
        return x
    quarters = frame.index.to_period("Q")
    last = frame.groupby(quarters).tail(1)
    # Drop the running quarter: only completed quarter ends count.
    complete = last[last.index.to_period("Q").end_time.normalize() <= last.index.max().normalize()]
    return TS(complete)


# --------------------------------------------------------------------------- window functions


def _scalar_input(ctx: Context, x: Any, fn: str) -> pd.DataFrame:
    return ctx.visible(_require_ts(x, fn))


def f_latest(ctx: Context, x: TS) -> Scalar:
    frame = _scalar_input(ctx, x, "latest")
    last = _last(frame)
    if last is None:
        return Scalar.missing("missing_input")
    return Scalar(last[0], last[1])


def f_ret(ctx: Context, x: TS, window: str) -> Scalar:
    frame = _scalar_input(ctx, x, "ret")
    last = _last(frame)
    anchor = _asof(frame, window_anchor(ctx.obs_cutoff, window))
    if last is None:
        return Scalar.missing("missing_input")
    if anchor is None or anchor[0] == 0:
        return Scalar.missing("insufficient_history", f"no value on/before {window} anchor")
    return Scalar((last[0] / anchor[0] - 1.0) * 100.0, last[1], detail=f"base {anchor[1].date()}")


def f_chg(ctx: Context, x: TS, window: str) -> Scalar:
    frame = _scalar_input(ctx, x, "chg")
    last = _last(frame)
    anchor = _asof(frame, window_anchor(ctx.obs_cutoff, window))
    if last is None:
        return Scalar.missing("missing_input")
    if anchor is None:
        return Scalar.missing("insufficient_history", f"no value on/before {window} anchor")
    return Scalar(last[0] - anchor[0], last[1], detail=f"base {anchor[1].date()}")


def f_snap(ctx: Context, x: TS, window: str) -> Scalar:
    """Value at the previous period end: ME=上月末, QE=上季末, YE=上年末."""
    frame = _scalar_input(ctx, x, "snap")
    anchor_date = window_anchor(ctx.obs_cutoff, window)
    hit = _asof(frame, anchor_date)
    if hit is None:
        return Scalar.missing("insufficient_history")
    return Scalar(hit[0], hit[1])


def f_pctile(ctx: Context, x: TS, window: str = "3Y") -> Scalar:
    """Percentile (0-100) of the current value within weekly samples of the window."""
    frame = _scalar_input(ctx, x, "pctile")
    last = _last(frame)
    if last is None:
        return Scalar.missing("missing_input")
    start = window_anchor(ctx.obs_cutoff, window)
    if frame.index[0] > start + pd.Timedelta(days=14):
        return Scalar.missing(
            "insufficient_history", f"history starts {frame.index[0].date()}, window needs {start.date()}"
        )
    samples = _sample_weekly(frame, start + DAY, ctx.obs_cutoff, stale_days=10)
    samples = samples[np.isfinite(samples)]
    if len(samples) < 10:
        return Scalar.missing("insufficient_history", f"{len(samples)} weekly samples")
    current = last[0]
    below = float(np.sum(samples < current))
    equal = float(np.sum(samples == current))
    n = len(samples)
    rank = (below + 0.5 * max(equal - 1.0, 0.0)) / max(n - 1, 1) * 100.0
    return Scalar(min(max(rank, 0.0), 100.0), last[1], detail=f"{n} weekly samples since {start.date()}")


def f_vol(ctx: Context, x: TS, window: str = "52W") -> Scalar:
    """Annualized volatility of weekly (Friday) returns: std * sqrt(52) * 100."""
    frame = _scalar_input(ctx, x, "vol")
    last = _last(frame)
    if last is None:
        return Scalar.missing("missing_input")
    start = window_anchor(ctx.obs_cutoff, window)
    samples = _sample_weekly(frame, start, ctx.obs_cutoff, stale_days=7)
    if len(samples) < 2 or not np.all(np.isfinite(samples)):
        return Scalar.missing("insufficient_history", "gaps in weekly samples")
    returns = samples[1:] / samples[:-1] - 1.0
    if len(returns) < 26:
        return Scalar.missing("insufficient_history", f"{len(returns)} weekly returns")
    return Scalar(float(np.std(returns, ddof=1) * math.sqrt(52) * 100.0), last[1], detail=f"{len(returns)} weekly returns")


def f_corr(ctx: Context, x: TS, y: TS, window: str = "52W") -> Scalar:
    """Correlation of weekly (Friday) returns of two series over the window."""
    fx, fy = _scalar_input(ctx, x, "corr"), _scalar_input(ctx, y, "corr")
    lx, ly = _last(fx), _last(fy)
    if lx is None or ly is None:
        return Scalar.missing("missing_input")
    start = window_anchor(ctx.obs_cutoff, window)
    sx = _sample_weekly(fx, start, ctx.obs_cutoff, stale_days=7)
    sy = _sample_weekly(fy, start, ctx.obs_cutoff, stale_days=7)
    if len(sx) < 2 or not (np.all(np.isfinite(sx)) and np.all(np.isfinite(sy))):
        return Scalar.missing("insufficient_history", "gaps in weekly samples")
    rx, ry = sx[1:] / sx[:-1] - 1.0, sy[1:] / sy[:-1] - 1.0
    if len(rx) < 8:
        return Scalar.missing("insufficient_history", f"{len(rx)} weekly returns")
    return Scalar(float(np.corrcoef(rx, ry)[0, 1]), min(lx[1], ly[1]), detail=f"{len(rx)} weekly returns")


def f_drawdown(ctx: Context, x: TS) -> Scalar:
    """Current value relative to the running peak of all stored history, in percent."""
    frame = _scalar_input(ctx, x, "drawdown")
    last = _last(frame)
    if last is None:
        return Scalar.missing("missing_input")
    peak = float(frame["value"].max())
    return Scalar((last[0] / peak - 1.0) * 100.0, last[1], detail=f"peak over history since {frame.index[0].date()}")


def f_hist_mean(ctx: Context, x: TS) -> Scalar:
    """Mean of all visible observations (e.g. historical mean of rolling returns)."""
    frame = _scalar_input(ctx, x, "hist_mean")
    if frame.empty:
        return Scalar.missing("missing_input")
    return Scalar(float(frame["value"].mean()), frame.index[-1], detail=f"{len(frame)} obs since {frame.index[0].date()}")


def f_hist_share(ctx: Context, x: TS, threshold: float = 0.0) -> Scalar:
    """Percent of visible observations strictly above threshold."""
    frame = _scalar_input(ctx, x, "hist_share")
    if frame.empty:
        return Scalar.missing("missing_input")
    share = float((frame["value"] > float(threshold)).mean() * 100.0)
    return Scalar(share, frame.index[-1], detail=f"{len(frame)} windows since {frame.index[0].date()}")


def f_maxdd(ctx: Context, x: TS, window: str = "YTD") -> Scalar:
    frame = _scalar_input(ctx, x, "maxdd")
    last = _last(frame)
    if last is None:
        return Scalar.missing("missing_input")
    anchor_date = window_anchor(ctx.obs_cutoff, window)
    anchor = _asof(frame, anchor_date)
    if anchor is None:
        return Scalar.missing("insufficient_history")
    path = np.r_[anchor[0], frame["value"][frame.index > anchor_date].to_numpy()]
    peaks = np.maximum.accumulate(path)
    return Scalar(float(np.min(path / peaks - 1.0) * 100.0), last[1])


# --------------------------------------------------------------------------- vintage functions
# These receive AST nodes because they re-evaluate their argument as of an
# earlier release (point-in-time / 发布版本).


def _primary_key(node: ast.AST) -> str:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == "S":
            return sub.args[0].value  # type: ignore[attr-defined]
    raise FormulaError("vintage functions need a series reference")


def _release_date(ctx: Context, key: str, obs_date: pd.Timestamp) -> tuple[pd.Timestamp | None, str]:
    raw = ctx.raw[key]
    starts, sources = raw.versions(obs_date, ctx.known_cutoff)
    if len(starts) == 0:
        return None, "missing_input"
    if sources[0] == "backfill_estimate":
        return None, "no_vintage"
    return pd.Timestamp(starts[0]), "ok"


def _series_at(ctx: Context, node: ast.AST, known: pd.Timestamp) -> pd.DataFrame:
    sub = ctx.at_vintage(known)
    result = evaluate_node(node, sub)
    return sub.visible(_require_ts(result, "vintage"))


def _period_before(frame: pd.DataFrame, obs_date: pd.Timestamp, k: int = 1) -> pd.Timestamp | None:
    pos = frame.index.searchsorted(obs_date, side="left") - k
    return frame.index[pos] if pos >= 0 else None


def _latest_period(ctx: Context, node: ast.AST) -> tuple[pd.DataFrame, pd.Timestamp] | None:
    current = ctx.visible(_require_ts(evaluate_node(node, ctx.at_vintage(ctx.known_cutoff)), "vintage"))
    if current.empty:
        return None
    return current, current.index[-1]


def v_first(ctx: Context, node: ast.AST) -> Scalar:
    """First-release value of the latest period (首次公布值)."""
    found = _latest_period(ctx, node)
    if found is None:
        return Scalar.missing("missing_input")
    _, period = found
    key = _primary_key(node)
    release, status = _release_date(ctx, key, period)
    if release is None:
        return Scalar.missing(status, "first release not recorded")
    frame = _series_at(ctx, node, release)
    if period not in frame.index:
        return Scalar.missing("missing_input")
    return Scalar(float(frame.at[period, "value"]), period, detail=f"release {release.date()}")


def v_prior(ctx: Context, node: ast.AST) -> Scalar:
    """Previous period's value as listed in the release that first published the latest period (本次发布所列前值)."""
    found = _latest_period(ctx, node)
    if found is None:
        return Scalar.missing("missing_input")
    _, period = found
    release, status = _release_date(ctx, _primary_key(node), period)
    if release is None:
        return Scalar.missing(status, "release vintage not recorded")
    frame = _series_at(ctx, node, release)
    previous = _period_before(frame, period)
    if previous is None:
        return Scalar.missing("insufficient_history")
    return Scalar(float(frame.at[previous, "value"]), previous, detail=f"as listed {release.date()}")


def v_rev(ctx: Context, node: ast.AST, k: ast.AST | None = None) -> Scalar:
    """Revision to period P-k in the latest release versus the previous release."""
    lag = int(ast.literal_eval(k)) if k is not None else 1
    found = _latest_period(ctx, node)
    if found is None:
        return Scalar.missing("missing_input")
    current, period = found
    key = _primary_key(node)
    release, status = _release_date(ctx, key, period)
    if release is None:
        return Scalar.missing(status)
    previous_period = _period_before(current, period)
    if previous_period is None:
        return Scalar.missing("insufficient_history")
    prev_release, status = _release_date(ctx, key, previous_period)
    if prev_release is None:
        return Scalar.missing(status)
    now_frame = _series_at(ctx, node, release)
    then_frame = _series_at(ctx, node, prev_release)
    target = _period_before(now_frame, period, lag)
    if target is None or target not in then_frame.index:
        return Scalar.missing("insufficient_history")
    value = float(now_frame.at[target, "value"]) - float(then_frame.at[target, "value"])
    return Scalar(value, target, detail=f"{prev_release.date()} -> {release.date()}")


def v_prev_vintage(ctx: Context, node: ast.AST) -> Scalar:
    """Latest period's value in the vintage before the current one (e.g. GDPNow 上次值)."""
    found = _latest_period(ctx, node)
    if found is None:
        return Scalar.missing("missing_input")
    _, period = found
    raw = ctx.raw[_primary_key(node)]
    starts, _ = raw.versions(period, ctx.known_cutoff)
    if len(starts) < 2:
        return Scalar.missing("insufficient_history", "only one estimate for this period")
    frame = _series_at(ctx, node, pd.Timestamp(starts[-2]))
    if period not in frame.index:
        return Scalar.missing("missing_input")
    return Scalar(float(frame.at[period, "value"]), period, detail=f"vintage {pd.Timestamp(starts[-2]).date()}")


def f_at_year(ctx: Context, x: TS, offset: int = 0) -> Scalar:
    """Latest value dated within calendar year (cut-off year + offset), e.g. SEP medians."""
    frame = _scalar_input(ctx, x, "at_year")
    year = ctx.obs_cutoff.year + int(offset)
    if frame.empty:
        return Scalar.missing("missing_input")
    # Annual projections are dated Jan 1 of the target year, which may lie after
    # obs_cutoff; only the knowledge cut-off applies to them.
    full = x.frame[x.frame["known"] <= ctx.known_cutoff]
    hits = full[full.index.year == year]
    if hits.empty:
        return Scalar.missing("missing_input", f"no value for {year}")
    return Scalar(float(hits["value"].iat[-1]), hits.index[-1], detail=f"target year {year}")


def f_year_ret(ctx: Context, x: TS, year: int) -> Scalar:
    """Calendar-year return: year-end level / previous year-end level - 1, in percent."""
    frame = _scalar_input(ctx, x, "year_ret")
    end = _asof(frame, pd.Timestamp(year=int(year), month=12, day=31))
    base = _asof(frame, pd.Timestamp(year=int(year) - 1, month=12, day=31))
    if end is None or base is None or end[1].year != int(year) or base[0] == 0:
        return Scalar.missing("insufficient_history")
    return Scalar((end[0] / base[0] - 1.0) * 100.0, end[1])


def f_before_change(ctx: Context, x: TS) -> Scalar:
    """Value in force before the most recent change (policy rate 前值)."""
    frame = _scalar_input(ctx, x, "before_change")
    if frame.empty:
        return Scalar.missing("missing_input")
    values = frame["value"].to_numpy()
    current = values[-1]
    changed = np.nonzero(values != current)[0]
    if len(changed) == 0:
        return Scalar.missing("insufficient_history", "no change in stored history")
    pos = changed[-1]
    return Scalar(float(values[pos]), frame.index[pos], detail=f"changed after {frame.index[pos].date()}")


# --------------------------------------------------------------------------- Treasury par-bond model

PAR_TENORS = {0.5: "6 Mo", 1: "1 Yr", 2: "2 Yr", 3: "3 Yr", 5: "5 Yr", 7: "7 Yr", 10: "10 Yr", 20: "20 Yr", 30: "30 Yr"}
PAR_KEYS = {t: f"TSYCURVE:{label}" for t, label in PAR_TENORS.items()}


def _bond_price(coupon: float, years: float, y: float) -> float:
    """Price per 100 of a semiannual bond, whole number of half-years."""
    n = int(round(years * 2))
    if n <= 0:
        return 100.0
    c, r = coupon * 100 / 2, y / 2
    if abs(r) < 1e-12:
        return c * n + 100.0
    return c * (1 - (1 + r) ** -n) / r + 100.0 * (1 + r) ** -n


def _curve_at(curve: dict[float, float], years: float) -> float:
    points = sorted(curve)
    if years <= points[0]:
        return curve[points[0]]
    for lo, hi in zip(points, points[1:]):
        if lo <= years <= hi:
            w = (years - lo) / (hi - lo)
            return curve[lo] * (1 - w) + curve[hi] * w
    return curve[points[-1]]


def par_bond_metrics(curve_pct: dict[float, float], tenor: float, shift_bp: float) -> dict[str, float]:
    """清单 109 定义：同日起始曲线定价合成平价券；前 6 个月曲线平行移动 shift，随后保持；
    持有 1 年；第一笔票息按（移动后）6 个月利率再投资。返回 % / 年 / 年²。"""
    curve = {t: v / 100.0 for t, v in curve_pct.items()}
    y0 = _curve_at(curve, tenor)
    coupon = y0  # par bond: coupon = par yield
    h = 1e-4
    p0 = _bond_price(coupon, tenor, y0)
    up, dn = _bond_price(coupon, tenor, y0 + h), _bond_price(coupon, tenor, y0 - h)
    mod_dur = -(up - dn) / (2 * h) / p0
    convexity = (up + dn - 2 * p0) / (h * h) / p0
    shifted = {t: v + shift_bp / 10000.0 for t, v in curve.items()}
    half_coupon = coupon * 100 / 2
    r6 = shifted[0.5]
    reinvested = half_coupon * (1 + r6 / 2)
    remaining = tenor - 1.0
    end_price = 100.0 if remaining <= 0 else _bond_price(coupon, remaining, _curve_at(shifted, remaining))
    total = (end_price + half_coupon + reinvested - p0) / p0 * 100.0
    return {"tr": total, "yield": y0 * 100.0, "coupon": coupon * 100.0, "duration": mod_dur, "convexity": convexity}


def v_parbond(ctx: Context, metric: ast.AST, tenor: ast.AST, shift: ast.AST | None = None) -> Scalar:
    """parbond("tr"|"yield"|"coupon"|"duration"|"convexity", tenor_years, shift_bp)."""
    name = ast.literal_eval(metric)
    t = float(ast.literal_eval(tenor))
    bp = float(ast.literal_eval(shift)) if shift is not None else 0.0
    curve: dict[float, float] = {}
    dates = []
    for years, key in PAR_KEYS.items():
        frame = ctx.visible(ctx.base(key))
        last = _last(frame)
        if last is None:
            return Scalar.missing("missing_input", f"{key} missing")
        curve[years], d = last
        dates.append(d)
    if max(dates) - min(dates) > pd.Timedelta(days=3):
        return Scalar.missing("missing_input", "curve points from different dates")
    value = par_bond_metrics(curve, t, bp)[name]
    return Scalar(float(value), max(dates), detail=f"par curve {max(dates).date()}")


def f_newest(ctx: Context, *xs: TS) -> Scalar:
    """Latest value across several series (e.g. Advance/Prelim/Final GDP consensus)."""
    best = None
    for x in xs:
        last = _last(_scalar_input(ctx, x, "newest"))
        if last is not None and (best is None or last[1] > best[1]):
            best = last
    if best is None:
        return Scalar.missing("missing_input")
    return Scalar(best[0], best[1])


def v_surprise(ctx: Context, actual: ast.AST, *consensus: ast.AST) -> Scalar:
    """First print of the latest period minus the consensus snapshot taken for that
    release (consensus dated within 20 days before / 3 days after the first print)."""
    found = _latest_period(ctx, actual)
    if found is None:
        return Scalar.missing("missing_input")
    _, period = found
    release, status = _release_date(ctx, _primary_key(actual), period)
    if release is None:
        return Scalar.missing(status, "first release of the actual not recorded")
    first_frame = _series_at(ctx, actual, release)
    if period not in first_frame.index:
        return Scalar.missing("missing_input")
    first_value = float(first_frame.at[period, "value"])
    best = None
    for node in consensus:
        frame = ctx.visible(_require_ts(evaluate_node(node, ctx), "surprise"))
        window = frame[(frame.index >= release - pd.Timedelta(days=20)) & (frame.index <= release + pd.Timedelta(days=3))]
        if not window.empty and (best is None or window.index[-1] > best[1]):
            best = (float(window["value"].iat[-1]), window.index[-1])
    if best is None:
        return Scalar.missing("missing_input", f"no consensus snapshot near release {release.date()}")
    return Scalar(first_value - best[0], period, detail=f"first print {release.date()} vs consensus {best[1].date()}")


SERIES_FUNCS: dict[str, Callable[..., Any]] = {
    "level": f_level,
    "pop": f_pop,
    "diff": f_diff,
    "lag": f_lag,
    "ma": f_ma,
    "msum": f_msum,
    "ann": f_ann,
    "yoy": f_yoy,
    "fytd": f_fytd,
    "ytd_sum": f_ytd_sum,
    "qe": f_qe,
}
SCALAR_FUNCS: dict[str, Callable[..., Any]] = {
    "latest": f_latest,
    "ret": f_ret,
    "chg": f_chg,
    "snap": f_snap,
    "pctile": f_pctile,
    "vol": f_vol,
    "corr": f_corr,
    "drawdown": f_drawdown,
    "maxdd": f_maxdd,
    "at_year": f_at_year,
    "year_ret": f_year_ret,
    "before_change": f_before_change,
    "hist_mean": f_hist_mean,
    "hist_share": f_hist_share,
    "newest": f_newest,
}
VINTAGE_FUNCS: dict[str, Callable[..., Any]] = {
    "first": v_first,
    "prior": v_prior,
    "rev": v_rev,
    "prev_vintage": v_prev_vintage,
    "parbond": v_parbond,
    "surprise": v_surprise,
}
# Functions that read fixed series in addition to the {KEY} references in a formula.
IMPLICIT_SERIES: dict[str, tuple[str, ...]] = {"parbond": tuple(PAR_KEYS.values())}
ALL_FUNCS = {"S", *SERIES_FUNCS, *SCALAR_FUNCS, *VINTAGE_FUNCS}


# --------------------------------------------------------------------------- parsing & evaluation


@dataclass(frozen=True)
class Formula:
    text: str
    tree: ast.Expression
    series: tuple[str, ...]


_PARSE_CACHE: dict[str, Formula] = {}


def parse(text: str) -> Formula:
    if text in _PARSE_CACHE:
        return _PARSE_CACHE[text]
    keys: list[str] = []

    def repl(match: re.Match[str]) -> str:
        keys.append(match.group(1))
        return f"S({match.group(1)!r})"

    source = SERIES_REF.sub(repl, text)
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as error:
        raise FormulaError(f"cannot parse formula {text!r}: {error}") from None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALL_FUNCS:
                raise FormulaError(f"unknown function in {text!r}")
        elif isinstance(node, ast.Name):
            if node.id not in ALL_FUNCS:
                raise FormulaError(f"unknown name {node.id!r} in {text!r}")
        elif not isinstance(
            node,
            (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Load, ast.keyword,
             ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd),
        ):
            raise FormulaError(f"unsupported syntax {type(node).__name__} in {text!r}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in IMPLICIT_SERIES:
            keys.extend(IMPLICIT_SERIES[node.func.id])
    formula = Formula(text, tree, tuple(dict.fromkeys(keys)))
    _PARSE_CACHE[text] = formula
    return formula


_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a ** b,
}


def _to_scalar(ctx: Context, x: Any) -> Scalar | float:
    if isinstance(x, TS):
        return f_latest(ctx, x)
    return x


def _binop(ctx: Context, op: ast.operator, a: Any, b: Any) -> Any:
    fn = _OPS[type(op)]
    if isinstance(a, TS) and isinstance(b, TS):
        left, right = a.frame, b.frame
        joined = left.join(right, how="inner", lsuffix="_a", rsuffix="_b")
        with np.errstate(divide="ignore", invalid="ignore"):
            values = fn(joined["value_a"], joined["value_b"])
        known = joined[["known_a", "known_b"]].max(axis=1)
        frame = pd.DataFrame({"value": values.astype(float), "known": known})
        frame = frame[np.isfinite(frame["value"].to_numpy())]
        return TS(frame)
    if isinstance(a, TS) and isinstance(b, (int, float)):
        with np.errstate(divide="ignore", invalid="ignore"):
            return a.with_values(fn(a.frame["value"], float(b)))
    if isinstance(b, TS) and isinstance(a, (int, float)):
        with np.errstate(divide="ignore", invalid="ignore"):
            return b.with_values(fn(float(a), b.frame["value"]))
    a, b = _to_scalar(ctx, a), _to_scalar(ctx, b)
    for side in (a, b):
        if isinstance(side, Scalar) and (side.status != "ok" or side.value is None):
            return Scalar.missing(side.status if side.status != "ok" else "missing_input", side.detail)
    av = a.value if isinstance(a, Scalar) else float(a)
    bv = b.value if isinstance(b, Scalar) else float(b)
    try:
        value = fn(av, bv)
    except ZeroDivisionError:
        return Scalar.missing("error", "division by zero")
    dates = [s.obs_date for s in (a, b) if isinstance(s, Scalar) and s.obs_date is not None]
    details = [s.detail for s in (a, b) if isinstance(s, Scalar) and s.detail]
    if value is None or not math.isfinite(value):
        return Scalar.missing("error", "non-finite result")
    return Scalar(float(value), max(dates) if dates else None, detail="; ".join(details))


def _cacheable(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
            if sub.func.id in SCALAR_FUNCS or sub.func.id in VINTAGE_FUNCS:
                return False
    return True


def evaluate_node(node: ast.AST, ctx: Context) -> Any:
    if isinstance(node, ast.Expression):
        return evaluate_node(node.body, ctx)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp):
        operand = evaluate_node(node.operand, ctx)
        if isinstance(node.op, ast.UAdd):
            return operand
        return _binop(ctx, ast.Mult(), operand, -1.0) if not isinstance(operand, (int, float)) else -operand
    if isinstance(node, ast.BinOp):
        cache_key = None
        if ctx.fast and _cacheable(node):
            cache_key = ast.dump(node)
            if cache_key in ctx.shared_cache:
                return ctx.shared_cache[cache_key]
        result = _binop(ctx, node.op, evaluate_node(node.left, ctx), evaluate_node(node.right, ctx))
        if cache_key is not None and isinstance(result, TS):
            ctx.shared_cache[cache_key] = result
        return result
    if isinstance(node, ast.Call):
        name = node.func.id  # type: ignore[attr-defined]
        if name == "S":
            return ctx.base(node.args[0].value)  # type: ignore[attr-defined]
        if name in VINTAGE_FUNCS:
            return VINTAGE_FUNCS[name](ctx, *node.args)
        cache_key = None
        if name in SERIES_FUNCS:
            store = ctx.shared_cache if ctx.fast else ctx.cache
            cache_key = ast.dump(node)
            if cache_key in store:
                return store[cache_key]
        args = [evaluate_node(arg, ctx) for arg in node.args]
        kwargs = {kw.arg: evaluate_node(kw.value, ctx) for kw in node.keywords}
        if name in SERIES_FUNCS:
            result = SERIES_FUNCS[name](ctx, *args, **kwargs)
            store[cache_key] = result
            return result
        return SCALAR_FUNCS[name](ctx, *args, **kwargs)
    raise FormulaError(f"unsupported node {type(node).__name__}")


def evaluate(formula: Formula | str, ctx: Context) -> Scalar:
    if isinstance(formula, str):
        formula = parse(formula)
    try:
        result = evaluate_node(formula.tree, ctx)
    except MissingSeries as error:
        return Scalar.missing("missing_input", f"series {error.args[0]} not loaded")
    except FormulaError:
        raise
    except Exception as error:  # noqa: BLE001 - surface as a status, never crash the batch
        return Scalar.missing("error", f"{type(error).__name__}: {error}"[:300])
    if isinstance(result, TS):
        return f_latest(ctx, result)
    if isinstance(result, (int, float)):
        return Scalar(float(result))
    return result
