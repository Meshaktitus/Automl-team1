"""Target-column suggestions and problem-type recommendations.

Works on any dataset. Input is the semantic report made by analyze_semantics.py
(one row per column). Nothing here is hard-coded to HR data.

Ranking uses: semantic type, cardinality, missing percentage, whether the
column name looks like an outcome (churn, price, default ...), position, and
whether the column is sensitive. All suggestions are proposals. The user can
override the target per dataset (overrides={"dataset.xlsx": "column"}) and the
override always wins.
"""
import argparse
from pathlib import Path

import pandas as pd

from semantic_rules import tokenize

PROJECT_FOLDER = Path(__file__).resolve().parent
DEFAULT_REPORT = PROJECT_FOLDER / "outputs" / "semantic_analysis_report.csv"
DEFAULT_OUTPUT = PROJECT_FOLDER / "outputs" / "target_suggestions.csv"
STATUS = "Proposed, pending verification"

NON_TARGET_TYPES = {
    "identifier", "text", "email", "phone", "time", "date", "unknown",
}
AUDIT_TOKENS = {"modified", "created", "updated", "rowguid"}
# Dates that describe a person or record (not a time axis for forecasting)
ATTRIBUTE_DATE_TOKENS = {
    "birth", "dob", "hire", "hired", "start", "end",
    "join", "joined", "expiry", "expire",
}
TARGET_HINT_TOKENS = {
    "churn", "default", "fraud", "attrition", "outcome", "target", "label",
    "result", "price", "revenue", "salary", "sales", "sold", "risk",
    "diabetes", "survived", "approved", "rejected", "cancelled", "canceled",
    "converted", "conversion", "readmission",
    "readmitted", "readmit", "churned", "defaulted", "dropout", "graduated",
    "passed", "failed", "final",
}
TYPE_BASE = {
    "boolean_flag": 0.80,
    "categorical": 0.70,
    "numerical_measure": 0.70,
    "financial_amount": 0.75,
    "percentage": 0.70,
}
COLUMNS = [
    "dataset", "rank", "candidate_target", "semantic_type",
    "suggested_problem_type", "score", "confidence_level", "priority",
    "reason", "alternative_problem_types", "warnings", "status",
]


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(number) else number


