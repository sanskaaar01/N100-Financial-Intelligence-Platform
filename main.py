from pathlib import Path
from src.etl.loader import ExcelLoader

loader = ExcelLoader()
raw_folder = Path("data/raw")

files = {
    "companies.xlsx": 1,
    "profitandloss.xlsx": 1,
    "balancesheet.xlsx": 1,
    "cashflow.xlsx": 1,
    "analysis.xlsx": 1,
    "documents.xlsx": 1,
    "prosandcons.xlsx": 1,
    "sectors.xlsx": 0,
    "stock_prices.xlsx": 0,
    "market_cap.xlsx": 0,
    "financial_ratios.xlsx": 0,
    "peer_groups.xlsx": 0,
}

for file, header in files.items():
    df = loader.load_excel(raw_folder / file, header=header)

    print("\n" + "=" * 80)
    print(file)
    print("=" * 80)
    print(df.columns.tolist())