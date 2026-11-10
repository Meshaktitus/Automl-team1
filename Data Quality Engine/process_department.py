import pandas as pd

print("--- Processing Department Data ---")
df = pd.read_excel('HumanResources.Department (1).xlsx', sheet_name='HumanResources.Department')
print(f"Dataset Shape: {df.shape}")
print(df.head(3))