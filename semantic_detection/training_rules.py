"""Training-eligibility rules (contract section 12.2, PROPOSED).

A small reference implementation for consumers (AutoML, backend, frontend).
It only reads fields of one result. It never trains and never changes data.
Status: Proposed. Not approved until Sumanth and Meshak confirm section 12.2.
"""

SUPERVISED = {"binary_classification", "multiclass_classification",
              "regression", "forecasting"}
UNSUPERVISED = {"clustering", "anomaly_detection", "recommendation"}


def training_blockers(result):
    """Return the list of reasons why supervised/model training may NOT
    start yet. An empty list means the rules of section 12.2 are met.
    Profiling and data-quality analysis are always allowed."""
    reasons = []
    problem = result.get("problem_type")
    if problem == "review_required" or problem not in SUPERVISED | UNSUPERVISED:
        return ["problem type is review_required: a person must choose a "
                "target or a problem type and the module must run again"]
    if result.get("needs_confirmation"):
        reasons.append("problem type is not confirmed (needs_confirmation)")
    if problem in SUPERVISED:
        if not result.get("target"):
            reasons.append("no target column")
        if not result.get("target_confirmed"):
            reasons.append("target is not confirmed by the user")
    if result.get("features_status") != "approved" \
            or result.get("approved_feature_columns") is None:
        reasons.append("features are not approved by the user")
    elif not result["approved_feature_columns"]:
        reasons.append("the approved feature list is empty")
    if problem == "forecasting" and not any(
            r.get("time_axis") for r in result.get("column_roles", [])):
        reasons.append("forecasting needs a date column with time_axis true")
    return reasons


def can_start_training(result):
    return not training_blockers(result)
