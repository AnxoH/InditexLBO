"""Dashboard web del plan de creación de valor: exporta los datos y monta una página HTML autocontenida.

La página (dashboard/plantilla.html) lleva dentro el motor en JavaScript (dashboard/motor.js, traducción
de lbo.py y levers.py), los cuatro casos del business plan y los 20.000 caminos simulados, así que
funciona sin Python ni Excel. Sus valores se pasan a la hoja Palancas del Excel integrado pegando una
columna o con pasar_al_excel.py.

Regenerar:  .venv/bin/python -m bp.web   (desde la carpeta «Business Plan»)
"""

from __future__ import annotations

import base64
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from . import levers as L
from .analysis import CASE_PERCENTILES
from .lbo import FLOW_YEARS, YEARS

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard"
OUTPUT = ROOT / "output" / "Dashboard_palancas.html"
CASES = ("Base", "Bull", "Bear", "Bank case")  # mismo orden que el selector LBO_Rollover50!F9 (1-4)
VARS = ("revenue", "gross_profit", "opex_post", "lease", "capex", "wc")
FIRST_ROW = 19  # primera palanca en la hoja Palancas (columna D)
# Paso de los deslizadores, por parámetro.
STEP = {"m2": 1, "density": 100, "margin": 0.005, "capex": 100, "cannib": 0.01, "uplift": 0.01, "bps": 5,
        "years": 0.5, "one_off": 0.05, "pay": 0.1, "inv": 0.1, "share": 0.05, "multiple": 0.1, "caprate": 0.0025,
        "target": 0.05, "year": 1}
YEAR_OPTIONS = (2027, 2028, 2029)


def _f32(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype="<f4").tobytes()).decode()


def excel_rows() -> list[dict]:
    """Fila de la hoja Palancas de cada interruptor y de cada parámetro (misma lógica que plan.read_dashboard)."""
    rows, r = [], FIRST_ROW
    for lv in L.LEVERS:
        rows.append({"row": r, "lever": lv.key, "param": None})
        r += 1
        for p in lv.params:
            rows.append({"row": r, "lever": lv.key, "param": p.key})
            r += 1
        r += 1
    return rows


def dashboard_data(o: dict, seed: int = 11) -> dict:
    """Todo lo que necesita la página: hipótesis de la operación, palancas, casos y caminos simulados."""
    op = o["op"]
    n = op.revenue.shape[0]
    # Mismos multiplicadores de ejecución que plan.simulate_plan con todas las palancas activas.
    mult = L.execution_multipliers(np.random.default_rng(seed), n)
    risky = [lv.key for lv in L.LEVERS if lv.execution[0] < lv.execution[2]]

    deal = asdict(o["deal"])
    deal["tla_amort"] = list(deal["tla_amort"])
    row_of = {(x["lever"], x["param"]): x["row"] for x in excel_rows()}
    levers = [{
        "key": lv.key, "name": lv.name, "what": lv.what, "kind": lv.kind, "execution": list(lv.execution),
        "row": row_of[(lv.key, None)],
        "params": [{"key": p.key, "label": p.label, "unit": p.unit, "default": p.default, "reverse": p.reverse,
                    "edges": None if p.edges is None else list(p.edges), "anchor": p.anchor, "fmt": p.fmt,
                    "step": STEP[p.key], "row": row_of[(lv.key, p.key)],
                    "options": list(YEAR_OPTIONS) if p.key == "year" else None} for p in lv.params],
    } for lv in L.LEVERS]

    cases = {name: {v: getattr(o["case_ops"][name], v)[0].tolist() for v in VARS} for name in CASES}
    return {
        "years": YEARS.tolist(), "flow_years": FLOW_YEARS.tolist(), "wc_fy25": op.wc_fy25,
        "fy25": {"revenue": 39864.0, "ebitda_pre": o["deal"].ebitda_ref},
        "deal": deal, "entry_multiple": o["deal"].entry_multiple,
        "F_COHORT": L.F_COHORT.tolist(), "G_COHORT": L.G_COHORT.tolist(), "H_COHORT": L.H_COHORT.tolist(),
        "GROUP_MARGIN": L.GROUP_MARGIN, "LEASE_SHARE": L.LEASE_SHARE, "BASE_DENSITY": L.BASE_DENSITY,
        "LAND_BUILDINGS_NBV": L.LAND_BUILDINGS_NBV, "WC_PHASE": L.WC_PHASE.tolist(),
        "levers": levers, "cases": cases, "case_order": list(CASES),
        "case_percentiles": {k: CASE_PERCENTILES[k] for k in CASES},
        "sim": {"n": n, "seed": seed, "vars": {v: _f32(getattr(op, v)) for v in VARS},
                "mult": {k: _f32(mult[k]) for k in risky}},
    }


def build_dashboard(o: dict, path: Path = OUTPUT, standalone: bool = True) -> Path:
    """standalone=True escribe un documento completo para abrirlo con doble clic; False, solo el contenido
    (la plataforma de artifacts de claude.ai añade ella misma el esqueleto del documento)."""
    page = (DASH / "plantilla.html").read_text(encoding="utf-8")
    motor = (DASH / "motor.js").read_text(encoding="utf-8")
    data = json.dumps(dashboard_data(o), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = page.replace("/*__MOTOR__*/", motor).replace("/*__DATOS__*/null", data)
    if standalone:
        page = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                f"</head>\n<body>\n{page}\n</body>\n</html>\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return path


if __name__ == "__main__":
    from .pipeline import build

    print(build_dashboard(build(figures=False)))
