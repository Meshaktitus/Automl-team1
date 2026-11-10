"""Dataset profiler - Team 1, Sanjay.

profile_dataset(df) -> dict (JSON-serialisable). Never modifies the input.
Status: PROTOTYPE (implemented + tested on synthetic data).
"""
import datetime as _dt
import json
import re
import warnings as _warnings
from pathlib import Path

import numpy as np
import pandas as pd

HIGH_CARDINALITY_RATIO = 0.9   # unique / non-null values
HIGH_CARDINALITY_MIN_ROWS = 20
HISTOGRAM_BINS = 10
MAX_CLASSES = 20               # a target with more distinct values is treated as continuous
MAX_CORRELATION_COLUMNS = 50
MAX_CORRELATION_PAIRS = 200
TEXT_AVG_LENGTH = 50           # longer average strings are free text, not categories
ID_NAME_PATTERN = re.compile(r"(id|guid|number)$", re.IGNORECASE)


def _is_number(v):
    return isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, (bool, np.bool_))


def _infer_type(s: pd.Series) -> str:
    non_null = s.dropna()
    if len(non_null) == 0:
        return "empty"
    if pd.api.types.is_bool_dtype(s):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime"
    if pd.api.types.is_numeric_dtype(s):
        return "numerical"
    # object column: look at the actual values
    n_num = sum(_is_number(v) for v in non_null)
    if n_num == len(non_null):
        return "numerical"
    if 0 < n_num < len(non_null):
        return "mixed"
    if all(isinstance(v, _dt.time) for v in non_null):
        return "time"
    as_str = non_null.astype(str)
    if as_str.str.len().mean() > TEXT_AVG_LENGTH:
        return "text"
    # all strings: do they look like dates?
    if as_str.str.contains(r"[-/]", regex=True).all():
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            parsed = pd.to_datetime(as_str, errors="coerce")
        if parsed.notna().mean() >= 0.9:
            return "datetime"
    return "categorical"


def _num(x):
    """Rounded float, or None when the value is missing or not finite (NaN and Infinity are not valid JSON)."""
    return None if pd.isna(x) or not np.isfinite(x) else round(float(x), 4)


def _safe_nunique(values: pd.Series) -> int:
    """Distinct count that also works for unhashable cells (lists, dicts) by comparing their text form."""
    try:
        return int(values.nunique())
    except TypeError:
        return int(values.astype(str).nunique())


