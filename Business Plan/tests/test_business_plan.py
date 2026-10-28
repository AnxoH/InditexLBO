"""
test_business_plan.py
=====================
Verificación del business plan estocástico:
- El motor LBO reproduce la hoja LBO_Rollover50 del Excel del grupo (valores calculados por Excel).
- La proyección con los drivers del Excel coincide con el caso base del Excel.
- La simulación es reproducible y sus magnitudes son coherentes con el histórico.
- Los casos están ordenados y el reparto de Shapley suma el R².
"""

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bp import analysis as A  # noqa: E402
from bp.calibration import calibrate  # noqa: E402
from bp.lbo import GROUP_DEAL, JAVI_DEAL, excel_base_operating, run, sources_and_uses  # noqa: E402
from bp.model import Drivers, project, simulate  # noqa: E402


class TestLBOEngine(unittest.TestCase):
    """Valores calculados por Excel en Excels/Inditex_LBO_Rollover50.xlsx (rama Javi), hoja LBO_Rollover50."""

    @classmethod
    def setUpClass(cls):
        cls.res = run(excel_base_operating(), JAVI_DEAL)

    def test_sources_and_uses(self):
        su = sources_and_uses(JAVI_DEAL)
        self.assertAlmostEqual(su["equity"], 119586.725, places=2)  # E196
        self.assertAlmostEqual(su["sponsor"], 65818.601, places=2)  # E208
        self.assertAlmostEqual(su["rollover"], 53768.124, places=2)  # K173

    def test_returns(self):
        self.assertAlmostEqual(float(self.res["irr"][0]), 0.11951, places=5)  # F229 (XIRR)
        self.assertAlmostEqual(float(self.res["mom"][0]), 1.75904, places=5)  # F230

    def test_debt_schedule(self):
        np.testing.assert_allclose(self.res["dscr"][0], [2.889, 1.894, 1.802, 1.739, 1.711], atol=1e-3)  # fila 136
        np.testing.assert_allclose(self.res["tlb"][0], [15416.536, 11851.084, 8196.502, 4461.909, 580.012],
                                   atol=1e-2)  # fila 92
        np.testing.assert_allclose(self.res["pik"][0, -1], 15540.365, atol=1e-2)  # R101
        np.testing.assert_allclose(self.res["tax"][0], [1154.012, 1223.331, 1297.795, 1484.282, 1689.148],
                                   atol=1e-2)  # fila 36

    def test_projection_matches_excel_drivers(self):
        ex = excel_base_operating()
        ones = np.ones((1, 5))
        dr = Drivers(growth=0.055 * ones, gross_margin=0.582 * ones, opex_ratio=(ex.opex_post + ex.lease) / ex.revenue,
                     lease_growth=0.02 * ones, capex_ratio=0.052 * ones, inv=0.0815 * ones, rec=0.0292 * ones,
                     pay=-0.2154 * ones)
        op = project(dr)
        np.testing.assert_allclose(op.ebitda_pre, ex.ebitda_pre, atol=1e-6)
        np.testing.assert_allclose(op.wc, ex.wc, atol=1e-6)


class TestSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cal = calibrate()
        cls.dr = simulate(cls.cal, n=5000, seed=7)
        cls.op = project(cls.dr)

    def test_reproducible(self):
        again = simulate(self.cal, n=5000, seed=7)
        np.testing.assert_array_equal(again.growth, self.dr.growth)

    def test_finite(self):
        for k in Drivers.CORE:
            self.assertTrue(np.isfinite(getattr(self.dr, k)).all(), k)

    def test_magnitudes_consistent_with_history(self):
        g = np.median(self.dr.growth)
        self.assertTrue(0.02 < g < 0.06, g)  # crecimiento reportado mediano
        margin = np.median(self.op.ebitda_pre / self.op.revenue)
        self.assertTrue(0.21 < margin < 0.25, margin)  # banda histórica del margen pre-IFRS 16
        crisis = self.dr.crisis.max(axis=1).mean()
        self.assertTrue(0.10 < crisis < 0.40, crisis)

    def test_calibration_signs(self):
        p = self.cal.params
        self.assertLess(p["fx_mean"].value, 0)  # la divisa resta crecimiento
        self.assertTrue(0 < p["opex_beta"].value < 1)  # gastos menos elásticos que las ventas a corto plazo
        self.assertLess(p["opex_gamma"].value, 0)  # el ratio vuelve a su media
        self.assertTrue(0 < p["gm_phi"].value < 1)

    def test_cases_are_ordered(self):
        cases = A.extract_cases(self.dr, self.op)
        e = [project(cases[k]).ebitda_pre[0, -1] for k in ["Bull", "Base", "Bear", "Bank case"]]
        self.assertTrue(all(a > b for a, b in zip(e, e[1:])), e)

    def test_shapley_sums_to_r2(self):
        res = run(self.op, GROUP_DEAL)
        phi, r2 = A.shapley_r2(res["irr"], A.path_factors(self.dr, self.op))
        self.assertAlmostEqual(phi.sum(), r2, places=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
