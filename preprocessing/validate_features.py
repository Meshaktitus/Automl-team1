
def validate_feature_columns(feature_columns, target_column):
    """
    Validate selected model input columns.

    Prevents direct target leakage and rejects invalid feature lists.
    Other leakage risks require separate review.
    """
    if not target_column:
        raise ValueError("Target column must be specified.")

    if isinstance(feature_columns, str):
        raise TypeError(
            "feature_columns must be a list of column names, not a string."
        )

    if not isinstance(feature_columns, list):
        raise TypeError(
            "feature_columns must be a list of column names."
        )

    if not feature_columns:
        raise ValueError("Feature columns must not be empty.")

    if any(not isinstance(column, str) or not column.strip()
           for column in feature_columns):
        raise ValueError(
            "Feature column names must be non-empty strings."
        )

    if len(feature_columns) != len(set(feature_columns)):
        raise ValueError("Duplicate feature columns are not allowed.")

    if target_column in feature_columns:
        raise ValueError(
            f"Target leakage detected: '{target_column}' "
            "must not be included in the input features."
        )

    return True
