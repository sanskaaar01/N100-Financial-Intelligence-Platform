import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


# ============================================================
# DATABASE
# ============================================================


def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    return sqlite3.connect(str(DB_PATH))


@st.cache_data(ttl=600)
def load_sector_data():

    conn = get_connection()

    try:

        # ----------------------------------------------------
        # COMPANIES
        # Actual primary key is companies.id
        # ----------------------------------------------------

        companies = pd.read_sql_query(
            """
            SELECT
                id AS company_id,
                company_name
            FROM companies
            """,
            conn,
        )

        # ----------------------------------------------------
        # PEER GROUP / SECTOR
        # ----------------------------------------------------

        peers = pd.read_sql_query(
            """
            SELECT
                company_id,
                peer_group_name AS broad_sector
            FROM peer_groups
            """,
            conn,
        )

        peers = peers.drop_duplicates(subset=["company_id"])

        # ----------------------------------------------------
        # LATEST ROE
        # ----------------------------------------------------

        ratios = pd.read_sql_query(
            """
            SELECT
                fr.company_id,
                fr.year,
                fr.return_on_equity_pct AS roe_value
            FROM financial_ratios fr
            INNER JOIN (
                SELECT
                    company_id,
                    MAX(CAST(year AS INTEGER)) AS latest_year
                FROM financial_ratios
                GROUP BY company_id
            ) latest
            ON fr.company_id = latest.company_id
            AND CAST(fr.year AS INTEGER) = latest.latest_year
            """,
            conn,
        )

        ratios = ratios.drop_duplicates(subset=["company_id"])

        # ----------------------------------------------------
        # LATEST REVENUE
        # Revenue = profitandloss.sales
        # ----------------------------------------------------

        pl = pd.read_sql_query(
            """
            SELECT
                p.company_id,
                p.year,
                p.sales AS revenue_value
            FROM profitandloss p
            INNER JOIN (
                SELECT
                    company_id,
                    MAX(CAST(year AS INTEGER)) AS latest_year
                FROM profitandloss
                GROUP BY company_id
            ) latest
            ON p.company_id = latest.company_id
            AND CAST(p.year AS INTEGER) = latest.latest_year
            """,
            conn,
        )

        pl = pl.drop_duplicates(subset=["company_id"])

        # ----------------------------------------------------
        # LATEST MARKET CAP
        # ----------------------------------------------------

        try:

            market_cap = pd.read_sql_query(
                """
                SELECT
                    company_id,
                    market_cap_crore
                FROM market_cap
                WHERE CAST(year AS INTEGER) = (
                    SELECT MAX(CAST(year AS INTEGER))
                    FROM market_cap
                )
                """,
                conn,
            )

            market_cap = market_cap.drop_duplicates(subset=["company_id"])

        except Exception:

            market_cap = pd.DataFrame(columns=["company_id", "market_cap_crore"])

        # ----------------------------------------------------
        # MERGE EVERYTHING
        # ----------------------------------------------------

        df = companies.copy()

        df["company_id"] = df["company_id"].astype(str).str.strip()

        peers["company_id"] = peers["company_id"].astype(str).str.strip()

        ratios["company_id"] = ratios["company_id"].astype(str).str.strip()

        pl["company_id"] = pl["company_id"].astype(str).str.strip()

        if not market_cap.empty:

            market_cap["company_id"] = market_cap["company_id"].astype(str).str.strip()

        # Sector
        df = df.merge(
            peers[["company_id", "broad_sector"]], on="company_id", how="left"
        )

        # ROE
        df = df.merge(ratios[["company_id", "roe_value"]], on="company_id", how="left")

        # Revenue
        df = df.merge(pl[["company_id", "revenue_value"]], on="company_id", how="left")

        # Market Cap
        if not market_cap.empty:

            df = df.merge(
                market_cap[["company_id", "market_cap_crore"]],
                on="company_id",
                how="left",
            )

        else:

            df["market_cap_crore"] = None

        # ----------------------------------------------------
        # CLEANUP
        # ----------------------------------------------------

        df["broad_sector"] = df["broad_sector"].fillna("Unknown").astype(str)

        df["company_name"] = df["company_name"].fillna(df["company_id"]).astype(str)

        df["roe_value"] = pd.to_numeric(df["roe_value"], errors="coerce")

        df["revenue_value"] = pd.to_numeric(df["revenue_value"], errors="coerce")

        df["market_cap_crore"] = pd.to_numeric(df["market_cap_crore"], errors="coerce")

        return df

    finally:

        conn.close()


