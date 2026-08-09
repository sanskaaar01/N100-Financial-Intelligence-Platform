"""
loader.py

Universal Excel Loader
"""

from pathlib import Path
import pandas as pd
from ..etl.validator import DataValidator

class ExcelLoader:

    def __init__(self):
        pass

    def load_excel(self, filepath, header=0):

        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"{filepath} not found.")

        print(f"Loading {filepath.name}...")

        df = pd.read_excel(filepath, header=header)

        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )

        print(f"Rows : {len(df)}")
        print(f"Columns : {len(df.columns)}")

        return df