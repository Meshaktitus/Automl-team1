"""Integration layer connecting dataset profiling and preprocessing."""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILING_DIR = (
    PROJECT_ROOT / "profiling_prototype" / "profiling_prototype"
)

if str(PROFILING_DIR) not in sys.path:
    sys.path.insert(0, str(PROFILING_DIR))

from profiling_service import run_profiling
from app.preprocessing.preprocessing_service import preprocess_request


def run_integrated_preprocessing(request):
    """Profile a dataset first, then preprocess it if profiling succeeds."""

    if not isinstance(request, dict):
        return {
            "status": "failed",
            "profiling": None,
            "preprocessing": None,
            "warnings": [],
            "error": {
                "code": "INVALID_REQUEST",
                "message": "The request must be a JSON object.",
            },
        }

    dataset = request.get("dataset", {})
    dataset_id = dataset.get("dataset_id", "")
    location = dataset.get("location", "")
    file_format = str(dataset.get("format", "")).lower()
    target = request.get("target")

    # Build a request using the profiling module's own contract.
    profiling_request = {
        "schema_version": "1.0-draft",
        "request_id": str(request.get("request_id", "integration-request")),
        "dataset_reference": {
            "dataset_id": str(dataset_id),
            "name": str(dataset_id),
            "source_type": "file",
            "location": str(location),
        },
        "metadata": {
            "format": file_format,
        },
        "options": {
            "include_statistics": True,
            "include_correlations": True,
        },
    }

    if target:
        profiling_request["options"]["target_column"] = str(target)

    # Run profiling before preprocessing.
    profile = run_profiling(profiling_request)

    if profile.get("status") == "failed":
        return {
            "status": "failed",
            "profiling": profile,
            "preprocessing": None,
            "warnings": [],
            "error": {
                "code": "PROFILING_FAILED",
                "message": "Preprocessing was stopped because profiling failed.",
            },
        }

    # Convert profiling warnings into the preprocessing warning format.
    profile_warnings = [
        {
            "code": "PROFILE_" + str(item.get("code", "WARNING")),
            "severity": item.get("severity", "warning"),
            "message": item.get("message", "Profiling warning."),
        }
        for item in profile.get("warnings", [])
    ]

    # Pass the original preprocessing request to the existing service.
    preprocessing = preprocess_request(request)

    # Preserve both modules' warnings in the combined result.
    preprocessing_warnings = preprocessing.get("warnings", [])
    combined_warnings = profile_warnings + preprocessing_warnings

    preprocessing_status = preprocessing.get("status")

    if preprocessing_status == "failed":
        combined_status = "failed"
    elif preprocessing_status == "review_required":
        combined_status = "review_required"
    elif profile.get("status") == "warning" or combined_warnings:
        combined_status = "partial_success"
    else:
        combined_status = "success"

    return {
        "status": combined_status,
        "profiling": profile,
        "preprocessing": preprocessing,
        "warnings": combined_warnings,
        "error": preprocessing.get("error"),
    }
