import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

def create_top_20_analysis():
    print("📊 Generating Top 20 Counties Analysis...")
    
    # 1. Load Data
    data_path = Path('housing_market_data/processed/all_counties_ranking_v2.csv')
    if not data_path.exists():
        print(f"❌ Data not found at {data_path}")
        return
        
    df = pd.read_csv(data_path)
    
    # 2. Get Top 20
    top_20 = df.nlargest(20, 'score_v2_norm').sort_values('score_v2_norm', ascending=True) # Ascending for horizontal bar chart
    
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
    bar_colors = [highlight_colors.get(c, default_color) for c in top_20['county']]
    
    bars = ax1.barh(top_20['county'], top_20['score_v2_norm'], color=bar_colors, edgecolor='black', alpha=0.9)
    
    ax1.set_title('Top 20 Counties by Investment Score', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Z-Score (0-100)', fontsize=12)
    ax1.grid(axis='x', linestyle='--', alpha=0.5)
    
    # Add value labels
    for i, bar in enumerate(bars):
        width = bar.get_width()
        county_name = top_20['county'].iloc[i]
        
        # Check if highlighted
        is_highlight = county_name in highlight_colors
        font_weight = 'bold' if is_highlight else 'normal'
        font_size = 12 if is_highlight else 10
        
        ax1.text(width + 1, bar.get_y() + bar.get_height()/2, 
                f'{width:.1f}', 
                va='center', fontsize=font_size, fontweight=font_weight)
        
        # Also bold the y-axis label for this bar
        if is_highlight:
            ax1.get_yticklabels()[i].set_fontweight('bold')
            ax1.get_yticklabels()[i].set_fontsize(12)

    # --- Plot 2: Scatter Plot (Right) - Growth vs Yield ---
    ax2 = axes[1]
    
    # Use same colors for points
    # We need to re-sort top_20 for scatter or just iterate
    # Let's use the same top_20 dataframe
    
    for _, row in top_20.iterrows():
        color = highlight_colors.get(row['county'], 'gray') # Gray for non-highlighted in scatter
        is_highlight = row['county'] in highlight_colors
        
        size = 200 if is_highlight else 80
        alpha = 1.0 if is_highlight else 0.6
        
        ax2.scatter(row['growth_combined'], row['actual_yield'], 
                   c=color, s=size, edgecolors='black', alpha=alpha, zorder=3)
        
        # Label points
        label_weight = 'bold' if is_highlight else 'normal'
        label_size = 12 if is_highlight else 9
        
        ax2.text(row['growth_combined'], row['actual_yield'] + 0.1, 
                row['county'].replace(' County', ''), 
                fontsize=label_size, ha='center', fontweight=label_weight)

    ax2.set_title('Growth vs Yield Trade-off (Top 20)', fontsize=14, fontweight='bold')
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
    output_file = 'visualizations/top_20_analysis_v2.png'
    plt.savefig(output_file, dpi=300)
    print(f"✅ Saved analysis to {output_file}")

if __name__ == "__main__":
    create_top_20_analysis()
