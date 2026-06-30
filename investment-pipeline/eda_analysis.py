#!/usr/bin/env python3
"""
Exploratory Data Analysis for Housing Market Investment
Identifies opportunities, compares markets, and analyzes trends
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class HousingMarketEDA:
    def __init__(self, data_dir='housing_market_data'):
        self.data_dir = Path(data_dir)
        self.processed_dir = self.data_dir / 'processed'
        self.features_file = self.processed_dir / 'features_master.csv'
        
    def load_data(self):
        """Load the features master dataset"""
        print("Loading data...")
        df = pd.read_csv(self.features_file)
        df['date'] = pd.to_datetime(df['date'])
        print(f"✓ Loaded {len(df):,} rows covering {df['name'].nunique()} metros")
        print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
        return df
    
    def get_latest_snapshot(self, df):
        """Get the most recent data for each metro"""
        latest_date = df['date'].max()
        snapshot = df[df['date'] == latest_date].copy()
        print(f"\n📊 Latest Snapshot: {latest_date.date()}")
        print(f"   Metros with data: {len(snapshot)}")
        return snapshot
    
    def top_investment_opportunities(self, df):
        """Identify top metros for investment based on multiple factors"""
        print("\n" + "="*70)
        print("🎯 TOP INVESTMENT OPPORTUNITIES (Latest Quarter)")
        print("="*70)
        
        # Get recent data (last 3 months average)
        recent = df[df['date'] >= df['date'].max() - pd.DateOffset(months=3)]
        
        # Aggregate metrics
        metrics = recent.groupby('name').agg({
            'price_yoy': 'mean',
            'rent_yoy': 'mean',
            'rental_yield': 'mean',
            'inventory_yoy': 'mean',
            'zhvi': 'last',
            'category': 'first'
        }).reset_index()
        
        # Create composite score
        # Positive factors: rental_yield, rent_yoy, price_yoy (moderate)
        # Negative factors: excessive price_yoy (>10% = bubble risk), high inventory growth
        metrics['investment_score'] = (
            (metrics['rental_yield'] * 100) +  # Higher yield is better
            (metrics['rent_yoy'].clip(-0.1, 0.15) * 50) +  # Rent growth (capped)
            (metrics['price_yoy'].clip(-0.05, 0.08) * 30) -  # Moderate price growth
            (metrics['inventory_yoy'].fillna(0) * 20)  # Lower inventory growth is better
        )
        
        # Add risk flags
        metrics['bubble_risk'] = (metrics['price_yoy'] > 0.10).astype(int)
        metrics['declining'] = (metrics['price_yoy'] < -0.02).astype(int)
        
        # Sort by score
        top_markets = metrics.sort_values('investment_score', ascending=False).head(15)
        
        print("\nTop 15 Markets (Ranked by Investment Score):")
        print("-" * 110)
        print(f"{'Rank':<5} {'Metro':<40} {'Score':<8} {'Yield':<8} {'Price YoY':<11} {'Rent YoY':<11} {'Risk':<10}")
        print("-" * 110)
        
        for idx, row in enumerate(top_markets.itertuples(), 1):
            risk_flag = ""
            if row.bubble_risk:
                risk_flag = "⚠️ BUBBLE"
            elif row.declining:
                risk_flag = "📉 DECLINE"
            
            print(f"{idx:<5} {row.name[:38]:<40} {row.investment_score:>6.2f}  "
                  f"{row.rental_yield*100:>6.2f}%  {row.price_yoy*100:>8.2f}%  "
                  f"{row.rent_yoy*100:>8.2f}%  {risk_flag}")
        
        return top_markets
    
    def ca_vs_tx_comparison(self, df):
        """Compare California vs Texas markets"""
        print("\n" + "="*70)
        print("🏠 CALIFORNIA vs TEXAS MARKET COMPARISON")
        print("="*70)
        
        # Define metros
        ca_metros = [
            'Los Angeles-Long Beach-Anaheim, CA',
            'San Francisco-Oakland-Berkeley, CA',
            'San Diego-Chula Vista-Carlsbad, CA',
            'San Jose-Sunnyvale-Santa Clara, CA',
            'Sacramento-Roseville-Folsom, CA'
        ]
        
        tx_metros = [
            'Dallas-Fort Worth-Arlington, TX',
            'Houston-The Woodlands-Sugar Land, TX',
            'Austin-Round Rock-Georgetown, TX',
            'San Antonio-New Braunfels, TX'
        ]
        
        # Get recent data
        recent = df[df['date'] >= df['date'].max() - pd.DateOffset(months=12)]
        
        ca_data = recent[recent['name'].isin(ca_metros)]
        tx_data = recent[recent['name'].isin(tx_metros)]
        
        # Calculate averages
        ca_avg = ca_data.groupby('name').agg({
            'zhvi': 'mean',
            'rental_yield': 'mean',
            'price_yoy': 'mean',
            'rent_yoy': 'mean'
        }).mean()
        
        tx_avg = tx_data.groupby('name').agg({
            'zhvi': 'mean',
            'rental_yield': 'mean',
            'price_yoy': 'mean',
            'rent_yoy': 'mean'
        }).mean()
        
        print("\nAverage Metrics (12-month trailing):")
        print("-" * 70)
        print(f"{'Metric':<30} {'California':<20} {'Texas':<20}")
        print("-" * 70)
        print(f"{'Median Home Value':<30} ${ca_avg['zhvi']:>15,.0f}   ${tx_avg['zhvi']:>15,.0f}")
        print(f"{'Rental Yield':<30} {ca_avg['rental_yield']*100:>18.2f}%  {tx_avg['rental_yield']*100:>18.2f}%")
        print(f"{'Price Growth (YoY)':<30} {ca_avg['price_yoy']*100:>18.2f}%  {tx_avg['price_yoy']*100:>18.2f}%")
        print(f"{'Rent Growth (YoY)':<30} {ca_avg['rent_yoy']*100:>18.2f}%  {tx_avg['rent_yoy']*100:>18.2f}%")
        print("-" * 70)
        
        # Individual metro breakdown
        print("\nTop Performer in Each State:")
        
        ca_best = ca_data.groupby('name').agg({
            'price_yoy': 'mean',
            'rental_yield': 'mean'
        }).sort_values('price_yoy', ascending=False).head(1)
        
        tx_best = tx_data.groupby('name').agg({
            'price_yoy': 'mean',
            'rental_yield': 'mean'
        }).sort_values('price_yoy', ascending=False).head(1)
        
        print(f"\n  CA: {ca_best.index[0]}")
        print(f"      Price Growth: {ca_best['price_yoy'].iloc[0]*100:.2f}%, Yield: {ca_best['rental_yield'].iloc[0]*100:.2f}%")
        
        print(f"\n  TX: {tx_best.index[0]}")
        print(f"      Price Growth: {tx_best['price_yoy'].iloc[0]*100:.2f}%, Yield: {tx_best['rental_yield'].iloc[0]*100:.2f}%")
    
    def emerging_markets_analysis(self, df):
        """Analyze emerging markets"""
        print("\n" + "="*70)
        print("🚀 EMERGING MARKETS ANALYSIS")
        print("="*70)
        
        emerging = df[df['category'] == 'Emerging Markets'].copy()
        
        if emerging.empty:
            print("No emerging markets data available")
            return
        
        # Get recent snapshot
        recent = emerging[emerging['date'] >= emerging['date'].max() - pd.DateOffset(months=3)]
        
        summary = recent.groupby('name').agg({
            'price_yoy': 'mean',
            'rent_yoy': 'mean',
            'rental_yield': 'mean',
            'zhvi': 'last'
        }).sort_values('price_yoy', ascending=False)
        
        print("\nEmerging Markets Performance (Last 3 Months):")
        print("-" * 90)
        print(f"{'Metro':<45} {'Price YoY':<12} {'Rent YoY':<12} {'Yield':<10}")
        print("-" * 90)
        
        for name, row in summary.iterrows():
            print(f"{name[:43]:<45} {row['price_yoy']*100:>9.2f}%  {row['rent_yoy']*100:>9.2f}%  {row['rental_yield']*100:>7.2f}%")
    
    def price_momentum_analysis(self, df):
        """Analyze price momentum trends"""
        print("\n" + "="*70)
        print("📈 PRICE MOMENTUM ANALYSIS")
        print("="*70)
        
        # Get latest data
        latest = self.get_latest_snapshot(df)
        
        # Categorize markets
        hot = latest[latest['price_yoy'] > 0.05]
        cooling = latest[(latest['price_yoy'] <= 0.05) & (latest['price_yoy'] > 0)]
        declining = latest[latest['price_yoy'] <= 0]
        
        print(f"\n🔥 HOT Markets (>5% YoY growth): {len(hot)}")
        if not hot.empty:
            for _, row in hot.nlargest(5, 'price_yoy').iterrows():
                print(f"   • {row['name'][:40]:<40} {row['price_yoy']*100:>6.2f}%")
        
        print(f"\n❄️  COOLING Markets (0-5% YoY growth): {len(cooling)}")
        
        print(f"\n📉 DECLINING Markets (<0% YoY growth): {len(declining)}")
        if not declining.empty:
            for _, row in declining.nsmallest(5, 'price_yoy').iterrows():
                print(f"   • {row['name'][:40]:<40} {row['price_yoy']*100:>6.2f}%")
    
    def affordability_analysis(self, df):
        """Analyze rental yield and affordability"""
        print("\n" + "="*70)
        print("💰 AFFORDABILITY & RENTAL YIELD ANALYSIS")
        print("="*70)
        
        latest = self.get_latest_snapshot(df)
        
        # Best rental yields
        print("\nTop 10 Markets by Rental Yield:")
        print("-" * 70)
        
        top_yields = latest.nlargest(10, 'rental_yield')[['name', 'rental_yield', 'zhvi']]
        for idx, row in enumerate(top_yields.itertuples(), 1):
            print(f"{idx:>2}. {row.name[:40]:<40} {row.rental_yield*100:>6.2f}%  (${row.zhvi:>10,.0f})")
        
        # Worst rental yields (expensive markets)
        print("\nLowest Rental Yields (Expensive Markets):")
        print("-" * 70)
        
        worst_yields = latest.nsmallest(5, 'rental_yield')[['name', 'rental_yield', 'zhvi']]
        for idx, row in enumerate(worst_yields.itertuples(), 1):
            print(f"{idx}. {row.name[:40]:<40} {row.rental_yield*100:>6.2f}%  (${row.zhvi:>10,.0f})")
    
    def run_full_analysis(self):
        """Run complete EDA"""
        print("\n" + "="*70)
        print("🏘️  HOUSING MARKET INVESTMENT ANALYSIS - EXPLORATORY DATA ANALYSIS")
        print("="*70)
        
        # Load data
        df = self.load_data()
        
        # Run analyses
        self.top_investment_opportunities(df)
        self.ca_vs_tx_comparison(df)
        self.emerging_markets_analysis(df)
        self.price_momentum_analysis(df)
        self.affordability_analysis(df)
        
        print("\n" + "="*70)
        print("✓ ANALYSIS COMPLETE")
        print("="*70)
        print("\nKey Takeaways:")
        print("1. Review top investment opportunities for best risk-adjusted returns")
        print("2. Consider emerging markets for higher growth potential")
        print("3. Balance rental yield with appreciation potential")
        print("4. Monitor declining markets for potential value plays")
        print("\n")

if __name__ == "__main__":
    eda = HousingMarketEDA()
    eda.run_full_analysis()
