"""One run: profiling output (+ quality output) -> semantic types ->
ranked target suggestions -> problem-type recommendation, per dataset.

    from run_detection import run_detection
    results = run_detection(
        profiles=["Employee.profile.json", ...],      # paths or loaded dicts
        quality="quality_report.json",                # optional
        goal="Forecast sales next month",             # optional, plain words
        overrides={"sales.xlsx": "units_sold"},       # optional, per dataset
        problem_type_override=None,                   # optional, always wins
    )

Each result (one per dataset) has: dataset, target, target_source
(user_override / top_suggestion / none), problem_type, confidence, source,
needs_confirmation, evidence, alternatives, warnings, candidates (ranked),
semantic_columns, dataset_characteristics, feature_columns, column_roles,
leakage_checks, status. Everything is a recommendation with evidence; nothing
is final until the user confirms.

For one dataset per call use detect_dataset(profile, ...), which returns a
single result instead of a list.

Command line:
    python run_detection.py --profiles <folder> [--quality file.json]
        [--quality-dataset NAME] [--goal "..."] [--override DATASET=COLUMN]
        [--problem-type TYPE] [--output outputs/integrated_detection.json]
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from problem_detection import (
    ATTRIBUTE_DATE_TOKENS,
    AUDIT_TOKENS,
    SUPPORTED_PROBLEM_TYPES,
    detect_problem,
    time_column_info,
)
from profiling_integration import analyze_profile, load_profile
from quality_integration import (
    _penalised,
    _worst,
    apply_quality_to_problem,
    apply_quality_to_suggestions,
    issues_by_column,
    load_quality_report,
)
from semantic_rules import tokenize
from target_suggestions import suggest_targets

PROJECT_FOLDER = Path(__file__).resolve().parent
DEFAULT_OUTPUT = PROJECT_FOLDER / "outputs" / "integrated_detection.json"
STATUS = "Proposed, pending verification"
MAX_CANDIDATES = 5


def _route_quality(quality, datasets, default_dataset):
    """Give every quality issue a dataset. Issues without one go to
    default_dataset, or to the only dataset if there is just one."""
    report = load_quality_report(quality)
    fallback = default_dataset or (datasets[0] if len(datasets) == 1 else None)
    issues, skipped = [], 0
    for issue in report["detected_issues"]:
        if not isinstance(issue, dict):
            continue
        issue = dict(issue)
        if issue.get("dataset") in (None, ""):
            if fallback is None:
                skipped += 1
                continue
            issue["dataset"] = fallback
        issues.append(issue)
    return {"detected_issues": issues}, skipped


LEAKAGE_CHECKS = {
    "status": "pending_integration",
    "reason": ("Target-leakage checks need column correlations from the "
               "profiling module (planned, not yet available). Not run."),
}
NOT_FEATURE_TYPES = {"identifier", "email", "phone"}


def build_column_roles(group, target, time_columns, quality_by_column):
    """Recommend a role for every column, each with a reason.

    Roles: target, feature, identifier, date, time, text, excluded.
    These are recommendations with evidence, not decisions.
    """
    roles = []
    for _, row in group.iterrows():
        column = str(row["column"])
        kind = str(row["semantic_type"]).lower()
        tokens = set(tokenize(column))
        unique = row.get("unique_values")
        missing = float(row.get("missing_pct") or 0)
        entry = {
            "column": column, "semantic_type": kind,
            "sensitive": bool(row.get("sensitive")),
            "time_axis": False, "quality_blocked": False,
            "quality_issues": [],
        }
        if column == target:
            role, reason = "target", "Suggested or chosen target column."
        elif tokens & AUDIT_TOKENS:
            role, reason = "excluded", "Audit or technical metadata column."
        elif kind in NOT_FEATURE_TYPES:
            role = "identifier"
            reason = ("Identifier or contact value; useful for joining "
                      "tables, not as a model input.")
        elif kind == "unknown":
            role, reason = "excluded", "Type could not be determined."
        elif pd.notna(unique) and unique <= 1:
            role, reason = "excluded", "Constant or empty column."
        elif missing >= 80:
            role, reason = "excluded", f"{missing}% of values are missing."
        elif kind == "date":
            role = "date"
            if column in time_columns:
                entry["time_axis"] = True
                reason = "Date column that can act as a time axis."
            else:
                reason = ("Date that describes a record or person; usable "
                          "after turning it into age, duration or similar.")
        elif kind == "time":
            role, reason = "time", "Time-of-day column."
        elif kind == "text":
            role = "text"
            reason = "Free text; needs text processing before use."
        else:
            role, reason = "feature", f"{kind} column usable as a model input."
            if entry["sensitive"]:
                reason += " Sensitive; review fairness and privacy."
            if missing >= 20:
                reason += f" {missing}% missing."

        issues = quality_by_column.get(column, [])
        entry["quality_issues"] = [
            f"{i['rule_id']} ({i['label'].lower()})" for i in issues]
        penalising = _penalised(issues)
        if penalising and _worst(penalising) == "blocking":
            entry["quality_blocked"] = True
            reason += " Blocking quality issue reported; review before use."
        entry["role"], entry["reason"] = role, reason
        roles.append(entry)
    return roles


def run_detection(profiles, quality=None, goal=None, overrides=None,
                  problem_type_override=None, quality_dataset=None,
                  quality_settings=None):
    rows = []
    characteristics = {}
    for profile in profiles:
        loaded = load_profile(profile)
        part = analyze_profile(loaded)
        rows.extend(part)
        info = loaded["dataset"]
        characteristics[part[0]["dataset"]] = {
            "row_count": info["row_count"],
            "column_count": info["column_count"],
            "duplicate_row_count": info["duplicate_row_count"],
            "profile_status": loaded.get("status"),
        }
    if not rows:
        raise ValueError("No profiles given")
    report = pd.DataFrame(rows)
    datasets = list(report["dataset"].drop_duplicates())

    overrides = dict(overrides or {})
    unknown = [d for d in overrides if d not in datasets]
    skipped_quality = 0
    suggestions = suggest_targets(report, overrides=overrides)
    routed = None
    if quality is not None:
        routed, skipped_quality = _route_quality(
            quality, datasets, quality_dataset)
        suggestions = apply_quality_to_suggestions(
            suggestions, routed, settings=quality_settings)

    results = []
    for dataset in datasets:
        group = suggestions[suggestions["dataset"] == dataset]
        chosen = group[group["priority"] == "User-selected"]
        top = group[group["priority"] == "Top suggestion"]
        if not chosen.empty:
            target, target_source = chosen.iloc[0]["candidate_target"], \
                "user_override"
        elif not top.empty:
            target, target_source = top.iloc[0]["candidate_target"], \
                "top_suggestion"
        else:
            target, target_source = None, "none"

        problem = detect_problem(
            report, dataset, target=target, business_goal=goal,
            problem_type_override=problem_type_override)
        if routed is not None:
            problem = apply_quality_to_problem(
                problem, routed, dataset, settings=quality_settings)

        warnings = list(problem["warnings"])
        if dataset in unknown:
            warnings.append("Override given for an unknown dataset")
        if target_source == "none":
            warnings.append(
                "No column clearly looks like an outcome; the project owner "
                "or user must confirm the business objective and target")
        if skipped_quality:
            warnings.append(
                f"{skipped_quality} quality issue(s) had no dataset and were "
                "not applied (pass quality_dataset)")

        keep = ["rank", "candidate_target", "semantic_type",
                "suggested_problem_type", "score", "confidence_level",
                "priority", "warnings"]
        if "quality_issues" in group.columns:
            keep.append("quality_issues")
        candidates = group[group["candidate_target"] != "(no target)"] \
            .head(MAX_CANDIDATES)[keep]
        dataset_rows = report[report["dataset"] == dataset]
        columns = dataset_rows[[
            "column", "semantic_type", "confidence", "sensitive"]]
        time_cols = [name for name, _ in time_column_info(dataset_rows)]
        quality_by_column = (
            issues_by_column(routed, dataset) if routed is not None else {})
        roles = build_column_roles(
            dataset_rows, target, time_cols, quality_by_column)
        feature_names = [r["column"] for r in roles if r["role"] == "feature"]
        facts = dict(characteristics[dataset])
        facts.update({
            "feature_column_count": len(feature_names),
            "time_columns": time_cols,
            "identifier_columns": [
                r["column"] for r in roles if r["role"] == "identifier"],
            "date_columns": [
                r["column"] for r in roles if r["role"] == "date"],
            "sensitive_columns": [
                r["column"] for r in roles if r["sensitive"]],
            "excluded_columns": [
                r["column"] for r in roles if r["role"] == "excluded"],
        })

        results.append({
            "dataset": dataset,
            "target": target,
            "target_source": target_source,
            "problem_type": problem["problem_type"],
            "confidence": problem["confidence"],
            "source": problem["source"],
            "needs_confirmation": problem["needs_confirmation"],
            "evidence": problem["evidence"],
            "alternatives": problem["alternatives"],
            "warnings": warnings,
            "candidates": json.loads(candidates.to_json(orient="records")),
            "semantic_columns": json.loads(
                columns.to_json(orient="records")),
            "dataset_characteristics": facts,
            "feature_columns": feature_names,
            "column_roles": roles,
            "leakage_checks": dict(LEAKAGE_CHECKS),
            "status": STATUS,
        })
    for name in unknown:
        results.append({
            "dataset": name, "target": None, "target_source": "none",
            "problem_type": "review_required", "confidence": 0.0,
            "source": "data_rules", "needs_confirmation": True,
            "evidence": [], "alternatives": [],
            "warnings": [f"Dataset '{name}' not found in the profiles"],
            "candidates": [], "semantic_columns": [],
            "dataset_characteristics": {}, "feature_columns": [],
            "column_roles": [], "leakage_checks": dict(LEAKAGE_CHECKS),
            "status": STATUS,
        })
    return results


def detect_dataset(profile, **kwargs):
    """One dataset per call: same inputs as run_detection, but takes a single
    profile and returns a single result."""
    return run_detection([profile], **kwargs)[0]


def main():
    parser = argparse.ArgumentParser(description="Integrated detection run.")
    parser.add_argument("--profiles", required=True,
                        help="Folder with *.profile.json files")
    parser.add_argument("--quality", help="Quality report JSON")
    parser.add_argument("--quality-dataset",
                        help="Dataset for quality issues that have none")
    parser.add_argument("--goal", help="Business goal in plain words")
    parser.add_argument("--override", action="append", default=[],
                        help="DATASET=COLUMN (repeatable)")
    parser.add_argument("--problem-type",
                        help="Override: " + ", ".join(SUPPORTED_PROBLEM_TYPES))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    overrides = {}
    for item in args.override:
        if "=" not in item:
            print(f"Bad --override '{item}'; use DATASET=COLUMN")
            return
        dataset, column = item.split("=", 1)
        overrides[dataset.strip()] = column.strip()

    files = sorted(Path(args.profiles).glob("*.profile.json"))
    if not files:
        print(f"No *.profile.json files found in {args.profiles}")
        return
    try:
        results = run_detection(
            files, quality=args.quality, goal=args.goal,
            overrides=overrides, problem_type_override=args.problem_type,
            quality_dataset=args.quality_dataset)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"Could not run: {error}")
        return

    print("\n===== INTEGRATED DETECTION =====")
    for r in results:
        print(f"\n{r['dataset']}")
        print(f"  target: {r['target'] or '(none)'} [{r['target_source']}]")
        print(f"  problem type: {r['problem_type']} "
              f"(confidence {r['confidence']}, source {r['source']}, "
              f"needs confirmation: {r['needs_confirmation']})")
        for c in r["candidates"][:3]:
            print(f"    {c['rank']}. {c['candidate_target']} "
                  f"score {c['score']} {c['confidence_level']} "
                  f"({c['priority']})")
        for w in r["warnings"][:3]:
            print(f"  warning: {w}")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved to: {output}")
    print(f"Status: {STATUS}")


if __name__ == "__main__":
    main()
