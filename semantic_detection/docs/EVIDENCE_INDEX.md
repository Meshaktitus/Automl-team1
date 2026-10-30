# Evidence index for the Team 1 Consolidated Integration Requirements

Module: Semantic Understanding, Target Detection and Problem Classification. Owner: Samarth. Prepared Thu 29 Oct 2026 for Meshak.
Repo: github.com/Meshaktitus/Automl-team1, folder `semantic_detection/`. Latest commit on `samarth-leakage-check`: `7e0cd77`.

**Meshak's six review points (29 Oct) and the resolution of each:** `docs/HANDOFF_CONTRACT.md` section 13.

**Document status: Proposed — Pending Review.**

**Approval status in one line:** no contract is approved yet. Everything below is **Proposed**, except the **working decisions** by Meshak (28-29 Oct), which are listed in section 12. All files are paths inside `semantic_detection/`.

## Items 1 to 12

| # | Requested | Where | Status |
|---|---|---|---|
| 1 | Module integration requirements | `docs/INTEGRATION_REQUIREMENTS.md` (inputs, outputs, questions for Team 2, Team 3, Sinchana, Sumanth, blockers with owners and requested times) | Proposed |
| 2 | Input and output contracts, JSON schemas | Output contract: `docs/HANDOFF_CONTRACT.md` (section 12 = contract for preprocessing and AutoML) and `handoff_result.schema.json`. Input from profiling: Sanjay's `PROFILING_CONTRACT.md` and `profiling_response.schema.json` (his files). Input from quality: format in `INTEGRATION_REQUIREMENTS.md` section 2. User decisions: `review_decisions.schema.json` (new) | Proposed. The schema file of the quality report does not exist; it is described in text only |
| 3 | Sample request and response files | `samples/`: `input_profiling_Employee.profile.json`, `input_quality_Employee.json`, `input_quality_all_tables.json`, `input_review_decisions_Employee.json` (new), `output_Employee_with_user_target.json`, `output_Shift_no_target.json`, `output_failed_profile.json`, `output_all_tables.json`, `output_Employee_mandatory_fields_only.json` | Proposed. Every full output sample is checked against the schema by tests, including `preprocessing_actions` |
| 4 | Problem type, target and feature selection documentation | `docs/SEMANTIC_PROBLEM_SPEC.md` (rules, confidence, precedence), `docs/PIPELINE_STAGE_SEMANTIC_DETECTION.md` (stage description), `docs/HANDOFF_CONTRACT.md` sections 3 to 6 | Proposed |
| 5 | Feature approval workflow and payload (one name everywhere: `approved_feature_columns`) | Workflow: `docs/INTEGRATION_REQUIREMENTS.md` sections 5b and 6 (single review screen, working decision 29 Oct). Payload: `review_decisions.schema.json` and `samples/input_review_decisions_Employee.json`. Result flags: `features_status`, `approved_feature_columns` | Workflow = working decision. Payload schema = Proposed, new 29 Oct; checked by `test_samples_and_examples.py`; the function takes the same values as separate arguments |
| 6 | Leakage rules and limits | `docs/HANDOFF_CONTRACT.md` section 5 and `docs/INTEGRATION_REQUIREMENTS.md` section 7. Rules: numerical targets only, Pearson from the profile, flag at 0.80 (possible) and 0.95 (strong), flags but never removes a column, correlation is not proof | Proposed (thresholds are defaults) |
| 7 | Branch and PR links | PR #1 `samarth-semantic-detection`: merged. PR #2 `samarth-contract-rev2`: github.com/Meshaktitus/Automl-team1/pull/2, open, do not merge until Sinchana reviews. PR #3 `samarth-leakage-check`: github.com/Meshaktitus/Automl-team1/pull/3, open, base PR #2, includes its commits | Open for review |
| 8 | Latest unit and integration test reports | `docs/TEST_REPORT.md` (281 tests, per file, 9 unresolved cases with owners) and `docs/SPRINT_PROGRESS_REPORT.md` | Implemented |
| 9 | Test execution evidence and sample outputs | `docs/TEST_EXECUTION_EVIDENCE.txt` (full `pytest -v`, 281 passed; run in my sandbox, Python 3.13). Same result on my own Windows machine (281 passed, 29 Oct). Sample outputs in `samples/`. `six_tables_test_output.txt` (six HR tables, shared with Sanjay) is outside the repo | Implemented |
| 10 | Field-mapping / dependencies for Preprocessing, Model Recommendation, Team 2, Team 3 | Preprocessing (Sinchana): `docs/HANDOFF_CONTRACT.md` 12.1 (mandatory vs optional), 12.4 (`preprocessing_actions`), 12.5 (privacy). Model recommendation / AutoML (Sumanth): 12.1 to 12.3. Team 2: questions B1 to B8. Team 3: section 5b and F1 to F6 in `INTEGRATION_REQUIREMENTS.md` | Proposed; pending validation by Sinchana and Sumanth, and Team 2 API |
| 11 | Known issues, pending reviews, unresolved dependencies | `docs/INTEGRATION_REQUIREMENTS.md` sections 7 and 9; table below | See below |
| 12 | Proposed defaults and decisions awaiting approval | Tables below | See below |

