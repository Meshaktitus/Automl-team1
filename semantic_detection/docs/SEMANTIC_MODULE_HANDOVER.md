# Module handover: Semantic Understanding, Target Detection and Problem Classification

Owner: Samarth (Team 1). Date: Fri 6 Nov 2026 (sprint closure). Status: **Proposed — Pending Review**. Code and evidence: pull request #3 (Meshaktitus/Automl-team1, branch `samarth-leakage-check`, folder `semantic_detection/`).

## 1. What the module does

It reads the profiling output (Sanjay) and the quality report (Vinitha), never the raw data, and recommends: the meaning of each column (12 semantic types plus a sensitive flag), the candidate target columns (ranked), the problem type, and the feature columns with a role and fixed `preprocessing_actions` per column. The user confirms target, problem type and features on one review screen before any training. The module does not train models and does not choose the algorithm; that belongs to model recommendation (Sumanth).

## 2. Inputs and outputs

| | File | Status |
|---|---|---|
| In | Profiling response (`profiling_response.schema.json`, v1.0-draft; no changes needed, confirmed with Sanjay 4 Nov) | Proposed |
| In | Quality report JSON (Vinitha) | Proposed |
| In | Goal, chosen target, problem type, approved features (`review_decisions.schema.json`) | Proposed |
| Out | Result per dataset (`handoff_result.schema.json`, contract `docs/HANDOFF_CONTRACT.md`, sections 12 to 14) | Proposed |

A missing, incomplete or failed profile gives a `review_required` result with a message; a failed quality report lets the run continue with a warning.

## 3. How to run and test

- Run: `python run_detection.py --profiles <folder with *.profile.json> --quality <quality report .json> --output <result .json>` (options in `README.md`).
- Test: `python -m pytest -q` gives **377 passed**. Evidence: `docs/TEST_EXECUTION_EVIDENCE.txt`, `docs/TEST_REPORT.md`, `docs/MODULE_COVERAGE_REPORT.md`, `docs/SEMANTIC_VALIDATION_RESULTS.md`.

## 4. Acceptance criteria (plan section 4.3)

All eight are covered; evidence per criterion is in `docs/MODULE_COVERAGE_REPORT.md`, section 2. A live walk-through is in `demo_acceptance.py` (local demo script, not in the repository).

## 5. Test data: what is real and what is mock

- **Real:** the 6 HR tables, with Sanjay's profile output and Vinitha's quality report.
- **Mock (synthetic):** the 7 fixtures from `make_synthetic_datasets.py`. Their profiles are built by a test helper (`tests/test_thursday_regression.py`), not by Sanjay's profiler. The HR tables have no outcome column, so `VacationHours` is only a provisional demo target.

## 6. Known limitations and unresolved defects

Severity and owner are proposals for the lead to confirm. Full detail: `docs/DEFECT_REGISTER.md`.

| # | Priority | Summary | Owner | Needs |
|---|---|---|---|---|
| D1 | Medium | A goal that names a column does not select it as the target | Samarth | Rule approval (lead) |
| D2 | Low | Anomaly detection and recommendation are only suggested with a goal | Samarth | Rule approval (lead); AutoML support |
| D3 | Low | A normal feature can be flagged as a possible leak | Samarth | Thresholds approved (Project Management Team) |
| D4 | Dependency | AutoML supports binary, multiclass and regression only | Sumanth | n/a |
| D5 | Dependency | Full run through preprocessing and AutoML not done | Samarth, Sinchana, Sumanth | Confirmed interfaces |
| D6 | Low | Multilabel classification and dimensionality reduction not detected | Samarth | Decision (lead) |
| D8 | Low | Phone numbers in a unique-value column read as `text` when input is a profile (43 of 44 labels; 44 of 44 on raw data) | Samarth | Rule approval, or a pattern flag from Sanjay |

Other limits: the leakage check covers numerical pairs only (straight-line correlation); time-series gaps cannot be found from a profile. Fixed this week: D7 (compact numeric ranges wrongly labelled identifiers).

## 7. Integration status

| Team | Item | State |
|---|---|---|
| Sanjay (profiling) | Contract v1.0-draft | Checked, no changes needed; real profiles for the 7 fixtures requested |
| Vinitha (quality) | Quality JSON for the 7 fixtures; approval of two assumptions | Pending |
| Sinchana (preprocessing) | Uses confirmed target, `approved_feature_columns`, `preprocessing_actions`, `leakage_suspect`; role mapping in `docs/PREPROCESSING_ROLE_MAPPING.md` | Agreed in principle; her review of the mapping pending |
| Sumanth (model recommendation) | Check of the mandatory result fields (contract 12.1) | Pending |
| Team 2 (Ajay, Vinay) | Payload for target and problem type (samples ready) | Not requested yet; API on hold |

## 8. Proposed next-sprint backlog (for the lead to confirm)

| # | Item | Owner | Acceptance criterion |
|---|---|---|---|
| B1 | Fix D1: goal wording that names a column selects it | Samarth | Tests show the named column is chosen and the full suite still passes; rule approved first |
| B2 | Fix D8: apply value patterns to the values the profile lists | Samarth (Sanjay for a pattern flag) | `contact` reads as `phone` from the profile; 44 of 44 on profile-built input; no regressions |
| B3 | Freeze contract v1.0 with a versioned schema and a validation test | Samarth | Sumanth and Sinchana confirmations recorded; the schema is versioned |
| B4 | Full run with real preprocessing and AutoML outputs | Samarth, Sinchana, Sumanth | One dataset per supported problem type (binary, multiclass, regression) runs end to end with saved evidence |
| B5 | Backend adapter for the agreed API | Samarth with Ajay and Vinay | Calls and error cases covered by tests, once the API contract exists |
| B6 | Extend the leakage check beyond numerical targets | Samarth | New checks tested; limits updated in `leakage_checks.limits` |
| B7 | Replace Proposed defaults with approved values | Samarth | Approved values recorded and tests updated |
| B8 | Decide D2 and D6 | Lead | Decision recorded; tests added for what is accepted |
