# Progress report: Semantic Understanding, Target Detection and Problem Classification

Owner: Samarth (Team 1). Report date: Tuesday 27 October 2026.
Coverage: Sprint 1 Week 1 and the dated plan from Thu 22 Oct up to today (Tue 27 Oct). Nothing after today is reported.
Honest labels used below: **Implemented**, **Prototype**, **Design only**, **Blocked**, **Ready for review**.

## 1. Summary

All planned work up to and including today (Tue 27 Oct) is complete. The module is Implemented and tested (209 test cases, all passing), the code is on GitHub (PR #1 merged, PR #2 open for review), and the written deliverables exist in `semantic_detection/docs/`. Open items are dependencies on other people, not unfinished work: target-leakage checks (partly built: numerical targets only), real quality output for the HR tables (Vinitha), agreement of the contract fields with Sinchana, and approval of the quality penalty values.

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
- Reads Sanjay's profiling output (verified: 40 of 40 profiled HR columns match the report from the real data) and Vinitha's quality output (rules `NULL_CHECK`, `DUP_ROW`, `INVALID_RANGE`, `OUTLIER_IQR`; Warning and Blocking).
- One entry point (`run_detection.py`) gives, per dataset: target, problem type, confidence, evidence, alternatives, warnings, ranked candidates, recommended and approved feature columns, a role and preprocessing hint for every column, target statistics, dataset characteristics and validation warnings, and the leakage-check status.
- Tested on HR data and on healthcare, banking, telecom, education and retail data, plus anonymous column names and an empty column. Nothing is hard-coded to HR.

Size: about 2,800 lines of code, 209 test cases, 3 documents.

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

Test count: 117 (Mon night) to 209 (today).

## 5. Open items and dependencies (not unfinished work)

| Item | Status | Who |
|---|---|---|
| Target-leakage checks | **Partly implemented.** Uses Sanjay's correlations; flags (does not remove) columns with correlation of at least 0.80 with a numerical target. Categorical targets, derived columns and time-based leakage are not covered | Meshak to approve thresholds |
| Real quality output for the HumanResources tables | Not received. The sample sent was for another dataset and contradicts Sanjay's profile (JobTitle missing values, duplicate rows) | Vinitha |
| Contract fields for preprocessing | Waiting for Sinchana's reply; interface not frozen | Sinchana, Sumanth, Meshak |
| Quality penalty values (Medium x0.85, High x0.6, Blocking x0) | Not in the SRS; configurable proposed defaults, waiting for approval | Meshak |
| HR demo business objective | `VacationHours` discussed as a possible target; final objective needs project-owner confirmation | Meshak, project owner |
| Review and merge of PR #2 | Open, review requested | Meshak |
| Where and how the user approves feature columns in the application | Open question | Meshak, Sumanth |
| Time-series gaps | Cannot be found from the profile; the field says so | Design limit |

## 6. Proposed follow-up tickets

1. Extend leakage checks beyond numerical targets if profiling can provide more (for example categorical association).
2. Freeze the output contract after Sinchana's and Sumanth's sign-off; add a versioned schema file and a validation test.
3. Add value-level checks (time-series gaps, full class distributions) if the profiling module can supply them.
4. Replace the proposed quality penalties with the approved values and document them.
5. Add the user-approval step for feature columns and the business-goal input to the application interface.
