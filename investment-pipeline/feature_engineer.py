#!/usr/bin/env python3
"""
Feature Engineering Script
Calculates investment metrics from the master dataset.
"""

import pandas as pd
import numpy as np
from pathlib import Path

class FeatureEngineer:
    def __init__(self, data_dir='housing_market_data'):
        self.data_dir = Path(data_dir)
        self.processed_dir = self.data_dir / 'processed'
        self.input_file = self.processed_dir / 'master_housing_data.csv'
        self.output_file = self.processed_dir / 'features_master.csv'
        
    def load_data(self):
        """Load the master dataset"""
        if not self.input_file.exists():
            raise FileNotFoundError(f"Master dataset not found at {self.input_file}. Run data_cleaner.py first.")
        
        df = pd.read_csv(self.input_file)
        df['date'] = pd.to_datetime(df['date'])
        print(f"✓ Loaded master dataset: {df.shape}")
        return df
        
    def calculate_metrics(self, df):
        """Calculate investment metrics"""
        print("\nCalculating Metrics...")
        
        # 1. Price-to-Income Ratio
        # Need annual wage. If monthly employment data has wages, use that.
        # Our BLS data currently only has 'employment'.
        # We need to check if we have wage data.
        # If not, we might need to skip or use a placeholder if we can't calculate it.
        # Let's check columns.
        
        # 2. Rental Yield (Gross)
        # (Monthly Rent * 12) / Home Value
        if 'rent_index' in df.columns and 'zhvi' in df.columns:
            df['rental_yield'] = (df['rent_index'] * 12) / df['zhvi']
            print("  ✓ Calculated Rental Yield")
        else:
            print("  ⚠ Skipping Rental Yield (missing rent_index or zhvi)")
            
        # 3. Momentum (Price Growth)
        # Calculate YoY and MoM changes for ZHVI
        if 'zhvi' in df.columns:
            # Sort by cbsa and date
            df = df.sort_values(['cbsa_code', 'date'])
            
            # Group by CBSA
            df['price_mom'] = df.groupby('cbsa_code')['zhvi'].pct_change(periods=1)
            df['price_yoy'] = df.groupby('cbsa_code')['zhvi'].pct_change(periods=12)
            df['price_3y_cagr'] = (df.groupby('cbsa_code')['zhvi'].pct_change(periods=36) + 1)**(1/3) - 1
            print("  ✓ Calculated Price Momentum")
            
        # 4. Rent Growth
        if 'rent_index' in df.columns:
            df = df.sort_values(['cbsa_code', 'date'])
            df['rent_mom'] = df.groupby('cbsa_code')['rent_index'].pct_change(periods=1)
            df['rent_yoy'] = df.groupby('cbsa_code')['rent_index'].pct_change(periods=12)
            print("  ✓ Calculated Rent Growth")
            
        # 5. Inventory Dynamics
        if 'inventory' in df.columns:
            df['inventory_yoy'] = df.groupby('cbsa_code')['inventory'].pct_change(periods=12)
            print("  ✓ Calculated Inventory Dynamics")
            
        return df
        
    def run(self):
        try:
            df = self.load_data()
            df_features = self.calculate_metrics(df)
            
            # Save
            df_features.to_csv(self.output_file, index=False)
            print(f"\n✓ Saved features to {self.output_file}")
            print(f"  Shape: {df_features.shape}")
            print(f"  Columns: {list(df_features.columns)}")
            
        except Exception as e:
            print(f"\n✗ Error: {e}")

if __name__ == "__main__":
    engineer = FeatureEngineer()
    engineer.run()
