"""Target-leakage check from the profiling module's correlations.

Idea in simple words: if one column moves almost exactly with the target
(correlation near +1 or -1), it may be a copy of the answer, or only known
after the answer. Such a column makes a model look great in testing and fail
in real use. This check FLAGS these columns. It does not remove them; the
user decides.

Limits (stated in the result, never hidden):
  * only numerical column pairs (that is all the profiling module gives),
  * only straight-line (Pearson) relationships,
  * a categorical or missing target cannot be checked,
  * derived or time-based leakage is not found by correlation.

Thresholds are proposed defaults, not from the SRS. Change them through
`leakage_settings`.
"""

DEFAULT_LEAKAGE_SETTINGS = {
    "possible": 0.80,   # |r| at or above this: possible leakage, review
    "strong": 0.95,     # |r| at or above this: strong leakage suspect
}

LIMITS = ("Numerical column pairs only, straight-line (Pearson) "
          "relationships only. Categorical targets, derived columns and "
          "time-based leakage are not detected.")


def resolve_leakage_settings(settings=None):
    merged = dict(DEFAULT_LEAKAGE_SETTINGS)
    for key, value in (settings or {}).items():
        if key not in merged:
            raise ValueError(f"Unknown leakage setting: {key!r}")
        if not isinstance(value, (int, float)) or not 0 < value <= 1:
            raise ValueError(f"Leakage setting {key!r} must be in (0, 1]")
        merged[key] = float(value)
    if merged["possible"] > merged["strong"]:
        raise ValueError("'possible' must not be above 'strong'")
    return merged


def read_correlations(profile):
    """Return (pairs, skipped). Pairs are (column_a, column_b, coefficient)."""
    raw = profile.get("correlations")
    if raw is None:
        return None, 0
    pairs, skipped = [], 0
    for item in raw if isinstance(raw, list) else []:
        try:
            a, b = str(item["column_a"]), str(item["column_b"])
            r = float(item["coefficient"])
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        if r != r or abs(r) > 1:   # NaN or out of range
            skipped += 1
            continue
        pairs.append((a, b, r))
    return pairs, skipped


def check_leakage(pairs, target, skipped=0, settings=None):
    """Compare every column with the target. pairs=None means the profile
    had no correlations at all."""
    cfg = resolve_leakage_settings(settings)
    base = {"thresholds": {"possible": cfg["possible"],
                           "strong": cfg["strong"]},
            "limits": LIMITS, "suspects": []}
    if pairs is None:
        return {**base, "status": "pending_integration",
                "reason": "The profile has no correlations, so the check "
                          "was not run."}
    if not target:
        return {**base, "status": "not_checked",
                "reason": "No target chosen yet, so there is nothing to "
                          "compare against."}
    related = [(b if a == target else a, r)
               for a, b, r in pairs if target in (a, b) and a != b]
    if not related:
        return {**base, "status": "not_checked",
                "reason": f"'{target}' is not in the correlations (it is "
                          "not a numerical column, or it is an identifier "
                          "or constant), so it could not be checked."}
    suspects = []
    for column, r in sorted(related, key=lambda x: -abs(x[1])):
        size = abs(r)
        if size >= cfg["possible"]:
            suspects.append({
                "column": column, "correlation": round(r, 4),
                "level": "strong" if size >= cfg["strong"] else "possible",
                "message": (f"'{column}' moves almost together with the "
                            f"target (correlation {r:+.2f}). Check that it "
                            "is known before the outcome and is not a copy "
                            "of it."),
            })
    out = {**base, "status": "checked", "suspects": suspects,
           "reason": (f"{len(suspects)} column(s) at or above "
                      f"{cfg['possible']:.2f}" if suspects else
                      "No column reaches the threshold.")}
    if skipped:
        out["reason"] += f" ({skipped} malformed correlation(s) ignored.)"
    return out
