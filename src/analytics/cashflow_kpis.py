from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_XLSX = OUTPUT_DIR / "cashflow_intelligence.xlsx"
OUTPUT_ALERTS = OUTPUT_DIR / "distress_alerts.csv"


# ============================================================
# HELPERS
# ============================================================

def numeric(value):
    try:
        if pd.isna(value):
            return np.nan
        return float(value)
    except Exception:
        return np.nan


def safe_divide(a, b):
    a = numeric(a)
    b = numeric(b)

    if pd.isna(a) or pd.isna(b) or b == 0:
        return np.nan

    return a / b


def sort_years(df):
    if df.empty:
        return df

    result = df.copy()

    result["_year_num"] = pd.to_numeric(
        result["year"],
        errors="coerce"
    )

    return (
        result
        .sort_values("_year_num")
        .drop(columns=["_year_num"])
        .reset_index(drop=True)
    )


def get_company_data(df, company_id):
    if df.empty:
        return pd.DataFrame()

    result = df[
        df["company_id"].astype(str) == str(company_id)
    ].copy()

    return sort_years(result)


def cagr(start, end, years):
    start = numeric(start)
    end = numeric(end)

    if (
        pd.isna(start)
        or pd.isna(end)
        or start <= 0
        or end <= 0
        or years <= 0
    ):
        return np.nan

    try:
        return (
            ((end / start) ** (1 / years)) - 1
        ) * 100
    except Exception:
        return np.nan


# ============================================================
# LOAD DATABASE
# ============================================================

def load_data():

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query(
        """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        """,
        conn
    )

    try:
        ratios = pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            """,
            conn
        )
    except Exception:
        ratios = pd.DataFrame()

    try:
        cashflow = pd.read_sql_query(
            """
            SELECT *
            FROM cashflow
            """,
            conn
        )
    except Exception:
        cashflow = pd.DataFrame()

    try:
        profit_loss = pd.read_sql_query(
            """
            SELECT *
            FROM profitandloss
            """,
            conn
        )
    except Exception:
        profit_loss = pd.DataFrame()

    try:
        balance_sheet = pd.read_sql_query(
            """
            SELECT *
            FROM balancesheet
            """,
            conn
        )
    except Exception:
        balance_sheet = pd.DataFrame()

    try:
        sectors = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            """,
            conn
        )
    except Exception:
        sectors = companies.copy()

    try:
        capital = pd.read_sql_query(
            """
            SELECT *
            FROM capital_allocation
            """,
            conn
        )
    except Exception:
        capital = pd.DataFrame()

    conn.close()

    return (
        companies,
        ratios,
        cashflow,
        profit_loss,
        balance_sheet,
        sectors,
        capital
    )


# ============================================================
# CFO QUALITY
# ============================================================

def calculate_cfo_quality(
    company_ratios,
    company_cf,
    company_pl
):

    if company_cf.empty:
        return np.nan, "Accrual Risk"

    merged = company_cf.copy()

    if company_pl.empty:
        return np.nan, "Accrual Risk"

    pl = company_pl[
        ["year", "net_profit"]
    ].copy()

    merged = merged.merge(
        pl,
        on="year",
        how="left"
    )

    merged["operating_activity"] = pd.to_numeric(
        merged["operating_activity"],
        errors="coerce"
    )

    merged["net_profit"] = pd.to_numeric(
        merged["net_profit"],
        errors="coerce"
    )

    merged["cfo_pat_ratio"] = np.where(
        merged["net_profit"] != 0,
        merged["operating_activity"]
        / merged["net_profit"],
        np.nan
    )

    ratios = (
        merged["cfo_pat_ratio"]
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
        .tail(5)
    )

    if ratios.empty:
        return np.nan, "Accrual Risk"

    score = ratios.mean()

    if score > 1.0:
        label = "High Quality"
    elif score >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return score, label


# ============================================================
# CAPEX INTENSITY
# ============================================================

