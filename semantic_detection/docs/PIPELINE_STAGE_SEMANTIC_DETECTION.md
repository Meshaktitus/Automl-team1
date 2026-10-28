# Pipeline stage submission: Semantic Understanding, Target Detection and Problem Classification

Owner: Samarth (Team 1). Date: Wednesday 28 October 2026. Requested by Meshak: inputs, outputs, target and problem-type handoff, unresolved dependencies, implemented versus proposed, samples.
Labels: **Implemented** (built and tested, 244 test cases passing), **Prototype** (works, not final), **Proposed** (decision or data still needed), **Design only**, **Blocked**.

## 1. Where this stage sits

Sanjay (profiling) and Vinitha (data quality) -> **this stage** -> Sumanth (AutoML: target, problem type, evidence) and Sinchana (preprocessing: feature columns, roles, hints).
This stage never reads the source data file. It reads only the JSON that Sanjay's and Vinitha's stages produce.

## 2. Inputs

| Input | From | Format | Required | Status |
|---|---|---|---|---|
| Profiling output, one per dataset | Sanjay | JSON, `schema_version` `1.0-draft` (`columns[]` with name, dtype, inferred_type, missing, unique, likely_identifier; optional summary, top_values, histogram; optional top-level `correlations[]` and `class_distribution`) | Yes | Implemented, tested on the 6 HumanResources profiles |
| Data-quality report | Vinitha | JSON: `dataset`, `issues[]` (`rule_id`, `severity`, `affected_column`, `affected_rows`, `recommended_action`). Also accepts the older `detected_issues` / `column` names | No | Implemented. **Final output from Vinitha not yet received in this format** (see 7) |
| Business goal | User / backend | Plain text, for example "Forecast sales next month" | No | Implemented |
| Target override | User | `{dataset: column}`. Always wins | No | Implemented |
| Problem-type override | User | One of the 7 supported types. Always wins | No | Implemented |
| Approved feature columns | User | `{dataset: [columns]}` | No | Implemented (how the application collects this is open, see 7) |
| Quality penalty settings, leakage thresholds | Config | Dict; defaults in code | No | Implemented; the default values are **Proposed** (not in the SRS) |

Call: `run_detection(profiles, quality=None, goal=None, overrides=None, problem_type_override=None, quality_dataset=None, quality_settings=None, approved_features=None, leakage_settings=None)`; also a command line. **Prototype:** it is a function and a JSON file. There is no HTTP or storage layer; the backend contract (Meshak) decides that.

## 3. Outputs

A list with one result per dataset (`handoff_result.schema.json` defines it; `docs/HANDOFF_CONTRACT.md` explains every field). Main fields: `target`, `target_source`, `target_confirmed`, `problem_type`, `confidence`, `source`, `needs_confirmation`, `evidence`, `alternatives`, `warnings`, `candidates` (ranked), `semantic_columns`, `feature_columns`, `recommended_feature_columns`, `approved_feature_columns`, `column_roles` (role, reason, preprocessing hint, privacy and quality flags per column), `target_statistics`, `dataset_characteristics`, `leakage_checks`, `status`.
Status is always "Proposed, pending verification". Nothing is final until the user confirms. Implemented; every real output is checked against the schema in the tests.

## 4. Handoff

**To Sumanth (AutoML):** `target`, `target_source`, `target_confirmed`, `problem_type`, `confidence`, `evidence`, `alternatives`, `needs_confirmation`, `target_statistics`, `leakage_checks`.
Rules: a user override always wins; a suggested target is not confirmed (`target_confirmed` false); `problem_type = review_required` means train nothing until a person decides; a column flagged by `leakage_checks` stays a feature with a warning, so the consumer must show it to the user.

**To Sinchana (preprocessing):** `column_roles` (role, reason, `preprocessing_hint`, `needs_privacy_review`, `quality_blocked`, `quality_issue_codes`, `leakage_suspect`), `recommended_feature_columns`, `approved_feature_columns`, `dataset_characteristics`.
Status: **Implemented and tested on our side; the fields are Proposed until Sinchana agrees them.** The reply from Sinchana has not arrived.

## 5. Error handling (verified by running each case on 28 Oct)

