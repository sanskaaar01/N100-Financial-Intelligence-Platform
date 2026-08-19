"""
load_database.py

Loads all Excel source files into SQLite.

Responsibilities:
- Read all 12 source Excel files
- Use the correct header row for each file
- Normalize column names
- Remove rows with invalid company IDs
- Load data into SQLite
- Generate load_audit.csv
- Run foreign-key validation
"""

from pathlib import Path

import pandas as pd

from ..etl.loader import ExcelLoader
from .database import Database


class DatabaseLoader:

    def __init__(self):

        # ------------------------------------------------------
        # Project paths
        # ------------------------------------------------------

        self.root = Path(__file__).resolve().parents[2]

        self.raw_folder = self.root / "data" / "raw"

        self.output_folder = self.root / "data" / "output"

        self.output_folder.mkdir(parents=True, exist_ok=True)

        # ------------------------------------------------------
        # Database
        # ------------------------------------------------------

        self.db = Database()

        self.conn = self.db.connect()

        # ------------------------------------------------------
        # Excel loader
        # ------------------------------------------------------

        self.loader = ExcelLoader()

        # ------------------------------------------------------
        # Audit
        # ------------------------------------------------------

        self.audit = []

    # ==========================================================
    # READ EXCEL FILE
    # ==========================================================

    def read_file(self, filename):

        filepath = self.raw_folder / filename

        if not filepath.exists():

            raise FileNotFoundError(f"File not found: {filepath}")

        # ------------------------------------------------------
        # IMPORTANT:
        #
        # Different source files have different header rows.
        #
        # header=0 -> first Excel row is header
        # header=1 -> second Excel row is header
        # ------------------------------------------------------

        header_rows = {
            # Header on Excel row 2
            "companies.xlsx": 1,
            "balancesheet.xlsx": 1,
            "profitandloss.xlsx": 1,
            "cashflow.xlsx": 1,
            "documents.xlsx": 1,
            "prosandcons.xlsx": 1,
            "analysis.xlsx": 1,
            # Header on Excel row 1
            "sectors.xlsx": 0,
            "peer_groups.xlsx": 0,
            "market_cap.xlsx": 0,
            "stock_prices.xlsx": 0,
            "financial_ratios.xlsx": 0,
        }

        header_row = header_rows.get(filename, 0)

        print(f"Loading {filename}...")

        df = pd.read_excel(filepath, header=header_row)

        # ------------------------------------------------------
        # Normalize column names
        # ------------------------------------------------------

        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.lower()
            .str.replace(" ", "_", regex=False)
            .str.replace("-", "_", regex=False)
        )

        # ------------------------------------------------------
        # Remove completely empty rows
        # ------------------------------------------------------

        df = df.dropna(how="all").copy()

        print(f"Rows : {len(df)}")

        print(f"Columns : {len(df.columns)}")

        return df

    # ==========================================================
    # GET SQLITE TABLE COLUMNS
    # ==========================================================

    def get_table_columns(self, table_name):

        result = pd.read_sql_query(f"PRAGMA table_info({table_name})", self.conn)

        if result.empty:
            return []

        return result["name"].tolist()

    # ==========================================================
    # CLEAN COMPANY ID
    # ==========================================================

    def normalize_company_id(self, df):

        if "company_id" not in df.columns:

            return df

        df = df.copy()

        df["company_id"] = df["company_id"].astype(str).str.strip().str.upper()

        return df

    # ==========================================================
    # INSERT DATAFRAME
    # ==========================================================

    def insert_dataframe(self, table_name, df):

        original_count = len(df)

        # ------------------------------------------------------
        # Normalize company IDs
        # ------------------------------------------------------

        df = self.normalize_company_id(df)

        # ------------------------------------------------------
        # Get actual SQLite columns
        # ------------------------------------------------------

        table_columns = self.get_table_columns(table_name)

        if not table_columns:

            raise RuntimeError(f"SQLite table '{table_name}' " f"does not exist.")

        # ------------------------------------------------------
        # Remove columns that don't exist
        # in SQLite schema
        # ------------------------------------------------------

        ignored_columns = [
            column for column in df.columns if column not in table_columns
        ]

        if ignored_columns:

            print(
                f"⚠ Ignoring extra columns " f"in {table_name}: " f"{ignored_columns}"
            )

        valid_columns = [column for column in df.columns if column in table_columns]

        df = df[valid_columns].copy()

        # ------------------------------------------------------
        # Remove invalid company IDs
        #
        # Only for tables that actually contain company_id.
        # ------------------------------------------------------

        invalid_company_rows = 0

        if "company_id" in df.columns:

            company_df = pd.read_sql_query("SELECT id FROM companies", self.conn)

            valid_company_ids = set(
                company_df["id"].astype(str).str.strip().str.upper()
            )

            before = len(df)

            df = df[df["company_id"].isin(valid_company_ids)].copy()

            invalid_company_rows = before - len(df)

            if invalid_company_rows > 0:

                print(
                    f"Removed "
                    f"{invalid_company_rows} "
                    f"rows with invalid "
                    f"company_id."
                )

        # ------------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT blindly drop duplicate
        # (company_id, year) rows here.
        #
        # We already verified that some source
        # duplicate rows contain different values.
        #
        # Those need to be investigated separately.
        # ------------------------------------------------------

        # ------------------------------------------------------
        # Empty dataframe check
        # ------------------------------------------------------

        if df.empty:

            print(f"⚠ No valid rows to insert " f"into {table_name}")

            self.audit.append(
                {
                    "table": table_name,
                    "source_rows": original_count,
                    "rows_loaded": 0,
                    "invalid_company_rows": invalid_company_rows,
                    "status": "EMPTY",
                }
            )

            return

        # ------------------------------------------------------
        # Insert
        # ------------------------------------------------------

        df.to_sql(table_name, self.conn, if_exists="append", index=False)

        loaded_count = len(df)

        print(f"✅ Inserted " f"{loaded_count} rows into " f"{table_name}")

        self.audit.append(
            {
                "table": table_name,
                "source_rows": original_count,
                "rows_loaded": loaded_count,
                "invalid_company_rows": invalid_company_rows,
                "status": "SUCCESS",
            }
        )

    # ==========================================================
    # RUN
    # ==========================================================

    def run(self):

        files = [
            ("companies.xlsx", "companies"),
            ("sectors.xlsx", "sectors"),
            ("peer_groups.xlsx", "peer_groups"),
            ("market_cap.xlsx", "market_cap"),
            ("stock_prices.xlsx", "stock_prices"),
            ("financial_ratios.xlsx", "financial_ratios"),
            ("balancesheet.xlsx", "balancesheet"),
            ("profitandloss.xlsx", "profitandloss"),
            ("cashflow.xlsx", "cashflow"),
            ("documents.xlsx", "documents"),
            ("prosandcons.xlsx", "prosandcons"),
            ("analysis.xlsx", "analysis"),
        ]

        # ------------------------------------------------------
        # Load files in dependency order
        # ------------------------------------------------------

        for excel_file, table_name in files:

            df = self.read_file(excel_file)

            self.insert_dataframe(table_name, df)

        # ------------------------------------------------------
        # Save load audit
        # ------------------------------------------------------

        audit_df = pd.DataFrame(self.audit)

        audit_path = self.output_folder / "load_audit.csv"

        audit_df.to_csv(audit_path, index=False)

        print()
        print("✅ load_audit.csv generated:")

        print(audit_path)

        # ------------------------------------------------------
        # Foreign key validation
        # ------------------------------------------------------

        fk_errors = self.conn.execute("PRAGMA foreign_key_check;").fetchall()

        company_count = self.conn.execute("SELECT COUNT(*) FROM companies").fetchone()[
            0
        ]

        print()
        print(f"Companies in database : " f"{company_count}")

        print(f"Foreign key errors : " f"{len(fk_errors)}")

        if len(fk_errors) == 0:

            print("✅ Foreign key check passed.")

        else:

            print("⚠ Foreign key violations detected:")

            for error in fk_errors[:20]:

                print(error)

        return audit_df

    # ==========================================================
    # CLOSE DATABASE
    # ==========================================================

    def close(self):

        if self.conn is not None:

            self.conn.close()

            self.conn = None


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":

    loader = None

    try:

        loader = DatabaseLoader()

        audit_df = loader.run()

        loader.conn.commit()

        print()
        print("=" * 70)
        print("DATABASE LOADING COMPLETED")
        print("=" * 70)

        print(audit_df.to_string(index=False))

    except Exception as e:

        print()
        print("=" * 70)
        print("❌ DATABASE LOADING FAILED")
        print("=" * 70)

        print(f"{type(e).__name__}: {e}")

        if loader is not None:

            try:
                loader.conn.rollback()
            except Exception:
                pass

        raise

    finally:

        if loader is not None:

            loader.close()
