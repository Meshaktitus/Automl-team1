"""Every real result must follow handoff_result.schema.json."""
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

from run_detection import run_detection
from test_profiling_integration import col, profile
from test_run_detection import churn_profile, sales_profile

SCHEMA = json.loads(
    (Path(__file__).resolve().parent.parent / "handoff_result.schema.json").read_text(
        encoding="utf-8"))


def check(result):
    jsonschema.validate(json.loads(json.dumps(result)), SCHEMA)


def test_schema_itself_is_valid():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


def test_binary_target_result_follows_schema():
    for r in run_detection([churn_profile()]):
        check(r)


def test_forecasting_result_follows_schema():
    for r in run_detection([sales_profile()], goal="Forecast sales next month"):
        check(r)


def test_no_target_result_follows_schema():
    anon = profile([col(f"col{i}", "numerical", "float64", unique=90,
                        summary={"min": 0.0, "max": 9.0})
                    for i in range(1, 5)], name="anon.xlsx")
    for r in run_detection([anon]):
        check(r)


def test_quality_blocked_and_approved_result_follows_schema():
    q = {"dataset": "churn.xlsx", "issues": [
        {"rule_id": "INVALID_RANGE", "severity": "Blocking",
         "affected_column": "tenure_months", "affected_rows": 2}]}
    r = run_detection([churn_profile()], quality=q,
                      approved_features={"churn.xlsx": ["tenure_months"]})[0]
    check(r)


def test_result_with_leakage_suspect_follows_schema():
    p = profile([col("vac", "numerical", unique=60,
                     summary={"min": 0.0, "max": 99.0}),
                 col("sick", "numerical", unique=50,
                     summary={"min": 20.0, "max": 80.0})])
    p["correlations"] = [
        {"column_a": "vac", "column_b": "sick", "coefficient": 0.97}]
    check(run_detection([p], overrides={"d.xlsx": "vac"})[0])


def test_unknown_dataset_override_result_follows_schema():
    rs = run_detection([churn_profile()], overrides={"nope.xlsx": "x"})
    for r in rs:
        check(r)


def test_a_broken_result_is_rejected():
    r = run_detection([churn_profile()])[0]
    r["problem_type"] = "made_up_type"
    with pytest.raises(jsonschema.ValidationError):
        check(r)
