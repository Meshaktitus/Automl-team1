"""Tests for the proposed training-eligibility rules (contract 12.2) and
for the two flags target_confirmed / needs_confirmation (Example A)."""
from run_detection import run_detection
from test_run_detection import churn_profile, sales_profile
from training_rules import can_start_training, training_blockers

CHURN = "churn.xlsx"


def run(**kw):
    return run_detection([churn_profile()], **kw)[0]


def test_suggestion_only_cannot_train():
    r = run()
    assert not r["target_confirmed"] and r["needs_confirmation"]
    assert not can_start_training(r)


def test_target_chosen_alone_is_not_enough():
    # Example A: target_confirmed true, needs_confirmation still true,
    # because the PROBLEM TYPE has not been confirmed yet.
    r = run(overrides={CHURN: "churn"})
    assert r["target_confirmed"] is True
    assert r["needs_confirmation"] is True
    reasons = " ".join(training_blockers(r))
    assert "problem type is not confirmed" in reasons
    assert "features are not approved" in reasons


def test_target_and_problem_type_without_features_cannot_train():
    r = run(overrides={CHURN: "churn"},
            problem_type_override="binary_classification")
    assert r["target_confirmed"] and not r["needs_confirmation"]
    assert training_blockers(r) == ["features are not approved by the user"]


def test_all_three_approvals_allow_training():
    r = run(overrides={CHURN: "churn"},
            problem_type_override="binary_classification",
            approved_feature_columns={CHURN: ["tenure_months"]})
    assert r["features_status"] == "approved"
    assert can_start_training(r)


def test_features_approved_but_target_not_confirmed_cannot_train():
    r = run(problem_type_override="binary_classification",
            approved_feature_columns={CHURN: ["tenure_months"]})
    assert not r["target_confirmed"]
    assert any("target is not confirmed" in x for x in training_blockers(r))


def test_review_required_never_trains():
    r = run_detection([churn_profile()], overrides={CHURN: "customer_id"},
                      approved_feature_columns={CHURN: ["tenure_months"]})[0]
    assert r["problem_type"] == "review_required" or not can_start_training(r)
    fake = dict(r, problem_type="review_required")
    assert not can_start_training(fake)


def test_empty_approved_list_cannot_train():
    r = run(overrides={CHURN: "churn"},
            problem_type_override="binary_classification",
            approved_feature_columns={CHURN: []})
    assert not can_start_training(r)


def test_unsupervised_type_does_not_need_a_target():
    r = run(problem_type_override="clustering",
            approved_feature_columns={CHURN: ["tenure_months"]})
    assert r["problem_type"] == "clustering"
    assert can_start_training(r)


def test_forecasting_needs_a_time_axis():
    r = run_detection([sales_profile()], goal="Forecast sales next month",
                      problem_type_override="forecasting",
                      overrides={"sales.xlsx": "units_sold"},
                      approved_feature_columns={"sales.xlsx": ["revenue"]})[0]
    assert any(c.get("time_axis") for c in r["column_roles"])
    assert can_start_training(r)
    no_axis = dict(r, column_roles=[dict(c, time_axis=False)
                                    for c in r["column_roles"]])
    assert any("time_axis" in x for x in training_blockers(no_axis))
