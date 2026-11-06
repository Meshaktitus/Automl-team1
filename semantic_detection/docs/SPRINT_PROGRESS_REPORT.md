# Progress report: Semantic Understanding, Target Detection and Problem Classification

Owner: Samarth (Team 1). Report date: Friday 30 October 2026 (sprint closure).
Coverage: Sprint 1 Week 1 and the dated plan from Thu 22 Oct up to today (Fri 30 Oct, sprint closure). Nothing after today is reported.
Honest labels used below: **Implemented**, **Prototype**, **Design only**, **Blocked**, **Ready for review**.

## 1. Summary

All planned work up to and including today (Fri 30 Oct, sprint closure) is complete on my side; what remains is confirmation from other teams (see section 5). The module is Implemented and tested (281 test cases, all passing), the code is on GitHub (PR #1 merged; PR #2 closed on 30 Oct because PR #3 contains all of it; PR #3, based on `main`, open for review), and the written deliverables exist in `semantic_detection/docs/`. All work is in one branch (`samarth-leakage-check`, PR #3, based on `main`). Document status: **Proposed — Pending Review**. Open items are dependencies on other people, not unfinished work: target-leakage checks (partly built: numerical targets only), real quality output for the HR tables (Vinitha), agreement of the contract fields with Sinchana, and approval of the quality penalty values.

## 2. Plan versus status (through today)

| Plan day | Planned deliverable | Status | Where |
|---|---|---|---|
| Sprint Mon | Semantic type catalogue | Implemented | Spec section 1 |
| | Problem-type matrix | Implemented | Spec section 4 |
| | Output schema and synthetic examples | Implemented | Spec section 2, contract, `make_synthetic_datasets.py` |
| Sprint Tue | Initial semantic detector | Implemented | `semantic_rules.py`, `analyze_semantics.py` |
| | Target-ranking design | Implemented | Spec section 3, `target_suggestions.py` |
| | Test cases and misclassification notes | Implemented | Tests; spec section 8 (bugs found and fixed) |
| Sprint Wed | Problem-detection prototype | Implemented | `problem_detection.py` |
| | Decision-rule specification | Implemented | Spec section 4 |
| | Scenario test results | Implemented | Spec sections 7 and 8, cross-domain tests |
| Sprint Thu | Integration specification | Implemented | Spec section 5 |
| | Recommendation examples | Implemented | Contract section 8 |
| | Updated interface and decision rules | Ready for review | Contract revision 3 |
| Sprint Fri | Validated examples, prototype, tests, docs committed | Implemented | GitHub PR #1 (merged), PR #2 |
| | Implementation tickets | See section 6 | |
| | Progress report | This document | |
| Thu 22 Oct | Baseline checklist | Implemented | Spec section 6 |
| | Synthetic task datasets (7) and ambiguous-target cases | Implemented | `make_synthetic_datasets.py` |
| Fri 23 Oct | Semantic output, target-ranking tests, problem-type examples | Implemented | Code and tests |
| Mon 26 Oct | Semantic labels with evidence, target candidates, unit tests | Implemented | Code and tests |
| Tue 27 Oct | Problem-type rules, alternative-target examples, override tests | Implemented | Code and tests; details in section 4 |
| Wed 28 Oct | Integrated detection module | Implemented | `run_detection.py` (profiling + quality + goal + overrides in one call) |
| | Test report and unresolved-case list | Implemented | `docs/TEST_REPORT.md` |
| | Updated interface contract | Ready for review | Contract revision 3 plus today's additions, `handoff_result.schema.json` |
| Thu 29 Oct | Prototype integration with the draft contract (AutoML handoff: target, problem type, features as one JSON file per run) | Implemented (prototype); contract **Proposed** | `run_detection.py`, `handoff_result.schema.json`, 281 tests |
| | Requirements and pending clarifications for Team 2, Team 3, Sinchana and Sumanth (proposed versus finalized, blockers, owners) | Implemented (document); answers **Pending** | `docs/INTEGRATION_REQUIREMENTS.md` |
| | Document the numerical-target leakage limit and the pending feature-approval step | Implemented | `docs/INTEGRATION_REQUIREMENTS.md` sections 6 and 7, contract section 11 |
| Fri 30 Oct | Sprint closure: record decisions, branch cleanup, final summary | Implemented; contract **Proposed** | Section 4d, `docs/HANDOFF_CONTRACT.md` section 14, `docs/INTEGRATION_REQUIREMENTS.md` section 11 |

## 3. What the module does now

- Detects 12 semantic column types with evidence, alternatives and a sensitive flag.
- Ranks target candidates (score, confidence, reason), keeps user overrides first, and never treats a suggestion as confirmed.
- Recommends one of 7 problem types from the target, the business goal and the data, checking that the goal fits the data.
- Reads Sanjay's profiling output, including the new correlations (verified: 40 of 40 profiled HR columns match the report from the real data; the 6 new HumanResources profiles run without code changes) and Vinitha's quality output (rules `NULL_CHECK`, `DUP_ROW`, `INVALID_RANGE`, `OUTLIER_IQR`; Warning and Blocking).
- Flags possible target leakage from Sanjay's correlations (numerical targets only; flagged columns are kept with a warning, not removed).
- One entry point (`run_detection.py`) gives, per dataset: target, problem type, confidence, evidence, alternatives, warnings, ranked candidates, recommended and approved feature columns, a role and preprocessing hint for every column, target statistics, dataset characteristics and validation warnings, and the leakage-check status.
- Tested on HR data and on healthcare, banking, telecom, education and retail data, plus anonymous column names and an empty column. Nothing is hard-coded to HR.

Size: about 2,900 lines of code, 281 test cases, 3 documents.

## 4. Tuesday 27 Oct

| Work | Deliverable |
|---|---|
| Task classification: classification vs regression, forecasting and clustering signals, alternatives, overrides, ambiguity tests | `problem_detection.py` with its tests (31) |
| Cross-domain tests requested by Meshak: 5 non-HR datasets, overrides, alternatives. Found two missing outcome words (`readmitted`, `final_score`) and fixed them | `test_cross_dataset.py` (26 tests), updated `target_suggestions.py` |
| Single integrated entry point, one dataset or many per call | `run_detection.py`, `test_run_detection.py` (30 tests) |
| Quality integration for the final format: both rule-ID styles, `issues` and `affected_column` field names, table-level duplicate-row findings, null findings as notes, configurable penalties | `quality_integration.py`, `test_quality_integration.py` (35 tests) |
| Checked Vinitha's sample against Sanjay's profile of the same table: they contradict each other (JobTitle missing, duplicate rows), so I asked for real output | Message to Vinitha |
| Contract revision 2 after Meshak's review, then revision 3 after Sumanth's review: target statistics, feature lists, preprocessing hints, time info, validation warnings, defined allowed values, score explanation | `handoff_details.py`, `test_handoff_details.py` (10 tests), `docs/HANDOFF_CONTRACT.md`, `docs/SEMANTIC_PROBLEM_SPEC.md` |
| Set up Git, cloned the team repo, opened PR #1 (merged by Meshak) and PR #2 (open, updated with revision 3) | github.com/Meshaktitus/Automl-team1 |
| Verified the merged `main`: all tests pass on it | Test run |
| Received Sanjay's new profiles (6 HumanResources tables, now with correlations, histograms, quartiles). Ran them through the entry point: no code changes needed. Noted two small points for him (`likely_identifier` on key columns and on JobCandidate.BusinessEntityID) | Message to Sanjay |
| Built the target-leakage check on his correlations: flags columns with correlation of at least 0.80 (possible) or 0.95 (strong) with a numerical target; keeps them as features with a warning. Real example: with VacationHours as target, SickLeaveHours is flagged strong (0.98) | `leakage_checks.py`, `test_leakage_checks.py` (18 tests), branch `samarth-leakage-check` (pushed; PR open on top of PR #2) |
| Fixed a display bug: quality findings with 0 affected rows are no longer listed on column roles | `run_detection.py` |
| Checked Vinitha's new Employee output against Sanjay's profile and the real data. Found two errors: an outlier count of 10 where the standard IQR rule gives 0, and a BirthDate rule described as "age against today" when the real rule is age at hire (2 rows; 0 against today). She confirmed both and sent a corrected re-run | Messages to Vinitha; I verified the numbers myself on the Employee file |
| Prepared a live demo on the 6 HR tables (target chosen by the user, leakage warning, quality notes) | `run_detection.py` run, `demo_summary.py` |
| Wrote the machine-readable output schema (JSON Schema) for the handoff result, with a test that checks real outputs against it. It caught one value the schema did not list (`User-selected` confidence level), fixed, and one unknown-dataset result with a different shape, fixed | `handoff_result.schema.json`, `test_handoff_schema.py` (8 tests) |
| Cleaned the project: moved an old backup folder out, which was making the tests load an old file | Test run: 209 passed |

Test count: 117 (Mon night) to 281 (today).

## 4b. Today's work (Wed 28 Oct), separate

| Work | Deliverable |
|---|---|
| Tested missing, ambiguous and poorly populated targets and columns: 19 cases (target mostly empty, constant target, mixed-type column, text/date/identifier targets, empty and tiny data, zero-row data, a profile without columns, tied outcome names, goals that do not fit, bad overrides) | `test_robustness.py` |
| Found and fixed 4 real gaps and 1 crash: a 90%-empty target was still recommended at 0.85 confidence; a constant target was recommended; mixed text/number columns were usable; a profile with no columns crashed | `problem_detection.py`, `profiling_integration.py`, `run_detection.py` |
| Used the full class distribution from Sanjay's profile when it is given for the chosen target (2 tests) | `handoff_details.py`, `run_detection.py` |
| Wrote the test report with the unresolved-case list (9 open cases, each with an owner) | `docs/TEST_REPORT.md` |
| Meshak asked every owner for inputs, outputs, dependencies, error handling, implemented versus proposed, and samples. Verified each failure case on real code, fixed 3 weak spots (one bad profile no longer stops a run; duplicate dataset names; quality findings for unknown columns), and wrote the stage submission with 5 real sample files | `docs/PIPELINE_STAGE_SEMANTIC_DETECTION.md`, `samples/` |
| Contract and spec updated with the new rules; progress report updated | `docs/HANDOFF_CONTRACT.md`, `docs/SEMANTIC_PROBLEM_SPEC.md` |

Test count today: 217 to 281.

## 4c. Today's work (Thu 29 Oct), separate

| Work | Deliverable |
|---|---|
| Answered Meshak's readiness question: target detection, problem-type identification and the agreed output schema are verified; limits and proposed values stated | Message, `docs/PIPELINE_STAGE_SEMANTIC_DETECTION.md` |
| Recorded Meshak's working decisions: `VacationHours` is a provisional demo target; thresholds, penalties and confidence values are proposed defaults; features stay pending until the user approves; one JSON file per run, API after Team 2 confirms | `docs/HANDOFF_CONTRACT.md` section 11 |
| Wrote the table "When a human must confirm before training" | `docs/HANDOFF_CONTRACT.md` section 11 |
| Followed Sanjay's corrections: class distribution is skipped only for identifiers, text or targets with more than 20 distinct values; a failed profile and the `CLASS_DISTRIBUTION_SKIPPED` warning are handled; `dataset_id` is the key. Fixed: a failed, duplicate or empty profile now keeps its `dataset_id` | `run_detection.py`, tests |
| Found and fixed a bug while checking the feature-approval input: approved features were matched by display name only, so a backend sending `dataset_id` would have been ignored. Now both work (1 new test) | `run_detection.py`, `tests/test_robustness.py` |
| Wrote the integration requirements for Team 2 (Backend) and Team 3 (Frontend), Sinchana and Sumanth: inputs, outputs, schema, API dependencies, feature-approval step, decisions needed, proposed versus finalized, blockers with owners and requested times. Documented that leakage is checked for numerical targets only | `docs/INTEGRATION_REQUIREMENTS.md` |
| Answered Sinchana's 4 clarifications (preprocessing): fixed-value `preprocessing_actions` added next to the free-text hint; sensitive features are no longer recommended until the user approves them (proposed default, found while checking her privacy question); mandatory versus optional fields, the training rule (no supervised training until the target is confirmed) and the exact problem-type values written down; trimmed sample added | `docs/HANDOFF_CONTRACT.md` section 12, `handoff_details.py`, `run_detection.py`, `samples/` |
| Test output on the six HR tables prepared for Sanjay | `six_tables_test_output.txt` (shared directly, not in the repo) |
| Recorded the lead's decision to use Team 3's single review screen for problem type, target and features (field mapping **Proposed**) | `docs/INTEGRATION_REQUIREMENTS.md` section 5b |
| Evidence pack for the lead's 12-item request: index of artifacts with Proposed/approved status, a schema and sample for the review-screen payload, the full test run | `docs/EVIDENCE_INDEX.md`, `review_decisions.schema.json`, `docs/TEST_EXECUTION_EVIDENCE.txt` |
| Fixed the lead's review points: regenerated the four contract examples (sensitive features were still recommended in one), one name `approved_feature_columns` everywhere, explained `target_confirmed` versus `needs_confirmation`, explained that `status` is neither approval nor runtime status, aligned the problem-type lists | `docs/HANDOFF_CONTRACT.md` section 13, `docs/INTEGRATION_REQUIREMENTS.md` section 10 |
| Added the training-eligibility rules as code with 9 tests, and 16 tests that check every sample and example against the schema | `training_rules.py`, `tests/test_training_rules.py`, `tests/test_samples_and_examples.py` |
| Classification and regression demo with saved output (stand-in profile, not the profiling module) | `demo_end_to_end.py`, `docs/DEMO_EVIDENCE_classification_regression.txt` |
| Test count today: 250 to 281, all passing | Test run |

## 4d. Today's work (Fri 30 Oct, sprint closure), separate

| Work | Deliverable |
|---|---|
| Windows blocked a pandas file in my main environment. Made a fresh environment with another pandas version and ran the full suite on my own laptop: 281 passed. Ran the demo live | Local test run, `demo_end_to_end.py` |
| Recorded AutoML's answers: the design covers binary classification, multiclass classification and regression; forecasting and clustering are planned; anomaly detection and recommendation are not confirmed; the training rule in 12.2 is acceptable. The mandatory fields in 12.1 are still to be checked by AutoML | `docs/INTEGRATION_REQUIREMENTS.md` sections 3b and 5, contract section 13 |
| Recorded the lead's decisions: defaults stay **Proposed** until the Project Management Team confirms; sensitive columns approved as not recommended by default; unsupported problem types are shown but marked unsupported with training disabled; PR #3 may go to `main` | `docs/HANDOFF_CONTRACT.md` section 14, `docs/INTEGRATION_REQUIREMENTS.md` section 11 |
| Recorded the preprocessing review: the eight `column_roles[]` fields cover its metadata needs; its own request/response contract is separate and pending. Found a gap she exposed: the trimmed sample hid the leakage flag of `SickLeaveHours`. Fixed the sample, proposed `leakage_suspect` as a ninth mandatory field | `samples/output_Employee_mandatory_fields_only.json`, contract section 14 |
| Branches: deleted the old merged branch, confirmed that all of PR #2 is inside PR #3 (`git merge-base --is-ancestor` returned 0), closed PR #2 without merging, updated the description of PR #3 (based on `main`) | GitHub |
| Final summary for sprint closure | This report |

## 5. Open items and dependencies (not unfinished work)

| Item | Status | Who |
|---|---|---|
| Target-leakage checks | **Partly implemented.** Uses Sanjay's correlations; flags (does not remove) columns with correlation of at least 0.80 with a numerical target. Categorical targets, derived columns and time-based leakage are not covered | Meshak to approve thresholds |
| Real quality output for the HumanResources tables | **Received and integrated (28 Oct):** the final quality JSON for all 6 tables, in the agreed format, with corrected counts. Still to confirm: her assumptions (pay band 6.50 to 125.00 per hour for `Rate`; age range at hire) | Vinitha |
| Contract fields for preprocessing | **Partly answered (30 Oct):** the eight `column_roles[]` fields cover the metadata needs; a ninth field (`leakage_suspect`) is proposed; the preprocessing request/response contract is a separate pending contract. Contract stays **Proposed** | Sinchana, Meshak |
| Quality penalty values and all other defaults (Medium x0.85, High x0.6, Blocking x0; confidence values; leakage 0.80 and 0.95) | Configurable proposed defaults. Stay **Proposed** until the Project Management Team confirms (lead, 30 Oct) | Meshak, Project Management Team |
| HR demo business objective | Working decision (29 Oct): `VacationHours` is a provisional demo target. The final objective and target must be confirmed by the Project Management Team; the lead was asked to request it (30 Oct). **Pending** | Meshak, Project Management Team |
| PR #2 | **Closed on 30 Oct** without merging; all its commits are in PR #3 | Done |
| PR #3 (all work, based on `main`) | Open; the lead reviews it before approving the merge. After the merge my two old branches are deleted | Meshak |
| Where and how the user approves feature columns in the application | Working decision: features stay pending until the user approves; the screen is to be agreed with Team 3 | Team 3, Meshak |
| Backend contract (how the module is called, `dataset_id`, storage of user decisions) and the API | Pending. API on hold until Team 2 confirms; questions B1 to B8 in `docs/INTEGRATION_REQUIREMENTS.md` | Team 2 |
| Time-series gaps | Cannot be found from the profile; the field says so | Design limit |

## 6. Proposed follow-up tickets

1. Extend leakage checks beyond numerical targets if profiling can provide more (for example categorical association).
2. Freeze the output contract after Sinchana's and Sumanth's sign-off; add a versioned schema file and a validation test.
3. Add value-level checks (time-series gaps, full class distributions) if the profiling module can supply them.
4. Replace the proposed quality penalties with the approved values and document them.
5. Add the user-approval step for feature columns and the business-goal input to the application interface.
