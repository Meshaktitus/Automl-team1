"""Side-by-side comparison of our Dataset Profiling module with Team 5's profile_csv -> team5_comparison_report.txt
Usage:  python compare_with_team5.py "<path to the unzipped team5-data-engineering folder>"
Runs both profilers on Team 5's profiling sample files and on edge cases (it imports their code; it does not copy it).
"""
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit('Usage: python compare_with_team5.py "<path to team5-data-engineering>"')
team5 = Path(sys.argv[1])
if not (team5 / "src" / "data_profiler.py").exists():
    sys.exit(f"{team5} does not contain src/data_profiler.py. Point to the team5-data-engineering folder.")
sys.path.insert(0, str(team5))
from src.data_profiler import profile_csv          # noqa: E402  (Team 5's profiler)

from profiling_service import run_profiling         # noqa: E402  (ours)

HERE = Path(__file__).parent
lines = []


def out(text=""):
    print(text)
    lines.append(text)


def ours(path):
    return run_profiling({"schema_version": "1.0-draft", "request_id": "cmp",
                          "dataset_reference": {"dataset_id": "x", "source_type": "file", "location": str(path)},
                          "metadata": {"format": "csv"}})


out(f"TEAM 5 vs DATASET PROFILING COMPARISON ({datetime.now().isoformat(timespec='seconds')})")
out("Their null_pct is a fraction (0 to 1); ours is a percentage (0 to 100). Compared here as percentages.\n")
out("== 1. Their profiling sample files ==")
samples = sorted((team5 / "data" / "test_samples").glob("profiling_*.csv"))
agree = total = 0
for path in samples:
    theirs, mine = profile_csv(path), ours(path)
    out(f"\n{path.name}: theirs {theirs['row_count']}x{theirs['column_count']} | ours {mine['dataset']['row_count']}x{mine['dataset']['column_count']} | ours status {mine['status']}")
    out(f"  {'column':14} {'their type':10} {'our type':12} {'null%':>12} {'distinct':>10}  min..max (theirs)  |  ours")
    ours_cols = {c["name"]: c for c in mine["columns"]}
    for c in theirs["columns"]:
        k = ours_cols[c["name"]]
        same = (round(c["null_pct"] * 100, 2) == k["missing_pct"] and c["distinct_count"] == k["unique_count"] and c["null_count"] == k["missing_count"])
        agree += same
        total += 1
        s = k.get("summary", {})
        out(f"  {c['name']:14} {c['data_type']:10} {k['inferred_type']:12} {c['null_pct'] * 100:>5.1f}/{k['missing_pct']:<5.1f} {c['distinct_count']:>4}/{k['unique_count']:<4}  "
            f"{c['min']}..{c['max']}  |  {s.get('min')}..{s.get('max')}  {'OK' if same else 'DIFFERENT'}")
out(f"\nCounts (missing, percentage, distinct) agree on {agree} of {total} columns.")

out("\n== 2. Edge cases ==")
tmp = tempfile.mkdtemp()


def case(label, text):
    path = Path(tmp) / "case.csv"
    path.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
    try:
        t = profile_csv(path)
        theirs = [(c["name"], c["data_type"], c["null_count"]) for c in t["columns"]]
    except Exception as exc:
        theirs = f"error: {exc}"
    o = ours(path)
    mine = [(c["name"], c["inferred_type"], c["missing_count"]) for c in o["columns"]] if o["status"] != "failed" else f"failed {[e['code'] for e in o['errors']]}"
    out(f"{label}\n   theirs: {theirs}\n   ours:   {mine}")


case("numbers mixed with words", "a\n1\n2\nunknown\n4\n")
case("whitespace-only cell", "a,b\n1,x\n2,   \n3,y\n")
case("duplicate header", "a,a\n1,2\n")
case("ragged row (too few fields)", "a,b\n1,2\n3\n")
case("empty file", "")
case("semicolon delimiter", "a;b\n1;2\n")
case("UTF-8 byte order mark", b"\xef\xbb\xbfid,name\n1,a\n")

out("\n== 3. What each side provides ==")
out("Both: row and column counts, null counts, distinct counts, numeric and date min and max, boolean and date detection.")
out("Ours only: mean, median, standard deviation, quartiles, skewness, histograms, top-value frequency tables, correlations, class distribution, "
    "structured warnings and errors, schema validation, XLSX input, identifier privacy, strict JSON.")
out("Theirs only: per-cell type validation against expected types, row numbers for findings, malformed-row detection, file-size limit, "
    "dataset metadata lookup and an API route.")
(HERE / "team5_comparison_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\nSaved: team5_comparison_report.txt")
