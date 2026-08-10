from __future__ import annotations

import pandas as pd


HORIZONS = (
    ("daily", "daily_change", "单日"),
    ("weekly", "weekly_change", "本周"),
    ("mtd", "mtd_change", "本月以来"),
    ("ytd", "ytd_change", "年初以来"),
)

GROUP_NAMES_CN = {
    "sovereign_curve": "主权收益率与曲线",
    "policy_money_market": "政策及货币市场利率",
    "credit_spreads": "信用利差",
    "commodities": "商品",
    "policy_rates": "政策利率",
    "money_market": "货币市场利率",
    "foreign_exchange": "外汇",
}


def _valid_mask(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame["qc_flag"].eq("OK") & frame[column].notna()


def add_macro_ranks(detail: pd.DataFrame) -> pd.DataFrame:
    ranked = detail.copy()
    for horizon, column, _ in HORIZONS:
        ranked[f"{horizon}_rank"] = (
            ranked[column]
            .where(_valid_mask(ranked, column))
            .groupby(ranked["group"], sort=False)
            .rank(method="dense", ascending=False, na_option="keep")
            .astype("Int64")
        )
    return ranked


def _format_change(value: float, unit: str) -> str:
    if unit == "pct":
        return f"{value:+.2%}" if value else "0.00%"
    return f"{value:+.2f}{unit}" if value else f"0.00{unit}"


def _format_magnitude(value: float, unit: str) -> str:
    magnitude = abs(value)
    if unit == "pct":
        return f"{magnitude:.2%}"
    return f"{magnitude:.2f}{unit}"


def _format_movers(rows: pd.DataFrame, unit: str) -> str:
    return "; ".join(
        f"{row.name_cn} {_format_change(row.change, unit)}"
        for row in rows.itertuples(index=False)
    )


def _direction_phrase(group: str, level_unit: str, value: float) -> str:
    if value == 0:
        return "持平"
    positive = value > 0
    if group == "commodities":
        return "商品上涨" if positive else "商品下跌"
    if group == "credit_spreads":
        return "信用利差走阔" if positive else "信用利差收窄"
    if group == "policy_money_market":
        return "利率上行" if positive else "利率下行"
    if group == "policy_rates":
        return "政策收紧、政策利率上调" if positive else "政策宽松、政策利率下调"
    if group == "money_market":
        return "资金利率上行、政策传导趋紧" if positive else "资金利率下行、政策传导趋松"
    if group == "foreign_exchange":
        return "汇率上涨" if positive else "汇率下跌"
    if group == "sovereign_curve" and level_unit == "percentage_points":
        return "曲线走陡" if positive else "曲线趋平"
    return "收益率上行" if positive else "收益率下行"


def _commentary(group: str, period_cn: str, rows: pd.DataFrame, unit: str) -> str:
    movements = "；".join(
        f"{row.name_cn}（{_direction_phrase(group, row.level_unit, row.change)}）"
        f"{_format_magnitude(row.change, unit)}"
        for row in rows.itertuples(index=False)
    )
    return f"{GROUP_NAMES_CN.get(group, group)}{period_cn}：{movements}。"


def _summary_row(group: str, horizon: str, column: str, period_cn: str,
                 group_frame: pd.DataFrame) -> dict[str, object]:
    columns = [
        "asset_class", "series_code", "name_cn", "level_unit", "change_unit", column
    ]
    valid = group_frame.loc[_valid_mask(group_frame, column), columns].copy()
    valid = valid.rename(columns={column: "change"})
    valid = valid.sort_values(
        ["change", "series_code"], ascending=[False, True], kind="stable"
    )
    valid_count = len(valid)
    base = {
        "asset_class": group_frame["asset_class"].iloc[0],
        "group": group,
        "group_cn": GROUP_NAMES_CN.get(group, group),
        "horizon": horizon,
        "horizon_cn": period_cn,
        "change_unit": group_frame["change_unit"].iloc[0],
        "valid_count": valid_count,
    }
    if valid_count < 2:
        return {
            **base,
            "up_count": None,
            "flat_count": None,
            "down_count": None,
            "median_change": None,
            "change_range": None,
            "dispersion": None,
            "top_movers": "",
            "bottom_movers": "",
            "commentary_cn": "",
            "qc_flag": "INSUFFICIENT_DATA",
        }

    values = valid["change"]
    bottom = valid.sort_values(
        ["change", "series_code"], ascending=[True, True], kind="stable"
    ).head(3)
    unit = str(base["change_unit"])
    return {
        **base,
        "up_count": int((values > 0).sum()),
        "flat_count": int((values == 0).sum()),
        "down_count": int((values < 0).sum()),
        "median_change": float(values.median()),
        "change_range": float(values.max() - values.min()),
        "dispersion": float(values.std(ddof=0)),
        "top_movers": _format_movers(valid.head(3), unit),
        "bottom_movers": _format_movers(bottom, unit),
        "commentary_cn": _commentary(group, period_cn, valid, unit),
        "qc_flag": "OK",
    }


def build_macro_divergence(detail: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for group, group_frame in detail.groupby("group", sort=False):
        for horizon, column, period_cn in HORIZONS:
            rows.append(_summary_row(group, horizon, column, period_cn, group_frame))
    return pd.DataFrame(rows)
