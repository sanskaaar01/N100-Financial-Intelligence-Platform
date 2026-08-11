from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "reports" / "portfolio"
OUTPUT_PDF = OUTPUT_DIR / "portfolio_summary.pdf"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#14213D")
GREEN = colors.HexColor("#16803C")
RED = colors.HexColor("#C62828")
GREY = colors.HexColor("#666666")
LIGHT_GREY = colors.HexColor("#F2F4F7")
WHITE = colors.white


def get_connection():
    return sqlite3.connect(DB_PATH)


def query_df(connection, sql, params=()):
    return pd.read_sql_query(sql, connection, params=params)


def numeric(value):
    try:
        if value is None or pd.isna(value):
            return np.nan
        return float(value)
    except Exception:
        return np.nan


def latest_two(df, value_col):
    if df.empty or value_col not in df.columns:
        return np.nan, np.nan

    x = df.copy()

    if "year" in x.columns:
        x["_year_num"] = pd.to_numeric(
            x["year"].astype(str).str.extract(r"(\d{4})")[0],
            errors="coerce",
        )
        x = x.sort_values(["_year_num", "year"])

    values = pd.to_numeric(
        x[value_col],
        errors="coerce",
    ).dropna()

    if len(values) == 0:
        return np.nan, np.nan

    latest = float(values.iloc[-1])

    previous = (
        float(values.iloc[-2])
        if len(values) >= 2
        else np.nan
    )

    return latest, previous


def trend_arrow(latest, previous):
    if pd.isna(latest) or pd.isna(previous):
        return "→"

    if abs(previous) < 1e-12:
        if latest > 0:
            return "↑"
        if latest < 0:
            return "↓"
        return "→"

    change_pct = ((latest - previous) / abs(previous)) * 100

    if change_pct > 2:
        return "↑"

    if change_pct < -2:
        return "↓"

    return "→"


def fmt(value, suffix=""):
    if pd.isna(value):
        return "N/A"

    return f"{value:,.2f}{suffix}"


def load_inputs():
    conn = get_connection()

    companies = query_df(
        conn,
        """
        SELECT
            id AS company_id,
            company_name,
            COALESCE(
                (
                    SELECT peer_group_name
                    FROM peer_groups pg
                    WHERE pg.company_id = companies.id
                    LIMIT 1
                ),
                'Unknown'
            ) AS sector
        FROM companies
        ORDER BY id
        """,
    )

    ratios = query_df(
        conn,
        """
        SELECT *
        FROM financial_ratios
        """,
    )

    pnl = query_df(
        conn,
        """
        SELECT *
        FROM profitandloss
        """,
    )

    conn.close()

    cashflow_path = ROOT / "output" / "cashflow_intelligence.xlsx"
    cashflow = pd.read_excel(cashflow_path)

    return companies, ratios, pnl, cashflow


def build_company_kpis(company_id, ratios, pnl, cashflow):
    r = ratios[
        ratios["company_id"].astype(str) == str(company_id)
    ].copy()

    p = pnl[
        pnl["company_id"].astype(str) == str(company_id)
    ].copy()

    cf = cashflow[
        cashflow["company_id"].astype(str) == str(company_id)
    ].copy()

    roe, roe_prev = latest_two(
        r,
        "return_on_equity_pct",
    )

    roce, roce_prev = latest_two(
        r,
        "return_on_equity_pct",
    )

    revenue, revenue_prev = latest_two(
        p,
        "sales",
    )

    net_profit, profit_prev = latest_two(
        p,
        "net_profit",
    )

    eps, eps_prev = latest_two(
        p,
        "eps",
    )

    fcf, fcf_prev = latest_two(
        r,
        "free_cash_flow_cr",
    )

    return [
        ("Revenue", fmt(revenue, " Cr"), trend_arrow(revenue, revenue_prev)),
        ("Net Profit", fmt(net_profit, " Cr"), trend_arrow(net_profit, profit_prev)),
        ("ROE", fmt(roe, "%"), trend_arrow(roe, roe_prev)),
        ("ROCE", fmt(roce, "%"), trend_arrow(roce, roce_prev)),
        ("EPS", fmt(eps), trend_arrow(eps, eps_prev)),
        ("Free Cash Flow", fmt(fcf, " Cr"), trend_arrow(fcf, fcf_prev)),
    ]


