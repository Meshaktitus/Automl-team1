# Handoff contract: target, problem type and input columns (1.0-draft, revision 2)

Owner: Samarth. Consumers: Sumanth (AutoML, primary), Sinchana (preprocessing). Reviewer: Meshak.
Status: **implemented and tested as a prototype; proposed, pending Team 1 review.** The exact fields are **to be agreed with Sumanth and Sinchana**. This document is not final until they and Meshak have reviewed it. Please share any change to a field before it is treated as final.

## Changes since the first draft (after Meshak's review, 27 Oct)
1. Added `feature_columns`, `column_roles` and `dataset_characteristics`, so Sumanth and Sinchana get the input columns, identifiers, date columns and dataset facts, each with a reason.
2. Added `leakage_checks`, which says plainly that leakage checks are **not run** yet.
3. Added `detect_dataset(...)` for one dataset per call (a technical choice, not an SRS requirement).
4. Quality penalties are now settings you can change (`quality_settings`). The defaults are proposals, not approved.

## 1. How it is called

```python
from run_detection import run_detection, detect_dataset

# one dataset per call
result = detect_dataset(
    "Employee.profile.json",        # profiling response (path or dict), contract 1.0-draft
    quality=None,                   # optional quality report (path or dict)
    goal=None,                      # optional business goal in plain words
    overrides=None,                 # optional {dataset_name: target_column} chosen by the user
    problem_type_override=None,     # optional problem type chosen by the user
    quality_settings=None,          # optional, change the proposed quality penalties
)

# several datasets at once: run_detection([...]) returns a list of the same results
```

Command line: `python run_detection.py --profiles <folder> [--quality file.json] [--goal "..."] [--override DATASET=COLUMN] [--problem-type TYPE]`.

Only the profiling output is read, never the raw data. Nothing is specific to one domain.

## 2. Result fields (always all present)

| Field | Type | Meaning |
|---|---|---|
| `dataset` | string | Dataset name from the profile |
| `target` | string or null | Suggested or chosen target. null when none can be suggested |
| `target_source` | `user_override` / `top_suggestion` / `none` | Who chose it |
| `problem_type` | string | One of the 7 types below, or `review_required` |
| `confidence` | number 0 to 1 | 1.0 only for a user override; otherwise at most 0.95 |
| `source` | `user_override` / `business_goal` / `data_rules` | What decided the problem type |
| `needs_confirmation` | boolean | true = a human must confirm before training |
| `evidence` | list of text | Why this problem type |
| `alternatives` | list of `{problem_type, reason}` | Other types worth considering |
| `warnings` | list of text | Anything the consumer should show or act on |
| `candidates` | list (up to 5) | Ranked target candidates (section 3) |
| `feature_columns` | list of column names | Recommended input columns (role `feature`) |
| `column_roles` | list | A recommended role and reason for every column (section 4) |
| `dataset_characteristics` | object | Dataset facts (section 5) |
| `leakage_checks` | object | `status` and `reason`. Currently `pending_integration` |
| `semantic_columns` | list | `column, semantic_type, confidence, sensitive` for every column |
| `status` | text | Always "Proposed, pending verification" |

Problem types: `binary_classification`, `multiclass_classification`, `regression`, `forecasting`, `clustering`, `anomaly_detection`, `recommendation`, `review_required` (nothing can be recommended yet).

## 3. Candidate fields

`rank, candidate_target, semantic_type, suggested_problem_type, score (0-100), confidence_level (High / Medium / Low / User-selected), priority, warnings`, and `quality_issues` when a quality report was given. `priority` values: `User-selected`, `Top suggestion` (only when the column name looks like an outcome), `Alternative`, `Candidate`, `Blocked by quality`.

## 4. Column roles (for Sumanth and Sinchana)

Each entry in `column_roles`: `column, semantic_type, role, reason, sensitive, time_axis, quality_blocked, quality_issues`.

| Role | Meaning |
|---|---|
| `target` | The suggested or chosen target |
| `feature` | Recommended model input |
| `identifier` | ID, key, email or phone; useful for joining tables, not as a model input |
| `date` | Date column. `time_axis` is true when it can order the data in time (forecasting); otherwise it describes a person or record and can be turned into age or duration |
| `time` | Time-of-day column |
| `text` | Free text; needs text processing |
| `excluded` | Audit metadata, constant, almost empty (80% or more missing) or unknown type |

These are **recommendations with the reason attached, not irreversible decisions.** The user can change them. `quality_blocked` is true when the quality report has a Blocking issue on that column that is not a null, duplicate-row or key finding.

