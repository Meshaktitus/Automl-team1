
from pathlib import Path
import re

import pandas as pd
from sklearn.preprocessing import StandardScaler

from app.preprocessing.preprocessing_contracts import (
    ContractValidationError,
    validate_preprocessing_request,
    validate_preprocessing_response,
)


SUPPORTED_INPUTS = {"csv", "xlsx", "parquet"}


def _is_identifier(column_name):
    """Identify likely record, account, or technical identifier columns."""
    name = str(column_name).strip().lower()
    compact_name = re.sub(r"[^a-z0-9]", "", name)

    return (
        name in {"id", "rowguid", "guid", "username"}
        or name.endswith("_id")
        or name.endswith("guid")
        or name.endswith("number")
        or compact_name.endswith("entityid")
        or compact_name in {"loginid", "userid"}
    )


def _safe_name(value):
    """Convert a dataset ID into a safe filename component."""
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value))
    return value.strip("._") or "dataset"


def _load_dataset(dataset):
    """Load a dataset from a supported file format."""
    file_format = str(dataset.get("format", "")).lower()
    location = dataset.get("location")

    if file_format not in SUPPORTED_INPUTS:
        raise ValueError(
            f"Unsupported input format: {file_format}. "
            f"Supported formats: {sorted(SUPPORTED_INPUTS)}"
        )

    if not location:
        raise ValueError("Dataset location is required.")

    path = Path(location)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    if file_format == "csv":
        result = pd.read_csv(path)
    elif file_format == "xlsx":
        result = pd.read_excel(path)
    else:
        result = pd.read_parquet(path)

    if result.empty:
        raise ValueError("The input dataset is empty.")

    if result.columns.duplicated().any():
        raise ValueError(
            "The input dataset contains duplicate column names."
        )

    return result


def _build_response(
    request_id,
    status,
    prepared_dataset=None,
    transformation_steps=None,
    feature_list=None,
    warnings=None,
    error=None,
):
    """Build a consistent response object."""
    return {
        "request_id": request_id,
        "status": status,
        "error": error,
        "prepared_dataset": prepared_dataset,
        "transformation_steps": transformation_steps or [],
        "feature_list": feature_list or [],
        "warnings": warnings or [],
    }


def _failed_response(
    request_id,
    code,
    message,
    steps=None,
    warnings=None,
):
    """Build a structured error response."""
    return _build_response(
        request_id=request_id,
        status="failed",
        transformation_steps=steps,
        warnings=warnings,
        error={"code": code, "message": message},
    )


def _quality_rule_message(rule):
    """Convert a quality finding into a readable message."""
    description = rule.get("description") or (
        "Review the reported data-quality finding."
    )
    column = rule.get("column")
    category = rule.get("category", "data_quality")
    rule_id = rule.get("rule_id")

    parts = []

    if rule_id:
        parts.append(f"Rule: {rule_id}")

    if column:
        parts.append(f"Column: {column}")

    parts.append(str(description))

    if rule.get("affected_rows") is not None:
        parts.append(f"Affected rows: {rule['affected_rows']}")

    if rule.get("recommended_action"):
        parts.append(
            f"Recommended action: {rule['recommended_action']}"
        )

    if not rule_id and not column:
        parts.insert(0, str(category))

    return " | ".join(parts)


def _collect_quality_rules(request):
    """Collect quality rules from supported request fields."""
    rules = []

    findings = request.get("quality_findings", [])

    if isinstance(findings, list):
        for rule in findings:
            if isinstance(rule, dict):
                rules.append(rule)

    quality_result = request.get("data_quality_result", {})

    if isinstance(quality_result, dict):
        evaluated = quality_result.get(
            "quality_rules_evaluated", []
        )

        if isinstance(evaluated, list):
            for rule in evaluated:
                if isinstance(rule, dict):
                    rules.append(rule)

    return rules


def _normalise_severity(rule):
    """Convert severity labels to response values."""
    severity = str(
        rule.get("severity", "warning")
    ).strip().lower()

    mapping = {
        "informational": "info",
        "low": "info",
        "medium": "warning",
        "high": "warning",
        "critical": "error",
        "blocking": "error",
        "error": "error",
        "warning": "warning",
        "info": "info",
    }

    return mapping.get(severity, severity or "warning")


