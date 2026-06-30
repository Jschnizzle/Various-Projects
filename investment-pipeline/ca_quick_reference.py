#!/usr/bin/env python3
"""
Quick Reference Table for Top CA Counties
"""

import pandas as pd

# Top picks with key metrics
data = {
    'Rank': [1, 2, 3, 4, 5],
    'County': [
        'Imperial County',
        'Kings County', 
        'Yuba County',
        'Madera County',
        'Placer County'
    ],
    'Entry_Price': [365425, 355330, 412777, 417882, 675913],
    'YoY_Growth': [6.83, 2.04, 0.82, 1.35, 0.18],
    'CAGR_3Y': [5.79, 2.47, None, None, None],
    'Pop_Growth': [None, None, 1.6, 1.6, 1.3],
    'Region': ['Southern CA', 'Central Valley', 'North CA', 'Central Valley', 'Sacramento Metro'],
    'Key_Cities': ['El Centro, Calexico', 'Hanford, Lemoore', 'Marysville', 'Oakhurst', 'Roseville, Rocklin'],
    'Investment_Grade': ['A+', 'A', 'A', 'A-', 'B+']
}

df = pd.DataFrame(data)

print("\n" + "="*100)
print("🏔️  TOP 5 CALIFORNIA COUNTIES FOR INVESTMENT - QUICK REFERENCE")
print("="*100)
print()
print(df.to_string(index=False))
print()
print("="*100)
print("\n💡 KEY INSIGHTS:")
print()
print("✅ IMPERIAL COUNTY: Clear winner - highest growth in CA (6.83% YoY)")
print("   • Entry: $365K (affordable)")
print("   • 3-Year CAGR: 5.79% (proven track record)")
print("   • Location: Southern CA border region")
print()
print("✅ CENTRAL VALLEY: Best region overall")
print("   • Kings, Madera counties offer strong value")
print("   • Prices: $355K-$418K range")
print("   • Growth: 1.35-2.04% YoY")
print()
print("✅ POPULATION PLAYS: Yuba & Madera")
print("   • Both showing 1.6% population growth (highest in CA)")
print("   • Demographic tailwind = sustained demand")
print()
print("🟡 PLACER COUNTY: Premium option")
print("   • Higher entry ($676K) but better fundamentals")
print("   • Sacramento metro spillover")
print("   • Quality of life + job market")
print()
print("="*100)
print("\n📊 COMPARISON TO NATIONAL ALTERNATIVES:")
print()
print("Imperial County ($365K, +6.83%) vs Chicago, IL ($337K, +0.99%)")
print("   → Imperial wins on GROWTH, Chicago wins on CASH FLOW (7.4% yield)")
print()
print("Kings County ($355K, +2.04%) vs Pittsburgh, PA ($222K, +0.08%)")
print("   → Pittsburgh much cheaper with 7.95% yield, Kings better appreciation")
print()
print("="*100)
print()
print("🎯 RECOMMENDED ACTION:")
print("   1. Focus on IMPERIAL COUNTY first (highest growth + affordable)")
print("   2. Add KINGS or YUBA as second property")
print("   3. Consider PLACER for higher-end portfolio")
print()
print("="*100)
print()

# Save to file
output_path = 'housing_market_data/processed/ca_top_counties.csv'
df.to_csv(output_path, index=False)
print(f"✓ Quick reference saved to: {output_path}\n")
