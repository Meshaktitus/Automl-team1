import json

import pandas as pd
import pytest

from problem_detection import detect_problem
from quality_integration import (
    _affected,
    apply_quality_to_problem,
    apply_quality_to_suggestions,
    issues_by_column,
    load_quality_report,
)
from target_suggestions import suggest_targets

# Sample from Vinitha's module (shortened)
SAMPLE = {
    "module_owner": "Gantla Vinitha (Data Quality Engine)",
    "source_data_preserved": True,
    "profiling_metadata_received": True,
    "total_issues_detected": 5,
    "detected_issues": [
        {"rule_id": "RULE_MISSING_001", "column": "age",
         "severity": "Warning", "affected_rows": 1,
         "description": "Column 'age' contains missing values.",
         "recommended_action": "Impute or drop missing records."},
        {"rule_id": "RULE_INVALID_NUM_001", "column": "age",
         "severity": "Error", "affected_rows": 1,
         "description": "Column 'age' contains negative values.",
         "recommended_action": "Correct invalid age values."},
        {"rule_id": "RULE_INVALID_PCT_001", "column": "percentage",
         "severity": "Error", "affected_rows": 1,
         "description": "Column 'percentage' has values outside 0-100.",
         "recommended_action": "Review and correct percentage bounds."},
        {"rule_id": "RULE_CONSTANT_COL_001", "column": "constant_col",
         "severity": "Warning", "affected_rows": 5,
         "description": "Column 'constant_col' is a constant column.",
         "recommended_action": "Evaluate predictive value."},
    ],
}


def report_rows(rows, dataset="d.csv"):
    return pd.DataFrame([{
        "dataset": dataset, "column": c, "semantic_type": t,
        "unique_values": u, "non_null_count": 100, "row_count": 100,
    } for c, t, u in rows])


def base_report():
    return report_rows([
        ("age", "numerical_measure", 50),
        ("income", "numerical_measure", 60),
        ("churn", "boolean_flag", 2),
    ])


def row_for(frame, column):
    return frame[frame["candidate_target"] == column].iloc[0]


def test_load_from_dict_and_file(tmp_path):
    assert load_quality_report(SAMPLE)["total_issues_detected"] == 5
    path = tmp_path / "quality.json"
    path.write_text(json.dumps(SAMPLE), encoding="utf-8")
    assert len(load_quality_report(path)["detected_issues"]) == 4


@pytest.mark.parametrize("bad", [[], {}, {"detected_issues": "x"}, 42])
def test_bad_report_is_rejected(bad):
    with pytest.raises(ValueError):
        load_quality_report(bad)


