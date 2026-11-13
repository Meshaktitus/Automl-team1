"""Run the profiler on the six HumanResources tables sent by the backend team."""
import sys
from profiler import load_tables, profile_tables, to_json

folder = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads"
result = profile_tables(load_tables(folder))
open("hr_profile_report.json", "w").write(to_json(result))
for name, rep in result["tables"].items():
    d = rep["dataset"]
    print(f"{name}: {d['row_count']} rows x {d['column_count']} cols, "
          f"{d['duplicate_row_count']} duplicates, status={rep['status']}")
    for w in rep["warnings"]:
        print("   -", w)
print("relationships:", len(result["relationships"]))
for r in result["relationships"]:
    print("  ", r)
