"""Problem-type recommendation.

detect_problem(report, dataset, target=None, business_goal=None,
               problem_type_override=None) returns a dict with:
    problem_type, confidence, source, needs_confirmation,
    evidence, alternatives, warnings, status

Precedence (highest first):
    1. problem_type_override   - the user's choice, always wins
    2. business_goal           - words such as "forecast", "segment"
    3. data rules              - target type, cardinality, time column

Nothing is final: unless the user overrides or states a goal that fits the
data, needs_confirmation stays True (the project owner confirms the
business objective).
"""
import argparse
from pathlib import Path

import pandas as pd

from semantic_rules import tokenize

PROJECT_FOLDER = Path(__file__).resolve().parent
DEFAULT_REPORT = PROJECT_FOLDER / "outputs" / "semantic_analysis_report.csv"
DEFAULT_OUTPUT = PROJECT_FOLDER / "outputs" / "problem_type_recommendations.csv"
STATUS = "Proposed, pending verification"

SUPPORTED_PROBLEM_TYPES = [
    "binary_classification", "multiclass_classification", "regression",
    "forecasting", "clustering", "anomaly_detection", "recommendation",
]
AUDIT_TOKENS = {"modified", "created", "updated", "rowguid"}
# Dates that describe a person or record (not a time axis for forecasting)
ATTRIBUTE_DATE_TOKENS = {
    "birth", "dob", "hire", "hired", "start", "end",
    "join", "joined", "expiry", "expire",
}
NON_FEATURE_TYPES = {
    "identifier", "text", "email", "phone", "time", "date", "unknown",
}
NUMERIC_TYPES = {"numerical_measure", "financial_amount", "percentage"}

GOAL_KEYWORDS = {
    "forecasting": (
        "forecast", "next month", "next quarter", "next year", "next week",
        "future", "projection",
    ),
    "clustering": (
        "segment", "cluster", "group similar", "grouping",
        "similar customers", "similar employees", "similar records",
    ),
    "anomaly_detection": (
        "anomal", "unusual", "outlier", "abnormal", "suspicious",
    ),
    "recommendation": ("recommend", "suggest products", "suggest items"),
    "classification": (
        "classify", "likely to", "will leave", "will churn", "churn",
        "whether", "yes or no",
    ),
    "regression": (
        "how much", "estimate", "predict the amount", "predict the price",
        "predict the value",
    ),
}
GOAL_CONFIDENCE = {
    "forecasting": 0.90, "clustering": 0.85,
    "anomaly_detection": 0.80, "recommendation": 0.75,
}


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(number) else number


