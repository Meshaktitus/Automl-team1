"""Contract tests for the Dataset Profiling module (request/response schemas + implementation)."""
import copy
import json
import tempfile
from pathlib import Path

import pandas as pd

from profiling_service import REQUEST_SCHEMA, RESPONSE_SCHEMA, run_profiling
from schema_validation import cross_check, schema_is_valid, validate

HERE = Path(__file__).parent
SAMPLE_REQUEST = json.loads((HERE / "samples" / "sample_profiling_request.json").read_text(encoding="utf-8"))


def request(**changes):
    r = copy.deepcopy(SAMPLE_REQUEST)
    r["dataset_reference"]["location"] = str(HERE / "samples" / "demo_customers.csv")
    for key, value in changes.items():
        r[key] = value
    return r


def col(resp, name):
    return next(c for c in resp["columns"] if c["name"] == name)


def codes(resp):
    return {(w["code"], w["column"]) for w in resp["warnings"]}


# ---- the sample request is valid and the response follows the contract -------------------
def test_sample_request_is_valid_against_request_schema():
    assert validate(SAMPLE_REQUEST, REQUEST_SCHEMA) == []


def test_response_follows_response_schema():
    resp = run_profiling(request())
    assert validate(resp, RESPONSE_SCHEMA) == []
    assert resp["status"] == "warning"
    assert resp["request_id"] == "req-0001"
    assert resp["module"] == "dataset_profiling"


def test_dataset_section():
    d = run_profiling(request())["dataset"]
    assert d["row_count"] == 6 and d["column_count"] == 7 and d["duplicate_row_count"] == 1
    assert d["column_names"][0] == "customer_id"


def test_columns_are_ordered_and_numbered():
    resp = run_profiling(request())
    assert [c["position"] for c in resp["columns"]] == list(range(7))
    assert [c["name"] for c in resp["columns"]] == resp["dataset"]["column_names"]


def test_warnings_are_structured_and_tied_to_columns():
    resp = run_profiling(request())
    assert ("CONSTANT_COLUMN", "country") in codes(resp)
    assert ("EMPTY_COLUMN", "notes") in codes(resp)
    assert all(set(w) == {"code", "severity", "column", "message"} for w in resp["warnings"])
    assert "CONSTANT_COLUMN" in col(resp, "country")["warnings"]


# ---- metadata and options are honoured -----------------------------------------------------
def test_missing_value_markers_are_applied():
    assert col(run_profiling(request()), "age")["missing_count"] == 1          # "NA" -> missing
    r = request(metadata={"format": "csv"})
    assert col(run_profiling(r), "age")["missing_count"] == 1                  # pandas default also reads NA


def test_declared_identifier_columns_hide_values():
    plain = request(metadata={"format": "csv"})
    assert "top_values" in col(run_profiling(plain), "city")
    declared = request(metadata={"format": "csv", "identifier_columns": ["city"]})
    c = col(run_profiling(declared), "city")
    assert c["likely_identifier"] is True and "top_values" not in c


def test_top_values_shape_and_option():
    c = col(run_profiling(request(options={"top_n_values": 2})), "city")
    assert len(c["top_values"]) == 2
    assert c["top_values"][0] == {"value": "Pune", "count": 4, "percentage": 66.67}


def test_include_statistics_false_removes_summary():
    resp = run_profiling(request(options={"include_statistics": False}))
    assert all("summary" not in c for c in resp["columns"])
    assert validate(resp, RESPONSE_SCHEMA) == []


# ---- errors and status handling ----------------------------------------------------------------
def failed_with(resp, code):
    assert resp["status"] == "failed"
    assert resp["dataset"] is None and resp["columns"] == []
    assert any(e["code"] == code for e in resp["errors"])
    assert validate(resp, RESPONSE_SCHEMA) == []


def test_source_not_found():
    r = request()
    r["dataset_reference"]["location"] = "does/not/exist.csv"
    resp = run_profiling(r)
    failed_with(resp, "SOURCE_NOT_FOUND")
    assert resp["request_id"] == "req-0001"
    assert "does/not/exist" not in json.dumps(resp)          # the path is never echoed


def test_unsupported_format():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "data.txt"
        p.write_text("a,b\n1,2\n")
        r = request()
        r["dataset_reference"]["location"] = str(p)
        r["metadata"] = {}
        failed_with(run_profiling(r), "UNSUPPORTED_FORMAT")


def test_unreadable_file():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "broken.xlsx"
        p.write_bytes(b"this is not an excel file")
        r = request()
        r["dataset_reference"]["location"] = str(p)
        r["metadata"] = {}
        failed_with(run_profiling(r), "DATASET_LOAD_FAILED")


def test_invalid_requests_return_errors_not_exceptions():
    bad = request()
    del bad["request_id"]
    bad["surprise"] = 1
    bad["options"] = {"top_n_values": 0}
    resp = run_profiling(bad)
    failed_with(resp, "INVALID_REQUEST")
    assert resp["request_id"] is None
    fields = {e["field"] for e in resp["errors"]}
    assert "surprise" in fields and "options.top_n_values" in fields


def test_non_object_requests():
    for junk in (None, 5, "text", [], {}):
        failed_with(run_profiling(junk), "INVALID_REQUEST")


def test_missing_location_without_table():
    r = request()
    del r["dataset_reference"]["location"]
    failed_with(run_profiling(r), "INVALID_REQUEST")


