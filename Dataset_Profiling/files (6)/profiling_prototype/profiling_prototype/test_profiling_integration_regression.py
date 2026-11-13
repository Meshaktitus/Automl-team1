"""Integration regression tests (Week 3, Day 3): serialization, field names and types, the fields downstream consumers read,
empty and invalid scenarios, and consistency between input modes."""
import copy
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from profiling_service import REQUEST_SCHEMA, RESPONSE_SCHEMA, run_profiling
from schema_validation import validate

HERE = Path(__file__).parent
DEMO = HERE / "samples" / "demo_customers.csv"
TYPES = {"numerical", "categorical", "datetime", "time", "text", "boolean", "mixed", "empty"}


def req(target=None, location=None, **extra):
    r = {"schema_version": "1.0-draft", "request_id": "reg-1", "dataset_reference": {"dataset_id": "reg", "source_type": "file"}}
    if location:
        r["dataset_reference"]["location"] = str(location)
    if target:
        r["options"] = {"target_column": target}
    r.update(extra)
    return r


def strict_roundtrip(resp):
    """Strict JSON: NaN or Infinity would be rejected here. Returns the decoded copy."""
    text = json.dumps(resp, allow_nan=False)
    back = json.loads(text)
    assert back == resp
    return back


def awkward_tables():
    rng = np.random.default_rng(3)
    return {
        "nan_and_inf": pd.DataFrame({"x": [1.0, np.nan, np.inf, -np.inf, 5.0], "y": [np.nan] * 5, "z": [1, 2, 3, 4, 5]}),
        "numpy_types": pd.DataFrame({"i": np.arange(5, dtype=np.int64), "f": np.linspace(0, 1, 5, dtype=np.float32),
                                     "b": np.array([True, False, True, True, False]), "u": np.arange(5, dtype=np.uint8)}),
        "dates_and_times": pd.DataFrame({"d": pd.date_range("2024-01-01", periods=5), "t": [pd.Timestamp("2024-01-01").time()] * 5}),
        "unicode_names": pd.DataFrame({"naïve": [1, 2, 3], "名前": ["a", "b", "c"], "col with space": [1.5, 2.5, 3.5]}),
        "integer_column_names": pd.DataFrame({0: [1, 2, 3], 1: ["a", "b", "c"]}),
        "very_large_numbers": pd.DataFrame({"big": [1e300, 2e300, 3e300], "tiny": [1e-300, 2e-300, 3e-300]}),
        "mixed": pd.DataFrame({"m": [1, "a", 2.5, None, "b"]}),
        "random": pd.DataFrame({"a": rng.normal(size=50), "b": rng.normal(size=50), "c": rng.choice(list("xyz"), 50)}),
    }


# ---- serialization -----------------------------------------------------------------------------------------------------
def test_responses_serialize_as_strict_json():
    for name, df in awkward_tables().items():
        resp = run_profiling(req(), dataframe=df)
        assert resp["status"] != "failed", (name, resp["errors"])
        assert not validate(resp, RESPONSE_SCHEMA), name
        strict_roundtrip(resp)


def test_failed_responses_serialize_as_strict_json():
    for r in (None, {}, req(location="missing.csv"), req("nope")):
        resp = run_profiling(r, dataframe=pd.DataFrame({"a": [1]}) if r and r.get("options") else None)
        assert resp["status"] == "failed"
        strict_roundtrip(resp)


