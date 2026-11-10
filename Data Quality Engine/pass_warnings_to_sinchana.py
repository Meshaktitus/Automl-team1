import os
import json
import pandas as pd

# Define paths
dataset_path = "HumanResources.EmployeePayHistory.xlsx"
payload_path = "sinchana_preprocessing_payload.json"

print("=" * 70)
print("PREPROCESSING INTEGRATION: PASSING WARNINGS TO SINCHANA'S MODULE")
print("=" * 70)

if not os.path.exists(dataset_path):
    print(f"[Error] Dataset '{dataset_path}' not found!")
    exit(1)

# Step 1: Load Dataset and Run Validation Scan for Warnings
df = pd.read_excel(dataset_path)
warnings_list = []

print("\n[Step 1] Scanning dataset for anomalies and generating warning payload...")

# Scan for missing values
for col in df.columns:
    nulls = int(df[col].isnull().sum())
    if nulls > 0:
        warnings_list.append({
            "column": col,
            "issue_type": "MISSING_VALUES",
            "severity": "MEDIUM",
            "count": nulls,
            "recommended_action": "Impute median or drop rows"
        })

# Scan numerical columns for IQR outliers
for col in df.select_dtypes(include=['int64', 'float64']).columns:
    if not col.lower().endswith('id'):
        s = df[col].dropna()
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        upper_bound = q3 + 1.5 * iqr
        outliers = int((s > upper_bound).sum())
        if outliers > 0:
            warnings_list.append({
                "column": col,
                "issue_type": "IQR_OUTLIER",
                "severity": "LOW",
                "count": outliers,
                "recommended_action": "Cap values at upper bound or review"
            })

# Step 2: Package Warnings into Structured Payload for Sinchana's Module
payload = {
    "target_dataset": "HumanResources.EmployeePayHistory",
    "total_warnings_detected": len(warnings_list),
    "warnings": warnings_list
}

with open(payload_path, "w") as f:
    json.dump(payload, f, indent=4)

print(f"[Step 2] Successfully exported {len(warnings_list)} warnings to '{payload_path}' for Sinchana's module.")

# Step 3: Simulate Sinchana's Preprocessing Module Consuming the Payload
print("\n[Step 3] Simulating Sinchana's Preprocessing Module Consumption:")
with open(payload_path, "r") as f:
    consumed_payload = json.load(f)

print(f"  • Target Received: {consumed_payload['target_dataset']}")
print(f"  • Active Warnings Loaded: {consumed_payload['total_warnings_detected']}")
for w in consumed_payload['warnings'][:3]:  # Display first 3 warnings
    print(f"    - Column: {w['column']} | Issue: {w['issue_type']} | Action: {w['recommended_action']}")

print("\n" + "=" * 70)
print("SUCCESS: Warnings successfully packaged and passed to Sinchana's Preprocessing Module!")
print("=" * 70)