def _profile_column(s: pd.Series, n_rows: int, top_n: int = 5, declared_identifier: bool = False):
    inferred = _infer_type(s)
    non_null = s.dropna()
    n_missing = int(s.isna().sum())
    n_unique = _safe_nunique(non_null)
    col = {
        "dtype": str(s.dtype),
        "inferred_type": inferred,
        "missing_count": n_missing,
        "missing_pct": round(100 * n_missing / n_rows, 2) if n_rows else 0.0,
        "unique_count": n_unique,
    }
    col["likely_identifier"] = bool(declared_identifier or (
        n_unique == len(non_null) and len(non_null) > 1
        and inferred in ("numerical", "categorical", "text")
        and ID_NAME_PATTERN.search(str(s.name) or "") is not None
    ))
    warnings = []

    if inferred == "numerical":
        x = pd.to_numeric(non_null, errors="coerce").replace([np.inf, -np.inf], np.nan)   # statistics use finite values only
        if not col["likely_identifier"]:      # min, max and quartiles of an id column are real ids: never reported (privacy)
            col["summary"] = {
                "min": _num(x.min()), "max": _num(x.max()), "mean": _num(x.mean()),
                "median": _num(x.median()), "std": _num(x.std()),
                "q1": _num(x.quantile(0.25)), "q3": _num(x.quantile(0.75)), "skewness": _num(x.skew()),
            }
        finite_unique = int(x.dropna().nunique())
        if finite_unique > 1 and not col["likely_identifier"]:      # a histogram of ids or of one value says nothing
            try:
                counts, edges = np.histogram(x.dropna().astype(float), bins=min(HISTOGRAM_BINS, finite_unique))
            except (ValueError, OverflowError):      # range too large to bin
                counts, edges = None, None
            if edges is not None and np.isfinite(edges).all():
                col["histogram"] = [{"start": round(float(edges[i]), 4), "end": round(float(edges[i + 1]), 4),
                                     "count": int(counts[i])} for i in range(len(counts))]
    elif inferred in ("categorical", "boolean"):
        if not col["likely_identifier"]:   # never expose sample values of ID columns (privacy)
            top = non_null.astype(str).value_counts().head(top_n)
            col["top_values"] = {k: int(v) for k, v in top.items()}
    elif inferred == "text":
        lengths = non_null.astype(str).str.len()
        col["summary"] = {"avg_length": _num(lengths.mean()), "max_length": int(lengths.max())}
    elif inferred == "time":
        col["top_values"] = {str(k): int(v) for k, v in non_null.astype(str).value_counts().head(top_n).items()}
    elif inferred == "datetime":
        d = pd.to_datetime(non_null, errors="coerce")
        col["summary"] = {"min": str(d.min()), "max": str(d.max())}
    elif inferred == "mixed":
        n_num = sum(_is_number(v) for v in non_null)
        col["mixed_breakdown"] = {"numeric_values": int(n_num), "text_values": int(len(non_null) - n_num)}
        warnings.append("mixed_types")

    if inferred == "empty":
        warnings.append("empty_column")
    elif n_unique == 1:
        warnings.append("constant_column")
    if (inferred == "categorical" and not col["likely_identifier"] and n_rows >= HIGH_CARDINALITY_MIN_ROWS
            and n_unique / max(len(non_null), 1) > HIGH_CARDINALITY_RATIO):
        warnings.append("high_cardinality")

    col["warnings"] = warnings
    return col


def profile_dataset(df: pd.DataFrame, top_n: int = 5, identifier_columns=None) -> dict:
    """Return a structured profile. Does not modify df."""
    report = {"status": "success", "dataset": {}, "columns": {}, "warnings": []}

    if not isinstance(df, pd.DataFrame):
        return {"status": "failed", "error": "input must be a pandas DataFrame",
                "dataset": {}, "columns": {}, "warnings": []}
    if df.shape[1] == 0 or df.shape[0] == 0:
        report["status"] = "warning"
        report["dataset"] = {"row_count": int(df.shape[0]), "column_count": int(df.shape[1]),
                             "column_names": [str(c) for c in df.columns], "duplicate_row_count": 0}
        report["warnings"].append("empty_dataset")
        return report

    n_rows, n_cols = df.shape
    declared = {str(c) for c in (identifier_columns or [])}
    try:
        dup = int(df.duplicated().sum())
    except TypeError:  # unhashable cells (lists/dicts)
        dup = int(df.astype(str).duplicated().sum())
        report["warnings"].append("duplicates_computed_on_string_form")

    report["dataset"] = {
        "row_count": int(n_rows),
        "column_count": int(n_cols),
        "column_names": [str(c) for c in df.columns],
        "duplicate_row_count": dup,
    }
    for name in df.columns:
        with np.errstate(all="ignore"):      # overflow in very large values becomes None, not a console warning
            col = _profile_column(df[name], n_rows, top_n, str(name) in declared)
        report["columns"][str(name)] = col
        for w in col["warnings"]:
            report["warnings"].append(f"{name}: {w}")
    if report["warnings"]:
        report["status"] = "warning"
    return report


