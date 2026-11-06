import pandas as pd

from analyze_semantics import analyze_dataframe
from make_synthetic_datasets import build
from target_suggestions import suggest_targets


def make_report(rows, dataset="d.csv", row_count=100):
    full = []
    for column, semantic_type, unique, non_null in rows:
        full.append({
            "dataset": dataset, "column": column,
            "semantic_type": semantic_type, "unique_values": unique,
            "non_null_count": non_null, "row_count": row_count,
        })
    return pd.DataFrame(full)


def targets(result):
    real = result[result["candidate_target"] != "(no target)"]
    return real["candidate_target"].tolist()


def row_for(result, column):
    return result[result["candidate_target"] == column].iloc[0]


def test_excluded_columns_never_suggested():
    report = make_report([
        ("customer_id", "identifier", 100, 100),
        ("notes", "text", 100, 100),
        ("ModifiedDate", "date", 50, 100),
        ("rowguid", "identifier", 100, 100),
        ("churn", "boolean_flag", 2, 100),
    ])
    assert targets(suggest_targets(report)) == ["churn"]


def test_constant_and_mostly_empty_columns_excluded():
    report = make_report([
        ("constant_col", "numerical_measure", 1, 100),
        ("empty_col", "unknown", 0, 0),
        ("mostly_empty", "numerical_measure", 10, 10),
        ("amount", "numerical_measure", 50, 100),
    ])
    assert targets(suggest_targets(report)) == ["amount"]


def test_missing_values_lower_the_score_and_warn():
    report = make_report([
        ("clean", "numerical_measure", 50, 100),
        ("gappy", "numerical_measure", 50, 50),
    ])
    result = suggest_targets(report)
    assert row_for(result, "clean")["score"] > row_for(result, "gappy")["score"]
    assert "missing" in row_for(result, "gappy")["warnings"]


def test_cardinality_changes_problem_type_and_score():
    report = make_report([
        ("binary", "categorical", 2, 100),
        ("many", "categorical", 67, 100),
    ])
    result = suggest_targets(report)
    assert row_for(result, "binary")["suggested_problem_type"] == (
        "binary_classification")
    assert row_for(result, "many")["suggested_problem_type"] == (
        "multiclass_classification")
    assert "67 classes" in row_for(result, "many")["warnings"]
    assert row_for(result, "binary")["score"] > row_for(result, "many")["score"]


def test_no_hard_coded_hr_columns():
    report = make_report([
        ("VacationHours", "numerical_measure", 100, 100),
        ("SickLeaveHours", "numerical_measure", 51, 100),
        ("Other", "numerical_measure", 60, 100),
    ], dataset="HumanResources.Employee.xlsx")
    assert set(targets(suggest_targets(report))) == {
        "VacationHours", "SickLeaveHours", "Other"}


def test_no_outcome_name_means_no_top_suggestion():
    report = make_report([
        ("score", "numerical_measure", 50, 100),
        ("status", "categorical", 3, 100),
        ("level", "categorical", 5, 100),
    ])
    result = suggest_targets(report)
    assert "Top suggestion" not in result["priority"].tolist()
    assert "confirm the business objective" in row_for(
        result, "score")["warnings"]


def test_override_always_wins():
    report = make_report([
        ("churn", "boolean_flag", 2, 100),
        ("age", "numerical_measure", 50, 100),
    ])
    result = suggest_targets(report, overrides={"d.csv": "age"})
    first = result.iloc[0]
    assert first["candidate_target"] == "age"
    assert first["priority"] == "User-selected"
    assert "Top suggestion" not in result["priority"].tolist()


def test_override_on_bad_column_is_handled_safely():
    report = make_report([("churn", "boolean_flag", 2, 100)])
    result = suggest_targets(report, overrides={"d.csv": "typo"})
    first = result.iloc[0]
    assert first["candidate_target"] == "typo"
    assert "not found" in first["warnings"]


