"""Compares two tables (for example data before and after preprocessing) using the profiling module.
Usage:  python compare_profiles.py before.csv after.csv
Reports shape, added and removed columns, and per-column changes in type and missing values.
"""
import sys
from pathlib import Path

import pandas as pd

from profiling_service import run_profiling


def profile(path):
    p = Path(path)
    fmt = "xlsx" if p.suffix.lower() == ".xlsx" else "csv"
    resp = run_profiling({"schema_version": "1.0-draft", "request_id": f"compare-{p.stem}",
                          "dataset_reference": {"dataset_id": p.stem, "source_type": "file", "location": str(p)},
                          "metadata": {"format": fmt}})
    if resp["status"] == "failed":
        sys.exit(f"Could not profile {path}: {resp['errors']}")
    return resp


def compare(before, after):
    """Returns a list of text lines describing what changed between two profiling responses."""
    b, a = before["dataset"], after["dataset"]
    lines = [f"Rows:    {b['row_count']} -> {a['row_count']}", f"Columns: {b['column_count']} -> {a['column_count']}"]
    bc = {c["name"]: c for c in before["columns"]}
    ac = {c["name"]: c for c in after["columns"]}
    removed, added = [n for n in bc if n not in ac], [n for n in ac if n not in bc]
    lines.append(f"Removed columns: {removed or 'none'}")
    lines.append(f"Added columns:   {added or 'none'}")
    changes = []
    for name in bc:
        if name in ac:
            x, y = bc[name], ac[name]
            if (x["inferred_type"], x["dtype"]) != (y["inferred_type"], y["dtype"]):
                changes.append(f"  {name}: type {x['dtype']}/{x['inferred_type']} -> {y['dtype']}/{y['inferred_type']}")
            if x["missing_count"] != y["missing_count"]:
                changes.append(f"  {name}: missing {x['missing_count']} -> {y['missing_count']}")
    lines.append("Changed columns:" + ("" if changes else " none"))
    lines.extend(changes)
    still_missing = [n for n in ac if ac[n]["missing_count"] > 0]
    lines.append(f"Columns that still have missing values after: {still_missing or 'none'}")
    return lines


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python compare_profiles.py before.csv after.csv")
    print("\n".join(compare(profile(sys.argv[1]), profile(sys.argv[2]))))
