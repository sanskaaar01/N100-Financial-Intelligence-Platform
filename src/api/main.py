import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "nifty100.db"


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="N100 Financial Intelligence API",
    description=(
        "REST API for the N100 Financial Intelligence Platform. "
        "Provides company, financial ratio, clustering, "
        "cash-flow intelligence and portfolio analytics."
    ),
    version="1.0.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Return HTTP 400 for invalid API parameters."""
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE HELPER
# ============================================================


def get_connection():
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="Database not found.",
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# SAFE DATAFRAME JSON CONVERSION
# ============================================================


def dataframe_records(df):
    import pandas as pd

    # Convert NaN / NaT values to JSON-safe None.
    df = df.astype(object)
    df = df.where(pd.notna(df), None)

    return df.to_dict(orient="records")


# ============================================================
# ROOT
# ============================================================


@app.get("/")
def root():
    return {
        "name": "N100 Financial Intelligence API",
        "version": "1.0.0",
        "status": "online",
    }


# ============================================================
# HEALTH
# ============================================================


@app.get("/health")
def health():
    try:
        conn = get_connection()

        conn.execute("SELECT 1").fetchone()

        conn.close()

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {exc}",
        )


# ============================================================
# COMPANY LIST
# ============================================================


@app.get("/api/companies")
def get_companies():
    conn = get_connection()

    rows = conn.execute("""
        SELECT
            id AS company_id,
            company_name
        FROM companies
        ORDER BY id
        """).fetchall()

    conn.close()

    return {
        "count": len(rows),
        "companies": [dict(row) for row in rows],
    }


# ============================================================
# COMPANY PROFILE
# ============================================================


@app.get("/api/companies/{company_id}")
def get_company(company_id: str):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT
            id AS company_id,
            company_name,
            about_company,
            website,
            nse_profile,
            bse_profile,
            face_value,
            book_value,
            roce_percentage,
            roe_percentage
        FROM companies
        WHERE id = ?
        """,
        (company_id,),
    ).fetchone()

    conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Company '{company_id}' not found.",
        )

    return dict(row)


# ============================================================
# FINANCIAL RATIOS
# ============================================================


@app.get("/api/companies/{company_id}/ratios")
def get_company_ratios(company_id: str):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year
        """,
        (company_id,),
    ).fetchall()

    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No ratio data found for '{company_id}'.",
        )

    return {
        "company_id": company_id,
        "count": len(rows),
        "data": [dict(row) for row in rows],
    }


# ============================================================
# CASH FLOW
# ============================================================


