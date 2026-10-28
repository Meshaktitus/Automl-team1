import pandas as pd

print("--- Processing Employee Data ---")
df = pd.read_excel('HumanResources.Employee (1).xlsx', sheet_name='HumanResources.Employee')
print(f"Dataset Shape: {df.shape}")
print(df.head(3))

