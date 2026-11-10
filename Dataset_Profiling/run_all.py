"""One command to run everything:  python run_all.py data
1) runs the test suite   2) profiles the synthetic demo dataset   3) profiles the 6 backend HR Excel tables
"""
import subprocess
import sys

import pandas as pd

from profiler import load_tables, profile_dataset, profile_tables, to_json

folder = sys.argv[1] if len(sys.argv) > 1 else "data"

print("=== 1. TESTS ===")
from pathlib import Path
_here = Path(__file__).resolve().parent     # always test the files next to this script, never stray copies elsewhere
code = subprocess.call([sys.executable, "-m", "pytest", "-q", str(_here / "test_profiler.py"),
                        str(_here / "test_profiling_contract.py"),
                        str(_here / "test_profiling_day4.py"),
                        str(_here / "test_profiling_day5.py"),
                        str(_here / "test_profiling_manual_checks.py"),
                        str(_here / "test_profiling_integration_regression.py"),
                        str(_here / "test_profiling_regression.py")], cwd=str(_here))
print("Tests:", "PASSED" if code == 0 else "FAILED (see output above)")

print("\n=== 2. SYNTHETIC DATASET (known answers) ===")
synthetic = pd.DataFrame({
    "customer_id": [1, 2, 3, 4, 5, 5],
    "age": [25, 30, None, 41, 30, 30],
    "city": ["Bengaluru", "Pune", "Pune", "Delhi", "Pune", "Pune"],
    "joined": ["2024-01-05", "2024-02-11", "2024-03-02", None, "2024-02-11", "2024-02-11"],
    "country": ["IN"] * 6,
    "notes": [None] * 6,
    "mixed": [1, "two", 3, "four", 5, 5],
})
rep = profile_dataset(synthetic)
open("synthetic_profile_report.json", "w").write(to_json(rep))
print(f"{rep['dataset']['row_count']} rows, {rep['dataset']['column_count']} cols, "
      f"{rep['dataset']['duplicate_row_count']} duplicate row(s), status={rep['status']}")
for w in rep["warnings"]:
    print("   -", w)

print("\n=== 3. BACKEND HR TABLES (6 Excel files) ===")
from pathlib import Path
if not Path(folder).is_dir():
    print(f"Folder '{folder}' was not found. Create a folder named data here and copy the six Excel files into it, "
          f"or run: python run_all.py <path to the folder with the Excel files>")
    sys.exit(1)
tables = load_tables(folder)
if not tables:
    print(f"No .xlsx/.csv files found in '{folder}'. Pass the folder: python run_all.py <folder>")
    sys.exit(1)
result = profile_tables(tables)
open("hr_profile_report.json", "w").write(to_json(result))
for name, r in result["tables"].items():
    d = r["dataset"]
    print(f"{name}: {d['row_count']} rows x {d['column_count']} cols, "
          f"{d['duplicate_row_count']} duplicates, status={r['status']}")
    for w in r["warnings"]:
        print("   -", w)

print("\nFiles written: synthetic_profile_report.json, hr_profile_report.json")

print("\n=== 4. CONTRACT: sample request -> response ===")
import json
from pathlib import Path
from profiling_service import run_profiling
here = Path(__file__).parent
request = json.loads((here / "samples" / "sample_profiling_request.json").read_text(encoding="utf-8"))
request["dataset_reference"]["location"] = str(here / "samples" / "demo_customers.csv")
response = run_profiling(request)
(here / "contract_response_run.json").write_text(json.dumps(response, indent=2), encoding="utf-8")
print(f"status={response['status']}, rows={response['dataset']['row_count']}, columns={response['dataset']['column_count']}, "
      f"warnings={[w['code'] for w in response['warnings']]}")
print("Written: contract_response_run.json")