# ============================================================
# PAGE HEADER
# ============================================================

st.title("📊 Nifty 100 Analytics")

st.caption("Financial Intelligence Platform — Dashboard & Valuation")

st.header("🏭 Sector Analysis")

st.write("Compare Nifty 100 companies and sector-level financial performance.")


# ============================================================
# LOAD DATA
# ============================================================

try:

    df = load_sector_data()

except Exception as e:

    st.error(f"Unable to load sector data: {e}")

    st.stop()


if df.empty:

    st.warning("No sector analysis data available.")

    st.stop()


# ============================================================
# SECTOR SELECTOR
# ============================================================

sectors = sorted(
    [
        sector
        for sector in df["broad_sector"].dropna().unique()
        if str(sector).strip() and str(sector).lower() != "unknown"
    ]
)

if not sectors:

    st.warning("No sectors were found in peer_groups.")

    st.stop()


selected_sector = st.selectbox("Select Sector", sectors)


sector_df = df[df["broad_sector"] == selected_sector].copy()


# ============================================================
# COMPANY COUNT
# ============================================================

st.header(f"{selected_sector} — {len(sector_df)} Companies")


# ============================================================
# BUBBLE CHART
# Revenue vs ROE
# ============================================================

st.subheader("📈 Revenue vs ROE")

chart_df = sector_df.copy()

chart_df = chart_df.dropna(subset=["revenue_value", "roe_value"])

if chart_df.empty:

    st.info("Revenue and ROE data is not available for this sector.")

else:

    # Plotly size cannot use NaN.
    chart_df["market_cap_crore"] = chart_df["market_cap_crore"].fillna(1).clip(lower=1)

    chart_df["sub_sector"] = "Sector"

    fig = px.scatter(
        chart_df,
        x="revenue_value",
        y="roe_value",
        size="market_cap_crore",
        color="sub_sector",
        hover_name="company_name",
        hover_data={
            "company_id": True,
            "revenue_value": ":,.2f",
            "roe_value": ":.2f",
            "market_cap_crore": ":,.2f",
            "sub_sector": False,
        },
        labels={
            "revenue_value": "Revenue / Sales",
            "roe_value": "ROE (%)",
            "market_cap_crore": "Market Cap (₹ Cr)",
        },
        title=(f"{selected_sector} — " "Revenue vs ROE"),
    )

    fig.update_layout(
        height=600, margin=dict(l=20, r=20, t=60, b=20), legend_title_text=""
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# SECTOR MEDIAN KPI
# ============================================================

st.subheader("📊 Sector Median KPIs")

median_rows = []

# Median ROE
roe_median = sector_df["roe_value"].median()

if pd.notna(roe_median):

    median_rows.append({"Metric": "ROE (%)", "Median": roe_median})


# Median Revenue
revenue_median = sector_df["revenue_value"].median()

if pd.notna(revenue_median):

    median_rows.append({"Metric": "Revenue / Sales", "Median": revenue_median})


# Median Market Cap
market_cap_median = sector_df["market_cap_crore"].median()

if pd.notna(market_cap_median):

    median_rows.append({"Metric": "Market Cap (₹ Cr)", "Median": market_cap_median})


median_df = pd.DataFrame(median_rows)


if median_df.empty:

    st.info("Sector median KPI data is unavailable.")

else:

    fig_median = px.bar(
        median_df,
        x="Metric",
        y="Median",
        text="Median",
        title=(f"{selected_sector} — " "Median Financial KPIs"),
    )

    fig_median.update_traces(texttemplate="%{text:.2f}", textposition="outside")

    fig_median.update_layout(height=450, margin=dict(l=20, r=20, t=60, b=20))

    st.plotly_chart(fig_median, use_container_width=True)


# ============================================================
# COMPANY TABLE
# ============================================================

st.subheader("🏢 Companies in Selected Sector")

table_df = sector_df[
    ["company_id", "company_name", "revenue_value", "roe_value", "market_cap_crore"]
].copy()


table_df = table_df.rename(
    columns={
        "company_id": "Company ID",
        "company_name": "Company Name",
        "revenue_value": "Revenue / Sales",
        "roe_value": "ROE (%)",
        "market_cap_crore": "Market Cap (₹ Cr)",
    }
)


st.dataframe(table_df, use_container_width=True, hide_index=True)


# ============================================================
# STATUS
# ============================================================

st.caption(f"Showing {len(sector_df)} companies in " f"{selected_sector}.")
