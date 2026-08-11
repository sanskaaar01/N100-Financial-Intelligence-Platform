import sqlite3
from pathlib import Path
from statistics import median

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
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
OUTPUT_DIR = ROOT / "reports" / "sector"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

NAVY = colors.HexColor("#102A43")
LIGHT = colors.HexColor("#EAF0F6")
WHITE = colors.white
GREY = colors.HexColor("#666666")


# ============================================================
# HELPERS
# ============================================================

def clean(value):

    if value is None:
        return ""

    return (
        str(value)
        .replace("\n", " ")
        .replace("\r", " ")
        .strip()
    )


def safe_filename(value):

    value = clean(value)

    for char in '<>:"/\\|?*':
        value = value.replace(char, "_")

    return value


def number(value):

    if value is None:
        return "-"

    try:
        return f"{float(value):,.2f}"

    except Exception:
        return "-"


def median_value(values):

    clean_values = []

    for value in values:

        try:

            if value is not None:
                clean_values.append(float(value))

        except Exception:
            pass

    if not clean_values:
        return None

    return median(clean_values)


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    conn = sqlite3.connect(DB_PATH)

    try:

        companies = conn.execute(
            """
            SELECT
                id,
                company_name,
                roe_percentage,
                roce_percentage
            FROM companies
            """
        ).fetchall()

        company_map = {}

        for row in companies:

            company_map[clean(row[0])] = {
                "company_id": clean(row[0]),
                "company_name": clean(row[1]),
                "roe": row[2],
                "roce": row[3],
            }

        peer_rows = conn.execute(
            """
            SELECT
                peer_group_name,
                company_id
            FROM peer_groups
            ORDER BY peer_group_name, company_id
            """
        ).fetchall()

        groups = {}

        for peer_group, company_id in peer_rows:

            peer_group = clean(peer_group)
            company_id = clean(company_id)

            if peer_group not in groups:
                groups[peer_group] = []

            if company_id in company_map:

                groups[peer_group].append(
                    company_map[company_id]
                )

        return groups

    finally:

        conn.close()


# ============================================================
# BUILD ONE SECTOR REPORT
# ============================================================

def build_report(
    sector,
    companies,
):

    filename = (
        OUTPUT_DIR
        / f"{safe_filename(sector)}_report.pdf"
    )

    doc = SimpleDocTemplate(
        str(filename),
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"{sector} Sector Report",
        author="N100 Financial Intelligence Platform",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "SectorTitle",
        parent=styles["Title"],
        fontSize=19,
        leading=22,
        alignment=TA_CENTER,
        textColor=NAVY,
        spaceAfter=5 * mm,
    )

    subtitle_style = ParagraphStyle(
        "SectorSubtitle",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=GREY,
        spaceAfter=6 * mm,
    )

    heading_style = ParagraphStyle(
        "SectorHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=NAVY,
        spaceBefore=4 * mm,
        spaceAfter=3 * mm,
    )

    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["BodyText"],
        fontSize=7,
        leading=8.5,
    )

    header_style = ParagraphStyle(
        "Header",
        parent=cell_style,
        textColor=WHITE,
        fontSize=7,
        leading=8.5,
    )

    story = []

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    story.append(
        Paragraph(
            f"{clean(sector)}",
            title_style,
        )
    )

    story.append(
        Paragraph(
            f"Peer Group Sector Report | "
            f"{len(companies)} Companies",
            subtitle_style,
        )
    )

    # --------------------------------------------------------
    # MEDIAN KPIs
    # --------------------------------------------------------

    roe_values = [
        x["roe"]
        for x in companies
    ]

    roce_values = [
        x["roce"]
        for x in companies
    ]

    summary_data = [
        [
            Paragraph(
                "<b>Sector KPI</b>",
                header_style,
            ),
            Paragraph(
                "<b>Median</b>",
                header_style,
            ),
        ],
        [
            Paragraph(
                "ROE %",
                cell_style,
            ),
            Paragraph(
                number(
                    median_value(
                        roe_values
                    )
                ),
                cell_style,
            ),
        ],
        [
            Paragraph(
                "ROCE %",
                cell_style,
            ),
            Paragraph(
                number(
                    median_value(
                        roce_values
                    )
                ),
                cell_style,
            ),
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            70 * mm,
            45 * mm,
        ],
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    NAVY,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.grey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, -1),
                    LIGHT,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    story.append(summary_table)

    story.append(
        Paragraph(
            "Companies in Peer Group",
            heading_style,
        )
    )

    # --------------------------------------------------------
    # COMPANY TABLE
    # --------------------------------------------------------

    table_data = [
        [
            Paragraph(
                "<b>Ticker</b>",
                header_style,
            ),
            Paragraph(
                "<b>Company</b>",
                header_style,
            ),
            Paragraph(
                "<b>ROE %</b>",
                header_style,
            ),
            Paragraph(
                "<b>ROCE %</b>",
                header_style,
            ),
        ]
    ]

    for company in companies:

        table_data.append(
            [
                Paragraph(
                    clean(
                        company["company_id"]
                    ),
                    cell_style,
                ),
                Paragraph(
                    clean(
                        company["company_name"]
                    ),
                    cell_style,
                ),
                Paragraph(
                    number(
                        company["roe"]
                    ),
                    cell_style,
                ),
                Paragraph(
                    number(
                        company["roce"]
                    ),
                    cell_style,
                ),
            ]
        )

    company_table = Table(
        table_data,
        colWidths=[
            28 * mm,
            105 * mm,
            25 * mm,
            25 * mm,
        ],
        repeatRows=1,
        splitByRow=1,
    )

    company_table.setStyle(
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
                    0.35,
                    colors.grey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        WHITE,
                        LIGHT,
                    ],
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
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    story.append(company_table)

    # --------------------------------------------------------
    # FOOTER SUMMARY
    # --------------------------------------------------------

    story.append(Spacer(1, 6 * mm))

    story.append(
        Paragraph(
            "Source: N100 Financial Intelligence Platform "
            "peer-group classification and company fundamentals.",
            ParagraphStyle(
                "Footer",
                parent=cell_style,
                fontSize=6.5,
                textColor=GREY,
            ),
        )
    )

    doc.build(story)

    return filename


