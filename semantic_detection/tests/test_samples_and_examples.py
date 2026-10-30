"""Every shipped sample and every example in the contract must be valid
and consistent (Meshak's review, 29 Oct)."""
import json
import re
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

_HERE = Path(__file__).resolve().parent
ROOT = next(d for d in (_HERE, _HERE.parent)
            if (d / "handoff_result.schema.json").exists())
SCHEMA = json.loads(
    (ROOT / "handoff_result.schema.json").read_text(encoding="utf-8"))
PREPROCESSING_FIELDS = {"column", "role", "semantic_type",
                        "preprocessing_actions", "sensitive",
                        "needs_privacy_review", "quality_blocked",
                        "time_axis"}
ALL = sorted((ROOT / "samples").glob("output_*.json"))
TRIMMED = [p for p in ALL if "mandatory_fields_only" in p.name]
SAMPLES = [p for p in ALL if p not in TRIMMED]  # full outputs


def results_in(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else [data]


def test_there_are_samples():
    assert len(SAMPLES) >= 4 and len(TRIMMED) == 1


@pytest.mark.parametrize("path", SAMPLES, ids=lambda p: p.name)
def test_sample_follows_schema(path):
    for result in results_in(path):
        jsonschema.validate(result, SCHEMA)


@pytest.mark.parametrize("path", SAMPLES, ids=lambda p: p.name)
def test_sample_has_mandatory_preprocessing_fields(path):
    for result in results_in(path):
        for entry in result["column_roles"]:
            assert PREPROCESSING_FIELDS <= set(entry), entry["column"]
            assert entry["preprocessing_actions"], entry["column"]


@pytest.mark.parametrize("path", SAMPLES, ids=lambda p: p.name)
def test_sample_sensitive_features_are_not_recommended(path):
    for result in results_in(path):
        held = {e["column"] for e in result["column_roles"]
                if e["role"] == "feature" and e["needs_privacy_review"]}
        assert not held & set(result["recommended_feature_columns"])
        for e in result["column_roles"]:
            if e["needs_privacy_review"]:
                assert "privacy_review_before_use" in \
                    e["preprocessing_actions"]


def test_review_decisions_schema_and_sample():
    schema = json.loads((ROOT / "review_decisions.schema.json").read_text(
        encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    sample = json.loads((ROOT / "samples" /
                         "input_review_decisions_Employee.json").read_text(
        encoding="utf-8"))
    jsonschema.validate(sample, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"dataset_id": "x", "problem_type": "banana"},
                            schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"dataset_id": "x", "approved_features": []},
                            schema)  # old name is no longer accepted


def contract_examples():
    text = (ROOT / "docs" / "HANDOFF_CONTRACT.md").read_text(encoding="utf-8")
    section = text.split("## 8. Examples")[1].split("## 9.")[0]
    return re.findall(r"```json\n(.*?)\n```", section, re.S)


def test_contract_examples_are_consistent_with_section_12():
    blocks = contract_examples()
    assert len(blocks) == 4
    for block in blocks:
        ex = json.loads(block)
        sensitive = set(ex["dataset_characteristics"]["sensitive_columns"])
        assert not sensitive & set(ex["recommended_feature_columns"])
        for entry in ex["column_roles"]:
            assert entry["preprocessing_actions"]


def test_trimmed_sample_has_every_mandatory_field():
    mandatory_top = {"dataset_id", "target", "target_confirmed",
                     "problem_type", "needs_confirmation", "features_status",
                     "feature_columns", "recommended_feature_columns",
                     "approved_feature_columns", "status", "column_roles"}
    for path in TRIMMED:
        for result in results_in(path):
            assert mandatory_top <= set(result)
            for entry in result["column_roles"]:
                assert PREPROCESSING_FIELDS <= set(entry)
                assert entry["preprocessing_actions"]
