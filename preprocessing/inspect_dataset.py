
from pathlib import Path
import pandas as pd


# Locate the project folder and original dataset
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "HumanResources.Employee.xlsx"
)


def inspect_dataset():
    # Step 1: Check whether the dataset exists
    if not DATASET_PATH.exists():
        print(f"Dataset not found: {DATASET_PATH}")
        return

    # Step 2: Read the original Excel dataset
    df = pd.read_excel(DATASET_PATH)

    # Step 3: Display dataset overview
    print("\n========== DATASET OVERVIEW ==========")
    print(f"File: {DATASET_PATH.name}")
    print(f"Number of rows: {df.shape[0]}")
    print(f"Number of columns: {df.shape[1]}")

    # Step 4: Display column names
    print("\n========== COLUMN NAMES ==========")
    print(df.columns.tolist())

    # Step 5: Display data types
    print("\n========== DATA TYPES ==========")
    print(df.dtypes)

    # Step 6: Check missing values
    print("\n========== MISSING VALUES ==========")
    print(df.isnull().sum())

    print("\nTotal missing values:", df.isnull().sum().sum())

    # Step 7: Check duplicate rows
    print("\n========== DUPLICATE ROWS ==========")
    print("Duplicate rows:", df.duplicated().sum())

    # Step 8: Check unique values in each column
    print("\n========== UNIQUE VALUES ==========")
    for column in df.columns:
        print(f"{column}: {df[column].nunique(dropna=False)}")

    # Step 9: Check ID uniqueness
    print("\n========== ID CHECK ==========")
    print(
        "BusinessEntityID unique:",
        df["BusinessEntityID"].is_unique
    )
    print(
        "NationalIDNumber unique:",
        df["NationalIDNumber"].is_unique
    )

    # Step 10: Check numeric ranges and statistics
    print("\n========== NUMERIC RANGES ==========")
    print(df.select_dtypes(include="number").describe().T)

    # Step 11: Display rows containing missing values
    print("\n========== ROWS WITH MISSING VALUES ==========")
    missing_rows = df[df.isnull().any(axis=1)]

    if missing_rows.empty:
        print("No missing values found.")
    else:
        print(missing_rows.to_string(index=False))

    # Step 12: Check categorical values
    print("\n========== CATEGORY VALUES ==========")

    categorical_columns = [
        "JobTitle",
        "MaritalStatus",
        "Gender",
        "CurrentFlag"
    ]

    for column in categorical_columns:
        if column in df.columns:
            print(f"\n{column}:")
            print(df[column].value_counts(dropna=False).to_string())

    # Step 13: Check date columns
    print("\n========== DATE COLUMNS ==========")

    date_columns = [
        "BirthDate",
        "HireDate",
        "ModifiedDate"
    ]

    for column in date_columns:
        if column in df.columns:
            print(f"\n{column}:")
            print("Earliest date:", df[column].min())
            print("Latest date:", df[column].max())

    # Step 14: Display the first five rows
    print("\n========== FIRST FIVE ROWS ==========")
    print(df.head().to_string(index=False))

    # Step 15: Finish
    print("\n========== INSPECTION COMPLETED ==========")
    print("The original Excel dataset has not been modified.")


if __name__ == "__main__":
    inspect_dataset()
