"""Measures profiling time and table memory, repeatably, to document performance limits.
Usage:  python benchmark_profiling.py            (sizes 10k, 100k, 500k, 1M rows; 3 runs each)
        python benchmark_profiling.py 2000000    (custom sizes)
Writes benchmark_results.json and benchmark_results.txt. Then run:  python update_contract_benchmark.py

Each size is measured RUNS times on the same table after a warm-up run. The median is reported with the fastest
and slowest run, so run-to-run variation (background load, memory allocation, caching) is visible.
  profiling only = profile_dataset(df)
  end to end     = run_profiling(request, dataframe=df): request validation, profiling, response conversion and the
                   module's own schema check of the response (file reading is not included).
"""
import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from profiler import profile_dataset
from profiling_service import run_profiling

HERE = Path(__file__).parent
RUNS = 3
sizes = [int(a) for a in sys.argv[1:]] or [10_000, 100_000, 500_000, 1_000_000]
REQUEST = {"schema_version": "1.0-draft", "request_id": "bench",
           "dataset_reference": {"dataset_id": "bench", "source_type": "file"}}


def make_table(n):
    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "id": np.arange(n), "x": rng.normal(size=n), "y": rng.integers(0, 100, n),
        "category": rng.choice(list("abcdefghij"), n),
        "date": pd.date_range("2020-01-01", periods=n, freq="min").astype(str)})
    df.loc[::17, "x"] = np.nan
    return df


def timed(fn):
    start = time.perf_counter()
    result = fn()
    return time.perf_counter() - start, result


env = {"platform": f"{platform.system()} {platform.release()}", "python": platform.python_version(),
       "pandas": pd.__version__, "numpy": np.__version__, "cpus": os.cpu_count(),
       "measured_at": datetime.now().isoformat(timespec="seconds"), "runs_per_size": RUNS}
lines = [f"BENCHMARK ({env['measured_at']})",
         f"{env['platform']} | Python {env['python']} | pandas {env['pandas']} | numpy {env['numpy']} | {env['cpus']} CPUs | {RUNS} runs per size",
         "Close other heavy programs while this runs. Times in seconds: median [fastest - slowest].", "",
         f"{'rows':>10} {'MB':>5}  {'profiling only':>26}  {'end to end':>26}"]
print("\n".join(lines))

warm = make_table(5_000)                      # warm-up so one-time start-up costs are not counted
profile_dataset(warm)
run_profiling(REQUEST, dataframe=warm)

results = []
for n in sizes:
    df = make_table(n)
    mb = df.memory_usage(deep=True).sum() / 1e6
    prof, e2e = [], []
    for _ in range(RUNS):
        prof.append(timed(lambda: profile_dataset(df))[0])
        seconds, resp = timed(lambda: run_profiling(REQUEST, dataframe=df))
        if resp["status"] == "failed":
            sys.exit(f"Benchmark stopped: profiling failed for {n} rows: {resp['errors']}")
        e2e.append(seconds)
    row = {"rows": n, "table_mb": round(mb), "profiling": [round(statistics.median(prof), 2), round(min(prof), 2), round(max(prof), 2)],
           "end_to_end": [round(statistics.median(e2e), 2), round(min(e2e), 2), round(max(e2e), 2)]}
    results.append(row)
    p, e = row["profiling"], row["end_to_end"]
    line = f"{n:>10,} {row['table_mb']:>5}  {p[0]:>8.2f} [{p[1]:.2f} - {p[2]:.2f}]  {e[0]:>8.2f} [{e[1]:.2f} - {e[2]:.2f}]"
    print(line)
    lines.append(line)

note = "Note: the whole table is held in memory. Tables larger than available memory are not supported."
print(note)
(HERE / "benchmark_results.json").write_text(json.dumps({"environment": env, "results": results}, indent=2), encoding="utf-8")
(HERE / "benchmark_results.txt").write_text("\n".join(lines + ["", note]) + "\n", encoding="utf-8")
print("Saved: benchmark_results.json, benchmark_results.txt. Next: python update_contract_benchmark.py")
