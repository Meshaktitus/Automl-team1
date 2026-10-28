# Handoff contract: target, problem type and input columns (1.0-draft, revision 3)

Owner: Samarth. Consumers: Sumanth (AutoML, primary), Sinchana (preprocessing). Reviewer: Meshak.
Status: **implemented and tested as a prototype; proposed, pending Team 1 review.** Revision 3 follows Sumanth's review of revision 2. Fields marked *optional* may be left out or filled later. **The interface is not frozen** until Sinchana and the reviewer have agreed it.

## Changes since revision 2 (after Sumanth's review)
1. Added `target_statistics` (data type, unique count, missing information, class distribution or numerical statistics).
2. Added `target_confirmed`, and split the input columns into `feature_columns` (technically usable), `recommended_feature_columns` and `approved_feature_columns`, with `features_status`.
3. Added to each column role: `data_type`, `unique_values`, `missing_count`, `missing_pct`, `preprocessing_hint`, `needs_privacy_review`, `quality_issue_codes`.
4. Added to each candidate: `quality_issue_codes` and `blocking_reason`.
5. Added to `dataset_characteristics`: `feature_type_counts`, `missing_summary`, `time_info` (date range and estimated frequency) and `validation_warnings`.
6. Defined all allowed values, how `score` works, and the difference between score and confidence (sections 3 and 4).

## 1. How it is called

```python
from run_detection import run_detection, detect_dataset

result = detect_dataset(            # one dataset per call
    "Employee.profile.json",        # profiling response (path or dict), contract 1.0-draft
    quality=None,                   # optional quality report (path or dict)
    goal=None,                      # optional business goal in plain words
    overrides=None,                 # optional {dataset_name: target_column} chosen by the user
    problem_type_override=None,     # optional problem type chosen by the user
    approved_features=None,         # optional columns the user approved for training
    quality_settings=None,          # optional, change the proposed quality penalties
)
# run_detection([...]) takes several profiles and returns a list of the same results
```

Command line: `python run_detection.py --profiles <folder> [--quality file.json] [--goal "..."] [--override DATASET=COLUMN] [--problem-type TYPE]`. Only the profiling output is read, never the raw data. Nothing is specific to one domain.

## 2. Result fields

**Machine-readable schema:** `handoff_result.schema.json` (JSON Schema 2020-12, one result per dataset; `run_detection` returns a list of these). Every real output is checked against it by `test_handoff_schema.py`. If this table and the schema ever disagree, fix both and the test will say which is wrong.

**Core** (always present):

| Field | Type | Meaning |
|---|---|---|
| `dataset` | string | Dataset name from the profile (`dataset_reference.name`, or `dataset_id` when there is no name) |
| `dataset_id` | string or null | `dataset_reference.dataset_id` from the profile. Sanjay: the backend decides `name`, so use `dataset_id` as the key. Quality results and overrides may use either; a file ending such as `.xlsx` and capital letters are ignored when matching |
| `target` | string or null | Suggested or chosen target. null when none can be suggested |
| `target_source` | enum | `user_override`, `top_suggestion` or `none` |
| `target_confirmed` | boolean | true only when the user chose the target. A suggested target is **not** confirmed |
| `problem_type` | enum | See section 3 |
| `confidence` | number 0 to 1 | Confidence in the **problem type** (not the target score). 1.0 only for a user override; otherwise at most 0.95 |
| `source` | enum | What decided the problem type: `user_override`, `business_goal` or `data_rules` |
| `needs_confirmation` | boolean | true = a human must confirm before training |
| `evidence` | list of text | Why this problem type |
| `alternatives` | list of `{problem_type, reason}` | Other types worth considering |
| `warnings` | list of text | Anything the consumer should show or act on |
| `candidates` | list (up to 5) | Ranked target candidates (section 4) |
| `feature_columns` | list | All technically usable input columns (role `feature`), including ones with a blocking quality issue |
| `recommended_feature_columns` | list | `feature_columns` minus columns with a blocking quality issue |
| `approved_feature_columns` | list or null | Columns the user approved for training. null until the user approves |
| `features_status` | enum | `recommended_pending_confirmation` or `approved` |
| `column_roles` | list | A recommended role and reason for every column (section 5) |
| `dataset_characteristics` | object | Dataset facts (section 6) |
| `leakage_checks` | object | `status` (`checked`, `not_checked` or `pending_integration`), `reason`, `thresholds`, `suspects[]` (`column`, `correlation`, `level` possible/strong, `message`) and `limits`. See section 5 |
| `semantic_columns` | list | `column, semantic_type, confidence, sensitive` for every column |
| `status` | text | Always `Proposed, pending verification` (the only value in this version) |

