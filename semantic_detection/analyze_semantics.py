"""Run semantic detection on every .xlsx / .csv file in a folder.

Usage:
    python analyze_semantics.py
    python analyze_semantics.py --data-folder synthetic --output outputs/synthetic_semantic_report.csv
"""
import argparse
from pathlib import Path

import pandas as pd

from semantic_rules import detect_semantic_type

PROJECT_FOLDER = Path(__file__).resolve().parent
DEFAULT_DATA = PROJECT_FOLDER / "data"
DEFAULT_OUTPUT = PROJECT_FOLDER / "outputs" / "semantic_analysis_report.csv"
SAMPLE_SIZE = 5000


def analyze_dataframe(dataset_name, df, sample_size=SAMPLE_SIZE):
    """Return one report row per column of df."""
    rows = []
    row_count = len(df)
    for column in df.columns:
        series = df[column]
        values = series.dropna().head(sample_size).tolist()
        detection = detect_semantic_type(str(column), values)
        non_null = int(series.notna().sum())
        rows.append({
            "dataset": dataset_name,
            "column": str(column),
            "data_type": str(series.dtype),
            "row_count": row_count,
            "non_null_count": non_null,
            "missing_pct": (
                round(100 * (1 - non_null / row_count), 1)
                if row_count else 0.0
            ),
            "unique_values": int(series.nunique()),
            "semantic_type": detection["semantic_type"],
            "confidence": detection["confidence"],
            "evidence": detection["evidence"],
            "alternatives": "; ".join(detection["alternatives"]),
            "sensitive": detection["sensitive"],
            "status": detection["status"],
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description="Semantic column analysis.")
    parser.add_argument("--data-folder", default=str(DEFAULT_DATA))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    data_folder = Path(args.data_folder)
    files = sorted(
        list(data_folder.glob("*.xlsx")) + list(data_folder.glob("*.csv"))
    )
    if not files:
        print(f"No .xlsx or .csv files found in {data_folder}")
        return

    results = []
    print("\n===== SEMANTIC ANALYSIS =====")
    for file_path in files:
        try:
            if file_path.suffix.lower() == ".csv":
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
        except Exception as error:
            print(f"Could not read {file_path.name}: {error}")
            continue

        print(f"\nAnalyzing: {file_path.name}  "
              f"(rows: {len(df)}, columns: {len(df.columns)})")
        rows = analyze_dataframe(file_path.name, df)
        for row in rows:
            flag = "  [sensitive]" if row["sensitive"] else ""
            print(f"  {row['column']} -> {row['semantic_type']} "
                  f"({row['confidence']:.0%}){flag}")
        results.extend(rows)

    if not results:
        print("No results generated.")
        return

    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_csv(output_file, index=False)
    print(f"\nColumns analyzed: {len(results)}")
    print(f"Report saved to: {output_file}")


if __name__ == "__main__":
    main()
