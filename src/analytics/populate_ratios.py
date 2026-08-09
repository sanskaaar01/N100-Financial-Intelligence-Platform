import sqlite3
import math

DB = "db/nifty100.db"


def num(x):
    try:
        x = float(x)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def cagr(start, end, years=5):
    start = num(start)
    end = num(end)

    if start is None or end is None or start <= 0 or end <= 0:
        return None

    return ((end / start) ** (1 / years) - 1) * 100


def quality_score(roe, npm, de, icr, turnover, rev_cagr, pat_cagr):
    """
    Composite quality score: 0-100.
    Components are capped so extreme values do not dominate.
    """

    score = 0.0

    # ROE - 20 points
    if roe is not None:
        score += min(max(roe, 0) / 20 * 20, 20)

    # Net profit margin - 15 points
    if npm is not None:
        score += min(max(npm, 0) / 20 * 15, 15)

    # Debt/Equity - 15 points
    if de is not None:
        if de <= 0.5:
            score += 15
        elif de <= 1:
            score += 12
        elif de <= 2:
            score += 8
        elif de <= 5:
            score += 3

    # Interest coverage - 15 points
    if icr is not None:
        if icr >= 5:
            score += 15
        elif icr >= 3:
            score += 12
        elif icr >= 1.5:
            score += 8
        elif icr >= 1:
            score += 3

    # Asset turnover - 10 points
    if turnover is not None:
        score += min(max(turnover, 0) / 2 * 10, 10)

    # Revenue CAGR - 12.5 points
    if rev_cagr is not None:
        score += min(max(rev_cagr, 0) / 15 * 12.5, 12.5)

    # PAT CAGR - 12.5 points
    if pat_cagr is not None:
        score += min(max(pat_cagr, 0) / 15 * 12.5, 12.5)

    return round(min(score, 100), 4)


