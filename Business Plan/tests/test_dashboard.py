"""
test_dashboard.py
=================
Verificación del dashboard web:
- El motor JavaScript (dashboard/motor.js) da los mismos resultados que bp/definitiva.py en los cuatro casos del
  Excel definitivo, con combinaciones aleatorias de palancas y años de salida, y el mismo reparto de Shapley.
- Sin palancas, la página da lo que el Excel tiene guardado.
- La simulación de la página (caminos en float32 con riesgo de ejecución) coincide con Python.
Necesita mini-racer (pip install mini-racer); sin él, se salta.
"""

from pathlib import Path
from itertools import combinations
from math import factorial
import base64
import json
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bp import definitiva as D  # noqa: E402
from bp import levers as L  # noqa: E402
from bp import web as W  # noqa: E402

try:
    from py_mini_racer import MiniRacer
except ImportError:
    MiniRacer = None


def random_plan(rng):
    values = W.dashboard_defaults()
    for lv in L.LEVERS:
        for p in lv.params:
            values[lv.key][p.key] = (float(rng.choice(W.RECAP_YEARS)) if p.edges is None
                                     else float(rng.uniform(p.edges[0], p.edges[4])))
    return values, {lv.key: bool(rng.random() < 0.7) for lv in L.LEVERS}


