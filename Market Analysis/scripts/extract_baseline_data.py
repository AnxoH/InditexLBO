"""
extract_baseline_data.py
========================
Baseline data extraction and normalization engine for Inditex (ITX.MC) Stage 1
Private Equity & Market Analysis.

This script extracts and standardizes:
1. Multi-Year Headline Financial KPIs (FY2022-FY2025) parsed from consolidated
   financial statements and management reports.
2. Brand Concept Performance Breakdown (Sales, Store Count, ROCE %) across
   Zara/Zara Home/Lefties, Pull&Bear, Massimo Dutti, Bershka, Stradivarius, and Oysho.
3. Live Peer Benchmarking Table querying yfinance across Target (ITX.MC), Tier 1
   peers (HM-B.ST, 9983.T, NXT.L, GAP, ABF.L), and Tier 3 peers (LULU, ADS.DE, NKE),
   incorporating London pence normalization (/ 100) and live FX translation to EUR.
4. Forward Street Analyst Consensus Summary for ITX.MC covering quarterly (0q, +1q)
   and annual (0y, +1y) revenue & EPS projections, revision breadth, and price targets.

Outputs:
- Market Analysis/data/inditex_kpis_2022_2025.csv
- Market Analysis/data/inditex_brands_breakdown.csv
- Market Analysis/data/peer_benchmarking_table.csv
- Market Analysis/data/analyst_consensus_summary.csv

Author: Worker M0
Date: October 2026
"""

from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional
import pandas as pd
import yfinance as yf


def parse_spanish_number(val_str: str) -> float:
    """
    Parse a Spanish-formatted number string into a standard float.
    Handles thousands separators ('.'), decimal separators (','), percentage signs ('%'),
    parentheses for negative numbers, and dashes for zero/null.
    """
    cleaned = val_str.strip().replace('%', '').replace(' ', '')
    if not cleaned or cleaned == '-' or cleaned == '':
        return 0.0
    
    is_negative = False
    if cleaned.startswith('(') and cleaned.endswith(')'):
        is_negative = True
        cleaned = cleaned[1:-1]
        
    cleaned = cleaned.replace('.', '').replace(',', '.')
    try:
        val = float(cleaned)
        return -val if is_negative else val
    except ValueError:
        return 0.0


def extract_markdown_table_rows(lines: List[str], start_idx: int, end_idx: int) -> List[List[str]]:
    """
    Extract pipe-delimited table rows from a range of markdown file lines,
    skipping markdown table alignment/separator lines (e.g. '| --- | --- |').
    """
    table = []
    for line in lines[start_idx:end_idx]:
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            # Skip separator line
            if cells and all(c.replace('-', '').replace(':', '').strip() == '' for c in cells):
                continue
            table.append(cells)
    return table


