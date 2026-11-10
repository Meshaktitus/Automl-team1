import unittest
import pandas as pd
import numpy as np
from quality_analyzer import DataQualityAnalyzer

class TestDataQualityAnalyzer(unittest.TestCase):

    def test_missing_values_detection(self):
        """1. Test missing values detection and row counts."""
        df = pd.DataFrame({
            'col_a': [1, 2, None, 4, 5],
            'col_b': [None, None, None, None, 'x']  # 80% missing -> CRITICAL
        })
        analyzer = DataQualityAnalyzer(df, dataset_name="TestMissing")
        issues = analyzer.run_quality_checks()
        
        missing_issues = [i for i in issues if i['issue_type'] == 'Missing Value']
        self.assertEqual(len(missing_issues), 2)
        
        col_a_issue = next(i for i in missing_issues if i['column'] == 'col_a')
        self.assertEqual(col_a_issue['affected_rows'], 1)
        self.assertEqual(col_a_issue['severity'], 'WARNING')
        
        col_b_issue = next(i for i in missing_issues if i['column'] == 'col_b')
        self.assertEqual(col_b_issue['affected_rows'], 4)
        self.assertEqual(col_b_issue['severity'], 'CRITICAL')

    def test_duplicate_records_detection(self):
        """1. Test duplicate row detection."""
        df = pd.DataFrame({
            'id': [1, 2, 2, 3],
            'val': ['a', 'b', 'b', 'c']
        })
        analyzer = DataQualityAnalyzer(df, dataset_name="TestDuplicates")
        issues = analyzer.run_quality_checks()
        
        dup_issues = [i for i in issues if i['issue_type'] == 'Duplicate Rows']
        self.assertEqual(len(dup_issues), 1)
        self.assertEqual(dup_issues[0]['affected_rows'], 1)
        self.assertEqual(dup_issues[0]['severity'], 'CRITICAL')

    def test_invalid_dates_and_formats(self):
        """2. Test invalid dates and inconsistent date formats."""
        df = pd.DataFrame({
            'HireDate': ['2026-01-01', 'invalid-date-string', '2026-05-12', 'not_a_date']
        })
        analyzer = DataQualityAnalyzer(df, dataset_name="TestDates")
        issues = analyzer.run_quality_checks()
        
        date_issues = [i for i in issues if i['issue_type'] == 'Inconsistent Date Format']
        self.assertEqual(len(date_issues), 1)
        self.assertEqual(date_issues[0]['affected_rows'], 2)
        self.assertEqual(date_issues[0]['severity'], 'CRITICAL')

    def test_severity_classification(self):
        """3. Validate severity classification thresholds."""
        df = pd.DataFrame({
            'high_missing': [1] + [None]*9,  # 90% missing -> CRITICAL
            'low_missing': [1]*9 + [None]    # 10% missing -> WARNING
        })
        analyzer = DataQualityAnalyzer(df, dataset_name="TestSeverity")
        issues = analyzer.run_quality_checks()
        
        crit_issues = [i for i in issues if i['severity'] == 'CRITICAL' and i['issue_type'] == 'Missing Value']
        warn_issues = [i for i in issues if i['severity'] == 'WARNING' and i['issue_type'] == 'Missing Value']
        
        self.assertEqual(len(crit_issues), 1)
        self.assertEqual(crit_issues[0]['column'], 'high_missing')
        self.assertEqual(len(warn_issues), 1)
        self.assertEqual(warn_issues[0]['column'], 'low_missing')

    def test_affected_counts(self):
        """4. Verify affected-row and affected-column counts."""
        df = pd.read_excel('HumanResources.JobCandidate (1).xlsx', sheet_name='HumanResources.JobCandidate')
        analyzer = DataQualityAnalyzer(df, dataset_name="JobCandidate")
        issues = analyzer.run_quality_checks()
        
        be_issue = next(i for i in issues if i['column'] == 'BusinessEntityID')
        self.assertEqual(be_issue['affected_rows'], 11)
        self.assertEqual(be_issue['severity'], 'CRITICAL')

    def test_non_destructive_preservation(self):
        """5. Confirm quality checks do not silently remove or modify records."""
        df_original = pd.DataFrame({
            'id': [1, 2, 2, 3],
            'val': ['a', 'b', None, 'c']
        })
        df_copy = df_original.copy(deep=True)
        
        analyzer = DataQualityAnalyzer(df_original, dataset_name="TestNonDestructive")
        _ = analyzer.run_quality_checks()
        
        # Verify original dataframe shape, columns, values, and nulls remain identical
        pd.testing.assert_frame_equal(df_original, df_copy)
        self.assertEqual(len(analyzer.df), len(df_copy))

if __name__ == '__main__':
    unittest.main()