def _quality_warnings(request):
    """Convert non-blocking quality findings into warnings."""
    warnings = []

    for rule in _collect_quality_rules(request):
        raw_severity = str(
            rule.get("severity", "")
        ).strip().lower()

        if raw_severity in {"critical", "blocking"}:
            continue

        code = (
            rule.get("rule_id")
            or (
                "INPUT_QUALITY_"
                + str(rule.get("category", "data_quality")).upper()
                if rule.get("category")
                else "DATA_QUALITY_WARNING"
            )
        )

        warnings.append({
            "code": code,
            "severity": _normalise_severity(rule),
            "message": _quality_rule_message(rule),
        })

    return warnings


def _blocking_quality_rules(request):
    """Return rules that explicitly block preprocessing."""
    blocking = []

    for rule in _collect_quality_rules(request):
        severity = str(
            rule.get("severity", "")
        ).strip().lower()

        if severity in {"critical", "blocking"}:
            blocking.append(rule)

    return blocking


def _transformation_step(
    step,
    status,
    affected_columns=None,
    parameters=None,
    message="",
):
    """Create a structured transformation log entry."""
    return {
        "step": step,
        "status": status,
        "affected_columns": affected_columns or [],
        "parameters": parameters or {},
        "message": message,
    }


def _record_failed_step(steps, step_name, error):
    """Record a failed preprocessing step without duplicating it."""
    if any(
        item.get("step") == step_name
        and item.get("status") == "failed"
        for item in steps
    ):
        return

    steps.append(_transformation_step(
        step_name,
        "failed",
        affected_columns=[],
        parameters={},
        message=str(error),
    ))


def _handle_missing_values(result, target):
    """Impute missing feature values without modifying the target."""
    result = result.copy()
    affected = []
    skipped_datetime = []

    for col in result.columns:
        if col == target:
            continue

        if not result[col].isna().any():
            continue

        if pd.api.types.is_datetime64_any_dtype(result[col]):
            skipped_datetime.append(col)
            continue

        if (
            pd.api.types.is_numeric_dtype(result[col])
            and not pd.api.types.is_bool_dtype(result[col])
        ):
            median = result[col].median()
            fill_value = 0 if pd.isna(median) else median
        else:
            mode = result[col].mode(dropna=True)
            fill_value = (
                mode.iloc[0] if not mode.empty else "Unknown"
            )

        result[col] = result[col].fillna(fill_value)
        affected.append(col)

    return result, affected, skipped_datetime


def _extract_date_features(result, target):
    """Extract year, month, quarter, and weekday features."""
    result = result.copy()
    affected = []
    generated = []

    for col in list(result.columns):
        if col == target:
            continue

        if not pd.api.types.is_datetime64_any_dtype(result[col]):
            continue

        if _is_identifier(col):
            continue

        result[f"{col}_year"] = result[col].dt.year
        result[f"{col}_month"] = result[col].dt.month
        result[f"{col}_quarter"] = result[col].dt.quarter
        result[f"{col}_dayofweek"] = result[col].dt.dayofweek

        affected.append(col)
        generated.extend([
            f"{col}_year",
            f"{col}_month",
            f"{col}_quarter",
            f"{col}_dayofweek",
        ])

    if generated:
        result = result.drop(columns=affected)

    return result, affected, generated


def _encode_categorical_features(result, target, options):
    """One-hot encode categorical features, excluding IDs and target."""
    result = result.copy()
    threshold = float(
        options.get("rare_category_threshold", 0.05)
    )

    if not 0 <= threshold <= 1:
        raise ValueError(
            "rare_category_threshold must be between 0 and 1."
        )

    categorical_columns = []
    excluded_identifiers = []
    rare_categories_grouped = {}

    for col in result.columns:
        if col == target:
            continue

        if _is_identifier(col):
            excluded_identifiers.append(col)
            continue

        if (
            pd.api.types.is_object_dtype(result[col])
            or isinstance(result[col].dtype, pd.CategoricalDtype)
            or pd.api.types.is_string_dtype(result[col])
        ):
            categorical_columns.append(col)

    if not categorical_columns:
        return result, [], {
            "method": "one_hot_encoding",
            "excluded_identifier_columns": excluded_identifiers,
            "rare_category_threshold": threshold,
            "rare_categories_grouped": rare_categories_grouped,
            "target_modified": False,
        }

    for col in categorical_columns:
        values = result[col].dropna()

        if values.empty:
            continue

        frequencies = values.value_counts(normalize=True)
        rare_categories = frequencies[
            frequencies < threshold
        ].index.tolist()

        if rare_categories:
            result[col] = result[col].where(
                result[col].isna()
                | ~result[col].isin(rare_categories),
                "Other",
            )

            rare_categories_grouped[col] = [
                str(value) for value in rare_categories
            ]

    result = pd.get_dummies(
        result,
        columns=categorical_columns,
        dummy_na=False,
        dtype=int,
    )

    parameters = {
        "method": "one_hot_encoding",
        "excluded_identifier_columns": excluded_identifiers,
        "rare_category_threshold": threshold,
        "rare_categories_grouped": rare_categories_grouped,
        "target_modified": False,
    }

    return result, categorical_columns, parameters


