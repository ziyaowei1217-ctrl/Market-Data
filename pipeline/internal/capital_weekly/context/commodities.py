from __future__ import annotations

from ..weekly_context import ProviderResult
from .eia_commodities import calculate_weekly_change, parse_eia_series


EIA_SOURCE_URL = "https://api.eia.gov/v2/"


def eia_not_configured_result() -> ProviderResult:
    return ProviderResult(
        category="commodity_fundamentals",
        rows=[],
        raw_text="",
        source="U.S. Energy Information Administration",
        source_url=EIA_SOURCE_URL,
        status="NOT_CONFIGURED",
        notes="Set EIA_API_KEY to enable the free EIA Open Data provider.",
    )


__all__ = [
    "calculate_weekly_change",
    "eia_not_configured_result",
    "parse_eia_series",
]
