import re
import csv
import io
import html
import os
from playwright.sync_api import sync_playwright
import mistune

def parse_csv_to_html_table(csv_content, table_class="consulting-table"):
    f = io.StringIO(csv_content.strip())
    reader = csv.reader(f)
    rows = list(reader)
    if not rows:
        return ""
    
    header = rows[0]
    data_rows = rows[1:]
    
    # Determine if this is a very wide table
    is_wide = len(header) >= 7
    extra_class = " wide-table" if is_wide else ""
    
    html_out = [f'<div class="table-container"><table class="{table_class}{extra_class}"><thead><tr>']
    for col in header:
        clean_col = col.replace('_', ' ')
        html_out.append(f'<th>{html.escape(clean_col)}</th>')
    html_out.append('</tr></thead><tbody>')
    
    for row in data_rows:
        html_out.append('<tr>')
        for i, cell in enumerate(row):
            cell_str = cell.strip()
            is_num = False
            clean_val = cell_str.replace(' ', '')
            if (re.match(r'^[\-\+]?[\€\$\£]?\s*[\d\.\,]+\s*[\%xXbpsBMBkK]*$', clean_val) or 
                re.match(r'^\([\€\$\£]?[\d\.\,]+\s*[\%xXbpsBMBkK]*\)$', clean_val)):
                is_num = True
            
            align_class = ' class="num-cell"' if is_num else ''
            
            # Special highlighting for totals / key aggregates
            is_key_metric = i == 0 and any(k in cell_str.lower() for k in [
                'total', 'ebitda', 'net income', 'net sales', 'gross profit', 'ebit ', 
                'free cash flow', 'statutory net cash', 'group roce', 'operating working capital'
            ])
            
            if is_key_metric:
                cell_html = f'<strong>{html.escape(cell_str)}</strong>'
            else:
                cell_html = html.escape(cell_str)
                
            html_out.append(f'<td{align_class}>{cell_html}</td>')
        html_out.append('</tr>')
        
    html_out.append('</tbody></table></div>')
    return '\n'.join(html_out)


class McKinseyRenderer(mistune.HTMLRenderer):
    def block_code(self, code, info=None):
        if info and info.strip().lower() == 'csv':
            return parse_csv_to_html_table(code, "consulting-table")
        else:
            escaped_code = html.escape(code.rstrip('\n'))
            return f'<div class="executive-callout"><pre class="executive-pre"><code>{escaped_code}</code></pre></div>\n'

def mckinsey_table(renderer, text):
    if 'EV/EBITDA' in text or 'Tier 1' in text or 'HM-B.ST' in text:
        return f'<div class="table-container"><table class="consulting-table peer-benchmarking-table">\n{text}</table></div>\n'
    return f'<div class="table-container"><table class="consulting-table">\n{text}</table></div>\n'

def mckinsey_table_cell(renderer, text, align=None, head=False):
    tag = 'th' if head else 'td'
    classes = []
    clean_text = re.sub(r'<[^>]+>', '', text).strip()
    
    if not head:
        clean_val = clean_text.replace(' ', '')
        if (re.match(r'^[\-\+]?[\€\$\£]?\s*[\d\.\,]+\s*[\%xXbpsBMBkK]*$', clean_val) or 
            re.match(r'^\([\€\$\£]?[\d\.\,]+\s*[\%xXbpsBMBkK]*\)$', clean_val)):
            classes.append('num-cell')
            
    if align:
        classes.append(f'align-{align}')
        
    class_attr = f' class="{" ".join(classes)}"' if classes else ''
    return f'<{tag}{class_attr}>{text}</{tag}>\n'


