"""
test_dashboard.py
=================
Verificación del dashboard web:
- El motor JavaScript (dashboard/motor.js) da los mismos resultados que Python en los cuatro casos con
  combinaciones aleatorias de palancas, y el mismo reparto de Shapley.
- La simulación del dashboard (20.000 caminos en float32 con riesgo de ejecución) coincide con Python.
- La columna que se copia en el dashboard se lee igual en pasar_al_excel.py, y escrita en una copia del
  Excel integrado se lee igual que la hoja Palancas.
Necesita mini-racer (pip install mini-racer); sin él, se salta.
"""

from pathlib import Path
from itertools import combinations
from math import factorial
import base64
import json
import shutil
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bp import levers as L  # noqa: E402
from bp import web as W  # noqa: E402
from bp.analysis import risk_summary  # noqa: E402
from bp.lbo import Operating, run  # noqa: E402
from bp.pipeline import build  # noqa: E402

try:
    from py_mini_racer import MiniRacer
except ImportError:
    MiniRacer = None

EXCEL = ROOT.parent / "Excels" / "Inditex_LBO_Rollover50_BusinessPlan.xlsx"


def random_plan(rng):
    values = L.default_values()
    for lv in L.LEVERS:
        for p in lv.params:
            values[lv.key][p.key] = (float(rng.choice(W.YEAR_OPTIONS)) if p.edges is None
                                     else float(rng.uniform(p.edges[0], p.edges[4])))
    return values, {lv.key: bool(rng.random() < 0.7) for lv in L.LEVERS}