def test_override_on_excluded_column_warns_but_is_honoured():
    report = make_report([
        ("customer_id", "identifier", 100, 100),
        ("churn", "boolean_flag", 2, 100),
    ])
    result = suggest_targets(report, overrides={"d.csv": "customer_id"})
    first = result.iloc[0]
    assert first["candidate_target"] == "customer_id"
    assert "identifier" in first["warnings"]


def test_forecasting_signal_when_date_column_present():
    report = make_report([
        ("date", "date", 24, 100),
        ("units_sold", "numerical_measure", 80, 100),
    ])
    result = suggest_targets(report)
    assert "forecasting" in row_for(result, "units_sold")[
        "alternative_problem_types"]


def test_clustering_offered_when_enough_features():
    report = make_report([
        ("a", "numerical_measure", 50, 100),
        ("b", "numerical_measure", 50, 100),
        ("c", "numerical_measure", 50, 100),
    ])
    result = suggest_targets(report)
    assert "clustering" in result["suggested_problem_type"].tolist()


def test_sensitive_columns_are_penalised():
    report = make_report([("gender", "categorical", 2, 100)])
    report["sensitive"] = True
    assert "fairness" in suggest_targets(report).iloc[0]["warnings"]


def test_two_datasets_are_ranked_separately():
    first = make_report([("churn", "boolean_flag", 2, 100)], dataset="a.csv")
    second = make_report([("price", "financial_amount", 90, 100)],
                         dataset="b.csv")
    result = suggest_targets(pd.concat([first, second]))
    tops = result[result["priority"] == "Top suggestion"]
    assert set(tops["candidate_target"]) == {"churn", "price"}


# End-to-end on the synthetic suite (detector + ranking together)
def run_pipeline(name):
    frame = build()[name]
    report = pd.DataFrame(analyze_dataframe(name, frame))
    return report, suggest_targets(report)


def test_synthetic_churn_classification():
    report, result = run_pipeline("churn_classification.csv")
    types = dict(zip(report["column"], report["semantic_type"]))
    assert types["customer_id"] == "identifier"
    assert types["email"] == "email"
    assert types["contact"] == "phone"
    assert types["signup_date"] == "date"
    top = result[result["priority"] == "Top suggestion"].iloc[0]
    assert top["candidate_target"] == "churn"
    assert top["suggested_problem_type"] == "binary_classification"


def test_synthetic_house_price_regression():
    _, result = run_pipeline("house_price_regression.csv")
    top = result[result["priority"] == "Top suggestion"].iloc[0]
    assert top["candidate_target"] == "price"
    assert top["suggested_problem_type"] == "regression"


def test_synthetic_sales_forecasting():
    _, result = run_pipeline("sales_forecasting.csv")
    top_names = result[result["priority"].isin(
        ["Top suggestion", "Alternative"])]["candidate_target"].tolist()
    assert "units_sold" in top_names and "revenue" in top_names
    assert "forecasting" in row_for(result, "units_sold")[
        "alternative_problem_types"]


def test_synthetic_clustering_has_no_clear_target():
    _, result = run_pipeline("customer_segments_clustering.csv")
    assert "Top suggestion" not in result["priority"].tolist()
    assert "clustering" in result["suggested_problem_type"].tolist()


def test_synthetic_ambiguous_columns():
    report, result = run_pipeline("ambiguous_targets.csv")
    types = dict(zip(report["column"], report["semantic_type"]))
    assert types["pct_complete"] == "percentage"
    assert types["is_active"] == "boolean_flag"
    assert types["notes"] == "text"
    names = targets(result)
    for excluded in ("record_id", "notes", "constant_col", "empty_col"):
        assert excluded not in names
    assert "missing" in row_for(result, "amount")["warnings"]
    assert "Top suggestion" not in result["priority"].tolist()


def test_birth_and_hire_dates_are_not_a_forecasting_axis():
    report = make_report([
        ("BirthDate", "date", 90, 100),
        ("HireDate", "date", 80, 100),
        ("VacationHours", "numerical_measure", 60, 100),
    ])
    result = suggest_targets(report)
    assert "forecasting" not in row_for(result, "VacationHours")[
        "alternative_problem_types"]
