import streamlit as st
import pandas as pd
import plotly.express as px

from src.dashboard.utils.db import get_companies, get_ratios

st.title("Trend Analysis")
st.caption("10-year financial trend analysis for individual companies.")

companies = get_companies()

if companies.empty:
    st.warning("Company data unavailable.")
    st.stop()

company_ids = sorted(
    companies["company_id"]
    .dropna()
    .astype(str)
    .unique()
)

ticker = st.selectbox(
    "Select Company",
    company_ids
)

data = get_ratios(ticker)

if data.empty:
    st.warning("No trend data available for this company.")
    st.stop()

data = data.copy()

if "year" in data.columns:
    data["year"] = data["year"].astype(str)

metric_options = {
    "ROE": "return_on_equity_pct",
    "ROCE": "return_on_capital_employed_pct",
    "Net Profit Margin": "net_profit_margin_pct",
    "Operating Profit Margin": "operating_profit_margin_pct",
    "Debt to Equity": "debt_to_equity",
    "Revenue CAGR 5Y": "revenue_cagr_5yr",
    "PAT CAGR 5Y": "pat_cagr_5yr",
    "EPS CAGR 5Y": "eps_cagr_5yr",
    "Asset Turnover": "asset_turnover",
    "Interest Coverage": "interest_coverage",
}

available = {
    label: column
    for label, column in metric_options.items()
    if column in data.columns
}

selected = st.multiselect(
    "Select up to 3 metrics",
    list(available.keys()),
    default=list(available.keys())[:2],
    max_selections=3,
)

if not selected:
    st.info("Select at least one metric.")
    st.stop()

plot_data = data[
    ["year"] + [available[x] for x in selected]
].copy()

rename_map = {
    available[label]: label
    for label in selected
}

plot_data = plot_data.rename(
    columns=rename_map
)

plot_data = plot_data.sort_values("year")

fig = px.line(
    plot_data,
    x="year",
    y=selected,
    markers=True,
    title=f"{ticker} — Financial Trends",
)

fig.update_layout(
    height=550,
    hovermode="x unified",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)

st.dataframe(
    plot_data,
    use_container_width=True,
    hide_index=True,
)
