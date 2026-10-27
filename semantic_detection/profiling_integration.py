"""Use Sanjay's dataset-profiling output (contract 1.0-draft) as the input of
semantic detection, instead of reading the raw data again.

A profile has no raw values, only facts about each column (type, missing,
unique count, min/max, top values). This module rebuilds a small stand-in
sample from those facts, runs the same rules as semantic_rules.py, and then
uses the profile's own flags as extra evidence:
  likely_identifier = true  -> identifier
  inferred_type text        -> text
The result has the same columns as analyze_semantics.py, so target_suggestions,
problem_detection and quality_integration work on it unchanged.

The stand-in sample is an approximation. Use --compare to check it against the
report built from the real data.

Usage:
    python profiling_integration.py --profiles "C:\\path\\to\\profiles"
    python profiling_integration.py --profiles <folder> --compare outputs\\semantic_analysis_report.csv
"""
import argparse
import json
from datetime import time as dt_time
from pathlib import Path

import pandas as pd

from semantic_rules import detect_semantic_type

PROJECT_FOLDER = Path(__file__).resolve().parent
DEFAULT_OUTPUT = PROJECT_FOLDER / "outputs" / "profiling_semantic_report.csv"
SAMPLE_CAP = 2000
SUPPORTED_VERSION = "1.0-draft"
REQUIRED_COLUMN_FIELDS = (
    "name", "dtype", "inferred_type", "missing_count", "missing_pct",
    "unique_count", "likely_identifier",
)


def load_profile(source):
    """Read one profiling response from a JSON file path or a loaded dict."""
    if isinstance(source, (str, Path)):
        with open(source, encoding="utf-8") as handle:
            data = json.load(handle)
    else:
        data = source
    if not isinstance(data, dict):
        raise ValueError("Profile must be a JSON object")
    if data.get("status") == "failed":
        raise ValueError(
            "Profile has status 'failed': "
            + "; ".join(str(e.get("code")) for e in data.get("errors", []))
        )
    if not isinstance(data.get("dataset"), dict) or not isinstance(
        data.get("columns"), list
    ):
        raise ValueError("Profile needs a 'dataset' object and a 'columns' list")
    if data.get("schema_version") != SUPPORTED_VERSION:
        raise ValueError(
            f"Unsupported schema_version {data.get('schema_version')!r}; "
            f"expected {SUPPORTED_VERSION!r}"
        )
    for column in data["columns"]:
        missing = [f for f in REQUIRED_COLUMN_FIELDS if f not in column]
        if missing:
            raise ValueError(
                f"Column {column.get('name')!r} lacks fields: {missing}"
            )
    return data


def dataset_name(profile):
    ref = profile.get("dataset_reference") or {}
    return str(ref.get("name") or ref.get("dataset_id") or "unknown")


def _whole_numbers(column, low, high, unique):
    if str(column["dtype"]).startswith(("int", "uint")):
        return True
    if low is None or high is None:
        return False
    return float(low).is_integer() and float(high).is_integer() and (
        unique <= high - low + 1
    )


def _stand_in_values(column, non_null):
    """Rebuild a small list of values that has the same shape as the column."""
    inferred = column["inferred_type"]
    unique = int(column["unique_count"])
    summary = column.get("summary") or {}
    top = column.get("top_values") or []
    if non_null == 0 or inferred == "empty":
        return []

    factor = min(1.0, SAMPLE_CAP / non_null)
    size = max(1, round(non_null * factor))
    if unique > 50:
        unique = max(51, round(unique * factor))
    unique = max(1, min(unique, size))

    if inferred == "datetime":
        stamps = [summary.get("min"), summary.get("max")]
        stamps = [pd.Timestamp(s) for s in stamps if s]
        return stamps or [pd.Timestamp("2000-01-01")]

    if inferred == "time":
        values = []
        for item in top:
            h, m, *rest = [int(p) for p in str(item["value"]).split(":")]
            values.append(dt_time(h, m, rest[0] if rest else 0))
        return values or [dt_time(0, 0)]

    if inferred in {"numerical", "boolean"} and "min" in summary:
        low, high = summary.get("min"), summary.get("max")
        if low is None or high is None:
            return []
        if unique == 1:
            return [low]
        points = [
            low + (high - low) * i / (unique - 1) for i in range(unique)
        ]
        if _whole_numbers(column, low, high, unique):
            points = [int(round(p)) for p in points]
            points = list(dict.fromkeys(points))
        return points

    if inferred == "text":
        length = int(summary.get("avg_length") or 1)
        return ["x" * max(1, length)] * min(size, 20)

    # categorical, boolean, mixed: top values, then placeholders so the
    # number of distinct values matches the profile
    values = []
    for item in top:
        values.extend([str(item["value"])] * max(1, round(item["count"] * factor)))
    named = len({str(i["value"]) for i in top})
    extra = max(0, unique - named)
    remaining = max(0, size - len(values))
    for i in range(extra):
        values.append(f"v{i}")
    if extra and remaining > extra:
        values.extend(f"v{i % extra}" for i in range(remaining - extra))
    return values or ["v0"]


