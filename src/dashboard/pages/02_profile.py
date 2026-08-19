import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_pl,
    get_ratios,
)

st.title("🏢 Company Profile")


# ============================================================
# LOAD COMPANIES
# ============================================================

companies = get_companies()

if companies.empty:
    st.error("Company data could not be loaded.")
    st.stop()


# ============================================================
# SEARCH
# ============================================================

search_options = []

for _, row in companies.drop_duplicates(subset=["company_id"]).iterrows():

    ticker = str(row.get("company_id", ""))

    name = str(row.get("company_name", ticker))

    search_options.append(f"{ticker} — {name}")


search_options = sorted(search_options)


selected_search = st.selectbox(
    "🔍 Search Company / Ticker",
    search_options,
)


ticker = selected_search.split(" — ")[0]


# ============================================================
# COMPANY RECORD
# ============================================================

company_rows = companies[companies["company_id"].astype(str) == ticker]

if company_rows.empty:

    st.warning("Ticker not found — please try another")

    st.stop()


company = company_rows.iloc[0]


company_name = company.get(
    "company_name",
    ticker,
)

sector = company.get(
    "broad_sector",
    "N/A",
)

sub_sector = company.get(
    "sub_sector",
    "N/A",
)


# ============================================================
# COMPANY CARD
# ============================================================

st.subheader(f"{company_name}")

info1, info2, info3, info4 = st.columns(4)

with info1:
    st.write("**NSE Ticker**")
    st.write(ticker)

with info2:
    st.write("**Sector**")
    st.write(sector)

with info3:
    st.write("**Sub-sector**")
    st.write(sub_sector)

with info4:
    st.write("**Company ID**")
    st.write(ticker)


# ============================================================
# LOAD FINANCIAL DATA
# ============================================================

ratios = get_ratios(ticker)
pl = get_pl(ticker)


if ratios.empty:
    st.warning("Financial ratio data is not available for this company.")
    st.stop()


ratios = ratios.copy()


if "year" in ratios.columns:
    ratios["year"] = ratios["year"].astype(str)


# ============================================================
# LATEST YEAR
# ============================================================

latest = ratios.iloc[-1]


def get_value(column):
    if column not in latest.index:
        return None

    value = latest[column]

    if pd.isna(value):
        return None

    return value


def format_value(
    value,
    suffix="",
):
    if value is None:
        return "N/A"

    try:
        return f"{float(value):,.2f}{suffix}"
    except Exception:
        return str(value)


roe = get_value("return_on_equity_pct")

roce = get_value("return_on_capital_employed_pct")

npm = get_value("net_profit_margin_pct")

de = get_value("debt_to_equity")

revenue_cagr = get_value("revenue_cagr_5yr")

fcf = get_value("free_cash_flow_cr")


# ============================================================
# KPI TILES
# ============================================================

st.subheader(f"Latest Financial KPIs — {latest.get('year', 'Latest')}")

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.metric(
        "ROE",
        format_value(roe, "%"),
    )

with k2:
    st.metric(
        "ROCE",
        format_value(roce, "%"),
    )

with k3:
    st.metric(
        "Net Profit Margin",
        format_value(npm, "%"),
    )

with k4:
    st.metric(
        "Debt / Equity",
        format_value(de),
    )

with k5:
    st.metric(
        "Revenue CAGR 5Y",
        format_value(revenue_cagr, "%"),
    )

with k6:
    st.metric(
        "Free Cash Flow",
        format_value(fcf, " Cr"),
    )


st.divider()


# ============================================================
# PREPARE P&L
# ============================================================

if not pl.empty:

    pl = pl.copy()

    if "year" in pl.columns:
        pl["year"] = pl["year"].astype(str)

    if "sales" in pl.columns:
        pl["sales"] = pd.to_numeric(
            pl["sales"],
            errors="coerce",
        )

    if "net_profit" in pl.columns:
        pl["net_profit"] = pd.to_numeric(
            pl["net_profit"],
            errors="coerce",
        )

    if "operating_profit" in pl.columns:
        pl["operating_profit"] = pd.to_numeric(
            pl["operating_profit"],
            errors="coerce",
        )


