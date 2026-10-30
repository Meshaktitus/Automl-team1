# Integration requirements: Semantic Understanding, Target Detection and Problem Classification

**Document status: Proposed — Pending Review.** Not finalized. Revised 29 Oct 2026 after Meshak's review (5 points, see section 10).

Owner: Samarth (Team 1). Written Thu 29 Oct 2026 for Team 2 (Backend), Team 3 (Frontend), Sinchana (preprocessing) and Sumanth (AutoML).

**Status labels used below**
- **Finalized**: agreed by the people who own both sides.
- **Proposed**: built and tested on my side, but not yet confirmed by the team that consumes it or approved as a requirement.
- **Pending**: needs a decision or an answer. The owner is named.

Everything this module returns is marked `Proposed, pending verification` until a person confirms it. API work stays pending until Team 2 confirms the backend contract. Until then the module runs as a Python function or a command line that writes one JSON file per run.

## 1. What this stage does (one paragraph)

It reads the profiling JSON (Sanjay) and the data-quality JSON (Vinitha) for each dataset. It proposes what each column means, which column could be the target, which problem type fits (binary classification, multiclass classification, regression, forecasting, clustering, anomaly detection, recommendation, or `review_required`; exact values in section 3b), which columns are usable as features, and what to warn about. It never reads the raw data. It never decides alone: the user confirms the target and the features before training.

## 2. Inputs

| Input | Source | Format | Status |
|---|---|---|---|
| Profiling result, one per dataset | Sanjay (profiling module) | JSON, `schema_version` `1.0-draft`: `dataset_reference`, `dataset`, `columns[]`, optional `correlations[]`, optional `class_distribution` | **Proposed** (draft contract; `class_distribution` appears only when the profiling request includes `options.target_column`) |
| Quality report for all datasets | Vinitha (quality engine) | JSON list `[{dataset, total_rows, issues[{rule_id, severity, affected_column, affected_rows, recommended_action}]}]`; rule IDs NULL_CHECK, DUP_ROW, INVALID_RANGE, OUTLIER_IQR; severities Info, Warning, Error, Blocking | **Proposed** (module owners agree; backend not yet confirmed) |
| Business goal (optional) | User, through the frontend | Plain text, for example "forecast units sold" | **Proposed** |
| Target chosen by the user (optional) | User, through the frontend | `{dataset_id: column}` | **Proposed** |
| Problem type chosen by the user (optional) | User | One of the supported problem types | **Proposed** |
| Approved features (optional) | User, through the frontend | List of column names | **Proposed** (the approval step itself is **Pending**, see section 6) |
| Settings (optional) | Project owner | Leakage thresholds, quality penalties | **Proposed defaults**, configurable, not approved requirements |

**Key for matching datasets: `dataset_id`** (Sanjay: `dataset_reference.name` is whatever the caller sends, so it is not guaranteed). Quality results and user choices may use `dataset_id` or the name; capitals and a file ending such as `.xlsx` are ignored.

## 3. Outputs

One result per dataset, in a list. The machine-readable format is `semantic_detection/handoff_result.schema.json` (JSON Schema 2020-12), checked by automatic tests. Field meanings are in `docs/HANDOFF_CONTRACT.md`, section 2. Examples are in `semantic_detection/samples/`.

Most important fields for the other teams:

| Field | Use |
|---|---|
| `dataset_id` | The key |
| `target`, `target_source`, `target_confirmed` | Suggested or chosen target. `target_confirmed` is true only when the user chose it |
| `problem_type`, `confidence`, `source`, `evidence`, `alternatives` | The recommendation and why. `confidence` is a rule-based score, not a probability |
| `needs_confirmation` | true = a human must confirm before training. It stays true until the **problem type** is confirmed (the user overrides the problem type, or gives a business goal that fits the data). Choosing a target alone does not clear it |
| `candidates[]` | Up to 5 ranked alternative targets, with score, confidence level, priority and quality notes |
| `feature_columns`, `recommended_feature_columns`, `approved_feature_columns`, `features_status` | Features: possible, recommended, user-approved (null until approved) |
| `column_roles[]` | Role and preprocessing hint for every column (for Sinchana) |
| `leakage_checks` | Suspect columns with a flag level. A flag is not proof |
| `warnings` | Show to the user |
| `status` | Always `Proposed, pending verification` |

Rules for any consumer (full list in the contract, sections 7 and 12.2; reference code `training_rules.py`, tests `test_training_rules.py`). Proposed:

