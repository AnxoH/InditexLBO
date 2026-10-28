"""
test_levers.py
==============
Verificación del plan de creación de valor:
- Con todas las palancas apagadas el plan es idéntico al standalone.
- Signos y monotonía de cada palanca (más agresivo → más TIR; la PropCo no toca el EBITDA reportado...).
- El recap reparte exactamente la nueva deuda.
- La hoja Palancas del Excel integrado da los mismos resultados que Python (si pycel está instalado).
"""

from pathlib import Path
import ast
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bp import levers as L  # noqa: E402
from bp.lbo import run  # noqa: E402
from bp.pipeline import build  # noqa: E402

EXCEL = ROOT.parent / "Excels" / "Inditex_LBO_Rollover50_BusinessPlan.xlsx"


class TestLevers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = build(n=2000, figures=False)
        cls.op = cls.o["case_ops"]["Base"]
        cls.deal = cls.o["deal"]

    def test_all_off_is_standalone(self):
        res = L.apply(self.op, self.deal, L.default_values(), on={lv.key: False for lv in L.LEVERS})
        for k in ("revenue", "gross_profit", "opex_post", "lease", "capex", "wc"):
            np.testing.assert_allclose(getattr(res.op, k), getattr(self.op, k), rtol=1e-12)
        self.assertEqual(res.deal.propco_proceeds, 0.0)

    def test_bands_are_monotonic(self):
        irr = [run(*(lambda r: (r.op, r.deal))(L.apply(self.op, self.deal, L.band_values(b))))["irr"][0]
               for b in L.BANDS]
        self.assertTrue(all(a < b for a, b in zip(irr, irr[1:])), irr)

    def test_propco_keeps_reported_ebitda(self):
        on = {lv.key: lv.key == "propco" for lv in L.LEVERS}
        res = L.apply(self.op, self.deal, L.default_values(), on=on)
        np.testing.assert_allclose(res.op.ebitda_reported, self.op.ebitda_reported, rtol=1e-12)
        self.assertTrue((res.op.ebitda_pre < self.op.ebitda_pre).all())
        self.assertGreater(res.deal.propco_proceeds, 0)

    def test_recap_pays_out_new_debt(self):
        vals = L.band_values("Optimista")
        on = {lv.key: lv.key == "recap" for lv in L.LEVERS}
        res = L.apply(self.op, self.deal, vals, on=on)
        with_recap, without = run(res.op, res.deal), run(self.op, self.deal)
        t = list(range(2026, 2031)).index(int(vals["recap"]["year"]))
        np.testing.assert_allclose(with_recap["cash"][:, :t], without["cash"][:, :t], rtol=1e-12)
        senior_net = (without["tla"] + without["tlb"] + without["rcf"] - without["cash"])[0, t - 1]
        expected = vals["recap"]["target"] * self.op.ebitda_pre[0, t - 1] - senior_net
        self.assertGreater(expected, 0)
        self.assertAlmostEqual(with_recap["dividend"][0, t], expected, places=6)  # deuda nueva = dividendo
        self.assertGreater(with_recap["tlb"][0, t], without["tlb"][0, t])

    def test_execution_risk_lowers_expected_effect(self):
        rng = np.random.default_rng(0)
        mult = L.execution_multipliers(rng, 20000)
        self.assertLess(mult["usa"].mean(), 1.0)  # la cola mala es más larga que la buena

    def test_bands_cover_defaults(self):
        for lv in L.LEVERS:
            for p in lv.params:
                if p.edges is not None:
                    self.assertTrue(p.edges[0] <= p.default <= p.edges[4], (lv.key, p.key))
                    self.assertEqual(list(p.edges), sorted(p.edges), (lv.key, p.key))


@unittest.skipUnless(EXCEL.exists(), "Excel integrado no disponible")
class TestExcelParity(unittest.TestCase):
    def test_dashboard_matches_python(self):
        try:
            if not hasattr(ast, "Str"):  # pycel usa ast.Str, eliminado en Python 3.12+
                ast.Str = lambda s: ast.Constant(value=s)
            from pycel import ExcelCompiler
        except ImportError:
            self.skipTest("pycel no instalado")
        import openpyxl

        o = build(figures=False)
        ws = openpyxl.load_workbook(EXCEL)["Palancas"]
        cells, r = {}, 19
        for lv in L.LEVERS:
            r += 1
            for p in lv.params:
                cells[(lv.key, p.key)] = f"Palancas!D{r}"
                r += 1
            r += 1
        xl = ExcelCompiler(filename=str(EXCEL))
        for a in ["LBO_Rollover50!F9", "LBO_Rollover50!F230", "LBO_Rollover50!R29", *cells.values()]:
            xl.evaluate(a)
        for band in ("Normal", "Optimista"):
            vals = L.band_values(band)
            for cell_key, addr in cells.items():
                xl.set_value(addr, float(vals[cell_key[0]][cell_key[1]]))
            for k, case in ((1, "Base"), (4, "Bank case")):
                xl.set_value("LBO_Rollover50!F9", k)
                res = L.apply(o["case_ops"][case], o["deal"], vals)
                py = run(res.op, res.deal)
                self.assertAlmostEqual(xl.evaluate("LBO_Rollover50!F230"), py["mom"][0], places=9)
                self.assertAlmostEqual(xl.evaluate("LBO_Rollover50!R29"), res.op.ebitda_pre[0, -1], places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
