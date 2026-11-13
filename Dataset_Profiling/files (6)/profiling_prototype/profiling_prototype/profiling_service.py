"""Dataset Profiling module - contract layer (Team 1, Sanjay).

run_profiling(request, dataframe=None) -> response dict that follows
schemas/profiling_response.schema.json. It never raises: every problem becomes a response with
status "failed" and a structured error. The source data is never modified.

Status: PROTOTYPE. Contract version 1.0-draft (proposed, pending Team 1 review).
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from profiler import class_distribution, compute_correlations, profile_dataset
from schema_validation import validate

SCHEMA_VERSION = "1.0-draft"
MODULE = "dataset_profiling"
_SCHEMA_DIR = Path(__file__).parent / "schemas"
REQUEST_SCHEMA = json.loads((_SCHEMA_DIR / "profiling_request.schema.json").read_text(encoding="utf-8"))
RESPONSE_SCHEMA = json.loads((_SCHEMA_DIR / "profiling_response.schema.json").read_text(encoding="utf-8"))

# internal profiler warning -> (contract code, severity, message)
_TABLE_WARNINGS = {
    "empty_dataset": ("EMPTY_DATASET", "warning", "The dataset has no rows or no columns."),
    "duplicates_computed_on_string_form": (
        "DUPLICATES_APPROXIMATE", "info", "Some cells cannot be compared directly, so duplicates were counted on their text form."),
}
_COLUMN_WARNINGS = {
    "empty_column": ("EMPTY_COLUMN", "warning", "Column has no values."),
    "constant_column": ("CONSTANT_COLUMN", "info", "Column contains a single distinct value."),
    "mixed_types": ("MIXED_TYPES", "warning", "Column mixes numeric and text values."),
    "high_cardinality": ("HIGH_CARDINALITY", "info", "Almost every value in the column is different."),
}


class _Failure(Exception):
    def __init__(self, code, message, field=None):
        super().__init__(message)
        self.code, self.message, self.field = code, message, field


def _error(code, message, field=None):
    return {"code": code, "message": message, "field": field}


def _response(request_id, status, started, reference=None, dataset=None, columns=None, warnings=None, errors=None,
              extras=None):
    body = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "module": MODULE,
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        "dataset_reference": reference,
        "dataset": dataset,
        "columns": columns or [],
        "warnings": warnings or [],
        "errors": errors or [],
    }
    body.update(extras or {})        # optional sections (correlations, class_distribution) appear only when computed
    return body


def _failed(request, started, errors):
    rid = request.get("request_id") if isinstance(request, dict) else None
    ref = request.get("dataset_reference") if isinstance(request, dict) else None
    reference = None
    if isinstance(ref, dict):
        reference = {"dataset_id": ref.get("dataset_id") if isinstance(ref.get("dataset_id"), str) else None,
                     "name": ref.get("name") if isinstance(ref.get("name"), str) else None}
    return _response(rid if isinstance(rid, str) else None, "failed", started, reference=reference, errors=errors)


def _check_header(path, fmt, metadata):
    """Duplicate column names in a file are reported, not silently renamed by the reader (a.1, a.2 ...)."""
    try:
        if fmt == "csv":
            raw = pd.read_csv(path, header=None, nrows=1, dtype=str, sep=metadata.get("delimiter", ","),
                              encoding=metadata.get("encoding", "utf-8"))
        else:
            raw = pd.read_excel(path, header=None, nrows=1, dtype=str, sheet_name=metadata.get("sheet_name", 0))
    except Exception:
        return                                   # the real read reports whatever is wrong with the file
    names = [str(v).strip() for v in raw.iloc[0].tolist() if pd.notna(v)] if len(raw) else []
    if len(names) != len(set(names)):
        raise _Failure("DUPLICATE_COLUMN_NAMES", "The file has duplicate column names.", None)


def _blank_to_missing(df):
    """Blank and whitespace-only text cells count as missing when profiling reads a file itself. When the caller passes a
    table, the caller's own loader decides."""
    for name in df.columns:
        s = df[name]
        if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_datetime64_any_dtype(s) or pd.api.types.is_bool_dtype(s):
            continue
        blank = s.map(lambda v: isinstance(v, str) and v.strip() == "")
        if blank.any():
            s = s.mask(blank)
            try:
                s = pd.to_numeric(s)             # a numeric column that only looked like text because of its blank cells
            except (ValueError, TypeError):
                pass
            df[name] = s
    return df


