"""
Independent Quantitative Stress-Testing Engine for Inditex LBO Model (v4)
Recalculates CFADS, Debt Service, DSCR, ICR, Cash Sweep, and Liquidity Floor
under parameter shocks:
- Euribor: Base (3.354%), +100 bps, +200 bps, +300 bps
- Revenue: Base, -2%, -5%, -10%
- Margin Compression: -100 bps, -200 bps Gross Margin
- Capex Overruns: +10%, +20%, +30% Expansion Capex
"""
import copy

def run_lbo_simulation(euribor_shock=0.0, 
                       rev_growth_shock=0.0, 
                       gross_margin_shock=0.0, 
                       expansion_capex_shock=0.0,
                       scenario_name="Base"):
    # Base parameters from Active Case & Debt & Covenants
    base_euribor = 0.03354 + euribor_shock
    tla_spread = 0.0225
    tlb_spread = 0.0325
    rcf_margin = 0.0200
    rcf_commit_fee = 0.0075
    
    tla_rate = base_euribor + tla_spread
    tlb_rate = base_euribor + tlb_spread
    sub_pik_rate = 0.1050
    vendor_pik_rate = 0.0500
    
    # Base operational drivers
    base_rev_growth = 0.055 + rev_growth_shock
    base_gross_margin = 0.582 + gross_margin_shock
    base_opex_growth = 0.0425
    base_lease_growth = 0.0200
    base_maint_capex_pct = 0.0350
    base_exp_capex_pct = 0.0170 * (1.0 + expansion_capex_shock)
    
    # NOF % of revenues
    inv_pct = 0.0815
    rec_pct = 0.0292
    pay_pct = -0.2154
    nof_pct = inv_pct + rec_pct + pay_pct # -0.1047
    
    # Starting values FY25A
    rev_2025 = 39864.0
    gross_profit_2025 = 23222.0
    cogs_2025 = -16642.0
    opex_2025 = -11955.0
    reported_ebitda_2025 = 11267.0
    lease_2025 = -1834.0
    cash_ebitda_2025 = 9433.0
    da_2025 = -1674.0
    ebit_2025 = 7759.0
    nof_2025 = -4172.0
    net_fixed_assets_2025 = 12778.0
    
    # Debt tranches closing 2025
    tla_initial = 18866.0
    tlb_initial = 33015.5
    sub_initial = 14149.5
    vendor_initial = 10639.850996544
    rcf_limit = 1000.0
    min_cash_floor = 1000.0
    
    # TLA amort schedule %
    tla_amort_schedule = [0.05, 0.10, 0.15, 0.15, 0.20, 0.20, 0.15]
    years = [2026, 2027, 2028, 2029, 2030, 2031, 2032]
    
    # Existing assets D&A
    asset_life = 10.0
    existing_da_annual = min_cash_floor # placeholder
    
    # Run annual projection
    results = []
    
    # State tracking
    bop_tla = tla_initial
    bop_tlb = tlb_initial
    bop_sub = sub_initial
    bop_vendor = vendor_initial
    bop_rcf = 0.0
    bop_cash = min_cash_floor
    prior_rev = rev_2025
    prior_opex = opex_2025
    prior_lease = lease_2025
    prior_nof = nof_2025
    
    bop_existing_nfa = net_fixed_assets_2025
    capex_vintages = [] # list of (capex_amt, yr_idx)
    
    bop_tax_carryforward = 0.0
    
    for i, yr in enumerate(years):
        # 1. P&L
        rev = prior_rev * (1.0 + base_rev_growth)
        gross_profit = rev * base_gross_margin
        cogs = gross_profit - rev
        opex = prior_opex * (1.0 + base_opex_growth)
        rep_ebitda = gross_profit + opex
        lease = prior_lease * (1.0 + base_lease_growth)
        cash_ebitda = rep_ebitda + lease # Pre-IFRS 16 Normalized Cash EBITDA
        
        # 2. Working Capital
        inv = rev * inv_pct
        rec = rev * rec_pct
        pay = rev * pay_pct
        nof = inv + rec + pay
        delta_nof_cf = prior_nof - nof # Cash inflow if positive
        
        # 3. Capex & D&A
        maint_capex = rev * base_maint_capex_pct
        exp_capex = rev * base_exp_capex_pct
        total_capex = maint_capex + exp_capex
        
        # D&A calculation
        existing_da = -min(bop_existing_nfa, net_fixed_assets_2025 / asset_life)
        eop_existing_nfa = bop_existing_nfa + existing_da
        
        # Vintage capex D&A
        vintage_da_year = 0.0
        # Add new capex
        capex_vintages.append([total_capex, 0.0]) # [orig_amt, accum_da]
        for v in capex_vintages:
            orig = v[0]
            accum = v[1]
            if accum == 0.0: # first year half-year convention
                d = -(orig / asset_life * 0.5)
            else:
                d = -min(orig - accum, orig / asset_life)
            v[1] += abs(d)
            vintage_da_year += d
            
        total_da = existing_da + vintage_da_year
        ebit = cash_ebitda + total_da
        
        # 4. Debt schedule & interest
        # TLA
        tla_sched_amort = -min(bop_tla, tla_initial * tla_amort_schedule[i])
        eop_tla = bop_tla + tla_sched_amort
        avg_tla = (bop_tla + eop_tla) / 2.0
        tla_interest = -tla_rate * avg_tla
        
        # TLB mandatory
        tlb_mand_amort = 0.0
        tlb_bal_pre_sweep = bop_tlb + tlb_mand_amort
        avg_tlb = (bop_tlb + tlb_bal_pre_sweep) / 2.0
        tlb_interest = -tlb_rate * avg_tlb
        
        # Subordinated PIK
        sub_pik_interest = bop_sub * sub_pik_rate
        eop_sub = bop_sub + sub_pik_interest
        sub_cash_interest = 0.0
        sub_pnl_interest = -sub_pik_interest
        
        # Vendor Loan PIK
        vendor_pik_interest = bop_vendor * vendor_pik_rate
        eop_vendor = bop_vendor + vendor_pik_interest
        vendor_cash_interest = 0.0
        vendor_pnl_interest = -vendor_pik_interest
        
        # RCF commitment fee
        rcf_interest = -(bop_rcf * (base_euribor + rcf_margin) + max(0.0, rcf_limit - bop_rcf) * rcf_commit_fee)
        
        total_cash_interest = tla_interest + tlb_interest + sub_cash_interest + vendor_cash_interest + rcf_interest
        total_pnl_interest = tla_interest + tlb_interest + sub_pnl_interest + vendor_pnl_interest + rcf_interest
        
        # 5. Taxes (Art. 16.1 LIS 30% EBITDA cap)
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
        
        # 6. CFADS & Debt Service
        cfads_excl_exp = cash_ebitda + cash_cit_paid + delta_nof_cf - maint_capex
        cfads_total = cfads_excl_exp - exp_capex
        
        mand_debt_amort = tla_sched_amort # negative
        debt_service = -(total_cash_interest + mand_debt_amort)
        
        dscr_bank = cfads_excl_exp / debt_service
        dscr_total = cfads_total / debt_service
        
        icr_cash = cash_ebitda / (-total_cash_interest)
        icr_ebit = ebit / (-total_cash_interest)
        
        # 7. Cash Flow to Equity & Sweep
        fcfe_after_debt_service = cfads_total + total_cash_interest + mand_debt_amort
        excess_cash_avail = (bop_cash - min_cash_floor) + fcfe_after_debt_service
        
        # RCF auto draw if excess cash < 0
        if excess_cash_avail < 0:
            rcf_draw = min(rcf_limit - bop_rcf, -excess_cash_avail)
        else:
            rcf_draw = -min(bop_rcf, excess_cash_avail)
        eop_rcf = bop_rcf + rcf_draw
        
        # Optional TLB Cash Sweep (85%)
        sweep_base = excess_cash_avail + rcf_draw
        if sweep_base > 0:
            tlb_sweep = -min(tlb_bal_pre_sweep, sweep_base * 0.85)
        else:
            tlb_sweep = 0.0
            
        eop_tlb = tlb_bal_pre_sweep + tlb_sweep
        net_cash_change = fcfe_after_debt_service + rcf_draw + tlb_sweep
        eop_cash = bop_cash + net_cash_change
        
        # SFA Leverage
        eop_senior_gross = eop_tla + eop_tlb + eop_rcf
        eop_total_gross = eop_senior_gross + eop_sub + eop_vendor
        eop_total_net = eop_total_gross - eop_cash
        sfa_leverage = eop_total_net / cash_ebitda
        
        # Store year result
        results.append({
            'year': yr,
            'rev': rev,
            'cash_ebitda': cash_ebitda,
            'ebit': ebit,
            'delta_nof': delta_nof_cf,
            'maint_capex': maint_capex,
            'exp_capex': exp_capex,
            'cit_paid': cash_cit_paid,
            'cfads_excl_exp': cfads_excl_exp,
            'cfads_total': cfads_total,
            'cash_interest': -total_cash_interest,
            'mand_amort': -mand_debt_amort,
            'debt_service': debt_service,
            'dscr_bank': dscr_bank,
            'dscr_total': dscr_total,
            'icr_cash': icr_cash,
            'icr_ebit': icr_ebit,
            'tlb_sweep': -tlb_sweep,
            'eop_cash': eop_cash,
            'eop_tla': eop_tla,
            'eop_tlb': eop_tlb,
            'eop_total_net': eop_total_net,
            'sfa_leverage': sfa_leverage,
            'rcf_drawn': eop_rcf
        })
        
        # Update BoP for next year
        bop_tla = eop_tla
        bop_tlb = eop_tlb
        bop_sub = eop_sub
        bop_vendor = eop_vendor
        bop_rcf = eop_rcf
        bop_cash = eop_cash
        prior_rev = rev
        prior_opex = opex
        prior_lease = lease
        prior_nof = nof
        bop_existing_nfa = eop_existing_nfa
        bop_tax_carryforward = eop_tax_carryforward

    return results

if __name__ == '__main__':
    res_base = run_lbo_simulation(scenario_name="Base")
    print(f"{'Year':<6} | {'CFADS Excl':<10} | {'CFADS Tot':<10} | {'Debt Serv':<10} | {'Bank DSCR':<10} | {'Tot DSCR':<10} | {'ICR Cash':<10} | {'ICR EBIT':<10} | {'TLB Sweep':<10} | {'EoP Cash':<10}")
    for r in res_base:
        print(f"{r['year']:<6} | {r['cfads_excl_exp']:<10.1f} | {r['cfads_total']:<10.1f} | {r['debt_service']:<10.1f} | {r['dscr_bank']:<10.2f} | {r['dscr_total']:<10.2f} | {r['icr_cash']:<10.2f} | {r['icr_ebit']:<10.2f} | {r['tlb_sweep']:<10.1f} | {r['eop_cash']:<10.1f}")
