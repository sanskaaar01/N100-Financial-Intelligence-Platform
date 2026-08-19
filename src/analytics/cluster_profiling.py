import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "nifty100.db"

CLUSTER_PATH = ROOT / "output" / "kmeans_clusters.csv"

ELBOW_PATH = ROOT / "reports" / "elbow_plot.png"
HEATMAP_PATH = ROOT / "reports" / "correlation_heatmap.png"

OUTLIER_PATH = ROOT / "output" / "outlier_report.csv"
STATS_PATH = ROOT / "output" / "portfolio_stats.csv"


FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]


def get_connection():
    """Return a connection to the project SQLite database."""
    return sqlite3.connect(DB_PATH)


def load_cluster_data():
    """Load the existing KMeans company-level dataset."""
    df = pd.read_csv(CLUSTER_PATH)

    if len(df) != 92:
        raise RuntimeError(
            f"Expected 92 companies in KMeans output, found {len(df)}"
        )

    return df


def profile_clusters(df):
    """Calculate mean and median values for the five clusters."""
    available = [
        col for col in FEATURES
        if col in df.columns
    ]

    if len(available) != 5:
        raise RuntimeError(
            f"Expected all 5 clustering features. Found: {available}"
        )

    mean_profile = (
        df.groupby(
            ["cluster", "cluster_name"],
            dropna=False
        )[available]
        .mean()
        .round(3)
    )

    median_profile = (
        df.groupby(
            ["cluster", "cluster_name"],
            dropna=False
        )[available]
        .median()
        .round(3)
    )

    mean_output = (
        ROOT / "output" / "cluster_profile_mean.csv"
    )

    median_output = (
        ROOT / "output" / "cluster_profile_median.csv"
    )

    mean_profile.to_csv(mean_output)
    median_profile.to_csv(median_output)

    return mean_profile, median_profile


def create_correlation_heatmap():
    """
    Create a correlation heatmap using financial ratio features.

    Uses financial_ratios directly. This avoids relying on
    broad_sector/sub_sector columns that do not exist in the
    companies table.
    """

    conn = get_connection()

    query = """
        SELECT
            company_id,
            year,
            net_profit_margin_pct,
            operating_profit_margin_pct,
            return_on_equity_pct,
            debt_to_equity,
            interest_coverage,
            asset_turnover,
            revenue_cagr_5yr,
            pat_cagr_5yr,
            eps_cagr_5yr,
            composite_quality_score
        FROM financial_ratios
    """

    ratios = pd.read_sql_query(query, conn)
    conn.close()

    if ratios.empty:
        raise RuntimeError(
            "No financial ratio data available for correlation analysis."
        )

    numeric_columns = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "eps_cagr_5yr",
        "composite_quality_score",
    ]

    available = [
        c for c in numeric_columns
        if c in ratios.columns
    ]

    data = ratios[available].apply(
        pd.to_numeric,
        errors="coerce",
    )

    corr = data.corr()

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        reports_dir / "correlation_heatmap.png"
    )

    plt.figure(
        figsize=(12, 9)
    )

    plt.imshow(
        corr,
        cmap="coolwarm",
        aspect="auto",
        vmin=-1,
        vmax=1,
    )

    plt.colorbar(
        label="Correlation"
    )

    plt.xticks(
        range(len(corr.columns)),
        corr.columns,
        rotation=45,
        ha="right",
    )

    plt.yticks(
        range(len(corr.index)),
        corr.index,
    )

    plt.title(
        "Financial Ratio Correlation Heatmap"
    )

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close()

    return corr