## 5. Dataset characteristics

`row_count, column_count, duplicate_row_count, profile_status, feature_column_count, time_columns, identifier_columns, date_columns, sensitive_columns, excluded_columns`. More facts can be added once Sumanth says what AutoML needs.

## 6. Rules for the consumer (proposed)

1. If `needs_confirmation` is true, do not start training automatically. Show the target, problem type, evidence and alternatives to the user.
2. If `target_source` or `source` is `user_override`, follow it. The user's choice always wins.
3. If `target` is null or `problem_type` is `review_required`, ask the user for the business objective and target. This is the normal result for data with no clear outcome.
4. Do not use a candidate with priority `Blocked by quality`, or a column with `quality_blocked` true, without the user's say-so.
5. Show `warnings` and `leakage_checks.status` to the user. Do not treat leakage as checked while the status is `pending_integration`.
6. Sensitive columns need a fairness and privacy review.

## 7. Examples (real outputs of the prototype, shortened)

**A. Clear outcome, needs confirmation** (customer churn).
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
  "candidates": [
    {
      "rank": 1,
      "candidate_target": "churn",
      "semantic_type": "boolean_flag",
      "suggested_problem_type": "binary_classification",
      "score": 100.0,
      "confidence_level": "High",
      "priority": "Top suggestion",
      "warnings": "Check class balance before training"
    },
    {
      "rank": 2,
      "candidate_target": "monthly_charges",
      "semantic_type": "numerical_measure",
      "suggested_problem_type": "regression",
      "score": 70.0,
      "confidence_level": "Low",
      "priority": "Candidate",
      "warnings": ""
    }
  ],
  "dataset_characteristics": {
    "row_count": 100,
    "column_count": 4,
    "duplicate_row_count": 0,
    "profile_status": "success",
    "feature_column_count": 2,
    "time_columns": [],
    "identifier_columns": [
      "customer_id"
    ],
    "date_columns": [],
    "sensitive_columns": [],
    "excluded_columns": []
  },
  "feature_columns": [
    "monthly_charges",
    "tenure_months"
  ],
  "column_roles": [
    {
      "column": "customer_id",
      "semantic_type": "identifier",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input."
    },
    {
      "column": "monthly_charges",
      "semantic_type": "numerical_measure",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "feature",
      "reason": "numerical_measure column usable as a model input."
    },
    {
      "column": "tenure_months",
      "semantic_type": "numerical_measure",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "feature",
      "reason": "numerical_measure column usable as a model input."
    },
    {
      "column": "churn",
      "semantic_type": "boolean_flag",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "target",
      "reason": "Suggested or chosen target column."
    }
  ],
  "leakage_checks": {
    "status": "pending_integration",
    "reason": "Target-leakage checks need column correlations from the profiling module (planned, not yet available). Not run."
  },
  "status": "Proposed, pending verification"
}
```

**B. Goal fits the data** (sales data, goal "Forecast revenue next month").
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
  "candidates": [
    {
      "rank": 1,
      "candidate_target": "revenue",
      "semantic_type": "financial_amount",
      "suggested_problem_type": "regression",
      "score": 95.0,
      "confidence_level": "High",
      "priority": "Top suggestion",
      "warnings": ""
    },
    {
      "rank": 2,
      "candidate_target": "units_sold",
      "semantic_type": "numerical_measure",
      "suggested_problem_type": "regression",
      "score": 85.0,
      "confidence_level": "High",
      "priority": "Alternative",
      "warnings": ""
    }
  ],
  "dataset_characteristics": {
    "row_count": 100,
    "column_count": 3,
    "duplicate_row_count": 0,
    "profile_status": "success",
    "feature_column_count": 1,
    "time_columns": [
      "order_date"
    ],
    "identifier_columns": [],
    "date_columns": [
      "order_date"
    ],
    "sensitive_columns": [],
    "excluded_columns": []
  },
  "feature_columns": [
    "units_sold"
  ],
  "column_roles": [
    {
      "column": "order_date",
      "semantic_type": "date",
      "sensitive": false,
      "time_axis": true,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "date",
      "reason": "Date column that can act as a time axis."
    },
    {
      "column": "units_sold",
      "semantic_type": "numerical_measure",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "feature",
      "reason": "numerical_measure column usable as a model input."
    },
    {
      "column": "revenue",
      "semantic_type": "financial_amount",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "target",
      "reason": "Suggested or chosen target column."
    }
  ],
  "leakage_checks": {
    "status": "pending_integration",
    "reason": "Target-leakage checks need column correlations from the profiling module (planned, not yet available). Not run."
  },
  "status": "Proposed, pending verification"
}
```

