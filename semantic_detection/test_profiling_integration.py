import json

import pandas as pd
import pytest

from problem_detection import detect_problem
from profiling_integration import (
    analyze_profile,
    compare_with_data_report,
    load_profile,
)
from target_suggestions import suggest_targets


def col(name, inferred, dtype="int64", unique=10, missing=0, pct=0.0,
        ident=False, summary=None, top=None, warnings=None):
    out = {
        "name": name, "position": 0, "dtype": dtype,
        "inferred_type": inferred, "missing_count": missing,
        "missing_pct": pct, "unique_count": unique,
        "likely_identifier": ident, "warnings": warnings or [],
    }
    if summary is not None:
        out["summary"] = summary
    if top is not None:
        out["top_values"] = top
    return out


def profile(columns, rows=100, name="d.xlsx", status="success"):
    return {
        "schema_version": "1.0-draft", "request_id": "r", "module":
        "dataset_profiling", "status": status, "generated_at": "x",
        "duration_ms": 1.0,
        "dataset_reference": {"dataset_id": "d", "name": name},
        "dataset": {"row_count": rows, "column_count": len(columns),
                    "column_names": [c["name"] for c in columns],
                    "duplicate_row_count": 0},
        "columns": columns, "warnings": [], "errors": [],
    }


NUM = {"min": 0.0, "max": 99.0, "mean": 50.0, "median": 51.0, "std": 28.0}


def kinds(columns, rows=100):
    result = analyze_profile(profile(columns, rows))
    return {r["column"]: r["semantic_type"] for r in result}


def test_report_has_the_same_columns_as_analyze_semantics():
    row = analyze_profile(profile([col("age", "numerical", summary=NUM)]))[0]
    assert set(row) == {
        "dataset", "column", "data_type", "row_count", "non_null_count",
        "missing_pct", "unique_values", "semantic_type", "confidence",
        "evidence", "alternatives", "sensitive", "status",
    }
    assert row["dataset"] == "d.xlsx"


def test_basic_types_from_profile():
    got = kinds([
        col("VacationHours", "numerical", unique=100, summary=NUM),
        col("Rate", "numerical", "float64", unique=66,
            summary={"min": 6.5, "max": 125.5}),
        col("HireDate", "datetime", "datetime64[us]", unique=50,
            summary={"min": "2006-06-30 00:00:00",
                     "max": "2013-05-30 00:00:00"}),
        col("StartTime", "time", "object", unique=3,
            top=[{"value": "07:00:00", "count": 1, "percentage": 33.3}]),
        col("Resume", "text", "str", unique=100,
            summary={"avg_length": 4136.0, "max_length": 6550}),
    ])
    assert got == {
        "VacationHours": "numerical_measure", "Rate": "financial_amount",
        "HireDate": "date", "StartTime": "time", "Resume": "text",
    }


def test_flag_and_constant_columns():
    got = kinds([
        col("SalariedFlag", "numerical", unique=2,
            summary={"min": 0.0, "max": 1.0}),
        col("CurrentFlag", "numerical", unique=1,
            summary={"min": 1.0, "max": 1.0}),
    ])
    assert got["SalariedFlag"] == "boolean_flag"
    assert got["CurrentFlag"] == "boolean_flag"


def test_likely_identifier_flag_is_used():
    row = analyze_profile(profile([
        col("serial", "categorical", "str", unique=100, ident=True)]))[0]
    assert row["semantic_type"] == "identifier"
    assert "Profiling flagged" in row["evidence"]


def test_high_cardinality_text_is_not_called_categorical():
    got = kinds([col("OrganizationNode", "categorical", "str", unique=289,
                     missing=1, pct=0.34, top=[
                         {"value": "0x58", "count": 1, "percentage": 0.35}])],
                rows=290)
    assert got["OrganizationNode"] == "text"


def test_few_distinct_categories_stay_categorical():
    got = kinds([col("Gender", "categorical", "str", unique=2, top=[
        {"value": "M", "count": 70, "percentage": 70.0},
        {"value": "F", "count": 30, "percentage": 30.0}])])
    assert got["Gender"] == "categorical"


def test_missing_values_are_carried_over():
    row = analyze_profile(profile([
        col("OrganizationLevel", "numerical", "float64", unique=4,
            missing=1, pct=0.34, summary={"min": 1.0, "max": 4.0})],
        rows=290))[0]
    assert row["non_null_count"] == 289
    assert row["missing_pct"] == 0.3
    assert row["unique_values"] == 4


def test_empty_column_is_unknown():
    row = analyze_profile(profile([
        col("blank", "empty", "object", unique=0, missing=100, pct=100.0)]))[0]
    assert row["semantic_type"] == "unknown"


def test_large_dataset_stays_fast_and_correct():
    got = kinds([col("amount", "numerical", "float64", unique=900000,
                     summary={"min": 1.5, "max": 99999.5})], rows=1_000_000)
    assert got["amount"] in {"numerical_measure", "financial_amount"}


def test_failed_profile_is_rejected():
    bad = profile([], status="failed")
    bad["errors"] = [{"code": "SOURCE_NOT_FOUND", "message": "m", "field": None}]
    with pytest.raises(ValueError, match="failed"):
        load_profile(bad)


def test_wrong_version_and_missing_fields_are_rejected():
    wrong = profile([col("a", "numerical", summary=NUM)])
    wrong["schema_version"] = "2.0"
    with pytest.raises(ValueError, match="schema_version"):
        load_profile(wrong)
    short = profile([{"name": "a"}])
    with pytest.raises(ValueError, match="lacks fields"):
        load_profile(short)
    with pytest.raises(ValueError):
        load_profile([1, 2])


def test_load_from_file(tmp_path):
    path = tmp_path / "x.profile.json"
    path.write_text(json.dumps(profile(
        [col("age", "numerical", summary=NUM)])), encoding="utf-8")
    assert analyze_profile(path)[0]["column"] == "age"


def test_compare_reports_differences():
    rows = analyze_profile(profile([col("age", "numerical", unique=50,
                                        summary=NUM)]))
    same = pd.DataFrame(rows)
    _, different = compare_with_data_report(rows, same)
    assert different.empty
    changed = same.copy()
    changed["semantic_type"] = "categorical"
    _, different = compare_with_data_report(rows, changed)
    assert len(different) == 1


def test_profile_report_feeds_target_and_problem_steps():
    columns = [
        col("customer_id", "numerical", unique=100, ident=True,
            summary={"min": 1.0, "max": 100.0}),
        col("income", "numerical", "float64", unique=95,
            summary={"min": 10000.0, "max": 90000.0}),
        col("churn", "numerical", unique=2,
            summary={"min": 0.0, "max": 1.0}),
    ]
    report = pd.DataFrame(analyze_profile(profile(columns, name="c.xlsx")))
    suggestions = suggest_targets(report)
    assert "customer_id" not in set(suggestions["candidate_target"])
    assert "churn" in set(suggestions["candidate_target"])
    result = detect_problem(report, "c.xlsx", target="churn")
    assert result["problem_type"] == "binary_classification"
