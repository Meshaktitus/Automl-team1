"""Missing, ambiguous and poorly populated targets/columns (Wed 28 Oct)."""
import pytest

from run_detection import detect_dataset, run_detection
from test_profiling_integration import col, profile

N = {"min": 0.0, "max": 9.0, "mean": 4.0, "median": 4.0, "std": 2.0}
BASE = [
    col("id", "numerical", ident=True, unique=100),
    col("a", "numerical", "float64", unique=80, summary=N),
    col("b", "numerical", "float64", unique=70, summary=N),
    col("c", "categorical", "str", unique=3,
        top=[{"value": "x", "count": 50, "percentage": 50.0}]),
]


def run(extra=(), rows=100, override=None, **kw):
    cols = list(BASE) + list(extra)
    if override:
        kw["overrides"] = {"d.xlsx": override}
    return detect_dataset(profile(cols, rows=rows), **kw)


def words(result):
    return " ".join(result["warnings"])


def test_target_mostly_missing_is_not_recommended():
    r = run([col("t", "numerical", "float64", unique=8, missing=90,
                 pct=90.0, summary=N)], override="t")
    assert r["problem_type"] == "review_required"
    assert "90% missing" in words(r)


def test_all_missing_target_is_not_recommended():
    r = run([col("t", "numerical", "float64", unique=0, missing=100,
                 pct=100.0)], override="t")
    assert r["problem_type"] == "review_required"
    assert "100% missing" in words(r)


def test_partly_missing_target_gets_a_warning_and_lower_confidence():
    full = run([col("t", "numerical", "int64", unique=2, summary=N)],
               override="t")
    part = run([col("t", "numerical", "int64", unique=2, missing=40,
                    pct=40.0, summary=N)], override="t")
    assert part["problem_type"] == full["problem_type"]
    assert part["confidence"] == pytest.approx(full["confidence"] - 0.15)
    assert "40% missing" in words(part)


def test_small_missing_share_is_not_warned_about():
    r = run([col("t", "numerical", "int64", unique=2, missing=10, pct=10.0,
                 summary=N)], override="t")
    assert "missing" not in words(r)


def test_constant_target_is_not_recommended():
    r = run([col("t", "numerical", "int64", unique=1, summary=N,
                 warnings=["CONSTANT_COLUMN"])], override="t")
    assert r["problem_type"] == "review_required"
    assert "nothing to learn" in words(r)


def test_mixed_type_column_cannot_be_a_target_or_a_feature():
    r = run([col("t", "mixed", "object", unique=20)], override="t")
    assert r["problem_type"] == "review_required"
    roles = {x["column"]: x for x in r["column_roles"]}
    r2 = run([col("m", "mixed", "object", unique=20)])
    roles2 = {x["column"]: x for x in r2["column_roles"]}
    assert roles2["m"]["role"] == "excluded"
    assert "m" not in r2["feature_columns"]
    assert roles["t"]["semantic_type"] == "unknown"


@pytest.mark.parametrize("name,extra", [
    ("text", col("t", "text", "str", unique=100,
                 summary={"avg_length": 50.0, "max_length": 90})),
    ("date", col("t", "datetime", "datetime64[us]", unique=90,
                 summary={"min": "2020-01-01 00:00:00",
                          "max": "2021-01-01 00:00:00"})),
])
def test_unpredictable_target_types_are_flagged(name, extra):
    r = run([extra], override="t")
    assert r["problem_type"] == "review_required"
    assert "cannot be predicted directly" in words(r)


def test_identifier_target_is_flagged():
    r = run(override="id")
    assert r["problem_type"] == "review_required"
    assert "cannot be predicted directly" in words(r)


def test_override_for_a_missing_column_is_reported_not_crashed():
    r = run(override="nope")
    assert "not found" in words(r)
    assert r["problem_type"] == "review_required"


def test_two_outcome_like_columns_still_need_confirmation():
    r = run([col("churn", "boolean", "int64", unique=2),
             col("churned", "boolean", "int64", unique=2)])
    assert r["needs_confirmation"]
    assert r["target"] in {"churn", "churned"}


def test_goal_that_does_not_fit_the_data_is_explained():
    r = run(goal="forecast sales next month")
    assert r["problem_type"] == "review_required"
    assert "does not fit" in words(r)


def test_unknown_problem_type_override_is_rejected_safely():
    r = run(problem_type_override="magic")
    assert r["problem_type"] == "review_required"
    assert "Unsupported" in words(r)