# ============================================================
# MAIN
# ============================================================

def main():

    groups = load_data()

    print()
    print("========================================")
    print("       SECTOR REPORT GENERATION")
    print("========================================")
    print()

    print(
        "Companies represented:",
        sum(
            len(x)
            for x in groups.values()
        ),
    )

    print(
        "Peer groups:",
        len(groups),
    )

    print()

    expected = {
        "Automobiles",
        "Consumer Finance",
        "FMCG",
        "IT Services",
        "Life Insurance",
        "Oil & Gas",
        "Pharmaceuticals",
        "Power & Utilities",
        "Private Banks",
        "Public Sector Banks",
        "Steel",
    }

    actual = set(groups.keys())

    print("Expected groups:")
    for name in sorted(expected):
        print(
            f"  - {name}: "
            f"{len(groups.get(name, []))} companies"
        )

    print()

    missing = expected - actual
    extra = actual - expected

    if missing:

        print(
            "ERROR - Missing peer groups:",
            sorted(missing),
        )

        raise RuntimeError(
            "Required peer groups missing"
        )

    if extra:

        print(
            "WARNING - Unexpected peer groups:",
            sorted(extra),
        )

    # Clean old sector PDFs first
    for old_file in OUTPUT_DIR.glob("*.pdf"):

        try:
            old_file.unlink()

        except Exception:
            pass

    print()
    print("Generating reports...")
    print()

    generated = []

    for sector in sorted(expected):

        companies = groups.get(
            sector,
            [],
        )

        if not companies:
            print(
                f"SKIP {sector} - no companies"
            )
            continue

        path = build_report(
            sector,
            companies,
        )

        generated.append(path)

        print(
            f"PASS  {sector:<24} "
            f"{len(companies):>2} companies  "
            f"{path.stat().st_size:,} bytes"
        )

    print()
    print("========================================")
    print("       SECTOR REPORT QA")
    print("========================================")

    print()
    print(
        "Expected PDFs:",
        11,
    )

    print(
        "Generated PDFs:",
        len(generated),
    )

    if len(generated) != 11:

        raise RuntimeError(
            f"Expected 11 PDFs, generated "
            f"{len(generated)}"
        )

    print()
    print("✅ 11 sector PDFs generated successfully")

    print()
    print("Output directory:")
    print(OUTPUT_DIR)

    print()
    print("========================================")
    print("       DAY 34 SECTOR REPORTS PASSED")
    print("========================================")


if __name__ == "__main__":
    main()
