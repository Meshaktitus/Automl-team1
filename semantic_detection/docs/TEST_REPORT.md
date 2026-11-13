# Test report and unresolved-case list: Semantic Understanding, Target Detection and Problem Classification

Owner: Samarth (Team 1). Report date: Wednesday 28 October 2026 (plan item: Integrated detection); updated Friday 6 November 2026 (review points: 377 tests).
Status labels: **Implemented**, **Prototype**, **Design only**, **Blocked**, **Ready for review**.

## 1. Result in one paragraph

377 automatic test cases, all passing (281 on 30 Oct; 65 added in Week 3: integration, input validation, Thursday regression; 31 added on 6 Nov: review decisions, training approval, sensitive columns, real-input tests, `Warning / Audit` severity). Only 8 of them use Sanjay's real profile and Vinitha's real quality reports; see section 2b. The integrated entry point (`run_detection.py`) reads Sanjay's profiling output and Vinitha's quality report and gives, per dataset, the target, the problem type, the evidence and the feature columns. Today I tested missing, ambiguous and poorly populated targets and columns (19 new cases plus 2 for the profiling class distribution). The tests found 4 real gaps and 1 crash, and a review of failure handling found 3 more weak spots (one bad profile stopped the whole run; duplicate dataset names were merged silently; quality findings for unknown columns were ignored silently); all are fixed. Nine cases remain open; they are listed in section 4 with the person each one depends on.

## 2. What was tested

| Test file | Cases | What it covers |
|---|---|---|
| `test_semantic_rules.py` | 26 | The 12 semantic column types, sensitive flag, tokenizing of column names |
| `test_target_suggestions.py` | 19 | Target ranking, exclusions, overrides, outcome-word rule, synthetic datasets |
| `test_problem_detection.py` | 31 | Classification vs regression, forecasting, clustering, goal wording, alternatives, overrides |
| `test_quality_integration.py` | 37 | Vinitha's rule IDs and severities, penalties, notes, blocking, table-level findings |
| `test_profiling_integration.py` | 14 | Reading Sanjay's profile format |
| `test_cross_dataset.py` | 26 | Healthcare, banking, telecom, education, retail, anonymous columns, empty column |
| `test_run_detection.py` | 33 | The single entry point, feature columns, column roles, statistics |
| `test_handoff_details.py` | 13 | Target statistics, preprocessing hints, time info, validation warnings |
| `test_leakage_checks.py` | 18 | Correlation-based leakage flags and settings |
| `test_handoff_schema.py` | 8 | Real outputs follow `handoff_result.schema.json` |
| `test_training_rules.py` | 9 | Training-eligibility rules (contract 12.2, proposed): suggestion only, target without problem type (Example A), all three approvals, empty feature list, clustering, forecasting time axis |
| `test_samples_and_examples.py` | 16 | Every sample output follows the schema and has the mandatory preprocessing fields (incl. `preprocessing_actions`); sensitive features never recommended; review-decisions schema and sample; the four examples in the contract |
| `test_robustness.py` | 32 | Missing, constant, mixed-type and unpredictable targets; empty, tiny and zero-row data; profiles without columns; failed or unreadable profiles in a multi-dataset run; duplicate dataset names; quality findings for unknown columns; class distribution from profiling |
| `test_integration_day3.py` | 5 | Real HR profile plus quality report, missing target flagged, user target respected |
| `test_input_validation.py` | 26 | Missing, incomplete or failed profiling and quality input; CSV and Excel profiles give the same result |
| `test_thursday_regression.py` | 34 | All 7 fixtures with and without a goal, identifier-like targets, confidence and evidence, leakage kept, D7 |
| `test_review_decisions.py` | 22 | Approved features, target and problem type from the review screen reach the result (and the CLI `--review-decisions`); a wrong dataset id or a plain list is reported, not ignored; sensitive columns are not recommended or approved implicitly; training blocked until target, problem type and features are approved; `review_required` never trains |
| `test_real_inputs.py` | 8 | **Real inputs**: see 2b |
| **Total** | **377** | |

(`test_quality_integration.py` is now 37: one case added for the `Warning / Audit` label.)

Real data: the 6 HumanResources tables from Sanjay's profiling output (with correlations) run through the entry point with Vinitha's corrected Employee findings. Result: no crash; the Employee table with `VacationHours` chosen as the target gives regression (0.80), a strong leakage flag on `SickLeaveHours` (0.98) and quality notes; the other five tables correctly say "review required" because no column looks like an outcome.

### 2b. Fixture-based tests against tests on real module output

