"""Day 3 integration tests: real profiling output (Employee table from the
HR set) plus the quality report, run through run_detection and checked
against the handoff schema. Covers: the result validates, a table with no
outcome column is flagged for human confirmation (never silently trained),
and a user-chosen target is respected."""
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

from run_detection import run_detection

_HERE = Path(__file__).resolve().parent
ROOT = next(d for d in (_HERE, _HERE.parent)
            if (d / "handoff_result.schema.json").exists())
SCHEMA = json.loads((ROOT / "handoff_result.schema.json").read_text(
    encoding="utf-8"))
PROFILE = ROOT / "samples" / "input_profiling_Employee.profile.json"
QUALITY = ROOT / "samples" / "input_quality_all_tables.json"


@pytest.fixture(scope="module")
def result():
    out = run_detection(profiles=[str(PROFILE)], quality=str(QUALITY))
    assert len(out) == 1
    return out[0]


def test_result_validates_against_the_schema(result):
    jsonschema.validate(result, SCHEMA)


def test_quality_and_profiling_matched_by_dataset(result):
    assert result["dataset"].startswith("HumanResources.Employee")


def test_no_outcome_column_means_human_confirmation(result):
    # The HR tables have no outcome column: nothing may be treated as
    # confirmed, and no training is allowed without a user decision.
    assert result["target_confirmed"] is False
    assert result["needs_confirmation"] is True


def test_user_target_is_respected_and_still_needs_problem_confirmation():
    res = run_detection(
        profiles=[str(PROFILE)],
        quality=str(QUALITY),
        overrides={"HumanResources.Employee.xlsx": "VacationHours"},
    )[0]
    jsonschema.validate(res, SCHEMA)
    assert res["target"] == "VacationHours"
    assert res["target_confirmed"] is True
    assert res["needs_confirmation"] is True


def test_result_is_json_serialisable(result):
    json.dumps(result)
