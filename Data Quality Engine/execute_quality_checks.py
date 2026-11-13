import pandas as pd


class DataQualityEngine:

  def __init__(self, df: pd.DataFrame, primary_key: str = None, dataset_name: str = "Dataset"):
    # Store deep copy to ensure original data remains 100% unchanged
    self.original_df = df
    self.working_df = df.copy()
    self.primary_key = primary_key
    self.dataset_name = dataset_name
    self.audit_results = []

  def run_duplicate_check(self):
    """Test duplicate rows."""
    if self.primary_key and self.primary_key in self.working_df.columns:
      dupes = self.working_df.duplicated(subset=[self.primary_key], keep=False)
      col_target = self.primary_key
    else:
      dupes = self.working_df.duplicated(keep=False)
      col_target = 'Entire Row'

    count = int(dupes.sum())
    if count > 0:
      self.audit_results.append({
          'Dataset': self.dataset_name,
          'Rule': 'Duplicate Records',
          'Column': col_target,
          'Affected_Count': count,
          'Affected_Percentage': round((count / len(self.working_df)) * 100, 2),
          'Recommendation': (
              'Deduplicate: Retain record with latest update timestamp or drop'
              ' exact copies.'
          ),
          'Severity': 'High',
      })

  def run_missing_value_check(self, threshold: float = 0.4):
    """Test missing values."""
    null_counts = self.working_df.isnull().sum()
    affected_cols = null_counts[null_counts > 0]

    for col, count in affected_cols.items():
      pct = count / len(self.working_df)
      recommendation = (
          'Drop column (exceeds threshold)'
          if pct > threshold
          else 'Impute using median (numeric) or mode (categorical)'
      )
      self.audit_results.append({
          'Dataset': self.dataset_name,
          'Rule': 'Missing Values',
          'Column': col,
          'Affected_Count': int(count),
          'Affected_Percentage': round(pct * 100, 2),
          'Recommendation': recommendation,
          'Severity': 'High' if pct > threshold else 'Medium',
      })

  def run_range_check(self, rules: dict):
    """Test invalid numerical ranges."""
    for col, (min_val, max_val) in rules.items():
      if col in self.working_df.columns:
        out_of_bounds = (self.working_df[col] < min_val) | (
            self.working_df[col] > max_val
        )
        count = int(out_of_bounds.sum())
        if count > 0:
          self.audit_results.append({
              'Dataset': self.dataset_name,
              'Rule': 'Invalid Range',
              'Column': col,
              'Affected_Count': count,
              'Affected_Percentage': round(
                  (count / len(self.working_df)) * 100, 2
              ),
              'Recommendation': (
                  f'Clip boundary values to range [{min_val}, {max_val}] or'
                  ' flag for quarantine.'
              ),
              'Severity': 'Medium',
          })

  def run_outlier_check(self, columns: list, threshold: float = 1.5):
    """Test statistical outliers using IQR."""
    for col in columns:
      if col in self.working_df.columns and pd.api.types.is_numeric_dtype(
          self.working_df[col]
      ):
        series = self.working_df[col].dropna()
        if len(series) > 0:
          Q1 = series.quantile(0.25)
          Q3 = series.quantile(0.75)
          IQR = Q3 - Q1
          lower_bound = Q1 - (threshold * IQR)
          upper_bound = Q3 + (threshold * IQR)

          outliers = (self.working_df[col] < lower_bound) | (
              self.working_df[col] > upper_bound
          )
          count = int(outliers.sum())
          if count > 0:
            self.audit_results.append({
                'Dataset': self.dataset_name,
                'Rule': 'Statistical Outliers (IQR)',
                'Column': col,
                'Affected_Count': count,
                'Affected_Percentage': round(
                    (count / len(self.working_df)) * 100, 2
                ),
                'Recommendation': (
                    'Apply Winsorization at 5th/95th percentiles or inspect for'
                    ' data entry errors.'
                ),
                'Severity': 'Low',
            })

  def generate_quality_report(self) -> pd.DataFrame:
    """Generate quality report identifying affected columns & recommendations."""
    return pd.DataFrame(self.audit_results)

  def verify_immutability(self, snapshot_df: pd.DataFrame) -> bool:
    """Ensure original data remains unchanged after validation."""
    return self.original_df.equals(snapshot_df)


# ==========================================
# MAIN EXECUTION SCRIPT
# ==========================================
if __name__ == '__main__':
  dataset_configs = [
      ('HumanResources.Department (1).xlsx', 'DepartmentID'),
      ('HumanResources.Employee (1).xlsx', 'BusinessEntityID'),
      (
          'HumanResources.EmployeeDepartmentHistory (1).xlsx',
          'BusinessEntityID',
      ),
      ('HumanResources.EmployeePayHistory.xlsx', 'BusinessEntityID'),
      ('HumanResources.JobCandidate (1).xlsx', 'JobCandidateID'),
      ('HumanResources.Shift (1).xlsx', 'ShiftID'),
  ]

  all_audit_reports = []

  print('=== STARTING INTEGRATED QUALITY-RULE WORKFLOW ===\n')

  for filename, pk in dataset_configs:
    try:
      # Read Excel sheet
      xls = pd.ExcelFile(filename)
      sheet_name = xls.sheet_names[0]
      raw_df = pd.read_excel(xls, sheet_name=sheet_name)

      # Take snapshot for immutability check
      snapshot_df = raw_df.copy()

      # Initialize Engine
      engine = DataQualityEngine(
          df=raw_df, primary_key=pk, dataset_name=filename.split(' ')[0]
      )

      # Run Quality Rules
      engine.run_duplicate_check()
      engine.run_missing_value_check(threshold=0.4)

      if 'Rate' in raw_df.columns:
        engine.run_range_check(rules={'Rate': (6.0, 200.0)})
        engine.run_outlier_check(columns=['Rate'])

      if 'OrganizationLevel' in raw_df.columns:
        engine.run_range_check(rules={'OrganizationLevel': (0, 5)})

      # Generate Report & Verify Immutability
      report_df = engine.generate_quality_report()
      if not report_df.empty:
        all_audit_reports.append(report_df)

      is_unchanged = engine.verify_immutability(snapshot_df)
      print(
          f'[{filename}] Validated | Immutability Verified:'
          f' {is_unchanged}'
      )

    except Exception as e:
      print(f'Skipping {filename}: {e}')

  # Combine and Print Master Report
  if all_audit_reports:
    master_report = pd.concat(all_audit_reports, ignore_index=True)
    print('\n=== MASTER DATA QUALITY AUDIT REPORT ===')
    print(master_report.to_string(index=False))
  else:
    print('\nNo quality anomalies detected across datasets.')