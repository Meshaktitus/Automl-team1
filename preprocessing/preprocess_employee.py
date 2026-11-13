
from pathlib import Path
import pandas as pd


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "HumanResources.Employee.xlsx"
)

# Proposed input and regression targets
FEATURE_COLUMN = "JobTitle"

TARGET_COLUMNS = [
    "VacationHours",
    "SickLeaveHours",
]


def validate_employee_dataset():
    """Validate required columns and data quality without changing the source."""

    print("=" * 60)
    print("EMPLOYEE DATASET - PREPROCESSING VALIDATION")
    print("=" * 60)

    # Check that the original file exists
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {INPUT_FILE}"
        )

    # Read the Excel file without modifying it
    df = pd.read_excel(INPUT_FILE)

    print(f"\nInput file: {INPUT_FILE.name}")
    print(f"Total rows: {len(df)}")
    print(f"Total columns: {len(df.columns)}")

    # Check required columns
    required_columns = [FEATURE_COLUMN] + TARGET_COLUMNS
    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        print("\nERROR: Required columns are missing:")
        print(missing_columns)
        return

    print("\nRequired columns found:")
    for column in required_columns:
        print(f"- {column}")

    # Check missing values
    print("\nMissing values in required columns:")
    print(df[required_columns].isnull().sum())

    # Check target data types
    print("\nTarget column data types:")
    for column in TARGET_COLUMNS:
        print(f"{column}: {df[column].dtype}")

    # Check whether target values are numeric
    print("\nNumeric target validation:")
    for column in TARGET_COLUMNS:
        numeric_values = pd.to_numeric(
            df[column], errors="coerce"
        )

        invalid_count = (
            df[column].notna() & numeric_values.isna()
        ).sum()

        print(f"{column}: {invalid_count} non-numeric values")

    # Check category consistency
    print("\nJobTitle category checks:")
    print(
        "Unique non-missing JobTitle values:",
        df[FEATURE_COLUMN].nunique()
    )
    print(
        "Missing JobTitle values:",
        df[FEATURE_COLUMN].isna().sum()
    )

    print("\nSample JobTitle values:")
    print(df[FEATURE_COLUMN].dropna().unique()[:10])

    # Count rows with all required values present
    valid_mask = df[required_columns].notna().all(axis=1)

    print("\nRecord validation summary:")
    print(f"Rows with all required values: {valid_mask.sum()}")
    print(f"Rows missing required values: {(~valid_mask).sum()}")

    print("\nValidation completed.")
    print("Original Excel file was not modified.")
    print("=" * 60)


if __name__ == "__main__":
    validate_employee_dataset()
