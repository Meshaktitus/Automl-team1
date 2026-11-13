import json
import os

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_data_quality_checks(response_data):
    print("=== Running Data-Quality Validation Checks ===")
    
    # 1. Check Dataset-level metrics
    dataset = response_data.get("dataset")
    if dataset:
        row_count = dataset.get("row_count", 0)
        dup_count = dataset.get("duplicate_row_count", 0)
        print(f"[PASS] Dataset loaded. Rows: {row_count}, Duplicate Rows: {dup_count}")
    else:
        print("[FAIL] Dataset table-level facts are missing.")

    # 2. Check Column-level quality metrics (missing percentages, types, warnings)
    columns = response_data.get("columns", [])
    print(f"\nAnalyzing {len(columns)} columns for data quality:")
    for col in columns:
        name = col.get("name")
        missing_pct = col.get("missing_pct", 0.0)
        inferred_type = col.get("inferred_type")
        col_warnings = col.get("warnings", [])
        
        print(f" - Column '{name}': type={inferred_type}, missing={missing_pct}%, warnings={col_warnings}")
        
        # Example data-quality rule check: Flag high missing values (> 50%)
        if missing_pct > 50.0:
            print(f"   [DQ ALERT] Column '{name}' has high missing percentage ({missing_pct}%).")

    # 3. Check Global Warnings
    warnings = response_data.get("warnings", [])
    print(f"\n[INFO] Total global warnings flagged: {len(warnings)}")
    for w in warnings:
        print(f" - [{w.get('severity').upper()}] {w.get('code')} on '{w.get('column')}': {w.get('message')}")

if __name__ == "__main__":
    # Check both potential locations for the file
    possible_paths = [
        os.path.join("samples", "sample_profiling_response.json"),
        "sample_profiling_response.json"
    ]
    
    response_path = None
    for path in possible_paths:
        if os.path.exists(path):
            response_path = path
            break
            
    if response_path:
        print(f"Loading profiling response from: {response_path}\n")
        resp = load_json(response_path)
        run_data_quality_checks(resp)
    else:
        print("Error: Could not find 'sample_profiling_response.json' in 'samples/' or the current directory.")
        print("Please ensure the file is saved in your workspace folder.")