**C. No clear outcome** (HR Employee data, nothing chosen).
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
  "candidates": [
    {
      "rank": 1,
      "candidate_target": "SalariedFlag",
      "semantic_type": "boolean_flag",
      "suggested_problem_type": "binary_classification",
      "score": 80.0,
      "confidence_level": "Low",
      "priority": "Candidate",
      "warnings": "Check class balance before training; No column clearly looks like an outcome; confirm the business objective"
    },
    {
      "rank": 2,
      "candidate_target": "VacationHours",
      "semantic_type": "numerical_measure",
      "suggested_problem_type": "regression",
      "score": 70.0,
      "confidence_level": "Low",
      "priority": "Candidate",
      "warnings": "No column clearly looks like an outcome; confirm the business objective"
    },
    {
      "rank": 3,
      "candidate_target": "SickLeaveHours",
      "semantic_type": "numerical_measure",
      "suggested_problem_type": "regression",
      "score": 70.0,
      "confidence_level": "Low",
      "priority": "Candidate",
      "warnings": "No column clearly looks like an outcome; confirm the business objective"
    }
  ],
  "dataset_characteristics": {
    "row_count": 290,
    "column_count": 16,
    "duplicate_row_count": 0,
    "profile_status": "warning",
    "feature_column_count": 7,
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
  "column_roles": [
    {
      "column": "BusinessEntityID",
      "semantic_type": "identifier",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input."
    },
    {
      "column": "NationalIDNumber",
      "semantic_type": "identifier",
      "sensitive": true,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input."
    },
    {
      "column": "LoginID",
      "semantic_type": "identifier",
      "sensitive": true,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input."
    },
    {
      "column": "OrganizationNode",
      "semantic_type": "text",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "text",
      "reason": "Free text; needs text processing before use."
    },
    {
      "column": "OrganizationLevel",
      "semantic_type": "categorical",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "feature",
      "reason": "categorical column usable as a model input."
    }
  ],
  "leakage_checks": {
    "status": "pending_integration",
    "reason": "Target-leakage checks need column correlations from the profiling module (planned, not yet available). Not run."
  },
  "status": "Proposed, pending verification"
}
```

**D. User picks the target** (HR Employee data, user selects `VacationHours`; **illustration only, the HR demo objective is not confirmed**).
```json
{
  "dataset": "HumanResources.Employee.xlsx",
  "target": "VacationHours",
  "target_source": "user_override",
  "problem_type": "regression",
  "confidence": 0.8,
  "source": "data_rules",
  "needs_confirmation": true,
  "evidence": [
    "Target 'VacationHours' is numerical_measure with 100 distinct values."
  ],
  "alternatives": [],
  "warnings": [],
  "candidates": [
    {
      "rank": 1,
      "candidate_target": "VacationHours",
      "semantic_type": "numerical_measure",
      "suggested_problem_type": "regression",
      "score": 70.0,
      "confidence_level": "User-selected",
      "priority": "User-selected",
      "warnings": ""
    },
    {
      "rank": 2,
      "candidate_target": "SalariedFlag",
      "semantic_type": "boolean_flag",
      "suggested_problem_type": "binary_classification",
      "score": 80.0,
      "confidence_level": "Low",
      "priority": "Candidate",
      "warnings": "Check class balance before training; No column clearly looks like an outcome; confirm the business objective"
    }
  ],
  "dataset_characteristics": {
    "row_count": 290,
    "column_count": 16,
    "duplicate_row_count": 0,
    "profile_status": "warning",
    "feature_column_count": 6,
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
    ]
  },
  "feature_columns": [
    "OrganizationLevel",
    "JobTitle",
    "MaritalStatus",
    "Gender",
    "SalariedFlag",
    "SickLeaveHours"
  ],
  "column_roles": [
    {
      "column": "BusinessEntityID",
      "semantic_type": "identifier",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input."
    },
    {
      "column": "NationalIDNumber",
      "semantic_type": "identifier",
      "sensitive": true,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input."
    },
    {
      "column": "LoginID",
      "semantic_type": "identifier",
      "sensitive": true,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input."
    },
    {
      "column": "OrganizationNode",
      "semantic_type": "text",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "text",
      "reason": "Free text; needs text processing before use."
    },
    {
      "column": "OrganizationLevel",
      "semantic_type": "categorical",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "feature",
      "reason": "categorical column usable as a model input."
    },
    {
      "column": "JobTitle",
      "semantic_type": "categorical",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "feature",
      "reason": "categorical column usable as a model input."
    },
    {
      "column": "BirthDate",
      "semantic_type": "date",
      "sensitive": true,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "date",
      "reason": "Date that describes a record or person; usable after turning it into age, duration or similar."
    },
    {
      "column": "MaritalStatus",
      "semantic_type": "categorical",
      "sensitive": true,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "feature",
      "reason": "categorical column usable as a model input. Sensitive; review fairness and privacy."
    },
    {
      "column": "Gender",
      "semantic_type": "categorical",
      "sensitive": true,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "feature",
      "reason": "categorical column usable as a model input. Sensitive; review fairness and privacy."
    },
    {
      "column": "HireDate",
      "semantic_type": "date",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "date",
      "reason": "Date that describes a record or person; usable after turning it into age, duration or similar."
    },
    {
      "column": "SalariedFlag",
      "semantic_type": "boolean_flag",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "feature",
      "reason": "boolean_flag column usable as a model input."
    },
    {
      "column": "VacationHours",
      "semantic_type": "numerical_measure",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "target",
      "reason": "Suggested or chosen target column."
    },
    {
      "column": "SickLeaveHours",
      "semantic_type": "numerical_measure",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "feature",
      "reason": "numerical_measure column usable as a model input."
    }
  ],
  "leakage_checks": {
    "status": "pending_integration",
    "reason": "Target-leakage checks need column correlations from the profiling module (planned, not yet available). Not run."
  },
  "status": "Proposed, pending verification"
}
```

**E. Quality issue** (a Blocking range problem on `monthly_charges`).
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
      "quality_issues": ""
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
      "quality_issues": ""
    },
    {
      "rank": 3,
      "candidate_target": "monthly_charges",
      "semantic_type": "numerical_measure",
      "suggested_problem_type": "regression",
      "score": 0.0,
      "confidence_level": "Low",
      "priority": "Blocked by quality",
      "warnings": "INVALID_RANGE (blocking):  [2 rows]",
      "quality_issues": "INVALID_RANGE (blocking):  [2 rows]"
    }
  ],
  "dataset_characteristics": {
    "row_count": 100,
    "column_count": 4,
    "duplicate_row_count": 0,
    "profile_status": "success",
    "feature_column_count": 2,
    "time_columns": [],
    "identifier_columns": [
      "customer_id"
    ],
    "date_columns": [],
    "sensitive_columns": [],
    "excluded_columns": []
  },
  "feature_columns": [
    "monthly_charges",
    "tenure_months"
  ],
  "column_roles": [
    {
      "column": "customer_id",
      "semantic_type": "identifier",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "identifier",
      "reason": "Identifier or contact value; useful for joining tables, not as a model input."
    },
    {
      "column": "monthly_charges",
      "semantic_type": "numerical_measure",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": true,
      "quality_issues": [
        "INVALID_RANGE (blocking)"
      ],
      "role": "feature",
      "reason": "numerical_measure column usable as a model input. Blocking quality issue reported; review before use."
    },
    {
      "column": "tenure_months",
      "semantic_type": "numerical_measure",
      "sensitive": false,
      "time_axis": false,
      "quality_blocked": false,
      "quality_issues": [],
      "role": "feature",
      "reason": "numerical_measure column usable as a model input."
    }
  ],
  "leakage_checks": {
    "status": "pending_integration",
    "reason": "Target-leakage checks need column correlations from the profiling module (planned, not yet available). Not run."
  },
  "status": "Proposed, pending verification"
}
```

## 8. Known limits and dependencies

- **Target leakage: not implemented.** The SRS asks for it. It needs column correlations from the profiling module, which are not available yet. Status: **design only / pending integration**. Not reported as done.
- "Top suggestion" needs an outcome-like word in the column name. Otherwise candidates are ranked, nothing is marked Top and the user confirms.
- Quality penalties (Medium x0.85, High x0.6, Blocking x0, and confidence -0.05, -0.10, -0.30) are **not in the SRS**. They are configurable proposed defaults until approved. Null, duplicate-row, key and reference findings are notes only. A Blocking finding makes a column unsuitable only when it is not one of those and is on that column.
- Profile-based types are an approximation of the data-based ones; they matched on all 40 profiled HR columns.
- Role recommendations use column names, types and profile facts only.

## 9. Open points

1. Sumanth: which fields does AutoML need beyond section 2 to 5?
2. Sinchana: which fields does preprocessing need (feature columns, identifiers, date columns are covered; anything else)?
3. Final HR demo objective: to be confirmed by the project owner. `VacationHours` has been discussed as a possible target only.
4. Approval of the quality penalty defaults.
