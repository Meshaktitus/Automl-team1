
import pandas as pd

df = pd.read_excel("data/HumanResources.Employee.xlsx")

print("DATASET SHAPE")
print(df.shape)

print("\nNUMERICAL COLUMN STATISTICS")
print(df.describe())

print("\nCATEGORICAL VALUE COUNTS")
for col in ["JobTitle", "Gender", "MaritalStatus"]:
    print(f"\n{col}:")
    print(df[col].value_counts(dropna=False))

print("\nPOTENTIAL TARGET COLUMN CHECKS")
for col in ["JobTitle", "VacationHours", "SickLeaveHours"]:
    print(f"\nColumn: {col}")
    print("Data type:", df[col].dtype)
    print("Unique values:", df[col].nunique())
    print("Missing values:", df[col].isna().sum())
    print("Sample values:")
    print(df[col].head(10).tolist())
