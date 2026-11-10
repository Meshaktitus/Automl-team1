import os
import pandas as pd

# Define dataset paths
datasets = {
    "Department": "HumanResources.Department (1).xlsx",
    "Employee": "HumanResources.Employee (1).xlsx",
    "EmployeeDepartmentHistory": "HumanResources.EmployeeDepartmentHistory (1).xlsx",
    "EmployeePayHistory": "HumanResources.EmployeePayHistory.xlsx",
    "JobCandidate": "HumanResources.JobCandidate (1).xlsx",
    "Shift": "HumanResources.Shift (1).xlsx"
}

print("=" * 70)
print("IQR OUTLIER DETECTION & INVALID VALUE SEPARATION REPORT")
print("=" * 70)

for name, filepath in datasets.items():
    if not os.path.exists(filepath):
        print(f"\n[Warning] File not found: {filepath}")
        continue
        
    xls = pd.ExcelFile(filepath)
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        print(f"\n--- Dataset: {name} (Sheet: {sheet}) ---")
        
        # Select numeric metric columns (skipping primary key IDs, flags)
        num_cols = [c for c in df.select_dtypes(include=['int64', 'float64']).columns 
                    if not c.lower().endswith('id') and not c.lower().endswith('flag')]
        
        if not num_cols:
            print("  No numerical metric columns to evaluate for IQR.")
            continue
            
        for col in num_cols:
            series = df[col].dropna()
            
            # Step 1: Calculate IQR Bounds
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            # Identify all values outside 1.5 * IQR bounds
            outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
            iqr_outliers = df[outlier_mask]
            
            # Step 2: Distinguish Invalid Values vs Valid Statistical Outliers
            # Example rule: Pay Rate / Hours cannot be negative (< 0)
            invalid_mask = df[col] < 0
            invalid_values = df[invalid_mask]
            valid_outliers = df[outlier_mask & ~invalid_mask]
            
            print(f"\n  Column: '{col}'")
            print(f"    - Statistics: Q1={q1:.2f}, Q3={q3:.2f}, IQR={iqr:.2f}")
            print(f"    - IQR Bounds: [{lower_bound:.2f}, {upper_bound:.2f}]")
            print(f"    - Total Outliers Detected: {len(iqr_outliers)}")
            print(f"      ├── Confirmed Invalid Values (< 0): {len(invalid_values)}")
            print(f"      └── Valid Statistical Outliers: {len(valid_outliers)}")
            
            if len(valid_outliers) > 0:
                top_values = valid_outliers[col].head(5).tolist()
                print(f"    - Sample Valid Outlier Values: {top_values}")

print("\n" + "=" * 70)
print("IQR Outlier Detection Complete!")
print("=" * 70)