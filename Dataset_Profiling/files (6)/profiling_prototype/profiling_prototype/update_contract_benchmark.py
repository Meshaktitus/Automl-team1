"""Rewrites the 'Memory and speed' paragraph of PROFILING_CONTRACT.md from benchmark_results.json.
Usage:  python update_contract_benchmark.py      (run after python benchmark_profiling.py)
The memory limitation and the correlation caps are kept.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
data_file = HERE / "benchmark_results.json"
if not data_file.exists():
    sys.exit("benchmark_results.json not found. Run: python benchmark_profiling.py")
data = json.loads(data_file.read_text(encoding="utf-8"))
env, rows = data["environment"], data["results"]


def fmt(t):
    return f"{t[0]:.2f} s [{t[1]:.2f} - {t[2]:.2f}]"


figures = "; ".join(f"{r['rows']:,} rows {fmt(r['profiling'])} profiling only, {fmt(r['end_to_end'])} end to end "
                    f"({r['table_mb']} MB)" for r in rows)
paragraph = (
    "**Memory and speed:** the whole table is loaded into memory, so a table larger than available memory is not "
    "supported. Measured on " + env["platform"] + f" (Python {env['python']}, pandas {env['pandas']}, numpy {env['numpy']}, "
    f"{env['cpus']} CPUs) on {env['measured_at'][:10]} with `python benchmark_profiling.py` ({env['runs_per_size']} runs per size "
    "after a warm-up; median shown with the fastest and slowest run in brackets) on a table of 5 columns (id, number, integer, "
    "10-value category, date text). \"Profiling only\" is `profile_dataset`; \"end to end\" is `run_profiling` including request "
    "validation and the response schema check, without file reading. " + figures + ". Timings depend on the machine, the data "
    "and background load, and a single run can differ noticeably from the median; re-measure on the target machine before "
    "relying on them. Correlations are capped at 50 columns and 200 pairs.")

path = HERE / "PROFILING_CONTRACT.md"
text = path.read_text(encoding="utf-8")
new_text, count = re.subn(r"^\*\*Memory and speed:\*\*.*$", lambda m: paragraph, text, flags=re.M)
if count != 1:
    sys.exit(f"Expected one 'Memory and speed' paragraph in PROFILING_CONTRACT.md, found {count}. No change made.")
path.write_text(new_text, encoding="utf-8")
print("PROFILING_CONTRACT.md updated with the benchmark from", env["measured_at"])