- **Never** start training while `needs_confirmation` is true (the problem type is not confirmed), or while the features are not approved.
- **Types that need a target** (`binary_classification`, `multiclass_classification`, `regression`, `forecasting`): also require `target_confirmed` true. `forecasting` also needs a date column with `time_axis` true.
- **Types that need no target** (`clustering`, `anomaly_detection`, `recommendation`): `target_confirmed` is not required, because there may be no target.
- `review_required` is never trainable. Ask the user for the business objective and the target (or the problem type), then run the module again.
- Train only on `approved_feature_columns`. Profiling and data-quality analysis are allowed at any time.

## 3b. Supported problem types (one list)

These eight lowercase values are the only ones the module returns (`handoff_result.schema.json`, contract section 12.3). This list is the same in this document, the contract and the schema.

| Value | Needs a target to train | Trainable |
|---|---|---|
| `binary_classification` | yes | yes |
| `multiclass_classification` | yes | yes |
| `regression` | yes | yes |
| `forecasting` | yes, plus a date column (`time_axis`) | yes |
| `clustering` | no | yes |
| `anomaly_detection` | no | yes |
| `recommendation` | no | yes |
| `review_required` | not applicable | no |

**AutoML support (Sumanth, 30 Oct):**

| Value | AutoML status |
|---|---|
| `binary_classification`, `multiclass_classification`, `regression` | Covered by the AutoML design. The working prototype mainly demonstrates regression |
| `forecasting`, `clustering` | Planned extensions, not yet supported |
| `anomaly_detection`, `recommendation` | Not confirmed as implemented. Recommendation also needs interaction / user-item data, which this module cannot see |
| `review_required` | Never trained |

This module can still **recommend** a type that AutoML does not support yet. Proposed handling (pending Meshak, Sumanth and the frontend team): show the recommendation, but do not offer training for a type AutoML does not support. The module itself does not change.

## 4. When a person must confirm

See `docs/HANDOFF_CONTRACT.md`, section 11 (table "When a human must confirm before training"). Working decision from Meshak (28 Oct): features stay pending until the user approves them; the exact screen is to be agreed with Team 3.

## 5. Decisions and confirmations needed, by team

### Team 2 (Backend)

| # | Question or decision | Why it matters | Status |
|---|---|---|---|
| B1 | How is the module called: Python function, one JSON file per run, or an API? | Today it is a function and a command line writing one JSON file per run | **Pending** (API on hold until Team 2 confirms the backend contract) |
| B2 | Where do the profiling JSON and the quality JSON come from, and who passes them in? | The module takes file paths or loaded JSON | **Pending** |
| B3 | Will `dataset_id` be the same in the profiling output, the quality output and the user's choices? | It is the matching key | **Pending** (Sanjay confirmed it is the key; Vinitha's JSON still uses the file name, which also matches) |
| B4 | After the user picks a target, will the backend run profiling again with `options.target_column`? | Only then does the profile carry `class_distribution` (Sanjay skips identifiers, text, and targets with more than 20 distinct values) | **Pending** |
| B5 | Where are the result and the user's decisions stored (confirmed target, approved features)? | The module is stateless: it returns the result, and the user's choices come back in as inputs | **Pending** |
| B6 | How should a failed or unreadable profile be reported? | Today that dataset gets a `review_required` result with a warning, and the other datasets continue | **Proposed** |
| B7 | Result schema versioning and error format | Today there is no version field in the result | **Pending** |
| B8 | Where do the proposed thresholds live (leakage 0.80 and 0.95, quality penalties, weak-target 20% and 80%)? | They are configurable settings, not approved requirements | **Pending** |

### Team 3 (Frontend)

| # | Question or decision | Why it matters | Status |
|---|---|---|---|
| F1 | Screen or step where the user confirms the target **and the problem type** (confirming only the target leaves `needs_confirmation` true) | Training must not start while `needs_confirmation` is true | **Working decision (Meshak, 29 Oct 14:31):** one review screen in the Experiment Workspace under Problem Definition and Features (proposed by Team 3). Field mapping below is **Proposed** |
| F2 | Screen or step where the user approves the features | `approved_feature_columns` stays null until then | **Working decision:** same single review screen (see F1). Field mapping **Proposed** |
| F3 | What to show: confidence, evidence, alternative problem types, ranked target candidates | All are in the result | **Proposed** |
| F4 | How to show warnings: leakage suspects, sensitive-column warning (for example Gender as a target), quality-blocked columns | A leakage flag is not proof; the `limits` text says what the check cannot see | **Proposed** |
| F5 | Can the user override the problem type, and enter a business goal? | Both are accepted inputs | **Proposed** |
| F6 | What goes back to the module after the user decides: chosen target, chosen problem type, approved features | These are the optional inputs in section 2 | **Pending** |

### Sinchana (preprocessing) and Sumanth (AutoML)

