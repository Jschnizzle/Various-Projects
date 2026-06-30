import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def create_map():
    print("🗺️  Generating CA Z-Score Map...")

    # 1. Load Data
    try:
        gdf = gpd.read_file('california-counties.geojson')
        df = pd.read_csv('housing_market_data/processed/all_counties_ranking_v2.csv')
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    # 2. Prepare Data for Merge
    # CSV has "Alameda County", GeoJSON has "Alameda"
    df['county_clean'] = df['county'].str.replace(' County', '', regex=False)
    
    # Handle special cases if any (e.g. San Francisco)
    # San Francisco might be "San Francisco" in both or "San Francisco County" in CSV
    # The replace above handles "San Francisco County" -> "San Francisco"
    
    # Merge
    merged = gdf.merge(df, left_on='name', right_on='county_clean', how='left')
    
    # Fill NaN scores with 0 or min for plotting purposes (though all CA counties should match)
    merged['score_v2_norm'] = merged['score_v2_norm'].fillna(0)

    # 3. Setup Plot
    fig, ax = plt.subplots(1, 1, figsize=(15, 15))
    
    # 4. Plot Base Map (All Counties) - Light Yellow
    base_plot = merged.plot(ax=ax, 
                           color='#FFFACD', # LemonChiffon (Light Yellow)
                           edgecolor='gray', linewidth=0.5)

    # 5. Highlight Specific Counties
    # "different color coding for each {Riverside, San Luis Obispo, and Imperial}"
    
    highlights = {
        'Riverside': {'color': '#00BFFF', 'label': 'Riverside (High Growth)'},       # Deep Sky Blue
        'San Luis Obispo': {'color': '#32CD32', 'label': 'San Luis Obispo (Stable)'}, # Lime Green
        'Imperial': {'color': '#FF1493', 'label': 'Imperial (Emerging)'}             # Deep Pink
    }
    
    for county_name, style in highlights.items():
        subset = merged[merged['name'] == county_name]
        
        if not subset.empty:
            # Plot the county with distinct color
            subset.plot(ax=ax, color=style['color'], edgecolor='black', linewidth=2)
            
            # Add Label
            # Get centroid for label placement
            centroid = subset.geometry.centroid.iloc[0]
            
            # Adjust label position slightly if needed
            x, y = centroid.x, centroid.y
            
            ax.annotate(county_name, 
                       xy=(x, y), 
                       xytext=(0, 0), 
                       textcoords="offset points",
                       ha='center', va='center',
                       fontsize=10, fontweight='bold', color='black',
                       bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", alpha=0.8))
    
    # 6. Final Touches
    # ax.set_title('Top 3 Counties of Investment Choice', fontsize=18, fontweight='bold')
    ax.set_axis_off()
    
    # Add a custom legend for the highlighted counties
    # We create dummy patches
    import matplotlib.patches as mpatches
    legend_patches = [mpatches.Patch(color=style['color'], label=style['label']) for name, style in highlights.items()]
    
    # Add second legend
    # We need to add the first legend back if we create a new one, or add to it.
    # Actually, the colorbar is separate. We can add a legend for the highlights.
    # leg = ax.legend(handles=legend_patches, loc='upper right', title='Key Counties', fontsize=10, title_fontsize=12)
    # ax.add_artist(leg)

    # Save
    output_path = 'visualizations/ca_zscore_map_highlighted.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Map saved to {output_path}")

if __name__ == "__main__":
    create_map()