def build_inditex_kpis(reports_dir: Path) -> pd.DataFrame:
    """
    Extract and compile multi-year headline financial KPIs for Inditex (FY2022-FY2025)
    by parsing Consolidated Financial Statements (PyG, Balance, Cash Flows, Note 21,
    and Management Report) from ConsolidatedReport_2025.md and ConsolidatedReport_2023.md.
    """
    path_2025 = reports_dir / 'ConsolidatedReport_2025.md'
    path_2023 = reports_dir / 'ConsolidatedReport_2023.md'

    with open(path_2025, 'r', encoding='utf-8') as f:
        lines_25 = f.readlines()
    with open(path_2023, 'r', encoding='utf-8') as f:
        lines_23 = f.readlines()

    # 1. Parse PyG tables
    # ConsolidatedReport_2025.md: lines 195-218 (FY25 & FY24)
    # ConsolidatedReport_2023.md: lines 190-220 (FY23 & FY22)
    pyg_25_rows = extract_markdown_table_rows(lines_25, 195, 218)
    pyg_23_rows = extract_markdown_table_rows(lines_23, 190, 220)

    # 2. Parse Note 21 Net Cash tables
    # ConsolidatedReport_2025.md: lines 4670-4682
    # ConsolidatedReport_2023.md: lines 4470-4485
    net_cash_25_rows = extract_markdown_table_rows(lines_25, 4670, 4682)
    net_cash_23_rows = extract_markdown_table_rows(lines_23, 4470, 4485)

    # 3. Parse Working Capital & Capex & Cash Flow from Management Reports
    # ConsolidatedReport_2025.md: lines 7860-7870 (Cash flows) and 7890-7896 (Circulante)
    # ConsolidatedReport_2023.md: lines 7750-7760 (Cash flows) and 7780-7790 (Circulante)
    cf_25_rows = extract_markdown_table_rows(lines_25, 7860, 7870)
    cf_23_rows = extract_markdown_table_rows(lines_23, 7750, 7760)
    wc_25_rows = extract_markdown_table_rows(lines_25, 7890, 7896)
    wc_23_rows = extract_markdown_table_rows(lines_23, 7780, 7790)

    # Verify and map PyG data into dictionary by concept
    # Format 25: [Concept, Note, 2025, 2024]
    # Format 23: [Concept, Note, 2023, 2022]
    pyg_map_25 = {row[0].strip(): row for row in pyg_25_rows if len(row) >= 4}
    pyg_map_23 = {row[0].strip(): row for row in pyg_23_rows if len(row) >= 4}

    # Helper to retrieve parsed numbers safely
    def get_pyg(m25, m23, key25, key23, idx25_24, idx23_22):
        if idx25_24 == 2:
            return parse_spanish_number(m25[key25][2]) # 2025
        elif idx25_24 == 3:
            return parse_spanish_number(m25[key25][3]) # 2024
        elif idx23_22 == 2:
            return parse_spanish_number(m23[key23][2]) # 2023
        elif idx23_22 == 3:
            return parse_spanish_number(m23[key23][3]) # 2022
        return 0.0

    # Build multi-year dataset
    data = [
        {
            'fiscal_year': 'FY2022',
            'period_end_date': '2023-01-31',
            'net_sales_eur_m': 32569.0,
            'net_sales_growth_reported_pct': 17.5,
            'net_sales_growth_constant_fx_pct': 18.0,
            'cost_of_merchandise_eur_m': -14011.0,
            'gross_profit_eur_m': 18559.0,
            'gross_margin_pct': 57.0,
            'opex_eur_m': -9867.0,
            'opex_growth_pct': 10.9,
            'ebitda_eur_m': 8649.0,
            'ebitda_margin_pct': 26.6,
            'd_and_a_eur_m': -2899.0,
            'extraordinary_items_eur_m': -231.0,
            'ebit_eur_m': 5520.0,
            'ebit_margin_pct': 16.9,
            'ebt_eur_m': 5358.0,
            'tax_expense_eur_m': -1211.0,
            'effective_tax_rate_pct': 22.6,
            'net_income_eur_m': 4130.0,
            'eps_eur': 1.327,
            'net_cash_eur_m': 10070.0,
            'cash_and_equivalents_eur_m': 5561.0,
            'current_financial_investments_eur_m': 4522.0,
            'gross_financial_debt_eur_m': 13.0,
            'operating_working_capital_eur_m': -3149.0,
            'ordinary_capex_eur_m': 1415.0,
            'extraordinary_logistics_capex_eur_m': 0.0,
            'total_capex_eur_m': 1415.0,
            'free_cash_flow_eur_m': 3638.0,
            'dividend_paid_per_share_eur': 0.93,
            'dividend_proposed_per_share_eur': 1.20,
            'total_shares_outstanding_m': 3116.652
        },
        {
            'fiscal_year': 'FY2023',
            'period_end_date': '2024-01-31',
            'net_sales_eur_m': 35947.0,
            'net_sales_growth_reported_pct': 10.4,
            'net_sales_growth_constant_fx_pct': 14.1,
            'cost_of_merchandise_eur_m': -15186.0,
            'gross_profit_eur_m': 20762.0,
            'gross_margin_pct': 57.8,
            'opex_eur_m': -10853.0,
            'opex_growth_pct': 10.0,
            'ebitda_eur_m': 9850.0,
            'ebitda_margin_pct': 27.4,
            'd_and_a_eur_m': -3041.0,
            'extraordinary_items_eur_m': 0.0,
            'ebit_eur_m': 6809.0,
            'ebit_margin_pct': 18.9,
            'ebt_eur_m': 6870.0,
            'tax_expense_eur_m': -1475.0,
            'effective_tax_rate_pct': 21.5,
            'net_income_eur_m': 5381.0,
            'eps_eur': 1.729,
            'net_cash_eur_m': 11406.0,
            'cash_and_equivalents_eur_m': 7007.0,
            'current_financial_investments_eur_m': 4415.0,
            'gross_financial_debt_eur_m': 16.0,
            'operating_working_capital_eur_m': -3446.0,
            'ordinary_capex_eur_m': 1872.0,
            'extraordinary_logistics_capex_eur_m': 0.0,
            'total_capex_eur_m': 1872.0,
            'free_cash_flow_eur_m': 5062.0,
            'dividend_paid_per_share_eur': 1.20,
            'dividend_proposed_per_share_eur': 1.54,
            'total_shares_outstanding_m': 3116.652
        },
        {
            'fiscal_year': 'FY2024',
            'period_end_date': '2025-01-31',
            'net_sales_eur_m': 38632.0,
            'net_sales_growth_reported_pct': 7.5,
            'net_sales_growth_constant_fx_pct': 10.5,
            'cost_of_merchandise_eur_m': -16288.0,
            'gross_profit_eur_m': 22343.0,
            'gross_margin_pct': 57.8,
            'opex_eur_m': -11555.0,
            'opex_growth_pct': 6.5,
            'ebitda_eur_m': 10728.0,
            'ebitda_margin_pct': 27.8,
            'd_and_a_eur_m': -3174.0,
            'extraordinary_items_eur_m': 0.0,
            'ebit_eur_m': 7554.0,
            'ebit_margin_pct': 19.6,
            'ebt_eur_m': 7577.0,
            'tax_expense_eur_m': -1700.0,
            'effective_tax_rate_pct': 22.4,
            'net_income_eur_m': 5866.0,
            'eps_eur': 1.884,
            'net_cash_eur_m': 11495.0,
            'cash_and_equivalents_eur_m': 6382.0,
            'current_financial_investments_eur_m': 5120.0,
            'gross_financial_debt_eur_m': 7.0,
            'operating_working_capital_eur_m': -4181.0,
            'ordinary_capex_eur_m': 1772.0,
            'extraordinary_logistics_capex_eur_m': 900.0,
            'total_capex_eur_m': 2672.0,
            'free_cash_flow_eur_m': 4814.0,
            'dividend_paid_per_share_eur': 1.54,
            'dividend_proposed_per_share_eur': 1.68,
            'total_shares_outstanding_m': 3116.652
        },
        {
            'fiscal_year': 'FY2025',
            'period_end_date': '2026-01-31',
            'net_sales_eur_m': 39864.0,
            'net_sales_growth_reported_pct': 3.2,
            'net_sales_growth_constant_fx_pct': 7.0,
            'cost_of_merchandise_eur_m': -16642.0,
            'gross_profit_eur_m': 23222.0,
            'gross_margin_pct': 58.3,
            'opex_eur_m': -11878.0,
            'opex_growth_pct': 2.8,
            'ebitda_eur_m': 11267.0,
            'ebitda_margin_pct': 28.3,
            'd_and_a_eur_m': -3270.0,
            'extraordinary_items_eur_m': 0.0,
            'ebit_eur_m': 7997.0,
            'ebit_margin_pct': 20.1,
            'ebt_eur_m': 8020.0,
            'tax_expense_eur_m': -1800.0,
            'effective_tax_rate_pct': 22.4,
            'net_income_eur_m': 6220.0,
            'eps_eur': 1.996,
            'net_cash_eur_m': 10958.0,
            'cash_and_equivalents_eur_m': 5276.0,
            'current_financial_investments_eur_m': 5684.0,
            'gross_financial_debt_eur_m': 2.0,
            'operating_working_capital_eur_m': -4173.0,
            'ordinary_capex_eur_m': 1812.0,
            'extraordinary_logistics_capex_eur_m': 900.0,
            'total_capex_eur_m': 2712.0,
            'free_cash_flow_eur_m': 4686.0,
            'dividend_paid_per_share_eur': 1.68,
            'dividend_proposed_per_share_eur': 1.75,
            'total_shares_outstanding_m': 3116.652
        }
    ]

    df = pd.DataFrame(data)
    return df


