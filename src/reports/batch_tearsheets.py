import sqlite3
from pathlib import Path

import pandas as pd

from src.reports.tearsheet import generate_tearsheet

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "reports" / "tearsheets"
SKIPPED_PATH = ROOT / "output" / "skipped_tearsheets.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SKIPPED_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_companies():
    conn = sqlite3.connect(DB_PATH)

    try:
        return pd.read_sql_query(
            """
            SELECT id AS company_id, company_name
            FROM companies
            ORDER BY id
            """,
            conn,
        )
    finally:
        conn.close()


def has_enough_data(company_id):
    conn = sqlite3.connect(DB_PATH)

    try:
        counts = {}

        for table in [
            "profitandloss",
            "balancesheet",
            "cashflow",
            "financial_ratios",
        ]:
            row = conn.execute(
                f"""
                SELECT COUNT(DISTINCT year)
                FROM {table}
                WHERE company_id = ?
                """,
                [company_id],
            ).fetchone()

            counts[table] = int(row[0] or 0)

        minimum = min(counts.values())

        return minimum >= 3, counts

    finally:
        conn.close()


def main():

    companies = get_companies()

    print("========================================")
    print("       DAY 34 BATCH TEARSHEETS")
    print("========================================")
    print()
    print("Companies found:", len(companies))
    print()

    skipped = []
    generated = []
    failed = []

    for index, row in companies.iterrows():

        company_id = str(row["company_id"])
        company_name = str(row["company_name"])

        print(f"[{index + 1:02d}/{len(companies)}] " f"{company_id} - {company_name}")

        try:

            enough, counts = has_enough_data(company_id)

            if not enough:

                print("  SKIPPED - fewer than 3 years of common data")

                skipped.append(
                    {
                        "company_id": company_id,
                        "company_name": company_name,
                        "reason": "Fewer than 3 years of data",
                        **counts,
                    }
                )

                continue

            output = generate_tearsheet(company_id)

            output_path = Path(output)

            if not output_path.exists():

                # Existing function may not return a path.
                output_path = OUTPUT_DIR / f"{company_id}_tearsheet.pdf"

            if output_path.exists():

                size = output_path.stat().st_size

                generated.append(
                    {
                        "company_id": company_id,
                        "company_name": company_name,
                        "path": str(output_path),
                        "size_bytes": size,
                    }
                )

                print(f"  PASS - {size:,} bytes")

            else:

                failed.append(
                    {
                        "company_id": company_id,
                        "company_name": company_name,
                        "reason": "PDF was not created",
                    }
                )

                print("  FAIL - PDF not found")

        except Exception as exc:

            failed.append(
                {
                    "company_id": company_id,
                    "company_name": company_name,
                    "reason": str(exc),
                }
            )

            print(f"  FAIL - {type(exc).__name__}: {exc}")

    pd.DataFrame(skipped).to_csv(
        SKIPPED_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("========================================")
    print("       BATCH GENERATION COMPLETE")
    print("========================================")
    print()
    print("Generated:", len(generated))
    print("Skipped:", len(skipped))
    print("Failed:", len(failed))
    print()

    if generated:
        sizes = [x["size_bytes"] for x in generated]

        print(
            "Smallest PDF:",
            f"{min(sizes):,}",
            "bytes",
        )

        print(
            "Largest PDF:",
            f"{max(sizes):,}",
            "bytes",
        )

    if failed:

        print()
        print("FAILED COMPANIES:")

        for item in failed:
            print(
                item["company_id"],
                "-",
                item["reason"],
            )

    print()
    print("Skipped log:")
    print(SKIPPED_PATH)

    # Do not silently claim success if companies failed.
    if failed:
        raise RuntimeError(f"{len(failed)} company tearsheet(s) failed.")


if __name__ == "__main__":
    main()
