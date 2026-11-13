# Evaluation Framework

## Overview
The Week 1 responsibility assigned to Sinchana was **Evaluation Framework and Metrics**. This module provides a shared interface for evaluation metrics, an evaluation runner, concrete classification and regression metrics, and a separate input-validation helper.

## Module structure
```text
app/evaluation/
├── classification_metrics.py
├── evaluation.py
├── metrics.py
├── metric_types.py
├── regression_metrics.py
└── validation.py
```

## Implemented classification metrics
| Class | Name | Direction |
|---|---|---|
| `AccuracyMetric` | accuracy | Maximize |
| `PrecisionMetric` | precision | Maximize |
| `RecallMetric` | recall | Maximize |
| `F1Metric` | f1 | Maximize |

Precision, recall, and F1 use `zero_division=0`.

## Implemented regression metrics
| Class | Name | Direction |
|---|---|---|
| `MAEMetric` | mae | Minimize |
| `RMSEMetric` | rmse | Minimize |
| `R2Metric` | r2 | Maximize |
| `MAPEMetric` | mape | Minimize |

## Common interface and execution
- `metrics.py` defines the abstract `Metric` interface, including `name`, `problem_type`, `direction`, `requires_score`, and `calculate()`.
- `metric_types.py` defines base classes for classification, regression, clustering, and forecasting.
- `evaluation.py` defines `EvaluationResult`, `Evaluation.add_metric()`, and `Evaluation.evaluate()`. The runner executes registered metrics and returns structured results.
- `validation.py` defines `validate_metric_inputs()` for checking missing inputs, matching lengths, and required score values.

**Implementation limitations visible in the inspected code:** concrete metric classes are shown for classification and regression only. Clustering and forecasting are base classes, not concrete metric implementations. The validation helper is separate; the shown `Evaluation.evaluate()` does not call it. The supplied concrete metrics accept `y_score` but do not use it.

## Metric-selection guidance
The companion `docs/Metric_Selection_Guide.md` documents metric purposes and selection guidance:
- Accuracy is most useful when class distributions are reasonably balanced.
- Precision is useful when false positives are costly.
- Recall is useful when false negatives are costly.
- F1 balances precision and recall.
- MAE gives average absolute error in target units.
- RMSE penalizes larger errors more strongly.
- R² measures performance relative to predicting the target mean and may be negative.
- MAPE requires care when actual values are zero or near zero.

## Tests and current status
Focused test files are present:
```text
tests/
├── test_classification_metrics.py
├── test_evaluation.py
└── test_regression_metrics.py
```
The metric-selection guide records an earlier result of **3 passed**. A later run on 12 November 2026 was blocked during collection: SciPy's compiled extension `_ccallback_c` could not load because a Windows Application Control policy blocked the DLL. The latest attempt therefore did **not** pass. This import failure alone does not show that the metric calculations are incorrect.