def main():

    print("=" * 70)
    print("DAY 12 — POPULATING FINANCIAL RATIO KPIs")
    print("=" * 70)

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # ------------------------------------------------------------
    # Load P&L
    # ------------------------------------------------------------

    pl = cur.execute("""
        SELECT
            company_id,
            year,
            sales,
            operating_profit,
            other_income,
            interest,
            net_profit,
            eps
        FROM profitandloss
    """).fetchall()

    # ------------------------------------------------------------
    # Load Balance Sheet
    # ------------------------------------------------------------

    bs = cur.execute("""
        SELECT
            company_id,
            year,
            equity_capital,
            reserves,
            borrowings,
            total_assets
        FROM balancesheet
    """).fetchall()

    # ------------------------------------------------------------
    # Load Cash Flow
    # ------------------------------------------------------------

    cf = cur.execute("""
        SELECT
            company_id,
            year,
            operating_activity,
            investing_activity
        FROM cashflow
    """).fetchall()

    print("P&L rows :", len(pl))
    print("BS rows  :", len(bs))
    print("CF rows  :", len(cf))

    # ------------------------------------------------------------
    # Create lookup maps
    # ------------------------------------------------------------

    pl_map = {}
    bs_map = {}
    cf_map = {}

    for r in pl:
        pl_map[(str(r[0]), str(r[1]))] = r

    for r in bs:
        bs_map[(str(r[0]), str(r[1]))] = r

    for r in cf:
        cf_map[(str(r[0]), str(r[1]))] = r

    # ------------------------------------------------------------
    # Build company P&L history for CAGR
    # ------------------------------------------------------------

    history = {}

    for r in pl:

        company = str(r[0])

        history.setdefault(company, []).append({
            "year": str(r[1]),
            "sales": num(r[2]),
            "pat": num(r[6]),
            "eps": num(r[7])
        })

    for company in history:
        history[company].sort(key=lambda x: x["year"])

    # ------------------------------------------------------------
    # Existing ratio rows
    # ------------------------------------------------------------

    ratio_rows = cur.execute("""
        SELECT id, company_id, year
        FROM financial_ratios
        ORDER BY company_id, year
    """).fetchall()

    print("financial_ratios rows :", len(ratio_rows))
    print()

    updated = 0
    skipped = 0
    cagr_count = 0

    # ------------------------------------------------------------
    # Update each ratio row
    # ------------------------------------------------------------

    for ratio_id, company_id, year in ratio_rows:

        company_id = str(company_id)
        year = str(year)

        key = (company_id, year)

        p = pl_map.get(key)
        b = bs_map.get(key)
        f = cf_map.get(key)

        if p is None or b is None or f is None:
            skipped += 1
            continue

        sales = num(p[2])
        operating_profit = num(p[3])
        other_income = num(p[4])
        interest = num(p[5])
        pat = num(p[6])
        eps = num(p[7])

        equity_capital = num(b[2])
        reserves = num(b[3])
        borrowings = num(b[4])
        total_assets = num(b[5])

        cfo = num(f[2])
        cfi = num(f[3])

        # --------------------------------------------------------
        # NPM
        # --------------------------------------------------------

        npm = None

        if sales is not None and sales != 0 and pat is not None:
            npm = pat / sales * 100

        # --------------------------------------------------------
        # OPM
        # --------------------------------------------------------

        opm = None

        if sales is not None and sales != 0 and operating_profit is not None:
            opm = operating_profit / sales * 100

        # --------------------------------------------------------
        # ROE
        # --------------------------------------------------------

        roe = None

        if (
            equity_capital is not None
            and reserves is not None
            and pat is not None
        ):
            equity = equity_capital + reserves

            if equity > 0:
                roe = pat / equity * 100

        # --------------------------------------------------------
        # Debt / Equity
        # --------------------------------------------------------

        de = None

        if borrowings is not None:

            if borrowings == 0:
                de = 0.0

            elif (
                equity_capital is not None
                and reserves is not None
                and equity_capital + reserves > 0
            ):
                de = borrowings / (equity_capital + reserves)

        # --------------------------------------------------------
        # Interest Coverage
        # --------------------------------------------------------

        icr = None

        if interest is not None and interest != 0:

            numerator = 0

            if operating_profit is not None:
                numerator += operating_profit

            if other_income is not None:
                numerator += other_income

            icr = numerator / interest

        # --------------------------------------------------------
        # Asset Turnover
        # --------------------------------------------------------

        turnover = None

        if (
            sales is not None
            and total_assets is not None
            and total_assets != 0
        ):
            turnover = sales / total_assets

        # --------------------------------------------------------
        # Free Cash Flow
        # --------------------------------------------------------

        fcf = None

        if cfo is not None and cfi is not None:
            fcf = cfo + cfi

        # --------------------------------------------------------
        # CapEx
        # --------------------------------------------------------

        capex = abs(cfi) if cfi is not None else None

        # --------------------------------------------------------
        # 5 YEAR CAGR
        # --------------------------------------------------------

        revenue_cagr = None
        pat_cagr = None
        eps_cagr = None

        company_history = history.get(company_id, [])

        current_index = None

        for i, item in enumerate(company_history):
            if item["year"] == year:
                current_index = i
                break

        if current_index is not None and current_index >= 5:

            start = company_history[current_index - 5]
            end = company_history[current_index]

            revenue_cagr = cagr(
                start["sales"],
                end["sales"],
                5
            )

            pat_cagr = cagr(
                start["pat"],
                end["pat"],
                5
            )

            eps_cagr = cagr(
                start["eps"],
                end["eps"],
                5
            )

            if (
                revenue_cagr is not None
                or pat_cagr is not None
                or eps_cagr is not None
            ):
                cagr_count += 1

        # --------------------------------------------------------
        # Composite Quality Score
        # --------------------------------------------------------

        score = quality_score(
            roe,
            npm,
            de,
            icr,
            turnover,
            revenue_cagr,
            pat_cagr
        )

        # --------------------------------------------------------
        # UPDATE DATABASE
        # --------------------------------------------------------

        cur.execute("""
            UPDATE financial_ratios
            SET
                net_profit_margin_pct = ?,
                operating_profit_margin_pct = ?,
                return_on_equity_pct = ?,
                debt_to_equity = ?,
                interest_coverage = ?,
                asset_turnover = ?,
                free_cash_flow_cr = ?,
                capex_cr = ?,
                earnings_per_share = ?,
                revenue_cagr_5yr = ?,
                pat_cagr_5yr = ?,
                eps_cagr_5yr = ?,
                composite_quality_score = ?
            WHERE id = ?
        """, (
            npm,
            opm,
            roe,
            de,
            icr,
            turnover,
            fcf,
            capex,
            eps,
            revenue_cagr,
            pat_cagr,
            eps_cagr,
            score,
            ratio_id
        ))

        updated += 1

        if updated % 100 == 0:
            print(f"Updated {updated} rows...")

    conn.commit()

    # ------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("DAY 12 VERIFICATION")
    print("=" * 70)

    total = cur.execute(
        "SELECT COUNT(*) FROM financial_ratios"
    ).fetchone()[0]

    print("Total rows :", total)
    print("Rows updated :", updated)
    print("Rows skipped :", skipped)
    print("Rows with CAGR calculated :", cagr_count)

    columns = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "capex_cr",
        "earnings_per_share",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "eps_cagr_5yr",
        "composite_quality_score"
    ]

    print()
    print("KPI population:")

    for column in columns:

        count = cur.execute(
            f"""
            SELECT COUNT(*)
            FROM financial_ratios
            WHERE "{column}" IS NOT NULL
            """
        ).fetchone()[0]

        print(f"{column:35} {count}")

    # ------------------------------------------------------------
    # FK check
    # ------------------------------------------------------------

    fk = cur.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    print()
    print("Foreign key errors :", len(fk))

    if len(fk) == 0:
        print("✅ Foreign key check passed")
    else:
        print("❌ Foreign key check FAILED")
        print(fk[:10])

    # ------------------------------------------------------------
    # Sample
    # ------------------------------------------------------------

    print()
    print("Sample populated rows:")

    samples = cur.execute("""
        SELECT
            company_id,
            year,
            ROUND(return_on_equity_pct, 2),
            ROUND(debt_to_equity, 2),
            ROUND(revenue_cagr_5yr, 2),
            ROUND(pat_cagr_5yr, 2),
            ROUND(eps_cagr_5yr, 2),
            ROUND(composite_quality_score, 2)
        FROM financial_ratios
        WHERE composite_quality_score IS NOT NULL
        LIMIT 5
    """).fetchall()

    for row in samples:
        print(row)

    conn.close()

    print()
    print("=" * 70)
    print("✅ DAY 12 POPULATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