def process_markdown_content(md_text):
    md_text = md_text.replace('\r\n', '\n')
    
    # Replace LaTeX math
    md_text = md_text.replace(r'$\Delta NWC > 0$', '&Delta;NWC &gt; 0')
    md_text = md_text.replace(r'$\Delta NWC = \Delta Sales \times 10.5\%$', '&Delta;NWC = &Delta;Sales &times; 10.5%')
    
    # Extract metadata header if present
    header_pattern = r'^#\s*(.*?)\n#\s*(.*?)\n\n(.*?)\n---'
    header_match = re.search(header_pattern, md_text, re.DOTALL)
    
    memo_header_html = ""
    if header_match:
        doc_type = header_match.group(1).strip()
        doc_title = header_match.group(2).strip()
        meta_lines = header_match.group(3).strip().split('\n')
        
        meta_items = []
        for line in meta_lines:
            line = line.strip()
            if not line:
                continue
            m = re.match(r'\*\*(.*?)\*\*:\s*(.*)', line)
            if m:
                key = m.group(1).strip()
                val = m.group(2).strip()
                val_html = val.replace('**', '')
                meta_items.append((key, val_html))
        
        memo_header_html = f'''
        <div class="memo-header-container">
            <div class="memo-eyebrow">PRIVATE EQUITY INVESTMENT COMMITTEE | STAGE 1 SCREENING MEMORANDUM</div>
            <h1 class="memo-main-title">{html.escape(doc_title)}</h1>
            <div class="memo-grid">
        '''
        for key, val in meta_items:
            is_rec = 'recommendation' in key.lower()
            rec_class = ' recommendation-row' if is_rec else ''
            val_display = f'<span class="badge-rec">{html.escape(val)}</span>' if is_rec else html.escape(val)
            memo_header_html += f'''
                <div class="memo-grid-item{rec_class}">
                    <span class="memo-key">{html.escape(key)}:</span>
                    <span class="memo-val">{val_display}</span>
                </div>
            '''
        memo_header_html += '''
            </div>
        </div>
        '''
        md_text = md_text[header_match.end():].strip()
        if md_text.startswith('---'):
            md_text = md_text[3:].strip()
            
    # Markdown parser with McKinsey renderer
    renderer = McKinseyRenderer()
    markdown = mistune.create_markdown(renderer=renderer, plugins=['table', 'strikethrough'])
    markdown.renderer.register('table', mckinsey_table)
    markdown.renderer.register('table_cell', mckinsey_table_cell)
    rendered_body = markdown(md_text)

    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Inditex - Project Galicia - IC Screening Memorandum</title>
