#!/usr/bin/env python3
"""
California County Investment Analysis
Identify undervalued counties with growth potential
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class CaliforniaCountyAnalysis:
    def __init__(self):
        self.data_dir = Path('housing_market_data/processed')
        self.df = pd.read_csv(self.data_dir / 'ca_county_master.csv')
        self.df['date'] = pd.to_datetime(self.df['date'])
        
    def load_and_prepare_data(self):
        """Load and prepare California county data"""
        print("\n" + "="*70)
        print("🏔️  CALIFORNIA COUNTY INVESTMENT ANALYSIS")
        print("="*70)
        
        print(f"\n✓ Loaded {self.df['RegionName'].nunique()} California counties")
        print(f"  Date range: {self.df['date'].min().date()} to {self.df['date'].max().date()}")
        
        # Remove rows with missing ZHVI
        self.df = self.df.dropna(subset=['zhvi'])
        print(f"  Counties with home value data: {self.df['RegionName'].nunique()}")
        
        return self.df
    
    def calculate_growth_metrics(self, df):
        """Calculate growth metrics for each county"""
        # Get data from last 3 years for trend analysis
        three_years_ago = df['date'].max() - pd.DateOffset(years=3)
        recent = df[df['date'] >= three_years_ago].copy()
        
        # Calculate metrics per county
        metrics = []
        for county in recent['RegionName'].unique():
            county_data = recent[recent['RegionName'] == county].sort_values('date')
            
            if len(county_data) < 12:  # Need at least 12 months of data
                continue
            
            # Price metrics
            latest_price = county_data['zhvi'].iloc[-1]
            year_ago_price = county_data[county_data['date'] <= county_data['date'].max() - pd.DateOffset(months=12)]['zhvi'].iloc[-1] if len(county_data[county_data['date'] <= county_data['date'].max() - pd.DateOffset(months=12)]) > 0 else None
            three_year_price = county_data['zhvi'].iloc[0]
            
            # Calculate YoY growth
            yoy_growth = ((latest_price - year_ago_price) / year_ago_price) if year_ago_price else None
            
            # Calculate 3-year CAGR
            years = (county_data['date'].iloc[-1] - county_data['date'].iloc[0]).days / 365.25
            cagr_3y = ((latest_price / three_year_price) ** (1/years) - 1) if years > 0 else None
            
            # Population growth
            latest_pop = county_data.dropna(subset=['population'])['population'].iloc[-1] if not county_data.dropna(subset=['population']).empty else None
            earliest_pop = county_data.dropna(subset=['population'])['population'].iloc[0] if not county_data.dropna(subset=['population']).empty else None
            pop_growth = ((latest_pop - earliest_pop) / earliest_pop) if (latest_pop and earliest_pop) else None
            
            # Get FIPS for reference
            fips = county_data['fips'].iloc[0]
            
            metrics.append({
                'county': county,
                'fips': fips,
                'latest_price': latest_price,
                'yoy_growth': yoy_growth,
                'cagr_3y': cagr_3y,
                'population': latest_pop,
                'pop_growth': pop_growth,
                'data_points': len(county_data)
            })
        
        return pd.DataFrame(metrics)
    
    def identify_undervalued_counties(self, metrics_df):
        """Identify undervalued counties with growth potential"""
        print("\n" + "="*70)
        print("💎 UNDERVALUED COUNTIES WITH GROWTH POTENTIAL")
        print("="*70)
        
        # Filter out counties with insufficient data
        metrics_df = metrics_df[metrics_df['yoy_growth'].notna()].copy()
        
        # Create value score
        # Factors:
        # 1. Low price (affordable entry)
        # 2. Positive growth (momentum)
        # 3. Population growth (demand)
        
        # Normalize prices (lower is better for value)
        price_median = metrics_df['latest_price'].median()
        metrics_df['price_score'] = (price_median - metrics_df['latest_price']) / price_median
        
        # Growth score (higher is better)
        metrics_df['growth_score'] = metrics_df['yoy_growth'].fillna(0)
        
        # Population score (higher is better)
        metrics_df['pop_score'] = metrics_df['pop_growth'].fillna(0)
        
        # Combined score
        metrics_df['value_score'] = (
            metrics_df['price_score'] * 40 +  # Affordability weight
            metrics_df['growth_score'] * 40 +  # Price momentum weight
            metrics_df['pop_score'] * 20       # Population growth weight
        )
        
        # Top undervalued counties
        undervalued = metrics_df.sort_values('value_score', ascending=False).head(15)
        
        print("\n🏆 Top 15 Undervalued Counties (Best Value + Growth):")
        print("-" * 100)
        print(f"{'Rank':<5} {'County':<30} {'Price':<15} {'YoY Growth':<12} {'3Y CAGR':<12} {'Pop Growth'}")
        print("-" * 100)
        
        for idx, row in enumerate(undervalued.itertuples(), 1):
            pop_str = f"{row.pop_growth*100:+.1f}%" if row.pop_growth else "N/A"
            cagr_str = f"{row.cagr_3y*100:+.2f}%" if row.cagr_3y else "N/A"
            
            print(f"{idx:<5} {row.county[:28]:<30} ${row.latest_price:>12,.0f}  "
                  f"{row.yoy_growth*100:>9.2f}%  {cagr_str:>10}  {pop_str:>10}")
        
        return undervalued
    
    def compare_by_region(self, metrics_df):
        """Compare counties by major regions"""
        print("\n" + "="*70)
        print("🗺️  REGIONAL COMPARISON")
        print("="*70)
        
        # Define regions (simplified)
        bay_area = ['Alameda', 'Contra Costa', 'Marin', 'San Francisco', 'San Mateo', 'Santa Clara', 'Napa', 'Sonoma', 'Solano']
        socal = ['Los Angeles', 'Orange', 'San Diego', 'Riverside', 'San Bernardino', 'Ventura']
        central_valley = ['Fresno', 'Kern', 'Kings', 'Madera', 'Merced', 'San Joaquin', 'Stanislaus', 'Tulare']
        central_coast = ['Monterey', 'San Luis Obispo', 'Santa Barbara', 'Santa Cruz']
        
        regions = {
            'Bay Area': bay_area,
            'Southern CA': socal,
            'Central Valley': central_valley,
            'Central Coast': central_coast
        }
        
        print("\nAverage Metrics by Region:")
        print("-" * 90)
        print(f"{'Region':<20} {'Avg Price':<15} {'Avg YoY Growth':<18} {'Avg 3Y CAGR'}")
        print("-" * 90)
        
        for region_name, counties in regions.items():
            region_data = metrics_df[metrics_df['county'].str.replace(' County', '').isin(counties)]
            if not region_data.empty:
                avg_price = region_data['latest_price'].mean()
                avg_yoy = region_data['yoy_growth'].mean()
                avg_cagr = region_data['cagr_3y'].mean()
                
                print(f"{region_name:<20} ${avg_price:>13,.0f}  {avg_yoy*100:>15.2f}%  {avg_cagr*100:>13.2f}%")
    
    def best_counties_by_category(self, metrics_df):
        """Identify best counties by different investment strategies"""
        print("\n" + "="*70)
        print("🎯 BEST COUNTIES BY INVESTMENT STRATEGY")
        print("="*70)
        
        # Strategy 1: Growth (highest appreciation)
        print("\n📈 GROWTH STRATEGY (Highest Price Appreciation):")
        print("-" * 70)
        growth = metrics_df.nlargest(5, 'yoy_growth')
        for idx, row in enumerate(growth.itertuples(), 1):
            print(f"{idx}. {row.county:<30} YoY: {row.yoy_growth*100:+.2f}%, Price: ${row.latest_price:,.0f}")
        
        # Strategy 2: Value (low price, positive growth)
        print("\n💰 VALUE STRATEGY (Affordable + Growing):")
        print("-" * 70)
        affordable = metrics_df[metrics_df['latest_price'] < metrics_df['latest_price'].median()]
        value = affordable[affordable['yoy_growth'] > 0].nlargest(5, 'yoy_growth')
        for idx, row in enumerate(value.itertuples(), 1):
            print(f"{idx}. {row.county:<30} Price: ${row.latest_price:,.0f}, YoY: {row.yoy_growth*100:+.2f}%")
        
        # Strategy 3: Momentum (best 3-year CAGR)
        print("\n🚀 MOMENTUM STRATEGY (Best 3-Year Track Record):")
        print("-" * 70)
        momentum = metrics_df.dropna(subset=['cagr_3y']).nlargest(5, 'cagr_3y')
        for idx, row in enumerate(momentum.itertuples(), 1):
            print(f"{idx}. {row.county:<30} 3Y CAGR: {row.cagr_3y*100:+.2f}%, Price: ${row.latest_price:,.0f}")
        
        # Strategy 4: Population Growth (demand-driven)
        print("\n👥 DEMOGRAPHIC STRATEGY (Population Growth):")
        print("-" * 70)
        demo = metrics_df.dropna(subset=['pop_growth']).nlargest(5, 'pop_growth')
        for idx, row in enumerate(demo.itertuples(), 1):
            pop_str = f"{row.pop_growth*100:+.1f}%" if row.pop_growth else "N/A"
            print(f"{idx}. {row.county:<30} Pop Growth: {pop_str}, Price: ${row.latest_price:,.0f}")
    
    def market_tiers(self, metrics_df):
        """Categorize counties into investment tiers"""
        print("\n" + "="*70)
        print("🏅 INVESTMENT TIER CLASSIFICATION")
        print("="*70)
        
        # Define tiers based on price and growth
        expensive_threshold = metrics_df['latest_price'].quantile(0.75)
        affordable_threshold = metrics_df['latest_price'].quantile(0.25)
        
        # Tier A: Affordable + High Growth
        tier_a = metrics_df[
            (metrics_df['latest_price'] < affordable_threshold) &
            (metrics_df['yoy_growth'] > metrics_df['yoy_growth'].median())
        ].sort_values('yoy_growth', ascending=False)
        
        print("\n🥇 TIER A: BEST VALUE (Affordable + Strong Growth)")
        print("   These are your BEST BETS for 2026")
        print("-" * 70)
        if not tier_a.empty:
            for idx, row in enumerate(tier_a.head(5).itertuples(), 1):
                print(f"{idx}. {row.county:<35} ${row.latest_price:>12,.0f}  YoY: {row.yoy_growth*100:>6.2f}%")
        else:
            print("   No counties in this tier")
        
        # Tier B: Affordable + Moderate Growth
        tier_b = metrics_df[
            (metrics_df['latest_price'] < affordable_threshold) &
            (metrics_df['yoy_growth'] > 0) &
            (metrics_df['yoy_growth'] <= metrics_df['yoy_growth'].median())
        ].sort_values('yoy_growth', ascending=False)
        
        print("\n🥈 TIER B: SOLID VALUE (Affordable + Stable)")
        print("   Good for conservative investors")
        print("-" * 70)
        if not tier_b.empty:
            for idx, row in enumerate(tier_b.head(5).itertuples(), 1):
                print(f"{idx}. {row.county:<35} ${row.latest_price:>12,.0f}  YoY: {row.yoy_growth*100:>6.2f}%")
        
        # Tier C: Premium markets
        tier_c = metrics_df[
            (metrics_df['latest_price'] > expensive_threshold) &
            (metrics_df['yoy_growth'] > 0)
        ].sort_values('yoy_growth', ascending=False)
        
        print("\n💎 TIER C: PREMIUM MARKETS (Expensive but Growing)")
        print("   For high-net-worth investors")
        print("-" * 70)
        if not tier_c.empty:
            for idx, row in enumerate(tier_c.head(3).itertuples(), 1):
                print(f"{idx}. {row.county:<35} ${row.latest_price:>12,.0f}  YoY: {row.yoy_growth*100:>6.2f}%")
    
    def specific_recommendations(self, metrics_df):
        """Provide specific investment recommendations"""
        print("\n" + "="*70)
        print("💡 SPECIFIC RECOMMENDATIONS FOR 2026")
        print("="*70)
        
        # Top 3 picks
        top_picks = metrics_df.sort_values('value_score', ascending=False).head(3)
        
        print("\n🎯 TOP 3 CALIFORNIA COUNTY PICKS:")
        
        for idx, row in enumerate(top_picks.itertuples(), 1):
            print(f"\n{idx}. {row.county} ⭐⭐⭐⭐⭐" if idx == 1 else f"\n{idx}. {row.county} ⭐⭐⭐⭐")
            print(f"   Entry Price: ${row.latest_price:,.0f}")
            print(f"   YoY Growth: {row.yoy_growth*100:+.2f}%")
            if row.cagr_3y:
                print(f"   3-Year CAGR: {row.cagr_3y*100:+.2f}%")
            if row.pop_growth:
                print(f"   Pop Growth: {row.pop_growth*100:+.1f}%")
            
            # Provide context
            if row.latest_price < 500000:
                print(f"   ✓ AFFORDABLE - Below median CA price")
            if row.yoy_growth and row.yoy_growth > 0.02:
                print(f"   ✓ STRONG MOMENTUM - Above 2% YoY")
            if row.pop_growth and row.pop_growth > 0:
                print(f"   ✓ GROWING - Positive population trend")
    
    def run(self):
        """Run complete California county analysis"""
        df = self.load_and_prepare_data()
        metrics_df = self.calculate_growth_metrics(df)
        
        # Run analyses
        undervalued_df = self.identify_undervalued_counties(metrics_df)
        self.compare_by_region(metrics_df)
        self.best_counties_by_category(metrics_df)
        self.market_tiers(metrics_df)
        self.specific_recommendations(undervalued_df)  # Use undervalued_df which has value_score
        
        print("\n" + "="*70)
        print("✓ CALIFORNIA COUNTY ANALYSIS COMPLETE")
        print("="*70)
        print("\nNext Steps:")
        print("1. Research top 3 recommended counties in detail")
        print("2. Connect with local real estate agents")
        print("3. Visit target areas for due diligence")
        print("4. Analyze specific neighborhoods within top counties")
        print("\n")

if __name__ == "__main__":
    analysis = CaliforniaCountyAnalysis()
    analysis.run()
