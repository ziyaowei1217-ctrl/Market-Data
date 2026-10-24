"""FactSet Earnings Insight (weekly PDF): S&P 500 earnings aggregates.

FactSet is the original publisher of these aggregates; the PDF is free. Each
issue becomes one observation per metric, dated by the issue date
(``vintage_source='report'`` semantics: obs_date = realtime_start = issue date).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Sequence

from ..db.store import Observation
from .base import FetchResult, Provider, SeriesDef, register
from .reports import BROWSER_UA, find_report_date, pdf_pages

URL = ("https://advantage.factset.com/hubfs/Website/Resources%20Section/Research%20Desk/"
       "Earnings%20Insight/EarningsInsight_{d:%m%d%y}{suffix}.pdf")

NUM = r"(-?\d+(?:\.\d+)?)"
PATTERNS: dict[str, str] = {
    "forward_pe": rf"forward 12-month P/E ratio for the S&P 500 is {NUM}",
    "eps_growth_blended": rf"blended \(year-over-year\) earnings growth rate for the S&P 500 is {NUM}%",
    "revenue_growth_blended": rf"blended revenue growth rate for the (?:first|second|third|fourth) quarter is {NUM}%",
    "net_margin_blended": rf"blended net profit margin for the S&P 500 for Q\d \d{{4}} is {NUM}%",
    "pct_reported": rf"with {NUM}% of S&P 500 companies reporting actual results",
    "pct_eps_beat": rf"{NUM}% of S&P 500 companies have reported a positive EPS surprise",
    "pct_revenue_beat": rf"{NUM}% of S&P 500 companies ha(?:s|ve) reported a positive revenue surprise",
    "eps_surprise_aggregate": rf"companies are reporting earnings that are {NUM}% above",
    "revenue_surprise_aggregate": rf"companies are reporting revenues that are {NUM}% above",
    "guidance_negative_next_q": rf"For Q\d \d{{4}}, {NUM} S&P 500 companies have issued negative EPS guidance",
    "guidance_positive_next_q": rf"have issued negative EPS guidance and {NUM} S&P 500 companies have issued positive EPS guidance",
}
CY_PATTERN = re.compile(
    rf"For CY (\d{{4}}), analysts are (?:projecting|predicting|calling for) (?:\(year-over-year\) )?earnings growth (?:rate )?of {NUM}%"
)


def parse(text: str, issue: date) -> dict[str, float]:
    flat = re.sub(r"\s+", " ", text)
    out: dict[str, float] = {}
    for metric, pattern in PATTERNS.items():
        m = re.search(pattern, flat)
        if m:
            out[metric] = float(m.group(1))
    for m in CY_PATTERN.finditer(flat):
        offset = int(m.group(1)) - issue.year
        if 0 <= offset <= 2 and f"cy_eps_growth_{offset}" not in out:
            out[f"cy_eps_growth_{offset}"] = float(m.group(2))  # 0 = current CY, 1 = next, 2 = second
    return out


@register
class FactSet(Provider):
    """code = metric name (see PATTERNS; cy_eps_growth_0/1/2). Fetches the last
    ``params.weeks`` issues (default 6); env FACTSET_BACKFILL=1 walks back to ``start``."""

    name = "FACTSET"
    batch = True

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        today = datetime.now(timezone.utc).date()
        weeks = 6 if not self.env.get("FACTSET_BACKFILL") else max(1, (today - start).days // 7 + 1)
        issues: dict[date, dict[str, float]] = {}
        for k in range(weeks):
            friday = today - timedelta(days=(today.weekday() - 4) % 7 + 7 * k)
            for d in (friday, friday - timedelta(days=1), friday + timedelta(days=1), friday - timedelta(days=2)):
                text = self._issue_text(d)
                if text:
                    issue = find_report_date(text) or d
                    issues[issue] = parse(text, issue)
                    break
        out = []
        for sd in defs:
            obs = [Observation(day, vals[sd.code], day) for day, vals in sorted(issues.items()) if sd.code in vals]
            out.append(FetchResult(sd.key, obs, "ok" if obs else "empty", f"{len(issues)} issues parsed"))
        return out

    def _issue_text(self, d: date) -> str | None:
        for suffix in ("", "A"):
            try:
                r = self.session.get(URL.format(d=d, suffix=suffix), timeout=(15, 90), headers={"User-Agent": BROWSER_UA})
            except Exception:  # noqa: BLE001
                continue
            if r.status_code == 200 and r.content[:5] == b"%PDF-":
                return "\n".join(pdf_pages(r.content)[:16])
        return None
