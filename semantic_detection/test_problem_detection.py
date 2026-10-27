import pandas as pd

from analyze_semantics import analyze_dataframe
from make_synthetic_datasets import build
from problem_detection import detect_problem


def make_report(rows, dataset="d.csv"):
    full = []
    for column, semantic_type, unique in rows:
        full.append({
            "dataset": dataset, "column": column,
            "semantic_type": semantic_type, "unique_values": unique,
            "non_null_count": 100, "row_count": 100,
        })
    return pd.DataFrame(full)


def alt_names(result):
    return [a["problem_type"] for a in result["alternatives"]]


def synthetic(name):
    return pd.DataFrame(analyze_dataframe(name, build()[name]))


# Data rules
def test_binary_target_is_binary_classification():
    report = make_report([("churn", "boolean_flag", 2),
                          ("age", "numerical_measure", 50)])
    result = detect_problem(report, "d.csv", target="churn")
    assert result["problem_type"] == "binary_classification"
    assert result["needs_confirmation"]


def test_categorical_target_is_multiclass():
    report = make_report([("city", "categorical", 4)])
    assert detect_problem(report, "d.csv", target="city")[
        "problem_type"] == "multiclass_classification"


def test_numeric_target_is_regression():
    report = make_report([("price", "financial_amount", 90)])
    assert detect_problem(report, "d.csv", target="price")[
        "problem_type"] == "regression"


def test_many_classes_lower_confidence_and_warn():
    report = make_report([("a", "categorical", 4), ("b", "categorical", 67)])
    few = detect_problem(report, "d.csv", target="a")
    many = detect_problem(report, "d.csv", target="b")
    assert many["confidence"] < few["confidence"]
    assert "67 classes" in " ".join(many["warnings"])


def test_few_distinct_numbers_suggest_classification_alternative():
    report = make_report([("rating", "numerical_measure", 5)])
    result = detect_problem(report, "d.csv", target="rating")
    assert result["problem_type"] == "regression"
    assert "multiclass_classification" in alt_names(result)


def test_time_column_adds_forecasting_alternative():
    report = make_report([("date", "date", 24),
                          ("units", "numerical_measure", 80)])
    result = detect_problem(report, "d.csv", target="units")
    assert "forecasting" in alt_names(result)


def test_birth_and_hire_dates_are_not_a_time_axis():
    report = make_report([("BirthDate", "date", 90),
                          ("HireDate", "date", 80),
                          ("VacationHours", "numerical_measure", 60)])
    result = detect_problem(report, "d.csv", target="VacationHours")
    assert "forecasting" not in alt_names(result)


def test_no_target_offers_clustering_and_asks_confirmation():
    report = make_report([("a", "numerical_measure", 50),
                          ("b", "numerical_measure", 50),
                          ("c", "numerical_measure", 50)])
    result = detect_problem(report, "d.csv")
    assert result["problem_type"] == "review_required"
    assert "clustering" in alt_names(result)
    assert result["needs_confirmation"]


def test_unknown_dataset_and_unknown_target_are_handled():
    report = make_report([("a", "numerical_measure", 50)])
    assert "not found" in " ".join(
        detect_problem(report, "other.csv")["warnings"])
    assert "not found" in " ".join(
        detect_problem(report, "d.csv", target="zzz")["warnings"])


# Business goal
def test_goal_forecast_with_time_column_gives_forecasting():
    report = make_report([("date", "date", 24),
                          ("units", "numerical_measure", 80)])
    result = detect_problem(report, "d.csv", target="units",
                            business_goal="Forecast sales for next month")
    assert result["problem_type"] == "forecasting"
    assert result["source"] == "business_goal"
    assert not result["needs_confirmation"]


def test_goal_forecast_without_time_column_is_rejected_with_warning():
    report = make_report([("units", "numerical_measure", 80)])
    result = detect_problem(report, "d.csv", target="units",
                            business_goal="Forecast sales")
    assert result["problem_type"] == "regression"
    assert "does not fit" in " ".join(result["warnings"])


def test_goal_segment_gives_clustering():
    report = make_report([("a", "numerical_measure", 50),
                          ("b", "numerical_measure", 50),
                          ("c", "numerical_measure", 50)])
    result = detect_problem(report, "d.csv",
                            business_goal="Segment my customers")
    assert result["problem_type"] == "clustering"


def test_goal_segment_with_too_few_features_is_rejected():
    report = make_report([("a", "numerical_measure", 50)])
    result = detect_problem(report, "d.csv",
                            business_goal="Segment my customers")
    assert result["problem_type"] != "clustering"
    assert "does not fit" in " ".join(result["warnings"])


def test_goal_anomaly_gives_anomaly_detection():
    report = make_report([("a", "numerical_measure", 50),
                          ("b", "numerical_measure", 50)])
    result = detect_problem(report, "d.csv",
                            business_goal="Find unusual transactions")
    assert result["problem_type"] == "anomaly_detection"


