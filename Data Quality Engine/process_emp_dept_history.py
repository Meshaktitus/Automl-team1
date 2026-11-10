import pandas as pd

print("--- Processing Employee Department History Data ---")
df = pd.read_excel('HumanResources.EmployeeDepartmentHistory (1).xlsx', sheet_name=0)
print(f"Dataset Shape: {df.shape}")
print(df.head(3))