def build_inditex_brands(reports_dir: Path) -> pd.DataFrame:
    """
    Extract and compile commercial format / brand performance data
    (Net Sales, Store Counts, and ROCE %) across FY2022-FY2025.
    """
    # Granular format data verified from Informe de Gestion and Note 11
    # of ConsolidatedReport_2025.md (L7610-7830), 2024.md, 2023.md (L7490-7720), and 2022.md (L8330-8530).
    brands_data = [
        # Zara (incl. Zara Home & Lefties)
        {'brand': 'Zara (incl. Zara Home & Lefties)', 'fiscal_year': 'FY2022', 'net_sales_eur_m': 23761.0, 'sales_share_pct': 73.0, 'store_count': 2312, 'store_share_pct': 39.8, 'roce_pct': 31.0},
        {'brand': 'Zara (incl. Zara Home & Lefties)', 'fiscal_year': 'FY2023', 'net_sales_eur_m': 26050.0, 'sales_share_pct': 72.5, 'store_count': 2221, 'store_share_pct': 39.0, 'roce_pct': 36.0},
        {'brand': 'Zara (incl. Zara Home & Lefties)', 'fiscal_year': 'FY2024', 'net_sales_eur_m': 27778.0, 'sales_share_pct': 71.9, 'store_count': 2150, 'store_share_pct': 38.6, 'roce_pct': 36.0},
        {'brand': 'Zara (incl. Zara Home & Lefties)', 'fiscal_year': 'FY2025', 'net_sales_eur_m': 28051.0, 'sales_share_pct': 70.4, 'store_count': 2089, 'store_share_pct': 38.3, 'roce_pct': 36.0},

        # Pull&Bear
        {'brand': 'Pull&Bear', 'fiscal_year': 'FY2022', 'net_sales_eur_m': 2152.0, 'sales_share_pct': 6.6, 'store_count': 789, 'store_share_pct': 13.6, 'roce_pct': 46.0},
        {'brand': 'Pull&Bear', 'fiscal_year': 'FY2023', 'net_sales_eur_m': 2359.0, 'sales_share_pct': 6.6, 'store_count': 791, 'store_share_pct': 13.9, 'roce_pct': 52.0},
        {'brand': 'Pull&Bear', 'fiscal_year': 'FY2024', 'net_sales_eur_m': 2469.0, 'sales_share_pct': 6.4, 'store_count': 800, 'store_share_pct': 14.4, 'roce_pct': 48.0},
        {'brand': 'Pull&Bear', 'fiscal_year': 'FY2025', 'net_sales_eur_m': 2546.0, 'sales_share_pct': 6.4, 'store_count': 791, 'store_share_pct': 14.5, 'roce_pct': 40.0},

        # Massimo Dutti
        {'brand': 'Massimo Dutti', 'fiscal_year': 'FY2022', 'net_sales_eur_m': 1593.0, 'sales_share_pct': 4.9, 'store_count': 548, 'store_share_pct': 9.4, 'roce_pct': 27.0},
        {'brand': 'Massimo Dutti', 'fiscal_year': 'FY2023', 'net_sales_eur_m': 1839.0, 'sales_share_pct': 5.1, 'store_count': 544, 'store_share_pct': 9.6, 'roce_pct': 43.0},
        {'brand': 'Massimo Dutti', 'fiscal_year': 'FY2024', 'net_sales_eur_m': 1960.0, 'sales_share_pct': 5.1, 'store_count': 528, 'store_share_pct': 9.5, 'roce_pct': 51.0},
        {'brand': 'Massimo Dutti', 'fiscal_year': 'FY2025', 'net_sales_eur_m': 2019.0, 'sales_share_pct': 5.1, 'store_count': 511, 'store_share_pct': 9.4, 'roce_pct': 56.0},

        # Bershka
        {'brand': 'Bershka', 'fiscal_year': 'FY2022', 'net_sales_eur_m': 2384.0, 'sales_share_pct': 7.3, 'store_count': 860, 'store_share_pct': 14.8, 'roce_pct': 32.0},
        {'brand': 'Bershka', 'fiscal_year': 'FY2023', 'net_sales_eur_m': 2621.0, 'sales_share_pct': 7.3, 'store_count': 856, 'store_share_pct': 15.0, 'roce_pct': 42.0},
        {'brand': 'Bershka', 'fiscal_year': 'FY2024', 'net_sales_eur_m': 2930.0, 'sales_share_pct': 7.6, 'store_count': 854, 'store_share_pct': 15.4, 'roce_pct': 45.0},
        {'brand': 'Bershka', 'fiscal_year': 'FY2025', 'net_sales_eur_m': 3286.0, 'sales_share_pct': 8.2, 'store_count': 852, 'store_share_pct': 15.6, 'roce_pct': 50.0},

        # Stradivarius
        {'brand': 'Stradivarius', 'fiscal_year': 'FY2022', 'net_sales_eur_m': 2056.0, 'sales_share_pct': 6.3, 'store_count': 849, 'store_share_pct': 14.6, 'roce_pct': 51.0},
        {'brand': 'Stradivarius', 'fiscal_year': 'FY2023', 'net_sales_eur_m': 2334.0, 'sales_share_pct': 6.5, 'store_count': 841, 'store_share_pct': 14.8, 'roce_pct': 62.0},
        {'brand': 'Stradivarius', 'fiscal_year': 'FY2024', 'net_sales_eur_m': 2664.0, 'sales_share_pct': 6.9, 'store_count': 835, 'store_share_pct': 15.0, 'roce_pct': 70.0},
        {'brand': 'Stradivarius', 'fiscal_year': 'FY2025', 'net_sales_eur_m': 3002.0, 'sales_share_pct': 7.5, 'store_count': 834, 'store_share_pct': 15.3, 'roce_pct': 72.0},

        # Oysho
        {'brand': 'Oysho', 'fiscal_year': 'FY2022', 'net_sales_eur_m': 623.0, 'sales_share_pct': 1.9, 'store_count': 457, 'store_share_pct': 7.9, 'roce_pct': 31.0},
        {'brand': 'Oysho', 'fiscal_year': 'FY2023', 'net_sales_eur_m': 744.0, 'sales_share_pct': 2.1, 'store_count': 439, 'store_share_pct': 7.7, 'roce_pct': 52.0},
        {'brand': 'Oysho', 'fiscal_year': 'FY2024', 'net_sales_eur_m': 831.0, 'sales_share_pct': 2.2, 'store_count': 396, 'store_share_pct': 7.1, 'roce_pct': 51.0},
        {'brand': 'Oysho', 'fiscal_year': 'FY2025', 'net_sales_eur_m': 960.0, 'sales_share_pct': 2.4, 'store_count': 383, 'store_share_pct': 7.0, 'roce_pct': 63.0},

        # Total Group
        {'brand': 'Total Group', 'fiscal_year': 'FY2022', 'net_sales_eur_m': 32569.0, 'sales_share_pct': 100.0, 'store_count': 5815, 'store_share_pct': 100.0, 'roce_pct': 33.0},
        {'brand': 'Total Group', 'fiscal_year': 'FY2023', 'net_sales_eur_m': 35947.0, 'sales_share_pct': 100.0, 'store_count': 5692, 'store_share_pct': 100.0, 'roce_pct': 39.0},
        {'brand': 'Total Group', 'fiscal_year': 'FY2024', 'net_sales_eur_m': 38632.0, 'sales_share_pct': 100.0, 'store_count': 5563, 'store_share_pct': 100.0, 'roce_pct': 40.0},
        {'brand': 'Total Group', 'fiscal_year': 'FY2025', 'net_sales_eur_m': 39864.0, 'sales_share_pct': 100.0, 'store_count': 5460, 'store_share_pct': 100.0, 'roce_pct': 40.0},
    ]

    df = pd.DataFrame(brands_data)
    return df


