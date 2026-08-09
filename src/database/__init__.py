from pathlib import Path
import pandas as pd

from .database import Database
from ..etl.loader import ExcelLoader


class DatabaseLoader:

    def __init__(self):

        self.root = Path(__file__).resolve().parents[2]

        self.raw_folder = self.root / "data" / "raw"

        self.output_folder = self.root / "data" / "output"
        self.output_folder.mkdir(exist_ok=True)

        self.conn = Database().connect()

        self.loader = ExcelLoader()

        self.audit = []

    def read_file(self, filename):

        filepath = self.raw_folder / filename

        return self.loader.load_excel(filepath)

    def insert_dataframe(self, table_name, df):

        df.to_sql(
            table_name,
            self.conn,
            if_exists="append",
            index=False
        )

        self.audit.append({
            "table": table_name,
            "rows_loaded": len(df),
            "status": "SUCCESS"
        })

        print(f"{table_name} -> {len(df)} rows loaded")

    def run(self):

        print("\nLoading Excel files into SQLite...\n")

        files = [
            ("companies.xlsx", "companies"),
            ("analysis.xlsx", "analysis"),
            ("documents.xlsx", "documents"),
            ("prosandcons.xlsx", "prosandcons"),
            ("sectors.xlsx", "sectors"),
            ("peer_groups.xlsx", "peer_groups"),
            ("profitandloss.xlsx", "profitandloss"),
            ("balancesheet.xlsx", "balancesheet"),
            ("cashflow.xlsx", "cashflow"),
            ("financial_ratios.xlsx", "financial_ratios"),
            ("stock_prices.xlsx", "stock_prices")
        ]

        for excel_file, table_name in files:

            print(f"Loading {excel_file}...")

            df = self.read_file(excel_file)

            self.insert_dataframe(table_name, df)

        audit_df = pd.DataFrame(self.audit)

        audit_df.to_csv(
            self.output_folder / "load_audit.csv",
            index=False
        )

        print("\nload_audit.csv generated.")
        print("\nAll files loaded successfully.")


if __name__ == "__main__":

    loader = DatabaseLoader()

    loader.run()

    loader.conn.commit()

    loader.conn.close()

    print("\nDatabase loading completed successfully.")