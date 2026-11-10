"""Integration check for the profiling stage: runs the scenarios a pipeline will meet and prints PASS/FAIL.
Usage:  python integration_check.py          (writes integration_results.txt)
Uses synthetic data only. Covers success, warning and failed responses and how a consumer should branch on them.
"""
import copy
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from profiling_service import RESPONSE_SCHEMA, run_profiling
from schema_validation import validate

HERE = Path(__file__).parent
rng = np.random.default_rng(7)
n = 200
classification = pd.DataFrame({
    "customer_id": range(1, n + 1), "age": rng.integers(18, 70, n),
    "income": rng.normal(50000, 12000, n).round(2), "plan": rng.choice(["basic", "pro"], n, p=[0.8, 0.2]),
    "city": rng.choice(["Pune", "Delhi", "Chennai"], n), "signup_date": pd.date_range("2024-01-01", periods=n, freq="D"),
    "churned": rng.choice([0, 1], n, p=[0.9, 0.1])})
regression = pd.DataFrame({
    "area": rng.normal(1200, 300, n).round(1), "rooms": rng.integers(1, 6, n),
    "city": rng.choice(["Pune", "Delhi", "Chennai"], n)})
regression["price"] = (regression["area"] * 55 + regression["rooms"] * 9000 + rng.normal(0, 8000, n)).round(2)


def req(target=None, location=None, **extra):
    r = {"schema_version": "1.0-draft", "request_id": "it-001",
         "dataset_reference": {"dataset_id": "ds-it", "name": "synthetic", "source_type": "file"}}
    if location:
        r["dataset_reference"]["location"] = location
    if target:
        r["options"] = {"target_column": target}
    r.update(extra)
    return r


def codes(resp, key):
    return sorted({x["code"] for x in resp[key]})


results = []


def check(name, expected, resp, ok):
    schema_ok = not validate(resp, RESPONSE_SCHEMA)
    passed = bool(ok) and schema_ok
    results.append((passed, name, expected, f"status={resp['status']} warnings={codes(resp, 'warnings')} errors={codes(resp, 'errors')}"
                    + ("" if schema_ok else " SCHEMA-INVALID")))


before = classification.copy(deep=True)
r = run_profiling(req("churned"), dataframe=classification)
check("Classification dataset, target 'churned'", "class_distribution with 2 classes", r,
      r["status"] in ("success", "warning") and r.get("class_distribution", {}).get("class_count") == 2)
check("Source table not modified", "input DataFrame unchanged", r, classification.equals(before))

r = run_profiling(req("price"), dataframe=regression)
check("Regression dataset, numeric target 'price'", "no class_distribution, CLASS_DISTRIBUTION_SKIPPED (info)", r,
      "class_distribution" not in r and "CLASS_DISTRIBUTION_SKIPPED" in codes(r, "warnings")
      and any("histogram" in c for c in r["columns"] if c["name"] == "price"))

r = run_profiling(req(), dataframe=classification)
check("No target selected", "profile only, no class_distribution, no failure", r,
      r["status"] != "failed" and "class_distribution" not in r)

r = run_profiling(req("not_a_column"), dataframe=classification)
check("Target column does not exist", "failed with TARGET_NOT_FOUND", r,
      r["status"] == "failed" and codes(r, "errors") == ["TARGET_NOT_FOUND"] and r["dataset"] is None and r["columns"] == [])

r = run_profiling(req(location="no/such/file.csv"))
check("Source file missing", "failed with SOURCE_NOT_FOUND", r, r["status"] == "failed" and codes(r, "errors") == ["SOURCE_NOT_FOUND"])

r = run_profiling({"hello": "world"})
check("Invalid request", "failed with INVALID_REQUEST, request_id null", r,
      r["status"] == "failed" and "INVALID_REQUEST" in codes(r, "errors") and r["request_id"] is None)

r = run_profiling(req())
check("No location and no table", "failed with INVALID_REQUEST on dataset_reference.location", r,
      r["status"] == "failed" and any(e["field"] == "dataset_reference.location" for e in r["errors"]))

r = run_profiling(req(), dataframe=pd.DataFrame())
check("Empty table", "warning EMPTY_DATASET (not a crash)", r, r["status"] == "warning" and "EMPTY_DATASET" in codes(r, "warnings"))

messy = pd.DataFrame({"a": [1, 2, 3, 4], "const": [7] * 4, "blank": [None] * 4, "mixed": [1, "x", 3, "y"]})
r = run_profiling(req(), dataframe=messy)
check("Constant, empty and mixed columns", "warning with CONSTANT_COLUMN, EMPTY_COLUMN, MIXED_TYPES", r,
      r["status"] == "warning" and {"CONSTANT_COLUMN", "EMPTY_COLUMN", "MIXED_TYPES"} <= set(codes(r, "warnings")))

dup = pd.DataFrame([[1, 2]], columns=["a", "a"])
r = run_profiling(req(), dataframe=dup)
check("Duplicate column names", "failed with DUPLICATE_COLUMN_NAMES", r,
      r["status"] == "failed" and codes(r, "errors") == ["DUPLICATE_COLUMN_NAMES"])

demo = HERE / "samples" / "demo_customers.csv"
if demo.exists():
    r = run_profiling(req("plan", location=str(demo), metadata={"format": "csv", "identifier_columns": ["customer_id"]}))
    check("demo_customers.csv from a file path", "6 rows, 7 columns, class_distribution on 'plan'", r,
          r["status"] == "warning" and r["dataset"]["row_count"] == 6 and r["dataset"]["column_count"] == 7
          and r.get("class_distribution", {}).get("target_column") == "plan")

lines = [f"INTEGRATION CHECK: profiling stage ({datetime.now().isoformat(timespec='seconds')})", ""]
for passed, name, expected, actual in results:
    lines += [f"{'PASS' if passed else 'FAIL'}  {name}", f"      expected: {expected}", f"      actual:   {actual}"]
total = sum(1 for r in results if r[0])
lines += ["", f"{total} of {len(results)} scenarios passed. Cross-module integration is still pending verification."]
text = "\n".join(lines)
print(text)
(HERE / "integration_results.txt").write_text(text + "\n", encoding="utf-8")