def test_missing_file_and_broken_json_fail_clearly(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_quality_report(tmp_path / "nope.json")
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_quality_report(broken)


def test_issues_grouped_and_severity_normalised():
    grouped = issues_by_column(SAMPLE)
    assert [i["severity"] for i in grouped["age"]] == ["warning", "error"]
    assert "income" not in grouped


def test_unknown_severity_is_treated_as_warning_and_flagged():
    report = {"detected_issues": [
        {"rule_id": "X", "column": "age", "severity": "Weird",
         "description": "d"}]}
    issue = issues_by_column(report)["age"][0]
    assert issue["severity"] == "warning"
    assert issue["unknown_severity"]


def test_issue_with_other_dataset_is_ignored():
    report = {"detected_issues": [
        {"rule_id": "X", "column": "age", "severity": "Error",
         "dataset": "other.csv", "description": "d"}]}
    assert issues_by_column(report, "d.csv") == {}
    assert "age" in issues_by_column(report, "other.csv")


def test_error_lowers_score_and_confidence_and_adds_note():
    suggestions = suggest_targets(base_report())
    before = row_for(suggestions, "age")
    after = row_for(
        apply_quality_to_suggestions(suggestions, SAMPLE, "d.csv"), "age")
    assert after["score"] == round(before["score"] * 0.6, 1)
    assert after["confidence_level"] == "Low"
    assert "negative values" in after["quality_issues"]
    assert "negative values" in after["warnings"]


def test_missing_rule_only_adds_a_note():
    suggestions = suggest_targets(base_report())
    report = {"detected_issues": [SAMPLE["detected_issues"][0]]}
    before = row_for(suggestions, "age")
    after = row_for(
        apply_quality_to_suggestions(suggestions, report, "d.csv"), "age")
    assert after["score"] == before["score"]
    assert "RULE_MISSING_001" in after["quality_issues"]


def test_columns_without_issues_are_unchanged():
    suggestions = suggest_targets(base_report())
    after = apply_quality_to_suggestions(suggestions, SAMPLE, "d.csv")
    assert row_for(after, "income")["score"] == row_for(
        suggestions, "income")["score"]
    assert row_for(after, "income")["quality_issues"] == ""


def test_blocking_column_is_marked_and_ranked_last():
    suggestions = suggest_targets(base_report())
    report = {"detected_issues": [
        {"rule_id": "RULE_INVALID_NUM_001", "column": "churn",
         "severity": "Blocking", "affected_rows": 40, "description": "bad"}]}
    after = apply_quality_to_suggestions(suggestions, report, "d.csv")
    blocked = row_for(after, "churn")
    assert blocked["priority"] == "Blocked by quality"
    assert blocked["score"] == 0.0
    real = after[after["candidate_target"] != "(no target)"]
    assert real.iloc[-1]["candidate_target"] == "churn"
    assert list(real["rank"]) == [1, 2, 3]


def test_user_selected_stays_first_even_with_a_blocking_issue():
    suggestions = suggest_targets(
        base_report(), overrides={"d.csv": "churn"})
    report = {"detected_issues": [
        {"rule_id": "RULE_INVALID_NUM_001", "column": "churn",
         "severity": "Blocking", "description": "bad"}]}
    after = apply_quality_to_suggestions(suggestions, report, "d.csv")
    first = after.iloc[0]
    assert first["candidate_target"] == "churn"
    assert first["priority"] == "User-selected"
    assert "bad" in first["warnings"]


def test_report_is_only_applied_to_the_named_dataset():
    one = suggest_targets(base_report())
    two = suggest_targets(report_rows(
        [("age", "numerical_measure", 50),
         ("income", "numerical_measure", 60)], dataset="e.csv"))
    both = pd.concat([one, two], ignore_index=True)
    after = apply_quality_to_suggestions(both, SAMPLE, "d.csv")
    e_age = after[(after["dataset"] == "e.csv")
                  & (after["candidate_target"] == "age")].iloc[0]
    assert e_age["quality_issues"] == ""


def test_problem_confidence_drops_on_target_error():
    result = detect_problem(base_report(), "d.csv", target="age")
    adjusted = apply_quality_to_problem(result, SAMPLE, "d.csv")
    assert adjusted["confidence"] == round(result["confidence"] - 0.10, 2)
    assert adjusted["needs_confirmation"]
    assert any("negative values" in w for w in adjusted["warnings"])


def test_problem_blocking_issue_warns_not_to_train():
    result = detect_problem(base_report(), "d.csv", target="churn")
    report = {"detected_issues": [
        {"rule_id": "R", "column": "churn", "severity": "Blocking",
         "description": "bad"}]}
    adjusted = apply_quality_to_problem(result, report, "d.csv")
    assert adjusted["confidence"] == round(result["confidence"] - 0.30, 2)
    assert "do not train" in " ".join(adjusted["warnings"])


def test_problem_user_override_confidence_is_not_lowered():
    result = detect_problem(
        base_report(), "d.csv", target="age",
        problem_type_override="regression")
    adjusted = apply_quality_to_problem(result, SAMPLE, "d.csv")
    assert adjusted["confidence"] == 1.0
    assert any("negative values" in w for w in adjusted["warnings"])


def test_problem_without_target_is_unchanged():
    result = detect_problem(base_report(), "d.csv")
    assert apply_quality_to_problem(result, SAMPLE, "d.csv") == result


def test_error_on_a_top_suggestion_removes_the_label():
    report = report_rows([
        ("churn", "boolean_flag", 2),
        ("income", "numerical_measure", 60),
        ("age", "numerical_measure", 50),
    ])
    suggestions = suggest_targets(report)
    assert row_for(suggestions, "churn")["priority"] == "Top suggestion"
    quality = {"detected_issues": [
        {"rule_id": "RULE_INVALID_NUM_001", "column": "churn",
         "severity": "Error", "description": "bad values"}]}
    after = apply_quality_to_suggestions(suggestions, quality, "d.csv")
    assert row_for(after, "churn")["priority"] == "Candidate"
    assert "Top suggestion" not in after["priority"].tolist()


# Final format from the Data Quality Engine (Low / Medium / High / Blocking,
# affected_rows with a percentage, issues on several columns)
FINAL = {"detected_issues": [
    {"rule_id": "RULE_NULL_001", "column": "OrganizationNode, OrganizationLevel",
     "severity": "Low", "affected_rows": "2 records (0.34%)",
     "description": "Missing values for top-level executives."},
    {"rule_id": "RULE_KEY_REF_001", "column": "BusinessEntityID",
     "severity": "Medium", "affected_rows": {"count": 11, "percentage": 84.62},
     "description": "Unassociated external applicants."},
    {"rule_id": "RULE_RANGE_001", "column": "Rate", "severity": "Low",
     "affected_rows": "0 invalid (0%)", "description": "Range verified."},
    {"rule_id": "RULE_KEY_UNIQUE_001",
     "column": "BusinessEntityID + StartDate", "severity": "Low",
     "affected_rows": 0, "description": "Composite key is unique."},
]}


def test_final_severity_labels_map_to_levels():
    report = {"detected_issues": [
        {"rule_id": "R", "column": c, "severity": s, "description": "d"}
        for c, s in [("a", "Low"), ("b", "Medium"), ("c", "High"),
                     ("d", "Blocking"), ("e", "Info")]]}
    grouped = issues_by_column(report)
    assert {c: grouped[c][0]["severity"] for c in grouped} == {
        "a": "warning", "b": "medium", "c": "error",
        "d": "blocking", "e": "warning"}
    assert not any(g[0]["unknown_severity"] for g in grouped.values())


def test_composite_and_multi_column_issues_apply_to_each_column():
    grouped = issues_by_column(FINAL)
    assert "OrganizationNode" in grouped and "OrganizationLevel" in grouped
    assert "BusinessEntityID" in grouped and "StartDate" in grouped


def test_affected_rows_shapes():
    assert _affected(5)[0] == 5
    assert _affected("2 records (0.34%)")[0] == 2
    assert _affected("0 invalid (0%)")[0] == 0
    assert _affected({"count": 11, "percentage": 84.62}) == (
        11, "11 rows (84.62%)")
    assert _affected(None) == (None, "")


def test_zero_affected_rows_never_penalises():
    suggestions = suggest_targets(report_rows(
        [("Rate", "financial_amount", 66), ("other", "numerical_measure", 50)]))
    after = apply_quality_to_suggestions(suggestions, FINAL, "d.csv")
    assert row_for(after, "Rate")["score"] == row_for(
        suggestions, "Rate")["score"]
    assert "RULE_RANGE_001" in row_for(after, "Rate")["quality_issues"]


def test_structural_null_rule_is_note_only():
    suggestions = suggest_targets(report_rows(
        [("OrganizationLevel", "categorical", 4),
         ("other", "numerical_measure", 50)]))
    after = apply_quality_to_suggestions(suggestions, FINAL, "d.csv")
    row = row_for(after, "OrganizationLevel")
    assert row["score"] == row_for(suggestions, "OrganizationLevel")["score"]
    assert "2 records (0.34%)" in row["quality_issues"]


def test_medium_issue_lowers_score_by_15_percent():
    suggestions = suggest_targets(base_report())
    report = {"detected_issues": [
        {"rule_id": "RULE_FORMAT_001", "column": "income",
         "severity": "Medium", "affected_rows": 4, "description": "odd"}]}
    after = apply_quality_to_suggestions(suggestions, report, "d.csv")
    assert row_for(after, "income")["score"] == round(
        row_for(suggestions, "income")["score"] * 0.85, 1)


def test_high_severity_behaves_like_error():
    result = detect_problem(base_report(), "d.csv", target="age")
    report = {"detected_issues": [
        {"rule_id": "RULE_X_001", "column": "age", "severity": "High",
         "affected_rows": 3, "description": "bad"}]}
    adjusted = apply_quality_to_problem(result, report, "d.csv")
    assert adjusted["confidence"] == round(result["confidence"] - 0.10, 2)
    assert adjusted["needs_confirmation"]


# Naming style in the second answer from the Data Quality Engine
def test_null_check_blocking_is_note_only_not_a_block():
    suggestions = suggest_targets(base_report())
    report = {"detected_issues": [
        {"rule_id": "NULL_CHECK", "column": "income", "severity": "Blocking",
         "affected_rows": 3, "description": "Missing mandatory values"}]}
    after = apply_quality_to_suggestions(suggestions, report, "d.csv")
    row = row_for(after, "income")
    assert row["score"] == row_for(suggestions, "income")["score"]
    assert row["priority"] != "Blocked by quality"
    assert "NULL_CHECK" in row["quality_issues"]


def test_invalid_range_blocking_still_blocks():
    suggestions = suggest_targets(base_report())
    report = {"detected_issues": [
        {"rule_id": "INVALID_RANGE", "column": "age", "severity": "Blocking",
         "affected_rows": 2, "description": "Negative age"}]}
    after = apply_quality_to_suggestions(suggestions, report, "d.csv")
    row = row_for(after, "age")
    assert row["score"] == 0
    assert row["priority"] == "Blocked by quality"


def test_outlier_warning_is_a_note():
    suggestions = suggest_targets(base_report())
    report = {"detected_issues": [
        {"rule_id": "OUTLIER_IQR", "column": "income", "severity": "Warning",
         "affected_rows": "5 records (2.5%)", "description": "Outliers"}]}
    after = apply_quality_to_suggestions(suggestions, report, "d.csv")
    assert row_for(after, "income")["score"] == row_for(
        suggestions, "income")["score"]


def test_table_level_duplicate_issue_does_not_crash():
    suggestions = suggest_targets(base_report())
    for column in (None, "", "missing_key"):
        issue = {"rule_id": "DUP_ROW", "severity": "Warning",
                 "affected_rows": 4, "description": "Duplicates"}
        if column != "missing_key":
            issue["column"] = column
        after = apply_quality_to_suggestions(
            suggestions, {"detected_issues": [issue]}, "d.csv")
        pd.testing.assert_series_equal(
            after["score"], suggest_targets(base_report())["score"])


# Format of the latest sample from the Data Quality Engine
LATEST = {
    "dataset": "hr_attrition.csv", "total_rows": 1250,
    "issues": [
        {"rule_id": "NULL_CHECK", "severity": "Blocking",
         "category": "Missing Values", "affected_column": "income",
         "affected_rows": 15, "recommended_action": "Impute"},
        {"rule_id": "INVALID_RANGE", "severity": "Blocking",
         "category": "Range Violation", "affected_column": "age",
         "affected_rows": 2, "recommended_action": "Filter negative ages"},
        {"rule_id": "OUTLIER_IQR", "severity": "Warning",
         "category": "Outlier", "affected_column": "income",
         "affected_rows": 8, "recommended_action": "Review"},
        {"rule_id": "DUP_ROW", "severity": "Warning", "category": "Duplicate",
         "affected_column": None, "affected_rows": 4,
         "recommended_action": "Remove duplicates"},
    ],
}


def test_latest_format_is_loaded():
    loaded = load_quality_report(LATEST)
    assert len(loaded["detected_issues"]) == 4
    assert all(i["dataset"] == "hr_attrition.csv"
               for i in loaded["detected_issues"])
    assert "Missing Values" in loaded["detected_issues"][0]["description"]


def test_table_level_markers_have_no_column():
    for marker in (None, "N/A", "null", ""):
        loaded = load_quality_report({"issues": [
            {"rule_id": "DUP_ROW", "severity": "Warning",
             "affected_column": marker, "affected_rows": 1}]})
        assert loaded["detected_issues"][0]["column"] is None
    assert issues_by_column({"issues": [
        {"rule_id": "DUP_ROW", "severity": "Warning",
         "affected_column": "N/A", "affected_rows": 1}]}) == {}


def test_latest_format_changes_the_ranking_as_agreed():
    suggestions = suggest_targets(base_report())
    report = {"dataset": "d.csv", "issues": [
        {"rule_id": "INVALID_RANGE", "severity": "Blocking",
         "affected_column": "age", "affected_rows": 2},
        {"rule_id": "NULL_CHECK", "severity": "Blocking",
         "affected_column": "income", "affected_rows": 15}]}
    after = apply_quality_to_suggestions(suggestions, report, "d.csv")
    assert row_for(after, "age")["priority"] == "Blocked by quality"
    assert row_for(after, "income")["priority"] != "Blocked by quality"
    assert row_for(after, "income")["score"] == row_for(
        suggestions, "income")["score"]


def test_report_for_a_different_dataset_is_not_applied():
    suggestions = suggest_targets(base_report())
    report = {"dataset": "other.csv", "issues": [
        {"rule_id": "INVALID_RANGE", "severity": "Blocking",
         "affected_column": "age", "affected_rows": 2}]}
    after = apply_quality_to_suggestions(suggestions, report, "d.csv")
    assert row_for(after, "age")["priority"] != "Blocked by quality"


def test_report_with_several_datasets_in_one_file():
    report = load_quality_report([
        {"dataset": "A.xlsx", "total_rows": 5, "issues": [
            {"rule_id": "NULL_CHECK", "severity": "Error",
             "affected_column": "x", "affected_rows": 2}]},
        {"dataset": "B.xlsx", "total_rows": 3, "issues": []},
    ])
    assert len(report["detected_issues"]) == 1
    assert report["detected_issues"][0]["dataset"] == "A.xlsx"
