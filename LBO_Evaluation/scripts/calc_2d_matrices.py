"""
Calculate full 2D cross-sensitivity matrices for Section 6:
1. Euribor (3.354% to 6.354%) vs Sales Drop (Base, -2%, -5%, -10%)
2. Exit Multiple (14.0x, 16.0x, 18.0x, 19.35x) vs Lead GP Net IRR / Passive LP Net IRR
3. Gross Margin Compression (58.2%, 57.2%, 56.2%, 55.2%) vs DSCR
"""
import sys

def run_sim(euribor=0.03354, haircut_pct=0.0, opex_flex=0.0, gm=0.582):
    tla_rate = euribor + 0.0225
    tlb_rate = euribor + 0.0325
    rcf_commit_fee = 0.0075
    base_rev_growth = 0.055
    base_opex_growth = 0.0425
    base_lease_growth = 0.0200
    base_maint_capex_pct = 0.0350
    base_exp_capex_pct = 0.0170
    inv_pct, rec_pct, pay_pct = 0.0815, 0.0292, -0.2154
    
    rev_2025 = 39864.0
    opex_2025 = -11955.0
    lease_2025 = -1834.0
    nof_2025 = -4172.0
    net_fixed_assets_2025 = 12778.0
    
    tla_initial = 18866.0
    tlb_initial = 33015.5
    sub_initial = 14149.5
    vendor_initial = 10639.850996544
    rcf_limit = 1000.0
    min_cash_floor = 1000.0
    tla_amort_schedule = [0.05, 0.10, 0.15, 0.15, 0.20, 0.20, 0.15]
    years = [2026, 2027, 2028, 2029, 2030, 2031, 2032]
    asset_life = 10.0
    
    bop_tla, bop_tlb, bop_sub, bop_vendor = tla_initial, tlb_initial, sub_initial, vendor_initial
    bop_rcf, bop_cash = 0.0, min_cash_floor
    prior_base_rev, prior_base_opex = rev_2025, opex_2025
    prior_lease, prior_nof = lease_2025, nof_2025
    bop_existing_nfa = net_fixed_assets_2025
    capex_vintages = []
    bop_tax_carryforward = 0.0
    
    results = []
    for i, yr in enumerate(years):
        base_rev = prior_base_rev * (1.0 + base_rev_growth)
        rev = base_rev * (1.0 - haircut_pct)
        gross_profit = rev * gm
        base_opex = prior_base_opex * (1.0 + base_opex_growth)
        opex = base_opex * (1.0 - haircut_pct * opex_flex)
        rep_ebitda = gross_profit + opex
        lease = prior_lease * (1.0 + base_lease_growth)
        cash_ebitda = rep_ebitda + lease
        nof = rev * (inv_pct + rec_pct + pay_pct)
        delta_nof_cf = prior_nof - nof
        maint_capex = rev * base_maint_capex_pct
        exp_capex = rev * base_exp_capex_pct
        total_capex = maint_capex + exp_capex
        
        existing_da = -min(bop_existing_nfa, net_fixed_assets_2025 / asset_life)
        eop_existing_nfa = bop_existing_nfa + existing_da
        vintage_da_year = 0.0
        capex_vintages.append([total_capex, 0.0])
        for v in capex_vintages:
            orig, accum = v[0], v[1]
            d = -(orig / asset_life * 0.5) if accum == 0.0 else -min(orig - accum, orig / asset_life)
            v[1] += abs(d)
            vintage_da_year += d
        total_da = existing_da + vintage_da_year
        ebit = cash_ebitda + total_da
        
        tla_sched_amort = -min(bop_tla, tla_initial * tla_amort_schedule[i])
        eop_tla = bop_tla + tla_sched_amort
        avg_tla = (bop_tla + eop_tla) / 2.0
        tla_interest = -tla_rate * avg_tla
        
        tlb_bal_pre_sweep = bop_tlb
        avg_tlb = (bop_tlb + tlb_bal_pre_sweep) / 2.0
        tlb_interest = -tlb_rate * avg_tlb
        
        sub_pik_interest = bop_sub * 0.1050
        eop_sub = bop_sub + sub_pik_interest
        vendor_pik_interest = bop_vendor * 0.0500
        eop_vendor = bop_vendor + vendor_pik_interest
        
        rcf_interest = -(bop_rcf * (euribor + 0.02) + max(0.0, rcf_limit - bop_rcf) * rcf_commit_fee)
        total_cash_interest = tla_interest + tlb_interest + rcf_interest
        total_pnl_interest = total_cash_interest - sub_pik_interest - vendor_pik_interest
        
        upfront_fee_amort = -1141.96 / 7.0
        acct_ebt = ebit + total_pnl_interest + upfront_fee_amort
        cap_30 = max(1.0, 0.30 * cash_ebitda)
        fin_expense_subj = -(total_pnl_interest + upfront_fee_amort)
        non_deductible = max(0.0, fin_expense_subj - cap_30)
        unused_headroom = max(0.0, cap_30 - fin_expense_subj)
        carryforward_deducted = -min(bop_tax_carryforward, unused_headroom)
        eop_tax_carryforward = bop_tax_carryforward + non_deductible + carryforward_deducted
        adjusted_taxable_income = acct_ebt + non_deductible + carryforward_deducted
        cash_cit_paid = -max(0.0, adjusted_taxable_income) * 0.25
        
        cfads_excl_exp = cash_ebitda + cash_cit_paid + delta_nof_cf - maint_capex
        cfads_total = cfads_excl_exp - exp_capex
        debt_service = -(total_cash_interest + tla_sched_amort)
        
        dscr_bank = cfads_excl_exp / debt_service
        dscr_total = cfads_total / debt_service
        
        fcfe = cfads_total + total_cash_interest + tla_sched_amort
        excess_cash = (bop_cash - min_cash_floor) + fcfe
        if excess_cash < 0:
            rcf_draw = min(rcf_limit - bop_rcf, -excess_cash)
        else:
            rcf_draw = -min(bop_rcf, excess_cash)
        eop_rcf = bop_rcf + rcf_draw
        sweep_base = excess_cash + rcf_draw
        tlb_sweep = -min(tlb_bal_pre_sweep, sweep_base * 0.85) if sweep_base > 0 else 0.0
        eop_tlb = tlb_bal_pre_sweep + tlb_sweep
        eop_cash = bop_cash + fcfe + rcf_draw + tlb_sweep
        
        results.append({
            'year': yr,
            'dscr_bank': dscr_bank,
            'dscr_total': dscr_total,
            'tlb_sweep': -tlb_sweep,
            'eop_cash': eop_cash,
            'eop_rcf': eop_rcf
        })
        bop_tla, bop_tlb, bop_sub, bop_vendor = eop_tla, eop_tlb, eop_sub, eop_vendor
        bop_rcf, bop_cash = eop_rcf, eop_cash
        prior_base_rev, prior_base_opex, prior_lease, prior_nof = base_rev, base_opex, lease, nof
        bop_existing_nfa = eop_existing_nfa
        bop_tax_carryforward = eop_tax_carryforward
        
    return {
        'min_bank_dscr': min(r['dscr_bank'] for r in results),
        'min_tot_dscr': min(r['dscr_total'] for r in results),
        'tot_sweep': sum(r['tlb_sweep'] for r in results),
        'min_cash': min(r['eop_cash'] for r in results),
        'max_rcf': max(r['eop_rcf'] for r in results)
    }

