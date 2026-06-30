import pandas as pd
import numpy as np
from pathlib import Path

def create_tx_county_master():
    data_dir = Path('housing_market_data')
    output_dir = data_dir / 'processed'
    output_dir.mkdir(exist_ok=True)

    # 1. Load ZHVI Data
    zhvi_path = data_dir / 'zillow' / 'zhvi_county.csv'
    if not zhvi_path.exists():
        print(f"Error: {zhvi_path} not found.")
        return

    print("Loading ZHVI data...")
    zhvi_df = pd.read_csv(zhvi_path)
    
    # Filter for Texas
    tx_zhvi = zhvi_df[zhvi_df['StateName'] == 'TX'].copy()
    
    # Create FIPS
    tx_zhvi['StateCodeFIPS'] = tx_zhvi['StateCodeFIPS'].astype(str).str.zfill(2)
    tx_zhvi['MunicipalCodeFIPS'] = tx_zhvi['MunicipalCodeFIPS'].astype(str).str.zfill(3)
    tx_zhvi['fips'] = tx_zhvi['StateCodeFIPS'] + tx_zhvi['MunicipalCodeFIPS']
    
    # Identify date columns
    date_cols = [c for c in tx_zhvi.columns if c[0].isdigit() and '-' in c]
    id_vars = ['fips', 'RegionName', 'RegionType', 'StateName']
    
    # Melt to long format
    print("Reshaping ZHVI data...")
    tx_long = tx_zhvi.melt(id_vars=id_vars, value_vars=date_cols, var_name='date', value_name='zhvi')
    tx_long['date'] = pd.to_datetime(tx_long['date'])
    
    # 2. Load Population Data
    pop_path = data_dir / 'census' / 'population_estimates.csv'
    if not pop_path.exists():
        print(f"Error: {pop_path} not found.")
        return

    print("Loading Population data...")
    try:
        pop_df = pd.read_csv(pop_path, encoding='latin-1')
    except:
        pop_df = pd.read_csv(pop_path)
        
    # Filter for Texas
    tx_pop = pop_df[pop_df['STNAME'] == 'Texas'].copy()
    
    # Create FIPS
    tx_pop['STATE'] = tx_pop['STATE'].astype(str).str.zfill(2)
    tx_pop['COUNTY'] = tx_pop['COUNTY'].astype(str).str.zfill(3)
    tx_pop['fips'] = tx_pop['STATE'] + tx_pop['COUNTY']
    
    # Extract population columns (POPESTIMATE2020-2023)
    pop_cols = [c for c in tx_pop.columns if 'POPESTIMATE' in c]
    
    pop_long = tx_pop.melt(id_vars=['fips'], value_vars=pop_cols, var_name='year_col', value_name='population')
    pop_long['year'] = pop_long['year_col'].str.extract(r'(\d{4})').astype(int)
    
    # Merge
    tx_long['year'] = tx_long['date'].dt.year
    
    print("Merging datasets...")
    master = pd.merge(tx_long, pop_long[['fips', 'year', 'population']], on=['fips', 'year'], how='left')
    
    # Select final columns
    final_cols = ['fips', 'RegionName', 'RegionType', 'StateName', 'date', 'zhvi', 'population']
    master = master[final_cols]
    
    # Sort
    master = master.sort_values(['fips', 'date'])
    
    # Save
    output_file = output_dir / 'tx_county_master.csv'
    master.to_csv(output_file, index=False, na_rep='NA')
    print(f"✓ Created {output_file}")
    print(f"  Shape: {master.shape}")
    print(master.head())

if __name__ == "__main__":
    create_tx_county_master()
