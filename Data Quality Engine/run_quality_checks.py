import pandas as pd

# Load csv file safely
df = pd.read_csv('demo_customers.csv', skip_blank_lines=True)

print("=== DATA QUALITY MODULE EXECUTION EVIDENCE ===")
print(f"Total Rows: {len(df)}")
print(f"Total Columns: {len(df.columns)}")
print(f"Duplicate Rows Count: {df.duplicated().sum()}")

print("\n--- Missing Values Count ---")
print(df.isnull().sum())

print("\n--- Missing Values Percentage ---")
print((df.isnull().sum() / len(df)) * 100)