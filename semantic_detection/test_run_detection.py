import json

from run_detection import detect_dataset, run_detection
from test_profiling_integration import col, profile

NUM = {"min": 0.0, "max": 99.0}


def churn_profile(name="churn.xlsx"):
    return profile([
        col("customer_id", "numerical", unique=100, ident=True,
            summary={"min": 1.0, "max": 100.0}),
        col("monthly_charges", "numerical", "float64", unique=95,
            summary={"min": 20.0, "max": 120.0}),
        col("tenure_months", "numerical", unique=60,
            summary={"min": 1.0, "max": 72.0}),
        col("churn", "numerical", unique=2,
            summary={"min": 0.0, "max": 1.0}),
    ], name=name)


def sales_profile(name="sales.xlsx"):
    return profile([
        col("order_date", "datetime", "datetime64[us]", unique=100,
            summary={"min": "2023-01-01 00:00:00",
                     "max": "2023-04-10 00:00:00"}),
        col("units_sold", "numerical", unique=80,
            summary={"min": 5.0, "max": 200.0}),
        col("revenue", "numerical", "float64", unique=99,
            summary={"min": 1000.0, "max": 9000.0}),
    ], name=name)


def one(results, name):
    return next(r for r in results if r["dataset"] == name)


def test_top_suggestion_becomes_the_target_and_problem_type():
    result = run_detection([churn_profile()])[0]
    assert result["target"] == "churn"
    assert result["target_source"] == "top_suggestion"
    assert result["problem_type"] == "binary_classification"
    assert result["needs_confirmation"]
    assert result["candidates"][0]["candidate_target"] == "churn"
    assert "customer_id" not in [c["candidate_target"]
                                 for c in result["candidates"]]


def test_two_datasets_in_one_run():
    results = run_detection([churn_profile(), sales_profile()])
    assert {r["dataset"] for r in results} == {"churn.xlsx", "sales.xlsx"}
    assert one(results, "sales.xlsx")["target"] == "revenue"


def test_user_override_of_target_and_problem_type():
    results = run_detection(
        [churn_profile()], overrides={"churn.xlsx": "monthly_charges"},
        problem_type_override="regression")
    result = results[0]
    assert result["target"] == "monthly_charges"
    assert result["target_source"] == "user_override"
    assert result["problem_type"] == "regression"
    assert not result["needs_confirmation"]


def test_goal_gives_forecasting_when_the_data_fits():
    result = run_detection(
        [sales_profile()], goal="Forecast revenue next month")[0]
    assert result["problem_type"] == "forecasting"
    assert result["source"] == "business_goal"


def test_no_outcome_column_asks_for_confirmation():
    anon = profile([col(f"col{i}", "numerical", "float64", unique=90,
                        summary=NUM) for i in range(1, 5)], name="anon.xlsx")
    result = run_detection([anon])[0]
    assert result["target"] is None
    assert result["needs_confirmation"]
    assert "confirm the business objective" in " ".join(result["warnings"])


def test_quality_blocking_issue_on_target_lowers_confidence():
    base = run_detection([churn_profile()])[0]
    quality = {"detected_issues": [
        {"dataset": "churn.xlsx", "rule_id": "INVALID_RANGE",
         "column": "monthly_charges", "severity": "Blocking",
         "affected_rows": 2, "description": "negative charge"}]}
    after = run_detection([churn_profile()], quality=quality)[0]
    blocked = [c for c in after["candidates"]
               if c["candidate_target"] == "monthly_charges"][0]
    assert blocked["priority"] == "Blocked by quality"
    assert after["target"] == base["target"]


def test_quality_on_the_target_is_applied_to_the_problem():
    base = run_detection([churn_profile()])[0]
    quality = {"detected_issues": [
        {"dataset": "churn.xlsx", "rule_id": "INVALID_RANGE",
         "column": "churn", "severity": "High", "affected_rows": 3,
         "description": "bad labels"}]}
    after = run_detection([churn_profile()], quality=quality)[0]
    assert after["confidence"] < base["confidence"]


def test_issue_without_dataset_goes_to_the_only_dataset():
    quality = {"detected_issues": [
        {"rule_id": "INVALID_RANGE", "column": "churn",
         "severity": "High", "affected_rows": 3, "description": "x"}]}
    base = run_detection([churn_profile()])[0]
    after = run_detection([churn_profile()], quality=quality)[0]
    assert after["confidence"] < base["confidence"]


def test_issue_without_dataset_is_skipped_with_a_warning_when_ambiguous():
    quality = {"detected_issues": [
        {"rule_id": "INVALID_RANGE", "column": "churn",
         "severity": "High", "affected_rows": 3, "description": "x"}]}
    results = run_detection([churn_profile(), sales_profile()],
                            quality=quality)
    assert "no dataset" in " ".join(one(results, "churn.xlsx")["warnings"])
    routed = run_detection([churn_profile(), sales_profile()],
                           quality=quality, quality_dataset="churn.xlsx")
    base = run_detection([churn_profile()])[0]
    assert one(routed, "churn.xlsx")["confidence"] < base["confidence"]


