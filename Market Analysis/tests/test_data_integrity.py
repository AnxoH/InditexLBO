"""
test_data_integrity.py
======================
Empirical verification test suite for Market Analysis/data/ CSV deliverables:
1. inditex_kpis_2022_2025.csv
2. inditex_brands_breakdown.csv
3. peer_benchmarking_table.csv
4. analyst_consensus_summary.csv

Tests:
- Zero null / missing / NaN values across all datasets.
- Schema conformity and row count validation.
- Accounting identity invariants (P&L, Net Cash, Working Capital, Capex).
- Concept aggregation consistency (sales sum, store sum, share sums).
- Peer benchmarking multiple realism and valuation bands.
- Analyst consensus bounds consistency (low <= avg <= high).
"""

from pathlib import Path
import unittest
import pandas as pd


class TestDataIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        cls.data_dir = cls.project_root / 'Market Analysis' / 'data'

        cls.kpis_path = cls.data_dir / 'inditex_kpis_2022_2025.csv'
        cls.brands_path = cls.data_dir / 'inditex_brands_breakdown.csv'
        cls.peers_path = cls.data_dir / 'peer_benchmarking_table.csv'
        cls.consensus_path = cls.data_dir / 'analyst_consensus_summary.csv'

        cls.df_kpis = pd.read_csv(cls.kpis_path)
        cls.df_brands = pd.read_csv(cls.brands_path)
        cls.df_peers = pd.read_csv(cls.peers_path)
        cls.df_consensus = pd.read_csv(cls.consensus_path)

    def test_files_exist_and_non_empty(self):
        """Verify all 4 CSV datasets exist and have non-zero size."""
        for path, name in [
            (self.kpis_path, 'inditex_kpis_2022_2025.csv'),
            (self.brands_path, 'inditex_brands_breakdown.csv'),
            (self.peers_path, 'peer_benchmarking_table.csv'),
            (self.consensus_path, 'analyst_consensus_summary.csv')
        ]:
            self.assertTrue(path.exists(), f"File missing: {name}")
            self.assertGreater(path.stat().st_size, 0, f"File empty: {name}")

    def test_zero_null_values_across_all_csvs(self):
        """Verify that there are exactly zero null/missing/NaN values in all datasets."""
        datasets = {
            'inditex_kpis_2022_2025.csv': self.df_kpis,
            'inditex_brands_breakdown.csv': self.df_brands,
            'peer_benchmarking_table.csv': self.df_peers,
            'analyst_consensus_summary.csv': self.df_consensus
        }

        for name, df in datasets.items():
            null_counts = df.isnull().sum()
            total_nulls = null_counts.sum()
            self.assertEqual(
                total_nulls, 0,
                f"Dataset {name} contains {total_nulls} null values! Columns with nulls: {null_counts[null_counts > 0].to_dict()}"
            )

    def test_kpis_schema_and_rows(self):
        """Verify headline KPIs schema, row count (4 years: FY22-FY25), and chronological order."""
        self.assertEqual(len(self.df_kpis), 4, f"Expected 4 rows in KPIs, got {len(self.df_kpis)}")
        expected_years = ['FY2022', 'FY2023', 'FY2024', 'FY2025']
        self.assertListEqual(list(self.df_kpis['fiscal_year']), expected_years)

        expected_columns = [
            'fiscal_year', 'period_end_date', 'net_sales_eur_m', 'net_sales_growth_reported_pct',
            'net_sales_growth_constant_fx_pct', 'cost_of_merchandise_eur_m', 'gross_profit_eur_m',
            'gross_margin_pct', 'opex_eur_m', 'opex_growth_pct', 'ebitda_eur_m',
            'ebitda_margin_pct', 'd_and_a_eur_m', 'extraordinary_items_eur_m', 'ebit_eur_m',
            'ebit_margin_pct', 'ebt_eur_m', 'tax_expense_eur_m', 'effective_tax_rate_pct',
            'net_income_eur_m', 'eps_eur', 'net_cash_eur_m', 'cash_and_equivalents_eur_m',
            'current_financial_investments_eur_m', 'gross_financial_debt_eur_m',
            'operating_working_capital_eur_m', 'ordinary_capex_eur_m',
            'extraordinary_logistics_capex_eur_m', 'total_capex_eur_m', 'free_cash_flow_eur_m',
            'dividend_paid_per_share_eur', 'dividend_proposed_per_share_eur',
            'total_shares_outstanding_m'
        ]
        for col in expected_columns:
            self.assertIn(col, self.df_kpis.columns, f"Missing KPI column: {col}")

    def test_kpis_accounting_identities(self):
        """Verify accounting identities in headline KPIs."""
        for _, row in self.df_kpis.iterrows():
            year = row['fiscal_year']
            # 1. Gross Profit = Net Sales + Cost of Merchandise (cost is negative)
            calc_gp = row['net_sales_eur_m'] + row['cost_of_merchandise_eur_m']
            self.assertAlmostEqual(
                calc_gp, row['gross_profit_eur_m'], delta=1.5,
                msg=f"{year}: Gross profit mismatch: {calc_gp} vs {row['gross_profit_eur_m']}"
            )

            # 2. Gross Margin % = Gross Profit / Net Sales * 100
            calc_gm_pct = (row['gross_profit_eur_m'] / row['net_sales_eur_m']) * 100.0
            self.assertAlmostEqual(
                calc_gm_pct, row['gross_margin_pct'], delta=0.2,
                msg=f"{year}: Gross margin % mismatch: {calc_gm_pct:.2f}% vs {row['gross_margin_pct']}%"
            )

            # 3. EBITDA to EBIT bridge: EBITDA + D&A + Extraordinary = EBIT (D&A is negative)
            calc_ebit = row['ebitda_eur_m'] + row['d_and_a_eur_m'] + row['extraordinary_items_eur_m']
            self.assertAlmostEqual(
                calc_ebit, row['ebit_eur_m'], delta=2.0,
                msg=f"{year}: EBIT bridge mismatch: {calc_ebit} vs {row['ebit_eur_m']}"
            )

            # 4. EBIT margin % = EBIT / Net Sales * 100
            calc_ebit_pct = (row['ebit_eur_m'] / row['net_sales_eur_m']) * 100.0
            self.assertAlmostEqual(
                calc_ebit_pct, row['ebit_margin_pct'], delta=0.2,
                msg=f"{year}: EBIT margin % mismatch: {calc_ebit_pct:.2f}% vs {row['ebit_margin_pct']}%"
            )

            # 5. Net Cash = Cash & Equivalents + Current Financial Investments - Gross Financial Debt
            calc_net_cash = (
                row['cash_and_equivalents_eur_m'] +
                row['current_financial_investments_eur_m'] -
                row['gross_financial_debt_eur_m']
            )
            self.assertAlmostEqual(
                calc_net_cash, row['net_cash_eur_m'], delta=1.0,
                msg=f"{year}: Net cash identity mismatch: {calc_net_cash} vs {row['net_cash_eur_m']}"
            )

            # 6. Total Capex = Ordinary Capex + Extraordinary Logistics Capex
            calc_capex = row['ordinary_capex_eur_m'] + row['extraordinary_logistics_capex_eur_m']
            self.assertAlmostEqual(
                calc_capex, row['total_capex_eur_m'], delta=0.1,
                msg=f"{year}: Capex breakdown mismatch: {calc_capex} vs {row['total_capex_eur_m']}"
            )

            # 7. EPS = Net Income / Total Shares Outstanding
            calc_eps = row['net_income_eur_m'] / row['total_shares_outstanding_m']
            self.assertAlmostEqual(
                calc_eps, row['eps_eur'], delta=0.01,
                msg=f"{year}: EPS calculation mismatch: {calc_eps:.3f} vs {row['eps_eur']}"
            )

    def test_brands_breakdown_consistency(self):
        """Verify commercial concept breakdown aggregations and consistency."""
        # 6 concepts + Total Group = 7 entities * 4 years = 28 rows
        self.assertEqual(len(self.df_brands), 28, f"Expected 28 rows in brands breakdown, got {len(self.df_brands)}")

        concepts = [
            'Zara (incl. Zara Home & Lefties)',
            'Pull&Bear',
            'Massimo Dutti',
            'Bershka',
            'Stradivarius',
            'Oysho'
        ]

        for year in ['FY2022', 'FY2023', 'FY2024', 'FY2025']:
            year_df = self.df_brands[self.df_brands['fiscal_year'] == year]
            total_row = year_df[year_df['brand'] == 'Total Group'].iloc[0]
            concepts_df = year_df[year_df['brand'].isin(concepts)]

            self.assertEqual(len(concepts_df), 6, f"{year}: Expected 6 concept rows")

            # 1. Sum of concept sales == Total Group sales
            sum_sales = concepts_df['net_sales_eur_m'].sum()
            self.assertAlmostEqual(
                sum_sales, total_row['net_sales_eur_m'], delta=1.0,
                msg=f"{year}: Sum of concept sales ({sum_sales}) != Total Group ({total_row['net_sales_eur_m']})"
            )

            # 2. Sum of concept store counts == Total Group store counts
            sum_stores = concepts_df['store_count'].sum()
            self.assertEqual(
                sum_stores, total_row['store_count'],
                msg=f"{year}: Sum of concept stores ({sum_stores}) != Total Group ({total_row['store_count']})"
            )

            # 3. Sum of sales share % == 100%
            sum_sales_share = concepts_df['sales_share_pct'].sum()
            self.assertAlmostEqual(
                sum_sales_share, 100.0, delta=0.5,
                msg=f"{year}: Concept sales share does not sum to 100%: {sum_sales_share}%"
            )

            # 4. Sum of store share % == 100%
            sum_store_share = concepts_df['store_share_pct'].sum()
            self.assertAlmostEqual(
                sum_store_share, 100.0, delta=0.5,
                msg=f"{year}: Concept store share does not sum to 100%: {sum_store_share}%"
            )

            # 5. ROCE % within realistic operating bounds [20%, 80%]
            for _, r in concepts_df.iterrows():
                self.assertGreaterEqual(r['roce_pct'], 20.0, f"{year} {r['brand']}: ROCE abnormally low: {r['roce_pct']}%")
                self.assertLessEqual(r['roce_pct'], 80.0, f"{year} {r['brand']}: ROCE abnormally high: {r['roce_pct']}%")

    def test_peer_benchmarking_table(self):
        """Verify peer benchmarking dataset completeness and multiple reasonableness."""
        self.assertEqual(len(self.df_peers), 9, f"Expected 9 peer rows, got {len(self.df_peers)}")

        expected_tickers = {
            'ITX.MC': 'Target',
            'HM-B.ST': 'Tier 1 - Core',
            '9983.T': 'Tier 1 - Core',
            'NXT.L': 'Tier 1 - Core',
            'GAP': 'Tier 1 - Core',
            'ABF.L': 'Tier 1 - Core',
            'LULU': 'Tier 3 - Lifestyle/Athletic',
            'ADS.DE': 'Tier 3 - Lifestyle/Athletic',
            'NKE': 'Tier 3 - Lifestyle/Athletic'
        }

        for ticker, tier in expected_tickers.items():
            row = self.df_peers[self.df_peers['ticker'] == ticker]
            self.assertEqual(len(row), 1, f"Missing or duplicate ticker in peers: {ticker}")
            self.assertEqual(row.iloc[0]['tier'], tier, f"Wrong tier for {ticker}")

        # Check financial multiple realism
        for _, r in self.df_peers.iterrows():
            ticker = r['ticker']
            self.assertGreater(r['share_price_eur'], 0.0, f"{ticker}: Share price EUR <= 0")
            self.assertGreater(r['market_cap_eur_b'], 1.0, f"{ticker}: Market cap EUR <= 1B")
            self.assertGreater(r['enterprise_value_eur_b'], 1.0, f"{ticker}: Enterprise value EUR <= 1B")
            self.assertGreater(r['ltm_revenue_eur_b'], 1.0, f"{ticker}: LTM Revenue EUR <= 1B")

            # Valuation multiple sanity bands
            self.assertTrue(5.0 <= r['trailing_pe'] <= 60.0, f"{ticker}: Trailing P/E out of bounds: {r['trailing_pe']}")
            self.assertTrue(5.0 <= r['forward_pe'] <= 60.0, f"{ticker}: Forward P/E out of bounds: {r['forward_pe']}")
            self.assertTrue(3.0 <= r['ev_ebitda'] <= 30.0, f"{ticker}: EV/EBITDA out of bounds: {r['ev_ebitda']}")
            self.assertTrue(0.3 <= r['ev_revenue'] <= 10.0, f"{ticker}: EV/Revenue out of bounds: {r['ev_revenue']}")

            # Margin sanity bands
            self.assertTrue(5.0 <= r['gross_margin_pct'] <= 70.0, f"{ticker}: Gross margin out of bounds: {r['gross_margin_pct']}")
            self.assertTrue(5.0 <= r['ebitda_margin_pct'] <= 35.0, f"{ticker}: EBITDA margin out of bounds: {r['ebitda_margin_pct']}")
            self.assertTrue(3.0 <= r['operating_margin_pct'] <= 25.0, f"{ticker}: Operating margin out of bounds: {r['operating_margin_pct']}")

            # Beta and float sanity bands
            self.assertTrue(0.3 <= r['beta_5y'] <= 2.5, f"{ticker}: Beta out of bounds: {r['beta_5y']}")
            self.assertTrue(10.0 <= r['free_float_pct'] <= 100.0, f"{ticker}: Free float out of bounds: {r['free_float_pct']}")

    def test_analyst_consensus_bounds(self):
        """Verify analyst consensus projections follow mathematical ordering (low <= avg <= high)."""
        self.assertEqual(len(self.df_consensus), 4, f"Expected 4 periods in consensus summary, got {len(self.df_consensus)}")
        expected_periods = ['0q', '+1q', '0y', '+1y']
        self.assertListEqual(list(self.df_consensus['period']), expected_periods)

        for _, r in self.df_consensus.iterrows():
            period = r['period']
            # Revenue bounds: low <= avg <= high
            self.assertLessEqual(
                r['revenue_low_eur_b'], r['revenue_avg_eur_b'],
                f"{period}: Revenue low ({r['revenue_low_eur_b']}) > avg ({r['revenue_avg_eur_b']})"
            )
            self.assertLessEqual(
                r['revenue_avg_eur_b'], r['revenue_high_eur_b'],
                f"{period}: Revenue avg ({r['revenue_avg_eur_b']}) > high ({r['revenue_high_eur_b']})"
            )

            # EPS bounds: low <= avg <= high
            self.assertLessEqual(
                r['eps_low_eur'], r['eps_avg_eur'],
                f"{period}: EPS low ({r['eps_low_eur']}) > avg ({r['eps_avg_eur']})"
            )
            self.assertLessEqual(
                r['eps_avg_eur'], r['eps_high_eur'],
                f"{period}: EPS avg ({r['eps_avg_eur']}) > high ({r['eps_high_eur']})"
            )

            # Price target bounds: low <= mean <= high
            self.assertLessEqual(
                r['price_target_low_eur'], r['price_target_mean_eur'],
                f"{period}: Target low ({r['price_target_low_eur']}) > mean ({r['price_target_mean_eur']})"
            )
            self.assertLessEqual(
                r['price_target_mean_eur'], r['price_target_high_eur'],
                f"{period}: Target mean ({r['price_target_mean_eur']}) > high ({r['price_target_high_eur']})"
            )

            # Analyst coverage counts > 0
            self.assertGreater(r['revenue_analyst_count'], 0, f"{period}: Zero revenue analysts")
            self.assertGreater(r['eps_analyst_count'], 0, f"{period}: Zero EPS analysts")


if __name__ == '__main__':
    unittest.main()
