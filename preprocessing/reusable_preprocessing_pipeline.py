
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


MODEL_SCALING = {
    "logistic_regression": True,
    "linear_regression": True,
    "knn": True,
    "decision_tree_classifier": False,
    "decision_tree_regressor": False,
    "random_forest_classifier": False,
    "random_forest_regressor": False,
}


def _validate_feature_names(columns, group_name):
    columns = list(columns)

    if any(not isinstance(c, str) or not c.strip() for c in columns):
        raise ValueError(
            f"{group_name} feature names must be non-empty strings."
        )

    if len(columns) != len(set(columns)):
        raise ValueError(
            f"{group_name} feature columns must not be duplicated."
        )

    return columns


def _validate_dataframe_columns(dataframe, dataframe_name):
    if not dataframe.columns.is_unique:
        duplicates = dataframe.columns[
            dataframe.columns.duplicated()
        ].tolist()

        raise ValueError(
            f"{dataframe_name} contains duplicate columns: {duplicates}"
        )


def _validate_feature_groups(numeric_columns, categorical_columns):
    numeric_columns = _validate_feature_names(
        numeric_columns, "Numeric"
    )
    categorical_columns = _validate_feature_names(
        categorical_columns, "Categorical"
    )

    overlap = set(numeric_columns) & set(categorical_columns)

    if overlap:
        raise ValueError(
            f"Feature groups overlap: {sorted(overlap)}"
        )

    columns = numeric_columns + categorical_columns

    if not columns:
        raise ValueError("At least one feature column is required.")

    return numeric_columns, categorical_columns, columns


def _resolve_scaling(model_family, scale_numeric):
    """Choose scaling based on model family when supplied."""

    if model_family is None:
        return scale_numeric

    if model_family not in MODEL_SCALING:
        raise ValueError(
            f"Unsupported model_family: {model_family}. "
            f"Supported models: {sorted(MODEL_SCALING)}"
        )

    return MODEL_SCALING[model_family]


def build_preprocessing_pipeline(
    numeric_columns,
    categorical_columns,
    scale_numeric=True,
    model_family=None,
):
    numeric_columns, categorical_columns, _ = (
        _validate_feature_groups(
            numeric_columns,
            categorical_columns,
        )
    )

    scale_numeric = _resolve_scaling(
        model_family, scale_numeric
    )

    transformers = []

    if numeric_columns:
        numeric_steps = [
            ("imputer", SimpleImputer(strategy="median"))
        ]

        if scale_numeric:
            numeric_steps.append(
                ("scaler", StandardScaler())
            )

        transformers.append(
            (
                "numeric",
                Pipeline(numeric_steps),
                numeric_columns,
            )
        )

    if categorical_columns:
        categorical_pipeline = Pipeline(
            [
                (
                    "imputer",
                    SimpleImputer(strategy="most_frequent"),
                ),
                (
                    "encoder",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        sparse_output=False,
                    ),
                ),
            ]
        )

        transformers.append(
            (
                "categorical",
                categorical_pipeline,
                categorical_columns,
            )
        )

    return ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        verbose_feature_names_out=False,
    )


def fit_and_save_pipeline(
    training_features,
    numeric_columns,
    categorical_columns,
    artifact_path,
    scale_numeric=True,
    model_family=None,
):
    """Fit on training data and save the reusable artifact."""

    if not isinstance(training_features, pd.DataFrame):
        raise TypeError(
            "training_features must be a pandas DataFrame."
        )

    _validate_dataframe_columns(training_features, "Training data")

    if training_features.empty:
        raise ValueError("Training data cannot be empty.")

    numeric_columns, categorical_columns, columns = (
        _validate_feature_groups(
            numeric_columns,
            categorical_columns,
        )
    )

    missing_columns = [
        c for c in columns if c not in training_features.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Training data is missing columns: {sorted(missing_columns)}"
        )

    scale_numeric = _resolve_scaling(
        model_family, scale_numeric
    )

    pipeline = build_preprocessing_pipeline(
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        scale_numeric=scale_numeric,
    )

    # Fit only on training data.
    pipeline.fit(training_features[columns])

    artifact = {
        "pipeline": pipeline,
        "input_columns": columns,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "scale_numeric": scale_numeric,
        "model_family": model_family,
        "artifact_version": 1,
    }

    artifact_path = Path(artifact_path)
    artifact_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(artifact, artifact_path)

    return artifact


def load_pipeline(artifact_path):
    """Load a saved preprocessing artifact."""

    artifact_path = Path(artifact_path)

    if not artifact_path.is_file():
        raise FileNotFoundError(
            f"Preprocessing artifact not found: {artifact_path}"
        )

    artifact = joblib.load(artifact_path)

    required_keys = {
        "pipeline",
        "input_columns",
        "numeric_columns",
        "categorical_columns",
        "scale_numeric",
    }

    if not isinstance(artifact, dict):
        raise ValueError("Invalid preprocessing artifact.")

    if not required_keys.issubset(artifact.keys()):
        raise ValueError(
            "The saved artifact does not have the expected structure."
        )

    return artifact


def transform_new_data(artifact, new_features):
    """Transform new data without refitting."""

    if not isinstance(new_features, pd.DataFrame):
        raise TypeError(
            "new_features must be a pandas DataFrame."
        )

    _validate_dataframe_columns(new_features, "Input data")

    if not isinstance(artifact, dict):
        raise TypeError("artifact must be a dictionary.")

    required_keys = {"pipeline", "input_columns"}

    if not required_keys.issubset(artifact.keys()):
        raise ValueError(
            "Artifact must contain 'pipeline' and 'input_columns'."
        )

    columns = artifact["input_columns"]

    missing_columns = [
        c for c in columns if c not in new_features.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Input data is missing columns: {sorted(missing_columns)}"
        )

    transformed = artifact["pipeline"].transform(
        new_features[columns]
    )

    feature_names = artifact["pipeline"].get_feature_names_out()

    return pd.DataFrame(
        transformed,
        columns=feature_names,
        index=new_features.index,
    )
