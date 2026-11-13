"""Generates PROFILING_FIELD_REFERENCE.md (field names, types, required/optional, descriptions) from the two JSON Schemas.
Usage:  python schema_to_markdown.py
Every field comes from the schema files, so the reference cannot drift from the contract.
"""
import json
from datetime import date
from pathlib import Path

from profiling_service import _COLUMN_WARNINGS, _TABLE_WARNINGS

HERE = Path(__file__).parent

GLOSSARY = {  # descriptions for fields whose schema entry has none
    "schema_version": 'Contract version. Always "1.0-draft" until the contract is finalised.',
    "module": 'Always "dataset_profiling".',
    "duration_ms": "Time taken by the profiling run, in milliseconds.",
    "dataset_reference.dataset_id": "Echo of the request's dataset_id. Null if the request was too invalid to read it.",
    "dataset_reference.name": "Echo of the request's name. Null when the request did not send one.",
    "dataset.row_count": "Number of rows in the table.",
    "dataset.column_count": "Number of columns in the table.",
    "dataset.column_names": "Column names in source order.",
    "columns[].name": "Column name.",
    "columns[].inferred_type": "Detected type: numerical, categorical, datetime, time, text, boolean, mixed or empty.",
    "columns[].missing_count": "Number of missing values in the column.",
    "columns[].top_values[].count": "Number of times the value occurs.",
    "columns[].mixed_breakdown.numeric_values": "Number of numeric values in the mixed column.",
    "columns[].mixed_breakdown.text_values": "Number of text values in the mixed column.",
    "columns[].histogram[].start": "Lower edge of the bin.",
    "columns[].histogram[].end": "Upper edge of the bin.",
    "columns[].histogram[].count": "Number of values in the bin.",
    "warnings": "Warnings about the profile. They do not block use of the profile.",
    "warnings[].code": "Warning code (see the list below).",
    "warnings[].severity": "info or warning.",
    "warnings[].message": "Human-readable explanation.",
    "errors": "Why no profile was produced. Empty unless status is failed.",
    "errors[].code": "Error code (see the list below).",
    "errors[].message": "Human-readable explanation. Never contains file paths.",
    "correlations[].column_a": "First column of the pair.",
    "correlations[].column_b": "Second column of the pair.",
    "correlations[].coefficient": "Pearson correlation coefficient, between -1 and 1.",
    "class_distribution.target_column": "The selected target column.",
    "class_distribution.class_count": "Number of classes found.",
    "class_distribution.classes[].value": "Class label, as text.",
    "class_distribution.classes[].count": "Number of rows with this class.",
    "class_distribution.classes[].percentage": "Share of non-missing target values, 0 to 100.",
    "class_distribution.majority_class": "Most frequent class.",
    "class_distribution.minority_class": "Least frequent class.",
}
ERROR_MEANING = {
    "INVALID_REQUEST": "The request does not follow the request schema (see field).",
    "SOURCE_NOT_FOUND": "The dataset file was not found.",
    "UNSUPPORTED_FORMAT": "The file extension is not csv or xlsx.",
    "DATASET_LOAD_FAILED": "The file could not be read with the given format and metadata.",
    "DUPLICATE_COLUMN_NAMES": "The table has duplicate column names.",
    "PROFILING_FAILED": "Profiling could not be completed (unexpected problem).",
    "TARGET_NOT_FOUND": "options.target_column is not a column of the table.",
}


def resolve(schema, defs):
    if "$ref" in schema:
        return {**defs[schema["$ref"].split("/")[-1]], **{k: v for k, v in schema.items() if k != "$ref"}}
    return schema


def type_text(s, defs):
    s = resolve(s, defs)
    if "oneOf" in s:
        return " or ".join(type_text(x, defs) for x in s["oneOf"])
    t = s.get("type")
    if isinstance(t, list):
        return " or ".join(t)
    if t == "array":
        return "array of " + type_text(s.get("items", {}), defs)
    return t or "object"


def walk(schema, defs, path, rows):
    schema = resolve(schema, defs)
    if "oneOf" in schema:
        for s in schema["oneOf"]:
            if s.get("type") != "null":
                walk(s, defs, path, rows)
        return
    if schema.get("type") == "array":
        items = resolve(schema.get("items", {}), defs)
        if items.get("type") == "object":
            walk(items, defs, path + "[]", rows)
        return
    required = set(schema.get("required", []))
    for name, sub in (schema.get("properties") or {}).items():
        full = f"{path}.{name}" if path else name
        s = resolve(sub, defs)
        desc = s.get("description") or GLOSSARY.get(full, "")
        if s.get("enum"):
            desc = (desc + " " if desc else "") + "Values: " + ", ".join(map(str, s["enum"])) + "."
        rows.append((full, type_text(sub, defs), "required" if name in required else "optional (absent when not applicable)", desc))
        walk(sub, defs, full, rows)


def table(rows):
    lines = ["| Field | Type | Presence | Description |", "|---|---|---|---|"]
    lines += [f"| `{f}` | {t} | {p} | {d.replace('|', '/')} |" for f, t, p, d in rows]
    return "\n".join(lines)


sections = []
for title, fname in (("Request", "profiling_request"), ("Response", "profiling_response")):
    schema = json.loads((HERE / "schemas" / f"{fname}.schema.json").read_text(encoding="utf-8"))
    rows = []
    walk(schema, schema.get("$defs", {}), "", rows)
    missing = [r[0] for r in rows if not r[3]]
    assert not missing, f"fields without a description: {missing}"
    sections.append((title, rows))

warn_rows = [(c, s, m) for c, s, m in list(_TABLE_WARNINGS.values()) + list(_COLUMN_WARNINGS.values())]
warn_rows.append(("CLASS_DISTRIBUTION_SKIPPED", "info", "The selected target could not be given a class distribution (continuous, identifier or text target)."))
text = f"""# Dataset Profiling: Field Reference (contract 1.0-draft)

Generated from `schemas/*.schema.json` by `schema_to_markdown.py` on {date.today().isoformat()}. Status: **proposed, pending Team 1 review.**
Every field in this document is **implemented** and covered by tests. The only proposed items are the error codes `SOURCE_ACCESS_DENIED` and `FILE_TOO_LARGE`, which are **not** in the schemas yet.

Conventions: names are snake_case. Optional fields are **absent** from the JSON when they do not apply, not null. `status` is `success` (profile, no warnings), `warning` (profile, warnings present) or `failed` (no profile: `dataset` is null, `columns` is empty, `errors` has at least one item). A non-failed response has `errors: []`.

## Response

{table(sections[1][1])}

### Warning codes (in `warnings[]` and `columns[].warnings`)

| Code | Severity | Meaning |
|---|---|---|
""" + "\n".join(f"| `{c}` | {s} | {m} |" for c, s, m in warn_rows) + f"""

### Error codes (in `errors[]`)

| Code | Meaning |
|---|---|
""" + "\n".join(f"| `{c}` | {m} |" for c, m in ERROR_MEANING.items()) + f"""

## Request

{table(sections[0][1])}
"""
(HERE / "PROFILING_FIELD_REFERENCE.md").write_text(text, encoding="utf-8")
print(f"Written: PROFILING_FIELD_REFERENCE.md ({len(sections[1][1])} response fields, {len(sections[0][1])} request fields)")
