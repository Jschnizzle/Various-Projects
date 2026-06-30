#!/usr/bin/env python3
"""
Advanced Investment Analysis
Deep dive into specific investment opportunities
"""

import pandas as pd
import numpy as np
from pathlib import Path

class InvestmentAnalysis:
    def __init__(self):
        self.data_dir = Path('housing_market_data/processed')
        self.df = pd.read_csv(self.data_dir / 'features_master.csv')
        self.df['date'] = pd.to_datetime(self.df['date'])
        
    def migration_corridor_analysis(self):
        """Analyze CA to TX migration impact"""
        print("\n" + "="*70)
        print("🚚 CA → TX MIGRATION CORRIDOR ANALYSIS")
        print("="*70)
        
        # Key metros
        ca_from = ['Los Angeles-Long Beach-Anaheim, CA', 
                   'San Francisco-Oakland-Berkeley, CA',
                   'San Diego-Chula Vista-Carlsbad, CA']
        
        tx_to = ['Austin-Round Rock-Georgetown, TX',
                 'Dallas-Fort Worth-Arlington, TX',
                 'Houston-The Woodlands-Sugar Land, TX']
        
        recent = self.df[self.df['date'] >= self.df['date'].max() - pd.DateOffset(months=12)]
        
        print("\n📊 OUTFLOW MARKETS (California)")
        print("-" * 70)
        for metro in ca_from:
            data = recent[recent['name'] == metro]
            if not data.empty:
                avg_price_yoy = data['price_yoy'].mean() * 100
                avg_yield = data['rental_yield'].mean() * 100
                latest_price = data['zhvi'].iloc[-1]
                print(f"\n{metro}")
                print(f"  Median Price: ${latest_price:,.0f}")
                print(f"  Price Change: {avg_price_yoy:+.2f}% YoY")
                print(f"  Rental Yield: {avg_yield:.2f}%")
        
        print("\n\n📊 INFLOW MARKETS (Texas)")
        print("-" * 70)
        for metro in tx_to:
            data = recent[recent['name'] == metro]
            if not data.empty:
                avg_price_yoy = data['price_yoy'].mean() * 100
                avg_yield = data['rental_yield'].mean() * 100
                latest_price = data['zhvi'].iloc[-1]
                print(f"\n{metro}")
                print(f"  Median Price: ${latest_price:,.0f}")
                print(f"  Price Change: {avg_price_yoy:+.2f}% YoY")
                print(f"  Rental Yield: {avg_yield:.2f}%")
        
        # Price comparison
        ca_avg = recent[recent['name'].isin(ca_from)]['zhvi'].mean()
        tx_avg = recent[recent['name'].isin(tx_to)]['zhvi'].mean()
        savings = ca_avg - tx_avg
        savings_pct = (savings / ca_avg) * 100
        
        print(f"\n\n💡 MIGRATION ECONOMICS:")
        print(f"   Average CA Home: ${ca_avg:,.0f}")
        print(f"   Average TX Home: ${tx_avg:,.0f}")
        print(f"   Savings: ${savings:,.0f} ({savings_pct:.1f}%)")
    
    def opportunity_matrix(self):
        """Create opportunity matrix based on yield vs growth"""
        print("\n" + "="*70)
        print("🎯 INVESTMENT OPPORTUNITY MATRIX")
        print("="*70)
        
        latest = self.df[self.df['date'] == self.df['date'].max()].copy()
        
        # Categorize
        high_yield = latest['rental_yield'] > latest['rental_yield'].median()
        positive_growth = latest['price_yoy'] > 0
        
        # Quadrants
        print("\n🟢 SWEET SPOT (High Yield + Growth):")
        sweet_spot = latest[high_yield & positive_growth].nlargest(5, 'rental_yield')
        for _, row in sweet_spot.iterrows():
            print(f"   • {row['name'][:35]:<35} Yield: {row['rental_yield']*100:.2f}%, Growth: {row['price_yoy']*100:+.2f}%")
        
        print("\n🔵 GROWTH PLAYS (Low Yield + Growth):")
        growth_plays = latest[~high_yield & positive_growth].nlargest(5, 'price_yoy')
        for _, row in growth_plays.iterrows():
            print(f"   • {row['name'][:35]:<35} Yield: {row['rental_yield']*100:.2f}%, Growth: {row['price_yoy']*100:+.2f}%")
        
        print("\n🟡 INCOME PLAYS (High Yield + Declining):")
        income_plays = latest[high_yield & ~positive_growth].nlargest(5, 'rental_yield')
        for _, row in income_plays.iterrows():
            print(f"   • {row['name'][:35]:<35} Yield: {row['rental_yield']*100:.2f}%, Growth: {row['price_yoy']*100:+.2f}%")
        
        print("\n🔴 AVOID (Low Yield + Declining):")
        avoid = latest[~high_yield & ~positive_growth].nsmallest(3, 'price_yoy')
        for _, row in avoid.iterrows():
            print(f"   • {row['name'][:35]:<35} Yield: {row['rental_yield']*100:.2f}%, Growth: {row['price_yoy']*100:+.2f}%")
    
    def three_year_performance(self):
        """Analyze 3-year CAGR performance"""
        print("\n" + "="*70)
        print("📊 3-YEAR PERFORMANCE ANALYSIS")
        print("="*70)
        
        latest = self.df[self.df['date'] == self.df['date'].max()].copy()
        latest = latest.dropna(subset=['price_3y_cagr'])
        
        print("\n🏆 Top 10 Markets (3-Year Price CAGR):")
        print("-" * 70)
        top = latest.nlargest(10, 'price_3y_cagr')
        for idx, row in enumerate(top.itertuples(), 1):
            print(f"{idx:>2}. {row.name[:40]:<40} {row.price_3y_cagr*100:>6.2f}% CAGR")
        
        print("\n\n📉 Bottom 5 Markets (3-Year Price CAGR):")
        print("-" * 70)
        bottom = latest.nsmallest(5, 'price_3y_cagr')
        for idx, row in enumerate(bottom.itertuples(), 1):
            print(f"{idx}. {row.name[:40]:<40} {row.price_3y_cagr*100:>6.2f}% CAGR")
    
    def value_vs_growth_picks(self):
        """Specific investment recommendations"""
        print("\n" + "="*70)
        print("💼 INVESTMENT RECOMMENDATIONS (2026)")
        print("="*70)
        
        latest = self.df[self.df['date'] == self.df['date'].max()].copy()
        
        print("\n🎯 GROWTH PICKS (Appreciating Markets):")
        growth = latest[latest['price_yoy'] > 0].nlargest(3, 'price_yoy')
        for _, row in growth.iterrows():
            print(f"\n   {row['name']}")
            print(f"   Why: {row['price_yoy']*100:.2f}% YoY growth, {row['rent_yoy']*100:.2f}% rent growth")
            print(f"   Entry: ${row['zhvi']:,.0f}, Yield: {row['rental_yield']*100:.2f}%")
        
        print("\n\n💰 VALUE PICKS (High Yield Markets):")
        value = latest.nlargest(3, 'rental_yield')
        for _, row in value.iterrows():
            print(f"\n   {row['name']}")
            print(f"   Why: {row['rental_yield']*100:.2f}% yield (${row['zhvi']:,.0f} entry)")
            print(f"   Growth: {row['price_yoy']*100:+.2f}% YoY")
        
        print("\n\n⚖️ BALANCED PICKS (Yield + Growth):")
        # Score: equal weight on yield and positive growth
        latest['balanced_score'] = (
            (latest['rental_yield'] * 100) +
            (latest['price_yoy'].clip(0, 0.1) * 100)
        )
        balanced = latest.nlargest(3, 'balanced_score')
        for _, row in balanced.iterrows():
            print(f"\n   {row['name']}")
            print(f"   Why: {row['rental_yield']*100:.2f}% yield + {row['price_yoy']*100:+.2f}% growth")
            print(f"   Entry: ${row['zhvi']:,.0f}")
    
    def run(self):
        """Run all analyses"""
        print("\n" + "="*70)
        print("🏘️  ADVANCED INVESTMENT ANALYSIS - 2026 OPPORTUNITY REPORT")
        print("="*70)
        
        self.migration_corridor_analysis()
        self.opportunity_matrix()
        self.three_year_performance()
        self.value_vs_growth_picks()
        
        print("\n" + "="*70)
        print("✓ ANALYSIS COMPLETE")
        print("="*70 + "\n")

if __name__ == "__main__":
    analysis = InvestmentAnalysis()
    analysis.run()
