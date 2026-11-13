"""REAL-INPUT tests: use Sanjay's actual profiling output for
HumanResources.Employee and Vinitha's actual quality reports. No synthetic
fixtures here. Every other test file uses fixtures or synthetic data unless
it says otherwise (see docs/TEST_REPORT.md, section 2)."""
import json
from pathlib import Path

import pytest

from quality_integration import issues_by_column, load_quality_report
from run_detection import run_detection
from training_rules import training_blockers

_HERE = Path(__file__).resolve().parent
ROOT = next(d for d in (_HERE, _HERE.parent)
            if (d / "handoff_result.schema.json").exists())
S = ROOT / "samples"
PROFILE = json.loads(
    (S / "input_profiling_Employee.profile.json").read_text(encoding="utf-8"))
QUALITY_FILES = ["input_quality_all_tables.json",
                 "input_quality_Employee_rerun.json"]
EMPLOYEE = "HumanResources.Employee"
APPROVED = dict(overrides={EMPLOYEE: "VacationHours"},
                problem_type_override="regression",
                approved_feature_columns=["SickLeaveHours", "JobTitle"])


def quality(name):
    return json.loads((S / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", QUALITY_FILES)
def test_vinitha_report_loads_and_every_severity_is_recognised(name):
    issues = load_quality_report(quality(name))["detected_issues"]
    assert issues
    for column_issues in issues_by_column(quality(name)).values():
        assert not any(i["unknown_severity"] for i in column_issues)


@pytest.mark.parametrize("name", QUALITY_FILES)
def test_full_run_on_real_profile_and_quality_reaches_training(name):
    result = run_detection([PROFILE], quality=quality(name), **APPROVED)[0]
    assert result["features_status"] == "approved"
    assert result["approved_feature_columns"] == ["SickLeaveHours",
                                                  "JobTitle"]
    assert training_blockers(result) == []


@pytest.mark.parametrize("name", QUALITY_FILES)
def test_real_run_without_confirmation_cannot_train(name):
    result = run_detection([PROFILE], quality=quality(name))[0]
    assert training_blockers(result)


def test_leakage_between_sick_leave_and_vacation_hours_is_a_warning_only():
    result = run_detection([PROFILE], **APPROVED)[0]
    check = result["leakage_checks"]
    assert check["status"] == "checked"
    suspects = {s["column"]: s for s in check["suspects"]}
    assert suspects["SickLeaveHours"]["level"] == "strong"
    assert suspects["SickLeaveHours"]["correlation"] == pytest.approx(
        0.9783, abs=1e-4)
    # warning, never removal: still recommended and still approved
    assert "SickLeaveHours" in result["recommended_feature_columns"]
    assert "SickLeaveHours" in result["approved_feature_columns"]
    assert any("SickLeaveHours" in w and "leakage" in w.lower()
               for w in result["warnings"])
    assert "Numerical column pairs only" in check["limits"]


def test_unflagged_columns_are_not_marked_as_leakage():
    result = run_detection([PROFILE], **APPROVED)[0]
    flagged = {c["column"] for c in result["column_roles"]
               if c.get("leakage_suspect")}
    assert flagged == {"SickLeaveHours"}