| Kind | Tests | Inputs |
|---|---|---|
| **Synthetic / fixture-based** | 342 | Datasets made by `make_synthetic_datasets.py` (7 fixtures) and small hand-written profile and quality dicts. Fixture profiles are rebuilt by this module, not produced by Sanjay's profiler. Quality dicts are written by me in Vinitha's field style. A few cases in `test_input_validation.py` and `test_samples_and_examples.py` read the sample files but check structure only |
| **Real Sanjay profile + real Vinitha quality** | 13 | `test_real_inputs.py` (8) and `test_integration_day3.py` (5). Inputs: `samples/input_profiling_Employee.profile.json` (Sanjay's output for `HumanResources.Employee`, 290 rows); `samples/input_quality_all_tables.json` (Vinitha's six-table report); `samples/input_quality_Employee_rerun.json` (her Employee re-run, converted from her text report by me) |
| **Mixed**: real profile, my own review choices | 22 | `test_review_decisions.py` |
| **Total** | **377** | |

### 2c. Current limits of end-to-end integration

- Only the Employee table has a real Sanjay profile in the tests; the other five HR tables were profiled but their profile files are not in the repository.
- Quality: the five other HR tables are in the six-table report; the fixtures have no real quality report.
- Nothing was run through Sinchana's preprocessing service or Sumanth's AutoML with my output. Her service does not read my approved features, roles or actions today (`PREPROCESSING_ROLE_MAPPING.md` section 4).
- No Team 2 API or UI was involved.
- The tests prove that this module behaves as described when given those inputs; they do not prove that the pipeline works end to end. The module is not marked integration-ready.

## 3. Gaps found today and fixed

| # | Case | Before | Now |
|---|---|---|---|
| 1 | Target 90% missing (user-chosen) | Recommended multiclass classification, confidence 0.85, no warning | `review_required` with a warning. A target 20% to 80% missing keeps its type, loses 0.15 confidence and gets a warning |
| 2 | Target with one distinct value | Recommended classification, 0.85 | `review_required`: "nothing to learn" |
| 3 | Column with mixed text and numbers (profile type `mixed`) | Treated as categorical, usable as target and feature | Treated as unknown: excluded as a feature, cannot be a target |
| 4 | Profile with zero columns | Crash (`IndexError`) | A clear `review_required` result with a warning; other datasets in the same run are unaffected |
| 5 | One failed or unreadable profile in a run of several | The whole run stopped with an error | That dataset gets a `review_required` result with the reason; the others continue |
| 6 | Same dataset name in two profiles | Merged silently into one dataset | First is used, the second gets a result saying so |
| 7 | Quality finding for a column that is not in the dataset | Ignored silently | Ignored with a warning in the result |
| 8 | Class distribution of the target | Only the top values from the profile were used | The profile's full `class_distribution` is used when present for the chosen target |

The thresholds in 1 (20% and 80%) are proposed defaults, not from the SRS.

## 4. Unresolved-case list

| # | Open case | Why it is open | Who |
|---|---|---|---|
| 1 | The HR tables have no outcome-like column, so no target is suggested by default | The system does not guess. The business objective (for example `VacationHours` as a regression target) needs the project owner | Meshak, project owner |
| 2 | Leakage check covers numerical targets only, straight-line correlation only | Profiling gives correlations for numerical pairs only. Categorical association, derived columns and time-based leakage are not detected | Sanjay (new data), Meshak (scope) |
| 3 | Leakage thresholds 0.80 / 0.95 and quality penalties are proposed defaults | Not in the SRS | Meshak |
| 4 | Target missing-share thresholds (20% / 80%) and the rule for mixed-type columns are proposed | Not in the SRS | Meshak |
| 5 | Final quality output for the HR tables is not received in the agreed JSON format | Vinitha's corrected Employee output came as a text report with new rule IDs and severities (`Warning / Audit`, `Low`); one count (structural nulls: 2 records versus 1 in the profile) still to confirm; the other five tables not yet received | Vinitha |
| 6 | Foreign-key columns such as `DepartmentID` and `ShiftID` are classed as identifiers and not offered as features | The column name looks like an ID, and the profile cannot tell a key from a category | Design limit; could use Sanjay's `likely_identifier` (false for these) |
| 7 | A categorical column with many values in a small table (for example 67 values in 100 rows) is treated as text | Judgement based on the share of distinct values; could be a legitimate multiclass target in a larger table | Meshak (confirm the rule) |
| 8 | Time-series gaps cannot be found | Needs the values; the profile only gives start, end and distinct dates | Design limit |
| 9 | Contract fields for preprocessing, and where the user approves feature columns | Interface not frozen; waiting for replies | Sinchana, Sumanth, Meshak |

## 5. Evidence

- Code and tests: GitHub, `semantic_detection/`, branch `samarth-leakage-check` (pull request on top of PR #2).
- Run it: `python -m pytest -q` (377 passed) and `python run_detection.py --profiles profiles --quality outputs/vinitha_employee_rerun_converted.json --quality-dataset HumanResources.Employee.xlsx --override HumanResources.Employee.xlsx=VacationHours`.
- Output structure: `handoff_result.schema.json` and `docs/HANDOFF_CONTRACT.md`.
