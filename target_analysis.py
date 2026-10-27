
import pandas as pd

df = pd.read_excel("data/HumanResources.Employee.xlsx")

# 1. Check JobTitle category frequencies
print("JOB TITLE DISTRIBUTION")
counts = df["JobTitle"].value_counts()

print("Number of categories:", len(counts))
print("Categories with only 1 record:", (counts == 1).sum())
print("Categories with 5 or fewer records:", (counts <= 5).sum())
print("\n10 least frequent job titles:")
print(counts.tail(10))

# 2. Examine numerical candidate columns
for col in ["VacationHours", "SickLeaveHours"]:
    print(f"\n{'=' * 40}")
    print("COLUMN:", col)
    print("Minimum:", df[col].min())
    print("Maximum:", df[col].max())
    print("Mean:", round(df[col].mean(), 2))
    print("Median:", df[col].median())
    print("Standard deviation:", round(df[col].std(), 2))
    print("Unique values:", df[col].nunique())

# 3. Check constant columns
print("\nCONSTANT COLUMNS")
for col in df.columns:
    if df[col].nunique(dropna=False) <= 1:
        print(col, "has only one value")
