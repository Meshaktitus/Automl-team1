# Evaluation Framework v1

## Metric Selection Guide

**Project:** Team 1 AI/ML
**Module:** Model Evaluation Framework
**Prepared by:** Sinchana
**Day:** 5

### 1. Objective

The objective of this document is to explain the evaluation metrics implemented in the framework and describe when each metric is useful.

### 2. Classification Metrics

| Metric    | Purpose                                                          | Selection Guidance                        |
| --------- | ---------------------------------------------------------------- | ----------------------------------------- |
| Accuracy  | Measures the proportion of correct predictions                   | Use when classes are reasonably balanced  |
| Precision | Measures how many predicted positive cases are actually positive | Use when false positives are costly       |
| Recall    | Measures how many actual positive cases are correctly identified | Use when false negatives are costly       |
| F1 Score  | Combines precision and recall                                    | Use when both precision and recall matter |

### 3. Regression Metrics

| Metric | Purpose                                                      | Selection Guidance                                                                     |
| ------ | ------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| MAE    | Average absolute prediction error                            | Use for an interpretable average error in target units                                 |
| RMSE   | Gives greater weight to larger errors                        | Use when large prediction errors should be penalized more                              |
| R²     | Measures performance relative to predicting the target mean  | Use to assess explained variation; it can be negative                                  |
| MAPE   | Measures absolute prediction error relative to actual values | Use for percentage-style errors when actual values are nonzero and suitable for ratios |

### 4. Important Limitations

* Accuracy can be misleading when classes are imbalanced.
* Precision and recall depend on the positive class definition.
* F1 does not include true negatives directly.
* MAE and RMSE are expressed in the target variable's units.
* RMSE penalizes large errors more heavily than MAE.
* R² may be negative and does not by itself establish that a model is suitable.
* MAPE can be unstable or misleading when actual values are zero or close to zero.

### 5. Direction of Improvement

**Higher is better:** Accuracy, Precision, Recall, F1, R².

**Lower is better:** MAE, RMSE, MAPE.

### 6. Testing Summary

The current automated test suite contains three test functions:

* Evaluation framework test
* Classification metrics integration test
* Regression metrics integration test

Latest recorded test result: **3 passed**.

### 7. Conclusion

The framework currently implements four classification metrics and four regression metrics. The `Evaluation` module can register metrics, execute them through the common metric interface, and return structured evaluation results.

**Framework status:** Evaluation Framework v1 — initial implementation and integration tests completed.
