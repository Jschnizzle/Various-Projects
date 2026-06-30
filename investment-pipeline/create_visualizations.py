#!/usr/bin/env python3
"""
Visualizations for California County Rankings
Creates charts comparing methodologies and showing full rankings
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
import geopandas as gpd
import matplotlib.colors as mcolors

class CountyRankingVisualizations:
    def __init__(self):
        self.data_dir = Path('housing_market_data/processed')
        self.output_dir = Path('visualizations')
        self.output_dir.mkdir(exist_ok=True)
        
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")
        
    def load_data(self):
        """Load the ranking data"""
        df = pd.read_csv(self.data_dir / 'full_county_ranking.csv')
        print(f"✓ Loaded {len(df)} counties")
        return df
    
    def create_score_comparison(self, df):
        """Compare all three scoring methodologies"""
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # Top 15 for each method
        top15_our = df.nsmallest(15, 'Rank')[['County', 'Our_Score']].sort_values('Our_Score', ascending=False)
        top15_sung = df.nlargest(15, 'Sungjin_Score')[['County', 'Sungjin_Score']].sort_values('Sungjin_Score', ascending=False)
        top15_comb = df.nsmallest(15, 'Rank')[['County', 'Combined_Score']].sort_values('Combined_Score', ascending=False)
        
        # Plot 1: Our methodology
        axes[0].barh(range(len(top15_our)), top15_our['Our_Score'], color='#3498db')
        axes[0].set_yticks(range(len(top15_our)))
        axes[0].set_yticklabels([c.replace(' County', '') for c in top15_our['County']], fontsize=9)
        axes[0].set_xlabel('Score', fontsize=11, fontweight='bold')
        axes[0].set_title('Our Component-Based Method\n(Growth 40%, Afford 30%)', fontsize=12, fontweight='bold')
        axes[0].grid(axis='x', alpha=0.3)
        axes[0].invert_yaxis()
        
        # Highlight Imperial
        imperial_idx = list(top15_our['County']).index('Imperial County')
        axes[0].barh(imperial_idx, top15_our.iloc[imperial_idx]['Our_Score'], color='#e74c3c', alpha=0.8)
        
        # Plot 2: Sungjin methodology
        axes[1].barh(range(len(top15_sung)), top15_sung['Sungjin_Score'], color='#2ecc71')
        axes[1].set_yticks(range(len(top15_sung)))
        axes[1].set_yticklabels([c.replace(' County', '') for c in top15_sung['County']], fontsize=9)
        axes[1].set_xlabel('Score', fontsize=11, fontweight='bold')
        axes[1].set_title('Sungjin Z-Score Method\n(YoY 60%, CAGR 25%)', fontsize=12, fontweight='bold')
        axes[1].grid(axis='x', alpha=0.3)
        axes[1].invert_yaxis()
        
        imperial_idx = list(top15_sung['County']).index('Imperial County')
        axes[1].barh(imperial_idx, top15_sung.iloc[imperial_idx]['Sungjin_Score'], color='#e74c3c', alpha=0.8)
        
        # Plot 3: Combined
        axes[2].barh(range(len(top15_comb)), top15_comb['Combined_Score'], color='#9b59b6')
        axes[2].set_yticks(range(len(top15_comb)))
        axes[2].set_yticklabels([c.replace(' County', '') for c in top15_comb['County']], fontsize=9)
        axes[2].set_xlabel('Score', fontsize=11, fontweight='bold')
        axes[2].set_title('Combined Consensus\n(Average of Both)', fontsize=12, fontweight='bold')
        axes[2].grid(axis='x', alpha=0.3)
        axes[2].invert_yaxis()
        
        imperial_idx = list(top15_comb['County']).index('Imperial County')
        axes[2].barh(imperial_idx, top15_comb.iloc[imperial_idx]['Combined_Score'], color='#e74c3c', alpha=0.8)
        
        plt.suptitle('🏔️ Top 15 California Counties - Methodology Comparison', 
                     fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        output_file = self.output_dir / '1_methodology_comparison.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_file}")
        plt.close()
    
    def create_full_ranking_visualization(self, df):
        """Visualize all 58 counties"""
        fig, ax = plt.subplots(figsize=(14, 16))
        
        # Sort by combined score
        df_sorted = df.sort_values('Combined_Score', ascending=True)
        
        # Color code: Top 10 green, Middle yellow, Bottom 10 red
        colors = []
        for i, rank in enumerate(df_sorted['Rank']):
            if rank <= 10:
                colors.append('#2ecc71')  # Green
            elif rank >= 49:
                colors.append('#e74c3c')  # Red
            else:
                colors.append('#95a5a6')  # Gray
        
        # Highlight Imperial
        colors[list(df_sorted['County']).index('Imperial County')] = '#f39c12'  # Gold
        
        bars = ax.barh(range(len(df_sorted)), df_sorted['Combined_Score'], color=colors, alpha=0.7)
        ax.set_yticks(range(len(df_sorted)))
        ax.set_yticklabels([c.replace(' County', '') for c in df_sorted['County']], fontsize=7)
        ax.set_xlabel('Combined Score', fontsize=12, fontweight='bold')
        ax.set_title('Complete California County Ranking (All 58 Counties)\n' +
                     '🟢 Top 10  |  ⚫ Middle 38  |  🔴 Bottom 10  |  🟡 #1 Imperial',
                     fontsize=14, fontweight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3)
        
        # Add score labels for top 10 and bottom 10
        for i, (idx, row) in enumerate(df_sorted.iterrows()):
            if row['Rank'] <= 10 or row['Rank'] >= 49 or row['County'] == 'Imperial County':
                ax.text(row['Combined_Score'] + 1, i, f"{row['Combined_Score']:.1f}", 
                       va='center', fontsize=7, fontweight='bold')
        
        plt.tight_layout()
        output_file = self.output_dir / '2_full_county_ranking.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_file}")
        plt.close()
    
    def create_price_vs_growth_scatter(self, df):
        """Scatter plot of price vs growth"""
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Create scatter plot
        scatter = ax.scatter(df['Price'], df['YoY_Growth_%'], 
                           s=df['Combined_Score']*5, 
                           c=df['Combined_Score'],
                           cmap='RdYlGn', alpha=0.6, edgecolors='black', linewidth=0.5)
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Combined Score', fontsize=11, fontweight='bold')
        
        # Annotate top 10
        top10 = df.nsmallest(10, 'Rank')
        for _, row in top10.iterrows():
            ax.annotate(row['County'].replace(' County', ''), 
                       (row['Price'], row['YoY_Growth_%']),
                       xytext=(10, 5), textcoords='offset points',
                       fontsize=8, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                       arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', lw=1))
        
        # Highlight Imperial
        imperial = df[df['County'] == 'Imperial County'].iloc[0]
        ax.scatter([imperial['Price']], [imperial['YoY_Growth_%']], 
                  s=500, c='red', marker='*', edgecolors='black', linewidth=2, zorder=5)
        
        ax.set_xlabel('Median Home Price ($)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Year-over-Year Growth (%)', fontsize=12, fontweight='bold')
        ax.set_title('Price vs Growth: California Counties\n(Size = Combined Score)',
                    fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=1)
        
        # Format price axis
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e3:.0f}K'))
        
        plt.tight_layout()
        output_file = self.output_dir / '3_price_vs_growth.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_file}")
        plt.close()
    
    def create_top_bottom_comparison(self, df):
        """Compare top 10 vs bottom 10"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        top10 = df.nsmallest(10, 'Rank')
        bottom10 = df.nlargest(10, 'Rank')
        
        # Chart 1: Price comparison
        ax = axes[0, 0]
        data_price = pd.DataFrame({
            'Top 10': top10['Price'].values,
            'Bottom 10': bottom10['Price'].values
        })
        data_price.plot(kind='box', ax=ax, color=dict(boxes='blue', whiskers='blue', medians='red'))
        ax.set_ylabel('Median Home Price ($)', fontsize=11, fontweight='bold')
        ax.set_title('Price Distribution: Top vs Bottom', fontsize=12, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e3:.0f}K'))
        
        # Chart 2: Growth comparison
        ax = axes[0, 1]
        data_growth = pd.DataFrame({
            'Top 10': top10['YoY_Growth_%'].values,
            'Bottom 10': bottom10['YoY_Growth_%'].values
        })
        data_growth.plot(kind='box', ax=ax, color=dict(boxes='green', whiskers='green', medians='red'))
        ax.set_ylabel('YoY Growth (%)', fontsize=11, fontweight='bold')
        ax.set_title('Growth Distribution: Top vs Bottom', fontsize=12, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        
        # Chart 3: Top 10 detailed
        ax = axes[1, 0]
        top10_sorted = top10.sort_values('Combined_Score', ascending=True)
        bars = ax.barh(range(len(top10_sorted)), top10_sorted['Combined_Score'], 
                      color=['#f39c12' if 'Imperial' in c else '#2ecc71' for c in top10_sorted['County']])
        ax.set_yticks(range(len(top10_sorted)))
        ax.set_yticklabels([c.replace(' County', '') for c in top10_sorted['County']], fontsize=9)
        ax.set_xlabel('Combined Score', fontsize=11, fontweight='bold')
        ax.set_title('🏆 Top 10 Counties (Detailed Scores)', fontsize=12, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        for i, score in enumerate(top10_sorted['Combined_Score']):
            ax.text(score + 1, i, f'{score:.1f}', va='center', fontsize=8, fontweight='bold')
        
        # Chart 4: Bottom 10 detailed
        ax = axes[1, 1]
        bottom10_sorted = bottom10.sort_values('Combined_Score', ascending=True)
        ax.barh(range(len(bottom10_sorted)), bottom10_sorted['Combined_Score'], color='#e74c3c')
        ax.set_yticks(range(len(bottom10_sorted)))
        ax.set_yticklabels([c.replace(' County', '') for c in bottom10_sorted['County']], fontsize=9)
        ax.set_xlabel('Combined Score', fontsize=11, fontweight='bold')
        ax.set_title('📉 Bottom 10 Counties (Detailed Scores)', fontsize=12, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        for i, score in enumerate(bottom10_sorted['Combined_Score']):
            ax.text(score + 0.5, i, f'{score:.1f}', va='center', fontsize=8, fontweight='bold')
        
        plt.suptitle('Top 10 vs Bottom 10 Counties - Detailed Comparison', 
                     fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        
        output_file = self.output_dir / '4_top_bottom_comparison.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_file}")
        plt.close()
    
    def create_score_distribution(self, df):
        """Show distribution of all scores"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # Combined score histogram
        ax = axes[0, 0]
        ax.hist(df['Combined_Score'], bins=20, color='#9b59b6', alpha=0.7, edgecolor='black')
        ax.axvline(df.loc[df['County'] == 'Imperial County', 'Combined_Score'].iloc[0], 
                  color='red', linestyle='--', linewidth=2, label='Imperial County')
        ax.set_xlabel('Combined Score', fontsize=11, fontweight='bold')
        ax.set_ylabel('Number of Counties', fontsize=11, fontweight='bold')
        ax.set_title('Combined Score Distribution (All 58 Counties)', fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # YoY Growth histogram
        ax = axes[0, 1]
        ax.hist(df['YoY_Growth_%'], bins=20, color='#2ecc71', alpha=0.7, edgecolor='black')
        ax.axvline(df.loc[df['County'] == 'Imperial County', 'YoY_Growth_%'].iloc[0],
                  color='red', linestyle='--', linewidth=2, label='Imperial County')
        ax.axvline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
        ax.set_xlabel('YoY Growth (%)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Number of Counties', fontsize=11, fontweight='bold')
        ax.set_title('Growth Distribution', fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # Price histogram
        ax = axes[1, 0]
        ax.hist(df['Price'], bins=20, color='#3498db', alpha=0.7, edgecolor='black')
        ax.axvline(df.loc[df['County'] == 'Imperial County', 'Price'].iloc[0],
                  color='red', linestyle='--', linewidth=2, label='Imperial County')
        ax.set_xlabel('Median Price ($)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Number of Counties', fontsize=11, fontweight='bold')
        ax.set_title('Price Distribution', fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e3:.0f}K'))
        
        # Score correlation
        ax = axes[1, 1]
        ax.scatter(df['Our_Score'], df['Sungjin_Score'], alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
        imperial = df[df['County'] == 'Imperial County'].iloc[0]
        ax.scatter([imperial['Our_Score']], [imperial['Sungjin_Score']], 
                  s=300, c='red', marker='*', edgecolors='black', linewidth=2, zorder=5, label='Imperial')
        
        # Add correlation line
        z = np.polyfit(df['Our_Score'], df['Sungjin_Score'], 1)
        p = np.poly1d(z)
        ax.plot(df['Our_Score'].sort_values(), p(df['Our_Score'].sort_values()), 
               "r--", alpha=0.5, linewidth=2, label=f'Correlation')
        
        ax.set_xlabel('Our Score', fontsize=11, fontweight='bold')
        ax.set_ylabel('Sungjin Score', fontsize=11, fontweight='bold')
        ax.set_title('Methodology Correlation', fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Calculate correlation
        corr = df['Our_Score'].corr(df['Sungjin_Score'])
        ax.text(0.05, 0.95, f'Correlation: {corr:.3f}', transform=ax.transAxes,
               fontsize=10, fontweight='bold', verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.suptitle('Statistical Analysis of California County Rankings', 
                     fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        
        output_file = self.output_dir / '5_score_distribution.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_file}")
        plt.close()

    def create_wealth_migration_map(self):
        """Create wealth migration map (Net AGI)"""
        print("🗺️  Generating CA Wealth Migration Map...")
        
        # Load GeoJSON
        geojson_path = Path('california-counties.geojson')
        if not geojson_path.exists():
            print("❌ GeoJSON not found. Skipping map.")
            return
            
        try:
            gdf = gpd.read_file(geojson_path)
        except Exception as e:
            print(f"❌ Error loading GeoJSON: {e}")
            return
        
        # Load Data
        data_path = self.data_dir / 'ca_wealth_migration.csv'
        if not data_path.exists():
            print(f"❌ Wealth data not found at {data_path}. Skipping map.")
            return
            
        df = pd.read_csv(data_path)
        
        # Prepare Data for Merge
        # Drop geometry from CSV if it exists to avoid conflict with GeoJSON geometry
        if 'geometry' in df.columns:
            df = df.drop(columns=['geometry'])

        # Use NAMELSAD (e.g. "Alameda County") and strip " County" to match GeoJSON "name" (e.g. "Alameda")
        if 'NAMELSAD' in df.columns:
            df['county_clean'] = df['NAMELSAD'].str.replace(' County', '', regex=False)
        elif 'County' in df.columns:
             df['county_clean'] = df['County'].str.replace(' County', '', regex=False)
        else:
            print("❌ Could not find county name column (NAMELSAD or County)")
            return

        merged = gdf.merge(df, left_on='name', right_on='county_clean', how='left')
        merged['net_agi'] = merged['net_agi'].fillna(0)
        
        # Helper for formatting
        def format_currency(val_thousands):
            val_raw = val_thousands * 1000
            if abs(val_raw) >= 1e9:
                return f"${val_raw/1e9:.1f}B"
            else:
                return f"${val_raw/1e6:.1f}M"

        # Print Top/Bottom Counties to Console
        print("\n📊 WEALTH MIGRATION RANKINGS (Net AGI):")
        print("-" * 60)
        
        top_10 = merged.nlargest(10, 'net_agi')[['name', 'net_agi']]
        bottom_10 = merged.nsmallest(10, 'net_agi')[['name', 'net_agi']]
        
        print("🟢 TOP 10 GAINERS (Net Inflow):")
        for idx, row in top_10.iterrows():
            print(f"   {row['name']:<20} {format_currency(row['net_agi'])}")
            
        print("\n🔴 BOTTOM 10 LOSERS (Net Outflow):")
        for idx, row in bottom_10.iterrows():
            print(f"   {row['name']:<20} {format_currency(row['net_agi'])}")
        print("-" * 60)
        
        # Plot
        fig, ax = plt.subplots(1, 1, figsize=(15, 15))
        
        # Diverging colormap centered at 0
        # Use symmetric limits for colorbar to ensure 0 is white
        max_abs = max(abs(merged['net_agi'].min()), abs(merged['net_agi'].max()))
        divnorm = mcolors.TwoSlopeNorm(vmin=-max_abs, vcenter=0, vmax=max_abs)
        
        cax = ax.inset_axes([0.9, 0.55, 0.03, 0.4])
        
        merged.plot(column='net_agi', ax=ax, 
                   cmap='RdYlGn', 
                   norm=divnorm,
                   edgecolor='gray', linewidth=0.5,
                   legend=True,
                   cax=cax,
                   legend_kwds={'orientation': "vertical"})
        
        # Highlight Riverside County
        riverside = merged[merged['name'] == 'Riverside']
        if not riverside.empty:
            riverside.plot(ax=ax, facecolor='none', edgecolor='cyan', linewidth=3, zorder=5)
            # Add a specific label for it if not already top/bottom (it is top, but good to ensure)
            centroid = riverside.geometry.centroid.iloc[0]
            val = riverside['net_agi'].iloc[0]
            label_text = f"RIVERSIDE\n{format_currency(val)}"
            ax.annotate(label_text, xy=(centroid.x, centroid.y), ha='center', va='center',
                       fontsize=10, fontweight='bold', color='black',
                       bbox=dict(boxstyle="round,pad=0.2", fc="cyan", ec="black", alpha=0.8, lw=1))
                   
        cax.set_ylabel("Net AGI Migration (Thousands $)", fontsize=12, fontweight='bold', labelpad=10)
        cax.tick_params(labelsize=10)
        
        # Labels for top 5 and bottom 5
        top_5 = merged.nlargest(5, 'net_agi')
        bottom_5 = merged.nsmallest(5, 'net_agi')
        labels_to_plot = pd.concat([top_5, bottom_5])
        
        for idx, row in labels_to_plot.iterrows():
            if row['name'] == 'Riverside':
                continue
                
            centroid = row.geometry.centroid
            label_text = f"{row['name']}\n{format_currency(row['net_agi'])}"
            
            ax.annotate(label_text, xy=(centroid.x, centroid.y), ha='center', va='center',
                       fontsize=8, fontweight='bold', color='black',
                       bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7))
                       
        ax.set_title('California Wealth Migration Trends (Net AGI)', fontsize=20, fontweight='bold')
        ax.set_axis_off()
        plt.figtext(0.5, 0.05, "Source: IRS Migration Data (2021-2022)", ha="center", fontsize=12, color="gray")
        
        output_file = self.output_dir / '6_wealth_migration_map.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_file}")
        plt.close()
    
    def run(self):
        """Generate all visualizations"""
        print("\n" + "="*80)
        print("🎨 GENERATING VISUALIZATIONS")
        print("="*80)
        
        df = self.load_data()
        
        print("\nCreating visualizations...")
        self.create_score_comparison(df)
        self.create_full_ranking_visualization(df)
        self.create_price_vs_growth_scatter(df)
        self.create_top_bottom_comparison(df)
        self.create_score_distribution(df)
        self.create_wealth_migration_map()
        
        print("\n" + "="*80)
        print("✓ ALL VISUALIZATIONS COMPLETE")
        print("="*80)
        print(f"\nOutput directory: {self.output_dir.absolute()}")
        print("\nFiles created:")
        print("  1. methodology_comparison.png - Top 15 counties by each method")
        print("  2. full_county_ranking.png - All 58 counties ranked")
        print("  3. price_vs_growth.png - Scatter plot showing relationships")
        print("  4. top_bottom_comparison.png - Top 10 vs Bottom 10 analysis")
        print("  5. score_distribution.png - Statistical distributions")
        print("  6. wealth_migration_map.png - Net AGI migration trends")
        print("\n")

if __name__ == "__main__":
    viz = CountyRankingVisualizations()
    viz.run()
