# Progress report: Semantic Understanding, Target Detection and Problem Classification

Owner: Samarth (Team 1). Report date: Tuesday 27 October 2026.
Coverage: Sprint 1 Week 1 and the dated plan from Thu 22 Oct up to today (Tue 27 Oct). Nothing after today is reported.
Honest labels used below: **Implemented**, **Prototype**, **Design only**, **Blocked**, **Ready for review**.

## 1. Summary

All planned work up to and including today (Tue 27 Oct) is complete. The module is Implemented and tested (217 test cases, all passing), the code is on GitHub (PR #1 merged, PR #2 open for review), and the written deliverables exist in `semantic_detection/docs/`. The target-leakage code is pushed to its own branch (`samarth-leakage-check`); its pull request has not been opened yet. Open items are dependencies on other people, not unfinished work: target-leakage checks (partly built: numerical targets only), real quality output for the HR tables (Vinitha), agreement of the contract fields with Sinchana, and approval of the quality penalty values.

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

## 3. What the module does now

- Detects 12 semantic column types with evidence, alternatives and a sensitive flag.
- Ranks target candidates (score, confidence, reason), keeps user overrides first, and never treats a suggestion as confirmed.
- Recommends one of 7 problem types from the target, the business goal and the data, checking that the goal fits the data.
- Reads Sanjay's profiling output, including the new correlations (verified: 40 of 40 profiled HR columns match the report from the real data; the 6 new HumanResources profiles run without code changes) and Vinitha's quality output (rules `NULL_CHECK`, `DUP_ROW`, `INVALID_RANGE`, `OUTLIER_IQR`; Warning and Blocking).
- Flags possible target leakage from Sanjay's correlations (numerical targets only; flagged columns are kept with a warning, not removed).
- One entry point (`run_detection.py`) gives, per dataset: target, problem type, confidence, evidence, alternatives, warnings, ranked candidates, recommended and approved feature columns, a role and preprocessing hint for every column, target statistics, dataset characteristics and validation warnings, and the leakage-check status.
- Tested on HR data and on healthcare, banking, telecom, education and retail data, plus anonymous column names and an empty column. Nothing is hard-coded to HR.

Size: about 2,900 lines of code, 217 test cases, 3 documents.

## 4. Today's work (Tue 27 Oct), separate

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
| Built the target-leakage check on his correlations: flags columns with correlation of at least 0.80 (possible) or 0.95 (strong) with a numerical target; keeps them as features with a warning. Real example: with VacationHours as target, SickLeaveHours is flagged strong (0.98) | `leakage_checks.py`, `test_leakage_checks.py` (18 tests), branch `samarth-leakage-check` (pushed, 209 tests passing, PR not yet opened) |
| Fixed a display bug: quality findings with 0 affected rows are no longer listed on column roles | `run_detection.py` |
| Checked Vinitha's new Employee output against Sanjay's profile and the real data. Found two errors: an outlier count of 10 where the standard IQR rule gives 0, and a BirthDate rule described as "age against today" when the real rule is age at hire (2 rows; 0 against today). She confirmed both and sent a corrected re-run | Messages to Vinitha; I verified the numbers myself on the Employee file |
| Prepared a live demo on the 6 HR tables (target chosen by the user, leakage warning, quality notes) | `run_detection.py` run, `demo_summary.py` |
| Wrote the machine-readable output schema (JSON Schema) for the handoff result, with a test that checks real outputs against it. It caught one value the schema did not list (`User-selected` confidence level), fixed, and one unknown-dataset result with a different shape, fixed | `handoff_result.schema.json`, `test_handoff_schema.py` (8 tests) |
| Cleaned the project: moved an old backup folder out, which was making the tests load an old file | Test run: 209 passed |

Test count: 117 (Mon night) to 217 (today).

## 5. Open items and dependencies (not unfinished work)

| Item | Status | Who |
|---|---|---|
| Target-leakage checks | **Partly implemented.** Uses Sanjay's correlations; flags (does not remove) columns with correlation of at least 0.80 with a numerical target. Categorical targets, derived columns and time-based leakage are not covered | Meshak to approve thresholds |
| Real quality output for the HumanResources tables | Corrected Employee re-run received today as a text report (age-at-hire rule, 0 outliers). I typed it into JSON to test it. Still needed: the final output in the agreed JSON format with the agreed rule IDs and severities; one count (structural nulls, 2 records versus 1 in Sanjay's profile) to confirm; the other five tables | Vinitha |
| Contract fields for preprocessing | Waiting for Sinchana's reply; interface not frozen | Sinchana, Sumanth, Meshak |
| Quality penalty values (Medium x0.85, High x0.6, Blocking x0) | Not in the SRS; configurable proposed defaults, waiting for approval | Meshak |
| HR demo business objective | `VacationHours` discussed as a possible target; final objective needs project-owner confirmation | Meshak, project owner |
| Review and merge of PR #2 | Open, review requested | Meshak |
| Pull request for the leakage check | Code pushed, PR to be opened with base branch `samarth-contract-rev2` (merge after PR #2) | Samarth, then Meshak |
| Where and how the user approves feature columns in the application | Open question | Meshak, Sumanth |
| Time-series gaps | Cannot be found from the profile; the field says so | Design limit |

## 6. Proposed follow-up tickets

1. Extend leakage checks beyond numerical targets if profiling can provide more (for example categorical association).
2. Freeze the output contract after Sinchana's and Sumanth's sign-off; add a versioned schema file and a validation test.
3. Add value-level checks (time-series gaps, full class distributions) if the profiling module can supply them.
4. Replace the proposed quality penalties with the approved values and document them.
5. Add the user-approval step for feature columns and the business-goal input to the application interface.
