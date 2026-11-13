import pytest

from leakage_checks import (
    check_leakage, read_correlations, resolve_leakage_settings)
from run_detection import detect_dataset
from test_profiling_integration import col, profile

PAIRS = [("vac", "sick", 0.9783), ("level", "vac", 0.0264),
         ("sick", "level", -0.97)]


def test_strong_suspect_found():
    out = check_leakage(PAIRS, "vac")
    assert out["status"] == "checked"
    assert [(s["column"], s["level"]) for s in out["suspects"]] == [
        ("sick", "strong")]


def test_negative_correlation_counts():
    out = check_leakage(PAIRS, "level")
    assert out["suspects"][0]["column"] == "sick"
    assert out["suspects"][0]["correlation"] < 0


def test_possible_level_between_thresholds():
    out = check_leakage([("a", "b", 0.85)], "a")
    assert out["suspects"][0]["level"] == "possible"


def test_nothing_above_threshold():
    out = check_leakage([("a", "b", 0.5)], "a")
    assert out["status"] == "checked" and out["suspects"] == []


def test_no_correlations_is_pending():
    assert check_leakage(None, "a")["status"] == "pending_integration"


def test_no_target_not_checked():
    assert check_leakage(PAIRS, None)["status"] == "not_checked"


def test_target_not_in_correlations_not_checked():
    out = check_leakage(PAIRS, "gender")
    assert out["status"] == "not_checked" and "gender" in out["reason"]


def test_limits_always_stated():
    assert "Numerical" in check_leakage(PAIRS, "vac")["limits"]


def test_settings_change_threshold():
    out = check_leakage([("a", "b", 0.6)], "a", settings={"possible": 0.5})
    assert len(out["suspects"]) == 1


@pytest.mark.parametrize("bad", [{"x": 1}, {"possible": 0}, {"possible": 2},
                                 {"possible": 0.99, "strong": 0.9}])
def test_bad_settings_rejected(bad):
    with pytest.raises(ValueError):
        resolve_leakage_settings(bad)


def test_read_correlations_skips_malformed():
    pairs, skipped = read_correlations({"correlations": [
        {"column_a": "a", "column_b": "b", "coefficient": 0.9},
        {"column_a": "a"}, {"column_a": "a", "column_b": "b",
                            "coefficient": 5}]})
    assert pairs == [("a", "b", 0.9)] and skipped == 2


def test_read_correlations_absent():
    assert read_correlations({}) == (None, 0)


def _hr(corr=True):
    cols = [
        col("id", "numerical", ident=True, unique=100),
        col("vac", "numerical", unique=60, summary={"min": 0, "max": 99}),
        col("sick", "numerical", unique=50, summary={"min": 20, "max": 80}),
    ]
    p = profile(cols)
    if corr:
        p["correlations"] = [
            {"column_a": "vac", "column_b": "sick", "coefficient": 0.97}]
    return p


def test_end_to_end_flags_column_and_keeps_it():
    r = detect_dataset(_hr(), overrides={"d.xlsx": "vac"})
    assert r["leakage_checks"]["status"] == "checked"
    roles = {x["column"]: x for x in r["column_roles"]}
    assert roles["sick"]["leakage_suspect"] == "strong"
    assert roles["sick"]["role"] == "feature"     # flagged, not removed
    assert "sick" in r["recommended_feature_columns"]
    assert any("leakage" in w for w in r["warnings"])


def test_end_to_end_without_correlations_pending():
    r = detect_dataset(_hr(corr=False), overrides={"d.xlsx": "vac"})
    assert r["leakage_checks"]["status"] == "pending_integration"
    assert all(x["leakage_suspect"] is None for x in r["column_roles"])


def test_zero_row_issue_not_listed_in_roles():
    q = {"dataset": "d.xlsx", "issues": [
        {"rule_id": "NULL_CHECK", "severity": "Blocking",
         "affected_column": "sick", "affected_rows": 0}]}
    r = detect_dataset(_hr(), quality=q, overrides={"d.xlsx": "vac"})
    roles = {x["column"]: x for x in r["column_roles"]}
    assert roles["sick"]["quality_issue_codes"] == []
    assert roles["sick"]["quality_blocked"] is False
