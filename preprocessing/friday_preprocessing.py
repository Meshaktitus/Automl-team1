
from pathlib import Path

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT / "data" / "raw" / "HumanResources.Employee.xlsx"
)
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "friday_preprocessing_sample.csv"

DATE_COLUMNS = ["BirthDate", "HireDate", "ModifiedDate"]
NUMERIC_COLUMNS = ["OrganizationLevel", "VacationHours", "SickLeaveHours"]
CATEGORICAL_COLUMNS = ["JobTitle", "MaritalStatus", "Gender"]


def preprocess_employee_data(df):
    """Demonstrate imputation, date features, encoding and scaling."""

    result = df.copy()

    # 1. Impute missing numeric values using the median.
    numeric_cols = [
        col for col in NUMERIC_COLUMNS if col in result.columns
    ]
    if numeric_cols:
        imputer = SimpleImputer(strategy="median")
        result[numeric_cols] = imputer.fit_transform(result[numeric_cols])

    # 2. Impute missing categorical values using the most frequent value.
    categorical_cols = [
        col for col in CATEGORICAL_COLUMNS if col in result.columns
    ]
    if categorical_cols:
        imputer = SimpleImputer(strategy="most_frequent")
        result[categorical_cols] = imputer.fit_transform(
            result[categorical_cols]
        )

    # 3. Extract date-derived features.
    for column in DATE_COLUMNS:
        if column in result.columns:
            dates = pd.to_datetime(result[column], errors="coerce")
            result[f"{column}_Year"] = dates.dt.year.astype("Int64")
            result[f"{column}_Month"] = dates.dt.month.astype("Int64")
            result[f"{column}_DayOfWeek"] = (
                dates.dt.dayofweek.astype("Int64")
            )

    # 4. Scale numeric columns, excluding potential targets.
    # Keep target values in their original units for this prototype.
    scale_cols = [
        col for col in ["OrganizationLevel"]
        if col in result.columns
    ]
    if scale_cols:
        scaler = StandardScaler()
        result[scale_cols] = scaler.fit_transform(result[scale_cols])

    # 5. One-hot encode selected categorical columns.
    encode_cols = [
        col for col in ["JobTitle", "MaritalStatus", "Gender"]
        if col in result.columns
    ]
    if encode_cols:
        result = pd.get_dummies(
            result,
            columns=encode_cols,
            dtype=int,
        )

    return result


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {INPUT_FILE}")

    original = pd.read_excel(INPUT_FILE)
    processed = preprocess_employee_data(original)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    processed.to_csv(OUTPUT_FILE, index=False)

    print("FRIDAY PREPROCESSING PROTOTYPE")
    print(f"Original shape: {original.shape}")
    print(f"Processed shape: {processed.shape}")
    print(f"Missing values remaining: {processed.isna().sum().sum()}")
    print("\nProcessed data types:")
    print(processed.dtypes.value_counts())
    print(f"\nOutput saved to: {OUTPUT_FILE}")
    print("Original Excel file was not modified.")


if __name__ == "__main__":
    main()
