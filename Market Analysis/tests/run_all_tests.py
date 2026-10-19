"""
run_all_tests.py
================
Master empirical verification test runner for Inditex Stage 1 deliverables.
Discovers and executes all test suites in Market Analysis/tests/:
- test_data_integrity.py (7 tests)
- test_markdown_links.py (2 tests)
- test_guardrails_compliance.py (3 tests)
- test_annual_reports_reconciliation.py (3 tests)
- test_extraction_script.py (6 tests)
- test_reports_content_and_language.py (8 tests)

Outputs detailed per-test execution statistics, execution time, and exit code.
"""

from pathlib import Path
import sys
import time
import unittest


def main():
    print("=" * 80)
    print("INDITEX STAGE 1 — EMPIRICAL VERIFICATION & STRESS TEST SUITE")
    print("=" * 80)

    tests_dir = Path(__file__).resolve().parent
    loader = unittest.TestLoader()
    suite = loader.discover(str(tests_dir), pattern="test_*.py")

    total_suites = suite.countTestCases()
    print(f"Discovered {total_suites} test cases across 6 test modules in {tests_dir}\n")

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("\n" + "=" * 80)
    print("EMPIRICAL TEST EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Total Tests Executed: {result.testsRun}")
    print(f"Passed:              {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures:            {len(result.failures)}")
    print(f"Errors:              {len(result.errors)}")
    print(f"Execution Time:      {elapsed:.3f} seconds")
    print("=" * 80)

    if result.wasSuccessful():
        print("VERDICT: ALL TESTS PASSED SUCCESSFULLY (STATUS: APPROVE)")
        sys.exit(0)
    else:
        print("VERDICT: EMPIRICAL FAILURES DETECTED (STATUS: REQUEST_CHANGES)")
        sys.exit(1)


if __name__ == '__main__':
    main()
