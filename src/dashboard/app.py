from pathlib import Path

import streamlit as st

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PAGES_DIR = BASE_DIR / "pages"


# ============================================================
# APPLICATION HEADER
# ============================================================

st.title("📊 Nifty 100 Analytics")
st.caption("Financial Intelligence Platform — Dashboard & Valuation")


# ============================================================
# PAGE DEFINITIONS
# ============================================================

page_definitions = [
    ("01_home.py", "Home", "🏠"),
    ("02_profile.py", "Company Profile", "🏢"),
    ("03_screener.py", "Screener", "🔎"),
    ("04_peers.py", "Peer Comparison", "👥"),
    ("05_trends.py", "Trend Analysis", "📈"),
    ("06_sectors.py", "Sector Analysis", "🏭"),
    ("07_capital.py", "Capital Allocation", "💰"),
    ("08_reports.py", "Annual Reports", "📄"),
]


# ============================================================
# CREATE ONLY EXISTING/VALID PAGES
# ============================================================

pages = []

for filename, title, icon in page_definitions:

    page_path = PAGES_DIR / filename

    if page_path.exists():
        pages.append(
            st.Page(
                page_path,
                title=title,
                icon=icon,
            )
        )


# ============================================================
# SAFETY CHECK
# ============================================================

if not pages:
    st.error(
        "No dashboard pages were found. "
        "Please create the pages directory and dashboard pages."
    )
    st.stop()


# ============================================================
# NAVIGATION
# ============================================================

pg = st.navigation(
    pages,
    position="sidebar",
)


# ============================================================
# RUN
# ============================================================

pg.run()
