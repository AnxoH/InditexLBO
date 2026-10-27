"""
Comprehensive extraction script for Inditex_LBO_Institutional_v4.xlsx
Dumps detailed audit data for:
- Active Case
- Debt & Covenants
- LBO Summary
- Checks
- Tax & WACC
"""
import sys
import openpyxl

sys.stdout.reconfigure(encoding='utf-8')

wb_v = openpyxl.load_workbook(r'Excels/Inditex_LBO_Institutional_v4.xlsx', data_only=True)
wb_f = openpyxl.load_workbook(r'Excels/Inditex_LBO_Institutional_v4.xlsx', data_only=False)

def dump_sheet(sheet_name, out_file=None):
    ws_v = wb_v[sheet_name]
    ws_f = wb_f[sheet_name]
    lines = []
    lines.append(f"================================================================================")
    lines.append(f"SHEET: {sheet_name} (rows: {ws_v.max_row}, cols: {ws_v.max_column})")
    lines.append(f"================================================================================")
    
    # Get column headers (usually rows 6, 7, 12, 13, 20)
    for r in range(1, ws_v.max_row + 1):
        row_has_val = False
        row_str = [f"R{r:03d}"]
        
        # Check label in cols A-D
        label = ""
        for c in range(1, 5):
            val = ws_v.cell(r, c).value
            if val is not None and str(val).strip() not in ['', '>']:
                label = str(val).strip()
                row_has_val = True
                break
        row_str.append(f"{label[:45]:<45}")
        
        for c in range(5, ws_v.max_column + 1):
            col_letter = openpyxl.utils.get_column_letter(c)
            v = ws_v.cell(r, c).value
            f = ws_f.cell(r, c).value
            if v is not None or f is not None:
                row_has_val = True
            if f is not None and str(f).startswith('='):
                val_repr = f"{col_letter}: {v} [{f}]"
            else:
                val_repr = f"{col_letter}: {v}" if v is not None else f"{col_letter}: -"
            row_str.append(val_repr)
            
        if row_has_val:
            lines.append(" | ".join(row_str))
            
    content = "\n".join(lines)
    if out_file:
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        print(content)

if __name__ == '__main__':
    for s in ['Active Case', 'Debt & Covenants', 'Checks', 'LBO Summary', 'Tax & WACC']:
        out_path = rf".agents/teamwork/explorer_survey_lbo_2/dump_{s.replace(' ', '_').lower()}.txt"
        dump_sheet(s, out_path)
        print(f"Dumped {s} to {out_path}")