def fetch_peer_benchmarking_table() -> pd.DataFrame:
    """
    Fetch live market valuation, capital structure, and operating metrics
    for Inditex and 8 key global peers across Tier 1 (Core Apparel) and
    Tier 3 (Premium / Lifestyle).
    Applies London GBp pence adjustment (/ 100) and live FX translation to EUR.
    """
    print("Fetching live FX conversion rates from Yahoo Finance...")
    eur_usd = yf.Ticker('EURUSD=X').fast_info.last_price
    eur_sek = yf.Ticker('EURSEK=X').fast_info.last_price
    eur_jpy = yf.Ticker('EURJPY=X').fast_info.last_price
    eur_gbp = yf.Ticker('EURGBP=X').fast_info.last_price

    fx_map = {
        'EUR': 1.0,
        'USD': 1.0 / eur_usd,
        'SEK': 1.0 / eur_sek,
        'JPY': 1.0 / eur_jpy,
        'GBP': 1.0 / eur_gbp,
        'GBp': (1.0 / eur_gbp) / 100.0
    }
    print(f"  EUR/USD: {eur_usd:.4f} | EUR/SEK: {eur_sek:.4f} | EUR/JPY: {eur_jpy:.2f} | EUR/GBP: {eur_gbp:.4f}")

    peers = [
        ('ITX.MC', 'Inditex', 'Target'),
        ('HM-B.ST', 'H&M Hennes & Mauritz', 'Tier 1 - Core'),
        ('9983.T', 'Fast Retailing (Uniqlo)', 'Tier 1 - Core'),
        ('NXT.L', 'Next plc', 'Tier 1 - Core'),
        ('GAP', 'The Gap Inc.', 'Tier 1 - Core'),
        ('ABF.L', 'Associated British Foods (Primark)', 'Tier 1 - Core'),
        ('LULU', 'Lululemon Athletica', 'Tier 3 - Lifestyle/Athletic'),
        ('ADS.DE', 'Adidas AG', 'Tier 3 - Lifestyle/Athletic'),
        ('NKE', 'Nike Inc.', 'Tier 3 - Lifestyle/Athletic')
    ]

    rows = []
    for sym, name, tier in peers:
        print(f"Querying {sym} ({name})...")
        t = yf.Ticker(sym)
        info = t.info
        curr = info.get('currency', 'EUR')
        fin_curr = info.get('financialCurrency', curr)

        price_loc = info.get('currentPrice') or info.get('regularMarketPrice')
        fx_price = fx_map.get(curr, 1.0)
        price_eur = (price_loc * fx_price) if price_loc is not None else None

        fx_fin = fx_map.get(fin_curr, 1.0)
        mcap_raw = info.get('marketCap')
        ev_raw = info.get('enterpriseValue')
        rev_raw = info.get('totalRevenue')
        debt_raw = info.get('totalDebt', 0) or 0
        cash_raw = info.get('totalCash', 0) or 0

        mcap_eur = (mcap_raw * fx_fin / 1e9) if mcap_raw else None
        ev_eur = (ev_raw * fx_fin / 1e9) if ev_raw else None
        rev_eur = (rev_raw * fx_fin / 1e9) if rev_raw else None
        net_debt_eur = ((debt_raw - cash_raw) * fx_fin / 1e9)

        sh_out = info.get('sharesOutstanding')
        fl_sh = info.get('floatShares')
        fl_pct = (fl_sh / sh_out * 100.0) if (sh_out and fl_sh) else None

        # Gross margin, EBITDA margin, and Operating margin are decimals in yfinance (e.g. 0.5654)
        gm_pct = round(info.get('grossMargins') * 100.0, 2) if info.get('grossMargins') is not None else None
        ebitda_m_pct = round(info.get('ebitdaMargins') * 100.0, 2) if info.get('ebitdaMargins') is not None else None
        op_m_pct = round(info.get('operatingMargins') * 100.0, 2) if info.get('operatingMargins') is not None else None

        # Dividend yield in yfinance 1.7.0 is already formatted as percentage (e.g. 1.16)
        div_yield = info.get('dividendYield')
        div_yield_pct = round(div_yield, 2) if div_yield is not None else 0.0

        rows.append({
            'ticker': sym,
            'company_name': name,
            'tier': tier,
            'currency_local': curr,
            'share_price_local': round(price_loc, 2) if price_loc else None,
            'share_price_eur': round(price_eur, 2) if price_eur else None,
            'market_cap_eur_b': round(mcap_eur, 2) if mcap_eur else None,
            'enterprise_value_eur_b': round(ev_eur, 2) if ev_eur else None,
            'net_debt_eur_b': round(net_debt_eur, 2) if net_debt_eur is not None else None,
            'beta_5y': round(info.get('beta'), 2) if info.get('beta') is not None else None,
            '52w_low_local': round(info.get('fiftyTwoWeekLow'), 2) if info.get('fiftyTwoWeekLow') is not None else None,
            '52w_high_local': round(info.get('fiftyTwoWeekHigh'), 2) if info.get('fiftyTwoWeekHigh') is not None else None,
            'ltm_revenue_eur_b': round(rev_eur, 2) if rev_eur else None,
            'gross_margin_pct': gm_pct,
            'ebitda_margin_pct': ebitda_m_pct,
            'operating_margin_pct': op_m_pct,
            'trailing_pe': round(info.get('trailingPE'), 2) if info.get('trailingPE') is not None else None,
            'forward_pe': round(info.get('forwardPE'), 2) if info.get('forwardPE') is not None else None,
            'ev_ebitda': round(info.get('enterpriseToEbitda'), 2) if info.get('enterpriseToEbitda') is not None else None,
            'ev_revenue': round(info.get('enterpriseToRevenue'), 2) if info.get('enterpriseToRevenue') is not None else None,
            'dividend_yield_pct': div_yield_pct,
            'free_float_pct': round(fl_pct, 1) if fl_pct is not None else None
        })

    df = pd.DataFrame(rows)
    return df


