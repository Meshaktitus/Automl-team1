# Dataset Profiling: Input/Output Contract (1.0-draft)

Owner: Sanjay. Status: **implemented and tested as a prototype; proposed, pending Team 1 review.**
The schema is not final until Meshak and the downstream owners have agreed it.

## Files

| File | Purpose |
|---|---|
| `schemas/profiling_request.schema.json` | Request/input schema |
| `schemas/profiling_response.schema.json` | Response/output schema |
| `profiling_service.py` | `run_profiling(request, dataframe=None)`: validates the request, profiles, returns a response that is checked against the response schema before it is sent |
| `profiler.py` | Profiling logic (unchanged role) |
| `samples/` | Real request and response JSONs (success with warnings, file not found, invalid request) |
| `test_profiling_contract.py` | Contract tests |

Run: `python generate_samples.py` regenerates the samples from the real code. `pytest` runs all tests.

## Request

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | string, `"1.0-draft"` | yes | Contract version |
| `request_id` | string | yes | Echoed in the response |
| `dataset_reference.dataset_id` | string | yes | Backend dataset id |
| `dataset_reference.source_type` | `"file"` | yes | Only `file` is implemented (see open questions) |
| `dataset_reference.location` | string | no | File path. Not needed if the backend passes a loaded table |
| `dataset_reference.name` | string | no | Display name |
| `metadata.format` | `csv` / `xlsx` | no | Inferred from the extension if omitted |
| `metadata.sheet_name` | string or integer | no | Default: first sheet |
| `metadata.delimiter`, `metadata.encoding` | string | no | CSV only. Defaults `,` and `utf-8` |
| `metadata.missing_value_markers` | string[] | no | Extra strings read as missing |
| `metadata.identifier_columns` | string[] | no | Declared identifiers. Their values are never reported |
| `options.top_n_values` | integer 1-50 | no | Default 5 |
| `options.include_statistics` | boolean | no | Default true |

Unknown fields are rejected, so typos are caught.

## Response

Top level: `schema_version`, `request_id`, `module`, `status`, `generated_at`, `duration_ms`, `dataset_reference`, `dataset`, `columns`, `warnings`, `errors`. All are always present.

- `status`: `success` (no warnings), `warning` (profile produced, warnings present), `failed` (no profile, see `errors`).
- `dataset`: `row_count`, `column_count`, `column_names`, `duplicate_row_count`. `null` when failed.
- `columns[]` (source order): `name`, `position`, `dtype`, `inferred_type`, `missing_count`, `missing_pct` (0-100), `unique_count`, `likely_identifier`, `warnings` (codes). Optional: `summary`, `top_values[]` (`value`, `count`, `percentage`), `mixed_breakdown`. Optional fields are **absent**, not null, when they do not apply.
- `warnings[]`: `code`, `severity` (`info`/`warning`), `column` (null for table-level), `message`. Codes: `EMPTY_DATASET`, `EMPTY_COLUMN`, `CONSTANT_COLUMN`, `MIXED_TYPES`, `HIGH_CARDINALITY`, `DUPLICATES_APPROXIMATE`.
- `errors[]`: `code`, `message`, `field`. Codes: `INVALID_REQUEST`, `SOURCE_NOT_FOUND`, `UNSUPPORTED_FORMAT`, `DATASET_LOAD_FAILED`, `DUPLICATE_COLUMN_NAMES`, `PROFILING_FAILED`.
- The module never raises: every problem comes back as a `failed` response. File paths are never echoed.

## Changes from the output shared on 23 October (need agreement from the affected owners)

1. `columns` is now an **array** (was an object keyed by column name). Reason: keeps order, easier for TypeScript.
2. Top-level `warnings` are now **objects** (were strings like `"col: constant_column"`). Codes are upper-case.
3. `top_values` is now an **array** with `percentage` (was a value-to-count object).
4. New fields: `schema_version`, `request_id`, `module`, `generated_at`, `duration_ms`, `dataset_reference`, `errors`, `column.position`.
5. Statistics are rounded to 4 decimals.

## Day 4 additions (proposed, all optional and additive; need review)

Nothing above was renamed or removed. Optional fields are absent when they do not apply.

| Addition | Where | Meaning |
|---|---|---|
| `summary.q1`, `summary.q3`, `summary.skewness` | numerical columns | Quartiles and skewness (null if it cannot be computed) |
| `columns[].histogram[]` | numerical columns | up to 10 equal-width bins (fewer when the column has fewer distinct values): `start`, `end`, `count`. Absent for identifier and constant columns |
| `correlations[]` | top level | Pearson `column_a`, `column_b`, `coefficient` (-1 to 1), strongest first. Identifier, constant and text columns excluded. Absent if fewer than two columns qualify |
| `class_distribution` | top level | Only when `options.target_column` is given and the target has at most 20 distinct values: `target_column`, `class_count`, `classes[]` (`value`, `count`, `percentage`), `majority_class`, `minority_class`, `imbalance_ratio` (largest count / smallest, null for one class), `missing_count` |
| `options.target_column`, `options.include_correlations` | request | Select a target; switch correlations off (default on) |
| Warning `CLASS_DISTRIBUTION_SKIPPED` | warnings | Target looks continuous or unsuitable |
| Error `TARGET_NOT_FOUND` | errors | Target column does not exist |

## Not in this version

Outlier flags (Data Quality owns outlier checks). Only CSV and XLSX, first sheet by default. No semantic types (Samarth) and no quality findings (Vinitha).

## Open questions for Team 2 / Meshak

- Will the backend send a file, an object-storage location, or a dataset reference? Until confirmed, only `file` is accepted. Passing an already-loaded table to `run_profiling` also works.
- Who validates that `location` is a path the module may read? The prototype reads any path it is given.

