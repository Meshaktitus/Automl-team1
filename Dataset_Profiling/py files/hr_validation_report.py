"""Validation report for the six HR datasets: compares the profiling output with an independent recomputation.
Usage:  python hr_validation_report.py data        (writes hr_validation_report.txt)
For every table it checks row and column counts against the agreed sizes, and re-computes duplicate rows,
missing counts and distinct counts directly with pandas to compare them with the profiling response.
No data values are written to the report, only counts and column names.
"""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from profiling_service import RESPONSE_SCHEMA, run_profiling
from schema_validation import validate

HERE = Path(__file__).parent
folder = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "data"
EXPECTED = {"Department": (16, 4), "Employee": (290, 16), "EmployeeDepartmentHistory": (296, 6),
            "EmployeePayHistory": (316, 5), "JobCandidate": (13, 4), "Shift": (3, 5)}
files = {k: f for f in folder.glob("*.xlsx") for k in EXPECTED if f.stem.replace(".", "_").endswith("_" + k)} if folder.is_dir() else {}
if not files:
    sys.exit(f"No HR Excel files found in '{folder}'. Run: python hr_validation_report.py <folder>")

lines = [f"DATASET PROFILING VALIDATION REPORT: six HR datasets ({datetime.now().isoformat(timespec='seconds')})",
         "Method: size check against the agreed sizes, plus an independent pandas recomputation of duplicates, missing counts and distinct counts.",
         "No data values are included; only counts and column names.", ""]
problems = 0
for key in EXPECTED:
    if key not in files:
        lines.append(f"{key}: FILE NOT FOUND")
        problems += 1
        continue
    resp = run_profiling({"schema_version": "1.0-draft", "request_id": f"hr-validation-{key}",
                          "dataset_reference": {"dataset_id": key, "source_type": "file", "location": str(files[key])},
                          "metadata": {"format": "xlsx"}})
    if resp["status"] == "failed":
        lines.append(f"{key}: FAILED {[e['code'] for e in resp['errors']]}")
        problems += 1
        continue
    df = pd.read_excel(files[key])
    d = resp["dataset"]
    checks = {
        "size matches agreed size": (d["row_count"], d["column_count"]) == EXPECTED[key],
        "row/column count matches recomputation": (d["row_count"], d["column_count"]) == df.shape,
        "duplicate rows match recomputation": d["duplicate_row_count"] == int(df.duplicated().sum()),
        "missing counts match recomputation": all(c["missing_count"] == int(df[c["name"]].isna().sum()) for c in resp["columns"]),
        "distinct counts match recomputation": all(c["unique_count"] == int(df[c["name"]].nunique()) for c in resp["columns"]),
        "response valid against schema": not validate(resp, RESPONSE_SCHEMA),
        "no values or statistics for identifier columns": not any(c["likely_identifier"] and ({"top_values", "summary", "histogram"} & set(c)) for c in resp["columns"]),
    }
    problems += sum(1 for ok in checks.values() if not ok)
    missing = [f"{c['name']} {c['missing_count']} ({c['missing_pct']}%)" for c in resp["columns"] if c["missing_count"]]
    ids = [c["name"] for c in resp["columns"] if c["likely_identifier"]]
    lines += [f"{key}: {d['row_count']} rows x {d['column_count']} columns, duplicate rows {d['duplicate_row_count']}, status {resp['status']}",
              *[f"    {'PASS' if ok else 'FAIL'}  {name}" for name, ok in checks.items()],
              f"    columns with missing values: {', '.join(missing) or 'none'}",
              f"    warnings: {', '.join(f'{w['code']} on {w['column']}' for w in resp['warnings']) or 'none'}",
              f"    flagged as identifier-like: {', '.join(ids) or 'none'}", ""]
lines.append("RESULT: all checks passed." if not problems else f"RESULT: {problems} check(s) failed. See FAIL lines above.")
text = "\n".join(lines)
print(text)
(HERE / "hr_validation_report.txt").write_text(text + "\n", encoding="utf-8")