def test_response_contains_only_plain_json_types():
    def walk(x):
        if isinstance(x, dict):
            assert all(isinstance(k, str) for k in x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        else:
            assert type(x) in (str, int, float, bool, type(None)), type(x)
            if isinstance(x, float):
                assert math.isfinite(x)
    for df in awkward_tables().values():
        walk(run_profiling(req(), dataframe=df))


# ---- field names and data types are consistent -----------------------------------------------------------------------------
def test_field_names_and_types_are_consistent_across_inputs():
    expected_top = set(RESPONSE_SCHEMA["properties"])
    for df in awkward_tables().values():
        resp = run_profiling(req(), dataframe=df)
        assert set(resp) <= expected_top
        for c in resp["columns"]:
            assert isinstance(c["name"], str) and isinstance(c["position"], int) and isinstance(c["dtype"], str)
            assert c["inferred_type"] in TYPES
            assert isinstance(c["missing_count"], int) and isinstance(c["unique_count"], int)
            assert isinstance(c["missing_pct"], (int, float)) and 0 <= c["missing_pct"] <= 100
            assert isinstance(c["likely_identifier"], bool) and isinstance(c["warnings"], list)


def test_same_data_gives_same_profile_from_file_and_from_dataframe():
    from_file = run_profiling(req(location=DEMO, metadata={"format": "csv"}))
    from_frame = run_profiling(req(), dataframe=pd.read_csv(DEMO))
    assert from_file["dataset"] == from_frame["dataset"]
    assert from_file["columns"] == from_frame["columns"]
    assert from_file["warnings"] == from_frame["warnings"]


def test_profile_is_repeatable():
    a = run_profiling(req(location=DEMO), dataframe=None)
    b = run_profiling(req(location=DEMO), dataframe=None)
    for r in (a, b):
        r.pop("generated_at"), r.pop("duration_ms")
    assert a == b


# ---- fields that downstream modules read ----------------------------------------------------------------------------------
DATASET_FIELDS = {"row_count": int, "column_count": int, "column_names": list, "duplicate_row_count": int}
COLUMN_FIELDS = {"name": str, "position": int, "dtype": str, "inferred_type": str, "missing_count": int,
                 "missing_pct": (int, float), "unique_count": int, "likely_identifier": bool, "warnings": list}


def test_fields_read_by_downstream_modules_are_present_with_the_right_types():
    for resp in (run_profiling(req(location=DEMO, metadata={"format": "csv"})),
                 run_profiling(req("plan", location=DEMO, metadata={"format": "csv"}))):
        for key in ("schema_version", "request_id", "status"):
            assert isinstance(resp[key], str)
        assert resp["dataset_reference"]["dataset_id"] == "reg"
        for key, t in DATASET_FIELDS.items():
            assert isinstance(resp["dataset"][key], t), key
        for c in resp["columns"]:
            for key, t in COLUMN_FIELDS.items():
                assert isinstance(c[key], t), (c["name"], key)
        numerical = [c for c in resp["columns"] if c["inferred_type"] == "numerical" and not c["likely_identifier"]]
        assert numerical and all({"min", "max", "mean", "median", "std", "q1", "q3", "skewness"} <= set(c["summary"]) for c in numerical)
        assert any("top_values" in c for c in resp["columns"])


def test_missingness_and_target_metadata_are_not_conflated():
    # the target's missing values are counted once, in the column and in the class distribution, and never as a class
    df = pd.DataFrame({"x": range(10), "y": ["a", "b", "a", None, "a", "b", None, "a", "b", "a"]})
    resp = run_profiling(req("y"), dataframe=df)
    target = next(c for c in resp["columns"] if c["name"] == "y")
    cd = resp["class_distribution"]
    assert target["missing_count"] == cd["missing_count"] == 2
    assert sum(k["count"] for k in cd["classes"]) + cd["missing_count"] == resp["dataset"]["row_count"]
    assert {k["value"] for k in cd["classes"]} == {"a", "b"}


# ---- empty and invalid scenarios -------------------------------------------------------------------------------------------------
def test_empty_and_invalid_scenarios_give_structured_results():
    cases = {
        "empty table": (req(), pd.DataFrame(), "warning"),
        "no rows, two columns": (req(), pd.DataFrame({"a": [], "b": []}), "warning"),
        "all values missing": (req(), pd.DataFrame({"a": [None, None], "b": [None, None]}), "warning"),
        "single row": (req(), pd.DataFrame({"a": [1], "b": ["x"]}), None),
        "unknown target": (req("zzz"), pd.DataFrame({"a": [1, 2]}), "failed"),
        "not a dataframe": (req(), "text", "failed"),
        "invalid request": ({"hello": 1}, None, "failed"),
        "no source": (req(), None, "failed"),
    }
    for name, (r, df, status) in cases.items():
        resp = run_profiling(r, dataframe=df)
        assert resp["status"] in ("success", "warning", "failed"), name
        if status:
            assert resp["status"] == status, (name, resp["status"], resp["errors"])
        assert not validate(resp, RESPONSE_SCHEMA), name
        strict_roundtrip(resp)
        if resp["status"] == "failed":
            assert resp["dataset"] is None and resp["columns"] == [] and resp["errors"], name


def test_request_is_not_modified_by_profiling():
    r = req("plan", location=DEMO, metadata={"format": "csv"})
    before = copy.deepcopy(r)
    run_profiling(r)
    assert r == before and not validate(r, REQUEST_SCHEMA)


def test_only_one_target_per_request_is_supported():
    """The contract supports one selected target. A list of targets is rejected, not silently accepted."""
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "x"]})
    resp = run_profiling({**req(), "options": {"target_column": ["a", "b"]}}, dataframe=df)
    assert resp["status"] == "failed"
    assert any(e["code"] == "INVALID_REQUEST" and e["field"] == "options.target_column" for e in resp["errors"])
