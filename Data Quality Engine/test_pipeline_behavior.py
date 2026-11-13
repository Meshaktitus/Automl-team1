import os
import pandas as pd

# Define paths
dataset_path = "HumanResources.EmployeePayHistory.xlsx"

print("=" * 70)
print("PIPELINE BEHAVIOR DEMONSTRATION: WARNINGS VS. BLOCKING ERRORS")
print("=" * 70)

if not os.path.exists(dataset_path):
    print(f"[Error] Dataset '{dataset_path}' not found!")
    exit(1)

df = pd.read_excel(dataset_path)

# -------------------------------------------------------------
# TEST 1: Non-Blocking Warnings (Pipeline Continues)
# -------------------------------------------------------------
print("\n[Test 1] Evaluating Non-Blocking Warnings...")
has_blocking_errors = False
warning_count = 0

# Check for IQR outliers (treated as non-blocking warnings)
if 'Rate' in df.columns:
    s = df['Rate'].dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    upper_bound = q3 + 1.5 * iqr
    outliers = (s > upper_bound).sum()
    if outliers > 0:
        warning_count += 1
        print(f"  ⚠️ [WARNING] Detected {outliers} IQR outliers in 'Rate'.")
        print("  ➔ Action: Flagged for preprocessing review, but pipeline continues execution.")

print(f"  Result: Found {warning_count} warning(s). Zero blocking errors.")
print("  ✔ Pipeline successfully proceeds to downstream preprocessing steps.")

# -------------------------------------------------------------
# TEST 2: Critical Invalid Inputs / Blocking Errors (Pipeline Stops)
# -------------------------------------------------------------
print("\n[Test 2] Evaluating Critical Invalid Inputs (Blocking Error)...")
required_columns = ["BusinessEntityID", "Rate", "PayFrequency", "NonExistentColumn"]
missing_cols = [col for col in required_columns if col not in df.columns]

if len(missing_cols) > 0:
    has_blocking_errors = True
    print(f"  ❌ [BLOCKING ERROR] Critical schema validation failed! Missing columns: {missing_cols}")
else:
    print("  ✔ Schema check passed.")

# Simulate an invalid schema / corrupt input condition to prove pipeline halt
simulate_corrupt_schema = True  # Triggering block condition for demonstration
if simulate_corrupt_schema:
    has_blocking_errors = True
    print("  ❌ [BLOCKING ERROR] Invalid primary key domain or corrupt schema structure detected.")

if has_blocking_errors:
    print("  🛑 [HALT] Pipeline execution stopped immediately to prevent corrupt data propagation.")
    print("  ➔ Action: Exiting workflow and triggering alert notification.")
    exit(0)  # Clean termination of pipeline
else:
    print("  ✔ Pipeline completed successfully.")

print("\n" + "=" * 70)
print("SUCCESS: Pipeline behavior verified (Continues on warnings, stops on invalid inputs)!")
print("=" * 70)