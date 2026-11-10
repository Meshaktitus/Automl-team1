import pandas as pd
import numpy as np
import json
import os

class HRDataQualityAnalyzer:
    def __init__(self, file_path, sheet_name):
        self.file_path = file_path
        self.sheet_name = sheet_name
        # 7. Verify source data is not modified (Non-destructive check)
        self.raw_df = pd.read_excel(file_path, sheet_name=sheet_name)
        self.original_shape = self.raw_df.shape
        self.issues = []

    def run_all_checks(self):
        self.verify_missing_values()
        self.verify_duplicates_and_identifiers()
        self.verify_empty_strings()
        self.verify_date_formats()
        
        is_modified = (self.raw_df.shape != self.original_shape)
        
        return {
            "file": self.file_path,
            "sheet": self.sheet_name,
            "total_rows": self.original_shape[0],
            "total_columns": self.original_shape[1],
            "total_issues_detected": len(self.issues),
            "is_source_modified": is_modified,
            "issues": self.issues
        }

    def verify_missing_values(self):
        # 2. Verify missing-value detection & 6. Warnings vs Critical errors
        null_counts = self.raw_df.isnull().sum()
        total_rows = len(self.raw_df)
        for col, count in null_counts.items():
            if count > 0:
                pct = (count / total_rows) * 100
                severity = "CRITICAL" if pct > 20 else "WARNING"
                self.issues.append({
                    "issue_id": "MISSING_VALUES",
                    "column": col,
                    "severity": severity,
                    "affected_count": int(count),
                    "percentage": round(pct, 2),
                    "description": f"Column '{col}' has {count} missing values ({pct:.2f}%)."
                })

    def verify_duplicates_and_identifiers(self):
        # 3. Verify duplicate-row and duplicate-identifier detection
        dup_count = self.raw_df.duplicated().sum()
        if dup_count > 0:
            self.issues.append({
                "issue_id": "DUPLICATE_ROWS",
                "column": None,
                "severity": "WARNING",
                "affected_count": int(dup_count),
                "description": f"Dataset contains {dup_count} duplicate row(s)."
            })
            
        # Check primary identifier columns if present
        id_cols = [c for c in self.raw_df.columns if 'id' in c.lower()]
        for col in id_cols:
            dup_ids = self.raw_df[col].duplicated().sum()
            if dup_ids > 0:
                self.issues.append({
                    "issue_id": "DUPLICATE_IDENTIFIERS",
                    "column": col,
                    "severity": "CRITICAL",
                    "affected_count": int(dup_ids),
                    "description": f"Identifier column '{col}' contains {dup_ids} duplicate value(s)."
                })

    def verify_empty_strings(self):
        # 5. Verify empty-string and null-value handling
        for col in self.raw_df.select_dtypes(include=['object', 'string']).columns:
            empty_count = (self.raw_df[col].astype(str).str.strip() == "").sum()
            if empty_count > 0:
                self.issues.append({
                    "issue_id": "EMPTY_STRINGS",
                    "column": col,
                    "severity": "WARNING",
                    "affected_count": int(empty_count),
                    "description": f"Column '{col}' contains {empty_count} whitespace/empty string entries."
                })

    def verify_date_formats(self):
        # 4. Check invalid values and inconsistent data formats (temporal columns)
        date_cols = [c for c in self.raw_df.columns if 'date' in c.lower() or 'time' in c.lower()]
        for col in date_cols:
            try:
                pd.to_datetime(self.raw_df[col], errors='raise')
            except Exception:
                self.issues.append({
                    "issue_id": "INCONSISTENT_DATE_FORMAT",
                    "column": col,
                    "severity": "CRITICAL",
                    "affected_count": len(self.raw_df),
                    "description": f"Column '{col}' contains unparseable date/time formats."
                })

# --- Execution Entry Point ---
if __name__ == "__main__":
    datasets_to_check = [
        ("HumanResources.Department (1).xlsx", "HumanResources.Department"),
        ("HumanResources.Employee (1).xlsx", "HumanResources.Employee"),
        ("HumanResources.JobCandidate (1).xlsx", "HumanResources.JobCandidate"),
        ("HumanResources.EmployeeDepartmentHistory (1).xlsx", "HumanResources.EmployeeDepartme")
    ]

    all_reports = []
    for filepath, sheet in datasets_to_check:
        if os.path.exists(filepath):
            analyzer = HRDataQualityAnalyzer(filepath, sheet)
            report = analyzer.run_all_checks()
            all_reports.append(report)
        else:
            print(f"Warning: File {filepath} not found in current directory.")

    # Print JSON output for VS Code terminal
    print(json.dumps(all_reports, indent=4))