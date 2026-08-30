from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal


CapabilityStatus = Literal[
    "available",
    "failed",
    "not_configured",
    "unavailable_licensed",
    "not_applicable",
]
MatchMode = Literal["all", "any", "contains_any"]


@dataclass(frozen=True)
class EvidenceRule:
    filename: str
    identity_column: str
    identities: tuple[str, ...]
    match: MatchMode = "all"


@dataclass(frozen=True)
class CapabilitySpec:
    capability_id: str
    module: str
    label: str
    proxy: bool
    available_reason: str
    evidence: EvidenceRule | None = None
    provider: str | None = None
    static_status: CapabilityStatus | None = None


def _data(
    capability_id: str,
    module: str,
    label: str,
    filename: str,
    identity_column: str,
    identities: tuple[str, ...],
    *,
    match: MatchMode = "all",
    proxy: bool = False,
    provider: str | None = None,
) -> CapabilitySpec:
    description = "公开代理" if proxy else "正式周数据"
    return CapabilitySpec(
        capability_id=capability_id,
        module=module,
        label=label,
        proxy=proxy,
        available_reason=f"{description}已通过目标周截止日与来源验证。",
        evidence=EvidenceRule(filename, identity_column, identities, match),
        provider=provider,
    )


def _static(
    capability_id: str,
    module: str,
    label: str,
    status: CapabilityStatus,
    reason: str,
) -> CapabilitySpec:
    return CapabilitySpec(
        capability_id=capability_id,
        module=module,
        label=label,
        proxy=False,
        available_reason=reason,
        static_status=status,
    )


