"""Hand-calculated expected values (Week 3, Day 2). Every expected number below was worked out by hand; the arithmetic is in the comments."""
import pandas as pd

from profiling_service import run_profiling

REQ = {"schema_version": "1.0-draft", "request_id": "manual", "dataset_reference": {"dataset_id": "manual", "source_type": "file"}}


def profile(df):
    resp = run_profiling(REQ, dataframe=df)
    assert resp["status"] != "failed", resp["errors"]
    return resp, {c["name"]: c for c in resp["columns"]}


def test_numerical_summary_by_hand():
    # values 2, 4, 4, 4, 5, 5, 7, 9 (8 values, sum 40)
    # mean 40 / 8 = 5.0 | median (4 + 5) / 2 = 4.5 | min 2 | max 9
    # deviations from 5: -3 -1 -1 -1 0 0 2 4 -> squares 9 1 1 1 0 0 4 16 = 32
    # sample standard deviation sqrt(32 / 7) = 2.1381 (4 decimals)
    # Q1: position 0.25 * (8 - 1) = 1.75 -> between 4 and 4 = 4.0 | Q3: position 5.25 -> 5 + 0.25 * (7 - 5) = 5.5
    _, c = profile(pd.DataFrame({"v": [2, 4, 4, 4, 5, 5, 7, 9]}))
    s = c["v"]["summary"]
    assert (s["min"], s["max"], s["mean"], s["median"]) == (2.0, 9.0, 5.0, 4.5)
    assert s["std"] == 2.1381
    assert (s["q1"], s["q3"]) == (4.0, 5.5)


def test_categorical_frequencies_by_hand():
    # a, b, a, c, a, b -> a 3 of 6 = 50.00% | b 2 of 6 = 33.33% | c 1 of 6 = 16.67% | 3 distinct values
    _, c = profile(pd.DataFrame({"k": ["a", "b", "a", "c", "a", "b"]}))
    assert c["k"]["unique_count"] == 3
    assert [(t["value"], t["count"], t["percentage"]) for t in c["k"]["top_values"]] == [("a", 3, 50.0), ("b", 2, 33.33), ("c", 1, 16.67)]
    assert "summary" not in c["k"]


def test_missing_percentage_by_hand():
    # [1, missing, 3, missing, 5] -> 2 missing of 5 = 40.00% | 3 distinct non-missing values
    _, c = profile(pd.DataFrame({"m": [1, None, 3, None, 5]}))
    assert c["m"]["missing_count"] == 2 and c["m"]["missing_pct"] == 40.0 and c["m"]["unique_count"] == 3


def test_duplicate_rows_by_hand():
    # rows: (1,x) (1,x) (2,y) (1,x) -> the 2nd and 4th rows repeat the 1st = 2 duplicate rows
    resp, _ = profile(pd.DataFrame({"a": [1, 1, 2, 1], "b": ["x", "x", "y", "x"]}))
    assert resp["dataset"]["duplicate_row_count"] == 2


def test_mixed_type_column_by_hand():
    # 1, "a", 2, "b", "c" -> 2 numeric values and 3 text values
    resp, c = profile(pd.DataFrame({"x": [1, "a", 2, "b", "c"]}))
    assert c["x"]["inferred_type"] == "mixed" and c["x"]["mixed_breakdown"] == {"numeric_values": 2, "text_values": 3}
    assert "MIXED_TYPES" in c["x"]["warnings"]


def test_empty_and_constant_columns_by_hand():
    # an all-missing column is empty (missing 100%, 0 distinct); a column of one repeated value has 1 distinct value
    _, c = profile(pd.DataFrame({"e": [None, None, None], "k": [7, 7, 7], "v": [1, 2, 3]}))
    assert c["e"]["inferred_type"] == "empty" and c["e"]["missing_pct"] == 100.0 and c["e"]["unique_count"] == 0
    assert "EMPTY_COLUMN" in c["e"]["warnings"]
    assert c["k"]["unique_count"] == 1 and "CONSTANT_COLUMN" in c["k"]["warnings"]
