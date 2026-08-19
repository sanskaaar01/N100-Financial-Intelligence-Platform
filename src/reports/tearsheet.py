import sqlite3
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

matplotlib.use("Agg")

import matplotlib.pyplot as plt

# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "db" / "nifty100.db"

PROS_CONS_PATH = ROOT / "output" / "pros_cons_generated.csv"

CASHFLOW_PATH = ROOT / "output" / "cashflow_intelligence.xlsx"

OUTPUT_DIR = ROOT / "reports" / "tearsheets"

TEMP_DIR = ROOT / "reports" / "temp"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# PDF SETTINGS
# ============================================================

PAGE_WIDTH, PAGE_HEIGHT = A4

MARGIN = 12 * mm

NAVY = colors.HexColor("#0B1F3A")
LIGHT_NAVY = colors.HexColor("#EAF0F7")
GREEN = colors.HexColor("#16834A")
LIGHT_GREEN = colors.HexColor("#E9F7EF")
RED = colors.HexColor("#B42318")
LIGHT_RED = colors.HexColor("#FDECEC")
GREY = colors.HexColor("#667085")
LIGHT_GREY = colors.HexColor("#F2F4F7")
DARK = colors.HexColor("#1D2939")
WHITE = colors.white


# ============================================================
# DATABASE
# ============================================================


def get_connection():
    return sqlite3.connect(DB_PATH)


def query_df(sql, params=()):
    conn = get_connection()

    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


# ============================================================
# HELPERS
# ============================================================


def clean_number(value):

    if value is None:
        return np.nan

    try:
        return float(value)
    except Exception:
        return np.nan


def fmt(value, decimals=1):

    value = clean_number(value)

    if pd.isna(value):
        return "N/A"

    return f"{value:,.{decimals}f}"


def safe_filename(text):

    text = str(text)

    invalid = '<>:"/\\|?*'

    for char in invalid:
        text = text.replace(char, "_")

    return text.strip() or "company"


def latest_row(df):

    if df.empty:
        return None

    temp = df.copy()

    temp["_year_num"] = pd.to_numeric(temp["year"], errors="coerce")

    temp = temp.sort_values("_year_num")

    return temp.iloc[-1]


def numeric_series(df, column):

    if column not in df.columns:
        return pd.Series(dtype=float)

    return pd.to_numeric(df[column], errors="coerce")


# ============================================================
# COMPANY DATA
# ============================================================


def load_company(company_id):

    company = query_df(
        """
        SELECT *
        FROM companies
        WHERE id = ?
        """,
        (company_id,),
    )

    if company.empty:
        raise ValueError(f"Company not found: {company_id}")

    company = company.iloc[0]

    pnl = query_df(
        """
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
        """,
        (company_id,),
    )

    bs = query_df(
        """
        SELECT *
        FROM balancesheet
        WHERE company_id = ?
        """,
        (company_id,),
    )

    cf = query_df(
        """
        SELECT *
        FROM cashflow
        WHERE company_id = ?
        """,
        (company_id,),
    )

    ratios = query_df(
        """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
        """,
        (company_id,),
    )

    return company, pnl, bs, cf, ratios


# ============================================================
# PROS / CONS
# ============================================================


def load_pros_cons(company_id):

    if not PROS_CONS_PATH.exists():
        return [], []

    df = pd.read_csv(PROS_CONS_PATH)

    df = df[df["company_id"].astype(str) == str(company_id)]

    pros = df[df["type"].astype(str).str.lower() == "pro"]

    cons = df[df["type"].astype(str).str.lower() == "con"]

    return (
        pros["text"].dropna().tolist(),
        cons["text"].dropna().tolist(),
    )


# ============================================================
# CAPITAL ALLOCATION
# ============================================================


def load_capital_allocation(company_id):

    if not CASHFLOW_PATH.exists():
        return "N/A"

    try:

        df = pd.read_excel(CASHFLOW_PATH)

        row = df[df["company_id"].astype(str) == str(company_id)]

        if row.empty:
            return "N/A"

        return str(row.iloc[0].get("capital_allocation_label", "N/A"))

    except Exception:
        return "N/A"


# ============================================================
# KPI CALCULATIONS
# ============================================================