@unittest.skipIf(MiniRacer is None, "mini-racer no instalado")
class TestDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = build(n=4000, figures=False)
        cls.data = W.dashboard_data(cls.o)
        cls.js = MiniRacer()
        cls.js.eval((ROOT / "dashboard" / "motor.js").read_text(encoding="utf-8"))
        cls.js.eval(f"Motor.init({json.dumps(cls.data)})")

    def call(self, expr: str):
        return json.loads(self.js.eval(f"JSON.stringify({expr})"))

    def test_cases_match_python(self):
        rng = np.random.default_rng(7)
        for i in range(40):
            values, on = random_plan(rng)
            case = W.CASES[i % 4]
            js = self.call(f"(r => ({{irr: r.res.irr, mom: r.res.mom, dscr: r.res.min_dscr, e: r.res.ebitda_pre[4],"
                           f" snd: r.res.senior_nd_ebitda[4], eq: r.res.equity_exit, sp: r.res.su.sponsor,"
                           f" div: r.res.dividend.reduce((a, b) => a + b, 0), capex: r.lever.op.capex}}))"
                           f"(Motor.runCase({json.dumps(case)}, {json.dumps(values)}, {json.dumps(on)}))")
            lr = L.apply(self.o["case_ops"][case], self.o["deal"], values, on)
            py = run(lr.op, lr.deal)
            expected = [py["irr"][0], py["mom"][0], py["min_dscr"][0], py["ebitda_pre"][0, -1],
                        py["senior_nd_ebitda"][0, -1], py["equity_exit"][0], py["su"]["sponsor"],
                        py["dividend"][0].sum()]
            got = [js["irr"], js["mom"], js["dscr"], js["e"], js["snd"], js["eq"], js["sp"], js["div"]]
            np.testing.assert_allclose(got, expected, rtol=1e-9, atol=1e-9, err_msg=f"{case} {on}")
            np.testing.assert_allclose(js["capex"], lr.op.capex[0], rtol=1e-12)

    def test_shapley_matches_python(self):
        values, on = L.band_values("Optimista"), {lv.key: True for lv in L.LEVERS}
        on["lefties"] = False
        phi_js = self.call(f"Motor.shapley('Base', {json.dumps(values)}, {json.dumps(on)})")
        keys = [k for k, v in on.items() if v]
        op, deal = self.o["case_ops"]["Base"], self.o["deal"]

        def irr(subset):
            lr = L.apply(op, deal, values, {k: k in subset for k in on})
            return run(lr.op, lr.deal)["irr"][0]

        n = len(keys)
        for k in keys:
            others = [x for x in keys if x != k]
            phi = sum(factorial(s) * factorial(n - s - 1) / factorial(n) * (irr(set(c) | {k}) - irr(set(c)))
                      for s in range(n) for c in combinations(others, s))
            self.assertAlmostEqual(phi_js[k], phi, places=10)
        self.assertAlmostEqual(sum(phi_js.values()), irr(set(keys)) - irr(set()), places=10)

    def test_value_bridge_adds_up(self):
        rng = np.random.default_rng(11)
        for i in range(12):
            values, on = random_plan(rng)
            on["propco"] = on["recap"] = i % 2 == 0
            case = W.CASES[i % 4]
            b = self.call(f"(r => Motor.valueBridge(r.res, r.lever.deal))"
                          f"(Motor.runCase({json.dumps(case)}, {json.dumps(values)}, {json.dumps(on)}))")
            self.assertAlmostEqual(b["start"] + sum(b["items"].values()), b["end"], delta=1e-6 * b["end"])
            lr = L.apply(self.o["case_ops"][case], self.o["deal"], values, on)
            py, d = run(lr.op, lr.deal), lr.deal
            self.assertAlmostEqual(b["end"], py["equity_exit"][0], delta=1e-6)
            self.assertAlmostEqual(b["dividend"], py["dividend"][0].sum(), delta=1e-6)
            ev_entry = d.offer_price * d.shares_m - d.net_cash_fy25
            self.assertAlmostEqual(b["items"]["ebitda"], py["ev_exit"][0] - ev_entry, delta=1e-6)
            self.assertAlmostEqual(b["items"]["propco"], d.propco_proceeds, delta=1e-9)

    def test_simulation_matches_python(self):
        s = self.data["sim"]
        f32 = lambda b: np.frombuffer(base64.b64decode(b), dtype="<f4").astype(float)
        op = Operating(**{v: f32(s["vars"][v]).reshape(-1, 5) for v in W.VARS}, wc_fy25=self.data["wc_fy25"])
        mult = {k: f32(v) for k, v in s["mult"].items()}
        scale = op.revenue / np.median(op.revenue, axis=0)
        values, on = L.band_values("Normal"), {lv.key: True for lv in L.LEVERS}
        for with_plan in (False, True):
            js = self.call(f"Motor.riskSummary(Motor.simulate({json.dumps(values)}, {json.dumps(on)}, {str(with_plan).lower()}))")
            if with_plan:
                lr = L.apply(op, self.o["deal"], values, on, mult=mult, scale=scale)
                res = run(lr.op, lr.deal)
            else:
                res = run(op, self.o["deal"])
            py = risk_summary(res)
            self.assertAlmostEqual(js["irr_median"], py["TIR mediana"], places=9)
            self.assertAlmostEqual(js["irr_p10"], py["TIR P10"], places=9)
            self.assertAlmostEqual(js["p_irr_15"], py["P(TIR ≥ 15 %)"], places=12)
            self.assertAlmostEqual(js["p_dscr_12"], py["P(DSCR mínimo < 1,2x)"], places=12)
            self.assertAlmostEqual(js["ebitda2030_median"], np.median(res["ebitda_pre"][:, -1]), places=6)
            self.assertAlmostEqual(sum(js["irr_hist"]["share"]), 1.0, places=12)
        # float32 apenas mueve el resultado respecto a la simulación original en float64
        base = self.call(f"Motor.riskSummary(Motor.simulate({json.dumps(values)}, {json.dumps(on)}, false))")
        self.assertAlmostEqual(base["irr_median"], float(np.median(self.o["res"]["irr"])), places=5)

    def test_excel_column_round_trip(self):
        from pasar_al_excel import parse_column, write_to_excel
        from bp.plan import read_dashboard

        rng = np.random.default_rng(3)
        values, on = random_plan(rng)
        for sep in (",", "."):
            text = self.call(f"Motor.excelColumn({json.dumps(values)}, {json.dumps(on)}, {json.dumps(sep)})")
            v2, on2 = parse_column(text)
            self.assertEqual(on2, on)
            for lv in L.LEVERS:
                for p in lv.params:
                    np.testing.assert_allclose(v2[lv.key][p.key], values[lv.key][p.key], rtol=1e-13)
            back = self.call(f"Motor.parseColumn({json.dumps(text)}, {json.dumps(sep)})")
            self.assertEqual(back["errors"], [])
            self.assertEqual(back["on"], on)
        # lo que Excel copia tal y como se ve (D21:D24): separador de miles y porcentajes
        lines = self.call(f"Motor.excelColumn(Motor.defaults(), {json.dumps(on)}, ',')").split("\n")
        lines[2:6] = ["7.500", "17,0 %", "6.000", "15%"]
        shown = self.call(f"Motor.parseColumn({json.dumps(chr(10).join(lines))}, ',')")
        self.assertEqual(shown["errors"], [])
        self.assertAlmostEqual(shown["values"]["usa"]["density"], 7500)
        self.assertAlmostEqual(shown["values"]["usa"]["margin"], 0.17)
        self.assertAlmostEqual(shown["values"]["usa"]["cannib"], 0.15)

        if not EXCEL.exists():
            return
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "copia.xlsx"
            shutil.copy2(EXCEL, copy)
            write_to_excel(values, on, copy, backup=None)
            v3, on3 = read_dashboard(copy)  # D4 (interruptor general) sigue a 1
            self.assertEqual(on3, on)
            for lv in L.LEVERS:
                for p in lv.params:
                    np.testing.assert_allclose(v3[lv.key][p.key], values[lv.key][p.key], rtol=1e-13)


if __name__ == "__main__":
    unittest.main(verbosity=2)
