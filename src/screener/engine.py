import re
import sqlite3
from pathlib import Path

import pandas as pd
import yaml

DB_PATH = Path("db/nifty100.db")
CONFIG_PATH = Path("config/screener_config.yaml")


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(CONFIG_PATH)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def year_sort_value(value):
    if value is None:
        return -1

    text = str(value).strip().upper()

    if text == "TTM":
        return 999999

    match = re.search(r"(19|20)\d{2}", text)

    if not match:
        return -1

    year = int(match.group())

    months = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }

    month = 0

    for name, number in months.items():
        if name in text:
            month = number
            break

    return year * 100 + month


def latest_per_company(df, year_column="year"):
    if df.empty:
        return df

    result = df.copy()

    result["_sort_year"] = result[year_column].apply(year_sort_value)

    result = (
        result.sort_values(["company_id", "_sort_year"], ascending=[True, False])
        .drop_duplicates(subset=["company_id"], keep="first")
        .drop(columns=["_sort_year"])
        .reset_index(drop=True)
    )

    return result


def load_financial_data():
    """
    Load latest available financial ratio + P&L data
    for every company.
    """

    conn = sqlite3.connect(DB_PATH)

    try:

        ratio_query = """
        SELECT
            fr.company_id,
            fr.year,
            fr.net_profit_margin_pct,
            fr.operating_profit_margin_pct,
            fr.return_on_equity_pct,
            fr.debt_to_equity,
            fr.interest_coverage,
            fr.asset_turnover,
            fr.free_cash_flow_cr,
            fr.earnings_per_share,
            fr.revenue_cagr_5yr,
            fr.pat_cagr_5yr,
            fr.eps_cagr_5yr,
            fr.composite_quality_score,
            fr.book_value_per_share,
            fr.dividend_payout_ratio_pct,
            fr.total_debt_cr,
            fr.cash_from_operations_cr
        FROM financial_ratios fr
        """

        df = pd.read_sql_query(ratio_query, conn)

        # Latest P&L per company.
        pnl_query = """
        SELECT
            company_id,
            year,
            sales,
            net_profit
        FROM profitandloss
        """

        pnl = pd.read_sql_query(pnl_query, conn)

        pnl = latest_per_company(pnl)

        # Latest market data per company.
        market_query = """
        SELECT
            company_id,
            year,
            market_cap_crore,
            pe_ratio,
            pb_ratio,
            dividend_yield_pct
        FROM market_cap
        """

        market = pd.read_sql_query(market_query, conn)

        market = latest_per_company(market)

        # Latest sector per company.
        sector_query = """
        SELECT
            company_id,
            MAX(broad_sector) AS broad_sector
        FROM sectors
        GROUP BY company_id
        """

        sectors = pd.read_sql_query(sector_query, conn)

    finally:
        conn.close()

    # Latest financial ratio row per company.
    df = latest_per_company(df)

    # Join latest P&L.
    df = df.merge(
        pnl[["company_id", "sales", "net_profit"]], on="company_id", how="left"
    )

    # Join latest market data.
    df = df.merge(
        market[
            [
                "company_id",
                "market_cap_crore",
                "pe_ratio",
                "pb_ratio",
                "dividend_yield_pct",
            ]
        ],
        on="company_id",
        how="left",
    )

    # Join sectors.
    df = df.merge(sectors, on="company_id", how="left")

    # Friendly column names.
    df = df.rename(
        columns={
            "market_cap_crore": "market_cap",
            "pe_ratio": "pe",
            "pb_ratio": "pb",
            "dividend_yield_pct": "dividend_yield",
        }
    )

    numeric_columns = [
        c
        for c in df.columns
        if c
        not in {
            "company_id",
            "year",
            "broad_sector",
        }
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df.reset_index(drop=True)


def load_historical_data():
    """
    Historical data for 3-year revenue CAGR and
    year-over-year D/E decline.
    """

    conn = sqlite3.connect(DB_PATH)

    try:

        query = """
        SELECT
            fr.company_id,
            fr.year,
            fr.debt_to_equity,
            pl.sales,
            fr.free_cash_flow_cr
        FROM financial_ratios fr
        LEFT JOIN profitandloss pl
            ON fr.company_id = pl.company_id
            AND fr.year = pl.year
        """

        df = pd.read_sql_query(query, conn)

    finally:
        conn.close()

    df["_sort_year"] = df["year"].apply(year_sort_value)

    return df.sort_values(["company_id", "_sort_year"]).reset_index(drop=True)


def calculate_revenue_cagr_3yr(historical):
    results = {}

    for company_id, group in historical.groupby("company_id"):

        group = group.sort_values("_sort_year")

        group = group[group["sales"].notna()]

        if len(group) < 4:
            continue

        latest = group.iloc[-1]

        candidates = group[group["_sort_year"] <= latest["_sort_year"] - 300]

        if candidates.empty:
            continue

        start = candidates.iloc[-1]

        start_value = start["sales"]
        end_value = latest["sales"]

        if (
            pd.isna(start_value)
            or pd.isna(end_value)
            or start_value <= 0
            or end_value <= 0
        ):
            continue

        results[company_id] = (((end_value / start_value) ** (1 / 3)) - 1) * 100

    return results


def calculate_debt_decline(historical):
    results = {}

    for company_id, group in historical.groupby("company_id"):

        group = group.sort_values("_sort_year")

        group = group[group["debt_to_equity"].notna()]

        if len(group) < 2:
            results[company_id] = False
            continue

        latest = float(group.iloc[-1]["debt_to_equity"])

        previous = float(group.iloc[-2]["debt_to_equity"])

        results[company_id] = latest < previous

    return results


def add_turnaround_metrics(df):
    historical = load_historical_data()

    revenue_cagr_3yr = calculate_revenue_cagr_3yr(historical)

    debt_declining = calculate_debt_decline(historical)

    result = df.copy()

    result["revenue_cagr_3yr"] = result["company_id"].map(revenue_cagr_3yr)

    result["debt_to_equity_declining"] = (
        result["company_id"].map(debt_declining).fillna(False)
    )

    return result


def prepare_icr(df):
    result = df.copy()

    result["icr_screen_value"] = pd.to_numeric(
        result["interest_coverage"], errors="coerce"
    )

    # Debt-free companies are treated as infinite ICR.
    result.loc[result["icr_screen_value"].isna(), "icr_screen_value"] = float("inf")

    return result


def apply_filter(df, name, threshold):

    if threshold is None:
        return df

    # ICR.
    if name == "icr_min":

        return df[df["icr_screen_value"] >= float(threshold)]

    # Debt declining.
    if name == "debt_to_equity_declining":

        if bool(threshold):

            return df[df["debt_to_equity_declining"] == True]

        return df

    column_map = {
        "roe_min": "return_on_equity_pct",
        "debt_to_equity_max": "debt_to_equity",
        "fcf_min": "free_cash_flow_cr",
        "revenue_cagr_3yr_min": "revenue_cagr_3yr",
        "revenue_cagr_5yr_min": "revenue_cagr_5yr",
        "pat_cagr_5yr_min": "pat_cagr_5yr",
        "opm_min": "operating_profit_margin_pct",
        "pe_max": "pe",
        "pb_max": "pb",
        "dividend_yield_min": "dividend_yield",
        "dividend_payout_ratio_max": "dividend_payout_ratio_pct",
        "market_cap_min": "market_cap",
        "net_profit_min": "net_profit",
        "eps_cagr_min": "eps_cagr_5yr",
        "asset_turnover_min": "asset_turnover",
        "sales_min": "sales",
    }

    column = column_map.get(name)

    if column is None:
        return df

    if column not in df.columns:
        return df

    values = pd.to_numeric(df[column], errors="coerce")

    if name.endswith("_min"):

        return df[values >= float(threshold)]

    if name.endswith("_max"):

        return df[values <= float(threshold)]

    return df


def apply_filters(df, filters):

    result = prepare_icr(df.copy())

    for name, threshold in filters.items():

        if threshold is None:
            continue

        # Financials D/E carve-out.
        if name == "debt_to_equity_max":

            financials_mask = (
                result["broad_sector"].fillna("").astype(str).str.strip().str.lower()
                == "financials"
            )

            financials = result[financials_mask]

            non_financials = result[~financials_mask]

            non_financials = apply_filter(non_financials, name, threshold)

            result = pd.concat([financials, non_financials], ignore_index=True)

        else:

            result = apply_filter(result, name, threshold)

    # Composite score descending.
    if "composite_quality_score" in result.columns:

        result = result.sort_values(
            "composite_quality_score", ascending=False, na_position="last"
        )

    return result.reset_index(drop=True)


def run_screener(filters=None, preset=None):

    config = load_config()

    df = load_financial_data()

    df = add_turnaround_metrics(df)

    if preset is not None:

        presets = config.get("presets", {})

        if preset not in presets:

            raise ValueError(f"Unknown preset: {preset}")

        filters = presets[preset]

    if filters is None:

        filters = config.get("filters", {})

    return apply_filters(df, filters)


def run_all_presets():

    config = load_config()

    results = {}

    for preset in config.get("presets", {}):

        results[preset] = run_screener(preset=preset)

    return results


if __name__ == "__main__":

    print("=" * 70)
    print("DAY 16 — 6 PRESET SCREENERS")
    print("=" * 70)

    data = load_financial_data()

    print()
    print("Latest company universe:", len(data))

    print("Unique companies:", data["company_id"].nunique())

    print("Market data available:", data["pe"].notna().sum())

    print()

    results = run_all_presets()

    for name, result in results.items():

        print(f"{name:25s} : " f"{len(result):3d} companies")

    print()
    print("✅ DAY 16 ENGINE COMPLETE")