def _load(reference, metadata):
    location = reference.get("location")
    if not location:
        raise _Failure("INVALID_REQUEST", "dataset_reference.location is required when no table is supplied.",
                       "dataset_reference.location")
    path = Path(location)
    if not path.is_file():
        raise _Failure("SOURCE_NOT_FOUND", "The dataset file was not found.", "dataset_reference.location")
    fmt = metadata.get("format") or path.suffix.lower().lstrip(".")
    markers = metadata.get("missing_value_markers") or None
    if fmt in ("csv", "xlsx"):
        _check_header(path, fmt, metadata)
    try:
        if fmt == "csv":
            return _blank_to_missing(pd.read_csv(path, sep=metadata.get("delimiter", ","),
                                                 encoding=metadata.get("encoding", "utf-8"), na_values=markers))
        if fmt == "xlsx":
            return _blank_to_missing(pd.read_excel(path, sheet_name=metadata.get("sheet_name", 0), na_values=markers))
    except Exception:
        raise _Failure("DATASET_LOAD_FAILED", "The file could not be read with the given format and metadata.", None)
    raise _Failure("UNSUPPORTED_FORMAT", f"Format '{fmt}' is not supported. Supported: csv, xlsx.", "metadata.format")


def _convert_column(position, name, col, include_statistics):
    out = {
        "name": name, "position": position, "dtype": col["dtype"], "inferred_type": col["inferred_type"],
        "missing_count": col["missing_count"], "missing_pct": col["missing_pct"], "unique_count": col["unique_count"],
        "likely_identifier": col["likely_identifier"],
        "warnings": [_COLUMN_WARNINGS[w][0] for w in col["warnings"]],
    }
    if include_statistics and "summary" in col:
        out["summary"] = col["summary"]
    if include_statistics and "histogram" in col:
        out["histogram"] = col["histogram"]
    if "mixed_breakdown" in col:
        out["mixed_breakdown"] = col["mixed_breakdown"]
    return out


def _build_profile(df, options, metadata):
    internal = profile_dataset(df, top_n=options.get("top_n_values", 5),
                               identifier_columns=metadata.get("identifier_columns"))
    if internal["status"] == "failed":
        raise _Failure("PROFILING_FAILED", "Profiling could not be completed.", None)
    include_stats = options.get("include_statistics", True)
    row_count = internal["dataset"]["row_count"]
    columns, warnings = [], []
    for position, (name, col) in enumerate(internal["columns"].items()):
        item = _convert_column(position, name, col, include_stats)
        if "top_values" in col:
            non_null = row_count - col["missing_count"]
            item["top_values"] = [
                {"value": v, "count": c, "percentage": round(100 * c / non_null, 2) if non_null else 0.0}
                for v, c in col["top_values"].items()]
        columns.append(item)
        for w in col["warnings"]:
            code, severity, message = _COLUMN_WARNINGS[w]
            warnings.append({"code": code, "severity": severity, "column": name, "message": message})
    for w in internal["warnings"]:
        if w in _TABLE_WARNINGS:
            code, severity, message = _TABLE_WARNINGS[w]
            warnings.append({"code": code, "severity": severity, "column": None, "message": message})

    extras = {}
    if options.get("include_correlations", True):
        pairs = compute_correlations(df, internal["columns"])
        if pairs:
            extras["correlations"] = pairs
    target = options.get("target_column")
    if target is not None:
        if target not in internal["columns"]:
            raise _Failure("TARGET_NOT_FOUND", "The target column was not found in the dataset.", "options.target_column")
        original = next(c for c in df.columns if str(c) == target)
        result, reason = class_distribution(df[original].rename(target), internal["columns"])
        if result:
            extras["class_distribution"] = result
        else:
            warnings.append({"code": "CLASS_DISTRIBUTION_SKIPPED", "severity": "info", "column": target, "message": reason})
    return internal["dataset"], columns, warnings, extras


def run_profiling(request, dataframe=None):
    """Profile the dataset described by `request`. Pass `dataframe` if the backend has already loaded it."""
    started = time.perf_counter()
    try:
        problems = validate(request, REQUEST_SCHEMA)
        if problems:
            return _failed(request, started, [_error("INVALID_REQUEST", msg, path or None) for path, msg in problems])
        reference = request["dataset_reference"]
        metadata = request.get("metadata", {})
        options = request.get("options", {})

        df = dataframe if dataframe is not None else _load(reference, metadata)
        if not isinstance(df, pd.DataFrame):
            raise _Failure("INVALID_REQUEST", "The supplied table is not a DataFrame.", None)
        if df.columns.duplicated().any():
            raise _Failure("DUPLICATE_COLUMN_NAMES", "The table has duplicate column names.", None)

        dataset, columns, warnings, extras = _build_profile(df, options, metadata)
        status = "warning" if warnings else "success"
        echo = {"dataset_id": reference["dataset_id"], "name": reference.get("name")}
        response = _response(request["request_id"], status, started, echo, dataset, columns, warnings, extras=extras)
    except _Failure as f:
        return _failed(request, started, [_error(f.code, f.message, f.field)])
    except Exception:  # never let an unexpected problem escape as a traceback
        return _failed(request, started, [_error("PROFILING_FAILED", "Profiling could not be completed.", None)])

    # last line of defence: the module must never emit a response that breaks its own contract
    if validate(response, RESPONSE_SCHEMA):
        return _failed(request, started, [_error("PROFILING_FAILED", "Profiling could not be completed.", None)])
    return response


if __name__ == "__main__":
    import sys
    req = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(json.dumps(run_profiling(req), indent=2))
