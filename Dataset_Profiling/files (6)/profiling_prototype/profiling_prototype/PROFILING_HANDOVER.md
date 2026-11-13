# Dataset Profiling: Module Handover

Owner: Sanjay G K. Status: **prototype, implemented and tested within the scope below.** Contract version `1.0-draft` until the review replies are complete.

## Purpose
Reads a table and reports measured facts about it: dimensions, column types, missing values, distinct counts, duplicates, summary statistics, distributions, correlations, an optional class distribution for a selected target, and warnings. It never modifies the data and never raises; every problem comes back as a structured response.

## How to run
```
pip install -r requirements.txt
pytest                              # all tests
python run_all.py data              # tests, HR tables and a contract sample (needs the HR files in data/, not in the repository)
python evidence.py data             # evidence_report.txt
python regression_report.py         # regression and performance report
```
Call it from Python: `run_profiling(request, dataframe=df)` (see `README.md` and `PROFILING_CONTRACT.md`).

## Acceptance criteria 4.1 and evidence
| Criterion | Evidence |
|---|---|
| Correct row and column counts | `hr_validation_report.txt`, `profiling_baseline_report.txt` |
| Column names and inferred data types | `profiling_baseline_report.txt`, `demonstration_report.txt` |
| Missing-value counts and percentages | `hr_validation_report.txt`, `test_profiling_manual_checks.py`, `test_profiling_regression.py` (null-heavy) |
| Unique-value counts | `hr_validation_report.txt` |
| Duplicate-row counts | `hr_validation_report.txt`, `test_profiling_regression.py` (duplicate-heavy) |
| Numerical descriptive statistics | `profiling_baseline_report.txt` (independent recomputation), `test_profiling_regression.py` |
| Categorical frequency summaries | `profiling_baseline_report.txt`, `test_profiling_regression.py` |
| Controlled handling of empty and unsupported inputs | `test_profiling_regression.py` (unsupported input), `integration_results.txt` |
| Consistent structured output | JSON Schemas, `test_profiling_integration_regression.py`, `evidence_report.txt` |

Test counts are in `unit_test_report.txt` (generate with `python make_test_report.py`).

## Interfaces and dependencies
- Request and response contract: `schemas/profiling_request.schema.json`, `schemas/profiling_response.schema.json`; field reference in `PROFILING_FIELD_REFERENCE.md`.
- Profiling service integration with Team 2 (Induraj): interface sent; the adapter sample and the final calling approach are pending.
- Dataset input and metadata: the common dataset reference is `dataset_reference` plus optional `metadata`; confirmation with the dataset-input owners is pending.
- Scope boundary: no semantic types, quality judgements or preprocessing recommendations (other modules).

## Known limitations
See `PROFILING_KNOWN_ISSUES.md`. In short: the whole table is held in memory; CSV and XLSX only; no delimiter or encoding detection; numbers stored as text are treated as text; no enforced path boundary, file-size limit or timeout; one target per request; repeated key columns are not flagged as identifiers; date columns report real minimum and maximum dates.

## Next sprint backlog (owner: Sanjay)
| Item | Acceptance criteria |
|---|---|
| Finalize contract v1.0 | All reviewer replies recorded; version changed everywhere; samples, types and field reference regenerated; all tests pass |
| Path boundary, file-size limit and timeout (after Team 2 decisions) | New error codes in schema; limits configurable; tests for allowed, blocked and oversized files |
| JSON, Parquet and multi-sheet Excel input | Loader tests with sample files; unsupported formats still return controlled errors |
| Larger-than-memory tables | Documented approach; test on a table above the memory limit; exact versus approximate noted |
| Outlier indicators (if confirmed in scope) | IQR fences and counts in the schema; hand-calculated tests |
| Delimiter and encoding detection | Wrong-delimiter file profiles correctly or returns a clear warning |
| Multi-target profiling (only if confirmed in scope) | Additive schema option; tests; consumers confirm the shape |
| Commit tests, README and samples to the repository | Pull request merged, link recorded |
