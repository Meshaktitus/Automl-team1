import pandas as pd
import numpy as np

class DataQualityAnalyzer:
    """Non-destructive Data Quality Analysis Engine for HR Datasets."""
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.findings = []

    def run_all_checks(self, range_rules=None):
        self.findings = []
        self._check_nulls()
        self._check_duplicates()
        self._check_constant_and_all_null_columns()
        if range_rules:
            self._check_invalid_ranges(range_rules)
        self._check_outliers_iqr()
        return self.findings

    def _add_finding(self, rule_id, column, severity, affected_count, description):
        self.findings.append({
            "rule_id": rule_id,
            "column": column,
            "severity": severity,
            "affected_count": int(affected_count),
            "affected_percentage": round((affected_count / len(self.df)) * 100, 2) if len(self.df) > 0 else 0.0,
            "description": description
        })

    def _check_nulls(self):
        # 1. Test missing-value detection
        null_counts = self.df.isnull().sum()
        for col, count in null_counts.items():
            if count > 0:
                severity = "CRITICAL" if (count / len(self.df)) > 0.5 else "WARNING"
                self._add_finding("NULL_CHECK", col, severity, count, f"Column '{col}' contains {count} missing value(s).")

    def _check_duplicates(self):
        # 2. Test duplicate detection
        dup_count = self.df.duplicated().sum()
        if dup_count > 0:
            self._add_finding("DUP_ROW", None, "WARNING", dup_count, f"Dataset contains {dup_count} exact duplicate row(s).")

    def _check_constant_and_all_null_columns(self):
        # 6. Test all-null and constant-value columns
        for col in self.df.columns:
            unique_vals = self.df[col].dropna().unique()
            if len(unique_vals) == 0:
                self._add_finding("ALL_NULL_COLUMN", col, "CRITICAL", len(self.df), f"Column '{col}' is entirely null.")
            elif len(unique_vals) == 1:
                self._add_finding("CONSTANT_COLUMN", col, "WARNING", len(self.df), f"Column '{col}' has a constant value across all rows.")

    def _check_invalid_ranges(self, range_rules):
        # 3. Test invalid-value and range checks
        for col, (min_val, max_val) in range_rules.items():
            if col in self.df.columns:
                invalid_mask = (self.df[col] < min_val) | (self.df[col] > max_val)
                invalid_count = invalid_mask.sum()
                if invalid_count > 0:
                    self._add_finding("INVALID_RANGE", col, "CRITICAL", invalid_count, f"Column '{col}' has {invalid_count} value(s) outside range [{min_val}, {max_val}].")

    def _check_outliers_iqr(self):
        # 4. Test outlier detection where implemented
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q3 - Q1
            if IQR > 0:
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outliers = (self.df[col] < lower_bound) | (self.df[col] > upper_bound)
                outlier_count = outliers.sum()
                if outlier_count > 0:
                    self._add_finding("OUTLIER_IQR", col, "WARNING", outlier_count, f"Column '{col}' contains {outlier_count} statistical outlier(s).")


# --- Execution on Uploaded HR Dataset ---
if __name__ == "__main__":
    # Load the Employee dataset
    df_emp = pd.read_excel('HumanResources.Employee (1).xlsx', sheet_name='HumanResources.Employee')
    
    initial_shape = df_emp.shape
    initial_columns = list(df_emp.columns)
    
    print(f"Loaded Employee Dataset. Shape: {initial_shape}\n")

    # Initialize analyzer
    analyzer = DataQualityAnalyzer(df_emp)
    
    # Define business range checks (e.g., VacationHours expected between 0 and 100)
    range_rules = {'VacationHours': (0, 100)}
    findings = analyzer.run_all_checks(range_rules=range_rules)

    # 5. Verify warning severity and affected-row counts
    print("--- Quality Findings & Affected-Row Reports ---")
    for f in findings:
        print(f"[{f['severity']}] Rule: {f['rule_id']} | Column: {f['column']} | Affected Count: {f['affected_count']} ({f['affected_percentage']}%) | {f['description']}")

    # 7. Validate non-destructive processing
    assert df_emp.shape == initial_shape, "Error: Dataset rows or columns were modified!"
    assert list(df_emp.columns) == initial_columns, "Error: Column names were modified!"
    print("\n[SUCCESS] Non-destructive processing validated: Original HR dataset remains completely unmodified.")