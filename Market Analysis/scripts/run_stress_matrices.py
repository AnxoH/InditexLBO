"""
Comprehensive Stress-Testing Analysis Script
Generates detailed institutional sensitivity matrices for R2 report:
1. Euribor Stress Matrix (Base, +100 bps, +200 bps, +300 bps)
2. Revenue Stress Matrix (Base, -2%, -5%, -10% level drop)
3. Gross Margin Compression Matrix (Base 58.2%, -100 bps, -200 bps, -300 bps)
4. Expansion Capex Overrun Matrix (Base, +10%, +20%, +30%)
5. Combined Macro Stress Scenarios (Base, Moderate, Severe, Extreme)
"""
import sys
from run_stress_testing import run_lbo_simulation

def analyze_scenario(euribor_shock=0.0, 
                     rev_growth_shock=0.0, 
                     gross_margin_shock=0.0, 
                     expansion_capex_shock=0.0,
                     name="Scenario"):
    results = run_lbo_simulation(euribor_shock, rev_growth_shock, gross_margin_shock, expansion_capex_shock, name)
    
    # Key aggregate metrics:
    min_bank_dscr = min(r['dscr_bank'] for r in results)
    min_bank_dscr_yr = [r['year'] for r in results if r['dscr_bank'] == min_bank_dscr][0]
    
    min_total_dscr = min(r['dscr_total'] for r in results)
    min_total_dscr_yr = [r['year'] for r in results if r['dscr_total'] == min_total_dscr][0]
    
    min_icr_cash = min(r['icr_cash'] for r in results)
    max_icr_cash = max(r['icr_cash'] for r in results)
    
    min_icr_ebit = min(r['icr_ebit'] for r in results)
    max_icr_ebit = max(r['icr_ebit'] for r in results)
    
    tot_sweep = sum(r['tlb_sweep'] for r in results)
    min_cash = min(r['eop_cash'] for r in results)
    max_rcf_drawn = max(r['rcf_drawn'] for r in results)
    
    final_net_debt = results[-1]['eop_total_net']
    final_leverage = results[-1]['sfa_leverage']
    
    # Check covenant adherence and constraints (DSCR >= 1.25, Cash >= 1000)
    dscr_covenant_compliant = min_bank_dscr >= 1.25
    cash_floor_compliant = min_cash >= 999.99
    
    return {
        'name': name,
        'euribor': 0.03354 + euribor_shock,
        'min_bank_dscr': min_bank_dscr,
        'min_bank_dscr_yr': min_bank_dscr_yr,
        'min_total_dscr': min_total_dscr,
        'min_total_dscr_yr': min_total_dscr_yr,
        'min_icr_cash': min_icr_cash,
        'max_icr_cash': max_icr_cash,
        'min_icr_ebit': min_icr_ebit,
        'max_icr_ebit': max_icr_ebit,
        'tot_sweep': tot_sweep,
        'min_cash': min_cash,
        'max_rcf_drawn': max_rcf_drawn,
        'final_net_debt': final_net_debt,
        'final_leverage': final_leverage,
        'dscr_compliant': dscr_covenant_compliant,
        'cash_compliant': cash_floor_compliant,
        'yearly': results
    }

def print_summary_table(scenarios):
    headers = [
        "Scenario", "Euribor", "Min Bank DSCR", "Min Tot DSCR", 
        "ICR Range (Cash)", "Tot TLB Sweep (€m)", "Min Cash (€m)", "Max RCF Draw", "Exit Lev (2032)", "Status"
    ]
    print(f"{headers[0]:<25} | {headers[1]:<8} | {headers[2]:<14} | {headers[3]:<14} | {headers[4]:<17} | {headers[5]:<18} | {headers[6]:<14} | {headers[7]:<12} | {headers[8]:<14} | {headers[9]:<10}")
    print("-" * 165)
    for s in scenarios:
        icr_str = f"{s['min_icr_cash']:.2f}x - {s['max_icr_cash']:.2f}x"
        bank_dscr_str = f"{s['min_bank_dscr']:.2f}x ({s['min_bank_dscr_yr']})"
        tot_dscr_str = f"{s['min_total_dscr']:.2f}x ({s['min_total_dscr_yr']})"
        eur_str = f"{s['euribor']*100:.2f}%"
        status = "PASS" if (s['dscr_compliant'] and s['cash_compliant']) else "BREACH"
        print(f"{s['name']:<25} | {eur_str:<8} | {bank_dscr_str:<14} | {tot_dscr_str:<14} | {icr_str:<17} | {s['tot_sweep']:<18.1f} | {s['min_cash']:<14.1f} | {s['max_rcf_drawn']:<12.1f} | {s['final_leverage']:<14.2f}x | {status:<10}")

