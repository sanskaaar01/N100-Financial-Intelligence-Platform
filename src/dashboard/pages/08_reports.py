import re
import sqlite3

import pandas as pd
import streamlit as st

from src.dashboard.utils.db import DB_PATH, get_companies


st.title("Annual Reports")
st.caption("Browse available annual reports for Nifty 100 companies.")


# ------------------------------------------------------------
# LOAD COMPANIES
# ------------------------------------------------------------

companies = get_companies()


if companies.empty:
    st.warning("Company data is unavailable.")
    st.stop()


company_ids = sorted(
    companies["company_id"]
    .dropna()
    .astype(str)
    .unique()
)


# ------------------------------------------------------------
# COMPANY SEARCH
# ------------------------------------------------------------

search = st.text_input(
    "Search company",
    placeholder="Type company name or ticker...",
)


filtered = companies.copy()


if search.strip():

    search_lower = search.strip().lower()

    filtered = filtered[
        filtered["company_id"]
        .astype(str)
        .str.lower()
        .str.contains(
            search_lower,
            na=False,
        )
        |
        filtered["company_name"]
        .astype(str)
        .str.lower()
        .str.contains(
            search_lower,
            na=False,
        )
    ]


if filtered.empty:

    st.warning(
        "Ticker not found — please try another."
    )

    st.stop()


options = filtered["company_id"].astype(str).tolist()


ticker = st.selectbox(
    "Select Company",
    options,
)


# ------------------------------------------------------------
# LOAD DOCUMENTS
# ------------------------------------------------------------

@st.cache_data(ttl=600)
def load_reports(company_id):

    conn = sqlite3.connect(
        str(DB_PATH)
    )

    try:

        return pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                annual_report
            FROM documents
            WHERE company_id = ?
            ORDER BY year DESC
            """,
            conn,
            params=[company_id],
        )

    finally:

        conn.close()


reports = load_reports(ticker)


# ------------------------------------------------------------
# COMPANY HEADER
# ------------------------------------------------------------

company_row = companies[
    companies["company_id"].astype(str)
    == str(ticker)
]


if not company_row.empty:

    row = company_row.iloc[0]

    company_name = row.get(
        "company_name",
        ticker,
    )

    sector = row.get(
        "broad_sector",
        "N/A",
    )

    st.subheader(
        str(company_name)
    )

    st.caption(
        f"{ticker} • {sector}"
    )


# ------------------------------------------------------------
# REPORTS
# ------------------------------------------------------------

if reports.empty:

    st.info(
        "No annual reports are available for this company."
    )

    st.stop()


st.success(
    f"{len(reports)} annual report records found."
)


st.subheader("Available Annual Reports")


# ------------------------------------------------------------
# URL EXTRACTION
# ------------------------------------------------------------

def extract_url(value):

    if pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    # Markdown URL:
    # [https://example.com/file.pdf](https://example.com/file.pdf)

    match = re.search(
        r"\]\((https?://[^)]+)\)",
        text,
    )

    if match:
        return match.group(1)


    # Plain URL fallback

    match = re.search(
        r"https?://\S+",
        text,
    )

    if match:

        url = match.group(0)

        # Remove common trailing characters
        url = url.rstrip(
            ")]}>\"'"
        )

        return url


    return None


# ------------------------------------------------------------
# REPORT CARDS
# ------------------------------------------------------------

for _, report in reports.iterrows():

    year = report.get(
        "year",
        "Unknown",
    )

    raw_url = report.get(
        "annual_report",
        None,
    )

    url = extract_url(
        raw_url
    )


    with st.container(
        border=True
    ):

        col1, col2, col3 = st.columns(
            [2, 5, 2]
        )


        with col1:

            st.markdown(
                f"### {year}"
            )


        with col2:

            if url:

                st.caption(
                    "BSE annual report available"
                )

            else:

                st.error(
                    "Report unavailable"
                )


        with col3:

            if url:

                st.link_button(
                    "Open PDF",
                    url,
                    use_container_width=True,
                )

            else:

                st.write(
                    "Unavailable"
                )


# ------------------------------------------------------------
# RAW DATA OPTION
# ------------------------------------------------------------

with st.expander(
    "View report data"
):

    st.dataframe(
        reports,
        use_container_width=True,
        hide_index=True,
    )
