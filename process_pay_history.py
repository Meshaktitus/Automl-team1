import pandas as pd

print("--- Processing Pay History Data ---")
df = pd.read_excel('HumanResources.EmployeePayHistory.xlsx', sheet_name=0) # Note: This one doesn't have (1)
print(f"Dataset Shape: {df.shape}")
print(df.head(3))