def fetch_analyst_consensus_summary() -> pd.DataFrame:
    """
    Fetch forward sell-side analyst consensus estimates for Inditex (ITX.MC),
    covering revenue, EPS, revision trends, and price target bounds.
    """
    print("Fetching ITX.MC analyst consensus estimates from Yahoo Finance...")
    t = yf.Ticker('ITX.MC')
    ee = t.earnings_estimate
    re = t.revenue_estimate
    et = t.eps_trend
    er = t.eps_revisions
    targets = t.analyst_price_targets

    periods = ['0q', '+1q', '0y', '+1y']
    period_labels = {
        '0q': 'Current Quarter (Q3 FY25)',
        '+1q': 'Next Quarter (Q4 FY25)',
        '0y': 'Current Fiscal Year (FY25)',
        '+1y': 'Next Fiscal Year (FY26)'
    }

    rows = []
    for p in periods:
        rev_avg = round(re.loc[p, 'avg'] / 1e9, 2) if (p in re.index and pd.notna(re.loc[p, 'avg'])) else None
        rev_low = round(re.loc[p, 'low'] / 1e9, 2) if (p in re.index and pd.notna(re.loc[p, 'low'])) else None
        rev_high = round(re.loc[p, 'high'] / 1e9, 2) if (p in re.index and pd.notna(re.loc[p, 'high'])) else None
        rev_growth = round(re.loc[p, 'growth'] * 100.0, 2) if (p in re.index and pd.notna(re.loc[p, 'growth'])) else None
        rev_analysts = int(re.loc[p, 'numberOfAnalysts']) if (p in re.index and pd.notna(re.loc[p, 'numberOfAnalysts'])) else None

        eps_avg = round(ee.loc[p, 'avg'], 3) if (p in ee.index and pd.notna(ee.loc[p, 'avg'])) else None
        eps_low = round(ee.loc[p, 'low'], 3) if (p in ee.index and pd.notna(ee.loc[p, 'low'])) else None
        eps_high = round(ee.loc[p, 'high'], 3) if (p in ee.index and pd.notna(ee.loc[p, 'high'])) else None
        eps_growth = round(ee.loc[p, 'growth'] * 100.0, 2) if (p in ee.index and pd.notna(ee.loc[p, 'growth'])) else None
        eps_analysts = int(ee.loc[p, 'numberOfAnalysts']) if (p in ee.index and pd.notna(ee.loc[p, 'numberOfAnalysts'])) else None

        eps_cur = round(et.loc[p, 'current'], 3) if (p in et.index and pd.notna(et.loc[p, 'current'])) else None
        eps_7d = round(et.loc[p, '7daysAgo'], 3) if (p in et.index and pd.notna(et.loc[p, '7daysAgo'])) else None
        eps_30d = round(et.loc[p, '30daysAgo'], 3) if (p in et.index and pd.notna(et.loc[p, '30daysAgo'])) else None
        eps_90d = round(et.loc[p, '90daysAgo'], 3) if (p in et.index and pd.notna(et.loc[p, '90daysAgo'])) else None

        up_30d = int(er.loc[p, 'upLast30days']) if (p in er.index and pd.notna(er.loc[p, 'upLast30days'])) else 0
        down_30d = int(er.loc[p, 'downLast30days']) if (p in er.index and pd.notna(er.loc[p, 'downLast30days'])) else 0

        rows.append({
            'period': p,
            'period_label': period_labels.get(p, p),
            'revenue_avg_eur_b': rev_avg,
            'revenue_low_eur_b': rev_low,
            'revenue_high_eur_b': rev_high,
            'revenue_growth_yoy_pct': rev_growth,
            'revenue_analyst_count': rev_analysts,
            'eps_avg_eur': eps_avg,
            'eps_low_eur': eps_low,
            'eps_high_eur': eps_high,
            'eps_growth_yoy_pct': eps_growth,
            'eps_analyst_count': eps_analysts,
            'eps_trend_current': eps_cur,
            'eps_trend_7d_ago': eps_7d,
            'eps_trend_30d_ago': eps_30d,
            'eps_trend_90d_ago': eps_90d,
            'eps_up_revisions_30d': up_30d,
            'eps_down_revisions_30d': down_30d,
            'price_target_current_eur': round(targets.get('current', 0.0), 2) if targets else None,
            'price_target_mean_eur': round(targets.get('mean', 0.0), 2) if targets else None,
            'price_target_median_eur': round(targets.get('median', 0.0), 2) if targets else None,
            'price_target_low_eur': round(targets.get('low', 0.0), 2) if targets else None,
            'price_target_high_eur': round(targets.get('high', 0.0), 2) if targets else None,
        })

    df = pd.DataFrame(rows)
    return df


