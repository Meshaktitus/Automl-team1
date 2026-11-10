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

## Not in this version

Distributions, outliers, correlations and class distributions (planned Day 4; class distribution needs a selected target). Only CSV and XLSX, first sheet by default. No semantic types (Samarth) and no quality findings (Vinitha).

## Open questions for Team 2 / Meshak

- Will the backend send a file, an object-storage location, or a dataset reference? Until confirmed, only `file` is accepted. Passing an already-loaded table to `run_profiling` also works.
- Who validates that `location` is a path the module may read? The prototype reads any path it is given.
