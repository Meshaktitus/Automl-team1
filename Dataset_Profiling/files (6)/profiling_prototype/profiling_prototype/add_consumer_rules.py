"""Adds (or refreshes) the 'Scope and consumer rules' section in PROFILING_CONTRACT.md and PROFILING_KNOWN_ISSUES.md.
Usage:  python add_consumer_rules.py        Safe to run more than once: it replaces its own section and leaves everything else alone.
"""
from pathlib import Path

HERE = Path(__file__).parent

CONTRACT_SECTION = """## Scope and consumer rules (clarified in response to review)

1. **Scope.** Profiling reports measured facts: dimensions, detected types (numerical, categorical, datetime, time, text, boolean, mixed, empty), missingness, distinct counts, duplicates, statistics, distributions, correlations, class distribution and warnings. It does **not** provide semantic types (for example email, currency or percentage), quality judgements, recommended actions or recommended preprocessing steps. Those belong to other modules under their own contracts.
2. **One target per request.** `options.target_column` is a single column name. Simultaneous multi-target prediction is not supported in v1.0, and a list is rejected as `INVALID_REQUEST`. To profile several candidate targets, send one request per target: the column profiles are identical and only `class_distribution` differs.
3. **Class distribution and continuous targets.** A categorical, boolean or numerical target with at most 20 distinct values gets `class_distribution`. A target with more than 20 distinct values, or an identifier or text target, gets no class distribution and the info warning `CLASS_DISTRIBUTION_SKIPPED`. For a continuous numerical target, use the target's own `columns[]` entry (missing count and percent, `summary` with min, max, mean, median, standard deviation, Q1, Q3 and skewness, and `histogram`) and `correlations`. Identifier columns carry no statistics by design.
4. **`status: "warning"`.** It is used whenever `warnings[]` is not empty, including informational warnings (`severity: "info"`). It does not mean the profile is unusable. Use each warning's `severity` to decide what to surface.
5. **`status: "failed"`.** No profile was produced: `dataset` is null, `columns` is empty and `errors[]` has at least one item. Consumers should stop processing and report `errors[]`.
6. **Forward compatibility.** Consumers should tolerate warning and error codes they do not recognise, because later versions may add codes.
7. **File loading and text columns.** When profiling reads a CSV or XLSX file itself, blank and whitespace-only text cells count as missing, and duplicate column names are reported as `DUPLICATE_COLUMN_NAMES` instead of being renamed by the reader. When the caller passes a table, the caller's own loader decides what is missing. In every case, a text column that mixes numbers and words is `mixed` (with the warning `MIXED_TYPES`), and text made only of true and false values is `boolean`. Rows with too few fields are read as missing values, so structural CSV validation belongs upstream of profiling.
"""

ISSUES_SECTION = """## 7. Scope decisions

- One target column per request. Simultaneous multi-target prediction is not part of v1.0; several targets need one request each. A multi-target option would be an additive change in a later version, and only if it is confirmed as in scope.
- Semantic types, quality judgements and preprocessing recommendations are outside profiling.
"""


REVIEW_FIXES = """## 8. Fixed after the comparison with another team's profiler

| Defect | Fix | Test |
|---|---|---|
| A CSV column mixing numbers and words (for example 25, 30, unknown, 35) was reported as categorical | Reported as `mixed` with `MIXED_TYPES` | `test_numbers_mixed_with_words_are_reported_as_mixed` |
| Text true/false values with missing cells were reported as categorical | Reported as `boolean` | `test_missing_values_sample_counts_and_percentages` |
| Whitespace-only cells in a file counted as values | Counted as missing; a numeric column stays numeric | `test_whitespace_only_cells_count_as_missing_in_files` |
| Duplicate column names in a file were silently renamed (a, a.1) | Reported as `DUPLICATE_COLUMN_NAMES` | `test_duplicate_header_in_a_file_is_reported_not_renamed` |

Remaining differences: rows with too few fields are read as missing values (structural CSV validation belongs upstream); neither profiler detects the delimiter.
"""


def upsert(path, marker, body):
    start, end = f"<!-- {marker}-start -->", f"<!-- {marker}-end -->"
    block = f"{start}\n{body.rstrip()}\n{end}\n"
    text = path.read_text(encoding="utf-8")
    if start in text and end in text:
        head, rest = text.split(start, 1)
        text = head + block + rest.split(end, 1)[1].lstrip("\n")
    else:
        text = text.rstrip("\n") + "\n\n" + block
    path.write_text(text, encoding="utf-8")
    print(f"Updated {path.name}")


upsert(HERE / "PROFILING_CONTRACT.md", "consumer-rules", CONTRACT_SECTION)
upsert(HERE / "PROFILING_KNOWN_ISSUES.md", "scope-decisions", ISSUES_SECTION)
upsert(HERE / "PROFILING_KNOWN_ISSUES.md", "team5-review-fixes", REVIEW_FIXES)