# ============================================================
# REVENUE + NET PROFIT CHART
# ============================================================

st.subheader("📊 Revenue & Net Profit — Historical")

if (
    not pl.empty
    and "year" in pl.columns
    and "sales" in pl.columns
    and "net_profit" in pl.columns
):

    chart_data = (
        pl[
            [
                "year",
                "sales",
                "net_profit",
            ]
        ]
        .dropna(
            subset=["sales", "net_profit"],
            how="all",
        )
        .tail(10)
    )

    if not chart_data.empty:

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=chart_data["year"],
                y=chart_data["sales"],
                name="Revenue",
            )
        )

        fig.add_trace(
            go.Bar(
                x=chart_data["year"],
                y=chart_data["net_profit"],
                name="Net Profit",
            )
        )

        fig.update_layout(
            barmode="group",
            height=450,
            xaxis_title="Year",
            yaxis_title="Amount",
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
        st.info("Insufficient historical P&L data.")

else:
    st.info("Revenue and net profit history unavailable.")


# ============================================================
# ROE + ROCE CHART
# ============================================================

st.subheader("📈 ROE & ROCE Trend")

chart_ratios = ratios.tail(10).copy()

if "return_on_equity_pct" in chart_ratios.columns:

    chart_ratios["return_on_equity_pct"] = pd.to_numeric(
        chart_ratios["return_on_equity_pct"],
        errors="coerce",
    )

if "return_on_capital_employed_pct" in chart_ratios.columns:

    chart_ratios["return_on_capital_employed_pct"] = pd.to_numeric(
        chart_ratios["return_on_capital_employed_pct"],
        errors="coerce",
    )


if "year" in chart_ratios.columns and "return_on_equity_pct" in chart_ratios.columns:

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=chart_ratios["year"],
            y=chart_ratios["return_on_equity_pct"],
            mode="lines+markers",
            name="ROE",
        )
    )

    if "return_on_capital_employed_pct" in chart_ratios.columns:

        fig.add_trace(
            go.Scatter(
                x=chart_ratios["year"],
                y=chart_ratios["return_on_capital_employed_pct"],
                mode="lines+markers",
                name="ROCE",
                yaxis="y2",
            )
        )

    fig.update_layout(
        height=450,
        xaxis_title="Year",
        yaxis=dict(
            title="ROE (%)",
        ),
        yaxis2=dict(
            title="ROCE (%)",
            overlaying="y",
            side="right",
        ),
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
    st.info("ROE / ROCE history unavailable.")


# ============================================================
# PROS & CONS
# ============================================================

st.subheader("✅ Pros & ⚠️ Cons")

pros = []
cons = []


if roe is not None:
    try:
        if float(roe) >= 15:
            pros.append(f"ROE is strong at {float(roe):.2f}%.")
        elif float(roe) < 10:
            cons.append(f"ROE is relatively low at {float(roe):.2f}%.")
    except Exception:
        pass


if de is not None:
    try:
        if float(de) < 1:
            pros.append(f"Low leverage with D/E of {float(de):.2f}.")
        elif float(de) > 5:
            cons.append(f"High leverage with D/E of {float(de):.2f}.")
    except Exception:
        pass


if revenue_cagr is not None:
    try:
        if float(revenue_cagr) >= 10:
            pros.append(f"Strong 5-year revenue CAGR of {float(revenue_cagr):.2f}%.")
    except Exception:
        pass


if fcf is not None:
    try:
        if float(fcf) > 0:
            pros.append("Latest free cash flow is positive.")
        else:
            cons.append("Latest free cash flow is negative.")
    except Exception:
        pass


if not pros:
    pros.append("No major positive signal available.")

if not cons:
    cons.append("No major negative signal identified.")


left, right = st.columns(2)

with left:
    for item in pros:
        st.success(f"✓ {item}")

with right:
    for item in cons:
        st.error(f"✗ {item}")