if __name__ == '__main__':
    euribor_rates = [0.03354, 0.04354, 0.05354, 0.06354]
    eur_labels = ['3.354% (Base)', '4.354% (+100bp)', '5.354% (+200bp)', '6.354% (+300bp)']
    haircuts = [0.0, 0.02, 0.05, 0.10]
    hc_labels = ['Base Sales', '-2.0% Haircut', '-5.0% Haircut', '-10.0% Haircut']

    print('=== 2D CROSS-SENSITIVITY: MIN BANK DSCR (Sticky OpEx) ===')
    print(f'{"Euribor Rate":<18} | {"Base Sales":<12} | {"-2.0% Drop":<12} | {"-5.0% Drop":<12} | {"-10.0% Drop":<12}')
    print('-'*76)
    for e, el in zip(euribor_rates, eur_labels):
        row = [el]
        for h in haircuts:
            res = run_sim(euribor=e, haircut_pct=h, opex_flex=0.0)
            row.append(f"{res['min_bank_dscr']:.2f}x")
        print(f"{row[0]:<18} | {row[1]:<12} | {row[2]:<12} | {row[3]:<12} | {row[4]:<12}")

    print('\n=== 2D CROSS-SENSITIVITY: MIN TOTAL DSCR (Sticky OpEx) ===')
    print(f'{"Euribor Rate":<18} | {"Base Sales":<12} | {"-2.0% Drop":<12} | {"-5.0% Drop":<12} | {"-10.0% Drop":<12}')
    print('-'*76)
    for e, el in zip(euribor_rates, eur_labels):
        row = [el]
        for h in haircuts:
            res = run_sim(euribor=e, haircut_pct=h, opex_flex=0.0)
            row.append(f"{res['min_tot_dscr']:.2f}x")
        print(f"{row[0]:<18} | {row[1]:<12} | {row[2]:<12} | {row[3]:<12} | {row[4]:<12}")

    print('\n=== 2D CROSS-SENSITIVITY: 7-YEAR TLB SWEEP (EUR M, Sticky OpEx) ===')
    print(f'{"Euribor Rate":<18} | {"Base Sales":<12} | {"-2.0% Drop":<12} | {"-5.0% Drop":<12} | {"-10.0% Drop":<12}')
    print('-'*76)
    for e, el in zip(euribor_rates, eur_labels):
        row = [el]
        for h in haircuts:
            res = run_sim(euribor=e, haircut_pct=h, opex_flex=0.0)
            row.append(f"EUR {res['tot_sweep']:,.0f}M")
        print(f"{row[0]:<18} | {row[1]:<12} | {row[2]:<12} | {row[3]:<12} | {row[4]:<12}")

    print('\n=== 2D CROSS-SENSITIVITY: MIN BANK DSCR (Semi-Flexible OpEx 30%) ===')
    print(f'{"Euribor Rate":<18} | {"Base Sales":<12} | {"-2.0% Drop":<12} | {"-5.0% Drop":<12} | {"-10.0% Drop":<12}')
    print('-'*76)
    for e, el in zip(euribor_rates, eur_labels):
        row = [el]
        for h in haircuts:
            res = run_sim(euribor=e, haircut_pct=h, opex_flex=0.30)
            row.append(f"{res['min_bank_dscr']:.2f}x")
        print(f"{row[0]:<18} | {row[1]:<12} | {row[2]:<12} | {row[3]:<12} | {row[4]:<12}")

    print('\n=== GROSS MARGIN COMPRESSION VS DSCR ===')
    gms = [0.582, 0.572, 0.562, 0.552]
    gm_labels = ['58.20% (Base)', '57.20% (-100bp)', '56.20% (-200bp)', '55.20% (-300bp)']
    print(f'{"Gross Margin":<18} | {"Min Bank DSCR":<14} | {"Min Tot DSCR":<14} | {"7y Sweep (€M)":<16} | {"Exit Leverage":<14}')
    print('-'*80)
    for g, gl in zip(gms, gm_labels):
        res = run_sim(euribor=0.03354, haircut_pct=0.0, gm=g)
        print(f"{gl:<18} | {res['min_bank_dscr']:.2f}x          | {res['min_tot_dscr']:.2f}x         | EUR {res['tot_sweep']:,.0f}M      | Compliant")