@unittest.skipIf(MiniRacer is None or not D.XLSX.exists(), "mini-racer no instalado o falta el Excel definitivo")
class TestDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = D.read_excel()
        cls.data = W.dashboard_data(cls.info, n=4000)
        cls.js = MiniRacer()
        cls.js.eval((ROOT / "dashboard" / "motor.js").read_text(encoding="utf-8"))
        cls.js.eval(f"Motor.init({json.dumps(cls.data)})")

    def call(self, expr: str):
        return json.loads(self.js.eval(f"JSON.stringify({expr})"))

    def python(self, case, values, on, year):
        op, d, _ = D.apply_levers(D.with_case(self.info, case), self.info["deal"], values, on)
        return D.run(op, d, exit_year=year), d

    def test_cases_match_python(self):
        rng = np.random.default_rng(7)
        for i in range(40):
            values, on = random_plan(rng)
            case, year = D.CASES[i % 4], int(rng.integers(2026, 2033))
            js = self.call(f"(r => [r.res.irr, r.res.mom, r.res.min_dscr, r.res.gp_irr, r.res.lp_irr, r.res.equity_exit,"
                           f" r.res.su.sponsor, r.res.ebitda_pre[6], r.res.senior_nd_ebitda[6], r.res.dividend.reduce((a, b) => a + b, 0),"
                           f" r.lever.op.capex_exp[3]])(Motor.runCase({json.dumps(case)}, {json.dumps(values)}, {json.dumps(on)}, {year}))")
            r, _ = self.python(case, values, on, year)
            op, _, _ = D.apply_levers(D.with_case(self.info, case), self.info["deal"], values, on)
            py = [r["irr"][0], r["mom"][0], r["min_dscr"][0], r["gp_irr"][0], r["lp_irr"][0], r["equity_exit"][0],
                  r["su"]["sponsor"], r["ebitda_pre"][0, 6], r["senior_nd_ebitda"][0, 6], r["dividend"][0].sum(), op.capex_exp[0, 3]]
            np.testing.assert_allclose(js, py, rtol=1e-11, atol=1e-11, err_msg=f"{case} {year} {on}")

    def test_deal_structure_matches_python(self):
        """El panel de estructura (Motor.setDeal) da lo mismo que cambiar esas hipótesis en Python."""
        from dataclasses import replace
        rng = np.random.default_rng(13)
        try:
            for i in range(12):
                patch = dict(premium=float(rng.uniform(0, 0.4)), rollover=float(rng.uniform(0, 0.59)),
                             tla_x=float(rng.uniform(0, 4)), tlb_x=float(rng.uniform(0, 5)), sub_x=float(rng.uniform(0, 3)),
                             vl_share=float(rng.uniform(0, 0.08)), euribor=float(rng.uniform(0, 0.06)),
                             tlb_sweep=float(rng.uniform(0, 1)), lp_share=float(rng.uniform(0.5, 0.95)),
                             hurdle=float(rng.uniform(0, 0.15)), carry=float(rng.uniform(0, 0.3)))
                if i % 3 == 0:
                    patch["exit_multiple"] = float(rng.uniform(12, 28))
                values, on = random_plan(rng)
                case, year = D.CASES[i % 4], int(rng.integers(2026, 2033))
                js = self.call(f"(Motor.setDeal({json.dumps(patch)}), (r => [r.res.irr, r.res.lp_irr, r.res.gp_irr, r.res.min_dscr, r.res.su.sponsor])"
                               f"(Motor.runCase({json.dumps(case)}, {json.dumps(values)}, {json.dumps(on)}, {year})))")
                d = replace(self.info["deal"], **patch)
                op, d2, _ = D.apply_levers(D.with_case(self.info, case), d, values, on)
                r = D.run(op, d2, exit_year=year)
                np.testing.assert_allclose(js, [r["irr"][0], r["lp_irr"][0], r["gp_irr"][0], r["min_dscr"][0], r["su"]["sponsor"]],
                                           rtol=1e-11, atol=1e-11, err_msg=str(patch))
        finally:
            self.js.eval("Motor.setDeal({})")

    def test_no_levers_reproduces_saved_excel(self):
        import openpyxl
        ls = openpyxl.load_workbook(D.XLSX, data_only=True)["LBO Summary"]
        case = D.CASES[self.info["active_case"] - 1]
        off = {lv.key: False for lv in L.LEVERS}
        js = self.call(f"(r => [r.res.irr, r.res.mom, r.res.lp_irr, r.res.gp_irr, r.res.su.sponsor])"
                       f"(Motor.runCase({json.dumps(case)}, Motor.defaults(), {json.dumps(off)}))")
        np.testing.assert_allclose(js, [ls[c].value for c in ("K17", "L17", "K21", "L18", "E39")], rtol=1e-12)

    def test_shapley_matches_python(self):
        values, on = L.band_values("Optimista"), {lv.key: True for lv in L.LEVERS}
        values["recap"].update(W.RECAP_DEFAULT)
        on["lefties"] = False
        phi_js = self.call(f"Motor.shapley('Base', {json.dumps(values)}, {json.dumps(on)}, 2030)")
        keys = [k for k, v in on.items() if v]

        def irr(subset):
            return self.python("Base", values, {k: k in subset for k in on}, 2030)[0]["irr"][0]

        n = len(keys)
        for k in keys:
            others = [x for x in keys if x != k]
            phi = sum(factorial(s) * factorial(n - s - 1) / factorial(n) * (irr(set(c) | {k}) - irr(set(c)))
                      for s in range(n) for c in combinations(others, s))
            self.assertAlmostEqual(phi_js[k], phi, places=10)
        self.assertAlmostEqual(sum(phi_js.values()), irr(set(keys)) - irr(set()), places=10)

    def test_value_bridge_matches_python(self):
        rng = np.random.default_rng(11)
        for i in range(8):
            values, on = random_plan(rng)
            on["propco"] = on["recap"] = i % 2 == 0
            case, year = D.CASES[i % 4], 2026 + i % 7
            b = self.call(f"(r => Motor.valueBridge(r.res, r.lever.deal))"
                          f"(Motor.runCase({json.dumps(case)}, {json.dumps(values)}, {json.dumps(on)}, {year}))")
            r, d = self.python(case, values, on, year)
            py = D.value_bridge(r, d)
            self.assertAlmostEqual(b["start"] + sum(b["items"].values()), b["end"], delta=1e-6)
            for k, v in py["items"].items():
                self.assertAlmostEqual(b["items"][k], v[0], delta=1e-6, msg=k)

    def test_simulation_matches_python(self):
        op = W.sim_operating(self.data)
        f32 = lambda b: np.frombuffer(base64.b64decode(b), dtype="<f4").astype(float)
        mult = {k: f32(v) for k, v in self.data["sim"]["mult"].items()}
        scale = op.revenue / np.median(op.revenue, axis=0)
        values, on = L.band_values("Normal"), {lv.key: True for lv in L.LEVERS}
        values["recap"].update(W.RECAP_DEFAULT)
        d = self.info["deal"]
        for with_plan in (False, True):
            js = self.call(f"Motor.riskSummary(Motor.simulate({json.dumps(values)}, {json.dumps(on)}, {str(with_plan).lower()}, 2031))")
            if with_plan:
                op2, d2, _ = D.apply_levers(op, d, values, on, mult=mult, scale=scale)
                res = D.run(op2, d2, exit_year=2031)
            else:
                res = D.run(op, d, exit_year=2031)
            py = W.risk_summary(res, d.dscr_min)
            self.assertAlmostEqual(js["irr_median"], py["TIR mediana"], places=9)
            self.assertAlmostEqual(js["irr_p10"], py["TIR P10"], places=9)
            self.assertAlmostEqual(js["p_irr_15"], py["P(TIR ≥ 15 %)"], places=12)
            self.assertAlmostEqual(js["p_dscr"], py["P(DSCR mínimo < covenant)"], places=12)
            self.assertAlmostEqual(js["ebitda_last_median"], np.median(res["ebitda_pre"][:, -1]), places=6)
            self.assertAlmostEqual(sum(js["irr_hist"]["share"]), 1.0, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
