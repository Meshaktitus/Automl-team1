"""Use the data-quality report (Gantla Vinitha's module) in target suggestions
and problem-type recommendations.

Input: the quality JSON report with a "detected_issues" list. Each issue has
rule_id, column, severity (Warning, Error or Blocking), affected_rows,
description and recommended_action. An issue may also carry "dataset"; when
it does not, the caller says which dataset the report belongs to.

Severity labels are grouped into four levels (proposed rules, not agreed):
  warning   Low, Info, Warning: a note is added, no score change
  medium    Medium: score x 0.85, problem-type confidence -0.05
  error     High, Error: score x 0.6, confidence Low, no longer Top
            suggestion or Alternative, problem-type confidence -0.10,
            confirmation needed
  blocking  Blocking: column marked "Blocked by quality", score x 0.0, ranked
            last, problem-type confidence -0.30, confirmation needed
Only a note is added (no score change) when the rule is about nulls (RULE_NULL_*
or NULL_CHECK), duplicate rows (DUP_ROW), constant columns or keys (the ranking already handles missing and constant columns,
and key checks are about the table, not the column), or when the issue
affects 0 rows.

An issue may name one column, a list of columns, or a composite such as
"BusinessEntityID + StartDate" or "OrganizationNode, OrganizationLevel";
it then applies to each column. affected_rows may be a number, a dict with
count and percentage, or text such as "2 records (0.34%)".
"""
import argparse
import json
import re
from pathlib import Path

import pandas as pd

PROJECT_FOLDER = Path(__file__).resolve().parent
DEFAULT_SUGGESTIONS = PROJECT_FOLDER / "outputs" / "target_suggestions.csv"
DEFAULT_OUTPUT = (
    PROJECT_FOLDER / "outputs" / "target_suggestions_with_quality.csv"
)

SEVERITY_ALIASES = {
    "info": "warning", "low": "warning", "warning": "warning",
    "medium": "medium",
    "high": "error", "error": "error",
    "blocking": "blocking",
}
SEVERITY_RANK = {"warning": 1, "medium": 2, "error": 3, "blocking": 4}
SCORE_FACTOR = {"warning": 1.0, "medium": 0.85, "error": 0.6, "blocking": 0.0}
CONFIDENCE_PENALTY = {
    "warning": 0.0, "medium": 0.05, "error": 0.10, "blocking": 0.30,
}
# Compared after removing a leading "RULE_", so RULE_NULL_001 and NULL_CHECK
# are treated the same. Duplicate-row findings are about the table.
NOTE_ONLY_PREFIXES = (
    "MISSING", "NULL", "CONSTANT", "KEY", "REF", "DUP",
)


def _rule_core(rule_id):
    text = str(rule_id).strip().upper()
    return text[5:] if text.startswith("RULE_") else text


TABLE_LEVEL = {"", "none", "null", "n/a", "na", "-"}


def _normalise_issue(issue, default_dataset):
    """Accept both field styles: column / affected_column, description /
    category + recommended_action, dataset on the issue or on the report."""
    out = dict(issue)
    column = out.get("column", out.get("affected_column"))
    if isinstance(column, str) and column.strip().lower() in TABLE_LEVEL:
        column = None
    out["column"] = column
    if out.get("dataset") in (None, "") and default_dataset:
        out["dataset"] = default_dataset
    if not out.get("description"):
        parts = [str(out.get("category") or "").strip(),
                 str(out.get("recommended_action") or "").strip()]
        out["description"] = ": ".join(p for p in parts if p)
    return out


def load_quality_report(source):
    """Read a quality report from a JSON file path or an already-loaded dict.

    The issue list may be called "detected_issues" or "issues". A "dataset"
    given once at the top of the report applies to issues that have none.
    """
    if isinstance(source, (str, Path)):
        with open(source, encoding="utf-8") as handle:
            data = json.load(handle)
    else:
        data = source
    issues = None
    if isinstance(data, dict):
        for key in ("detected_issues", "issues"):
            if isinstance(data.get(key), list):
                issues = data[key]
                break
    if issues is None:
        raise ValueError(
            "Quality report must be an object with a 'detected_issues' "
            "(or 'issues') list"
        )
    default_dataset = data.get("dataset")
    return {
        **{k: v for k, v in data.items() if k not in {"issues"}},
        "detected_issues": [
            _normalise_issue(i, default_dataset)
            for i in issues if isinstance(i, dict)
        ],
    }