def test_all_columns_empty_asks_for_confirmation():
    cols = [col(f"e{i}", "empty", "float64", unique=0, missing=100,
                pct=100.0, warnings=["EMPTY_COLUMN"]) for i in range(3)]
    r = detect_dataset(profile(cols))
    assert r["problem_type"] == "review_required"
    assert r["feature_columns"] == []


def test_single_column_and_tiny_datasets_do_not_crash():
    one = detect_dataset(profile([col("a", "numerical", "float64",
                                      unique=80, summary=N)]))
    tiny = detect_dataset(profile(
        [col("a", "numerical", "float64", unique=3, summary=N),
         col("b", "categorical", "str", unique=2)], rows=3))
    assert one["problem_type"] == tiny["problem_type"] == "review_required"
    assert any("small" in w.lower() for w in
               tiny["dataset_characteristics"]["validation_warnings"])


def test_zero_row_profile_does_not_crash():
    r = detect_dataset(profile(
        [col("a", "numerical", "float64", unique=0)], rows=0))
    assert r["problem_type"] == "review_required"


def test_numeric_columns_without_summary_do_not_crash():
    r = detect_dataset(profile([
        col("a", "numerical", "float64", unique=80),
        col("b", "numerical", "float64", unique=70)]))
    assert r["problem_type"] == "review_required"


def test_profile_without_columns_gives_a_clear_result_not_a_crash():
    empty = profile([], name="empty.xlsx")
    good = profile(BASE, name="good.xlsx")
    results = run_detection([empty, good])
    by = {r["dataset"]: r for r in results}
    assert "no columns" in " ".join(by["empty.xlsx"]["warnings"])
    assert by["empty.xlsx"]["problem_type"] == "review_required"
    assert by["good.xlsx"]["feature_columns"]


def test_no_profiles_is_still_rejected():
    with pytest.raises(ValueError):
        run_detection([])


def _binary_profile(distribution=None):
    cols = [col("id", "numerical", ident=True, unique=100),
            col("a", "numerical", "float64", unique=80, summary=N),
            col("churn", "categorical", "str", unique=2,
                top=[{"value": "no", "count": 90, "percentage": 90.0}])]
    p = profile(cols)
    if distribution:
        p["class_distribution"] = distribution
    return p


GIVEN = {"target_column": "churn", "class_count": 2,
         "classes": [{"value": "no", "count": 90, "percentage": 90.0},
                     {"value": "yes", "count": 10, "percentage": 10.0}],
         "majority_class": "no", "minority_class": "yes",
         "imbalance_ratio": 9.0, "missing_count": 0}


def test_full_class_distribution_from_profiling_is_used():
    r = detect_dataset(_binary_profile(GIVEN), overrides={"d.xlsx": "churn"})
    stats = r["target_statistics"]
    assert [c["value"] for c in stats["class_distribution"]] == ["no", "yes"]
    assert stats["minority_class_pct"] == 10.0


def test_class_distribution_for_another_column_is_ignored():
    other = dict(GIVEN, target_column="something_else")
    r = detect_dataset(_binary_profile(other), overrides={"d.xlsx": "churn"})
    assert r["target_statistics"]["minority_class_pct"] is None


# ---- failure handling in a multi-dataset run -------------------------------

def test_a_failed_profile_does_not_stop_the_other_datasets():
    failed = profile([], name="bad.xlsx")
    failed["status"] = "failed"
    failed["errors"] = [{"code": "SOURCE_NOT_FOUND", "message": "x",
                         "field": None}]
    results = run_detection([failed, profile(BASE, name="good.xlsx")])
    by = {r["dataset"]: r for r in results}
    assert "could not be used" in " ".join(by["bad.xlsx"]["warnings"])
    assert "SOURCE_NOT_FOUND" in " ".join(by["bad.xlsx"]["warnings"])
    assert by["good.xlsx"]["feature_columns"]


def test_wrong_schema_version_is_reported_per_dataset():
    wrong = profile(BASE, name="wrong.xlsx")
    wrong["schema_version"] = "9.9"
    results = run_detection([wrong, profile(BASE, name="good.xlsx")])
    by = {r["dataset"]: r for r in results}
    assert "schema_version" in " ".join(by["wrong.xlsx"]["warnings"])
    assert by["good.xlsx"]["feature_columns"]