@app.get("/api/companies/{company_id}/cashflow")
def get_company_cashflow(company_id: str):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM cashflow
        WHERE company_id = ?
        ORDER BY year
        """,
        (company_id,),
    ).fetchall()

    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No cash-flow data found for '{company_id}'.",
        )

    return {
        "company_id": company_id,
        "count": len(rows),
        "data": [dict(row) for row in rows],
    }


# ============================================================
# KMEANS CLUSTER
# ============================================================


@app.get("/api/clusters")
def get_clusters():
    path = ROOT / "output" / "kmeans_clusters.csv"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="KMeans output not found.",
        )

    import pandas as pd

    df = pd.read_csv(path)

    return {
        "count": len(df),
        "clusters": dataframe_records(df),
    }


# ============================================================
# CLUSTER LABELS
# ============================================================


@app.get("/api/cluster-labels")
def get_cluster_labels():
    path = ROOT / "output" / "cluster_labels.csv"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Cluster labels output not found.",
        )

    import pandas as pd

    df = pd.read_csv(path)

    return {
        "count": len(df),
        "labels": dataframe_records(df),
    }


# ============================================================
# PORTFOLIO STATISTICS
# ============================================================


@app.get("/api/portfolio/stats")
def get_portfolio_stats():
    path = ROOT / "output" / "portfolio_stats.csv"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Portfolio statistics not found.",
        )

    import pandas as pd

    df = pd.read_csv(path)

    return {
        "count": len(df),
        "stats": dataframe_records(df),
    }


# ============================================================
# OUTLIERS
# ============================================================


@app.get("/api/outliers")
def get_outliers():
    path = ROOT / "output" / "outlier_report.csv"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Outlier report not found.",
        )

    import pandas as pd

    df = pd.read_csv(path)

    return {
        "count": len(df),
        "outliers": dataframe_records(df),
    }


# ============================================================
# CAPITAL ALLOCATION
# ============================================================


@app.get("/api/capital-allocation")
def get_capital_allocation():
    path = ROOT / "output" / "capital_allocation.csv"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Capital allocation output not found.",
        )

    import pandas as pd

    df = pd.read_csv(path)

    return {
        "count": len(df),
        "data": dataframe_records(df),
    }


# ============================================================
# PROS & CONS
# ============================================================


@app.get("/api/companies/{company_id}/pros-cons")
def get_pros_cons(company_id: str):
    path = ROOT / "output" / "pros_cons_generated.csv"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Pros/cons output not found.",
        )

    import pandas as pd

    df = pd.read_csv(path)

    df = df[df["company_id"].astype(str) == company_id]

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No pros/cons found for '{company_id}'.",
        )

    return {
        "company_id": company_id,
        "signals": dataframe_records(df),
    }


# ============================================================
# DAY 39 - VERSIONED COMPANY DATA API
# ============================================================

import math

from fastapi import Query
from fastapi.responses import FileResponse


def _json_safe(value):
    """Convert non-JSON-safe numeric values to None."""
    if value is None:
        return None

    try:
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
    except Exception:
        pass

    return value


def _rows_to_dicts(rows):
    """Convert SQLite rows into JSON-safe dictionaries."""
    return [
        {key: _json_safe(value) for key, value in dict(row).items()} for row in rows
    ]


def _company_exists(conn, ticker):
    """Return company row for a ticker."""
    return conn.execute(
        "SELECT * FROM companies WHERE id = ?",
        (ticker.upper(),),
    ).fetchone()


def _validate_ticker(conn, ticker):
    """Validate ticker and return uppercase ticker."""
    ticker = ticker.upper()

    if _company_exists(conn, ticker) is None:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found.",
        )

    return ticker


def _validate_year(value, name):
    """Validate YYYY-MM year format."""
    if value is None:
        return

    import re

    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise HTTPException(
            status_code=400,
            detail=f"{name} must use YYYY-MM format.",
        )


# ============================================================
# COMPANY LIST
# ============================================================


@app.get("/api/v1/health")
def v1_health():
    """Return API health and database row counts."""
    conn = get_connection()

    tables = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
        "sectors",
        "market_cap",
        "peer_groups",
        "peer_percentiles",
        "documents",
    ]

    counts = {}

    for table in tables:
        try:
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.Error:
            counts[table] = 0

    conn.close()

    return {
        "status": "ok",
        "db_row_counts": counts,
    }


@app.get("/api/v1/companies")
def v1_companies(
    sector: str | None = None,
    market_cap_category: str | None = None,
    search: str | None = None,
):
    """Return all companies with optional filters."""
    conn = get_connection()

    sql = """
        SELECT
            c.id AS company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            COALESCE(
                c.roe_percentage,
                c.roe_percentage
            ) AS roe_pct,
            c.roce_percentage AS roce_pct,
            s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.id
        WHERE 1=1
    """

    params = []

    if sector:
        sql += """
            AND LOWER(COALESCE(s.broad_sector, ''))
                = LOWER(?)
        """
        params.append(sector)

    if market_cap_category:
        sql += """
            AND LOWER(COALESCE(s.market_cap_category, ''))
                = LOWER(?)
        """
        params.append(market_cap_category)

    if search:
        sql += """
            AND (
                LOWER(c.id) LIKE LOWER(?)
                OR LOWER(c.company_name) LIKE LOWER(?)
            )
        """

        search_term = f"%{search}%"
        params.extend([search_term, search_term])

    sql += " ORDER BY c.company_name"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return {
        "count": len(rows),
        "data": _rows_to_dicts(rows),
    }


# ============================================================
# FULL COMPANY PROFILE
# ============================================================


@app.get("/api/v1/companies/{ticker}")
def v1_company(ticker: str):
    """Return complete company profile and latest KPIs."""
    conn = get_connection()

    ticker = _validate_ticker(conn, ticker)

    company = conn.execute(
        """
        SELECT
            c.*,
            s.broad_sector,
            s.sub_sector,
            s.index_weight_pct,
            s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.id
        WHERE c.id = ?
        """,
        (ticker,),
    ).fetchone()

    latest = conn.execute(
        """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year DESC
        LIMIT 1
        """,
        (ticker,),
    ).fetchone()

    conn.close()

    result = dict(company)

    result["latest_kpis"] = (
        {key: _json_safe(value) for key, value in dict(latest).items()}
        if latest
        else {}
    )

    return {
        "company_id": ticker,
        "company_name": company["company_name"],
        "company": {key: _json_safe(value) for key, value in result.items()},
    }


# ============================================================
# P&L
# ============================================================


@app.get("/api/v1/companies/{ticker}/pl")
def v1_company_pl(
    ticker: str,
    from_year: str | None = Query(default=None),
    to_year: str | None = Query(default=None),
):
    """Return P&L history with optional year range."""
    _validate_year(from_year, "from_year")
    _validate_year(to_year, "to_year")

    conn = get_connection()
    ticker = _validate_ticker(conn, ticker)

    sql = """
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
    """

    params = [ticker]

    if from_year:
        sql += " AND year >= ?"
        params.append(from_year)

    if to_year:
        sql += " AND year <= ?"
        params.append(to_year)

    sql += " ORDER BY year"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return {
        "company_id": ticker,
        "count": len(rows),
        "history": _rows_to_dicts(rows),
    }


# ============================================================
# BALANCE SHEET
# ============================================================


@app.get("/api/v1/companies/{ticker}/bs")
def v1_company_bs(
    ticker: str,
    from_year: str | None = Query(default=None),
    to_year: str | None = Query(default=None),
):
    """Return balance sheet history with optional year range."""
    _validate_year(from_year, "from_year")
    _validate_year(to_year, "to_year")

    conn = get_connection()
    ticker = _validate_ticker(conn, ticker)

    sql = """
        SELECT *
        FROM balancesheet
        WHERE company_id = ?
    """

    params = [ticker]

    if from_year:
        sql += " AND year >= ?"
        params.append(from_year)

    if to_year:
        sql += " AND year <= ?"
        params.append(to_year)

    sql += " ORDER BY year"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return {
        "company_id": ticker,
        "count": len(rows),
        "history": _rows_to_dicts(rows),
    }


# ============================================================
# CASH FLOW
# ============================================================


@app.get("/api/v1/companies/{ticker}/cashflow")
def v1_company_cashflow(
    ticker: str,
    from_year: str | None = Query(default=None),
    to_year: str | None = Query(default=None),
):
    """Return cash flow history with optional year range."""
    _validate_year(from_year, "from_year")
    _validate_year(to_year, "to_year")

    conn = get_connection()
    ticker = _validate_ticker(conn, ticker)

    sql = """
        SELECT *
        FROM cashflow
        WHERE company_id = ?
    """

    params = [ticker]

    if from_year:
        sql += " AND year >= ?"
        params.append(from_year)

    if to_year:
        sql += " AND year <= ?"
        params.append(to_year)

    sql += " ORDER BY year"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return {
        "company_id": ticker,
        "count": len(rows),
        "history": _rows_to_dicts(rows),
    }


# ============================================================
# RATIOS
# ============================================================


@app.get("/api/v1/companies/{ticker}/ratios")
def v1_company_ratios(
    ticker: str,
    year: str | None = Query(default=None),
):
    """Return computed financial ratios."""
    conn = get_connection()
    ticker = _validate_ticker(conn, ticker)

    sql = """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
    """

    params = [ticker]

    if year:
        sql += " AND year = ?"
        params.append(year)

    sql += " ORDER BY year"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return {
        "company_id": ticker,
        "count": len(rows),
        "data": _rows_to_dicts(rows),
    }


# ============================================================
# TEARSHEET PDF
# ============================================================


@app.get("/api/v1/companies/{ticker}/tearsheet")
def v1_company_tearsheet(ticker: str):
    """Return the pre-generated company tearsheet PDF."""
    conn = get_connection()
    ticker = _validate_ticker(conn, ticker)
    conn.close()

    pdf_path = Path("reports") / "tearsheets" / f"{ticker}_tearsheet.pdf"

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Tearsheet for '{ticker}' not found.",
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"{ticker}_tearsheet.pdf",
    )


# ============================================================
# DAY 40 - SCREENER, SECTOR, PEER & REMAINING API
# ============================================================


@app.get("/api/v1/screener")
def v1_screener(
    min_roe: float | None = None,
    max_de: float | None = None,
    min_fcf: float | None = None,
    sector: str | None = None,
    min_rev_cagr_5yr: float | None = None,
    min_pat_cagr_5yr: float | None = None,
    max_pe: float | None = None,
):
    """Screen companies using latest financial KPIs."""

    for name, value in {
        "min_roe": min_roe,
        "max_de": max_de,
        "min_fcf": min_fcf,
        "min_rev_cagr_5yr": min_rev_cagr_5yr,
        "min_pat_cagr_5yr": min_pat_cagr_5yr,
        "max_pe": max_pe,
    }.items():

        if value is not None:
            try:
                value = float(value)
                if not math.isfinite(value):
                    raise ValueError
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid value for {name}.",
                )

    if max_de is not None and max_de < 0:
        raise HTTPException(
            status_code=400,
            detail="max_de cannot be negative.",
        )

    conn = get_connection()

    sql = """
        WITH latest_ratios AS (
            SELECT *
            FROM financial_ratios
            WHERE id IN (
                SELECT MAX(id)
                FROM financial_ratios
                GROUP BY company_id
            )
        ),
        latest_market_cap AS (
            SELECT *
            FROM market_cap
            WHERE id IN (
                SELECT MAX(id)
                FROM market_cap
                GROUP BY company_id
            )
        ),
        sector_one AS (
            SELECT *
            FROM sectors
            WHERE id IN (
                SELECT MAX(id)
                FROM sectors
                GROUP BY company_id
            )
        )
        SELECT
            c.id AS company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            COALESCE(
                c.roe_percentage,
                c.roe_percentage
            ) AS roe_pct,
            c.roce_percentage AS roce_pct,
            s.market_cap_category,
            fr.year,
            fr.net_profit_margin_pct,
            fr.operating_profit_margin_pct,
            c.roe_percentage,
            fr.debt_to_equity,
            fr.free_cash_flow_cr,
            fr.revenue_cagr_5yr,
            fr.pat_cagr_5yr,
            fr.eps_cagr_5yr,
            fr.composite_quality_score,
            mc.pe_ratio
        FROM companies c
        LEFT JOIN sector_one s
            ON s.company_id = c.id
        LEFT JOIN latest_ratios fr
            ON fr.company_id = c.id
        LEFT JOIN latest_market_cap mc
            ON mc.company_id = c.id
        WHERE 1=1
    """

    params = []

    if min_roe is not None:
        sql += """
            AND COALESCE(
                c.roe_percentage,
                c.roe_percentage,
                0
            ) >= ?
        """
        params.append(min_roe)

    if max_de is not None:
        sql += """
            AND COALESCE(fr.debt_to_equity, 999999) <= ?
        """
        params.append(max_de)

    if min_fcf is not None:
        sql += """
            AND COALESCE(fr.free_cash_flow_cr, 0) >= ?
        """
        params.append(min_fcf)

    if min_rev_cagr_5yr is not None:
        sql += """
            AND COALESCE(fr.revenue_cagr_5yr, -999999) >= ?
        """
        params.append(min_rev_cagr_5yr)

    if min_pat_cagr_5yr is not None:
        sql += """
            AND COALESCE(fr.pat_cagr_5yr, -999999) >= ?
        """
        params.append(min_pat_cagr_5yr)

    if max_pe is not None:
        sql += """
            AND COALESCE(mc.pe_ratio, 999999) <= ?
        """
        params.append(max_pe)

    if sector:
        sql += """
            AND LOWER(COALESCE(s.broad_sector, '')) = LOWER(?)
        """
        params.append(sector)

    sql += """
        ORDER BY
            COALESCE(fr.composite_quality_score, 0) DESC,
            c.company_name
    """

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    data = _rows_to_dicts(rows)

    # Absolute guarantee: one result per company.
    unique = {}
    for row in data:
        unique[row["company_id"]] = row

    data = list(unique.values())

    return {
        "count": len(data),
        "data": data,
    }


@app.get("/api/v1/sectors")
def v1_sectors():
    """Return all sectors with company counts and median KPIs."""

    conn = get_connection()

    rows = conn.execute("""
        SELECT
            s.broad_sector AS sector,
            COUNT(DISTINCT s.company_id) AS company_count,
            AVG(c.roe_percentage) AS median_roe,
            AVG(mc.pe_ratio) AS median_pe,
            AVG(fr.debt_to_equity) AS median_de
        FROM sectors s

        LEFT JOIN companies c
            ON c.id = s.company_id

        LEFT JOIN financial_ratios fr
            ON fr.company_id = s.company_id
            AND fr.year = (
                SELECT MAX(fr2.year)
                FROM financial_ratios fr2
                WHERE fr2.company_id = s.company_id
            )

        LEFT JOIN market_cap mc
            ON mc.company_id = s.company_id
            AND mc.year = (
                SELECT MAX(mc2.year)
                FROM market_cap mc2
                WHERE mc2.company_id = s.company_id
            )

        WHERE s.broad_sector IS NOT NULL
        GROUP BY s.broad_sector
        ORDER BY s.broad_sector
        """).fetchall()

    conn.close()

    return {
        "count": len(rows),
        "data": _rows_to_dicts(rows),
    }


@app.get("/api/v1/sectors/{sector}/companies")
def v1_sector_companies(sector: str):
    """Return companies belonging to a sector."""

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            c.id AS company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            COALESCE(
                c.roe_percentage,
                c.roe_percentage
            ) AS roe_pct,
            c.roce_percentage AS roce_pct,
            fr.year,
            c.roe_percentage,
            fr.debt_to_equity,
            fr.net_profit_margin_pct,
            fr.operating_profit_margin_pct,
            fr.revenue_cagr_5yr,
            fr.pat_cagr_5yr,
            fr.eps_cagr_5yr,
            fr.composite_quality_score
        FROM companies c

        JOIN sectors s
            ON s.company_id = c.id

        LEFT JOIN financial_ratios fr
            ON fr.company_id = c.id
            AND fr.year = (
                SELECT MAX(fr2.year)
                FROM financial_ratios fr2
                WHERE fr2.company_id = c.id
            )

        WHERE LOWER(s.broad_sector) = LOWER(?)

        ORDER BY c.company_name
        """,
        (sector,),
    ).fetchall()

    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Sector '{sector}' not found.",
        )

    return {
        "sector": sector,
        "count": len(rows),
        "data": _rows_to_dicts(rows),
    }


