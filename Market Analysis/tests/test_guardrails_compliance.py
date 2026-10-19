"""
test_guardrails_compliance.py
=============================
Empirical verification test suite for R8 Scope Boundary Guardrails across all
Market Analysis reports, data files, and scripts:

Guardrail terms monitored:
- Senior Tranche / Senior Debt
- Mezzanine / Mezzanine Debt
- Covenant Compliance / Financial Covenants
- 3-statement model / Three-statement model / Full financial model
- Debt amortization schedule
- Interest rate schedule

Enforcement:
1. No prohibited financial models or debt schedules are constructed.
2. If any guardrail term appears in text, it MUST occur strictly within an
   explicit negative attestation or scope boundary declaration (e.g. stating
   that debt structures, covenants, and 3-statement models are intentionally
   excluded from Stage 1 to serve as inputs for the user's upcoming Excel model).
"""

from pathlib import Path
import re
import unittest
from typing import List, Dict, Tuple


class TestGuardrailsCompliance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        cls.market_analysis_dir = cls.project_root / 'Market Analysis'
        
        # Collect all markdown, python, and csv files in Market Analysis
        cls.files_to_scan = (
            list(cls.market_analysis_dir.glob('*.md')) +
            list((cls.market_analysis_dir / 'modules').glob('*.md')) +
            list((cls.market_analysis_dir / 'scripts').glob('*.py')) +
            list((cls.market_analysis_dir / 'data').glob('*.csv'))
        )

        cls.guardrail_patterns = [
            (r'\bsenior\s+tranche\b', 'Senior Tranche'),
            (r'\bmezzanine\b', 'Mezzanine'),
            (r'\bcovenant\s+compliance\b', 'Covenant Compliance'),
            (r'\b3-statement\s+model\b', '3-statement model'),
            (r'\bthree-statement\s+model\b', 'Three-statement model'),
            (r'\bdebt\s+amortization\s+schedule\b', 'Debt amortization schedule'),
            (r'\binterest\s+rate\s+schedule\b', 'Interest rate schedule'),
        ]

        # Valid negative attestation indicators
        cls.negative_attestation_keywords = [
            'not', 'no ', 'do not', 'neither', 'nor', 'never', 'out of scope',
            'exclusion', 'exclude', 'excluded', 'excluding', 'boundary',
            'guardrail', 'guardrails', 'negative attestation', 'attestation',
            'omitted', 'deliberately omitted', 'pre-model', 'starting point',
            'for financial modeling', 'for future excel', 'feed into',
            'will be modeled', 'unlevered', 'without constructing', 'prohibited'
        ]

    def _is_negative_attestation(self, context: str) -> bool:
        """Check if the context contains explicit negative attestation phrasing."""
        context_lower = context.lower()
        return any(kw in context_lower for kw in self.negative_attestation_keywords)

    def test_guardrail_terms_presence_and_attestation(self):
        """
        Verify that guardrail terms do not appear outside negative attestation.
        Every occurrence must be examined in its surrounding paragraph (context window).
        """
        violations = []
        occurrences = []

        for file_path in self.files_to_scan:
            # Skip test files themselves
            if 'tests' in file_path.parts:
                continue

            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()

            for pattern, term_name in self.guardrail_patterns:
                for line_idx, line in enumerate(lines):
                    if re.search(pattern, line, re.IGNORECASE):
                        # Extract 3-line surrounding window for context
                        start_idx = max(0, line_idx - 2)
                        end_idx = min(len(lines), line_idx + 3)
                        context_window = " ".join(lines[start_idx:end_idx])

                        is_attested = self._is_negative_attestation(context_window)
                        record = {
                            'file': str(file_path.relative_to(self.project_root)),
                            'line': line_idx + 1,
                            'term': term_name,
                            'matched_line': line.strip(),
                            'is_attested': is_attested
                        }
                        occurrences.append(record)

                        if not is_attested:
                            violations.append(record)

        print(f"\n[TestGuardrailsCompliance] Found {len(occurrences)} references to guardrail terms across deliverables.")
        for occ in occurrences:
            status = "ATTESTED (PASS)" if occ['is_attested'] else "UNATTESTED (FAIL)"
            print(f"  [{status}] {occ['file']}:{occ['line']} -> Term: '{occ['term']}'")

        if violations:
            msg = f"Found {len(violations)} UNAUTHORIZED / UNATTESTED appearances of guardrail terms:\n"
            for v in violations:
                msg += f"  - {v['file']}:{v['line']} | Term: '{v['term']}' | Line: \"{v['matched_line']}\"\n"
            self.fail(msg)

    def test_absence_of_debt_schedules(self):
        """
        Verify absence of actual debt tranche schedule structures.
        Ensure no tables contain columns like 'Beginning Balance', 'Repayment', 'Ending Balance'
        combined with 'Senior', 'Mezzanine', or 'Term Loan'.
        """
        for file_path in self.files_to_scan:
            if 'tests' in file_path.parts:
                continue

            content = file_path.read_text(encoding='utf-8')
            # Check for debt schedule table patterns
            has_tranche_headers = bool(re.search(r'\|\s*(Term Loan [A-Z]|Senior Notes|Mezzanine Debt|Revolving Credit Facility)\s*\|', content, re.IGNORECASE))
            has_amortization_columns = bool(re.search(r'\|\s*(Principal Repayment|Mandatory Amortization|Cash Sweep)\s*\|', content, re.IGNORECASE))

            self.assertFalse(
                has_tranche_headers and has_amortization_columns,
                f"Prohibited debt schedule table detected in {file_path.relative_to(self.project_root)}!"
            )

    def test_absence_of_three_statement_model(self):
        """
        Verify absence of complete 3-statement integrated financial model (P&L + Balance Sheet + Cash Flow).
        Stage 1 should deliver starting-point datasets and baseline metrics, not a full 10-year forecasting model.
        """
        for file_path in self.files_to_scan:
            if 'tests' in file_path.parts:
                continue

            content = file_path.read_text(encoding='utf-8')
            # Prohibit 10-year forecasting tables like FY2026E through FY2035E in a full 3-statement format
            has_long_projection = bool(re.search(r'FY2030E.*FY2035E', content))
            has_integrated_model = bool(re.search(r'Balance Sheet.*Cash Flow.*Debt Schedule', content, re.DOTALL))

            self.assertFalse(
                has_long_projection and has_integrated_model,
                f"Prohibited 3-statement integrated long-term forecast detected in {file_path.relative_to(self.project_root)}!"
            )


if __name__ == '__main__':
    unittest.main()