| # | Question or decision | Owner | Status |
|---|---|---|---|
| C1 | Does preprocessing need anything beyond `column_roles` (role, reason, preprocessing hint), semantic types and privacy flags? | Sinchana | **Answered (29 Oct):** the fields are a good starting point. She asked 4 clarifications; all four are answered in contract section 12 (proposed). She then asked for `scale_numeric`, `extract_date_features` and `group_rare_categories`: added (29 Oct); she is reviewing section 12.1 before confirming |
| C2 | Which output fields are core for the first integration, and which stay optional? | Sumanth, Meshak | **Partly answered (Sumanth, 30 Oct):** AutoML needs the dataset reference, confirmed problem type, target (where applicable), approved feature columns and dataset validation information. He will check the exact mandatory fields in contract 12.1 before confirming. **Pending** |
| C3 | What does AutoML take as input: the target, the problem type, `approved_feature_columns`? How should it treat `target_confirmed` false? | Sumanth | **Answered (Sumanth, 30 Oct): the training rule in contract 12.2 is acceptable to AutoML.** Training only after the validation and approval checks. Supervised: confirmed target, problem type and approved features. Clustering and anomaly detection: no target. Recommendation: no conventional target, but needs interaction / user-item data. `review_required` is never trained. Still Proposed until Meshak approves |
| C4 | Are the problem type names acceptable to AutoML? Exact values: `binary_classification`, `multiclass_classification`, `regression`, `forecasting`, `clustering`, `anomaly_detection`, `recommendation`, `review_required` | Sumanth | **Answered (Sumanth, 30 Oct):** AutoML design covers `binary_classification`, `multiclass_classification` and `regression`. `forecasting` and `clustering` are planned extensions. `anomaly_detection` and `recommendation` are not confirmed as implemented. The working prototype mainly demonstrates regression. The names themselves were not objected to. **Pending:** exact mandatory fields (C2) |
| C5 | Sensitive columns: proposed default is **not recommended until the user approves them** (they stay in `feature_columns`). Confirm this default | Meshak, Sinchana | **Proposed** (contract section 12.5) |

## 5b. Review screen: working decision and proposed field mapping

Working decision (Meshak, 29 Oct 14:31): follow Team 3's single review screen for problem type, target column and feature selection. This module supplies the suggested values. The user reviews, approves or changes them. The approved selections then go to preprocessing and model recommendation. The workflow and the field mapping stay **Proposed** until Team 2 confirms the API contract and Sinchana and Sumanth validate their input requirements.

| User approval on the screen | Field that shows it | Status |
|---|---|---|
| Target confirmed | `target_confirmed` is true | Proposed |
| Problem type confirmed | `needs_confirmation` is false | Proposed |
| Features approved | `features_status` is `approved`, `approved_feature_columns` not null | Proposed |

Training starts only when all three are done. If the user changes the target, the backend runs this module again with the new target, because candidates, statistics, leakage checks and recommended features depend on it (needs B5 from Team 2).

## 6. Feature-approval requirements (pending step)

- The module recommends feature columns and never trains. A person approves them.
- Until approval, `features_status` is `recommended_pending_confirmation` and `approved_feature_columns` is null.
- After approval, the backend or frontend passes the approved list back as `approved_feature_columns` (a dictionary `{dataset_id: [columns]}`, or a plain list when there is one dataset). The name is the same as the result field `approved_feature_columns`, and the result then shows `features_status` `approved`. Columns in the list that are not usable features are dropped with a warning.
- Identifiers, excluded columns and the target are never normal model inputs. A column with a blocking quality issue is not recommended. A leakage suspect is **flagged but still listed**; the person decides.
- **Working decision (29 Oct):** the screen is the single review screen (section 5b). **Pending (Team 2):** who sends the approved list back, and how it is stored (B5).

## 7. Known limitations (documented on purpose)

1. **Target leakage is checked for numerical targets only.** It uses the profile's pairwise correlations (Pearson, straight-line relationships). Categorical targets, derived columns and time-based leakage are not detected. A suspect is a flag for a person; correlation alone is not proof. Datasets with fewer than two numeric columns have no correlations, so the check reports `pending_integration`.
2. Everything is computed from the profile. The module cannot see raw values, so it cannot check gaps in a time series.
3. The HR tables have no outcome column. `Employee.VacationHours` is a provisional demo target; the final business objective needs the project owner.
4. All confidence values and thresholds (including leakage 0.80 and 0.95, quality penalties, target missing 20% and 80%) are **proposed defaults**, not approved requirements.
5. The module is a prototype. Forecasting and clustering recommendations are tested on example data.

## 8. Proposed versus finalized

