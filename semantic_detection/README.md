# Semantic Understanding, Target Detection and Problem Classification

Team 1, GTS Data Science Intelligence and Automated ML Engine.
Owner: Samarth.

This module reads the profiling output (Sanjay) and the data quality output (Vinitha) for each dataset. It then proposes the meaning of each column, the target column, the problem type (classification, regression, forecasting, clustering) and the feature columns, and writes one JSON result per dataset for the next stages.

**Status: Prototype.** Everything is a proposal. A person must confirm the target and the features before training. See the working decisions in `docs/HANDOFF_CONTRACT.md`, section 11.

## Where to start

| If you want to... | Open |
|---|---|
| Understand what this stage does, its inputs and outputs, error handling, and what is tested versus proposed | `docs/PIPELINE_STAGE_SEMANTIC_DETECTION.md` |
| Know exactly what the output contains (for preprocessing and AutoML) | `docs/HANDOFF_CONTRACT.md` and `handoff_result.schema.json` |
| See a real input and a real output | `samples/` |
| See the test results and the open cases | `docs/TEST_REPORT.md` |
| Read the rules behind the detection | `docs/SEMANTIC_PROBLEM_SPEC.md` |
| See what the backend and frontend teams need to decide, and what is proposed versus finalized | `docs/INTEGRATION_REQUIREMENTS.md` |

## Run it

```
python run_detection.py --profiles <folder with *.profile.json> --quality <quality report .json> --output <result .json>
```

Optional: `--goal "<business goal in plain words>"`, `--override <dataset>=<target column>` (can be repeated), `--problem-type <type>`.

Tests (needs `pytest` and `jsonschema`):

```
python -m pytest -q
```

## What is in this folder

| Path | What it is |
|---|---|
| `run_detection.py` | The entry point. Joins everything below and writes the result |
| `profiling_integration.py` | Reads Sanjay's profiling output |
| `quality_integration.py` | Reads Vinitha's quality output |
| `semantic_rules.py`, `analyze_semantics.py` | Detects the meaning of each column |
| `target_suggestions.py` | Ranks the candidate target columns |
| `problem_detection.py` | Recommends the problem type |
| `leakage_checks.py` | Flags columns that may leak the target (a flag, not proof) |
| `handoff_details.py` | Builds the extra details in the output (statistics, roles) |
| `make_synthetic_datasets.py` | Makes small example datasets used by the tests |
| `handoff_result.schema.json` | The output format (JSON Schema) |
| `tests/` | The automatic tests |
| `docs/` | The documents listed above |
| `samples/` | Real input and output examples |
