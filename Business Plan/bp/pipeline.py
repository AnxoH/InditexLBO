"""Orquesta el business plan completo: calibración → simulación → casos → LBO → riesgo → salidas."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import analysis as A
from . import charts
from .calibration import calibrate
from .lbo import GROUP_DEAL, YEARS, Deal, excel_base_operating, run
from .model import project, simulate

ROOT = Path(__file__).resolve().parents[1]
N_PATHS = 20000
SEED = 2026
MARKET_MULTIPLE = (55.42 * 3116.652 - 10958) / 9433  # EV/EBITDA pre-IFRS 16 a precio de mercado, sin prima


def build(n: int = N_PATHS, seed: int = SEED, deal: Deal = GROUP_DEAL, figures: bool = True) -> dict:
    cal = calibrate()
    dr = simulate(cal, n=n, seed=seed)
    op = project(dr)
    res = run(op, deal)

    excel_op = excel_base_operating()
    excel_res = run(excel_op, deal)
    excel_pctile = (op.ebitda_pre[:, -1] < excel_op.ebitda_pre[0, -1]).mean() * 100

    case_drivers = A.extract_cases(dr, op)
    case_ops = {k: project(v) for k, v in case_drivers.items()}
    case_res = {k: run(o, deal) for k, o in case_ops.items()}

    crisis = dr.crisis.max(axis=1) > 0
    frontier = A.leverage_frontier(op, deal)
    capacity = pd.DataFrame({
        "Sin crisis tipo COVID": {f"{int(s*100)} % TLA": A.max_senior(op, deal, s, mask=~crisis) for s in (0.5, 0.25, 0.0)},
        "Incluyendo crisis": {f"{int(s*100)} % TLA": A.max_senior(op, deal, s) for s in (0.5, 0.25, 0.0)},
    })

    rng = np.random.default_rng(seed + 1)
    exit_mult = rng.triangular(15.0, MARKET_MULTIPLE, deal.entry_multiple, n)
    res_mult = run(op, replace(deal, exit_multiple=exit_mult))
    phi, r2 = A.shapley_r2(res_mult["irr"], A.path_factors(dr, op, exit_mult))

    premiums = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    exits = [14.0, 15.0, 16.0, round(MARKET_MULTIPLE, 2), 18.0, 19.0, round(deal.entry_multiple, 2)]
    grid = pd.DataFrame([[np.median(run(op, replace(deal, premium=p, exit_multiple=m))["irr"]) for m in exits]
                         for p in premiums], index=premiums, columns=exits)

    required = pd.DataFrame([
        {"TIR objetivo": t, "Múltiplo de salida": m, "EBITDA 2030 necesario": e,
         "TACC EBITDA 2025-30 necesaria": (e / 9433) ** (1 / 5) - 1, "Probabilidad según la simulación": (op.ebitda_pre[:, -1] >= e).mean()}
        for t in (0.15, 0.20) for m in (MARKET_MULTIPLE, deal.entry_multiple)
        for e in [A.required_ebitda(deal, res, t, m)]
    ])

    vcp_res = run(project(A.value_creation_plan(dr)), deal)

    out = dict(cal=cal, dr=dr, op=op, res=res, deal=deal, excel_op=excel_op, excel_res=excel_res,
               excel_pctile=excel_pctile, case_drivers=case_drivers, case_ops=case_ops, case_res=case_res,
               frontier=frontier, capacity=capacity, shapley=phi, r2=r2, grid=grid, required=required,
               vcp_res=vcp_res, crisis=crisis, exit_mult=exit_mult)
    if figures:
        out["figures"] = make_figures(out)
    return out


def make_figures(o: dict) -> list[Path]:
    h = o["cal"].history
    excel = o["excel_op"]
    sim_ratio = A.pct(o["dr"].opex_ratio)
    excel_ratio = ((excel.opex_post + excel.lease) / excel.revenue)[0]
    sim_ebitda = A.pct(o["op"].ebitda_pre)
    sim_ebitda.attrs["excel_percentile"] = o["excel_pctile"]
    case_ebitda = {k: v.ebitda_pre[0] for k, v in o["case_ops"].items()}
    return [
        charts.opex_ratio(h, sim_ratio, excel_ratio),
        charts.fx_drag(h),
        charts.ebitda_fan(h, sim_ebitda, excel.ebitda_pre[0], case_ebitda),
        charts.irr_histogram(o["res"]["irr"], float(o["excel_res"]["irr"][0])),
        charts.leverage_frontier(o["frontier"], chosen=o["deal"].total_x),
        charts.senior_capacity(o["capacity"]),
        charts.shapley(o["shapley"], o["r2"]),
        charts.premium_exit_heatmap(o["grid"]),
        charts.cases(case_ebitda, excel.ebitda_pre[0], 9433.0),
    ]


def case_summary(o: dict) -> pd.DataFrame:
    rows = {}
    for name in ["Bull", "Base", "Bear", "Bank case"]:
        opx, r = o["case_ops"][name], o["case_res"][name]
        rows[name] = {
            "Percentil (EBITDA 2030)": A.CASE_PERCENTILES[name],
            "Crecimiento ventas TACC 25-30": (opx.revenue[0, -1] / 39864) ** 0.2 - 1,
            "Margen EBITDA pre-IFRS 16 2030": opx.ebitda_pre[0, -1] / opx.revenue[0, -1],
            "EBITDA pre-IFRS 16 2030 (€m)": opx.ebitda_pre[0, -1],
            "CFADS acumulado 26-30 (€m)": r["cfads"][0].sum(),
            "DSCR mínimo": r["min_dscr"][0],
            "Deuda senior neta / EBITDA 2030": r["senior_nd_ebitda"][0, -1],
            "TIR sponsor": r["irr"][0],
            "MoM sponsor": r["mom"][0],
        }
    ex, er = o["excel_op"], o["excel_res"]
    rows["Excel del grupo (base)"] = {
        "Percentil (EBITDA 2030)": o["excel_pctile"],
        "Crecimiento ventas TACC 25-30": (ex.revenue[0, -1] / 39864) ** 0.2 - 1,
        "Margen EBITDA pre-IFRS 16 2030": ex.ebitda_pre[0, -1] / ex.revenue[0, -1],
        "EBITDA pre-IFRS 16 2030 (€m)": ex.ebitda_pre[0, -1],
        "CFADS acumulado 26-30 (€m)": er["cfads"][0].sum(),
        "DSCR mínimo": er["min_dscr"][0],
        "Deuda senior neta / EBITDA 2030": er["senior_nd_ebitda"][0, -1],
        "TIR sponsor": er["irr"][0],
        "MoM sponsor": er["mom"][0],
    }
    return pd.DataFrame(rows)