def _split_columns(value):
    """One issue can name a column, a list, or a composite key."""
    if isinstance(value, (list, tuple, set)):
        parts = [str(v).strip() for v in value]
    else:
        parts = re.split(r"[,+;]", str(value))
    return [p.strip() for p in parts if p and p.strip()]


def _affected(value):
    """Return (count or None, text for notes) for any affected_rows shape."""
    if value is None:
        return None, ""
    if isinstance(value, bool):
        return None, str(value)
    if isinstance(value, (int, float)):
        return int(value), f"{int(value)} rows"
    if isinstance(value, dict):
        count = None
        for key in ("count", "affected_rows", "rows", "records"):
            if isinstance(value.get(key), (int, float)):
                count = int(value[key])
                break
        pct = value.get("percentage", value.get("pct"))
        text = f"{count} rows" if count is not None else str(value)
        if pct is not None:
            text += f" ({pct}%)"
        return count, text
    text = str(value).strip()
    match = re.search(r"\d[\d,]*", text)
    count = int(match.group().replace(",", "")) if match else None
    return count, text


def issues_by_column(report, dataset=None):
    """Group the report's issues by column name, normalising severity.

    An issue with its own "dataset" is only used for that dataset.
    """
    grouped = {}
    for issue in load_quality_report(report)["detected_issues"]:
        if issue.get("column") in (None, ""):
            continue  # table-level issue (for example duplicate rows)
        issue_dataset = issue.get("dataset")
        if (
            issue_dataset is not None
            and dataset is not None
            and str(issue_dataset) != str(dataset)
        ):
            continue
        label = str(issue.get("severity", "")).strip()
        level = SEVERITY_ALIASES.get(label.lower())
        unknown = level is None
        if unknown:
            level = "warning"
        count, affected_text = _affected(issue.get("affected_rows"))
        record = {
            "rule_id": str(issue.get("rule_id", "")),
            "severity": level,
            "label": label or "unspecified",
            "unknown_severity": unknown,
            "affected_rows": issue.get("affected_rows"),
            "affected_count": count,
            "affected_text": affected_text,
            "description": str(issue.get("description", "")),
        }
        for column in _split_columns(issue["column"]):
            grouped.setdefault(column, []).append(record)
    return grouped


def _penalised(issues):
    """Issues that may change a score: not note-only rules, not 0 rows."""
    return [
        i for i in issues
        if not _rule_core(i["rule_id"]).startswith(NOTE_ONLY_PREFIXES)
        and i["affected_count"] != 0
    ]


def _note(issue):
    text = f"{issue['rule_id']} ({issue['label'].lower()}): "
    text += issue["description"]
    if issue["affected_text"]:
        text += f" [{issue['affected_text']}]"
    if issue["unknown_severity"]:
        text += " [unknown severity, treated as warning]"
    return text


def _worst(issues):
    return max(issues, key=lambda i: SEVERITY_RANK[i["severity"]])["severity"]


