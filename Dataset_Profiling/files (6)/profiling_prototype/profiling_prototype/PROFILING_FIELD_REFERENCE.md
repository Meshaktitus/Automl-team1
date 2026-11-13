# Dataset Profiling: Field Reference (contract 1.0-draft)

Generated from `schemas/*.schema.json` by `schema_to_markdown.py` on 2026-11-04. Status: **proposed, pending Team 1 review.**
Every field in this document is **implemented** and covered by tests. The only proposed items are the error codes `SOURCE_ACCESS_DENIED` and `FILE_TOO_LARGE`, which are **not** in the schemas yet.

Conventions: names are snake_case. Optional fields are **absent** from the JSON when they do not apply, not null. `status` is `success` (profile, no warnings), `warning` (profile, warnings present) or `failed` (no profile: `dataset` is null, `columns` is empty, `errors` has at least one item). A non-failed response has `errors: []`.

## Response

| Field | Type | Presence | Description |
|---|---|---|---|
| `schema_version` | string | required | Contract version. Always "1.0-draft" until the contract is finalised. |
| `request_id` | string or null | required | Echo of the request id. Null if the request had none. |
| `module` | string | required | Always "dataset_profiling". |
| `status` | string | required | success = profile produced, no warnings. warning = profile produced, warnings present. failed = no profile produced, see errors. Values: success, warning, failed. |
| `generated_at` | string | required | UTC timestamp, ISO 8601. |
| `duration_ms` | number | required | Time taken by the profiling run, in milliseconds. |
| `dataset_reference` | object or null | required | Echo of the dataset identity. Null when the request was too invalid to read it. The file location is never echoed. |
| `dataset_reference.dataset_id` | string or null | required | Echo of the request's dataset_id. Null if the request was too invalid to read it. |
| `dataset_reference.name` | string or null | required | Echo of the request's name. Null when the request did not send one. |
| `dataset` | null or object | required | Table-level facts. Null when status is failed. |
| `dataset.row_count` | integer | required | Number of rows in the table. |
| `dataset.column_count` | integer | required | Number of columns in the table. |
| `dataset.column_names` | array of string | required | Column names in source order. |
| `dataset.duplicate_row_count` | integer | required | Rows that exactly repeat an earlier row. |
| `columns` | array of object | required | One entry per column, in source order. Empty when status is failed. |
| `columns[].name` | string | required | Column name. |
| `columns[].position` | integer | required | 0-based position in the source table. |
| `columns[].dtype` | string | required | Storage type as read from the source, for example int64 or object. |
| `columns[].inferred_type` | string | required | Detected type: numerical, categorical, datetime, time, text, boolean, mixed or empty. Values: numerical, categorical, datetime, time, text, boolean, mixed, empty. |
| `columns[].missing_count` | integer | required | Number of missing values in the column. |
| `columns[].missing_pct` | number | required | 0 to 100, two decimals. |
| `columns[].unique_count` | integer | required | Distinct non-missing values. |
| `columns[].likely_identifier` | boolean | required | True if declared by the caller or if values are all unique and the name looks like an id. |
| `columns[].warnings` | array of string | required | Warning codes that apply to this column. |
| `columns[].summary` | object | optional (absent when not applicable) | Optional. numerical: min, max, mean, median, std, q1, q3, skewness (never present for identifier columns, whose values are real ids). datetime: min, max (text). text: avg_length, max_length. A value is null when it cannot be computed. |
| `columns[].top_values` | array of object | optional (absent when not applicable) | Optional. Most frequent values of categorical, boolean and time columns, most frequent first. Never present for identifier columns. |
| `columns[].top_values[].value` | string | required | Always text. |
| `columns[].top_values[].count` | integer | required | Number of times the value occurs. |
| `columns[].top_values[].percentage` | number | required | Share of non-missing values, 0 to 100. |
| `columns[].mixed_breakdown` | object | optional (absent when not applicable) | Optional. Only for inferred_type mixed. |
| `columns[].mixed_breakdown.numeric_values` | integer | required | Number of numeric values in the mixed column. |
| `columns[].mixed_breakdown.text_values` | integer | required | Number of text values in the mixed column. |
| `columns[].histogram` | array of object | optional (absent when not applicable) | Optional. Up to 10 equal-width bins of a numerical column (fewer when it has fewer distinct values). Absent for identifier and constant columns, and when statistics are excluded. |
| `columns[].histogram[].start` | number | required | Lower edge of the bin. |
| `columns[].histogram[].end` | number | required | Upper edge of the bin. |
| `columns[].histogram[].count` | integer | required | Number of values in the bin. |
| `warnings` | array of object | required | Warnings about the profile. They do not block use of the profile. |
| `warnings[].code` | string | required | Warning code (see the list below). Values: EMPTY_DATASET, EMPTY_COLUMN, CONSTANT_COLUMN, MIXED_TYPES, HIGH_CARDINALITY, DUPLICATES_APPROXIMATE, CLASS_DISTRIBUTION_SKIPPED. |
| `warnings[].severity` | string | required | info or warning. Values: info, warning. |
| `warnings[].column` | string or null | required | Column name, or null for table-level warnings. |
| `warnings[].message` | string | required | Human-readable explanation. |
| `errors` | array of object | required | Why no profile was produced. Empty unless status is failed. |
| `errors[].code` | string | required | Error code (see the list below). Values: INVALID_REQUEST, SOURCE_NOT_FOUND, UNSUPPORTED_FORMAT, DATASET_LOAD_FAILED, DUPLICATE_COLUMN_NAMES, PROFILING_FAILED, TARGET_NOT_FOUND. |
| `errors[].message` | string | required | Human-readable explanation. Never contains file paths. |
| `errors[].field` | string or null | required | Request field the error refers to, or null. |
| `correlations` | array of object | optional (absent when not applicable) | Optional. Pearson correlation of numerical column pairs, strongest first. Identifier and constant columns are excluded. Absent when fewer than two columns qualify or include_correlations is false. |
| `correlations[].column_a` | string | required | First column of the pair. |
| `correlations[].column_b` | string | required | Second column of the pair. |
| `correlations[].coefficient` | number | required | Pearson correlation coefficient, between -1 and 1. |
| `class_distribution` | object | optional (absent when not applicable) | Optional. Present only when options.target_column is given and the target has at most 20 distinct values. |
| `class_distribution.target_column` | string | required | The selected target column. |
| `class_distribution.class_count` | integer | required | Number of classes found. |
| `class_distribution.classes` | array of object | required | Most frequent first. Values are always text. |
| `class_distribution.classes[].value` | string | required | Class label, as text. |
| `class_distribution.classes[].count` | integer | required | Number of rows with this class. |
| `class_distribution.classes[].percentage` | number | required | Share of non-missing target values, 0 to 100. |
| `class_distribution.majority_class` | string | required | Most frequent class. |
| `class_distribution.minority_class` | string | required | Least frequent class. |
| `class_distribution.imbalance_ratio` | number or null | required | Largest class count divided by smallest. Null when there is one class. |
| `class_distribution.missing_count` | integer | required | Rows where the target is missing. Not counted in the classes. |

