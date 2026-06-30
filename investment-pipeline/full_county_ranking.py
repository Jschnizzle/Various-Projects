#!/usr/bin/env python3
"""
Full California County Ranking
Combines our methodology with Sungjin's scoring approach
"""

import pandas as pd
import numpy as np
from pathlib import Path

class FullCountyRanking:
    def __init__(self):
        self.data_dir = Path('housing_market_data/processed')
        
    def our_methodology(self, df):
        """Our original scoring method"""
        # Calculate metrics
        metrics_list = []
        
        for county in df['RegionName'].unique():
            county_data = df[df['RegionName'] == county].sort_values('date')
            
            if len(county_data) < 12:
                continue
            
            latest_price = county_data['zhvi'].iloc[-1]
            
            # YoY growth
            year_ago = county_data[county_data['date'] <= county_data['date'].max() - pd.DateOffset(months=12)]
            if not year_ago.empty:
                yoy_growth = ((latest_price - year_ago['zhvi'].iloc[-1]) / year_ago['zhvi'].iloc[-1]) * 100
            else:
                yoy_growth = 0
            
            # 3-year CAGR
            three_years_ago = county_data[county_data['date'] <= county_data['date'].max() - pd.DateOffset(years=3)]
            if not three_years_ago.empty:
                years = (county_data['date'].iloc[-1] - three_years_ago['date'].iloc[0]).days / 365.25
                cagr = (((latest_price / three_years_ago['zhvi'].iloc[0]) ** (1/years)) - 1) * 100
            else:
                cagr = 0
            
            # Population growth
            pop_data = county_data.dropna(subset=['population'])
            if len(pop_data) >= 2:
                pop_growth = ((pop_data['population'].iloc[-1] - pop_data['population'].iloc[0]) / 
                             pop_data['population'].iloc[0]) * 100
            else:
                pop_growth = 0
            
            # Yield estimate (rough for all counties)
            yield_est = 6.0  # Default estimate
            
            metrics_list.append({
                'county': county,
                'price': latest_price,
                'yoy_growth': yoy_growth,
                'cagr_3y': cagr,
                'pop_growth': pop_growth,
                'yield': yield_est
            })
        
        metrics_df = pd.DataFrame(metrics_list)
        
        # Calculate scores (our method)
        median_price = metrics_df['price'].median()
        metrics_df['affordability_raw'] = ((median_price - metrics_df['price']) / median_price) * 100
        metrics_df['growth_raw'] = (metrics_df['yoy_growth'] * 0.7) + (metrics_df['cagr_3y'] * 0.3)
        metrics_df['demographic_raw'] = metrics_df['pop_growth'] * 10
        metrics_df['yield_raw'] = metrics_df['yield']
        
        # Normalize
        def normalize(series):
            min_val = series.min()
            max_val = series.max()
            if max_val == min_val:
                return pd.Series([50] * len(series), index=series.index)
            return ((series - min_val) / (max_val - min_val)) * 100
        
        metrics_df['affordability_norm'] = normalize(metrics_df['affordability_raw'])
        metrics_df['growth_norm'] = normalize(metrics_df['growth_raw'])
        metrics_df['demographic_norm'] = normalize(metrics_df['demographic_raw'])
        metrics_df['yield_norm'] = normalize(metrics_df['yield_raw'])
        
        # Final score (our weights)
        metrics_df['our_score'] = (
            metrics_df['affordability_norm'] * 0.30 +
            metrics_df['growth_norm'] * 0.40 +
            metrics_df['demographic_norm'] * 0.20 +
            metrics_df['yield_norm'] * 0.10
        )
        
        return metrics_df
    
    def sungjin_methodology(self, metrics_df):
        """
        Sungjin's methodology from notebook:
        - Uses Z-score normalization
        - Weights: 40% price growth, 20% rent growth, 15% tightness, 10% DOM, 15% mortgage
        - We'll adapt to our available data
        """
        def z_score(x):
            mean = x.mean()
            std = x.std()
            if std == 0:
                return pd.Series([0] * len(x), index=x.index)
            return (x - mean) / std
        
        # Sungjin's weights (adapted to our data)
        # We don't have rent growth, tightness, DOM, or mortgage rate per county
        # So we'll focus on what we have: price growth and affordability
        
        metrics_df['sungjin_score'] = (
            0.60 * z_score(metrics_df['yoy_growth']) +      # Price growth (increased weight)
            0.25 * z_score(metrics_df['cagr_3y']) +         # Proven track record
            0.10 * -z_score(metrics_df['price']) +          # Lower price is better
            0.05 * z_score(metrics_df['pop_growth'])        # Demographics
        )
        
        # Normalize Sungjin score to 0-100 for easier comparison
        min_s = metrics_df['sungjin_score'].min()
        max_s = metrics_df['sungjin_score'].max()
        metrics_df['sungjin_score_norm'] = ((metrics_df['sungjin_score'] - min_s) / (max_s - min_s)) * 100
        
        return metrics_df
    
    def combined_score(self, metrics_df):
        """Combine both methodologies"""
        # Simple average of both normalized scores
        metrics_df['combined_score'] = (metrics_df['our_score'] + metrics_df['sungjin_score_norm']) / 2
        return metrics_df
    
    def create_full_ranking(self):
        """Create complete ranking table"""
        print("\n" + "="*120)
        print("🏔️  COMPLETE CALIFORNIA COUNTY RANKING")
        print("="*120)
        
        # Load data
        df = pd.read_csv(self.data_dir / 'ca_county_master.csv')
        df['date'] = pd.to_datetime(df['date'])
        df = df.dropna(subset=['zhvi'])
        
        total_counties = df['RegionName'].nunique()
        print(f"\nAnalyzing {total_counties} California counties with data...")
        
        # Calculate both methodologies
        metrics_df = self.our_methodology(df)
        metrics_df = self.sungjin_methodology(metrics_df)
        metrics_df = self.combined_score(metrics_df)
        
        # Sort by combined score
        metrics_df = metrics_df.sort_values('combined_score', ascending=False)
        metrics_df['rank'] = range(1, len(metrics_df) + 1)
        
        print("\n" + "="*120)
        print("FULL RANKING TABLE (All Counties)")
        print("="*120)
        print(f"\n{'Rank':<5} {'County':<40} {'Price':<12} {'YoY%':<8} {'CAGR%':<8} {'Pop%':<8} "
              f"{'Our':<7} {'Sung':<7} {'Comb':<7}")
        print("-" * 120)
        
        for _, row in metrics_df.iterrows():
            print(f"{row['rank']:<5} {row['county'][:38]:<40} ${row['price']:>10,.0f} "
                  f"{row['yoy_growth']:>6.2f}% {row['cagr_3y']:>6.2f}% {row['pop_growth']:>6.1f}% "
                  f"{row['our_score']:>5.1f}  {row['sungjin_score_norm']:>5.1f}  {row['combined_score']:>5.1f}")
        
        return metrics_df
    
    def methodology_comparison(self, metrics_df):
        """Compare the two methodologies"""
        print("\n" + "="*120)
        print("📊 METHODOLOGY COMPARISON")
        print("="*120)
        
        print("\n🔵 OUR METHODOLOGY:")
        print("-" * 120)
        print("Formula: (Affordability × 30%) + (Growth × 40%) + (Demographics × 20%) + (Yield × 10%)")
        print("Approach: Component-based weighting with normalization")
        print("Philosophy: Balance between affordability, growth, and demographics")
        
        print("\n🟢 SUNGJIN'S METHODOLOGY (Adapted):")
        print("-" * 120)
        print("Formula: Z-score based with weights: YoY(60%) + CAGR(25%) + Price(-10%) + Pop(5%)")
        print("Approach: Statistical normalization (Z-scores)")
        print("Philosophy: Heavy emphasis on growth momentum")
        
        print("\n🟣 COMBINED METHODOLOGY:")
        print("-" * 120)
        print("Formula: (Our Score + Sungjin Score) / 2")
        print("Approach: Average of both methods")
        print("Philosophy: Balanced perspective from two different approaches")
        
        # Show top 10 from each method
        print("\n" + "="*120)
        print("TOP 10 COMPARISON")
        print("="*120)
        
        our_top10 = metrics_df.nsmallest(10, 'rank')[['county', 'our_score']].copy()
        sung_df = metrics_df.sort_values('sungjin_score_norm', ascending=False).head(10)[['county', 'sungjin_score_norm']].copy()
        comb_top10 = metrics_df.head(10)[['county', 'combined_score']].copy()
        
        print(f"\n{'Our Top 10':<45} {'Sungjin Top 10':<45} {'Combined Top 10':<45}")
        print("-" * 120)
        
        for i in range(10):
            our_name = our_top10.iloc[i]['county'][:25] if i < len(our_top10) else ""
            our_score = our_top10.iloc[i]['our_score'] if i < len(our_top10) else 0
            
            sung_name = sung_df.iloc[i]['county'][:25] if i < len(sung_df) else ""
            sung_score = sung_df.iloc[i]['sungjin_score_norm'] if i < len(sung_df) else 0
            
            comb_name = comb_top10.iloc[i]['county'][:25] if i < len(comb_top10) else ""
            comb_score = comb_top10.iloc[i]['combined_score'] if i < len(comb_top10) else 0
            
            print(f"{i+1}. {our_name:<27} ({our_score:>5.1f})  "
                  f"{i+1}. {sung_name:<27} ({sung_score:>5.1f})  "
                  f"{i+1}. {comb_name:<27} ({comb_score:>5.1f})")
    
    def export_results(self, metrics_df):
        """Export full results to CSV"""
        output_file = self.data_dir / 'full_county_ranking.csv'
        
        export_df = metrics_df[[
            'rank', 'county', 'price', 'yoy_growth', 'cagr_3y', 'pop_growth',
            'our_score', 'sungjin_score_norm', 'combined_score'
        ]].copy()
        
        export_df.columns = [
            'Rank', 'County', 'Price', 'YoY_Growth_%', '3Y_CAGR_%', 'Pop_Growth_%',
            'Our_Score', 'Sungjin_Score', 'Combined_Score'
        ]
        
        export_df.to_csv(output_file, index=False)
        print(f"\n✓ Full ranking exported to: {output_file}")
        
        return output_file
    
    def run(self):
        """Run complete analysis"""
        metrics_df = self.create_full_ranking()
        self.methodology_comparison(metrics_df)
        self.export_results(metrics_df)
        
        print("\n" + "="*120)
        print("✓ COMPLETE RANKING ANALYSIS DONE")
        print("="*120)
        print("\n💡 KEY INSIGHTS:")
        print(f"   • Total Counties Analyzed: {len(metrics_df)}")
        print(f"   • #1 Combined Ranking: {metrics_df.iloc[0]['county']}")
        print(f"   • Methodologies compared: Our weighted approach vs Sungjin's Z-score approach")
        print(f"   • Export: housing_market_data/processed/full_county_ranking.csv")
        print()
        
        return metrics_df

if __name__ == "__main__":
    ranker = FullCountyRanking()
    ranker.run()