| Item | Status |
|---|---|
| Output field list and schema (`handoff_result.schema.json`) | Proposed (draft contract) |
| Profiling JSON contract 1.0-draft | Proposed (draft) |
| Quality JSON format, rule IDs and severities | Proposed (module owners agree) |
| `dataset_id` as the key | Proposed (confirmed by Sanjay, not yet by the backend) |
| Features pending until the user approves them | Working decision (Meshak, 28 Oct) |
| One JSON file per run for now, API later | Working decision (Meshak, 28 Oct); API pending Team 2 |
| `VacationHours` as the demo target | Working decision (provisional) |
| Thresholds, penalties, confidence values | Proposed defaults, not approved |
| Preprocessing actions (fixed values) and mandatory versus optional fields | Proposed (contract section 12), pending Sumanth and Sinchana |
| Sensitive features held back until approved | Proposed default (29 Oct), pending Meshak and Sinchana |
| Single review screen for problem type, target and features | Working decision (Meshak, 29 Oct 14:31); field mapping Proposed (section 5b) |
| API and backend contract | Pending (Team 2) |

Nothing in this document is finalized yet.

## 9. Blockers, owners and requested times

I cannot promise another team's time. The times in the last column are the times I am **asking for**, so the integration sprint ends on Fri 30 Oct. Each owner should confirm or change them.

| # | Blocker | Owner | Requested by |
|---|---|---|---|
| 1 | Backend contract: B1 to B8 above | Team 2 | Today, 29 Oct, end of day (at least B1, B3, B4) |
| 2 | Review screen details: F3 to F6 (F1 and F2 are a working decision, section 5b) | Team 3 | Today, 29 Oct, end of day |
| 3 | Preprocessing fields: C1 | Sinchana | Today, 29 Oct |
| 4 | AutoML input and field priority: C2 to C4. C3 and C4 answered 30 Oct. Waiting for his check of contract 12.1 (C2) | Sumanth | Today, 30 Oct |
| 5 | Approval of the proposed defaults (thresholds, confidence values) | Meshak | By Fri 30 Oct (sprint closure) |
| 6 | Final business objective and target for the HR demo | Project owner, through Meshak | By Fri 30 Oct |
| 7 | Reviews and merge of PR #2 and PR #3 into `main` | Meshak, Sumanth, Sinchana | Today, 29 Oct |
| 8 | Quality results: two assumptions (pay band 6.50 to 125.00 per hour for `Rate`; age at hire 18 to 65). Vinitha answered on 29 Oct that the band is a project baseline wage assumption. **They stay Pending** until the project owner approves them | Vinitha, project owner | Today, 29 Oct |

My own items (prototype integration, 281 tests, schema, documents) are done and pushed. I continue prototype integration wherever the interfaces are compatible, and I update this document when anything is decided.

## 10. Meshak's review (29 Oct) and how each point was handled

Document stays **Proposed — Pending Review**. Resolutions are Proposed until reviewed.

| # | Point | Resolution | Status |
|---|---|---|---|
| 1 | Training eligibility for problem types without a target | Section 3 now follows contract 12.2: `target_confirmed` is required only for types that need a target. Clustering, anomaly detection and recommendation need only a confirmed problem type and approved features. Code: `training_rules.py`; tests: `test_training_rules.py` (includes clustering) | Proposed; pending Sumanth and Meshak |
| 2 | Two different lists of problem types | One list of eight values in section 3b, same as contract 12.3 and the schema. The first paragraph is corrected. Sumanth answered on 30 Oct which types AutoML covers (section 3b): three supported by design, two planned, two not confirmed | Answered; exact mandatory fields still Pending (Sumanth) |
| 3 | Sensitive features, field names, consistency | Sensitive features are not in `recommended_feature_columns` until the user approves them explicitly (`approved_feature_columns`). One name for approved features everywhere: `approved_feature_columns` (result field, function argument, review-screen payload, schema, documents). The four examples in the contract were regenerated and are tested | Proposed default; pending Meshak and Sinchana |
| 4 | Schema and sample validation, tests | Every full sample output is validated against `handoff_result.schema.json` by `test_samples_and_examples.py`, with the mandatory preprocessing fields and `preprocessing_actions` checked on every column. Eligibility rules are tested in `test_training_rules.py`. 281 tests pass (`docs/TEST_EXECUTION_EVIDENCE.txt`) | Done |
| 5 | Pending dependencies | Kept as Pending, nothing marked confirmed: Team 2 API contract (B1 to B8); Team 3 UI mapping (section 5b, F3 to F6); Sinchana's review of contract 12.1; Sumanth's required fields and problem types (C2 to C4); Vinitha's two assumptions (blocker 8) | Pending |

PR status: PR #1 merged. PR #2 (`samarth-contract-rev2`) and PR #3 (`samarth-leakage-check`) are open, waiting for review. Do not merge PR #2 until Sinchana has reviewed 12.1.

