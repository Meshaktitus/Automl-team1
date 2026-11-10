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
print("DUPLICATE DETECTION VALIDATION REPORT")
print("=" * 65)

for name, filepath in datasets.items():
    if not os.path.exists(filepath):
        print(f"\n[Warning] File not found: {filepath}")
        continue
        
    xls = pd.ExcelFile(filepath)
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        print(f"\n--- Dataset: {name} (Sheet: {sheet}) ---")
        
        # 1. Exact Duplicate-Row Detection
        exact_dups = df.duplicated().sum()
        print(f"  Exact Duplicate Rows: {exact_dups}")
        
        # 2. Duplicate-Identifier Detection
        if name == "Department":
            dup_id = df['DepartmentID'].duplicated().sum()
            print(f"  Duplicate 'DepartmentID's: {dup_id}")
            
        elif name == "Employee":
            for col in ['BusinessEntityID', 'NationalIDNumber', 'LoginID']:
                dup_id = df[col].duplicated().sum()
                print(f"  Duplicate '{col}'s: {dup_id}")
                
        elif name == "EmployeeDepartmentHistory":
            single_id_dups = df['BusinessEntityID'].duplicated().sum()
            composite_dups = df.duplicated(subset=['BusinessEntityID', 'StartDate']).sum()
            print(f"  Duplicate 'BusinessEntityID' (Single): {single_id_dups} (Normal for history table)")
            print(f"  Duplicate Composite Key ('BusinessEntityID' + 'StartDate'): {composite_dups}")
            
        elif name == "EmployeePayHistory":
            single_id_dups = df['BusinessEntityID'].duplicated().sum()
            composite_dups = df.duplicated(subset=['BusinessEntityID', 'RateChangeDate']).sum()
            print(f"  Duplicate 'BusinessEntityID' (Single): {single_id_dups} (Normal for history table)")
            print(f"  Duplicate Composite Key ('BusinessEntityID' + 'RateChangeDate'): {composite_dups}")
            
        elif name == "JobCandidate":
            dup_id = df['JobCandidateID'].duplicated().sum()
            print(f"  Duplicate 'JobCandidateID's: {dup_id}")
            
        elif name == "Shift":
            dup_id = df['ShiftID'].duplicated().sum()
            print(f"  Duplicate 'ShiftID's: {dup_id}")

print("\n" + "=" * 65)
print("Duplicate Validation Complete!")
print("=" * 65)