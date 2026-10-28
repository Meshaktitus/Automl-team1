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
semantic_columns, dataset_characteristics, target_confirmed,
target_statistics, feature_columns, recommended_feature_columns,
approved_feature_columns, features_status, column_roles, leakage_checks,
status. Everything is a recommendation with evidence; nothing
is final until the user confirms.

For one dataset per call use detect_dataset(profile, ...), which returns a
single result instead of a list.

Command line:
    python run_detection.py --profiles <folder> [--quality file.json]
        [--quality-dataset NAME] [--goal "..."] [--override DATASET=COLUMN]
        [--problem-type TYPE] [--output outputs/integrated_detection.json]

Leakage check: uses the profile's `correlations`. Flags (does not remove)
columns whose correlation with the target is >= 0.80 (possible) or >= 0.95
(strong). Change with leakage_settings={"possible": 0.7, "strong": 0.9}.
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
from leakage_checks import check_leakage, read_correlations
from profiling_integration import analyze_profile, dataset_name, load_profile
from quality_integration import (
    _penalised,
    _worst,
    apply_quality_to_problem,
    apply_quality_to_suggestions,
    issues_by_column,
    load_quality_report,
)
from handoff_details import (
    feature_type_counts,
    missing_summary,
    preprocessing_hint,
    target_statistics,
    time_info,
    validation_warnings,
)
from semantic_rules import tokenize
from target_suggestions import suggest_targets

PROJECT_FOLDER = Path(__file__).resolve().parent
DEFAULT_OUTPUT = PROJECT_FOLDER / "outputs" / "integrated_detection.json"
STATUS = "Proposed, pending verification"
MAX_CANDIDATES = 5


FILE_ENDINGS = (".xlsx", ".xls", ".csv", ".tsv", ".json", ".parquet")


def _key(name):
    """Compare dataset names without case or a file ending, so
    "HumanResources.Employee.xlsx" and "HumanResources.Employee" match."""
    text = str(name).strip().lower()
    for ending in FILE_ENDINGS:
        if text.endswith(ending):
            return text[:-len(ending)]
    return text


def _aliases(datasets, dataset_ids):
    """Every name a dataset may be called by (its name and its dataset_id)
    mapped to the dataset name used in the results."""
    found = {}
    for name in datasets:
        for label in (name, dataset_ids.get(name)):
            if label:
                found.setdefault(_key(label), name)
    return found


def _route_quality(quality, datasets, default_dataset, aliases=None):
    """Give every quality issue a dataset. Issues without one go to
    default_dataset, or to the only dataset if there is just one. A dataset
    given by dataset_id, or by file name, is matched to the profile."""
    aliases = aliases or {}
    report = load_quality_report(quality)
    fallback = default_dataset or (datasets[0] if len(datasets) == 1 else None)
    if fallback is not None:
        fallback = aliases.get(_key(fallback), fallback)
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
        else:
            issue["dataset"] = aliases.get(
                _key(issue["dataset"]), issue["dataset"])
        issues.append(issue)
    return {"detected_issues": issues}, skipped


LEAKAGE_CHECKS = {
    "status": "pending_integration",
    "reason": ("Dataset not found in the profiles, so the leakage check "
               "was not run."),
}
NOT_FEATURE_TYPES = {"identifier", "email", "phone"}


def build_column_roles(group, target, time_columns, quality_by_column,
                       problem_type=None):
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
            "data_type": str(row.get("data_type") or ""),
            "unique_values": None if pd.isna(unique) else int(unique),
            "missing_count": int(
                (row.get("row_count") or 0) - (row.get("non_null_count") or 0)),
            "missing_pct": missing,
            "sensitive": bool(row.get("sensitive")),
            "needs_privacy_review": bool(row.get("sensitive")),
            "time_axis": False, "quality_blocked": False,
            "quality_issues": [], "quality_issue_codes": [],
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

        issues = [i for i in quality_by_column.get(column, [])
                  if i["affected_count"] != 0]   # 0 rows = check passed
        entry["quality_issues"] = [
            f"{i['rule_id']} ({i['label'].lower()})" for i in issues]
        entry["quality_issue_codes"] = sorted({i["rule_id"] for i in issues})
        penalising = _penalised(issues)
        if penalising and _worst(penalising) == "blocking":
            entry["quality_blocked"] = True
            reason += " Blocking quality issue reported; review before use."
        entry["role"], entry["reason"] = role, reason
        entry["preprocessing_hint"] = preprocessing_hint(
            role, kind, None if pd.isna(unique) else unique, missing,
            entry["time_axis"], problem_type)
        roles.append(entry)
    return roles


