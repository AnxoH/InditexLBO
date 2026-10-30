"""Dashboard web del plan de creación de valor sobre el modelo definitivo del grupo.

La página (dashboard/plantilla.html) lleva dentro el motor en JavaScript (dashboard/motor.js, traducción de
definitiva.py y levers.py), las hipótesis y los cuatro casos leídos del Excel definitivo
(Excels/Inditex_LBO_Version_Definitiva.xlsx) y 20.000 caminos simulados a siete años, así que funciona sin
Python ni Excel. Si el grupo cambia el Excel, basta con regenerarla.

Regenerar:  .venv/bin/python -m bp.web   (desde la carpeta «Business Plan»)
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import asdict
from pathlib import Path

import numpy as np

from . import definitiva as D
from . import levers as L

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "dashboard"
OUTPUT = ROOT / "output" / "Dashboard_palancas.html"
N_PATHS = 20000
SIM_SEED = 2026
MARKET_MULTIPLE = (55.42 * 3116.652 - 10958) / 9433  # EV/EBITDA pre-IFRS 16 a precio de mercado, sin prima
VARS = ("revenue", "gross_profit", "opex", "lease", "capex", "wc")
# Paso de los deslizadores, por parámetro.
STEP = {"m2": 1, "density": 100, "margin": 0.005, "capex": 100, "cannib": 0.01, "uplift": 0.01, "bps": 5,
        "years": 0.5, "one_off": 0.05, "pay": 0.1, "inv": 0.1, "share": 0.05, "multiple": 0.1, "caprate": 0.0025,
        "target": 0.05, "year": 1}
# Recap en el horizonte de siete años: el año del dividendo y la deuda senior neta objetivo por defecto.
RECAP_YEARS = (2027, 2028, 2029, 2030, 2031)
RECAP_DEFAULT = {"year": 2031, "target": 3.0}

# Hoja Palancas del Excel integrado anterior (Inditex_LBO_Rollover50_BusinessPlan.xlsx), que usa pasar_al_excel.py.
FIRST_ROW = 19
YEAR_OPTIONS = (2027, 2028, 2029)


def _f32(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype="<f4").tobytes()).decode()


def excel_rows() -> list[dict]:
    """Fila de la hoja Palancas del Excel integrado anterior de cada interruptor y de cada parámetro."""
    rows, r = [], FIRST_ROW
    for lv in L.LEVERS:
        rows.append({"row": r, "lever": lv.key, "param": None})
        r += 1
        for p in lv.params:
            rows.append({"row": r, "lever": lv.key, "param": p.key})
            r += 1
        r += 1
    return rows


def dashboard_defaults() -> dict:
    """Valores por defecto de las palancas en el dashboard (el recap, ajustado al horizonte de siete años)."""
    values = L.default_values()
    values["recap"].update(RECAP_DEFAULT)
    return values


def _op_dict(op: D.OpDef) -> dict:
    return {k: getattr(op, k)[0].tolist() for k in ("revenue", "gross_profit", "opex", "lease", "capex_maint",
                                                    "capex_exp", "wc")}


def _lever_meta(info: dict) -> list[dict]:
    """Palancas para la página, con los textos que dependen del caso Base del Excel."""
    d, base = info["deal"], D.with_case(info, "Base")
    res = D.run(base, d)
    years = [d.first_year + t for t in range(info["n_years"])]
    opex_ratio = lambda t: (base.opex[0, t] + base.lease[0, t]) / base.revenue[0, t]
    fy = info["fy25"]
    opex25 = (fy["opex"] + fy["lease"]) / fy["revenue"]
    es = lambda v, f: format(v, f).replace(".", ",")
    snd = res["senior_nd_ebitda"][0]
    anchors = {
        ("efficiency", "bps"): (f"El caso Base del Excel ya baja los gastos (con alquileres) del {es(opex25 * 100, '.1f')} % "
                                f"al {es(opex_ratio(-1) * 100, '.1f')} % de las ventas en {years[-1]}: este ahorro es adicional"),
        ("recap", "target"): (f"Senior neta al cierre {es((D.sources_and_uses(d)['tla'] + D.sources_and_uses(d)['tlb'] - d.min_cash) / d.ebitda_ref, '.1f')}x; "
                              f"en el caso Base baja a {es(snd[3], '.1f')}x en {years[3]} y {es(snd[5], '.1f')}x en {years[5]}"),
        ("recap", "year"): f"De {RECAP_YEARS[0]} a {RECAP_YEARS[-1]}; si la salida es antes, no hay dividendo",
    }
    defaults = dashboard_defaults()
    return [{
        "key": lv.key, "name": lv.name, "what": lv.what, "kind": lv.kind, "execution": list(lv.execution),
        "params": [{"key": p.key, "label": p.label, "unit": p.unit, "default": defaults[lv.key][p.key],
                    "reverse": p.reverse, "edges": None if p.edges is None else list(p.edges),
                    "anchor": anchors.get((lv.key, p.key), p.anchor), "fmt": p.fmt, "step": STEP[p.key],
                    "options": list(RECAP_YEARS) if p.key == "year" else None} for p in lv.params],
    } for lv in L.LEVERS]


def dashboard_data(info: dict | None = None, n: int = N_PATHS, seed: int = 11) -> dict:
    """Todo lo que necesita la página: hipótesis y casos del Excel, palancas y caminos simulados."""
    info = info or D.read_excel()
    d, T = info["deal"], info["n_years"]
    op, meta = D.simulated_paths(info, n=n, seed=SIM_SEED)
    # Mismos multiplicadores de ejecución que plan.simulate_plan con todas las palancas activas.
    mult = L.execution_multipliers(np.random.default_rng(seed), n)
    risky = [lv.key for lv in L.LEVERS if lv.execution[0] < lv.execution[2]]
    F, G, H = L.cohort_factors(T)

    deal = asdict(d)
    deal["tla_amort"] = list(deal["tla_amort"])
    pct = {k: int(m.group(1)) for k, lab in info["labels"].items() if (m := re.search(r"P(\d+)", lab))}
    sim_vars = dict(revenue=op.revenue, gross_profit=op.gross_profit, opex=op.opex, lease=op.lease, capex=op.capex,
                    wc=op.wc)
    return {
        "years": [d.first_year + t for t in range(T)], "fy25": info["fy25"], "deal": deal,
        "entry_multiple": d.entry_multiple, "market_multiple": MARKET_MULTIPLE,
        "lev_step": D.LEV_STEP, "lev_floor": D.LEV_FLOOR,
        "excel": {"file": info["path"].name, "active_case": info["active_case"]},
        "F_COHORT": F.tolist(), "G_COHORT": G.tolist(), "H_COHORT": H.tolist(),
        "GROUP_MARGIN": L.GROUP_MARGIN, "LEASE_SHARE": L.LEASE_SHARE, "BASE_DENSITY": L.BASE_DENSITY,
        "LAND_BUILDINGS_NBV": L.LAND_BUILDINGS_NBV, "WC_PHASE": L._pad(L.WC_PHASE, T).tolist(),
        "levers": _lever_meta(info), "case_order": list(D.CASES), "case_labels": info["labels"],
        "case_percentiles": pct, "case_drivers": info["cases"],
        "cases": {name: _op_dict(D.with_case(info, name)) for name in D.CASES},
        "sim": {"n": n, "seed": SIM_SEED, "maint_share": np.asarray(meta["maint_share"], dtype=float).tolist(),
                "vars": {v: _f32(x) for v, x in sim_vars.items()}, "mult": {k: _f32(mult[k]) for k in risky}},
    }


def sim_operating(data: dict) -> D.OpDef:
    """Los caminos tal y como los ve la página (float32), para comprobar el motor JavaScript desde Python."""
    s = data["sim"]
    T = len(data["years"])
    f32 = lambda b: np.frombuffer(base64.b64decode(b), dtype="<f4").astype(float).reshape(-1, T)
    v = {k: f32(s["vars"][k]) for k in VARS}
    share = np.asarray(s["maint_share"], dtype=float)
    return D.OpDef(revenue=v["revenue"], gross_profit=v["gross_profit"], opex=v["opex"], lease=v["lease"],
                   capex_maint=v["capex"] * share, capex_exp=v["capex"] * (1 - share), wc=v["wc"], wc0=data["fy25"]["wc"])


def risk_summary(res: dict, dscr_min: float) -> dict:
    irr = res["irr"]
    return {"TIR mediana": np.median(irr), "TIR P10": np.percentile(irr, 10), "TIR P90": np.percentile(irr, 90),
            "P(TIR ≥ 15 %)": (irr >= 0.15).mean(), "P(DSCR mínimo < covenant)": (res["min_dscr"] < dscr_min).mean()}


def build_dashboard(path: Path = OUTPUT, standalone: bool = True, data: dict | None = None) -> Path:
    """standalone=True escribe un documento completo para abrirlo con doble clic; False, solo el contenido
    (la plataforma de artifacts de claude.ai añade ella misma el esqueleto del documento)."""
    page = (DASH / "plantilla.html").read_text(encoding="utf-8")
    motor = (DASH / "motor.js").read_text(encoding="utf-8")
    data = json.dumps(data or dashboard_data(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = page.replace("/*__MOTOR__*/", motor).replace("/*__DATOS__*/null", data)
    # Logo y monograma de Herrera Lázaro Pérez Partners (sacados de la presentación del grupo)
    png = lambda name: "data:image/png;base64," + base64.b64encode((DASH / name).read_bytes()).decode()
    page = page.replace("/*__LOGO__*/", png("hlp_logo.png")).replace("/*__MONO__*/", png("hlp_monograma.png"))
    if standalone:
        page = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                f"</head>\n<body>\n{page}\n</body>\n</html>\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return path


if __name__ == "__main__":
    print(build_dashboard())
