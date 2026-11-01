
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/raw")


def load_dataset(name):
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset: {path}")
    return pd.read_excel(path)


employee = load_dataset("HumanResources.Employee.xlsx")
department = load_dataset("HumanResources.Department.xlsx")
history = load_dataset("HumanResources.EmployeeDepartmentHistory.xlsx")
pay_history = load_dataset("HumanResources.EmployeePayHistory.xlsx")
shift = load_dataset("HumanResources.Shift.xlsx")
candidate = load_dataset("HumanResources.JobCandidate.xlsx")


def check_relationship(label, source, source_key, target, target_key):
    source_values = source[source_key].dropna()
    target_values = target[target_key].dropna()

    unmatched = ~source_values.isin(set(target_values))

    print(f"\n{label}")
    print(f"Source rows with a key: {len(source_values)}")
    print(f"Unmatched source keys: {int(unmatched.sum())}")


print("========== KEY VALIDATION ==========")

for label, df, key in [
    ("Employee.BusinessEntityID", employee, "BusinessEntityID"),
    ("Department.DepartmentID", department, "DepartmentID"),
    ("Shift.ShiftID", shift, "ShiftID"),
]:
    print(
        f"{label}: unique={df[key].is_unique}, "
        f"missing={df[key].isna().sum()}"
    )

print("\n========== RELATIONSHIP CHECKS ==========")

check_relationship(
    "History -> Employee",
    history, "BusinessEntityID",
    employee, "BusinessEntityID"
)

check_relationship(
    "History -> Department",
    history, "DepartmentID",
    department, "DepartmentID"
)

check_relationship(
    "History -> Shift",
    history, "ShiftID",
    shift, "ShiftID"
)

check_relationship(
    "Pay history -> Employee",
    pay_history, "BusinessEntityID",
    employee, "BusinessEntityID"
)

check_relationship(
    "Candidate -> Employee",
    candidate, "BusinessEntityID",
    employee, "BusinessEntityID"
)

print("\n========== ROW-GRAIN CHECKS ==========")
print(
    "Employees:",
    len(employee),
    "| Unique employee keys:",
    employee["BusinessEntityID"].nunique()
)
print(
    "History rows per employee (maximum):",
    history.groupby("BusinessEntityID").size().max()
)
print(
    "Pay-history rows per employee (maximum):",
    pay_history.groupby("BusinessEntityID").size().max()
)
print(
    "History rows with missing EndDate:",
    history["EndDate"].isna().sum()
)
print(
    "Candidate records without BusinessEntityID:",
    candidate["BusinessEntityID"].isna().sum()
)

print("\nValidation completed. No source files were modified.")
