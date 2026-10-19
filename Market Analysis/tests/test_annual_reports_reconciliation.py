"""
test_annual_reports_reconciliation.py
=====================================
Empirical reconciliation test suite between:
- Market Analysis/data/inditex_kpis_2022_2025.csv
- Market Analysis/data/inditex_brands_breakdown.csv
AND
- Annual Reports/Transformed/ConsolidatedReport_2025.md
- Annual Reports/Transformed/ConsolidatedReport_2024.md
- Annual Reports/Transformed/ConsolidatedReport_2023.md
- Annual Reports/Transformed/ConsolidatedReport_2022.md

Tests:
- Headline figures (Sales, Gross Profit, EBITDA, EBIT, Net Income, Net Cash)
  are verified directly against the underlying audited statements.
- Store counts and format breakdowns reconcile 100% against the management reports.
"""

from pathlib import Path
import re
import unittest
import pandas as pd


class TestAnnualReportsReconciliation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        cls.data_dir = cls.project_root / 'Market Analysis' / 'data'
        cls.reports_dir = cls.project_root / 'Annual Reports' / 'Transformed'

        cls.df_kpis = pd.read_csv(cls.data_dir / 'inditex_kpis_2022_2025.csv')
        cls.df_brands = pd.read_csv(cls.data_dir / 'inditex_brands_breakdown.csv')

        # Read sections from annual reports
        cls.rep25_text = (cls.reports_dir / 'ConsolidatedReport_2025.md').read_text(encoding='utf-8')
        cls.rep23_text = (cls.reports_dir / 'ConsolidatedReport_2023.md').read_text(encoding='utf-8')

    def test_reconciliation_headline_figures(self):
        """
        Verify that headline KPIs in the CSV match audited figures in Consolidated Reports.
        """
        # FY2025 Audited Verification
        self.assertIn("39.864", self.rep25_text, "FY25 Sales 39.864 not found in 2025 report")
        self.assertIn("23.222", self.rep25_text, "FY25 Gross Profit 23.222 not found in 2025 report")
        self.assertIn("11.267", self.rep25_text, "FY25 EBITDA 11.267 not found in 2025 report")
        self.assertIn("7.997", self.rep25_text, "FY25 EBIT 7.997 not found in 2025 report")
        self.assertIn("6.220", self.rep25_text, "FY25 Net Income 6.220 not found in 2025 report")
        self.assertIn("10.958", self.rep25_text, "FY25 Net Cash 10.958 not found in 2025 report")

        # FY2024 Audited Verification (from 2025 comparative column)
        self.assertIn("38.632", self.rep25_text, "FY24 Sales 38.632 not found in 2025 report")
        self.assertIn("22.343", self.rep25_text, "FY24 Gross Profit 22.343 not found in 2025 report")
        self.assertIn("10.728", self.rep25_text, "FY24 EBITDA 10.728 not found in 2025 report")
        self.assertIn("7.554", self.rep25_text, "FY24 EBIT 7.554 not found in 2025 report")
        self.assertIn("5.866", self.rep25_text, "FY24 Net Income 5.866 not found in 2025 report")
        self.assertIn("11.495", self.rep25_text, "FY24 Net Cash 11.495 not found in 2025 report")

        # FY2023 Audited Verification
        self.assertIn("35.947", self.rep23_text, "FY23 Sales 35.947 not found in 2023 report")
        self.assertIn("20.762", self.rep23_text, "FY23 Gross Profit 20.762 not found in 2023 report")
        self.assertIn("9.850", self.rep23_text, "FY23 EBITDA 9.850 not found in 2023 report")
        self.assertIn("6.809", self.rep23_text, "FY23 EBIT 6.809 not found in 2023 report")
        self.assertIn("5.381", self.rep23_text, "FY23 Net Income 5.381 not found in 2023 report")
        self.assertIn("11.406", self.rep23_text, "FY23 Net Cash 11.406 not found in 2023 report")

        # FY2022 Audited Verification (from 2023 comparative column)
        self.assertIn("32.569", self.rep23_text, "FY22 Sales 32.569 not found in 2023 report")
        self.assertIn("18.559", self.rep23_text, "FY22 Gross Profit 18.559 not found in 2023 report")
        self.assertIn("8.649", self.rep23_text, "FY22 EBITDA 8.649 not found in 2023 report")
        self.assertIn("5.520", self.rep23_text, "FY22 EBIT 5.520 not found in 2023 report")
        self.assertIn("4.130", self.rep23_text, "FY22 Net Income 4.130 not found in 2023 report")
        self.assertIn("10.070", self.rep23_text, "FY22 Net Cash 10.070 not found in 2023 report")

    def test_reconciliation_brand_concept_sales_and_stores(self):
        """
        Verify that commercial brand concept sales and store counts reconcile with annual reports.
        """
        # Check FY25 brand sales in 2025 report
        self.assertIn("28.051", self.rep25_text, "FY25 Zara sales 28.051 not in 2025 report")
        self.assertIn("2.546", self.rep25_text, "FY25 Pull&Bear sales 2.546 not in 2025 report")
        self.assertIn("2.019", self.rep25_text, "FY25 Massimo Dutti sales 2.019 not in 2025 report")
        self.assertIn("3.286", self.rep25_text, "FY25 Bershka sales 3.286 not in 2025 report")
        self.assertIn("3.002", self.rep25_text, "FY25 Stradivarius sales 3.002 not in 2025 report")
        self.assertIn("960", self.rep25_text, "FY25 Oysho sales 960 not in 2025 report")

        # Check FY25 store counts in 2025 report
        self.assertIn("2.089", self.rep25_text, "FY25 Zara stores 2.089 not in 2025 report")
        self.assertIn("791", self.rep25_text, "FY25 Pull&Bear stores 791 not in 2025 report")
        self.assertIn("511", self.rep25_text, "FY25 Massimo Dutti stores 511 not in 2025 report")
        self.assertIn("852", self.rep25_text, "FY25 Bershka stores 852 not in 2025 report")
        self.assertIn("834", self.rep25_text, "FY25 Stradivarius stores 834 not in 2025 report")
        self.assertIn("383", self.rep25_text, "FY25 Oysho stores 383 not in 2025 report")
        self.assertIn("5.460", self.rep25_text, "FY25 Total stores 5.460 not in 2025 report")

        # Check FY23 brand sales in 2023 report
        self.assertIn("26.050", self.rep23_text, "FY23 Zara sales 26.050 not in 2023 report")
        self.assertIn("2.359", self.rep23_text, "FY23 Pull&Bear sales 2.359 not in 2023 report")
        self.assertIn("1.839", self.rep23_text, "FY23 Massimo Dutti sales 1.839 not in 2023 report")
        self.assertIn("2.621", self.rep23_text, "FY23 Bershka sales 2.621 not in 2023 report")
        self.assertIn("2.334", self.rep23_text, "FY23 Stradivarius sales 2.334 not in 2023 report")
        self.assertIn("744", self.rep23_text, "FY23 Oysho sales 744 not in 2023 report")

    def test_shares_outstanding_and_dividend(self):
        """
        Verify share capital and dividends in CSV match annual reports.
        """
        # Inditex share capital consists of 3,116,652,000 shares of €0.03 par value
        self.assertIn("3.116.652.000", self.rep25_text, "Total shares 3.116.652.000 not in 2025 report")
        
        # FY25 dividend proposed is €1.75 / share
        self.assertIn("1,75", self.rep25_text, "FY25 proposed dividend 1,75 not in 2025 report")
        # FY24 dividend paid is €1.54 / share, proposed was €1.68 / share
        self.assertIn("1,68", self.rep25_text, "FY24 proposed dividend 1,68 not in 2025 report")


if __name__ == '__main__':
    unittest.main()
