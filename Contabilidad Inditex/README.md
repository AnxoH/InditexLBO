# Contabilidad Inditex — Working Capital, Negative NOF & IFRS 16 Analysis (2013–2025)

> **Primary Deliverable:** [`Informe_Inditex.pdf`](Informe_Inditex.pdf)

This workstream analyzes 13 years of audited Inditex financial statements (`FY2013–FY2025`) to quantify the structural cash conversion mechanics that underpin the LBO debt service capacity in [`../Inditex_LBO_Version_Definitiva.xlsx`](../Inditex_LBO_Version_Definitiva.xlsx):

1. **Structural Negative Operating Working Capital (`NOF < 0`)**:
   - Inditex operates with a **`-51.02` day Cash Conversion Cycle** (`28.88` receivable days + `91.85` inventory days vs. `171.75` supplier payable days).
   - As top-line revenue expands, trade payables grow faster than inventory and receivables, turning working capital into a self-financing operational float (`NOF` reaching `-€4,121m` in `FY2025`).
2. **Working Capital (`Fondo de Maniobra`) vs. Operating Working Capital Requirements (`NOF`)**:
   - Decomposes the spread between `FM` and `NOF` into Inditex's structural net cash position (`€11,255m` balance sheet cash at `FY2025` close), justifying the separation between the **`€2,226m` Locked Operational Cash Box** (retained inside OpCo to absorb intra-season inventory peaks) and **`€9,029m` Sweepable Cash** at LBO closing.
3. **IFRS 16 Lease Capitalization Adjustment (`2019–2025`)**:
   - Quantifies how IFRS 16 reclassifies cash store lease payments (`~€2,226m/yr`) from Operating Expenses into Right-of-Use (`RoU`) depreciation and lease interest, inflating Reported EBITDA vs. **Pre-IFRS 16 Cash EBITDA** (`€11,243m` in `FY2025`).

## Directory Contents

| Path | Description |
| :--- | :--- |
| [`Informe_Inditex.pdf`](Informe_Inditex.pdf) | Full Historical Accounting, Working Capital (`FM` vs. `NOF`), Cash Cycle & IFRS 16 Report |
| [`src/main.tex`](src/main.tex) | LaTeX source document for `Informe_Inditex.pdf` |
| [`src/fig1_fm_nof.pdf`](src/fig1_fm_nof.pdf) | Historical trajectory of `Fondo de Maniobra (FM)` vs. `NOF` (`2013–2025`) |
| [`src/fig2_ciclo_caja.pdf`](src/fig2_ciclo_caja.pdf) | Cash Conversion Cycle decomposition (inventory, receivable, and payable days) |
| [`src/fig3_cascada.pdf`](src/fig3_cascada.pdf) | EBITDA-to-Free Cash Flow conversion waterfall & Pre-IFRS 16 reconciliation |
