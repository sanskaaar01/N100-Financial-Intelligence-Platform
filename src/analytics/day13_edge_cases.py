import sqlite3
from pathlib import Path
import pandas as pd

DB = Path("db/nifty100.db")
COMPANIES = Path("data/raw/companies.xlsx")
OUTPUT = Path("data/output")
LOG = OUTPUT / "ratio_edge_cases.log"


def f(x):
    try:
        if pd.isna(x):
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def is_financials(sector):
    return str(sector).strip().lower() == "financials"


def high_leverage_flag(debt_equity, broad_sector):
    if debt_equity is None:
        return False
    if is_financials(broad_sector):
        return False
    return debt_equity > 5


def roe(net_profit, equity_capital, reserves):
    net_profit = f(net_profit)
    equity_capital = f(equity_capital)
    reserves = f(reserves)

    if None in (net_profit, equity_capital, reserves):
        return None

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return net_profit / equity * 100


def roce(operating_profit, equity_capital, reserves, borrowings):
    operating_profit = f(operating_profit)
    equity_capital = f(equity_capital)
    reserves = f(reserves)
    borrowings = f(borrowings)

    if None in (
        operating_profit,
        equity_capital,
        reserves,
        borrowings,
    ):
        return None

    capital_employed = (
        equity_capital +
        reserves +
        borrowings
    )

    if capital_employed <= 0:
        return None

    return operating_profit / capital_employed * 100


