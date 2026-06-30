#!/usr/bin/env python3
"""
BLS API Data Downloader
Download employment and wage data from Bureau of Labor Statistics API
Requires free API key from: https://www.bls.gov/developers/
"""

import os
import json
import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

class BLSAPIDownloader:
    """
    Download BLS data using their public API
    API Documentation: https://www.bls.gov/developers/api_signature_v2.htm
    """
    
    def __init__(self, api_key=None, output_dir='housing_market_data/bls'):
        """
        Initialize BLS API downloader
        
        Args:
            api_key: BLS API key (or set BLS_API_KEY environment variable)
            output_dir: Directory to save downloaded data
        """
        self.api_key = api_key or os.getenv('BLS_API_KEY')
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # API endpoints
        self.api_url = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
        
        # Rate limiting (registered users: 500 requests/day, 50 series/query)
        self.max_series_per_request = 50 if self.api_key else 25
        self.requests_made = 0
        self.max_requests_per_day = 500 if self.api_key else 25
        
        print(f"✓ BLS API Downloader initialized")
        print(f"  API Key: {'Provided' if self.api_key else 'NOT PROVIDED (limited access)'}")
        print(f"  Output: {self.output_dir}")
    
    def _make_api_request(self, series_ids, start_year, end_year):
        """
        Make a request to BLS API with rate limiting
        
        Args:
            series_ids: List of BLS series IDs
            start_year: Start year for data
            end_year: End year for data
        
        Returns:
            JSON response or None on error
        """
        if self.requests_made >= self.max_requests_per_day:
            print(f"✗ Daily API limit reached ({self.max_requests_per_day} requests)")
            return None
        
        headers = {'Content-type': 'application/json'}
        
        payload = {
            'seriesid': series_ids,
            'startyear': str(start_year),
            'endyear': str(end_year)
        }
        
        if self.api_key:
            payload['registrationkey'] = self.api_key
        
        try:
            response = requests.post(
                self.api_url,
                data=json.dumps(payload),
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            self.requests_made += 1
            print(f"  API request {self.requests_made}/{self.max_requests_per_day}")
            
            # Rate limiting: 1 request per second for unregistered, can go faster with key
            time.sleep(0.5 if self.api_key else 2)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"✗ API request failed: {e}")
            return None
    
    def download_metro_employment_data(self, metro_codes, start_year=2020, end_year=2024):
        """
        Download employment data for specific metro areas
        
        Args:
            metro_codes: List of CBSA codes
            start_year: Start year
            end_year: End year
        
        Returns:
            DataFrame with employment data
        """
        print(f"\n{'='*70}")
        print(f"Downloading Employment Data for {len(metro_codes)} metro areas")
        print(f"Years: {start_year}-{end_year}")
        print(f"{'='*70}")
        
        # Map metros to primary state FIPS for SM series
        metro_state_map = {
            '31080': '06', '41860': '06', '41740': '06', '41940': '06', '40900': '06', # CA
            '19100': '48', '26420': '48', '12420': '48', '41700': '48', # TX
            '38060': '04', # AZ
            '16740': '37', '39580': '37', # NC
            '34980': '47', # TN
            '24860': '45', '16700': '45', # SC
            '15380': '36', # NY
            '47260': '51'  # VA
        }
        
        all_data = []
        
        # BLS Series ID format for employment: SMS + State(2) + Area(5) + 00000000 + 01
        # Example: SMS06310800000000001 (Los Angeles, CA)
        for metro in metro_codes:
            state_code = metro_state_map.get(metro)
            if not state_code:
                print(f"⚠ Warning: No state code found for metro {metro}, skipping...")
                continue
                
            series_id = f"SMS{state_code}{metro}0000000001"
            
            print(f"\nFetching: {metro}")
            response = self._make_api_request([series_id], start_year, end_year)
            
            if response and response.get('status') == 'REQUEST_SUCCEEDED':
                for series in response.get('Results', {}).get('series', []):
                    for item in series.get('data', []):
                        all_data.append({
                            'metro_code': metro,
                            'series_id': series_id,
                            'year': item['year'],
                            'period': item['period'],
                            'value': float(item['value']),
                            'footnotes': item.get('footnotes', '')
                        })
                print(f"  ✓ Downloaded {len(series.get('data', []))} data points")
            else:
                print(f"  ✗ Failed to download data")
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data)
        
        if not df.empty:
            # Save to file
            output_file = self.output_dir / 'metro_employment.csv'
            df.to_csv(output_file, index=False)
            print(f"\n✓ Saved employment data to: {output_file}")
        
        return df
    
    def download_metro_wage_data(self, metro_codes, start_year=2020, end_year=2024):
        """
        Download average weekly wage data for metro areas
        
        Args:
            metro_codes: List of CBSA codes
            start_year: Start year
            end_year: End year
        
        Returns:
            DataFrame with wage data
        """
        print(f"\n{'='*70}")
        print(f"Downloading Wage Data for {len(metro_codes)} metro areas")
        print(f"Years: {start_year}-{end_year}")
        print(f"{'='*70}")
        
        all_data = []
        
        # BLS Series ID format for wages (QCEW): ENU + C + Area(4) + 40510
        # Area: C + first 4 digits of MSA code (for post-2003 definitions)
        # DataType: 4 (Avg Weekly Wage)
        # Size: 0 (All sizes)
        # Ownership: 5 (Private)
        # Industry: 10 (Total, all industries)
        for metro in metro_codes:
            # Use first 4 digits of metro code prefixed with C
            area_code = f"C{metro[:4]}"
            series_id = f"ENU{area_code}40510"
            
            print(f"\nFetching: {metro}")
            response = self._make_api_request([series_id], start_year, end_year)
            
            if response and response.get('status') == 'REQUEST_SUCCEEDED':
                for series in response.get('Results', {}).get('series', []):
                    for item in series.get('data', []):
                        all_data.append({
                            'metro_code': metro,
                            'series_id': series_id,
                            'year': item['year'],
                            'period': item['period'],
                            'value': float(item['value']),
                            'footnotes': item.get('footnotes', '')
                        })
                print(f"  ✓ Downloaded {len(series.get('data', []))} data points")
            else:
                print(f"  ✗ Failed to download data")
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data)
        
        if not df.empty:
            # Save to file
            output_file = self.output_dir / 'metro_wages.csv'
            df.to_csv(output_file, index=False)
            print(f"\n✓ Saved wage data to: {output_file}")
        
        return df
    
    def download_state_employment(self, state_fips_codes, start_year=2020, end_year=2024):
        """
        Download state-level employment data
        
        Args:
            state_fips_codes: List of state FIPS codes
            start_year: Start year
            end_year: End year
        
        Returns:
            DataFrame with state employment
        """
        print(f"\n{'='*70}")
        print(f"Downloading State Employment Data")
        print(f"States: {len(state_fips_codes)}, Years: {start_year}-{end_year}")
        print(f"{'='*70}")
        
        all_data = []
        
        # BLS Series ID format for state unemployment: LAUST + state FIPS + 0000000000003
        # This gets unemployment rate
        for state_fips in state_fips_codes:
            series_id = f"LAUST{state_fips}0000000000003"
            
            print(f"\nFetching: State {state_fips}")
            response = self._make_api_request([series_id], start_year, end_year)
            
            if response and response.get('status') == 'REQUEST_SUCCEEDED':
                for series in response.get('Results', {}).get('series', []):
                    for item in series.get('data', []):
                        all_data.append({
                            'state_fips': state_fips,
                            'series_id': series_id,
                            'year': item['year'],
                            'period': item['period'],
                            'value': float(item['value']),
                            'footnotes': item.get('footnotes', '')
                        })
                print(f"  ✓ Downloaded {len(series.get('data', []))} data points")
            else:
                print(f"  ✗ Failed to download data")
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data)
        
        if not df.empty:
            output_file = self.output_dir / 'state_employment.csv'
            df.to_csv(output_file, index=False)
            print(f"\n✓ Saved state employment to: {output_file}")
        
        return df
    
    def download_all_bls_data(self):
        """
        Download all relevant BLS data for housing market analysis
        """
        print(f"\n{'='*70}")
        print("BLS DATA DOWNLOAD - COMPREHENSIVE")
        print(f"{'='*70}")
        
        # Key metros for analysis
        metro_codes = [
            # California
            '31080',  # Los Angeles
            '41860',  # San Francisco
            '41740',  # San Diego
            '41940',  # San Jose
            '40900',  # Sacramento
            
            # Texas
            '19100',  # Dallas-Fort Worth
            '26420',  # Houston
            '12420',  # Austin
            '41700',  # San Antonio
            
            # Emerging markets
            '38060',  # Phoenix
            '16740',  # Charlotte
            '39580',  # Raleigh
            '34980',  # Nashville
            '24860',  # Greenville, SC
            '16700',  # Charleston, SC
            '15380',  # Buffalo
            '47260',  # Virginia Beach
        ]
        
        # State FIPS codes
        state_fips = {
            '06': 'California',
            '48': 'Texas',
            '04': 'Arizona',
            '37': 'North Carolina',
            '45': 'South Carolina',
            '47': 'Tennessee',
            '36': 'New York',
            '51': 'Virginia'
        }
        
        # Download data
        employment_df = self.download_metro_employment_data(metro_codes, 2020, 2024)
        wage_df = self.download_metro_wage_data(metro_codes, 2020, 2024)
        state_df = self.download_state_employment(list(state_fips.keys()), 2020, 2024)
        
        # Create summary
        print(f"\n{'='*70}")
        print("DOWNLOAD SUMMARY")
        print(f"{'='*70}")
        print(f"API requests made: {self.requests_made}/{self.max_requests_per_day}")
        print(f"Employment records: {len(employment_df) if not employment_df.empty else 0}")
        print(f"Wage records: {len(wage_df) if not wage_df.empty else 0}")
        print(f"State records: {len(state_df) if not state_df.empty else 0}")
        print(f"{'='*70}")
        
        return {
            'employment': employment_df,
            'wages': wage_df,
            'state_employment': state_df
        }


def main():
    """
    Main execution function
    """
    # Check for API key
    api_key = os.getenv('BLS_API_KEY')
    
    # If not in env, check file
    if not api_key:
        key_file = Path('housing_market_data/bls/api_key.txt')
        if key_file.exists():
            with open(key_file, 'r') as f:
                api_key = f.read().strip()
            print(f"✓ API key loaded from {key_file}")
    
    if not api_key:
        print("\n" + "="*70)
        print("WARNING: No BLS API key found")
        print("="*70)
        print("""
        To use this script with full functionality:
        
        1. Register for a free API key at:
           https://www.bls.gov/developers/home.htm
        
        2. Set the API key as an environment variable:
           export BLS_API_KEY='your-key-here'
           
           Or create a file: housing_market_data/bls/api_key.txt
        
        3. Re-run this script
        
        Without an API key, you can still make limited requests.
        """)
        print("="*70)
        
        response = input("\nContinue with limited access? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            return
    
    # Create downloader
    downloader = BLSAPIDownloader(api_key=api_key)
    
    # Download all data
    results = downloader.download_all_bls_data()
    
    print("\n✓ BLS data download complete!")


if __name__ == "__main__":
    main()
