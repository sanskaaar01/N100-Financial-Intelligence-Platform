# N100 Financial Intelligence Platform

A financial analytics and intelligence platform built around the Nifty 100 universe.

The platform combines financial data processing, KPI analysis, screening, peer benchmarking, radar analysis, valuation analytics, and an interactive Streamlit dashboard.

---

## 1. Project Overview

The N100 Financial Intelligence Platform provides a structured analytical workflow for evaluating companies using financial statements, profitability ratios, leverage metrics, cash-flow indicators, peer comparisons, screening rules, and valuation multiples.

### Core Capabilities

- Financial data processing
- Financial KPI calculation
- Profitability analysis
- Leverage analysis
- Cash-flow analysis
- CAGR analysis
- Composite quality scoring
- Preset stock screeners
- Peer-group percentile analysis
- Peer comparison reports
- Peer radar charts
- Valuation analytics
- Interactive Streamlit dashboard
- Excel exports
- CSV exports
- Data-quality testing

---

# 2. Technology Stack

- Python
- Pandas
- NumPy
- SQLite
- Streamlit
- Plotly
- OpenPyXL
- Pytest
- SQL
- YAML

---

# 3. Project Structure

```text
N100-Financial-Intelligence-Platform/
│
├── db/
│   └── nifty100.db
│
├── output/
│   ├── screener_output.xlsx
│   ├── peer_comparison.xlsx
│   ├── valuation_summary.xlsx
│   └── valuation_flags.csv
│
├── reports/
│   └── radar_charts/
│
├── src/
│   ├── analytics/
│   │   ├── ratios.py
│   │   ├── cagr.py
│   │   ├── cashflow_kpis.py
│   │   ├── peer.py
│   │   ├── radar.py
│   │   ├── peer_comparison.py
│   │   └── valuation.py
│   │
│   ├── dashboard/
│   │   ├── app.py
│   │   ├── pages/
│   │   │   ├── 01_home.py
│   │   │   ├── 02_profile.py
│   │   │   ├── 03_screener.py
│   │   │   ├── 04_peers.py
│   │   │   ├── 05_trends.py
│   │   │   ├── 06_sectors.py
│   │   │   ├── 07_capital.py
│   │   │   └── 08_reports.py
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── db.py
│   │
│   └── screener/
│       └── engine.py
│
├── tests/
│   ├── dq/
│   ├── etl/
│   └── kpi/
│
└── README.md