<style>
    @page {{
        size: A4 portrait;
        margin: 18mm 16mm 18mm 16mm;
    }}
    
    * {{
        box-sizing: border-box;
    }}
    
    body {{
        font-family: Arial, Helvetica, sans-serif;
        font-size: 10pt;
        line-height: 1.48;
        color: #333333;
        background-color: #ffffff;
        margin: 0;
        padding: 0;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }}
    
    /* Document Header (McKinsey Style) */
    .memo-header-container {{
        border-bottom: 2.5px solid #002b49;
        padding-bottom: 14px;
        margin-bottom: 20px;
    }}
    
    .memo-eyebrow {{
        font-size: 8pt;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #002b49;
        font-weight: 700;
        margin-bottom: 6px;
    }}
    
    .memo-main-title {{
        font-size: 18pt;
        font-weight: 700;
        color: #002b49;
        margin: 0 0 12px 0;
        line-height: 1.25;
        border-bottom: none !important;
        padding-bottom: 0 !important;
    }}
    
    .memo-grid {{
        display: grid;
        grid-template-columns: 1fr;
        row-gap: 5px;
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #002b49;
        padding: 10px 14px;
        font-size: 8.8pt;
    }}
    
    .memo-grid-item {{
        display: flex;
        align-items: baseline;
    }}
    
    .memo-key {{
        font-weight: 700;
        color: #002b49;
        width: 220px;
        flex-shrink: 0;
    }}
    
    .memo-val {{
        color: #333333;
    }}
    
    .badge-rec {{
        background-color: #002b49;
        color: #ffffff;
        padding: 2px 7px;
        border-radius: 2px;
        font-weight: 700;
        font-size: 8.5pt;
        letter-spacing: 0.5px;
    }}
    
    /* Action Titles (H1, H2, H3, H4) */
    h1 {{
        color: #002b49;
        font-size: 15pt;
        font-weight: 700;
        line-height: 1.3;
        margin-top: 24px;
        margin-bottom: 10px;
        padding-bottom: 4px;
        border-bottom: 2px solid #002b49;
        page-break-after: avoid;
    }}
    
    h2 {{
        color: #002b49;
        font-size: 12.5pt;
        font-weight: 700;
        line-height: 1.35;
        margin-top: 20px;
        margin-bottom: 8px;
        padding-bottom: 3px;
        border-bottom: 1.5px solid #002b49;
        page-break-after: avoid;
    }}
    
    h3 {{
        color: #002b49;
        font-size: 10.5pt;
        font-weight: 700;
        line-height: 1.4;
        margin-top: 15px;
        margin-bottom: 6px;
        page-break-after: avoid;
    }}
    
    h4 {{
        color: #002b49;
        font-size: 9.8pt;
        font-weight: 700;
        margin-top: 12px;
        margin-bottom: 4px;
        page-break-after: avoid;
    }}
    
    p {{
        margin-top: 0;
        margin-bottom: 8px;
        color: #333333;
        text-align: justify;
    }}
    
    strong, b {{
        color: #111111;
        font-weight: 700;
    }}
    
    ul, ol {{
        margin-top: 0;
        margin-bottom: 9px;
        padding-left: 20px;
    }}
    
    li {{
        margin-bottom: 4px;
        color: #333333;
    }}
    
    hr {{
        border: none;
        border-top: 1px solid #dce4ec;
        margin: 18px 0;
    }}
    
    a {{
        color: #002b49;
        text-decoration: none;
        border-bottom: 1px dotted #002b49;
    }}
    
    /* Executive Callout Boxes */
    .executive-callout {{
        background-color: #eef4f8;
        border-left: 5px solid #002b49;
        padding: 12px 14px;
        margin: 12px 0 14px 0;
        border-radius: 2px;
        page-break-inside: avoid;
    }}
    
    .executive-pre {{
        margin: 0;
        padding: 0;
        font-family: 'Consolas', 'Menlo', 'Courier New', monospace;
        font-size: 6.8pt;
        line-height: 1.28;
        color: #1a2b3c;
        white-space: pre;
        overflow-x: hidden;
    }}
    
    /* Consulting Tables (Strict McKinsey Rules) */
    .table-container {{
        width: 100%;
        margin: 12px 0 16px 0;
        page-break-inside: avoid;
    }}
    
    table.consulting-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 8.2pt;
        line-height: 1.32;
        border-left: none !important;
        border-right: none !important;
        border-top: 2.5px solid #002b49;
        border-bottom: 2.5px solid #002b49;
    }}
    
    table.consulting-table thead tr {{
        border-top: none;
        border-bottom: 2px solid #002b49;
        background-color: #ffffff;
    }}
    
    table.consulting-table th {{
        color: #002b49;
        font-weight: 700;
        text-align: left;
        padding: 5px 6px;
        border-left: none !important;
        border-right: none !important;
        border-top: none;
        border-bottom: 2px solid #002b49;
        vertical-align: bottom;
    }}
    
    table.consulting-table td {{
        padding: 4px 6px;
        border-left: none !important;
        border-right: none !important;
        border-top: none;
        border-bottom: 1px solid #edf2f7;
        color: #333333;
        vertical-align: middle;
    }}
    
    table.consulting-table tbody tr:last-child td {{
        border-bottom: none;
    }}
    
    table.consulting-table tbody tr:nth-child(even) {{
        background-color: #f9f9f9;
    }}
    
    table.consulting-table tbody tr:nth-child(odd) {{
        background-color: #ffffff;
    }}
    
    td.num-cell, th.align-right, td.align-right {{
        text-align: right;
        font-variant-numeric: tabular-nums;
    }}
    
    th.align-center, td.align-center {{
        text-align: center;
    }}
    
    /* Wide tables styling (Section 6 tables) */
    table.wide-table {{
        font-size: 7.2pt !important;
        line-height: 1.25;
    }}
    table.wide-table th, table.wide-table td {{
        padding: 4px 4px !important;
    }}
    
    /* 17-column Peer Benchmarking Table */
    table.peer-benchmarking-table {{
        font-size: 5.8pt !important;
        line-height: 1.2;
    }}
    table.peer-benchmarking-table th,
    table.peer-benchmarking-table td {{
        padding: 3px 2px !important;
    }}
    
    /* Inline code */
    code:not(.executive-pre code) {{
        font-family: 'Consolas', 'Menlo', 'Courier New', monospace;
        font-size: 8.8pt;
        background-color: #f1f5f9;
        color: #002b49;
        padding: 1px 4px;
        border-radius: 2px;
    }}
    
    blockquote {{
        border-left: 3px solid #002b49;
        margin: 10px 0;
        padding: 6px 12px;
        color: #4a5568;
        font-style: italic;
        background-color: #f8fafc;
    }}
