"""Baseline verification of the Dataset Profiling module (Week 3, Day 1) -> profiling_baseline_report.txt
Usage:  python baseline_verification.py data        (folder with the HR Excel files; demo_customers.csv is always included)
Runs the existing module, re-computes every statistic independently with pandas and compares it with the profiling output,
runs all tests and lists failing ones. Only counts, names and statistics are written, never row values.
"""
import importlib
import math
import platform
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from profiling_service import run_profiling

HERE = Path(__file__).parent
folder = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "data"
lines = []


def out(text=""):
    print(text)
    lines.append(text)


def close(a, b):
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-4)


out(f"PROFILING BASELINE REPORT ({datetime.now().isoformat(timespec='seconds')})")
out(f"Python {platform.python_version()} | pandas {pd.__version__} | {platform.system()} {platform.release()}")

# 1. tests ------------------------------------------------------------------------------------------------------
out("\n== 1. Existing test suite (failing tests are listed) ==")
passed, failing, skipped = 0, [], []
for f in sorted(HERE.glob("test_*.py")):
    mod = importlib.import_module(f.stem)
    for name in sorted(n for n in dir(mod) if n.startswith("test_")):
        try:
            getattr(mod, name)()
            passed += 1
        except Exception as exc:
            (skipped if type(exc).__name__ == "Skipped" else failing).append(f"{f.stem}.{name}: {type(exc).__name__}")
out(f"{passed} passed, {len(failing)} failing, {len(skipped)} skipped")
for item in failing:
    out(f"  FAILING  {item}")

# 2-4. independent recomputation ---------------------------------------------------------------------------------
sources = sorted(folder.glob("*.xlsx")) if folder.is_dir() else []
demo = HERE / "samples" / "demo_customers.csv"
if demo.exists():
    sources.append(demo)
totals = {"checks": 0, "mismatches": 0}
type_review = []
for path in sources:
    fmt = "xlsx" if path.suffix.lower() == ".xlsx" else "csv"
    resp = run_profiling({"schema_version": "1.0-draft", "request_id": "baseline",
                          "dataset_reference": {"dataset_id": path.stem, "source_type": "file", "location": str(path)},
                          "metadata": {"format": fmt, "missing_value_markers": ["NA", "n/a"] if fmt == "csv" else []}})
    out(f"\n== {path.stem} ==")
    if resp["status"] == "failed":
        out(f"  FAILED {[e['code'] for e in resp['errors']]}")
        totals["mismatches"] += 1
        continue
    df = pd.read_excel(path) if fmt == "xlsx" else pd.read_csv(path, na_values=["NA", "n/a"])
    problems = []

    def check(label, ok):
        totals["checks"] += 1
        if not ok:
            totals["mismatches"] += 1
            problems.append(label)

    d = resp["dataset"]
    check("row count", d["row_count"] == len(df))
    check("column count", d["column_count"] == df.shape[1])
    check("column names", d["column_names"] == [str(c) for c in df.columns])
    check("duplicate rows", d["duplicate_row_count"] == int(df.duplicated().sum()))
    n_num = n_cat = n_id = 0
    for c in resp["columns"]:
        s = df[c["name"]]
        check(f"{c['name']}: missing count", c["missing_count"] == int(s.isna().sum()))
        check(f"{c['name']}: missing percent", close(c["missing_pct"], round(100 * s.isna().mean(), 2)))
        check(f"{c['name']}: unique count", c["unique_count"] == int(s.nunique()))
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s) and c["inferred_type"] not in ("numerical", "empty"):
            type_review.append(f"{path.stem}.{c['name']}: dtype {s.dtype} but inferred {c['inferred_type']}")
        if pd.api.types.is_datetime64_any_dtype(s) and c["inferred_type"] not in ("datetime", "empty"):
            type_review.append(f"{path.stem}.{c['name']}: dtype {s.dtype} but inferred {c['inferred_type']}")
        if c["inferred_type"] == "numerical" and "summary" in c:
            n_num += 1
            x = pd.to_numeric(s.dropna(), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
            exp = {"min": x.min(), "max": x.max(), "mean": x.mean(), "median": x.median(), "std": x.std(),
                   "q1": x.quantile(0.25), "q3": x.quantile(0.75)}
            for key, value in exp.items():
                check(f"{c['name']}: {key}", close(c["summary"].get(key), None if pd.isna(value) else round(float(value), 4)))
        elif c["likely_identifier"]:
            n_id += 1
        if "top_values" in c:
            n_cat += 1
            non_null = s.dropna().astype(str)
            vc = non_null.value_counts().head(len(c["top_values"]))
            got = [(t["value"], t["count"], t["percentage"]) for t in c["top_values"]]
            want = [(str(k), int(v), round(100 * v / len(non_null), 2)) for k, v in vc.items()]
            check(f"{c['name']}: frequency table", got == want)
    out(f"  {d['row_count']} rows x {d['column_count']} columns | numerical columns checked {n_num} | "
        f"frequency tables checked {n_cat} | identifier columns (no statistics by design) {n_id}")
    out(f"  {'ALL CHECKS MATCH' if not problems else str(len(problems)) + ' MISMATCH(ES)'}")
    for p in problems[:15]:
        out(f"    MISMATCH  {p}")

out("\n== Type detection review (numeric or date storage type not detected as such) ==")
for item in type_review or ["none found"]:
    out(f"  {item}")

out("\n== Summary ==")
out(f"Tables verified: {len(sources)} | independent checks: {totals['checks']} | mismatches: {totals['mismatches']} | failing tests: {len(failing)}")
out("Defects: see PROFILING_KNOWN_ISSUES.md for the defect register (known issues, fixed defects and limitations).")
(HERE / "profiling_baseline_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\nSaved: profiling_baseline_report.txt")
