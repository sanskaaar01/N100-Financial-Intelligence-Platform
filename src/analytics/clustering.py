from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_XLSX = OUTPUT_DIR / "kmeans_clusters.xlsx"
OUTPUT_CSV = OUTPUT_DIR / "kmeans_clusters.csv"

FEATURE_COLUMNS = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "eps_cagr_5yr",
    "fcf_cagr_5yr",
    "composite_quality_score",
]


def load_data():

    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query(
        """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        """,
        conn,
    )

    ratios = pd.read_sql_query(
        """
        SELECT *
        FROM financial_ratios
        """,
        conn,
    )

    conn.close()

    return companies, ratios


def num(value):

    try:
        return float(value)
    except:
        return np.nan


def calculate_fcf_cagr(group):

    g = group.copy()

    if g.empty:
        return np.nan

    g["free_cash_flow_cr"] = pd.to_numeric(
        g["free_cash_flow_cr"],
        errors="coerce",
    )

    g = g.dropna(
        subset=["free_cash_flow_cr"]
    )

    if len(g) < 6:
        return np.nan

    # Remove duplicate year records.
    g = (
        g.groupby("year", as_index=False)
        ["free_cash_flow_cr"]
        .mean()
    )

    # Extract numeric year.
    g["year_num"] = pd.to_numeric(
        g["year"]
        .astype(str)
        .str.extract(r"(\d{4})")[0],
        errors="coerce",
    )

    g = g.sort_values(
        ["year_num", "year"]
    )

    if len(g) < 6:
        return np.nan

    first = num(
        g.iloc[-6]["free_cash_flow_cr"]
    )

    latest = num(
        g.iloc[-1]["free_cash_flow_cr"]
    )

    # CAGR is undefined when FCF is
    # zero or negative.
    if (
        pd.isna(first)
        or pd.isna(latest)
        or first <= 0
        or latest <= 0
    ):
        return np.nan

    return (
        (latest / first) ** (1 / 5) - 1
    ) * 100


def build_features(companies, ratios):

    rows = []

    ratio_company_ids = set(
        ratios["company_id"]
        .astype(str)
        .unique()
    )

    print()
    print(
        "Companies with ratio data:",
        len(ratio_company_ids),
    )

    print(
        "Companies without ratio data:",
        len(companies) - len(ratio_company_ids),
    )

    for company_id in companies["company_id"].astype(str):

        r = ratios[
            ratios["company_id"].astype(str)
            == company_id
        ].copy()

        # ----------------------------------------------------
        # IMPORTANT:
        # Keep ALL 92 companies.
        # If a company has no ratio data, create a row
        # containing NaN features. These will later be
        # median-imputed before KMeans.
        # ----------------------------------------------------

        if r.empty:

            print(
                f"WARNING - No ratio data for {company_id}"
            )

            row = {
                "company_id": company_id
            }

            for column in FEATURE_COLUMNS:
                row[column] = np.nan

            rows.append(row)

            continue

        # Remove duplicate company/year records.
        r = r.drop_duplicates(
            subset=["company_id", "year"]
        ).copy()

        # Determine latest year.
        r["year_num"] = pd.to_numeric(
            r["year"]
            .astype(str)
            .str.extract(r"(\d{4})")[0],
            errors="coerce",
        )

        r = r.sort_values(
            ["year_num", "year"]
        )

        latest = r.iloc[-1]

        row = {
            "company_id": company_id,

            "net_profit_margin_pct":
                num(
                    latest.get(
                        "net_profit_margin_pct"
                    )
                ),

            "operating_profit_margin_pct":
                num(
                    latest.get(
                        "operating_profit_margin_pct"
                    )
                ),

            "return_on_equity_pct":
                num(
                    latest.get(
                        "return_on_equity_pct"
                    )
                ),

            "debt_to_equity":
                num(
                    latest.get(
                        "debt_to_equity"
                    )
                ),

            "interest_coverage":
                num(
                    latest.get(
                        "interest_coverage"
                    )
                ),

            "asset_turnover":
                num(
                    latest.get(
                        "asset_turnover"
                    )
                ),

            "revenue_cagr_5yr":
                num(
                    latest.get(
                        "revenue_cagr_5yr"
                    )
                ),

            "pat_cagr_5yr":
                num(
                    latest.get(
                        "pat_cagr_5yr"
                    )
                ),

            "eps_cagr_5yr":
                num(
                    latest.get(
                        "eps_cagr_5yr"
                    )
                ),

            "fcf_cagr_5yr":
                calculate_fcf_cagr(r),

            "composite_quality_score":
                num(
                    latest.get(
                        "composite_quality_score"
                    )
                ),
        }

        rows.append(row)

    return pd.DataFrame(rows)


