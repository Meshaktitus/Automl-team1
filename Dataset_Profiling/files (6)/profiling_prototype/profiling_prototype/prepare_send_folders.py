"""Creates send/ with one folder per person, containing exactly the files to send them.
Run after:  python evidence.py data   and   python generate_hr_outputs.py data
"""
import shutil
from pathlib import Path

here = Path(__file__).parent
CONTRACT = "PROFILING_CONTRACT.md"
RESPONSE_SCHEMA = "schemas/profiling_response.schema.json"
REQUEST_SCHEMA = "schemas/profiling_request.schema.json"
SAMPLE_REQ = "samples/sample_profiling_request.json"
SAMPLE_RESP = "samples/sample_profiling_response.json"

SAMPLE_REQ_T = "samples/sample_profiling_request_with_target.json"
SAMPLE_RESP_T = "samples/sample_profiling_response_with_target.json"

four = [SAMPLE_RESP, RESPONSE_SCHEMA, SAMPLE_REQ, CONTRACT]
with_target = [SAMPLE_RESP_T, SAMPLE_REQ_T, RESPONSE_SCHEMA, REQUEST_SCHEMA, CONTRACT]
plan = {
    "1_Meshak": [CONTRACT, REQUEST_SCHEMA, RESPONSE_SCHEMA, SAMPLE_REQ, SAMPLE_RESP, SAMPLE_REQ_T, SAMPLE_RESP_T,
                 "evidence_report.txt"],
    "2_Sinchana": four,
    "3_Samarth": four + [SAMPLE_REQ_T, SAMPLE_RESP_T]
                 + sorted(str(p.relative_to(here)) for p in (here / "hr_outputs").glob("*.profile.json")),
    "4_Vinitha": [SAMPLE_RESP, RESPONSE_SCHEMA, "samples/demo_customers.csv", CONTRACT],
    "5_Sumanth": with_target,
    # Team 2 backend (Sathish): everything needed to review the API contract, including failure examples
    "6_Team2_Sathish": [CONTRACT, "PROFILING_FIELD_REFERENCE.md", "README.md", REQUEST_SCHEMA, RESPONSE_SCHEMA, SAMPLE_REQ, SAMPLE_RESP, SAMPLE_REQ_T, SAMPLE_RESP_T,
                        "samples/sample_profiling_response_not_found.json", "samples/sample_profiling_response_invalid.json",
                        "samples/sample_profiling_request_not_found.json", "samples/sample_profiling_request_invalid.json",
                        "evidence_report.txt"],
    # One uniform package for the contract review: every reviewer gets the same schemas, field reference, contract and samples
    "0_Review_Package": [REQUEST_SCHEMA, RESPONSE_SCHEMA, "PROFILING_FIELD_REFERENCE.md", CONTRACT, "PROFILING_KNOWN_ISSUES.md",
                         *sorted(str(p.relative_to(here)) for p in (here / "samples").glob("sample_profiling_*.json"))],
    # Meshak's consolidated integration requirements: contract, schemas, samples and all evidence
    "8_Meshak_Consolidated": [CONTRACT, "PROFILING_FIELD_REFERENCE.md", "PROFILING_KNOWN_ISSUES.md", REQUEST_SCHEMA, RESPONSE_SCHEMA,
                              *sorted(str(p.relative_to(here)) for p in (here / "samples").glob("sample_profiling_*.json")),
                              "unit_test_report.txt", "evidence_report.txt", "integration_results.txt",
                              "hr_validation_report.txt", "profiling_baseline_report.txt", "demonstration_report.txt", "benchmark_results.txt", "benchmark_results.json",
                              *sorted(str(p.relative_to(here)) for p in (here / "hr_outputs").glob("*.profile.json"))],
    # Contract review package: everything a reviewer needs to confirm "No changes needed" or "Changes needed"
    "9_Contract_Review": [CONTRACT, "PROFILING_FIELD_REFERENCE.md", "PROFILING_KNOWN_ISSUES.md", REQUEST_SCHEMA, RESPONSE_SCHEMA,
                          "profiling.types.ts",
                          *sorted(str(p.relative_to(here)) for p in (here / "samples").glob("sample_profiling_*.json"))],
    # Day 4 (Thursday): regression evidence for the Team Lead
    "10_Day4_Regression_Evidence": ["profiling_regression_report.txt", "test_profiling_regression.py", "unit_test_report.txt",
                                    "evidence_report.txt", "integration_results.txt", "hr_validation_report.txt",
                                    "profiling_baseline_report.txt", "benchmark_results.txt", "benchmark_results.json"],
    # Day 5 (Friday): module handover and final evidence
    "11_Day5_Handover": ["PROFILING_HANDOVER.md", "README.md", CONTRACT, "PROFILING_FIELD_REFERENCE.md", "PROFILING_KNOWN_ISSUES.md",
                         REQUEST_SCHEMA, RESPONSE_SCHEMA, "profiling.types.ts",
                         *sorted(str(p.relative_to(here)) for p in (here / "samples").glob("sample_profiling_*.json")),
                         "unit_test_report.txt", "evidence_report.txt", "integration_results.txt", "hr_validation_report.txt",
                         "demonstration_report.txt", "benchmark_results.txt", "profiling_regression_report.txt"],
    # Team 3 frontend: success and failure responses, schemas and the field reference
    "7_Team3_Frontend": [SAMPLE_RESP, SAMPLE_RESP_T, "samples/sample_profiling_response_not_found.json",
                         "samples/sample_profiling_response_invalid.json", RESPONSE_SCHEMA, REQUEST_SCHEMA, "profiling.types.ts",
                         "PROFILING_KNOWN_ISSUES.md", "PROFILING_FIELD_REFERENCE.md", CONTRACT],
}

out = here / "send"
if out.exists():
    shutil.rmtree(out)
problems = []
for person, files in plan.items():
    (out / person).mkdir(parents=True)
    for name in files:
        src = here / name
        if src.exists():
            shutil.copy(src, out / person / src.name)
        else:
            problems.append(f"{person}: missing {name}")
    print(f"{person}: {len(list((out / person).iterdir()))} file(s)")
if not (here / "hr_outputs").is_dir() or not list((here / "hr_outputs").glob("*.profile.json")):
    problems.append("3_Samarth: no hr_outputs found. Run: python generate_hr_outputs.py data")
for p in problems:
    print("PROBLEM:", p)
print("Done. Open the 'send' folder and attach each person's files to their message." if not problems else "Fix the problems above and run again.")
