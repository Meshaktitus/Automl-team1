"""
Module: Data Quality Analyzer
Author: Gantla Vinitha Reddy
Project: Data Science Intelligence & Automated Machine Learning Engine
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any

class DataQualityAnalyzer:
    def __init__(self, df: pd.DataFrame, dataset_name: str = "Dataset"):
        # Non-destructive: preserve original input dataframe
        self.df = df.copy(deep=True)
        self.dataset_name = dataset_name
        self.issues: List[Dict[str, Any]] = []

    def run_quality_checks(self) -> List[Dict[str, Any]]:
        self.issues = []
        self._check_missing_values()
        self._check_duplicates()
        self._check_constant_and_cardinality()
        self._check_numerical_ranges()
        self._check_date_formats()
        self._check_invalid_values()
        return self.issues

    def _add_issue(self, issue_type: str, severity: str, column: str, affected_count: int, description: str):
        self.issues.append({
            "dataset": self.dataset_name,
            "issue_type": issue_type,
            "severity": severity,
            "column": column,
            "affected_rows": affected_count,
            "description": description
        })

    def _check_missing_values(self):
        missing_counts = self.df.isnull().sum()
        for col, count in missing_counts.items():
            if count > 0:
                pct = (count / len(self.df)) * 100
                severity = "CRITICAL" if pct > 50 else "WARNING"
                self._add_issue(
                    issue_type="Missing Value",
                    severity=severity,
                    column=str(col),
                    affected_count=int(count),
                    description=f"Column '{col}' contains {count} missing values ({pct:.1f}%)."
                )

    def _check_duplicates(self):
        duplicate_count = self.df.duplicated().sum()
        if duplicate_count > 0:
            self._add_issue(
                issue_type="Duplicate Rows",
                severity="CRITICAL",
                column="Dataset-wide",
                affected_count=int(duplicate_count),
                description=f"Identified {duplicate_count} duplicate rows across the dataset."
            )

    def _check_constant_and_cardinality(self):
        total_count = len(self.df)
        if total_count == 0:
            return
        for col in self.df.columns:
            unique_count = self.df[col].nunique()
            if unique_count <= 1:
                self._add_issue(
                    issue_type="Constant Column",
                    severity="WARNING",
                    column=str(col),
                    affected_count=total_count,
                    description=f"Column '{col}' is constant with {unique_count} unique value."
                )
            elif str(self.df[col].dtype) in ['object', 'string'] and (unique_count / total_count) > 0.9 and total_count > 10:
                self._add_issue(
                    issue_type="High Cardinality",
                    severity="WARNING",
                    column=str(col),
                    affected_count=unique_count,
                    description=f"Column '{col}' exhibits high cardinality ({unique_count} unique values)."
                )

    def _check_numerical_ranges(self):
        numerical_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in numerical_cols:
            series = self.df[col].dropna()
            if series.empty:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outliers = self.df[(self.df[col] < lower_bound) | (self.df[col] > upper_bound)][col].count()
            if outliers > 0:
                self._add_issue(
                    issue_type="Numerical Outlier / Range Anomaly",
                    severity="WARNING",
                    column=str(col),
                    affected_count=int(outliers),
                    description=f"Column '{col}' contains {outliers} statistical outliers outside IQR bounds."
                )

    def _check_date_formats(self):
        date_cols = [col for col in self.df.columns if any(kw in str(col).lower() for kw in ['date', 'time', 'modified', 'changed', 'hire'])]
        for col in date_cols:
            series = self.df[col].astype(str)
            parsed = pd.to_datetime(series, errors='coerce')
            invalid_dates = parsed.isnull().sum() - self.df[col].isnull().sum()
            if invalid_dates > 0:
                self._add_issue(
                    issue_type="Inconsistent Date Format",
                    severity="CRITICAL",
                    column=str(col),
                    affected_count=int(invalid_dates),
                    description=f"Column '{col}' contains {invalid_dates} unparseable or inconsistently formatted date entries."
                )

    def _check_invalid_values(self):
        object_cols = self.df.select_dtypes(include=['object', 'string']).columns
        for col in object_cols:
            blank_mask = self.df[col].astype(str).str.strip().eq('') & self.df[col].notnull()
            blank_count = blank_mask.sum()
            if blank_count > 0:
                self._add_issue(
                    issue_type="Invalid Value (Blank/Whitespace)",
                    severity="WARNING",
                    column=str(col),
                    affected_count=int(blank_count),
                    description=f"Column '{col}' contains {blank_count} empty or whitespace-only string values."
                )

if __name__ == "__main__":
    df = pd.read_excel('HumanResources.Employee (1).xlsx', sheet_name='HumanResources.Employee')
    analyzer = DataQualityAnalyzer(df, dataset_name="Employee")
    issues = analyzer.run_quality_checks()
    
    print(f"\n--- DATA QUALITY ANALYSIS RESULTS ---")
    print(f"Total issues found: {len(issues)}\n")
    for issue in issues:
        print(f"[{issue['severity']}] {issue['issue_type']} -> Column: '{issue['column']}' (Affected: {issue['affected_rows']})")
        print(f"   Details: {issue['description']}\n")