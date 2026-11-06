# Semantic validation results: Thursday 5 Nov 2026

Module: Semantic Understanding, Target Detection and Problem Classification. Owner: Samarth (Team 1). Status: **Proposed — Pending Review**.
Tests: **346 passed, 0 failed** (`python -m pytest`). Commits on pull request #3: `fd21ac8`, `48926ca`, and the commit that adds this document.

## 1. How the checks were run

- The 7 synthetic fixtures (`make_synthetic_datasets.py`) were turned into profiles in the shape Sanjay's profiler returns, by a helper inside `tests/test_thursday_regression.py`. These are **test-built profiles, not output of Sanjay's profiler**. Real profiler output for the fixtures has not been received, so the same checks should be repeated on it when available.
- The 6 HR tables were checked with Sanjay's real profile output (`profiles_new/`) and Vinitha's real quality report (`test_integration_day3.py`).
- Each fixture was run without a goal and, where it makes sense, with a plain-words goal.

## 2. Results per fixture (no goal)

| Fixture | Target | Problem type | Expected | Result |
|---|---|---|---|---|
| churn_classification | `churn` | binary_classification | same | Pass |
| house_price_regression | `price` | regression | same | Pass |
| sales_forecasting | `revenue` | regression | forecasting needs a goal (D1/D2 area) | Pass as designed |
| customer_segments_clustering | none | review_required | clustering needs a goal (D2 area) | Pass as designed |
| transactions_anomaly | none | review_required | anomaly needs a goal (D2) | Pass as designed |
| ratings_recommendation | none | review_required | recommendation needs a goal (D2) | Pass as designed |
| ambiguous_targets | none | review_required | human confirmation | Pass |

With a goal: churn gives binary_classification (`churn`), sales gives forecasting (`revenue`), segments give clustering, transactions give anomaly_detection, ratings give recommendation. All pass.

## 3. Checks requested in the sprint plan

| Check | Result |
|---|---|
| Semantic detection across all fixture types | 44 of 44 labels on the raw data; **43 of 44 on profile-built input** (D8: `contact` phone numbers labelled `text`) |
| Identifier and date detection | Pass for `*_id` columns, `signup_date`, `date`, `rated_on`; **D7 found and fixed** (see section 5) |
| Target detection with several candidate columns | Pass; ranked candidates are returned, the top one is not forced |
| Classification and regression identification | Pass (churn, house price) |
| Low-confidence and ambiguous cases | Pass; no target is chosen, `needs_confirmation` is true |
| Identifier-like columns recommended as targets | None, on all 7 fixtures (test per fixture) |
| Confidence and evidence fields | Present on every column and every result (test per fixture) |

## 4. Data leakage validation

| Fixture | Leakage suspects found | Kept in the output? |
|---|---|---|
| house_price_regression (target `price`) | `area_sqft`, correlation +0.99, level strong | Yes, flagged only (`leakage_suspect`) |
| sales_forecasting (target `revenue`) | `units_sold`, correlation +1.00, level strong | Yes, flagged only |
| churn_classification (target `churn`) | none | n/a |

Known limits (also in the result field `leakage_checks.limits`): numerical column pairs only, straight-line relationships only; categorical targets, derived columns and time-based leakage are not detected. A flag can be a false alarm (D3). Thresholds 0.80 and 0.95 are Proposed.

This is the leakage check of **this module** (a column too close to the target). Train/test leakage during preprocessing belongs to Sinchana's module.

## 5. Incorrect inferences found and what was done

| # | Finding | Action | Retest |
|---|---|---|---|
| D8 | Phone numbers in a unique-value column are labelled `text` when read from a profile (only 10 values are in the profile) | Open; proposed fix needs approval | n/a |
| D7 | Compact whole-number columns (`hour_of_day` 0 to 23, month 1 to 12) were labelled `identifier` when read from a profile | **Fixed** in `profiling_integration.py` | 2 tests failed on the old code, all pass now; a truly unique consecutive column is still an identifier |
| D1 | A goal naming a column does not choose it as the target | Open; rule needs approval | n/a |
| D2 | Anomaly and recommendation need a goal; no shape rule | Open; rule needs approval | n/a |
| D3 | Normal feature can be flagged as a leak | Open; thresholds need approval | n/a |
| D6 | Multilabel and dimensionality reduction not detected | Open; decision needed | n/a |

## 6. Ambiguous-case handling

Behaviour verified: no target is picked, `needs_confirmation` is true, and ranked candidates are returned. **Improvement made on Thursday:** when no target can be chosen, a warning now lists the top three candidate columns with their problem types (for example "Columns the user can pick from as the target: SalariedFlag (binary_classification), VacationHours (regression), SickLeaveHours (regression)"), so the review screen can show a shortlist. Tests: `test_ambiguous_result_lists_columns_the_user_can_pick`, `test_confirmed_target_has_no_pick_list`. Two samples and one contract example were regenerated to match.

## 7. Open points

- Real profiler output for the 7 synthetic fixtures (Sanjay) to repeat section 2.
- D1, D2, D3, D6 decisions (lead, Project Management Team).
- Full run through preprocessing and AutoML (dependency).
