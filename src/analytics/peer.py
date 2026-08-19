import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

DB_PATH = Path("db/nifty100.db")


METRICS = {
    "roe": "return_on_equity_pct",
    "roce": "return_on_capital_employed_pct",
    "net_profit_margin": "net_profit_margin_pct",
    "debt_to_equity": "debt_to_equity",
    "free_cash_flow": "free_cash_flow_cr",
    "pat_cagr_5yr": "pat_cagr_5yr",
    "revenue_cagr_5yr": "revenue_cagr_5yr",
    "eps_cagr_5yr": "eps_cagr_5yr",
    "interest_coverage": "interest_coverage",
    "asset_turnover": "asset_turnover",
}


def get_connection():
    return sqlite3.connect(DB_PATH)


def latest_rows(df):
    """
    Keep the latest available year for each company.
    """

    if df.empty:
        return df

    result = df.copy()

    def year_value(value):
        text = str(value)

        if text.upper() == "TTM":
            return 999999

        import re

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

        upper = text.upper()

        for name, number in months.items():
            if name in upper:
                month = number
                break

        return year * 100 + month

    result["_year_sort"] = result["year"].apply(year_value)

    result = (
        result.sort_values(["company_id", "_year_sort"], ascending=[True, False])
        .drop_duplicates("company_id", keep="first")
        .drop(columns="_year_sort")
    )

    return result.reset_index(drop=True)


def find_column(columns, candidates):
    """
    Find the first matching column from a list of possible
    source column names.
    """

    normalized = {str(column).lower().replace(" ", "_"): column for column in columns}

    for candidate in candidates:

        key = candidate.lower().replace(" ", "_")

        if key in normalized:
            return normalized[key]

    return None


def calculate_roce(conn):
    """
    Calculate ROCE using:

        EBIT / (Equity + Reserves + Borrowings) * 100

    EBIT is represented by operating profit + other income,
    consistent with the Sprint 2 ratio engine.
    """

    pnl = pd.read_sql_query("SELECT * FROM profitandloss", conn)

    bs = pd.read_sql_query("SELECT * FROM balancesheet", conn)

    if pnl.empty or bs.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "year",
                "return_on_capital_employed_pct",
            ]
        )

    operating_profit_col = find_column(
        pnl.columns,
        [
            "operating_profit",
            "op_profit",
        ],
    )

    other_income_col = find_column(
        pnl.columns,
        [
            "other_income",
            "otherincome",
        ],
    )

    equity_col = find_column(
        bs.columns,
        [
            "equity_capital",
            "equity",
            "shareholders_equity",
        ],
    )

    reserves_col = find_column(
        bs.columns,
        [
            "reserves",
            "reserves_surplus",
            "reserve_surplus",
        ],
    )

    borrowings_col = find_column(
        bs.columns,
        [
            "borrowings",
            "total_borrowings",
            "debt",
            "total_debt",
        ],
    )

    if operating_profit_col is None:
        return pd.DataFrame(
            columns=[
                "company_id",
                "year",
                "return_on_capital_employed_pct",
            ]
        )

    for column in [
        other_income_col,
        equity_col,
        reserves_col,
        borrowings_col,
    ]:

        if column is None:
            continue

    pnl["operating_profit"] = pd.to_numeric(pnl[operating_profit_col], errors="coerce")

    if other_income_col:
        pnl["other_income"] = pd.to_numeric(pnl[other_income_col], errors="coerce")
    else:
        pnl["other_income"] = 0.0

    bs_temp = bs[
        [
            "company_id",
            "year",
        ]
    ].copy()

    if equity_col:
        bs_temp["equity_capital"] = pd.to_numeric(bs[equity_col], errors="coerce")
    else:
        bs_temp["equity_capital"] = 0.0

    if reserves_col:
        bs_temp["reserves"] = pd.to_numeric(bs[reserves_col], errors="coerce")
    else:
        bs_temp["reserves"] = 0.0

    if borrowings_col:
        bs_temp["borrowings"] = pd.to_numeric(bs[borrowings_col], errors="coerce")
    else:
        bs_temp["borrowings"] = 0.0

    pnl_temp = pnl[
        [
            "company_id",
            "year",
            "operating_profit",
            "other_income",
        ]
    ].copy()

    merged = pnl_temp.merge(
        bs_temp,
        on=[
            "company_id",
            "year",
        ],
        how="inner",
    )

    merged["capital_employed"] = (
        merged["equity_capital"] + merged["reserves"] + merged["borrowings"]
    )

    merged["ebit"] = merged["operating_profit"] + merged["other_income"]

    merged["return_on_capital_employed_pct"] = np.where(
        merged["capital_employed"] > 0,
        (merged["ebit"] / merged["capital_employed"]) * 100,
        np.nan,
    )

    return merged[
        [
            "company_id",
            "year",
            "return_on_capital_employed_pct",
        ]
    ]


