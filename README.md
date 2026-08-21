````markdown
# 📊 N100 Financial Intelligence Platform

> An end-to-end financial intelligence platform for analyzing, screening, benchmarking, and comparing NIFTY 100 companies using financial statements, market data, financial ratios, machine learning, and automated analytics.

---

## 🚀 Overview

The **N100 Financial Intelligence Platform** transforms raw financial data into actionable insights for analysts and investors.

The platform covers **92 NIFTY 100 companies** and provides:

- 📈 Financial statement analysis
- 🔎 Multi-criteria stock screening
- 🏢 Company profiling
- 🏭 Sector intelligence
- 👥 Peer comparison
- 💰 Valuation & market-cap analysis
- 💵 Cash-flow & profitability KPIs
- 🤖 K-Means company clustering
- 🚨 Financial outlier detection
- 📊 Portfolio-level statistics
- 📄 Automated company tearsheets
- ⚡ REST APIs with FastAPI
- 🧪 Automated ETL, KPI, DQ & API testing

---

## 🏗️ System Architecture

```text
                 ┌─────────────────────┐
                 │   Financial Data    │
                 │  P&L / BS / CF /    │
                 │ Ratios / Market Data│
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │   ETL & Data       │
                 │ Cleaning / QA /     │
                 │ Transformation      │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │      SQLite        │
                 │   nifty100.db      │
                 └──────────┬──────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
      ┌───────────────┐           ┌───────────────┐
      │  Analytics    │           │    FastAPI    │
      │               │           │     REST API  │
      │ • KPIs        │           │               │
      │ • Clustering  │           │ • Screener    │
      │ • Outliers    │           │ • Profiles    │
      │ • Statistics  │           │ • Peers       │
      └───────┬───────┘           └───────┬───────┘
              │                           │
              └─────────────┬─────────────┘
                            ▼
                 ┌─────────────────────┐
                 │ Analyst Dashboard /  │
                 │ Reports / Tearsheet  │
                 └─────────────────────┘
````

---

## 🧩 Core Features

### 🔎 Financial Screener

Screen companies using financial criteria such as:

* ROE
* Debt-to-Equity
* P/E
* Free Cash Flow
* Revenue CAGR
* PAT CAGR
* Sector
* Profitability metrics

Example:

```http
GET /api/v1/screener?min_roe=15
```

---

### 🏢 Company Intelligence

Each company profile provides access to:

* Company information
* Historical P&L
* Balance Sheet
* Cash Flow
* Financial Ratios
* Market Capitalization
* Valuation metrics
* Financial documents
* Automated tearsheet

Example:

```http
GET /api/v1/companies/TCS
GET /api/v1/companies/TCS/pl
GET /api/v1/companies/TCS/bs
GET /api/v1/companies/TCS/cashflow
GET /api/v1/companies/TCS/ratios
GET /api/v1/companies/TCS/tearsheet
```

---

### 🏭 Sector Intelligence

Analyze companies at the sector level.

The platform currently contains **10 broad sectors** across the dataset.

```http
GET /api/v1/sectors
GET /api/v1/sectors/{sector}/companies
```

---

### 👥 Peer Benchmarking

Compare companies against their peers using:

* Financial ratios
* Profitability
* Growth
* Leverage
* Valuation
* Percentile rankings

This enables relative company analysis rather than relying only on absolute metrics.

---

### 🤖 Machine Learning — Company Clustering

K-Means clustering is used to segment companies according to financial characteristics.

The clustering pipeline uses:

* Return on Equity
* Debt-to-Equity
* Revenue CAGR
* FCF CAGR
* Operating Profit Margin

The system generates:

* Cluster assignments
* Cluster profiles
* Mean & median cluster statistics
* Elbow analysis

---

### 🚨 Financial Outlier Detection

The analytics engine identifies unusual financial behaviour using sector-level statistical analysis.

Metrics include:

* Net Profit Margin
* Operating Profit Margin
* ROE
* Debt-to-Equity
* Interest Coverage
* Asset Turnover
* Revenue CAGR
* PAT CAGR
* EPS CAGR
* Composite Quality Score

---

### 📊 Portfolio Statistics

The platform generates percentile-based statistics across the company universe.

Available percentile levels include:

```text
P10
P20
P30
P40
P50
P60
P70
P80
P90
```

This allows analysts to benchmark an individual company against the broader universe.

---

### 💵 Cash-Flow Intelligence

Cash-flow KPIs include:

* Free Cash Flow
* CFO Quality Ratio
* CFO Quality Classification
* Capex Intensity
* FCF Conversion Rate
* Capital Allocation Pattern

Capital allocation patterns can identify behaviours such as:

* Reinvestor
* Shareholder Returns
* Liquidating Assets
* Distress Signal
* Growth Funded by Debt
* Cash Accumulator
* Pre-Revenue
* Mixed

---

## 🗄️ Database

The platform uses **SQLite** as its analytical database.

### Core Tables

```text
companies
profitandloss
balancesheet
cashflow
financial_ratios
sectors
market_cap
peer_groups
peer_percentiles
stock_prices
analysis
prosandcons
documents
```

The database contains financial and analytical information covering **92 companies**.

---

## 🛠️ Tech Stack

### Programming

* Python

### Backend

* FastAPI
* Uvicorn
* REST APIs
* OpenAPI

### Data & Database

* Pandas
* NumPy
* SQLite
* SQL

### Machine Learning

* Scikit-learn
* K-Means Clustering
* StandardScaler
* Statistical Outlier Detection

### Visualization

* Matplotlib
* Plotly

### Testing & Quality

* Pytest
* Black
* Ruff
* API testing
* Data-quality testing
* KPI testing
* ETL testing
* Load testing

### Reporting

* ReportLab
* PDF Tearsheets
* OpenAPI Documentation

---

## 📁 Project Structure

```text
N100-Financial-Intelligence-Platform/
│
├── db/
│   └── nifty100.db
│
├── src/
│   ├── api/
│   │   └── main.py
│   │
│   ├── analytics/
│   │   ├── clustering.py
│   │   ├── cluster_profiling.py
│   │   ├── radar.py
│   │   └── cashflow_kpis.py
│   │
│   ├── etl/
│   └── dashboard/
│
├── tests/
│   ├── api/
│   ├── etl/
│   ├── kpi/
│   └── dq/
│
├── docs/
│   ├── analyst_guide.pdf
│   └── openapi.json
│
├── output/
│   ├── cluster_labels.csv
│   ├── outlier_report.csv
│   ├── portfolio_stats.csv
│   └── kmeans_clusters.csv
│
├── reports/
│   ├── pytest_report.html
│   ├── elbow_plot.png
│   └── correlation_heatmap.png
│
└── README.md
```

---

## ⚡ Installation

Clone the repository:

```bash
git clone https://github.com/sanskaaar01/N100-Financial-Intelligence-Platform.git
cd N100-Financial-Intelligence-Platform
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the API

