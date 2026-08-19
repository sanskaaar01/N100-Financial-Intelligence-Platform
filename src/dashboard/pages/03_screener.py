import streamlit as st

from src.screener.engine import load_financial_data, run_screener

st.title("Screener")
st.caption("Filter the Nifty 100 universe using financial and valuation metrics.")

# ============================================================
# PRESETS
# ============================================================

PRESETS = {
    "Quality": {
        "roe_min": 15,
        "debt_to_equity_max": 1,
        "free_cash_flow_min": 0,
        "revenue_cagr_5yr_min": 10,
    },
    "Value": {
        "pe_ratio_max": 20,
        "pb_ratio_max": 3,
        "debt_to_equity_max": 2,
        "dividend_yield_min": 1,
    },
    "Growth": {
        "pat_cagr_5yr_min": 20,
        "revenue_cagr_5yr_min": 15,
        "debt_to_equity_max": 2,
    },
    "Dividend": {
        "dividend_yield_min": 2,
        "dividend_payout_ratio_max": 80,
        "free_cash_flow_min": 0,
    },
    "Debt-Free": {
        "debt_to_equity_max": 0,
        "roe_min": 12,
        "sales_min": 5000,
    },
    "Turnaround": {
        "revenue_cagr_3yr_min": 10,
        "free_cash_flow_min": 0,
    },
}

# ============================================================
# LOAD DATA
# ============================================================

try:
    universe = load_financial_data()
except Exception as e:
    st.error(f"Unable to load screener data: {e}")
    st.stop()

if universe.empty:
    st.warning("No financial data available.")
    st.stop()

# ============================================================
# PRESET BUTTONS
# ============================================================

st.subheader("Preset Screeners")

cols = st.columns(6)

selected_preset = None

for i, name in enumerate(PRESETS):
    with cols[i]:
        if st.button(name, use_container_width=True):
            selected_preset = name

if selected_preset:
    st.session_state["selected_preset"] = selected_preset

active_preset = st.session_state.get("selected_preset")

if active_preset:
    st.info(f"Active preset: {active_preset}")

# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.header("Screener Filters")


def preset_value(key, default):
    if active_preset and key in PRESETS.get(active_preset, {}):
        return PRESETS[active_preset][key]
    return default


roe_min = st.sidebar.number_input(
    "ROE minimum (%)",
    min_value=-100.0,
    max_value=500.0,
    value=float(preset_value("roe_min", 0)),
    step=1.0,
)

de_max = st.sidebar.number_input(
    "D/E maximum",
    min_value=0.0,
    max_value=20.0,
    value=float(preset_value("debt_to_equity_max", 20)),
    step=0.1,
)

fcf_min = st.sidebar.number_input(
    "FCF minimum (Cr)",
    min_value=-100000.0,
    max_value=100000.0,
    value=float(preset_value("free_cash_flow_min", -100000)),
    step=100.0,
)

rev_cagr_min = st.sidebar.number_input(
    "Revenue CAGR 5Y minimum (%)",
    min_value=-100.0,
    max_value=200.0,
    value=float(preset_value("revenue_cagr_5yr_min", -100)),
    step=1.0,
)

pat_cagr_min = st.sidebar.number_input(
    "PAT CAGR 5Y minimum (%)",
    min_value=-100.0,
    max_value=200.0,
    value=float(preset_value("pat_cagr_5yr_min", -100)),
    step=1.0,
)

opm_min = st.sidebar.number_input(
    "OPM minimum (%)",
    min_value=-100.0,
    max_value=100.0,
    value=float(preset_value("opm_min", -100)),
    step=1.0,
)

pe_max = st.sidebar.number_input(
    "P/E maximum",
    min_value=0.0,
    max_value=500.0,
    value=float(preset_value("pe_ratio_max", 500)),
    step=1.0,
)

pb_max = st.sidebar.number_input(
    "P/B maximum",
    min_value=0.0,
    max_value=100.0,
    value=float(preset_value("pb_ratio_max", 100)),
    step=0.5,
)

div_yield_min = st.sidebar.number_input(
    "Dividend Yield minimum (%)",
    min_value=0.0,
    max_value=50.0,
    value=float(preset_value("dividend_yield_min", 0)),
    step=0.5,
)

icr_min = st.sidebar.number_input(
    "Interest Coverage minimum",
    min_value=0.0,
    max_value=100.0,
    value=float(preset_value("interest_coverage_min", 0)),
    step=0.5,
)

# ============================================================
# RUN SCREENER
# ============================================================

filters = {}

if roe_min != 0:
    filters["roe_min"] = roe_min

if de_max != 20:
    filters["debt_to_equity_max"] = de_max

if fcf_min != -100000:
    filters["free_cash_flow_min"] = fcf_min

if rev_cagr_min != -100:
    filters["revenue_cagr_5yr_min"] = rev_cagr_min

if pat_cagr_min != -100:
    filters["pat_cagr_5yr_min"] = pat_cagr_min

if opm_min != -100:
    filters["operating_profit_margin_pct_min"] = opm_min

if pe_max != 500:
    filters["pe_ratio_max"] = pe_max

if pb_max != 100:
    filters["pb_ratio_max"] = pb_max

if div_yield_min != 0:
    filters["dividend_yield_min"] = div_yield_min

if icr_min != 0:
    filters["interest_coverage_min"] = icr_min

try:
    results = run_screener(filters=filters)
except Exception as e:
    st.error(f"Screener error: {e}")
    st.stop()

# ============================================================
# RESULT COUNT
# ============================================================

st.divider()

st.subheader(f"{len(results)} companies match your filters")

# ============================================================
# DISPLAY COLUMNS
# ============================================================

preferred_columns = [
    "company_id",
    "company_name",
    "broad_sector",
    "year",
    "composite_quality_score",
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin_pct",
    "interest_coverage",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
]

display_columns = [c for c in preferred_columns if c in results.columns]

if display_columns:
    table = results[display_columns].copy()
else:
    table = results.copy()

# ============================================================
# FORMAT
# ============================================================

numeric_columns = table.select_dtypes(include="number").columns

for col in numeric_columns:
    table[col] = table[col].round(2)

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
)

# ============================================================
# CSV DOWNLOAD
# ============================================================

csv_data = table.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Screener Results CSV",
    data=csv_data,
    file_name="screener_results.csv",
    mime="text/csv",
    use_container_width=True,
)

st.caption(
    "Financials-sector companies are handled according to the screener engine's D/E rules."
)