def load_peer_data():
    conn = get_connection()

    try:

        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                net_profit_margin_pct,
                return_on_equity_pct,
                debt_to_equity,
                interest_coverage,
                asset_turnover,
                free_cash_flow_cr,
                pat_cagr_5yr,
                revenue_cagr_5yr,
                eps_cagr_5yr
            FROM financial_ratios
            """,
            conn,
        )

        peer_groups = pd.read_sql_query(
            """
            SELECT
                company_id,
                peer_group_name,
                is_benchmark
            FROM peer_groups
            """,
            conn,
        )

        roce = calculate_roce(conn)

    finally:
        conn.close()

    ratios = latest_rows(ratios)

    roce = latest_rows(roce)

    ratios = ratios.merge(
        roce[
            [
                "company_id",
                "return_on_capital_employed_pct",
            ]
        ],
        on="company_id",
        how="left",
    )

    return ratios, peer_groups


def percent_rank(series):
    """
    SQL-style PERCENT_RANK:

        (RANK - 1) / (N - 1)

    Ties receive the same rank.
    """

    values = pd.to_numeric(series, errors="coerce")

    result = pd.Series(np.nan, index=series.index, dtype=float)

    valid = values.notna()

    if valid.sum() == 0:
        return result

    if valid.sum() == 1:
        result.loc[valid] = 1.0
        return result

    ranks = values.loc[valid].rank(method="min", ascending=True)

    n = valid.sum()

    result.loc[valid] = (ranks - 1) / (n - 1)

    return result


def calculate_peer_percentiles():
    ratios, peer_groups = load_peer_data()

    if ratios.empty:
        raise RuntimeError("No financial ratio data found.")

    if peer_groups.empty:
        raise RuntimeError("No peer group assignments found.")

    merged = peer_groups.merge(ratios, on="company_id", how="left")

    output = []

    metric_definitions = [
        (
            "ROE",
            "return_on_equity_pct",
            False,
        ),
        (
            "ROCE",
            "return_on_capital_employed_pct",
            False,
        ),
        (
            "Net Profit Margin",
            "net_profit_margin_pct",
            False,
        ),
        (
            "D/E",
            "debt_to_equity",
            True,
        ),
        (
            "FCF",
            "free_cash_flow_cr",
            False,
        ),
        (
            "PAT CAGR 5yr",
            "pat_cagr_5yr",
            False,
        ),
        (
            "Revenue CAGR 5yr",
            "revenue_cagr_5yr",
            False,
        ),
        (
            "EPS CAGR 5yr",
            "eps_cagr_5yr",
            False,
        ),
        (
            "Interest Coverage",
            "interest_coverage",
            False,
        ),
        (
            "Asset Turnover",
            "asset_turnover",
            False,
        ),
    ]

    for peer_group_name, group in merged.groupby("peer_group_name", dropna=False):

        for metric_name, source_column, inverse in metric_definitions:

            values = pd.to_numeric(group[source_column], errors="coerce")

            # Debt-free companies:
            # D/E = 0, therefore they receive the highest
            # D/E percentile after inversion.
            if source_column == "debt_to_equity":
                values = values.fillna(0)

            ranks = percent_rank(values)

            if inverse:
                ranks = 1 - ranks

            for index in group.index:

                value = values.loc[index]
                percentile = ranks.loc[index]

                output.append(
                    {
                        "company_id": group.loc[index, "company_id"],
                        "peer_group_name": peer_group_name,
                        "metric": metric_name,
                        "value": None if pd.isna(value) else float(value),
                        "percentile_rank": (
                            None if pd.isna(percentile) else float(percentile)
                        ),
                        "year": group.loc[index, "year"],
                    }
                )

    result = pd.DataFrame(output)

    return result


def save_peer_percentiles(df):
    conn = get_connection()

    try:

        df.to_sql("peer_percentiles", conn, if_exists="replace", index=False)

        conn.commit()

    finally:
        conn.close()


def run_peer_engine():
    print("=" * 70)
    print("DAY 18 — PEER PERCENTILE ENGINE")
    print("=" * 70)

    peer_groups = None

    conn = get_connection()

    try:
        peer_groups = pd.read_sql_query(
            """
            SELECT
                peer_group_name,
                COUNT(DISTINCT company_id) AS companies
            FROM peer_groups
            GROUP BY peer_group_name
            ORDER BY peer_group_name
            """,
            conn,
        )
    finally:
        conn.close()

    print()
    print("Peer groups:", len(peer_groups))

    print()
    print(peer_groups.to_string(index=False))

    result = calculate_peer_percentiles()

    save_peer_percentiles(result)

    print()
    print("Percentile rows:", len(result))

    print("Companies covered:", result["company_id"].nunique())

    print("Peer groups covered:", result["peer_group_name"].nunique())

    print("Metrics covered:", result["metric"].nunique())

    conn = get_connection()

    try:

        count = conn.execute("SELECT COUNT(*) FROM peer_percentiles").fetchone()[0]

    finally:
        conn.close()

    print("SQLite rows:", count)

    print()
    print("Sample:")
    print(result.head(10).to_string(index=False))

    print()
    print("✅ DAY 18 PEER ENGINE COMPLETE")


if __name__ == "__main__":
    run_peer_engine()