CAPABILITY_SPECS = (
    _data("liquidity.fed_balance_sheet", "Liquidity", "Fed Balance Sheet", "liquidity.csv", "series_code", ("FED_TOTAL_ASSETS",)),
    _data("liquidity.tga", "Liquidity", "TGA", "liquidity.csv", "series_code", ("TGA_BALANCE",)),
    _data("liquidity.on_rrp", "Liquidity", "ON RRP", "liquidity.csv", "series_code", ("ON_RRP_TAKE_UP",)),
    _data("liquidity.net_liquidity", "Liquidity", "Fed BS − TGA − RRP", "liquidity.csv", "series_code", ("FED_NET_LIQUIDITY",)),
    _data("rates.ust_curve", "Rates", "UST 2Y / 5Y / 10Y / 30Y", "fixed_income.csv", "series_code", ("UST2Y", "UST5Y", "UST10Y", "UST30Y")),
    _data("rates.curve_spreads", "Rates", "2s10s / 5s30s", "fixed_income.csv", "series_code", ("UST10Y2Y", "UST30Y5Y")),
    _data("rates.real_yields", "Rates", "TIPS Real Yield", "fixed_income.csv", "series_code", ("UST_REAL5Y", "UST_REAL10Y")),
    _data("rates.breakeven_inflation", "Rates", "Breakeven Inflation", "fixed_income.csv", "series_code", ("US_BE5Y", "US_BE10Y", "US_5Y5Y")),
    _data("rates.fed_funds_sofr", "Rates", "Fed Funds / SOFR", "money_market.csv", "series_code", ("US_EFFR", "US_SOFR")),
    _data("macro.public_actuals", "Macro", "CPI / PCE / Payroll / GDP / Retail Sales", "economic_releases.csv", "indicator_code", ("CPI_INDEX_NSA", "CORE_CPI_INDEX_NSA", "PCE_PRICE_INDEX_YOY_PCT", "CORE_PCE_PRICE_INDEX_YOY_PCT", "NFP_CHANGE", "UNEMPLOYMENT_RATE", "REAL_GDP_QOQ_SAAR", "RETAIL_SALES_MOM"), match="any"),
    _data("macro.cpi", "Macro", "BLS CPI", "economic_releases.csv", "indicator_code", ("CPI_INDEX_NSA", "CORE_CPI_INDEX_NSA")),
    _data("macro.employment", "Macro", "BLS Employment", "economic_releases.csv", "indicator_code", ("NFP_CHANGE",)),
    _data("macro.wages", "Macro", "BLS Average Hourly Earnings", "economic_releases.csv", "indicator_code", ("AVERAGE_HOURLY_EARNINGS", "AVERAGE_HOURLY_EARNINGS_MOM_PCT", "AVERAGE_HOURLY_EARNINGS_YOY_PCT")),
    _data("macro.unemployment", "Macro", "BLS Unemployment", "economic_releases.csv", "indicator_code", ("UNEMPLOYMENT_RATE",)),
    _data("macro.gdp", "Macro", "BEA Real GDP", "economic_releases.csv", "indicator_code", ("REAL_GDP_QOQ_SAAR", "REAL_GDP_YOY_PCT")),
    _data("macro.pce_inflation", "Macro", "BEA PCE Inflation", "economic_releases.csv", "indicator_code", ("PCE_PRICE_INDEX_YOY_PCT", "CORE_PCE_PRICE_INDEX_YOY_PCT")),
    _data("macro.personal_income", "Macro", "BEA Personal Income", "economic_releases.csv", "indicator_code", ("PERSONAL_INCOME_MOM_PCT", "DISPOSABLE_PERSONAL_INCOME_MOM_PCT")),
    _data("macro.personal_spending", "Macro", "BEA Personal Spending", "economic_releases.csv", "indicator_code", ("PERSONAL_CONSUMPTION_EXPENDITURES_MOM_PCT",)),
    _data("macro.retail_sales", "Macro", "Census Retail Sales", "economic_releases.csv", "indicator_code", ("RETAIL_SALES_MOM", "RETAIL_SALES_YOY_PCT")),
    _data("macro.housing", "Macro", "Census Housing", "economic_releases.csv", "indicator_code", ("HOUSING_PERMITS_SAAR", "HOUSING_STARTS_SAAR", "HOUSING_COMPLETIONS_SAAR")),
    _data("macro.durable_goods", "Macro", "Census Durable Goods", "economic_releases.csv", "indicator_code", ("DURABLE_GOODS_NEW_ORDERS_MOM", "DURABLE_GOODS_NEW_ORDERS_EX_TRANSPORTATION_MOM", "DURABLE_GOODS_NEW_ORDERS_EX_DEFENSE_MOM")),
    _data("macro.surprise_proxy", "Macro", "Actual-data momentum proxy (not Citi Surprise)", "economic_releases.csv", "indicator_code", ("CORE_CPI_MOMENTUM_GAP_PROXY", "CORE_PCE_PRICE_INDEX_MOMENTUM_GAP_PROXY"), match="any", proxy=True),
    _data("positioning.cftc_cot", "Positioning", "CFTC COT", "positioning_flows.csv", "metric_code", ("SP500_COT_asset_manager_net", "SP500_COT_leveraged_fund_net", "GOLD_COT_managed_money_net"), match="any", provider="cftc_tff"),
    _data("positioning.cftc_percentile", "Positioning", "CFTC Net Position %ile", "positioning_flows.csv", "metric_code", ("SP500_COT_asset_manager_percentile", "SP500_COT_leveraged_fund_percentile", "GOLD_COT_managed_money_percentile"), match="any", provider="cftc_tff"),
    _static("positioning.cta", "Positioning", "CTA Positioning", "unavailable_licensed", "CTA positioning is proprietary bank-model data and requires a licensed source."),
    _static("positioning.dealer_gamma", "Positioning", "Dealer Gamma Exposure", "unavailable_licensed", "Defensible dealer-gamma history requires licensed option-chain data and a model; no value is published."),
    _data("volatility.vix", "Volatility", "VIX", "financial_conditions.csv", "metric_code", ("vix_1m_level",), provider="yahoo_volatility_signals"),
    _static("volatility.vvix", "Volatility", "VVIX", "not_configured", "No stable redistribution-safe historical acquisition path is configured."),
    _data("volatility.vix_term_structure", "Volatility", "VIX Term Structure", "financial_conditions.csv", "metric_code", ("vix_1m_3m_spread", "vix_1m_3m_ratio", "vix_9d_1m_spread"), provider="yahoo_volatility_signals", proxy=True),
    _static("volatility.put_call_ratio", "Volatility", "Put/Call Ratio", "not_configured", "No stable exchange-history acquisition path is configured for formal weekly publication."),
    _static("volatility.move", "Volatility", "MOVE", "unavailable_licensed", "Complete MOVE history and redistribution are license-restricted; no substitute value is published."),
    _data("credit.hy_oas", "Credit", "HY OAS", "fixed_income.csv", "series_code", ("USHY_OAS",)),
    _data("credit.ig_oas", "Credit", "IG OAS", "fixed_income.csv", "series_code", ("USIG_OAS",)),
    _data("credit.hy_ig_spread", "Credit", "HY–IG Spread", "fixed_income.csv", "series_code", ("USHY_IG_OAS",)),
    _static("credit.cdx", "Credit", "CDX IG / HY", "unavailable_licensed", "Reliable CDX history requires a licensed index-data source."),
    _data("internals.above_20dma", "Market Internals", "% > 20DMA", "market_internals.csv", "metric_code", ("us_sector_etf_proxy_pct_above_20d_ma",), proxy=True, provider="yahoo_market_state"),
    _data("internals.above_50dma", "Market Internals", "% > 50DMA", "market_internals.csv", "metric_code", ("us_sector_etf_proxy_pct_above_50d_ma",), proxy=True, provider="yahoo_market_state"),
    _data("internals.above_200dma", "Market Internals", "% > 200DMA", "market_internals.csv", "metric_code", ("us_sector_etf_proxy_pct_above_200d_ma",), proxy=True, provider="yahoo_market_state"),
    _data("internals.advance_decline", "Market Internals", "Advance / Decline", "market_internals.csv", "metric_code", ("us_sector_etf_proxy_advance_decline_ratio", "us_sector_etf_proxy_net_advances"), proxy=True, provider="yahoo_market_state"),
    _data("internals.new_high_low", "Market Internals", "New High / New Low", "market_internals.csv", "metric_code", ("us_sector_etf_proxy_new_highs", "us_sector_etf_proxy_new_lows"), proxy=True, provider="yahoo_market_state"),
    _data("internals.equal_cap_weight", "Market Internals", "Equal Weight vs Cap Weight", "market_internals.csv", "metric_code", ("rsp_spy_relative_return_5d", "rsp_spy_relative_return_20d"), match="any", proxy=True, provider="yahoo_market_state"),
    _data("fund_flow.etf_implied_flow", "Fund Flow", "ETF implied flow", "fund_flows.csv", "metric_code", ("ivv_implied_flow",), proxy=True, provider="ishares_ivv_fund"),
    _data("fund_flow.etf_aum", "Fund Flow", "ETF AUM", "fund_flows.csv", "metric_code", ("ivv_net_assets",), provider="ishares_ivv_fund"),
    _static("fund_flow.epfr", "Fund Flow", "EPFR global fund flows", "unavailable_licensed", "EPFR fund-flow data requires a commercial license."),
    _static("fund_flow.mutual_fund", "Fund Flow", "Mutual fund comprehensive flows", "unavailable_licensed", "Comprehensive mutual-fund flow coverage requires a licensed database."),
    _data("china_flow.southbound", "China/HK Flow", "港股通南向", "fund_flows.csv", "metric_code", ("hkex_southbound_net_buy",), provider="hkex_stock_connect_flows"),
    _static("china_flow.northbound", "China/HK Flow", "沪深港通北向相关数据", "not_applicable", "The integrated official daily-statistics definition does not provide the required northbound net-flow measure; it is not inferred."),
    _data("earnings.reported_eps", "Earnings", "Reported EPS", "company_fundamentals.csv", "metric_code", ("diluted_eps_ttm",), provider="sec_company_fundamentals"),
    _data("earnings.revenue_margin_fcf", "Earnings", "Revenue / Margin / FCF", "company_fundamentals.csv", "metric_code", ("revenue_ttm", "operating_margin_ttm", "free_cash_flow_ttm"), provider="sec_company_fundamentals"),
    _static("earnings.beat_miss", "Earnings", "Earnings Beat/Miss", "unavailable_licensed", "Beat/miss requires point-in-time consensus estimates; no consensus value is fabricated."),
    _static("earnings.forward_eps_consensus", "Earnings", "Forward EPS Consensus", "unavailable_licensed", "Forward EPS consensus requires a licensed estimates database."),
    _static("earnings.eps_revision_breadth", "Earnings", "EPS Revision Breadth", "unavailable_licensed", "Standard EPS revision breadth requires licensed point-in-time estimates."),
    _static("earnings.sales_revision_breadth", "Earnings", "Sales Revision Breadth", "unavailable_licensed", "Standard sales revision breadth requires licensed point-in-time estimates."),
    _data("earnings.guidance_proxy", "Earnings", "Guidance Trend Proxy", "company_fundamentals.csv", "metric_code", ("guidance_direction_proxy",), proxy=True, provider="sec_guidance_proxy"),
    _data("fundamentals.sec_filings", "Fundamentals", "SEC 10-K / 10-Q / 8-K", "company_events.csv", "form", ("10-K", "10-Q", "8-K"), match="any", provider="sec_company_events"),
    _data("fundamentals.xbrl_company_facts", "Fundamentals", "XBRL Company Facts", "company_fundamentals.csv", "metric_code", ("revenue", "revenue_ttm"), match="any", provider="sec_company_fundamentals"),
    _data("valuation.trailing_pe", "Valuation", "Trailing P/E", "company_fundamentals.csv", "metric_code", ("trailing_pe",), provider="sec_company_fundamentals"),
    _data("valuation.price_to_book", "Valuation", "P/B", "company_fundamentals.csv", "metric_code", ("price_to_book",), provider="sec_company_fundamentals"),
    _data("valuation.ev_ebitda", "Valuation", "EV/EBITDA", "company_fundamentals.csv", "metric_code", ("ev_to_ebitda",), provider="sec_company_fundamentals"),
    _static("valuation.forward_pe", "Valuation", "Forward P/E", "unavailable_licensed", "Accurate forward P/E requires licensed consensus estimates."),
    _data("valuation.historical_percentiles", "Valuation", "Historical Valuation Percentile", "company_fundamentals.csv", "metric_code", ("trailing_pe_percentile", "price_to_book_percentile", "price_to_sales_percentile", "ev_to_ebitda_percentile"), match="any", proxy=True, provider="sec_company_fundamentals"),
    _data("cross_asset.stock_bond", "Cross Asset", "Stock–Bond Correlation", "cross_asset.csv", "series_code", ("US_STOCK_BOND_CORR_13W", "US_STOCK_BOND_CORR_26W"), match="any", proxy=True),
    _data("cross_asset.equity_usd", "Cross Asset", "Equity–USD Correlation", "cross_asset.csv", "series_code", ("EQUITY_USD_CORR_13W", "EQUITY_USD_CORR_26W"), match="any", proxy=True),
    _data("cross_asset.gold_real_yield", "Cross Asset", "Gold–Real Yield", "cross_asset.csv", "series_code", ("GOLD_REAL_YIELD_CORR_13W", "GOLD_REAL_YIELD_CORR_26W"), match="any", proxy=True),
    _data("cross_asset.oil_breakeven", "Cross Asset", "Oil–Breakeven", "cross_asset.csv", "series_code", ("OIL_BREAKEVEN_CORR_13W", "OIL_BREAKEVEN_CORR_26W"), match="any", proxy=True),
    _data("commodities.gold_oil_copper", "Commodities", "Gold / Oil / Copper", "commodities.csv", "series_code", ("COMEX_GOLD", "WTI", "COMEX_COPPER"), proxy=True),
    _data("fx.dxy", "FX", "DXY", "foreign_exchange.csv", "series_code", ("DXY",), proxy=True),
    _data("fx.major", "FX", "Major FX", "foreign_exchange.csv", "series_code", ("EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CAD", "USD_CHF"), proxy=True),
    _data("events.fomc", "Events", "FOMC Calendar", "events.csv", "event_name", ("FOMC", "Federal Open Market Committee"), match="contains_any"),
    _data("events.fomc_decisions", "Events", "FOMC Policy Decisions", "events.csv", "event_type", ("fomc_policy_decision",)),
    _data("events.economic_calendar", "Events", "Economic Calendar", "events.csv", "event_type", ("macro_release",)),
    _data("events.earnings_calendar", "Events", "Confirmed Earnings Calendar", "company_events.csv", "event_type", ("earnings_release",), provider="sec_company_events"),
    _data("capital_markets.ipo_filings", "Capital Markets", "IPO filings / filing activity proxy", "capital_markets.csv", "event_type", ("ipo_registration_filing", "ipo_prospectus_filing", "ipo_filing_count_proxy"), match="any", proxy=True, provider="sec_capital_markets"),
    _static("capital_markets.ipo_issuance_volume", "Capital Markets", "IPO issuance volume", "not_configured", "Public filing counts are available, but completed issuance volume and proceeds are not yet aggregated; filing counts are not relabeled as issuance."),
    _data("capital_markets.ma_announcements", "Capital Markets", "M&A announcements proxy", "capital_markets.csv", "event_type", ("ma_filing_announcement",), proxy=True, provider="sec_capital_markets"),
    _static("capital_markets.ecm_dcm", "Capital Markets", "ECM/DCM aggregate volume", "unavailable_licensed", "High-quality aggregate ECM/DCM volume requires a licensed transactions database."),
    _static("alternative.google_trends", "Alternative", "Google Trends", "not_configured", "No stable official or auditable local-research acquisition path was approved at implementation time; no value is published."),
    _static("alternative.app_downloads", "Alternative", "App downloads", "unavailable_licensed", "Defensible app-download history requires a licensed measurement provider."),
    _static("alternative.web_traffic", "Alternative", "Complete web traffic", "unavailable_licensed", "Complete comparable web-traffic history requires a licensed measurement provider."),
)


