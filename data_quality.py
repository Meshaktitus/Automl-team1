import pandas as pd
<<<<<<< HEAD
import numpy as np

class DataQualityEngine:
    def __init__(self, df, dataset_name="Dataset", target_col=None, id_cols=None):
        self.df = df.copy()
        self.dataset_name = dataset_name
        self.target_col = target_col
        self.id_cols = id_cols if id_cols else []
        self.issues = []

    def add_issue(self, rule_id, category, severity, column, affected_count, description, recommendation):
        self.issues.append({
            "Dataset": self.dataset_name,
            "RuleID": rule_id,
            "Category": category,
            "Severity": severity,
            "Column": column,
            "AffectedRows": int(affected_count),
            "Description": description,
            "Recommendation": recommendation
        })

    def run_checks(self):
        # 1. Missing Value / Missing Target Checks
        for col in self.df.columns:
            missing_count = self.df[col].isnull().sum()
            if missing_count > 0:
                is_target = (col == self.target_col)
                severity = "Blocking Error" if is_target else "Warning"
                category = "Missing Target" if is_target else "Missing Values"
                self.add_issue("VAL_NULL_001", category, severity, col, missing_count,
                               f"Column '{col}' contains {missing_count} missing values.",
                               "Apply imputation or drop rows if target is missing.")

        # 2. Duplicate Identifier Checks
        for id_col in self.id_cols:
            if id_col in self.df.columns:
                dup_count = self.df[id_col].duplicated().sum()
                if dup_count > 0:
                    self.add_issue("VAL_DUP_001", "Duplicate Identifiers", "Blocking Error", id_col, dup_count,
                                   f"Identifier column '{id_col}' contains {dup_count} duplicate entries.",
                                   "Investigate primary key relationship or composite keys.")

        # 3. Numerical Outliers (IQR) & Confirmed Invalid Values
        num_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in num_cols:
            series = self.df[col].dropna()
            if len(series) == 0: continue
            
            # Confirmed Invalid Values (Domain Rules, e.g. negative values)
            invalid_mask = series < 0
            inv_count = invalid_mask.sum()
            if inv_count > 0:
                self.add_issue("VAL_INV_001", "Confirmed Invalid Values", "Blocking Error", col, inv_count,
                               f"Column '{col}' contains {inv_count} physically impossible negative values.",
                               "Correct data entry error or filter out.")
            
            series_valid = series[~invalid_mask]
            
            # Interquartile Range (IQR) Outlier Detection
            if len(series_valid) > 4:
                Q1 = series_valid.quantile(0.25)
                Q3 = series_valid.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outliers = series_valid[(series_valid < lower_bound) | (series_valid > upper_bound)]
                if len(outliers) > 0:
                    self.add_issue("VAL_OUT_001", "Statistical Outliers", "Warning", col, len(outliers),
                                   f"Column '{col}' has {len(outliers)} statistical outliers beyond IQR bounds.",
                                   "Retain data; apply robust scaling or winsorization.")

        return pd.DataFrame(self.issues)

# --- Execute on HR Datasets ---
files_to_check = [
    ('Employee', 'HumanResources.Employee (1).xlsx', 'BusinessEntityID', 'VacationHours'),
    ('PayHistory', 'HumanResources.EmployeePayHistory.xlsx', 'BusinessEntityID', 'Rate'),
    ('Department', 'HumanResources.Department (1).xlsx', 'DepartmentID', None),
    ('JobCandidate', 'HumanResources.JobCandidate (1).xlsx', 'JobCandidateID', None),
    ('EmployeeDepartmentHistory', 'HumanResources.EmployeeDepartmentHistory (1).xlsx', 'BusinessEntityID', None)
]

all_issues = []
for name, filename, id_col, target_col in files_to_check:
    try:
        xl = pd.ExcelFile(filename)
        df = pd.read_excel(filename, sheet_name=xl.sheet_names[0])
        engine = DataQualityEngine(df, dataset_name=name, target_col=target_col, id_cols=[id_col])
        res = engine.run_checks()
        if not res.empty:
            all_issues.append(res)
    except Exception as e:
        print(f"Skipping {name} due to error: {e}")

if all_issues:
    master_report = pd.concat(all_issues, ignore_index=True)
    print("=== MASTER DATA QUALITY REPORT ===")
    print(master_report[['Dataset', 'Category', 'Severity', 'Column', 'AffectedRows', 'Description']])
    
    # Optionally save to CSV for your team repository
    master_report.to_csv("quality_summary_report.csv", index=False)
    print("\n[INFO] Quality report successfully saved to 'quality_summary_report.csv'.")
else:
    print("No issues found across datasets.")
=======

print("--- STARTING DATA QUALITY & VALIDATION PIPELINE ---")

# 1. Load datasets using the exact filenames in your folder
emp = pd.read_excel('HumanResources.Employee (1).xlsx', sheet_name=0)
emp_dept = pd.read_excel('HumanResources.EmployeeDepartmentHistory (1).xlsx', sheet_name=0)
pay = pd.read_excel('HumanResources.EmployeePayHistory.xlsx', sheet_name=0)
dept = pd.read_excel('HumanResources.Department (1).xlsx', sheet_name=0)
shift = pd.read_excel('HumanResources.Shift (1).xlsx', sheet_name=0)
cand = pd.read_excel('HumanResources.JobCandidate (1).xlsx', sheet_name=0)

# 2. Verify Primary Key Uniqueness
print("\n[1] Primary Key Uniqueness Checks:")
print(f"-> Employee.BusinessEntityID unique: {emp['BusinessEntityID'].is_unique}")
print(f"-> Department.DepartmentID unique: {dept['DepartmentID'].is_unique}")
print(f"-> Shift.ShiftID unique: {shift['ShiftID'].is_unique}")
print(f"-> JobCandidate.JobCandidateID unique: {cand['JobCandidateID'].is_unique}")

# 3. Check Foreign Key Referential Integrity
print("\n[2] Foreign Key Referential Integrity Checks:")
unmatched_emp_dept = ~emp_dept['BusinessEntityID'].isin(emp['BusinessEntityID'])
print(f"-> Unmatched BusinessEntityID in EmployeeDepartmentHistory: {unmatched_emp_dept.sum()}")

unmatched_pay = ~pay['BusinessEntityID'].isin(emp['BusinessEntityID'])
print(f"-> Unmatched BusinessEntityID in EmployeePayHistory: {unmatched_pay.sum()}")

# 4. Check Numerical Bounds & Pay Statistics
print("\n[3] Pay Rate Distribution Bounds:")
print(pay['Rate'].describe())
print(f"-> Negative or zero pay rates: {(pay['Rate'] <= 0).sum()}")

print("\n--- VALIDATION COMPLETED SUCCESSFULLY ---")
>>>>>>> 679ca58 (Add execute_quality_checks script and complete HR dataset validation workflow)
