
import pandas as pd

df = pd.read_excel("data/HumanResources.Employee.xlsx")

def recommend_models(data, target):
    if target not in data.columns:
        return {"error": f"Target '{target}' was not found."}

    y = data[target].dropna()

    if y.empty:
        return {"error": "Target contains no usable values."}

    if y.nunique() <= 1:
        return {
            "target": target,
            "problem_type": "Undetermined",
            "recommendations": [],
            "reason": "Target has only one distinct value."
        }

    if pd.api.types.is_numeric_dtype(y):
        problem_type = "Regression"
        models = [
            "Linear Regression",
            "Decision Tree Regressor",
            "Random Forest Regressor"
        ]
    else:
        problem_type = "Classification"
        models = [
            "Logistic Regression",
            "Decision Tree Classifier",
            "Random Forest Classifier"
        ]

    result = {
        "target": target,
        "problem_type": problem_type,
        "rows_with_target": len(y),
        "unique_target_values": int(y.nunique()),
        "recommendations": models
    }

    if problem_type == "Classification":
        counts = y.value_counts()
        result["smallest_class_count"] = int(counts.min())
        result["classes_with_one_record"] = int((counts == 1).sum())

    return result


for target in ["JobTitle", "VacationHours",
               "SickLeaveHours", "CurrentFlag"]:
    print("\n", recommend_models(df, target))