def run_detection(profiles, quality=None, goal=None, overrides=None,
                  problem_type_override=None, quality_dataset=None,
                  quality_settings=None, approved_features=None,
                  leakage_settings=None):
    """approved_features: optional {dataset: [columns]} (or a plain list when
    there is one dataset) that the user has approved for training."""
    rows = []
    characteristics = {}
    profile_columns = {}
    dataset_ids = {}
    profile_correlations = {}
    profile_distributions = {}
    empty_profiles = []
    unusable = []
    for profile in profiles:
        try:
            loaded = load_profile(profile)
            part = analyze_profile(loaded)
        except (ValueError, OSError) as error:
            # one bad profile must not stop the other datasets
            unusable.append((_profile_label(profile), str(error)))
            continue
        if not part:
            empty_profiles.append(dataset_name(loaded))
            continue
        if part[0]["dataset"] in profile_columns:
            unusable.append((part[0]["dataset"], "Dataset name appears in "
                             "more than one profile; only the first one "
                             "was used"))
            continue
        rows.extend(part)
        info = loaded["dataset"]
        profile_columns[part[0]["dataset"]] = {
            c["name"]: c for c in loaded["columns"]}
        dataset_ids[part[0]["dataset"]] = (
            loaded.get("dataset_reference") or {}).get("dataset_id")
        profile_correlations[part[0]["dataset"]] = read_correlations(loaded)
        profile_distributions[part[0]["dataset"]] = loaded.get(
            "class_distribution")
        characteristics[part[0]["dataset"]] = {
            "row_count": info["row_count"],
            "column_count": info["column_count"],
            "duplicate_row_count": info["duplicate_row_count"],
            "profile_status": loaded.get("status"),
        }
    if not rows and not empty_profiles and not unusable:
        raise ValueError("No profiles given")
    report = pd.DataFrame(rows, columns=[
        "dataset", "column", "data_type", "row_count", "non_null_count",
        "missing_pct", "unique_values", "semantic_type", "confidence",
        "evidence", "alternatives", "sensitive", "status"])
    datasets = list(report["dataset"].drop_duplicates())

    aliases = _aliases(datasets, dataset_ids)
    overrides = {aliases.get(_key(d), d): c
                 for d, c in dict(overrides or {}).items()}
    unknown = [d for d in overrides if d not in datasets]
    skipped_quality = 0
    suggestions = suggest_targets(report, overrides=overrides)
    routed = None
    if quality is not None:
        routed, skipped_quality = _route_quality(
            quality, datasets, quality_dataset, aliases)
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
        for unknown_column in [c for c in quality_by_column
                               if c not in set(dataset_rows["column"])][:5]:
            warnings.append(
                f"Quality report names column '{unknown_column}', which is "
                "not in this dataset; the finding was ignored")
        roles = build_column_roles(
            dataset_rows, target, time_cols, quality_by_column,
            problem["problem_type"])
        pairs, bad_pairs = profile_correlations[dataset]
        leakage = check_leakage(pairs, target, bad_pairs, leakage_settings)
        flagged = {x["column"]: x for x in leakage["suspects"]}
        for r in roles:
            hit = flagged.get(r["column"])
            r["leakage_suspect"] = hit["level"] if hit else None
            r["leakage_correlation"] = hit["correlation"] if hit else None
            if hit and r["role"] == "feature":
                r["reason"] += (" Possible target leakage (correlation "
                                f"{hit['correlation']:+.2f} with the target).")
        for x in leakage["suspects"]:
            warnings.append("Possible target leakage: " + x["message"])
        feature_names = [r["column"] for r in roles if r["role"] == "feature"]
        recommended = [r["column"] for r in roles
                       if r["role"] == "feature" and not r["quality_blocked"]]
        approved = None
        if approved_features is not None:
            given = approved_features.get(dataset) \
                if isinstance(approved_features, dict) else (
                    approved_features if len(datasets) == 1 else None)
            if given is not None:
                approved = [c for c in given if c in feature_names]
                rejected = [c for c in given if c not in feature_names]
                if rejected:
                    warnings.append(
                        "Approved columns that are not usable features: "
                        + ", ".join(rejected))
        pcols = profile_columns[dataset]
        target_stats = target_statistics(
            pcols.get(target) if target else None,
            next((r["semantic_type"] for r in roles if r["column"] == target),
                 None), problem["problem_type"],
            profile_distributions[dataset])
        facts = dict(characteristics[dataset])
        facts.update({
            "feature_column_count": len(feature_names),
            "feature_type_counts": feature_type_counts(roles),
            "missing_summary": missing_summary(roles),
            "time_info": time_info(pcols, time_cols),
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
        facts["validation_warnings"] = validation_warnings(
            facts, roles, target_stats, problem["problem_type"])

        candidate_list = json.loads(candidates.to_json(orient="records"))
        for c in candidate_list:
            found = [i for i in quality_by_column.get(
                c["candidate_target"], []) if i["affected_count"] != 0]
            c["quality_issue_codes"] = sorted({i["rule_id"] for i in found})
            reasons = [
                f"{i['rule_id']}: {i['description']}".strip(": ")
                for i in _penalised(found) if i["severity"] == "blocking"]
            c["blocking_reason"] = (
                "; ".join(reasons)
                if c["priority"] == "Blocked by quality" and reasons else None)

        results.append({
            "dataset": dataset,
            "dataset_id": dataset_ids.get(dataset),
            "target": target,
            "target_source": target_source,
            "problem_type": problem["problem_type"],
            "confidence": problem["confidence"],
            "source": problem["source"],
            "needs_confirmation": problem["needs_confirmation"],
            "evidence": problem["evidence"],
            "alternatives": problem["alternatives"],
            "warnings": warnings,
            "target_confirmed": target_source == "user_override",
            "target_statistics": target_stats,
            "candidates": candidate_list,
            "semantic_columns": json.loads(
                columns.to_json(orient="records")),
            "dataset_characteristics": facts,
            "feature_columns": feature_names,
            "recommended_feature_columns": recommended,
            "approved_feature_columns": approved,
            "features_status": ("approved" if approved is not None
                                else "recommended_pending_confirmation"),
            "column_roles": roles,
            "leakage_checks": leakage,
            "status": STATUS,
        })
    for name, why in unusable:
        results.append(_placeholder_result(
            name, f"Profile for '{name}' could not be used: {why}",
            leakage_settings))
    for name in empty_profiles:
        results.append(_placeholder_result(
            name, f"Profile for '{name}' has no columns, so nothing could "
                  "be analysed", leakage_settings))
    for name in unknown:
        results.append(_placeholder_result(
            name, f"Dataset '{name}' not found in the profiles",
            leakage_settings))
    return results


def _profile_label(profile):
    """A readable name for a profile that could not be read."""
    if isinstance(profile, dict):
        ref = profile.get("dataset_reference") or {}
        return str(ref.get("name") or ref.get("dataset_id") or "unknown")
    return Path(str(profile)).name


def _placeholder_result(name, warning, leakage_settings=None):
    """Result for a dataset that could not be analysed (same fields as a
    normal result, so consumers need no special case)."""
    return {
        "dataset": name, "dataset_id": None, "target": None,
        "target_source": "none",
        "problem_type": "review_required", "confidence": 0.0,
        "source": "data_rules", "needs_confirmation": True,
        "evidence": [], "alternatives": [], "warnings": [warning],
        "target_confirmed": False, "target_statistics": None,
        "candidates": [], "semantic_columns": [],
        "dataset_characteristics": {}, "feature_columns": [],
        "recommended_feature_columns": [],
        "approved_feature_columns": None,
        "features_status": "recommended_pending_confirmation",
        "column_roles": [],
        "leakage_checks": {**check_leakage(None, None, 0, leakage_settings),
                           "reason": "Dataset could not be analysed, so the "
                                     "leakage check was not run."},
        "status": STATUS,
    }


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
