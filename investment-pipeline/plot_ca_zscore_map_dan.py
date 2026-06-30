import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def create_map():
    print("🗺️  Generating CA Z-Score Map (Rural Development Area)...")

    # 1. Load Data
    try:
        gdf = gpd.read_file('california-counties.geojson')
        df = pd.read_csv('housing_market_data/processed/all_counties_ranking_v2.csv')
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    # 2. Prepare Data for Merge
    df['county_clean'] = df['county'].str.replace(' County', '', regex=False)
    merged = gdf.merge(df, left_on='name', right_on='county_clean', how='left')
    merged['score_v2_norm'] = merged['score_v2_norm'].fillna(0)

    # 3. Setup Plot
    fig, ax = plt.subplots(1, 1, figsize=(15, 15))
    
    # 4. Plot Base Map
    # Color scale: Light Blue to Purple-Blue
    # 'PuBu' is Purple-Blue, 'BuPu' is Blue-Purple. 
    # User asked for "light blue to purple-blue", so 'BuPu' or 'PuBu' works. 
    # Let's use 'PuBu' (starts light purple/white, goes to dark blue) or 'Blues' or 'YlGnBu'.
    # Actually 'BuPu' starts white/light blue and goes to purple.
    # Let's try 'BuPu'.
    
    # Create custom axis for colorbar vertical on top right side
    # [x, y, width, height] relative to parent axes
    cax = ax.inset_axes([0.9, 0.55, 0.03, 0.4])

    base_plot = merged.plot(column='score_v2_norm', ax=ax, 
                           cmap='BuPu', 
                           edgecolor='gray', linewidth=0.5,
                           legend=True,
                           cax=cax,
                           legend_kwds={'orientation': "vertical"})

    # Adjust Colorbar Text Size
    cax.set_ylabel("Standardized Investment Score (0-100)", fontsize=16, fontweight='bold', labelpad=10)
    cax.tick_params(labelsize=14)

    # 5. Highlight/Label Counties with Z-Score > 50
    high_score_counties = merged[merged['score_v2_norm'] > 50]
    
    print(f"Found {len(high_score_counties)} counties with score > 50")
    
    for idx, row in high_score_counties.iterrows():
        # Get centroid for label placement
        centroid = row.geometry.centroid
        x, y = centroid.x, centroid.y
        
        # Annotate
        ax.annotate(row['name'], 
                   xy=(x, y), 
                   xytext=(0, 0), 
                   textcoords="offset points",
                   ha='center', va='center',
                   fontsize=9, fontweight='bold', color='black',
                   bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.6))
    
    # 6. Final Touches
    # ax.set_title('Rural Development Area', fontsize=20, fontweight='bold')
    # ax.set_axis_off()
    
    # Save
    output_path = 'visualizations/ca_rural_development_map.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Map saved to {output_path}")

if __name__ == "__main__":
    create_map()
