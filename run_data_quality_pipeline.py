import json
import pandas as pd
import numpy as np

class DataQualityEngine:
    def __init__(self, target_column=None):
        self.target_column = target_column

    def evaluate_dataset(self, profiling_json: dict, df: pd.DataFrame) -> dict:
        """
        Point 1: Consumes profiling results and produces structured findings for Samarth's interface.
        Point 2 & 3: Tests blocking errors vs warnings, controlling pipeline continuation/stopping.
        Point 4: Provides recommended remediation actions for each issue category.
        """
        dataset_name = profiling_json.get("dataset_reference", {}).get("name", "dataset.csv")
        dataset_id = profiling_json.get("dataset_reference", {}).get("dataset_id", "ds-001")
        
        findings = []
        has_blocking_error = False
        
        # --- Rule 1: DUP_ROW (Table Level) ---
        dup_rows = profiling_json.get("dataset", {}).get("duplicate_row_count", 0)
        if dup_rows > 0:
            findings.append({
                "dataset": dataset_id,
                "rule_id": "DUP_ROW",
                "severity": "Warning",
                "affected_column": "",  # Table-level issues have empty column per Samarth's spec
                "affected_rows": dup_rows,
                "recommended_action": f"Remove or deduplicate {dup_rows} exact duplicate row(s) before model ingestion."
            })

        # --- Column-Level Checks ---
        for col in profiling_json.get("columns", []):
            col_name = col["name"]
            missing_count = col["missing_count"]
            inferred_type = col["inferred_type"]
            summary = col.get("summary", {})
            
            # --- Rule 2: NULL_CHECK ---
            if missing_count > 0:
                is_target = (col_name == self.target_column)
                # Point 2: Blocking if target column is missing values; Warning/Info otherwise
                severity = "Blocking" if is_target else ("Warning" if col["missing_pct"] > 10.0 else "Info")
                if severity == "Blocking":
                    has_blocking_error = True

                findings.append({
                    "dataset": dataset_id,
                    "rule_id": "NULL_CHECK",
                    "severity": severity,
                    "affected_column": col_name,
                    "affected_rows": missing_count,
                    "recommended_action": f"Impute missing values using median/mode or drop affected rows in column '{col_name}'."
                })

            # --- Rule 3: OUTLIER_IQR ---
            if inferred_type == "numerical" and "q1" in summary and "q3" in summary:
                q1, q3 = summary["q1"], summary["q3"]
                if q1 is not None and q3 is not None:
                    iqr = q3 - q1
                    if iqr > 0 and col_name in df.columns:
                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr
                        series = df[col_name].dropna()
                        outliers = series[(series < lower_bound) | (series > upper_bound)]
                        outlier_count = len(outliers)
                        
                        if outlier_count > 0:
                            is_target = (col_name == self.target_column)
                            severity = "Blocking" if is_target else "Warning"
                            if severity == "Blocking":
                                has_blocking_error = True
                                
                            findings.append({
                                "dataset": dataset_id,
                                "rule_id": "OUTLIER_IQR",
                                "severity": severity,
                                "affected_column": col_name,
                                "affected_rows": int(outlier_count),
                                "recommended_action": f"Apply Winsorization/capping to values outside range [{lower_bound:.2f}, {upper_bound:.2f}]."
                            })

            # --- Rule 4: INVALID_RANGE ---
            if inferred_type == "numerical" and col_name in df.columns:
                series = df[col_name].dropna()
                invalid_count = 0
                if any(k in col_name.lower() for k in ["price", "spend", "revenue", "income", "amount"]):
                    invalid_count = int((series < 0).sum())
                elif "age" in col_name.lower():
                    invalid_count = int(((series < 18) | (series > 70)).sum())

                if invalid_count > 0:
                    is_target = (col_name == self.target_column)
                    severity = "Blocking" if is_target else "Error"
                    if severity == "Blocking":
                        has_blocking_error = True
                        
                    findings.append({
                        "dataset": dataset_id,
                        "rule_id": "INVALID_RANGE",
                        "severity": severity,
                        "affected_column": col_name,
                        "affected_rows": invalid_count,
                        "recommended_action": f"Filter out or replace {invalid_count} record(s) violating valid numerical domain limits."
                    })

        # Point 3: Pipeline Flow Control Decision
        pipeline_status = "STOPPED_BLOCKING_ERROR" if has_blocking_error else "PROCEED_WITH_WARNINGS"

        return {
            "pipeline_status": pipeline_status,
            "has_blocking_error": has_blocking_error,
            "findings": findings
        }

# Execution in VS Code
if __name__ == "__main__":
    print("=== Executing Data Quality Pipeline ===")
    
    # Load test dataset (e.g. transactions_anomaly.csv)
    filename = "transactions_anomaly.csv"
    try:
        df_test = pd.read_csv(filename)
    except FileNotFoundError:
        df_test = pd.DataFrame({"transaction_id": [1], "amount": [-10.0], "num_items": [2]})
    
    # Mocking Sanjay's profiling response JSON
    profiling_sample = {
        "schema_version": "1.0-draft",
        "request_id": "req-trans-01",
        "module": "dataset_profiling",
        "status": "warning",
        "dataset_reference": {"dataset_id": filename, "name": filename},
        "dataset": {"row_count": len(df_test), "column_count": len(df_test.columns), "column_names": list(df_test.columns), "duplicate_row_count": int(df_test.duplicated().sum())},
        "columns": [
            {"name": "amount", "position": 1, "dtype": "float64", "inferred_type": "numerical", "missing_count": int(df_test['amount'].isna().sum()), "missing_pct": 0.0, "unique_count": df_test['amount'].nunique(), "likely_identifier": False, "warnings": [], "summary": {"q1": float(df_test['amount'].quantile(0.25)), "q3": float(df_test['amount'].quantile(0.75))}}
        ],
        "warnings": [],
        "errors": []
    }

    engine = DataQualityEngine(target_column="amount")
    result = engine.evaluate_dataset(profiling_sample, df_test)
    
    print(json.dumps(result, indent=2))