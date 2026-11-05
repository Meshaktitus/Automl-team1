# Module coverage report: Semantic Understanding, Target Detection and Problem Classification

Owner: Samarth (Team 1). Date: Thu 5 Nov 2026. Status: **Proposed — Pending Review**. Total: **346 tests, all passing**.
This report maps behaviour to tests. It is not a line-coverage percentage; no line-coverage tool was run.

## 1. Tests per file

| Test file | Tests | What it covers |
|---|---|---|
| test_semantic_rules.py | 26 | 12 semantic types, value and name rules, sensitive flag |
| test_target_suggestions.py | 19 | target ranking, exclusions, overrides |
| test_problem_detection.py | 31 | problem-type rules, goal precedence, feasibility, confidence |
| test_profiling_integration.py | 14 | reading Sanjay's profile, required fields, failed profiles |
| test_quality_integration.py | 36 | Vinitha's rule IDs, severities, penalties, routing by dataset |
| test_run_detection.py | 33 | single entry point, overrides, approved features, roles |
| test_cross_dataset.py | 26 | healthcare, banking, telecom, education, retail, anonymous and empty columns |
| test_leakage_checks.py | 18 | correlation thresholds, flags without removal, limits |
| test_handoff_details.py | 13 | target statistics, preprocessing actions, time info |
| test_handoff_schema.py | 8 | real results follow `handoff_result.schema.json` |
| test_training_rules.py | 9 | training eligibility rules |
| test_samples_and_examples.py | 16 | shipped samples, contract examples, review-decisions schema |
| test_robustness.py | 32 | bad, empty and odd inputs |
| test_integration_day3.py | 5 | real HR profile plus quality report, missing target, user target |
| test_input_validation.py | 26 | incomplete or failed profiling and quality input, CSV and Excel consistency |
| test_thursday_regression.py | 34 | all 7 fixtures, goals, identifier targets, confidence and evidence, leakage kept, D7 |

## 2. Behaviour against sprint acceptance criteria (plan section 4.3)

| Acceptance criterion | Covered by | Status |
|---|---|---|
| Semantic column classification | test_semantic_rules, test_cross_dataset, test_thursday_regression | Tested |
| Date and identifier detection | test_semantic_rules, test_thursday_regression (D7) | Tested |
| Numerical and categorical interpretation | test_semantic_rules, test_cross_dataset | Tested |
| Candidate target-column identification | test_target_suggestions, test_thursday_regression | Tested |
| Supported ML problem-type detection | test_problem_detection, test_thursday_regression | Tested for the 8 types; D1, D2, D6 open |
| Confidence and evidence reporting | test_thursday_regression, test_handoff_schema | Tested |
| Handling of ambiguous columns | test_thursday_regression, test_robustness | Tested |
| Human confirmation where confidence is insufficient | test_integration_day3, test_thursday_regression, test_training_rules | Tested |

## 3. Not covered

- Real profiler output for the 7 synthetic fixtures (fixtures use test-built profiles).
- The path through preprocessing and AutoML (their interfaces are not confirmed).
- Leakage beyond numerical pairs; large-column performance and memory.
- Line-coverage percentage (no coverage tool run).
