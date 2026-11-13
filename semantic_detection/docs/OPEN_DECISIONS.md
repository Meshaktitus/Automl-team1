# Open decisions and pending items

Owner: Samarth. Date: Fri 6 Nov 2026. Nothing below is approved. The module is **not** marked "fully integration-ready": the cross-module contracts and the end-to-end workflow are not verified (section 2).

## 1. Decisions

| # | Decision | What is open | Needed from | Effect until decided |
|---|---|---|---|---|
| D1 | Goal that names a column | A goal such as "Forecast units sold" does not pick that column as target. Proposed: match goal words to column names | Lead (rule approval) | User must override the target |
| D2 | Anomaly detection and recommendation without a goal | Never suggested without a goal; ratings table gets `review_required`. Proposed: detect user + item + rating shape | Lead; AutoML does not support these types yet | User gives a goal or a type |
| D3 | Leakage threshold tuning | `area_sqft` against house price (0.99) is flagged although legitimate. Thresholds 0.80 / 0.95 are Proposed | Project Management Team | An extra warning; nothing is removed |
| D6 | Multilabel classification and dimensionality reduction | SRS 9.1 and 9.7 list them; the module returns only the eight values in contract 12.3 | Lead / SRS owner | Nearest type or `review_required` |
| D8 | Phone numbers read from a profile | Labelled `text` instead of `phone` (43 of 44 labels on profile-built input) | Lead (rule); Sanjay (pattern flag) | Contact column treated as text |
| 4 | Defaults in general | Quality penalties, missing-share thresholds (20% / 80%), mixed-type rule, ambiguity rule | Meshak | Proposed defaults stay |
| 5 | **HR business objective and target confirmation** | The HR tables have no outcome-like column, so no target is suggested. `VacationHours` (regression) is only an example used in tests and demos | Meshak / HR | The HR run stays `review_required` until the user confirms a target and problem type |
| 6 | **Forecasting scope** | Forecasting is detected, and needs a time axis, but AutoML does not train it (D4). Is it in scope for this release, and which time column rules apply? | Meshak, Sumanth | Shown as a type; training stays disabled |
| 7 | Quality report format | Rule IDs and severity labels differ between Vinitha's two reports; list in `QUALITY_REPORT_CONTRACT.md` section 5 | Vinitha | `Warning / Audit` is read as a warning |

## 2. Integration items still open

| Item | State |
|---|---|
| Sinchana's service uses my output | Not yet. It reads `target`, `preprocessing_options`, `profiling_metadata`, `quality_findings`; it does not read `approved_feature_columns`, `column_roles`, `preprocessing_actions`, sensitive flags or `leakage_suspect`. Details in `PREPROCESSING_ROLE_MAPPING.md` section 4 |
| Sinchana confirms the mapping table | Sent 5 Nov, no reply |
| Sumanth confirms field list (12.1) | Pending |
| Team 2 API and UI contract | Pending (questions B1 to B8) |
| Real profiler output for the 7 fixtures | Pending (Sanjay) |
| Vinitha quality JSON for the 5 other HR tables and the fixtures | Pending |
| End-to-end run: profile -> quality -> semantic -> preprocessing -> AutoML | **Not done** |
