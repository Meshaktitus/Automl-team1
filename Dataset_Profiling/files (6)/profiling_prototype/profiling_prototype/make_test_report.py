"""Runs the unit tests with full detail and saves the output as unit_test_report.txt.
Usage:  python make_test_report.py
"""
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
tests = sorted(str(p) for p in HERE.glob("test_*.py"))
run = subprocess.run([sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", *tests], cwd=str(HERE),
                     capture_output=True, text=True, encoding="utf-8", errors="replace")
header = [f"UNIT TEST REPORT: Dataset Profiling ({datetime.now().isoformat(timespec='seconds')})",
          f"Python {platform.python_version()} | pandas {pd.__version__} | {platform.system()} {platform.release()}",
          f"Command: python -m pytest -v {' '.join(Path(t).name for t in tests)}", ""]
report = "\n".join(header) + run.stdout + (("\n" + run.stderr) if run.stderr.strip() else "") + f"\nExit code: {run.returncode} (0 means all passed)\n"
(HERE / "unit_test_report.txt").write_text(report, encoding="utf-8")
print(report[-700:])
print("Saved: unit_test_report.txt")
