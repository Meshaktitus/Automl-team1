# Defect register: Semantic Understanding, Target Detection and Problem Classification

Owner: Samarth (Team 1). Date: Fri 30 Oct 2026 (sprint closure); updated Thu 5 Nov 2026 (D7 added). Severity is my proposal, to be reviewed. Status: **Proposed — Pending Review**.
Live evidence: `python demo_part4.py`. Other open cases: `docs/TEST_REPORT.md` section 4.

| # | Severity | Problem (evidence) | Impact | Proposed improvement | Depends on |
|---|---|---|---|---|---|
| D1 | Medium | A goal that names a column does not pick that column as the target. Sales data with goal "Forecast units sold next month" suggests `revenue`; ambiguous data with goal "Predict status" suggests no target | Wrong or missing suggestion; the user must override | Match goal words to column names and prefer that candidate | Own module; rule needs approval (lead) |
| D2 | Low | With no goal, `anomaly_detection` and `recommendation` are never suggested. The ratings table (user, item, rating) gets `review_required` with no alternative. Sales data gets `regression` with `forecasting` only as an alternative | The user must give a goal or a type | Detect a user + item + rating shape for recommendation | Rule approval (lead); AutoML does not support these types yet |
| D3 | Low | A normal feature is flagged as a possible leak (`area_sqft` against house price, correlation 0.99) | Extra warning. A flag only; nothing is removed | Tune thresholds; add a "may be legitimate" hint | Thresholds are Proposed until the Project Management Team confirms |
| D4 | High (dependency) | AutoML covers only binary classification, multiclass classification and regression | For forecasting, clustering, anomaly detection and recommendation the type is shown but training is disabled (accepted by the lead, 30 Oct) | None needed in this module | AutoML team |
| D6 | Low | SRS section 9 also lists multilabel classification (9.1) and dimensionality reduction (9.7). This module does not detect them and returns only the eight values in contract 12.3 | A dataset of that kind gets the nearest type or `review_required` | Decide with the lead whether to add them as problem types | Lead / SRS owner; AutoML does not cover them either |
| D5 | High (dependency) | The end-to-end run through preprocessing and AutoML was not done | The integrated prototype covers this stage only | Run it after their fields are confirmed | Preprocessing, AutoML, backend |
| D7 | Medium (fixed 5 Nov) | A numeric column with a compact whole-number range was labelled `identifier` when read from a profile. `hour_of_day` (values 0 to 23, 1000 rows) and a month column (1 to 12) were affected. Cause: the profile path rebuilds each column from its distinct values only, so the "unique consecutive whole numbers" rule always fired | Time and calendar columns were dropped from the recommended features as identifiers | Repeat a value in the rebuilt column whenever the profile says values repeat (`unique_count` below the non-null count). Fixed in `profiling_integration.py` | Fixed; retested by `test_thursday_regression.py` (2 tests failed before the fix, all pass after) |

Test results behind this register (`demo_part1.py` to `demo_part3.py`): 44 of 44 semantic labels match the expected labels on the 7 synthetic datasets (expected labels written from the dataset design); 6 of 7 target and problem-type cases match (the one that differs is D1); overrides always win; bad overrides are kept with a warning; ambiguous data is never guessed.

Nothing here is hidden or marked complete.