def test_goal_recommend_needs_two_id_columns():
    report = make_report([("user_id", "identifier", 100),
                          ("item_id", "identifier", 50),
                          ("rating", "numerical_measure", 5)])
    result = detect_problem(report, "d.csv",
                            business_goal="Recommend products to users")
    assert result["problem_type"] == "recommendation"
    thin = make_report([("rating", "numerical_measure", 5)])
    assert detect_problem(thin, "d.csv",
                          business_goal="Recommend products")[
        "problem_type"] != "recommendation"


def test_conflicting_goal_stays_ambiguous():
    report = make_report([("date", "date", 24),
                          ("units", "numerical_measure", 80),
                          ("a", "numerical_measure", 50),
                          ("b", "numerical_measure", 50)])
    result = detect_problem(report, "d.csv", target="units",
                            business_goal="Forecast sales and segment "
                                          "customers")
    assert result["needs_confirmation"]
    assert result["confidence"] <= 0.5
    assert "several task types" in " ".join(result["warnings"])


def test_goal_that_agrees_with_target_raises_confidence():
    report = make_report([("churn", "boolean_flag", 2)])
    plain = detect_problem(report, "d.csv", target="churn")
    with_goal = detect_problem(report, "d.csv", target="churn",
                               business_goal="Which customers will churn?")
    assert with_goal["confidence"] > plain["confidence"]
    assert not with_goal["needs_confirmation"]


def test_goal_that_disagrees_with_target_warns():
    report = make_report([("price", "financial_amount", 90)])
    result = detect_problem(report, "d.csv", target="price",
                            business_goal="Classify houses as cheap or not")
    assert "classification" in " ".join(result["warnings"])
    assert result["needs_confirmation"]


# Override
def test_override_always_wins_over_goal_and_data():
    report = make_report([("churn", "boolean_flag", 2)])
    result = detect_problem(report, "d.csv", target="churn",
                            business_goal="Forecast churn next month",
                            problem_type_override="regression")
    assert result["problem_type"] == "regression"
    assert result["source"] == "user_override"
    assert result["confidence"] == 1.0
    assert not result["needs_confirmation"]


def test_override_that_does_not_fit_warns_but_is_honoured():
    report = make_report([("units", "numerical_measure", 80)])
    result = detect_problem(report, "d.csv", target="units",
                            problem_type_override="forecasting")
    assert result["problem_type"] == "forecasting"
    assert "may not fit" in " ".join(result["warnings"])


def test_unsupported_override_is_handled_safely():
    report = make_report([("a", "numerical_measure", 50)])
    result = detect_problem(report, "d.csv", target="a",
                            problem_type_override="magic")
    assert result["problem_type"] == "review_required"
    assert "Unsupported" in " ".join(result["warnings"])


# End to end on the synthetic suite
def test_synthetic_churn():
    result = detect_problem(synthetic("churn_classification.csv"),
                            "churn_classification.csv", target="churn")
    assert result["problem_type"] == "binary_classification"


def test_synthetic_house_price():
    result = detect_problem(synthetic("house_price_regression.csv"),
                            "house_price_regression.csv", target="price")
    assert result["problem_type"] == "regression"


def test_synthetic_sales_forecasting_goal():
    name = "sales_forecasting.csv"
    result = detect_problem(synthetic(name), name, target="units_sold",
                            business_goal="Forecast units sold next month")
    assert result["problem_type"] == "forecasting"
    assert any("date" in e for e in result["evidence"])


def test_synthetic_sales_without_goal_offers_forecasting_alternative():
    name = "sales_forecasting.csv"
    result = detect_problem(synthetic(name), name, target="units_sold")
    assert result["problem_type"] == "regression"
    assert "forecasting" in alt_names(result)


def test_synthetic_clustering_goal():
    name = "customer_segments_clustering.csv"
    result = detect_problem(synthetic(name), name,
                            business_goal="Segment my customers")
    assert result["problem_type"] == "clustering"


def test_synthetic_ambiguous_dataset_needs_confirmation():
    name = "ambiguous_targets.csv"
    result = detect_problem(synthetic(name), name, target="score")
    assert result["needs_confirmation"]


def test_synthetic_anomaly_goal():
    name = "transactions_anomaly.csv"
    result = detect_problem(synthetic(name), name,
                            business_goal="Find unusual transactions")
    assert result["problem_type"] == "anomaly_detection"
    assert not result["needs_confirmation"]


def test_synthetic_anomaly_without_goal_is_not_guessed():
    name = "transactions_anomaly.csv"
    result = detect_problem(synthetic(name), name)
    assert result["problem_type"] == "review_required"
    assert result["needs_confirmation"]


def test_synthetic_recommendation_goal():
    name = "ratings_recommendation.csv"
    report = synthetic(name)
    types = dict(zip(report["column"], report["semantic_type"]))
    assert types["user_id"] == "identifier"
    assert types["item_id"] == "identifier"
    assert types["rating"] == "numerical_measure"
    result = detect_problem(report, name,
                            business_goal="Recommend products to users")
    assert result["problem_type"] == "recommendation"
    assert not result["needs_confirmation"]


def test_recommendation_goal_rejected_on_data_without_id_pair():
    name = "house_price_regression.csv"
    result = detect_problem(synthetic(name), name, target="price",
                            business_goal="Recommend products to users")
    assert result["problem_type"] == "regression"
    assert "does not fit" in " ".join(result["warnings"])
