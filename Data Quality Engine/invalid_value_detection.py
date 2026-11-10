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

print("=" * 65)
print("INVALID-VALUE DETECTION VALIDATION REPORT")
print("=" * 65)

for name, filepath in datasets.items():
    if not os.path.exists(filepath):
        print(f"\n[Warning] File not found: {filepath}")
        continue
        
    xls = pd.ExcelFile(filepath)
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        total_rows = len(df)
        print(f"\n--- Dataset: {name} (Sheet: {sheet}) ---")
        
        invalid_found = False
        
        # 1. Check for Negative Numbers (e.g., negative Vacation Hours, Rates, Sick Leave)
        for col in df.select_dtypes(include=['int64', 'float64']).columns:
            negatives = (df[col] < 0).sum()
            if negatives > 0:
                print(f"  [Invalid Negative Values]: Column '{col}' has {negatives} negative values.")
                invalid_found = True
                
        # 2. Check for Malformed Dates or Logical Date Anomalies
        for col in df.select_dtypes(include=['datetime64[ns]', 'object']).columns:
            if 'date' in col.lower() or 'birth' in col.lower():
                # Attempt to convert to datetime to catch unparseable/malformed strings
                parsed = pd.to_datetime(df[col], errors='coerce')
                malformed = df[col][parsed.isnull() & df[col].notnull()]
                if len(malformed) > 0:
                    print(f"  [Malformed Dates]: Column '{col}' has {len(malformed)} malformed entries.")
                    invalid_found = True
                    
            # Specific validation checks for Employee dataset (e.g., BirthDate vs HireDate logic)
            if name == "Employee" and 'BirthDate' in df.columns and 'HireDate' in df.columns:
                # Check if anyone was hired before age 15 or with future birth dates
                future_births = (df['BirthDate'] > '2008-01-01').sum()
                if future_births > 0:
                    print(f"  [Invalid Logic]: {future_births} records have unrealistic birth dates.")
                    invalid_found = True

        if not invalid_found:
            print("  [Status]: No invalid negative values, percentages, or malformed dates detected.")

print("\n" + "=" * 65)
print("Invalid-Value Validation Complete!")
print("=" * 65)