## 11. Known issues, pending reviews, unresolved dependencies

| Item | Owner | State |
|---|---|---|
| Backend contract B1 to B8 (call method, `dataset_id`, re-profiling with target, storage of decisions, errors, version field, where settings live) | Team 2 | Pending. API stays on hold |
| Review screen details F3 to F6 | Team 3 | Pending |
| Section 12.1 review against preprocessing request/response contracts | Sinchana | In review; she will send gaps before confirming |
| Exact mandatory fields (12.1) | Sumanth | Pending. He will check them. Problem types and training rule answered 30 Oct |
| Review of PR #2 and PR #3, merge to `main` | Meshak, Sumanth, Sinchana | Pending |
| Final HR business objective and target | Project owner via Meshak | Pending; HR tables have no outcome column |
| Quality JSON for the 7 synthetic datasets | Vinitha | She will run it; not received yet |
| Leakage covers numerical targets only; no time-series gap check; goal words used for forecasting and clustering | Samarth | Known limits, documented |
| Training rules (12.2) have a reference function `training_rules.py` and 9 tests. Sumanth accepted the rule on 30 Oct; still Proposed until Meshak approves | Samarth | Done; approval pending Meshak |
| AutoML supports only 3 types today (binary, multiclass, regression); forecasting and clustering planned; anomaly detection and recommendation not confirmed | Sumanth | Answered 30 Oct. Handling of unsupported recommended types: Pending (Meshak, Sumanth, frontend) |
| `VacationHours` correlates 0.9783 with `SickLeaveHours` | Samarth | Flagged by the leakage check |

## 12. Decisions and defaults

**Working decisions (Meshak):** features stay pending until the user approves them (28 Oct); one JSON file per run for now, API later (28 Oct); `VacationHours` as provisional demo target (28 Oct); single review screen for problem type, target and features, proposed by Team 3 (29 Oct 14:31). Field mappings stay Proposed.

**Answered by the owners (29 Oct):** `dataset_id` is the key (Sanjay); `class_distribution` appears only with `options.target_column` and not above 20 distinct values (Sanjay); Vinitha answered that the pay band 6.50 to 125.00 per hour is a project baseline wage assumption and that the valid age at hire is 18 to 65. **These two assumptions stay Pending** until the project owner approves them.

**Proposed defaults awaiting approval (Meshak, by Fri 30 Oct):**

| Default | Value |
|---|---|
| Confidence start values | classification 0.85 (0.60 above 20 classes); regression 0.80 (0.55 if 10 or fewer distinct values); no target 0.30; goal-based forecasting 0.90, clustering 0.85, anomaly 0.80, recommendation 0.75; user override 1.0; maximum 0.95 |
| Confidence adjustments | goal agrees +0.10; goal disagrees -0.20; several task types cap 0.50 |
| Target missing values | 20 to 80 percent: -0.15; 80 percent or more, or constant: `review_required` (0.3) |
| Leakage thresholds | possible 0.80, strong 0.95 |
| Quality penalties and blocking rules | `quality_integration.py` settings; Blocking blocks a column (not for null, duplicate or key findings) |
| Sensitive features not recommended until the user approves them | Proposed 29 Oct; pending Meshak and Sinchana |
| `preprocessing_actions` fixed values (incl. `scale_numeric`, `extract_date_features`, `group_rare_categories`) | Proposed; pending Sinchana |
| Mandatory vs optional output fields; exact problem-type values | Proposed; pending Sumanth and Sinchana |
