"""
test_definitiva.py
==================
El motor de bp/definitiva.py reproduce el Excel definitivo del grupo (Excels/Inditex_LBO_Version_Definitiva.xlsx):
- con los valores que el Excel tiene guardados (caso y año de salida activos), fila a fila;
- recalculando el Excel con pycel en los cuatro casos, con otras primas y otros años de salida (si pycel está);
- y las palancas y la simulación cumplen sus identidades (puente del equity, mediana centrada en el caso Base).
"""

from dataclasses import replace
from pathlib import Path
import ast
import sys
import unittest
import warnings

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bp import definitiva as D  # noqa: E402
from bp import levers as L  # noqa: E402

try:
    import openpyxl
except ImportError:
    openpyxl = None

COLS = "FGHIJKL"


@unittest.skipIf(openpyxl is None or not D.XLSX.exists(), "falta el Excel definitivo u openpyxl")
class TestDefinitiva(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = D.read_excel()
        cls.deal = cls.info["deal"]
        wb = openpyxl.load_workbook(D.XLSX, data_only=True)
        cls.ls, cls.dc, cls.tw = wb["LBO Summary"], wb["Debt & Covenants"], wb["Tax & WACC"]
        cls.case = D.CASES[cls.info["active_case"] - 1]
        cls.res = D.run(D.with_case(cls.info, cls.case), cls.deal)

    def test_headline_returns_match_saved_excel(self):
        r, ls = self.res, self.ls
        pairs = [(r["su"]["sponsor"], "E39"), (r["su"]["equity"], "E45"), (r["su"]["sponsor_share"], "F44"),
                 (r["irr"][0], "K17"), (r["mom"][0], "L17"), (r["gp_irr"][0], "L18"), (r["gp_mom"][0], "L19"),
                 (r["lp_irr"][0], "K21"), (r["lp_mom"][0], "L21"), (self.deal.entry_multiple, "L8")]
        for got, cell in pairs:
            self.assertAlmostEqual(got, ls[cell].value, delta=1e-9 * max(1, abs(ls[cell].value)), msg=cell)

    def test_schedules_match_saved_excel(self):
        r, dc, tw = self.res, self.dc, self.tw
        rows = {"tla": 24, "tlb": 34, "sub": 43, "vl": 52, "rcf": 59, "cash": 93, "dscr": 105, "dscr_total": 106,
                "senior_nd_ebitda": 97, "total_nd_ebitda": 99}
        for key, row in rows.items():
            xl = np.array([dc[f"{c}{row}"].value for c in COLS], dtype=float)
            np.testing.assert_allclose(r[key][0], xl, rtol=1e-9, atol=1e-7, err_msg=key)
        np.testing.assert_allclose(r["cash_interest"][0], -np.array([dc[f"{c}71"].value for c in COLS]), rtol=1e-9)
        np.testing.assert_allclose(r["tax"][0], -np.array([tw[f"{c}22"].value for c in COLS]), rtol=1e-9)
        np.testing.assert_allclose(r["carry_fwd"][0], [tw[f"{c}35"].value for c in COLS], rtol=1e-9)
        np.testing.assert_allclose(r["lev_covenant"], [dc[f"{c}100"].value for c in "E" + COLS], rtol=1e-12)

    def test_every_exit_year_matches_saved_excel(self):
        for t, c in enumerate(COLS):
            year = self.deal.first_year + t
            ex = D.exit_returns(self.res, self.deal, year)
            self.assertAlmostEqual(ex["irr"][0], self.ls[f"{c}58"].value, places=12)
            self.assertAlmostEqual(ex["mom"][0], self.ls[f"{c}59"].value, places=12)
            self.assertAlmostEqual(ex["lp_irr"][0], self.ls[f"{c}85"].value, places=12)
            self.assertAlmostEqual(ex["gp_irr"][0], self.ls[f"{c}87"].value, places=12)

    def test_recalculated_excel_in_all_cases(self):
        try:
            if not hasattr(ast, "Str"):  # pycel usa ast.Str, eliminado en Python 3.12+
                ast.Str = lambda s: ast.Constant(value=s)
            from pycel import ExcelCompiler
        except ImportError:
            self.skipTest("pycel no instalado")
        warnings.filterwarnings("ignore")
        xl = ExcelCompiler(filename=str(D.XLSX))
        out = ["LBO Summary!K17", "LBO Summary!L18", "LBO Summary!K21", "LBO Summary!E39"] + \
              [f"Debt & Covenants!{c}105" for c in COLS]
        for cell in out + ["Active Case!F8", "LBO Summary!F10", "LBO Summary!L10"]:
            xl.evaluate(cell)
        for i, name in enumerate(D.CASES, 1):
            for premium, year in ((0.15, 2032), (0.25, 2029), (0.0, 2027)):
                xl.set_value("Active Case!F8", i)
                xl.set_value("LBO Summary!F10", premium)
                xl.set_value("LBO Summary!L10", year)
                r = D.run(D.with_case(self.info, name), replace(self.deal, premium=premium), exit_year=year)
                got = [r["irr"][0], r["gp_irr"][0], r["lp_irr"][0], r["su"]["sponsor"], r["min_dscr"][0]]
                exp = [xl.evaluate(c) for c in out[:4]] + [min(xl.evaluate(c) for c in out[4:])]
                np.testing.assert_allclose(got, exp, rtol=1e-10, err_msg=f"{name} {premium} {year}")

    def test_levers_off_change_nothing_and_bridge_adds_up(self):
        rng = np.random.default_rng(3)
        op = D.with_case(self.info, "Base")
        op0, d0, _ = D.apply_levers(op, self.deal, L.default_values(), {lv.key: False for lv in L.LEVERS})
        self.assertAlmostEqual(D.run(op0, d0)["irr"][0], self.res["irr"][0], places=14)
        for i in range(10):
            values = L.default_values()
            for lv in L.LEVERS:
                for p in lv.params:
                    values[lv.key][p.key] = (float(rng.choice((2027, 2029, 2031))) if p.edges is None
                                             else float(rng.uniform(p.edges[0], p.edges[4])))
            on = {lv.key: bool(rng.random() < 0.7) for lv in L.LEVERS}
            on["propco"] = on["recap"] = i % 2 == 0
            opx, dx, _ = D.apply_levers(D.with_case(self.info, D.CASES[i % 4]), self.deal, values, on)
            r = D.run(opx, dx, exit_year=2026 + i % 7)
            b = D.value_bridge(r, dx)
            self.assertAlmostEqual(b["start"] + sum(v[0] for v in b["items"].values()), b["end"][0], delta=1e-6)

    def test_simulation_is_centred_on_excel_base(self):
        op, _ = D.simulated_paths(self.info, n=4000, seed=7)
        base = D.with_case(self.info, "Base")
        growth = op.revenue / np.concatenate([np.full((op.revenue.shape[0], 1), self.info["fy25"]["revenue"]),
                                              op.revenue[:, :-1]], axis=1) - 1
        np.testing.assert_allclose(np.median(growth, axis=0), self.info["cases"]["Base"]["growth"], atol=1e-12)
        np.testing.assert_allclose(np.median(op.gross_profit / op.revenue, axis=0),
                                   base.gross_profit[0] / base.revenue[0], atol=1e-12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