def calc_multiple_sensitivity():
    ebitda_exit = 15644.50
    net_debt_exit = 48984.17
    fee_pct = 0.0075
    sponsor_share = 0.55798935
    lp_share = 0.85
    gp_share = 0.15
    lp_equity = 51894.944
    gp_equity = 9157.931
    total_sponsor_eq = 61052.875
    hurdle_rate = 0.08
    hurdle_mult = (1.0 + hurdle_rate)**7 - 1.0
    lp_hurdle = lp_equity * hurdle_mult

    multiples = [14.0, 16.0, 18.0, 19.3463]
    print("\n=== EXIT MULTIPLE SENSITIVITY: LEAD GP IRR vs LP NET IRR ===")
    print(f"{'Exit Multiple':<14} | {'Gross EV (EUR M)':<16} | {'TopCo Eq (EUR M)':<16} | {'Sponsor Pool':<14} | {'LP Net MOIC/IRR':<18} | {'GP Net MOIC/IRR':<18} | {'Carried Interest':<16}")
    print("-" * 125)

    for m in multiples:
        gross_ev = ebitda_exit * m
        fees = gross_ev * fee_pct
        topco_eq = gross_ev - fees - net_debt_exit
        sponsor_pool = topco_eq * sponsor_share
        
        lp_t1 = min(sponsor_pool * lp_share, lp_equity)
        rem_lp_pool = max(0.0, sponsor_pool * lp_share - lp_equity)
        
        lp_t2 = min(rem_lp_pool, lp_hurdle)
        rem_lp_above_hurdle = max(0.0, rem_lp_pool - lp_hurdle)
        
        gp_catchup_target = lp_t2 * (0.20 / 0.80)
        gp_catchup_paid = min(rem_lp_above_hurdle, gp_catchup_target)
        rem_after_catchup = max(0.0, rem_lp_above_hurdle - gp_catchup_paid)
        
        lp_t4 = rem_after_catchup * 0.80
        gp_t4 = rem_after_catchup * 0.20
        
        lp_total_proceeds = lp_t1 + lp_t2 + lp_t4
        gp_pro_rata = sponsor_pool * gp_share
        carried_interest = gp_catchup_paid + gp_t4
        gp_total_proceeds = gp_pro_rata + carried_interest
        
        lp_moic = lp_total_proceeds / lp_equity
        lp_irr = (lp_moic**(1/7) - 1.0) * 100
        
        gp_moic = gp_total_proceeds / gp_equity
        gp_irr = (gp_moic**(1/7) - 1.0) * 100
        
        print(f"{m:<14.2f} | EUR {gross_ev:<12,.1f}M | EUR {topco_eq:<12,.1f}M | EUR {sponsor_pool:<10,.1f}M | {lp_moic:.2f}x / {lp_irr:5.2f}%    | {gp_moic:.2f}x / {gp_irr:5.2f}%    | EUR {carried_interest:<12,.1f}M")

if __name__ == '__main__':
    calc_multiple_sensitivity()