def test_override_for_unknown_dataset_is_reported():
    results = run_detection([churn_profile()],
                            overrides={"other.xlsx": "x"})
    assert "not found" in " ".join(one(results, "other.xlsx")["warnings"])


def test_result_is_json_serialisable_and_has_the_agreed_fields():
    results = run_detection([churn_profile()])
    text = json.dumps(results)
    assert json.loads(text)[0]["status"] == "Proposed, pending verification"
    assert set(results[0]) == {
        "dataset", "target", "target_source", "problem_type", "confidence",
        "source", "needs_confirmation", "evidence", "alternatives",
        "warnings", "candidates", "semantic_columns",
        "dataset_characteristics", "feature_columns", "column_roles",
        "leakage_checks", "status",
    }


def test_no_profiles_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        run_detection([])


def roles(result):
    return {r["column"]: r for r in result["column_roles"]}


def test_feature_columns_exclude_target_ids_dates_and_constants():
    prof = profile([
        col("emp_id", "numerical", unique=100, ident=True,
            summary={"min": 1.0, "max": 100.0}),
        col("salary", "numerical", "float64", unique=90,
            summary={"min": 1000.0, "max": 9000.0}),
        col("hire_date", "datetime", "datetime64[us]", unique=50,
            summary={"min": "2010-01-01 00:00:00",
                     "max": "2020-01-01 00:00:00"}),
        col("age", "numerical", unique=40, summary={"min": 20.0, "max": 60.0}),
        col("active", "numerical", unique=1, summary={"min": 1.0, "max": 1.0}),
    ], name="hr.xlsx")
    result = run_detection([prof], overrides={"hr.xlsx": "salary"})[0]
    got = roles(result)
    assert got["salary"]["role"] == "target"
    assert got["emp_id"]["role"] == "identifier"
    assert got["hire_date"]["role"] == "date"
    assert got["active"]["role"] == "excluded"
    assert result["feature_columns"] == ["age"]
    assert all(r["reason"] for r in result["column_roles"])


def test_dataset_characteristics():
    result = run_detection([churn_profile()])[0]
    facts = result["dataset_characteristics"]
    assert facts["row_count"] == 100
    assert facts["column_count"] == 4
    assert facts["duplicate_row_count"] == 0
    assert facts["identifier_columns"] == ["customer_id"]
    assert facts["feature_column_count"] == len(result["feature_columns"])


def test_time_axis_is_marked_on_date_columns():
    result = run_detection([sales_profile()])[0]
    assert roles(result)["order_date"]["time_axis"] is True
    assert result["dataset_characteristics"]["time_columns"] == ["order_date"]


def test_leakage_checks_are_reported_as_pending_not_done():
    result = run_detection([churn_profile()])[0]
    assert result["leakage_checks"]["status"] == "pending_integration"
    assert "correlation" in result["leakage_checks"]["reason"]


def test_blocking_quality_issue_is_flagged_on_the_column_role():
    quality = {"dataset": "churn.xlsx", "issues": [
        {"rule_id": "INVALID_RANGE", "severity": "Blocking",
         "affected_column": "tenure_months", "affected_rows": 2}]}
    result = run_detection([churn_profile()], quality=quality)[0]
    assert roles(result)["tenure_months"]["quality_blocked"] is True
    assert roles(result)["monthly_charges"]["quality_blocked"] is False


def test_null_check_blocking_does_not_flag_the_role():
    quality = {"dataset": "churn.xlsx", "issues": [
        {"rule_id": "NULL_CHECK", "severity": "Blocking",
         "affected_column": "tenure_months", "affected_rows": 2}]}
    result = run_detection([churn_profile()], quality=quality)[0]
    assert roles(result)["tenure_months"]["quality_blocked"] is False
    assert roles(result)["tenure_months"]["quality_issues"] == [
        "NULL_CHECK (blocking)"]


def test_detect_dataset_returns_one_result():
    result = detect_dataset(churn_profile())
    assert isinstance(result, dict)
    assert result["dataset"] == "churn.xlsx"


def test_quality_penalties_are_configurable():
    quality = {"dataset": "churn.xlsx", "issues": [
        {"rule_id": "INVALID_RANGE", "severity": "Blocking",
         "affected_column": "monthly_charges", "affected_rows": 2}]}
    default = run_detection([churn_profile()], quality=quality)[0]
    softer = run_detection(
        [churn_profile()], quality=quality,
        quality_settings={"score_factor": {"blocking": 0.5}})[0]

    def score(result):
        return [c for c in result["candidates"]
                if c["candidate_target"] == "monthly_charges"][0]["score"]
    assert score(default) == 0
    assert score(softer) == 35.0


def test_unknown_quality_setting_is_rejected():
    import pytest
    quality = {"dataset": "churn.xlsx", "issues": []}
    with pytest.raises(ValueError):
        run_detection([churn_profile()], quality=quality,
                      quality_settings={"nonsense": {"medium": 1}})
    with pytest.raises(ValueError):
        run_detection([churn_profile()], quality=quality,
                      quality_settings={"score_factor": {"huge": 1}})