def build_kpis(
    company,
    pnl,
    bs,
    cf,
    ratios,
):

    latest_ratio = latest_row(ratios)

    latest_pnl = latest_row(pnl)

    latest_bs = latest_row(bs)

    latest_cf = latest_row(cf)

    kpis = {}

    if latest_pnl is not None:

        kpis["Revenue"] = latest_pnl.get("sales", np.nan)

        kpis["Net Profit"] = latest_pnl.get("net_profit", np.nan)

        kpis["EPS"] = latest_pnl.get("eps", np.nan)

    else:

        kpis["Revenue"] = np.nan
        kpis["Net Profit"] = np.nan
        kpis["EPS"] = np.nan

    if latest_ratio is not None:

        kpis["ROE"] = latest_ratio.get(
            "return_on_equity_pct", company.get("roe_percentage", np.nan)
        )

        kpis["OPM"] = latest_ratio.get("operating_profit_margin_pct", np.nan)

        kpis["D/E"] = latest_ratio.get("debt_to_equity", np.nan)

    else:

        kpis["ROE"] = company.get("roe_percentage", np.nan)

        kpis["OPM"] = np.nan
        kpis["D/E"] = np.nan

    if latest_cf is not None:

        kpis["CFO"] = latest_cf.get("operating_activity", np.nan)

        kpis["FCF"] = clean_number(
            latest_cf.get("operating_activity", np.nan)
        ) + clean_number(latest_cf.get("investing_activity", np.nan))

    else:

        kpis["CFO"] = np.nan
        kpis["FCF"] = np.nan

    return kpis


# ============================================================
# CHART 1 - REVENUE / PROFIT
# ============================================================


def create_revenue_profit_chart(
    pnl,
    company_id,
):

    if pnl.empty:
        return None

    data = pnl.copy()

    data["year_num"] = pd.to_numeric(data["year"], errors="coerce")

    data["sales_num"] = pd.to_numeric(data["sales"], errors="coerce")

    data["profit_num"] = pd.to_numeric(data["net_profit"], errors="coerce")

    data = data.dropna(subset=["year_num"]).sort_values("year_num")

    data = data.tail(10)

    if data.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, 2.8))

    x = np.arange(len(data))

    width = 0.36

    ax.bar(
        x - width / 2,
        data["sales_num"].fillna(0),
        width,
        label="Revenue",
    )

    ax.bar(
        x + width / 2,
        data["profit_num"].fillna(0),
        width,
        label="Net Profit",
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        data["year_num"].astype(int).astype(str),
        rotation=45,
        ha="right",
        fontsize=7,
    )

    ax.set_ylabel("₹ Crore", fontsize=8)

    ax.set_title(
        "10-Year Revenue & Net Profit",
        fontsize=10,
        fontweight="bold",
    )

    ax.grid(axis="y", alpha=0.2)

    ax.legend(
        fontsize=7,
        loc="upper left",
    )

    fig.tight_layout()

    path = TEMP_DIR / f"{company_id}_revenue_profit.png"

    fig.savefig(
        path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)

    return path


# ============================================================
# CHART 2 - ROE / ROCE
# ============================================================


def create_return_chart(
    ratios,
    company_id,
):

    if ratios.empty:
        return None

    data = ratios.copy()

    data["year_num"] = pd.to_numeric(data["year"], errors="coerce")

    data["roe_num"] = pd.to_numeric(data["return_on_equity_pct"], errors="coerce")

    data = data.dropna(subset=["year_num"]).sort_values("year_num")

    data = data.tail(10)

    if data.empty:
        return None

    # ROCE may not exist in financial_ratios.
    # If unavailable, use ROE only rather than inventing values.

    roce_col = None

    for col in [
        "roce_pct",
        "return_on_capital_employed_pct",
        "roce_percentage",
    ]:
        if col in data.columns:
            roce_col = col
            break

    fig, ax = plt.subplots(figsize=(8, 2.8))

    ax.plot(
        data["year_num"],
        data["roe_num"],
        marker="o",
        linewidth=2,
        label="ROE",
    )

    if roce_col:

        data["roce_num"] = pd.to_numeric(data[roce_col], errors="coerce")

        ax.plot(
            data["year_num"],
            data["roce_num"],
            marker="o",
            linewidth=2,
            label="ROCE",
        )

    ax.set_title(
        "ROE / ROCE Trend",
        fontsize=10,
        fontweight="bold",
    )

    ax.set_ylabel("%", fontsize=8)

    ax.grid(alpha=0.2)

    ax.legend(fontsize=7)

    fig.tight_layout()

    path = TEMP_DIR / f"{company_id}_returns.png"

    fig.savefig(
        path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)

    return path


