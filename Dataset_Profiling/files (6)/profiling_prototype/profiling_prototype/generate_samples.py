"""Writes the sample request/response JSON files by running the real implementation."""
import copy
import json
from pathlib import Path

from profiling_service import run_profiling

HERE = Path(__file__).parent
S = HERE / "samples"


def write(name, data):
    (S / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run(name, request):
    request_file = S / f"sample_profiling_request{name}.json"
    if name:
        write(request_file.name, request)
    # always run against the real file, whatever relative path the request shows
    actual = copy.deepcopy(request)
    if isinstance(actual, dict) and isinstance(actual.get("dataset_reference"), dict):
        loc = actual["dataset_reference"].get("location", "")
        if loc == "samples/demo_customers.csv":
            actual["dataset_reference"]["location"] = str(S / "demo_customers.csv")
    write(f"sample_profiling_response{name}.json", run_profiling(actual))


base = json.loads((S / "sample_profiling_request.json").read_text(encoding="utf-8"))
run("", base)                                                   # warning (profile with warnings)

not_found = copy.deepcopy(base)
not_found["request_id"] = "req-0002"
not_found["dataset_reference"]["location"] = "samples/missing_file.csv"
run("_not_found", not_found)                                    # failed: file not found

invalid = copy.deepcopy(base)
invalid["request_id"] = "req-0003"
invalid["options"] = {"top_n_values": 0}
invalid["dataset_reference"]["source_type"] = "database"
run("_invalid", invalid)                                        # failed: invalid request
with_target = copy.deepcopy(base)
with_target["request_id"] = "req-0004"
with_target["options"]["target_column"] = "plan"
run("_with_target", with_target)                                # success: class distribution for a selected target
print("samples written")
