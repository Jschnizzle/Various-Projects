#!/usr/bin/env python3
"""
Investment Scoring Methodology - Z-Score Version
Incorporates z-score normalization from Sungjin.ipynb analysis
Uses statistical standardization instead of min-max normalization
"""

import pandas as pd
import numpy as np
from pathlib import Path

class ZScoreCountyScoringMethodology:
    def __init__(self):
        self.data_dir = Path('housing_market_data/processed')
        
    def load_all_county_data(self):
        """Load and calculate metrics for ALL CA counties"""
        print("\n" + "="*100)
        print("📊 LOADING ALL CALIFORNIA COUNTIES (Z-SCORE METHOD)")
        print("="*100)
        
        df = pd.read_csv(self.data_dir / 'ca_county_master.csv')
        df['date'] = pd.to_datetime(df['date'])
        
        # Get all unique counties
        all_counties = df['RegionName'].unique()
        print(f"\nTotal Counties Found: {len(all_counties)}")
        
        # Calculate metrics for each county
        metrics = []
        counties_processed = 0
        counties_skipped = 0
        
        for county in sorted(all_counties):
            county_data = df[df['RegionName'] == county].sort_values('date')
            
            # Need at least 36 months of data (3 years)
            if len(county_data) < 36:
                counties_skipped += 1
                continue
            
            # Check if we have recent data
            max_date = county_data['date'].max()
            if max_date < pd.Timestamp('2023-01-01'):
                counties_skipped += 1
                continue
            
            # Latest price
            latest_price = county_data['zhvi'].iloc[-1]
            
            # Skip if price data is missing
            if pd.isna(latest_price):
                counties_skipped += 1
                continue
            
            # YoY growth (1 year)
            year_ago = county_data[county_data['date'] <= county_data['date'].max() - pd.DateOffset(months=12)]
            if not year_ago.empty and not pd.isna(year_ago['zhvi'].iloc[-1]):
                yoy_growth = ((latest_price - year_ago['zhvi'].iloc[-1]) / year_ago['zhvi'].iloc[-1]) * 100
            else:
                yoy_growth = 0
            
            # 3-year CAGR (primary metric for z-score)
            three_years_ago = county_data[county_data['date'] <= county_data['date'].max() - pd.DateOffset(years=3)]
            if not three_years_ago.empty and not pd.isna(three_years_ago['zhvi'].iloc[0]):
                years = (county_data['date'].iloc[-1] - three_years_ago['date'].iloc[0]).days / 365.25
                cagr_3y = (((latest_price / three_years_ago['zhvi'].iloc[0]) ** (1/years)) - 1) * 100
            else:
                cagr_3y = 0
            
            # Population growth (demographics)
            pop_data = county_data.dropna(subset=['population'])
            if len(pop_data) >= 2:
                pop_growth = ((pop_data['population'].iloc[-1] - pop_data['population'].iloc[0]) / 
                             pop_data['population'].iloc[0]) * 100
            else:
                pop_growth = 0
            
            metrics.append({
                'county': county,
                'price': latest_price,
                'yoy_growth': yoy_growth,
                'cagr_3y': cagr_3y,
                'pop_growth': pop_growth,
                'data_months': len(county_data),
                'latest_date': max_date
            })
            
            counties_processed += 1
        
        print(f"\n✅ Successfully processed: {counties_processed} counties")
        print(f"⚠️  Skipped: {counties_skipped} counties")
        print("="*100)
        
        return pd.DataFrame(metrics)
    
    def estimate_yields(self, df):
        """Estimate rental yields for all counties"""
        def estimate_yield(price):
            if price < 350000:
                return 6.5
            elif price < 450000:
                return 6.0
            elif price < 550000:
                return 5.5
            elif price < 700000:
                return 5.0
            else:
                return 4.5
        
        df['yield'] = df['price'].apply(estimate_yield)
        return df
    
    def zscore(self, series):
        """Calculate z-score for a series (Sungjin's method)"""
        mean = series.mean()
        std = series.std()
        if std == 0:
            return pd.Series([0] * len(series), index=series.index)
        return (series - mean) / std
    
    def calculate_scores_zscore(self, df):
        """Apply z-score based scoring (inspired by Sungjin's methodology)"""
        print("\n" + "="*100)
        print("🔢 Z-SCORE INVESTMENT SCORING METHODOLOGY")
        print("="*100)
        
        print("\n📐 Z-SCORE METHOD (Sungjin's Approach):")
        print("-" * 100)
        print("""
        Z-Score Formula: z = (value - mean) / standard_deviation
        
        This standardizes all metrics to the same scale:
        - z = 0 means average
        - z > 0 means above average (good)
        - z < 0 means below average (bad)
        - z ≈ ±2 means 2 standard deviations from mean (exceptional)
        
        SCORING COMPONENTS:
        
        1. GROWTH Z-SCORE (50% weight)
           - Based on 3-Year CAGR (70%) + YoY Growth (30%)
           - Rationale: Primary appreciation metric
           
        2. AFFORDABILITY Z-SCORE (25% weight)
           - INVERTED price z-score (lower price = higher score)
           - Rationale: Lower entry = better opportunity
           
        3. DEMOGRAPHICS Z-SCORE (15% weight)
           - Population growth rate
           - Rationale: Demand driver
           
        4. YIELD Z-SCORE (10% weight)
           - Estimated rental yield
           - Rationale: Cash flow contribution
        
        Final Score = 0.50 * z_growth + 0.25 * z_afford + 0.15 * z_demo + 0.10 * z_yield
        """)
        
        # Estimate yields
        df = self.estimate_yields(df)
        
        # Calculate combined growth metric (like Sungjin: 3Y CAGR primary)
        df['growth_combined'] = (df['cagr_3y'] * 0.7) + (df['yoy_growth'] * 0.3)
        
        print(f"\n📊 DATA SUMMARY:")
        print("-" * 100)
        print(f"Median Price: ${df['price'].median():,.0f}")
        print(f"Mean Price: ${df['price'].mean():,.0f}")
        print(f"Price Std Dev: ${df['price'].std():,.0f}")
        print(f"\nMean 3Y CAGR: {df['cagr_3y'].mean():.2f}%")
        print(f"Std Dev 3Y CAGR: {df['cagr_3y'].std():.2f}%")
        print(f"\nMean YoY Growth: {df['yoy_growth'].mean():.2f}%")
        print(f"Std Dev YoY Growth: {df['yoy_growth'].std():.2f}%")
        print(f"\nMean Pop Growth: {df['pop_growth'].mean():.2f}%")
        print(f"Std Dev Pop Growth: {df['pop_growth'].std():.2f}%")
        print()
        
        # Calculate z-scores
        df['z_growth'] = self.zscore(df['growth_combined'])
        df['z_price'] = self.zscore(df['price'])
        df['z_affordability'] = -df['z_price']  # Invert: lower price = higher affordability
        df['z_demographics'] = self.zscore(df['pop_growth'])
        df['z_yield'] = self.zscore(df['yield'])
        
        # Calculate weighted final score using z-scores
        df['z_score_final'] = (
            df['z_growth'] * 0.50 +
            df['z_affordability'] * 0.25 +
            df['z_demographics'] * 0.15 +
            df['z_yield'] * 0.10
        )
        
        # Also keep the old min-max normalized score for comparison
        def normalize_minmax(series):
            min_val = series.min()
            max_val = series.max()
            if max_val == min_val:
                return pd.Series([50] * len(series), index=series.index)
            return ((series - min_val) / (max_val - min_val)) * 100
        
        df['affordability_raw'] = ((df['price'].median() - df['price']) / df['price'].median()) * 100
        df['affordability_norm'] = normalize_minmax(df['affordability_raw'])
        df['growth_norm'] = normalize_minmax(df['growth_combined'])
        df['demographic_norm'] = normalize_minmax(df['pop_growth'] * 10)
        df['yield_norm'] = normalize_minmax(df['yield'])
        
        df['final_score_old'] = (
            df['affordability_norm'] * 0.30 +
            df['growth_norm'] * 0.40 +
            df['demographic_norm'] * 0.20 +
            df['yield_norm'] * 0.10
        )
        
        # Convert z-score to 0-100 scale for easier interpretation
        # Assuming z-scores typically range from -3 to +3
        df['z_score_normalized'] = ((df['z_score_final'] + 3) / 6) * 100
        df['z_score_normalized'] = df['z_score_normalized'].clip(0, 100)
        
        # Sort by z-score
        df = df.sort_values('z_score_final', ascending=False).reset_index(drop=True)
        
        return df
    
    def show_top_counties_comparison(self, df, top_n=20):
        """Show top N counties with both scoring methods"""
        print("\n" + "="*130)
        print(f"🏆 TOP {top_n} COUNTIES - Z-SCORE vs OLD METHOD COMPARISON")
        print("="*130)
        
        print(f"\n{'Rank':<6} {'County':<25} {'Z-Score':<10} {'Old Score':<10} {'Price':<12} {'Growth':<10} {'Pop%':<8}")
        print("-" * 130)
        
        for idx, row in df.head(top_n).iterrows():
            rank = idx + 1
            print(f"{rank:<6} {row['county']:<25} "
                  f"{row['z_score_final']:>8.2f}  {row['final_score_old']:>8.1f}  "
                  f"${row['price']:<11,.0f} {row['growth_combined']:>8.2f}% {row['pop_growth']:>6.2f}%")
        
        print("-" * 130)
    
    def show_ranking_differences(self, df):
        """Show how rankings differ between methods"""
        print("\n" + "="*100)
        print("📊 RANKING COMPARISON: Z-Score vs Old Method")
        print("="*100)
        
        # Create separate rankings
        df['rank_zscore'] = df['z_score_final'].rank(ascending=False).astype(int)
        df_old_sorted = df.sort_values('final_score_old', ascending=False).reset_index(drop=True)
        df_old_sorted['rank_old'] = range(1, len(df_old_sorted) + 1)
        
        # Merge rankings
        df = df.merge(df_old_sorted[['county', 'rank_old']], on='county', how='left')
        df['rank_change'] = df['rank_old'] - df['rank_zscore']
        
        print("\n🔼 BIGGEST GAINERS (Z-Score Method):")
        print("-" * 100)
        gainers = df.nlargest(10, 'rank_change')
        for _, row in gainers.iterrows():
            print(f"   • {row['county']:<25} Old: #{row['rank_old']:<3.0f} → New: #{row['rank_zscore']:<3} "
                  f"(+{row['rank_change']:.0f}) | Growth: {row['growth_combined']:>6.2f}%")
        
        print("\n🔽 BIGGEST LOSERS (Z-Score Method):")
        print("-" * 100)
        losers = df.nsmallest(10, 'rank_change')
        for _, row in losers.iterrows():
            print(f"   • {row['county']:<25} Old: #{row['rank_old']:<3.0f} → New: #{row['rank_zscore']:<3} "
                  f"({row['rank_change']:.0f}) | Growth: {row['growth_combined']:>6.2f}%")
        
        return df
    
    def detailed_breakdown_top_10(self, df):
        """Show detailed z-score breakdown for top 10"""
        print("\n" + "="*120)
        print("📋 DETAILED Z-SCORE BREAKDOWN - TOP 10 COUNTIES")
        print("="*120)
        
        for idx, row in df.head(10).iterrows():
            rank = idx + 1
            print(f"\n{'='*120}")
            print(f"#{rank}  {row['county'].upper()}")
            print(f"{'='*120}")
            
            print(f"\n📊 Z-SCORE COMPONENTS:")
            print(f"   Growth Z-Score (50%):        {row['z_growth']:>6.2f}  →  Weighted: {row['z_growth'] * 0.50:>6.2f}")
            print(f"   Affordability Z-Score (25%): {row['z_affordability']:>6.2f}  →  Weighted: {row['z_affordability'] * 0.25:>6.2f}")
            print(f"   Demographics Z-Score (15%):  {row['z_demographics']:>6.2f}  →  Weighted: {row['z_demographics'] * 0.15:>6.2f}")
            print(f"   Yield Z-Score (10%):         {row['z_yield']:>6.2f}  →  Weighted: {row['z_yield'] * 0.10:>6.2f}")
            
            print(f"\n💰 RAW METRICS:")
            print(f"   Price: ${row['price']:,.0f}")
            print(f"   YoY Growth: {row['yoy_growth']:+.2f}%")
            print(f"   3Y CAGR: {row['cagr_3y']:+.2f}%")
            print(f"   Combined Growth: {row['growth_combined']:+.2f}%")
            print(f"   Population Growth: {row['pop_growth']:+.2f}%")
            print(f"   Estimated Yield: {row['yield']:.1f}%")
            
            print(f"\n🏆 FINAL Z-SCORE: {row['z_score_final']:.2f}")
            print(f"   (Normalized to 0-100: {row['z_score_normalized']:.1f}/100)")
            print(f"   (Old Method Score: {row['final_score_old']:.1f}/100)")
    
    def save_results(self, df):
        """Save z-score ranking to CSV"""
        output_file = self.data_dir / 'all_counties_ranking_zscore.csv'
        
        # Select key columns for output
        output_df = df[[
            'county', 'price', 'yoy_growth', 'cagr_3y', 'growth_combined', 'pop_growth', 'yield',
            'z_growth', 'z_affordability', 'z_demographics', 'z_yield',
            'z_score_final', 'z_score_normalized', 
            'final_score_old', 'rank_zscore', 'rank_old', 'rank_change',
            'data_months', 'latest_date'
        ]].copy()
        
        output_df.to_csv(output_file, index=False)
        print(f"\n✅ Z-Score ranking saved to: {output_file}")
        print(f"   Total counties ranked: {len(output_df)}")
        
        return output_file
    
    def run(self):
        """Run complete z-score analysis"""
        print("\n" + "="*100)
        print("🔬 Z-SCORE INVESTMENT SCORING METHODOLOGY - ALL CALIFORNIA COUNTIES")
        print("="*100)
        
        # Load data
        df = self.load_all_county_data()
        
        if len(df) == 0:
            print("\n❌ No counties to process!")
            return None
        
        # Calculate z-scores
        df = self.calculate_scores_zscore(df)
        
        # Show results
        self.show_top_counties_comparison(df, top_n=20)
        
        # Show ranking differences
        df = self.show_ranking_differences(df)
        
        # Detailed breakdown
        self.detailed_breakdown_top_10(df)
        
        # Save results
        output_file = self.save_results(df)
        
        print("\n" + "="*100)
        print("✓ Z-SCORE ANALYSIS COMPLETE")
        print("="*100)
        print("\n💡 KEY DIFFERENCES FROM OLD METHOD:")
        print("   • Uses statistical z-scores instead of min-max normalization")
        print("   • More weight on growth (50% vs 40%)")
        print("   • Better handling of outliers")
        print("   • Standardized scale across all metrics")
        print()
        
        return df

if __name__ == "__main__":
    methodology = ZScoreCountyScoringMethodology()
    methodology.run()
