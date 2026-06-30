#!/usr/bin/env python3
"""
Housing Market Data Downloader
Downloads datasets for housing market investment analysis (2024-2025)
Focuses on CA to TX migration and emerging market opportunities
"""

import os
import requests
import pandas as pd
from datetime import datetime
import time
from pathlib import Path
import zipfile
import io

class HousingDataDownloader:
    """
    Downloads housing market data from multiple sources:
    - Zillow Research Data
    - U.S. Census Bureau (Migration & Demographics)
    - Bureau of Labor Statistics (Employment & Wages)
    - Additional market data sources
    """
    
    def __init__(self, output_dir='housing_data'):
        """
        Initialize downloader with output directory
        
        Args:
            output_dir: Directory to save downloaded datasets
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for organization
        self.zillow_dir = self.output_dir / 'zillow'
        self.census_dir = self.output_dir / 'census'
        self.bls_dir = self.output_dir / 'bls'
        self.other_dir = self.output_dir / 'other'
        
        for dir_path in [self.zillow_dir, self.census_dir, self.bls_dir, self.other_dir]:
            dir_path.mkdir(exist_ok=True)
        
        print(f"✓ Output directory created: {self.output_dir}")
    
    def download_file(self, url, filename, description=""):
        """
        Generic file downloader with progress indication
        
        Args:
            url: URL to download from
            filename: Path object or string for output file
            description: Description of what's being downloaded
        """
        try:
            print(f"\n{'='*70}")
            print(f"Downloading: {description if description else filename}")
            print(f"URL: {url}")
            
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            # Get file size if available
            total_size = int(response.headers.get('content-length', 0))
            
            with open(filename, 'wb') as f:
                if total_size == 0:
                    f.write(response.content)
                else:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        downloaded += len(chunk)
                        f.write(chunk)
                        done = int(50 * downloaded / total_size)
                        print(f"\r[{'█' * done}{'.' * (50-done)}] {downloaded}/{total_size} bytes", end='')
            
            print(f"\n✓ Saved to: {filename}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"\n✗ Error downloading {url}: {e}")
            return False
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            return False
    
    def download_zillow_data(self):
        """
        Download Zillow Research Data
        - ZHVI (Home Value Index)
        - Rental Index
        - Inventory data
        - Days on Market
        - Sales data
        """
        print("\n" + "="*70)
        print("DOWNLOADING ZILLOW RESEARCH DATA")
        print("="*70)
        
        zillow_datasets = {
            # Home Values (ZHVI)
            'zhvi_metro': {
                'url': 'https://files.zillowstatic.com/research/public_csvs/zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv',
                'description': 'ZHVI All Homes (SFR & Condo) - Metro Level - Time Series'
            },
            'zhvi_county': {
                'url': 'https://files.zillowstatic.com/research/public_csvs/zhvi/County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv',
                'description': 'ZHVI All Homes (SFR & Condo) - County Level - Time Series'
            },
            'zhvi_zip': {
                'url': 'https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv',
                'description': 'ZHVI All Homes (SFR & Condo) - ZIP Code Level - Time Series'
            },
            
            # Rental Data
            'zori_metro': {
                'url': 'https://files.zillowstatic.com/research/public_csvs/zori/Metro_zori_uc_sfrcondomfr_sm_month.csv',
                'description': 'Zillow Observed Rent Index (ZORI) - Metro Level'
            },
            
            # Inventory
            'inventory_metro': {
                'url': 'https://files.zillowstatic.com/research/public_csvs/invt_fs/Metro_invt_fs_uc_sfrcondo_sm_month.csv',
                'description': 'For-Sale Inventory - Metro Level'
            },
            
            # Days on Market
            'days_on_market_metro': {
                'url': 'https://files.zillowstatic.com/research/public_csvs/median_days_to_close/Metro_median_days_to_close_uc_sfrcondo_sm_week.csv',
                'description': 'Median Days to Close - Metro Level'
            },
            
            # Sales Count
            'sales_count_metro': {
                'url': 'https://files.zillowstatic.com/research/public_csvs/sales_count_now/Metro_sales_count_now_uc_sfrcondo_month.csv',
                'description': 'Sales Count - Metro Level'
            },
            
            # List Price
            'median_list_price_metro': {
                'url': 'https://files.zillowstatic.com/research/public_csvs/mlp/Metro_mlp_uc_sfrcondo_sm_month.csv',
                'description': 'Median List Price - Metro Level'
            },
            
            # Price Cuts (URL often changes, recommended manual download if 404)
            # 'price_cuts_metro': {
            #     'url': 'https://files.zillowstatic.com/research/public_csvs/pct_listings_price_cut/Metro_pct_listings_price_cut_uc_sfrcondo_month.csv',
            #     'description': 'Percent of Listings With Price Cut - Metro Level'
            # }
        }
        
        success_count = 0
        for dataset_name, info in zillow_datasets.items():
            filename = self.zillow_dir / f"{dataset_name}.csv"
            if self.download_file(info['url'], filename, info['description']):
                success_count += 1
            time.sleep(1)  # Be polite to the server
        
        print(f"\n✓ Downloaded {success_count}/{len(zillow_datasets)} Zillow datasets")
        return success_count
    
    def download_census_data(self):
        """
        Download U.S. Census Bureau data
        - County-to-County Migration Flows
        - Population Estimates
        - American Community Survey (ACS) data
        """
        print("\n" + "="*70)
        print("DOWNLOADING U.S. CENSUS BUREAU DATA")
        print("="*70)
        
        census_datasets = {
            # Population Estimates
            'population_estimates': {
                'url': 'https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/totals/co-est2023-alldata.csv',
                'description': 'County Population Estimates (2020-2023)'
            },
            
            # Building Permits
            'building_permits': {
                'url': 'https://www2.census.gov/econ/bps/Metro/ma2023a.txt',
                'description': 'Building Permits by Metro Area (2023 Annual)'
            },
        }
        
        success_count = 0
        for dataset_name, info in census_datasets.items():
            filename = self.census_dir / f"{dataset_name}.csv"
            if self.download_file(info['url'], filename, info['description']):
                success_count += 1
            time.sleep(1)
        
        print(f"\n✓ Downloaded {success_count}/{len(census_datasets)} Census datasets")
        
        # Note about migration data
        print("\n" + "="*70)
        print("NOTE: County-to-County Migration Data")
        print("="*70)
        print("Migration flows data requires manual download from:")
        print("https://www.census.gov/data/tables/time-series/demo/geographic-mobility/county-to-county-migration.html")
        print("Download the most recent year's data and save to:", self.census_dir / "migration_flows.csv")
        print("="*70)
        
        return success_count
    
    def download_bls_data(self):
        """
        Download Bureau of Labor Statistics data
        Note: BLS requires API key for programmatic access
        This method provides instructions for manual download
        """
        print("\n" + "="*70)
        print("BLS DATA DOWNLOAD INSTRUCTIONS")
        print("="*70)
        
        instructions = """
        Bureau of Labor Statistics data requires either:
        1. Manual download from https://www.bls.gov/data/
        2. API access (requires free registration at https://www.bls.gov/developers/)
        
        KEY DATASETS TO DOWNLOAD:
        
        1. QCEW (Quarterly Census of Employment and Wages)
           URL: https://www.bls.gov/cew/downloadable-data-files.htm
           - Download: County High-Level CSVs (most recent 4 quarters)
           - Save to: {self.bls_dir}/qcew/
        
        2. OES (Occupational Employment Statistics)
           URL: https://www.bls.gov/oes/tables.htm
           - Download: Metropolitan Area data (annual)
           - Save to: {self.bls_dir}/oes/
        
        3. CPI (Consumer Price Index) - for inflation adjustment
           URL: https://www.bls.gov/cpi/data.htm
           - Download: All items in U.S. city average (monthly)
           - Save to: {self.bls_dir}/cpi.csv
        
        ALTERNATIVE: Use BLS API
        -------------------------
        To use the BLS API:
        1. Register for API key at: https://www.bls.gov/developers/home.htm
        2. Save your API key to: {self.bls_dir}/api_key.txt
        3. Run the companion script: bls_api_downloader.py
        """
        
        print(instructions)
        
        # Create subdirectories
        (self.bls_dir / 'qcew').mkdir(exist_ok=True)
        (self.bls_dir / 'oes').mkdir(exist_ok=True)
        
        print("✓ Created BLS data directories")
        return 0
    
    def download_additional_sources(self):
        """
        Download data from additional sources
        - FHFA House Price Index
        - Freddie Mac mortgage rates
        """
        print("\n" + "="*70)
        print("DOWNLOADING ADDITIONAL DATA SOURCES")
        print("="*70)
        
        additional_datasets = {
            # FHFA House Price Index
            'fhfa_hpi_metro': {
                'url': 'https://www.fhfa.gov/hpi/download/monthly/hpi_master.csv',
                'description': 'FHFA House Price Index - Master File'
            },
            
            # Freddie Mac Primary Mortgage Market Survey
            # 'freddie_mac_rates': {
            #     'url': 'https://www.freddiemac.com/pmms/pmms_archives/PMMS_averages_since_1971.csv',
            #     'description': 'Freddie Mac Historical Mortgage Rates'
            # },
        }
        
        success_count = 0
        for dataset_name, info in additional_datasets.items():
            filename = self.other_dir / f"{dataset_name}.csv"
            if self.download_file(info['url'], filename, info['description']):
                success_count += 1
            time.sleep(1)
            
        print("\n" + "="*70)
        print("MANUAL DOWNLOADS REQUIRED")
        print("="*70)
        print("The following datasets require manual download due to URL changes:")
        print("\n1. Freddie Mac Mortgage Rates")
        print("   - URL: https://www.freddiemac.com/pmms/pmms_archives/PMMS_averages_since_1971.csv (or search for 'PMMS Archive')")
        print("   - Save as: housing_market_data/other/freddie_mac_rates.csv")
        
        print(f"\n✓ Downloaded {success_count}/{len(additional_datasets)} additional datasets")
        return success_count
    
    def create_metro_reference(self):
        """
        Create a reference file mapping metro codes to names
        This helps with data merging later
        """
        print("\n" + "="*70)
        print("CREATING METRO AREA REFERENCE FILE")
        print("="*70)
        
        # Key metros for CA to TX migration analysis
        metros_of_interest = {
            'California Metros': [
                {'name': 'Los Angeles-Long Beach-Anaheim, CA', 'cbsa_code': '31080'},
                {'name': 'San Francisco-Oakland-Berkeley, CA', 'cbsa_code': '41860'},
                {'name': 'San Diego-Chula Vista-Carlsbad, CA', 'cbsa_code': '41740'},
                {'name': 'San Jose-Sunnyvale-Santa Clara, CA', 'cbsa_code': '41940'},
                {'name': 'Sacramento-Roseville-Folsom, CA', 'cbsa_code': '40900'},
            ],
            'Texas Metros': [
                {'name': 'Dallas-Fort Worth-Arlington, TX', 'cbsa_code': '19100'},
                {'name': 'Houston-The Woodlands-Sugar Land, TX', 'cbsa_code': '26420'},
                {'name': 'Austin-Round Rock-Georgetown, TX', 'cbsa_code': '12420'},
                {'name': 'San Antonio-New Braunfels, TX', 'cbsa_code': '41700'},
            ],
            'Emerging Markets': [
                {'name': 'Phoenix-Mesa-Chandler, AZ', 'cbsa_code': '38060'},
                {'name': 'Charlotte-Concord-Gastonia, NC-SC', 'cbsa_code': '16740'},
                {'name': 'Raleigh-Cary, NC', 'cbsa_code': '39580'},
                {'name': 'Nashville-Davidson--Murfreesboro--Franklin, TN', 'cbsa_code': '34980'},
                {'name': 'Greenville-Anderson, SC', 'cbsa_code': '24860'},
                {'name': 'Charleston-North Charleston, SC', 'cbsa_code': '16700'},
                {'name': 'Buffalo-Cheektowaga, NY', 'cbsa_code': '15380'},
                {'name': 'Virginia Beach-Norfolk-Newport News, VA-NC', 'cbsa_code': '47260'},
            ]
        }
        
        # Flatten the structure
        all_metros = []
        for category, metros in metros_of_interest.items():
            for metro in metros:
                metro['category'] = category
                all_metros.append(metro)
        
        # Create DataFrame
        metro_df = pd.DataFrame(all_metros)
        
        # Save to file
        output_file = self.output_dir / 'metro_reference.csv'
        metro_df.to_csv(output_file, index=False)
        
        print(f"✓ Created metro reference file with {len(all_metros)} metros")
        print(f"✓ Saved to: {output_file}")
        
        return metro_df
    
    def generate_download_summary(self):
        """
        Generate a summary report of all downloaded files
        """
        print("\n" + "="*70)
        print("DOWNLOAD SUMMARY")
        print("="*70)
        
        summary = {
            'Zillow': list(self.zillow_dir.glob('*.csv')),
            'Census': list(self.census_dir.glob('*.csv')),
            'BLS': list(self.bls_dir.glob('*.csv')),
            'Other': list(self.other_dir.glob('*.csv')),
        }
        
        total_files = 0
        total_size = 0
        
        for category, files in summary.items():
            print(f"\n{category}:")
            if files:
                for file in files:
                    size = file.stat().st_size / 1024 / 1024  # Convert to MB
                    total_size += size
                    print(f"  ✓ {file.name} ({size:.2f} MB)")
                    total_files += 1
            else:
                print("  No files downloaded (may require manual download)")
        
        print(f"\n{'='*70}")
        print(f"Total files downloaded: {total_files}")
        print(f"Total size: {total_size:.2f} MB")
        print(f"Output directory: {self.output_dir.absolute()}")
        print(f"{'='*70}")
        
        # Create a metadata file
        metadata = {
            'download_date': datetime.now().isoformat(),
            'total_files': total_files,
            'total_size_mb': round(total_size, 2),
            'categories': {cat: len(files) for cat, files in summary.items()}
        }
        
        import json
        with open(self.output_dir / 'download_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n✓ Metadata saved to: {self.output_dir / 'download_metadata.json'}")
    
    def download_all(self):
        """
        Download all datasets
        """
        print("\n" + "="*70)
        print("HOUSING MARKET DATA DOWNLOADER")
        print("Starting comprehensive data download...")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # Download from each source
        self.download_zillow_data()
        self.download_census_data()
        self.download_bls_data()
        self.download_additional_sources()
        self.create_metro_reference()
        
        # Generate summary
        self.generate_download_summary()
        
        print("\n" + "="*70)
        print("NEXT STEPS")
        print("="*70)
        print("""
        1. Complete manual downloads:
           - Census migration flows data
           - BLS QCEW and OES data (or set up API access)
        
        2. Verify data quality:
           - Check for missing values
           - Verify date ranges
           - Ensure metro codes align
        
        3. Run data cleaning script: data_cleaner.py
           - Will standardize formats
           - Merge datasets
           - Create analysis-ready dataset
        
        4. Ready for analysis!
        """)
        print("="*70)


def main():
    """
    Main execution function
    """
    # Create downloader instance
    downloader = HousingDataDownloader(output_dir='housing_market_data')
    
    # Download all data
    downloader.download_all()


if __name__ == "__main__":
    main()