# ============================================================
# BALANCE SHEET CHART
# ============================================================


def create_balance_chart(
    bs,
    company_id,
):

    if bs.empty:
        return None

    data = bs.copy()

    data["year_num"] = pd.to_numeric(data["year"], errors="coerce")

    data = data.dropna(subset=["year_num"]).sort_values("year_num")

    data = data.tail(10)

    if data.empty:
        return None

    equity = numeric_series(data, "equity_capital").fillna(0) + numeric_series(
        data, "reserves"
    ).fillna(0)

    borrowings = numeric_series(data, "borrowings").fillna(0)

    other = numeric_series(data, "other_liabilities").fillna(0)

    fig, ax = plt.subplots(figsize=(8, 2.8))

    x = np.arange(len(data))

    ax.bar(
        x,
        equity,
        label="Equity",
    )

    ax.bar(
        x,
        borrowings,
        bottom=equity,
        label="Borrowings",
    )

    ax.bar(
        x,
        other,
        bottom=equity + borrowings,
        label="Other Liabilities",
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        data["year_num"].astype(int).astype(str),
        rotation=45,
        ha="right",
        fontsize=7,
    )

    ax.set_ylabel("₹ Crore", fontsize=8)

    ax.set_title(
        "Balance Sheet Composition",
        fontsize=10,
        fontweight="bold",
    )

    ax.legend(fontsize=7)

    ax.grid(axis="y", alpha=0.2)

    fig.tight_layout()

    path = TEMP_DIR / f"{company_id}_balance.png"

    fig.savefig(
        path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)

    return path


# ============================================================
# CASH FLOW CHART
# ============================================================


def create_cashflow_chart(
    cf,
    company_id,
):

    if cf.empty:
        return None

    row = latest_row(cf)

    if row is None:
        return None

    labels = [
        "CFO",
        "CFI",
        "CFF",
        "Net Cash Flow",
    ]

    values = [
        clean_number(row.get("operating_activity", np.nan)),
        clean_number(row.get("investing_activity", np.nan)),
        clean_number(row.get("financing_activity", np.nan)),
        clean_number(row.get("net_cash_flow", np.nan)),
    ]

    values = [0 if pd.isna(v) else v for v in values]

    fig, ax = plt.subplots(figsize=(8, 2.6))

    x = np.arange(len(labels))

    ax.bar(
        x,
        values,
    )

    ax.axhline(
        0,
        linewidth=0.8,
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        labels,
        fontsize=8,
    )

    ax.set_ylabel(
        "₹ Crore",
        fontsize=8,
    )

    ax.set_title(
        "Latest-Year Cash Flow",
        fontsize=10,
        fontweight="bold",
    )

    ax.grid(
        axis="y",
        alpha=0.2,
    )

    fig.tight_layout()

    path = TEMP_DIR / f"{company_id}_cashflow.png"

    fig.savefig(
        path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)

    return path


# ============================================================
# PDF HEADER / FOOTER
# ============================================================


def draw_page_header(
    canvas,
    doc,
):

    canvas.saveState()

    canvas.setFillColor(NAVY)

    canvas.rect(
        0,
        PAGE_HEIGHT - 18 * mm,
        PAGE_WIDTH,
        18 * mm,
        fill=1,
        stroke=0,
    )

    canvas.setFillColor(colors.HexColor("#98A2B3"))

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.drawRightString(
        PAGE_WIDTH - MARGIN,
        7 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# STYLES
# ============================================================


def build_styles():

    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "title",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=21,
            textColor=WHITE,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=WHITE,
        ),
        "section": ParagraphStyle(
            "section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=NAVY,
            spaceBefore=3,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=DARK,
        ),
        "small": ParagraphStyle(
            "small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8,
            textColor=GREY,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            leftIndent=9,
            firstLineIndent=-6,
            textColor=DARK,
            spaceAfter=2,
        ),
        "kpi_value": ParagraphStyle(
            "kpi_value",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            alignment=TA_CENTER,
            textColor=NAVY,
        ),
        "kpi_label": ParagraphStyle(
            "kpi_label",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8,
            alignment=TA_CENTER,
            textColor=GREY,
        ),
        "badge": ParagraphStyle(
            "badge",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            textColor=WHITE,
        ),
    }


