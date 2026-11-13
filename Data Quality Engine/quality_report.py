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

print("=" * 110)
print("COMPREHENSIVE DATA QUALITY REPORT")
print("=" * 110)

quality_findings = []

# Analyze datasets and compile findings dynamically
for name, filepath in datasets.items():
    if not os.path.exists(filepath):
        continue
    xls = pd.ExcelFile(filepath)
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        
        # 1. Missing Values checks
        if name == "Employee":
            null_count = df[['OrganizationNode', 'OrganizationLevel']].isnull().sum().max()
            if null_count > 0:
                quality_findings.append({
                    "Rule ID": "MIS-001",
                    "Severity": "Warning",
                    "Dataset": name,
                    "Column": "OrganizationNode / Level",
                    "Affected Rows": int(null_count),
                    "Recommended Action": "Verify top executive root node; expected for CEO."
                })
        elif name == "EmployeeDepartmentHistory":
            null_count = df['EndDate'].isnull().sum()
            if null_count > 0:
                quality_findings.append({
                    "Rule ID": "MIS-002",
                    "Severity": "Warning",
                    "Dataset": name,
                    "Column": "EndDate",
                    "Affected Rows": int(null_count),
                    "Recommended Action": "Confirm null EndDate represents active department assignments."
                })
        elif name == "JobCandidate":
            null_count = df['BusinessEntityID'].isnull().sum()
            if null_count > 0:
                quality_findings.append({
                    "Rule ID": "MIS-003",
                    "Severity": "Warning",
                    "Dataset": name,
                    "Column": "BusinessEntityID",
                    "Affected Rows": int(null_count),
                    "Recommended Action": "Validate candidate status; expect null IDs until onboarding."
                })

        # 2. Duplicate checks
        exact_dups = df.duplicated().sum()
        if exact_dups > 0:
            quality_findings.append({
                "Rule ID": "DUP-001",
                "Severity": "Blocking Error",
                "Dataset": name,
                "Column": "Entire Row",
                "Affected Rows": int(exact_dups),
                "Recommended Action": "Purge exact duplicate rows to prevent data distortion."
            })

        # 3. Invalid Values checks (Negatives)
        for col in df.select_dtypes(include=['int64', 'float64']).columns:
            neg_count = (df[col] < 0).sum()
            if neg_count > 0:
                quality_findings.append({
                    "Rule ID": "INV-001",
                    "Severity": "Blocking Error",
                    "Dataset": name,
                    "Column": col,
                    "Affected Rows": int(neg_count),
                    "Recommended Action": "Reject negative values; correct data entry error."
                })

        # 4. IQR Outlier checks
        for col in df.select_dtypes(include=['int64', 'float64']).columns:
            if not col.lower().endswith('id') and not col.lower().endswith('flag'):
                s = df[col].dropna()
                q1, q3 = s.quantile(0.25), s.quantile(0.75)
                iqr = q3 - q1
                outliers = s[(s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)]
                if len(outliers) > 0 and not (s < 0).any():
                    quality_findings.append({
                        "Rule ID": "OUT-001",
                        "Severity": "Warning",
                        "Dataset": name,
                        "Column": col,
                        "Affected Rows": int(len(outliers)),
                        "Recommended Action": f"Review IQR outliers (values > {q3 + 1.5 * iqr:.2f}) for executive validity."
                    })

# Print formatted report table
report_df = pd.DataFrame(quality_findings)
print(report_df.to_string(index=False))
print("=" * 110)
print("Quality Report Generated Successfully!")
print("=" * 110)