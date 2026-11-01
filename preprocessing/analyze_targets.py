
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "HumanResources.Employee.xlsx"
)


def analyze_targets():
    df = pd.read_excel(INPUT_FILE)

    feature = "JobTitle"
    targets = ["VacationHours", "SickLeaveHours"]

    print("=" * 55)
    print("TARGET AND FEATURE ANALYSIS")
    print("=" * 55)

    print("\n1. Overall target statistics")
    print(df[targets].describe().round(2))

    print("\n2. Target values by job title")
    summary = (
        df.groupby(feature)[targets]
        .agg(["count", "mean", "std", "min", "max"])
        .round(2)
    )
    print(summary.to_string())

    print("\n3. Number of employees per job title")
    counts = df[feature].value_counts()
    print(counts.describe().round(2))

    print("\n4. Job titles with only one employee")
    print(counts[counts == 1])

    print("\n5. Number of distinct target values")
    for target in targets:
        print(f"{target}: {df[target].nunique()}")

    print("\nAnalysis completed.")
    print("Original dataset was not modified.")


if __name__ == "__main__":
    analyze_targets()
