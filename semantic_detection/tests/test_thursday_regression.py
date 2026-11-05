"""Thursday (Day 4) regression tests for semantic detection, target and
problem-type detection across all synthetic fixture types. The profiles are
built from the fixture data in the shape Sanjay's profiler returns."""
import numpy as np
import pandas as pd
import pytest

from make_synthetic_datasets import build
from run_detection import run_detection
from test_profiling_integration import col, profile
from profiling_integration import analyze_profile


def _inferred(series):
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        return "numerical"
    if series.dropna().nunique() == 0:
        return "empty"
    if series.dropna().astype(str).str.len().mean() > 40:
        return "text"
    return "categorical"


def make_profile(name, df):
    n = len(df)
    columns = []
    for i, c in enumerate(df.columns):
        s = df[c]
        kind = _inferred(s)
        unique = int(s.nunique(dropna=True))
        ident = unique == n and str(c).lower().endswith("id")
        item = {
            "name": c, "position": i, "dtype": str(s.dtype),
            "inferred_type": kind, "missing_count": int(s.isna().sum()),
            "missing_pct": float(round(100 * s.isna().mean(), 2)),
            "unique_count": unique, "likely_identifier": bool(ident),
            "warnings": [],
        }
        if not ident:
            if kind == "numerical":
                item["summary"] = {
                    "min": float(s.min()), "max": float(s.max()),
                    "mean": float(s.mean()), "median": float(s.median()),
                    "std": float(s.std())}
            elif kind == "datetime":
                item["summary"] = {"min": str(s.min()), "max": str(s.max())}
            elif kind == "text":
                item["summary"] = {
                    "avg_length": float(s.astype(str).str.len().mean())}
            if kind in ("categorical", "boolean", "text"):
                counts = s.astype(str).value_counts().head(10)
                item["top_values"] = [
                    {"value": k, "count": int(v),
                     "percentage": float(round(100 * v / n, 2))}
                    for k, v in counts.items()]
        columns.append(item)
    numbers = df.select_dtypes("number").drop(
        columns=[c["name"] for c in columns if c["likely_identifier"]],
        errors="ignore")
    matrix = numbers.corr()
    pairs = [
        {"column_a": a, "column_b": b,
         "coefficient": round(float(matrix.loc[a, b]), 4)}
        for a in matrix.columns for b in matrix.columns
        if a < b and not np.isnan(matrix.loc[a, b])]
    pairs.sort(key=lambda x: -abs(x["coefficient"]))
    return {
        "schema_version": "1.0-draft", "request_id": "r",
        "module": "dataset_profiling", "status": "success",
        "generated_at": "x", "duration_ms": 1.0,
        "dataset_reference": {"dataset_id": name, "name": name},
        "dataset": {"row_count": n, "column_count": len(columns),
                    "column_names": list(df.columns),
                    "duplicate_row_count": int(df.duplicated().sum())},
        "columns": columns, "correlations": pairs,
        "warnings": [], "errors": []}


FIXTURES = build()
NAMES = sorted(FIXTURES)


def detect(name, **kwargs):
    return run_detection([make_profile(name, FIXTURES[name])], **kwargs)[0]


# expected result without a goal, then with a plain-words goal
NO_GOAL = {
    "churn_classification.csv": ("churn", "binary_classification"),
    "house_price_regression.csv": ("price", "regression"),
    "sales_forecasting.csv": ("revenue", "regression"),
    "customer_segments_clustering.csv": (None, "review_required"),
    "ambiguous_targets.csv": (None, "review_required"),
    "transactions_anomaly.csv": (None, "review_required"),
    "ratings_recommendation.csv": (None, "review_required"),
}
WITH_GOAL = {
    "churn_classification.csv": (
        "Predict which customers will churn", "churn",
        "binary_classification"),
    "sales_forecasting.csv": (
        "Forecast revenue next month", "revenue", "forecasting"),
    "customer_segments_clustering.csv": (
        "Group customers into segments", None, "clustering"),
    "transactions_anomaly.csv": (
        "Detect unusual transactions", None, "anomaly_detection"),
    "ratings_recommendation.csv": (
        "Recommend items to users", None, "recommendation"),
}


@pytest.mark.parametrize("name", NAMES)
def test_every_fixture_has_the_expected_result_without_a_goal(name):
    target, problem = NO_GOAL[name]
    result = detect(name)
    assert result["target"] == target
    assert result["problem_type"] == problem


@pytest.mark.parametrize("name", sorted(WITH_GOAL))
def test_goal_selects_the_expected_problem_type(name):
    goal, target, problem = WITH_GOAL[name]
    result = detect(name, goal=goal)
    assert result["target"] == target
    assert result["problem_type"] == problem


@pytest.mark.parametrize("name", NAMES)
def test_identifier_like_columns_are_never_suggested_as_targets(name):
    result = detect(name)
    identifiers = {c["column"] for c in result["semantic_columns"]
                   if c["semantic_type"] == "identifier"}
    assert result["target"] not in identifiers
    assert not identifiers & {c["candidate_target"]
                              for c in result["candidates"]}


@pytest.mark.parametrize("name", NAMES)
def test_confidence_and_evidence_fields_are_present(name):
    result = detect(name)
    assert 0 <= result["confidence"] <= 1
    assert result["evidence"]
    for column in result["semantic_columns"]:
        assert 0 <= column["confidence"] <= 1
    for role in result["column_roles"]:
        assert role["reason"]


def test_ambiguous_columns_need_human_confirmation():
    result = detect("ambiguous_targets.csv")
    assert result["target"] is None
    assert result["needs_confirmation"] is True
    assert any("confirm" in w for w in result["warnings"])


def test_ambiguous_result_lists_columns_the_user_can_pick():
    result = detect("ambiguous_targets.csv")
    pick = [w for w in result["warnings"]
            if w.startswith("Columns the user can pick from")]
    assert len(pick) == 1
    shown = result["candidates"][:3]
    for candidate in shown:
        assert candidate["candidate_target"] in pick[0]


def test_confirmed_target_has_no_pick_list():
    result = detect("churn_classification.csv")
    assert not any(w.startswith("Columns the user can pick from")
                   for w in result["warnings"])


def test_leakage_suspect_is_flagged_but_kept():
    result = detect("house_price_regression.csv")
    assert any("area_sqft" in w and "leakage" in w
               for w in result["warnings"])
    assert "area_sqft" in {r["column"] for r in result["column_roles"]}


# defect found on Thursday: a compact whole-number range is not an identifier
@pytest.mark.parametrize("name,unique,low,high", [
    ("hour_of_day", 24, 0, 23),
    ("month_number_of_sale", 12, 1, 12),
    ("birth_year_offset", 58, 18, 75),
])
def test_compact_repeating_whole_numbers_are_not_identifiers(
        name, unique, low, high):
    rows = analyze_profile(profile(
        [col(name, "numerical", unique=unique,
             summary={"min": float(low), "max": float(high)})], rows=1000))
    assert rows[0]["semantic_type"] != "identifier"


def test_unique_consecutive_numbers_are_still_an_identifier():
    rows = analyze_profile(profile(
        [col("serial", "numerical", unique=100,
             summary={"min": 1.0, "max": 100.0})], rows=100))
    assert rows[0]["semantic_type"] == "identifier"
