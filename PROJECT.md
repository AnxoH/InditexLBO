# Project Context: Inditex LBO (`Project Galicia`)

## 1. Project Overview & Completed Milestones

This repository hosts the institutional-grade Leveraged Buyout (LBO) feasibility analysis, stochastic operating calibration, and financial model for **Industria de Diseño Textil, S.A. (Inditex / `BME: ITX`)**:

- **Definitive Financial Model ([`Excels/Inditex_LBO_Version_Definitiva.xlsx`](Excels/Inditex_LBO_Version_Definitiva.xlsx)) — COMPLETED**:
  - 6-tab dynamic Excel workbook (`LBO Summary`, `Active Case`, `Debt & Covenants`, `Tax & WACC`, `Checks`, `Data`).
  - Integrates the 4 operating scenarios (`1 = Base P50`, `2 = Bull P80`, `3 = Bear P20`, `4 = Bank P10`) derived from the ex-COVID Monte Carlo calibration and operational value-creation levers (`+160 bps` S&M efficiency, `+30 bps` Gross Margin).
  - Implements institutional credit and legal structuring: Pre-IFRS 16 Cash EBITDA separation, dynamic `MAX(1800, 4.5% Rev)` CapEx floor in Base/Bull, `25.0%` Amancio Ortega rollover under Art. 87 LIS tax neutrality, `80% / 20%` LP/GP co-investment waterfall (`10.0%` hurdle, `20.0%` carry), and Spanish Art. 16 LIS (`30%` Operating Profit) interest deductibility cap.
- **Workstream 1: Commercial & Strategic Due Diligence ([`Market Analysis/`](Market%20Analysis)) — COMPLETED**:
  - Full Stage 1 IC Memorandum ([`00_Inditex_Stage1_IC_Overview_McKinsey.pdf`](Market%20Analysis/00_Inditex_Stage1_IC_Overview_McKinsey.pdf)), 5 analytical modules, reconciled CSV datasets (`FY2022–FY2025`), and 36 automated verification tests.
- **Workstream 2: Historical Accounting & Working Capital Analysis ([`Contabilidad Inditex/`](Contabilidad%20Inditex)) — COMPLETED**:
  - 2013–2025 working capital (`FM` vs. negative `NOF`), `-51.02` day Cash Conversion Cycle, and IFRS 16 lease accounting analysis ([`Contabilidad Inditex/Informe_Inditex.pdf`](Contabilidad%20Inditex/Informe_Inditex.pdf)).
- **Workstream 3: Econometric Calibration, Monte Carlo & Value Creation Levers ([`Business Plan/`](Business%20Plan)) — COMPLETED (Standalone Calibration)**:
  - 2005–2025 econometric estimation, 20,000-path Monte Carlo simulation, 8 operational levers with Shapley value attribution, and interactive HTML/JS dashboard ([`Business Plan/output/Dashboard_palancas.html`](Business%20Plan/output/Dashboard_palancas.html)).

---

## 2. Future Work & Next Iteration Roadmap (`To-Do`)

The following items are scheduled for the next phase of repository refinement:

1. **`Business Plan/` Alignment & De-Noising**:
   - Refactor the standalone Python LBO vector engine (`Business Plan/bp/lbo.py`) and interactive HTML dashboard (`Business Plan/output/Dashboard_palancas.html`) so that their internal capital structure parameters match [`Excels/Inditex_LBO_Version_Definitiva.xlsx`](Excels/Inditex_LBO_Version_Definitiva.xlsx) (`25.0%` Ortega rollover, `80%/20%` LP/GP waterfall, `0%` cash / `5%` PIK Vendor Loan, dynamic `MAX(1800, 4.5% Rev)` CapEx floor, and ex-COVID baseline toggle), removing legacy references to the preliminary `Rollover50` template.
2. **Definitive Institutional Audit & Stress-Testing Report**:
   - Generate a new, comprehensive Multi-Agent IC Evaluation & Stress-Testing Memorandum audited directly against [`Excels/Inditex_LBO_Version_Definitiva.xlsx`](Excels/Inditex_LBO_Version_Definitiva.xlsx) across all 4 operating cases (`Base P50`, `Bull P80`, `Bear P20`, `Bank P10`), including updated 2D sensitivity grids, covenant headroom stress tests, and credit rating transition matrices.
