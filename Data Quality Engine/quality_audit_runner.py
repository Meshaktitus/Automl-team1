import pandas as pd
import numpy as np

# Define dataset file paths
files = {
    "Department": "HumanResources.Department (1).xlsx",
    "Employee": "HumanResources.Employee (1).xlsx",
    "EmployeeDepartmentHistory": "HumanResources.EmployeeDepartmentHistory (1).xlsx",
    "EmployeePayHistory": "HumanResources.EmployeePayHistory.xlsx",
    "JobCandidate": "HumanResources.JobCandidate (1).xlsx",
    "Shift": "HumanResources.Shift (1).xlsx"
}

# Load datasets and run data quality verification
quality_audit_results = {}

for name, filepath in files.items():
    # Read Excel sheets
    xls = pd.ExcelFile(filepath)
    sheet_name = xls.sheet_names[0]
    df = pd.read_excel(filepath, sheet_name=sheet_name)
    
    # Capture shape before analysis (for non-destructive verification)
    shape_before = df.shape
    
    # Run checks
    row_count, col_count = df.shape
    missing_vals = df.isnull().sum().to_dict()
    total_missing = int(df.isnull().sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    
    # Capture shape after analysis
    shape_after = df.shape
    non_destructive = (shape_before == shape_after)
    
    quality_audit_results[name] = {
        "RowCount": row_count,
        "ColCount": col_count,
        "MissingValues": missing_vals,
        "TotalMissing": total_missing,
        "DuplicateRows": duplicate_rows,
        "NonDestructive": non_destructive
    }

# Print summary report
import json
print("=== DATA QUALITY TEST SUITE EXECUTION REPORT ===")
print(json.dumps(quality_audit_results, indent=2))