def test_unreadable_profile_file_is_reported_not_raised(tmp_path):
    broken = tmp_path / "x.profile.json"
    broken.write_text("{not json", encoding="utf-8")
    results = run_detection([str(broken), profile(BASE, name="good.xlsx")])
    names = [r["dataset"] for r in results]
    assert "x.profile.json" in names and "good.xlsx" in names


def test_same_dataset_name_twice_uses_the_first_only():
    results = run_detection([profile(BASE, name="d.xlsx"),
                             profile(BASE, name="d.xlsx")])
    assert len(results) == 2
    assert "more than one profile" in " ".join(results[1]["warnings"])
    assert results[0]["feature_columns"] and not results[1]["feature_columns"]


def test_quality_finding_for_an_unknown_column_is_flagged():
    q = {"dataset": "d.xlsx", "issues": [
        {"rule_id": "INVALID_RANGE", "severity": "Blocking",
         "affected_column": "zzz", "affected_rows": 3}]}
    r = run(quality=q)
    assert "zzz" in words(r) and "ignored" in words(r)
    assert all(not x["quality_blocked"] for x in r["column_roles"])


# Sanjay's profiling warnings and failed profiles (Thu 29 Oct)
def test_failed_profile_keeps_its_dataset_id():
    bad = profile(BASE, status="failed")
    bad["dataset_reference"] = {"dataset_id": "HR.Broken",
                                "name": "HR.Broken.xlsx"}
    results = run_detection([profile(BASE), bad])
    broken = [r for r in results if r["dataset"] == "HR.Broken.xlsx"][0]
    assert broken["dataset_id"] == "HR.Broken"
    assert broken["problem_type"] == "review_required"
    assert "could not be used" in words(broken)


def test_class_distribution_skipped_warning_does_not_break_the_run():
    p = profile(BASE + [col("t", "numerical", "float64", unique=50,
                            summary=N)], status="warning")
    p["warnings"] = [{"code": "CLASS_DISTRIBUTION_SKIPPED",
                      "severity": "warning", "column": "t",
                      "message": "More than 20 distinct values."}]
    r = detect_dataset(p, overrides={"d.xlsx": "t"})
    assert r["target"] == "t" and r["problem_type"] == "regression"
    assert r["target_statistics"]["class_distribution"] is None


def test_numeric_target_with_few_values_uses_profile_class_distribution():
    p = profile(BASE + [col("flag", "numerical", "int64", unique=2,
                            summary={"min": 0.0, "max": 1.0, "mean": 0.2,
                                     "median": 0.0, "std": 0.4})])
    p["class_distribution"] = {
        "target_column": "flag", "class_count": 2,
        "classes": [{"value": 0, "count": 80, "percentage": 80.0},
                    {"value": 1, "count": 20, "percentage": 20.0}]}
    r = detect_dataset(p, overrides={"d.xlsx": "flag"})
    assert r["problem_type"] == "binary_classification"
    assert r["target_statistics"]["minority_class_pct"] == 20.0


def test_approved_features_can_be_given_by_dataset_id():
    p = profile(BASE)
    p["dataset_reference"] = {"dataset_id": "HR.D", "name": "d.xlsx"}
    for key in ("HR.D", "d.xlsx", "d"):
        r = run_detection([p], approved_features={key: ["a", "b"]})[0]
        assert r["approved_feature_columns"] == ["a", "b"], key
        assert r["features_status"] == "approved", key


# Privacy: sensitive columns are not recommended until reviewed (29 Oct)
def _with_sensitive():
    return profile(BASE + [col("gender", "categorical", "str", unique=2,
                               top=[{"value": "M", "count": 60,
                                     "percentage": 60.0}])])


def test_sensitive_feature_is_listed_but_not_recommended():
    r = detect_dataset(_with_sensitive(), overrides={"d.xlsx": "a"})
    assert "gender" in r["feature_columns"]
    assert "gender" not in r["recommended_feature_columns"]
    entry = [x for x in r["column_roles"] if x["column"] == "gender"][0]
    assert entry["needs_privacy_review"] is True
    assert entry["preprocessing_actions"][0] == "privacy_review_before_use"
    assert "privacy review" in words(r)


def test_sensitive_feature_can_be_used_when_the_user_approves_it():
    r = detect_dataset(_with_sensitive(), overrides={"d.xlsx": "a"},
                       approved_features=["gender", "b"])
    assert r["approved_feature_columns"] == ["gender", "b"]
    assert r["features_status"] == "approved"