**Optional / task-dependent:** `target_statistics` (null when there is no target), and inside `dataset_characteristics`: `feature_type_counts`, `missing_summary`, `time_info`, `validation_warnings`; and `preprocessing_hint` in each role.

**Which columns does AutoML train on?** `feature_columns` is what is technically possible. `recommended_feature_columns` is what the module suggests. `approved_feature_columns` is what the user has confirmed. While `features_status` is `recommended_pending_confirmation`, use the recommended list only as a proposal. The suggested target is also not confirmed until `target_confirmed` is true.

## 3. Allowed values

| Field | Values |
|---|---|
| `problem_type` | `binary_classification` (two outcomes), `multiclass_classification` (3 or more categories), `regression` (a number), `forecasting` (a number over time, needs a time column), `clustering` (no target; group similar rows), `anomaly_detection` (find unusual rows), `recommendation` (user and item with a rating), `review_required` (nothing can be recommended yet) |
| `source` | `user_override` (the user chose it; always wins), `business_goal` (words in the goal, accepted only if the data fits), `data_rules` (from the target column and data) |
| `target_source` | `user_override`, `top_suggestion` (a column whose name looks like an outcome), `none` |
| `status` | `Proposed, pending verification` |
| `semantic_type` | identifier, email, phone, percentage, date, time, boolean_flag, categorical, financial_amount, numerical_measure, text, unknown |

## 4. Candidates

Fields: `rank, candidate_target, semantic_type, suggested_problem_type, score, confidence_level, priority, warnings, quality_issues, quality_issue_codes, blocking_reason`.

| Field | Values and meaning |
|---|---|
| `priority` | `User-selected`, `Top suggestion` (name looks like an outcome), `Alternative` (up to 3 more outcome-like names), `Candidate`, `Blocked by quality` |
| `confidence_level` | `High`, `Medium`, `Low`, `User-selected` |
| `suggested_problem_type` | `binary_classification`, `multiclass_classification`, `regression`, `review_required` (the type implied by this column alone) |
| `quality_issue_codes` | List of rule IDs reported for this column, for example `["INVALID_RANGE"]` |
| `blocking_reason` | Text such as `INVALID_RANGE: negative charge` when `priority` is `Blocked by quality`; otherwise null |

**How `score` (0 to 100) is calculated:** `base(type) x cardinality factor x (1 - missing share) x sensitivity factor`, then +0.15 if the name looks like an outcome and +0.05 if it is the last column, and the result is scaled to 100.
- Base: boolean_flag 0.80, financial_amount 0.75, categorical, numerical_measure and percentage 0.70.
- Cardinality (classification): 2 values 1.0, up to 10 0.9, up to 20 0.65, more 0.35. Regression: up to 5 values 0.5, up to 10 0.75, more 1.0.
- Sensitive column: x0.5.
- Quality: Medium x0.85, High x0.6, Blocking x0 (proposed defaults, configurable; not in the SRS).

**Score is not confidence.** `score` ranks the *target candidates* against each other. `confidence_level` says how much to trust a candidate (High needs a score of at least 75 and an outcome-like name; Medium at least 50; otherwise Low). `confidence` at the top level is about the **problem type**. A high score does not mean the target is confirmed.

## 5. Column roles

Fields: `column, semantic_type, data_type, role, reason, unique_values, missing_count, missing_pct, sensitive, needs_privacy_review, time_axis, quality_blocked, quality_issues, quality_issue_codes, preprocessing_hint, leakage_suspect, leakage_correlation`. Quality findings with 0 affected rows are treated as a passed check and are not listed.

