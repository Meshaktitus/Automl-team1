"""Review decisions and training approval (Meshak's review, 6 Nov): the
approved features, target and problem type sent back from the review screen
must reach the result; sensitive columns need explicit approval; training
stays blocked until target, problem type and features are approved."""
import copy
import json
from pathlib import Path

import pytest

from run_detection import (review_decisions_to_arguments, run_detection)
from training_rules import training_blockers

_HERE = Path(__file__).resolve().parent
ROOT = next(d for d in (_HERE, _HERE.parent)
            if (d / "handoff_result.schema.json").exists())
PROFILE = ROOT / "samples" / "input_profiling_Employee.profile.json"
DECISIONS = json.loads(
    (ROOT / "samples" / "input_review_decisions_Employee.json").read_text(
        encoding="utf-8"))


def profile(dataset_id=None):
    data = json.loads(PROFILE.read_text(encoding="utf-8"))
    if dataset_id:
        data["dataset_reference"] = {"dataset_id": dataset_id,
                                     "name": dataset_id + ".xlsx"}
    return data


def run(**kw):
    return run_detection([profile()], **kw)[0]


# ---- point 1: approved features reach the result -------------------------
def test_sample_review_payload_matches_the_profile_dataset_id():
    assert DECISIONS["dataset_id"] == profile()["dataset_reference"][
        "dataset_id"]


def test_review_payload_gives_approved_features_target_and_problem_type():
    result = run(**review_decisions_to_arguments(DECISIONS))
    assert result["features_status"] == "approved"
    assert result["approved_feature_columns"] == ["SickLeaveHours",
                                                  "JobTitle"]
    assert result["target"] == "VacationHours"
    assert result["target_confirmed"] is True
    assert result["problem_type"] == "regression"
    assert result["needs_confirmation"] is False
    assert training_blockers(result) == []


def test_payload_given_as_a_list_works_too():
    args = review_decisions_to_arguments([DECISIONS])
    assert run(**args)["features_status"] == "approved"


def test_dataset_id_that_matches_nothing_is_reported_not_ignored():
    wrong = dict(DECISIONS, dataset_id="Employee")
    result = run(**review_decisions_to_arguments(wrong))
    assert result["features_status"] == "recommended_pending_confirmation"
    assert result["approved_feature_columns"] is None
    assert any("has no entry for this dataset" in w
               and "Employee" in w for w in result["warnings"])
    assert training_blockers(result)


def test_plain_list_with_several_datasets_is_reported_not_ignored():
    results = run_detection([profile(), profile("Other.Table")],
                            approved_feature_columns=["JobTitle"])
    for result in results:
        assert result["features_status"] == "recommended_pending_confirmation"
        assert any("plain list" in w for w in result["warnings"])


def test_each_dataset_gets_its_own_problem_type_override():
    results = run_detection(
        [profile(), profile("Other.Table")],
        overrides={"HumanResources.Employee": "VacationHours",
                   "Other.Table": "SalariedFlag"},
        problem_type_override={"HumanResources.Employee": "regression",
                               "Other.Table": "binary_classification"})
    by = {r["dataset_id"]: r for r in results}
    assert by["HumanResources.Employee"]["problem_type"] == "regression"
    assert by["Other.Table"]["problem_type"] == "binary_classification"


@pytest.mark.parametrize("bad", [[], {}, None, "text", [{"target": "x"}]])
def test_bad_review_payload_is_rejected_with_a_message(bad):
    with pytest.raises(ValueError):
        review_decisions_to_arguments(bad)


def test_different_goals_in_one_call_are_rejected():
    with pytest.raises(ValueError):
        review_decisions_to_arguments([
            {"dataset_id": "A", "goal": "Predict x"},
            {"dataset_id": "B", "goal": "Predict y"}])


# ---- point 5: sensitive columns --------------------------------------------
def test_sensitive_columns_are_not_recommended_by_default():
    result = run()
    sensitive = set(result["dataset_characteristics"]["sensitive_columns"])
    assert sensitive
    assert not sensitive & set(result["recommended_feature_columns"])
    assert result["approved_feature_columns"] is None


def test_sensitive_column_is_used_only_when_the_user_approves_it():
    result = run(overrides={"HumanResources.Employee": "VacationHours"},
                 problem_type_override="regression",
                 approved_feature_columns=["JobTitle", "MaritalStatus"])
    assert "MaritalStatus" in result["approved_feature_columns"]
    assert "MaritalStatus" not in result["recommended_feature_columns"]
    entry = [r for r in result["column_roles"]
             if r["column"] == "MaritalStatus"][0]
    assert "privacy_review_before_use" in entry["preprocessing_actions"]


def test_approving_other_columns_does_not_pass_sensitive_ones():
    result = run(approved_feature_columns=["JobTitle"])
    assert not set(result["approved_feature_columns"]) & set(
        result["dataset_characteristics"]["sensitive_columns"])


# ---- point 6: training approval rules --------------------------------------
BASE = dict(overrides={"HumanResources.Employee": "VacationHours"},
            problem_type_override="regression",
            approved_feature_columns=["JobTitle"])


def test_training_is_allowed_only_when_everything_is_approved():
    assert training_blockers(run(**BASE)) == []


@pytest.mark.parametrize("missing", [
    "overrides", "problem_type_override", "approved_feature_columns"])
def test_training_is_blocked_when_one_approval_is_missing(missing):
    kwargs = {k: v for k, v in BASE.items() if k != missing}
    assert training_blockers(run(**kwargs))


def test_empty_approved_feature_list_blocks_training():
    kwargs = dict(BASE, approved_feature_columns=[])
    assert training_blockers(run(**kwargs))


def test_review_required_never_enters_training():
    result = run()
    assert result["problem_type"] == "review_required"
    assert any("review_required" in reason
               for reason in training_blockers(result))
    forced = copy.deepcopy(result)
    forced.update(target_confirmed=True, features_status="approved",
                  approved_feature_columns=["JobTitle"],
                  needs_confirmation=False)
    assert training_blockers(forced)


def test_cli_review_decisions_option_gives_approved_features(tmp_path):
    import subprocess
    import sys
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / PROFILE.name).write_text(PROFILE.read_text(encoding="utf-8"),
                                         encoding="utf-8")
    out = tmp_path / "out.json"
    done = subprocess.run(
        [sys.executable, str(ROOT / "run_detection.py"), "--profiles",
         str(profiles), "--review-decisions",
         str(ROOT / "samples" / "input_review_decisions_Employee.json"),
         "--output", str(out)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    result = data[0] if isinstance(data, list) else (
        data.get("results") or [data])[0]
    assert result["features_status"] == "approved"
    assert result["approved_feature_columns"] == ["SickLeaveHours",
                                                  "JobTitle"]
