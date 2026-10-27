
import pandas as pd

file_path = "data/HumanResources.Employee.xlsx"
df = pd.read_excel(file_path)

print("=" * 65)
print("AUTOML - FEATURE REVIEW")
print("=" * 65)

for column in df.columns:
    unique_count = df[column].nunique(dropna=True)
    missing_count = df[column].isna().sum()

    flags = []

    if column in ["BusinessEntityID", "NationalIDNumber",
                  "LoginID", "rowguid"]:
        flags.append("Identifier - investigate before using")

    if unique_count <= 1:
        flags.append("Constant - not informative")

    if missing_count > 0:
        flags.append("Contains missing values")

    print(
        f"{column}: unique={unique_count}, "
        f"missing={missing_count}, "
        f"review={'; '.join(flags) if flags else 'No automatic flag'}"
    )

print("\nThis is a preliminary review, not a leakage detector.")
print("Check feature suitability separately for each target.")
