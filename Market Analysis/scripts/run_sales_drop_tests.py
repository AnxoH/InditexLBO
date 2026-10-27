"""
Detailed Sales Level Sensitivity Engine
Calculates the impact of -2%, -5%, and -10% revenue level haircuts
under both Sticky OpEx (conservative) and Semi-Flexible OpEx (realistic).
"""
import sys
import copy
from run_stress_testing import run_lbo_simulation

def run_sales_level_haircut(haircut_pct=0.0, opex_flexibility=0.0):
    # opex_flexibility: 0.0 = sticky opex (100% fixed vs base)
    #                   0.30 = 30% of opex varies with revenue (turnover rent, staffing)
    
    # Base parameters
    euribor = 0.03354
    tla_rate = euribor + 0.0225
    tlb_rate = euribor + 0.0325
    rcf_commit_fee = 0.0075
    
    base_rev_growth = 0.055
    base_gross_margin = 0.582
    base_opex_growth = 0.0425
    base_lease_growth = 0.0200
    base_maint_capex_pct = 0.0350
    base_exp_capex_pct = 0.0170
    
    inv_pct = 0.0815
    rec_pct = 0.0292
    pay_pct = -0.2154
    
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
    
    results = []
    bop_tla = tla_initial
    bop_tlb = tlb_initial
    bop_sub = sub_initial
    bop_vendor = vendor_initial
    bop_rcf = 0.0
    bop_cash = min_cash_floor
    prior_base_rev = rev_2025
    prior_base_opex = opex_2025
    prior_lease = lease_2025
    prior_nof = nof_2025
    bop_existing_nfa = net_fixed_assets_2025
    capex_vintages = []
    bop_tax_carryforward = 0.0
    
    for i, yr in enumerate(years):
        # Base rev and shocked rev
        base_rev = prior_base_rev * (1.0 + base_rev_growth)
        rev = base_rev * (1.0 - haircut_pct)
        
        gross_profit = rev * base_gross_margin
        
        # Base opex
        base_opex = prior_base_opex * (1.0 + base_opex_growth)
        # Shocked opex
        opex = base_opex * (1.0 - haircut_pct * opex_flexibility)
        
        rep_ebitda = gross_profit + opex
        lease = prior_lease * (1.0 + base_lease_growth)
        cash_ebitda = rep_ebitda + lease
        
        # NOF
        nof = rev * (inv_pct + rec_pct + pay_pct)
        delta_nof_cf = prior_nof - nof
        
        # Capex
        maint_capex = rev * base_maint_capex_pct
        exp_capex = rev * base_exp_capex_pct
        total_capex = maint_capex + exp_capex
        
        # D&A
        existing_da = -min(bop_existing_nfa, net_fixed_assets_2025 / asset_life)
        eop_existing_nfa = bop_existing_nfa + existing_da
        
        vintage_da_year = 0.0
        capex_vintages.append([total_capex, 0.0])
        for v in capex_vintages:
            orig = v[0]
            accum = v[1]
            if accum == 0.0:
                d = -(orig / asset_life * 0.5)
            else:
                d = -min(orig - accum, orig / asset_life)
            v[1] += abs(d)
            vintage_da_year += d
            
        total_da = existing_da + vintage_da_year
        ebit = cash_ebitda + total_da
        
        # Debt
        tla_sched_amort = -min(bop_tla, tla_initial * tla_amort_schedule[i])
        eop_tla = bop_tla + tla_sched_amort
        avg_tla = (bop_tla + eop_tla) / 2.0
        tla_interest = -tla_rate * avg_tla
        
        tlb_mand_amort = 0.0
        tlb_bal_pre_sweep = bop_tlb + tlb_mand_amort
        avg_tlb = (bop_tlb + tlb_bal_pre_sweep) / 2.0
        tlb_interest = -tlb_rate * avg_tlb
        
        sub_pik_interest = bop_sub * 0.1050
        eop_sub = bop_sub + sub_pik_interest
        vendor_pik_interest = bop_vendor * 0.0500
        eop_vendor = bop_vendor + vendor_pik_interest
        
        rcf_interest = -(bop_rcf * (euribor + 0.02) + max(0.0, rcf_limit - bop_rcf) * rcf_commit_fee)
        
        total_cash_interest = tla_interest + tlb_interest + rcf_interest
        total_pnl_interest = total_cash_interest - sub_pik_interest - vendor_pik_interest
        
        # Tax
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
        
        # CFADS & Debt service
        cfads_excl_exp = cash_ebitda + cash_cit_paid + delta_nof_cf - maint_capex
        cfads_total = cfads_excl_exp - exp_capex
        mand_debt_amort = tla_sched_amort
        debt_service = -(total_cash_interest + mand_debt_amort)
        
        dscr_bank = cfads_excl_exp / debt_service
        dscr_total = cfads_total / debt_service
        icr_cash = cash_ebitda / (-total_cash_interest)
        icr_ebit = ebit / (-total_cash_interest)
        
        fcfe_after_debt_service = cfads_total + total_cash_interest + mand_debt_amort
        excess_cash_avail = (bop_cash - min_cash_floor) + fcfe_after_debt_service
        
        if excess_cash_avail < 0:
            rcf_draw = min(rcf_limit - bop_rcf, -excess_cash_avail)
        else:
            rcf_draw = -min(bop_rcf, excess_cash_avail)
        eop_rcf = bop_rcf + rcf_draw
        
        sweep_base = excess_cash_avail + rcf_draw
        if sweep_base > 0:
            tlb_sweep = -min(tlb_bal_pre_sweep, sweep_base * 0.85)
        else:
            tlb_sweep = 0.0
            
        eop_tlb = tlb_bal_pre_sweep + tlb_sweep
        net_cash_change = fcfe_after_debt_service + rcf_draw + tlb_sweep
        eop_cash = bop_cash + net_cash_change
        
        eop_senior_gross = eop_tla + eop_tlb + eop_rcf
        eop_total_gross = eop_senior_gross + eop_sub + eop_vendor
        eop_total_net = eop_total_gross - eop_cash
        sfa_leverage = eop_total_net / cash_ebitda
        
        results.append({
            'year': yr,
            'rev': rev,
            'cash_ebitda': cash_ebitda,
            'ebit': ebit,
            'debt_service': debt_service,
            'dscr_bank': dscr_bank,
            'dscr_total': dscr_total,
            'icr_cash': icr_cash,
            'icr_ebit': icr_ebit,
            'tlb_sweep': -tlb_sweep,
            'eop_cash': eop_cash,
            'rcf_drawn': eop_rcf,
            'sfa_leverage': sfa_leverage
        })
        
        bop_tla = eop_tla
        bop_tlb = eop_tlb
        bop_sub = eop_sub
        bop_vendor = eop_vendor
        bop_rcf = eop_rcf
        bop_cash = eop_cash
        prior_base_rev = base_rev
        prior_base_opex = base_opex
        prior_lease = lease
        prior_nof = nof
        bop_existing_nfa = eop_existing_nfa
        bop_tax_carryforward = eop_tax_carryforward

    return results

