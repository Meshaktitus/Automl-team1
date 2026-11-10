import os
import pandas as pd

# Define the dictionary of datasets and their filenames
datasets = {
    "Department": "HumanResources.Department (1).xlsx",
    "Employee": "HumanResources.Employee (1).xlsx",
    "EmployeeDepartmentHistory": "HumanResources.EmployeeDepartmentHistory (1).xlsx",
    "EmployeePayHistory": "HumanResources.EmployeePayHistory.xlsx",
    "JobCandidate": "HumanResources.JobCandidate (1).xlsx",
    "Shift": "HumanResources.Shift (1).xlsx"
}

# Configured missing markers to check in string/object columns
missing_markers = ['NA', 'N/A', 'null', 'NULL', 'None', '-', '?']

print("=" * 65)
print("MISSING-VALUE DETECTION VALIDATION REPORT")
print("=" * 65)

for name, filepath in datasets.items():
    if not os.path.exists(filepath):
        print(f"\n[Warning] File not found: {filepath}")
        continue
        
    # Load Excel file and inspect sheets
    xls = pd.ExcelFile(filepath)
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        total_rows = len(df)
        
        print(f"\n--- Dataset: {name} (Sheet: {sheet}) ---")
        print(f"Total Rows: {total_rows} | Total Columns: {df.shape[1]}")
        
        # 1. Null Detection (NaN / None)
        null_counts = df.isnull().sum()
        null_counts = null_counts[null_counts > 0]
        if not null_counts.empty:
            print("  [Null Values Found]:")
            for col, count in null_counts.items():
                print(f"    - {col}: {count} missing ({(count/total_rows)*100:.1f}%)")
        else:
            print("  [Null Values]: None")
            
        # 2. Empty-String Detection
        empty_counts = pd.Series(0, index=df.columns)
        for col in df.select_dtypes(include=['object', 'string']):
            s = df[col].astype(str).str.strip()
            empty_counts[col] = (s == '').sum()
        empty_counts = empty_counts[empty_counts > 0]
        
        if not empty_counts.empty:
            print("  [Empty Strings Found]:")
            for col, count in empty_counts.items():
                print(f"    - {col}: {count} empty strings")
        else:
            print("  [Empty Strings]: None")
            
        # 3. Configured Missing Marker Detection
        marker_found = False
        for col in df.select_dtypes(include=['object', 'string']):
            s = df[col].astype(str).str.strip()
            for marker in missing_markers:
                matches = (s.str.lower() == marker.lower()).sum()
                if matches > 0:
                    if not marker_found:
                        print("  [Configured Missing Markers Found]:")
                        marker_found = True
                    print(f"    - {col}: {matches} occurrences of marker '{marker}'")
        if not marker_found:
            print("  [Configured Markers]: None")

print("\n" + "=" * 65)
print("Validation Complete!")
print("=" * 65)