def prepare_features(features):

    X = features[
        FEATURE_COLUMNS
    ].copy()

    X = X.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    # Median imputation.
    for column in X.columns:

        median = X[column].median()

        if pd.isna(median):
            median = 0.0

        X[column] = X[column].fillna(
            median
        )

    return X


def run_kmeans(features):

    X = prepare_features(
        features
    )

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(
        X
    )

    model = KMeans(
        n_clusters=5,
        random_state=42,
        n_init=20,
    )

    labels = model.fit_predict(
        X_scaled
    )

    result = features.copy()

    result["cluster"] = labels

    distances = model.transform(
        X_scaled
    )

    result["cluster_distance"] = [
        distances[i, labels[i]]
        for i in range(len(labels))
    ]

    # Cluster naming based on average
    # composite quality score.
    quality = (
        result
        .groupby("cluster")
        ["composite_quality_score"]
        .mean()
        .sort_values()
    )

    names = [
        "Value / Lower Quality",
        "Stable / Moderate",
        "Growth",
        "Quality",
        "High Quality / Compounders",
    ]

    cluster_names = {}

    for rank, cluster_id in enumerate(
        quality.index
    ):

        cluster_names[
            cluster_id
        ] = names[rank]

    result["cluster_name"] = result[
        "cluster"
    ].map(cluster_names)

    return result


def main():

    print()
    print("========================================")
    print("       DAY 36 KMEANS ENGINE")
    print("========================================")

    print()
    print("Database:")
    print(DB_PATH)

    companies, ratios = load_data()

    print()
    print(
        "Companies loaded:",
        len(companies)
    )

    print(
        "Ratio rows:",
        len(ratios)
    )

    if len(companies) != 92:

        raise RuntimeError(
            f"Expected 92 companies, "
            f"found {len(companies)}"
        )

    print()
    print("Building features...")

    features = build_features(
        companies,
        ratios
    )

    print()
    print(
        "Feature rows:",
        len(features)
    )

    # --------------------------------------------------------
    # HARD QA BEFORE KMEANS
    # --------------------------------------------------------

    if len(features) != 92:

        missing = set(
            companies["company_id"].astype(str)
        ) - set(
            features["company_id"].astype(str)
        )

        raise RuntimeError(
            f"Feature generation produced "
            f"{len(features)} rows instead of 92. "
            f"Missing: {sorted(missing)}"
        )

    print(
        "PASS - All 92 companies have feature rows"
    )

    print()
    print("Features used:")

    for column in FEATURE_COLUMNS:
        print(" -", column)

    print()
    print("Standardizing features...")

    result = run_kmeans(
        features
    )

    # --------------------------------------------------------
    # ADD COMPANY NAMES
    # --------------------------------------------------------

    result = result.merge(
        companies[
            [
                "company_id",
                "company_name",
            ]
        ],
        on="company_id",
        how="left",
    )

    result = result[
        [
            "company_id",
            "company_name",
            "cluster",
            "cluster_name",
        ]
        + FEATURE_COLUMNS
        + [
            "cluster_distance"
        ]
    ]

    # --------------------------------------------------------
    # SAVE OUTPUTS
    # --------------------------------------------------------

    result.to_excel(
        OUTPUT_XLSX,
        index=False,
    )

    result.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("========================================")
    print("       CLUSTER DISTRIBUTION")
    print("========================================")

    print(
        result[
            "cluster_name"
        ]
        .value_counts()
        .to_string()
    )

    print()
    print(
        "Companies clustered:",
        result[
            "company_id"
        ].nunique()
    )

    print(
        "Clusters:",
        result[
            "cluster"
        ].nunique()
    )

    print()
    print("Excel:")
    print(OUTPUT_XLSX)

    print()
    print("CSV:")
    print(OUTPUT_CSV)

    # --------------------------------------------------------
    # FINAL QA
    # --------------------------------------------------------

    print()
    print("========================================")
    print("       DAY 36 QA")
    print("========================================")

    assert len(result) == 92

    assert (
        result[
            "company_id"
        ].nunique()
        == 92
    )

    assert (
        result[
            "cluster"
        ].nunique()
        == 5
    )

    assert OUTPUT_XLSX.exists()
    assert OUTPUT_CSV.exists()

    print()
    print("PASS - 92 companies verified")
    print("PASS - 5 clusters generated")
    print("PASS - FCF CAGR calculated")
    print("PASS - Missing ratio data handled")
    print("PASS - Missing values imputed")
    print("PASS - Features standardized")
    print("PASS - Excel generated")
    print("PASS - CSV generated")

    print()
    print("========================================")
    print("       DAY 36 COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()
