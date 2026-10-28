"""Business plan estocástico de Inditex (2026-2030).

Árbol de drivers por camino y año:
    ventas      = ventas_{t-1} · (1 + crecimiento orgánico) · (1 + efecto divisa)
    orgánico    = superficie + productividad/m2, con shocks y crisis tipo COVID (salto + rebote)
    margen bruto: AR(1) con vuelta a su media de largo plazo
    gastos      : modelo de corrección de error sobre el ratio gastos/ventas (pre-IFRS 16)
    alquileres  : crecen con la superficie + indexación
    capex, circulante: ratios sobre ventas con ruido; en crisis las existencias no bajan

Además de la incertidumbre año a año, cada camino sortea sus propios parámetros de
largo plazo (crecimiento, margen, ratio de gastos, probabilidad de crisis...):
incertidumbre de proceso + incertidumbre paramétrica.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np

from .calibration import FY25, Calibration
from .lbo import Operating

T = 5


@dataclass
class Drivers:
    growth: np.ndarray  # crecimiento reportado de ventas
    gross_margin: np.ndarray
    opex_ratio: np.ndarray  # gastos operativos pre-IFRS 16 / ventas (incluye alquileres fijos)
    lease_growth: np.ndarray
    capex_ratio: np.ndarray
    inv: np.ndarray
    rec: np.ndarray
    pay: np.ndarray
    growth_org: np.ndarray | None = None
    fx: np.ndarray | None = None
    crisis: np.ndarray | None = None

    CORE = ("growth", "gross_margin", "opex_ratio", "lease_growth", "capex_ratio", "inv", "rec", "pay")

    def subset(self, idx) -> "Drivers":
        return Drivers(**{f.name: (None if getattr(self, f.name) is None else getattr(self, f.name)[idx])
                          for f in fields(self)})


def project(dr: Drivers) -> Operating:
    """Convierte drivers en cuenta de resultados, capex y circulante (€m)."""
    rev = FY25["revenue"] * np.cumprod(1 + dr.growth, axis=1)
    lease = FY25["lease"] * np.cumprod(1 + dr.lease_growth, axis=1)
    opex_pre = dr.opex_ratio * rev
    return Operating(revenue=rev, gross_profit=rev * dr.gross_margin, opex_post=opex_pre - lease, lease=lease,
                     capex=rev * dr.capex_ratio, wc=rev * (dr.inv + dr.rec + dr.pay))


def simulate(cal: Calibration, n: int = 20000, seed: int = 2026) -> Drivers:
    rng = np.random.default_rng(seed)
    p = cal.params
    draw = lambda k: rng.normal(p[k].value, p[k].se, n) if p[k].se > 0 else np.full(n, p[k].value)

    # Parámetros de largo plazo propios de cada camino.
    space = draw("space_growth")
    mu_org = draw("org_mean") + (space - p["space_growth"].value)
    mu_fx = draw("fx_mean")
    mu_gm = draw("gm_mean")
    r_bar = np.clip(draw("opex_ratio_mean"), 0.33, 0.37)
    beta = np.clip(draw("opex_beta"), 0.4, 1.0)
    gamma = np.clip(draw("opex_gamma"), -0.9, -0.05)
    mu_capex = draw("capex_mean")
    mu_inv, mu_rec, mu_pay = (rng.normal(p[k].value, p[k].se / 2, n) for k in ("inv_mean", "rec_mean", "pay_mean"))
    p_crisis = rng.beta(p["crisis_a"].value, p["crisis_b"].value, n)

    L = np.linalg.cholesky(cal.corr)
    z = rng.standard_normal((n, T, 4)) @ L.T  # shocks correlacionados: orgánico, margen, gastos, divisa

    out = {k: np.zeros((n, T)) for k in Drivers.CORE + ("growth_org", "fx", "crisis")}
    base_org = np.full(n, p["org_start"].value)
    gm_prev = np.full(n, FY25["gross_margin"])
    ln_r_prev = np.log(np.full(n, (FY25["opex_post"] + FY25["lease"]) / FY25["revenue"]))
    rev_prev = np.full(n, FY25["revenue"])
    inv_prev = np.full(n, FY25["inventory"])
    jump_prev = np.zeros(n)
    expected = np.log((1 + mu_org) * (1 + mu_fx))

    for t in range(T):
        crisis = rng.random(n) < p_crisis
        jump = np.where(crisis, np.clip(rng.normal(p["crisis_size"].value, p["crisis_size"].se, n), -0.5, -0.05), 0.0)
        rho = np.clip(rng.normal(p["crisis_rebound"].value, p["crisis_rebound"].se, n), 0.5, 1.0)
        rebound = np.where(jump_prev < 0, (1 / (1 + jump_prev)) ** rho - 1, 0.0)

        base_org = mu_org + p["org_phi"].value * (base_org - mu_org) + p["org_sd"].value * z[:, t, 0]
        g_org = (1 + base_org) * (1 + jump) * (1 + rebound) - 1
        fx = (p["fx_2026"].value if t == 0 else mu_fx) + p["fx_sd"].value * z[:, t, 3]
        g = (1 + g_org) * (1 + fx) - 1

        gm = mu_gm + p["gm_phi"].value * (gm_prev - mu_gm) + p["gm_sd"].value * z[:, t, 1]

        surprise = np.log(1 + g) - expected
        ln_r = ln_r_prev - (1 - beta) * surprise + gamma * (ln_r_prev - np.log(r_bar)) + p["opex_sd"].value * z[:, t, 2]

        cpi = rng.normal(p["rent_index"].value, p["rent_index"].se, n)
        lease_g = (1 + space) * (1 + cpi) - 1

        rev = rev_prev * (1 + g)
        if t == 0:  # 2026: guía de la compañía, escalada si las ventas del camino se desvían de lo esperado
            capex_ratio = np.full(n, p["capex_2026"].value / (FY25["revenue"] * (1 + p["org_mean"].value)
                                                              * (1 + p["fx_2026"].value)))
        else:
            capex_ratio = np.clip(mu_capex + p["capex_sd"].value * rng.standard_normal(n), 0.02, 0.09)
        inv_normal = mu_inv + 0.004 * rng.standard_normal(n)
        inv = np.where(crisis, inv_prev / rev, inv_normal)  # en crisis el stock ya comprado no baja
        rec = mu_rec + 0.001 * rng.standard_normal(n)
        pay = mu_pay + 0.005 * rng.standard_normal(n)

        for k, v in dict(growth=g, gross_margin=gm, opex_ratio=np.exp(ln_r), lease_growth=lease_g,
                         capex_ratio=capex_ratio, inv=inv, rec=rec, pay=pay, growth_org=g_org, fx=fx,
                         crisis=crisis.astype(float)).items():
            out[k][:, t] = v

        gm_prev, ln_r_prev, rev_prev, inv_prev, jump_prev = gm, ln_r, rev, inv * rev, jump

    return Drivers(**out)