# ============================================================
# KPI TILE
# ============================================================


def kpi_tile(
    label,
    value,
    styles,
):

    content = [
        Paragraph(
            str(value),
            styles["kpi_value"],
        ),
        Spacer(1, 2),
        Paragraph(
            str(label),
            styles["kpi_label"],
        ),
    ]

    table = Table(
        [[content]],
        colWidths=[52 * mm],
        rowHeights=[18 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_GREY,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#D0D5DD"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    return table


# ============================================================
# BUILD TEARSHEET
# ============================================================


def generate_tearsheet(
    company_id,
):

    company, pnl, bs, cf, ratios = load_company(company_id)

    company_name = str(company.get("company_name", company_id))

    sector = str(company.get("sector", "Unknown"))

    output_path = OUTPUT_DIR / f"{safe_filename(company_id)}_tearsheet.pdf"

    styles = build_styles()

    kpis = build_kpis(
        company,
        pnl,
        bs,
        cf,
        ratios,
    )

    pros, cons = load_pros_cons(company_id)

    capital_label = load_capital_allocation(company_id)

    revenue_chart = create_revenue_profit_chart(
        pnl,
        company_id,
    )

    returns_chart = create_return_chart(
        ratios,
        company_id,
    )

    balance_chart = create_balance_chart(
        bs,
        company_id,
    )

    cashflow_chart = create_cashflow_chart(
        cf,
        company_id,
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=23 * mm,
        bottomMargin=10 * mm,
        title=f"{company_name} Financial Tearsheat",
        author="N100 Financial Intelligence Platform",
    )

    story = []

    # ========================================================
    # PAGE 1 HEADER
    # ========================================================

    header = Table(
        [
            [
                [
                    Paragraph(
                        company_name,
                        styles["title"],
                    ),
                    Paragraph(
                        f"{company_id}  |  {sector}",
                        styles["subtitle"],
                    ),
                ]
            ]
        ],
        colWidths=[PAGE_WIDTH - 2 * MARGIN],
    )

    header.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    NAVY,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.append(header)

    story.append(Spacer(1, 5))

    # ========================================================
    # KPI TILES
    # ========================================================

    kpi_data = [
        [
            kpi_tile(
                "Revenue (₹ Cr)",
                fmt(kpis["Revenue"]),
                styles,
            ),
            kpi_tile(
                "Net Profit (₹ Cr)",
                fmt(kpis["Net Profit"]),
                styles,
            ),
            kpi_tile(
                "ROE",
                (
                    fmt(kpis["ROE"]) + "%"
                    if not pd.isna(clean_number(kpis["ROE"]))
                    else "N/A"
                ),
                styles,
            ),
        ],
        [
            kpi_tile(
                "OPM",
                (
                    fmt(kpis["OPM"]) + "%"
                    if not pd.isna(clean_number(kpis["OPM"]))
                    else "N/A"
                ),
                styles,
            ),
            kpi_tile(
                "Debt / Equity",
                fmt(kpis["D/E"]),
                styles,
            ),
            kpi_tile(
                "Free Cash Flow (₹ Cr)",
                fmt(kpis["FCF"]),
                styles,
            ),
        ],
    ]

    kpi_table = Table(
        kpi_data,
        colWidths=[
            55 * mm,
            55 * mm,
            55 * mm,
        ],
        hAlign="CENTER",
    )

    kpi_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]
        )
    )

    story.append(kpi_table)

    story.append(Spacer(1, 5))

    # ========================================================
    # CHARTS
    # ========================================================

    story.append(
        Paragraph(
            "Financial Performance",
            styles["section"],
        )
    )

    if revenue_chart:

        story.append(
            Image(
                str(revenue_chart),
                width=175 * mm,
                height=57 * mm,
            )
        )

    if returns_chart:

        story.append(
            Image(
                str(returns_chart),
                width=175 * mm,
                height=57 * mm,
            )
        )

    story.append(PageBreak())

    # ========================================================
    # PAGE 2 - BALANCE SHEET
    # ========================================================

    story.append(
        Paragraph(
            "Balance Sheet & Cash Flow Intelligence",
            styles["section"],
        )
    )

    if balance_chart:

        story.append(
            Image(
                str(balance_chart),
                width=175 * mm,
                height=57 * mm,
            )
        )

    story.append(Spacer(1, 3))

    if cashflow_chart:

        story.append(
            Image(
                str(cashflow_chart),
                width=175 * mm,
                height=53 * mm,
            )
        )

    story.append(Spacer(1, 3))

    # ========================================================
    # CAPITAL ALLOCATION BADGE
    # ========================================================

    capital_badge = Table(
        [
            [
                Paragraph(
                    f"CAPITAL ALLOCATION: {capital_label}",
                    styles["badge"],
                )
            ]
        ],
        colWidths=[PAGE_WIDTH - 2 * MARGIN],
    )

    capital_badge.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    NAVY,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    NAVY,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(capital_badge)

    story.append(Spacer(1, 5))

    # ========================================================
    # PROS / CONS
    # ========================================================

    pros_text = []

    for text in pros[:6]:

        pros_text.append(
            Paragraph(
                f"• {text!s}",
                styles["bullet"],
            )
        )

    if not pros_text:

        pros_text.append(
            Paragraph(
                "• No qualifying positive signal available.",
                styles["bullet"],
            )
        )

    cons_text = []

    for text in cons[:6]:

        cons_text.append(
            Paragraph(
                f"• {text!s}",
                styles["bullet"],
            )
        )

    if not cons_text:

        cons_text.append(
            Paragraph(
                "• No qualifying negative signal available.",
                styles["bullet"],
            )
        )

    pros_box = Table(
        [
            [
                Paragraph(
                    "<b>PROS</b>",
                    styles["body"],
                )
            ],
            [pros_text],
        ],
        colWidths=[87 * mm],
    )

    pros_box.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_GREEN,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    GREEN,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#A6D8BA"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    cons_box = Table(
        [
            [
                Paragraph(
                    "<b>CONS</b>",
                    styles["body"],
                )
            ],
            [cons_text],
        ],
        colWidths=[87 * mm],
    )

    cons_box.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_RED,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    RED,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#F2A9A1"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    pros_cons_table = Table(
        [
            [
                pros_box,
                cons_box,
            ]
        ],
        colWidths=[
            89 * mm,
            89 * mm,
        ],
    )

    pros_cons_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    1,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    1,
                ),
            ]
        )
    )

    story.append(pros_cons_table)

    # ========================================================
    # BUILD PDF
    # ========================================================

    doc.build(
        story,
        onFirstPage=draw_page_header,
        onLaterPages=draw_page_header,
    )

    return output_path