# ============================================================
# PEERS
# ============================================================


@app.get("/api/v1/peers/{group_name}")
def v1_peers(group_name: str):
    """Return companies in a peer group."""

    conn = get_connection()

    columns = [
        row[1] for row in conn.execute("PRAGMA table_info(peer_groups)").fetchall()
    ]

    if not columns:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Peer group not found.",
        )

    group_col = None

    for candidate in [
        "group_name",
        "peer_group",
        "group",
        "name",
    ]:
        if candidate in columns:
            group_col = candidate
            break

    if group_col is None:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Peer group not found.",
        )

    rows = conn.execute(
        f"""
        SELECT *
        FROM peer_groups
        WHERE LOWER(CAST({group_col} AS TEXT)) = LOWER(?)
        """,
        (group_name,),
    ).fetchall()

    conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Peer group '{group_name}' not found.",
        )

    return {
        "group_name": group_name,
        "count": len(rows),
        "data": _rows_to_dicts(rows),
    }


@app.get("/api/v1/companies/{ticker}/peers/compare")
def v1_peer_compare(ticker: str):
    """Return radar comparison data for a company."""

    conn = get_connection()
    ticker = _validate_ticker(conn, ticker)

    company = conn.execute(
        """
        SELECT
            c.id AS company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            c.roe_percentage,
            fr.net_profit_margin_pct,
            fr.operating_profit_margin_pct,
            fr.debt_to_equity,
            fr.interest_coverage,
            fr.asset_turnover,
            fr.revenue_cagr_5yr,
            fr.pat_cagr_5yr
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.id
        LEFT JOIN financial_ratios fr
            ON fr.company_id = c.id
            AND fr.year = (
                SELECT MAX(fr2.year)
                FROM financial_ratios fr2
                WHERE fr2.company_id = c.id
            )
        WHERE c.id = ?
        """,
        (ticker,),
    ).fetchone()

    conn.close()

    if company is None:
        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found.",
        )

    company_data = {key: _json_safe(value) for key, value in dict(company).items()}

    metrics = [
        "return_on_equity_pct",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
    ]

    axes = []

    for metric in metrics:
        axes.append(
            {
                "metric": metric,
                "company": company_data.get(metric),
                "peer_average": None,
                "benchmark": None,
            }
        )

    return {
        "company_id": ticker,
        "company": company_data,
        "axes": axes,
    }


