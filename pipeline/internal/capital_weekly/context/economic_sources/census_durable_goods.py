from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlparse

from ..economic_releases import build_release_row
from ..provider_contracts import (
    ContextProvider,
    HONG_KONG,
    ProviderResult,
    ProviderSpec,
    target_sunday_cutoff,
)
from .census_release_common import (
    SOURCE,
    latest_release,
    month_period,
    release_timestamp,
    require_census_pdf,
    signed,
    space,
)


CENSUS_DURABLE_RELEASES = (
    "https://www.census.gov/manufacturing/m3/adv/historical_data/index.html"
)
DURABLE_PATH = "/manufacturing/m3/"


def parse_durable_goods_release(
    text: str, source_url: str, as_of_date: date
) -> list[dict]:
    source_period = _source_period(source_url)
    normalized = space(text)
    released = release_timestamp(normalized)
    if released.astimezone(HONG_KONG) > target_sunday_cutoff(as_of_date):
        return []
    titles = re.findall(
        r"MONTHLY ADVANCE REPORT ON DURABLE GOODS MANUFACTURERS['’] "
        r"SHIPMENTS, INVENTORIES AND ORDERS,?\s*([A-Z]+\s+\d{4})",
        normalized,
        flags=re.IGNORECASE,
    )
    if len(titles) != 1 or (period := month_period(titles[0])) is None:
        raise ValueError(
            "Census durable-goods release requires one observation-month title"
        )
    if source_period != period:
        raise ValueError(
            "Census durable-goods filename conflicts with the PDF observation period"
        )
    headline_matches = list(
        re.finditer(
            r"New orders for manufactured durable goods in ([A-Za-z]+).*?"
            r"(increased|decreased) \$[\d,.]+ billion or ([\d.]+) percent "
            r"to \$[\d,.]+ billion",
            normalized,
            flags=re.IGNORECASE,
        )
    )
    if len(headline_matches) != 1:
        raise ValueError("Census durable-goods release requires exactly one headline")
    headline = headline_matches[0]
    observed_month, direction, raw_value = headline.groups()
    if not period.endswith(f"-{_month_number(observed_month):02d}"):
        raise ValueError(
            "Census durable-goods headline month conflicts with release title"
        )
    new_orders_section = re.split(
        r"\s+Shipments\s+",
        normalized[headline.start() :],
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    prior = re.findall(
        r"This followed an? ([\d.]+) percent ([A-Za-z]+) (increase|decrease)",
        new_orders_section,
        flags=re.IGNORECASE,
    )
    if len(prior) != 1:
        raise ValueError("Census durable-goods release requires one prior-month change")
    prior_value, prior_month, prior_direction = prior[0]
    if _month_number(prior_month) != _previous_month_number(period):
        raise ValueError(
            "Census durable-goods prior change must describe the previous month"
        )
    exclusions = {}
    for label, code in (
        ("transportation", "DURABLE_GOODS_NEW_ORDERS_EX_TRANSPORTATION_MOM"),
        ("defense", "DURABLE_GOODS_NEW_ORDERS_EX_DEFENSE_MOM"),
    ):
        matches = re.findall(
            rf"Excluding {label}, new orders (increased|decreased) ([\d.]+) percent",
            new_orders_section,
            flags=re.IGNORECASE,
        )
        if len(matches) != 1:
            raise ValueError(
                f"Census durable-goods release requires one ex-{label} change"
            )
        exclusions[code] = signed(matches[0][0], matches[0][1])

    common = {
        "release_at_bjt": released.astimezone(HONG_KONG).isoformat(),
        "observation_period": period,
        "unit": "percent",
        "frequency": "monthly",
        "seasonal_adjustment": "seasonally adjusted",
        "source": SOURCE,
        "source_url": source_url,
        "known_as_of": released.isoformat(),
        "vintage_date": released.date().isoformat(),
        "as_of_date": as_of_date,
    }
    rows = [
        build_release_row(
            indicator_code="DURABLE_GOODS_NEW_ORDERS_MOM",
            indicator_name="Durable goods new orders MoM",
            value=signed(direction, raw_value),
            previous_value=signed(prior_direction, prior_value),
            **common,
        )
    ]
    names = {
        "DURABLE_GOODS_NEW_ORDERS_EX_TRANSPORTATION_MOM": (
            "Durable goods new orders ex transportation MoM"
        ),
        "DURABLE_GOODS_NEW_ORDERS_EX_DEFENSE_MOM": (
            "Durable goods new orders ex defense MoM"
        ),
    }
    rows.extend(
        build_release_row(
            indicator_code=code,
            indicator_name=names[code],
            value=value,
            **common,
        )
        for code, value in exclusions.items()
    )
    return rows


def build_census_durable_goods_provider(
    start: date, end: date, session
) -> ContextProvider:
    if end < start:
        raise ValueError("Report end must not precede start")

    def fetch() -> ProviderResult:
        rows, content, selected_url = latest_release(
            session,
            index_url=CENSUS_DURABLE_RELEASES,
            path_fragment=DURABLE_PATH,
            description="durable-goods",
            as_of_date=end,
            parser=parse_durable_goods_release,
        )
        required = {
            "DURABLE_GOODS_NEW_ORDERS_MOM",
            "DURABLE_GOODS_NEW_ORDERS_EX_TRANSPORTATION_MOM",
            "DURABLE_GOODS_NEW_ORDERS_EX_DEFENSE_MOM",
        }
        if {str(row["indicator_code"]) for row in rows} != required:
            raise ValueError("Archived Census durable-goods provider is incomplete")
        return ProviderResult(
            category="economic_releases",
            rows=rows,
            raw_text=content,
            source=SOURCE,
            source_url=CENSUS_DURABLE_RELEASES,
            notes=f"selected artifact: {selected_url}",
        )

    return ContextProvider(
        spec=ProviderSpec(
            name="census_durable_goods",
            category="economic_releases",
            source_tier="public",
            requiredness="required",
            provider_version="1.0.0",
            schema_version="economic-release-v1",
            frequency="monthly",
            freshness_days=60,
        ),
        fetch=fetch,
    )


def _month_number(value: str) -> int:
    period = month_period(f"{value} 2000")
    if period is None:
        raise ValueError(f"Unsupported Census durable-goods month: {value}")
    return int(period[-2:])


def _previous_month_number(period: str) -> int:
    month = int(period[-2:])
    return 12 if month == 1 else month - 1


def _source_period(source_url: str) -> str:
    require_census_pdf(
        source_url,
        path_fragment=DURABLE_PATH,
        description="durable-goods",
    )
    match = re.fullmatch(
        r"/manufacturing/m3/historical_data/pressreleases/adv/"
        r"(\d{4})/([a-z]{3})(\d{2})adv\.pdf",
        urlparse(source_url).path,
        flags=re.IGNORECASE,
    )
    if match is None or int(match.group(1)) % 100 != int(match.group(3)):
        raise ValueError(
            "Census durable-goods archive filename is not release-specific"
        )
    period = month_period(f"{match.group(2)} {match.group(1)}")
    if period is None:
        raise ValueError(
            "Census durable-goods archive filename has an invalid month"
        )
    return period


__all__ = [
    "CENSUS_DURABLE_RELEASES",
    "build_census_durable_goods_provider",
    "parse_durable_goods_release",
]
