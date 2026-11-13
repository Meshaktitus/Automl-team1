"""Builds profiling_module_for_team2.zip: the Python implementation Team 2 needs to integrate and verify the profiling module.
Usage:  python make_team2_package.py
Contains code, schemas, samples, tests and requirements only. No datasets, reports or personal data.
"""
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
files = ["profiling_service.py", "profiler.py", "schema_validation.py", "generate_samples.py", "example_usage.py", "compare_profiles.py",
         "requirements.txt", "README.md", *sorted(p.name for p in HERE.glob("test_*.py"))]
files += sorted(str(p.relative_to(HERE)).replace("\\", "/") for p in (HERE / "schemas").glob("*.json"))
files += sorted(str(p.relative_to(HERE)).replace("\\", "/") for p in (HERE / "samples").iterdir() if p.suffix in (".json", ".csv"))
missing = [f for f in files if not (HERE / f).exists()]
if missing:
    raise SystemExit(f"Missing files, nothing written: {missing}")
target = HERE / "profiling_module_for_team2.zip"
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(HERE / f, f"profiling_module/{f}")
print(f"Wrote {target.name} with {len(files)} files:")
for f in files:
    print("  ", f)
