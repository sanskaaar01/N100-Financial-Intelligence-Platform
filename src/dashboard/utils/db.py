from pathlib import Path
from typing import Optional

import sqlite3
import pandas as pd
import streamlit as st


# ============================================================
# DATABASE CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def _get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    return sqlite3.connect(str(DB_PATH))


# ============================================================
# GENERIC HELPERS
# ============================================================

def _read_query(
    query: str,
    params=None,
) -> pd.DataFrame:

    conn = _get_connection()

    try:
        return pd.read_sql_query(
            query,
            conn,
            params=params,
        )
    finally:
        conn.close()


def _table_columns(
    table_name: str,
) -> list[str]:

    conn = _get_connection()

    try:
        rows = conn.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()

        return [
            row[1]
            for row in rows
        ]

    finally:
        conn.close()


def _first_existing(
    columns: list[str],
    candidates: list[str],
) -> Optional[str]:

    lower_map = {
        column.lower(): column
        for column in columns
    }

    for candidate in candidates:

        if candidate.lower() in lower_map:
            return lower_map[
                candidate.lower()
            ]

    return None


def _empty_dataframe():

    return pd.DataFrame()


# ============================================================
# COMPANIES
# ============================================================

@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:

    try:

        columns = _table_columns(
            "companies"
        )

        if not columns:
            return _empty_dataframe()

        df = _read_query(
            "SELECT * FROM companies"
        )

        if df.empty:
            return df

        # ----------------------------------------------------
        # COMPANY ID
        # ----------------------------------------------------

        id_column = _first_existing(
            columns,
            [
                "company_id",
                "nse_ticker",
                "nse_code",
                "ticker",
                "symbol",
                "code",
            ],
        )

        if id_column:

            df["company_id"] = (
                df[id_column]
                .astype(str)
                .str.strip()
            )

        elif "id" in df.columns:

            df["company_id"] = (
                df["id"]
                .astype(str)
                .str.strip()
            )

        # ----------------------------------------------------
        # COMPANY NAME
        # ----------------------------------------------------

        name_column = _first_existing(
            columns,
            [
                "company_name",
                "name",
                "company",
            ],
        )

        if name_column:

            df["company_name"] = (
                df[name_column]
                .astype(str)
            )

        else:

            df["company_name"] = (
                df["company_id"]
            )

        # ----------------------------------------------------
        # SECTOR DIRECTLY IN COMPANIES
        # ----------------------------------------------------

        sector_column = _first_existing(
            columns,
            [
                "broad_sector",
                "sector",
            ],
        )

        if sector_column:

            df["broad_sector"] = (
                df[sector_column]
                .astype(str)
            )

        # ----------------------------------------------------
        # SUB-SECTOR
        # ----------------------------------------------------

        sub_sector_column = _first_existing(
            columns,
            [
                "sub_sector",
                "subsector",
                "industry",
            ],
        )

        if sub_sector_column:

            df["sub_sector"] = (
                df[sub_sector_column]
                .astype(str)
            )

        # ----------------------------------------------------
        # JOIN SECTORS TABLE IF NEEDED
        # ----------------------------------------------------

        if (
            "broad_sector" not in df.columns
            or df["broad_sector"]
            .replace(
                ["", "None", "nan", "NaN"],
                pd.NA,
            )
            .isna()
            .all()
        ):

            try:

                sector_columns = _table_columns(
                    "sectors"
                )

                if sector_columns:

                    sectors = _read_query(
                        "SELECT * FROM sectors"
                    )

                    if not sectors.empty:

                        sector_id_column = (
                            _first_existing(
                                list(
                                    sectors.columns
                                ),
                                [
                                    "company_id",
                                    "nse_ticker",
                                    "ticker",
                                    "symbol",
                                ],
                            )
                        )

                        sector_name_column = (
                            _first_existing(
                                list(
                                    sectors.columns
                                ),
                                [
                                    "broad_sector",
                                    "sector",
                                    "sector_name",
                                ],
                            )
                        )

                        sub_sector_name_column = (
                            _first_existing(
                                list(
                                    sectors.columns
                                ),
                                [
                                    "sub_sector",
                                    "subsector",
                                    "industry",
                                ],
                            )
                        )

                        if (
                            sector_id_column
                            and sector_name_column
                        ):

                            sector_lookup = (
                                sectors[
                                    [
                                        sector_id_column,
                                        sector_name_column,
                                    ]
                                ]
                                .drop_duplicates(
                                    subset=[
                                        sector_id_column
                                    ]
                                )
                                .copy()
                            )

                            sector_lookup.columns = [
                                "company_id",
                                "broad_sector",
                            ]

                            sector_lookup[
                                "company_id"
                            ] = (
                                sector_lookup[
                                    "company_id"
                                ]
                                .astype(str)
                                .str.strip()
                            )

                            df = df.merge(
                                sector_lookup,
                                on="company_id",
                                how="left",
                                suffixes=(
                                    "",
                                    "_sector",
                                ),
                            )

                            if (
                                "broad_sector_sector"
                                in df.columns
                            ):

                                if (
                                    "broad_sector"
                                    in df.columns
                                ):

                                    df[
                                        "broad_sector"
                                    ] = (
                                        df[
                                            "broad_sector"
                                        ]
                                        .replace(
                                            [
                                                "",
                                                "None",
                                                "nan",
                                                "NaN",
                                            ],
                                            pd.NA,
                                        )
                                        .fillna(
                                            df[
                                                "broad_sector_sector"
                                            ]
                                        )
                                    )

                                else:

                                    df[
                                        "broad_sector"
                                    ] = df[
                                        "broad_sector_sector"
                                    ]

                                df = df.drop(
                                    columns=[
                                        "broad_sector_sector"
                                    ],
                                    errors="ignore",
                                )

                            if (
                                sub_sector_name_column
                            ):

                                sub_lookup = (
                                    sectors[
                                        [
                                            sector_id_column,
                                            sub_sector_name_column,
                                        ]
                                    ]
                                    .drop_duplicates(
                                        subset=[
                                            sector_id_column
                                        ]
                                    )
                                    .copy()
                                )

                                sub_lookup.columns = [
                                    "company_id",
                                    "sub_sector_from_sector",
                                ]

                                sub_lookup[
                                    "company_id"
                                ] = (
                                    sub_lookup[
                                        "company_id"
                                    ]
                                    .astype(str)
                                    .str.strip()
                                )

                                df = df.merge(
                                    sub_lookup,
                                    on="company_id",
                                    how="left",
                                )

                                if (
                                    "sub_sector"
                                    not in df.columns
                                ):

                                    df[
                                        "sub_sector"
                                    ] = df[
                                        "sub_sector_from_sector"
                                    ]

                                else:

                                    df[
                                        "sub_sector"
                                    ] = (
                                        df[
                                            "sub_sector"
                                        ]
                                        .replace(
                                            [
                                                "",
                                                "None",
                                                "nan",
                                                "NaN",
                                            ],
                                            pd.NA,
                                        )
                                        .fillna(
                                            df[
                                                "sub_sector_from_sector"
                                            ]
                                        )
                                    )

                                df = df.drop(
                                    columns=[
                                        "sub_sector_from_sector"
                                    ],
                                    errors="ignore",
                                )

            except Exception:
                pass

        # ----------------------------------------------------
        # CLEAN OUTPUT
        # ----------------------------------------------------

        if "company_id" in df.columns:

            df["company_id"] = (
                df["company_id"]
                .astype(str)
                .str.strip()
            )

        if "company_name" in df.columns:

            df["company_name"] = (
                df["company_name"]
                .astype(str)
                .str.strip()
            )

        if "broad_sector" not in df.columns:

            df["broad_sector"] = "Unknown"

        if "sub_sector" not in df.columns:

            df["sub_sector"] = "Unknown"

        return df

    except Exception as exc:

        st.error(
            f"Unable to load company data: {exc}"
        )

        return _empty_dataframe()