# ============================================================
# MARKET CAP / VALUATION
# ============================================================


@app.get("/api/v1/market-cap/{ticker}")
def v1_market_cap(ticker: str):
    """Return historical valuation multiples."""
    conn = get_connection()
    ticker = _validate_ticker(conn, ticker)

    rows = conn.execute(
        """
        SELECT
            year,
            pe_ratio,
            pb_ratio,
            ev_ebitda,
            dividend_yield_pct
        FROM market_cap
        WHERE company_id = ?
        ORDER BY year
        """,
        (ticker,),
    ).fetchall()

    conn.close()

    return {
        "company_id": ticker,
        "count": len(rows),
        "data": _rows_to_dicts(rows),
    }


# ============================================================
# PORTFOLIO STATS
# ============================================================


@app.get("/api/v1/portfolio/stats")
def v1_portfolio_stats():
    """Return percentile statistics for core KPIs."""

    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM financial_ratios
        WHERE year IN (
            SELECT MAX(year)
            FROM financial_ratios
            GROUP BY company_id
        )
        """).fetchall()

    conn.close()

    if not rows:
        return {
            "count": 0,
            "data": [],
        }

    import pandas as pd

    df = pd.DataFrame([dict(row) for row in rows])

    metrics = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "eps_cagr_5yr",
        "composite_quality_score",
    ]

    result = []

    for metric in metrics:
        if metric not in df.columns:
            continue

        values = pd.to_numeric(
            df[metric],
            errors="coerce",
        ).dropna()

        if values.empty:
            continue

        result.append(
            {
                "metric": metric,
                "p10": _json_safe(float(values.quantile(0.10))),
                "p20": _json_safe(float(values.quantile(0.20))),
                "p30": _json_safe(float(values.quantile(0.30))),
                "p40": _json_safe(float(values.quantile(0.40))),
                "p50": _json_safe(float(values.quantile(0.50))),
                "p60": _json_safe(float(values.quantile(0.60))),
                "p70": _json_safe(float(values.quantile(0.70))),
                "p80": _json_safe(float(values.quantile(0.80))),
                "p90": _json_safe(float(values.quantile(0.90))),
            }
        )

    return {
        "count": len(result),
        "data": result,
    }


# ============================================================
# DOCUMENTS
# ============================================================


@app.get("/api/v1/companies/{ticker}/documents")
def v1_company_documents(ticker: str):
    """Return company annual report documents."""
    conn = get_connection()
    ticker = _validate_ticker(conn, ticker)

    rows = conn.execute(
        """
        SELECT *
        FROM documents
        WHERE company_id = ?
        """,
        (ticker,),
    ).fetchall()

    conn.close()

    data = _rows_to_dicts(rows)

    for item in data:
        url = item.get("url") or item.get("document_url") or item.get("link")

        item["is_url_valid"] = bool(
            isinstance(url, str) and url.strip().startswith(("http://", "https://"))
        )

    return {
        "company_id": ticker,
        "count": len(data),
        "documents": data,
    }


# ============================================================
# API METADATA
# ============================================================


@app.get("/api/v1/openapi-info")
def v1_openapi_info():
    """Return OpenAPI metadata."""
    return {
        "title": app.title,
        "version": app.version,
        "openapi": app.openapi()["openapi"],
    }
