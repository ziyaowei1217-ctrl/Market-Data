from __future__ import annotations

import pandas as pd


HORIZONS = (
    ("daily", "daily_change", "单日"),
    ("weekly", "weekly_change", "本周"),
    ("mtd", "mtd_change", "本月以来"),
    ("ytd", "ytd_change", "年初以来"),
)

MARKET_NAMES_CN = {"US": "美国", "China A": "A股", "HK": "港股"}


def _success_mask(frame: pd.DataFrame) -> pd.Series:
    if "qc_flag" not in frame:
        return pd.Series(True, index=frame.index)
    return frame["qc_flag"].eq("OK")


def add_return_ranks(frame: pd.DataFrame) -> pd.DataFrame:
    ranked = frame.copy()
    successful = _success_mask(ranked)
    for horizon, column, _ in HORIZONS:
        ranked[f"{horizon}_rank"] = (
            ranked[column].where(successful)
            .groupby(ranked["market"], sort=False)
            .rank(method="dense", ascending=False, na_option="keep")
            .astype("Int64")
        )
    return ranked


def _dispersion_label(spread: float) -> str:
    if spread < 0.02:
        return "较低"
    if spread < 0.05:
        return "中等"
    return "较高"


def _formatted_sectors(rows: pd.DataFrame) -> str:
    return "; ".join(
        f"{row.sector_name_cn} {row.return_value * 100:.2f}%"
        for row in rows.itertuples(index=False)
    )


def _summary_row(market: str, horizon: str, column: str, period_cn: str,
                 market_frame: pd.DataFrame) -> dict[str, object]:
    valid = market_frame.loc[
        _success_mask(market_frame) & market_frame[column].notna(),
        ["sector_name_cn", "sort_order", column],
    ].copy()
    valid = valid.rename(columns={column: "return_value"}).sort_values(
        ["return_value", "sort_order"], ascending=[False, True], kind="stable"
    )
    valid_count = len(valid)
    base = {
        "market": market,
        "market_cn": MARKET_NAMES_CN.get(market, market),
        "horizon": horizon,
        "horizon_cn": period_cn,
        "valid_count": valid_count,
    }
    if valid_count < 2:
        return {
            **base,
            "positive_count": None,
            "flat_count": None,
            "negative_count": None,
            "breadth_ratio": None,
            "leader_laggard_spread": None,
            "dispersion": None,
            "median_return": None,
            "top_3": "",
            "bottom_3": "",
            "commentary_cn": "",
            "qc_flag": "INSUFFICIENT_DATA",
        }

    values = valid["return_value"]
    positive_count = int((values > 0).sum())
    flat_count = int((values == 0).sum())
    negative_count = int((values < 0).sum())
    spread = float(values.max() - values.min())
    top = valid.head(3)
    bottom = valid.sort_values(["return_value", "sort_order"], ascending=[True, True], kind="stable").head(3)
    leader_names = "、".join(top["sector_name_cn"])
    laggard_names = "、".join(bottom["sector_name_cn"])
    commentary = (
        f"{base['market_cn']}{period_cn}由{leader_names}领涨，{laggard_names}落后；"
        f"{valid_count}个行业中{positive_count}个上涨，"
        f"首尾差{spread * 100:.1f}个百分点，分化{_dispersion_label(spread)}。"
    )
    return {
        **base,
        "positive_count": positive_count,
        "flat_count": flat_count,
        "negative_count": negative_count,
        "breadth_ratio": positive_count / valid_count,
        "leader_laggard_spread": spread,
        "dispersion": float(values.std(ddof=0)),
        "median_return": float(values.median()),
        "top_3": _formatted_sectors(top),
        "bottom_3": _formatted_sectors(bottom),
        "commentary_cn": commentary,
        "qc_flag": "OK",
    }


def build_divergence_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for market, market_frame in frame.groupby("market", sort=False):
        for horizon, column, period_cn in HORIZONS:
            rows.append(_summary_row(market, horizon, column, period_cn, market_frame))
    return pd.DataFrame(rows)
