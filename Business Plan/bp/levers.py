"""Plan de creación de valor: palancas que se suman al business plan standalone.

Cada palanca produce, año a año, ventas, EBITDA, capex, alquileres y circulante
incrementales. La misma aritmética está en la hoja Palancas del Excel integrado, así
que cambiar un input en Excel y en Python da exactamente el mismo resultado.

Cada parámetro trae cuatro bandas (Conservador, Normal, Optimista, Agresivo) con el
dato de las cuentas que las ancla. En los costes la dirección se invierte: un capex
por m² bajo es la hipótesis agresiva.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from .lbo import Deal, Operating

T = 5
RAMP_REV = np.array([0.60, 0.85, 1.0, 1.0, 1.0])  # ventas de una tienda nueva según su antigüedad
RAMP_MARGIN = np.array([0.50, 0.80, 1.0, 1.0, 1.0])  # margen de una tienda nueva según su antigüedad
COHORT_DECAY = 0.03  # cada añada de aperturas vende un 3 % menos que la anterior (peores ubicaciones)
GROUP_MARGIN = 9433 / 39864  # margen EBITDA pre-IFRS 16 FY2025, el que se pierde por canibalización
LEASE_SHARE = 1834 / 39864  # alquileres fijos / ventas FY2025
BASE_DENSITY = 39864e6 / 4720703  # ventas por m² del grupo FY2025 (€/m², online incluido)
LAND_BUILDINGS_NBV = 3063 - 659  # terrenos y construcciones, valor neto contable a 31-01-2026 (€m)
WC_PHASE = np.array([0.5, 1.0, 1.0, 1.0, 1.0])
BANDS = ("Conservador", "Normal", "Optimista", "Agresivo")


def _cohort_factors() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Suma sobre añadas de aperturas: F (ventas), G (ventas × margen) y H (ventas sin pérdida por añada)."""
    F, G, H = np.zeros(T), np.zeros(T), np.zeros(T)
    for t in range(T):
        for k in range(t + 1):
            age = t - k
            F[t] += (1 - COHORT_DECAY) ** k * RAMP_REV[age]
            G[t] += (1 - COHORT_DECAY) ** k * RAMP_REV[age] * RAMP_MARGIN[age]
            H[t] += RAMP_REV[age]
    return F, G, H


F_COHORT, G_COHORT, H_COHORT = _cohort_factors()


@dataclass(frozen=True)
class LeverParam:
    key: str
    label: str
    unit: str
    edges: tuple | None  # (b0, b1, b2, b3, b4); None = sin barómetro
    default: float
    reverse: bool = False  # True: valores bajos son la hipótesis agresiva (costes, canibalización...)
    anchor: str = ""
    fmt: str = "0"

    def band(self, v: float) -> str:
        if self.edges is None:
            return ""
        b0, b1, b2, b3, b4 = self.edges
        order = BANDS if not self.reverse else BANDS[::-1]
        idx = 0 if v < b1 else 1 if v < b2 else 2 if v < b3 else 3
        return order[idx]

    def band_range(self, name: str) -> tuple[float, float]:
        order = BANDS if not self.reverse else BANDS[::-1]
        i = order.index(name)
        return self.edges[i], self.edges[i + 1]


@dataclass(frozen=True)
class Lever:
    key: str
    name: str
    what: str
    params: tuple
    execution: tuple = (1.0, 1.0, 1.0)  # (mín, moda, máx) del multiplicador de ejecución en la simulación
    kind: str = "operativa"


def _expansion(key: str, name: str, what: str, m2, density, margin, capex, cannib, execution) -> Lever:
    """Programa de aperturas; cada spec es (bandas, valor por defecto, dato que las ancla)."""
    p = lambda k, label, unit, spec, **kw: LeverParam(k, label, unit, edges=spec[0], default=spec[1], anchor=spec[2],
                                                      **kw)
    return Lever(key, name, what, (
        p("m2", "Superficie nueva al año", "miles m²", m2, fmt="0"),
        p("density", "Ventas por m² de una tienda madura", "€/m²", density, fmt="#,##0"),
        p("margin", "Margen EBITDA pre-IFRS 16 de la tienda madura", "%", margin, fmt="0.0%"),
        p("capex", "Capex por m² abierto", "€/m²", capex, reverse=True, fmt="#,##0"),
        p("cannib", "Canibalización (ventas que se quitan a otras tiendas y al online)", "%", cannib, reverse=True,
          fmt="0%"),
    ), execution=execution)