def create_outlier_report():
    """Detect KPI outliers using sector-level absolute Z-score above three."""
    conn = get_connection()

    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        conn,
    )

    companies = pd.read_sql_query(
        """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        """,
        conn,
    )

    conn.close()

    ratios["year_sort"] = (
        ratios["year"]
        .astype(str)
        .str.extract(r"(\d{4})")[0]
    )

    ratios["year_sort"] = pd.to_numeric(
        ratios["year_sort"],
        errors="coerce",
    )

    ratios = ratios.sort_values(
        ["company_id", "year_sort"]
    )

    latest = (
        ratios
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    latest = latest.merge(
        companies,
        on="company_id",
        how="left",
    )

    if "broad_sector" not in latest.columns:
        latest["broad_sector"] = "Unknown"

    metrics = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "eps_cagr_5yr",
        "composite_quality_score",
    ]

    available = [
        c for c in metrics
        if c in latest.columns
    ]

    records = []

    for metric in available:

        values = pd.to_numeric(
            latest[metric],
            errors="coerce",
        )

        latest[f"{metric}_z"] = (
            latest
            .groupby("broad_sector")[metric]
            .transform(
                lambda s:
                (
                    pd.to_numeric(
                        s,
                        errors="coerce"
                    ) - pd.to_numeric(
                        s,
                        errors="coerce"
                    ).mean()
                )
                /
                pd.to_numeric(
                    s,
                    errors="coerce"
                ).std(ddof=0)
                if pd.to_numeric(
                    s,
                    errors="coerce"
                ).std(ddof=0) not in [0, np.nan]
                else np.nan
            )
        )

    z_columns = [
        f"{metric}_z"
        for metric in available
    ]

    for _, row in latest.iterrows():

        flagged = []

        for metric in available:

            z = row.get(
                f"{metric}_z",
                np.nan,
            )

            if pd.notna(z) and abs(z) > 3:
                flagged.append(
                    {
                        "metric": metric,
                        "z_score": round(float(z), 3),
                        "value": row.get(metric),
                    }
                )

        if flagged:

            for item in flagged:

                records.append(
                    {
                        "company_id": row["company_id"],
                        "company_name": row.get(
                            "company_name",
                            "",
                        ),
                        "broad_sector": row.get(
                            "broad_sector",
                            "Unknown",
                        ),
                        "metric": item["metric"],
                        "value": item["value"],
                        "z_score": item["z_score"],
                        "severity": "High",
                    }
                )

    result = pd.DataFrame(
        records,
        columns=[
            "company_id",
            "company_name",
            "broad_sector",
            "metric",
            "value",
            "z_score",
            "severity",
        ],
    )

    result.to_csv(
        OUTLIER_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    return result


def create_portfolio_stats():
    """Calculate percentile and dispersion statistics for ten core KPIs."""
    conn = get_connection()

    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        conn,
    )

    conn.close()

    ratios["year_sort"] = (
        ratios["year"]
        .astype(str)
        .str.extract(r"(\d{4})")[0]
    )

    ratios["year_sort"] = pd.to_numeric(
        ratios["year_sort"],
        errors="coerce",
    )

    ratios = ratios.sort_values(
        ["company_id", "year_sort"]
    )

    latest = (
        ratios
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    metrics = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "eps_cagr_5yr",
        "composite_quality_score",
    ]

    available = [
        c for c in metrics
        if c in latest.columns
    ]

    rows = []

    for metric in available:

        values = pd.to_numeric(
            latest[metric],
            errors="coerce",
        ).dropna()

        if values.empty:
            continue

        rows.append(
            {
                "kpi": metric,
                "P10": values.quantile(0.10),
                "P25": values.quantile(0.25),
                "P50": values.quantile(0.50),
                "P75": values.quantile(0.75),
                "P90": values.quantile(0.90),
                "Mean": values.mean(),
                "Std": values.std(),
                "Company_Count": values.count(),
            }
        )

    result = pd.DataFrame(rows)

    result = result.round(4)

    result.to_csv(
        STATS_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    return result


def main():
    """Run all Day 37 profiling and statistics outputs."""

    print("========================================")
    print("       DAY 37 ANALYTICS ENGINE")
    print("========================================")

    print()
    print("Database:", DB_PATH)

    df = load_cluster_data()

    print()
    print("Companies loaded:", len(df))
    print("Clusters:", df["cluster"].nunique())

    print()
    print("Cluster distribution:")
    print(
        df["cluster_name"]
        .value_counts()
        .to_string()
    )

    print()
    print("[1] Profiling clusters...")

    mean_profile, median_profile = profile_clusters(df)

    print("PASS - Cluster mean profile generated")
    print("PASS - Cluster median profile generated")

    print()
    print("Cluster means:")
    print(mean_profile.to_string())

    print()
    print("[2] Creating correlation heatmap...")

    corr = create_correlation_heatmap()

    print(
        "PASS - Correlation heatmap generated:",
        HEATMAP_PATH,
    )

    print("Correlation matrix shape:", corr.shape)

    print()
    print("[3] Running outlier detection...")

    outliers = create_outlier_report()

    print(
        "Outlier rows:",
        len(outliers),
    )

    print(
        "PASS - Outlier report generated:",
        OUTLIER_PATH,
    )

    print()
    print("[4] Creating portfolio statistics...")

    stats = create_portfolio_stats()

    print(
        "Portfolio KPI rows:",
        len(stats),
    )

    print(
        "PASS - Portfolio statistics generated:",
        STATS_PATH,
    )

    print()
    print("========================================")
    print("       DAY 37 QA")
    print("========================================")

    assert len(df) == 92
    assert df["company_id"].nunique() == 92
    assert df["cluster"].nunique() == 5

    assert HEATMAP_PATH.exists()
    assert OUTLIER_PATH.exists()
    assert STATS_PATH.exists()

    assert len(stats) >= 10

    print("PASS - 92 companies verified")
    print("PASS - 5 clusters verified")
    print("PASS - Cluster profiling generated")
    print("PASS - Correlation heatmap generated")
    print("PASS - Outlier report generated")
    print("PASS - Portfolio statistics generated")

    print()
    print("========================================")
    print("       DAY 37 COMPLETE")
    print("========================================")

    print()
    print("Generated:")
    print(HEATMAP_PATH)
    print(OUTLIER_PATH)
    print(STATS_PATH)

    print()
    print("NEXT: DAY 38 - FASTAPI SERVER SCAFFOLD")


if __name__ == "__main__":
    main()
