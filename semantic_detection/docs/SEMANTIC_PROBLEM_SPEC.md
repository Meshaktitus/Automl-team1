# Semantic Understanding, Target Detection and Problem Classification

Owner: Samarth (Team 1). Status as of Mon 26 Oct 2026: **Implemented and tested as a prototype; proposed, pending Team 1 review.** Nothing here is final until Meshak and the dependent owners agree it.

Modules: `semantic_rules.py`, `analyze_semantics.py`, `target_suggestions.py`, `problem_detection.py`, `quality_integration.py`, `profiling_integration.py`, `run_detection.py` (single entry point), `leakage_checks.py` (correlation-based leakage flags), `handoff_result.schema.json` (output schema), `handoff_details.py` (target statistics, preprocessing hints, time info, validation warnings), `make_synthetic_datasets.py`. Tests: 251 test cases, all passing. Output contract for the AutoML handoff (revision 3, after Sumanth's review; to be agreed with Sinchana and the reviewer): `docs/HANDOFF_CONTRACT.md`.

---

## 1. Semantic type catalogue

12 types. Names are split into whole words (`BusinessEntityID` -> business, entity, id), so "Manager" is not read as "age" and "Overtime" is not read as "time". Checks run in this order and the first match wins.

| Type | Main signals (name word, or values) | Typical confidence |
|---|---|---|
| email | name has email/mail; or >=80% of values match an email pattern | 0.95-0.99 |
| percentage | name has percent/pct; or >=80% of values contain `%` | 0.90-0.95 |
| date | datetime dtype; name has date/datetime/timestamp/dob or ends in "date"; or >=80% of values match a date pattern | 0.90-0.99 |
| time | name has "time"; time-of-day objects; or >=80% of values look like HH:MM | 0.90-0.95 |
| phone | name has phone/mobile/telephone/fax/cell; or >=80% of values look like phone numbers | 0.85-0.95 |
| identifier | name has id/key/guid/uuid or ends in "number"; unique consecutive whole numbers | 0.65-0.99 |
| boolean_flag | True/False; only 0 and 1; only yes/no style text | 0.85-0.95 |
| categorical | name matches a known category word (gender, status, title, level, group ...); few distinct values | 0.55-0.95 |
| financial_amount | currency symbols in values; name has salary/rate/price/cost/amount ... | 0.90 |
| numerical_measure | name has hours/age/count/score/rating/weight ... ; numeric fallback | 0.60-0.90 |
| text | name has resume/description/comment/notes ...; long strings or markup | 0.50-0.95 |
| unknown | no non-null values and no name rule matched | 0.30-0.50 |

Every result also carries `evidence` (why), `alternatives` (other possible types) and a `sensitive` flag (email, phone, birth, gender, marital, salary, national ID, resume ...). Status is always "Proposed, pending verification".

**Ambiguous cases and how they are handled**
- A whole-number column with few values and an inconclusive name (e.g. `PayFrequency` 1/2) -> categorical, with numerical_measure as the alternative.
- `rating` (1-5) is a numeric measure, not a category. This was a bug and is fixed (see section 8).
- A generic `Name` column -> categorical at only 0.70 with text and identifier as alternatives.
- A phone-like value that is also a date or a decimal is not read as a phone.

## 2. Output schema

**Semantic report** (one row per column): `dataset, column, data_type, row_count, non_null_count, missing_pct, unique_values, semantic_type, confidence, evidence, alternatives, sensitive, status`.

**Target suggestions** (one row per candidate): `dataset, rank, candidate_target, semantic_type, suggested_problem_type, score, confidence_level, priority, reason, alternative_problem_types, warnings, status`. With quality applied, `quality_issues` is added.

**Problem-type result**: `problem_type, confidence, source, needs_confirmation, evidence, alternatives[{problem_type, reason}], warnings, status`. `source` is `user_override`, `business_goal` or `data_rules`.

## 3. Target-ranking design

Excluded from candidates: audit columns (modified/created/updated/rowguid); types identifier, text, email, phone, time, date, unknown; constant columns; columns >=80% missing. A user-selected column is always kept, with a warning.

Score (0-100):

`score = base(type) x cardinality factor x (1 - missing%) x sensitivity factor`, then +0.15 if the name looks like an outcome (churn, price, default, attrition ...), +0.05 if it is the last column.

- Base: boolean_flag 0.80, financial_amount 0.75, categorical/numerical/percentage 0.70.
- Cardinality (classification): <=2 values 1.0, <=10 0.9, <=20 0.65, more 0.35. Regression: <=5 values 0.5, <=10 0.75, more 1.0.
- Sensitive column: x0.5 with a fairness/privacy warning.

Priority: "Top suggestion" only when a column name looks like an outcome; up to 3 "Alternative"; everything else "Candidate"; "User-selected" always ranks first. Confidence: High if score >=75 and outcome-like name, Medium if >=50, otherwise Low. If no column looks like an outcome, every row says: confirm the business objective.

## 4. Problem-type matrix and decision rules

Supported: binary_classification, multiclass_classification, regression, forecasting, clustering, anomaly_detection, recommendation.

| Type | Needs (feasibility check) |
|---|---|
| binary_classification | target with 2 values or a flag |
| multiclass_classification | categorical target (warns above 20 classes) |
| regression | numeric target (warns and offers classification if <=10 distinct values) |
| forecasting | numeric target and a usable date column with >=6 distinct dates (birth, hire, start, end, expiry, audit dates are not a time axis) |
| clustering | no target; >=3 usable feature columns |
| anomaly_detection | >=2 numeric columns |
| recommendation | >=2 identifier columns and >=1 numeric column |

**Precedence:** 1. user override (always wins, confidence 1.0, warns if it may not fit) -> 2. business goal wording ("forecast", "segment", "unusual", "recommend", ...), accepted only if feasible, otherwise a warning that it does not fit -> 3. data rules.

**Data-rule confidence:** classification 0.85 (0.60 above 20 classes); regression 0.80 (0.55 if <=10 values); no target 0.30. A goal that agrees adds +0.10; a goal that disagrees subtracts 0.20. A goal mentioning several task types caps confidence at 0.50. Maximum is 0.95 unless overridden. `needs_confirmation` stays true unless the user overrides or states a goal that fits the data.

## 5. Integration specification

**Profiling (Sanjay, contract 1.0-draft).** `profiling_integration.py` reads `*.profile.json`, rejects failed profiles and other versions, and checks the required column fields (`name, dtype, inferred_type, missing_count, missing_pct, unique_count, likely_identifier`). Because a profile has no raw values, it rebuilds a small stand-in sample from the summary and top values, runs the same rules, and uses `likely_identifier` and `inferred_type: text` as extra evidence. Output is the same report layout as section 2.

**Quality (Vinitha).** `quality_integration.py` accepts the issue list as `detected_issues` or `issues`, a column as `column` or `affected_column`, and a `dataset` on each issue or once at the top of the report. Confirmed by the Data Quality Engine on 27 Oct: rule IDs `NULL_CHECK`, `DUP_ROW`, `INVALID_RANGE`, `OUTLIER_IQR` with severities Warning and Blocking; `DUP_ROW` is table-level (column null); null findings are notes only. The earlier `RULE_*` names and Low/Medium/High labels are still accepted. Severity levels (**the penalty values are not in the SRS; they are configurable proposed defaults until approved**, set through `quality_settings`):

| Level (labels) | Effect on target suggestion | Effect on problem type |
|---|---|---|
| warning (Low, Info, Warning) | note only | note only |
| medium (Medium) | score x0.85 | confidence -0.05 |
| error (High, Error) | score x0.6, confidence Low, loses Top/Alternative label | confidence -0.10, needs confirmation |
| blocking (Blocking) | score x0, "Blocked by quality", ranked last | confidence -0.30, "do not train" warning |

Note only, whatever the severity: rules about nulls (`NULL_CHECK`, `RULE_NULL_*`), duplicate rows, missing, constant, key and reference checks (the ranking already handles missing and constant columns; key and duplicate checks are about the table), and any issue affecting 0 rows. `INVALID_RANGE` at Blocking does block the column; a Blocking finding should make a target ineligible only when it genuinely makes it unsuitable (Meshak, 27 Oct). One issue may name several columns (`A, B` or `A + B`). `affected_rows` may be a number, a count with percentage, or text. A user override is never overridden by quality.

**Single entry point (`run_detection.py`).** One call takes profiles, an optional quality report, an optional business goal and optional user overrides, and returns one result per dataset (target, problem type, confidence, evidence, alternatives, warnings, ranked candidates, semantic columns, recommended and approved feature columns, a role, reason and preprocessing hint for every column, target statistics, dataset characteristics, validation warnings, leakage-check status). A suggested target is never treated as confirmed (`target_confirmed`). `detect_dataset` does one dataset per call. Roles are recommendations with evidence, not decisions. The output fields are defined in `docs/HANDOFF_CONTRACT.md`.

## 6. Baseline checklist (status)

| Item | Status |
|---|---|
| Semantic catalogue (section 1) | Implemented |
| Examples for dates, IDs, emails, percentages, categories, amounts | Implemented, tested |
| Synthetic task datasets: churn (classification), house price (regression), sales (forecasting), customer segments (clustering), transactions (anomaly), ratings (recommendation), ambiguous targets | Implemented |
| Ambiguous-target cases | Implemented, tested |
| Target-leakage checks | **Partly implemented (27 Oct).** Uses Sanjay's `correlations[]`: flags columns with correlation of at least 0.80 (possible) or 0.95 (strong) with a numerical target; flagged columns are kept and warned about, not removed. Thresholds are proposed defaults. Not covered: categorical targets, derived columns, time-based leakage. Status is `pending_integration` when a profile has no correlations |

## 7. Results on the HR data (Employee, EmployeePayHistory)

No column clearly looks like an outcome, and `CurrentFlag` is 1 for all 290 employees (constant, excluded). Every suggestion is therefore Low confidence and needs the project owner to confirm the business objective.

- Employee: SalariedFlag 80.0, VacationHours 70.0, SickLeaveHours 70.0, OrganizationLevel 62.8, MaritalStatus 35.0, Gender 35.0 (sensitive), JobTitle 24.5.
- EmployeePayHistory: Rate 75.0, PayFrequency 70.0.
- Profiling-based and data-based reports agree on all 40 profiled columns (types, unique counts, missing %).

## 8. Test report

251 test cases, 251 passing across semantic rules, target suggestions, problem detection, quality integration, profiling integration, cross-domain datasets (healthcare, banking, telecom, education, retail, anonymous columns, empty column) and the entry point.

**Correct:** HR-style columns; value-based email, phone, percentage, date, time, currency, flags; ranking and exclusions; all 7 problem types on synthetic data; override precedence; goal feasibility; quality severities; profile adapter.

**Incorrect results found during testing and fixed**
1. Words hidden inside other words (Manager read as "age", Overtime as "time") -> whole-word matching.
2. Birth and hire dates offered as a forecasting time axis -> attribute-date words excluded.
3. `rating` (1-5) read as categorical, so a recommendation goal was wrongly rejected -> rating is numeric.
4. An errored column still labelled "Top suggestion" after a quality penalty -> Error now demotes the label.
5. A bad report path was treated as data in one test -> clear error added.
6. Cross-domain tests: `readmitted` and `final_score` got no "Top suggestion" because the outcome-word list lacked them -> words added (readmitted, churned, defaulted, dropout, graduated, passed, failed, final).
7. A null-check finding marked Blocking would have zeroed a column's score -> null and duplicate rules are note-only under both naming styles.
8. The quality loader rejected the engine's latest field names (`issues`, `affected_column`) -> both styles accepted.

**Unresolved**
- Business objective and final target for the HR data: must come from the project owner.
- Quality penalty values above are a proposal and still need Meshak's agreement. Vinitha confirmed the rule IDs, the Warning/Blocking meaning and that null findings are notes only. Real quality output for the HumanResources tables has not been received; her sample was for a different dataset (`hr_employee_attrition_data.csv`) and contained stray text ("[cite: 6]").
- "Top suggestion" needs an outcome-like word in the column name; otherwise the user confirms the target.
- Target-leakage checks are partial: numerical targets only, straight-line correlation only; thresholds are proposed defaults.
- The profile-based report is an approximation; verified on 40 of 40 columns here, to be re-checked on other datasets.
- A mistyped dataset name in the quality tool returns an empty table without a warning.

## 9. Work labels (per plan section 3)

| Work | Label |
|---|---|
| Semantic detector, target ranking, problem-type rules, overrides | Implemented |
| Quality and profiling integration | Implemented |
| Single integrated entry point (profile + quality + semantic + target + problem) | Implemented (done 27 Oct, ahead of the Wed 28 Oct plan) |
| Handoff contract to AutoML (Sumanth) and preprocessing (Sinchana) | Draft revision 3 written (after Meshak's and Sumanth's reviews: feature columns, roles, target statistics, preprocessing hints, defined allowed values); fields still to be agreed with Sinchana, then shared for review before it is frozen |
| Target-leakage checks | Partly implemented: correlation-based flags for numerical targets (see limits) |
| Final target for HR data | Not needed for the application (the user supplies goal and overrides at run time). The HR demo objective needs project-owner confirmation; `VacationHours` has been discussed as a possible target only |
| Code submission method | Blocked (no Git; needs Meshak) |
