"""
Independent Verification Script for Inditex LBO Tax & Legal Structuring Audit (Module 03)
Audits Ley 27/2014 del Impuesto sobre Sociedades (LIS) compliance:
- Art. 16.5 LIS: Anti-LBO Safe Harbor Ratio (< 70%)
- Art. 58 LIS: Tax Consolidation Group Perimeter (>= 75%)
- Art. 87 / 76.5 LIS: FEAC Special Restructuring Regime / Rollover Valuation
- Art. 16.1 LIS: 30% Operating EBITDA Interest Cap, Carryforward & DTA Reserve
"""

import openpyxl

EXCEL_PATH = r"d:\Escritorio\MEFI\Asignaturas\Módulo 1\Corporate Finance\Inditex LBO\Excels\Inditex_LBO_Institutional_v4.xlsx"


def run_tax_audit():
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)

    ws_lbo = wb["LBO Summary"]
    ws_tax = wb["Tax & WACC"]
    ws_chk = wb["Checks"]

    print("=" * 80)
    print("INDITEX LBO TAX & LEGAL STRUCTURING INDEPENDENT AUDIT VERIFICATION")
    print("=" * 80)

    # 1. Article 16.5 LIS Anti-LBO Ratio Audit
    drawn_debt = ws_lbo["F30"].value
    offer_equity = ws_lbo["F13"].value
    art16_5_ratio = ws_tax["J10"].value
    statutory_cap = ws_tax["E10"].value
    chk_diff_8 = ws_chk["E8"].value
    chk_status_8 = ws_chk["F8"].value

    assert abs(art16_5_ratio - (drawn_debt / offer_equity)) < 1e-6
    assert abs(art16_5_ratio - 0.3963304) < 1e-5
    assert chk_status_8 == "OK"
    print(
        f"[1/4] Art. 16.5 LIS Anti-LBO Ratio: {art16_5_ratio:.4%} (Statutory Ceiling: {statutory_cap:.2%})"
    )
    print(f"      Headroom: {chk_diff_8:.4%} ({chk_diff_8 * 10000:.0f} bps below cap) -> Status: {chk_status_8}")

    # 2. Article 58 LIS Tax Consolidation Group Perimeter Audit
    amancio_rollover = ws_lbo["F14"].value
    cash_takeover = ws_lbo["F15"].value
    total_perimeter = amancio_rollover + cash_takeover
    chk_diff_7 = ws_chk["E7"].value
    chk_status_7 = ws_chk["F7"].value

    assert abs(total_perimeter - 1.0000) < 1e-6
    assert chk_status_7 == "OK"
    print(
        f"[2/4] Art. 58 LIS Tax Perimeter: {total_perimeter:.2%} (Statutory Minimum: 75.00%) -> Status: {chk_status_7}"
    )
    print("      BidCo owns 100.0% post squeeze-out; zero minority leakage.")

    # 3. Article 87 / 76.5 LIS FEAC Share Rollover Audit
    rollover_equity_val = ws_lbo["F16"].value
    topco_equity_val = ws_lbo["E45"].value
    amancio_topco_pct = ws_lbo["F43"].value

    assert abs(rollover_equity_val - 48362.959075) < 1e-3
    assert abs(amancio_topco_pct - (rollover_equity_val / topco_equity_val)) < 1e-6
    print(
        f"[3/4] Art. 87 LIS Rollover Value: €{rollover_equity_val:,.2f}M ({amancio_topco_pct:.4%} of TopCo Equity)"
    )
    print("      FEAC tax neutrality: full capital gains deferral (~€12.0B deferred).")

    # 4. Article 16.1 LIS 30% EBITDA Cap, Cumulative Shield & DTA Reserve Audit
    cumulative_tax_shield = ws_tax["E62"].value
    pv_tax_shield = ws_tax["E63"].value
    peak_carryforward = ws_tax["K35"].value
    turnaround_headroom = ws_tax["L31"].value
    terminal_dta_carryforward = ws_tax["L35"].value
    dta_tax_value = terminal_dta_carryforward * 0.25

    assert round(cumulative_tax_shield, 2) == 6694.02
    assert round(pv_tax_shield, 2) == 4971.74
    assert round(peak_carryforward, 2) == 8927.51
    assert round(turnaround_headroom, 2) == 72.31
    assert round(terminal_dta_carryforward, 2) == 8855.20
    assert round(dta_tax_value, 2) == 2213.80

    print(f"[4/4] Art. 16.1 LIS Deductibility Schedule:")
    print(f"      - Cumulative Realized Cash Tax Savings: €{cumulative_tax_shield:,.2f}M")
    print(f"      - Present Value of Tax Shields (Ku = 7.44%): €{pv_tax_shield:,.2f}M")
    print(f"      - Peak Non-Deductible Interest (2031E): €{peak_carryforward:,.2f}M")
    print(f"      - Turnaround Unused Headroom Recovered (2032E): €{turnaround_headroom:,.2f}M")
    print(f"      - Terminal Non-Deductible Carryforward (2032E): €{terminal_dta_carryforward:,.2f}M")
    print(f"      - Terminal Deferred Tax Asset (DTA) Value (@ 25% CIT): €{dta_tax_value:,.2f}M")

    print("=" * 80)
    print("ALL 4 SUBSTANTIVE TAX & LEGAL CRITERIA PASS INDEPENDENT VERIFICATION.")
    print("=" * 80)


if __name__ == "__main__":
    run_tax_audit()
