import pandas as pd

# Define the structured issue audit table for handover
handover_data = [
    {
        "Dataset": "Employee",
        "Issue Description": "Missing organizational hierarchy nodes (OrganizationNode, OrganizationLevel)",
        "Affected Count": "2 fields (1 row - CEO record)",
        "Severity Level": "Medium (Warning)"
    },
    {
        "Dataset": "JobCandidate",
        "Issue Description": "Unassigned BusinessEntityID for external applicants prior to hiring conversion",
        "Affected Count": "11 records",
        "Severity Level": "Medium (Warning)"
    },
    {
        "Dataset": "EmployeeDepartmentHistory",
        "Issue Description": "Open-ended active assignment EndDate entries for current employees",
        "Affected Count": "290 records",
        "Severity Level": "Low (Informational)"
    },
    {
        "Dataset": "Department / Pay / Shift",
        "Issue Description": "Zero missing values, zero duplicates, and complete referential integrity",
        "Affected Count": "0 records",
        "Severity Level": "Pass"
    }
]

df_report = pd.DataFrame(handover_data)
print("=== FINAL DATA QUALITY MODULE HANDOVER REPORT ===")
print(df_report.to_string(index=False))

# Export handover report to CSV for submission
df_report.to_csv("data_quality_handover_report.csv", index=False)
print("\n[INFO] Handover report successfully saved as 'data_quality_handover_report.csv'")