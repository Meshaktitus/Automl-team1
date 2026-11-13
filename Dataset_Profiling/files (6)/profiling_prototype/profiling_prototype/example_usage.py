"""Minimal example: calling the profiling module from Python (illustrative; the API layer, route and authentication belong to Team 2).
Run from this folder:  python example_usage.py
"""
from pathlib import Path

import pandas as pd

from profiling_service import RESPONSE_SCHEMA, run_profiling
from schema_validation import validate

HERE = Path(__file__).parent

# 1. The backend loads the authorised dataset into a pandas DataFrame
df = pd.read_csv(HERE / "samples" / "demo_customers.csv", na_values=["NA", "n/a"])

# 2. The backend builds the request (target_column is optional; one target per request)
request = {
    "schema_version": "1.0-draft",
    "request_id": "example-001",
    "dataset_reference": {"dataset_id": "ds-demo-001", "name": "demo_customers.csv", "source_type": "file"},
    "options": {"target_column": "plan"},
}

# 3. Call the module. It never raises; branch on response["status"]
response = run_profiling(request, dataframe=df)

if response["status"] == "failed":                      # no profile: dataset is None, columns is []
    print("Profiling failed:", [(e["code"], e["field"]) for e in response["errors"]])
else:                                                   # "success", or "warning" (warnings are hints, not blockers)
    d = response["dataset"]
    print(f"status={response['status']}: {d['row_count']} rows, {d['column_count']} columns, {d['duplicate_row_count']} duplicate rows")
    for w in response["warnings"]:
        print(f"  warning {w['code']} ({w['severity']}) on {w['column']}")
    if "class_distribution" in response:
        print("  class distribution:", [(c["value"], c["count"]) for c in response["class_distribution"]["classes"]])

# 4. Optional: confirm the response follows the contract (an empty list means valid)
print("valid against the response schema:", validate(response, RESPONSE_SCHEMA) == [])
