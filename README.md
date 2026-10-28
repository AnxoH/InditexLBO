# Project Galicia: Inditex S.A. LBO & Corporate Finance Analysis

Master Investment Committee (IC) Screening Memorandum, empirical financial reconciliations, and LBO modeling kit for **Industria de Diseño Textil, S.A. (Inditex, S.A.)** (BME: `ITX.MC`).

---

## 📌 Executive Summary

This repository contains the institutional Private Equity Stage 1 screening analysis and LBO feasibility evaluation for Inditex, S.A., conducted within the Corporate Finance framework (MEFI). The thesis investigates an Ortega Family rollover (64.35%) alongside a sponsor consortium take-private of the public free float (35.65%).

```
========================================================================================================================
                                    INDITEX STAGE 1 IC SCORECARD & TRANSACTION OVERVIEW
========================================================================================================================
 Market Capitalization:    €172.63B (@ €55.42/share)        Audited FY25 Net Sales:   €39,864M (+3.2% rep / +7.0% const FX)
 Enterprise Value (EV):    €169.80B (Market) / €167.60B     Audited FY25 Gross Margin: 58.3% (+130 bps vs FY22)
 Statutory Net Cash:       €10,958M (€10.96B cash/inv.)     Audited FY25 EBITDA:      €11,267M (28.3% margin)
 IFRS 16 Lease Debt:       €5,933M (€2,504M cash outflow)   Audited FY25 EBIT:        €7,997M (20.1% margin)
 Operating Working Capital: -€4,173M (-10.5% of sales)      Audited FY25 Net Income:  €6,220M (EPS €1.996)
 Group ROCE:               40.0% (Specialty brands 50-72%)  FY25 Free Cash Flow:      €4,686M (FCF Yield: 2.71%)
 Ownership & Control:      64.35% Ortega Family Control     Public Free Float:        35.65% (1,110.89M shares | ~€61.5B)
 Recommendation:           PROCEED TO STAGE 2 LBO MODEL     Proposed Deal Structure:  Consortium Take-Private of Float
========================================================================================================================
```

---

## 📂 Repository Structure

```tree
├── Annual Reports/
│   └── Transformed/                  # Audited FY22-FY25 reports converted to clean Markdown
│       ├── ConsolidatedReport_2022.md
│       ├── ConsolidatedReport_2023.md
│       ├── ConsolidatedReport_2024.md
│       └── ConsolidatedReport_2025.md
│
├── Business Plan/                         # Stochastic business plan, LBO engine & value-creation plan (Spanish; see its README)
│   ├── Guia_Business_Plan_desde_cero.pdf  # Start here: everything explained from scratch
│   ├── output/Dashboard_palancas.html     # Lever dashboard (open by double-clicking)
│   ├── Business_Plan_Inditex.ipynb        # Calibration, Monte Carlo and the four Excel cases
│   ├── Plan_de_creacion_de_valor.ipynb    # Value-creation plan read from the Excel's Palancas sheet
│   └── bp/, dashboard/, tests/            # Python model, JS engine, parity tests
│
├── Excels/
│   └── Inditex_LBO_Rollover50_BusinessPlan.xlsx  # Group LBO (50 % rollover) wired to the business plan
│
├── Market Analysis/
│   ├── 00_Inditex_Stage1_IC_Overview.md   # Master IC Stage 1 Screening Memo & Excel Kit
│   ├── STAGE_1_EXECUTION_PLAN.md          # Multi-agent architectural roadmap & QA protocol
│   │
│   ├── modules/                           # Deep-dive analytical modules
│   │   ├── 01_Market_Position.md          # Global market sizing, geography, format matrix
│   │   ├── 02_Business_Model_Moat.md      # Supply chain, proximity sourcing, negative NWC
│   │   ├── 03_Growth_and_Trajectory.md    # Post-pandemic trajectory, omnichannel, CapEx
│   │   ├── 04_Competitor_Benchmarking.md  # Inditex vs H&M, Fast Retailing, Shein, Temu
│   │   └── 05_Valuation_and_PE_Thesis.md  # Multiples, DCF benchmarks, LBO debt capacity
│   │
│   ├── data/                              # Reconciled empirical datasets
│   │   ├── inditex_kpis_2022_2025.csv     # Audited financial statement time series
│   │   ├── inditex_brands_breakdown.csv   # Brand-level sales and store footprint
│   │   ├── peer_benchmarking_table.csv    # Comparative multiples & operational KPIs
│   │   └── analyst_consensus_summary.csv  # Sell-side consensus & price target dispersion
│   │
│   ├── scripts/
│   │   └── extract_baseline_data.py       # Automated data extraction pipeline
│   │
│   └── tests/                             # Comprehensive automated verification suite
│       ├── run_all_tests.py               # Test runner
│       ├── test_financial_oracle.py       # High-precision financial metrics verification
│       ├── test_data_integrity.py         # CSV mathematical reconciliation
│       ├── test_annual_reports_reconciliation.py # Verification against audited reports
│       ├── test_guardrails_compliance.py  # Methodology & guardrail checks
│       ├── test_markdown_links.py         # Link validation
│       ├── test_reports_content_and_language.py # Format & language compliance
│       └── test_extraction_script.py      # Extraction script unit tests
│
├── .gitignore                             # Git ignore rules
└── README.md                              # Project documentation
```

---

## 🧪 Verification & Automated Testing

All financial metrics, CSV records, and Markdown deliverables are strictly checked through an empirical automated test suite:

```bash
python "Market Analysis/tests/run_all_tests.py"
```

The test suite validates:
1. **Mathematical Integrity**: Headline items (Sales, Gross Profit, EBITDA, EBIT, Net Income, Net Cash, Working Capital) exactly match audited financial statements.
2. **Oracle Consistency**: Multiples, debt capacities, lease liabilities under IFRS 16, and ROCE calculations.
3. **Link & Deliverable Coverage**: Cross-references, module structure, and completeness.

---

## ⚖️ License & Disclaimer

Academic project prepared for Corporate Finance / MEFI. All corporate brand names and trademarks belong to their respective owners. Audited financial data sourced from Inditex S.A. published annual reports (FY2022–FY2025).

