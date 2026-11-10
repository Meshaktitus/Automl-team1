# Handoff contract: target and problem-type output (1.0-draft)

Owner: Samarth. Primary consumer: Sumanth (AutoML). Also: Sinchana (preprocessing), Meshak (review).
Status: **implemented and tested as a prototype; proposed, pending Team 1 review.** Not final until Meshak and the consumers agree it. Any change to a field below must be shared with the consumers first.

## 1. How it is called

```python
from run_detection import run_detection
results = run_detection(
    profiles=[...],                 # profiling responses (paths or dicts), contract 1.0-draft
    quality=None,                   # optional quality report (path or dict)
    goal=None,                      # optional business goal in plain words
    overrides=None,                 # optional {dataset_name: target_column} chosen by the user
    problem_type_override=None,     # optional problem type chosen by the user
    quality_dataset=None,           # dataset for quality issues that name none
)
```

Command line: `python run_detection.py --profiles <folder> [--quality file.json] [--goal "..."] [--override DATASET=COLUMN] [--problem-type TYPE]`. It writes `outputs/integrated_detection.json`.

It returns a list with **one result per dataset**. Nothing is read from the raw data; only the profiling output is used. Nothing is specific to one domain.

## 2. Result fields (always all present)

| Field | Type | Meaning |
|---|---|---|
| `dataset` | string | Dataset name from the profile |
| `target` | string or null | Suggested or chosen target column. null when none can be suggested |
| `target_source` | `user_override` / `top_suggestion` / `none` | Who chose it |
| `problem_type` | string | One of the 7 types below, or `review_required` |
| `confidence` | number 0 to 1 | 1.0 only for a user override; otherwise at most 0.95 |
| `source` | `user_override` / `business_goal` / `data_rules` | What decided the problem type |
| `needs_confirmation` | boolean | true = a human must confirm before training |
| `evidence` | list of text | Why this problem type |
| `alternatives` | list of `{problem_type, reason}` | Other types worth considering |
| `warnings` | list of text | Anything the consumer should show or act on |
| `candidates` | list (up to 5) | Ranked target candidates, see section 3 |
| `semantic_columns` | list | `column, semantic_type, confidence, sensitive` for every column |
| `status` | text | Always "Proposed, pending verification" |

Problem types: `binary_classification`, `multiclass_classification`, `regression`, `forecasting`, `clustering`, `anomaly_detection`, `recommendation`, `review_required` (nothing can be recommended yet).

Semantic types: identifier, email, phone, percentage, date, time, boolean_flag, categorical, financial_amount, numerical_measure, text, unknown.

## 3. Candidate fields

`rank, candidate_target, semantic_type, suggested_problem_type, score (0-100), confidence_level (High / Medium / Low / User-selected), priority, warnings`, and `quality_issues` when a quality report was given.

`priority` values: `User-selected`, `Top suggestion` (only when the column name looks like an outcome), `Alternative`, `Candidate`, `Blocked by quality` (a blocking quality issue; score 0).

## 4. Rules for the consumer (proposed)

1. If `needs_confirmation` is true, do not start training automatically. Show the target, problem type, evidence and alternatives to the user.
2. If `target_source` is `user_override` or `source` is `user_override`, follow it. The user's choice always wins.
3. If `target` is null or `problem_type` is `review_required`, ask the user for the business objective and target. This is the normal result for data with no clear outcome.
4. Never use a candidate with priority `Blocked by quality` as a target or feature without the user's say-so.
5. Columns with `semantic_type` identifier, email, phone, text, date or time are not features by default. Columns with `sensitive` true need a fairness and privacy review.
6. Show `warnings` to the user; they are written to be readable.
7. Treat the target as unconfirmed until a human confirms it; the module only proposes.

## 5. Examples (real outputs of the prototype, shortened)

**A. Clear outcome, needs confirmation** (customer churn): target `churn`, binary classification.
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
  "semantic_columns": [
    {
      "column": "customer_id",
      "semantic_type": "identifier",
      "confidence": 0.99,
      "sensitive": false
    },
    {
      "column": "monthly_charges",
      "semantic_type": "numerical_measure",
      "confidence": 0.6,
      "sensitive": false
    },
    {
      "column": "tenure_months",
      "semantic_type": "numerical_measure",
      "confidence": 0.9,
      "sensitive": false
    }
  ],
  "status": "Proposed, pending verification"
}
```

**B. Goal fits the data** (sales data, goal "Forecast revenue next month"): forecasting, no confirmation needed.
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
  "semantic_columns": [
    {
      "column": "order_date",
      "semantic_type": "date",
      "confidence": 0.99,
      "sensitive": false
    },
    {
      "column": "units_sold",
      "semantic_type": "numerical_measure",
      "confidence": 0.9,
      "sensitive": false
    },
    {
      "column": "revenue",
      "semantic_type": "financial_amount",
      "confidence": 0.9,
      "sensitive": false
    }
  ],
  "status": "Proposed, pending verification"
}
```

**C. No clear outcome** (HR Employee data): no target, ask for the business objective.
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
    }
  ],
  "semantic_columns": [
    {
      "column": "BusinessEntityID",
      "semantic_type": "identifier",
      "confidence": 0.99,
      "sensitive": false
    },
    {
      "column": "NationalIDNumber",
      "semantic_type": "identifier",
      "confidence": 0.99,
      "sensitive": true
    },
    {
      "column": "LoginID",
      "semantic_type": "identifier",
      "confidence": 0.99,
      "sensitive": true
    }
  ],
  "status": "Proposed, pending verification"
}
```

**D. Quality issue** (a Blocking range problem on `monthly_charges`): the column is shown as `Blocked by quality`.
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
  "semantic_columns": [
    {
      "column": "customer_id",
      "semantic_type": "identifier",
      "confidence": 0.99,
      "sensitive": false
    },
    {
      "column": "monthly_charges",
      "semantic_type": "numerical_measure",
      "confidence": 0.6,
      "sensitive": false
    },
    {
      "column": "tenure_months",
      "semantic_type": "numerical_measure",
      "confidence": 0.9,
      "sensitive": false
    }
  ],
  "status": "Proposed, pending verification"
}
```

## 6. Known limits

- "Top suggestion" needs an outcome-like word in the column name; otherwise the candidates are ranked but nothing is marked Top and the user confirms.
- Target-leakage checks are not built (they need correlations from profiling).
- Quality penalties (Medium x0.85, High x0.6, Blocking x0) are proposed defaults, not agreed. Null, duplicate-row, key and reference findings are notes only.
- Profile-based types are an approximation of the data-based ones; they matched on all 40 profiled HR columns.

## 7. Open questions for Meshak

1. Is this the field set Sumanth needs, or should anything be added (for example the list of feature columns)?
2. Should the module return the whole list, or one dataset per call?
3. Where do the user's goal and overrides come from at run time (frontend, backend)?
