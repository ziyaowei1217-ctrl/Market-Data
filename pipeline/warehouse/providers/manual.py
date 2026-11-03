"""Hand-maintained tables in catalog/manual/*.csv (official announcements only).

Columns: ``series_key,obs_date,value,source_url,note``. One row per official announcement;
``obs_date`` is the announcement (or verification) date and dates as values are written
YYYYMMDD. A row with an empty value records that nothing has been announced yet.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Sequence

from ..db.store import Observation
from .base import FetchResult, Provider, SeriesDef, register, to_float

MANUAL_DIR = Path(__file__).resolve().parent.parent / "catalog" / "manual"


@register
class ManualTable(Provider):
    name = "MANUAL"
    batch = True

    def fetch_many(self, defs: Sequence[SeriesDef], start: date) -> list[FetchResult]:
        folder = Path(self.env.get("MANUAL_DIR") or MANUAL_DIR)
        rows: dict[str, dict[date, float]] = {}
        for path in sorted(folder.glob("*.csv")):
            with path.open(newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    value = to_float(r.get("value"))
                    if value is None:
                        continue
                    rows.setdefault(r["series_key"].strip(), {})[date.fromisoformat(r["obs_date"].strip())] = value
        out = []
        for d in defs:
            values = rows.get(d.key, {})
            obs = [Observation(k, v) for k, v in sorted(values.items()) if k >= start]
            out.append(FetchResult(d.key, obs, "ok" if obs else "empty", "" if obs else "nothing announced yet"))
        return out
