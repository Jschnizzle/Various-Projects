#!/usr/bin/env python3
"""
Data Cleaning and Merging Script
Standardizes and merges data from Zillow, Census, BLS, and FHFA into a master dataset.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
import requests
import io

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

class DataCleaner:
    def __init__(self, data_dir='housing_market_data'):
        self.data_dir = Path(data_dir)
        self.output_dir = self.data_dir / 'processed'
        self.output_dir.mkdir(exist_ok=True)
        
        # Load metro reference
        self.metro_ref = pd.read_csv(self.data_dir / 'metro_reference.csv')
        self.metro_ref['cbsa_code'] = self.metro_ref['cbsa_code'].astype(str)
        self.target_metros = self.metro_ref['cbsa_code'].tolist()
        
        print(f"✓ Initialized DataCleaner")
        print(f"  Target Metros: {len(self.target_metros)}")

    def download_crosswalk(self):
        """
        Downloads the HUD USPS ZIP-Crosswalk or Census Bureau County-CBSA crosswalk.
        We will use a NBER provided Census Core Based Statistical Area (CBSA) to County Crosswalk.
        URL: https://data.nber.org/cbsa-csa-fips-county-crosswalk/cbsa2fipsxw.csv
        """
        crosswalk_path = self.data_dir / 'census' / 'cbsa_to_county.csv'
        if crosswalk_path.exists():
            print("  ✓ Crosswalk file already exists")
            return pd.read_csv(crosswalk_path)

        print("  ⬇ Downloading County-to-CBSA crosswalk...")
        url = "https://data.nber.org/cbsa-csa-fips-county-crosswalk/cbsa2fipsxw.csv"
        try:
            response = requests.get(url)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
            
            # Save for future use
            df.to_csv(crosswalk_path, index=False)
            print("  ✓ Downloaded and saved crosswalk")
            return df
        except Exception as e:
            print(f"  ✗ Error downloading crosswalk: {e}")
            return pd.DataFrame()

    def load_and_standardize_zillow(self):
        """
        Standardize Zillow data:
        - Convert from wide (dates as columns) to long format
        - Filter for target metros using robust name matching
        """
        print("\nProcessing Zillow Data...")
        zillow_dir = self.data_dir / 'zillow'
        
        files = {
            'zhvi_metro.csv': 'zhvi',
            'zori_metro.csv': 'rent_index',
            'inventory_metro.csv': 'inventory',
            'median_list_price_metro.csv': 'median_list_price',
            'sales_count_metro.csv': 'sales_count',
            'days_on_market_metro.csv': 'days_on_market',
            'price_cuts_metro.csv': 'price_cuts'
        }
        
        merged_zillow = None
        
        for filename, metric in files.items():
            filepath = zillow_dir / filename
            if not filepath.exists():
                print(f"  ⚠ Skipping {filename} (not found)")
                continue
                
            print(f"  Processing {filename}...")
            df = pd.read_csv(filepath)
            
            # Identify date columns
            date_cols = [c for c in df.columns if c[0].isdigit() and '-' in c]
            id_vars = [c for c in df.columns if c not in date_cols]
            
            # Melt to long format
            df_long = df.melt(id_vars=id_vars, value_vars=date_cols, var_name='date', value_name=metric)
            df_long['date'] = pd.to_datetime(df_long['date'])
            
            # Standardize RegionName to match our reference
            # Zillow format: "City, ST"
            # We will merge with our metro_reference on 'name' or fuzzy match if needed
            # For now, let's try to map RegionName to cbsa_code using our reference file
            
            # Create a mapping dictionary from our reference file
            # We assume Zillow RegionName matches our reference 'name' column roughly
            # Actually, let's clean Zillow names: "New York, NY" -> "New York, NY"
            # Our reference has "New York-Newark-Jersey City, NY-NJ-PA" which is different.
            # We need a robust way. 
            # Strategy: Use the 'RegionID' if we had a map, but we don't.
            # Strategy: String matching.
            
            # Let's try to join on StateName and City Name parts? Too complex.
            # Simplest: Add a 'zillow_name' column to metro_reference.csv manually or programmatically.
            # Or, since we only have 17 metros, we can hardcode the mapping in a dictionary here.
            
            zillow_mapping = {
                "New York, NY": "35620",
                "Los Angeles, CA": "31080",
                "Chicago, IL": "16980",
                "Dallas, TX": "19100",
                "Houston, TX": "26420",
                "Washington, DC": "47900",
                "Philadelphia, PA": "37980",
                "Miami, FL": "33100",
                "Atlanta, GA": "12060",
                "Boston, MA": "14460",
                "Phoenix, AZ": "38060",
                "San Francisco, CA": "41860",
                "Riverside, CA": "40140",
                "Detroit, MI": "19820",
                "Seattle, WA": "42660",
                "Minneapolis, MN": "33460",
                "San Diego, CA": "41740",
                "Tampa, FL": "45300",
                "Denver, CO": "19740",
                "Baltimore, MD": "12580",
                "St. Louis, MO": "41180",
                "Charlotte, NC": "16740",
                "Orlando, FL": "36740",
                "San Antonio, TX": "41700",
                "Portland, OR": "38900",
                "Sacramento, CA": "40900",
                "Pittsburgh, PA": "38300",
                "Cincinnati, OH": "17140",
                "Austin, TX": "12420",
                "Las Vegas, NV": "29820",
                "Kansas City, MO": "28140",
                "Columbus, OH": "18140",
                "Indianapolis, IN": "26900",
                "Cleveland, OH": "17460",
                "San Jose, CA": "41940",
                "Nashville, TN": "34980",
                "Virginia Beach, VA": "47260",
                "Providence, RI": "39300",
                "Jacksonville, FL": "27260",
                "Milwaukee, WI": "33340",
                "Oklahoma City, OK": "36420",
                "Raleigh, NC": "39580",
                "Memphis, TN": "32820",
                "Richmond, VA": "40060",
                "Louisville, KY": "31140",
                "New Orleans, LA": "35380",
                "Salt Lake City, UT": "41620",
                "Hartford, CT": "25540",
                "Buffalo, NY": "15380",
                "Birmingham, AL": "13820",
                "Rochester, NY": "40380",
                "Grand Rapids, MI": "24340",
                "Tucson, AZ": "46060",
                "Urban Honolulu, HI": "46520",
                "Tulsa, OK": "46140",
                "Fresno, CA": "23420",
                "Worcester, MA": "49340",
                "Omaha, NE": "36540",
                "Bridgeport, CT": "14860",
                "Greenville, SC": "24860",
                "New Haven, CT": "35300",
                "Bakersfield, CA": "12540",
                "Knoxville, TN": "28940",
                "Albany, NY": "10580",
                "Albuquerque, NM": "10740",
                "McAllen, TX": "32580",
                "Baton Rouge, LA": "12940",
                "El Paso, TX": "21340",
                "Allentown, PA": "10900",
                "Dayton, OH": "19380",
                "Columbia, SC": "17900",
                "North Port, FL": "35840",
                "Charleston, SC": "16700",
                "Greensboro, NC": "24660",
                "Cape Coral, FL": "15980",
                "Stockton, CA": "44700",
                "Little Rock, AR": "30780",
                "Colorado Springs, CO": "17820",
                "Boise City, ID": "14260",
                "Lakeland, FL": "29460",
                "Akron, OH": "10420",
                "Des Moines, IA": "19780",
                "Springfield, MA": "44140",
                "Ogden, UT": "36260",
                "Poughkeepsie, NY": "39100",
                "Winston-Salem, NC": "49180",
                "Deltona, FL": "19660",
                "Syracuse, NY": "45060",
                "Provo, UT": "39340",
                "Toledo, OH": "45780",
                "Wichita, KS": "48620",
                "Durham, NC": "20500",
                "Augusta, GA": "12260",
                "Palm Bay, FL": "37340",
                "Jackson, MS": "27140",
                "Madison, WI": "31540",
                "Harrisburg, PA": "25420",
                "Spokane, WA": "44060",
                "Chattanooga, TN": "16860",
                "Scranton, PA": "42540",
                "Modesto, CA": "33700",
                "Lansing, MI": "29620",
                "Youngstown, OH": "49660",
                "Fayetteville, AR": "22220",
                "Fayetteville, NC": "22180",
                "Lancaster, PA": "29540",
                "Portland, ME": "38860",
                "Lexington, KY": "30460",
                "Pensacola, FL": "37860",
                "Myrtle Beach, SC": "34820",
                "Port St. Lucie, FL": "38940",
                "Lafayette, LA": "29180",
                "Springfield, MO": "44180",
                "Killeen, TX": "28660",
                "Visalia, CA": "47300",
                "Asheville, NC": "11700",
                "York, PA": "49620",
                "Vallejo, CA": "46700",
                "Santa Maria, CA": "42200",
                "Salinas, CA": "41500",
                "Huntsville, AL": "26620",
                "Mobile, AL": "33660",
                "Reading, PA": "39740",
                "Corpus Christi, TX": "18580",
                "Brownsville, TX": "15180",
                "Reno, NV": "39900",
                "Fort Wayne, IN": "23060",
                "Gulfport, MS": "25060",
                "Savannah, GA": "42340",
                "Peoria, IL": "37900",
                "Canton, OH": "15940",
                "Beaumont, TX": "13140",
                "Shreveport, LA": "43340",
                "Salem, OR": "41420",
                "Davenport, IA": "19340",
                "Montgomery, AL": "33860",
                "Tallahassee, FL": "45220",
                "Eugene, OR": "21660",
                "Ocala, FL": "36100",
                "Ann Arbor, MI": "11460",
                "Anchorage, AK": "11260",
                "Wilmington, NC": "48900",
                "Hickory, NC": "25860",
                "Fort Collins, CO": "22660",
                "Naples, FL": "34940",
                "Trenton, NJ": "45940",
                "Lincoln, NE": "30700",
                "Rockford, IL": "40420",
                "South Bend, IN": "43780",
                "Green Bay, WI": "24580",
                "Lubbock, TX": "31180",
                "Columbus, GA": "17980",
                "Roanoke, VA": "40220",
                "Evansville, IN": "21780",
                "Kingsport, TN": "28700",
                "Boulder, CO": "14500",
                "Kennewick, WA": "28420",
                "Santa Rosa, CA": "42220",
                "Hagerstown, MD": "25180",
                "Duluth, MN": "20260",
                "Gainesville, FL": "23540",
                "Fort Smith, AR": "22900",
                "Crestview, FL": "18880",
                "Spartanburg, SC": "43900",
                "Olympia, WA": "36500",
                "Laredo, TX": "29700",
                "Lynchburg, VA": "31340",
                "Utica, NY": "46540",
                "Waco, TX": "47380",
                "Clarksville, TN": "17300",
                "Bremerton, WA": "14740",
                "Cedar Rapids, IA": "16300",
                "Slidell, LA": "42980",
                "Amarillo, TX": "11100",
                "Erie, PA": "21500",
                "Norwich, CT": "35980",
                "Kalamazoo, MI": "28020",
                "College Station, TX": "17780",
                "Santa Cruz, CA": "42100",
                "Topeka, KS": "45820",
                "Tuscaloosa, AL": "46220",
                "Appleton, WI": "11540",
                "Fargo, ND": "22020",
                "Sioux Falls, SD": "43620",
                "Thousand Oaks, CA": "37100",
                "Manchester, NH": "31700",
                "Charlottesville, VA": "16820",
                "San Luis Obispo, CA": "42020",
                "Lafayette, IN": "29200",
                "Champaign, IL": "16580",
                "Athens, GA": "12020",
                "Macon, GA": "31420",
                "Binghamton, NY": "13780",
                "Yakima, WA": "49420",
                "Lake Havasu City, AZ": "29420",
                "Tyler, TX": "46340",
                "Bellingham, WA": "13380",
                "Rochester, MN": "40340",
                "Hilton Head Island, SC": "25940",
                "Yuma, AZ": "49740",
                "Chico, CA": "17020",
                "Elkhart, IN": "21140",
                "Las Cruces, NM": "29740",
                "Greeley, CO": "24540",
                "Barnstable Town, MA": "12700",
                "Burlington, VT": "15540",
                "Daphne, AL": "19300",
                "Houma, LA": "26380",
                "Florence, SC": "22500",
                "Medford, OR": "32780",
                "St. Cloud, MN": "41060",
                "Sarasota, FL": "42260",
                "Punta Gorda, FL": "39460",
                "Sebastian, FL": "42680",
                "The Villages, FL": "45540",
                "Homosassa Springs, FL": "26140"
            }
            
            # Map RegionName to CBSA
            df_long['cbsa_code'] = df_long['RegionName'].map(zillow_mapping)
            
            # Filter for our target metros
            df_filtered = df_long[df_long['cbsa_code'].isin(self.target_metros)].copy()
            
            if df_filtered.empty:
                print(f"    ⚠ No matching metros found in {filename} after filtering")
                continue
                
            # Select columns
            df_filtered = df_filtered[['cbsa_code', 'date', metric]]
            
            if merged_zillow is None:
                merged_zillow = df_filtered
            else:
                merged_zillow = pd.merge(merged_zillow, df_filtered, on=['cbsa_code', 'date'], how='outer')
                
        if merged_zillow is not None:
            print(f"  ✓ Zillow data processed: {merged_zillow.shape}")
            return merged_zillow
        else:
            return pd.DataFrame()

    def load_and_standardize_census(self):
        """
        Standardize Census data:
        - Load County Population Estimates
        - Use Crosswalk to aggregate to CBSA level
        - Forward fill annual data to monthly
        """
        print("\nProcessing Census Data...")
        
        # 1. Load Crosswalk
        crosswalk = self.download_crosswalk()
        if crosswalk.empty:
            print("  ⚠ Cannot process Census data without crosswalk")
            return pd.DataFrame()
            
        # Ensure string types for merging
        # Crosswalk columns: 'cbsa', 'fipsstatecode', 'fipscountycode'
        # We need to construct a 5-digit county FIPS from state and county codes
        # Note: NBER crosswalk column names might vary. Let's inspect if needed.
        # Based on typical NBER file: 'cbsa', 'fipsstatecode', 'fipscountycode'
        
        # Check columns
        if 'cbsacode' not in crosswalk.columns:
            # Fallback or error
            print(f"  ⚠ Unexpected crosswalk columns: {crosswalk.columns}")
            return pd.DataFrame()
            
        crosswalk['cbsa_code'] = crosswalk['cbsacode'].astype(str)
        # Create 5-digit FIPS: State (2) + County (3)
        crosswalk['fips_state'] = crosswalk['fipsstatecode'].astype(str).str.zfill(2)
        crosswalk['fips_county'] = crosswalk['fipscountycode'].astype(str).str.zfill(3)
        crosswalk['county_fips'] = crosswalk['fips_state'] + crosswalk['fips_county']
        
        # Filter crosswalk for our target metros
        target_crosswalk = crosswalk[crosswalk['cbsa_code'].isin(self.target_metros)]
        valid_county_fips = target_crosswalk['county_fips'].tolist()
        
        # 2. Load Population Data
        pop_file = self.data_dir / 'census' / 'population_estimates.csv'
        if not pop_file.exists():
            print("  ⚠ Population file not found")
            return pd.DataFrame()
            
        try:
            # Census file has STATE (2 digits) and COUNTY (3 digits)
            try:
                raw_pop = pd.read_csv(pop_file)
            except UnicodeDecodeError:
                raw_pop = pd.read_csv(pop_file, encoding='latin-1')
                
            # Create county_fips in population data
            raw_pop['state_fips'] = raw_pop['STATE'].astype(str).str.zfill(2)
            raw_pop['county_fips_suffix'] = raw_pop['COUNTY'].astype(str).str.zfill(3)
            raw_pop['county_fips'] = raw_pop['state_fips'] + raw_pop['county_fips_suffix']
            
            # Filter for relevant counties
            pop_filtered = raw_pop[raw_pop['county_fips'].isin(valid_county_fips)].copy()
            
            # Merge with crosswalk to get CBSA
            pop_merged = pd.merge(pop_filtered, target_crosswalk[['county_fips', 'cbsa_code']], on='county_fips', how='left')
            
            # Extract population columns (POPESTIMATE2020, etc.)
            pop_cols = [c for c in pop_merged.columns if 'POPESTIMATE' in c]
            
            # Group by CBSA and sum
            cbsa_pop = pop_merged.groupby('cbsa_code')[pop_cols].sum().reset_index()
            
            # Melt to long format
            cbsa_pop_long = cbsa_pop.melt(id_vars=['cbsa_code'], var_name='year_col', value_name='population')
            cbsa_pop_long['year'] = cbsa_pop_long['year_col'].str.extract(r'(\d{4})').astype(int)
            cbsa_pop_long['date'] = pd.to_datetime(cbsa_pop_long['year'].astype(str) + '-01-01')
            
            # We have annual data (Jan 1st). We need monthly.
            # We will reindex to monthly and interpolate/ffill
            
            # Get min and max dates
            min_date = cbsa_pop_long['date'].min()
            max_date = datetime.now() # Up to current
            
            # Create full monthly range
            dates = pd.date_range(start=min_date, end=max_date, freq='MS')
            
            final_pop = pd.DataFrame()
            
            for cbsa in cbsa_pop_long['cbsa_code'].unique():
                subset = cbsa_pop_long[cbsa_pop_long['cbsa_code'] == cbsa].set_index('date')
                subset = subset.reindex(dates)
                subset['cbsa_code'] = cbsa
                # Interpolate population
                subset['population'] = subset['population'].interpolate(method='linear')
                # Forward fill remaining (for current year if missing)
                subset['population'] = subset['population'].ffill()
                
                final_pop = pd.concat([final_pop, subset.reset_index().rename(columns={'index': 'date'})])
            
            final_pop = final_pop[['cbsa_code', 'date', 'population']]
            print(f"  ✓ Processed Census Population: {final_pop.shape}")
            return final_pop
            
        except Exception as e:
            print(f"  ✗ Error processing Census data: {e}")
            return pd.DataFrame()

    def load_and_standardize_bls(self):
        """
        Standardize BLS data:
        - Employment
        """
        print("\nProcessing BLS Data...")
        bls_dir = self.data_dir / 'bls'
        emp_file = bls_dir / 'metro_employment.csv'
        
        if not emp_file.exists():
            print("  ⚠ BLS employment file not found")
            return pd.DataFrame()
            
        try:
            raw_emp = pd.read_csv(emp_file)
            series_col = 'seriesID' if 'seriesID' in raw_emp.columns else 'series_id'
            
            # Filter for SMS (State Metro Area Employment)
            raw_emp = raw_emp[raw_emp[series_col].str.startswith('SMS', na=False)]
            
            # Extract Metro Code (digits 5-9)
            # SMS 06 31080 00000000 01
            raw_emp['cbsa_code'] = raw_emp[series_col].str[5:10]
            
            # Filter for target metros
            raw_emp = raw_emp[raw_emp['cbsa_code'].isin(self.target_metros)]
            
            # Create Date
            raw_emp['month'] = raw_emp['period'].str.replace('M', '').astype(int)
            raw_emp['date'] = pd.to_datetime(raw_emp['year'].astype(str) + '-' + raw_emp['month'].astype(str) + '-01')
            
            emp_df = raw_emp[['cbsa_code', 'date', 'value']].rename(columns={'value': 'employment'})
            
            # Handle duplicates if any (shouldn't be for same series, but maybe multiple series per metro?)
            # Usually we want Total Nonfarm (00000000). Check if we have multiple datatypes.
            # The downloader might have fetched specific series. Assuming Total Nonfarm for now.
            
            print(f"  ✓ Processed BLS Employment: {emp_df.shape}")
            return emp_df
            
        except Exception as e:
            print(f"  ✗ Error processing BLS data: {e}")
            return pd.DataFrame()

    def load_and_standardize_fhfa(self):
        """
        Standardize FHFA HPI data:
        - Quarterly to Monthly (Upsample)
        """
        print("\nProcessing FHFA Data...")
        fhfa_file = self.data_dir / 'other' / 'fhfa_hpi_metro.csv'
        
        if not fhfa_file.exists():
            print("  ⚠ FHFA file not found")
            return pd.DataFrame()
            
        try:
            # Load data
            # Expected cols: hpi_type, hpi_flavor, frequency, level, place_name, place_id, yr, period, index_nsa, index_sa
            # place_id for metros is usually the CBSA code? Or a custom ID?
            # Let's check the file content we saw earlier: "DV_ENC" for division. 
            # We need to filter for 'Metro' level.
            
            df = pd.read_csv(fhfa_file)
            
            # Filter for Metros
            # Ensure place_id is string
            df['place_id'] = df['place_id'].astype(str)
            
            # Filter for specific HPI types to avoid duplicates
            if 'hpi_type' in df.columns:
                df = df[df['hpi_type'] == 'traditional']
            if 'hpi_flavor' in df.columns:
                df = df[df['hpi_flavor'] == 'purchase-only']
            if 'frequency' in df.columns:
                df = df[df['frequency'].isin(['monthly', 'quarterly'])]
                
            # Map CBSA codes to FHFA IDs (MSADs for large metros)
            fhfa_map = {
                '31080': '31084', # Los Angeles
                '41860': '41884', # San Francisco
                '19100': '19124'  # Dallas
            }
            
            # Create reverse map for restoring CBSA codes
            reverse_map = {v: k for k, v in fhfa_map.items()}
            
            # Prepare target IDs
            target_ids = []
            for cbsa in self.target_metros:
                target_ids.append(fhfa_map.get(cbsa, cbsa))
                
            df_metro = df[df['place_id'].isin(target_ids)].copy()
            
            if df_metro.empty:
                print("  ⚠ No matching metros found in FHFA file (check place_id format)")
                return pd.DataFrame()
            
            # Map back to standard CBSA codes
            df_metro['cbsa_code'] = df_metro['place_id'].map(lambda x: reverse_map.get(x, x))
                
            # Create Date
            # Handle quarterly vs monthly
            if 'frequency' in df_metro.columns:
                # If quarterly, convert to month (1->1, 2->4, 3->7, 4->10)
                mask_q = df_metro['frequency'] == 'quarterly'
                df_metro.loc[mask_q, 'period'] = (df_metro.loc[mask_q, 'period'] * 3) - 2
            
            df_metro['date'] = pd.to_datetime(df_metro['yr'].astype(str) + '-' + df_metro['period'].astype(str) + '-01')
            
            # Select relevant columns
            # We prefer 'index_sa' (Seasonally Adjusted) if available, else 'index_nsa'
            metric = 'index_sa' if 'index_sa' in df_metro.columns else 'index_nsa'
            
            df_clean = df_metro[['place_id', 'date', metric]].rename(columns={'place_id': 'cbsa_code', metric: 'hpi'})
            
            # Handle potential duplicates
            df_clean = df_clean.drop_duplicates(subset=['cbsa_code', 'date'])
            
            # Upsample to Monthly (if needed, though we filtered for monthly)
            # But just in case we have gaps or it was actually quarterly
            final_hpi = pd.DataFrame()
            
            for cbsa in df_clean['cbsa_code'].unique():
                subset = df_clean[df_clean['cbsa_code'] == cbsa].set_index('date').sort_index()
                # Resample to MS (Month Start) and interpolate to fill gaps
                subset_monthly = subset.resample('MS').interpolate(method='linear')
                subset_monthly['cbsa_code'] = cbsa
                
                final_hpi = pd.concat([final_hpi, subset_monthly.reset_index()])
                
            print(f"  ✓ Processed FHFA HPI: {final_hpi.shape}")
            return final_hpi
            
        except Exception as e:
            print(f"  ✗ Error processing FHFA data: {e}")
            return pd.DataFrame()

    def load_and_standardize_freddie_mac(self):
        """
        Standardize Freddie Mac Mortgage Rates:
        - Weekly to Monthly (Average)
        """
        print("\nProcessing Freddie Mac Data...")
        freddie_file = self.data_dir / 'other' / 'freddie_mac_rates.csv'
        
        if not freddie_file.exists():
            print("  ⚠ Freddie Mac file not found")
            return pd.DataFrame()
            
        try:
            df = pd.read_csv(freddie_file)
            
            # Expected cols: date, pmms30, etc.
            # Check column names. Usually 'date' or 'Week'
            date_col = next((c for c in df.columns if 'date' in c.lower() or 'week' in c.lower()), None)
            rate_col = next((c for c in df.columns if '30' in c and 'us' in c.lower() or 'pmms30' in c.lower()), None)
            
            if not date_col or not rate_col:
                print(f"  ⚠ Could not identify date/rate columns in {df.columns}")
                return pd.DataFrame()
                
            df['date'] = pd.to_datetime(df[date_col])
            df['mortgage_rate'] = pd.to_numeric(df[rate_col], errors='coerce')
            
            # Resample to Monthly Average
            df_monthly = df.set_index('date').resample('MS')['mortgage_rate'].mean().reset_index()
            
            # This is national data, so we need to broadcast it to all metros
            # We'll return it as is, and merge_data will handle the broadcast
            print(f"  ✓ Processed Freddie Mac Rates: {df_monthly.shape}")
            return df_monthly
            
        except Exception as e:
            print(f"  ✗ Error processing Freddie Mac data: {e}")
            return pd.DataFrame()

    def merge_data(self, zillow, census, bls, fhfa, freddie):
        """
        Merge all datasets on cbsa_code and date
        """
        print("\nMerging Master Dataset...")
        
        if zillow.empty:
            print("  ⚠ Zillow data is empty, cannot create master dataset")
            return pd.DataFrame()
            
        # Start with Zillow as base (monthly)
        master = zillow.copy()
        
        # Merge Census
        if not census.empty:
            master = pd.merge(master, census, on=['cbsa_code', 'date'], how='left')
            
        # Merge BLS
        if not bls.empty:
            master = pd.merge(master, bls, on=['cbsa_code', 'date'], how='left')
            
        # Merge FHFA
        if not fhfa.empty:
            master = pd.merge(master, fhfa, on=['cbsa_code', 'date'], how='left')
            
        # Merge Freddie Mac (National Level - Broadcast)
        if not freddie.empty:
            master = pd.merge(master, freddie, on='date', how='left')
            
        # Add Metro Name from reference
        master = pd.merge(master, self.metro_ref[['cbsa_code', 'name', 'category']], on='cbsa_code', how='left')
        
        # Sort
        master = master.sort_values(['cbsa_code', 'date'])
        
        print(f"  ✓ Master Dataset Created: {master.shape}")
        return master

    def clean_data(self, df):
        """
        Final cleaning:
        - Handle missing values (interpolation/ffill)
        - Drop rows with critical missing data
        """
        print("\nCleaning Master Dataset...")
        if df.empty:
            return df
            
        # Sort for interpolation
        df = df.sort_values(['cbsa_code', 'date'])
        
        # Interpolate missing values within each metro
        # For numeric columns only
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        # Group by metro and apply interpolation
        # We use a lambda to avoid issues if a group is all NaN
        df[numeric_cols] = df.groupby('cbsa_code')[numeric_cols].transform(
            lambda x: x.interpolate(method='linear').ffill().bfill()
        )
        
        # Drop rows where date is future (if any)
        current_date = datetime.now()
        df = df[df['date'] <= current_date]
        
        print(f"  ✓ Data cleaned (interpolated and filled)")
        return df

    def save_data(self, df):
        if df.empty:
            print("  ⚠ No data to save")
            return
            
        output_path = self.output_dir / 'master_housing_data.csv'
        df.to_csv(output_path, index=False)
        print(f"\n✓ Saved Master Dataset to: {output_path}")
        
        # Save a summary
        agg_dict = {'date': ['min', 'max']}
        if 'zhvi' in df.columns:
            agg_dict['zhvi'] = 'count'
        if 'population' in df.columns:
            agg_dict['population'] = 'count'
            
        summary = df.groupby('name').agg(agg_dict)
        print("\nData Summary per Metro:")
        print(summary)

    def run(self):
        zillow_df = self.load_and_standardize_zillow()
        census_df = self.load_and_standardize_census()
        bls_df = self.load_and_standardize_bls()
        fhfa_df = self.load_and_standardize_fhfa()
        freddie_df = self.load_and_standardize_freddie_mac()
        
        master_df = self.merge_data(zillow_df, census_df, bls_df, fhfa_df, freddie_df)
        clean_df = self.clean_data(master_df)
        self.save_data(clean_df)

if __name__ == "__main__":
    cleaner = DataCleaner()
    cleaner.run()
