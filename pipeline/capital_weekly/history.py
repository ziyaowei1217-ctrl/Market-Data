from __future__ import annotations

from datetime import date

import pandas as pd


def truncate_history_as_of(
    history: pd.DataFrame,
    as_of_date: date | None,
) -> pd.DataFrame:
    attributes = dict(history.attrs)
    if as_of_date is None:
        result = history.copy()
    else:
        normalized_dates = pd.to_datetime(history["date"], errors="raise").dt.date
        result = history.loc[normalized_dates <= as_of_date].copy()
    result.attrs.update(attributes)
    return result
