"""Readable profiling summary for every table in a folder; also saved as demonstration_report.txt.
Usage:  python show_profile_summary.py data          (or:  python show_profile_summary.py data Employee)
Shows dimensions, data types, missingness, cardinality, summary statistics and warnings straight from the profiling response.
No sample values of identifier columns are shown.
"""
import sys
from datetime import datetime
from pathlib import Path

from profiling_service import run_profiling

HERE = Path(__file__).parent
folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
only = sys.argv[2].lower() if len(sys.argv) > 2 else None
files = [f for f in sorted(folder.glob("*.xlsx")) + sorted(folder.glob("*.csv")) if not only or only in f.stem.lower()]
if not files:
    sys.exit(f"No matching .xlsx/.csv files in '{folder}'.")

lines = []


def out(text=""):
    print(text)
    lines.append(text)


out(f"DATASET PROFILING DEMONSTRATION REPORT ({datetime.now().isoformat(timespec='seconds')})")
for f in files:
    fmt = "xlsx" if f.suffix.lower() == ".xlsx" else "csv"
    resp = run_profiling({"schema_version": "1.0-draft", "request_id": "summary", "metadata": {"format": fmt},
                          "dataset_reference": {"dataset_id": f.stem, "name": f.name, "source_type": "file", "location": str(f)}})
    if resp["status"] == "failed":
        out(f"\n{f.stem}: FAILED {[e['code'] for e in resp['errors']]}")
        continue
    d = resp["dataset"]
    types = {}
    for c in resp["columns"]:
        types[c["inferred_type"]] = types.get(c["inferred_type"], 0) + 1
    out(f"\n{f.stem}: status={resp['status']}, {d['row_count']} rows x {d['column_count']} columns, "
        f"{d['duplicate_row_count']} duplicate rows")
    out("  data types: " + ", ".join(f"{n} {t}" for t, n in sorted(types.items())))
    out(f"  {'column':28} {'type':12} {'missing%':>8} {'unique':>7}  distribution        warnings")
    for c in resp["columns"]:
        dist = ("histogram" if "histogram" in c else "top_values" if "top_values" in c
                else "range" if c["inferred_type"] == "datetime" and "summary" in c else "-")
        flag = " (id)" if c["likely_identifier"] else ""
        out(f"  {c['name'][:26] + flag:28} {c['inferred_type']:12} {c['missing_pct']:>8} {c['unique_count']:>7}  "
            f"{dist:19} {', '.join(c['warnings']) or '-'}")
    stats = [c for c in resp["columns"] if c["inferred_type"] == "numerical" and "summary" in c]
    if stats:
        out("  numerical summary statistics:")
        for c in stats:
            s = c["summary"]
            out(f"    {c['name'][:26]:26} min {s.get('min')}  max {s.get('max')}  mean {s.get('mean')}  "
                f"median {s.get('median')}  std {s.get('std')}")
    if resp.get("correlations"):
        out(f"  strongest correlation: {resp['correlations'][0]}")

(HERE / "demonstration_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\nSaved: demonstration_report.txt")
