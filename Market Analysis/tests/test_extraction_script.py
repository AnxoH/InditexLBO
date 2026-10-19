"""
test_extraction_script.py
=========================
Empirical unit and integration tests for Market Analysis/scripts/extract_baseline_data.py:
1. parse_spanish_number unit test (edge cases, formatting variants).
2. extract_markdown_table_rows parser test (separator stripping, whitespace trimming).
3. build_inditex_kpis function execution and DataFrame schema validation.
4. build_inditex_brands function execution and DataFrame schema validation.
5. End-to-end execution safety and determinism.
"""

from pathlib import Path
import sys
import unittest
import pandas as pd

# Add scripts directory to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
scripts_dir = project_root / 'Market Analysis' / 'scripts'
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import extract_baseline_data as extractor


class TestExtractionScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports_dir = project_root / 'Annual Reports' / 'Transformed'

    def test_parse_spanish_number_standard(self):
        """Test parsing of standard Spanish formatted numbers."""
        self.assertEqual(extractor.parse_spanish_number("12.345,67"), 12345.67)
        self.assertEqual(extractor.parse_spanish_number("39.864"), 39864.0)
        self.assertEqual(extractor.parse_spanish_number("1.234"), 1234.0)
        self.assertEqual(extractor.parse_spanish_number("58,3%"), 58.3)
        self.assertEqual(extractor.parse_spanish_number("0,0%"), 0.0)

    def test_parse_spanish_number_negatives(self):
        """Test parsing of negative numbers with parentheses and minus signs."""
        self.assertEqual(extractor.parse_spanish_number("(1.234,56)"), -1234.56)
        self.assertEqual(extractor.parse_spanish_number("(14.011)"), -14011.0)
        self.assertEqual(extractor.parse_spanish_number("-500,25"), -500.25)
        self.assertEqual(extractor.parse_spanish_number(" ( 231 ) "), -231.0)

    def test_parse_spanish_number_edge_cases(self):
        """Test parsing of edge cases (blanks, dashes, invalid strings)."""
        self.assertEqual(extractor.parse_spanish_number("-"), 0.0)
        self.assertEqual(extractor.parse_spanish_number(""), 0.0)
        self.assertEqual(extractor.parse_spanish_number("   "), 0.0)
        self.assertEqual(extractor.parse_spanish_number("N/A"), 0.0)
        self.assertEqual(extractor.parse_spanish_number("invalid_string"), 0.0)

    def test_extract_markdown_table_rows(self):
        """Test markdown table row extractor ignores separators and extracts clean cells."""
        sample_lines = [
            "Some introduction text",
            "| Concept | FY25 | FY24 |",
            "| :--- | :--- | :--- |",
            "| Net Sales | 39.864 | 38.632 |",
            "| Gross Profit | 23.222 | 22.343 |",
            "",
            "Some footer text"
        ]
        table = extractor.extract_markdown_table_rows(sample_lines, 0, len(sample_lines))
        self.assertEqual(len(table), 3)  # Header + 2 data rows (separator skipped)
        self.assertEqual(table[0], ["Concept", "FY25", "FY24"])
        self.assertEqual(table[1], ["Net Sales", "39.864", "38.632"])
        self.assertEqual(table[2], ["Gross Profit", "23.222", "22.343"])

    def test_build_inditex_kpis_execution(self):
        """Test build_inditex_kpis generates correct DataFrame from transformed reports."""
        df = extractor.build_inditex_kpis(self.reports_dir)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 4)
        self.assertIn('net_sales_eur_m', df.columns)
        self.assertIn('ebitda_eur_m', df.columns)
        self.assertIn('net_cash_eur_m', df.columns)
        
        # Verify FY25 values
        fy25 = df[df['fiscal_year'] == 'FY25'].iloc[0] if 'FY25' in list(df['fiscal_year']) else df[df['fiscal_year'] == 'FY2025'].iloc[0]
        self.assertEqual(fy25['net_sales_eur_m'], 39864.0)
        self.assertEqual(fy25['net_income_eur_m'], 6220.0)
        self.assertEqual(fy25['net_cash_eur_m'], 10958.0)

    def test_build_inditex_brands_execution(self):
        """Test build_inditex_brands generates correct DataFrame from transformed reports."""
        df = extractor.build_inditex_brands(self.reports_dir)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 28)
        self.assertIn('brand', df.columns)
        self.assertIn('net_sales_eur_m', df.columns)
        self.assertIn('roce_pct', df.columns)

        # Check Zara FY25
        zara_fy25 = df[(df['brand'].str.startswith('Zara')) & (df['fiscal_year'].str.contains('2025|25'))].iloc[0]
        self.assertEqual(zara_fy25['net_sales_eur_m'], 28051.0)
        self.assertEqual(zara_fy25['store_count'], 2089)
        self.assertEqual(zara_fy25['roce_pct'], 36.0)


if __name__ == '__main__':
    unittest.main()