def _find_unique_file(root: Path, filename: str) -> Path | None:
    candidates = [
        directory / filename
        for directory in root.iterdir()
        if directory.is_dir()
        and not directory.is_symlink()
        and directory.name.startswith("capital_weekly_")
        and (directory / filename).is_file()
        and not (directory / filename).is_symlink()
    ]
    return candidates[0] if len(candidates) == 1 else None


def _read_rows(path: Path | None) -> list[dict[str, str]]:
    if path is None:
        return []
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file, strict=True))


def _eligible_by_cutoff(row: dict[str, str], target_end: date) -> bool:
    if row.get("qc_flag") not in {None, "", "OK"}:
        return False
    for column in (
        "latest_date",
        "as_of_date",
        "observation_date",
        "event_date",
        "report_date",
        "known_as_of",
    ):
        raw = str(row.get(column) or "").strip()
        if not raw:
            continue
        try:
            observed = date.fromisoformat(raw[:10])
        except ValueError:
            return False
        if observed > target_end:
            return False
    return True


def _matches(rule: EvidenceRule, rows: list[dict[str, str]]) -> bool:
    values = {
        str(row.get(rule.identity_column) or "").strip()
        for row in rows
    }
    if rule.match == "all":
        return set(rule.identities).issubset(values)
    if rule.match == "any":
        return bool(set(rule.identities) & values)
    lowered = tuple(identity.lower() for identity in rule.identities)
    return any(
        any(identity in value.lower() for identity in lowered)
        for value in values
    )


