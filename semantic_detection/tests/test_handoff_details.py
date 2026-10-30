from handoff_details import (
    class_distribution,
    feature_type_counts,
    missing_summary,
    preprocessing_hint,
    target_statistics,
    time_info,
    validation_warnings,
)


def column(name="y", dtype="int64", unique=2, missing=0, pct=0.0, **extra):
    base = {"name": name, "dtype": dtype, "unique_count": unique,
            "missing_count": missing, "missing_pct": pct}
    base.update(extra)
    return base


def test_class_distribution_from_top_values():
    col = column(unique=2, top_values=[
        {"value": "yes", "count": 90, "percentage": 90.0},
        {"value": "no", "count": 10, "percentage": 10.0}])
    items, note = class_distribution(col)
    assert [i["value"] for i in items] == ["yes", "no"]
    assert note is None


def test_class_distribution_notes_a_truncated_list():
    col = column(unique=30, top_values=[
        {"value": str(i), "count": 5, "percentage": 3.0} for i in range(5)])
    items, note = class_distribution(col)
    assert len(items) == 5 and "Top 5 of 30" in note
    stats = target_statistics(col, "categorical", "multiclass_classification")
    assert stats["minority_class_pct"] is None


def test_class_distribution_from_a_zero_one_mean():
    col = column(summary={"min": 0, "max": 1, "mean": 0.2})
    items, note = class_distribution(col)
    assert items[0] == {"value": "0", "percentage": 80.0}
    assert items[1]["percentage"] == 20.0
    assert "Derived" in note


def test_class_distribution_not_available_is_said_plainly():
    items, note = class_distribution(column(unique=3))
    assert items is None and "not available" in note


def test_numerical_target_statistics():
    col = column("price", "float64", unique=90,
                 summary={"min": 1.0, "max": 9.0, "mean": 5.0,
                          "median": 5.0, "std": 2.0})
    stats = target_statistics(col, "financial_amount", "regression")
    assert stats["numerical_statistics"]["mean"] == 5.0
    assert stats["class_distribution"] is None


def test_no_target_column_gives_none():
    assert target_statistics(None, "x", "regression") is None


def test_preprocessing_hints():
    assert "one-hot" in preprocessing_hint(
        "feature", "categorical", 4, 0, False).lower()
    assert "many values" in preprocessing_hint(
        "feature", "categorical", 80, 0, False)
    assert "impute" in preprocessing_hint(
        "feature", "numerical_measure", 50, 12.5, False).lower()
    assert "0/1" in preprocessing_hint(
        "feature", "boolean_flag", 2, 0, False)
    assert "time index" in preprocessing_hint("date", "date", 90, 0, True)
    assert "age" in preprocessing_hint("date", "date", 90, 0, False)
    assert "Do not use" in preprocessing_hint(
        "identifier", "identifier", 90, 0, False)
    assert "Drop" in preprocessing_hint("excluded", "unknown", 0, 0, False)
    assert "Text" in preprocessing_hint("text", "text", 90, 0, False)
    assert "labels" in preprocessing_hint(
        "target", "boolean_flag", 2, 0, False, "binary_classification")


def test_time_info_estimates_frequency_and_admits_unknown_gaps():
    cols = {"d": column("d", "datetime64[us]", unique=12, summary={
        "min": "2023-01-01 00:00:00", "max": "2023-12-01 00:00:00"})}
    info = time_info(cols, ["d"])[0]
    assert info["estimated_frequency"] == "monthly"
    assert "Not available" in info["gaps"]
    assert time_info(cols, ["missing"]) == []


def test_validation_warnings():
    roles = [{"role": "feature", "semantic_type": "categorical",
              "column": "c", "unique_values": 120, "quality_blocked": False}]
    stats = {"missing_count": 3, "missing_pct": 1.5, "minority_class_pct": 4.0}
    facts = {"row_count": 20, "duplicate_row_count": 2}
    text = " ".join(validation_warnings(
        facts, roles, stats, "binary_classification"))
    for expected in ("Only 1 usable", "Small dataset", "2 duplicate rows",
                     "Target has 1.5% missing", "Class imbalance",
                     "high cardinality"):
        assert expected in text
    other = dict(roles[0], column="d", unique_values=3)
    assert validation_warnings(
        {"row_count": 500, "duplicate_row_count": 0},
        roles + [other], None, "regression") == [
            "Feature 'c' has 120 distinct values (high cardinality)."]


def test_counts_and_missing_summary():
    roles = [
        {"role": "feature", "semantic_type": "numerical_measure",
         "missing_count": 2, "missing_pct": 1.0, "column": "a"},
        {"role": "feature", "semantic_type": "categorical",
         "missing_count": 0, "missing_pct": 0.0, "column": "b"},
        {"role": "identifier", "semantic_type": "identifier",
         "missing_count": 0, "missing_pct": 0.0, "column": "id"},
    ]
    assert feature_type_counts(roles) == {
        "numerical": 1, "categorical": 1, "boolean": 0, "other": 0}
    assert missing_summary(roles) == [
        {"column": "a", "missing_count": 2, "missing_pct": 1.0}]


# Machine-readable preprocessing actions (29 Oct, Sinchana's question 4)
from handoff_details import PREPROCESSING_ACTIONS, preprocessing_actions


def acts(role, kind="numerical_measure", unique=50, missing=0.0,
         axis=False, problem=None, privacy=False):
    return preprocessing_actions(role, kind, unique, missing, axis,
                                 problem, privacy)


def test_actions_for_each_role():
    assert acts("identifier") == ["do_not_use_as_input", "keep_for_join"]
    assert acts("excluded") == ["drop"]
    assert acts("text", "text") == ["text_processing"]
    assert acts("time", "time") == ["extract_time_parts"]
    assert acts("date", "date", axis=True) == ["time_index"]
    assert acts("date", "date", axis=False) == ["extract_date_features"]
    assert acts("target", problem="regression") == ["use_as_target"]
    assert acts("target", "boolean_flag", problem="binary_classification") \
        == ["use_as_target", "label_encode"]


def test_actions_for_feature_types():
    assert acts("feature") == ["scale_numeric"]
    assert acts("feature", "boolean_flag", 2) == ["encode_binary"]
    assert acts("feature", "categorical", 5) == ["one_hot_encode"]
    assert acts("feature", "categorical", 60) == [
        "group_rare_categories", "frequency_or_target_encode"]
    assert acts("feature", "percentage") == [
        "convert_percentage_to_number", "scale_numeric"]
    assert acts("feature", missing=12.0) == ["impute", "scale_numeric"]


def test_privacy_review_comes_first_and_every_value_is_allowed():
    result = acts("feature", "categorical", 2, privacy=True)
    assert result[0] == "privacy_review_before_use"
    for role in ("target", "feature", "identifier", "excluded", "text",
                 "time", "date"):
        for value in acts(role, privacy=True, missing=5.0):
            assert value in PREPROCESSING_ACTIONS
