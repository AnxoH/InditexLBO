"""Motor LBO vectorizado que replica la hoja LBO_Rollover50 del Excel del grupo.

Cada variable operativa es un array (n_caminos, n_años), así que el mismo motor
sirve para el caso determinista del Excel (n_caminos = 1) y para las decenas de
miles de caminos de la simulación de Monte Carlo.

Referencias de filas: Excels/Inditex_LBO_Rollover50.xlsx (rama Javi), hoja
LBO_Rollover50.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

import numpy as np

YEARS = np.arange(2026, 2031)
# La TIR del Excel es un XIRR entre el cierre (31-ene-2026) y la salida (31-ene-2031): exponente 365/días.
HOLD_DAYS = (date(2031, 1, 31) - date(2026, 1, 31)).days
# Años (base 365) desde el cierre hasta cada flujo: los de cada ejercicio se fechan el 31-ene siguiente (fila 232).
FLOW_YEARS = np.array([(date(2027 + t, 1, 31) - date(2026, 1, 31)).days / 365 for t in range(len(YEARS))])


@dataclass(frozen=True)
class Deal:
    """Hipótesis de la operación (filas 163-186 del Excel)."""

    share_price: float = 55.42
    premium: float = 0.20
    shares_m: float = 3116.652
    stake: float = 1.0
    net_cash_fy25: float = 10958.0
    min_cash: float = 2000.0
    ebitda_ref: float = 9433.0
    amancio_stake: float = 0.59294
    rollover_pct: float = 0.50
    entry_fees_pct: float = 0.015
    financing_fees_pct: float = 0.0225
    exit_fees_pct: float = 0.005
    euribor: float = 0.0259
    tla_x: float = 2.25
    tlb_x: float = 2.25
    pik_x: float = 1.50
    vl_x: float = 1.00
    tla_spread: float = 0.0325
    tlb_spread: float = 0.0425
    pik_rate: float = 0.105
    vl_rate: float = 0.10
    tla_amort: tuple = (0.0, 0.10, 0.15, 0.20, 0.25)
    tlb_sweep: float = 0.75
    rcf_limit: float = 4000.0
    rcf_spread: float = 0.03
    rcf_fee: float = 0.0105
    tax_rate: float = 0.224
    interest_cap: float = 0.30
    exit_multiple: float | None = None  # None = múltiplo de entrada (convención del Excel)
    nfa_fy25: float = 12778.0
    asset_life: float = 10.0
    first_period: float = 0.5
    propco_proceeds: float = 0.0  # venta y realquiler de inmuebles: fuente adicional al cierre (fila 195)
    recap_year: int = 0  # 0 = sin dividendo financiado con deuda
    recap_target: float = 0.0  # deuda senior neta / EBITDA tras el recap

    @property
    def total_x(self) -> float:
        return self.tla_x + self.tlb_x + self.pik_x + self.vl_x

    @property
    def offer_price(self) -> float:
        return self.share_price * (1 + self.premium)

    @property
    def entry_multiple(self) -> float:
        return (self.offer_price * self.shares_m - self.net_cash_fy25) / self.ebitda_ref

    def with_leverage(self, total_x: float) -> "Deal":
        """Escala todos los tramos en proporción hasta alcanzar total_x veces EBITDA."""
        k = total_x / self.total_x
        return replace(self, tla_x=self.tla_x * k, tlb_x=self.tlb_x * k,
                       pik_x=self.pik_x * k, vl_x=self.vl_x * k)

    def with_stack(self, total_x: float, senior_cap: float = 4.5, pik_cap: float = 1.5) -> "Deal":
        """Apila la deuda por orden de prelación: senior (50/50 TLA/TLB), luego PIK, luego vendor loan."""
        senior = min(total_x, senior_cap)
        pik = min(max(total_x - senior_cap, 0.0), pik_cap)
        vl = max(total_x - senior_cap - pik_cap, 0.0)
        return replace(self, tla_x=senior / 2, tlb_x=senior / 2, pik_x=pik, vl_x=vl)


# Hipótesis exactas de la hoja LBO_Rollover50 de Javi (prima 5 %, deuda 6,0x).
JAVI_DEAL = Deal(premium=0.05, tla_x=2.0, tlb_x=2.0, pik_x=1.0, vl_x=1.0)
# Estructura acordada por el grupo: prima 20 %, deuda ≈ 7,0x (senior 4,5x + PIK 1,5x + vendor loan 1,0x).
GROUP_DEAL = Deal()


@dataclass
class Operating:
    """Variables operativas proyectadas (2026-2030), cada una de forma (n, 5), en €m."""

    revenue: np.ndarray
    gross_profit: np.ndarray
    opex_post: np.ndarray  # gastos operativos sin los alquileres fijos (positivo)
    lease: np.ndarray  # pagos fijos de arrendamiento (positivo)
    capex: np.ndarray
    wc: np.ndarray  # saldo de circulante operativo al cierre (negativo = financia a Inditex)
    wc_fy25: float = -4172.0

    @property
    def ebitda_reported(self) -> np.ndarray:
        return self.gross_profit - self.opex_post

    @property
    def ebitda_pre(self) -> np.ndarray:
        return self.ebitda_reported - self.lease

    @property
    def wc_cash_flow(self) -> np.ndarray:
        prev = np.concatenate([np.full((self.wc.shape[0], 1), self.wc_fy25), self.wc[:, :-1]], axis=1)
        return prev - self.wc


def sources_and_uses(d: Deal) -> dict:
    ebitda = d.ebitda_ref * d.stake
    tla, tlb, pik, vl = (x * ebitda for x in (d.tla_x, d.tlb_x, d.pik_x, d.vl_x))
    purchase = d.offer_price * d.shares_m * d.stake
    fin_fees = (tla + tlb + pik) * d.financing_fees_pct
    adv_fees = purchase * d.entry_fees_pct
    uses = purchase + fin_fees + adv_fees
    excess_cash = max(0.0, d.net_cash_fy25 - d.min_cash) * d.stake + d.propco_proceeds
    equity = uses - (tla + tlb + pik + vl) - excess_cash
    rollover = d.offer_price * d.shares_m * d.amancio_stake * d.rollover_pct
    sponsor = equity - rollover
    return dict(tla=tla, tlb=tlb, pik=pik, vl=vl, purchase=purchase, fin_fees=fin_fees,
                adv_fees=adv_fees, uses=uses, excess_cash=excess_cash, equity=equity,
                rollover=rollover, sponsor=sponsor, sponsor_share=sponsor / equity)


def _depreciation(capex: np.ndarray, d: Deal) -> np.ndarray:
    """D&A de los activos existentes (lineal a 10 años) más cada añada de capex (medio año el primero)."""
    n, T = capex.shape
    da = np.zeros((n, T))
    remaining_existing = d.nfa_fy25
    for t in range(T):
        da_existing = min(remaining_existing, d.nfa_fy25 / d.asset_life)
        remaining_existing -= da_existing
        da[:, t] += da_existing
    for v in range(T):
        remaining = capex[:, v].copy()
        for t in range(v, T):
            charge = capex[:, v] / d.asset_life * (d.first_period if t == v else 1.0)
            charge = np.minimum(remaining, charge)
            remaining -= charge
            da[:, t] += charge
    return da


def run(op: Operating, d: Deal) -> dict:
    """Ejecuta la cascada de deuda año a año y devuelve balances, ratios y retornos."""
    su = sources_and_uses(d)
    n, T = op.revenue.shape
    ebitda_pre = op.ebitda_pre
    ebitda_rep = op.ebitda_reported
    da = _depreciation(op.capex, d)
    wc_cf = op.wc_cash_flow

    r_tla, r_tlb = d.euribor + d.tla_spread, d.euribor + d.tlb_spread
    r_rcf = d.euribor + d.rcf_spread
    min_cash = d.min_cash * d.stake

    tla = np.full(n, su["tla"]); tlb = np.full(n, su["tlb"])
    pik = np.full(n, su["pik"]); vl = np.full(n, su["vl"])
    rcf = np.zeros(n); cash = np.full(n, min_cash)

    keys = ["tla", "tlb", "pik", "vl", "rcf", "cash", "tax", "cfads", "cash_interest", "pl_interest",
            "tla_repay", "tlb_sweep", "dscr", "senior_nd_ebitda", "total_nd_ebitda", "ebitda_interest", "dividend"]
    out = {k: np.zeros((n, T)) for k in keys}

    for t in range(T):
        tla_rep = np.minimum(tla, su["tla"] * d.tla_amort[t])
        tla_eop = tla - tla_rep
        tla_int = r_tla * (tla + tla_eop) / 2
        draw = np.zeros(n)
        if t > 0 and YEARS[t] == d.recap_year:  # recap: nueva TLB hasta la deuda senior neta objetivo (fila 88)
            draw = np.maximum(0.0, d.recap_target * ebitda_pre[:, t - 1] - (tla + tlb + rcf - cash))
        tlb_pre = tlb + draw
        tlb_int = r_tlb * (tlb + tlb_pre) / 2
        pik_acc = pik * d.pik_rate
        vl_acc = vl * d.vl_rate
        rcf_int = rcf * r_rcf + np.maximum(0.0, d.rcf_limit - rcf) * d.rcf_fee
        cash_int = tla_int + tlb_int + rcf_int
        pl_int = cash_int + pik_acc + vl_acc

        ebit = ebitda_pre[:, t] - da[:, t]
        deductible = np.minimum(pl_int, d.interest_cap * ebitda_rep[:, t])
        tax = np.maximum(0.0, ebit - deductible) * d.tax_rate
        cfads = ebitda_pre[:, t] - tax + wc_cf[:, t] - op.capex[:, t]

        fcf_after = cfads - cash_int - tla_rep
        excess = cash - min_cash + fcf_after
        rcf_chg = np.where(excess < 0, np.minimum(d.rcf_limit - rcf, -excess), -np.minimum(rcf, excess))
        sweep = np.minimum(tlb_pre, np.maximum(0.0, excess + rcf_chg) * d.tlb_sweep)

        tla, tlb = tla_eop, tlb_pre - sweep
        pik, vl = pik + pik_acc, vl + vl_acc
        rcf = rcf + rcf_chg
        cash = cash + fcf_after + rcf_chg - sweep

        debt_service = cash_int + tla_rep
        out["tla"][:, t], out["tlb"][:, t], out["pik"][:, t], out["vl"][:, t] = tla, tlb, pik, vl
        out["rcf"][:, t], out["cash"][:, t], out["tax"][:, t], out["cfads"][:, t] = rcf, cash, tax, cfads
        out["cash_interest"][:, t], out["pl_interest"][:, t] = cash_int, pl_int
        out["tla_repay"][:, t], out["tlb_sweep"][:, t], out["dividend"][:, t] = tla_rep, sweep, draw
        out["dscr"][:, t] = np.where(debt_service > 0, cfads / np.maximum(debt_service, 1e-9), np.inf)
        out["senior_nd_ebitda"][:, t] = (tla + tlb + rcf - cash) / ebitda_pre[:, t]
        out["total_nd_ebitda"][:, t] = (tla + tlb + pik + vl + rcf - cash) / ebitda_pre[:, t]
        out["ebitda_interest"][:, t] = ebitda_pre[:, t] / np.maximum(pl_int, 1e-9)

    exit_multiple = d.entry_multiple if d.exit_multiple is None else d.exit_multiple
    exit_multiple = np.broadcast_to(np.asarray(exit_multiple, dtype=float), (n,))
    ev_exit = exit_multiple * ebitda_pre[:, -1]
    debt_exit = tla + tlb + pik + vl + rcf
    equity_exit = ev_exit - debt_exit + cash - d.exit_fees_pct * ev_exit
    sponsor_proceeds = equity_exit * su["sponsor_share"]
    flows = out["dividend"] * su["sponsor_share"]
    flows[:, -1] += sponsor_proceeds
    mom = flows.sum(axis=1) / su["sponsor"]
    irr = xirr(-su["sponsor"], flows)

    out.update(ebitda_pre=ebitda_pre, ebitda_reported=ebitda_rep, da=da, wc_cf=wc_cf,
               ev_exit=ev_exit, debt_exit=debt_exit, equity_exit=equity_exit, exit_multiple=exit_multiple,
               sponsor_proceeds=sponsor_proceeds, mom=mom, irr=irr, su=su,
               min_dscr=out["dscr"].min(axis=1), cash_shortfall=(out["cash"] < -1e-6).any(axis=1))
    return out


def xirr(outlay: float, flows: np.ndarray, lo: float = -0.99, hi: float = 2.0, iters: int = 80) -> np.ndarray:
    """XIRR de Excel vectorizado (bisección): inversión en el cierre y flujos anuales fechados según FLOW_YEARS."""
    npv = lambda r: outlay + (flows / (1 + r[:, None]) ** FLOW_YEARS).sum(axis=1)
    lo = np.full(flows.shape[0], lo); hi = np.full(flows.shape[0], hi)
    for _ in range(iters):
        mid = (lo + hi) / 2
        pos = npv(mid) > 0
        lo, hi = np.where(pos, mid, lo), np.where(pos, hi, mid)
    irr = (lo + hi) / 2
    return np.where(flows.sum(axis=1) > 0, irr, -1.0)


def excel_base_operating(n: int = 1) -> Operating:
    """Caso base del Excel del grupo (filas 10-17 constantes), para validar el motor."""
    growth, gm, opex_g, lease_g, capex_pct = 0.055, 0.582, 0.0425, 0.02, 0.052
    inv, rec, pay = 0.0815, 0.0292, -0.2154
    rev = 39864.0 * (1 + growth) ** np.arange(1, 6)
    opex = 11955.0 * (1 + opex_g) ** np.arange(1, 6)
    lease = 1834.0 * (1 + lease_g) ** np.arange(1, 6)
    tile = lambda x: np.tile(x, (n, 1))
    return Operating(revenue=tile(rev), gross_profit=tile(rev * gm), opex_post=tile(opex),
                     lease=tile(lease), capex=tile(rev * capex_pct), wc=tile(rev * (inv + rec + pay)))
