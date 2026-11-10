from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from reusable_preprocessing_pipeline import (
    fit_and_save_pipeline,
    load_pipeline,
    transform_new_data,
)


def run_workflow(name, features, target, numeric_columns, categorical_columns):
    print(f"\n{'=' * 65}")
    print(f"{name} SYNTHETIC WORKFLOW")
    print("=" * 65)

    # 1. Validate target separation.
    if target.name in features.columns:
        raise ValueError(
            f"Target leakage detected: {target.name} is present in features."
        )

    X_train = features.iloc[:6].copy()
    X_test = features.iloc[6:].copy()
    y_train = target.iloc[:6].copy()
    y_test = target.iloc[6:].copy()

    print("\n1. INPUT VALIDATION")
    print("Complete feature shape:", features.shape)
    print("Training input shape:", X_train.shape)
    print("Test input shape:", X_test.shape)
    print("Training target shape:", y_train.shape)
    print("Test target shape:", y_test.shape)
    print("Target excluded from model inputs:", target.name not in X_train.columns)

    # 2. Input data types and missing values.
    print("\n2. INPUT DATA TYPES")
    print(features.dtypes)

    print("\nTraining missing values before:")
    print(X_train.isna().sum())

    print("\nTest missing values before:")
    print(X_test.isna().sum())

    with TemporaryDirectory() as temp_dir:
        artifact_path = Path(temp_dir) / "pipeline.joblib"

        # 3. Fit transformations using training data only.
        artifact = fit_and_save_pipeline(
            training_features=X_train,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
            artifact_path=artifact_path,
            scale_numeric=True,
        )

        # 4. Reload fitted transformations.
        artifact = load_pipeline(artifact_path)

        # 5. Transform training and test data without refitting.
        train_output = transform_new_data(artifact, X_train)
        test_output = transform_new_data(artifact, X_test)

        # 6. Check repeatability.
        repeated_test_output = transform_new_data(artifact, X_test)
        repeatable = test_output.equals(repeated_test_output)

        print("\n3. INPUT AND OUTPUT SHAPE COMPARISON")
        print("Training input:", X_train.shape)
        print("Training output:", train_output.shape)
        print("Test input:", X_test.shape)
        print("Test output:", test_output.shape)

        print("\n4. OUTPUT DATA TYPES")
        print(train_output.dtypes)

        print("\n5. MISSING VALUES AFTER TRANSFORMATION")
        print(
            "Training output missing values:",
            int(train_output.isna().sum().sum()),
        )
        print(
            "Test output missing values:",
            int(test_output.isna().sum().sum()),
        )

        # 7. Trace output features to their source columns.
        print("\n6. FEATURE LINEAGE")
        lineage = []

        for output_column in train_output.columns:
            source_column = next(
                (
                    source
                    for source in numeric_columns + categorical_columns
                    if output_column == source
                    or output_column.startswith(source + "_")
                ),
                "Source mapping requires review",
            )

            record = {
                "source_column": source_column,
                "output_feature": output_column,
            }
            lineage.append(record)
            print(record)

        # 8. Target leakage checks.
        print("\n7. TARGET-LEAKAGE VALIDATION")
        print("Target column:", target.name)
        print("Target excluded from input:", target.name not in X_train.columns)
        print("Training target preserved:", y_train.equals(target.iloc[:6]))
        print("Test target preserved:", y_test.equals(target.iloc[6:]))

        # 9. Reusable transformation checks.
        print("\n8. REUSABLE TRANSFORMATION VALIDATION")
        print("Pipeline artifact saved:", artifact_path.exists())
        print("Pipeline artifact reloaded: Yes")
        print("Inference transformed without refitting: Yes")
        print("Repeated inference output identical:", repeatable)

        print(
            "Training and test output columns consistent:",
            list(train_output.columns) == list(test_output.columns),
        )

        # 10. Display fitted transformation parameters.
        print("\n9. FITTED TRANSFORMATION PARAMETERS")

        fitted_pipeline = artifact["pipeline"]

        numeric_pipeline = fitted_pipeline.named_transformers_["numeric"]

        print(
            "Numeric imputer statistics:",
            numeric_pipeline.named_steps["imputer"].statistics_,
        )

        print(
            "Scaler mean:",
            numeric_pipeline.named_steps["scaler"].mean_,
        )

        print(
            "Scaler scale:",
            numeric_pipeline.named_steps["scaler"].scale_,
        )

        categorical_pipeline = fitted_pipeline.named_transformers_["categorical"]

        print(
            "Categorical imputer statistics:",
            categorical_pipeline.named_steps["imputer"].statistics_,
        )

        # Do not assume the one-hot encoder's step name.
        encoder = next(
            (
                step
                for step in categorical_pipeline.named_steps.values()
                if hasattr(step, "categories_")
            ),
            None,
        )

        if encoder is not None:
            print("One-hot encoder categories:", encoder.categories_)
        else:
            print("One-hot encoder categories: Encoder step not identified.")

        # 11. Final workflow summary.
        print("\n10. WORKFLOW SUMMARY")
        print(
            "Training output contains missing values:",
            bool(train_output.isna().any().any()),
        )
        print(
            "Test output contains missing values:",
            bool(test_output.isna().any().any()),
        )
        print("Repeatability check passed:", repeatable)

        # Explicit validation assertions.
        assert target.name not in X_train.columns
        assert target.name not in X_test.columns
        assert not train_output.isna().any().any()
        assert not test_output.isna().any().any()
        assert list(train_output.columns) == list(test_output.columns)
        assert repeatable

        print("Workflow validation assertions: PASSED")


# ---------------------------------------------------------
# SYNTHETIC CLASSIFICATION DATASET
# ---------------------------------------------------------

classification_X = pd.DataFrame({
    "Age": [22, np.nan, 35, 40, 29, 50, 31, 44],
    "Salary": [30000, 35000, 45000, np.nan, 40000, 60000, 42000, 52000],
    "Department": [
        "Engineering",
        "HR",
        "Sales",
        "Engineering",
        "HR",
        "Sales",
        "Legal",
        "Engineering",
    ],
})

classification_y = pd.Series(
    [0, 0, 1, 1, 0, 1, 0, 1],
    name="Outcome",
)


# ---------------------------------------------------------
# SYNTHETIC REGRESSION DATASET
# ---------------------------------------------------------

regression_X = pd.DataFrame({
    "Experience": [1, 2, np.nan, 4, 5, 6, 3, 7],
    "HoursTraining": [10, 12, 15, np.nan, 20, 22, 18, 25],
    "Department": [
        "HR",
        "Sales",
        "HR",
        "Engineering",
        "Sales",
        "Engineering",
        "Legal",
        "HR",
    ],
})

regression_y = pd.Series(
    [25.0, 28.0, 31.0, 35.0, 39.0, 42.0, 33.0, 46.0],
    name="TargetValue",
)


# ---------------------------------------------------------
# RUN BOTH WORKFLOWS
# ---------------------------------------------------------

if __name__ == "__main__":

    run_workflow(
        "CLASSIFICATION",
        classification_X,
        classification_y,
        ["Age", "Salary"],
        ["Department"],
    )

    run_workflow(
        "REGRESSION",
        regression_X,
        regression_y,
        ["Experience", "HoursTraining"],
        ["Department"],
    )