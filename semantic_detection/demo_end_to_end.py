"""End-to-end evidence run: synthetic data -> stand-in profile -> detection.

The profile is built here by a small stand-in that follows Sanjay's profiling
format (contract 1.0-draft). It is NOT Sanjay's profiler. It only lets this
module be shown on classification and regression examples.
Run:  python demo_end_to_end.py
"""
import json
import pandas as pd
from make_synthetic_datasets import build
from run_detection import run_detection
from training_rules import training_blockers


def make_profile(name, df, target=None):
    cols = []
    for i, c in enumerate(df.columns):
        s = df[c]
        unique = int(s.nunique())
        miss = int(s.isna().sum())
        ident = unique == len(s) and any(
            w in c.lower() for w in ("id", "key", "number"))
        if pd.api.types.is_numeric_dtype(s):
            kind = "numerical" if unique > 2 else "categorical"
        elif pd.api.types.is_datetime64_any_dtype(s):
            kind = "datetime"
        else:
            kind = "categorical" if unique <= 50 else "text"
        e = {"name": c, "position": i, "dtype": str(s.dtype),
             "inferred_type": kind, "missing_count": miss,
             "missing_pct": round(100 * miss / len(s), 2),
             "unique_count": unique, "likely_identifier": bool(ident),
             "warnings": []}
        if kind == "numerical":
            e["summary"] = {"min": float(s.min()), "max": float(s.max()),
                            "mean": float(s.mean())}
        elif kind == "categorical" and not ident:
            vc = s.value_counts().head(5)
            e["top_values"] = [{"value": str(k), "count": int(v),
                                "percentage": round(100 * v / len(s), 2)}
                               for k, v in vc.items()]
        cols.append(e)
    p = {"schema_version": "1.0-draft", "status": "success",
         "dataset_reference": {"dataset_id": "ds-" + name, "name": name},
         "dataset": {"row_count": len(df), "column_count": df.shape[1],
                     "column_names": list(df.columns),
                     "duplicate_row_count": int(df.duplicated().sum())},
         "columns": cols, "warnings": [], "errors": []}
    num = df.select_dtypes("number").columns
    corr = []
    for a in range(len(num)):
        for b in range(a + 1, len(num)):
            v = df[num[a]].corr(df[num[b]])
            if pd.notna(v):
                corr.append({"column_a": num[a], "column_b": num[b],
                             "coefficient": round(float(v), 4)})
    p["correlations"] = corr
    return p


def show(title, result):
    print("=" * 70)
    print(title)
    for k in ("dataset_id", "target", "target_source", "target_confirmed",
              "problem_type", "confidence", "source", "needs_confirmation",
              "features_status"):
        print(f"  {k:20}: {result[k]}")
    print("  evidence            :", result["evidence"])
    print("  alternatives        :", [a["problem_type"]
                                     for a in result["alternatives"]])
    print("  recommended features:", result["recommended_feature_columns"])
    print("  leakage_checks      :", result["leakage_checks"]["status"],
          [s["column"] for s in result["leakage_checks"].get("suspects", [])])
    print("  warnings            :", result["warnings"])
    print("  training blockers   :", training_blockers(result))


def main():
    data = build()
    cases = [("churn_classification.csv", "Customer churn (classification)"),
             ("house_price_regression.csv", "House price (regression)")]
    for fname, title in cases:
        df = data[fname]
        prof = make_profile(fname, df)
        did = prof["dataset_reference"]["dataset_id"]
        show(title + " - 1. suggestion only", run_detection([prof])[0])
        top = run_detection([prof])[0]["target"]
        r2 = run_detection([prof], overrides={did: top})[0]
        show(title + " - 2. user picked the target", r2)
        other = [c for c in df.columns if c != top][0]
        r3 = run_detection([prof], overrides={did: other})[0]
        show(title + f" - 3. user overrides with '{other}' (override wins)", r3)
        feats = r2["recommended_feature_columns"]
        r4 = run_detection([prof], overrides={did: top},
                           problem_type_override=r2["problem_type"],
                           approved_feature_columns={did: feats})[0]
        show(title + " - 4. target + problem type + features approved", r4)
    anon = data["ambiguous_targets.csv"]
    show("No clear target (ambiguous columns)",
         run_detection([make_profile("ambiguous_targets.csv", anon)])[0])


if __name__ == "__main__":
    main()
