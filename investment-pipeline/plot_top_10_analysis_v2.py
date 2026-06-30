import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

def create_top_10_analysis():
    print("📊 Generating Top 10 Counties Analysis...")
    
    # 1. Load Data
    data_path = Path('housing_market_data/processed/all_counties_ranking_v2.csv')
    if not data_path.exists():
        print(f"❌ Data not found at {data_path}")
        return
        
    df = pd.read_csv(data_path)
    
    # 2. Get Top 10
    top_10 = df.nlargest(10, 'score_v2_norm').sort_values('score_v2_norm', ascending=True) # Ascending for horizontal bar chart
    
    # 3. Setup Plot
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    
    # Define Highlights
    highlight_colors = {
        'San Luis Obispo County': '#32CD32', # Lime Green
        'Riverside County': '#00BFFF',       # Deep Sky Blue
        'Imperial County': '#FF1493'         # Deep Pink
    }
    default_color = '#D3D3D3' # Light Gray
    
    # --- Plot 1: Bar Chart (Left) ---
    ax1 = axes[0]
    
    # Create color list based on county names
    bar_colors = [highlight_colors.get(c, default_color) for c in top_10['county']]
    
    bars = ax1.barh(top_10['county'], top_10['score_v2_norm'], color=bar_colors, edgecolor='black', alpha=0.9)
    
    ax1.set_title('Top 10 Counties by Investment Score (V2)', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Z-Score (0-100)', fontsize=12)
    ax1.grid(axis='x', linestyle='--', alpha=0.5)
    
    # Add value labels
    for bar in bars:
        width = bar.get_width()
        ax1.text(width + 1, bar.get_y() + bar.get_height()/2, 
                f'{width:.1f}', 
                va='center', fontsize=10, fontweight='bold')

    # --- Plot 2: Scatter Plot (Right) - Growth vs Yield ---
    ax2 = axes[1]
    
    # Use same colors for points
    # We need to re-sort top_10 for scatter or just iterate
    # Let's use the same top_10 dataframe
    
    for _, row in top_10.iterrows():
        color = highlight_colors.get(row['county'], 'gray') # Gray for non-highlighted in scatter
        size = 150 if row['county'] in highlight_colors else 80
        alpha = 1.0 if row['county'] in highlight_colors else 0.6
        
        ax2.scatter(row['growth_combined'], row['actual_yield'], 
                   c=color, s=size, edgecolors='black', alpha=alpha, zorder=3)
        
        # Label points
        label_weight = 'bold' if row['county'] in highlight_colors else 'normal'
        ax2.text(row['growth_combined'], row['actual_yield'] + 0.1, 
                row['county'].replace(' County', ''), 
                fontsize=9, ha='center', fontweight=label_weight)

    ax2.set_title('Growth vs Yield Trade-off (Top 10)', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Combined Growth Score', fontsize=12)
    ax2.set_ylabel('Actual Rental Yield (%)', fontsize=12)
    ax2.grid(True, linestyle='--', alpha=0.5)
    
    # Add quadrants or average lines
    avg_growth = df['growth_combined'].mean()
    avg_yield = df['actual_yield'].mean()
    ax2.axvline(avg_growth, color='gray', linestyle=':', alpha=0.5, label='State Avg Growth')
    ax2.axhline(avg_yield, color='gray', linestyle=':', alpha=0.5, label='State Avg Yield')
    ax2.legend(loc='upper right')

    plt.tight_layout()
    
    # Save
    output_file = 'visualizations/top_10_analysis_v2.png'
    plt.savefig(output_file, dpi=300)
    print(f"✅ Saved analysis to {output_file}")

if __name__ == "__main__":
    create_top_10_analysis()
