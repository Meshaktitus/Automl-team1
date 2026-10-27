
import pandas as pd

# Load the HR Employee dataset
file_path = "data/HumanResources.Employee.xlsx"
df = pd.read_excel(file_path)

candidates = {
    "JobTitle": "Classification",
    "VacationHours": "Regression",
    "SickLeaveHours": "Regression",
    "CurrentFlag": "Classification",
}

print("=" * 65)
print("AUTOML - CANDIDATE FEASIBILITY ASSESSMENT")
print("=" * 65)

for target, problem_type in candidates.items():
    print(f"\nTarget: {target}")
    print(f"Proposed problem type: {problem_type}")

    if target not in df.columns:
        print("Feasibility: Cannot assess - target column not found")
        continue

    values = df[target].dropna()
    unique_count = values.nunique()

    print(f"Rows with target values: {len(values)}")
    print(f"Missing target values: {df[target].isna().sum()}")
    print(f"Distinct target values: {unique_count}")

    if unique_count <= 1:
        print("Recommendation feasibility: NOT SUITABLE")
        print("Reason: Target has no variation.")
        continue

    if problem_type == "Classification":
        counts = values.value_counts()
        singleton_classes = int((counts == 1).sum())
        rare_classes = int((counts <= 5).sum())

        print(f"Classes with one record: {singleton_classes}")
        print(f"Classes with 5 or fewer records: {rare_classes}")
        print("Evaluation metrics: Accuracy, macro-F1, weighted-F1")
        
        if singleton_classes > 0:
            print("Evaluation concern: Rare classes may prevent reliable")
            print("stratified validation and per-class assessment.")

    else:
        print("Evaluation metrics: MAE, RMSE, R-squared")
        print("Check: Target distribution, baseline performance,")
        print("feature leakage, and business relevance.")

    print("Feasibility: PRELIMINARY - further review required")

print("\n" + "=" * 65)
print("No final target selected. No models trained.")
print("Final decision requires team agreement.")
print("=" * 65)
