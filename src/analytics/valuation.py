import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

SUMMARY_FILE = OUTPUT_DIR / "valuation_summary.xlsx"
FLAGS_FILE = OUTPUT_DIR / "valuation_flags.csv"


# ============================================================
# DATABASE
# ============================================================


def get_connection():
    return sqlite3.connect(str(DB_PATH))


# ============================================================
# LOAD DATA
# ============================================================


def load_data():

    conn = get_connection()

    try:

        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            """,
            conn,
        )

        market_cap = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                market_cap_crore,
                pe_ratio,
                pb_ratio,
                ev_ebitda
            FROM market_cap
            """,
            conn,
        )

        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                free_cash_flow_cr
            FROM financial_ratios
            """,
            conn,
        )

        peers = pd.read_sql_query(
            """
            SELECT
                company_id,
                peer_group_name AS broad_sector
            FROM peer_groups
            """,
            conn,
        )

    finally:

        conn.close()

    return (
        companies,
        market_cap,
        ratios,
        peers,
    )


# ============================================================
# LATEST MARKET DATA
# ============================================================


def latest_market_data(market_cap):

    df = market_cap.copy()

    df["year_num"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    df = df.sort_values(["company_id", "year_num"])

    df = (
        df.groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .drop(columns=["year_num"], errors="ignore")
    )

    return df


# ============================================================
# LATEST FCF
# ============================================================


def latest_fcf(ratios):

    df = ratios.copy()

    df["year_num"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    df = df.sort_values(["company_id", "year_num"])

    df = (
        df.groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .drop(columns=["year_num"], errors="ignore")
    )

    return df[
        [
            "company_id",
            "free_cash_flow_cr",
        ]
    ]


# ============================================================
# BUILD VALUATION DATA
# ============================================================


def build_valuation():

    (
        companies,
        market_cap,
        ratios,
        peers,
    ) = load_data()

    latest_market = latest_market_data(market_cap)

    latest_cashflow = latest_fcf(ratios)

    # --------------------------------------------------------
    # Remove duplicate peer assignments
    # --------------------------------------------------------

    peers = peers.drop_duplicates(subset=["company_id"])

    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    df = companies.merge(
        peers,
        on="company_id",
        how="left",
    )

    df = df.merge(
        latest_market,
        on="company_id",
        how="left",
    )

    df = df.merge(
        latest_cashflow,
        on="company_id",
        how="left",
    )

    # --------------------------------------------------------
    # Clean sector
    # --------------------------------------------------------

    df["broad_sector"] = df["broad_sector"].fillna("Unknown")

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    numeric_columns = [
        "market_cap_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "free_cash_flow_cr",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # --------------------------------------------------------
    # FCF Yield
    # --------------------------------------------------------

    df["fcf_yield_pct"] = np.where(
        df["market_cap_crore"] > 0,
        (df["free_cash_flow_cr"] / df["market_cap_crore"]) * 100,
        np.nan,
    )

    # --------------------------------------------------------
    # Sector median P/E
    # --------------------------------------------------------

    sector_median_pe = (
        df[
            [
                "broad_sector",
                "pe_ratio",
            ]
        ]
        .dropna(subset=["pe_ratio"])
        .groupby("broad_sector")["pe_ratio"]
        .median()
        .rename("5yr_median_PE")
        .reset_index()
    )

    df = df.merge(
        sector_median_pe,
        on="broad_sector",
        how="left",
    )

    # --------------------------------------------------------
    # P/E vs sector median
    # --------------------------------------------------------

    df["PE_vs_sector_median_pct"] = np.where(
        (df["5yr_median_PE"].notna() & (df["5yr_median_PE"] != 0)),
        ((df["pe_ratio"] / df["5yr_median_PE"]) - 1) * 100,
        np.nan,
    )

    # --------------------------------------------------------
    # Valuation flag
    #
    # PE > median * 1.5 = Caution
    # PE < median * 0.7 = Discount
    # Otherwise Fair
    # --------------------------------------------------------

    def valuation_flag(row):

        pe = row["pe_ratio"]
        median = row["5yr_median_PE"]

        if pd.isna(pe) or pd.isna(median):
            return "Fair"

        if median <= 0 or pe <= 0:
            return "Fair"

        if pe > median * 1.5:
            return "Caution"

        if pe < median * 0.7:
            return "Discount"

        return "Fair"

    df["flag"] = df.apply(
        valuation_flag,
        axis=1,
    )

    # --------------------------------------------------------
    # Final columns
    # --------------------------------------------------------

    result = df[
        [
            "company_id",
            "company_name",
            "broad_sector",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "fcf_yield_pct",
            "5yr_median_PE",
            "PE_vs_sector_median_pct",
            "flag",
        ]
    ].copy()

    result = result.rename(
        columns={
            "broad_sector": "sector",
            "pe_ratio": "P/E",
            "pb_ratio": "P/B",
            "ev_ebitda": "EV/EBITDA",
        }
    )

    result = result.sort_values(
        [
            "flag",
            "company_id",
        ]
    ).reset_index(drop=True)

    return result


# ============================================================
# SAVE OUTPUTS
# ============================================================


def save_outputs():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = build_valuation()

    # --------------------------------------------------------
    # Excel
    # --------------------------------------------------------

    result.to_excel(
        SUMMARY_FILE,
        index=False,
        engine="openpyxl",
    )

    # --------------------------------------------------------
    # Flags CSV
    # --------------------------------------------------------

    flags = result[
        result["flag"].isin(
            [
                "Caution",
                "Discount",
            ]
        )
    ].copy()

    flags.to_csv(
        FLAGS_FILE,
        index=False,
    )

    print()
    print("=" * 60)
    print("DAY 26 - VALUATION MODULE")
    print("=" * 60)

    print(f"Companies: {len(result)}")

    print(f"Caution: {(result['flag'] == 'Caution').sum()}")

    print(f"Discount: {(result['flag'] == 'Discount').sum()}")

    print(f"Fair: {(result['flag'] == 'Fair').sum()}")

    print()
    print(f"Excel: {SUMMARY_FILE}")

    print(f"CSV:   {FLAGS_FILE}")

    print()
    print("Required columns:")

    print(result.columns.tolist())

    print()
    print(result.head(10).to_string(index=False))

    print()
    print("✅ DAY 26 VALUATION COMPLETE")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    save_outputs()