Start FastAPI:

```bash
uvicorn src.api.main:app --reload --port 8000
```

API:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

OpenAPI specification:

```text
docs/openapi.json
```

---

## 🧪 Testing

The project includes automated tests covering:

* ETL
* KPI calculations
* Data-quality rules
* API endpoints
* Financial analytics

Run the complete test suite:

```bash
python -m pytest tests/ -q
```

### Final Test Result

```text
180 passed
```

---

## ⚡ Performance Validation

### Screener Load Test

10 concurrent screener requests were successfully processed.

```text
Total time:       0.140s
Max response:     0.138s
```

### Company Profile Performance

Validated across:

```text
TCS
INFY
RELIANCE
HDFCBANK
ICICIBANK
```

All company-profile API workflows completed successfully within the required performance threshold.

---

## 📄 Analyst Documentation

The project includes a **16-page Analyst Guide** covering:

* Platform overview
* Company analysis
* Financial statements
* KPIs
* Screener
* Sector analysis
* Peer comparison
* Valuation
* Portfolio statistics
* API usage
* Tearsheet generation
* Troubleshooting
* Testing
* Analyst workflow

---

## 📈 Generated Analytics

The platform generates analytical artifacts including:

```text
Cluster Labels
Cluster Profiles
Elbow Plot
Correlation Heatmap
Outlier Report
Portfolio Statistics
Company Tearsheets
Pytest Report
OpenAPI Specification
```

---

## 🎯 Key Engineering Outcomes

* **92** NIFTY 100 companies analyzed
* **180/180 automated tests passing**
* **10 concurrent API requests** validated
* **16-page analyst guide**
* REST API architecture with **FastAPI**
* ML-based **K-Means company segmentation**
* Automated **financial KPI engine**
* Statistical **outlier detection**
* Sector and peer-level benchmarking
* Automated PDF financial tearsheets

---

## 👨‍💻 Author

**Sanskar Bhosle**

B.Tech — Data Science


---

## 📌 Project Status

```text
████████████████████████████████  COMPLETE

ETL                     ✅
Database                ✅
Financial Analytics     ✅
KPI Engine              ✅
Machine Learning        ✅
FastAPI                 ✅
Dashboard               ✅
Testing                 ✅
Performance QA          ✅
Documentation           ✅
Reporting               ✅
```

