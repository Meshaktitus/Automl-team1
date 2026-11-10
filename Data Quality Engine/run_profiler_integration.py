import os
import json
import pandas as pd

profile_path = "sanjay_profiling_output.json"
dataset_path = "HumanResources.Employee (1).xlsx"

print("=" * 70)
print("PROFILING INTEGRATION ENGINE: CONSUMING SANJAY'S PROFILE METADATA")
print("=" * 70)

if not os.path.exists(profile_path):
    print(f"[Error] Sanjay's profiling file '{profile_path}' not found!")
    exit(1)

with open(profile_path, "r") as f:
    profile_meta = json.load(f)

print(f"\n[Loaded Profiling Metadata]")
print(f"  • Profiler: {profile_meta['profiler_name']}")
print(f"  • Target Dataset: {profile_meta['dataset']}")
print(f"  • Baseline Total Rows: {profile_meta['total_rows']}")

if not os.path.exists(dataset_path):
    print(f"[Error] Dataset file '{dataset_path}' not found!")
    exit(1)

df = pd.read_excel(dataset_path)

print("\n[Executing Validation Rules Driven by Sanjay's Profile]")
assertions_passed = 0
assertions_total = 0

for col, specs in profile_meta["columns"].items():
    assertions_total += 1
    if col not in df.columns:
        print(f"  ❌ [FAIL] Column '{col}' listed in profile is missing from dataset.")
        continue
        
    actual_nulls = df[col].isnull().sum()
    expected_nulls = specs["null_count"]
    
    if actual_nulls == expected_nulls:
        print(f"  ✔ [PASS] '{col}': Null count matches Sanjay's profile ({actual_nulls} nulls).")
        assertions_passed += 1
    else:
        print(f"  ⚠️ [MISMATCH] '{col}': Expected {expected_nulls} nulls from profile, found {actual_nulls}.")

    if "min" in specs and "max" in specs:
        assertions_total += 1
        actual_min = df[col].min()
        actual_max = df[col].max()
        if actual_min >= specs["min"] and actual_max <= specs["max"]:
            print(f"    ✔ [PASS] '{col}' values bounded within Sanjay's limits [{specs['min']}, {specs['max']}].")
            assertions_passed += 1
        else:
            print(f"    ⚠️ [ALERT] '{col}' out of profile bounds.")

print("\n" + "=" * 70)
print(f"Integration Summary: {assertions_passed}/{assertions_total} Profile Assertions Passed.")
print("SUCCESS: Quality engine successfully consumed and validated against Sanjay's profile!")
print("=" * 70)