def _provider_statuses(root: Path) -> dict[str, str]:
    source_log = _find_unique_file(root, "source_log.csv")
    return {
        str(row.get("provider") or "").strip(): str(row.get("status") or "").strip()
        for row in _read_rows(source_log)
        if str(row.get("provider") or "").strip()
    }


def _missing_status(spec: CapabilitySpec, provider_status: str | None) -> tuple[str, str]:
    if provider_status == "NOT_CONFIGURED":
        return (
            "not_configured",
            f"Registered provider {spec.provider} reported NOT_CONFIGURED; no business value is published.",
        )
    if provider_status == "UNAVAILABLE_LICENSED":
        return (
            "unavailable_licensed",
            f"Registered provider {spec.provider} reported UNAVAILABLE_LICENSED; no substitute value is published.",
        )
    if provider_status:
        return (
            "failed",
            f"Registered evidence is unavailable; provider {spec.provider} reported {provider_status}.",
        )
    return (
        "failed",
        "Registered output does not contain an eligible evidence row by the target Sunday.",
    )


def build_capability_manifest(release_root: Path, target_end: date) -> list[dict]:
    root = Path(release_root)
    provider_statuses = _provider_statuses(root)
    capabilities = []
    for spec in CAPABILITY_SPECS:
        evidence_files: list[str] = []
        if spec.static_status is not None:
            status = spec.static_status
            reason = spec.available_reason
        else:
            rule = spec.evidence
            if rule is None:
                raise ValueError(f"Capability {spec.capability_id} has no evidence rule")
            path = _find_unique_file(root, rule.filename)
            rows = [
                row
                for row in _read_rows(path)
                if _eligible_by_cutoff(row, target_end)
            ]
            if path is not None and _matches(rule, rows):
                status = "available"
                reason = spec.available_reason
                evidence_files = [path.relative_to(root).as_posix()]
            else:
                status, reason = _missing_status(
                    spec,
                    provider_statuses.get(spec.provider) if spec.provider else None,
                )
        capabilities.append(
            {
                "capability_id": spec.capability_id,
                "module": spec.module,
                "label": spec.label,
                "status": status,
                "reason": reason,
                "proxy": spec.proxy,
                "evidence_files": evidence_files,
            }
        )
    return capabilities
