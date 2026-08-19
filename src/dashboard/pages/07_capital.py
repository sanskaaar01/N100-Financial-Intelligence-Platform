import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import DB_PATH

st.title("Capital Allocation Map")
st.caption("Nifty 100 companies grouped by capital allocation pattern.")


@st.cache_data(ttl=600)
def load_capital_data():

    conn = sqlite3.connect(str(DB_PATH))

    try:
        tables = pd.read_sql_query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """,
            conn,
        )["name"].tolist()

        if "capital_allocation" in tables:

            return pd.read_sql_query(
                "SELECT * FROM capital_allocation",
                conn,
            )

        # Fallback: derive patterns from latest cash-flow data.
        cf = pd.read_sql_query(
            """
            SELECT *
            FROM cashflow
            """,
            conn,
        )

        return cf

    finally:
        conn.close()


data = load_capital_data()

if data.empty:
    st.warning("Capital allocation data is not available yet.")
    st.stop()

# ------------------------------------------------------------
# Find cash-flow columns
# ------------------------------------------------------------


def find_column(columns, candidates):

    lower = {str(x).lower(): x for x in columns}

    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]

    return None


cfo = find_column(
    data.columns,
    [
        "cash_from_operating",
        "cash_from_operations",
        "cfo",
        "operating_activity",
    ],
)

cfi = find_column(
    data.columns,
    [
        "cash_from_investing",
        "cfi",
        "investing_activity",
    ],
)

cff = find_column(
    data.columns,
    [
        "cash_from_financing",
        "cff",
        "financing_activity",
    ],
)

company = find_column(
    data.columns,
    [
        "company_id",
        "ticker",
        "symbol",
    ],
)

if not all([cfo, cfi, cff, company]):

    st.warning(
        "Capital allocation pattern data is not available in the current dataset."
    )

    st.dataframe(
        data.head(20),
        use_container_width=True,
        hide_index=True,
    )

    st.stop()


latest = data.copy()

latest["_year_num"] = (
    latest["year"].astype(str).str.extract(r"(\d{4})")[0].astype(float)
)

latest = latest.sort_values("_year_num").groupby(company, as_index=False).tail(1)

latest = latest.copy()

latest["cfo_sign"] = latest[cfo].apply(
    lambda x: "+" if pd.notna(x) and x > 0 else "-" if pd.notna(x) and x < 0 else "0"
)

latest["cfi_sign"] = latest[cfi].apply(
    lambda x: "+" if pd.notna(x) and x > 0 else "-" if pd.notna(x) and x < 0 else "0"
)

latest["cff_sign"] = latest[cff].apply(
    lambda x: "+" if pd.notna(x) and x > 0 else "-" if pd.notna(x) and x < 0 else "0"
)

patterns = {
    ("+", "-", "-"): "Reinvestor",
    ("+", "+", "-"): "Liquidating Assets",
    ("-", "+", "+"): "Distress Signal",
    ("-", "-", "+"): "Growth Funded by Debt",
    ("+", "+", "+"): "Cash Accumulator",
    ("-", "-", "-"): "Pre-Revenue",
    ("+", "-", "+"): "Mixed",
}

latest["pattern_label"] = latest.apply(
    lambda row: patterns.get(
        (
            row["cfo_sign"],
            row["cfi_sign"],
            row["cff_sign"],
        ),
        "Mixed",
    ),
    axis=1,
)

summary = latest["pattern_label"].value_counts().reset_index()

summary.columns = [
    "pattern_label",
    "companies",
]

fig = px.treemap(
    summary,
    path=["pattern_label"],
    values="companies",
    title="Capital Allocation Patterns",
)

fig.update_layout(height=600)

st.plotly_chart(
    fig,
    use_container_width=True,
)

selected_pattern = st.selectbox(
    "Select Pattern",
    sorted(latest["pattern_label"].dropna().unique()),
)

members = latest[latest["pattern_label"] == selected_pattern]

st.subheader(f"{selected_pattern} — {len(members)} Companies")

st.dataframe(
    members[
        [
            company,
            "cfo_sign",
            "cfi_sign",
            "cff_sign",
            "pattern_label",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)
