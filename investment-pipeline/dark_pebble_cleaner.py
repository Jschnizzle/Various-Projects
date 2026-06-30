import pandas as pd
import numpy as np
from pathlib import Path

def create_dark_pebble_master():
    data_dir = Path('housing_market_data')
    output_dir = data_dir / 'processed'
    output_dir.mkdir(exist_ok=True)

    print("Loading Crosswalk...")
    crosswalk_path = data_dir / 'census' / 'cbsa_to_county.csv'
    crosswalk = pd.read_csv(crosswalk_path)
    # Create FIPS
    crosswalk['fips'] = crosswalk['fipsstatecode'].astype(str).str.zfill(2) + \
                        crosswalk['fipscountycode'].astype(str).str.zfill(3)
    crosswalk['cbsa_code'] = crosswalk['cbsacode'].astype(str)
    county_to_cbsa = crosswalk[['fips', 'cbsa_code', 'countycountyequivalent', 'statename']].drop_duplicates()

    # 1. Load ZHVI (County)
    print("Loading ZHVI (County)...")
    zhvi_path = data_dir / 'zillow' / 'zhvi_county.csv'
    zhvi_df = pd.read_csv(zhvi_path)
    
    # Create FIPS
    zhvi_df['StateCodeFIPS'] = zhvi_df['StateCodeFIPS'].astype(str).str.zfill(2)
    zhvi_df['MunicipalCodeFIPS'] = zhvi_df['MunicipalCodeFIPS'].astype(str).str.zfill(3)
    zhvi_df['fips'] = zhvi_df['StateCodeFIPS'] + zhvi_df['MunicipalCodeFIPS']
    
    # Melt
    date_cols = [c for c in zhvi_df.columns if c[0].isdigit() and '-' in c]
    zhvi_long = zhvi_df.melt(id_vars=['fips'], value_vars=date_cols, var_name='date', value_name='zhvi')
    zhvi_long['date'] = pd.to_datetime(zhvi_long['date'])
    
    # Normalize to Month Start for merging
    zhvi_long['date'] = zhvi_long['date'].dt.to_period('M').dt.to_timestamp()
    
    # Merge with Crosswalk to get CBSA for each county
    zhvi_merged = pd.merge(zhvi_long, county_to_cbsa, on='fips', how='inner')

    # 2. Load ZORI (Metro)
    print("Loading ZORI (Rent)...")
    zori_path = data_dir / 'zillow' / 'zori_metro.csv'
    zori_df = pd.read_csv(zori_path)
    
    # Zillow RegionName to CBSA Mapping
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
    
    zori_df['cbsa_code'] = zori_df['RegionName'].map(zillow_mapping)
    
    # Melt
    date_cols_zori = [c for c in zori_df.columns if c[0].isdigit() and '-' in c]
    zori_long = zori_df.melt(id_vars=['cbsa_code'], value_vars=date_cols_zori, var_name='date', value_name='rent')
    zori_long['date'] = pd.to_datetime(zori_long['date']).dt.to_period('M').dt.to_timestamp()

    # 3. Load Wages (Metro - Quarterly)
    print("Loading Wages...")
    wages_path = data_dir / 'bls' / 'metro_wages.csv'
    wages_df = pd.read_csv(wages_path)
    wages_df['cbsa_code'] = wages_df['metro_code'].astype(str)
    
    # Convert Quarter to Date (approximate to middle of quarter or start)
    # Q1 -> 01-01, Q2 -> 04-01, etc.
    q_map = {'Q01': '01-01', 'Q02': '04-01', 'Q03': '07-01', 'Q04': '10-01'}
    wages_df['date_str'] = wages_df['year'].astype(str) + '-' + wages_df['period'].map(q_map)
    wages_df['date'] = pd.to_datetime(wages_df['date_str'])
    
    wages_long = wages_df[['cbsa_code', 'date', 'value']].rename(columns={'value': 'wage'})
    
    # Resample Wages to Monthly (Interpolate)
    # We need to pivot, resample, and melt back
    wages_pivot = wages_long.pivot(index='date', columns='cbsa_code', values='wage')
    wages_monthly = wages_pivot.resample('MS').interpolate(method='linear')
    wages_monthly = wages_monthly.reset_index().melt(id_vars='date', var_name='cbsa_code', value_name='wage')
    # Already Month Start

    # 4. Load Employment (Metro - Monthly)
    print("Loading Employment...")
    emp_path = data_dir / 'bls' / 'metro_employment.csv'
    emp_df = pd.read_csv(emp_path)
    emp_df['cbsa_code'] = emp_df['metro_code'].astype(str)
    
    # M01 -> 01-01
    emp_df['month'] = emp_df['period'].str.replace('M', '').astype(int)
    emp_df['date'] = pd.to_datetime(emp_df['year'].astype(str) + '-' + emp_df['month'].astype(str) + '-01')
    # Already Month Start
    
    emp_long = emp_df[['cbsa_code', 'date', 'value']].rename(columns={'value': 'employment'})

    # 5. Merge All
    print("Merging datasets...")
    # Start with ZHVI (County level is our base unit for "Dark Pebble")
    master = zhvi_merged.copy()
    
    # Merge Metro level data onto County level data using CBSA
    master = pd.merge(master, zori_long, on=['cbsa_code', 'date'], how='left')
    master = pd.merge(master, wages_monthly, on=['cbsa_code', 'date'], how='left')
    master = pd.merge(master, emp_long, on=['cbsa_code', 'date'], how='left')
    
    # 6. Calculate Metrics
    print("Calculating Dark Pebble Metrics...")
    master = master.sort_values(['fips', 'date'])
    
    # Price-to-Rent Ratio
    master['price_to_rent'] = master['zhvi'] / (master['rent'] * 12)
    
    # 3-Year Growth Rates
    # We use transform to calculate per group
    grouped = master.groupby('fips')
    
    master['appreciation_3y'] = grouped['zhvi'].pct_change(periods=36)
    master['rent_growth_3y'] = grouped['rent'].pct_change(periods=36)
    master['wage_growth_3y'] = grouped['wage'].pct_change(periods=36)
    master['job_growth_3y'] = grouped['employment'].pct_change(periods=36)
    
    # Rent Gap Proxy: Appreciation - Rent Growth
    # If prices rise faster than rents, it suggests "Upside Potential" (or bubble/displacement risk)
    master['rent_gap_proxy'] = master['appreciation_3y'] - master['rent_growth_3y']
    
    # Forward fill to handle lagging data sources (BLS/ZORI vs Zillow)
    # We set index to fips to preserve it during groupby operations
    master = master.set_index('fips')
    master = master.groupby(level=0).ffill()
    master = master.reset_index()
    
    # Save
    output_file = output_dir / 'dark_pebble_master.csv'
    master.to_csv(output_file, index=False)
    print(f"✓ Created {output_file}")
    print(f"  Shape: {master.shape}")
    
    # Create a "Latest Snapshot" for the Scatter/Map
    latest_date = master['date'].max()
    # Actually, different counties might have different max dates. Let's take the latest available for each.
    snapshot = master.sort_values('date').groupby('fips').tail(1)
    snapshot_file = output_dir / 'dark_pebble_snapshot.csv'
    snapshot.to_csv(snapshot_file, index=False)
    print(f"✓ Created {snapshot_file}")

if __name__ == "__main__":
    create_dark_pebble_master()