## Known limitations and behaviour (Day 5)

**Unsupported or not implemented:** `.xls`, JSON and Parquet files; more than one Excel sheet per request (first sheet, or `metadata.sheet_name`); storage references (MinIO/S3), uploads and dataset-id lookup (`source_type` accepts only `file`); streaming or chunked reading.

**Memory and speed:** the whole table is loaded into memory, so a table larger than available memory is not supported. Measured on the developer's Windows machine (Python 3.15.1, pandas 3.0.6) with `python benchmark_profiling.py`, a table of 5 columns (id, number, integer, 10-value category, date text), profiling time only: 10,000 rows 0.1 s (1 MB); 100,000 rows 0.7 s (14 MB); 500,000 rows 3.5 s (71 MB); 1,000,000 rows 6.9 s (142 MB). Timings depend on the machine and the data; re-measure on the target machine before relying on them. Correlations are capped at 50 columns and 200 pairs.

**Behaviour worth knowing:**
- Numbers stored as text (for example `"1"`, `"2"`) are reported as `categorical`, not `numerical`.
- Text that is only spaces is a value, not a missing value. Use `metadata.missing_value_markers` for blanks that must count as missing.
- Infinite values are left out of the statistics, the histogram and the correlations. They are not counted separately.
- Cells holding lists or dictionaries are compared by their text form; duplicates are then approximate (`DUPLICATES_APPROXIMATE`).
- Date detection accepts a text column only when at least 90% of its values parse as dates.
- A column mixing numbers and text is `mixed`: it has `mixed_breakdown` and no numeric statistics.
- An empty column is `empty`: 100% missing, no statistics, and excluded from correlations.

## How to call the module (Python)

Files needed together: `profiling_service.py`, `profiler.py`, `schema_validation.py` and the `schemas/` folder (both JSON schemas). Packages: pandas, numpy, openpyxl.

```python
from profiling_service import run_profiling

request = {"schema_version": "1.0-draft", "request_id": "pre-001",
           "dataset_reference": {"dataset_id": "ds-001", "source_type": "file"},
           "options": {"target_column": "plan"}}          # target_column is optional
response = run_profiling(request, dataframe=df)            # df = table already loaded by the caller
# or send dataset_reference.location (CSV/XLSX path) instead of passing dataframe=
```

`run_profiling` never raises. Branch on `response["status"]`:

| status | Meaning | Consumer behaviour (proposed) |
|---|---|---|
| `success` | Profile produced, no warnings | Continue |
| `warning` | Profile produced, warnings present | Continue. Read `warnings[]` (`code`, `severity`, `column`, `message`); they are hints, not blockers |
| `failed` | No profile. `dataset` is null, `columns` is empty | Stop, report `errors[]` (`code`, `message`, `field`) |

## Proposed errors (documented only, not implemented, pending Team 2)

| Code | Meaning | Field |
|---|---|---|
| `SOURCE_ACCESS_DENIED` | Path outside the approved dataset folder, or blocked by permissions | `dataset_reference.location` |
| `FILE_TOO_LARGE` | File exceeds the approved maximum size | `dataset_reference.location` |

`DATASET_UNAUTHORIZED` stays a backend-level error and is not produced by profiling. No size limit, timeout or approved folder is enforced today; the values are to be confirmed with Team 2 before implementation.

## Test data

`samples/demo_customers.csv` is synthetic. The six HumanResources tables came from the backend team; the Employee table holds National ID numbers and birth dates, so profiling never reports sample values for identifier columns, and the source files should not be committed unless approved.

<!-- consumer-rules-start -->
## Scope and consumer rules (clarified in response to review)

1. **Scope.** Profiling reports measured facts: dimensions, detected types (numerical, categorical, datetime, time, text, boolean, mixed, empty), missingness, distinct counts, duplicates, statistics, distributions, correlations, class distribution and warnings. It does **not** provide semantic types (for example email, currency or percentage), quality judgements, recommended actions or recommended preprocessing steps. Those belong to other modules under their own contracts.
2. **One target per request.** `options.target_column` is a single column name. Simultaneous multi-target prediction is not supported in v1.0, and a list is rejected as `INVALID_REQUEST`. To profile several candidate targets, send one request per target: the column profiles are identical and only `class_distribution` differs.
3. **Class distribution and continuous targets.** A categorical, boolean or numerical target with at most 20 distinct values gets `class_distribution`. A target with more than 20 distinct values, or an identifier or text target, gets no class distribution and the info warning `CLASS_DISTRIBUTION_SKIPPED`. For a continuous numerical target, use the target's own `columns[]` entry (missing count and percent, `summary` with min, max, mean, median, standard deviation, Q1, Q3 and skewness, and `histogram`) and `correlations`. Identifier columns carry no statistics by design.
4. **`status: "warning"`.** It is used whenever `warnings[]` is not empty, including informational warnings (`severity: "info"`). It does not mean the profile is unusable. Use each warning's `severity` to decide what to surface.
5. **`status: "failed"`.** No profile was produced: `dataset` is null, `columns` is empty and `errors[]` has at least one item. Consumers should stop processing and report `errors[]`.
6. **Forward compatibility.** Consumers should tolerate warning and error codes they do not recognise, because later versions may add codes.
7. **File loading and text columns.** When profiling reads a CSV or XLSX file itself, blank and whitespace-only text cells count as missing, and duplicate column names are reported as `DUPLICATE_COLUMN_NAMES` instead of being renamed by the reader. When the caller passes a table, the caller's own loader decides what is missing. In every case, a text column that mixes numbers and words is `mixed` (with the warning `MIXED_TYPES`), and text made only of true and false values is `boolean`. Rows with too few fields are read as missing values, so structural CSV validation belongs upstream of profiling.
<!-- consumer-rules-end -->