def main():

    print("=" * 70)
    print("DAY 13 — BANK ROCE CARVE-OUT & EDGE CASE LOG")
    print("=" * 70)

    OUTPUT.mkdir(parents=True, exist_ok=True)

    if not DB.exists():
        raise FileNotFoundError(DB)

    if not COMPANIES.exists():
        raise FileNotFoundError(COMPANIES)

    companies = pd.read_excel(
        COMPANIES,
        header=1
    )

    companies.columns = [
        str(c).strip().lower()
        for c in companies.columns
    ]

    required = {
        "id",
        "roce_percentage",
        "roe_percentage",
    }

    missing = required - set(companies.columns)

    if missing:
        raise ValueError(
            f"Missing columns in companies.xlsx: {missing}"
        )

    source = {}

    for _, row in companies.iterrows():
        cid = str(row["id"]).strip()

        source[cid] = {
            "roce": f(row["roce_percentage"]),
            "roe": f(row["roe_percentage"]),
        }

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")

    try:

        financials = {
            str(r[0]).strip()
            for r in conn.execute(
                """
                SELECT DISTINCT company_id
                FROM sectors
                WHERE LOWER(TRIM(broad_sector)) = 'financials'
                """
            ).fetchall()
        }

        print()
        print("Financials companies:", len(financials))
        print("Financials IDs:", sorted(financials))

        ratios = pd.read_sql_query(
            """
            SELECT
                fr.company_id,
                fr.year,
                fr.debt_to_equity,
                bs.equity_capital,
                bs.reserves,
                bs.borrowings,
                pl.operating_profit,
                pl.net_profit
            FROM financial_ratios fr
            LEFT JOIN balancesheet bs
                ON fr.company_id = bs.company_id
                AND fr.year = bs.year
            LEFT JOIN profitandloss pl
                ON fr.company_id = pl.company_id
                AND fr.year = pl.year
            """,
            conn
        )

        print()
        print("Ratio rows:", len(ratios))

        # --------------------------------------------------------
        # High leverage carve-out
        # --------------------------------------------------------

        financials_high = 0
        financials_flagged = 0
        nonfinancial_high = 0
        nonfinancial_flagged = 0

        for _, row in ratios.iterrows():

            cid = str(row["company_id"]).strip()
            de = f(row["debt_to_equity"])

            if de is None or de <= 5:
                continue

            flag = high_leverage_flag(
                de,
                "Financials" if cid in financials else "Other"
            )

            if cid in financials:
                financials_high += 1

                if flag:
                    financials_flagged += 1

            else:
                nonfinancial_high += 1

                if flag:
                    nonfinancial_flagged += 1

        print()
        print("HIGH LEVERAGE CARVE-OUT")
        print("-" * 70)
        print("Financials D/E > 5       :", financials_high)
        print("Financials incorrectly flagged:", financials_flagged)
        print("Non-Financials D/E > 5   :", nonfinancial_high)
        print("Non-Financials flagged    :", nonfinancial_flagged)

        # --------------------------------------------------------
        # ROCE / ROE anomalies
        # --------------------------------------------------------

        anomalies = []

        for _, row in ratios.iterrows():

            cid = str(row["company_id"]).strip()
            year = str(row["year"])

            if cid not in source:
                continue

            computed_roce = roce(
                row["operating_profit"],
                row["equity_capital"],
                row["reserves"],
                row["borrowings"],
            )

            computed_roe = roe(
                row["net_profit"],
                row["equity_capital"],
                row["reserves"],
            )

            source_roce = source[cid]["roce"]
            source_roe = source[cid]["roe"]

            if (
                computed_roce is not None
                and source_roce is not None
            ):

                diff = abs(
                    computed_roce -
                    source_roce
                )

                if diff > 5:

                    anomalies.append({
                        "company": cid,
                        "year": year,
                        "metric": "ROCE",
                        "computed": computed_roce,
                        "source": source_roce,
                        "difference": diff,
                        "category": "data source issue",
                        "explanation":
                            "Computed ROCE differs from "
                            "companies.xlsx source value by "
                            "more than 5 percentage points."
                    })

            if (
                computed_roe is not None
                and source_roe is not None
            ):

                diff = abs(
                    computed_roe -
                    source_roe
                )

                if diff > 5:

                    if cid.upper() == "TCS":
                        explanation = (
                            "Source ROE appears anomalous. "
                            "Use ratio-engine ROE for analytics "
                            "and source value for display only."
                        )
                    else:
                        explanation = (
                            "Computed ROE differs from "
                            "companies.xlsx source value by "
                            "more than 5 percentage points."
                        )

                    anomalies.append({
                        "company": cid,
                        "year": year,
                        "metric": "ROE",
                        "computed": computed_roe,
                        "source": source_roe,
                        "difference": diff,
                        "category": "data source issue",
                        "explanation": explanation
                    })

        # --------------------------------------------------------
        # Write final log
        # --------------------------------------------------------

        with open(LOG, "w", encoding="utf-8") as out:

            out.write(
                "SPRINT 2 — DAY 13 RATIO EDGE CASE LOG\n"
            )
            out.write("=" * 70 + "\n\n")

            out.write(
                f"Financials companies: {len(financials)}\n"
            )

            out.write(
                f"Financials D/E > 5: {financials_high}\n"
            )

            out.write(
                f"Financials incorrectly flagged: "
                f"{financials_flagged}\n"
            )

            out.write(
                f"Non-Financials D/E > 5: "
                f"{nonfinancial_high}\n"
            )

            out.write(
                f"Non-Financials correctly flagged: "
                f"{nonfinancial_flagged}\n\n"
            )

            out.write(
                f"Total anomalies: {len(anomalies)}\n\n"
            )

            out.write("ANOMALIES\n")
            out.write("-" * 70 + "\n\n")

            if not anomalies:
                out.write(
                    "No ROCE/ROE anomalies greater than "
                    "5 percentage points were detected.\n"
                )

            for a in anomalies:

                out.write(
                    f"Company: {a['company']}\n"
                )

                out.write(
                    f"Year: {a['year']}\n"
                )

                out.write(
                    f"Metric: {a['metric']}\n"
                )

                out.write(
                    f"Computed: {a['computed']:.4f}\n"
                )

                out.write(
                    f"Source: {a['source']:.4f}\n"
                )

                out.write(
                    f"Difference: {a['difference']:.4f}\n"
                )

                out.write(
                    f"Category: {a['category']}\n"
                )

                out.write(
                    f"Explanation: {a['explanation']}\n"
                )

                out.write("\n" + "-" * 70 + "\n\n")

        print()
        print("=" * 70)
        print("✅ DAY 13 COMPLETE")
        print("=" * 70)

        print("ROCE anomalies :", sum(
            a["metric"] == "ROCE"
            for a in anomalies
        ))

        print("ROE anomalies  :", sum(
            a["metric"] == "ROE"
            for a in anomalies
        ))

        print("Total anomalies :", len(anomalies))

        print()
        print("Log:", LOG.resolve())

    finally:
        conn.close()


if __name__ == "__main__":
    main()
