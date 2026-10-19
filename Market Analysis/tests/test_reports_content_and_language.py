"""
test_reports_content_and_language.py
====================================
Empirical verification test suite for report contents, deliverables coverage,
and English language integrity across:
- Market Analysis/00_Inditex_Stage1_IC_Overview.md
- Market Analysis/modules/01_Market_Position.md
- Market Analysis/modules/02_Business_Model_Moat.md
- Market Analysis/modules/03_Growth_and_Trajectory.md
- Market Analysis/modules/04_Competitor_Benchmarking.md
- Market Analysis/modules/05_Valuation_and_PE_Thesis.md

Tests:
- All required modules and the master overview memo exist and are substantial (> 20KB).
- English language purity (zero untranslated Spanish paragraphs).
- Section 6 Excel Modeling Starting-Point Kit exists and contains complete input tables.
- Verification of mandatory analytical content specified in ORIGINAL_REQUEST.md.
"""

from pathlib import Path
import re
import unittest
from typing import Dict, List


class TestReportsContentAndLanguage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        cls.market_dir = cls.project_root / 'Market Analysis'
        cls.modules_dir = cls.market_dir / 'modules'

        cls.overview_path = cls.market_dir / '00_Inditex_Stage1_IC_Overview.md'
        cls.m1_path = cls.modules_dir / '01_Market_Position.md'
        cls.m2_path = cls.modules_dir / '02_Business_Model_Moat.md'
        cls.m3_path = cls.modules_dir / '03_Growth_and_Trajectory.md'
        cls.m4_path = cls.modules_dir / '04_Competitor_Benchmarking.md'
        cls.m5_path = cls.modules_dir / '05_Valuation_and_PE_Thesis.md'

        cls.all_reports = {
            'Overview': cls.overview_path,
            'Module 1': cls.m1_path,
            'Module 2': cls.m2_path,
            'Module 3': cls.m3_path,
            'Module 4': cls.m4_path,
            'Module 5': cls.m5_path
        }

    def test_all_reports_exist_and_are_substantial(self):
        """Verify all 6 analytical reports exist and exceed minimum content threshold (> 20KB)."""
        for name, path in self.all_reports.items():
            self.assertTrue(path.exists(), f"{name} file does not exist at {path}")
            size_kb = path.stat().st_size / 1024.0
            self.assertGreater(
                size_kb, 20.0,
                f"{name} is too short ({size_kb:.1f} KB), expected > 20 KB"
            )

    def test_english_language_integrity(self):
        """
        Verify that all reports are strictly written in English.
        Detects unintended Spanish continuous text (common Spanish stop words in sentence context).
        Allows legitimate proper nouns / source citations (e.g. 'Informe de Gestión', 'Cuentas Anuales').
        """
        spanish_phrases = [
            r'\ben el presente informe\b',
            r'\bpor lo tanto\b',
            r'\bsin embargo\b',
            r'\bcuenta de resultados\b',
            r'\bbalance de situaci[oó]n\b',
            r'\bel ejercicio anterior\b',
            r'\bcabe destacar que\b',
            r'\bcon respecto a\b',
            r'\ben comparaci[oó]n con\b',
            r'\blos resultados de\b',
            r'\bpara el a[nñ]o\b'
        ]

        violations = []
        for name, path in self.all_reports.items():
            content = path.read_text(encoding='utf-8')
            for phrase in spanish_phrases:
                matches = list(re.finditer(phrase, content, re.IGNORECASE))
                for m in matches:
                    line_no = content[:m.start()].count('\n') + 1
                    snippet = content[max(0, m.start() - 30):min(len(content), m.end() + 30)]
                    violations.append({
                        'report': name,
                        'line': line_no,
                        'pattern': phrase,
                        'snippet': snippet.replace('\n', ' ')
                    })

        if violations:
            msg = f"Found {len(violations)} untranslated Spanish text fragments:\n"
            for v in violations:
                msg += f"  - [{v['report']}:L{v['line']}] Matched '{v['pattern']}': \"...{v['snippet']}...\"\n"
            self.fail(msg)

    def test_overview_section_6_excel_kit(self):
        """Verify Section 6 'Excel Modeling Starting-Point Kit' exists and is complete in 00_Overview."""
        content = self.overview_path.read_text(encoding='utf-8')
        self.assertRegex(
            content,
            r'Section 6[:\s]+Excel Modeling Starting-Point Kit',
            "Missing 'Section 6: Excel Modeling Starting-Point Kit' in 00_Overview.md"
        )
        
        # Check required cheat-sheet components
        self.assertIn("Audited Historical Anchor Figures", content)
        self.assertIn("Driver Ranges", content)
        self.assertIn("Cost of Capital & WACC Benchmarks", content)
        self.assertIn("Valuation Multiples & Exit Sensitivity Ranges", content)
        self.assertIn("IFRS 16 Lease Liability", content)

    def test_module_01_content(self):
        """Verify Module 01 covers scale (€39,864M / ~€39.9B), geographic splits, masstige positioning, and US expansion."""
        content = self.m1_path.read_text(encoding='utf-8')
        has_scale = "39,864" in content or "39.9" in content or "39.86" in content
        self.assertTrue(has_scale, "Missing €39.9B / €39,864M scale reference in Module 1")
        self.assertIn("Masstige", content)
        self.assertIn("Spain", content)
        self.assertIn("Europe ex-Spain", content)
        self.assertIn("Americas", content)
        self.assertIn("United States", content)

    def test_module_02_content(self):
        """Verify Module 02 covers proximity supply chain, negative working capital, and concept ROCE."""
        content = self.m2_path.read_text(encoding='utf-8')
        self.assertIn("Proximity", content)
        self.assertIn("Portugal", content)
        self.assertIn("Morocco", content)
        self.assertIn("Turkey", content)
        self.assertIn("Negative Working Capital", content)
        self.assertIn("ROCE", content)
        self.assertIn("Pull&Bear", content)
        self.assertIn("Massimo Dutti", content)
        self.assertIn("Bershka", content)
        self.assertIn("Stradivarius", content)
        self.assertIn("Oysho", content)

    def test_module_03_content(self):
        """Verify Module 03 covers multi-year margins, IFRS 16 lease liability, capex, and consensus driver ranges."""
        content = self.m3_path.read_text(encoding='utf-8')
        self.assertIn("IFRS 16", content)
        self.assertIn("Lease", content)
        self.assertIn("Logistics", content)
        self.assertIn("Capex", content)
        self.assertIn("Base", content)
        self.assertIn("Bull", content)
        self.assertIn("Bear", content)

    def test_module_04_content(self):
        """Verify Module 04 benchmarks Tier 1, Tier 2 (Shein, Mango), Tier 3 peers, beta, and correlation."""
        content = self.m4_path.read_text(encoding='utf-8')
        self.assertIn("H&M", content)
        self.assertIn("Fast Retailing", content)
        self.assertIn("Next", content)
        self.assertIn("Gap", content)
        self.assertIn("Primark", content)
        self.assertIn("Shein", content)
        self.assertIn("Mango", content)
        self.assertIn("Lululemon", content)
        self.assertIn("Adidas", content)
        self.assertIn("Nike", content)
        self.assertIn("Beta", content)
        self.assertIn("Correlation", content)

    def test_module_05_content(self):
        """Verify Module 05 covers 64.35% family shareholding, PE feasibility, Brand SOTP, WACC parameters."""
        content = self.m5_path.read_text(encoding='utf-8')
        self.assertIn("64.35%", content)
        self.assertIn("Amancio Ortega", content)
        self.assertIn("Pontegadea", content)
        self.assertIn("Sandra Ortega", content)
        self.assertIn("35.65%", content)
        self.assertIn("WACC", content)
        self.assertIn("SOTP", content)
        self.assertIn("Buyout", content)


if __name__ == '__main__':
    unittest.main()
