/*
 * motor.js
 * ========
 * Motor LBO y palancas del plan de creación de valor para el dashboard web.
 *
 * Es una traducción línea a línea de bp/lbo.py (sources_and_uses, _depreciation, run, xirr) y de
 * bp/levers.py (apply), para un camino cada vez. tests/test_dashboard.py comprueba que da los mismos
 * resultados que Python (y por tanto que el Excel integrado).
 *
 * No toca el DOM: se puede ejecutar en el navegador o en un intérprete de JavaScript sin página.
 */
"use strict";

const Motor = (() => {
  const T = 5;
  const BANDS = ["Conservador", "Normal", "Optimista", "Agresivo"];
  const EXPANSION = ["usa", "young", "lefties"];
  let K = null;  // datos exportados por bp/web.py
  let SIM = null;  // caminos simulados ya decodificados

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

  function pathOp(i) {
    const v = SIM.vars, o = i * T;
    const take = (a) => [a[o], a[o + 1], a[o + 2], a[o + 3], a[o + 4]];
    return { revenue: take(v.revenue), gross_profit: take(v.gross_profit), opex_post: take(v.opex_post),
             lease: take(v.lease), capex: take(v.capex), wc: take(v.wc), wc_fy25: K.wc_fy25 };
  }

  // ---------- Motor LBO (bp/lbo.py) ----------

  const offerPrice = (d) => d.share_price * (1 + d.premium);
  const entryMultiple = (d) => (offerPrice(d) * d.shares_m - d.net_cash_fy25) / d.ebitda_ref;

  function sourcesAndUses(d) {
    const ebitda = d.ebitda_ref * d.stake;
    const tla = d.tla_x * ebitda, tlb = d.tlb_x * ebitda, pik = d.pik_x * ebitda, vl = d.vl_x * ebitda;
    const purchase = offerPrice(d) * d.shares_m * d.stake;
    const finFees = (tla + tlb + pik) * d.financing_fees_pct;
    const advFees = purchase * d.entry_fees_pct;
    const uses = purchase + finFees + advFees;
    const excessCash = Math.max(0, d.net_cash_fy25 - d.min_cash) * d.stake + d.propco_proceeds;
    const equity = uses - (tla + tlb + pik + vl) - excessCash;
    const rollover = offerPrice(d) * d.shares_m * d.amancio_stake * d.rollover_pct;
    const sponsor = equity - rollover;
    return { tla, tlb, pik, vl, purchase, finFees, advFees, uses, excessCash, equity, rollover, sponsor,
             sponsorShare: sponsor / equity };
  }

  function depreciation(capex, d) {
    const da = [0, 0, 0, 0, 0];
    let remainingExisting = d.nfa_fy25;
    for (let t = 0; t < T; t++) {
      const daExisting = Math.min(remainingExisting, d.nfa_fy25 / d.asset_life);
      remainingExisting -= daExisting;
      da[t] += daExisting;
    }
    for (let v = 0; v < T; v++) {
      let remaining = capex[v];
      for (let t = v; t < T; t++) {
        let charge = capex[v] / d.asset_life * (t === v ? d.first_period : 1.0);
        charge = Math.min(remaining, charge);
        remaining -= charge;
        da[t] += charge;
      }
    }
    return da;
  }

  function npv(outlay, flows, r) {
    let s = outlay;
    for (let t = 0; t < T; t++) s += flows[t] / Math.pow(1 + r, K.flow_years[t]);
    return s;
  }

  function xirr(outlay, flows) {
    let total = 0, nonNegative = true;
    for (const f of flows) { total += f; if (f < 0) nonNegative = false; }
    if (!(total > 0)) return -1.0;
    if (nonNegative && outlay < 0) {
      // Con flujos positivos el VAN es decreciente y convexo: Newton desde la TIR "todo al final" converge
      // por la izquierda. Si se sale del intervalo, se usa la misma bisección que Python.
      let r = Math.pow(total / -outlay, 1 / K.flow_years[T - 1]) - 1;
      for (let it = 0; it < 60; it++) {
        let f = outlay, df = 0;
        for (let t = 0; t < T; t++) {
          const disc = Math.pow(1 + r, -K.flow_years[t]);
          f += flows[t] * disc;
          df -= K.flow_years[t] * flows[t] * disc / (1 + r);
        }
        const step = f / df;
        r -= step;
        if (!(r > -0.99 && r < 2.0)) break;
        if (Math.abs(step) < 1e-14) return r;
      }
    }
    let lo = -0.99, hi = 2.0;
    for (let it = 0; it < 80; it++) {
      const mid = (lo + hi) / 2;
      if (npv(outlay, flows, mid) > 0) lo = mid; else hi = mid;
    }
    return (lo + hi) / 2;
  }

  // full = true guarda las series año a año (para la página); false solo lo que necesita la simulación.
  function run(op, d, full = true) {
    const su = sourcesAndUses(d);
    const ebitdaRep = [], ebitdaPre = [], wcCf = [];
    for (let t = 0; t < T; t++) {
      ebitdaRep.push(op.gross_profit[t] - op.opex_post[t]);
      ebitdaPre.push(ebitdaRep[t] - op.lease[t]);
      wcCf.push((t === 0 ? op.wc_fy25 : op.wc[t - 1]) - op.wc[t]);
    }
    const da = depreciation(op.capex, d);
    const rTla = d.euribor + d.tla_spread, rTlb = d.euribor + d.tlb_spread, rRcf = d.euribor + d.rcf_spread;
    const minCash = d.min_cash * d.stake;

    let tla = su.tla, tlb = su.tlb, pik = su.pik, vl = su.vl, rcf = 0, cash = minCash;
    let minDscr = Infinity, shortfall = false;
    const dividend = [0, 0, 0, 0, 0];
    const out = full ? { tla: [], tlb: [], pik: [], vl: [], rcf: [], cash: [], tax: [], cfads: [], dscr: [],
                         senior_nd_ebitda: [], total_nd_ebitda: [], cash_interest: [], tlb_sweep: [] } : null;

    for (let t = 0; t < T; t++) {
      const tlaRep = Math.min(tla, su.tla * d.tla_amort[t]);
      const tlaEop = tla - tlaRep;
      const tlaInt = rTla * (tla + tlaEop) / 2;
      let draw = 0;
      if (t > 0 && K.years[t] === d.recap_year) {  // recap: nueva TLB hasta la deuda senior neta objetivo
        draw = Math.max(0, d.recap_target * ebitdaPre[t - 1] - (tla + tlb + rcf - cash));
      }
      const tlbPre = tlb + draw;
      const tlbInt = rTlb * (tlb + tlbPre) / 2;
      const pikAcc = pik * d.pik_rate;
      const vlAcc = vl * d.vl_rate;
      const rcfInt = rcf * rRcf + Math.max(0, d.rcf_limit - rcf) * d.rcf_fee;
      const cashInt = tlaInt + tlbInt + rcfInt;
      const plInt = cashInt + pikAcc + vlAcc;

      const ebit = ebitdaPre[t] - da[t];
      const deductible = Math.min(plInt, d.interest_cap * ebitdaRep[t]);
      const tax = Math.max(0, ebit - deductible) * d.tax_rate;
      const cfads = ebitdaPre[t] - tax + wcCf[t] - op.capex[t];

      const fcfAfter = cfads - cashInt - tlaRep;
      const excess = cash - minCash + fcfAfter;
      const rcfChg = excess < 0 ? Math.min(d.rcf_limit - rcf, -excess) : -Math.min(rcf, excess);
      const sweep = Math.min(tlbPre, Math.max(0, excess + rcfChg) * d.tlb_sweep);

      tla = tlaEop; tlb = tlbPre - sweep;
      pik = pik + pikAcc; vl = vl + vlAcc;
      rcf = rcf + rcfChg;
      cash = cash + fcfAfter + rcfChg - sweep;

      const debtService = cashInt + tlaRep;
      const dscr = debtService > 0 ? cfads / Math.max(debtService, 1e-9) : Infinity;
      minDscr = Math.min(minDscr, dscr);
      if (cash < -1e-6) shortfall = true;
      dividend[t] = draw;
      if (full) {
        out.tla.push(tla); out.tlb.push(tlb); out.pik.push(pik); out.vl.push(vl); out.rcf.push(rcf);
        out.cash.push(cash); out.tax.push(tax); out.cfads.push(cfads); out.dscr.push(dscr);
        out.cash_interest.push(cashInt); out.tlb_sweep.push(sweep);
        out.senior_nd_ebitda.push((tla + tlb + rcf - cash) / ebitdaPre[t]);
        out.total_nd_ebitda.push((tla + tlb + pik + vl + rcf - cash) / ebitdaPre[t]);
      }
    }

    const exitMultiple = d.exit_multiple == null ? entryMultiple(d) : d.exit_multiple;
    const evExit = exitMultiple * ebitdaPre[T - 1];
    const debtExit = tla + tlb + pik + vl + rcf;
    const equityExit = evExit - debtExit + cash - d.exit_fees_pct * evExit;
    const sponsorProceeds = equityExit * su.sponsorShare;
    const flows = dividend.map((x) => x * su.sponsorShare);
    flows[T - 1] += sponsorProceeds;
    let total = 0;
    for (const f of flows) total += f;
    const res = { irr: xirr(-su.sponsor, flows), mom: total / su.sponsor, min_dscr: minDscr,
                  ebitda_pre: ebitdaPre, ebitda_reported: ebitdaRep, equity_exit: equityExit,
                  cash_shortfall: shortfall, dividend, su, ev_exit: evExit, debt_exit: debtExit,
                  exit_multiple: exitMultiple, sponsor_proceeds: sponsorProceeds, flows };
    if (full) Object.assign(res, out, { da, wc_cf: wcCf });
    return res;
  }

  // ---------- Palancas (bp/levers.py, apply) ----------

  const zeros = () => [0, 0, 0, 0, 0];
  const add = (a, b) => a.map((x, t) => x + b[t]);

  function applyLevers(op, deal, values, on, mult = null, scale = null) {
    const m = (k) => (mult && k in mult ? mult[k] : 1);
    const sc = scale || [1, 1, 1, 1, 1];
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

    const revF = [], gpF = [], leaseF = [], opexF = [], capexF = [], wcF = [];
    for (let t = 0; t < T; t++) {
      const ebitdaPreB = gpB[t] - op.opex_post[t] - op.lease[t];
      revF.push(revB[t] + totalRev[t]);
      gpF.push(gpB[t] + totalRev[t] * (gpB[t] / revB[t]));
      leaseF.push(op.lease[t] + totalRev[t] * K.LEASE_SHARE + dLease[t]);
      const ebitdaPreF = ebitdaPreB + totalEbitda[t];
      opexF.push(gpF[t] - ebitdaPreF - leaseF[t]);
      capexF.push(op.capex[t] + totalCapex[t]);
      wcF.push(revF[t] * (op.wc[t] / revB[t] + dWcRatio[t]));
    }
    const newOp = { revenue: revF, gross_profit: gpF, opex_post: opexF, lease: leaseF, capex: capexF, wc: wcF,
                    wc_fy25: op.wc_fy25 };
    const newDeal = Object.assign({}, deal, { propco_proceeds: proceeds });
    if (on.recap) Object.assign(newDeal, { recap_year: Math.trunc(values.recap.year), recap_target: values.recap.target });
    return { op: newOp, deal: newDeal, dRev, dEbitda, dCapex, dLease, dWcRatio, proceeds };
  }

  // ---------- Casos deterministas y simulación ----------

  function caseOp(name) {
    const c = K.cases[name];
    return { revenue: c.revenue, gross_profit: c.gross_profit, opex_post: c.opex_post, lease: c.lease,
             capex: c.capex, wc: c.wc, wc_fy25: K.wc_fy25 };
  }

  function runCase(name, values, on) {
    const op = caseOp(name);
    const lr = applyLevers(op, K.deal, values, on);
    return { lever: lr, res: run(lr.op, lr.deal, true) };
  }

  // Puente del valor del equity (100 %) entre el cierre y la salida; necesita run(..., full = true).
  // start + suma de items = end. La PropCo suma porque su caja rebaja el equity del cierre.
  function valueBridge(res, d) {
    const su = res.su, t = T - 1;
    const items = {
      ebitda: res.ev_exit - entryMultiple(d) * d.ebitda_ref,
      senior: su.tla + su.tlb - (res.tla[t] + res.tlb[t] + res.rcf[t]),
      pik: su.pik + su.vl - (res.pik[t] + res.vl[t]),
      cash: res.cash[t] - d.min_cash * d.stake,
      fees_entry: -(su.finFees + su.advFees),
      fees_exit: -d.exit_fees_pct * res.ev_exit,
      propco: d.propco_proceeds,
    };
    return { start: su.equity, items, end: res.equity_exit, dividend: res.dividend.reduce((a, b) => a + b, 0) };
  }

  // Reparto exacto (Shapley) de la mejora de la TIR del caso entre las palancas activas.
  function shapley(name, values, on) {
    const keys = Object.keys(on).filter((k) => on[k]);
    const op = caseOp(name);
    const cache = new Map();
    const value = (mask) => {
      if (!cache.has(mask)) {
        const sub = {};
        keys.forEach((k, i) => { sub[k] = Boolean(mask & (1 << i)); });
        const lr = applyLevers(op, K.deal, values, sub);
        cache.set(mask, run(lr.op, lr.deal, false).irr);
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
  function simulate(values, on, withPlan = true) {
    const n = SIM.n;
    const irr = new Float64Array(n), mom = new Float64Array(n), minDscr = new Float64Array(n);
    const ebitda = [0, 1, 2, 3, 4].map(() => new Float64Array(n));
    let shortfall = 0, negEquity = 0;
    const mult = {};
    for (let i = 0; i < n; i++) {
      let op = pathOp(i), deal = K.deal;
      if (withPlan) {
        const scale = op.revenue.map((r, t) => r / SIM.medRev[t]);
        for (const k of Object.keys(SIM.mult)) mult[k] = SIM.mult[k][i];
        const lr = applyLevers(op, deal, values, on, mult, scale);
        op = lr.op; deal = lr.deal;
      }
      const r = run(op, deal, false);
      irr[i] = r.irr; mom[i] = r.mom; minDscr[i] = r.min_dscr;
      for (let t = 0; t < T; t++) ebitda[t][i] = r.ebitda_pre[t];
      if (r.cash_shortfall) shortfall++;
      if (r.equity_exit <= 0) negEquity++;
    }
    return { n, irr, mom, minDscr, ebitda, shortfall: shortfall / n, negEquity: negEquity / n };
  }

  // Mismas métricas que analysis.risk_summary, más las bandas de EBITDA y el histograma de la TIR.
  function riskSummary(sim) {
    const share = (a, f) => { let c = 0; for (const x of a) if (f(x)) c++; return c / a.length; };
    const [irrP10, irrMed, irrP90] = quantiles(sim.irr, [10, 50, 90]);
    const eb = sim.ebitda.map((col) => quantiles(col, [10, 50, 90]));
    return {
      irr_median: irrMed, irr_p10: irrP10, irr_p90: irrP90, mom_median: median(sim.mom),
      p_irr_neg: share(sim.irr, (x) => x < 0), p_irr_15: share(sim.irr, (x) => x >= 0.15),
      p_irr_20: share(sim.irr, (x) => x >= 0.20),
      p_dscr_12: share(sim.minDscr, (x) => x < 1.2), p_dscr_10: share(sim.minDscr, (x) => x < 1.0),
      p_shortfall: sim.shortfall, p_neg_equity: sim.negEquity,
      ebitda_p10: eb.map((q) => q[0]), ebitda_p50: eb.map((q) => q[1]), ebitda_p90: eb.map((q) => q[2]),
      ebitda2030_median: eb[T - 1][1], irr_hist: histogram(sim.irr, -0.10, 0.30, 0.01),
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

  // Columna D19:D62 de la hoja Palancas, lista para pegar en Excel (una línea por fila).
  function excelColumn(values, on, decimalSep = ",") {
    const lines = [];
    const num = (x) => {
      const s = String(Number(x.toPrecision(15)));
      return decimalSep === "," ? s.replace(".", ",") : s;
    };
    K.levers.forEach((lv, i) => {
      lines.push(on[lv.key] ? "1" : "0");
      for (const p of lv.params) lines.push(num(values[lv.key][p.key]));
      if (i < K.levers.length - 1) lines.push("");
    });
    return lines.join("\n");
  }

  // Lee la columna D19:D62 copiada de Excel o del propio dashboard. decimalSep es el separador decimal de
  // ese Excel; el otro signo se toma como separador de miles. Excel copia lo que se ve: «17,0 %», «7.500».
  function parseColumn(text, decimalSep = ",") {
    const lines = text.replace(/\r\n?/g, "\n").split("\n");
    while (lines.length && !lines[lines.length - 1].trim()) lines.pop();
    const values = defaults(), on = {}, errors = [];
    const expected = [];
    K.levers.forEach((lv, i) => {
      expected.push({ lever: lv, param: null });
      for (const p of lv.params) expected.push({ lever: lv, param: p });
      if (i < K.levers.length - 1) expected.push(null);
    });
    const first = K.levers[0].row;
    if (lines.length !== expected.length) {
      return { errors: [`Se esperaban ${expected.length} filas (D${first}:D${first + expected.length - 1}) y hay ${lines.length}.`] };
    }
    const toNumber = (s) => {
      let x = s.replace(/[\s  ]/g, "");
      const pct = x.endsWith("%");
      if (pct) x = x.slice(0, -1);
      const thousands = decimalSep === "," ? "." : ",";
      x = x.split(thousands).join("").replace(decimalSep, ".");
      if (!/^[-+]?\d*\.?\d+(e[-+]?\d+)?$/i.test(x)) return NaN;
      return pct ? Number(x) / 100 : Number(x);
    };
    lines.forEach((line, i) => {
      const e = expected[i], s = line.trim(), row = first + i;
      if (e === null) { if (s) errors.push(`D${row} debería estar vacía.`); return; }
      const v = toNumber(s);
      if (!Number.isFinite(v)) { errors.push(`D${row}: «${s}» no es un número.`); return; }
      if (e.param === null) {
        if (v !== 0 && v !== 1) errors.push(`D${row}: el interruptor de ${e.lever.name} debe ser 0 o 1.`);
        on[e.lever.key] = v === 1;
        return;
      }
      const p = e.param;
      if (p.options && !p.options.includes(v)) errors.push(`D${row}: el año debe ser ${p.options.join(", ")}.`);
      else if (p.edges && (v < p.edges[0] - 1e-12 || v > p.edges[4] + 1e-12)) {
        errors.push(`D${row}: ${p.label} fuera de rango (${p.edges[0]} a ${p.edges[4]}).`);
      }
      values[e.lever.key][p.key] = v;
    });
    return { values, on, errors };
  }

  return { init, run, applyLevers, runCase, valueBridge, caseOp, shapley, simulate, riskSummary, sourcesAndUses, entryMultiple,
           band, defaults, bandValues, excelColumn, parseColumn, quantiles, percentile, median, histogram, BANDS,
           get K() { return K; }, get SIM() { return SIM; } };
})();

if (typeof globalThis !== "undefined") globalThis.Motor = Motor;
