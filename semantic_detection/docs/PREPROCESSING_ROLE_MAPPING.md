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