| Situation | What happens | Tested |
|---|---|---|
| Profile has `status: failed` | That dataset gets a `review_required` result with the profile's error code in `warnings`; other datasets continue | Yes |
| Wrong `schema_version`, missing required column field, profile not a JSON object | Same: a result for that dataset with the reason; others continue | Yes |
| Profile file missing or not valid JSON | Same: result named after the file, with the reason | Yes |
| Profile with no columns | `review_required` result: "no columns" | Yes |
| Same dataset name in two profiles | First is used; the second gets a result saying so | Yes |
| No profiles at all | Raises a clear error (a caller mistake) | Yes |
| Quality report is not an object or has no `issues` list | Raises a clear error | Yes |
| Quality finding names a column that is not in the dataset | Finding ignored, warning added to the result | Yes |
| Quality finding with an unknown severity | Treated as a warning, and the note says so | Yes |
| Quality finding with 0 affected rows | Treated as a passed check: no penalty, not listed on the column | Yes |
| Quality report for another dataset, or no dataset given for several datasets | Not applied; warning says so | Yes |
| Target override names a missing column | Warning; `review_required` | Yes |
| Target is 80% or more missing, or constant | `review_required` with a reason (20% to 80% missing lowers confidence) | Yes |
| Target is an identifier, text, date, or a mixed-type column | `review_required`: "cannot be predicted directly" | Yes |
| Unsupported problem-type override | Warning; `review_required` | Yes |
| Business goal does not fit the data (for example forecasting with no date column) | Goal not used; the reason is in `warnings` | Yes |
| Unknown quality or leakage setting | Raises a clear error | Yes |

Known gap: an unreadable quality file raises an error and stops the call (it is a caller mistake). A quality finding without a `rule_id` is accepted without a warning.

## 6. Source-data preservation and reproducibility

- **Source data:** never opened. The inputs (profiles, quality report) are only read, never changed. The only file written is the output path you pass in. Verified in the code: no network calls, no writes except the output.
- **Reproducibility:** no random numbers. The same inputs and the same settings give identical output (checked by running the same call twice and comparing). **Implemented.**
- **Proposed, not built:** put the code version, the settings used and the input file names into every output, so an experiment can be traced back to exactly what was used. I propose adding this once Meshak confirms where such metadata should live.

## 7. Unresolved dependencies and questions

| # | Open point | Depends on |
|---|---|---|
| 1 | Final quality output for the HR tables in the agreed JSON format with the agreed rule IDs and severities (Employee re-run came as text with new IDs and severities such as "Warning / Audit"). One count (structural nulls: 2 records versus 1 in the profile) to confirm. Other five tables not received | Vinitha |
| 2 | Will `dataset_reference.name` stay the file name? Quality results are matched on it | Sanjay |
| 3 | Profiling's `class_distribution` only exists when `target_column` is sent. Will the backend run profiling again after the user picks a target? | Sanjay, Meshak |
| 4 | Profiling's `likely_identifier` on key columns (`JobCandidate.BusinessEntityID` is true with 84.6% missing) | Sanjay |
| 5 | Agree the preprocessing fields (roles, hints, privacy flags) and who owns each | Sinchana, Sumanth, Meshak |
| 6 | Where and how the user approves feature columns (`approved_features`) | Meshak, Sumanth |
| 7 | Approve the proposed defaults: leakage 0.80 / 0.95, quality penalties, target missing 20% / 80%, mixed-type columns excluded | Meshak |
| 8 | Final business objective for the HR demo (no outcome-like column exists; `VacationHours` was an example) | Meshak, project owner |
| 9 | Transport: function call, JSON file or API for passing results | Meshak (backend contract) |
| 10 | Leakage check covers numerical targets only; categorical association, derived columns and time-based leakage are not detected | Sanjay (data), Meshak (scope) |

## 8. Sample inputs and outputs (real files in `samples/`)

| File | What it is |
|---|---|
| `input_profiling_Employee.profile.json` | Sanjay's real profile of HumanResources.Employee (290 rows, with correlations) |
| `input_quality_Employee.json` | Vinitha's corrected Employee findings (typed into JSON by me from her text report) |
| `output_Employee_with_user_target.json` | Result with `VacationHours` chosen as target: regression, strong leakage flag on `SickLeaveHours`, quality notes |
| `output_Shift_no_target.json` | Result for a table with no outcome-like column: `review_required` |
| `output_failed_profile.json` | Result when the profile has `status: failed` |

Run: `python run_detection.py --profiles profiles --quality samples/input_quality_Employee.json --quality-dataset HumanResources.Employee.xlsx --override HumanResources.Employee.xlsx=VacationHours`

## 9. Implemented and tested versus proposed

| Item | Status |
|---|---|
| 12 semantic column types with evidence and sensitive flag | Implemented, tested |
| Target ranking, overrides, alternatives | Implemented, tested |
| Problem-type recommendation (7 types, goal check, overrides) | Implemented, tested |
| Reading Sanjay's profile and Vinitha's report | Implemented, tested |
| Column roles, preprocessing hints, target statistics | Implemented, tested; fields Proposed until Sinchana agrees |
| Leakage check (numerical targets) | Implemented, tested; limits stated; thresholds Proposed |
| Output schema and tests that check it | Implemented, tested |
| Error handling in section 5 | Implemented, tested |
| Quality penalties, missing-target thresholds | Implemented; values Proposed |
| Source and settings recorded in each output | Proposed |
| API or storage layer | Not built; depends on the backend contract |
| Preprocessing and AutoML consumption of our output | Not in this stage; owners Sinchana and Sumanth |