| Role | Meaning | Use as a normal model input? |
|---|---|---|
| `target` | The suggested or chosen target | **No** |
| `feature` | Recommended model input | Yes |
| `identifier` | ID, key, email or phone | **No** (keep for joining tables) |
| `date` | Date column | Not directly; see below |
| `time` | Time-of-day column | After extracting hour or part of day |
| `text` | Free text | After text processing |
| `excluded` | Audit metadata, constant, almost empty (80% or more missing) or unknown type | **No** |

**Dates.** `time_axis` true: the date can order the data in time, so it is the time index for **forecasting** (and the source of lag features). `time_axis` false: the date describes a person or record (birth date, hire date); for **feature engineering** turn it into age, duration, year or month. Birth, hire, start, end and audit dates are never a time axis.

**`preprocessing_hint`** is a one-line recommendation (impute, encode, scale, date transformation, text processing or drop). It is a suggestion for Sinchana's step, not a decision.

**Data quality is not target leakage.** `quality_issues`, `quality_issue_codes` and `quality_blocked` report data problems (for example an invalid range). `quality_blocked` is true only for a Blocking finding that is not a null, duplicate-row or key finding. Leakage means a column that gives away the target; it is reported separately in `leakage_checks` and on each role as `leakage_suspect` (`possible`, `strong` or null) with `leakage_correlation`.