LEVERS: tuple[Lever, ...] = (
    _expansion(
        "usa", "Expansión en EE. UU.",
        "Abrir superficie de Zara, Bershka y Massimo Dutti en EE. UU. por encima del plan de Inditex.",
        ((0, 10, 25, 45, 80), 20, "Inditex prevé ≈ 5 % de espacio bruto en 2026 (≈ 236.000 m² en todo el mundo)"),
        ((5000, 6500, 8500, 10000, 13000), 7500, "Grupo 8.445 €/m²; Zara 8.819 €/m² (FY2025, online incluido)"),
        ((0.08, 0.14, 0.20, 0.24, 0.30), 0.17, "Grupo 23,7 %. EE. UU. ganó 396 M€ antes de impuestos, -5 % en 2025"),
        ((2000, 3500, 5000, 7000, 9000), 6000, "Capex ordinario 2025 / m² brutos abiertos ≈ 7.400 €/m² (con IT)"),
        ((0.0, 0.05, 0.10, 0.25, 0.40), 0.15, "Online = 27 % de las ventas: una tienda nueva le quita clientes"),
        (0.5, 1.0, 1.1)),
    _expansion(
        "young", "Marcas jóvenes (Stradivarius, Oysho, Bershka)",
        "Acelerar aperturas de las marcas con mayor ROCE y crecimiento en mercados donde ya están.",
        ((0, 15, 35, 60, 100), 25, "Las tres marcas suman 918.000 m²; crecer un 3-4 % son 30-35.000 m²"),
        ((5500, 6800, 8500, 10000, 12000), 7900, "Media ponderada FY2025: Bershka 6.656, Stradivarius 9.149, "
                                                 "Oysho 10.009 €/m²"),
        ((0.15, 0.22, 0.27, 0.31, 0.36), 0.24, "ROCE FY2025: Stradivarius 72 %, Oysho 63 %, Bershka 50 % (grupo 40 %)"),
        ((1500, 2500, 3500, 5000, 6500), 4200, "Tiendas más pequeñas y baratas de montar que un flagship de Zara"),
        ((0.0, 0.05, 0.15, 0.30, 0.45), 0.20, "Mismos mercados y clientela parecida a Zara y Pull&Bear"),
        (0.5, 1.0, 1.1)),
    _expansion(
        "lefties", "Lefties frente a Shein y Temu",
        "Formato de precio bajo para defender cuota frente a la moda ultrarrápida online.",
        ((0, 5, 20, 40, 70), 10, "215 tiendas Lefties a cierre de 2025 (209 en 2024)"),
        ((3000, 4000, 5500, 7000, 8500), 4800, "Precio medio muy inferior a Zara: densidad por debajo del grupo"),
        ((0.06, 0.12, 0.17, 0.21, 0.25), 0.14, "Margen bruto menor que el grupo (precio bajo)"),
        ((1000, 1800, 2500, 3500, 4500), 3000, "Tiendas de formato sencillo"),
        ((0.0, 0.10, 0.25, 0.40, 0.60), 0.30, "Riesgo alto de quitar ventas a Zara y Bershka"),
        (0.4, 1.0, 1.15)),
    Lever("refurb", "Optimización de tiendas adicional",
          "Más reformas y ampliaciones que las ya previstas (las actuales ya están en el plan base).", (
              LeverParam("m2", "Superficie reformada o ampliada adicional al año", "miles m²",
                         (0, 20, 60, 120, 200), 40, anchor="2025: 217 reformas (96 ampliaciones) y 293 absorciones"),
              LeverParam("uplift", "Aumento de ventas por m² en lo reformado", "%", (0.03, 0.08, 0.15, 0.25, 0.40),
                         0.12, anchor="3 últimos años: tiendas -6 %, superficie +6 %, ventas +22 %", fmt="0%"),
              LeverParam("capex", "Capex por m² reformado", "€/m²", (500, 1000, 1500, 2500, 3500), 2000,
                         reverse=True, anchor="Reforma: una fracción del coste de abrir", fmt="#,##0"),
              LeverParam("margin", "Margen sobre las ventas incrementales", "%", (0.15, 0.25, 0.35, 0.45, 0.55), 0.30,
                         anchor="La tienda ya existe: alquiler y plantilla casi fijos", fmt="0%"),
          ), execution=(0.6, 1.0, 1.1)),
    Lever("efficiency", "Eficiencia operativa",
          "Rentabilizar el plan logístico de 1.800 M€ (2024-25), RFID y automatización de tienda.", (
              LeverParam("bps", "Ahorro de gastos a régimen", "pb de ventas", (0, 25, 60, 100, 200), 40,
                         anchor="Gastos/ventas: mínimo histórico 34,6 %; más de 60 pb es terreno nunca visto"),
              LeverParam("years", "Años hasta alcanzar el ahorro completo", "años", (1, 2, 3, 4, 5), 3, reverse=True,
                         anchor="Los planes de eficiencia suelen tardar 2-4 años"),
              LeverParam("one_off", "Coste de implantación", "× ahorro anual", (0.0, 0.4, 0.75, 1.5, 2.5), 1.0,
                         reverse=True, anchor="Se paga en 2026-27 (consultoría, despidos, sistemas)", fmt="0.00"),
          ), execution=(0.4, 1.0, 1.1)),
    Lever("wc", "Circulante",
          "Alargar el pago a proveedores y reducir stock (RFID, mejor reposición).", (
              LeverParam("pay", "Más proveedores sobre ventas", "pp", (0.0, 0.5, 1.5, 2.5, 4.0), 1.0,
                         anchor="Proveedores / ventas: 20,1 % (2022) a 22,2 % (2024); 21,5 % en 2025", fmt="0.0"),
              LeverParam("inv", "Menos existencias sobre ventas", "pp", (0.0, 0.2, 0.6, 1.0, 1.8), 0.4,
                         anchor="Existencias / ventas: 8,2 % en 2025 (9,8 % en 2022)", fmt="0.0"),
          ), execution=(0.7, 1.0, 1.05)),
    Lever("propco", "Venta y realquiler de inmuebles (PropCo)",
          "Vender terrenos y edificios propios y realquilarlos: caja hoy a cambio de alquiler para siempre.", (
              LeverParam("share", "Parte de terrenos y construcciones vendida", "%", (0.0, 0.2, 0.5, 0.8, 1.0), 0.35,
                         anchor="Valor neto contable a 31-01-2026: 2.404 M€", fmt="0%"),
              LeverParam("multiple", "Valor de mercado / valor contable", "x", (1.0, 1.3, 1.8, 2.5, 3.5), 1.5,
                         anchor="El suelo está a coste histórico: el valor de mercado suele ser mayor", fmt="0.0"),
              LeverParam("caprate", "Rentabilidad que exige el comprador (cap rate)", "%",
                         (0.035, 0.045, 0.0525, 0.065, 0.08), 0.0575, reverse=True,
                         anchor="Logística y retail prime en Europa ≈ 4,5-6,5 %", fmt="0.00%"),
          ), kind="financiera"),
    Lever("recap", "Dividendo financiado con deuda (recap)",
          "Volver a endeudar la senior para pagar un dividendo al fondo antes de la salida.", (
              LeverParam("target", "Deuda senior neta objetivo tras el recap", "x EBITDA", (0.0, 2.0, 3.0, 3.75, 4.5),
                         2.5, anchor="Al cierre la senior es 4,5x; en el caso base baja a ≈ 2,5x en 2027", fmt="0.00"),
              LeverParam("year", "Año del recap", "año", None, 2028, anchor="2027, 2028 o 2029", fmt="0"),
          ), kind="financiera"),
)
LEVER_BY_KEY = {lv.key: lv for lv in LEVERS}
SHORT_NAME = {"usa": "EE. UU.", "young": "Marcas\njóvenes", "lefties": "Lefties", "refurb": "Reformas",
              "efficiency": "Eficiencia", "wc": "Circulante", "propco": "PropCo", "recap": "Recap"}


