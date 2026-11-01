
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/raw")

for file_path in sorted(DATA_DIR.glob("*.xlsx")):
    print("\n" + "=" * 70)
    print(f"DATASET: {file_path.name}")
    print("=" * 70)

    try:
        df = pd.read_excel(file_path)

        print(f"Rows: {df.shape[0]}")
        print(f"Columns: {df.shape[1]}")

        print("\nColumn names and data types:")
        print(df.dtypes.to_string())

        print("\nMissing values per column:")
        print(df.isnull().sum().to_string())

        print(f"\nExact duplicate rows: {df.duplicated().sum()}")

        print("\nFirst 3 rows:")
        print(df.head(3).to_string(index=False))

    except Exception as error:
        print(f"Could not inspect file: {error}")
