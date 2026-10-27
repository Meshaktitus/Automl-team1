
import pandas as pd
from pathlib import Path

data_folder = Path("data")

for file in sorted(data_folder.glob("*.xlsx")):
    df = pd.read_excel(file)

    print("\n" + "=" * 55)
    print("FILE:", file.name)
    print("Rows:", len(df))
    print("Columns:", len(df.columns))

    print("\nColumn names and data types:")
    print(df.dtypes)

    print("\nMissing values:")
    print(df.isna().sum()[df.isna().sum() > 0])

    print("\nDistinct values per column:")
    print(df.nunique(dropna=True))

    print("\nFully duplicated rows:", df.duplicated().sum())

    print("\nDuplicate identifier occurrences:")
    for col in [
        "BusinessEntityID",
        "DepartmentID",
        "ShiftID",
        "JobCandidateID",
    ]:
        if col in df.columns:
            print(
                col,
                "duplicate occurrences:",
                df[col].duplicated().sum()
            )

    print("\nFirst five rows:")
    print(df.head())
