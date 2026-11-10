"""Cross-domain checks: the same code, datasets that are not HR.

Each case builds a table, runs analyze_dataframe -> suggest_targets ->
detect_problem, and checks the expected target and problem type, plus
overrides and alternatives.
"""
import numpy as np
import pandas as pd
import pytest

from analyze_semantics import analyze_dataframe
from problem_detection import detect_problem
from target_suggestions import suggest_targets

RNG = np.random.default_rng(7)
N = 200


def report(name, df):
    return pd.DataFrame(analyze_dataframe(name, df))


def healthcare():
    return pd.DataFrame({
        "patient_no": [f"P{i:05d}" for i in range(N)],
        "age": RNG.integers(18, 90, N),
        "bmi": RNG.normal(27, 5, N).round(1),
        "glucose": RNG.normal(110, 25, N).round(1),
        "smoker": RNG.choice(["Y", "N"], N),
        "diagnosis": RNG.choice(["diabetes", "asthma", "hypertension"], N),
        "readmitted": RNG.choice([0, 1], N),
    })


def banking():
    return pd.DataFrame({
        "loan_id": np.arange(1000, 1000 + N),
        "annual_income": RNG.integers(20000, 150000, N),
        "loan_amount": RNG.integers(1000, 50000, N),
        "credit_score": RNG.integers(300, 850, N),
        "employment_status": RNG.choice(["salaried", "self", "retired"], N),
        "default": RNG.choice(["yes", "no"], N),
    })


def telecom():
    return pd.DataFrame({
        "CustomerID": [f"C-{i}" for i in range(N)],
        "tenure_months": RNG.integers(1, 72, N),
        "monthly_charges": RNG.normal(65, 20, N).round(2),
        "contract_type": RNG.choice(["monthly", "yearly", "two-year"], N),
        "Churn": RNG.choice(["Yes", "No"], N),
    })


def education():
    return pd.DataFrame({
        "student_id": np.arange(1, N + 1),
        "attendance_pct": [f"{x}%" for x in RNG.integers(50, 100, N)],
        "study_hours": RNG.normal(10, 3, N).round(1),
        "grade": RNG.choice(["A", "B", "C", "D"], N),
        "final_score": RNG.integers(0, 101, N),
    })


def retail_sales():
    dates = pd.date_range("2023-01-01", periods=N, freq="D")
    return pd.DataFrame({
        "order_date": dates,
        "store": RNG.choice(["north", "south", "east"], N),
        "units_sold": RNG.integers(5, 200, N),
        "revenue": RNG.normal(5000, 900, N).round(2),
    })


def anonymous():
    return pd.DataFrame({f"col{i}": RNG.normal(0, 1, N) for i in range(1, 6)})


def with_empty_column():
    df = healthcare()
    df["notes_blank"] = np.nan
    return df


CASES = [
    ("healthcare.csv", healthcare, "readmitted", "binary_classification"),
    ("banking.csv", banking, "default", "binary_classification"),
    ("telecom.csv", telecom, "Churn", "binary_classification"),
    ("education.csv", education, "final_score", "regression"),
    ("retail.csv", retail_sales, "revenue", "regression"),
]


@pytest.mark.parametrize("name, build, target, problem", CASES)
def test_outcome_column_is_the_top_suggestion(name, build, target, problem):
    rep = report(name, build())
    top = suggest_targets(rep)
    top = top[top["priority"] == "Top suggestion"]
    assert list(top["candidate_target"]) == [target]


@pytest.mark.parametrize("name, build, target, problem", CASES)
def test_problem_type_for_the_target(name, build, target, problem):
    rep = report(name, build())
    result = detect_problem(rep, name, target=target)
    assert result["problem_type"] == problem
    assert result["needs_confirmation"]


@pytest.mark.parametrize("name, build, target, problem", CASES)
def test_identifier_columns_are_never_targets(name, build, target, problem):
    rep = report(name, build())
    types = dict(zip(rep["column"], rep["semantic_type"]))
    ids = {c for c, t in types.items() if t == "identifier"}
    got = set(suggest_targets(rep)["candidate_target"])
    assert not ids & got


@pytest.mark.parametrize("name, build, target, problem", CASES)
def test_user_override_wins_on_every_dataset(name, build, target, problem):
    rep = report(name, build())
    other = next(c for c in suggest_targets(rep)["candidate_target"]
                 if c != target and c != "(no target)")
    out = suggest_targets(rep, overrides={name: other})
    first = out[out["dataset"] == name].iloc[0]
    assert first["candidate_target"] == other
    assert first["priority"] == "User-selected"
    forced = detect_problem(rep, name, target=target,
                            problem_type_override="regression")
    assert forced["problem_type"] == "regression"
    assert not forced["needs_confirmation"]


def test_alternatives_are_offered():
    rep = report("education.csv", education())
    out = suggest_targets(rep)
    assert (out["priority"] == "Alternative").any() or \
        (out["priority"] == "Candidate").any()
    assert out["candidate_target"].nunique() >= 3


def test_forecasting_goal_on_retail_data():
    rep = report("retail.csv", retail_sales())
    result = detect_problem(rep, "retail.csv", target="revenue",
                            business_goal="Forecast revenue next month")
    assert result["problem_type"] == "forecasting"


def test_attendance_percent_text_is_a_percentage():
    rep = report("education.csv", education())
    types = dict(zip(rep["column"], rep["semantic_type"]))
    assert types["attendance_pct"] == "percentage"


def test_clustering_goal_on_banking_data():
    rep = report("banking.csv", banking())
    result = detect_problem(rep, "banking.csv",
                            business_goal="Segment my customers")
    assert result["problem_type"] == "clustering"


def test_anonymous_columns_do_not_crash_and_need_confirmation():
    rep = report("anon.csv", anonymous())
    out = suggest_targets(rep)
    assert not (out["priority"] == "Top suggestion").any()
    result = detect_problem(rep, "anon.csv")
    assert result["needs_confirmation"]


def test_empty_column_is_not_a_target_candidate():
    rep = report("hc_empty.csv", with_empty_column())
    out = suggest_targets(rep)
    assert "notes_blank" not in set(out["candidate_target"])
