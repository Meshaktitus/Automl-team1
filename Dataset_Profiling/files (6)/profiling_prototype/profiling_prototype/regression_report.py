"""Regression and performance report for the Dataset Profiling module (Week 3, Day 4) -> profiling_regression_report.txt
Usage:  python regression_report.py            (wide tables of 100, 500, 1000 and 2000 columns; 200,000-row table)
        python regression_report.py 4000       (custom widest size)
1. runs every regression test and lists pass or fail with its time
2. measures time, peak Python memory and response size for wide and long tables (observations, not limits)
Synthetic data only. Close other heavy programs first: timings depend on the machine and its load.
"""
import json
import platform
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import test_profiling_regression as regression
from profiling_service import RESPONSE_SCHEMA, run_profiling
from schema_validation import validate

HERE = Path(__file__).parent
widest = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
REQ = {"schema_version": "1.0-draft", "request_id": "perf", "dataset_reference": {"dataset_id": "perf", "source_type": "file"}}
lines = []


def out(text=""):
    print(text)
    lines.append(text)


out(f"PROFILING REGRESSION REPORT ({datetime.now().isoformat(timespec='seconds')})")
out(f"Python {platform.python_version()} | pandas {pd.__version__} | numpy {np.__version__} | {platform.system()} {platform.release()}")

out("\n== 1. Regression tests ==")
failed = []
for name in sorted(n for n in dir(regression) if n.startswith("test_")):
    start = time.perf_counter()
    try:
        getattr(regression, name)()
        out(f"PASS  {name} ({time.perf_counter() - start:.2f} s)")
    except Exception as exc:
        failed.append(name)
        out(f"FAIL  {name}: {type(exc).__name__}: {str(exc)[:200]}")
total = sum(1 for n in dir(regression) if n.startswith("test_"))
out(f"{total - len(failed)} passed, {len(failed)} failed")


def measure(df):
    start = time.perf_counter()
    resp = run_profiling(REQ, dataframe=df)
    seconds = time.perf_counter() - start
    tracemalloc.start()
    run_profiling(REQ, dataframe=df)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    ok = resp["status"] != "failed" and not validate(resp, RESPONSE_SCHEMA)
    size = len(json.dumps(resp, allow_nan=False))
    return ok, seconds, peak / 1e6, size / 1e6, resp


out("\n== 2. Performance and memory observations ==")
out("Peak memory is the extra Python memory used during profiling, measured on a second run; the table itself is not included.")
out(f"{'case':34} {'table MB':>9} {'seconds':>8} {'peak MB':>8} {'response MB':>12}  result")
sizes = [c for c in (100, 500, 1000, 2000) if c <= widest] + ([widest] if widest not in (100, 500, 1000, 2000) else [])
cases = [(f"wide: 100 rows x {c} columns", regression.wide_frame(c, 100)) for c in sizes]
rng = np.random.default_rng(5)
n = 200_000
cases.append(("long: 200,000 rows x 5 columns", pd.DataFrame({"id": np.arange(n), "x": rng.normal(size=n), "y": rng.integers(0, 100, n),
                                                              "category": rng.choice(list("abcdefghij"), n), "flag": rng.random(n) < 0.3})))
problems = 0
for label, df in cases:
    ok, seconds, peak, size, resp = measure(df)
    problems += 0 if ok else 1
    extra = f", {len(resp['columns'])} columns profiled" if ok else f", status {resp['status']}"
    out(f"{label:34} {df.memory_usage(deep=True).sum() / 1e6:>9.1f} {seconds:>8.2f} {peak:>8.1f} {size:>12.2f}  {'OK' if ok else 'PROBLEM'}{extra}")

out("\n== Summary ==")
out(f"Regression tests failing: {len(failed)} | performance cases with problems: {problems}")
out("Known limit: the whole table is held in memory, and wide tables produce proportionally larger responses; correlations are capped at 50 columns and 200 pairs.")
(HERE / "profiling_regression_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\nSaved: profiling_regression_report.txt")
