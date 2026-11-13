"""Regression tests (Week 3, Day 4): numerical, categorical, mixed-type, null-heavy, duplicate-heavy and wide datasets,
statistics checked against independent calculations, and unsupported input. Synthetic data only, fixed seeds."""
import json
import math
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from profiling_service import RESPONSE_SCHEMA, run_profiling
from schema_validation import validate

REQ = {"schema_version": "1.0-draft", "request_id": "regression", "dataset_reference": {"dataset_id": "reg", "source_type": "file"}}


def profile(df, **options):
    resp = run_profiling({**REQ, **({"options": options} if options else {})}, dataframe=df)
    assert resp["status"] != "failed", resp["errors"]
    assert not validate(resp, RESPONSE_SCHEMA)
    json.dumps(resp, allow_nan=False)
    return resp, {c["name"]: c for c in resp["columns"]}


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-4)


def numerical_frame(n=5000):
    rng = np.random.default_rng(11)
    return pd.DataFrame({"normal": rng.normal(50, 10, n), "uniform": rng.uniform(0, 1, n), "integers": rng.integers(0, 1000, n),
                         "skewed": rng.lognormal(0, 1.5, n), "negative": -rng.exponential(5, n)})


def test_numerical_dataset_matches_independent_calculation():
    df = numerical_frame()
    resp, cols = profile(df)
    assert resp["dataset"]["row_count"] == 5000 and resp["dataset"]["column_count"] == 5
    for name in df.columns:
        x = df[name].to_numpy(dtype=float)
        s = cols[name]["summary"]
        expected = {"min": x.min(), "max": x.max(), "mean": x.mean(), "median": np.median(x), "std": x.std(ddof=1),
                    "q1": np.percentile(x, 25), "q3": np.percentile(x, 75)}
        for key, value in expected.items():
            assert close(s[key], round(float(value), 4)), (name, key, s[key], value)
        assert cols[name]["inferred_type"] == "numerical" and cols[name]["missing_count"] == 0
    assert cols["skewed"]["summary"]["skewness"] > 1 and abs(cols["normal"]["summary"]["skewness"]) < 0.2   # skew is visible
    assert sum(b["count"] for b in cols["normal"]["histogram"]) == 5000


def test_categorical_dataset_frequencies_match_independent_count():
    rng = np.random.default_rng(12)
    df = pd.DataFrame({"binary": rng.choice(["yes", "no"], 3000, p=[0.7, 0.3]), "five": rng.choice(list("abcde"), 3000),
                       "twenty": rng.choice([f"c{i}" for i in range(20)], 3000), "many": [f"u{i % 900}" for i in range(3000)]})
    resp, cols = profile(df, top_n_values=5)
    for name in df.columns:
        counts = Counter(df[name]).most_common()
        assert cols[name]["unique_count"] == len(counts)
        top = cols[name]["top_values"]
        assert len(top) == min(5, len(counts))
        assert [t["count"] for t in top] == [c for _, c in sorted(counts, key=lambda kv: -kv[1])[:len(top)]]
        assert all(close(t["percentage"], round(100 * t["count"] / 3000, 2)) for t in top)
        assert "summary" not in cols[name]


def test_mixed_type_dataset():
    df = pd.DataFrame({"ints_and_text": [1, "a", 2, "b", 3, "c"], "bools": [True, False, True, True, False, True],
                       "date_text": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01", "2024-06-01"],
                       "floats": [1.5, 2.5, None, 4.5, 5.5, 6.5], "words": list("abcdef")})
    _, cols = profile(df)
    assert cols["ints_and_text"]["inferred_type"] == "mixed" and "MIXED_TYPES" in cols["ints_and_text"]["warnings"]
    assert cols["ints_and_text"]["mixed_breakdown"] == {"numeric_values": 3, "text_values": 3}
    assert cols["bools"]["inferred_type"] == "boolean"
    assert cols["date_text"]["inferred_type"] == "datetime"
    assert cols["floats"]["inferred_type"] == "numerical" and cols["floats"]["missing_count"] == 1
    assert cols["words"]["inferred_type"] == "categorical"


def test_numbers_stored_as_text_are_treated_as_text_not_numbers():
    """Documented behaviour: a text column holding digits is categorical. Convert the column before profiling to get numeric statistics."""
    _, cols = profile(pd.DataFrame({"digits": ["1", "2", "3", "2", "1"]}))
    assert cols["digits"]["inferred_type"] == "categorical" and "summary" not in cols["digits"]