</style>
</head>
<body>

{memo_header_html}

{rendered_body}

</body>
</html>
'''
    return full_html

def generate_pdf():
    # Resolve paths relative to script location: Market Analysis/scripts/ -> Market Analysis/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    market_analysis_dir = os.path.abspath(os.path.join(script_dir, ".."))
    
    input_path = os.path.join(market_analysis_dir, "00_Inditex_Stage1_IC_Overview.md")
    output_html_path = os.path.join(market_analysis_dir, "00_Inditex_Stage1_IC_Overview_McKinsey.html")
    output_pdf_path = os.path.join(market_analysis_dir, "00_Inditex_Stage1_IC_Overview_McKinsey.pdf")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
        
    print(f"Read input markdown: {len(md_text)} characters from {input_path}")
    
    full_html = process_markdown_content(md_text)
    
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
    print(f"Wrote styled HTML: {output_html_path}")
    
    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    chrome_exe = next((p for p in chrome_candidates if os.path.exists(p)), None)
    
    header_html = '''
    <div style="font-family: Arial, Helvetica, sans-serif; font-size: 7.5pt; color: #718096; width: 100%; display: flex; justify-content: space-between; padding: 0 16mm; border-bottom: 0.5px solid #e2e8f0; padding-bottom: 4px;">
        <span style="font-weight: 700; color: #002b49; letter-spacing: 0.5px;">PROJECT GALICIA: INDITEX, S.A. (BME: ITX.MC)</span>
        <span>INVESTMENT COMMITTEE STAGE 1 SCREENING MEMORANDUM</span>
    </div>
    '''
    footer_html = '''
    <div style="font-family: Arial, Helvetica, sans-serif; font-size: 7.5pt; color: #718096; width: 100%; display: flex; justify-content: space-between; padding: 0 16mm; border-top: 0.5px solid #e2e8f0; padding-top: 4px;">
        <span style="color: #c53030; font-weight: 700; letter-spacing: 0.5px;">STRICTLY CONFIDENTIAL — INVESTMENT COMMITTEE USE ONLY</span>
        <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
    </div>
    '''
    
    print("Launching browser via Playwright...")
    with sync_playwright() as p:
        launch_kwargs = {"headless": True}
        if chrome_exe:
            launch_kwargs["executable_path"] = chrome_exe
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page()
        page.goto(f"file:///{output_html_path.replace(os.sep, '/')}")
        page.wait_for_load_state("networkidle")
        
        print(f"Rendering PDF to {output_pdf_path}...")
        page.pdf(
            path=output_pdf_path,
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template=header_html,
            footer_template=footer_html,
            margin={
                "top": "16mm",
                "bottom": "16mm",
                "left": "16mm",
                "right": "16mm"
            }
        )
        browser.close()
        
    print("PDF generation complete successfully!")
    print(f"Output PDF file size: {os.path.getsize(output_pdf_path)} bytes")

if __name__ == "__main__":
    generate_pdf()

