"""Gráficos para la presentación (PNG, fondo claro).

Paleta de referencia validada (orden fijo de series), líneas de 2 px, rejilla fina
y discreta, un solo eje Y por panel y etiquetas directas selectivas.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

FIG_DIR = Path(__file__).resolve().parents[1] / "figures"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # azul, naranja, aqua, amarillo
BLUE_RAMP = {150: "#b7d3f6", 250: "#86b6ef", 450: "#2a78d6", 600: "#184f95"}
CRITICAL = "#d03b3b"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 11, "axes.edgecolor": AXIS, "axes.linewidth": 1, "axes.labelcolor": INK_2,
    "axes.titlesize": 14, "axes.titleweight": "semibold", "axes.titlecolor": INK, "axes.titlelocation": "left",
    "axes.titlepad": 30, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "axes.axisbelow": True, "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK_2, "ytick.labelcolor": INK_2,
    "lines.linewidth": 2, "lines.solid_capstyle": "round", "legend.frameon": False,
    "legend.labelcolor": INK_2, "figure.dpi": 110, "savefig.dpi": 200,
})

pct0 = FuncFormatter(lambda v, _: f"{v*100:.0f}%".replace("-", "−"))
thousands = FuncFormatter(lambda v, _: f"{v/1000:,.0f}K".replace(",", "."))


def _subtitle(ax, text: str) -> None:
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK_2, fontsize=10.5, va="bottom")


def _save(fig, name: str) -> Path:
    FIG_DIR.mkdir(exist_ok=True)
    path = FIG_DIR / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _fan(ax, years, q: pd.DataFrame, label: str, color: str = SERIES[0]) -> None:
    ax.fill_between(years, q["P5"], q["P95"], color=color, alpha=0.10, lw=0, label=f"{label}: P5–P95")
    ax.fill_between(years, q["P25"], q["P75"], color=color, alpha=0.22, lw=0, label=f"{label}: P25–P75")
    ax.plot(years, q["P50"], color=color, label=f"{label}: mediana")


def opex_ratio(history: pd.DataFrame, sim: pd.DataFrame, excel_path: np.ndarray) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5.4))
    hist = history.opex_ratio.dropna()
    normal = hist.drop(2021, errors="ignore")
    lo, hi = normal.min(), normal.max()
    ax.axhspan(lo, hi, color=MUTED, alpha=0.12, lw=0)
    ax.text(2009.2, hi + 0.0008, f"Rango histórico {lo:.1%}–{hi:.1%}".replace(".", ","), color=INK_2, fontsize=10)
    seg1 = hist.loc[:2018]
    ax.plot(seg1.index, seg1.values, color=INK, marker="o", ms=4, mec=SURFACE, mew=1.5, label="Histórico")
    seg2 = hist.loc[2021:]
    ax.plot(seg2.index, seg2.values, color=INK, marker="o", ms=4, mec=SURFACE, mew=1.5)
    ax.annotate("2021: COVID", (2021, hist[2021]), xytext=(2019.2, hist[2021] + 0.002), color=INK_2, fontsize=9.5,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    years = sim.index.values
    _fan(ax, np.r_[2025, years], pd.concat([pd.DataFrame({c: [hist[2025]] for c in sim.columns}, index=[2025]), sim]),
         "Simulación")
    ax.plot(np.r_[2025, years], np.r_[hist[2025], excel_path], color=SERIES[1], label="Caso base del Excel del grupo")
    ax.text(years[-1] + 0.15, excel_path[-1], f"{excel_path[-1]:.1%}".replace(".", ","), color=INK, va="center", fontsize=10)
    ax.text(years[-1] + 0.15, sim["P50"].iloc[-1], f"{sim['P50'].iloc[-1]:.1%}".replace(".", ","), color=INK, va="center",
            fontsize=10)
    ax.yaxis.set_major_formatter(pct0)
    ax.set_xlim(2008.5, 2031.2)
    ax.set_ylim(0.315, 0.38)
    ax.set_title("El caso base del grupo exige unos gastos que Inditex nunca ha tenido")
    _subtitle(ax, "Gastos operativos pre-IFRS 16 (incluidos alquileres) sobre ventas, 2009–2030")
    ax.legend(loc="lower left", ncol=2, fontsize=9.5)
    return _save(fig, "fig1_ratio_gastos.png")


def fx_drag(history: pd.DataFrame) -> Path:
    h = history.dropna(subset=["growth_constant_fx_pct"])
    years = h.index.values
    x = np.arange(len(years))
    w = 0.36
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(x - w / 2 - 0.02, h.growth_constant_fx_pct / 100, w, color=SERIES[0], label="A tipo de cambio constante")
    ax.bar(x + w / 2 + 0.02, h.growth_reported_pct / 100, w, color=SERIES[1], label="Reportado en euros")
    for xi, d in zip(x, h.fx_drag):
        ax.text(xi, max(h.growth_constant_fx_pct.max(), 0) / 100 + 0.012, f"{d*100:+.1f}".replace(".", ","), ha="center",
                color=INK_2, fontsize=9)
    ax.text(-0.6, h.growth_constant_fx_pct.max() / 100 + 0.032, "Efecto divisa (pp):", color=INK_2, fontsize=9.5)
    ax.set_xticks(x, years)
    ax.yaxis.set_major_formatter(pct0)
    ax.axhline(0, color=AXIS, lw=1)
    ax.set_ylim(0, h.growth_constant_fx_pct.max() / 100 + 0.09)
    ax.set_title(f"La divisa resta {abs(h.fx_drag.mean())*100:.1f} pp de crecimiento al año de media".replace(".", ","))
    _subtitle(ax, f"Crecimiento de ventas de Inditex: {int((h.fx_drag < 0).sum())} de {len(h)} años con efecto "
                  "divisa negativo. El Excel del grupo supone cero")
    ax.legend(loc="upper right", fontsize=9.5)
    return _save(fig, "fig2_efecto_divisa.png")


def ebitda_fan(history: pd.DataFrame, sim: pd.DataFrame, excel_path: np.ndarray, cases: dict[str, np.ndarray]) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5.4))
    hist = history.ebitda_pre_ifrs16_eur_m.loc[2021:]
    ax.plot(hist.index, hist.values, color=INK, marker="o", ms=4, mec=SURFACE, mew=1.5, label="Histórico")
    years = sim.index.values
    joined = pd.concat([pd.DataFrame({c: [hist[2025]] for c in sim.columns}, index=[2025]), sim])
    _fan(ax, np.r_[2025, years], joined, "Simulación")
    ax.plot(np.r_[2025, years], np.r_[hist[2025], excel_path], color=SERIES[1], label="Caso base del Excel del grupo")
    ax.plot(np.r_[2025, years], np.r_[hist[2025], cases["Bank case"]], color=SERIES[2], label="Bank case (P10)")
    for y, label in [(excel_path[-1], f"Excel {excel_path[-1]/1000:,.1f}K"),
                     (sim["P50"].iloc[-1], f"Mediana {sim['P50'].iloc[-1]/1000:,.1f}K"),
                     (cases["Bank case"][-1], f"Bank case {cases['Bank case'][-1]/1000:,.1f}K")]:
        ax.text(years[-1] + 0.12, y, label.replace(".", ","), color=INK, va="center", fontsize=10)
    ax.yaxis.set_major_formatter(thousands)
    ax.set_xlim(2020.7, 2031.6)
    ax.set_title("El EBITDA de 2030 del Excel está en el percentil "
                 f"{(sim.attrs.get('excel_percentile', np.nan)):.0f} de la simulación")
    _subtitle(ax, "EBITDA pre-IFRS 16 de Inditex, €m. 20.000 caminos simulados con parámetros calibrados")
    ax.legend(loc="upper left", fontsize=9.5)
    return _save(fig, "fig3_ebitda_simulado.png")


def irr_histogram(irr: np.ndarray, excel_irr: float, hurdle: float = 0.15) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    bins = np.arange(-0.15, 0.20, 0.005)
    ax.hist(np.clip(irr, bins[0], bins[-1]), bins=bins, color=SERIES[0], rwidth=0.82)
    med = np.median(irr)
    ymax = ax.get_ylim()[1] * 1.12
    ax.set_ylim(0, ymax)
    for (x, label, color), level in zip([(med, f"Mediana {med:.1%}", INK),
                                         (excel_irr, f"Excel del grupo {excel_irr:.1%}", SERIES[1]),
                                         (hurdle, f"Objetivo típico de un fondo {hurdle:.0%}", MUTED)],
                                        (0.97, 0.88, 0.79)):
        ax.axvline(x, color=color, lw=2)
        ax.text(x + 0.002, ymax * level, label.replace(".", ","), color=INK, fontsize=10, va="top")
    ax.text(bins[0], -ymax * 0.075, "≤ −15%", color=INK_2, fontsize=9, ha="center", va="top")
    ax.xaxis.set_major_formatter(pct0)
    ax.set_ylabel("Nº de caminos")
    p_neg, p_hurdle = (irr < 0).mean(), (irr >= hurdle).mean()
    ax.set_title("Con un business plan realista, la TIR del sponsor ronda el 5%")
    _subtitle(ax, f"TIR del sponsor (prima 20%, deuda 7,0x, salida en 2030). P(TIR < 0) = {p_neg:.0%}; "
                  f"P(TIR ≥ {hurdle:.0%}) = {p_hurdle:.1%}".replace(".", ","))
    return _save(fig, "fig4_distribucion_tir.png")


def leverage_frontier(fr: pd.DataFrame, chosen: float = 7.0) -> Path:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8), sharex=True)
    L = fr.index.values
    for ax in (a1, a2):
        for lo, hi, name in [(0, 4.5, "Senior"), (4.5, 6.0, "PIK"), (6.0, 10.0, "Vendor loan y más")]:
            ax.axvspan(lo, hi, color=MUTED, alpha=0.06 if name != "PIK" else 0.13, lw=0)
            ax.text((lo + hi) / 2, 1.0, name, transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                    color=INK_2, fontsize=9.5)
        ax.axvline(chosen, color=MUTED, lw=1)
    a1.fill_between(L, fr["TIR P10"], fr["TIR P90"], color=SERIES[0], alpha=0.12, lw=0, label="P10–P90")
    a1.plot(L, fr["TIR mediana"], color=SERIES[0], label="Mediana")
    a1.yaxis.set_major_formatter(pct0)
    a1.set_xlabel("Deuda total / EBITDA pre-IFRS 16")
    a1.set_title("Más deuda no sube la TIR…", pad=26)
    a1.legend(loc="lower left", fontsize=9.5)
    a2.plot(L, fr["P(DSCR mínimo < 1,2x)"], color=SERIES[1], label="P(DSCR mínimo < 1,2x)")
    a2.plot(L, fr["P(TIR < 0)"], color=SERIES[0], label="P(TIR < 0)")
    a2.yaxis.set_major_formatter(pct0)
    a2.set_ylim(0, 1)
    a2.set_xlabel("Deuda total / EBITDA pre-IFRS 16")
    a2.set_title("…pero sí el riesgo", pad=26)
    a2.legend(loc="center right", fontsize=9.5)
    a1.text(chosen + 0.1, 0.02, "7,0x del grupo", transform=a1.get_xaxis_transform(), color=INK_2, fontsize=9)
    fig.tight_layout()
    return _save(fig, "fig5_frontera_apalancamiento.png")


def senior_capacity(table: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.6))
    x = np.arange(len(table))
    w = 0.34
    cols = list(table.columns)
    for i, (col, color) in enumerate(zip(cols, SERIES)):
        bars = ax.bar(x + (i - 0.5) * (w + 0.03), table[col], w, color=color, label=col)
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.12, f"{b.get_height():.1f}x".replace(".", ","),
                    ha="center", color=INK, fontsize=10)
    ax.set_xticks(x, table.index)
    ax.set_ylabel("Deuda senior máxima (x EBITDA)")
    ax.set_ylim(0, table.values.max() * 1.18)
    ax.set_title("Menos TLA y más TLB: misma TIR, más capacidad de deuda")
    _subtitle(ax, "Deuda senior máxima con P(DSCR mínimo < 1,2x) ≤ 5%, según el peso de la TLA amortizable")
    ax.legend(loc="upper left", fontsize=9.5)
    return _save(fig, "fig6_capacidad_senior.png")


def shapley(phi: pd.Series, r2: float) -> Path:
    s = phi.sort_values()
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.barh(s.index, s.values, height=0.55, color=SERIES[0])
    for y, v in enumerate(s.values):
        ax.text(v + 0.004, y, f"{v:.0%}", va="center", color=INK, fontsize=10)
    ax.xaxis.set_major_formatter(pct0)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, s.max() * 1.15)
    ax.set_title("El crecimiento orgánico explica el 40% del riesgo de la TIR")
    _subtitle(ax, f"Reparto de Shapley de la varianza de la TIR del sponsor (R² del modelo = {r2:.0%})")
    return _save(fig, "fig7_shapley_tir.png")


def premium_exit_heatmap(grid: pd.DataFrame) -> Path:
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm, to_rgb

    fig, ax = plt.subplots(figsize=(10, 5))
    data = grid.values
    # Divergente: rojo = TIR negativa, gris neutro = 0, azul = positiva.
    cmap = LinearSegmentedColormap.from_list("div", ["#a32b2b", "#e34948", "#f0efec", "#3987e5", "#104281"])
    span = max(abs(data.min()), abs(data.max()))
    norm = TwoSlopeNorm(vmin=-span, vcenter=0.0, vmax=span)
    ax.imshow(data, cmap=cmap, norm=norm, aspect="auto")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            r, g, b = to_rgb(cmap(norm(v)))
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            ax.text(j, i, f"{v:.1%}".replace(".", ",").replace("-", "−"), ha="center", va="center", fontsize=10,
                    color="#ffffff" if lum < 0.45 else INK)
    ax.set_xticks(range(grid.shape[1]), [f"{c:.1f}x".replace(".", ",") for c in grid.columns])
    ax.set_yticks(range(grid.shape[0]), [f"{r:.0%}" for r in grid.index])
    ax.set_xlabel("Múltiplo de salida (EV / EBITDA pre-IFRS 16 en 2030)")
    ax.set_ylabel("Prima de la OPA")
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Ni sin prima se llega al 15%: el problema es el precio de partida")
    _subtitle(ax, "TIR mediana del sponsor (deuda 7,0x) según la prima pagada y el múltiplo de salida. "
                  "17,1x = mercado hoy; 20,8x = entrada con prima del 20%")
    return _save(fig, "fig8_prima_vs_salida.png")


def cases(case_ebitda: dict[str, np.ndarray], excel_path: np.ndarray, hist_2025: float) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5.2))
    years = np.arange(2025, 2031)
    order = ["Bull", "Base", "Bear", "Bank case"]
    for name, color in zip(order, SERIES):
        y = np.r_[hist_2025, case_ebitda[name]]
        ax.plot(years, y, color=color, label=name)
        ax.text(2030.12, y[-1], f"{name} {y[-1]/1000:,.1f}K".replace(".", ","), color=INK, va="center", fontsize=10)
    ax.plot(years, np.r_[hist_2025, excel_path], color=MUTED, label="Excel del grupo (base)")
    ax.text(2030.12, excel_path[-1], f"Excel {excel_path[-1]/1000:,.1f}K".replace(".", ","), color=INK_2, va="center",
            fontsize=10)
    ax.yaxis.set_major_formatter(thousands)
    ax.set_xlim(2024.8, 2031.4)
    ax.set_xticks(years)
    ax.set_title("Los cuatro casos salen de la simulación, no de la intuición")
    _subtitle(ax, "EBITDA pre-IFRS 16, €m. Bull = P80, Base = P50, Bear = P20, Bank case = P10 del EBITDA 2030")
    ax.legend(loc="upper left", fontsize=9.5)
    return _save(fig, "fig9_casos.png")


def plan_bands(table: pd.DataFrame, hurdle: float = 0.15) -> Path:
    cols = list(table.columns)
    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = np.arange(len(cols))
    med, p10, p90 = (table.loc[k].values.astype(float) for k in ("TIR mediana", "TIR P10", "TIR P90"))
    colors = [MUTED] + [SERIES[0]] * (len(cols) - 1)
    ax.bar(x, med, width=0.5, color=colors)
    ax.vlines(x, p10, p90, color=INK_2, lw=1.5)
    for xi, m, hi in zip(x, med, p90):
        ax.text(xi, hi + 0.006, f"{m:.1%}".replace(".", ","), ha="center", color=INK, fontsize=10.5, fontweight="bold")
    ax.axhline(hurdle, color=CRITICAL, lw=1.5)
    ax.text(-0.45, hurdle + 0.004, f"Objetivo típico de un fondo {hurdle:.0%}", ha="left", color=INK_2, fontsize=9.5)
    ax.axhline(0, color=AXIS, lw=1)
    ax.set_xticks(x, [c.replace("Todas en ", "Todas en\n") for c in cols])
    from matplotlib.ticker import MultipleLocator
    ax.yaxis.set_major_locator(MultipleLocator(0.05))
    ax.yaxis.set_major_formatter(pct0)
    ax.set_title("Hasta con todas las palancas en «Optimista» la TIR se queda en el 8%")
    _subtitle(ax, "TIR del sponsor con el plan de creación de valor (barra = mediana, línea = P10–P90; con riesgo de "
                  "ejecución y crisis)")
    return _save(fig, "fig10_plan_por_bandas.png")


def plan_waterfall(shapley: pd.Series) -> Path:
    s = shapley[shapley.abs() > 1e-5].sort_values(ascending=False)
    base, plan = shapley.attrs["base"], shapley.attrs["plan"]
    from .levers import LEVERS, SHORT_NAME
    short = {lv.name: SHORT_NAME[lv.key] for lv in LEVERS}
    labels = ["Sin plan"] + [short.get(k, k) for k in s.index] + ["Con el plan"]
    fig, ax = plt.subplots(figsize=(11, 5))
    level = base
    for i, (name, v) in enumerate(s.items(), start=1):
        ax.bar(i, v, bottom=level, width=0.55, color=SERIES[0] if v >= 0 else CRITICAL)
        ax.text(i, level + max(v, 0) + 0.0006, f"{v*100:+.2f} pp".replace(".", ","), ha="center", color=INK,
                fontsize=9.5)
        level += v
    for xi, v, color in [(0, base, MUTED), (len(labels) - 1, plan, INK)]:  # totales como niveles, no como barras
        ax.hlines(v, xi - 0.3, xi + 0.3, color=color, lw=4)
        ax.text(xi, v + 0.0006, f"{v:.1%}".replace(".", ","), ha="center", color=INK, fontsize=10.5, fontweight="bold")
    ax.set_xticks(range(len(labels)), labels, fontsize=9.5)
    from matplotlib.ticker import MaxNLocator
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, steps=[1, 2, 5]))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v*100:.1f}%".replace(".", ",")))
    ax.set_ylim(min(base, plan) * 0.92, max(base, plan) * 1.06)
    ax.set_title("Lo que aporta cada palanca a la TIR mediana")
    _subtitle(ax, "Reparto de Shapley de la mejora de la TIR mediana del sponsor (palancas en sus valores del panel)")
    return _save(fig, "fig11_plan_cascada.png")


def plan_distribution(irr_base: np.ndarray, irr_plan: np.ndarray, label_plan: str = "Con el plan") -> Path:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    bins = np.arange(-0.15, 0.30, 0.005)
    for irr, label, color in [(irr_base, "Sin plan", MUTED), (irr_plan, label_plan, SERIES[0])]:
        h, e = np.histogram(np.clip(irr, bins[0], bins[-1]), bins=bins)
        ax.plot((e[:-1] + e[1:]) / 2, h, color=color, label=f"{label} (mediana {np.median(irr):.1%})".replace(".", ","))
        ax.fill_between((e[:-1] + e[1:]) / 2, h, color=color, alpha=0.10, lw=0)
    ax.axvline(0.15, color=CRITICAL, lw=1.5)
    ax.text(0.152, ax.get_ylim()[1] * 0.95, "15%", color=INK_2, fontsize=9.5, va="top")
    ax.text(bins[0], -ax.get_ylim()[1] * 0.075, "≤ −15%", color=INK_2, fontsize=9, ha="center", va="top")
    ax.xaxis.set_major_formatter(pct0)
    ax.set_ylabel("Nº de caminos")
    ax.set_title("El plan desplaza la distribución, pero no la cola")
    _subtitle(ax, "TIR del sponsor en 20.000 caminos, sin plan y con el plan de creación de valor")
    ax.legend(loc="upper left", fontsize=9.5)
    return _save(fig, "fig12_plan_distribucion.png")