### Warning codes (in `warnings[]` and `columns[].warnings`)

| Code | Severity | Meaning |
|---|---|---|
| `EMPTY_DATASET` | warning | The dataset has no rows or no columns. |
| `DUPLICATES_APPROXIMATE` | info | Some cells cannot be compared directly, so duplicates were counted on their text form. |
| `EMPTY_COLUMN` | warning | Column has no values. |
| `CONSTANT_COLUMN` | info | Column contains a single distinct value. |
| `MIXED_TYPES` | warning | Column mixes numeric and text values. |
| `HIGH_CARDINALITY` | info | Almost every value in the column is different. |
| `CLASS_DISTRIBUTION_SKIPPED` | info | The selected target could not be given a class distribution (continuous, identifier or text target). |

### Error codes (in `errors[]`)

| Code | Meaning |
|---|---|
| `INVALID_REQUEST` | The request does not follow the request schema (see field). |
| `SOURCE_NOT_FOUND` | The dataset file was not found. |
| `UNSUPPORTED_FORMAT` | The file extension is not csv or xlsx. |
| `DATASET_LOAD_FAILED` | The file could not be read with the given format and metadata. |
| `DUPLICATE_COLUMN_NAMES` | The table has duplicate column names. |
| `PROFILING_FAILED` | Profiling could not be completed (unexpected problem). |
| `TARGET_NOT_FOUND` | options.target_column is not a column of the table. |

## Request

| Field | Type | Presence | Description |
|---|---|---|---|
| `schema_version` | string | required | Contract version. Must equal 1.0-draft until the contract is approved. |
| `request_id` | string | required | Caller-generated id. Echoed in the response. |
| `dataset_reference` | object | required | Which dataset to profile. |
| `dataset_reference.dataset_id` | string | required | Backend dataset id. |
| `dataset_reference.name` | string | optional (absent when not applicable) | Display name (optional). |
| `dataset_reference.source_type` | string | required | How the data is delivered. Only 'file' is implemented; other types wait for Team 2's decision. Values: file. |
| `dataset_reference.location` | string | optional (absent when not applicable) | File path for source_type 'file'. Optional when the caller passes an already-loaded table to the module. |
| `metadata` | object | optional (absent when not applicable) | Optional hints about the dataset. Never required. |
| `metadata.format` | string | optional (absent when not applicable) | File format. Inferred from the file extension when omitted. Values: csv, xlsx. |
| `metadata.sheet_name` | string or integer | optional (absent when not applicable) | Excel sheet name or 0-based index. Default: first sheet. |
| `metadata.delimiter` | string | optional (absent when not applicable) | CSV delimiter. Default: comma. |
| `metadata.encoding` | string | optional (absent when not applicable) | CSV text encoding. Default: utf-8. |
| `metadata.missing_value_markers` | array of string | optional (absent when not applicable) | Extra strings to treat as missing (for example NA, n/a). |
| `metadata.identifier_columns` | array of string | optional (absent when not applicable) | Columns the caller declares as identifiers. Their sample values are never reported. |
| `options` | object | optional (absent when not applicable) | Optional profiling behaviour. |
| `options.top_n_values` | integer | optional (absent when not applicable) | Number of most frequent values reported for categorical columns. Default 5. |
| `options.include_statistics` | boolean | optional (absent when not applicable) | Include the per-column summary statistics. Default true. |
| `options.target_column` | string | optional (absent when not applicable) | Optional. Column to treat as the target. Adds class_distribution to the response when the target has few distinct values. |
| `options.include_correlations` | boolean | optional (absent when not applicable) | Include correlations between numerical columns. Default true. |
