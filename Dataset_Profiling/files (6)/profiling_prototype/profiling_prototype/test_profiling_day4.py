"""Day 4 tests: distributions, correlations, class distribution, skewed and high-cardinality data."""
import numpy as np
import pandas as pd

from profiling_service import RESPONSE_SCHEMA, run_profiling
from schema_validation import validate


def run(df, **options):
    request = {"schema_version": "1.0-draft", "request_id": "d4",
               "dataset_reference": {"dataset_id": "d4", "source_type": "file"}}
    if options:
        request["options"] = options
    resp = run_profiling(request, dataframe=df)
    assert validate(resp, RESPONSE_SCHEMA) == [], validate(resp, RESPONSE_SCHEMA)
    return resp


def col(resp, name):
    return next(c for c in resp["columns"] if c["name"] == name)


def codes(resp):
    return {(w["code"], w["column"]) for w in resp["warnings"]}


# ---- distribution summaries ---------------------------------------------------------------
def test_quartiles_and_skewness_are_reported():
    s = col(run(pd.DataFrame({"v": range(1, 21)})), "v")["summary"]
    assert s["q1"] == 5.75 and s["q3"] == 15.25 and s["skewness"] == 0.0


def test_histogram_counts_add_up():
    resp = run(pd.DataFrame({"v": [1, 2, 2, 3, 3, 3, 4, 4, 5, 9]}))
    bins = col(resp, "v")["histogram"]
    assert sum(b["count"] for b in bins) == 10
    assert bins[0]["start"] == 1.0 and bins[-1]["end"] == 9.0


def test_skewed_distribution_is_visible():
    values = [1] * 60 + [2] * 25 + [3] * 10 + [500, 900]          # long right tail
    c = col(run(pd.DataFrame({"v": values})), "v")
    assert c["summary"]["skewness"] > 1
    assert c["summary"]["mean"] > c["summary"]["median"]
    assert c["histogram"][0]["count"] > 90                         # almost everything in the first bin


def test_no_histogram_for_constant_or_identifier_columns():
    resp = run(pd.DataFrame({"k": [7] * 10, "row_id": range(10), "v": range(10, 20)}))
    assert "histogram" not in col(resp, "k") and "histogram" not in col(resp, "row_id")
    assert "histogram" in col(resp, "v")


def test_statistics_off_removes_histogram_and_summary():
    c = col(run(pd.DataFrame({"v": range(10)}), include_statistics=False), "v")
    assert "histogram" not in c and "summary" not in c


def test_categorical_frequency_table_size_follows_option():
    df = pd.DataFrame({"g": list("aaaabbbccd")})
    assert len(col(run(df), "g")["top_values"]) == 4
    assert len(col(run(df, top_n_values=2), "g")["top_values"]) == 2


# ---- constant-column and high-cardinality warnings ----------------------------------------------
def test_many_unique_values():
    df = pd.DataFrame({"nickname": [f"n{i}" for i in range(1000)], "amount": np.arange(1000) * 1.5,
                       "user_id": [f"u{i}" for i in range(1000)]})
    resp = run(df)
    assert ("HIGH_CARDINALITY", "nickname") in codes(resp)
    assert ("HIGH_CARDINALITY", "amount") not in codes(resp)       # a numeric column may be all-unique
    assert ("HIGH_CARDINALITY", "user_id") not in codes(resp)      # identifiers are expected to be unique


def test_constant_and_near_constant_columns():
    df = pd.DataFrame({"one": [5] * 30, "almost": [1] * 29 + [2], "text_one": ["x"] * 30})
    resp = run(df)
    assert ("CONSTANT_COLUMN", "one") in codes(resp) and ("CONSTANT_COLUMN", "text_one") in codes(resp)
    assert ("CONSTANT_COLUMN", "almost") not in codes(resp)


# ---- correlations ---------------------------------------------------------------------------------
def test_correlation_values_and_order():
    x = np.arange(1, 21)
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"x": x, "double": 2 * x, "neg": -x, "noise": rng.normal(size=20)})
    pairs = run(df)["correlations"]
    got = {(p["column_a"], p["column_b"]): p["coefficient"] for p in pairs}
    assert got[("x", "double")] == 1.0 and got[("x", "neg")] == -1.0
    assert [abs(p["coefficient"]) for p in pairs] == sorted((abs(p["coefficient"]) for p in pairs), reverse=True)


def test_correlation_skips_identifier_constant_and_text_columns():
    df = pd.DataFrame({"row_id": range(1, 21), "a": range(20), "b": [i * i for i in range(20)],
                       "k": [3] * 20, "t": list("ab") * 10})
    pairs = run(df)["correlations"]
    assert {(p["column_a"], p["column_b"]) for p in pairs} == {("a", "b")}


def test_correlation_absent_when_not_applicable_or_switched_off():
    assert "correlations" not in run(pd.DataFrame({"a": range(10), "t": list("ab") * 5}))
    assert "correlations" not in run(pd.DataFrame({"a": range(10), "b": range(10)}), include_correlations=False)


# ---- class distribution -------------------------------------------------------------------------------
def test_class_distribution_for_imbalanced_target():
    df = pd.DataFrame({"flag": [0] * 912 + [1] * 88, "f": range(1000)})
    cd = run(df, target_column="flag")["class_distribution"]
    assert cd["class_count"] == 2 and cd["majority_class"] == "0" and cd["minority_class"] == "1"
    assert cd["classes"][0] == {"value": "0", "count": 912, "percentage": 91.2}
    assert cd["imbalance_ratio"] == 10.36 and cd["missing_count"] == 0


def test_class_distribution_reports_missing_target_values():
    df = pd.DataFrame({"t": ["a", "a", "b", None, None]})
    cd = run(df, target_column="t")["class_distribution"]
    assert cd["missing_count"] == 2 and sum(c["count"] for c in cd["classes"]) == 3


def test_class_distribution_absent_without_target():
    assert "class_distribution" not in run(pd.DataFrame({"t": list("abab")}))


def test_unknown_target_is_an_error():
    resp = run(pd.DataFrame({"t": list("abab")}), target_column="nope")
    assert resp["status"] == "failed"
    assert resp["errors"][0]["code"] == "TARGET_NOT_FOUND" and resp["errors"][0]["field"] == "options.target_column"


def test_continuous_target_is_skipped_with_a_warning():
    rng = np.random.default_rng(1)
    resp = run(pd.DataFrame({"price": rng.normal(size=200)}), target_column="price")
    assert "class_distribution" not in resp
    assert ("CLASS_DISTRIBUTION_SKIPPED", "price") in codes(resp)


def test_single_class_target_has_no_ratio():
    cd = run(pd.DataFrame({"t": ["a"] * 5}), target_column="t")["class_distribution"]
    assert cd["class_count"] == 1 and cd["imbalance_ratio"] is None


def test_source_data_untouched():
    df = pd.DataFrame({"t": list("aabb"), "v": [1.0, 2.0, 3.0, 4.0]})
    before = df.copy(deep=True)
    run(df, target_column="t")
    pd.testing.assert_frame_equal(df, before)
