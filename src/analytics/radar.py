import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DB_PATH = Path("db/nifty100.db")
OUTPUT_DIR = Path("reports/radar_charts")

AXES = [
    "ROE",
    "ROCE",
    "NPM",
    "D/E",
    "FCF",
    "PAT CAGR 5yr",
    "Revenue CAGR 5yr",
    "Composite Score",
]


def get_connection():
    return sqlite3.connect(DB_PATH)


def load_peer_percentiles():
    conn = get_connection()

    try:
        return pd.read_sql_query(
            """
            SELECT
                company_id,
                peer_group_name,
                metric,
                value,
                percentile_rank,
                year
            FROM peer_percentiles
            """,
            conn,
        )
    finally:
        conn.close()


def load_composite_scores():
    conn = get_connection()

    try:
        df = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                composite_quality_score
            FROM financial_ratios
            """,
            conn,
        )
    finally:
        conn.close()

    if df.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "composite_quality_score",
            ]
        )

    def year_sort(value):
        import re

        text = str(value).upper()

        if text == "TTM":
            return 999999

        match = re.search(r"(19|20)\d{2}", text)

        if not match:
            return -1

        year = int(match.group())

        months = {
            "JAN": 1,
            "FEB": 2,
            "MAR": 3,
            "APR": 4,
            "MAY": 5,
            "JUN": 6,
            "JUL": 7,
            "AUG": 8,
            "SEP": 9,
            "OCT": 10,
            "NOV": 11,
            "DEC": 12,
        }

        month = 0

        for name, number in months.items():
            if name in text:
                month = number
                break

        return year * 100 + month

    df["_sort"] = df["year"].apply(year_sort)

    df = (
        df.sort_values(
            ["company_id", "_sort"],
            ascending=[True, False],
        )
        .drop_duplicates(
            "company_id",
            keep="first",
        )
        .drop(columns="_sort")
    )

    return df[
        [
            "company_id",
            "composite_quality_score",
        ]
    ].reset_index(drop=True)


def load_all_companies():
    """
    companies table does not expose company_id in this database.
    financial_ratios does, so use it as the Nifty 100 universe.
    """

    conn = get_connection()

    try:
        companies = pd.read_sql_query(
            """
            SELECT DISTINCT company_id
            FROM financial_ratios
            WHERE company_id IS NOT NULL
            """,
            conn,
        )
    finally:
        conn.close()

    return companies


def metric_axis_value(group, metric):
    rows = group[group["metric"] == metric]

    if rows.empty:
        return np.nan

    value = rows.iloc[0]["percentile_rank"]

    if pd.isna(value):
        return np.nan

    return float(value) * 100


def build_company_profile(
    company_id,
    peer_group,
    peer_data,
    composite_scores,
):
    company_data = peer_data[peer_data["company_id"] == company_id]

    profile = {}

    profile["ROE"] = metric_axis_value(
        company_data,
        "ROE",
    )

    profile["ROCE"] = metric_axis_value(
        company_data,
        "ROCE",
    )

    profile["NPM"] = metric_axis_value(
        company_data,
        "Net Profit Margin",
    )

    profile["D/E"] = metric_axis_value(
        company_data,
        "D/E",
    )

    profile["FCF"] = metric_axis_value(
        company_data,
        "FCF",
    )

    profile["PAT CAGR 5yr"] = metric_axis_value(
        company_data,
        "PAT CAGR 5yr",
    )

    profile["Revenue CAGR 5yr"] = metric_axis_value(
        company_data,
        "Revenue CAGR 5yr",
    )

    score_rows = composite_scores[composite_scores["company_id"] == company_id]

    if score_rows.empty:
        profile["Composite Score"] = 50.0
    else:
        score = pd.to_numeric(
            score_rows.iloc[0]["composite_quality_score"],
            errors="coerce",
        )

        if pd.isna(score):
            profile["Composite Score"] = 50.0
        else:
            profile["Composite Score"] = float(np.clip(score, 0, 100))

    return profile


def build_peer_average(
    peer_group,
    peer_data,
    composite_scores,
):
    companies = peer_data[peer_data["peer_group_name"] == peer_group][
        "company_id"
    ].unique()

    profiles = []

    for company_id in companies:
        profiles.append(
            build_company_profile(
                company_id,
                peer_group,
                peer_data,
                composite_scores,
            )
        )

    if not profiles:
        return {axis: 50.0 for axis in AXES}

    average = {}

    for axis in AXES:
        values = [profile[axis] for profile in profiles if not pd.isna(profile[axis])]

        average[axis] = float(np.mean(values)) if values else 50.0

    return average


def make_radar_chart(
    company_id,
    peer_group,
    company_profile,
    peer_average,
    output_path,
    standalone=False,
):
    labels = AXES

    company_values = [company_profile.get(axis, 50.0) for axis in labels]

    average_values = [peer_average.get(axis, 50.0) for axis in labels]

    company_values = [
        50.0 if pd.isna(value) else float(value) for value in company_values
    ]

    average_values = [
        50.0 if pd.isna(value) else float(value) for value in average_values
    ]

    number_axes = len(labels)

    angles = np.linspace(
        0,
        2 * np.pi,
        number_axes,
        endpoint=False,
    ).tolist()

    angles += angles[:1]
    company_values += company_values[:1]
    average_values += average_values[:1]

    fig = plt.figure(figsize=(8, 8))

    ax = fig.add_subplot(
        111,
        polar=True,
    )

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.plot(
        angles,
        company_values,
        linewidth=2,
        label=company_id,
    )

    ax.fill(
        angles,
        company_values,
        alpha=0.20,
    )

    ax.plot(
        angles,
        average_values,
        linestyle="--",
        linewidth=2,
        label=("Nifty 100 Average" if standalone else f"{peer_group} Average"),
    )

    ax.set_xticks(angles[:-1])

    ax.set_xticklabels(
        labels,
        fontsize=9,
    )

    ax.set_ylim(0, 100)

    ax.set_yticks([20, 40, 60, 80, 100])

    ax.set_yticklabels(
        ["20", "40", "60", "80", "100"],
        fontsize=8,
    )

    if standalone:
        title = f"{company_id} — Nifty 100 Standalone"
    else:
        title = f"{company_id} — {peer_group}"

    ax.set_title(
        title,
        fontsize=14,
        fontweight="bold",
        pad=25,
    )

    ax.legend(
        loc="upper right",
        bbox_to_anchor=(1.25, 1.10),
    )

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)


def generate_peer_group_charts(
    peer_data,
    composite_scores,
):
    generated = 0

    peer_groups = peer_data["peer_group_name"].dropna().unique()

    for peer_group in peer_groups:

        group_companies = peer_data[peer_data["peer_group_name"] == peer_group][
            "company_id"
        ].unique()

        average = build_peer_average(
            peer_group,
            peer_data,
            composite_scores,
        )

        for company_id in group_companies:

            profile = build_company_profile(
                company_id,
                peer_group,
                peer_data,
                composite_scores,
            )

            output_path = OUTPUT_DIR / f"{company_id}_radar.png"

            make_radar_chart(
                company_id,
                peer_group,
                profile,
                average,
                output_path,
                standalone=False,
            )

            generated += 1

    return generated


def generate_standalone_charts(
    peer_data,
    composite_scores,
    all_companies,
):
    assigned = set(peer_data["company_id"].dropna())

    all_ids = set(all_companies["company_id"].dropna())

    unassigned = sorted(all_ids - assigned)

    if not unassigned:
        return 0

    all_profiles = []

    for company_id in assigned:

        profile = build_company_profile(
            company_id,
            None,
            peer_data,
            composite_scores,
        )

        all_profiles.append(profile)

    if all_profiles:

        nifty_average = {}

        for axis in AXES:

            values = [
                profile[axis] for profile in all_profiles if not pd.isna(profile[axis])
            ]

            nifty_average[axis] = float(np.mean(values)) if values else 50.0

    else:

        nifty_average = {axis: 50.0 for axis in AXES}

    generated = 0

    for company_id in unassigned:

        profile = {axis: 50.0 for axis in AXES}

        score_rows = composite_scores[composite_scores["company_id"] == company_id]

        if not score_rows.empty:

            score = pd.to_numeric(
                score_rows.iloc[0]["composite_quality_score"],
                errors="coerce",
            )

            if not pd.isna(score):

                profile["Composite Score"] = float(np.clip(score, 0, 100))

        output_path = OUTPUT_DIR / f"{company_id}_radar.png"

        make_radar_chart(
            company_id,
            "Nifty 100",
            profile,
            nifty_average,
            output_path,
            standalone=True,
        )

        generated += 1

    return generated


def run_radar_engine():

    print("=" * 70)
    print("DAY 19 — PEER RADAR CHART ENGINE")
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("Loading peer percentile data...")

    peer_data = load_peer_percentiles()

    print(
        "Peer percentile rows:",
        len(peer_data),
    )

    print(
        "Companies with peer groups:",
        peer_data["company_id"].nunique(),
    )

    print(
        "Peer groups:",
        peer_data["peer_group_name"].nunique(),
    )

    composite_scores = load_composite_scores()

    all_companies = load_all_companies()

    print(
        "Latest company universe:",
        len(all_companies),
    )

    print()
    print("Generating peer-group charts...")

    peer_count = generate_peer_group_charts(
        peer_data,
        composite_scores,
    )

    print(
        "Peer charts generated:",
        peer_count,
    )

    print()
    print("Generating standalone charts...")

    standalone_count = generate_standalone_charts(
        peer_data,
        composite_scores,
        all_companies,
    )

    print(
        "Standalone charts generated:",
        standalone_count,
    )

    total = peer_count + standalone_count

    print()
    print(
        "Total radar charts:",
        total,
    )

    print(
        "Output directory:",
        OUTPUT_DIR.resolve(),
    )

    print()
    print("Sample files:")

    files = sorted(OUTPUT_DIR.glob("*_radar.png"))

    for file in files[:10]:
        print(" ", file.name)

    print()
    print("✅ DAY 19 RADAR ENGINE COMPLETE")


if __name__ == "__main__":
    run_radar_engine()
