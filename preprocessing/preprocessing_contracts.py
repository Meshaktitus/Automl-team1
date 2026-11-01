
import json
from pathlib import Path

from jsonschema import Draft202012Validator


# Resolve paths from the project root, not the current terminal directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = PROJECT_ROOT / "schemas"


class ContractValidationError(ValueError):
    """Raised when a request or response does not match its schema."""


def load_json(path):
    """Load a JSON file and return its contents."""
    path = Path(path)

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}"
        ) from exc


def _validate(payload, schema_name):
    """Validate a Python dictionary against a project JSON schema."""
    schema_path = SCHEMA_DIR / schema_name

    if not schema_path.is_file():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)

    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: list(map(str, error.absolute_path)),
    )

    if errors:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path)
            location = location or "<root>"
            details.append(f"{location}: {error.message}")

        raise ContractValidationError(
            f"{schema_name} validation failed:\n" + "\n".join(details)
        )

    return True


def validate_preprocessing_request(payload):
    """Validate an incoming preprocessing request."""
    return _validate(payload, "preprocessing_request.schema.json")


def validate_preprocessing_response(payload):
    """Validate an outgoing preprocessing response."""
    return _validate(payload, "preprocessing_response.schema.json")
