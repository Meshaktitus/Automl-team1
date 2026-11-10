import pandas as pd

print("--- Processing Shift Data ---")
df = pd.read_excel('HumanResources.Shift (1).xlsx', sheet_name='HumanResources.Shift')
print(f"Dataset Shape: {df.shape}")
print(df.head(3))
