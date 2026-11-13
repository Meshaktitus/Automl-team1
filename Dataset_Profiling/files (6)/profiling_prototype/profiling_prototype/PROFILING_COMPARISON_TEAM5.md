# Dataset Profiling (Team 1) compared with Team 5's profiler

Method: Team 5's repository (`team5-data-engineering`) was read and run. Their 9 profiler unit tests pass. Both profilers were run on their four profiling sample files and on seven edge cases (`python compare_with_team5.py "<path>"` reproduces this and writes `team5_comparison_report.txt`).

## Where they agree
On their four sample files (16 columns) the missing counts, missing percentages and distinct counts agree on all 16, as do row and column counts, numeric and date minimum and maximum, and boolean, date and mixed detection. Their `null_pct` is a fraction (0 to 1); ours is a percentage (0 to 100).

## What each provides
| | Team 5 `profile_csv` | Dataset Profiling module |
|---|---|---|
| Counts, missing, distinct, min and max | Yes | Yes |
| Mean, median, standard deviation, quartiles, skewness | No | Yes |
| Histograms, frequency tables, correlations, class distribution | No | Yes |
| Duplicate rows | In their validator | Yes |
| Warnings and errors | Raises exceptions | Structured codes and severities |
| Input | CSV (standard library) | CSV, XLSX, or a loaded table (pandas) |
| Output contract | Provisional, no schema | JSON Schemas, samples, field reference, TypeScript types |
| Per-cell validation against expected types, row numbers, malformed-row detection, size limit | Yes (validator) | No |
| API route and dataset metadata lookup | Yes | No (Team 2 owns the API) |

## Important points
- Their `/api/v1/datasets/profile` route runs their **validator**, not `profile_csv`; their own document says the profiler is not yet part of the API response. The route name could be mistaken for profiling statistics.
- Their profiler output uses different field names (`data_type`, `null_count`, `null_pct`, `distinct_count`, `min`, `max`).

## Gaps found in our module and fixed
Numbers mixed with words in a CSV column, true/false text with missing cells, whitespace-only cells and duplicate headers in files were handled less well than in their profiler. All four are fixed and tested (`test_profiling_team5_alignment.py`).

## Remaining differences
Rows with too few fields are read as missing values by our module and rejected by theirs; neither detects a delimiter.

## Proposed division
- **Team 5:** ingestion checks: CSV structure, headers, expected types, size limit, dataset metadata.
- **Team 1:** profiling statistics for a table that has passed those checks, through `run_profiling(request, dataframe=df)`.
- **One source of profiling facts:** their `profile_csv` should call our module (or be retired) rather than maintain a second set of statistics, and the route naming should be agreed with Team 2.