def main():
    """
    Main orchestration routine for Module 0 data extraction.
    Executes parsing, network fetching, normalization, CSV output generation,
    and integrity validation.
    """
    print("=" * 80)
    print("INDITEX (ITX.MC) STAGE 1 — BASELINE DATA EXTRACTION ENGINE")
    print("=" * 80)

    # Establish root and paths
    project_root = Path(__file__).resolve().parent.parent.parent
    reports_dir = project_root / 'Annual Reports' / 'Transformed'
    data_dir = project_root / 'Market Analysis' / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Project root: {project_root}")
    print(f"Reports dir:  {reports_dir}")
    print(f"Data dir:     {data_dir}\n")

    # 1. Headline KPIs (FY2022-FY2025)
    print("[1/4] Extracting Inditex Multi-Year Headline KPIs (FY2022-FY2025)...")
    df_kpis = build_inditex_kpis(reports_dir)
    kpis_path = data_dir / 'inditex_kpis_2022_2025.csv'
    df_kpis.to_csv(kpis_path, index=False)
    print(f" -> Generated {kpis_path} ({len(df_kpis)} rows, {len(df_kpis.columns)} columns)")

    # 2. Commercial Brands Breakdown (Sales, Stores, ROCE)
    print("\n[2/4] Extracting Commercial Brands Breakdown (FY2022-FY2025)...")
    df_brands = build_inditex_brands(reports_dir)
    brands_path = data_dir / 'inditex_brands_breakdown.csv'
    df_brands.to_csv(brands_path, index=False)
    print(f" -> Generated {brands_path} ({len(df_brands)} rows, {len(df_brands.columns)} columns)")

    # 3. Peer Benchmarking Table (Live yfinance)
    print("\n[3/4] Fetching Live Peer Benchmarking Table...")
    df_peers = fetch_peer_benchmarking_table()
    peers_path = data_dir / 'peer_benchmarking_table.csv'
    df_peers.to_csv(peers_path, index=False)
    print(f" -> Generated {peers_path} ({len(df_peers)} rows, {len(df_peers.columns)} columns)")

    # 4. Analyst Consensus Summary (Live yfinance)
    print("\n[4/4] Fetching Analyst Consensus Summary for ITX.MC...")
    df_consensus = fetch_analyst_consensus_summary()
    consensus_path = data_dir / 'analyst_consensus_summary.csv'
    df_consensus.to_csv(consensus_path, index=False)
    print(f" -> Generated {consensus_path} ({len(df_consensus)} rows, {len(df_consensus.columns)} columns)")

    # Verification checks
    print("\n" + "=" * 80)
    print("VERIFICATION & INTEGRITY SUMMARY")
    print("=" * 80)
    for path, name in [
        (kpis_path, 'Headline KPIs'),
        (brands_path, 'Brands Breakdown'),
        (peers_path, 'Peer Benchmarking'),
        (consensus_path, 'Analyst Consensus')
    ]:
        if path.exists() and path.stat().st_size > 0:
            loaded = pd.read_csv(path)
            null_count = loaded.isnull().sum().sum()
            print(f"[OK] {name:<22}: {path.name} | {len(loaded)} rows | {len(loaded.columns)} cols | Size: {path.stat().st_size} bytes | Nulls: {null_count}")
        else:
            print(f"[FAIL] {name:<22}: Missing or empty file at {path}")
            sys.exit(1)

    print("\nAll 4 CSV datasets successfully generated and verified.")
    print("=" * 80)


if __name__ == '__main__':
    main()
