
from pathlib import Path

import pandas as pd
from sklearn.preprocessing import OneHotEncoder


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "HumanResources.Employee.xlsx"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "job_title_encoding_sample.csv"

FEATURE_COLUMN = "JobTitle"
TARGET_COLUMNS = ["VacationHours", "SickLeaveHours"]


def encode_job_title():
    """Validate and encode JobTitle without modifying the raw dataset."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {INPUT_FILE}")

    df = pd.read_excel(INPUT_FILE)

    required_columns = [FEATURE_COLUMN] + TARGET_COLUMNS
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # For this initial sample, use only records with complete
    # feature and target values. No imputation is performed.
    sample = df[required_columns].dropna().copy()

    if sample.empty:
        raise ValueError("No complete records available for encoding.")

    # Fit the encoder on this sample only for a demonstration.
    # In model development, fit it on training data only.
    encoder = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=False,
    )

    encoded_values = encoder.fit_transform(sample[[FEATURE_COLUMN]])

    encoded_columns = encoder.get_feature_names_out([FEATURE_COLUMN])

    encoded_df = pd.DataFrame(
        encoded_values,
        columns=encoded_columns,
        index=sample.index,
    )

    # Retain the numeric targets for inspection.
    result = pd.concat(
        [
            encoded_df,
            sample[TARGET_COLUMNS],
        ],
        axis=1,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False)

    print("JobTitle encoding sample completed.")
    print(f"Input rows used: {len(sample)}")
    print(f"Original JobTitle categories: {sample[FEATURE_COLUMN].nunique()}")
    print(f"Encoded feature count: {len(encoded_columns)}")
    print(f"Output file: {OUTPUT_FILE}")
    print("Original Excel dataset was not modified.")


if __name__ == "__main__":
    encode_job_title()
