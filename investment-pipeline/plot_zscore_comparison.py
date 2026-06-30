#!/usr/bin/env python3
"""
Seaborn Scatter Plot: Z-Score vs Old Total Score Comparison
Visualizes the relationship between the two scoring methodologies
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)

# Load data
data_dir = Path('housing_market_data/processed')
df_zscore = pd.read_csv(data_dir / 'all_counties_ranking_zscore.csv')

print("=" * 100)
print("📊 Z-SCORE vs OLD METHOD COMPARISON - SCATTER PLOT ANALYSIS")
print("=" * 100)
print(f"\nTotal counties: {len(df_zscore)}")
print(f"\nZ-Score Method - Stats:")
print(f"  Mean: {df_zscore['z_score_normalized'].mean():.2f}")
print(f"  Median: {df_zscore['z_score_normalized'].median():.2f}")
print(f"  Std Dev: {df_zscore['z_score_normalized'].std():.2f}")
print(f"\nOld Method - Stats:")
print(f"  Mean: {df_zscore['final_score_old'].mean():.2f}")
print(f"  Median: {df_zscore['final_score_old'].median():.2f}")
print(f"  Std Dev: {df_zscore['final_score_old'].std():.2f}")

# Create figure with subplots
fig = plt.figure(figsize=(16, 12))
gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

# 1. Main scatter plot: Z-Score vs Old Method
ax1 = fig.add_subplot(gs[0:2, :])
scatter = ax1.scatter(df_zscore['final_score_old'], 
                      df_zscore['z_score_normalized'],
                      c=df_zscore['z_score_final'],
                      cmap='RdYlGn',
                      s=100,
                      alpha=0.6,
                      edgecolors='black',
                      linewidth=0.5)

# Add diagonal reference line (perfect agreement)
min_val = min(df_zscore['final_score_old'].min(), df_zscore['z_score_normalized'].min())
max_val = max(df_zscore['final_score_old'].max(), df_zscore['z_score_normalized'].max())
ax1.plot([min_val, max_val], [min_val, max_val], 'k--', alpha=0.3, linewidth=2, label='Perfect Agreement')

# Annotate top counties (z-score method)
top_counties = df_zscore.nlargest(5, 'z_score_final')
for _, row in top_counties.iterrows():
    ax1.annotate(row['county'], 
                xy=(row['final_score_old'], row['z_score_normalized']),
                xytext=(5, 5), 
                textcoords='offset points',
                fontsize=9,
                fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='red'))

ax1.set_xlabel('Old Method Score (0-100)', fontsize=13, fontweight='bold')
ax1.set_ylabel('Z-Score Method Score (0-100)', fontsize=13, fontweight='bold')
ax1.set_title('California County Investment Scores: Z-Score vs Old Method Comparison', 
              fontsize=15, fontweight='bold', pad=20)
ax1.legend(fontsize=11)
ax1.grid(True, alpha=0.3)

# Add colorbar
cbar = plt.colorbar(scatter, ax=ax1)
cbar.set_label('Raw Z-Score', fontsize=11, fontweight='bold')

# Calculate correlation
correlation = df_zscore['z_score_normalized'].corr(df_zscore['final_score_old'])
ax1.text(0.02, 0.98, f'Correlation: {correlation:.3f}', 
         transform=ax1.transAxes, fontsize=12, verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

# 2. Distribution of Z-Score Method
ax2 = fig.add_subplot(gs[2, 0])
sns.histplot(data=df_zscore, x='z_score_normalized', bins=30, kde=True, 
             color='green', alpha=0.6, ax=ax2)
ax2.axvline(df_zscore['z_score_normalized'].mean(), color='red', linestyle='--', 
            linewidth=2, label=f'Mean: {df_zscore["z_score_normalized"].mean():.1f}')
ax2.axvline(df_zscore['z_score_normalized'].median(), color='blue', linestyle='--', 
            linewidth=2, label=f'Median: {df_zscore["z_score_normalized"].median():.1f}')
ax2.set_xlabel('Z-Score Method Score', fontsize=11, fontweight='bold')
ax2.set_ylabel('Count', fontsize=11, fontweight='bold')
ax2.set_title('Distribution: Z-Score Method', fontsize=12, fontweight='bold')
ax2.legend()
ax2.grid(True, alpha=0.3)

# 3. Distribution of Old Method
ax3 = fig.add_subplot(gs[2, 1])
sns.histplot(data=df_zscore, x='final_score_old', bins=30, kde=True, 
             color='orange', alpha=0.6, ax=ax3)
ax3.axvline(df_zscore['final_score_old'].mean(), color='red', linestyle='--', 
            linewidth=2, label=f'Mean: {df_zscore["final_score_old"].mean():.1f}')
ax3.axvline(df_zscore['final_score_old'].median(), color='blue', linestyle='--', 
            linewidth=2, label=f'Median: {df_zscore["final_score_old"].median():.1f}')
ax3.set_xlabel('Old Method Score', fontsize=11, fontweight='bold')
ax3.set_ylabel('Count', fontsize=11, fontweight='bold')
ax3.set_title('Distribution: Old Method', fontsize=12, fontweight='bold')
ax3.legend()
ax3.grid(True, alpha=0.3)

plt.tight_layout()

# Save plot
output_file = 'visualizations/zscore_vs_old_comparison.png'
Path('visualizations').mkdir(exist_ok=True)
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n✅ Plot saved to: {output_file}")
plt.close()

# ============================================================================
# Additional Analysis: Biggest Disagreements
# ============================================================================

print("\n" + "=" * 100)
print("📈 BIGGEST DISAGREEMENTS BETWEEN METHODS")
print("=" * 100)

# Calculate score difference
df_zscore['score_diff'] = df_zscore['z_score_normalized'] - df_zscore['final_score_old']

print("\n🔼 Counties favored by Z-Score Method (top 10):")
print("-" * 100)
favored_zscore = df_zscore.nlargest(10, 'score_diff')
for idx, row in favored_zscore.iterrows():
    print(f"  {row['county']:<25} Z-Score: {row['z_score_normalized']:>5.1f}  |  "
          f"Old: {row['final_score_old']:>5.1f}  |  Diff: {row['score_diff']:>+6.1f}  |  "
          f"Growth: {row['growth_combined']:>6.2f}%")

print("\n🔽 Counties favored by Old Method (top 10):")
print("-" * 100)
favored_old = df_zscore.nsmallest(10, 'score_diff')
for idx, row in favored_old.iterrows():
    print(f"  {row['county']:<25} Z-Score: {row['z_score_normalized']:>5.1f}  |  "
          f"Old: {row['final_score_old']:>5.1f}  |  Diff: {row['score_diff']:>+6.1f}  |  "
          f"Price: ${row['price']:>,.0f}")

# ============================================================================
# Create second figure: Component comparison
# ============================================================================

fig2, axes = plt.subplots(2, 2, figsize=(14, 10))
fig2.suptitle('Score Components: Z-Score vs Old Method', fontsize=16, fontweight='bold', y=1.00)

# Growth component
axes[0, 0].scatter(df_zscore['growth_combined'], df_zscore['z_growth'], 
                   c=df_zscore['z_score_final'], cmap='RdYlGn', s=50, alpha=0.6)
axes[0, 0].set_xlabel('Combined Growth (%)', fontweight='bold')
axes[0, 0].set_ylabel('Growth Z-Score', fontweight='bold')
axes[0, 0].set_title('Growth Component', fontweight='bold')
axes[0, 0].grid(True, alpha=0.3)

# Affordability component
axes[0, 1].scatter(df_zscore['price'], df_zscore['z_affordability'], 
                   c=df_zscore['z_score_final'], cmap='RdYlGn', s=50, alpha=0.6)
axes[0, 1].set_xlabel('Price ($)', fontweight='bold')
axes[0, 1].set_ylabel('Affordability Z-Score', fontweight='bold')
axes[0, 1].set_title('Affordability Component (Inverted)', fontweight='bold')
axes[0, 1].grid(True, alpha=0.3)

# Demographics component
axes[1, 0].scatter(df_zscore['pop_growth'], df_zscore['z_demographics'], 
                   c=df_zscore['z_score_final'], cmap='RdYlGn', s=50, alpha=0.6)
axes[1, 0].set_xlabel('Population Growth (%)', fontweight='bold')
axes[1, 0].set_ylabel('Demographics Z-Score', fontweight='bold')
axes[1, 0].set_title('Demographics Component', fontweight='bold')
axes[1, 0].grid(True, alpha=0.3)

# Yield component
axes[1, 1].scatter(df_zscore['yield'], df_zscore['z_yield'], 
                   c=df_zscore['z_score_final'], cmap='RdYlGn', s=50, alpha=0.6)
axes[1, 1].set_xlabel('Estimated Yield (%)', fontweight='bold')
axes[1, 1].set_ylabel('Yield Z-Score', fontweight='bold')
axes[1, 1].set_title('Yield Component', fontweight='bold')
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()

# Save second plot
output_file2 = 'visualizations/zscore_components_breakdown.png'
plt.savefig(output_file2, dpi=300, bbox_inches='tight')
print(f"✅ Component breakdown plot saved to: {output_file2}")
plt.close()

print("\n" + "=" * 100)
print("✓ ANALYSIS COMPLETE")
print("=" * 100)