def default_values() -> dict[str, dict[str, float]]:
    return {lv.key: {p.key: p.default for p in lv.params} for lv in LEVERS}


def band_values(band: str) -> dict[str, dict[str, float]]:
    """Punto medio de la banda pedida en cada parámetro (p. ej. «todo Optimista»)."""
    out = default_values()
    for lv in LEVERS:
        for p in lv.params:
            if p.edges is not None:
                lo, hi = p.band_range(band)
                out[lv.key][p.key] = (lo + hi) / 2
    return out


@dataclass
class LeverResult:
    op: Operating
    deal: Deal
    d_revenue: dict = field(default_factory=dict)
    d_ebitda: dict = field(default_factory=dict)
    d_capex: dict = field(default_factory=dict)


def apply(op: Operating, deal: Deal, values: dict, on: dict | None = None, mult: dict | None = None,
          scale: np.ndarray | None = None) -> LeverResult:
    """Suma las palancas activas al business plan standalone.

    mult: multiplicador de ejecución por palanca (array (n,) en la simulación; 1 en el caso determinista).
    scale: ventas del camino / ventas medianas (n, 5); las palancas de ventas sufren las mismas crisis.
    """
    on = on or {lv.key: True for lv in LEVERS}
    n = op.revenue.shape[0]
    one = np.ones((n, 1))
    scale = np.ones((n, T)) if scale is None else scale
    m = lambda k: one if mult is None or k not in mult else np.asarray(mult[k]).reshape(n, 1)

    rev_b, gp_b = op.revenue, op.gross_profit
    d_rev, d_ebitda, d_capex = {}, {}, {}
    d_lease = np.zeros((n, T))
    d_wc_ratio = np.zeros((n, T))
    zeros = np.zeros((n, T))

    for key in ("usa", "young", "lefties"):
        if not on.get(key):
            continue
        v = values[key]
        base = v["m2"] * v["density"] / 1000 * m(key) * scale
        d_rev[key] = base * F_COHORT * (1 - v["cannib"])
        d_ebitda[key] = base * (v["margin"] * G_COHORT - v["cannib"] * GROUP_MARGIN * F_COHORT)
        d_capex[key] = np.full((n, T), v["m2"] * v["capex"] / 1000)

    if on.get("refurb"):
        v = values["refurb"]
        d_rev["refurb"] = v["m2"] * BASE_DENSITY / 1000 * v["uplift"] * H_COHORT * m("refurb") * scale
        d_ebitda["refurb"] = d_rev["refurb"] * v["margin"]
        d_capex["refurb"] = np.full((n, T), v["m2"] * v["capex"] / 1000)

    if on.get("efficiency"):
        v = values["efficiency"]
        phase = np.minimum(1.0, np.arange(1, T + 1) / v["years"])
        savings = v["bps"] / 1e4 * rev_b * phase * m("efficiency")
        one_off = np.zeros((n, T))
        one_off[:, :2] = 0.5 * v["one_off"] * v["bps"] / 1e4 * rev_b[:, :1]
        d_ebitda["efficiency"] = savings - one_off

    if on.get("wc"):
        v = values["wc"]
        d_wc_ratio -= (v["pay"] + v["inv"]) / 100 * WC_PHASE * m("wc")

    proceeds = 0.0
    if on.get("propco"):
        v = values["propco"]
        proceeds = LAND_BUILDINGS_NBV * v["share"] * v["multiple"]
        d_lease = proceeds * v["caprate"] * 1.02 ** np.arange(T) * np.ones((n, 1))
        d_ebitda["propco"] = -d_lease

    total_rev = sum(d_rev.values(), zeros)
    total_ebitda = sum(d_ebitda.values(), zeros)
    total_capex = sum(d_capex.values(), zeros)

    rev_f = rev_b + total_rev
    gp_f = gp_b + total_rev * (gp_b / rev_b)
    lease_f = op.lease + total_rev * LEASE_SHARE + d_lease
    ebitda_pre_f = op.ebitda_pre + total_ebitda
    new_op = Operating(revenue=rev_f, gross_profit=gp_f, opex_post=gp_f - ebitda_pre_f - lease_f, lease=lease_f,
                       capex=op.capex + total_capex, wc=rev_f * (op.wc / rev_b + d_wc_ratio), wc_fy25=op.wc_fy25)

    new_deal = replace(deal, propco_proceeds=proceeds)
    if on.get("recap"):
        new_deal = replace(new_deal, recap_year=int(values["recap"]["year"]), recap_target=values["recap"]["target"])
    return LeverResult(new_op, new_deal, d_rev, d_ebitda, d_capex)


def execution_multipliers(rng: np.random.Generator, n: int, on: dict | None = None) -> dict[str, np.ndarray]:
    """Riesgo de ejecución: multiplicador triangular (mín, moda, máx) por palanca y camino."""
    on = on or {lv.key: True for lv in LEVERS}
    return {lv.key: rng.triangular(*lv.execution, n) if lv.execution[0] < lv.execution[2] else np.ones(n)
            for lv in LEVERS if on.get(lv.key)}