# ============================================================
# TEST 5 COMPANIES
# ============================================================


def main():

    test_companies = [
        "TCS",
        "HDFCBANK",
        "RELIANCE",
        "SUNPHARMA",
        "TATASTEEL",
    ]

    print()
    print("========================================")
    print("       DAY 33 TEARSHEET TEST")
    print("========================================")
    print()

    results = []

    for company_id in test_companies:

        try:

            path = generate_tearsheet(company_id)

            size = path.stat().st_size

            print(f"✅ {company_id}: " f"{size:,} bytes")

            results.append((company_id, True, size))

        except Exception as exc:

            print(f"❌ {company_id}: " f"{type(exc).__name__}: {exc}")

            results.append((company_id, False, 0))

    print()
    print("========================================")
    print("       DAY 33 TEST RESULTS")
    print("========================================")
    print()

    passed = 0

    for company_id, ok, size in results:

        if ok:

            print(f"PASS  {company_id:<12} " f"{size:,} bytes")

            passed += 1

        else:

            print(f"FAIL  {company_id}")

    print()

    if passed == len(test_companies):

        print("✅ ALL 5 TEARSHEETS GENERATED")

        print("Next: VISUAL CHECK OF THE PDFs")

    else:

        print(f"❌ {len(test_companies) - passed} " "tearsheet(s) failed")

        raise SystemExit(1)


if __name__ == "__main__":
    main()