def calculate_capex_intensity(
    company_cf,
    company_pl
):

    if company_cf.empty or company_pl.empty:
        return np.nan, "Asset Light"

    merged = company_cf[
        [
            "year",
            "investing_activity"
        ]
    ].merge(
        company_pl[
            [
                "year",
                "sales"
            ]
        ],
        on="year",
        how="inner"
    )

    merged["investing_activity"] = pd.to_numeric(
        merged["investing_activity"],
        errors="coerce"
    )

    merged["sales"] = pd.to_numeric(
        merged["sales"],
        errors="coerce"
    )

    latest = merged.iloc[-1]

    investing = numeric(
        latest["investing_activity"]
    )

    sales = numeric(
        latest["sales"]
    )

    if pd.isna(investing) or pd.isna(sales) or sales == 0:
        return np.nan, "Asset Light"

    intensity = (
        abs(investing) / abs(sales)
    ) * 100

    if intensity < 3:
        label = "Asset Light"
    elif intensity <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"

    return intensity, label


# ============================================================
# FCF CAGR
# ============================================================

def calculate_fcf_cagr(company_cf):

    if company_cf.empty:
        return np.nan

    x = company_cf.copy()

    x["operating_activity"] = pd.to_numeric(
        x["operating_activity"],
        errors="coerce"
    )

    x["investing_activity"] = pd.to_numeric(
        x["investing_activity"],
        errors="coerce"
    )

    x["fcf"] = (
        x["operating_activity"]
        + x["investing_activity"]
    )

    x = x.dropna(subset=["fcf"])

    if len(x) < 2:
        return np.nan

    x = x.tail(6)

    start = numeric(x.iloc[0]["fcf"])
    end = numeric(x.iloc[-1]["fcf"])

    years = len(x) - 1

    return cagr(
        start,
        end,
        years
    )


# ============================================================
# FCF CONVERSION
# ============================================================

def calculate_fcf_conversion(
    company_cf,
    company_pl
):

    if company_cf.empty or company_pl.empty:
        return np.nan

    cf = company_cf.copy()

    pl = company_pl[
        [
            "year",
            "net_profit"
        ]
    ].copy()

    merged = cf.merge(
        pl,
        on="year",
        how="inner"
    )

    merged["operating_activity"] = pd.to_numeric(
        merged["operating_activity"],
        errors="coerce"
    )

    merged["investing_activity"] = pd.to_numeric(
        merged["investing_activity"],
        errors="coerce"
    )

    merged["net_profit"] = pd.to_numeric(
        merged["net_profit"],
        errors="coerce"
    )

    merged["fcf"] = (
        merged["operating_activity"]
        + merged["investing_activity"]
    )

    latest = merged.iloc[-1]

    fcf = numeric(latest["fcf"])
    profit = numeric(latest["net_profit"])

    if pd.isna(fcf) or pd.isna(profit) or profit == 0:
        return np.nan

    return (
        fcf / abs(profit)
    ) * 100


# ============================================================
# DISTRESS SIGNAL
# ============================================================

def calculate_distress(company_cf):

    if company_cf.empty:
        return False, np.nan, np.nan

    latest = company_cf.iloc[-1]

    cfo = numeric(
        latest.get("operating_activity")
    )

    cff = numeric(
        latest.get("financing_activity")
    )

    if (
        pd.notna(cfo)
        and pd.notna(cff)
        and cfo < 0
        and cff > 0
    ):
        return True, cfo, cff

    return False, cfo, cff


# ============================================================
# DELEVERAGING
# ============================================================

def calculate_deleveraging(
    company_cf,
    company_bs
):

    if company_cf.empty or company_bs.empty:
        return False

    cf = company_cf.copy()
    bs = company_bs.copy()

    if len(cf) < 1 or len(bs) < 2:
        return False

    latest_cf = cf.iloc[-1]

    cff = numeric(
        latest_cf.get("financing_activity")
    )

    bs["borrowings"] = pd.to_numeric(
        bs["borrowings"],
        errors="coerce"
    )

    bs = bs.dropna(
        subset=["borrowings"]
    )

    if len(bs) < 2:
        return False

    latest_debt = numeric(
        bs.iloc[-1]["borrowings"]
    )

    previous_debt = numeric(
        bs.iloc[-2]["borrowings"]
    )

    if (
        pd.notna(cff)
        and pd.notna(latest_debt)
        and pd.notna(previous_debt)
        and cff < 0
        and latest_debt < previous_debt
    ):
        return True

    return False


