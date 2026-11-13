# Quality report contract: what this module reads from Vinitha's output

For: Vinitha (data quality), Sinchana (preprocessing). From: Samarth. Date: Fri 6 Nov 2026.
Status: **Proposed — Pending Review.** The field names, issue types and severity levels below are what the two real reports received so far contain, and what `quality_integration.py` accepts. Vinitha has not yet confirmed them as final. The two JSON examples are copied from her real files (`samples/input_quality_all_tables.json`, `samples/input_quality_Employee_rerun.json`), not written by me.

## 1. Report shape

One file holds a list with one entry per dataset (an entry with `dataset`, `total_rows`, `issues`). A single object with `dataset` and `issues` is also accepted. The older name `detected_issues` for the list is still accepted. A report with `"status": "failed"` is rejected with a message, and the run goes on without quality adjustment (warning `quality_problem`).

| Field | Where | Type | Meaning | Required by this module |
|---|---|---|---|---|
| `dataset` | report entry | text | Dataset name, as in the profile (`HumanResources.Employee.xlsx` or `HumanResources.Employee`; case and file ending are ignored) | Yes, on the entry or on each issue |
| `total_rows` | report entry | number | Row count of the dataset | No (not used) |
| `issues` | report entry | list | The findings | Yes |
| `rule_id` | issue | text | Rule that fired | Yes |
| `severity` | issue | text | One of the labels in section 3 | Yes (unknown label is treated as a warning, with a note) |
| `affected_column` | issue | text | One column, a list, or a composite (`"A, B"`, `"A + B"`). Empty, `none`, `n/a` mean a table-level finding | Yes (`column` is also accepted) |
| `affected_rows` | issue | number, `{count, percentage}` or text such as `"2 records (0.34%)"` | How many rows | No. 0 rows means the check passed and nothing is listed |
| `recommended_action` | issue | text | Suggested action | No (shown in the note) |
| `description` | issue | text | Longer text | No |

## 2. Representative examples (real output)

Six-table report (`input_quality_all_tables.json`, first dataset, shortened):

```json
[{
  "dataset": "HumanResources.Employee.xlsx",
  "total_rows": 290,
  "issues": [
    {"rule_id": "NULL_CHECK", "severity": "Info",
     "affected_column": "OrganizationLevel", "affected_rows": 1,
     "recommended_action": "Root organizational node (CEO); expected structural null."}
  ]
}]
```

Employee re-run (`input_quality_Employee_rerun.json`, converted from Vinitha's text report):

```json
{
  "dataset": "HumanResources.Employee.xlsx",
  "total_rows": 290,
  "issues": [
    {"rule_id": "RULE_INVALID_RANGE_HIRE_AGE", "severity": "Warning / Audit",
     "affected_column": "BirthDate, HireDate", "affected_rows": 2,
     "recommended_action": "Audit"},
    {"rule_id": "RULE_NULL_STRUCTURAL", "severity": "Low",
     "affected_column": "OrganizationNode, OrganizationLevel", "affected_rows": 2,
     "recommended_action": "Do not impute"}
  ]
}
```

## 3. Severity levels (observed in the two real files, and how this module groups them)

| Label seen | Seen in | Module level | Effect |
|---|---|---|---|
| `Info` | six-table report | warning | Note only |
| `Low` | Employee re-run | warning | Note only |
| `Warning` | six-table report | warning | Note only |
| `Warning / Audit` | Employee re-run | warning | Note only. **Added today**: before it was read as an unknown label (still treated as a warning, but flagged "unknown severity") |
| `Medium` | not seen yet | medium | Score x 0.85, confidence -0.05 |
| `High`, `Error` | `Error` in the six-table report | error | Score x 0.6, confidence -0.10, confirmation needed |
| `Blocking` | not seen yet | blocking | Column marked "Blocked by quality", ranked last |

## 4. Issue types (`rule_id`) seen

| `rule_id` | Seen in | Handling |
|---|---|---|
| `NULL_CHECK`, `RULE_NULL_STRUCTURAL` | both | Note only (nulls are handled by the ranking) |
| `INVALID_RANGE`, `RULE_INVALID_RANGE_HIRE_AGE` | both | Penalty according to severity |

The note-only prefixes are `MISSING`, `NULL`, `CONSTANT`, `KEY`, `REF`, `DUP` (after removing a leading `RULE_`). Other rule IDs are accepted and use the severity.

## 5. Differences between the two real reports (to settle with Vinitha)

1. Rule IDs differ for the same kind of check (`NULL_CHECK` and `RULE_NULL_STRUCTURAL`; `INVALID_RANGE` and `RULE_INVALID_RANGE_HIRE_AGE`).
2. Severity labels differ (`Info`/`Error` against `Warning / Audit`/`Low`). Proposal: one fixed list: `Info`, `Low`, `Warning`, `Medium`, `High`, `Blocking`.
3. The re-run came as a text report and was converted to this format by me; the other five tables are not re-run yet.
4. One count (structural nulls: 2 records in the re-run, 1 in the profile) is still to confirm.
5. Preprocessing reads severities differently: Sinchana's service only blocks on `critical` or `blocking`, and maps labels to `info`/`warning`/`error`. `Warning / Audit` is not in her map, so it would be passed through unchanged, which her response schema (`info`, `warning`, `error` only) does not allow. This was found by reading her code; the end-to-end run has not been done.