def compute_correlations(df: pd.DataFrame, columns: dict) -> list:
    """Pearson correlation for pairs of numerical columns, strongest first.
    Identifier and constant columns are left out. Returns [] when fewer than two columns qualify."""
    lookup = {str(c): c for c in df.columns}
    names = [n for n, c in columns.items()
             if c["inferred_type"] == "numerical" and not c["likely_identifier"] and c["unique_count"] > 1]
    names = names[:MAX_CORRELATION_COLUMNS]
    if len(names) < 2:
        return []
    num = pd.DataFrame({n: pd.to_numeric(df[lookup[n]], errors="coerce") for n in names}).replace([np.inf, -np.inf], np.nan)
    corr = num.corr(method="pearson", min_periods=3)
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            v = corr.loc[a, b]
            if pd.notna(v) and np.isfinite(v):
                pairs.append({"column_a": a, "column_b": b, "coefficient": round(float(v), 4)})
    pairs.sort(key=lambda p: -abs(p["coefficient"]))
    return pairs[:MAX_CORRELATION_PAIRS]


def class_distribution(series: pd.Series, columns: dict):
    """Class distribution of a selected target. Returns (result, None) or (None, reason it was skipped)."""
    info = columns[str(series.name)]
    non_null = series.dropna()
    if info["inferred_type"] not in ("categorical", "boolean", "numerical") or info["likely_identifier"]:
        return None, "The target column type does not suit a class distribution."
    if len(non_null) == 0:
        return None, "The target column has no values."
    if non_null.nunique() > MAX_CLASSES:
        return None, f"The target has more than {MAX_CLASSES} distinct values, so it looks continuous."
    counts = non_null.astype(str).value_counts()
    total = int(counts.sum())
    classes = [{"value": str(v), "count": int(c), "percentage": round(100 * int(c) / total, 2)} for v, c in counts.items()]
    ratio = round(int(counts.iloc[0]) / int(counts.iloc[-1]), 2) if len(counts) >= 2 else None
    return {"target_column": str(series.name), "class_count": len(classes), "classes": classes,
            "majority_class": classes[0]["value"], "minority_class": classes[-1]["value"],
            "imbalance_ratio": ratio, "missing_count": int(series.isna().sum())}, None


def load_tables(folder: str) -> dict:
    """Load every .xlsx / .csv in a folder as its own table (first sheet of each workbook)."""
    tables = {}
    for p in sorted(Path(folder).iterdir()):
        if p.suffix.lower() == ".xlsx":
            tables[p.stem] = pd.read_excel(p)
        elif p.suffix.lower() == ".csv":
            tables[p.stem] = pd.read_csv(p)
    return tables


def find_relationships(tables: dict) -> list:
    """Optional cross-table check: for same-named *ID columns, how well do the values line up?"""
    out = []
    names = list(tables)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for col in set(tables[a].columns) & set(tables[b].columns):
                if not ID_NAME_PATTERN.search(str(col)) or str(col).lower() == "rowguid":
                    continue
                va, vb = tables[a][col].dropna(), tables[b][col].dropna()
                if not (pd.api.types.is_numeric_dtype(va) and pd.api.types.is_numeric_dtype(vb)):
                    continue
                sa, sb = set(va), set(vb)
                out.append({"column": str(col), "table_a": a, "table_b": b,
                            "values_only_in_a": len(sa - sb), "values_only_in_b": len(sb - sa),
                            "shared_values": len(sa & sb)})
    return out


def profile_tables(tables: dict) -> dict:
    """Profile each table separately; relationships are reported on the side, tables are never merged."""
    return {"tables": {n: profile_dataset(df) for n, df in tables.items()},
            "relationships": find_relationships(tables)}


def to_json(report: dict) -> str:
    return json.dumps(report, indent=2, default=str)


if __name__ == "__main__":
    demo = pd.DataFrame({
        "age": [25, 30, None, 41, 30],
        "city": ["Bengaluru", "Pune", "Pune", "Delhi", "Pune"],
        "joined": ["2024-01-05", "2024-02-11", "2024-03-02", None, "2024-02-11"],
        "const": [1, 1, 1, 1, 1],
        "blank": [None] * 5,
    })
    print(to_json(profile_dataset(demo)))