def test_backend_can_pass_a_loaded_table():
    r = request()
    del r["dataset_reference"]["location"]
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "x"]})
    before = df.copy(deep=True)
    resp = run_profiling(r, dataframe=df)
    assert resp["status"] == "success" and resp["warnings"] == []
    assert validate(resp, RESPONSE_SCHEMA) == []
    pd.testing.assert_frame_equal(df, before)                 # source data untouched


def test_duplicate_column_names_are_rejected():
    r = request()
    del r["dataset_reference"]["location"]
    df = pd.DataFrame([[1, 2]], columns=["a", "a"])
    failed_with(run_profiling(r, dataframe=df), "DUPLICATE_COLUMN_NAMES")


def test_empty_table_is_a_warning_not_a_failure():
    r = request()
    del r["dataset_reference"]["location"]
    resp = run_profiling(r, dataframe=pd.DataFrame())
    assert resp["status"] == "warning" and ("EMPTY_DATASET", None) in codes(resp)
    assert validate(resp, RESPONSE_SCHEMA) == []


# ---- the schemas themselves ----------------------------------------------------------------------
def test_schemas_are_generic():
    text = ((HERE / "schemas" / "profiling_request.schema.json").read_text(encoding="utf-8")
            + (HERE / "schemas" / "profiling_response.schema.json").read_text(encoding="utf-8")).lower()
    for word in ("employee", "loan", "salary", "income", "credit", "customer", "department"):
        assert word not in text, f"schema must not mention '{word}'"


def test_response_schema_rejects_contract_violations():
    good = run_profiling(request())
    broken = copy.deepcopy(good)
    broken["status"] = "failed"                               # failed but has a dataset and no errors
    assert validate(broken, RESPONSE_SCHEMA)
    broken = copy.deepcopy(good)
    broken["columns"][0]["inferred_type"] = "banana"
    assert validate(broken, RESPONSE_SCHEMA)
    broken = copy.deepcopy(good)
    del broken["dataset"]["row_count"]
    assert validate(broken, RESPONSE_SCHEMA)
    broken = copy.deepcopy(good)
    broken["columns"][0]["missing_pct"] = 150
    assert validate(broken, RESPONSE_SCHEMA)


def test_standard_jsonschema_package_agrees_when_installed():
    """Independent second opinion. Skipped silently if `pip install jsonschema` was not done."""
    if schema_is_valid(REQUEST_SCHEMA) is None:
        return
    assert schema_is_valid(REQUEST_SCHEMA) and schema_is_valid(RESPONSE_SCHEMA)
    assert cross_check(SAMPLE_REQUEST, REQUEST_SCHEMA) == []
    for name in ("", "_not_found", "_invalid"):
        resp = json.loads((HERE / "samples" / f"sample_profiling_response{name}.json").read_text(encoding="utf-8"))
        assert cross_check(resp, RESPONSE_SCHEMA) == [], name
    assert cross_check(run_profiling(request()), RESPONSE_SCHEMA) == []
    bad = copy.deepcopy(SAMPLE_REQUEST)
    bad["surprise"] = 1
    assert cross_check(bad, REQUEST_SCHEMA) and validate(bad, REQUEST_SCHEMA)   # both reject it


# ---- the six backend tables (skipped when the Excel files are not on this machine) -----------
HR_EXPECTED = {"Department": (16, 4), "Employee": (290, 16), "EmployeeDepartmentHistory": (296, 6),
               "EmployeePayHistory": (316, 5), "JobCandidate": (13, 4), "Shift": (3, 5)}


def _hr_files():
    for folder in (HERE / "data", Path("/mnt/user-data/uploads")):
        files = {k: f for f in folder.glob("*.xlsx") for k in HR_EXPECTED
                 if f.stem.replace(".", "_").endswith("_" + k)} if folder.is_dir() else {}
        if len(files) == len(HR_EXPECTED):
            return files
    return {}


def test_six_backend_tables_match_expected_dimensions():
    files = _hr_files()
    if not files:
        try:
            import pytest
            pytest.skip("HR Excel files not found in ./data")
        except ImportError:
            return
    for key, path in files.items():
        r = request()
        r["dataset_reference"] = {"dataset_id": key, "source_type": "file", "location": str(path)}
        r["metadata"] = {"format": "xlsx"}
        resp = run_profiling(r)
        assert resp["status"] in ("success", "warning"), key
        assert (resp["dataset"]["row_count"], resp["dataset"]["column_count"]) == HR_EXPECTED[key], key
        assert validate(resp, RESPONSE_SCHEMA) == [], key
        for c in resp["columns"]:
            if c["likely_identifier"]:
                assert "top_values" not in c, (key, c["name"])


def test_identifier_columns_expose_no_values_or_statistics():
    """min, max and quartiles of an id column are real ids, so identifier columns get no summary, histogram or top_values."""
    df = pd.DataFrame({"NationalIDNumber": [295847284, 245797967, 509647174, 112457891],
                       "LoginID": ["a\\x", "b\\y", "c\\z", "d\\w"], "score": [1.0, 2.0, 3.0, 9.0]})
    resp = run_profiling({"schema_version": "1.0-draft", "request_id": "p", "dataset_reference": {"dataset_id": "d", "source_type": "file"}},
                         dataframe=df)
    cols = {c["name"]: c for c in resp["columns"]}
    for name in ("NationalIDNumber", "LoginID"):
        assert cols[name]["likely_identifier"] is True
        assert not ({"summary", "histogram", "top_values"} & set(cols[name]))
    assert "summary" in cols["score"]
    assert "295847284" not in json.dumps(resp)