**Leakage check (added after Sanjay's correlations arrived, 27 Oct).** It compares every column with the chosen target using the profile's `correlations[]`. A column with absolute correlation of at least 0.80 is `possible`, at least 0.95 is `strong`. These two thresholds are proposed defaults, not from the SRS, and can be changed (`leakage_settings`). A flagged column is **not removed**: it stays a feature with a warning, and the user decides. Status `checked` means the target was found in the correlations; `not_checked` means there is no target, or the target is not a numerical column (so it is not in the correlations); `pending_integration` means the profile had no correlations. **Limits:** numerical pairs only, straight-line relationships only; categorical targets, derived columns and time-based leakage are not detected.

**Sensitive columns** have `sensitive` and `needs_privacy_review` true. They need an explicit privacy and fairness review before use.

## 6. Dataset characteristics and target statistics

`dataset_characteristics`: `row_count, column_count, duplicate_row_count, profile_status, feature_column_count, feature_type_counts` (numerical, categorical, boolean, other), `missing_summary` (columns with missing values), `time_columns, time_info, identifier_columns, date_columns, sensitive_columns, excluded_columns, validation_warnings`.

- `time_info` (when there is a time axis): `column, start, end, distinct_dates, estimated_frequency` (daily, weekly, monthly, quarterly, yearly or unknown), `average_spacing_days`, and `gaps`. **Frequency is an estimate from the date range. Gaps cannot be found from the profile**; the field says so.
- `validation_warnings`: no or few usable features, small dataset (under 50 rows), duplicate rows, target with missing values, class imbalance (smallest class under 10%), high-cardinality features (over 50 distinct values), features with blocking quality issues.

`target_statistics`: `column, data_type, semantic_type, unique_count, missing_count, missing_pct, class_distribution, minority_class_pct, numerical_statistics, notes`. Class distribution comes from the profile's top values, or from the mean of a 0/1 column; when the profile lists only the top values, the notes say so and `minority_class_pct` stays null. Numerical statistics are min, max, mean, median and std.

## 7. Rules for the consumer (proposed)

1. If `needs_confirmation` is true or `target_confirmed` is false, do not start training automatically. Show the target, problem type, evidence and alternatives to the user.
2. If `target_source` or `source` is `user_override`, follow it.
3. If `target` is null or `problem_type` is `review_required`, ask the user for the business objective and target.
4. Train on `approved_feature_columns` when it is not null. Otherwise treat `recommended_feature_columns` as a proposal.
5. Never use identifiers, excluded columns or the target as normal model inputs.
6. Do not use a candidate with priority `Blocked by quality`, or a column with `quality_blocked` true, without the user's say-so.
7. Show `warnings`, `validation_warnings` and `leakage_checks.status`. Do not treat leakage as checked unless the status is `checked`, and remember its limits.

## 8. Examples (real outputs of the prototype, shortened)

**A. The user picked the target** (customer churn; `target_confirmed` true).
```json
{
  "dataset": "churn.xlsx",
  "target": "churn",
  "target_source": "user_override",
  "problem_type": "binary_classification",
  "confidence": 0.85,
  "source": "data_rules",
  "needs_confirmation": true,
  "evidence": [
    "Target 'churn' is boolean_flag with 2 distinct values."
  ],
  "alternatives": [],
  "warnings": [],
  "target_confirmed": true,
  "target_statistics": {
    "column": "churn",
    "data_type": "int64",
    "semantic_type": "boolean_flag",
    "unique_count": 2,
    "missing_count": 0,
    "missing_pct": 0.0,
    "class_distribution": null,
    "minority_class_pct": null,
    "numerical_statistics": null,
    "notes": [
      "Class distribution not available from the profile."
    ]
  },
  "candidates": [
    {
      "rank": 1,
      "candidate_target": "churn",
      "semantic_type": "boolean_flag",
      "suggested_problem_type": "binary_classification",
      "score": 100.0,
      "confidence_level": "User-selected",
      "priority": "User-selected",
      "warnings": "Check class balance before training",
      "quality_issue_codes": [],
      "blocking_reason": null
    },
    {
      "rank": 2,
      "candidate_target": "monthly_charges",
      "semantic_type": "numerical_measure",
      "suggested_problem_type": "regression",
      "score": 70.0,
      "confidence_level": "Low",
      "priority": "Candidate",
      "warnings": "",
      "quality_issue_codes": [],
      "blocking_reason": null
    }
  ],
  "dataset_characteristics": {
    "row_count": 100,
    "column_count": 4,
    "duplicate_row_count": 0,
    "profile_status": "success",
    "feature_column_count": 2,
    "feature_type_counts": {
      "numerical": 2,
      "categorical": 0,
      "boolean": 0,
      "other": 0
    },
    "missing_summary": [],
    "time_info": [],
    "time_columns": [],
    "identifier_columns": [
      "customer_id"
    ],
    "date_columns": [],
    "sensitive_columns": [],
    "excluded_columns": [],
    "validation_warnings": []
  },
  "feature_columns": [
    "monthly_charges",
    "tenure_months"
  ],
  "recommended_feature_columns": [
    "monthly_charges",
    "tenure_months"
  ],
  "approved_feature_columns": null,
  "features_status": "recommended_pending_confirmation",
  "column_roles": [
    {
      "column": "customer_id",
      "semantic_type": "identifier",
      "data_type": "int64",
      "unique_values": 100,
      "missing_count": 0,
      "missing_pct": 0.0,
      "sensitive": false,
      "needs_privacy_review": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "quality_issue_codes": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input.",
      "preprocessing_hint": "Do not use as a model input; keep for joining tables."
    },
    {
      "column": "monthly_charges",
      "semantic_type": "numerical_measure",
      "data_type": "float64",
      "unique_values": 95,
      "missing_count": 0,
      "missing_pct": 0.0,
      "sensitive": false,
      "needs_privacy_review": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "quality_issue_codes": [],
      "role": "feature",
      "reason": "numerical_measure column usable as a model input.",
      "preprocessing_hint": "Scale if the model needs it."
    },
    {
      "column": "tenure_months",
      "semantic_type": "numerical_measure",
      "data_type": "int64",
      "unique_values": 60,
      "missing_count": 0,
      "missing_pct": 0.0,
      "sensitive": false,
      "needs_privacy_review": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "quality_issue_codes": [],
      "role": "feature",
      "reason": "numerical_measure column usable as a model input.",
      "preprocessing_hint": "Scale if the model needs it."
    }
  ],
  "leakage_checks": {
    "status": "pending_integration",
    "reason": "Target-leakage checks need column correlations from the profiling module (planned, not yet available). Not run."
  },
  "status": "Proposed, pending verification"
}
```

**B. Forecasting** (sales data, goal "Forecast revenue next month"), with `time_info`.
```json
{
  "dataset": "sales.xlsx",
  "target": "revenue",
  "target_source": "top_suggestion",
  "problem_type": "forecasting",
  "confidence": 0.9,
  "source": "business_goal",
  "needs_confirmation": false,
  "evidence": [
    "Business goal mentions 'forecast'.",
    "Time column 'order_date' (100 distinct dates); numeric target 'revenue'."
  ],
  "alternatives": [
    {
      "problem_type": "regression",
      "reason": "Use if the time order does not matter"
    }
  ],
  "warnings": [],
  "target_confirmed": false,
  "target_statistics": {
    "column": "revenue",
    "data_type": "float64",
    "semantic_type": "financial_amount",
    "unique_count": 99,
    "missing_count": 0,
    "missing_pct": 0.0,
    "class_distribution": null,
    "minority_class_pct": null,
    "numerical_statistics": null,
    "notes": []
  },
  "candidates": [
    {
      "rank": 1,
      "candidate_target": "revenue",
      "semantic_type": "financial_amount",
      "suggested_problem_type": "regression",
      "score": 95.0,
      "confidence_level": "High",
      "priority": "Top suggestion",
      "warnings": "",
      "quality_issue_codes": [],
      "blocking_reason": null
    },
    {
      "rank": 2,
      "candidate_target": "units_sold",
      "semantic_type": "numerical_measure",
      "suggested_problem_type": "regression",
      "score": 85.0,
      "confidence_level": "High",
      "priority": "Alternative",
      "warnings": "",
      "quality_issue_codes": [],
      "blocking_reason": null
    }
  ],
  "dataset_characteristics": {
    "row_count": 100,
    "column_count": 3,
    "duplicate_row_count": 0,
    "profile_status": "success",
    "feature_column_count": 1,
    "feature_type_counts": {
      "numerical": 1,
      "categorical": 0,
      "boolean": 0,
      "other": 0
    },
    "missing_summary": [],
    "time_info": [
      {
        "column": "order_date",
        "start": "2023-01-01 00:00:00",
        "end": "2023-04-10 00:00:00",
        "distinct_dates": 100,
        "estimated_frequency": "daily",
        "gaps": "Not available from the profile (needs the values).",
        "average_spacing_days": 1.0
      }
    ],
    "time_columns": [
      "order_date"
    ],
    "identifier_columns": [],
    "date_columns": [
      "order_date"
    ],
    "sensitive_columns": [],
    "excluded_columns": [],
    "validation_warnings": [
      "Only 1 usable feature column."
    ]
  },
  "feature_columns": [
    "units_sold"
  ],
  "recommended_feature_columns": [
    "units_sold"
  ],
  "approved_feature_columns": null,
  "features_status": "recommended_pending_confirmation",
  "column_roles": [
    {
      "column": "order_date",
      "semantic_type": "date",
      "data_type": "datetime64[us]",
      "unique_values": 100,
      "missing_count": 0,
      "missing_pct": 0.0,
      "sensitive": false,
      "needs_privacy_review": false,
      "time_axis": true,
      "quality_blocked": false,
      "quality_issues": [],
      "quality_issue_codes": [],
      "role": "date",
      "reason": "Date column that can act as a time axis.",
      "preprocessing_hint": "Use as the time index for forecasting; derive lag features."
    },
    {
      "column": "units_sold",
      "semantic_type": "numerical_measure",
      "data_type": "int64",
      "unique_values": 80,
      "missing_count": 0,
      "missing_pct": 0.0,
      "sensitive": false,
      "needs_privacy_review": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "quality_issue_codes": [],
      "role": "feature",
      "reason": "numerical_measure column usable as a model input.",
      "preprocessing_hint": "Scale if the model needs it."
    },
    {
      "column": "revenue",
      "semantic_type": "financial_amount",
      "data_type": "float64",
      "unique_values": 99,
      "missing_count": 0,
      "missing_pct": 0.0,
      "sensitive": false,
      "needs_privacy_review": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "quality_issue_codes": [],
      "role": "target",
      "reason": "Suggested or chosen target column.",
      "preprocessing_hint": "Target: use as the value to predict; check for outliers."
    }
  ],
  "leakage_checks": {
    "status": "pending_integration",
    "reason": "Target-leakage checks need column correlations from the profiling module (planned, not yet available). Not run."
  },
  "status": "Proposed, pending verification"
}
```

**C. Quality issue** (a Blocking range problem on `monthly_charges`; shows `blocking_reason`).
```json
{
  "dataset": "churn.xlsx",
  "target": "churn",
  "target_source": "top_suggestion",
  "problem_type": "binary_classification",
  "confidence": 0.85,
  "source": "data_rules",
  "needs_confirmation": true,
  "evidence": [
    "Target 'churn' is boolean_flag with 2 distinct values."
  ],
  "alternatives": [],
  "warnings": [],
  "target_confirmed": false,
  "target_statistics": {
    "column": "churn",
    "data_type": "int64",
    "semantic_type": "boolean_flag",
    "unique_count": 2,
    "missing_count": 0,
    "missing_pct": 0.0,
    "class_distribution": null,
    "minority_class_pct": null,
    "numerical_statistics": null,
    "notes": [
      "Class distribution not available from the profile."
    ]
  },
  "candidates": [
    {
      "rank": 1,
      "candidate_target": "churn",
      "semantic_type": "boolean_flag",
      "suggested_problem_type": "binary_classification",
      "score": 100.0,
      "confidence_level": "High",
      "priority": "Top suggestion",
      "warnings": "Check class balance before training",
      "quality_issues": "",
      "quality_issue_codes": [],
      "blocking_reason": null
    },
    {
      "rank": 2,
      "candidate_target": "tenure_months",
      "semantic_type": "numerical_measure",
      "suggested_problem_type": "regression",
      "score": 70.0,
      "confidence_level": "Low",
      "priority": "Candidate",
      "warnings": "",
      "quality_issues": "",
      "quality_issue_codes": [],
      "blocking_reason": null
    },
    {
      "rank": 3,
      "candidate_target": "monthly_charges",
      "semantic_type": "numerical_measure",
      "suggested_problem_type": "regression",
      "score": 0.0,
      "confidence_level": "Low",
      "priority": "Blocked by quality",
      "warnings": "INVALID_RANGE (blocking): negative charge [2 rows]",
      "quality_issues": "INVALID_RANGE (blocking): negative charge [2 rows]",
      "quality_issue_codes": [
        "INVALID_RANGE"
      ],
      "blocking_reason": "INVALID_RANGE: negative charge"
    }
  ],
  "dataset_characteristics": {
    "row_count": 100,
    "column_count": 4,
    "duplicate_row_count": 0,
    "profile_status": "success",
    "feature_column_count": 2,
    "feature_type_counts": {
      "numerical": 2,
      "categorical": 0,
      "boolean": 0,
      "other": 0
    },
    "missing_summary": [],
    "time_info": [],
    "time_columns": [],
    "identifier_columns": [
      "customer_id"
    ],
    "date_columns": [],
    "sensitive_columns": [],
    "excluded_columns": [],
    "validation_warnings": [
      "Some features have a blocking quality issue; review them."
    ]
  },
  "feature_columns": [
    "monthly_charges",
    "tenure_months"
  ],
  "recommended_feature_columns": [
    "tenure_months"
  ],
  "approved_feature_columns": null,
  "features_status": "recommended_pending_confirmation",
  "column_roles": [
    {
      "column": "customer_id",
      "semantic_type": "identifier",
      "data_type": "int64",
      "unique_values": 100,
      "missing_count": 0,
      "missing_pct": 0.0,
      "sensitive": false,
      "needs_privacy_review": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "quality_issue_codes": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input.",
      "preprocessing_hint": "Do not use as a model input; keep for joining tables."
    },
    {
      "column": "monthly_charges",
      "semantic_type": "numerical_measure",
      "data_type": "float64",
      "unique_values": 95,
      "missing_count": 0,
      "missing_pct": 0.0,
      "sensitive": false,
      "needs_privacy_review": false,
      "time_axis": false,
      "quality_blocked": true,
      "quality_issues": [
        "INVALID_RANGE (blocking)"
      ],
      "quality_issue_codes": [
        "INVALID_RANGE"
      ],
      "role": "feature",
      "reason": "numerical_measure column usable as a model input. Blocking quality issue reported; review before use.",
      "preprocessing_hint": "Scale if the model needs it."
    }
  ],
  "leakage_checks": {
    "status": "pending_integration",
    "reason": "Target-leakage checks need column correlations from the profiling module (planned, not yet available). Not run."
  },
  "status": "Proposed, pending verification"
}
```

**D. No clear outcome** (HR Employee data, nothing chosen).
```json
{
  "dataset": "HumanResources.Employee.xlsx",
  "target": null,
  "target_source": "none",
  "problem_type": "review_required",
  "confidence": 0.3,
  "source": "data_rules",
  "needs_confirmation": true,
  "evidence": [
    "No target column selected."
  ],
  "alternatives": [
    {
      "problem_type": "clustering",
      "reason": "Works without a target (7 usable feature columns)"
    }
  ],
  "warnings": [
    "No column clearly looks like an outcome; the project owner or user must confirm the business objective and target"
  ],
  "target_confirmed": false,
  "target_statistics": null,
  "candidates": [
    {
      "rank": 1,
      "candidate_target": "SalariedFlag",
      "semantic_type": "boolean_flag",
      "suggested_problem_type": "binary_classification",
      "score": 80.0,
      "confidence_level": "Low",
      "priority": "Candidate",
      "warnings": "Check class balance before training; No column clearly looks like an outcome; confirm the business objective",
      "quality_issue_codes": [],
      "blocking_reason": null
    },
    {
      "rank": 2,
      "candidate_target": "VacationHours",
      "semantic_type": "numerical_measure",
      "suggested_problem_type": "regression",
      "score": 70.0,
      "confidence_level": "Low",
      "priority": "Candidate",
      "warnings": "No column clearly looks like an outcome; confirm the business objective",
      "quality_issue_codes": [],
      "blocking_reason": null
    }
  ],
  "dataset_characteristics": {
    "row_count": 290,
    "column_count": 16,
    "duplicate_row_count": 0,
    "profile_status": "warning",
    "feature_column_count": 7,
    "feature_type_counts": {
      "numerical": 2,
      "categorical": 4,
      "boolean": 1,
      "other": 0
    },
    "missing_summary": [
      {
        "column": "OrganizationNode",
        "missing_count": 1,
        "missing_pct": 0.3
      },
      {
        "column": "OrganizationLevel",
        "missing_count": 1,
        "missing_pct": 0.3
      }
    ],
    "time_info": [],
    "time_columns": [],
    "identifier_columns": [
      "BusinessEntityID",
      "NationalIDNumber",
      "LoginID"
    ],
    "date_columns": [
      "BirthDate",
      "HireDate"
    ],
    "sensitive_columns": [
      "NationalIDNumber",
      "LoginID",
      "BirthDate",
      "MaritalStatus",
      "Gender"
    ],
    "excluded_columns": [
      "CurrentFlag",
      "rowguid",
      "ModifiedDate"
    ],
    "validation_warnings": [
      "Feature 'JobTitle' has 67 distinct values (high cardinality)."
    ]
  },
  "feature_columns": [
    "OrganizationLevel",
    "JobTitle",
    "MaritalStatus",
    "Gender",
    "SalariedFlag",
    "VacationHours",
    "SickLeaveHours"
  ],
  "recommended_feature_columns": [
    "OrganizationLevel",
    "JobTitle",
    "MaritalStatus",
    "Gender",
    "SalariedFlag",
    "VacationHours",
    "SickLeaveHours"
  ],
  "approved_feature_columns": null,
  "features_status": "recommended_pending_confirmation",
  "column_roles": [
    {
      "column": "BusinessEntityID",
      "semantic_type": "identifier",
      "data_type": "int64",
      "unique_values": 290,
      "missing_count": 0,
      "missing_pct": 0.0,
      "sensitive": false,
      "needs_privacy_review": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "quality_issue_codes": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input.",
      "preprocessing_hint": "Do not use as a model input; keep for joining tables."
    },
    {
      "column": "NationalIDNumber",
      "semantic_type": "identifier",
      "data_type": "int64",
      "unique_values": 290,
      "missing_count": 0,
      "missing_pct": 0.0,
      "sensitive": true,
      "needs_privacy_review": true,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "quality_issue_codes": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input.",
      "preprocessing_hint": "Do not use as a model input; keep for joining tables."
    },
    {
      "column": "LoginID",
      "semantic_type": "identifier",
      "data_type": "str",
      "unique_values": 290,
      "missing_count": 0,
      "missing_pct": 0.0,
      "sensitive": true,
      "needs_privacy_review": true,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "quality_issue_codes": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input.",
      "preprocessing_hint": "Do not use as a model input; keep for joining tables."
    }
  ],
  "leakage_checks": {
    "status": "pending_integration",
    "reason": "Target-leakage checks need column correlations from the profiling module (planned, not yet available). Not run."
  },
  "status": "Proposed, pending verification"
}
```

## 9. Known limits and dependencies

- **Target leakage: partly implemented.** Correlation-based flagging works when the profile has `correlations[]` and the target is numerical. It does not cover categorical targets, derived columns or time-based leakage. The examples below were made from profiles without correlations, so they show `pending_integration`.
- "Top suggestion" needs an outcome-like word in the column name.
- Quality penalties are not in the SRS; they are configurable proposed defaults until approved. Null, duplicate-row, key and reference findings are notes only.
- Everything is computed from the profile only. Time-series gaps, full class distributions beyond the top values, and value-level checks are not available.
- Preprocessing hints and roles are recommendations.
- **Weak targets are not recommended.** A target that is 80% or more missing, or has one distinct value, gives `review_required` with a warning. A target 20% to 80% missing keeps its type, loses 0.15 confidence and gets a warning. A column with mixed text and numbers is treated as `unknown` (not a feature, not a target). These thresholds are proposed defaults, not from the SRS.
- When the profile contains a full `class_distribution` for the chosen target, `target_statistics.class_distribution` uses it.
- A profile with no columns gives a `review_required` result with a warning (other datasets in the same run are unaffected).

## 10. Open points

1. Sinchana: does preprocessing need anything more than the roles and hints above?
2. Meshak and Sumanth: which fields are core for the first integration, and which stay optional?
3. How and where does the user approve features (`approved_features`) in the application? Features stay pending until approved; the screen is to be agreed with Team 3 (section 11).
4. Final HR demo objective: `VacationHours` is a provisional demo target (see section 11); the final objective is to be confirmed by the project owner.
5. Approval of the quality penalty and leakage defaults: they stay configurable proposed defaults for now (section 11).

## 11. Working decisions (from Meshak, Wed 28 Oct 2026)

These are current working decisions, not final approvals. Anything not listed here is still open (section 10).

| # | Decision | Status |
|---|---|---|
| 1 | **Demo target:** `Employee.VacationHours` is used as a provisional demo target, clearly labeled as a demo choice. The final business objective and target are still pending confirmation. In the Employee sample, `target_confirmed` is true only because the run was given the target by override; it does not mean the business objective is approved. | Working decision |
| 2 | **Defaults:** leakage thresholds (0.80 / 0.95), quality penalties and the weak-target rules (80% missing or constant gives `review_required`; 20% to 80% missing gives a warning) stay configurable and are **proposed defaults, not approved requirements**. | Working decision |
| 3 | **Correlation is not proof of leakage.** A leakage suspect is a flag for a person to check. It never removes a column and is never a final verdict. | Working decision |
| 4 | **Feature confirmation:** features stay pending confirmation until the user approves them before training. The exact screen or step in the application is to be agreed with Team 3. | Pending (Team 3) |
| 5 | **Handoff to Sumanth:** one JSON file per run, using the agreed output schema (`handoff_result.schema.json`). A move to an API can follow once Team 2 confirms the contract. | Working decision; API pending Team 2 |

### When a human must confirm before training

| Situation | Where it shows in the result | Who confirms |
|---|---|---|
| No target found | `target` is null, `problem_type` is `review_required` | User / project owner (business objective) |
| Target only suggested by the system | `target_confirmed` false, `needs_confirmation` true | User |
| Problem type unclear or goal cannot be met | `problem_type` `review_required`, warnings | User |
| Target mostly missing (80% or more) or constant | `review_required`, warning | User / data owner |
| Target 20% to 80% missing | Lower confidence and warning | User |
| Leakage suspect found | `leakage_checks.suspects` (possible or strong) | User / data owner (correlation alone is not proof) |
| Quality finding that blocks a column | `quality_blocked`, candidate priority `Blocked by quality` | Data owner / Vinitha |
| Features not yet approved | `features_status` is `recommended_pending_confirmation` | User (screen to be agreed with Team 3) |
| Run used a demo or override target | `target_source` is `user_override` | Project owner for the final objective |