if __name__ == '__main__':
    print("=== REVENUE LEVEL DROP SENSITIVITIES (STICKY OPEX) ===")
    for drop in [0.0, 0.02, 0.05, 0.10]:
        res = run_sales_level_haircut(haircut_pct=drop, opex_flexibility=0.0)
        min_bank = min(r['dscr_bank'] for r in res)
        min_tot = min(r['dscr_total'] for r in res)
        min_cash = min(r['eop_cash'] for r in res)
        max_rcf = max(r['rcf_drawn'] for r in res)
        tot_swp = sum(r['tlb_sweep'] for r in res)
        icr_min = min(r['icr_cash'] for r in res)
        icr_max = max(r['icr_cash'] for r in res)
        lev_exit = res[-1]['sfa_leverage']
        status = "COMPLIANT" if min_bank >= 1.25 and min_cash >= 1000 else "BREACH"
        print(f"Sales Drop -{drop*100:4.1f}% | Min Bank DSCR: {min_bank:.2f}x | Min Tot DSCR: {min_tot:.2f}x | ICR: {icr_min:.2f}x-{icr_max:.2f}x | Sweep: €{tot_swp:7.1f}M | Min Cash: €{min_cash:7.1f}M | RCF: €{max_rcf:4.1f}M | Exit Lev: {lev_exit:.2f}x | Status: {status}")

    print("\n=== REVENUE LEVEL DROP SENSITIVITIES (SEMI-FLEXIBLE OPEX: 30% Variable) ===")
    for drop in [0.0, 0.02, 0.05, 0.10]:
        res = run_sales_level_haircut(haircut_pct=drop, opex_flexibility=0.30)
        min_bank = min(r['dscr_bank'] for r in res)
        min_tot = min(r['dscr_total'] for r in res)
        min_cash = min(r['eop_cash'] for r in res)
        max_rcf = max(r['rcf_drawn'] for r in res)
        tot_swp = sum(r['tlb_sweep'] for r in res)
        icr_min = min(r['icr_cash'] for r in res)
        icr_max = max(r['icr_cash'] for r in res)
        lev_exit = res[-1]['sfa_leverage']
        status = "COMPLIANT" if min_bank >= 1.25 and min_cash >= 1000 else "BREACH"
        print(f"Sales Drop -{drop*100:4.1f}% | Min Bank DSCR: {min_bank:.2f}x | Min Tot DSCR: {min_tot:.2f}x | ICR: {icr_min:.2f}x-{icr_max:.2f}x | Sweep: €{tot_swp:7.1f}M | Min Cash: €{min_cash:7.1f}M | RCF: €{max_rcf:4.1f}M | Exit Lev: {lev_exit:.2f}x | Status: {status}")
