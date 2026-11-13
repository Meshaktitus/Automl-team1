# Role and action mapping: semantic detection to preprocessing

For: Sinchana (preprocessing). From: Samarth (semantic detection). Date: Thu 5 Nov 2026.
Status: **Proposed — Pending Review.** Nothing here is agreed until Sinchana confirms her side. Source of the values: `handoff_result.schema.json` and `handoff_details.py`.

## 1. Roles

My `column_roles[].role` has 7 values; your feature list has 4 (`feature`, `target`, `identifier`, `excluded`). Proposed mapping:

| My role | Your role | What to do with the column | Notes |
|---|---|---|---|
| `target` | `target` | Never transform (as today) | Use only the confirmed target (`target_confirmed` true) |
| `feature` | `feature` | Apply the column's `preprocessing_actions` | Only if the column is in `approved_feature_columns` |
| `identifier` | `identifier` | Keep for joining; do not feed to the model | Same as today |
| `excluded` | `excluded` | Drop from model input | Audit or constant columns |
| `date` (not the time axis) | `feature` (derived) | Replace by derived parts: action `extract_date_features` | Do not scale or encode the raw date |
| `date` on the time axis (`time_axis` true) | `excluded` from features, keep as ordering key | Action `time_index` | Used by forecasting; return a step `time_index` with status `skipped` or `review_required` if not supported yet |
| `time` | `feature` (derived) | Action `extract_time_parts` (hour, minute) | Return `skipped` if not supported yet |
| `text` | `excluded` for now | Action `text_processing` | Return a `review_required` step; text must not be fed to the model raw |

## 2. Actions

`preprocessing_actions` is a fixed list (17 values). Proposed mapping to the options I saw in your service (`handle_missing_values`, `extract_date_features`, `encode_categorical`, `scale_numeric`, `rare_category_threshold`); please correct me where I read your code wrongly.

| My action | Your operation | If not supported yet |
|---|---|---|
| `impute` | `handle_missing_values` | n/a |
| `extract_date_features` | `extract_date_features` | n/a |
| `one_hot_encode` | `encode_categorical` (one-hot) | n/a |
| `group_rare_categories` | `rare_category_threshold` | `skipped` |
| `scale_numeric` | `scale_numeric` | n/a |
| `encode_binary` | not seen | `skipped` |
| `label_encode` (classification target) | not seen | `skipped`; the target must stay unmodified, so this is only a note for the model stage |
| `frequency_or_target_encode` | not seen | `skipped`, or fall back to one-hot only if cardinality is small |
| `convert_percentage_to_number` | not seen | `skipped` |
| `extract_time_parts` | not seen | `skipped` |
| `time_index` | not seen | `review_required` |
| `text_processing` | not seen | `review_required` |
| `use_as_target`, `do_not_use_as_input`, `keep_for_join`, `drop` | role handling (section 1) | n/a |
| `privacy_review_before_use` | no transformation | `review_required` unless the column is in `approved_feature_columns` |

## 3. Other fields to carry

- `leakage_suspect` (`possible`, `strong`, or null; Proposed): carry it as a flag on the feature; do not drop the column.
- `sensitive` and `needs_privacy_review`: sensitive columns are not in `recommended_feature_columns` and are used only after the user approves them.
- Use only `approved_feature_columns` as the feature list.

## 4. Checked against the actual preprocessing code (Fri 6 Nov 2026)

Source: Sinchana's package as received (`preprocessing_service.py`, `integration_service.py`, `preprocessing_response.schema.json`). I read the code; I have **not** run her service on my output, and she has not confirmed this section. Her tests need Sanjay's profiling folder, which I do not have here.

### 4.1 What her service reads today

`dataset`, `target`, `preprocessing_options` (`handle_missing_values`, `extract_date_features`, `encode_categorical`, `scale_numeric`, `rare_category_threshold`), `profiling_metadata` (only `likely_identifier`), `quality_findings` / `data_quality_result`. Each option acts on the **whole dataset** (every column except the target and identifiers), not on a list of columns.

It does **not** read: `approved_feature_columns`, `features_status`, `column_roles`, `preprocessing_actions`, `sensitive`, `needs_privacy_review`, `leakage_suspect`, `target_confirmed`, `problem_type`.

### 4.2 Fields

| My field | Her side | State |
|---|---|---|
| `target` (confirmed) | `target` | **Supported** (name matches) |
| `column_roles[].role`, `approved_feature_columns` | none; she assigns `feature`, `target`, `identifier` herself (response schema also allows `excluded`, never set by the code I read) | **Unsupported today.** All non-target, non-identifier columns become `feature`, including sensitive ones and ones the user did not approve |
| `sensitive`, `needs_privacy_review` | none | **Unsupported.** A sensitive column the user did not approve would still be encoded and passed on |
| `leakage_suspect` | none | **Pending** (she agreed to carry it as a flag) |
| `quality_issues` | `quality_findings` | **Different shape**; she maps severity to `info`/`warning`/`error`, blocks on `critical`/`blocking` only. `Warning / Audit` is not in her map (see `QUALITY_REPORT_CONTRACT.md`) |
| `preprocessing_hint` | none | Free text; not used |

### 4.3 Actions

| `preprocessing_actions` value | Her service | State |
|---|---|---|
| `impute` | `handle_missing_values`: median for numbers, most frequent for text; skips dates | **Supported** (whole dataset) |
| `extract_date_features` | `extract_date_features`: year, month, quarter, day of week; drops the raw date | **Supported** (option default off) |
| `one_hot_encode` | `encode_categorical`: one-hot, identifiers excluded | **Supported** (whole dataset) |
| `group_rare_categories` | `rare_category_threshold` (default 0.05), values below the share become "Other" | **Supported**, but only together with `encode_categorical` |
| `scale_numeric` | `scale_numeric`: `StandardScaler` | **Supported** (option default off) |
| `keep_for_join`, `do_not_use_as_input` | identifiers are left out of encoding, kept in the output; by name rules and `likely_identifier` | **Partly supported** (own heuristics, may differ from my roles) |
| `use_as_target` | target is never transformed | **Supported** |
| `drop` | none | **Unsupported** |
| `encode_binary`, `label_encode`, `frequency_or_target_encode`, `convert_percentage_to_number`, `extract_time_parts`, `time_index`, `text_processing` | none | **Unsupported.** Proposed: return the step with status `skipped` (or `review_required` for `time_index`, `text_processing`) |
| `privacy_review_before_use` | none | **Unsupported.** Proposed: `review_required` unless the column is approved |

### 4.4 What has to change before the two modules can be run together

1. She needs to accept the approved feature list, and leave out everything else (her side).
2. She needs to stop treating unapproved sensitive columns as features (her side).
3. Per-column actions: map each column's `preprocessing_actions` to her options, or accept the list directly (her side, her decision).
4. Severity labels: agree on one list (Vinitha and Sinchana).
5. Until then, a caller must not pass my output to her service as if it were already supported.

