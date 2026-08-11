from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

CASHFLOW_XLSX = OUTPUT_DIR / "cashflow_intelligence.xlsx"
CAPITAL_CSV = OUTPUT_DIR / "capital_allocation.csv"
DISTRIBUTION_CSV = OUTPUT_DIR / "capital_allocation_distribution.csv"
PATTERN_CHANGES_CSV = OUTPUT_DIR / "pattern_changes.csv"


def get_connection():
    return sqlite3.connect(str(DB_PATH))


def load_companies():
    conn = get_connection()

    try:
        return pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            ORDER BY id
            """,
            conn
        )
    finally:
        conn.close()


def load_cashflow_intelligence():
    if not CASHFLOW_XLSX.exists():
        raise FileNotFoundError(
            f"Missing {CASHFLOW_XLSX}"
        )

    return pd.read_excel(CASHFLOW_XLSX)


def load_financial_ratios():
    conn = get_connection()

    try:
        return pd.read_sql_query(
            """
            SELECT *
            FROM financial_ratios
            ORDER BY company_id, year
            """,
            conn
        )
    finally:
        conn.close()


def determine_pattern(row):
    distress = bool(row.get("distress_flag", False))
    deleveraging = bool(row.get("deleveraging_flag", False))

    cfo_quality = row.get("cfo_quality_label")
    capex_label = row.get("capex_label")
    fcf_conversion = row.get("fcf_conversion_pct")

    if distress:
        return "Distress Signal"

    if deleveraging:
        return "Deleveraging"

    if (
        cfo_quality == "High Quality"
        and capex_label == "Capital Intensive"
    ):
        return "Reinvestor"

    if (
        cfo_quality == "High Quality"
        and capex_label == "Asset Light"
    ):
        return "Cash Generator"

    if (
        pd.notna(fcf_conversion)
        and fcf_conversion > 80
    ):
        return "Cash Distributor"

    if cfo_quality == "Accrual Risk":
        return "Accrual Risk"

    if capex_label == "Capital Intensive":
        return "Capital Intensive"

    return "Balanced"


def build_current_allocation():
    intelligence = load_cashflow_intelligence()
    companies = load_companies()

    df = intelligence.copy()

    df["capital_allocation_label"] = df.apply(
        determine_pattern,
        axis=1
    )

    result = df.merge(
        companies,
        on="company_id",
        how="left"
    )

    preferred_columns = [
        "company_id",
        "company_name",
        "sector",
        "capital_allocation_label",
        "cfo_quality_label",
        "cfo_quality_score",
        "capex_label",
        "capex_intensity_pct",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
        "distress_flag",
        "deleveraging_flag",
    ]

    columns = [
        c for c in preferred_columns
        if c in result.columns
    ]

    result = result[columns]

    result = result.sort_values(
        "company_id"
    ).reset_index(drop=True)

    return result


def build_distribution(result):
    distribution = (
        result[
            "capital_allocation_label"
        ]
        .value_counts()
        .rename_axis("capital_allocation_label")
        .reset_index(name="company_count")
    )

    distribution["percentage"] = (
        distribution["company_count"]
        / len(result)
        * 100
    ).round(2)

    distribution = distribution.sort_values(
        "capital_allocation_label"
    ).reset_index(drop=True)

    return distribution


def build_pattern_changes():
    ratios = load_financial_ratios()

    if ratios.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "previous_year",
                "previous_pattern",
                "latest_year",
                "latest_pattern",
            ]
        )

    ratios["year"] = ratios["year"].astype(str)

    required = [
        "company_id",
        "year",
        "debt_to_equity",
        "free_cash_flow_cr",
        "capex_cr",
        "cash_from_operations_cr",
    ]

    available = [
        c for c in required
        if c in ratios.columns
    ]

    ratios = ratios[available].copy()

    rows = []

    for company_id, group in ratios.groupby(
        "company_id"
    ):
        group = group.copy()

        def numeric(column):
            if column not in group.columns:
                return pd.Series(
                    np.nan,
                    index=group.index
                )
            return pd.to_numeric(
                group[column],
                errors="coerce"
            )

        group["debt_to_equity"] = numeric(
            "debt_to_equity"
        )
        group["free_cash_flow_cr"] = numeric(
            "free_cash_flow_cr"
        )
        group["capex_cr"] = numeric(
            "capex_cr"
        )
        group["cash_from_operations_cr"] = numeric(
            "cash_from_operations_cr"
        )

        group = group.sort_values("year")

        if len(group) < 2:
            continue

        previous = group.iloc[-2]
        latest = group.iloc[-1]

        previous_cfo = previous[
            "cash_from_operations_cr"
        ]

        latest_cfo = latest[
            "cash_from_operations_cr"
        ]

        previous_fcf = previous[
            "free_cash_flow_cr"
        ]

        latest_fcf = latest[
            "free_cash_flow_cr"
        ]

        previous_de = previous[
            "debt_to_equity"
        ]

        latest_de = latest[
            "debt_to_equity"
        ]

        previous_pattern = "Balanced"
        latest_pattern = "Balanced"

        if (
            pd.notna(latest_cfo)
            and latest_cfo < 0
            and pd.notna(previous_cfo)
            and previous_cfo >= 0
        ):
            latest_pattern = "Distress Signal"

        elif (
            pd.notna(previous_de)
            and pd.notna(latest_de)
            and latest_de < previous_de
        ):
            latest_pattern = "Deleveraging"

        elif (
            pd.notna(latest_fcf)
            and latest_fcf > 0
        ):
            latest_pattern = "Cash Generator"

        if (
            pd.notna(previous_cfo)
            and previous_cfo < 0
        ):
            previous_pattern = "Distress Signal"

        elif (
            pd.notna(previous_de)
            and previous_de > 0
        ):
            previous_pattern = "Deleveraging"

        elif (
            pd.notna(previous_fcf)
            and previous_fcf > 0
        ):
            previous_pattern = "Cash Generator"

        if previous_pattern != latest_pattern:
            rows.append(
                {
                    "company_id": company_id,
                    "previous_year": previous["year"],
                    "previous_pattern": previous_pattern,
                    "latest_year": latest["year"],
                    "latest_pattern": latest_pattern,
                }
            )

    return pd.DataFrame(rows)


def main():
    print("Loading Day 31 cash flow intelligence...")

    result = build_current_allocation()

    print()
    print("Companies:", len(result))

    if len(result) != 92:
        raise ValueError(
            f"Expected 92 companies, found {len(result)}"
        )

    if result["company_id"].nunique() != 92:
        raise ValueError(
            "Company IDs are not unique."
        )

    result.to_csv(
        CAPITAL_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    distribution = build_distribution(
        result
    )

    distribution.to_csv(
        DISTRIBUTION_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    changes = build_pattern_changes()

    changes.to_csv(
        PATTERN_CHANGES_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    # Update the Day 31 Excel with the
    # final Day 32 allocation column.
    if CASHFLOW_XLSX.exists():
        original = pd.read_excel(
            CASHFLOW_XLSX
        )

        allocation = result[
            [
                "company_id",
                "capital_allocation_label"
            ]
        ]

        original = original.drop(
            columns=[
                "capital_allocation_label"
            ],
            errors="ignore"
        )

        original = original.merge(
            allocation,
            on="company_id",
            how="left"
        )

        original.to_excel(
            CASHFLOW_XLSX,
            index=False
        )

    print()
    print("========================================")
    print("       DAY 32 COMPLETE")
    print("========================================")

    print()
    print("Capital Allocation Distribution:")
    print(
        distribution.to_string(
            index=False
        )
    )

    print()
    print(
        "Pattern changes detected:",
        len(changes)
    )

    print()
    print("Capital Allocation CSV:")
    print(CAPITAL_CSV)

    print()
    print("Distribution CSV:")
    print(DISTRIBUTION_CSV)

    print()
    print("Pattern Changes CSV:")
    print(PATTERN_CHANGES_CSV)

    print()
    print("========================================")
    print("       DAY 32 QA")
    print("========================================")

    assert len(result) == 92
    assert result["company_id"].nunique() == 92

    valid_patterns = {
        "Reinvestor",
        "Deleveraging",
        "Distress Signal",
        "Balanced",
        "Cash Distributor",
        "Cash Generator",
        "Accrual Risk",
        "Capital Intensive",
    }

    assert set(
        result["capital_allocation_label"]
        .dropna()
        .unique()
    ).issubset(valid_patterns)

    assert distribution["company_count"].sum() == 92

    assert CAPITAL_CSV.exists()
    assert DISTRIBUTION_CSV.exists()
    assert PATTERN_CHANGES_CSV.exists()

    print()
    print("PASS - 92 companies verified")
    print("PASS - 8 capital allocation patterns supported")
    print("PASS - distribution generated")
    print("PASS - year-over-year pattern changes generated")
    print("PASS - cashflow_intelligence.xlsx updated")
    print("PASS - capital_allocation.csv generated")
    print("PASS - capital_allocation_distribution.csv generated")
    print("PASS - pattern_changes.csv generated")

    print()
    print("========================================")
    print("       DAY 32 QA PASSED")
    print("========================================")

    print()
    print("NEXT: DAY 33 - PDF TEARSHEET TEMPLATE")


if __name__ == "__main__":
    main()
