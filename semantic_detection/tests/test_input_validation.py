"""Input validation and consistency (Meshak, 5 Nov): the module must handle
CSV-sourced and Excel-sourced profiles the same way, and must report missing,
incomplete or failed profiling and quality responses instead of crashing."""
import copy
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")
validate = jsonschema.validate

from run_detection import run_detection

_HERE = Path(__file__).resolve().parent
ROOT = next(d for d in (_HERE, _HERE.parent)
            if (d / "handoff_result.schema.json").exists())
SCHEMA = json.loads((ROOT / "handoff_result.schema.json").read_text(
    encoding="utf-8"))
EMPLOYEE = ROOT / "samples" / "input_profiling_Employee.profile.json"
QUALITY_ALL = ROOT / "samples" / "input_quality_all_tables.json"


def profile():
    return copy.deepcopy(json.loads(EMPLOYEE.read_text(encoding="utf-8")))


def only(result_list):
    assert len(result_list) == 1
    validate(result_list[0], SCHEMA)
    return result_list[0]


def strip_name(result):
    """Everything except the dataset name, for comparing two runs."""
    out = copy.deepcopy(result)
    for key in ("dataset", "dataset_id"):
        out.pop(key, None)
    return json.dumps(out, sort_keys=True, default=str).replace(
        ".xlsx", ".EXT").replace(".csv", ".EXT")


def test_csv_and_excel_profiles_give_the_same_result():
    excel, csv = profile(), profile()
    excel["dataset_reference"]["name"] = "Employee.xlsx"
    csv["dataset_reference"]["name"] = "Employee.csv"
    a = only(run_detection([excel], overrides={"Employee.xlsx": "VacationHours"}))
    b = only(run_detection([csv], overrides={"Employee.csv": "VacationHours"}))
    assert strip_name(a) == strip_name(b)


@pytest.mark.parametrize("damage", [
    lambda d: d.pop("columns"),
    lambda d: d.pop("dataset"),
    lambda d: d["dataset"].pop("row_count"),
    lambda d: d["dataset"].pop("column_count"),
    lambda d: d["dataset"].pop("duplicate_row_count"),
    lambda d: d["columns"][0].pop("inferred_type"),
    lambda d: d["columns"][0].pop("unique_count"),
    lambda d: d["columns"][0].pop("name"),
    lambda d: d["columns"][0].update(unique_count=-1),
    lambda d: d["columns"][0].update(missing_pct=150),
    lambda d: d["columns"][0].update(missing_pct="abc"),
    lambda d: d["dataset"].update(row_count=-5),
    lambda d: d.update(schema_version="9.9"),
    lambda d: d.update(status="failed", errors=[{"code": "SOURCE_NOT_FOUND"}]),
])
def test_bad_profile_is_reported_not_crashed(damage):
    broken = profile()
    damage(broken)
    result = only(run_detection([broken]))
    assert result["problem_type"] == "review_required"
    assert result["target"] is None
    assert any("could not be used" in w for w in result["warnings"])


@pytest.mark.parametrize("bad", [{}, None, "no_such_file.json", [1, 2]])
def test_unusable_profile_object_is_reported(bad):
    result = only(run_detection([bad]))
    assert result["problem_type"] == "review_required"
    assert any("could not be used" in w for w in result["warnings"])


def test_one_bad_profile_does_not_stop_the_good_one():
    broken = profile()
    broken["dataset"].pop("row_count")
    broken["dataset_reference"]["name"] = "Broken.xlsx"
    results = run_detection([profile(), broken])
    assert len(results) == 2
    by = {r["dataset"]: r for r in results}
    assert by["Broken.xlsx"]["problem_type"] == "review_required"
    assert by[[k for k in by if k != "Broken.xlsx"][0]]["feature_columns"]


@pytest.mark.parametrize("quality", [
    {},
    {"status": "failed", "errors": [{"code": "QUALITY_FAILED"}]},
    {"detected_issues": "oops"},
    "no_such_quality_file.json",
])
def test_unusable_quality_report_is_reported_and_run_continues(quality):
    result = only(run_detection([profile()], quality=quality))
    assert any("quality report could not be used" in w
               for w in result["warnings"])
    assert result["semantic_columns"]


def test_good_quality_report_has_no_quality_warning():
    q = json.loads(QUALITY_ALL.read_text(encoding="utf-8"))
    result = only(run_detection([profile()], quality=q))
    assert not any("quality report could not be used" in w
                   for w in result["warnings"])


def test_no_profiles_at_all_is_a_caller_error():
    with pytest.raises(ValueError):
        run_detection([])
