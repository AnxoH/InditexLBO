/*
 * motor.js
 * ========
 * Motor LBO y palancas del plan de creación de valor para el dashboard web.
 *
 * Es una traducción línea a línea de bp/definitiva.py (réplica del Excel definitivo del grupo,
 * Excels/Inditex_LBO_Version_Definitiva.xlsx) y de bp/levers.py (deltas), para un camino cada vez.
 * tests/test_dashboard.py comprueba que da los mismos resultados que Python, y tests/test_definitiva.py
 * que Python da lo mismo que el Excel.
 *
 * No toca el DOM: se puede ejecutar en el navegador o en un intérprete de JavaScript sin página.
 */
"use strict";

const Motor = (() => {
  const BANDS = ["Conservador", "Normal", "Optimista", "Agresivo"];
  const EXPANSION = ["usa", "young", "lefties"];
  let K = null;  // datos exportados por bp/web.py
  let T = 7;
  let SIM = null;  // caminos simulados ya decodificados
  let DEAL = null;  // hipótesis de la operación en uso: las del Excel más los cambios del panel de estructura

  // ---------- Datos ----------

  function decodeFloat32(b64) {
    // Decodificador base64 propio: atob no existe fuera del navegador.
    const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    const lookup = new Uint8Array(128);
    for (let i = 0; i < alphabet.length; i++) lookup[alphabet.charCodeAt(i)] = i;
    const clean = b64.replace(/=+$/, "");
    const bytes = new Uint8Array(Math.floor(clean.length * 3 / 4));
    let j = 0;
    for (let i = 0; i < clean.length; i += 4) {
      const a = lookup[clean.charCodeAt(i)], b = lookup[clean.charCodeAt(i + 1)];
      const c = lookup[clean.charCodeAt(i + 2)] || 0, d = lookup[clean.charCodeAt(i + 3)] || 0;
      const n = (a << 18) | (b << 12) | (c << 6) | d;
      if (j < bytes.length) bytes[j++] = (n >> 16) & 255;
      if (j < bytes.length) bytes[j++] = (n >> 8) & 255;
      if (j < bytes.length) bytes[j++] = n & 255;
    }
    return new Float32Array(bytes.buffer);
  }

  function init(data) {
    K = data;
    T = data.years.length;
    DEAL = Object.assign({}, data.deal);
    const s = data.sim;
    const vars = {};
    for (const k of Object.keys(s.vars)) vars[k] = decodeFloat32(s.vars[k]);
    const mult = {};
    for (const k of Object.keys(s.mult)) mult[k] = decodeFloat32(s.mult[k]);
    const medRev = [];
    for (let t = 0; t < T; t++) {
      const col = new Float64Array(s.n);
      for (let i = 0; i < s.n; i++) col[i] = vars.revenue[i * T + t];
      medRev.push(median(col));
    }
    SIM = { n: s.n, vars, mult, medRev };
  }

  // Cambia hipótesis de la operación sobre las del Excel (p. ej. { rollover: 0.3, lp_share: 0.8 }); {} vuelve al Excel.
  function setDeal(patch) {
    DEAL = Object.assign({}, K.deal, patch || {});
    return DEAL;
  }

  const range = (f) => Array.from({ length: T }, (_, t) => f(t));
  const zeros = () => range(() => 0);

  function pathOp(i) {
    const v = SIM.vars, o = i * T, share = K.sim.maint_share;
    const take = (a) => range((t) => a[o + t]);
    const capex = take(v.capex);
    return { revenue: take(v.revenue), gross_profit: take(v.gross_profit), opex: take(v.opex), lease: take(v.lease),
             capex_maint: capex.map((c, t) => c * share[t]), capex_exp: capex.map((c, t) => c * (1 - share[t])), wc: take(v.wc),
             wc0: K.fy25.wc };
  }

  // ---------- Motor LBO (bp/definitiva.py) ----------

  const offerPrice = (d) => d.share_price * (1 + d.premium);
  const equityValue = (d) => offerPrice(d) * d.shares_m;
  const entryMultiple = (d) => (equityValue(d) - d.net_cash) / d.ebitda_ref;

  function sourcesAndUses(d) {
    const e0 = d.ebitda_ref, P = equityValue(d);
    const rollover = P * d.rollover, cashTakeover = P - rollover;
    const tla = d.tla_x * e0, tlb = d.tlb_x * e0, sub = d.sub_x * e0, vl = d.vl_share * P;
    const fees = tla * d.fee_tla + tlb * d.fee_tlb + sub * d.fee_sub + vl * d.fee_vl + d.rcf_limit * d.fee_rcf;
    const adv = cashTakeover * d.adv_fee;
    const excessCash = Math.max(0, d.net_cash - d.min_cash) + d.propco_proceeds;
    const uses = cashTakeover + rollover + fees + adv;
    const sponsor = uses - (tla + tlb + sub + vl) - excessCash - rollover;
    const equity = rollover + sponsor;
    return { P, rollover, cashTakeover, tla, tlb, sub, vl, fees, adv, excessCash, uses, sponsor, equity,
             sponsorShare: sponsor / equity, debt: tla + tlb + sub + vl };
  }

  function depreciation(capex, d) {
    const da = zeros();
    let remaining = d.nfa0;
    for (let t = 0; t < T; t++) {
      const x = Math.min(remaining, d.nfa0 / d.asset_life);
      remaining -= x;
      da[t] += x;
    }
    for (let v = 0; v < T; v++) {
      let left = capex[v];
      for (let t = v; t < T; t++) {
        const charge = Math.min(left, capex[v] / d.asset_life * (t === v ? d.first_period : 1.0));
        left -= charge;
        da[t] += charge;
      }
    }
    return da;
  }

  function levCovenant(d) {
    const su = sourcesAndUses(d);
    const entry = (su.debt - d.min_cash) / d.ebitda_ref;
    const out = [Math.ceil(Math.round(entry / (1 - d.lev_headroom) * 20 * 1e9) / 1e9) / 20];
    for (let t = 0; t < T; t++) out.push(Math.max(K.lev_floor, out[out.length - 1] - K.lev_step));
    return out;
  }

  // full = true guarda las series año a año (para la página); false solo lo que necesita la simulación.
  function run(op, d, full = true, exitYear = null) {
    const su = sourcesAndUses(d);
    const ebitdaRep = [], ebitda = [], wcCf = [], capex = [];
    for (let t = 0; t < T; t++) {
      ebitdaRep.push(op.gross_profit[t] - op.opex[t]);
      ebitda.push(ebitdaRep[t] - op.lease[t]);
      wcCf.push((t === 0 ? op.wc0 : op.wc[t - 1]) - op.wc[t]);
      capex.push(op.capex_maint[t] + op.capex_exp[t]);
    }
    const da = depreciation(capex, d);
    const rTla = d.euribor + d.tla_spread, rTlb = d.euribor + d.tlb_spread, rRcf = d.euribor + d.rcf_spread;
    const feeAm = su.fees / d.fee_amort_years;

    let tla = su.tla, tlb = su.tlb, sub = su.sub, vl = su.vl, rcf = 0, cash = d.min_cash, carryFwd = 0;
    let minDscr = Infinity, shortfall = false;
    const dividend = zeros(), debt = zeros(), cashArr = zeros(), tlaArr = zeros(), tlbArr = zeros(), rcfArr = zeros(),
          subArr = zeros(), vlArr = zeros();
    const out = full ? { tax: [], cfads: [], cfads_bank: [], dscr: [], dscr_total: [], senior_nd_ebitda: [],
                         total_nd_ebitda: [], cash_interest: [], pl_interest: [], tla_repay: [], tlb_sweep: [],
                         nondeductible: [] } : null;

    for (let t = 0; t < T; t++) {
      const year = d.first_year + t;
      const tlaRep = Math.min(tla, su.tla * d.tla_amort[t]);
      const tlaEop = tla - tlaRep;
      const tlaInt = rTla * (tla + tlaEop) / 2;
      const tlbMand = Math.min(tlb, su.tlb * d.tlb_amort);
      let draw = 0;
      if (t > 0 && year === d.recap_year) draw = Math.max(0, d.recap_target * ebitda[t - 1] - (tla + tlb + rcf - cash));
      const tlbPre = tlb - tlbMand + draw;
      const tlbInt = rTlb * (tlb + tlbPre) / 2;
      const subAcc = sub * d.sub_rate, vlAcc = vl * d.vl_rate;
      const rcfInt = rcf * rRcf + Math.max(0, d.rcf_limit - rcf) * d.rcf_undrawn;
      const cashInt = tlaInt + tlbInt + (d.sub_pik ? 0 : subAcc) + (d.vl_pik ? 0 : vlAcc) + rcfInt;
      const plInt = tlaInt + tlbInt + subAcc + vlAcc + rcfInt;

      // Tax & WACC filas 14-35
      const ebit = ebitda[t] - da[t];
      const feeT = t < d.fee_amort_years ? feeAm : 0;
      const cap = Math.max(d.cap_floor, d.interest_cap * ebitda[t]);
      const subject = plInt + feeT;
      const nondeductible = Math.max(0, subject - cap);
      const recovered = Math.min(carryFwd, Math.max(0, cap - subject));
      carryFwd = carryFwd + nondeductible - recovered;
      const taxable = ebit - plInt - feeT + nondeductible - recovered;
      const tax = Math.max(0, taxable) * d.tax_rate;

      // Debt & Covenants filas 77-93
      const cfadsBank = ebitda[t] - tax + wcCf[t] - op.capex_maint[t];
      const cfads = cfadsBank - op.capex_exp[t];
      const mandatory = tlaRep + tlbMand;
      const fcf = cfads - cashInt - mandatory;
      const excess = cash - d.min_cash + fcf;
      const rcfChg = excess < 0 ? Math.min(d.rcf_limit - rcf, -excess) : -Math.min(rcf, excess);
      const sweep = Math.min(tlbPre, Math.max(0, excess + rcfChg) * d.tlb_sweep);

      tla = tlaEop; tlb = tlbPre - sweep;
      if (d.sub_pik) sub += subAcc;
      if (d.vl_pik) vl += vlAcc;
      rcf += rcfChg;
      cash = cash + fcf + rcfChg - sweep;

      const service = cashInt + mandatory;
      const dscr = service > 0 ? cfadsBank / Math.max(service, 1e-9) : Infinity;
      minDscr = Math.min(minDscr, dscr);
      if (cash < -1e-6) shortfall = true;
      dividend[t] = draw; debt[t] = tla + tlb + sub + vl + rcf; cashArr[t] = cash;
      tlaArr[t] = tla; tlbArr[t] = tlb; subArr[t] = sub; vlArr[t] = vl; rcfArr[t] = rcf;
      if (full) {
        out.tax.push(tax); out.cfads.push(cfads); out.cfads_bank.push(cfadsBank); out.dscr.push(dscr);
        out.dscr_total.push(service > 0 ? cfads / Math.max(service, 1e-9) : Infinity);
        out.cash_interest.push(cashInt); out.pl_interest.push(plInt); out.tla_repay.push(tlaRep); out.tlb_sweep.push(sweep);
        out.nondeductible.push(nondeductible);
        out.senior_nd_ebitda.push((tla + tlb + rcf - cash) / ebitda[t]);
        out.total_nd_ebitda.push((tla + tlb + sub + vl + rcf - cash) / ebitda[t]);
      }
    }

    const res = { su, ebitda_pre: ebitda, ebitda_reported: ebitdaRep, dividend, debt, cash: cashArr, tla: tlaArr,
                  tlb: tlbArr, sub: subArr, vl: vlArr, rcf: rcfArr, min_dscr: minDscr, cash_shortfall: shortfall };
    if (full) Object.assign(res, out, { da, wc_cf: wcCf, lev_covenant: levCovenant(d) });
    return Object.assign(res, exitReturns(res, d, exitYear ?? d.exit_year));
  }

  // LBO Summary filas 48-97: valor de salida, retorno del fondo y cascada GP/LP en el año elegido.
  function exitReturns(res, d, exitYear) {
    const su = res.su, k = exitYear - d.first_year, years = k + 1;
    const multiple = d.exit_multiple == null ? entryMultiple(d) : d.exit_multiple;
    const ev = multiple * res.ebitda_pre[k];
    const equityExit = ev - d.exit_fee * ev - res.debt[k] + res.cash[k];
    const s = su.sponsorShare, proceeds = equityExit * s;
    const flows = [];
    for (let t = 0; t <= k; t++) flows.push(res.dividend[t] * s);
    flows[k] += proceeds;
    let pool = 0;
    for (const f of flows) pool += f;
    const wf = waterfall(pool, su.sponsor, years, d);
    return Object.assign({ exit_year: exitYear, exit_years: years, exit_multiple: multiple, ev_exit: ev,
                           equity_exit: equityExit, sponsor_proceeds: proceeds, flows, mom: pool / su.sponsor,
                           irr: annualIrr(su.sponsor, flows) }, wf);
  }

  // TIR con flujos al final de cada año; con un solo flujo es MOIC^(1/años) - 1, como el Excel (LBO Summary!M62).
  function annualIrr(outlay, flows) {
    const k = flows.length;
    let total = 0, single = true;
    for (let t = 0; t < k; t++) { total += flows[t]; if (t < k - 1 && flows[t] !== 0) single = false; }
    if (!(total > 0)) return -1.0;
    if (single) return Math.pow(total / outlay, 1 / k) - 1;
    const npv = (r) => { let v = -outlay; for (let t = 0; t < k; t++) v += flows[t] / Math.pow(1 + r, t + 1); return v; };
    let lo = -0.99, hi = 2.0;
    for (let it = 0; it < 90; it++) {
      const mid = (lo + hi) / 2;
      if (npv(mid) > 0) lo = mid; else hi = mid;
    }
    return (lo + hi) / 2;
  }

  // LBO Summary filas 73-97: cascada europea (capital, preferente, catch-up y reparto 80/20) entre LPs y GP.
  function waterfall(pool, sponsor, years, d) {
    const lpTicket = sponsor * d.lp_share, gpTicket = sponsor * (1 - d.lp_share);
    const gpCoinvest = pool * (1 - d.lp_share), lpPool = pool * d.lp_share;
    const t1 = Math.min(lpPool, lpTicket);
    const target = lpTicket * (Math.pow(1 + d.hurdle, years) - 1);
    const t2 = Math.min(Math.max(0, lpPool - t1), target);
    const t3 = Math.min(Math.max(0, lpPool - t1 - t2), t2 * (d.carry / (1 - d.carry)) * d.catch_up);
    const rest = Math.max(0, lpPool - t1 - t2 - t3);
    const lpNet = t1 + t2 + rest * (1 - d.carry), carry = t3 + rest * d.carry, gpNet = gpCoinvest + carry;
    const root = (x, ticket) => (x > 0 ? Math.pow(x / ticket, 1 / years) - 1 : -1);
    return { lp_net: lpNet, gp_net: gpNet, gp_carry: carry, gp_coinvest: gpCoinvest, lp_ticket: lpTicket, gp_ticket: gpTicket,
             lp_irr: root(lpNet, lpTicket), lp_mom: lpNet / lpTicket, gp_irr: root(gpNet, gpTicket), gp_mom: gpNet / gpTicket,
             wf_tiers: { capital: t1, preferred: t2, catch_up: t3, lp_split: rest * (1 - d.carry), gp_split: rest * d.carry } };
  }

  // ---------- Palancas (bp/levers.py, deltas; bp/definitiva.py, apply_levers) ----------

  const add = (a, b) => a.map((x, t) => x + b[t]);

  function applyLevers(op, deal, values, on, mult = null, scale = null) {
    const m = (k) => (mult && k in mult ? mult[k] : 1);
    const sc = scale || range(() => 1);
    const revB = op.revenue, gpB = op.gross_profit;
    const dRev = {}, dEbitda = {}, dCapex = {};
    let dLease = zeros();
    const dWcRatio = zeros();

    for (const key of EXPANSION) {
      if (!on[key]) continue;
      const v = values[key];
      const base = sc.map((s) => v.m2 * v.density / 1000 * m(key) * s);
      dRev[key] = base.map((b, t) => b * K.F_COHORT[t] * (1 - v.cannib));
      dEbitda[key] = base.map((b, t) => b * (v.margin * K.G_COHORT[t] - v.cannib * K.GROUP_MARGIN * K.F_COHORT[t]));
      dCapex[key] = zeros().map(() => v.m2 * v.capex / 1000);
    }

    if (on.refurb) {
      const v = values.refurb;
      dRev.refurb = sc.map((s, t) => v.m2 * K.BASE_DENSITY / 1000 * v.uplift * K.H_COHORT[t] * m("refurb") * s);
      dEbitda.refurb = dRev.refurb.map((x) => x * v.margin);
      dCapex.refurb = zeros().map(() => v.m2 * v.capex / 1000);
    }

    if (on.efficiency) {
      const v = values.efficiency;
      const savings = revB.map((r, t) => v.bps / 1e4 * r * Math.min(1.0, (t + 1) / v.years) * m("efficiency"));
      const oneOff = zeros();
      oneOff[0] = oneOff[1] = 0.5 * v.one_off * v.bps / 1e4 * revB[0];
      dEbitda.efficiency = savings.map((s, t) => s - oneOff[t]);
    }

    if (on.wc) {
      const v = values.wc;
      for (let t = 0; t < T; t++) dWcRatio[t] -= (v.pay + v.inv) / 100 * K.WC_PHASE[t] * m("wc");
    }

    let proceeds = 0.0;
    if (on.propco) {
      const v = values.propco;
      proceeds = K.LAND_BUILDINGS_NBV * v.share * v.multiple;
      dLease = zeros().map((_, t) => proceeds * v.caprate * Math.pow(1.02, t));
      dEbitda.propco = dLease.map((x) => -x);
    }

    const totalRev = Object.values(dRev).reduce(add, zeros());
    const totalEbitda = Object.values(dEbitda).reduce(add, zeros());
    const totalCapex = Object.values(dCapex).reduce(add, zeros());

    const revF = [], gpF = [], leaseF = [], opexF = [], expF = [], wcF = [];
    for (let t = 0; t < T; t++) {
      const ebitdaB = gpB[t] - op.opex[t] - op.lease[t];
      revF.push(revB[t] + totalRev[t]);
      gpF.push(gpB[t] + totalRev[t] * (gpB[t] / revB[t]));
      leaseF.push(op.lease[t] + totalRev[t] * K.LEASE_SHARE + dLease[t]);
      opexF.push(gpF[t] - (ebitdaB + totalEbitda[t]) - leaseF[t]);
      expF.push(op.capex_exp[t] + totalCapex[t]);
      wcF.push(revF[t] * (op.wc[t] / revB[t] + dWcRatio[t]));
    }
    const newOp = { revenue: revF, gross_profit: gpF, opex: opexF, lease: leaseF, capex_maint: op.capex_maint,
                    capex_exp: expF, wc: wcF, wc0: op.wc0 };
    const newDeal = Object.assign({}, deal, { propco_proceeds: proceeds });
    if (on.recap) Object.assign(newDeal, { recap_year: Math.trunc(values.recap.year), recap_target: values.recap.target });
    return { op: newOp, deal: newDeal, dRev, dEbitda, dCapex, dLease, dWcRatio, proceeds };
  }

  // ---------- Casos deterministas y simulación ----------

  function caseOp(name) {
    const c = K.cases[name];
    return { revenue: c.revenue, gross_profit: c.gross_profit, opex: c.opex, lease: c.lease, capex_maint: c.capex_maint,
             capex_exp: c.capex_exp, wc: c.wc, wc0: K.fy25.wc };
  }

  function runCase(name, values, on, exitYear = null) {
    const lr = applyLevers(caseOp(name), DEAL, values, on);
    return { lever: lr, res: run(lr.op, lr.deal, true, exitYear) };
  }

  // Puente del equity (100 %) entre el cierre y la salida: start + suma de items = end (bp/definitiva.value_bridge).
  function valueBridge(res, d) {
    const su = res.su, k = res.exit_year - d.first_year, m0 = entryMultiple(d), eT = res.ebitda_pre[k];
    const items = {
      growth: m0 * (eT - d.ebitda_ref),
      multiple: (res.exit_multiple - m0) * eT,
      senior: su.tla + su.tlb - (res.tla[k] + res.tlb[k] + res.rcf[k]),
      sub: su.sub + su.vl - (res.sub[k] + res.vl[k]),
      cash: res.cash[k] - d.min_cash,
      fees_entry: -(su.fees + su.adv),
      fees_exit: -d.exit_fee * res.ev_exit,
      propco: d.propco_proceeds,
    };
    let dividend = 0;
    for (let t = 0; t <= k; t++) dividend += res.dividend[t];
    return { start: su.equity, items, end: res.equity_exit, dividend };
  }

  // Reparto exacto (Shapley) de la mejora de la TIR del caso entre las palancas activas.
  function shapley(name, values, on, exitYear = null) {
    const keys = Object.keys(on).filter((k) => on[k]);
    const op = caseOp(name);
    const cache = new Map();
    const value = (mask) => {
      if (!cache.has(mask)) {
        const sub = {};
        keys.forEach((k, i) => { sub[k] = Boolean(mask & (1 << i)); });
        const lr = applyLevers(op, DEAL, values, sub);
        cache.set(mask, run(lr.op, lr.deal, false, exitYear).irr);
      }
      return cache.get(mask);
    };
    const n = keys.length, fact = [1];
    for (let i = 1; i <= n; i++) fact.push(fact[i - 1] * i);
    const phi = {};
    keys.forEach((k, i) => {
      let total = 0;
      for (let mask = 0; mask < (1 << n); mask++) {
        if (mask & (1 << i)) continue;
        let size = 0;
        for (let j = 0; j < n; j++) if (mask & (1 << j)) size++;
        total += fact[size] * fact[n - size - 1] / fact[n] * (value(mask | (1 << i)) - value(mask));
      }
      phi[k] = total;
    });
    return phi;
  }

  // Todos los caminos simulados con el plan (con riesgo de ejecución y las mismas crisis que el negocio).
  function simulate(values, on, withPlan = true, exitYear = null) {
    const n = SIM.n;
    const irr = new Float64Array(n), mom = new Float64Array(n), minDscr = new Float64Array(n);
    const gpIrr = new Float64Array(n), lpIrr = new Float64Array(n);
    const ebitda = range(() => new Float64Array(n));
    let shortfall = 0, negEquity = 0;
    const mult = {};
    for (let i = 0; i < n; i++) {
      let op = pathOp(i), deal = DEAL;
      if (withPlan) {
        const scale = op.revenue.map((r, t) => r / SIM.medRev[t]);
        for (const k of Object.keys(SIM.mult)) mult[k] = SIM.mult[k][i];
        const lr = applyLevers(op, deal, values, on, mult, scale);
        op = lr.op; deal = lr.deal;
      }
      const r = run(op, deal, false, exitYear);
      irr[i] = r.irr; mom[i] = r.mom; minDscr[i] = r.min_dscr; gpIrr[i] = r.gp_irr; lpIrr[i] = r.lp_irr;
      for (let t = 0; t < T; t++) ebitda[t][i] = r.ebitda_pre[t];
      if (r.cash_shortfall) shortfall++;
      if (r.equity_exit <= 0) negEquity++;
    }
    return { n, irr, mom, minDscr, gpIrr, lpIrr, ebitda, shortfall: shortfall / n, negEquity: negEquity / n };
  }

  // Mismas métricas que web.risk_summary, más las bandas de EBITDA y el histograma de la TIR.
  function riskSummary(sim) {
    const share = (a, f) => { let c = 0; for (const x of a) if (f(x)) c++; return c / a.length; };
    const [irrP10, irrMed, irrP90] = quantiles(sim.irr, [10, 50, 90]);
    const eb = sim.ebitda.map((col) => quantiles(col, [10, 50, 90]));
    return {
      irr_median: irrMed, irr_p10: irrP10, irr_p90: irrP90, mom_median: median(sim.mom),
      gp_irr_median: median(sim.gpIrr), lp_irr_median: median(sim.lpIrr),
      p_irr_neg: share(sim.irr, (x) => x < 0), p_irr_15: share(sim.irr, (x) => x >= 0.15),
      p_irr_20: share(sim.irr, (x) => x >= 0.20), p_lp_hurdle: share(sim.lpIrr, (x) => x >= DEAL.hurdle),
      p_dscr: share(sim.minDscr, (x) => x < DEAL.dscr_min), p_dscr_10: share(sim.minDscr, (x) => x < 1.0),
      p_shortfall: sim.shortfall, p_neg_equity: sim.negEquity,
      ebitda_p10: eb.map((q) => q[0]), ebitda_p50: eb.map((q) => q[1]), ebitda_p90: eb.map((q) => q[2]),
      ebitda_last_median: eb[T - 1][1], irr_hist: histogram(sim.irr, -0.10, 0.30, 0.01),
    };
  }

  // ---------- Utilidades ----------

  function quantiles(arr, qs) {  // interpolación lineal, como numpy.percentile (una sola ordenación)
    const s = Float64Array.from(arr).sort();
    return qs.map((q) => {
      const pos = (q / 100) * (s.length - 1);
      const lo = Math.floor(pos), hi = Math.ceil(pos);
      return s[lo] + (s[hi] - s[lo]) * (pos - lo);
    });
  }

  const percentile = (arr, q) => quantiles(arr, [q])[0];
  const median = (arr) => percentile(arr, 50);

  // Proporción de caminos por tramo de 1 pp; los extremos acumulan lo que queda fuera.
  function histogram(arr, lo, hi, step) {
    const bins = Math.round((hi - lo) / step);
    const counts = new Array(bins).fill(0);
    for (const x of arr) counts[Math.min(bins - 1, Math.max(0, Math.floor((x - lo) / step + 1e-9)))]++;
    return { lo, step, share: counts.map((c) => c / arr.length) };
  }

  function band(param, v) {
    if (!param.edges) return "";
    const e = param.edges;
    const order = param.reverse ? BANDS.slice().reverse() : BANDS;
    const idx = v < e[1] ? 0 : v < e[2] ? 1 : v < e[3] ? 2 : 3;
    return order[idx];
  }

  function defaults() {
    const out = {};
    for (const lv of K.levers) { out[lv.key] = {}; for (const p of lv.params) out[lv.key][p.key] = p.default; }
    return out;
  }

  function bandValues(name) {  // punto medio de la banda en cada parámetro, como levers.band_values
    const out = defaults();
    for (const lv of K.levers) {
      for (const p of lv.params) {
        if (!p.edges) continue;
        const order = p.reverse ? BANDS.slice().reverse() : BANDS;
        const i = order.indexOf(name);
        out[lv.key][p.key] = (p.edges[i] + p.edges[i + 1]) / 2;
      }
    }
    return out;
  }

  return { init, setDeal, run, applyLevers, runCase, valueBridge, caseOp, shapley, simulate, riskSummary, sourcesAndUses,
           entryMultiple, band, defaults, bandValues, quantiles, percentile, median, histogram, BANDS,
           get K() { return K; }, get T() { return T; }, get SIM() { return SIM; }, get deal() { return DEAL; } };
})();

if (typeof globalThis !== "undefined") globalThis.Motor = Motor;