def _scale_numeric_features(result, target):
    """Standardize numeric features, excluding target and identifiers."""
    result = result.copy()
    numeric_columns = []

    for col in result.columns:
        if col == target or _is_identifier(col):
            continue

        if (
            pd.api.types.is_numeric_dtype(result[col])
            and not pd.api.types.is_bool_dtype(result[col])
        ):
            numeric_columns.append(col)

    if numeric_columns:
        scaler = StandardScaler()
        result[numeric_columns] = scaler.fit_transform(
            result[numeric_columns]
        )

    return result, numeric_columns


def preprocess_request(request):
    """Validate, preprocess, and return a structured response."""
    request_id = (
        request.get("request_id", "unknown-request")
        if isinstance(request, dict)
        else "unknown-request"
    )

    steps = []
    warnings = []
    active_step = "validate_request"

    if not isinstance(request, dict):
        return _failed_response(
            request_id,
            "INVALID_REQUEST",
            "The request must be a JSON object.",
        )

    try:
        validate_preprocessing_request(request)
    except ContractValidationError as exc:
        return _failed_response(
            request_id,
            "INVALID_REQUEST",
            str(exc),
        )
    except (FileNotFoundError, ValueError) as exc:
        return _failed_response(
            request_id,
            "CONTRACT_VALIDATION_ERROR",
            str(exc),
        )

    warnings = _quality_warnings(request)

    try:
        dataset = request.get("dataset")
        options = request.get("preprocessing_options", {})
        target = request.get("target")

        active_step = "check_data_quality"
        blocking_rules = _blocking_quality_rules(request)

        if blocking_rules:
            return _failed_response(
                request_id,
                "QUALITY_BLOCKING_ISSUE",
                "Preprocessing stopped because blocking quality findings were supplied.",
                steps,
                warnings,
            )

        active_step = "load_and_validate_dataset"
        result = _load_dataset(dataset)
        original = result.copy(deep=True)

        if target is not None and target not in result.columns:
            raise ValueError(
                f"Target column not found in dataset: {target}"
            )

        original_columns = result.columns.tolist()

        steps.append(_transformation_step(
            "load_and_validate_dataset",
            "applied",
            affected_columns=original_columns,
            parameters={"input_format": dataset.get("format")},
            message="Dataset loaded and validated successfully.",
        ))

        # Missing-value handling
        active_step = "handle_missing_values"

        if options.get("handle_missing_values", True):
            result, affected, skipped_datetime = (
                _handle_missing_values(result, target)
            )

            message = (
                "Missing values imputed in feature columns. "
                "The target column was not modified."
                if affected
                else "No eligible feature columns required imputation."
            )

            if skipped_datetime:
                message += (
                    " Missing values in datetime columns were left unchanged."
                )

            steps.append(_transformation_step(
                "handle_missing_values",
                "applied" if affected else "skipped",
                affected_columns=affected,
                parameters={
                    "numeric_strategy": "median",
                    "categorical_strategy": "most_frequent",
                    "all_missing_numeric_fallback": 0,
                    "all_missing_categorical_fallback": "Unknown",
                    "target_modified": False,
                    "skipped_datetime_columns": skipped_datetime,
                },
                message=message,
            ))
        else:
            steps.append(_transformation_step(
                "handle_missing_values",
                "skipped",
                parameters={"enabled": False},
                message=(
                    "Skipped because handle_missing_values is disabled "
                    "in the request."
                ),
            ))

        # Date feature extraction
        active_step = "extract_date_features"

        if options.get("extract_date_features", False):
            result, affected, generated = _extract_date_features(
                result, target
            )

            steps.append(_transformation_step(
                "extract_date_features",
                "applied" if generated else "skipped",
                affected_columns=affected,
                parameters={
                    "enabled": True,
                    "generated_columns": generated,
                    "features": [
                        "year", "month", "quarter", "dayofweek"
                    ],
                },
                message=(
                    "Date features extracted."
                    if generated
                    else "No eligible datetime columns were found."
                ),
            ))
        else:
            steps.append(_transformation_step(
                "extract_date_features",
                "skipped",
                parameters={"enabled": False},
                message=(
                    "Skipped because extract_date_features is disabled "
                    "in the request."
                ),
            ))

        # Categorical encoding
        active_step = "encode_categorical"

        if options.get("encode_categorical", True):
            result, affected, parameters = (
                _encode_categorical_features(result, target, options)
            )

            steps.append(_transformation_step(
                "encode_categorical",
                "applied" if affected else "skipped",
                affected_columns=affected,
                parameters=parameters,
                message=(
                    "Categorical features one-hot encoded. "
                    "Identifier columns and the target were excluded."
                    if affected
                    else "No eligible categorical columns required encoding."
                ),
            ))
        else:
            steps.append(_transformation_step(
                "encode_categorical",
                "skipped",
                parameters={"enabled": False},
                message=(
                    "Skipped because encode_categorical is disabled "
                    "in the request."
                ),
            ))

        # Numeric scaling
        active_step = "scale_numeric"

        if options.get("scale_numeric", False):
            result, affected = _scale_numeric_features(result, target)

            steps.append(_transformation_step(
                "scale_numeric",
                "applied" if affected else "skipped",
                affected_columns=affected,
                parameters={
                    "enabled": True,
                    "method": "StandardScaler",
                    "target_modified": False,
                },
                message=(
                    "Numeric feature columns standardized."
                    if affected
                    else "No eligible numeric columns required scaling."
                ),
            ))
        else:
            steps.append(_transformation_step(
                "scale_numeric",
                "skipped",
                parameters={"enabled": False},
                message=(
                    "Skipped because scale_numeric is disabled "
                    "in the request."
                ),
            ))

        # Validate row count
        active_step = "validate_preprocessed_data"

        if len(result) != len(original):
            raise ValueError(
                "Preprocessing unexpectedly changed the row count."
            )

        # Validate target values and dtype
        if target is not None:
            if not result[target].equals(original[target]):
                raise ValueError(
                    "The target column was unexpectedly modified."
                )

        # Save the processed dataset without overwriting the original
        active_step = "save_preprocessed_dataset"

        output_dir = Path("data/processed")
        output_dir.mkdir(parents=True, exist_ok=True)

        dataset_id = dataset.get("dataset_id", "dataset")
        output_path = (
            output_dir / f"{_safe_name(dataset_id)}_preprocessed.csv"
        )

        result.to_csv(output_path, index=False)

        # Build feature metadata
        active_step = "build_feature_metadata"
        feature_list = []

        for col in result.columns:
            if col == target:
                role = "target"
            elif _is_identifier(col):
                role = "identifier"
            else:
                role = "feature"

            feature_list.append({
                "name": str(col),
                "data_type": str(result[col].dtype),
                "role": role,
            })

        if target is None:
            warnings.append({
                "code": "TARGET_NOT_CONFIRMED",
                "severity": "warning",
                "message": "No target column was specified.",
            })

        status = "success" if target else "review_required"

        prepared_dataset = {
            "dataset_id": dataset_id,
            "format": "csv",
            "location": str(output_path),
            "row_count": len(result),
            "column_count": len(result.columns),
        }

        response = _build_response(
            request_id=request_id,
            status=status,
            prepared_dataset=prepared_dataset,
            transformation_steps=steps,
            feature_list=feature_list,
            warnings=warnings,
        )

        # Validate response against the response schema
        active_step = "validate_preprocessing_response"

        try:
            validate_preprocessing_response(response)
        except (
            ContractValidationError,
            FileNotFoundError,
            ValueError,
        ) as exc:
            _record_failed_step(steps, active_step, exc)
            return _failed_response(
                request_id,
                "INVALID_RESPONSE",
                str(exc),
                steps,
                warnings,
            )

        return response

    except FileNotFoundError as exc:
        _record_failed_step(steps, active_step, exc)
        return _failed_response(
            request_id,
            "DATASET_NOT_FOUND",
            str(exc),
            steps,
            warnings,
        )

    except (ValueError, TypeError, KeyError) as exc:
        _record_failed_step(steps, active_step, exc)
        return _failed_response(
            request_id,
            "PREPROCESSING_ERROR",
            str(exc),
            steps,
            warnings,
        )

    except Exception as exc:
        _record_failed_step(steps, active_step, exc)
        return _failed_response(
            request_id,
            "INTERNAL_PREPROCESSING_ERROR",
            str(exc),
            steps,
            warnings,
        )
