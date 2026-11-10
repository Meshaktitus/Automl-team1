import numpy as np
import pandas as pd
from profiler import profile_dataset


def sample():
    return pd.DataFrame({
        "age": [25, 30, None, 41, 30],
        "city": ["Bengaluru", "Pune", "Pune", "Delhi", "Pune"],
        "joined": ["2024-01-05", "2024-02-11", "2024-03-02", None, "2024-02-11"],
    })


def test_counts_and_types():
    r = profile_dataset(sample())
    assert r["dataset"]["row_count"] == 5
    assert r["dataset"]["column_count"] == 3
    assert r["columns"]["age"]["inferred_type"] == "numerical"
    assert r["columns"]["city"]["inferred_type"] == "categorical"
    assert r["columns"]["joined"]["inferred_type"] == "datetime"


def test_missing_and_unique():
    c = profile_dataset(sample())["columns"]["age"]
    assert c["missing_count"] == 1
    assert c["missing_pct"] == 20.0
    assert c["unique_count"] == 3


def test_numeric_summary():
    s = profile_dataset(sample())["columns"]["age"]["summary"]
    assert s["min"] == 25 and s["max"] == 41
    assert s["median"] == 30


def test_categorical_has_frequencies_not_stats():
    c = profile_dataset(sample())["columns"]["city"]
    assert "summary" not in c
    assert c["top_values"]["Pune"] == 3


def test_duplicate_rows():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    assert profile_dataset(df)["dataset"]["duplicate_row_count"] == 1


def test_empty_column():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [None, None, None]})
    r = profile_dataset(df)
    assert r["columns"]["b"]["inferred_type"] == "empty"
    assert "empty_column" in r["columns"]["b"]["warnings"]


def test_constant_column():
    df = pd.DataFrame({"a": [1, 2, 3], "k": [7, 7, 7]})
    assert "constant_column" in profile_dataset(df)["columns"]["k"]["warnings"]


def test_mixed_type_column():
    df = pd.DataFrame({"m": [1, "two", 3, "four"]})
    c = profile_dataset(df)["columns"]["m"]
    assert c["inferred_type"] == "mixed"
    assert c["mixed_breakdown"] == {"numeric_values": 2, "text_values": 2}


def test_high_cardinality():
    df = pd.DataFrame({"nickname": [f"u{i}" for i in range(50)],
                       "user_id": [f"u{i}" for i in range(50)]})
    c = profile_dataset(df)["columns"]
    assert "high_cardinality" in c["nickname"]["warnings"]
    assert "high_cardinality" not in c["user_id"]["warnings"]   # identifiers are expected to be unique


def test_empty_dataset():
    r = profile_dataset(pd.DataFrame())
    assert r["status"] == "warning" and "empty_dataset" in r["warnings"]


def test_invalid_input():
    assert profile_dataset([1, 2, 3])["status"] == "failed"


def test_source_not_modified():
    df = sample()
    before = df.copy(deep=True)
    profile_dataset(df)
    pd.testing.assert_frame_equal(df, before)


def test_time_and_text_columns():
    import datetime as dt
    df = pd.DataFrame({"t": [dt.time(7), dt.time(15), dt.time(23)],
                       "doc": ["x" * 120, "y" * 200, "z" * 90]})
    c = profile_dataset(df)["columns"]
    assert c["t"]["inferred_type"] == "time"
    assert c["doc"]["inferred_type"] == "text" and "top_values" not in c["doc"]


def test_identifier_flag():
    df = pd.DataFrame({"EmployeeID": [1, 2, 3, 4], "score": [5, 5, 6, 7]})
    c = profile_dataset(df)["columns"]
    assert c["EmployeeID"]["likely_identifier"] is True
    assert c["score"]["likely_identifier"] is False


def test_relationships_do_not_merge_tables():
    from profiler import profile_tables
    a = pd.DataFrame({"EmpID": [1, 2, 3]})
    b = pd.DataFrame({"EmpID": [2, 3, 9], "x": [1, 2, 3]})
    r = profile_tables({"a": a, "b": b})
    assert set(r["tables"]) == {"a", "b"}
    assert r["relationships"][0]["values_only_in_b"] == 1
    assert a.shape == (3, 1) and b.shape == (3, 2)


def test_identifier_columns_do_not_expose_values():
    df = pd.DataFrame({"LoginID": ["a\\x", "b\\y", "c\\z"], "city": ["P", "P", "D"]})
    c = profile_dataset(df)["columns"]
    assert "top_values" not in c["LoginID"]
    assert "top_values" in c["city"]