def _truthy(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def base_problem_type(semantic_type, n_unique):
    """Problem type implied by the target column alone."""
    if semantic_type == "boolean_flag" or (
        semantic_type == "categorical" and n_unique == 2
    ):
        return "binary_classification"
    if semantic_type == "categorical":
        return "multiclass_classification"
    if semantic_type in NUMERIC_TYPES:
        return "regression"
    return "review_required"


def time_column_info(group, min_unique=6):
    """Date columns that can act as a time axis: [(column, distinct_dates)]."""
    found = []
    for _, row in group.iterrows():
        if str(row["semantic_type"]).lower() != "date":
            continue
        column = str(row["column"])
        if set(tokenize(column)) & (AUDIT_TOKENS | ATTRIBUTE_DATE_TOKENS):
            continue
        n_unique = _number(row.get("unique_values"))
        if n_unique is not None and n_unique < min_unique:
            continue
        found.append((column, n_unique))
    return found


def find_time_columns(group, min_unique=6):
    return [name for name, _ in time_column_info(group, min_unique)]


def count_columns(group, target=None):
    """Return (usable features, numeric features, identifier columns)."""
    features = numeric = ids = 0
    for _, row in group.iterrows():
        column = str(row["column"])
        semantic_type = str(row["semantic_type"]).lower()
        if set(tokenize(column)) & AUDIT_TOKENS:
            continue
        if semantic_type == "identifier":
            ids += 1
            continue
        if semantic_type in NON_FEATURE_TYPES:
            continue
        n_unique = _number(row.get("unique_values"))
        if n_unique is not None and n_unique <= 1:
            continue
        if target is not None and column == str(target):
            continue
        features += 1
        if semantic_type in NUMERIC_TYPES:
            numeric += 1
    return features, numeric, ids


def _goal_hits(business_goal):
    text = str(business_goal or "").lower()
    hits = {}
    for category, words in GOAL_KEYWORDS.items():
        matched = [word for word in words if word in text]
        if matched:
            hits[category] = matched
    return hits


def _target_info(group, target):
    rows = group[group["column"].astype(str) == str(target)]
    if rows.empty:
        return None
    row = rows.iloc[0]
    semantic_type = str(row["semantic_type"]).lower()
    n_unique = _number(row.get("unique_values"))
    return {
        "column": str(row["column"]),
        "semantic_type": semantic_type,
        "n_unique": n_unique,
        "problem": base_problem_type(semantic_type, n_unique),
        "sensitive": _truthy(row.get("sensitive", False)),
    }


def _feasibility(problem, info, time_cols, n_features, n_numeric, n_ids):
    """Reasons why a problem type cannot work on this dataset."""
    reasons = []
    if problem == "forecasting":
        if not time_cols:
            reasons.append("no usable time column (a date column that is "
                           "not a birth/hire/start/end date)")
        if info is None or info["problem"] != "regression":
            reasons.append("forecasting needs a numeric target")
    elif problem == "clustering":
        if n_features < 3:
            reasons.append(f"only {n_features} usable feature columns; "
                           "clustering needs at least 3")
    elif problem == "anomaly_detection":
        if n_numeric < 2:
            reasons.append("anomaly detection needs at least 2 numeric "
                           "columns")
    elif problem == "recommendation":
        if n_ids < 2 or n_numeric < 1:
            reasons.append("recommendation needs two ID columns (for "
                           "example user and item) and a numeric rating "
                           "or amount")
    elif problem.endswith("classification") or problem == "regression":
        if info is None:
            reasons.append("a target column is needed")
    return reasons


def detect_problem(report, dataset, target=None, business_goal=None,
                   problem_type_override=None):
    out = {
        "dataset": dataset, "target": target,
        "problem_type": "review_required", "confidence": 0.0,
        "source": "data_rules", "needs_confirmation": True,
        "evidence": [], "alternatives": [], "warnings": [],
        "status": STATUS,
    }
    evidence, alternatives, warnings = [], [], []

    def add_alt(problem, reason):
        if all(a["problem_type"] != problem for a in alternatives):
            alternatives.append({"problem_type": problem, "reason": reason})

    def finish():
        out["evidence"] = evidence
        out["alternatives"] = [
            a for a in alternatives if a["problem_type"] != out["problem_type"]
        ]
        out["warnings"] = warnings
        ceiling = 1.0 if out["source"] == "user_override" else 0.95
        out["confidence"] = round(min(max(out["confidence"], 0.0), ceiling), 2)
        return out

    group = report[report["dataset"].astype(str) == str(dataset)]
    if group.empty:
        warnings.append(f"Dataset '{dataset}' not found in the report")
        return finish()

    time_info = time_column_info(group)
    time_cols = [name for name, _ in time_info]
    n_features, n_numeric, n_ids = count_columns(group, target)
    info = _target_info(group, target) if target else None
    if target and info is None:
        warnings.append(f"Target '{target}' not found in this dataset")

    # 1. User override always wins
    if problem_type_override:
        choice = str(problem_type_override).strip().lower()
        if choice not in SUPPORTED_PROBLEM_TYPES:
            warnings.append(
                f"Unsupported problem type '{problem_type_override}'; "
                "supported: " + ", ".join(SUPPORTED_PROBLEM_TYPES)
            )
            return finish()
        out.update(problem_type=choice, confidence=1.0,
                   source="user_override", needs_confirmation=False)
        evidence.append("Problem type selected by the user.")
        for reason in _feasibility(choice, info, time_cols, n_features,
                                   n_numeric, n_ids):
            warnings.append(f"Selected type may not fit: {reason}")
        return finish()

    # 2. Business goal wording
    hits = _goal_hits(business_goal)
    groups = {
        "supervised" if c in {"classification", "regression"} else c
        for c in hits
    }
    goal_ambiguous = len(groups) > 1
    goal_type = None
    if goal_ambiguous:
        warnings.append(
            "Goal mentions several task types ("
            + ", ".join(sorted(groups))
            + "); confirm which one you want"
        )
        for name in sorted(groups):
            if name != "supervised":
                add_alt(name, "Mentioned in the business goal")
    elif groups:
        goal_type = next(iter(groups))
        if goal_type == "supervised":
            goal_type = "classification" if "classification" in hits \
                else "regression"

    if goal_type in GOAL_CONFIDENCE:
        reasons = _feasibility(goal_type, info, time_cols, n_features,
                               n_numeric, n_ids)
        keyword = hits[goal_type][0]
        if not reasons:
            out.update(problem_type=goal_type,
                       confidence=GOAL_CONFIDENCE[goal_type],
                       source="business_goal", needs_confirmation=False)
            evidence.append(f"Business goal mentions '{keyword}'.")
            if goal_type == "forecasting":
                name, distinct = time_info[0]
                detail = f" ({int(distinct)} distinct dates)" if distinct \
                    else ""
                evidence.append(f"Time column '{name}'{detail}; numeric "
                                f"target '{info['column']}'.")
                add_alt("regression", "Use if the time order does not matter")
            elif goal_type == "clustering":
                evidence.append(f"{n_features} usable feature columns; "
                                "no target needed.")
            elif goal_type == "anomaly_detection":
                evidence.append(f"{n_numeric} numeric columns available.")
            else:
                evidence.append(f"{n_ids} ID columns and {n_numeric} "
                                "numeric column(s) found.")
            return finish()
        warnings.append(
            f"Goal mentions '{keyword}' ({goal_type}) but it does not fit "
            "this data: " + "; ".join(reasons)
        )

    # 3. Data rules
    confidence = 0.3
    agrees = False
    if info is None:
        evidence.append("No target column selected.")
        if n_features >= 3:
            add_alt("clustering", "Works without a target "
                    f"({n_features} usable feature columns)")
    else:
        problem = info["problem"]
        out["problem_type"] = problem
        n_unique = info["n_unique"]
        distinct = f"{int(n_unique)} distinct values" if n_unique is not None \
            else "unknown number of distinct values"
        evidence.append(f"Target '{info['column']}' is "
                        f"{info['semantic_type']} with {distinct}.")
        if problem.endswith("classification"):
            confidence = 0.85
            if n_unique is not None and n_unique > 20:
                confidence = 0.60
                warnings.append(f"{int(n_unique)} classes; many classes with "
                                "few examples make prediction unreliable")
        elif problem == "regression":
            confidence = 0.80
            if n_unique is not None and n_unique <= 10:
                confidence = 0.55
                warnings.append(f"Only {int(n_unique)} distinct values; "
                                "classification may fit better")
                add_alt("multiclass_classification",
                        "Target has few distinct values")
            if time_cols:
                add_alt("forecasting",
                        "Time column present: " + ", ".join(time_cols[:2]))
        else:
            warnings.append(f"Target type '{info['semantic_type']}' cannot "
                            "be predicted directly; pick another column")
        if info["sensitive"]:
            warnings.append("Target is a sensitive attribute; review "
                            "fairness and privacy")

        if goal_type == "classification":
            if problem.endswith("classification"):
                confidence += 0.10
                agrees = True
                evidence.append("Business goal wording fits classification.")
            elif problem == "regression":
                confidence -= 0.20
                warnings.append("Goal sounds like classification but the "
                                "target is numeric")
                add_alt("multiclass_classification",
                        "Goal sounds like classification")
        elif goal_type == "regression":
            if problem == "regression":
                confidence += 0.10
                agrees = True
                evidence.append("Business goal wording fits regression.")
            elif problem.endswith("classification"):
                confidence -= 0.20
                warnings.append("Goal sounds like a numeric estimate but "
                                "the target is categorical")
                add_alt("regression", "Goal sounds like a numeric estimate")

    if goal_ambiguous:
        confidence = min(confidence, 0.50)
        agrees = False
    out["confidence"] = confidence
    out["needs_confirmation"] = not agrees
    return finish()


def main():
    parser = argparse.ArgumentParser(description="Recommend problem types.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--dataset", help="Only this dataset")
    parser.add_argument("--target", help="Target column (needs --dataset)")
    parser.add_argument("--goal", help="Business goal in plain words")
    parser.add_argument("--problem-type",
                        help="Override: " + ", ".join(SUPPORTED_PROBLEM_TYPES))
    args = parser.parse_args()

    report_file = Path(args.report)
    if not report_file.exists():
        print("Semantic report not found.")
        print("Run: python analyze_semantics.py")
        return
    if args.target and not args.dataset:
        print("--target needs --dataset (say which file it belongs to).")
        return

    report = pd.read_csv(report_file)
    datasets = [args.dataset] if args.dataset \
        else list(report["dataset"].astype(str).unique())

    from target_suggestions import suggest_targets
    tops = {}
    if not args.target:
        suggestions = suggest_targets(report)
        for _, row in suggestions.iterrows():
            if row["priority"] == "Top suggestion":
                tops[row["dataset"]] = row["candidate_target"]

    rows = []
    for dataset in datasets:
        target = args.target or tops.get(dataset)
        result = detect_problem(report, dataset, target, args.goal,
                                args.problem_type)
        rows.append({
            "dataset": dataset,
            "target": target or "",
            "problem_type": result["problem_type"],
            "confidence": result["confidence"],
            "source": result["source"],
            "needs_confirmation": result["needs_confirmation"],
            "evidence": "; ".join(result["evidence"]),
            "alternatives": "; ".join(
                f"{a['problem_type']} ({a['reason']})"
                for a in result["alternatives"]),
            "warnings": "; ".join(result["warnings"]),
            "status": result["status"],
        })

    frame = pd.DataFrame(rows)
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_file, index=False)

    print("\n===== PROBLEM TYPE RECOMMENDATIONS =====")
    print(frame[["dataset", "target", "problem_type", "confidence",
                 "source", "needs_confirmation"]].to_string(index=False))
    print(f"\nSaved to: {output_file}")
    print("Status: Proposed, pending verification")


if __name__ == "__main__":
    main()