def build_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="CompanyTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=NAVY,
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Subtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            textColor=GREY,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=NAVY,
            spaceBefore=10,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="KPIName",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=GREY,
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="KPIValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=NAVY,
            alignment=TA_CENTER,
        )
    )

    return styles


def kpi_table(kpis, styles):
    cells = []

    for name, value, arrow in kpis:
        arrow_color = (
            GREEN if arrow == "↑"
            else RED if arrow == "↓"
            else GREY
        )

        content = [
            Paragraph(name, styles["KPIName"]),
            Spacer(1, 2),
            Paragraph(value, styles["KPIValue"]),
            Spacer(1, 2),
            Paragraph(
                f'<font color="{arrow_color}"><b>{arrow}</b></font>',
                styles["KPIValue"],
            ),
        ]

        cells.append(content)

    rows = [
        cells[:3],
        cells[3:6],
    ]

    table = Table(
        rows,
        colWidths=[
            57 * mm,
            57 * mm,
            57 * mm,
        ],
        rowHeights=[
            30 * mm,
            30 * mm,
        ],
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
                    0.7,
                    colors.HexColor("#D5D9DE"),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#D5D9DE"),
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
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    return table


def build_pdf():
    companies, ratios, pnl, cashflow = load_inputs()

    companies = companies.sort_values(
        "company_id",
        key=lambda s: s.astype(str).str.upper(),
    )

    styles = build_styles()

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="N100 Portfolio Summary",
        author="N100 Financial Intelligence Platform",
    )

    story = []

    for index, company in companies.reset_index(drop=True).iterrows():
        company_id = str(company["company_id"])
        company_name = str(
            company.get("company_name", company_id)
        ).replace("\n", " ").strip()

        sector = str(
            company.get("sector", "Unknown")
        ).replace("\n", " ").strip()

        story.append(
            Paragraph(
                company_name,
                styles["CompanyTitle"],
            )
        )

        story.append(
            Paragraph(
                f"{company_id}  |  {sector}",
                styles["Subtitle"],
            )
        )

        story.append(Spacer(1, 8))

        story.append(
            Paragraph(
                "Portfolio Snapshot",
                styles["Section"],
            )
        )

        kpis = build_company_kpis(
            company_id,
            ratios,
            pnl,
            cashflow,
        )

        story.append(
            kpi_table(
                kpis,
                styles,
            )
        )

        story.append(Spacer(1, 12))

        story.append(
            Paragraph(
                "Trend Interpretation",
                styles["Section"],
            )
        )

        trend_rows = [
            [
                Paragraph("<b>Metric</b>", styles["Subtitle"]),
                Paragraph("<b>Latest</b>", styles["Subtitle"]),
                Paragraph("<b>Trend</b>", styles["Subtitle"]),
            ]
        ]

        for name, value, arrow in kpis:
            trend_rows.append(
                [
                    Paragraph(name, styles["Subtitle"]),
                    Paragraph(value, styles["Subtitle"]),
                    Paragraph(
                        f"<b>{arrow}</b>",
                        styles["Subtitle"],
                    ),
                ]
            )

        trend_table = Table(
            trend_rows,
            colWidths=[
                70 * mm,
                70 * mm,
                35 * mm,
            ],
        )

        trend_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        NAVY,
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        WHITE,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#D5D9DE"),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
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

        story.append(trend_table)

        story.append(Spacer(1, 14))

        story.append(
            Paragraph(
                "Trend logic: ↑ improved by more than 2%, ↓ declined by more than 2%, → remained within ±2%.",
                styles["Subtitle"],
            )
        )

        story.append(Spacer(1, 10))

        story.append(
            Paragraph(
                "N100 Financial Intelligence Platform • Sprint 5",
                styles["Subtitle"],
            )
        )

        if index < len(companies) - 1:
            story.append(PageBreak())

    doc.build(story)

    return OUTPUT_PDF


def main():
    print("========================================")
    print("       DAY 35 - PORTFOLIO SUMMARY")
    print("========================================")

    print()
    print("Building portfolio summary...")

    output = build_pdf()

    print()
    print("PASS - Portfolio PDF generated")
    print("Output:", output)
    print("Size:", output.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
