# Project: Inditex Institutional LBO Evaluation & IC Recommendation Memo

## Architecture
- **Target Company**: Industria de Diseño Textil, S.A. (Inditex, ITX.MC).
- **Transaction**: Public-to-Private (PtoP) Leveraged Buyout with Delisting / Squeeze-out.
- **Sponsor Consortium**: Lead Private Equity GP (15% sponsor commitment) + Sovereign/Pension LPs (85% syndicate).
- **Key Rollover**: Amancio Ortega (Pontegadea) 25.0% equity rollover into TopCo; Sandra Ortega 5.0% buyout funded via subordinated Vendor Loan Note.
- **Corporate Entity Structure**: TopCo (Equity issuer) -> BidCo/NewCo (Borrower of Senior & Junior Debt) -> Inditex S.A. (100% operating subsidiary post-squeeze-out, consolidated fiscal group under Art. 58 LIS).
- **Authoritative Model**: `Excels/Inditex_LBO_Institutional_v4.xlsx`.

## Feature Inventory
| # | Feature / Analysis Area | Description | Milestone | Source |
|---|-------------------------|-------------|-----------|--------|
| 1 | Baseline & Architecture Survey | Full cell-by-cell extraction of sheets, parameters, and 11 automated checks | M0 | Survey (Done) |
| 2 | Credit, Pricing & Debt Sizing Audit | Sizing 8.13x EBITDA, deleveraging to 2.90x, WALL 6.63y, SFA covenants (-0.65x/y), pricing spreads vs European mega-LBOs | M1 | R1 |
| 3 | Liquidity, Cash Flow & Stress-Testing | CFADS generation, DSCR (1.44x min vs 1.25x), ICR (3.15x to 15.04x), NOF (+€1,899M), 85% Cash Sweep (€25,282M), €1,000M cash floor, rate/sales/margin stress matrices | M2 | R2 |
| 4 | Tax Shield & Legal Structuring Audit | Art. 16.5 LIS (39.63% vs 70% cap), Art. 58 LIS (100% fiscal consolidation), Art. 87 LIS (FEAC tax neutrality), Art. 16.1 LIS (30% cap, €8,855M DTA reserve) | M3 | R3 |
| 5 | M&A Valuation & GP/LP Waterfall Audit | 19.35x Cash EBITDA, +12% premium, Gross IRR 12.88% / 2.33x MOIC, LPs 10.94% Net IRR vs 8% hurdle, Lead GP 21.23% Net IRR / 3.85x MOIC / €13.85B carry | M4 | R4 |
| 6 | Integrated Executive IC Memo | 7-section institutional markdown report with definitive IC recommendation, risk matrices, and confirmation items | M5 | R5 |
| 7 | Multi-Agent Review, Verification & Forensic Audit | Reviewers, Challengers, and Forensic Auditor verification suite | M6 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Survey & Model Extraction | Full workbook inspection, cell extraction, check formulas | none | DONE |
| M1 | Credit, Pricing & Debt Sizing Audit (R1) | Capital structure, tranches, WALL, covenant step-downs, market pricing contrast | M0 | DONE |
| M2 | Liquidity, Cash Flow & Stress-Testing (R2) | CFADS, DSCR, ICR, NOF dynamics, 85% cash sweep, multi-variable stress engine | M0 | DONE |
| M3 | Tax Shield & Legal Structuring Audit (R3) | Arts. 16.5, 58, 87, 16.1 LIS, fiscal group modeling, tax shields | M0 | DONE |
| M4 | M&A Valuation & GP/LP Waterfall Audit (R4) | Valuation multiples, Sources/Uses, Gross returns, 4-tier waterfall, institutional benchmarking | M0 | DONE |
| M5 | Integrated Executive Synthesis & IC Memo (R5) | Full 7-section IC Memorandum deliverable in Markdown | M1, M2, M3, M4 | DONE |
| M6 | Independent Verification & Forensic Audit | Reviewers (2), Challengers (2), Forensic Auditor (1) gate checks | M5 | DONE |

## Interface Contracts & Deliverables
- `LBO_Evaluation/01_Credit_and_Debt_Sizing_Audit.md`: Specialist module R1.
- `LBO_Evaluation/02_Liquidity_and_Stress_Testing_Audit.md`: Specialist module R2.
- `LBO_Evaluation/03_Tax_and_Legal_Structuring_Audit.md`: Specialist module R3.
- `LBO_Evaluation/04_Returns_and_Waterfall_Audit.md`: Specialist module R4.
- `Inditex_LBO_Institutional_IC_Evaluation.md`: Final integrated master deliverable (R5).

## Code Layout
- `Excels/Inditex_LBO_Institutional_v4.xlsx` (Read-only authoritative source)
- `LBO_Evaluation/` (Specialist analytical audit modules and technical scripts)
- `Inditex_LBO_Institutional_IC_Evaluation.md` (Master deliverable)
- `.agents/teamwork/orchestrator_1/` (Orchestrator state, progress, and briefing)