# ============================================================
# FINANCIAL RATIOS
# ============================================================

@st.cache_data(ttl=600)
def get_ratios(
    ticker: str,
    year: Optional[str] = None,
) -> pd.DataFrame:

    if not ticker:
        return _empty_dataframe()

    try:

        query = """
            SELECT *
            FROM financial_ratios
            WHERE company_id = ?
        """

        params = [
            str(ticker)
        ]

        if year is not None:

            query += """
                AND year = ?
            """

            params.append(
                str(year)
            )

        query += """
            ORDER BY
                CAST(
                    substr(year, -4)
                    AS INTEGER
                ),
                year
        """

        return _read_query(
            query,
            params,
        )

    except Exception:

        return _empty_dataframe()


# ============================================================
# PROFIT & LOSS
# ============================================================

@st.cache_data(ttl=600)
def get_pl(
    ticker: str,
) -> pd.DataFrame:

    if not ticker:
        return _empty_dataframe()

    try:

        return _read_query(
            """
            SELECT *
            FROM profitandloss
            WHERE company_id = ?
            ORDER BY
                CAST(
                    substr(year, -4)
                    AS INTEGER
                ),
                year
            """,
            [str(ticker)],
        )

    except Exception:

        return _empty_dataframe()


# ============================================================
# BALANCE SHEET
# ============================================================

