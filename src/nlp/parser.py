import re
import sqlite3
from pathlib import Path

import pandas as pd

# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

PARSED_FILE = OUTPUT_DIR / "analysis_parsed.csv"
FAILURE_FILE = OUTPUT_DIR / "parse_failures.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Required pattern:
# 10 Years: 21%
# 5 Years: 22%
# 3 Years: 30%
#
# Allows arbitrary spaces around the text.
PATTERN = re.compile(
    r"^\s*(\d+)\s*Years?\s*:?\s*([-+]?\d+(?:\.\d+)?)\s*%\s*$",
    re.IGNORECASE,
)

FIELDS = {
    "compounded_sales_growth": "sales_growth",
    "compounded_profit_growth": "profit_growth",
    "stock_price_cagr": "stock_price_cagr",
    "roe": "roe",
}


# ============================================================
# DATABASE
# ============================================================


def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    return sqlite3.connect(str(DB_PATH))


# ============================================================
# PARSER
# ============================================================


def parse_value(text):
    if text is None:
        return None

    text = str(text).strip()

    if not text:
        return None

    match = PATTERN.match(text)

    if not match:
        return None

    period_years = int(match.group(1))
    value_pct = float(match.group(2))

    return period_years, value_pct


# ============================================================
# MAIN ENGINE
# ============================================================


def run_parser():

    conn = get_connection()

    try:
        query = """
            SELECT
                company_id,
                compounded_sales_growth,
                compounded_profit_growth,
                stock_price_cagr,
                roe
            FROM analysis
            ORDER BY company_id, id
        """

        df = pd.read_sql_query(query, conn)

    finally:
        conn.close()

    parsed_rows = []
    failure_rows = []

    for _, row in df.iterrows():

        company_id = str(row["company_id"])

        for column, metric_type in FIELDS.items():

            raw_value = row[column]

            result = parse_value(raw_value)

            if result is not None:

                period_years, value_pct = result

                parsed_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "period_years": period_years,
                        "value_pct": value_pct,
                    }
                )

            else:

                failure_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "raw_value": "" if pd.isna(raw_value) else str(raw_value),
                        "reason": "Pattern did not match N Years: X%",
                    }
                )

    parsed_df = pd.DataFrame(
        parsed_rows,
        columns=[
            "company_id",
            "metric_type",
            "period_years",
            "value_pct",
        ],
    )

    failure_df = pd.DataFrame(
        failure_rows,
        columns=[
            "company_id",
            "metric_type",
            "raw_value",
            "reason",
        ],
    )

    parsed_df.to_csv(
        PARSED_FILE,
        index=False,
        encoding="utf-8",
    )

    failure_df.to_csv(
        FAILURE_FILE,
        index=False,
        encoding="utf-8",
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 60)
    print("DAY 29 — NLP ANALYSIS TEXT PARSER")
    print("=" * 60)

    print(f"Analysis rows: {len(df)}")
    print(f"Parsed rows: {len(parsed_df)}")
    print(f"Parse failures: {len(failure_df)}")

    if not parsed_df.empty:
        print()
        print("Metrics:")
        print(parsed_df["metric_type"].value_counts().to_string())

        print()
        print("Periods:")
        print(parsed_df["period_years"].value_counts().sort_index().to_string())

    print()
    print(f"Parsed output: {PARSED_FILE}")
    print(f"Failure output: {FAILURE_FILE}")

    print()
    print("Sample parsed rows:")

    if not parsed_df.empty:
        print(parsed_df.head(10).to_string(index=False))
    else:
        print("No rows parsed.")

    print()
    print("Sample failures:")

    if not failure_df.empty:
        print(failure_df.head(10).to_string(index=False))
    else:
        print("No parse failures.")

    print()
    print("✅ DAY 29 NLP PARSER COMPLETE")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    run_parser()