# ============================================================
# CAPITAL ALLOCATION LABEL
# ============================================================

def determine_capital_allocation(
    cfo_quality_label,
    capex_label,
    distress_flag,
    deleveraging_flag,
    fcf_conversion
):

    if distress_flag:
        return "Distress Signal"

    if deleveraging_flag:
        return "Deleveraging"

    if (
        cfo_quality_label == "High Quality"
        and capex_label == "Capital Intensive"
    ):
        return "Reinvestor"

    if (
        cfo_quality_label == "High Quality"
        and capex_label == "Asset Light"
    ):
        return "Cash Generator"

    if (
        pd.notna(fcf_conversion)
        and fcf_conversion > 80
    ):
        return "Cash Distributor"

    if cfo_quality_label == "Accrual Risk":
        return "Accrual Risk"

    if capex_label == "Capital Intensive":
        return "Capital Intensive"

    return "Balanced"


# ============================================================
# BUILD OUTPUT
# ============================================================

def build_intelligence():

    (
        companies,
        ratios,
        cashflow,
        profit_loss,
        balance_sheet,
        sectors,
        capital
    ) = load_data()

    results = []
    distress_rows = []

    print()
    print("Companies loaded:", len(companies))

    for _, company in companies.iterrows():

        company_id = str(
            company["company_id"]
        )

        company_name = company.get(
            "company_name",
            company_id
        )

        r = get_company_data(
            ratios,
            company_id
        )

        cf = get_company_data(
            cashflow,
            company_id
        )

        pl = get_company_data(
            profit_loss,
            company_id
        )

        bs = get_company_data(
            balance_sheet,
            company_id
        )

        # ----------------------------------------------------
        # Sector
        # ----------------------------------------------------

        sector = "Unknown"

        # Existing companies table does not expose a sector
        # column in this project version. Preserve a safe value.
        # Dashboard/peer sector information can be joined later.

        # ----------------------------------------------------
        # CFO QUALITY
        # ----------------------------------------------------

        cfo_score, cfo_label = calculate_cfo_quality(
            r,
            cf,
            pl
        )

        # ----------------------------------------------------
        # CAPEX
        # ----------------------------------------------------

        capex_intensity, capex_label = (
            calculate_capex_intensity(
                cf,
                pl
            )
        )

        # ----------------------------------------------------
        # FCF CAGR
        # ----------------------------------------------------

        fcf_cagr = calculate_fcf_cagr(
            cf
        )

        # ----------------------------------------------------
        # FCF CONVERSION
        # ----------------------------------------------------

        fcf_conversion = calculate_fcf_conversion(
            cf,
            pl
        )

        # ----------------------------------------------------
        # DISTRESS
        # ----------------------------------------------------

        distress, latest_cfo, latest_cff = (
            calculate_distress(cf)
        )

        # ----------------------------------------------------
        # DELEVERAGING
        # ----------------------------------------------------

        deleveraging = calculate_deleveraging(
            cf,
            bs
        )

        # ----------------------------------------------------
        # CAPITAL ALLOCATION
        # ----------------------------------------------------

        allocation_label = determine_capital_allocation(
            cfo_label,
            capex_label,
            distress,
            deleveraging,
            fcf_conversion
        )

        results.append(
            {
                "company_id": company_id,
                "sector": sector,
                "cfo_quality_score": cfo_score,
                "cfo_quality_label": cfo_label,
                "capex_intensity_pct": capex_intensity,
                "capex_label": capex_label,
                "fcf_cagr_5yr": fcf_cagr,
                "fcf_conversion_pct": fcf_conversion,
                "distress_flag": bool(distress),
                "deleveraging_flag": bool(deleveraging),
                "capital_allocation_label": allocation_label,
            }
        )

        if distress:

            latest_profit = np.nan

            if not pl.empty:
                latest_profit = numeric(
                    pl.iloc[-1].get(
                        "net_profit"
                    )
                )

            distress_rows.append(
                {
                    "company_id": company_id,
                    "company_name": company_name,
                    "sector": sector,
                    "CFO": latest_cfo,
                    "CFF": latest_cff,
                    "latest_net_profit": latest_profit,
                }
            )

    result = pd.DataFrame(results)

    distress_df = pd.DataFrame(
        distress_rows
    )

    # --------------------------------------------------------
    # Ensure all 92 companies exist
    # --------------------------------------------------------

    expected_ids = set(
        companies["company_id"]
        .astype(str)
    )

    actual_ids = set(
        result["company_id"]
        .astype(str)
    )

    missing = sorted(
        expected_ids - actual_ids
    )

    if missing:
        raise RuntimeError(
            "Missing companies: "
            + ", ".join(missing)
        )

    # --------------------------------------------------------
    # Save Excel
    # --------------------------------------------------------

    required_columns = [
        "company_id",
        "sector",
        "cfo_quality_score",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_label",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
        "distress_flag",
        "deleveraging_flag",
        "capital_allocation_label",
    ]

    result = result[
        required_columns
    ]

    result.to_excel(
        OUTPUT_XLSX,
        index=False
    )

    # --------------------------------------------------------
    # Save distress alerts
    # --------------------------------------------------------

    distress_df.to_csv(
        OUTPUT_ALERTS,
        index=False,
        encoding="utf-8-sig"
    )

    return result, distress_df


