"""Day 5 tests: mixed types, empty columns, unusual values, large tables. Behaviour is documented, not changed."""
import time
import warnings

import numpy as np
import pandas as pd

from profiler import profile_dataset
from profiling_service import RESPONSE_SCHEMA, run_profiling
from schema_validation import validate


def service(df):
    request = {"schema_version": "1.0-draft", "request_id": "day5",
               "dataset_reference": {"dataset_id": "d", "source_type": "file"}}
    return run_profiling(request, dataframe=df)


def test_infinite_values_do_not_crash_and_are_left_out_of_statistics():
    df = pd.DataFrame({"a": [np.inf, 1.0, 2.0, 3.0, -np.inf], "b": [1, 2, 3, 4, 5]})
    with warnings.catch_warnings():
        warnings.simplefilter("error")                      # no numpy warnings allowed either
        r = profile_dataset(df)
    s = r["columns"]["a"]["summary"]
    assert (s["min"], s["max"]) == (1.0, 3.0)               # finite values only
    assert len(r["columns"]["a"]["histogram"]) == 3


def test_column_of_only_infinite_values():
    r = profile_dataset(pd.DataFrame({"a": [np.inf, np.inf, np.inf]}))
    assert r["columns"]["a"]["summary"]["min"] is None
    assert "histogram" not in r["columns"]["a"]


def test_unhashable_cells_do_not_crash():
    df = pd.DataFrame({"a": [[1, 2], [3], [1, 2]], "b": [{"k": 1}, {"k": 2}, {"k": 1}]})
    r = profile_dataset(df)
    assert r["columns"]["a"]["unique_count"] == 2
    assert "duplicates_computed_on_string_form" in r["warnings"]


def test_mixed_column_is_flagged_and_has_no_numeric_statistics():
    c = profile_dataset(pd.DataFrame({"m": [1, "two", 3.5, "four", None]}))["columns"]["m"]
    assert c["inferred_type"] == "mixed" and "mixed_types" in c["warnings"]
    assert c["mixed_breakdown"] == {"numeric_values": 2, "text_values": 2}
    assert "summary" not in c and "histogram" not in c


def test_mixed_bool_text_and_numbers():
    c = profile_dataset(pd.DataFrame({"m": [True, "x", 1, None]}))["columns"]["m"]
    assert c["inferred_type"] == "mixed"


def test_empty_column_has_no_statistics_and_is_ignored_by_correlations():
    df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [2, 4, 6, 9], "e": [None] * 4})
    r = profile_dataset(df)
    c = r["columns"]["e"]
    assert c["inferred_type"] == "empty" and c["missing_pct"] == 100.0 and c["unique_count"] == 0
    assert "summary" not in c
    assert all("e" not in (p["column_a"], p["column_b"]) for p in r.get("correlations", []))


def test_documented_behaviour_numbers_stored_as_text_are_categorical():
    c = profile_dataset(pd.DataFrame({"a": ["1", "2", "3", "4"]}))["columns"]["a"]
    assert c["inferred_type"] == "categorical"              # known limitation, listed in the contract note


def test_documented_behaviour_whitespace_only_text_is_not_missing():
    c = profile_dataset(pd.DataFrame({"a": ["x", "  ", "y", " "]}))["columns"]["a"]
    assert c["missing_count"] == 0                          # use metadata.missing_value_markers for blanks


def test_service_responses_stay_schema_valid_for_awkward_tables():
    awkward = {
        "mixed": pd.DataFrame({"m": [1, "two", 3, "four"]}),
        "empty column": pd.DataFrame({"a": [1, 2, 3], "e": [None, None, None]}),
        "infinite": pd.DataFrame({"a": [np.inf, 1.0, 2.0]}),
        "lists": pd.DataFrame({"a": [[1], [2], [1]]}),
        "single row": pd.DataFrame({"a": [1], "b": ["x"]}),
        "one column": pd.DataFrame({"a": [1, 2, 3, 4]}),
        "all missing": pd.DataFrame({"a": [None, None], "b": [None, None]}),
    }
    for label, df in awkward.items():
        resp = service(df)
        assert resp["status"] in ("success", "warning"), label
        assert validate(resp, RESPONSE_SCHEMA) == [], label


def test_a_table_with_200000_rows_profiles_in_reasonable_time():
    rng = np.random.default_rng(0)
    n = 200_000
    df = pd.DataFrame({"id": np.arange(n), "x": rng.normal(size=n), "c": rng.choice(list("abcde"), n)})
    start = time.perf_counter()
    r = profile_dataset(df)
    assert time.perf_counter() - start < 30                 # very loose bound; typical time is about a second
    assert r["dataset"]["row_count"] == n


def test_compare_profiles_reports_changes():
    from compare_profiles import compare
    before = pd.DataFrame({"age": [25.0, None, 30.0], "city": ["a", "b", "a"], "junk": [None, None, None]})
    after = pd.DataFrame({"age": [25.0, 27.5, 30.0], "city": ["a", "b", "a"], "city_code": [0, 1, 0]})
    text = "\n".join(compare(service(before), service(after)))
    assert "Columns: 3 -> 3" in text
    assert "Removed columns: ['junk']" in text and "Added columns:   ['city_code']" in text
    assert "age: missing 1 -> 0" in text
