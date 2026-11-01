
from pathlib import Path
import pandas as pd

# Path to the original Employee dataset
DATA_PATH = Path("data/raw/HumanResources.Employee.xlsx")

df = pd.read_excel(DATA_PATH)

print("========== DATASET OVERVIEW ==========")
print("Rows:", len(df))
print("Columns:", len(df.columns))
print("Duplicate rows:", df.duplicated().sum())

# --------------------------------------------------
# 1. LEAVE BALANCE SUMMARY
# --------------------------------------------------
print("\n========== LEAVE BALANCE SUMMARY ==========")

targets = ["VacationHours", "SickLeaveHours"]
print(df[targets].describe().round(2))

# --------------------------------------------------
# 2. MISSING VALUES
# --------------------------------------------------
print("\n========== MISSING VALUES ==========")

selected_columns = [
    "JobTitle",
    "Gender",
    "MaritalStatus",
    "HireDate",
    "BirthDate",
] + targets

print("\nMissing values in selected columns:")
print(df[selected_columns].isna().sum())

print("\nMissing values in all columns:")
print(df.isna().sum().to_string())

# --------------------------------------------------
# 3. JOB TITLE ANALYSIS
# --------------------------------------------------
print("\n========== JOB TITLE ANALYSIS ==========")

job_summary = (
    df.groupby("JobTitle", dropna=False)
    .agg(
        EmployeeCount=("BusinessEntityID", "count"),
        VacationMean=("VacationHours", "mean"),
        SickLeaveMean=("SickLeaveHours", "mean"),
        VacationMedian=("VacationHours", "median"),
        SickLeaveMedian=("SickLeaveHours", "median"),
    )
    .round(2)
    .sort_values("EmployeeCount", ascending=False)
)

print(job_summary.to_string())

# --------------------------------------------------
# 4. CATEGORICAL GROUP ANALYSIS
# --------------------------------------------------
print("\n========== CATEGORICAL GROUP ANALYSIS ==========")

for column in ["Gender", "MaritalStatus", "SalariedFlag"]:
    print(f"\n--- {column} ---")

    group_summary = (
        df.groupby(column, dropna=False)
        .agg(
            EmployeeCount=("BusinessEntityID", "count"),
            VacationMean=("VacationHours", "mean"),
            SickLeaveMean=("SickLeaveHours", "mean"),
        )
        .round(2)
    )

    print(group_summary.to_string())

# --------------------------------------------------
# 5. CORRELATION ANALYSIS
# --------------------------------------------------
print("\n========== CORRELATION ANALYSIS ==========")

numeric_columns = [
    "VacationHours",
    "SickLeaveHours",
    "OrganizationLevel",
    "SalariedFlag",
]

print(df[numeric_columns].corr().round(3))

# --------------------------------------------------
# 6. CONSTANT COLUMN ASSESSMENT
# --------------------------------------------------
print("\n========== CONSTANT COLUMN ASSESSMENT ==========")

constant_columns = [
    column
    for column in df.columns
    if df[column].nunique(dropna=False) == 1
]

if constant_columns:
    print("Columns with only one unique value:")
    for column in constant_columns:
        print(f"- {column}")
else:
    print("No constant columns found.")

# --------------------------------------------------
# 7. HIGH-CARDINALITY ASSESSMENT
# --------------------------------------------------
print("\n========== HIGH-CARDINALITY ASSESSMENT ==========")
print("Review threshold: more than 50% unique values.")

for column in df.columns:
    unique_count = df[column].nunique(dropna=True)
    unique_percentage = (unique_count / len(df) * 100) if len(df) else 0

    if unique_percentage > 50:
        print(
            f"{column}: {unique_count} unique values "
            f"({unique_percentage:.2f}%)"
        )

# --------------------------------------------------
# 8. POTENTIAL IDENTIFIER REVIEW
# --------------------------------------------------
print("\n========== POTENTIAL IDENTIFIER REVIEW ==========")

potential_identifiers = [
    "BusinessEntityID",
    "NationalIDNumber",
    "LoginID",
    "rowguid",
]

for column in potential_identifiers:
    if column in df.columns:
        unique_count = df[column].nunique(dropna=True)
        print(
            f"{column}: {unique_count} unique values "
            f"out of {len(df)} rows"
        )

print(
    "\nNote: These columns require review; "
    "this script does not automatically exclude them."
)

# --------------------------------------------------
# 9. PROVISIONAL FEATURE AND TARGET ASSESSMENT
# --------------------------------------------------
print("\n========== PROVISIONAL CANDIDATES ==========")

provisional_candidates = [
    "JobTitle",
    "VacationHours",
    "SickLeaveHours",
]

for column in provisional_candidates:
    if column in df.columns:
        print(
            f"{column}: present, "
            f"missing={df[column].isna().sum()}, "
            f"unique={df[column].nunique(dropna=True)}"
        )

print(
    "\nThese are provisional candidates only. "
    "Final feature and target selection requires team confirmation."
)

# --------------------------------------------------
# 10. COMPLETION
# --------------------------------------------------
print("\n========== COMPLETION ==========")
print("Exploratory data analysis completed.")
print("Feature assessment completed for this script.")
print("Original Excel dataset was not modified.")

# --------------------------------------------------
# 11. DISTRIBUTION, SKEWNESS, QUARTILES AND IQR
# --------------------------------------------------
print("\n========== DISTRIBUTION AND SCALING ASSESSMENT ==========")

numeric_columns = df.select_dtypes(include="number").columns.tolist()

distribution_results = []

for column in numeric_columns:
    values = df[column].dropna()

    if values.empty:
        continue

    q1 = values.quantile(0.25)
    median = values.quantile(0.50)
    q3 = values.quantile(0.75)
    iqr = q3 - q1
    skewness = values.skew()

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outlier_count = (
        (values < lower_bound) | (values > upper_bound)
    ).sum()

    distribution_results.append({
        "Column": column,
        "Q1": q1,
        "Median": median,
        "Q3": q3,
        "IQR": iqr,
        "Skewness": skewness,
        "PotentialOutliers": int(outlier_count),
    })

distribution_df = pd.DataFrame(distribution_results)

if not distribution_df.empty:
    print(distribution_df.round(3).to_string(index=False))

    print("\n========== SCALING REVIEW GUIDANCE ==========")

    for _, row in distribution_df.iterrows():
        skewness = row["Skewness"]
        iqr = row["IQR"]
        column = row["Column"]

        if pd.isna(skewness):
            recommendation = "Insufficient variation for skewness assessment"
        elif abs(skewness) >= 1:
            recommendation = (
                "Strong skewness: investigate transformation "
                "and scaling alternatives"
            )
        elif abs(skewness) >= 0.5:
            recommendation = (
                "Moderate skewness: review distribution before choosing scaling"
            )
        else:
            recommendation = (
                "No strong skewness signal; compare scaling options as needed"
            )

        if iqr == 0:
            recommendation += "; zero IQR requires further review"

        print(f"{column}: {recommendation}")

    print(
        "\nNote: Potential outliers are flagged using the 1.5 x IQR rule. "
        "They are not automatically removed. These recommendations are "
        "advisory and do not change the preprocessing pipeline."
    )
else:
    print("No numeric columns are available for distribution analysis.")

