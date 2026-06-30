#!/usr/bin/env python3
"""
Investment Scoring Methodology V3 - ZORI Enhanced
Integrates Zillow Observed Rent Index (ZORI) for actual yield calculations.
Weights: 40% Growth, 30% Income (Yield+RentGrowth), 20% Affordability, 10% Demographics
"""

import pandas as pd
import numpy as np
from pathlib import Path

class ZScoreV3Scoring:
    def __init__(self):
        self.data_dir = Path('housing_market_data')
        self.processed_dir = self.data_dir / 'processed'
        self.zillow_dir = self.data_dir / 'zillow'
        self.census_dir = self.data_dir / 'census'
        
    def load_crosswalk(self):
        """Load CBSA to County crosswalk"""
        crosswalk_path = self.census_dir / 'cbsa_to_county.csv'
        if not crosswalk_path.exists():
            print(f"❌ Crosswalk not found at {crosswalk_path}")
            return None
            
        df = pd.read_csv(crosswalk_path)
        # Ensure codes are strings
        df['cbsacode'] = df['cbsacode'].astype(str)
        df['fipscountycode'] = df['fipscountycode'].astype(str).str.zfill(3)
        df['fipsstatecode'] = df['fipsstatecode'].astype(str).str.zfill(2)
        
        # Filter for CA (State Code 06)
        df = df[df['fipsstatecode'] == '06'].copy()
        return df

    def load_zori_data(self):
        """Load Zillow Rental Index (Metro)"""
        zori_path = self.zillow_dir / 'zori_metro.csv'
        if not zori_path.exists():
            print(f"❌ ZORI data not found at {zori_path}")
            return None
            
        print("📊 Loading ZORI Rental Data...")
        df = pd.read_csv(zori_path)
        
        # Melt to long format
        id_vars = ['RegionID', 'SizeRank', 'RegionName', 'RegionType', 'StateName']
        date_cols = [c for c in df.columns if c not in id_vars]
        
        df_long = df.melt(id_vars=id_vars, value_vars=date_cols, var_name='date', value_name='rent_index')
        df_long['date'] = pd.to_datetime(df_long['date'])
        
        # Get latest rent and YoY growth for each metro
        metro_metrics = []
        
        for metro in df_long['RegionName'].unique():
            metro_data = df_long[df_long['RegionName'] == metro].sort_values('date')
            if metro_data.empty:
                continue
                
            latest_rent = metro_data['rent_index'].iloc[-1]
            if pd.isna(latest_rent):
                continue
                
            # Calculate YoY Rent Growth
            year_ago = metro_data[metro_data['date'] <= metro_data['date'].max() - pd.DateOffset(months=12)]
            if not year_ago.empty and not pd.isna(year_ago['rent_index'].iloc[-1]):
                rent_yoy = ((latest_rent - year_ago['rent_index'].iloc[-1]) / year_ago['rent_index'].iloc[-1]) * 100
            else:
                rent_yoy = 0
                
            # Extract CBSA Code from RegionName if possible, or we need a mapping
            # Zillow RegionName is like "San Francisco, CA"
            # We will merge on Name for now as RegionID mapping is complex without a lookup
            
            metro_metrics.append({
                'metro_name': metro,
                'latest_rent': latest_rent,
                'rent_yoy': rent_yoy
            })
            
        return pd.DataFrame(metro_metrics)

    def load_county_data(self):
        """Load existing processed county data"""
        input_file = self.processed_dir / 'ca_county_master.csv'
        df = pd.read_csv(input_file)
        df['date'] = pd.to_datetime(df['date'])
        
        # Get latest stats per county
        county_stats = []
        for county in df['RegionName'].unique():
            c_data = df[df['RegionName'] == county].sort_values('date')
            if len(c_data) < 36: continue
            
            latest = c_data.iloc[-1]
            
            # 3Y CAGR
            three_years_ago = c_data[c_data['date'] <= c_data['date'].max() - pd.DateOffset(years=3)]
            if not three_years_ago.empty:
                start_price = three_years_ago['zhvi'].iloc[0]
                end_price = latest['zhvi']
                cagr = (((end_price / start_price) ** (1/3)) - 1) * 100
            else:
                cagr = 0
                
            # Pop Growth
            pop_growth = 0
            if 'population' in c_data.columns:
                pop_data = c_data.dropna(subset=['population'])
                if len(pop_data) >= 2:
                    pop_growth = ((pop_data['population'].iloc[-1] - pop_data['population'].iloc[0]) / pop_data['population'].iloc[0]) * 100

            county_stats.append({
                'county': county,
                'price': latest['zhvi'],
                'cagr_3y': cagr,
                'yoy_growth': ((latest['zhvi'] - c_data.iloc[-13]['zhvi'])/c_data.iloc[-13]['zhvi'])*100 if len(c_data) > 12 else 0,
                'pop_growth': pop_growth,
                'cbsa_title': latest.get('cbsa_title', '') # Assuming this might exist or we map it
            })
            
        return pd.DataFrame(county_stats)

    def map_rent_to_county(self, county_df, rent_df, crosswalk):
        """Map Metro rents to Counties using CBSA codes"""
        print("\n🔗 Mapping Metro Rents to Counties...")
        
        # Zillow RegionName to CBSA Mapping (from dark_pebble_cleaner.py)
        zillow_mapping = {
            "New York, NY": "35620", "Los Angeles, CA": "31080", "Chicago, IL": "16980", "Dallas, TX": "19100",
            "Houston, TX": "26420", "Washington, DC": "47900", "Philadelphia, PA": "37980", "Miami, FL": "33100",
            "Atlanta, GA": "12060", "Boston, MA": "14460", "Phoenix, AZ": "38060", "San Francisco, CA": "41860",
            "Riverside, CA": "40140", "Detroit, MI": "19820", "Seattle, WA": "42660", "Minneapolis, MN": "33460",
            "San Diego, CA": "41740", "Tampa, FL": "45300", "Denver, CO": "19740", "Baltimore, MD": "12580",
            "St. Louis, MO": "41180", "Charlotte, NC": "16740", "Orlando, FL": "36740", "San Antonio, TX": "41700",
            "Portland, OR": "38900", "Sacramento, CA": "40900", "Pittsburgh, PA": "38300", "Cincinnati, OH": "17140",
            "Austin, TX": "12420", "Las Vegas, NV": "29820", "Kansas City, MO": "28140", "Columbus, OH": "18140",
            "Indianapolis, IN": "26900", "Cleveland, OH": "17460", "San Jose, CA": "41940", "Nashville, TN": "34980",
            "Virginia Beach, VA": "47260", "Providence, RI": "39300", "Jacksonville, FL": "27260", "Milwaukee, WI": "33340",
            "Oklahoma City, OK": "36420", "Raleigh, NC": "39580", "Memphis, TN": "32820", "Richmond, VA": "40060",
            "Louisville, KY": "31140", "New Orleans, LA": "35380", "Salt Lake City, UT": "41620", "Hartford, CT": "25540",
            "Buffalo, NY": "15380", "Birmingham, AL": "13820", "Rochester, NY": "40380", "Grand Rapids, MI": "24340",
            "Tucson, AZ": "46060", "Urban Honolulu, HI": "46520", "Tulsa, OK": "46140", "Fresno, CA": "23420",
            "Worcester, MA": "49340", "Omaha, NE": "36540", "Bridgeport, CT": "14860", "Greenville, SC": "24860",
            "New Haven, CT": "35300", "Bakersfield, CA": "12540", "Knoxville, TN": "28940", "Albany, NY": "10580",
            "Albuquerque, NM": "10740", "McAllen, TX": "32580", "Baton Rouge, LA": "12940", "El Paso, TX": "21340",
            "Allentown, PA": "10900", "Dayton, OH": "19380", "Columbia, SC": "17900", "North Port, FL": "35840",
            "Charleston, SC": "16700", "Greensboro, NC": "24660", "Cape Coral, FL": "15980", "Stockton, CA": "44700",
            "Little Rock, AR": "30780", "Colorado Springs, CO": "17820", "Boise City, ID": "14260", "Lakeland, FL": "29460",
            "Akron, OH": "10420", "Des Moines, IA": "19780", "Springfield, MA": "44140", "Ogden, UT": "36260",
            "Poughkeepsie, NY": "39100", "Winston-Salem, NC": "49180", "Deltona, FL": "19660", "Syracuse, NY": "45060",
            "Provo, UT": "39340", "Toledo, OH": "45780", "Wichita, KS": "48620", "Durham, NC": "20500",
            "Augusta, GA": "12260", "Palm Bay, FL": "37340", "Jackson, MS": "27140", "Madison, WI": "31540",
            "Harrisburg, PA": "25420", "Spokane, WA": "44060", "Chattanooga, TN": "16860", "Scranton, PA": "42540",
            "Modesto, CA": "33700", "Lansing, MI": "29620", "Youngstown, OH": "49660", "Fayetteville, AR": "22220",
            "Fayetteville, NC": "22180", "Lancaster, PA": "29540", "Portland, ME": "38860", "Lexington, KY": "30460",
            "Pensacola, FL": "37860", "Myrtle Beach, SC": "34820", "Port St. Lucie, FL": "38940", "Lafayette, LA": "29180",
            "Springfield, MO": "44180", "Killeen, TX": "28660", "Visalia, CA": "47300", "Asheville, NC": "11700",
            "York, PA": "49620", "Vallejo, CA": "46700", "Santa Maria, CA": "42200", "Salinas, CA": "41500",
            "Huntsville, AL": "26620", "Mobile, AL": "33660", "Reading, PA": "39740", "Corpus Christi, TX": "18580",
            "Brownsville, TX": "15180", "Reno, NV": "39900", "Fort Wayne, IN": "23060", "Gulfport, MS": "25060",
            "Savannah, GA": "42340", "Peoria, IL": "37900", "Canton, OH": "15940", "Beaumont, TX": "13140",
            "Shreveport, LA": "43340", "Salem, OR": "41420", "Davenport, IA": "19340", "Montgomery, AL": "33860",
            "Tallahassee, FL": "45220", "Eugene, OR": "21660", "Ocala, FL": "36100", "Ann Arbor, MI": "11460",
            "Anchorage, AK": "11260", "Wilmington, NC": "48900", "Hickory, NC": "25860", "Fort Collins, CO": "22660",
            "Naples, FL": "34940", "Trenton, NJ": "45940", "Lincoln, NE": "30700", "Rockford, IL": "40420",
            "South Bend, IN": "43780", "Green Bay, WI": "24580", "Lubbock, TX": "31180", "Columbus, GA": "17980",
            "Roanoke, VA": "40220", "Evansville, IN": "21780", "Kingsport, TN": "28700", "Boulder, CO": "14500",
            "Kennewick, WA": "28420", "Santa Rosa, CA": "42220", "Hagerstown, MD": "25180", "Duluth, MN": "20260",
            "Gainesville, FL": "23540", "Fort Smith, AR": "22900", "Crestview, FL": "18880", "Spartanburg, SC": "43900",
            "Olympia, WA": "36500", "Laredo, TX": "29700", "Lynchburg, VA": "31340", "Utica, NY": "46540",
            "Waco, TX": "47380", "Clarksville, TN": "17300", "Bremerton, WA": "14740", "Cedar Rapids, IA": "16300",
            "Slidell, LA": "42980", "Amarillo, TX": "11100", "Erie, PA": "21500", "Norwich, CT": "35980",
            "Kalamazoo, MI": "28020", "College Station, TX": "17780", "Santa Cruz, CA": "42100", "Topeka, KS": "45820",
            "Tuscaloosa, AL": "46220", "Appleton, WI": "11540", "Fargo, ND": "22020", "Sioux Falls, SD": "43620",
            "Thousand Oaks, CA": "37100", "Manchester, NH": "31700", "Charlottesville, VA": "16820",
            "San Luis Obispo, CA": "42020", "Lafayette, IN": "29200", "Champaign, IL": "16580", "Athens, GA": "12020",
            "Macon, GA": "31420", "Binghamton, NY": "13780", "Yakima, WA": "49420", "Lake Havasu City, AZ": "29420",
            "Tyler, TX": "46340", "Bellingham, WA": "13380", "Rochester, MN": "40340", "Hilton Head Island, SC": "25940",
            "Yuma, AZ": "49740", "Chico, CA": "17020", "Elkhart, IN": "21140", "Las Cruces, NM": "29740",
            "Greeley, CO": "24540", "Barnstable Town, MA": "12700", "Burlington, VT": "15540", "Daphne, AL": "19300",
            "Houma, LA": "26380", "Florence, SC": "22500", "Medford, OR": "32780", "St. Cloud, MN": "41060",
            "Sarasota, FL": "42260", "Punta Gorda, FL": "39460", "Sebastian, FL": "42680", "The Villages, FL": "45540",
            "Homosassa Springs, FL": "26140", "Merced, CA": "32900", "Yuba City, CA": "49700", "El Centro, CA": "20940",
            "Hanford, CA": "25260", "Madera, CA": "31460", "Napa, CA": "34900", "Redding, CA": "39820"
        }
        
        # Add CBSA Code to Rent Data
        rent_df['cbsa_code'] = rent_df['metro_name'].map(zillow_mapping)
        
        # Prepare Crosswalk
        # Use 'countycountyequivalent' instead of 'countyname'
        crosswalk['county_full'] = crosswalk['countycountyequivalent']
        crosswalk['cbsa_code'] = crosswalk['cbsacode'].astype(str)
        
        # Merge County DF with Crosswalk to get CBSA Code
        # Crosswalk might have duplicates if a county is in multiple CBSAs (rare but possible) or file has duplicates
        crosswalk_unique = crosswalk[['county_full', 'cbsa_code', 'cbsatitle']].drop_duplicates(subset=['county_full'])
        
        merged = county_df.merge(crosswalk_unique, 
                               left_on='county', 
                               right_on='county_full', 
                               how='left')
    
        rent_unique = rent_df[['cbsa_code', 'latest_rent', 'rent_yoy']].drop_duplicates(subset=['cbsa_code'])

        # Merge with Rent Data using CBSA Code
        merged = merged.merge(rent_unique, 
                            on='cbsa_code', 
                            how='left')
        
        # Rename columns
        merged['mapped_rent'] = merged['latest_rent']
        merged['mapped_rent_yoy'] = merged['rent_yoy']
        
        matches = merged['mapped_rent'].notna().sum()
        print(f"✅ Found rental data for {matches} out of {len(county_df)} counties")
        
        return merged

    def zscore(self, series):
        """Calculate z-score"""
        if series.std() == 0: return series * 0
        return (series - series.mean()) / series.std()

    def run(self):
        print("="*100)
        print("🚀 STARTING Z-SCORE V3 ANALYSIS (WITH ZORI RENT DATA)")
        print("="*100)
        
        # 1. Load Data
        county_df = self.load_county_data()
        rent_df = self.load_zori_data()
        crosswalk = self.load_crosswalk()
        
        if rent_df is None or county_df is None:
            print("❌ Failed to load data")
            return
            
        # 2. Map Rents
        df = self.map_rent_to_county(county_df, rent_df, crosswalk)
        
        # 3. Calculate Real Yield
        # If rent is missing, we use the old estimation method as fallback, but penalize it slightly?
        # Or just fill with median? Let's fill with median of found rents to be neutral.
        
        avg_rent = df['mapped_rent'].median()
        avg_rent_yoy = df['mapped_rent_yoy'].median()
        
        df['is_estimated_rent'] = df['mapped_rent'].isna()
        df['rent_final'] = df['mapped_rent'].fillna(avg_rent)
        df['rent_yoy_final'] = df['mapped_rent_yoy'].fillna(avg_rent_yoy)
        
        # Yield Formula: (Monthly Rent * 12) / Price * 100
        df['actual_yield'] = (df['rent_final'] * 12 / df['price']) * 100
        
        print(f"\n📊 Yield Stats:")
        print(f"  Mean Yield: {df['actual_yield'].mean():.2f}%")
        print(f"  Max Yield:  {df['actual_yield'].max():.2f}%")
        print(f"  Min Yield:  {df['actual_yield'].min():.2f}%")
        
        # 4. Calculate Z-Scores
        
        # Growth (40%)
        # Fix: Fill missing 3Y CAGR with YoY Growth (e.g. for Imperial County)
        df['cagr_3y'] = df['cagr_3y'].fillna(df['yoy_growth'])
        
        df['growth_combined'] = (df['cagr_3y'] * 0.7) + (df['yoy_growth'] * 0.3)
        df['z_growth'] = self.zscore(df['growth_combined'])
        
        # Income (30%) - Yield (20%) + Rent Growth (10%)
        df['z_yield'] = self.zscore(df['actual_yield'])
        df['z_rent_growth'] = self.zscore(df['rent_yoy_final'])
        df['z_income'] = (df['z_yield'] * 0.67) + (df['z_rent_growth'] * 0.33)
        
        # Affordability (20%)
        df['z_price'] = self.zscore(df['price'])
        df['z_affordability'] = -df['z_price'] # Inverted
        
        # Demographics (10%)
        df['z_demographics'] = self.zscore(df['pop_growth'])
        
        # 5. Final Score Calculation
        # Weights: Growth 50%, Affordability 25%, Demographics 15%, Income 10%
        df['z_score_v3'] = (
            df['z_growth'] * 0.50 +
            df['z_income'] * 0.10 +
            df['z_affordability'] * 0.25 +
            df['z_demographics'] * 0.15
        )
        
        # Normalize to 0-100
        df['score_v3_norm'] = ((df['z_score_v3'] + 3) / 6) * 100
        df['score_v3_norm'] = df['score_v3_norm'].clip(0, 100)
        
        # Sort
        df = df.sort_values('z_score_v3', ascending=False).reset_index(drop=True)
        
        # 6. Display Results
        print("\n" + "="*120)
        print("🏆 TOP 20 COUNTIES - V3 MODEL (Growth + Real Income)")
        print("="*120)
        print(f"{'Rank':<5} {'County':<25} {'V3 Score':<10} {'Yield':<8} {'Rent':<10} {'Price':<12} {'Growth':<8}")
        print("-" * 120)
        
        for idx, row in df.head(20).iterrows():
            est_flag = "*" if row['is_estimated_rent'] else " "
            print(f"{idx+1:<5} {row['county']:<25} {row['score_v3_norm']:>6.1f}     {row['actual_yield']:>5.2f}%{est_flag}  "
                  f"${row['rent_final']:<9,.0f} ${row['price']:<11,.0f} {row['growth_combined']:>6.2f}%")
            
        print("-" * 120)
        print("* = Estimated Rent (Metro data not found, used median)")
        
        # Save
        output_file = self.processed_dir / 'all_counties_ranking_v3.csv'
        df.to_csv(output_file, index=False)
        print(f"\n✅ Saved V3 rankings to: {output_file}")
        
        return df

if __name__ == "__main__":
    scorer = ZScoreV3Scoring()
    scorer.run()
