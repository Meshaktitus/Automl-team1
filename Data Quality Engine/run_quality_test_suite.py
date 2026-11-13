import json
import os
import pandas as pd
import numpy as np

class QualityTestRunner:
    def __init__(self):
        # Automatically finds files in the exact same folder where this script is saved
        self.base_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
        self.test_suites = [
            ("churn_classification.csv", "churn", {"INVALID_RANGE": 44, "OUTLIER_IQR": 2}),
            ("house_price_regression.csv", "price", {}),
            ("transactions_anomaly.csv", "amount", {"OUTLIER_IQR": 38}),
            ("customer_segments_clustering.csv", "spending_score", {"OUTLIER_IQR": 6}),
            ("ambiguous_targets.csv", "amount", {"NULL_CHECK": 320, "OUTLIER_IQR": 1})
        ]

    def execute_test_suite(self):
        report = {}
        print(f"=== Executing Quality-Rule Test Suite ==-\n")
        
        for filename, target_col, expected_counts in self.test_suites:
            filepath = os.path.join(self.base_dir, filename)
            if not os.path.exists(filepath):
                print(f"[WARNING] File not found: {filename}. Make sure it's in this folder!")
                continue
            
            df_original = pd.read_csv(filepath)
            df_copy = df_original.copy() # Used to check source-data preservation
            
            row_count, col_count = df_original.shape
            dup_rows = int(df_original.duplicated().sum())
            findings = []
            
            # 1. Duplicate Row Check
            if dup_rows > 0:
                findings.append({
                    "rule_id": "DUP_ROW",
                    "severity": "Warning",
                    "affected_column": "",
                    "affected_rows": dup_rows,
                    "recommended_action": f"Remove or deduplicate {dup_rows} exact duplicate row(s)."
                })
                
            # 2. Column-Level Checks
            for col in df_original.columns:
                series = df_original[col]
                missing = int(series.isna().sum())
                missing_pct = round((missing / row_count) * 100, 2)
                
                # Null Check
                if missing > 0:
                    is_target = (col == target_col)
                    severity = "Blocking" if is_target else ("Warning" if missing_pct > 10 else "Info")
                    findings.append({
                        "rule_id": "NULL_CHECK",
                        "severity": severity,
                        "affected_column": col,
                        "affected_rows": missing,
                        "recommended_action": f"Impute missing values or drop affected rows in column '{col}'."
                    })
                    
                # Numerical Checks: IQR Outliers & Invalid Ranges
                if pd.api.types.is_numeric_dtype(series):
                    non_null = series.dropna()
                    if len(non_null) > 0:
                        q1, q3 = non_null.quantile(0.25), non_null.quantile(0.75)
                        iqr = q3 - q1
                        if iqr > 0:
                            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                            outliers = non_null[(non_null < lower) | (non_null > upper)]
                            if len(outliers) > 0:
                                is_target = (col == target_col)
                                severity = "Blocking" if is_target else "Warning"
                                findings.append({
                                    "rule_id": "OUTLIER_IQR",
                                    "severity": severity,
                                    "affected_column": col,
                                    "affected_rows": int(len(outliers)),
                                    "recommended_action": f"Apply Winsorization/capping outside [{lower:.2f}, {upper:.2f}]."
                                })
                                
                        # Domain Range Check
                        invalid_count = 0
                        if col in ['price', 'revenue', 'monthly_spend', 'annual_income', 'spending_score', 'amount', 'units_sold']:
                            invalid_count = int((non_null < 0).sum())
                        elif col == 'age':
                            invalid_count = int(((non_null < 18) | (non_null > 70)).sum())
                            
                        if invalid_count > 0:
                            is_target = (col == target_col)
                            severity = "Blocking" if is_target else "Error"
                            findings.append({
                                "rule_id": "INVALID_RANGE",
                                "severity": severity,
                                "affected_column": col,
                                "affected_rows": invalid_count,
                                "recommended_action": f"Filter/correct {invalid_count} record(s) violating domain limits in '{col}'."
                            })

            # Verify source-data preservation (immutability check)
            data_preserved = df_original.equals(df_copy)
            
            detected_summary = {}
            for f in findings:
                r_id = f["rule_id"]
                detected_summary[r_id] = detected_summary.get(r_id, 0) + f["affected_rows"]
                
            report[filename] = {
                "source_data_preserved": data_preserved,
                "row_count": row_count,
                "detected_issue_counts": detected_summary,
                "expected_issue_counts": expected_counts,
                "findings_detail": findings
            }

        return report

if __name__ == "__main__":
    runner = QualityTestRunner()
    final_report = runner.execute_test_suite()
    print(json.dumps(final_report, indent=2))