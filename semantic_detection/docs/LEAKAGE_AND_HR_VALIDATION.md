# Leakage check: what it does, what it does not do, and the HR relationship to validate

For: Meshak, HR validation. From: Samarth. Date: Fri 6 Nov 2026. Status: **Proposed — Pending Review** (thresholds are not from the SRS).

## 1. Rule

Leakage is a **warning, never an automatic removal**. A flagged column stays in `recommended_feature_columns` and, if the user approves it, in `approved_feature_columns`. Only the person reviewing the dataset can say whether the column would be known at prediction time. Tests: `test_leakage_checks.py` (18, fixtures) and `test_real_inputs.py` (real HR profile).

## 2. Limit (also written in the output as `leakage_checks.limits`)

The check compares the target with **numerical columns only, by straight-line (Pearson) correlation**, using the correlations in Sanjay's profile. A high correlation is a hint, not proof. It does **not** find:
- leakage from categorical columns (the check does not look at them);
- a column derived from the target (for example a formula or a renamed copy with a low correlation);
- time-based leakage (information from after the prediction moment);
- relationships that are not straight-line;
- anything when the target is categorical or not chosen yet (`status: "not_checked"`).

So a clean result does not mean the dataset has no leakage.

Thresholds: 0.80 gives `possible`, 0.95 gives `strong` (Proposed, can be changed in the settings).

## 3. HR validation: `SickLeaveHours` and `VacationHours`

Run: real HR Employee profile from Sanjay (290 rows), target `VacationHours` chosen by the user, problem type regression.

| Item | Value |
|---|---|
| Correlation | +0.9783 |
| Level | `strong` (above 0.95) |
| Output | `column_roles[SickLeaveHours].leakage_suspect = "strong"`, `leakage_correlation = 0.9783`, one warning in `warnings` |
| Column removed? | No. It is still recommended, and it is approved when the user approves it |

What to ask HR (Meshak):
1. What does each column mean: are both hours recorded for the same period, so that they move together by design (for example both depend on length of service or a job group), or is one calculated from the other?
2. Would `SickLeaveHours` be known at the moment a `VacationHours` prediction is needed? If not, it should not be a feature.
3. Is a model of `VacationHours` from `SickLeaveHours` a meaningful business question? The business objective and target are not confirmed yet (decision list, item 5).

My reading of the data stops here: a correlation of 0.98 on 290 rows shows that the two columns are almost the same measure, but the file cannot say why, or which one is known first. That judgement needs HR.
