import streamlit as st
import pandas as pd
import plotly.express as px

from src.dashboard.utils.db import (
    get_companies,
    get_latest_ratios,
    get_available_years,
    _read_query,
)


st.title("🏠 Nifty 100 Analytics")
st.caption("Financial Intelligence Platform — Market Overview")


# ============================================================
# LOAD DATA
# ============================================================

companies = get_companies()
ratios = get_latest_ratios()

if companies.empty:
    st.error("Company data could not be loaded.")
    st.stop()

if ratios.empty:
    st.error("Financial ratio data could not be loaded.")
    st.stop()


# ============================================================
# YEAR SELECTOR
# ============================================================

years = get_available_years()

if years:
    selected_year = st.sidebar.selectbox(
        "Analysis Year",
        years,
        index=len(years) - 1,
    )

    selected = ratios[
        ratios["year"].astype(str) == str(selected_year)
    ].copy()

    if selected.empty:
        selected = ratios.copy()
else:
    selected_year = "Latest"
    selected = ratios.copy()


# ============================================================
# COMPANY INFORMATION
# ============================================================

company_columns = [
    c
    for c in [
        "company_id",
        "company_name",
        "broad_sector",
        "sub_sector",
    ]
    if c in companies.columns
]

company_info = companies[
    company_columns
].drop_duplicates(
    subset=["company_id"]
)

df = selected.merge(
    company_info,
    on="company_id",
    how="left",
)


# ============================================================
# HELPERS
# ============================================================

def numeric_series(column):
    if column not in df.columns:
        return pd.Series(dtype=float)

    return pd.to_numeric(
        df[column],
        errors="coerce",
    ).dropna()


def median(column):
    values = numeric_series(column)

    if values.empty:
        return None

    return values.median()


def mean(column):
    values = numeric_series(column)

    if values.empty:
        return None

    return values.mean()


def fmt(value, suffix=""):
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:,.2f}{suffix}"


# ============================================================
# MARKET DATA
# ============================================================

try:
    market = _read_query(
        """
        SELECT
            company_id,
            pe_ratio,
            pb_ratio,
            dividend_yield_pct
        FROM market_cap
        """
    )
except Exception:
    market = pd.DataFrame()


median_pe = None

if not market.empty and "pe_ratio" in market.columns:
    pe_values = pd.to_numeric(
        market["pe_ratio"],
        errors="coerce",
    ).dropna()

    if not pe_values.empty:
        median_pe = pe_values.median()


# ============================================================
# SUMMARY METRICS
# ============================================================

average_roe = mean(
    "return_on_equity_pct"
)

median_de = median(
    "debt_to_equity"
)

median_revenue_cagr = median(
    "revenue_cagr_5yr"
)

total_companies = df["company_id"].nunique()

debt_free_count = 0

if "debt_to_equity" in df.columns:
    de_values = pd.to_numeric(
        df["debt_to_equity"],
        errors="coerce",
    )

    debt_free_count = int(
        (de_values == 0).sum()
    )


# ============================================================
# KPI CARDS
# ============================================================

st.subheader(
    f"Market Overview — {selected_year}"
)

c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    st.metric(
        "Average ROE",
        fmt(average_roe, "%"),
    )

with c2:
    st.metric(
        "Median P/E",
        fmt(median_pe),
    )

with c3:
    st.metric(
        "Median D/E",
        fmt(median_de),
    )

with c4:
    st.metric(
        "Total Companies",
        str(total_companies),
    )

with c5:
    st.metric(
        "Median Revenue CAGR",
        fmt(median_revenue_cagr, "%"),
    )

with c6:
    st.metric(
        "Debt-Free Companies",
        str(debt_free_count),
    )


st.divider()


# ============================================================
# SECTOR BREAKDOWN
# ============================================================

left, right = st.columns(2)


with left:

    st.subheader("🏭 Sector Breakdown")

    if "broad_sector" in df.columns:

        sector_data = (
            df.dropna(
                subset=["broad_sector"]
            )
            .groupby("broad_sector")["company_id"]
            .nunique()
            .reset_index(name="companies")
            .sort_values(
                "companies",
                ascending=False,
            )
        )

        if not sector_data.empty:

            fig = px.pie(
                sector_data,
                names="broad_sector",
                values="companies",
                hole=0.45,
            )

            fig.update_layout(
                height=450,
                margin=dict(
                    l=10,
                    r=10,
                    t=30,
                    b=10,
                ),
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

        else:
            st.info("Sector data unavailable.")

    else:
        st.info("Sector data unavailable.")


# ============================================================
# TOP 5 QUALITY COMPANIES
# ============================================================

with right:

    st.subheader("🏆 Top 5 Companies by Quality Score")

    if "composite_quality_score" in df.columns:

        top = df.copy()

        top["composite_quality_score"] = pd.to_numeric(
            top["composite_quality_score"],
            errors="coerce",
        )

        top = (
            top.dropna(
                subset=["composite_quality_score"]
            )
            .sort_values(
                "composite_quality_score",
                ascending=False,
            )
            .drop_duplicates(
                subset=["company_id"]
            )
            .head(5)
        )

        columns = [
            c
            for c in [
                "company_id",
                "company_name",
                "broad_sector",
                "composite_quality_score",
            ]
            if c in top.columns
        ]

        display = top[columns].copy()

        if "composite_quality_score" in display.columns:
            display[
                "composite_quality_score"
            ] = display[
                "composite_quality_score"
            ].round(2)

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            "Composite quality score unavailable."
        )


st.divider()

st.caption(
    "Nifty 100 Financial Intelligence Platform"
)
