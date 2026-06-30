#!/usr/bin/env python3
"""
Comparison Plot: Z-Score V1 vs V2 (ZORI Enhanced)
Visualizes how adding actual rental data changes the investment rankings.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg') # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)

def load_data():
    data_dir = Path('housing_market_data/processed')
    
    # Load V1 (Original Z-Score)
    v1 = pd.read_csv(data_dir / 'all_counties_ranking_zscore.csv')
    v1 = v1[['county', 'z_score_normalized', 'rank_zscore']].rename(
        columns={'z_score_normalized': 'score_v1', 'rank_zscore': 'rank_v1'}
    )
    
    # Load V2 (ZORI Enhanced)
    v2 = pd.read_csv(data_dir / 'all_counties_ranking_v2.csv')
    # Create rank if not exists
    if 'rank_v2' not in v2.columns:
        v2['rank_v2'] = v2['z_score_v2'].rank(ascending=False)
        
    # Merge
    df = v2.merge(v1, on='county', how='inner')
    
    # Calculate differences
    df['rank_change'] = df['rank_v1'] - df['rank_v2'] # Positive = Improved Rank
    df['score_change'] = df['score_v2_norm'] - df['score_v1']
    
    return df

def create_comparison_plot(df):
    print("📊 Creating Comparison Plot...")
    
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])
    
    # 1. Main Scatter: V1 vs V2
    ax1 = fig.add_subplot(gs[0, :])
    
    # Color by Actual Yield
    scatter = ax1.scatter(df['score_v1'], df['score_v2_norm'], 
                         c=df['actual_yield'], cmap='viridis_r', 
                         s=100, alpha=0.8, edgecolors='black')
    
    # Diagonal line (No Change)
    min_val = min(df['score_v1'].min(), df['score_v2_norm'].min())
    max_val = max(df['score_v1'].max(), df['score_v2_norm'].max())
    ax1.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.3, label='No Change')
    
    # Annotate biggest movers
    # Biggest Gainers (V2 > V1)
    gainers = df.nlargest(5, 'score_change')
    for _, row in gainers.iterrows():
        ax1.annotate(f"{row['county']}\n(+{row['score_change']:.1f})", 
                    (row['score_v1'], row['score_v2_norm']),
                    xytext=(-20, 20), textcoords='offset points',
                    arrowprops=dict(arrowstyle='->', color='green'),
                    fontsize=9, fontweight='bold', color='green')
        
    # Biggest Losers (V2 < V1)
    losers = df.nsmallest(5, 'score_change')
    for _, row in losers.iterrows():
        ax1.annotate(f"{row['county']}\n({row['score_change']:.1f})", 
                    (row['score_v1'], row['score_v2_norm']),
                    xytext=(20, -20), textcoords='offset points',
                    arrowprops=dict(arrowstyle='->', color='red'),
                    fontsize=9, fontweight='bold', color='red')

    ax1.set_xlabel('V1 Score (Estimated Yield)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('V2 Score (Actual ZORI Yield)', fontsize=12, fontweight='bold')
    ax1.set_title('Impact of Real Rental Data: V1 vs V2 Scoring', fontsize=15, fontweight='bold')
    
    cbar = plt.colorbar(scatter, ax=ax1)
    cbar.set_label('Actual Rental Yield (%)', fontsize=11, fontweight='bold')
    
    ax1.grid(True, alpha=0.3)
    
    # 2. Bar Chart: Top 10 V2 Counties
    ax2 = fig.add_subplot(gs[1, 0])
    top_10 = df.nlargest(10, 'score_v2_norm')
    sns.barplot(data=top_10, x='score_v2_norm', y='county', palette='viridis', ax=ax2)
    ax2.set_title('Top 10 Counties (V2 Model)', fontweight='bold')
    ax2.set_xlabel('V2 Score')
    ax2.set_ylabel('')
    
    # 3. Bar Chart: Yield vs Growth for Top 10
    ax3 = fig.add_subplot(gs[1, 1])
    # Normalize for comparison
    top_10_melt = top_10[['county', 'actual_yield', 'growth_combined']].melt(id_vars='county')
    
    # Dual axis or side-by-side? Let's do a scatter for Top 10
    sns.scatterplot(data=top_10, x='growth_combined', y='actual_yield', hue='county', s=200, ax=ax3, legend=False)
    
    # Label points
    for _, row in top_10.iterrows():
        ax3.text(row['growth_combined']+0.5, row['actual_yield'], 
                row['county'].replace(' County', ''), fontsize=9)
                
    ax3.set_title('Top 10: Growth vs Yield Trade-off', fontweight='bold')
    ax3.set_xlabel('Combined Growth (%)')
    ax3.set_ylabel('Actual Yield (%)')
    ax3.grid(True)
    
    plt.tight_layout()
    output_file = Path('visualizations/v1_vs_v2_comparison.png')
    plt.savefig(output_file, dpi=300)
    print(f"✅ Saved plot to {output_file}")

if __name__ == "__main__":
    df = load_data()
    create_comparison_plot(df)
    
    # Print Summary Table
    print("\n" + "="*80)
    print("SUMMARY: BIGGEST RANKING CHANGES")
    print("="*80)
    print(f"{'County':<25} {'Rank V1':<8} {'Rank V2':<8} {'Change':<8} {'Yield':<8}")
    print("-" * 80)
    
    # Sort by rank change (Gainers first)
    df_sorted = df.sort_values('rank_change', ascending=False)
    
    # Top 5 Gainers
    for _, row in df_sorted.head(5).iterrows():
        print(f"{row['county']:<25} #{row['rank_v1']:<7.0f} #{row['rank_v2']:<7.0f} +{row['rank_change']:<7.0f} {row['actual_yield']:.2f}%")
        
    print("..." * 10)
    
    # Top 5 Losers
    for _, row in df_sorted.tail(5).iterrows():
        print(f"{row['county']:<25} #{row['rank_v1']:<7.0f} #{row['rank_v2']:<7.0f} {row['rank_change']:<7.0f} {row['actual_yield']:.2f}%")
