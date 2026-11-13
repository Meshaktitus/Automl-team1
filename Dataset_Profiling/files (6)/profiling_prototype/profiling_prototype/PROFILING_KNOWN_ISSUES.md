# Dataset Profiling: Status, Known Issues and Pending Changes

Owner: Sanjay. Contract: `v1.0-draft` (not final). Date: 29 October 2026.

Status labels: **Implemented and tested** | **Proposed (not implemented)** | **Pending decision or confirmation**.

## 1. Implemented and tested

| Capability | Evidence |
|---|---|
| Request and response JSON schemas (`schemas/`) | `unit_test_report.txt`, `evidence_report.txt` section 2 |
| `run_profiling(request, dataframe=None)` returning `success`, `warning` or `failed`; it never raises | `integration_results.txt` |
| Dataset summary: row count, column count, column names, duplicate rows | `hr_validation_report.txt` |
| Per column: dtype, inferred type, missing count and percent, distinct count, identifier flag, warnings | `hr_validation_report.txt` |
| Statistics: min, max, mean, median, std, Q1, Q3, skewness; histograms; top values; correlations | unit tests |
| Class distribution for a selected target (at most 20 distinct values) | unit tests, `integration_results.txt` |
| Warnings: `EMPTY_DATASET`, `EMPTY_COLUMN`, `CONSTANT_COLUMN`, `MIXED_TYPES`, `HIGH_CARDINALITY`, `DUPLICATES_APPROXIMATE`, `CLASS_DISTRIBUTION_SKIPPED` | unit tests |
| Structured errors: `INVALID_REQUEST`, `SOURCE_NOT_FOUND`, `UNSUPPORTED_FORMAT`, `DATASET_LOAD_FAILED`, `DUPLICATE_COLUMN_NAMES`, `PROFILING_FAILED`, `TARGET_NOT_FOUND` | `evidence_report.txt` section 4, failed sample responses |
| No sample values, statistics or histogram for identifier columns; source data never modified | unit tests, `hr_validation_report.txt` |

## 2. Proposed (not implemented)

| Item | Note |
|---|---|
| Error `SOURCE_ACCESS_DENIED` (path outside the approved folder or blocked by permissions) | Documented in the contract only; not in the schema |
| Error `FILE_TOO_LARGE` | Same. No size limit is enforced today |
| Enforced approved dataset folder | The prototype reads any path it is given |
| Maximum file size and execution timeout | Values to come from Team 2 |
| Storage references (MinIO/S3) as a source type | Only `source_type: "file"` exists |
| Background jobs with status polling, HTTP route, response envelope, dataset resolver | Owned by Team 2; not part of the profiling module |
| `DATASET_UNAUTHORIZED` | Backend-level error, not produced by profiling |

## 3. Pending decisions and confirmations

- Team 2: Python call or HTTP, dataset-resolution method, file-size and time limits, approved test data, endpoint and contact.
- Formal "No changes needed" replies: Samarth received. Vinitha, Sinchana and Sumanth pending. Team 3 has not confirmed the mapping.
- Meshak decides when the contract moves from `v1.0-draft`.
- Repository location or PR link for the implementation: not available yet.

## 3a. Fixed defects (for the register)

| Defect | Fix | Test |
|---|---|---|
| Sample values of identifier columns appeared in frequency tables | Removed | `test_identifier_columns_do_not_expose_values` |
| Min, max and quartiles of numeric identifier columns were real identifiers | Removed | `test_identifier_columns_expose_no_values_or_statistics` |
| Very large numbers (for example 1e300) overflowed in standard deviation or skewness and produced `Infinity`, which is not valid JSON | Non-finite values are reported as null; histograms are skipped when the range cannot be binned | `test_responses_serialize_as_strict_json` |

## 4. Known issues and limitations

1. The whole table is held in memory. Tables larger than available memory are not supported.
2. Only CSV and XLSX load. JSON and Parquet are not supported (`UNSUPPORTED_FORMAT` for the extension; `INVALID_REQUEST` if `metadata.format` is set to anything else). Excel reads the first sheet unless `sheet_name` is given.
3. A repeated ID column such as a foreign key is not flagged as an identifier (it is not unique), so it gets a histogram that means little.
4. `likely_identifier` can rest on thin evidence, for example `JobCandidate.BusinessEntityID` (2 values present, 84.62% missing).
5. Date detection is a heuristic (strings containing `-` or `/` where at least 90% parse as dates).
6. No outlier counts and no recommended actions in profiling. Those belong to Data Quality; profiling gives quartiles and skewness.
7. `top_values` shows only the most frequent values (default 5) and none for identifier columns.
8. Class distribution is skipped with `CLASS_DISTRIBUTION_SKIPPED` when the target has more than 20 distinct values or is an identifier or text column.
9. Relationships between tables are not part of the contract.
10. There is no delimiter or encoding detection. A CSV read with the wrong delimiter profiles as a single column with status `success`; a wrong encoding gives `DATASET_LOAD_FAILED`. Callers should set `metadata.delimiter` and `metadata.encoding`, or validate the CSV before profiling.
11. Date columns report their minimum and maximum. For a column such as a birth date these are real individual dates. Use `options.include_statistics: false` for sensitive datasets, or treat the output as sensitive.

## 5. Behaviour when optional request fields are omitted

| Omitted | Behaviour |
|---|---|
| `dataset_reference.name` | Response `dataset_reference.name` is `null` (the key is still present). Use `dataset_id` as the key |
| `dataset_reference.location` | Accepted only if the caller passes the loaded table; otherwise `INVALID_REQUEST` on `dataset_reference.location` |
| `metadata` | Format from the file extension, comma delimiter, UTF-8, first Excel sheet, no extra missing markers, no declared identifiers |
| `options` | `top_n_values` 5, `include_statistics` true, `include_correlations` true, no target (so no `class_distribution`) |
| `options.target_column` | No `class_distribution`; the response is otherwise unchanged |

## 6. Proposed contract fields

`SOURCE_ACCESS_DENIED` and `FILE_TOO_LARGE` (error codes, field `dataset_reference.location`). No other new fields are proposed at this time.

<!-- scope-decisions-start -->
## 7. Scope decisions

- One target column per request. Simultaneous multi-target prediction is not part of v1.0; several targets need one request each. A multi-target option would be an additive change in a later version, and only if it is confirmed as in scope.
- Semantic types, quality judgements and preprocessing recommendations are outside profiling.
<!-- scope-decisions-end -->
<!-- team5-review-fixes-start -->
## 8. Fixed after the comparison with another team's profiler

| Defect | Fix | Test |
|---|---|---|
| A CSV column mixing numbers and words (for example 25, 30, unknown, 35) was reported as categorical | Reported as `mixed` with `MIXED_TYPES` | `test_numbers_mixed_with_words_are_reported_as_mixed` |
| Text true/false values with missing cells were reported as categorical | Reported as `boolean` | `test_missing_values_sample_counts_and_percentages` |
| Whitespace-only cells in a file counted as values | Counted as missing; a numeric column stays numeric | `test_whitespace_only_cells_count_as_missing_in_files` |
| Duplicate column names in a file were silently renamed (a, a.1) | Reported as `DUPLICATE_COLUMN_NAMES` | `test_duplicate_header_in_a_file_is_reported_not_renamed` |

Remaining differences: rows with too few fields are read as missing values (structural CSV validation belongs upstream); neither profiler detects the delimiter.
<!-- team5-review-fixes-end -->
