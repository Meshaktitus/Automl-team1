"""Extra facts for the AutoML and preprocessing handoff, built only from the
profiling output (no raw data):

    target_statistics(...)      data type, counts, class distribution or
                                numerical statistics of the target
    preprocessing_hint(...)     a short recommendation per column
    feature_type_counts(...)    how many features of each kind
    missing_summary(...)        columns that have missing values
    time_info(...)              date range and estimated frequency
    validation_warnings(...)    things that may hurt model training

Everything here is a recommendation or an estimate, not a decision. What the
profile cannot tell (for example gaps in a time series) is said so.
"""
import pandas as pd

HIGH_CARDINALITY = 50
SMALL_DATASET_ROWS = 50
IMBALANCE_PCT = 10.0
ONE_HOT_MAX = 15


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(number) else number


def class_distribution(column):
    """Class shares of a target, from the profile. Returns (list, note)."""
    top = column.get("top_values")
    unique = int(column.get("unique_count") or 0)
    if top:
        items = [{"value": str(t["value"]), "count": t["count"],
                  "percentage": t["percentage"]} for t in top]
        note = None
        if unique > len(items):
            note = (f"Top {len(items)} of {unique} values only; "
                    "the profile does not list the rest.")
        return items, note
    summary = column.get("summary") or {}
    mean = _number(summary.get("mean"))
    if (unique == 2 and summary.get("min") == 0 and summary.get("max") == 1
            and mean is not None):
        return [
            {"value": "0", "percentage": round((1 - mean) * 100, 2)},
            {"value": "1", "percentage": round(mean * 100, 2)},
        ], "Derived from the mean of a 0/1 column."
    return None, "Class distribution not available from the profile."


def target_statistics(column, semantic_type, problem_type):
    """Statistics about the target column. column is the profile entry."""
    if column is None:
        return None
    out = {
        "column": column["name"],
        "data_type": column["dtype"],
        "semantic_type": semantic_type,
        "unique_count": column["unique_count"],
        "missing_count": column["missing_count"],
        "missing_pct": column["missing_pct"],
        "class_distribution": None,
        "minority_class_pct": None,
        "numerical_statistics": None,
        "notes": [],
    }
    if str(problem_type).endswith("classification"):
        items, note = class_distribution(column)
        out["class_distribution"] = items
        if note:
            out["notes"].append(note)
        complete = items and not (note and note.startswith("Top "))
        if complete:
            out["minority_class_pct"] = min(i["percentage"] for i in items)
    elif problem_type == "regression" or (column.get("summary") or {}).get(
            "mean") is not None:
        summary = column.get("summary") or {}
        keep = {k: summary[k] for k in ("min", "max", "mean", "median", "std")
                if k in summary}
        out["numerical_statistics"] = keep or None
        if not keep:
            out["notes"].append("Numerical statistics not in the profile.")
    return out


def preprocessing_hint(role, semantic_type, unique, missing_pct, time_axis,
                       problem_type=None):
    """One short preprocessing recommendation for a column."""
    parts = []
    if role == "target":
        if str(problem_type).endswith("classification"):
            return "Target: encode classes as labels; check class balance."
        return "Target: use as the value to predict; check for outliers."
    if role == "identifier":
        return "Do not use as a model input; keep for joining tables."
    if role == "excluded":
        return "Drop; not useful as a model input."
    if role == "text":
        return "Text processing (tokenise or embed), or leave out."
    if role == "time":
        return "Extract hour or part of day."
    if role == "date":
        if time_axis:
            return ("Use as the time index for forecasting; derive lag "
                    "features.")
        return "Turn into age, duration, year or month."
    # features
    if missing_pct and missing_pct > 0:
        parts.append(f"impute missing values ({missing_pct}%)")
    if semantic_type == "boolean_flag":
        parts.append("encode as 0/1")
    elif semantic_type == "categorical":
        if unique is not None and unique > ONE_HOT_MAX:
            parts.append("encode categories (many values: use frequency or "
                         "target encoding, not one-hot)")
        else:
            parts.append("one-hot encode")
    elif semantic_type == "percentage":
        parts.append("convert to a plain number")
        parts.append("scale")
    else:
        parts.append("scale if the model needs it")
    return "; ".join(parts).capitalize() + "."


def feature_type_counts(roles):
    """Counts of recommended feature columns by semantic type group."""
    groups = {"numerical": 0, "categorical": 0, "boolean": 0, "other": 0}
    for entry in roles:
        if entry["role"] != "feature":
            continue
        kind = entry["semantic_type"]
        if kind in {"numerical_measure", "financial_amount", "percentage"}:
            groups["numerical"] += 1
        elif kind == "categorical":
            groups["categorical"] += 1
        elif kind == "boolean_flag":
            groups["boolean"] += 1
        else:
            groups["other"] += 1
    return groups


def missing_summary(roles):
    return [
        {"column": r["column"], "missing_count": r["missing_count"],
         "missing_pct": r["missing_pct"]}
        for r in roles if r["missing_count"]
    ]


def time_info(profile_columns, time_columns):
    """Date range and estimated frequency of each time-axis column."""
    out = []
    for name in time_columns:
        column = profile_columns.get(name)
        if not column:
            continue
        summary = column.get("summary") or {}
        distinct = int(column.get("unique_count") or 0)
        entry = {
            "column": name, "start": summary.get("min"),
            "end": summary.get("max"), "distinct_dates": distinct,
            "estimated_frequency": "unknown",
            "gaps": "Not available from the profile (needs the values).",
        }
        try:
            span = (pd.Timestamp(summary["max"])
                    - pd.Timestamp(summary["min"])).days
        except (KeyError, TypeError, ValueError):
            span = None
        if span is not None and distinct > 1:
            step = span / (distinct - 1)
            for limit, label in ((1.5, "daily"), (8, "weekly"),
                                 (35, "monthly"), (100, "quarterly"),
                                 (380, "yearly")):
                if step <= limit:
                    entry["estimated_frequency"] = label
                    break
            entry["average_spacing_days"] = round(step, 1)
        out.append(entry)
    return out


def validation_warnings(facts, roles, target_stats, problem_type):
    """Things that may hurt training. Warnings, not errors."""
    warnings = []
    features = [r for r in roles if r["role"] == "feature"]
    if problem_type not in {"review_required"} and not features:
        warnings.append("No usable feature columns.")
    elif problem_type != "review_required" and len(features) < 2:
        warnings.append(f"Only {len(features)} usable feature column.")
    if facts.get("row_count", 0) < SMALL_DATASET_ROWS:
        warnings.append(
            f"Small dataset ({facts.get('row_count')} rows); results may be "
            "unreliable.")
    if facts.get("duplicate_row_count"):
        warnings.append(f"{facts['duplicate_row_count']} duplicate rows.")
    if target_stats:
        if target_stats["missing_count"]:
            warnings.append(
                f"Target has {target_stats['missing_pct']}% missing values; "
                "rows without a target cannot be used for supervised "
                "training.")
        minority = target_stats.get("minority_class_pct")
        if minority is not None and minority < IMBALANCE_PCT:
            warnings.append(
                f"Class imbalance: smallest class is {minority}% of the "
                "data.")
    for r in features:
        unique = r.get("unique_values")
        if r["semantic_type"] == "categorical" and unique is not None \
                and unique > HIGH_CARDINALITY:
            warnings.append(
                f"Feature '{r['column']}' has {int(unique)} distinct "
                "values (high cardinality).")
    if any(r["quality_blocked"] for r in features):
        warnings.append(
            "Some features have a blocking quality issue; review them.")
    return warnings