def apply_quality_to_suggestions(suggestions, report, dataset=None):
    """Return a copy of the target suggestions adjusted by the quality report.

    Pass dataset so the report is only applied to that dataset's rows.
    """
    out = suggestions.copy()
    out["quality_issues"] = ""
    by_column = issues_by_column(report, dataset)

    for index in out.index:
        row = out.loc[index]
        if dataset is not None and str(row["dataset"]) != str(dataset):
            continue
        issues = by_column.get(str(row["candidate_target"]))
        if not issues:
            continue

        notes = [_note(i) for i in issues]
        out.at[index, "quality_issues"] = "; ".join(notes)
        warnings = str(row["warnings"]) if pd.notna(row["warnings"]) else ""
        out.at[index, "warnings"] = "; ".join(
            part for part in [warnings] + notes if part
        )

        penalised = _penalised(issues)
        if not penalised:
            continue
        worst = _worst(penalised)
        if pd.notna(row["score"]):
            out.at[index, "score"] = round(
                float(row["score"]) * SCORE_FACTOR[worst], 1
            )
        user_selected = row["priority"] == "User-selected"
        if worst == "blocking" and not user_selected:
            out.at[index, "priority"] = "Blocked by quality"
        if worst in {"error", "blocking"} and not user_selected:
            out.at[index, "confidence_level"] = "Low"
        if worst == "error" and row["priority"] in {
            "Top suggestion", "Alternative"
        }:
            out.at[index, "priority"] = "Candidate"

    return _rerank(out)


def _rerank(frame):
    """User-selected first, then by score, blocked columns and the
    no-target clustering row last. Ranks are renumbered per dataset."""
    first_seen = {d: i for i, d in enumerate(frame["dataset"].drop_duplicates())}

    def key(i):
        row = frame.loc[i]
        score = float(row["score"]) if pd.notna(row["score"]) else -1.0
        return (
            first_seen[row["dataset"]],
            row["candidate_target"] == "(no target)",
            0 if row["priority"] == "User-selected" else 1,
            row["priority"] == "Blocked by quality",
            -score,
        )

    ordered = frame.loc[sorted(frame.index, key=key)].copy()
    counters = {}
    ranks = []
    for _, row in ordered.iterrows():
        if row["candidate_target"] == "(no target)":
            ranks.append(pd.NA)
            continue
        counters[row["dataset"]] = counters.get(row["dataset"], 0) + 1
        ranks.append(counters[row["dataset"]])
    ordered["rank"] = pd.array(ranks, dtype="Int64")
    return ordered.reset_index(drop=True)


def apply_quality_to_problem(result, report, dataset=None):
    """Return a copy of a detect_problem() result adjusted by the report.

    Only issues on the chosen target column are used.
    """
    out = dict(result)
    out["warnings"] = list(result.get("warnings", []))
    target = out.get("target")
    if not target:
        return out
    issues = issues_by_column(report, dataset or out.get("dataset")).get(
        str(target)
    )
    if not issues:
        return out

    for issue in issues:
        out["warnings"].append("Quality: " + _note(issue))
    penalised = _penalised(issues)
    if not penalised:
        return out

    worst = _worst(penalised)
    if out.get("source") != "user_override":
        out["confidence"] = round(
            max(0.0, out["confidence"] - CONFIDENCE_PENALTY[worst]), 2
        )
        if worst in {"error", "blocking"}:
            out["needs_confirmation"] = True
    if worst == "blocking":
        out["warnings"].append(
            f"Target '{target}' has a blocking quality issue; "
            "do not train until it is resolved"
        )
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Apply a data-quality report to target suggestions."
    )
    parser.add_argument("--quality", required=True,
                        help="Quality report JSON file")
    parser.add_argument("--dataset", required=True,
                        help="Dataset the report belongs to")
    parser.add_argument("--suggestions", default=str(DEFAULT_SUGGESTIONS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    suggestions_file = Path(args.suggestions)
    if not suggestions_file.exists():
        print("Target suggestions not found.")
        print("Run: python target_suggestions.py")
        return

    report = load_quality_report(args.quality)
    result = apply_quality_to_suggestions(
        pd.read_csv(suggestions_file), report, args.dataset
    )
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_file, index=False)

    rows = result[result["dataset"] == args.dataset]
    print("\n===== TARGET SUGGESTIONS WITH QUALITY =====")
    print(rows[[
        "dataset", "rank", "candidate_target", "score",
        "confidence_level", "priority", "quality_issues",
    ]].to_string(index=False))
    print(f"\nSaved to: {output_file}")
    print("Status: Proposed, pending verification")


if __name__ == "__main__":
    main()