if __name__ == '__main__':
    # 1. Euribor Sensitivity
    euribor_scenarios = [
        analyze_scenario(euribor_shock=0.0, name="Base Case (3.354%)"),
        analyze_scenario(euribor_shock=0.01, name="Euribor +100 bps (4.354%)"),
        analyze_scenario(euribor_shock=0.02, name="Euribor +200 bps (5.354%)"),
        analyze_scenario(euribor_shock=0.03, name="Euribor +300 bps (6.354%)"),
    ]
    print("\n============================== EURIBOR SENSITIVITY ==============================")
    print_summary_table(euribor_scenarios)
    
    # 2. Revenue Growth Sensitivity
    rev_scenarios = [
        analyze_scenario(name="Base Case (5.50% YoY)"),
        analyze_scenario(rev_growth_shock=-0.02, name="Rev Growth -200 bps (3.5%)"),
        analyze_scenario(rev_growth_shock=-0.05, name="Rev Growth -500 bps (0.5%)"),
        analyze_scenario(rev_growth_shock=-0.0775, name="Rev Growth Bear (2.25%)"),
    ]
    print("\n============================== REVENUE GROWTH SENSITIVITY ==============================")
    print_summary_table(rev_scenarios)
    
    # 3. Gross Margin Compression Sensitivity
    margin_scenarios = [
        analyze_scenario(name="Base Case (58.20% GM)"),
        analyze_scenario(gross_margin_shock=-0.01, name="Gross Margin -100 bps (57.2%)"),
        analyze_scenario(gross_margin_shock=-0.02, name="Gross Margin -200 bps (56.2%)"),
        analyze_scenario(gross_margin_shock=-0.03, name="Gross Margin -300 bps (55.2%)"),
    ]
    print("\n============================== MARGIN COMPRESSION SENSITIVITY ==============================")
    print_summary_table(margin_scenarios)
    
    # 4. Capex Overrun Sensitivity
    capex_scenarios = [
        analyze_scenario(name="Base Case (1.70% Exp Capex)"),
        analyze_scenario(expansion_capex_shock=0.10, name="Expansion Capex +10% Overrun"),
        analyze_scenario(expansion_capex_shock=0.20, name="Expansion Capex +20% Overrun"),
        analyze_scenario(expansion_capex_shock=0.30, name="Expansion Capex +30% Overrun"),
    ]
    print("\n============================== CAPEX OVERRUN SENSITIVITY ==============================")
    print_summary_table(capex_scenarios)

    # 5. Combined Macro Stress Scenarios
    macro_scenarios = [
        analyze_scenario(name="Base Case"),
        analyze_scenario(euribor_shock=0.01, rev_growth_shock=-0.02, gross_margin_shock=-0.005, name="Mild Headwinds"),
        analyze_scenario(euribor_shock=0.02, rev_growth_shock=-0.035, gross_margin_shock=-0.01, expansion_capex_shock=0.15, name="Stagflationary Shock"),
        analyze_scenario(euribor_shock=0.03, rev_growth_shock=-0.05, gross_margin_shock=-0.02, expansion_capex_shock=0.25, name="Severe Downside Crisis"),
    ]
    print("\n============================== COMBINED STRESS SCENARIOS ==============================")
    print_summary_table(macro_scenarios)