def analyze_profile(profile):
    """Return one report row per column, in the analyze_semantics.py layout."""
    profile = load_profile(profile)
    name = dataset_name(profile)
    row_count = int(profile["dataset"]["row_count"])
    rows = []
    for column in profile["columns"]:
        non_null = row_count - int(column["missing_count"])
        values = _stand_in_values(column, non_null)
        detection = detect_semantic_type(str(column["name"]), values)
        semantic_type = detection["semantic_type"]
        confidence = detection["confidence"]
        evidence = detection["evidence"]
        alternatives = list(detection["alternatives"])

        if (
            column["likely_identifier"]
            and semantic_type not in {"identifier", "email", "phone"}
        ):
            alternatives.insert(0, semantic_type)
            semantic_type = "identifier"
            confidence = max(confidence, 0.85)
            evidence = "Profiling flagged this column as a likely identifier."
        elif (
            column["inferred_type"] == "text"
            and semantic_type in {"categorical", "unknown"}
        ):
            alternatives.insert(0, semantic_type)
            semantic_type = "text"
            confidence = max(confidence, 0.80)
            evidence = "Profiling classed the values as free text."

        rows.append({
            "dataset": name,
            "column": str(column["name"]),
            "data_type": str(column["dtype"]),
            "row_count": row_count,
            "non_null_count": non_null,
            "missing_pct": round(float(column["missing_pct"]), 1),
            "unique_values": int(column["unique_count"]),
            "semantic_type": semantic_type,
            "confidence": confidence,
            "evidence": evidence,
            "alternatives": "; ".join(dict.fromkeys(alternatives)),
            "sensitive": detection["sensitive"],
            "status": detection["status"],
        })
    return rows


def compare_with_data_report(profile_rows, data_report):
    """List columns where the profile-based type differs from the data-based
    report, so the approximation can be checked."""
    data = pd.read_csv(data_report) if isinstance(
        data_report, (str, Path)) else data_report
    merged = pd.DataFrame(profile_rows).merge(
        data[["dataset", "column", "semantic_type", "unique_values",
              "missing_pct"]],
        on=["dataset", "column"], suffixes=("_profile", "_data"),
    )
    different = merged[
        (merged["semantic_type_profile"] != merged["semantic_type_data"])
        | (merged["unique_values_profile"] != merged["unique_values_data"])
        | ((merged["missing_pct_profile"] - merged["missing_pct_data"]).abs()
           > 0.1)
    ]
    return merged, different


def main():
    parser = argparse.ArgumentParser(
        description="Semantic detection from profiling output.")
    parser.add_argument("--profiles", required=True,
                        help="Folder with *.profile.json files")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--compare",
                        help="Data-based semantic report CSV to compare with")
    args = parser.parse_args()

    files = sorted(Path(args.profiles).glob("*.profile.json"))
    if not files:
        print(f"No *.profile.json files found in {args.profiles}")
        return

    rows = []
    print("\n===== SEMANTIC ANALYSIS FROM PROFILES =====")
    for path in files:
        try:
            result = analyze_profile(path)
        except (ValueError, OSError, json.JSONDecodeError) as error:
            print(f"Skipped {path.name}: {error}")
            continue
        print(f"\n{result[0]['dataset']}  (columns: {len(result)})")
        for row in result:
            flag = "  [sensitive]" if row["sensitive"] else ""
            print(f"  {row['column']} -> {row['semantic_type']} "
                  f"({row['confidence']:.0%}){flag}")
        rows.extend(result)
    if not rows:
        print("No usable profiles.")
        return

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    print(f"\nColumns analyzed: {len(rows)}")
    print(f"Report saved to: {output}")

    if args.compare:
        merged, different = compare_with_data_report(rows, args.compare)
        print("\n===== COMPARISON WITH REPORT FROM REAL DATA =====")
        print(f"Columns compared: {len(merged)}")
        if different.empty:
            print("All semantic types, unique counts and missing % match.")
        else:
            print(different[[
                "dataset", "column", "semantic_type_profile",
                "semantic_type_data", "unique_values_profile",
                "unique_values_data",
            ]].to_string(index=False))
    print("\nStatus: Proposed, pending verification")


if __name__ == "__main__":
    main()