def _truthy(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def _evaluate(row, is_last, time_columns):
    column = str(row["column"])
    semantic_type = str(row["semantic_type"]).lower()
    tokens = set(tokenize(column))
    n_unique = _number(row.get("unique_values"))
    non_null = _number(row.get("non_null_count"))
    row_count = _number(row.get("row_count"))
    sensitive = _truthy(row.get("sensitive", False))

    missing_pct = None
    if non_null is not None and row_count:
        missing_pct = round(100 * (1 - non_null / row_count), 1)

    exclusion = None
    if tokens & AUDIT_TOKENS:
        exclusion = "audit or technical metadata column"
    elif semantic_type in NON_TARGET_TYPES:
        exclusion = f"{semantic_type} columns are not used as targets"
    elif n_unique is not None and n_unique <= 1:
        exclusion = "constant or empty column"
    elif missing_pct is not None and missing_pct >= 80:
        exclusion = f"{missing_pct}% of values are missing"

    warnings = []
    alternatives = []

    if semantic_type == "boolean_flag" or (
        semantic_type == "categorical" and n_unique == 2
    ):
        problem = "binary_classification"
    elif semantic_type == "categorical":
        problem = "multiclass_classification"
    elif semantic_type in {
        "numerical_measure", "financial_amount", "percentage",
    }:
        problem = "regression"
    else:
        problem = "review_required"

    if problem == "regression":
        if n_unique is not None and n_unique <= 10:
            alternatives.append("multiclass_classification")
            warnings.append(
                f"Only {int(n_unique)} distinct values; "
                "classification may fit better"
            )
        if time_columns:
            alternatives.append(
                "forecasting (time column: "
                + ", ".join(time_columns[:2]) + ")"
            )
    if (
        problem == "multiclass_classification"
        and n_unique is not None and n_unique > 20
    ):
        warnings.append(
            f"{int(n_unique)} classes; many classes with few examples "
            "make reliable prediction difficult"
        )
    if problem == "binary_classification":
        warnings.append("Check class balance before training")

    # Score
    base = TYPE_BASE.get(semantic_type, 0.3)
    if problem.endswith("classification"):
        if n_unique is None:
            cardinality = 0.8
        elif n_unique <= 2:
            cardinality = 1.0
        elif n_unique <= 10:
            cardinality = 0.9
        elif n_unique <= 20:
            cardinality = 0.65
        else:
            cardinality = 0.35
    elif problem == "regression":
        if n_unique is None:
            cardinality = 0.8
        elif n_unique <= 5:
            cardinality = 0.5
        elif n_unique <= 10:
            cardinality = 0.75
        else:
            cardinality = 1.0
    else:
        cardinality = 0.5

    missing_factor = 1 - (missing_pct or 0) / 100
    if missing_pct is not None and missing_pct >= 20:
        warnings.append(f"{missing_pct}% missing values")

    sensitive_factor = 1.0
    if sensitive:
        sensitive_factor = 0.5
        warnings.append(
            "Sensitive attribute; review fairness and privacy before use"
        )

    hint = bool(tokens & TARGET_HINT_TOKENS)
    score = base * cardinality * missing_factor * sensitive_factor
    score += 0.15 if hint else 0.0
    score += 0.05 if is_last else 0.0
    score = round(100 * min(max(score, 0.0), 1.0), 1)

    parts = [f"{semantic_type} column"]
    if n_unique is not None:
        parts.append(f"{int(n_unique)} distinct values")
    if missing_pct is not None:
        parts.append(f"{missing_pct}% missing")
    if hint:
        parts.append("column name looks like an outcome")
    reason = (
        "; ".join(parts)
        + ". Confirm that predicting this supports the business objective."
    )

    return {
        "column": column,
        "semantic_type": semantic_type,
        "problem": problem,
        "score": score,
        "hint": hint,
        "reason": reason,
        "alternatives": alternatives,
        "warnings": warnings,
        "exclusion": exclusion,
    }


def suggest_targets(report, overrides=None, max_alternatives=3):
    """Return ranked target candidates for every dataset in the report.

    overrides: optional {dataset_name: column_name}. The chosen column is
    ranked first with priority "User-selected", whatever its score.
    """
    needed = {"dataset", "column", "semantic_type"}
    missing = needed - set(report.columns)
    if missing:
        raise ValueError(f"Report is missing columns: {sorted(missing)}")

    overrides = overrides or {}
    output = []

    for dataset, group in report.groupby("dataset", sort=False):
        group = group.reset_index(drop=True)
        dataset = str(dataset)
        last_index = len(group) - 1

        time_columns = [
            str(r["column"]) for _, r in group.iterrows()
            if str(r["semantic_type"]).lower() == "date"
            and not (
                set(tokenize(str(r["column"])))
                & (AUDIT_TOKENS | ATTRIBUTE_DATE_TOKENS)
            )
        ]
        evaluated = [
            _evaluate(r, i == last_index, time_columns)
            for i, r in group.iterrows()
        ]

        chosen = overrides.get(dataset)
        candidates = []
        chosen_item = None
        for item in evaluated:
            is_chosen = chosen is not None and item["column"] == chosen
            if item["exclusion"] and not is_chosen:
                continue
            if is_chosen:
                chosen_item = item
                if item["exclusion"]:
                    item["warnings"].append(
                        "You selected this column although it is "
                        + item["exclusion"]
                    )
            candidates.append(item)

        if chosen is not None and chosen_item is None:
            chosen_item = {
                "column": str(chosen), "semantic_type": "unknown",
                "problem": "unknown", "score": None, "hint": False,
                "reason": "Column not found in this dataset.",
                "alternatives": [],
                "warnings": [
                    "Selected column not found; check the spelling"
                ],
                "exclusion": None,
            }
            candidates.append(chosen_item)

        candidates.sort(key=lambda c: -(c["score"] or 0))
        if chosen_item is not None:
            candidates.remove(chosen_item)
            candidates.insert(0, chosen_item)

        any_hint = any(c["hint"] for c in candidates)
        top_given = chosen_item is not None
        alt_count = 0

        for rank, item in enumerate(candidates, start=1):
            warnings = list(item["warnings"])
            if item is chosen_item:
                priority, confidence = "User-selected", "User-selected"
            else:
                if item["hint"] and not top_given:
                    priority, top_given = "Top suggestion", True
                elif item["hint"] and alt_count < max_alternatives:
                    priority, alt_count = "Alternative", alt_count + 1
                else:
                    priority = "Candidate"
                if not item["hint"]:
                    confidence = "Low"
                elif item["score"] >= 75:
                    confidence = "High"
                elif item["score"] >= 50:
                    confidence = "Medium"
                else:
                    confidence = "Low"
            if not any_hint and item is not chosen_item:
                warnings.append(
                    "No column clearly looks like an outcome; "
                    "confirm the business objective"
                )
            output.append({
                "dataset": dataset,
                "rank": rank,
                "candidate_target": item["column"],
                "semantic_type": item["semantic_type"],
                "suggested_problem_type": item["problem"],
                "score": item["score"],
                "confidence_level": confidence,
                "priority": priority,
                "reason": item["reason"],
                "alternative_problem_types": "; ".join(item["alternatives"]),
                "warnings": "; ".join(warnings),
                "status": STATUS,
            })

        usable = [e for e in evaluated if not e["exclusion"]]
        if len(usable) >= 3:
            output.append({
                "dataset": dataset,
                "rank": None,
                "candidate_target": "(no target)",
                "semantic_type": "n/a",
                "suggested_problem_type": "clustering",
                "score": None,
                "confidence_level": "Low" if any_hint else "Medium",
                "priority": "Alternative",
                "reason": (
                    "Use this if the goal is to group similar records "
                    "instead of predicting a value. No target is needed."
                ),
                "alternative_problem_types": "",
                "warnings": "",
                "status": STATUS,
            })

    frame = pd.DataFrame(output, columns=COLUMNS)
    frame["rank"] = frame["rank"].astype("Int64")
    return frame


def main():
    parser = argparse.ArgumentParser(description="Suggest target columns.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--override", action="append", default=[],
        metavar="DATASET=COLUMN",
        help="Force the target for a dataset (can be repeated)",
    )
    args = parser.parse_args()

    report_file = Path(args.report)
    if not report_file.exists():
        print("Semantic report not found.")
        print("Run: python analyze_semantics.py")
        return

    overrides = {}
    for item in args.override:
        dataset, _, column = item.partition("=")
        overrides[dataset] = column

    suggestions = suggest_targets(pd.read_csv(report_file), overrides)
    if suggestions.empty:
        print("No candidate targets found.")
        return

    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    suggestions.to_csv(output_file, index=False)

    print("\n===== TARGET VARIABLE SUGGESTIONS =====")
    print(suggestions[[
        "dataset", "rank", "candidate_target", "suggested_problem_type",
        "score", "confidence_level", "priority",
    ]].to_string(index=False))
    print(f"\nSaved to: {output_file}")
    print("Status: Proposed, pending verification")
    print("All suggestions need business review; overrides always win.")


if __name__ == "__main__":
    main()
