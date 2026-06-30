#!/usr/bin/env python3
"""
Investment Scoring Methodology - ALL California Counties
Applies the balanced scoring formula to ALL counties, not just top 5
"""

import pandas as pd
import numpy as np
from pathlib import Path

class AllCountyScoringMethodology:
    def __init__(self):
        self.data_dir = Path('housing_market_data/processed')
        
    def load_all_county_data(self):
        """Load and calculate metrics for ALL CA counties"""
        print("\n" + "="*100)
        print("📊 LOADING ALL CALIFORNIA COUNTIES")
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
                print(f"⚠️  Skipping {county}: insufficient data ({len(county_data)} months)")
                counties_skipped += 1
                continue
            
            # Check if we have recent data
            max_date = county_data['date'].max()
            if max_date < pd.Timestamp('2023-01-01'):
                print(f"⚠️  Skipping {county}: data too old (latest: {max_date.date()})")
                counties_skipped += 1
                continue
            
            # Latest price
            latest_price = county_data['zhvi'].iloc[-1]
            
            # Skip if price data is missing
            if pd.isna(latest_price):
                print(f"⚠️  Skipping {county}: missing price data")
                counties_skipped += 1
                continue
            
            # YoY growth
            year_ago = county_data[county_data['date'] <= county_data['date'].max() - pd.DateOffset(months=12)]
            if not year_ago.empty and not pd.isna(year_ago['zhvi'].iloc[-1]):
                yoy_growth = ((latest_price - year_ago['zhvi'].iloc[-1]) / year_ago['zhvi'].iloc[-1]) * 100
            else:
                yoy_growth = 0
            
            # 3-year CAGR
            three_years_ago = county_data[county_data['date'] <= county_data['date'].max() - pd.DateOffset(years=3)]
            if not three_years_ago.empty and not pd.isna(three_years_ago['zhvi'].iloc[0]):
                years = (county_data['date'].iloc[-1] - three_years_ago['date'].iloc[0]).days / 365.25
                cagr = (((latest_price / three_years_ago['zhvi'].iloc[0]) ** (1/years)) - 1) * 100
            else:
                cagr = 0
            
            # Population growth (if available)
            pop_data = county_data.dropna(subset=['population'])
            if len(pop_data) >= 2:
                pop_growth = ((pop_data['population'].iloc[-1] - pop_data['population'].iloc[0]) / 
                             pop_data['population'].iloc[0]) * 100
            else:
                pop_growth = 0  # Default if no population data
            
            metrics.append({
                'county': county,
                'price': latest_price,
                'yoy_growth': yoy_growth,
                'cagr_3y': cagr,
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
        # Use market research and estimates
        # Lower price counties generally have higher yields
        # Adjust based on price tier
        
        def estimate_yield(price):
            if price < 350000:
                return 6.5  # Higher yield for lower prices
            elif price < 450000:
                return 6.0
            elif price < 550000:
                return 5.5
            elif price < 700000:
                return 5.0
            else:
                return 4.5  # Lower yield for expensive areas
        
        df['yield'] = df['price'].apply(estimate_yield)
        return df
    
    def calculate_scores(self, df):
        """Apply scoring formula to all counties"""
        print("\n" + "="*100)
        print("🔢 INVESTMENT SCORING METHODOLOGY - ALL COUNTIES")
        print("="*100)
        
        print("\n📐 SCORING FORMULA:")
        print("-" * 100)
        print("""
        Total Score = (Affordability × 30%) + (Growth × 40%) + (Demographics × 20%) + (Yield × 10%)
        
        WHERE:
        
        1. AFFORDABILITY SCORE (30% weight)
           - Lower price = Higher score
           - Formula: (Median_CA_Price - County_Price) / Median_CA_Price × 100
           - Rationale: Easier entry, better risk/reward for appreciation
           
        2. GROWTH SCORE (40% weight) - MOST IMPORTANT
           - Based on YoY Growth (70%) + 3-Year CAGR (30%)
           - Formula: (YoY_Growth × 0.70 + CAGR_3Y × 0.30)
           - Rationale: Recent momentum + proven track record
           
        3. DEMOGRAPHIC SCORE (20% weight)
           - Population growth rate
           - Formula: Pop_Growth_Rate × 10
           - Rationale: Growing population = sustained demand
           
        4. YIELD SCORE (10% weight)
           - Estimated rental yield
           - Formula: (Annual_Rent / Purchase_Price) × 10
           - Rationale: Cash flow matters, but appreciation more important
        """)
        
        # Estimate yields
        df = self.estimate_yields(df)
        
        # Calculate median CA price for affordability scoring
        median_ca_price = df['price'].median()
        
        print(f"\n📊 DATA SUMMARY:")
        print("-" * 100)
        print(f"California Median Home Price: ${median_ca_price:,.0f}")
        print(f"Price Range: ${df['price'].min():,.0f} - ${df['price'].max():,.0f}")
        print(f"YoY Growth Range: {df['yoy_growth'].min():.2f}% - {df['yoy_growth'].max():.2f}%")
        print(f"CAGR Range: {df['cagr_3y'].min():.2f}% - {df['cagr_3y'].max():.2f}%")
        print()
        
        # Add affordability score
        df['affordability_raw'] = ((median_ca_price - df['price']) / median_ca_price) * 100
        
        # Add growth score (YoY 70%, CAGR 30%)
        df['growth_raw'] = (df['yoy_growth'] * 0.7) + (df['cagr_3y'] * 0.3)
        
        # Add demographic score
        df['demographic_raw'] = df['pop_growth'] * 10
        
        # Yield raw
        df['yield_raw'] = df['yield']
        
        # Normalize all scores to 0-100 scale for fair weighting
        def normalize(series):
            min_val = series.min()
            max_val = series.max()
            if max_val == min_val:
                return pd.Series([50] * len(series), index=series.index)
            return ((series - min_val) / (max_val - min_val)) * 100
        
        df['affordability_norm'] = normalize(df['affordability_raw'])
        df['growth_norm'] = normalize(df['growth_raw'])
        df['demographic_norm'] = normalize(df['demographic_raw'])
        df['yield_norm'] = normalize(df['yield_raw'])
        
        # Calculate weighted final score
        df['final_score'] = (
            df['affordability_norm'] * 0.30 +
            df['growth_norm'] * 0.40 +
            df['demographic_norm'] * 0.20 +
            df['yield_norm'] * 0.10
        )
        
        # Sort by final score
        df = df.sort_values('final_score', ascending=False).reset_index(drop=True)
        
        return df
    
    def show_top_counties(self, df, top_n=20):
        """Show top N counties"""
        print("\n" + "="*120)
        print(f"🏆 TOP {top_n} CALIFORNIA COUNTIES - INVESTMENT RANKING")
        print("="*120)
        
        print(f"\n{'Rank':<6} {'County':<25} {'Price':<12} {'YoY%':<8} {'CAGR%':<8} {'Pop%':<8} {'Yield%':<8} {'Score':<8}")
        print("-" * 120)
        
        for idx, row in df.head(top_n).iterrows():
            rank = idx + 1
            print(f"{rank:<6} {row['county']:<25} ${row['price']:<11,.0f} "
                  f"{row['yoy_growth']:>6.2f}% {row['cagr_3y']:>6.2f}% "
                  f"{row['pop_growth']:>6.2f}% {row['yield']:>6.1f}% "
                  f"{row['final_score']:>6.1f}")
        
        print("-" * 120)
    
    def show_bottom_counties(self, df, bottom_n=10):
        """Show bottom N counties"""
        print("\n" + "="*120)
        print(f"📊 BOTTOM {bottom_n} CALIFORNIA COUNTIES")
        print("="*120)
        
        print(f"\n{'Rank':<6} {'County':<25} {'Price':<12} {'YoY%':<8} {'CAGR%':<8} {'Pop%':<8} {'Yield%':<8} {'Score':<8}")
        print("-" * 120)
        
        total = len(df)
        for idx, row in df.tail(bottom_n).iterrows():
            rank = total - (len(df) - idx - 1)
            print(f"{rank:<6} {row['county']:<25} ${row['price']:<11,.0f} "
                  f"{row['yoy_growth']:>6.2f}% {row['cagr_3y']:>6.2f}% "
                  f"{row['pop_growth']:>6.2f}% {row['yield']:>6.1f}% "
                  f"{row['final_score']:>6.1f}")
        
        print("-" * 120)
    
    def categorize_counties(self, df):
        """Categorize counties by investment type"""
        print("\n" + "="*100)
        print("📊 COUNTY CATEGORIZATION BY INVESTMENT STRATEGY")
        print("="*100)
        
        # Best for Appreciation (high growth)
        appreciation = df[df['growth_raw'] > df['growth_raw'].quantile(0.75)].head(10)
        print("\n💹 BEST FOR APPRECIATION (Top Growth):")
        print("-" * 100)
        for idx, row in appreciation.iterrows():
            print(f"   • {row['county']:<25} YoY: {row['yoy_growth']:>6.2f}%, "
                  f"CAGR: {row['cagr_3y']:>6.2f}%, Price: ${row['price']:>10,.0f}")
        
        # Best for Affordability
        affordable = df.nsmallest(10, 'price')
        print("\n💰 MOST AFFORDABLE (Lowest Entry):")
        print("-" * 100)
        for idx, row in affordable.iterrows():
            print(f"   • {row['county']:<25} Price: ${row['price']:>10,.0f}, "
                  f"YoY: {row['yoy_growth']:>6.2f}%, Score: {row['final_score']:>5.1f}")
        
        # Best for Demographics
        demographic = df.nlargest(10, 'pop_growth')
        print("\n👥 BEST DEMOGRAPHICS (Population Growth):")
        print("-" * 100)
        for idx, row in demographic.iterrows():
            print(f"   • {row['county']:<25} Pop Growth: {row['pop_growth']:>6.2f}%, "
                  f"Price: ${row['price']:>10,.0f}, Score: {row['final_score']:>5.1f}")
        
        # Best for Yield
        yield_leaders = df.nlargest(10, 'yield')
        print("\n💵 BEST FOR CASH FLOW (Highest Estimated Yield):")
        print("-" * 100)
        for idx, row in yield_leaders.iterrows():
            print(f"   • {row['county']:<25} Yield: {row['yield']:>4.1f}%, "
                  f"Price: ${row['price']:>10,.0f}, Score: {row['final_score']:>5.1f}")
    
    def detailed_breakdown_top_10(self, df):
        """Show detailed breakdown for top 10 counties"""
        print("\n" + "="*120)
        print("📋 DETAILED SCORING BREAKDOWN - TOP 10 COUNTIES")
        print("="*120)
        
        for idx, row in df.head(10).iterrows():
            rank = idx + 1
            print(f"\n{'='*120}")
            print(f"#{rank}  {row['county'].upper()}")
            print(f"{'='*120}")
            
            print(f"\n💰 AFFORDABILITY (30% weight)")
            print(f"   Entry Price: ${row['price']:,.0f}")
            print(f"   vs CA Median: {row['affordability_raw']:+.1f}% {'cheaper' if row['affordability_raw'] > 0 else 'more expensive'}")
            print(f"   Normalized Score: {row['affordability_norm']:.2f}/100")
            print(f"   Weighted Contribution: {row['affordability_norm'] * 0.30:.2f}")
            
            print(f"\n📈 GROWTH (40% weight) - MOST IMPORTANT")
            print(f"   YoY Growth (70%): {row['yoy_growth']:+.2f}%")
            print(f"   3-Year CAGR (30%): {row['cagr_3y']:+.2f}%")
            print(f"   Combined Growth: {row['growth_raw']:.2f}")
            print(f"   Normalized Score: {row['growth_norm']:.2f}/100")
            print(f"   Weighted Contribution: {row['growth_norm'] * 0.40:.2f}")
            
            print(f"\n👥 DEMOGRAPHICS (20% weight)")
            print(f"   Population Growth: {row['pop_growth']:+.2f}%")
            print(f"   Normalized Score: {row['demographic_norm']:.2f}/100")
            print(f"   Weighted Contribution: {row['demographic_norm'] * 0.20:.2f}")
            
            print(f"\n💵 RENTAL YIELD (10% weight)")
            print(f"   Estimated Yield: {row['yield']:.1f}%")
            print(f"   Normalized Score: {row['yield_norm']:.2f}/100")
            print(f"   Weighted Contribution: {row['yield_norm'] * 0.10:.2f}")
            
            print(f"\n🏆 FINAL SCORE: {row['final_score']:.2f}/100")
    
    def save_results(self, df):
        """Save full ranking to CSV"""
        output_file = self.data_dir / 'all_counties_ranking.csv'
        
        # Select key columns for output
        output_df = df[[
            'county', 'price', 'yoy_growth', 'cagr_3y', 'pop_growth', 'yield',
            'affordability_norm', 'growth_norm', 'demographic_norm', 'yield_norm',
            'final_score', 'data_months', 'latest_date'
        ]].copy()
        
        output_df['rank'] = range(1, len(output_df) + 1)
        output_df = output_df[['rank'] + [col for col in output_df.columns if col != 'rank']]
        
        output_df.to_csv(output_file, index=False)
        print(f"\n✅ Full ranking saved to: {output_file}")
        print(f"   Total counties ranked: {len(output_df)}")
        
        return output_file
    
    def run(self):
        """Run complete analysis for all counties"""
        print("\n" + "="*100)
        print("🔬 INVESTMENT SCORING METHODOLOGY - ALL CALIFORNIA COUNTIES")
        print("="*100)
        
        # Load data for all counties
        df = self.load_all_county_data()
        
        if len(df) == 0:
            print("\n❌ No counties to process!")
            return None
        
        # Calculate scores
        df = self.calculate_scores(df)
        
        # Show results
        self.show_top_counties(df, top_n=20)
        self.show_bottom_counties(df, bottom_n=10)
        self.categorize_counties(df)
        self.detailed_breakdown_top_10(df)
        
        # Save results
        output_file = self.save_results(df)
        
        print("\n" + "="*100)
        print("✓ COMPLETE COUNTY ANALYSIS FINISHED")
        print("="*100)
        print()
        
        return df

if __name__ == "__main__":
    methodology = AllCountyScoringMethodology()
    methodology.run()
