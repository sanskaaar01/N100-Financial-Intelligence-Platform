from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


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

        conn.execute(
            "SELECT 1"
        ).fetchone()

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

    rows = conn.execute(
        """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    return {
        "count": len(rows),
        "companies": [
            dict(row)
            for row in rows
        ],
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
        "data": [
            dict(row)
            for row in rows
        ],
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
        "data": [
            dict(row)
            for row in rows
        ],
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

    df = df[
        df["company_id"].astype(str)
        == company_id
    ]

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No pros/cons found for '{company_id}'.",
        )

    return {
        "company_id": company_id,
        "signals": dataframe_records(df),
    }