@st.cache_data(ttl=600)
def get_bs(
    ticker: str,
) -> pd.DataFrame:

    if not ticker:
        return _empty_dataframe()

    try:

        return _read_query(
            """
            SELECT *
            FROM balancesheet
            WHERE company_id = ?
            ORDER BY
                CAST(
                    substr(year, -4)
                    AS INTEGER
                ),
                year
            """,
            [str(ticker)],
        )

    except Exception:

        return _empty_dataframe()


# ============================================================
# CASH FLOW
# ============================================================

@st.cache_data(ttl=600)
def get_cf(
    ticker: str,
) -> pd.DataFrame:

    if not ticker:
        return _empty_dataframe()

    try:

        return _read_query(
            """
            SELECT *
            FROM cashflow
            WHERE company_id = ?
            ORDER BY
                CAST(
                    substr(year, -4)
                    AS INTEGER
                ),
                year
            """,
            [str(ticker)],
        )

    except Exception:

        return _empty_dataframe()


# ============================================================
# SECTORS
# ============================================================

@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:

    try:

        companies = get_companies()

        if companies.empty:
            return _empty_dataframe()

        columns = [
            column
            for column in [
                "company_id",
                "company_name",
                "broad_sector",
                "sub_sector",
            ]
            if column in companies.columns
        ]

        if "broad_sector" not in columns:
            return _empty_dataframe()

        return (
            companies[columns]
            .drop_duplicates(
                subset=["company_id"]
            )
            .sort_values(
                [
                    "broad_sector",
                    "company_name",
                ],
                na_position="last",
            )
            .reset_index(drop=True)
        )

    except Exception:

        return _empty_dataframe()


# ============================================================
# PEER GROUPS
# ============================================================

@st.cache_data(ttl=600)
def get_peers(
    group_name: Optional[str] = None,
) -> pd.DataFrame:

    try:

        if group_name:

            return _read_query(
                """
                SELECT *
                FROM peer_groups
                WHERE peer_group_name = ?
                ORDER BY company_id
                """,
                [str(group_name)],
            )

        return _read_query(
            """
            SELECT *
            FROM peer_groups
            ORDER BY
                peer_group_name,
                company_id
            """
        )

    except Exception:

        return _empty_dataframe()


# ============================================================
# VALUATION
# ============================================================

@st.cache_data(ttl=600)
def get_valuation(
    ticker: Optional[str] = None,
) -> pd.DataFrame:

    valuation_path = (
        PROJECT_ROOT
        / "output"
        / "valuation_summary.xlsx"
    )

    if not valuation_path.exists():
        return _empty_dataframe()

    try:

        df = pd.read_excel(
            valuation_path
        )

    except Exception:

        return _empty_dataframe()

    if (
        ticker
        and "company_id" in df.columns
    ):

        df = df[
            df["company_id"]
            .astype(str)
            .str.strip()
            == str(ticker).strip()
        ]

    return df.reset_index(
        drop=True
    )


