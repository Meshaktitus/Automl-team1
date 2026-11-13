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
print("SEVERITY CLASSIFICATION REPORT: WARNINGS VS. BLOCKING ERRORS")
print("=" * 70)

warning_count = 0
blocking_count = 0

for name, filepath in datasets.items():
    if not os.path.exists(filepath):
        continue
    xls = pd.ExcelFile(filepath)
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        print(f"\n--- Dataset: {name} ({sheet}) ---")
        
        # 1. Exact Duplicate Rows -> Blocking Error
        exact_dups = df.duplicated().sum()
        if exact_dups > 0:
            print(f"  [BLOCKING ERROR] Found {exact_dups} exact duplicate rows.")
            blocking_count += 1
        else:
            print("  [Pass] Exact Duplicate Rows: 0")

        # 2. Negative Numerical Values -> Blocking Error
        for col in df.select_dtypes(include=['int64', 'float64']).columns:
            if (df[col] < 0).sum() > 0:
                print(f"  [BLOCKING ERROR] Negative values found in '{col}'.")
                blocking_count += 1

        # 3. Missing Values Classification
        if name == "Employee":
            null_nodes = df['OrganizationNode'].isnull().sum()
            if null_nodes > 0:
                print(f"  [WARNING] {null_nodes} missing OrganizationNode (Root executive - expected).")
                warning_count += 1
        elif name == "EmployeeDepartmentHistory":
            null_ends = df['EndDate'].isnull().sum()
            if null_ends > 0:
                print(f"  [WARNING] {null_ends} active department records with missing EndDate (Expected).")
                warning_count += 1
        elif name == "JobCandidate":
            null_beis = df['BusinessEntityID'].isnull().sum()
            if null_beis > 0:
                print(f"  [WARNING] {null_beis} candidates without BusinessEntityID (Not yet hired - expected).")
                warning_count += 1

        # 4. Statistical Outliers (IQR) -> Warning
        for col in df.select_dtypes(include=['int64', 'float64']).columns:
            if not col.lower().endswith('id') and not col.lower().endswith('flag'):
                s = df[col].dropna()
                q1, q3 = s.quantile(0.25), s.quantile(0.75)
                iqr = q3 - q1
                outliers = s[(s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)]
                if len(outliers) > 0 and not (s < 0).any():
                    print(f"  [WARNING] Column '{col}' has {len(outliers)} statistical IQR outliers (Valid extreme values).")
                    warning_count += 1

print("\n" + "=" * 70)
print(f"Summary: Total Blocking Errors = {blocking_count} | Total Warnings = {warning_count}")
print("=" * 70)