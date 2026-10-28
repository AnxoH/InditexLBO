"""Análisis sobre la simulación: casos para el Excel, frontera de apalancamiento,
descomposición de varianza (Sobol) e ingeniería inversa de la TIR."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from .lbo import HOLD_DAYS, YEARS, Deal, Operating, run
from .model import Drivers, project

CASE_PERCENTILES = {"Bull": 80, "Base": 50, "Bear": 20, "Bank case": 10}


def pct(x: np.ndarray, qs=(5, 25, 50, 75, 95)) -> pd.DataFrame:
    return pd.DataFrame(np.percentile(x, qs, axis=0).T, index=YEARS, columns=[f"P{q}" for q in qs])


def extract_cases(dr: Drivers, op: Operating, band: float = 2.5) -> dict[str, Drivers]:
    """Caso = mediana año a año de los drivers de los caminos cuyo EBITDA 2030 cae en P±band."""
    stat = op.ebitda_pre[:, -1]
    ranks = stat.argsort().argsort() / (len(stat) - 1) * 100
    cases = {}
    for name, q in CASE_PERCENTILES.items():
        idx = np.where(np.abs(ranks - q) <= band)[0]
        cases[name] = Drivers(**{k: np.median(getattr(dr, k)[idx], axis=0, keepdims=True) for k in Drivers.CORE})
    return cases


def excel_rows(dr: Drivers) -> pd.DataFrame:
    """Drivers en el formato exacto de las filas 10-17 de la hoja LBO del Excel."""
    op = project(dr)
    opex_prev = np.concatenate([[11955.0], op.opex_post[0, :-1]])
    rows = {
        "Revenue growth (% YoY)": dr.growth[0],
        "Gross margin (% of revenues)": dr.gross_margin[0],
        "OpEx growth (% YoY)": op.opex_post[0] / opex_prev - 1,
        "Fixed lease cash outflow growth (%)": dr.lease_growth[0],
        "Capex (% of revenues)": dr.capex_ratio[0],
        "Inventory (% of revenues)": dr.inv[0],
        "Receivables (% of revenues)": dr.rec[0],
        "Payables (% of revenues, negative)": dr.pay[0],
    }
    return pd.DataFrame(rows, index=YEARS).T


def operating_table(op: Operating, res: dict | None = None) -> pd.DataFrame:
    """Lo que pide el compañero de deuda: EBITDA pre-IFRS 16, capex, circulante y caja disponible."""
    rows = {
        "Ventas": op.revenue[0],
        "Margen bruto": op.gross_profit[0],
        "Gastos operativos (sin alquileres fijos)": -op.opex_post[0],
        "EBITDA reportado (IFRS 16)": op.ebitda_reported[0],
        "Pagos fijos de arrendamiento": -op.lease[0],
        "EBITDA pre-IFRS 16": op.ebitda_pre[0],
        "Margen EBITDA pre-IFRS 16": op.ebitda_pre[0] / op.revenue[0],
        "Capex": -op.capex[0],
        "Saldo de circulante operativo": op.wc[0],
        "Flujo de caja del circulante": op.wc_cash_flow[0],
    }
    if res is not None:
        rows.update({
            "Impuestos (con escudo fiscal)": -res["tax"][0],
            "CFADS (caja para servir la deuda)": res["cfads"][0],
            "Dividendo a la BidCo (= CFADS, 100 % tras squeeze-out)": res["cfads"][0],
            "DSCR": res["dscr"][0],
            "Deuda senior neta / EBITDA": res["senior_nd_ebitda"][0],
            "Deuda total neta / EBITDA": res["total_nd_ebitda"][0],
        })
    return pd.DataFrame(rows, index=YEARS).T


def risk_summary(res: dict) -> dict:
    irr = res["irr"]
    return {
        "TIR mediana": np.median(irr),
        "TIR P10": np.percentile(irr, 10),
        "TIR P90": np.percentile(irr, 90),
        "MoM mediano": np.median(res["mom"]),
        "P(TIR < 0)": (irr < 0).mean(),
        "P(TIR ≥ 15 %)": (irr >= 0.15).mean(),
        "P(TIR ≥ 20 %)": (irr >= 0.20).mean(),
        "P(DSCR mínimo < 1,2x)": (res["min_dscr"] < 1.2).mean(),
        "P(DSCR mínimo < 1,0x)": (res["min_dscr"] < 1.0).mean(),
        "P(caja < 0 con la RCF agotada)": res["cash_shortfall"].mean(),
        "P(equity a la salida ≤ 0)": (res["equity_exit"] <= 0).mean(),
    }


def leverage_frontier(op: Operating, deal: Deal, grid=np.arange(0.0, 10.01, 0.5), stack: bool = True) -> pd.DataFrame:
    """Para cada nivel de deuda total: rentabilidad y riesgo sobre los mismos caminos (números aleatorios comunes)."""
    rows = []
    for L in grid:
        d = deal.with_stack(L) if stack else deal.with_leverage(L)
        res = run(op, d)
        rows.append({"deuda_x_ebitda": L, **risk_summary(res), "TIR media": res["irr"].mean()})
    return pd.DataFrame(rows).set_index("deuda_x_ebitda")


def max_leverage(op: Operating, deal: Deal, alpha: float = 0.05, dscr_floor: float = 1.2,
                 lo: float = 0.0, hi: float = 12.0, stack: bool = True) -> float:
    """Mayor deuda total tal que P(DSCR mínimo < dscr_floor) ≤ alpha (bisección; el riesgo es monótono en L)."""
    breach = lambda L: (run(op, deal.with_stack(L) if stack else deal.with_leverage(L))["min_dscr"] < dscr_floor).mean()
    if breach(hi) <= alpha:
        return hi
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if breach(mid) <= alpha else (lo, mid)
    return lo


def max_senior(op: Operating, deal: Deal, tla_share: float, alpha: float = 0.05, dscr_floor: float = 1.2,
               mask: np.ndarray | None = None, hi: float = 10.0) -> float:
    """Mayor deuda senior (sin PIK ni vendor loan) con P(DSCR mínimo < dscr_floor) ≤ alpha en los caminos de mask."""
    mask = np.ones(op.revenue.shape[0], bool) if mask is None else mask

    def breach(S: float) -> float:
        d = replace(deal, tla_x=S * tla_share, tlb_x=S * (1 - tla_share), pik_x=0.0, vl_x=0.0)
        return (run(op, d)["min_dscr"][mask] < dscr_floor).mean()

    lo = 0.0
    if breach(hi) <= alpha:
        return hi
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if breach(mid) <= alpha else (lo, mid)
    return lo


def shapley_r2(y: np.ndarray, factors: dict[str, np.ndarray]) -> tuple[pd.Series, float]:
    """Reparto exacto de la varianza explicada (R²) entre factores correlacionados: valor de Shapley (LMG).

    Para cada factor promedia su aportación marginal al R² sobre todos los subconjuntos de
    los demás. A diferencia de los índices de Sobol de primer orden, suma exactamente el R²
    total aunque los factores estén correlacionados.
    """
    names = list(factors)
    k = len(names)
    X = np.column_stack([(factors[n] - factors[n].mean()) / (factors[n].std() or 1.0) for n in names])
    yc = y - y.mean()
    sst = yc @ yc
    r2 = {}
    for mask in range(1 << k):
        cols = [i for i in range(k) if mask >> i & 1]
        if not cols:
            r2[mask] = 0.0
            continue
        beta, *_ = np.linalg.lstsq(X[:, cols], yc, rcond=None)
        resid = yc - X[:, cols] @ beta
        r2[mask] = 1 - resid @ resid / sst
    from math import factorial
    phi = np.zeros(k)
    for i in range(k):
        for mask in range(1 << k):
            if mask >> i & 1:
                continue
            s = bin(mask).count("1")
            w = factorial(s) * factorial(k - s - 1) / factorial(k)
            phi[i] += w * (r2[mask | 1 << i] - r2[mask])
    return pd.Series(phi, index=names).sort_values(ascending=False), r2[(1 << k) - 1]


def path_factors(dr: Drivers, op: Operating, exit_multiple: np.ndarray | None = None) -> dict[str, np.ndarray]:
    f = {
        "Crecimiento orgánico (media 26-30)": dr.growth_org.mean(axis=1),
        "Efecto divisa (media 26-30)": dr.fx.mean(axis=1),
        "Margen bruto (media 26-30)": dr.gross_margin.mean(axis=1),
        "Ratio de gastos (media 26-30)": dr.opex_ratio.mean(axis=1),
        "Capex / ventas (media 26-30)": dr.capex_ratio.mean(axis=1),
        "Circulante / ventas (2030)": (dr.inv + dr.rec + dr.pay)[:, -1],
        "Crisis tipo COVID en el periodo": dr.crisis.max(axis=1),
    }
    if exit_multiple is not None:
        f["Múltiplo de salida"] = exit_multiple
    return f


def required_ebitda(deal: Deal, base_res: dict, target_irr: float, exit_multiple: float) -> float:
    """EBITDA pre-IFRS 16 de 2030 necesario para lograr target_irr, con la deuda neta de salida mediana."""
    su = base_res["su"]
    mom = (1 + target_irr) ** (HOLD_DAYS / 365)
    equity_needed = mom * su["sponsor"] / su["sponsor_share"]
    net_debt = np.median(base_res["debt_exit"] - base_res["cash"][:, -1])
    return (equity_needed + net_debt) / (exit_multiple * (1 - deal.exit_fees_pct))


def value_creation_plan(dr: Drivers, capex_cut: float = 0.003, opex_cut: float = 0.004,
                        payables_gain: float = 0.01, inventory_cut: float = 0.003) -> Drivers:
    """Palancas operativas típicas de un sponsor, aplicadas de forma escalonada (25/50/75/100/100 %)."""
    ramp = np.array([0.25, 0.5, 0.75, 1.0, 1.0])
    return replace(dr, capex_ratio=dr.capex_ratio - capex_cut * ramp, opex_ratio=dr.opex_ratio - opex_cut * ramp,
                   pay=dr.pay - payables_gain * ramp, inv=dr.inv - inventory_cut * ramp)
