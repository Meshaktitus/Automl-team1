"""Writes one contract-format profiling response per HR table into hr_outputs/.

Usage:
    python generate_hr_outputs.py data
    python generate_hr_outputs.py data Employee:Gender            (also writes a with-target file for that table)
    python generate_hr_outputs.py data Employee:Gender Employee:MaritalStatus

A target is written as Table:Column, where Table is the end of the file name (for example Employee).
The files follow schemas/profiling_response.schema.json (1.0-draft). No identifier values are included.
"""
import json
import sys
from pathlib import Path

from profiling_service import run_profiling

folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
targets = []
for arg in sys.argv[2:]:
    table, _, column = arg.partition(":")
    if not column:
        sys.exit(f"Target '{arg}' must look like Table:Column, for example Employee:Gender")
    targets.append((table, column))

out = Path("hr_outputs")
out.mkdir(exist_ok=True)
files = sorted(folder.glob("*.xlsx"))
if not files:
    sys.exit(f"No .xlsx files found in '{folder}'.")


def profile(f, options=None):
    request = {"schema_version": "1.0-draft", "request_id": f"hr-{f.stem}",
               "dataset_reference": {"dataset_id": f.stem, "name": f.name, "source_type": "file", "location": str(f)},
               "metadata": {"format": "xlsx"}}
    if options:
        request["options"] = options
    return run_profiling(request)


def show(label, resp):
    d = resp["dataset"]
    cd = resp.get("class_distribution")
    extra = f", class_distribution on '{cd['target_column']}' ({cd['class_count']} classes)" if cd else ""
    print(f"{label}: status={resp['status']}" + (f", {d['row_count']}x{d['column_count']}{extra}" if d else f", errors={resp['errors']}"))


used = set()
for f in files:
    resp = profile(f)
    (out / f"{f.stem}.profile.json").write_text(json.dumps(resp, indent=2), encoding="utf-8")
    show(f.stem, resp)
    key = f.stem.replace(".", "_")
    for table, column in targets:
        if key == table or key.endswith("_" + table):
            used.add(table)
            resp_t = profile(f, {"target_column": column})
            (out / f"{f.stem}.profile_target_{column}.json").write_text(json.dumps(resp_t, indent=2), encoding="utf-8")
            show(f"  with target {column}", resp_t)
            for w in resp_t["warnings"]:
                if "target" in w["message"].lower():
                    print(f"    note: {w['code']}: {w['message']}")
for table in sorted({t for t, _ in targets} - used):
    print(f"No table ending in '{table}' was found.")
print(f"Written to {out}/")
