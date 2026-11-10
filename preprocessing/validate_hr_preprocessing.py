from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

from reusable_preprocessing_pipeline import (
    fit_and_save_pipeline,
    load_pipeline,
    transform_new_data,
)

DATA_PATH = Path("data/raw/HumanResources.Employee.xlsx")
ARTIFACT_PATH = Path("data/processed/hr_preprocessing_validation.joblib")

NUMERIC = ["OrganizationLevel", "SalariedFlag", "CurrentFlag"]
CATEGORICAL = ["JobTitle", "MaritalStatus", "Gender"]
FEATURES = NUMERIC + CATEGORICAL
TARGETS = ["VacationHours", "SickLeaveHours"]

df = pd.read_excel(DATA_PATH)
X = df[FEATURES].copy()

# Create a validation-only copy with missing values to test imputers.
X.loc[X.index[0], "OrganizationLevel"] = None
X.loc[X.index[1], "JobTitle"] = None

X_train, X_test = train_test_split(
    X, test_size=0.2, random_state=42
)

artifact = fit_and_save_pipeline(
    training_features=X_train,
    numeric_columns=NUMERIC,
    categorical_columns=CATEGORICAL,
    artifact_path=ARTIFACT_PATH,
    model_family="logistic_regression",
)

loaded = load_pipeline(ARTIFACT_PATH)
X_test_transformed = transform_new_data(loaded, X_test)

# Test unseen category handling without refitting.
unseen = X_test.iloc[[0]].copy()
unseen["JobTitle"] = "Unseen_Test_JobTitle"
unseen_transformed = transform_new_data(loaded, unseen)

print("HR preprocessing validation")
print("Original dataset shape:", df.shape)
print("Feature columns used:", FEATURES)
print("Targets excluded from features:", TARGETS)
print("Training rows:", len(X_train))
print("Test rows:", len(X_test))
print("Transformed test shape:", X_test_transformed.shape)
print("Missing values after transform:", int(X_test_transformed.isna().sum().sum()))
print("Train/test transformed columns match:",
      list(X_test_transformed.columns) == list(transform_new_data(loaded, X_train).columns))
print("Unseen category handled:", unseen_transformed.shape[1] == X_test_transformed.shape[1])
print("Scaler enabled for logistic regression:", loaded["scale_numeric"])
print("Artifact saved and loaded:", ARTIFACT_PATH.exists())
print("Target columns included in features:",
      any(target in loaded["input_columns"] for target in TARGETS))

assert X_test_transformed.isna().sum().sum() == 0
assert list(X_test_transformed.columns) == list(transform_new_data(loaded, X_train).columns)
assert unseen_transformed.shape[1] == X_test_transformed.shape[1]
assert not any(target in loaded["input_columns"] for target in TARGETS)
assert loaded["scale_numeric"] is True
print("VALIDATION PASSED")
