"""Collects evidence of the profiling work and writes evidence_report.txt.

Usage:  python evidence.py [data_folder]      (default folder: data)
Every line in the report comes from running the real code on the machine where you run this.
"""
import json
import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

import test_profiler
import test_profiling_contract
import test_profiling_day4
import test_profiling_day5
import test_profiling_manual_checks
import test_profiling_integration_regression
import test_profiling_regression
import test_profiling_team5_alignment
from profiling_service import REQUEST_SCHEMA, RESPONSE_SCHEMA, run_profiling
from schema_validation import validate

HERE = Path(__file__).parent
data_folder = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "data"
lines = []


def out(text=""):
    print(text)
    lines.append(text)


def section(title):
    out()
    out(f"== {title} ==")


out("EVIDENCE REPORT - Dataset Profiling (Sanjay)")
out(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
out(f"Python {platform.python_version()} | pandas {pd.__version__} | {platform.system()}")

# 1. tests -------------------------------------------------------------------------------------
section("1. Automated tests")
passed, failed = 0, []
for module in (test_profiler, test_profiling_contract, test_profiling_day4, test_profiling_day5, test_profiling_manual_checks, test_profiling_integration_regression, test_profiling_regression, test_profiling_team5_alignment):
    for name in sorted(n for n in dir(module) if n.startswith("test_")):
        try:
            getattr(module, name)()
            passed += 1
        except Exception as exc:  # includes pytest skips
            if type(exc).__name__ == "Skipped":
                out(f"SKIPPED  {module.__name__}.{name}: {exc}")
            else:
                failed.append(f"{module.__name__}.{name}")
                out(f"FAILED   {module.__name__}.{name}")
                out(traceback.format_exc())
out(f"{passed} passed, {len(failed)} failed")

# 2. sample files follow the schemas ---------------------------------------------------------------
section("2. Sample JSON files validated against the schemas")
for path in sorted((HERE / "samples").glob("sample_profiling_request*.json")):
    problems = validate(json.loads(path.read_text(encoding="utf-8")), REQUEST_SCHEMA)
    if "invalid" in path.name:   # this sample is deliberately wrong: the schema must reject it
        out(f"{'OK  ' if problems else 'FAIL'} {path.name} (deliberately invalid, rejected as expected)")
    else:
        out(f"{'OK  ' if not problems else 'FAIL'} {path.name} (request schema)")
for path in sorted((HERE / "samples").glob("sample_profiling_response*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    problems = validate(data, RESPONSE_SCHEMA)
    out(f"{'OK  ' if not problems else 'FAIL'} {path.name} (response schema) status={data['status']}")

# 3. the six backend tables ----------------------------------------------------------------------------
section("3. Backend HR tables: expected vs actual size")
expected = {"Department": (16, 4), "Employee": (290, 16), "EmployeeDepartmentHistory": (296, 6),
            "EmployeePayHistory": (316, 5), "JobCandidate": (13, 4), "Shift": (3, 5)}
found = {k: f for f in data_folder.glob("*.xlsx") for k in expected
         if f.stem.replace(".", "_").endswith("_" + k)} if data_folder.is_dir() else {}
if not found:
    out(f"No HR Excel files found in '{data_folder}'. Pass the folder: python evidence.py <folder>")
for key, path in sorted(found.items()):
    resp = run_profiling({"schema_version": "1.0-draft", "request_id": f"evidence-{key}",
                          "dataset_reference": {"dataset_id": key, "source_type": "file", "location": str(path)},
                          "metadata": {"format": "xlsx"}})
    if resp["dataset"] is None:
        out(f"FAIL {key}: {resp['errors']}")
        continue
    actual = (resp["dataset"]["row_count"], resp["dataset"]["column_count"])
    leaked = [c["name"] for c in resp["columns"] if c["likely_identifier"] and ({"top_values", "summary", "histogram"} & set(c))]
    out(f"{'OK  ' if actual == expected[key] else 'FAIL'} {key}: expected {expected[key][0]}x{expected[key][1]}, "
        f"actual {actual[0]}x{actual[1]}, duplicates={resp['dataset']['duplicate_row_count']}, "
        f"status={resp['status']}, schema-valid={not validate(resp, RESPONSE_SCHEMA)}, "
        f"identifier values exposed={leaked or 'none'}")

# 4. error handling ------------------------------------------------------------------------------------------
section("4. Error handling (the module returns errors, it never crashes)")
base = json.loads((HERE / "samples" / "sample_profiling_request.json").read_text(encoding="utf-8"))
cases = {"file not found": {**base, "dataset_reference": {**base["dataset_reference"], "location": "missing.csv"}},
         "invalid request": {"hello": "world"}, "empty request (None)": None}
for label, req in cases.items():
    resp = run_profiling(req)
    out(f"{label}: status={resp['status']}, errors={[e['code'] for e in resp['errors']]}, "
        f"schema-valid={not validate(resp, RESPONSE_SCHEMA)}")

# 5. delivered files ---------------------------------------------------------------------------------------------
section("5. Delivered files")
for name in ["profiler.py", "profiling_service.py", "schema_validation.py", "schemas/profiling_request.schema.json",
             "schemas/profiling_response.schema.json", "samples/sample_profiling_request.json",
             "samples/sample_profiling_response.json", "PROFILING_CONTRACT.md", "test_profiler.py",
             "test_profiling_contract.py", "test_profiling_day4.py", "test_profiling_day5.py", "test_profiling_manual_checks.py", "test_profiling_integration_regression.py", "test_profiling_regression.py", "test_profiling_team5_alignment.py", "benchmark_profiling.py",
             "update_contract_benchmark.py"]:
    p = HERE / name
    out(f"{'present' if p.exists() else 'MISSING'}  {name}" + (f"  ({p.stat().st_size} bytes)" if p.exists() else ""))

# 6. benchmark -----------------------------------------------------------------------------------------------------
section("6. Performance benchmark (memory limitation: the whole table is held in memory)")
bench = HERE / "benchmark_results.json"
if bench.exists():
    b = json.loads(bench.read_text(encoding="utf-8"))
    e = b["environment"]
    out(f"Measured {e['measured_at']} on {e['platform']}, Python {e['python']}, pandas {e['pandas']}, {e['cpus']} CPUs, "
        f"{e['runs_per_size']} runs per size (median [fastest - slowest], seconds)")
    for r in b["results"]:
        p, q = r["profiling"], r["end_to_end"]
        out(f"{r['rows']:>10,} rows ({r['table_mb']} MB): profiling only {p[0]:.2f} [{p[1]:.2f} - {p[2]:.2f}], "
            f"end to end {q[0]:.2f} [{q[1]:.2f} - {q[2]:.2f}]")
    out("Tables larger than available memory are not supported.")
else:
    out("No benchmark results found. Run: python benchmark_profiling.py")

(HERE / "evidence_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\nSaved: evidence_report.txt")
