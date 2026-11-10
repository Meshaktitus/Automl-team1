import pandas as pd
import numpy as np
import json
import os

class FinalizedDataQualityEngine:
    def __init__(self, file_path, sheet_name=None):
        self.file_path = file_path
        self.sheet_name = sheet_name
        if sheet_name:
            self.raw_df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            self.raw_df = pd.read_excel(file_path)
        self.original_shape = self.raw_df.shape
        self.issues = []

    def execute_quality_pipeline(self):
        self.check_missing_values()
        self.check_duplicate_rows()
        self.check_empty_strings()
        self.check_date_formats()
        
        # Verify non-destructive guarantee
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

    def check_missing_values(self):
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

    def check_duplicate_rows(self):
        dup_count = self.raw_df.duplicated().sum()
        if dup_count > 0:
            self.issues.append({
                "issue_id": "DUPLICATE_ROWS",
                "column": None,
                "severity": "WARNING",
                "affected_count": int(dup_count),
                "description": f"Dataset contains {dup_count} duplicate row(s)."
            })

    def check_empty_strings(self):
        for col in self.raw_df.select_dtypes(include=['object', 'string']).columns:
            empty_count = (self.raw_df[col].astype(str).str.strip() == "").sum()
            if empty_count > 0:
                self.issues.append({
                    "issue_id": "EMPTY_STRINGS",
                    "column": col,
                    "severity": "WARNING",
                    "affected_count": int(empty_count),
                    "description": f"Column '{col}' contains {empty_count} whitespace or empty string entries."
                })

    def check_date_formats(self):
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
                    "description": f"Column '{col}' contains unparseable or mixed date/time formats."
                })

if __name__ == "__main__":
    print("Executing Finalized Data Quality Rule Catalogue Pipeline...")
    engine = FinalizedDataQualityEngine("HumanResources.Department (1).xlsx", "HumanResources.Department")
    report = engine.execute_quality_pipeline()
    print(json.dumps(report, indent=4))