"""Pre-review check of the Dataset Profiling folder that is about to go to (or is already in) the shared repository.
Usage:  python check_repo_folder.py "<path to the Dataset_Profiling folder>"
Checks: required files present, nothing that must never be committed, no obvious secrets, and the tests pass from that folder.
Run it in your local clone before 'git add', and again after any change requested in the review.
"""
import re
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit('Usage: python check_repo_folder.py "<path to the Dataset_Profiling folder>"')
root = Path(sys.argv[1])
if not root.is_dir():
    sys.exit(f"Folder not found: {root}")

REQUIRED = ["profiling_service.py", "profiler.py", "schema_validation.py", "schemas/profiling_request.schema.json",
            "schemas/profiling_response.schema.json", "samples/sample_profiling_request.json", "samples/sample_profiling_response.json",
            "samples/demo_customers.csv", "requirements.txt", "README.md", "PROFILING_CONTRACT.md", "PROFILING_FIELD_REFERENCE.md",
            "PROFILING_KNOWN_ISSUES.md", "PROFILING_HANDOVER.md", "test_profiler.py", "test_profiling_contract.py", ".gitignore"]
OPTIONAL = ["example_usage.py", "run_all.py", "evidence.py", "profiling.types.ts", "generate_samples.py", "compare_profiles.py",
            "make_test_report.py", "baseline_verification.py", "integration_check.py", "regression_report.py", "hr_validation_report.py"]
FORBIDDEN_SUFFIX = (".xlsx", ".xls", ".exe", ".zip", ".pyc", ".parquet", ".sqlite", ".db", ".env", ".pem", ".key")
FORBIDDEN_DIRS = {"data", "hr_outputs", "send", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules"}
SECRET = re.compile(r"(password|passwd|secret|api[_-]?key|token|aws_access_key)\s*[:=]\s*['\"][^'\"]{6,}", re.IGNORECASE)

problems, warnings = [], []
files = [p for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts]
rel = {str(p.relative_to(root)).replace("\\", "/") for p in files}

print("== 1. Required files ==")
for f in REQUIRED:
    print(f"  {'OK     ' if f in rel else 'MISSING'} {f}")
    if f not in rel:
        problems.append(f"missing required file {f}")
print("\n== 2. Optional helper files present ==")
print("  " + (", ".join(f for f in OPTIONAL if f in rel) or "none"))
absent = [f for f in OPTIONAL if f not in rel]
if absent:
    print("  not included (fine if you chose to leave them out): " + ", ".join(absent))

print("\n== 3. Files and folders that must not be committed ==")
bad = [r for r in sorted(rel) if r.lower().endswith(FORBIDDEN_SUFFIX) or FORBIDDEN_DIRS & set(r.split("/")[:-1])]
for r in bad:
    print(f"  NOT ALLOWED  {r}")
    problems.append(f"remove {r}")
print("  none found" if not bad else "")
big = [(p.stat().st_size / 1e6, str(p.relative_to(root))) for p in files if p.stat().st_size > 2_000_000]
for mb, name in sorted(big, reverse=True):
    warnings.append(f"large file {name} ({mb:.1f} MB)")
    print(f"  LARGE FILE   {name} ({mb:.1f} MB)")

print("\n== 4. Possible secrets in text files ==")
hits = []
for p in files:
    if p.suffix.lower() in (".py", ".json", ".md", ".txt", ".ts", ".csv", ".yml", ".yaml", ".ini", ".cfg"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in SECRET.finditer(text):
            hits.append(f"{p.relative_to(root)}: {m.group(0)[:40]}...")
for h in hits:
    print("  CHECK  " + h)
    problems.append("review possible secret " + h.split(":")[0])
print("  none found" if not hits else "")

print("\n== 5. Tests from this folder ==")
test_files = sorted(str(p) for p in root.glob("test_*.py"))
if not test_files:
    problems.append("no test files")
    print("  no test files found")
else:
    have_pytest = subprocess.run([sys.executable, "-c", "import pytest"], capture_output=True).returncode == 0
    if have_pytest:
        cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *test_files]
    else:                                   # pytest not installed: run the test functions directly
        code = ("import glob, importlib, sys\nsys.path.insert(0, '.')\nn = bad = 0\n"
                "for f in sorted(glob.glob('test_*.py')):\n    m = importlib.import_module(f[:-3])\n"
                "    for x in [y for y in dir(m) if y.startswith('test_')]:\n        try:\n            getattr(m, x)(); n += 1\n"
                "        except Exception as e:\n            bad += 1; print('FAIL', x, type(e).__name__, str(e)[:100])\n"
                "print(n, 'passed,', bad, 'failed'); sys.exit(1 if bad else 0)")
        cmd = [sys.executable, "-c", code]
    run = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (run.stdout.strip().splitlines() or ["(no output)"])[-1]
    print("  " + tail)
    if run.returncode != 0:
        problems.append("tests did not all pass (run 'python -m pytest -q' in the folder to see why)")
        print("\n".join("  " + l for l in run.stdout.strip().splitlines()[-12:]))

print("\n== Result ==")
for w in warnings:
    print("  WARNING:", w)
if problems:
    print(f"  {len(problems)} problem(s) to fix before the review request:")
    for p in problems:
        print("   -", p)
else:
    print("  READY: required files present, nothing forbidden, no secrets found, tests pass.")