def test_null_heavy_dataset():
    n = 1000
    rng = np.random.default_rng(13)
    df = pd.DataFrame({"half": np.where(rng.random(n) < 0.5, np.nan, rng.normal(size=n)),
                       "ninety": np.where(rng.random(n) < 0.9, np.nan, rng.normal(size=n)),
                       "one_value": [np.nan] * (n - 1) + [7.0], "all_missing": [np.nan] * n,
                       "text_90": np.where(rng.random(n) < 0.9, None, "x")})
    resp, cols = profile(df)
    for name in df.columns:
        assert cols[name]["missing_count"] == int(df[name].isna().sum())
        assert close(cols[name]["missing_pct"], round(100 * df[name].isna().mean(), 2))
    assert cols["all_missing"]["inferred_type"] == "empty" and "EMPTY_COLUMN" in cols["all_missing"]["warnings"]
    assert cols["one_value"]["summary"]["std"] is None and cols["one_value"]["summary"]["min"] == 7.0   # one value: no spread, reported as null
    assert "CONSTANT_COLUMN" in cols["one_value"]["warnings"]
    x = df["half"].dropna().to_numpy()
    assert close(cols["half"]["summary"]["mean"], round(float(x.mean()), 4))          # statistics ignore missing values


def test_duplicate_heavy_dataset():
    base = pd.DataFrame({"a": range(100), "b": [f"v{i % 7}" for i in range(100)]})
    many = pd.concat([base] * 100, ignore_index=True)                    # 10,000 rows, 100 distinct rows
    resp, _ = profile(many)
    assert resp["dataset"]["row_count"] == 10000 and resp["dataset"]["duplicate_row_count"] == 9900
    same = pd.DataFrame({"a": [1] * 500, "b": ["x"] * 500})
    resp, cols = profile(same)
    assert resp["dataset"]["duplicate_row_count"] == 499
    assert "CONSTANT_COLUMN" in cols["a"]["warnings"] and "CONSTANT_COLUMN" in cols["b"]["warnings"]


def wide_frame(n_columns, n_rows=100):
    rng = np.random.default_rng(14)
    data = {}
    for i in range(n_columns):
        data[f"col_{i:04d}"] = rng.normal(size=n_rows) if i % 2 == 0 else rng.choice(list("abcdef"), n_rows)
    return pd.DataFrame(data)


def test_wide_dataset_is_profiled_completely():
    df = wide_frame(300)
    resp, cols = profile(df)
    assert resp["dataset"]["column_count"] == 300 and len(resp["columns"]) == 300
    assert [c["position"] for c in resp["columns"]] == list(range(300))
    assert len(resp.get("correlations", [])) <= 200                      # correlation output is capped
    assert cols["col_0000"]["inferred_type"] == "numerical" and cols["col_0001"]["inferred_type"] == "categorical"


def test_unsupported_and_unreadable_input_returns_controlled_errors():
    cases = {"data.json": (b'{"a": 1}', "UNSUPPORTED_FORMAT"), "data.parquet": (b"PAR1", "UNSUPPORTED_FORMAT"),
             "data.txt": (b"a,b\n1,2\n", "UNSUPPORTED_FORMAT"), "empty.csv": (b"", "DATASET_LOAD_FAILED"),
             "spaces.csv": (b"   \n  \n", "DATASET_LOAD_FAILED"), "broken.xlsx": (b"not an excel file", "DATASET_LOAD_FAILED"),
             "binary.csv": (bytes(range(256)) * 4, "DATASET_LOAD_FAILED")}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (content, code) in cases.items():
            path = Path(tmp) / name
            path.write_bytes(content)
            resp = run_profiling({**REQ, "dataset_reference": {**REQ["dataset_reference"], "location": str(path)}})
            assert resp["status"] == "failed", name
            assert [e["code"] for e in resp["errors"]] == [code], (name, resp["errors"])
            assert resp["dataset"] is None and resp["columns"] == [] and not validate(resp, RESPONSE_SCHEMA)
            assert tmp not in json.dumps(resp)                                          # no path leaks
        folder = run_profiling({**REQ, "dataset_reference": {**REQ["dataset_reference"], "location": tmp}})
        assert folder["status"] == "failed" and folder["errors"][0]["code"] == "SOURCE_NOT_FOUND"
