"""Calibración de los procesos estocásticos del business plan con el histórico de Inditex.

Cada parámetro guarda su valor, cómo se ha obtenido y si sale de los datos
("estimado") o de un criterio razonado ("criterio"), para que la tabla de
hipótesis de la presentación sea trazable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"

# Año fiscal 2025 (cerrado el 31-ene-2026): punto de partida de la proyección.
FY25 = dict(revenue=39864.0, gross_margin=23222 / 39864, opex_post=11955.0, lease=1834.0,
            inventory=3249.0, receivables=1166.0, payables=-8587.0, growth_cfx=0.07)
# Perspectivas 2026 publicadas por Inditex en el Informe anual 2025 (margen bruto: estable ±50 pb).
GUIDANCE_2026 = dict(capex=2300.0, fx=-0.01)


@dataclass
class Param:
    value: float
    se: float  # desviación típica de la incertidumbre sobre el propio parámetro
    how: str
    kind: str  # "estimado" o "criterio"


@dataclass
class Calibration:
    params: dict[str, Param]
    corr: np.ndarray  # correlación de los shocks [crecimiento orgánico, margen bruto, ratio de opex, divisa]
    history: pd.DataFrame
    opex_regression: dict = field(default_factory=dict)

    def __getitem__(self, key: str) -> Param:
        return self.params[key]

    def table(self) -> pd.DataFrame:
        rows = [(k, p.value, p.se, p.kind, p.how) for k, p in self.params.items()]
        return pd.DataFrame(rows, columns=["parámetro", "valor", "incertidumbre (σ)", "origen", "cómo se obtiene"])


def load_history() -> pd.DataFrame:
    h = pd.read_csv(DATA / "inditex_history_2005_2025.csv").set_index("fiscal_year")
    h["growth"] = h.net_sales_eur_m.pct_change()
    h["fx_drag"] = (1 + h.growth_reported_pct / 100) / (1 + h.growth_constant_fx_pct / 100) - 1
    h["gm"] = h.gross_margin_pct / 100
    h["opex_pre"] = h.net_sales_eur_m * h.gm - h.ebitda_pre_ifrs16_eur_m
    h["opex_ratio"] = h.opex_pre / h.net_sales_eur_m
    h["ebitda_margin_pre"] = h.ebitda_pre_ifrs16_eur_m / h.net_sales_eur_m
    return h


def load_detail() -> pd.DataFrame:
    return pd.read_csv(DATA / "inditex_operating_detail_2021_2025.csv")


def _ols(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    s2 = resid @ resid / dof
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    return beta, se, resid


def calibrate() -> Calibration:
    h = load_history()
    detail = load_detail()
    covid = [2020, 2021, 2022]
    P: dict[str, Param] = {}

    # 1. Efecto divisa: diferencia entre crecimiento reportado y a tipo de cambio constante.
    fx = h.fx_drag.dropna()
    P["fx_mean"] = Param(fx.mean(), fx.std() / np.sqrt(len(fx)),
                         f"Media de (1+g_reportado)/(1+g_tc_constante)-1 en {len(fx)} años con dato", "estimado")
    P["fx_sd"] = Param(fx.std(), 0.0, "Desviación típica anual del efecto divisa", "estimado")

    # 2. Crecimiento orgánico (tipo de cambio constante): tendencia + ruido.
    gc = (h.growth_constant_fx_pct / 100).dropna().drop(covid, errors="ignore")
    t = gc.index.values - 2025
    beta, se, resid = _ols(np.c_[np.ones(len(t)), t], gc.values)
    P["org_sd"] = Param(resid.std(ddof=2), 0.0,
                        f"σ de los residuos del crecimiento a tc constante sin tendencia ({len(gc)} años, sin COVID)",
                        "estimado")

    # Persistencia: AR(1) del crecimiento reportado sin tendencia, años consecutivos sin COVID.
    g = h.growth.loc[2006:2025].drop(covid)
    tg = g.index.values - 2025
    bg, _, rg = _ols(np.c_[np.ones(len(tg)), tg], g.values)
    rg = pd.Series(rg, index=g.index)
    pairs = [(y, y - 1) for y in rg.index if y - 1 in rg.index]
    x_lag = np.array([rg[b] for _, b in pairs]); x_now = np.array([rg[a] for a, _ in pairs])
    phi = float(np.clip(np.polyfit(x_lag, x_now, 1)[0], 0.0, 0.9))
    P["org_phi"] = Param(phi, 0.0, f"AR(1) del crecimiento sin tendencia ({len(pairs)} pares de años consecutivos)",
                         "estimado")
    trend_2026_30 = bg[0] + bg[1] * np.arange(1, 6)
    P["trend_reported_growth"] = Param(float(trend_2026_30.mean()), 0.0,
                                       f"Tendencia lineal del crecimiento reportado (pendiente {bg[1]*100:.2f} pp/año), "
                                       "media 2026-30", "estimado")

    # 3. Árbol de crecimiento: superficie (m2) + productividad por m2 a tc constante.
    area = detail[(detail.dimension == "area_m2") & (detail.item == "Total")].set_index("fiscal_year").value
    space = area.pct_change().loc[2023:2025]
    P["space_growth"] = Param(space.mean(), 0.005,
                              "Crecimiento neto de superficie 2023-25 (m2 totales, informes anuales)", "estimado")
    density_lr = 0.04  # inflación de precios ≈ 2 % + productividad real (online, ampliaciones) ≈ 2 %
    P["org_mean"] = Param(P["space_growth"].value + density_lr, 0.010,
                          "Superficie + productividad por m2 a largo plazo (≈ inflación 2 % + mejora real 2 %); "
                          "contraste: tendencia reportada + divisa", "criterio")
    P["org_start"] = Param(FY25["growth_cfx"], 0.0, "Crecimiento a tc constante FY2025 (7,0 %)", "estimado")

    # 4. Margen bruto: AR(1) (Ornstein-Uhlenbeck discreto) 2009-2025.
    gm = h.gm.loc[2009:2025]
    b, _, r = _ols(np.c_[np.ones(len(gm) - 1), gm.values[:-1]], gm.values[1:])
    phi_gm = float(b[1]); mu_gm = float(b[0] / (1 - b[1])); sd_gm = float(r.std(ddof=2))
    P["gm_mean"] = Param(mu_gm, sd_gm / (1 - phi_gm) / np.sqrt(len(gm)),
                         f"Media de largo plazo del AR(1) del margen bruto ({len(gm)} años)", "estimado")
    P["gm_phi"] = Param(phi_gm, 0.0, "Persistencia AR(1) del margen bruto", "estimado")
    P["gm_sd"] = Param(sd_gm, 0.0, "σ del shock anual del margen bruto", "estimado")

    # 5. Gastos operativos pre-IFRS 16: modelo de corrección de error.
    #    Δln(ratio) = -(1-β)·(Δln ventas - tendencia) + γ·(ln ratio_{t-1} - ln ratio_medio) + ε
    ratio = h.opex_ratio.dropna()
    r_bar = ratio.drop(2021).mean()
    obs = [y for y in ratio.index if y - 1 in ratio.index]
    trend = lambda y: bg[0] + bg[1] * (y - 2025)
    dlr = np.array([np.log(ratio[y] / ratio[y - 1]) for y in obs])
    surprise = np.array([np.log(1 + h.growth[y]) - np.log(1 + trend(y)) for y in obs])
    gap = np.array([np.log(ratio[y - 1] / r_bar) for y in obs])
    be, se_e, re = _ols(np.c_[surprise, gap], dlr)
    beta_sr = 1 + be[0]
    P["opex_beta"] = Param(float(np.clip(beta_sr, 0.0, 1.0)), float(se_e[0]),
                           f"Elasticidad a corto plazo de los gastos a una sorpresa de ventas (MCE, {len(obs)} obs.)",
                           "estimado")
    P["opex_gamma"] = Param(float(np.clip(be[1], -1.0, 0.0)), float(se_e[1]),
                            "Velocidad de vuelta del ratio de gastos a su media (MCE)", "estimado")
    P["opex_sd"] = Param(float(re.std(ddof=2)), 0.0, "σ del shock anual del ratio de gastos (MCE)", "estimado")
    recent = ratio.loc[2022:2025].mean()
    P["opex_ratio_mean"] = Param(float(recent), float(ratio.drop(2021).std()),
                                 f"Ratio gastos/ventas pre-IFRS 16 medio 2022-25 (histórico 2009-25: {r_bar:.2%})",
                                 "estimado")

    # 6. Alquileres fijos: crecen con la superficie más la indexación.
    P["rent_index"] = Param(0.02, 0.005, "Indexación de rentas ≈ IPC zona euro objetivo BCE", "criterio")

    # 7. Capex ordinario / ventas (sin el plan logístico extraordinario de 2024-25) y guía de Inditex para 2026.
    P["capex_2026"] = Param(GUIDANCE_2026["capex"], 0.0, "Guía de Inditex: inversiones ordinarias ≈ 2.300 M€ en 2026 "
                                                         "(Informe anual 2025, Perspectivas)", "guía")
    P["fx_2026"] = Param(GUIDANCE_2026["fx"], 0.0, "Guía de Inditex: impacto divisa ≈ -1 % en ventas en 2026", "guía")
    rev_2026 = FY25["revenue"] * (1 + P["org_mean"].value) * (1 + GUIDANCE_2026["fx"])
    capex_ord = pd.Series({2022: 1415, 2023: 1872, 2024: 1772, 2025: 1812}) / h.net_sales_eur_m.loc[2022:2025]
    capex_ord.loc[2026] = GUIDANCE_2026["capex"] / rev_2026
    P["capex_mean"] = Param(float(capex_ord.mean()), float(capex_ord.std() / np.sqrt(len(capex_ord))),
                            "Capex ordinario / ventas 2022-25 más la guía de 2026 (sin el plan logístico de 900 M€/año)",
                            "estimado")
    P["capex_sd"] = Param(float(capex_ord.std()), 0.0, "σ anual del capex / ventas", "estimado")

    # 8. Circulante: existencias, clientes y proveedores sobre ventas (2023-25).
    wc = pd.DataFrame({"inv": [2966, 3321, 3249], "rec": [1038, 1088, 1166], "pay": [-7467, -8590, -8587]},
                      index=[2023, 2024, 2025]).div(h.net_sales_eur_m.loc[2023:2025], axis=0)
    for k, name in [("inv", "existencias"), ("rec", "clientes"), ("pay", "proveedores")]:
        P[f"{k}_mean"] = Param(float(wc[k].mean()), float(wc[k].std()), f"{name.capitalize()} / ventas, media 2023-25",
                               "estimado")

    # 9. Crisis tipo COVID: 1 evento en 25 años desde la salida a bolsa (2001-2025), prior de Jeffreys.
    P["crisis_a"] = Param(1.5, 0.0, "Beta(1+½, 24+½): 1 crisis en 25 años, prior de Jeffreys", "estimado")
    P["crisis_b"] = Param(24.5, 0.0, "Ídem", "estimado")
    P["crisis_size"] = Param(-0.25, 0.05, "Caída de ventas a tc constante en el año de la crisis (FY2020: -28 % "
                                          "reportado)", "estimado")
    P["crisis_rebound"] = Param(0.90, 0.05, "Fracción de la caída recuperada al año siguiente (FY2021: +36 %)",
                                "estimado")

    # 10. Correlaciones entre shocks, encogidas a la mitad hacia cero por el tamaño muestral.
    gm_res = pd.Series(r, index=gm.index[1:])
    gc_res = pd.Series(resid, index=gc.index)
    fxs = fx - fx.mean()
    re_s = pd.Series(re, index=obs)

    def rho(a: pd.Series, b: pd.Series) -> float:
        j = a.index.intersection(b.index)
        return float(np.corrcoef(a[j], b[j])[0, 1]) if len(j) >= 6 else 0.0

    raw = np.eye(4)
    pairs_idx = {(0, 1): (gc_res, gm_res), (0, 2): (gc_res, re_s), (0, 3): (gc_res, fxs),
                 (1, 2): (gm_res, re_s), (1, 3): (gm_res, fxs), (2, 3): (re_s, fxs)}
    for (i, j), (a, b_) in pairs_idx.items():
        raw[i, j] = raw[j, i] = rho(a, b_)
    corr = 0.5 * raw + 0.5 * np.eye(4)
    w, v = np.linalg.eigh(corr)
    corr = v @ np.diag(np.clip(w, 1e-6, None)) @ v.T
    d = np.sqrt(np.diag(corr)); corr = corr / np.outer(d, d)

    return Calibration(params=P, corr=corr, history=h,
                       opex_regression=dict(coef=be, se=se_e, n=len(obs), r_bar=r_bar, years=obs))
