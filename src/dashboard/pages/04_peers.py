import sqlite3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import DB_PATH, get_peers, get_companies

st.title("Peer Comparison")
st.caption("Compare companies against their assigned peer groups.")

# ============================================================
# DATABASE HELPER
# ============================================================

@st.cache_data(ttl=600)
def load_peer_percentiles():
    conn = sqlite3.connect(str(DB_PATH))
    try:
        return pd.read_sql_query(
            """
            SELECT
                company_id,
                peer_group_name,
                metric,
                value,
                percentile_rank,
                year
            FROM peer_percentiles
            ORDER BY peer_group_name, company_id, metric
            """,
            conn,
        )
    finally:
        conn.close()


@st.cache_data(ttl=600)
def load_latest_ratios():
    conn = sqlite3.connect(str(DB_PATH))
    try:
        return pd.read_sql_query(
            """
            SELECT fr.*
            FROM financial_ratios fr
            INNER JOIN (
                SELECT company_id, MAX(year) AS latest_year
                FROM financial_ratios
                GROUP BY company_id
            ) x
            ON fr.company_id = x.company_id
            AND fr.year = x.latest_year
            """,
            conn,
        )
    finally:
        conn.close()


peer_data = load_peer_percentiles()

if peer_data.empty:
    st.warning("Peer percentile data is not available.")
    st.stop()

# ============================================================
# PEER GROUP SELECTION
# ============================================================

groups = sorted(
    peer_data["peer_group_name"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

if not groups:
    st.warning("No peer groups available.")
    st.stop()

selected_group = st.selectbox(
    "Select Peer Group",
    groups,
)

group_data = peer_data[
    peer_data["peer_group_name"] == selected_group
].copy()

if group_data.empty:
    st.info("No companies available for this peer group.")
    st.stop()

companies = sorted(
    group_data["company_id"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

selected_company = st.selectbox(
    "Select Company",
    companies,
)

# ============================================================
# COMPANY / PEER METRICS
# ============================================================

company_data = group_data[
    group_data["company_id"] == selected_company
].copy()

metric_order = [
    "ROE",
    "ROCE",
    "Net Profit Margin",
    "D/E",
    "FCF",
    "PAT CAGR 5yr",
    "Revenue CAGR 5yr",
    "EPS CAGR 5yr",
    "Interest Coverage",
    "Asset Turnover",
]

available_metrics = [
    m for m in metric_order
    if m in company_data["metric"].unique()
]

# ============================================================
# RADAR CHART
# ============================================================

if available_metrics:
    company_values = []
    peer_values = []

    for metric in available_metrics:
        row = company_data[
            company_data["metric"] == metric
        ]

        if row.empty:
            company_values.append(0)
        else:
            company_values.append(
                float(row.iloc[0]["percentile_rank"]) * 100
            )

        peer_rows = group_data[
            group_data["metric"] == metric
        ]

        if peer_rows.empty:
            peer_values.append(0)
        else:
            peer_values.append(
                float(
                    peer_rows["percentile_rank"]
                    .mean()
                ) * 100
            )

    theta = available_metrics

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=company_values + [company_values[0]],
            theta=theta + [theta[0]],
            fill="toself",
            name=selected_company,
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=peer_values + [peer_values[0]],
            theta=theta + [theta[0]],
            fill="none",
            name="Peer Average",
            line=dict(dash="dash"),
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
            )
        ),
        title=f"{selected_company} vs {selected_group}",
        height=600,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

# ============================================================
# PEER KPI TABLE
# ============================================================

st.subheader(f"{selected_group} — Peer Companies")

pivot = group_data.pivot_table(
    index="company_id",
    columns="metric",
    values="value",
    aggfunc="first",
).reset_index()

if not pivot.empty:
    ordered = [
        "company_id"
    ] + [
        m for m in metric_order
        if m in pivot.columns
    ]

    pivot = pivot[
        [c for c in ordered if c in pivot.columns]
    ]

    numeric = pivot.select_dtypes(
        include="number"
    ).columns

    for col in numeric:
        pivot[col] = pivot[col].round(2)

    st.dataframe(
        pivot,
        use_container_width=True,
        hide_index=True,
    )

# ============================================================
# PERCENTILE TABLE
# ============================================================

st.subheader("Percentile Rankings")

percentile_table = group_data.pivot_table(
    index="company_id",
    columns="metric",
    values="percentile_rank",
    aggfunc="first",
).reset_index()

if not percentile_table.empty:

    for col in percentile_table.columns:
        if col != "company_id":
            percentile_table[col] = (
                percentile_table[col] * 100
            ).round(1)

    st.dataframe(
        percentile_table,
        use_container_width=True,
        hide_index=True,
    )

st.caption("Percentile values are displayed as 0–100. Higher percentile indicates stronger relative performance.")