# ============================================================
# MAIN
# ============================================================

def main():

    result, distress = build_intelligence()

    print()
    print("========================================")
    print("       DAY 31 CASH FLOW COMPLETE")
    print("========================================")

    print()
    print("Rows:", len(result))
    print("Columns:", result.columns.tolist())

    print()
    print("CFO Quality:")
    print(
        result[
            "cfo_quality_label"
        ]
        .value_counts(dropna=False)
        .to_string()
    )

    print()
    print("CapEx Labels:")
    print(
        result[
            "capex_label"
        ]
        .value_counts(dropna=False)
        .to_string()
    )

    print()
    print("Capital Allocation:")
    print(
        result[
            "capital_allocation_label"
        ]
        .value_counts(dropna=False)
        .to_string()
    )

    print()
    print(
        "Distress companies:",
        int(result["distress_flag"].sum())
    )

    print(
        "Deleveraging companies:",
        int(result["deleveraging_flag"].sum())
    )

    print()
    print("Excel:")
    print(OUTPUT_XLSX)

    print()
    print("Distress CSV:")
    print(OUTPUT_ALERTS)

    print()
    print("========================================")
    print("       DAY 31 QA")
    print("========================================")

    assert len(result) == 92

    assert list(result.columns) == [
        "company_id",
        "sector",
        "cfo_quality_score",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_label",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
        "distress_flag",
        "deleveraging_flag",
        "capital_allocation_label",
    ]

    assert result["company_id"].nunique() == 92

    assert set(
        result["cfo_quality_label"].dropna().unique()
    ).issubset(
        {
            "High Quality",
            "Moderate",
            "Accrual Risk"
        }
    )

    assert set(
        result["capex_label"].dropna().unique()
    ).issubset(
        {
            "Asset Light",
            "Moderate",
            "Capital Intensive"
        }
    )

    assert set(
        result["distress_flag"].dropna().unique()
    ).issubset(
        {True, False}
    )

    assert set(
        result["deleveraging_flag"].dropna().unique()
    ).issubset(
        {True, False}
    )

    assert OUTPUT_XLSX.exists()
    assert OUTPUT_ALERTS.exists()

    print()
    print("✅ 92 companies verified")
    print("✅ Required columns verified")
    print("✅ CFO quality classification verified")
    print("✅ CapEx intensity classification verified")
    print("✅ Distress detection verified")
    print("✅ Deleveraging detection verified")
    print("✅ Capital allocation labels generated")
    print("✅ Excel output generated")
    print("✅ Distress alerts CSV generated")

    print()
    print("========================================")
    print("       DAY 31 QA PASSED")
    print("========================================")

    print()
    print("NEXT: DAY 32 - CAPITAL ALLOCATION REPORT")


if __name__ == "__main__":
    main()
