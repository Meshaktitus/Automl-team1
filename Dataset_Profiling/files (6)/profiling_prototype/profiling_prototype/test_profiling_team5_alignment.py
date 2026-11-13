"""Cases taken from the review of Team 5's profiler (their sample CSVs and six edge cases), run through our module.
Each case records the agreed behaviour of the Dataset Profiling module for CSV files."""
import tempfile
from pathlib import Path

import pandas as pd

from profiling_service import RESPONSE_SCHEMA, run_profiling
from schema_validation import validate

REQ = {"schema_version": "1.0-draft", "request_id": "t5", "dataset_reference": {"dataset_id": "t5", "source_type": "file"}}


def profile_csv_text(text, raw=False, **metadata):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "case.csv"
        path.write_bytes(text if raw else text.encode("utf-8"))
        resp = run_profiling({**REQ, "dataset_reference": {**REQ["dataset_reference"], "location": str(path)},
                              "metadata": {"format": "csv", **metadata}})
    assert not validate(resp, RESPONSE_SCHEMA)
    return resp, {c["name"]: c for c in resp.get("columns", [])}


def test_mixed_types_sample_types_are_detected():
    text = ("customer_id,name,age,salary,is_active,joining_date,last_login\n"
            "1,Alice,25,45000.50,true,2024-01-15,2024-01-15T10:30:00\n2,Bob,30,55000.75,false,2023-06-20,2024-02-10T14:45:00\n"
            "3,Charlie,28,50000.00,true,2022-11-05,2024-03-12T09:15:00\n4,David,35,65000.25,true,2021-08-10,2024-04-20T18:20:00")
    resp, c = profile_csv_text(text)
    assert (resp["dataset"]["row_count"], resp["dataset"]["column_count"]) == (4, 7)
    assert [c[n]["inferred_type"] for n in ("customer_id", "name", "age", "salary", "is_active", "joining_date", "last_login")] == \
        ["numerical", "categorical", "numerical", "numerical", "boolean", "datetime", "datetime"]
    assert c["salary"]["summary"]["min"] == 45000.5 and c["salary"]["summary"]["max"] == 65000.25


def test_missing_values_sample_counts_and_percentages():
    text = "customer_id,name,age,salary,is_active\n1,Alice,25,45000.50,true\n2,,30,,false\n3,Charlie,,50000.00,true\n4,David,35,65000.25,"
    _, c = profile_csv_text(text)
    assert [c[n]["missing_count"] for n in ("customer_id", "name", "age", "salary", "is_active")] == [0, 1, 1, 1, 1]
    assert c["name"]["missing_pct"] == 25.0            # their null_pct 0.25 is a fraction; ours is a percentage
    assert c["is_active"]["inferred_type"] == "boolean"   # true/false text with a missing cell is still boolean


def test_numbers_mixed_with_words_are_reported_as_mixed():
    resp, c = profile_csv_text("customer_id,age\n1,25\n2,30\n3,unknown\n4,35")
    assert c["age"]["inferred_type"] == "mixed" and c["age"]["mixed_breakdown"] == {"numeric_values": 3, "text_values": 1}
    assert "MIXED_TYPES" in c["age"]["warnings"] and resp["status"] == "warning"


def test_distinct_counts_exclude_missing_and_repeats():
    _, c = profile_csv_text("customer_id,city\n1,Bengaluru\n2,Bengaluru\n3,Mysuru\n4,Mysuru\n5,Hubli")
    assert c["customer_id"]["unique_count"] == 5 and c["city"]["unique_count"] == 3


def test_whitespace_only_cells_count_as_missing_in_files():
    resp, c = profile_csv_text("a,b\n1,x\n2,   \n3,y\n")
    assert c["b"]["missing_count"] == 1 and c["b"]["unique_count"] == 2
    _, c = profile_csv_text("a,b\n1,x\n  ,y\n3,z\n")
    assert c["a"]["inferred_type"] == "numerical" and c["a"]["missing_count"] == 1      # still numeric: the blank was the only reason it read as text


def test_duplicate_header_in_a_file_is_reported_not_renamed():
    resp, _ = profile_csv_text("a,a\n1,2\n")
    assert resp["status"] == "failed" and resp["errors"][0]["code"] == "DUPLICATE_COLUMN_NAMES"


def test_utf8_byte_order_mark_does_not_change_the_first_column_name():
    resp, c = profile_csv_text(b"\xef\xbb\xbfid,name\n1,a\n2,b\n", raw=True)
    assert resp["dataset"]["column_names"] == ["id", "name"]


def test_empty_file_returns_a_controlled_error():
    resp, _ = profile_csv_text(b"", raw=True)
    assert resp["status"] == "failed" and resp["errors"][0]["code"] == "DATASET_LOAD_FAILED"


def test_a_table_passed_by_the_caller_keeps_the_callers_missing_definition():
    """When the backend loads the table, whitespace-only cells stay values; the caller decides how to treat them."""
    resp = run_profiling(REQ, dataframe=pd.DataFrame({"b": ["x", "   ", "y"]}))
    col = resp["columns"][0]
    assert col["missing_count"] == 0 and col["unique_count"] == 3