# ============================================================
# LATEST / AS-OF-YEAR RATIOS
# ============================================================

@st.cache_data(ttl=600)
def get_latest_ratios(
    selected_year: Optional[str] = None,
) -> pd.DataFrame:

    try:

        # ----------------------------------------------------
        # No selected year:
        # latest available row for EVERY company
        # ----------------------------------------------------

        if selected_year is None:

            query = """
                SELECT fr.*
                FROM financial_ratios fr

                INNER JOIN (
                    SELECT
                        company_id,
                        MAX(
                            CAST(
                                substr(year, -4)
                                AS INTEGER
                            )
                        ) AS latest_year
                    FROM financial_ratios
                    GROUP BY company_id
                ) latest

                ON fr.company_id =
                    latest.company_id

                AND CAST(
                    substr(fr.year, -4)
                    AS INTEGER
                ) = latest.latest_year

                WHERE fr.id IN (
                    SELECT MAX(fr2.id)
                    FROM financial_ratios fr2
                    WHERE fr2.company_id =
                        fr.company_id
                    AND CAST(
                        substr(fr2.year, -4)
                        AS INTEGER
                    ) = latest.latest_year
                    GROUP BY
                        fr2.company_id
                )

                ORDER BY fr.company_id
            """

            return _read_query(
                query
            )

        # ----------------------------------------------------
        # Selected year:
        # latest available record for EACH company
        # up to that year.
        #
        # This prevents "Sep 2024" from returning only
        # companies that reported specifically in Sep 2024.
        # ----------------------------------------------------

        selected_year_text = str(
            selected_year
        ).strip()

        digits = "".join(
            character
            for character
            in selected_year_text
            if character.isdigit()
        )

        if len(digits) >= 4:

            target_year = int(
                digits[-4:]
            )

        else:

            target_year = 9999

        query = """
            SELECT fr.*
            FROM financial_ratios fr

            INNER JOIN (
                SELECT
                    company_id,
                    MAX(
                        CAST(
                            substr(year, -4)
                            AS INTEGER
                        )
                    ) AS selected_year
                FROM financial_ratios
                WHERE CAST(
                    substr(year, -4)
                    AS INTEGER
                ) <= ?

                GROUP BY company_id
            ) selected

            ON fr.company_id =
                selected.company_id

            AND CAST(
                substr(fr.year, -4)
                AS INTEGER
            ) = selected.selected_year

            WHERE fr.id IN (
                SELECT MAX(fr2.id)
                FROM financial_ratios fr2
                WHERE fr2.company_id =
                    fr.company_id

                AND CAST(
                    substr(fr2.year, -4)
                    AS INTEGER
                ) = selected.selected_year

                GROUP BY
                    fr2.company_id
            )

            ORDER BY fr.company_id
        """

        return _read_query(
            query,
            [target_year],
        )

    except Exception as exc:

        st.error(
            f"Unable to load latest ratio data: {exc}"
        )

        return _empty_dataframe()


# ============================================================
# AVAILABLE REPORTING YEARS
# ============================================================

@st.cache_data(ttl=600)
def get_available_years() -> list[str]:

    try:

        df = _read_query(
            """
            SELECT DISTINCT year
            FROM financial_ratios
            WHERE year IS NOT NULL
            """
        )

        if df.empty:
            return []

        values = (
            df["year"]
            .astype(str)
            .str.strip()
            .drop_duplicates()
            .tolist()
        )

        def sort_key(value):

            digits = "".join(
                character
                for character in value
                if character.isdigit()
            )

            year_number = (
                int(digits[-4:])
                if len(digits) >= 4
                else 0
            )

            month_order = {
                "Mar": 3,
                "Apr": 4,
                "Jun": 6,
                "Jul": 7,
                "Sep": 9,
                "Dec": 12,
            }

            month_number = 0

            for month, number in (
                month_order.items()
            ):

                if value.startswith(month):
                    month_number = number
                    break

            return (
                year_number,
                month_number,
                value,
            )

        values.sort(
            key=sort_key
        )

        return values

    except Exception:

        return []
