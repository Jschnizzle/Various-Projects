#!/usr/bin/env python3
"""
Data Verification Script
Checks downloaded housing market data for completeness and quality
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import json

class DataVerifier:
    """
    Verify downloaded housing market data
    """
    
    def __init__(self, data_dir='housing_market_data'):
        """
        Initialize verifier
        
        Args:
            data_dir: Directory containing downloaded data
        """
        self.data_dir = Path(data_dir)
        self.issues = []
        self.warnings = []
        self.stats = {}
    
    def verify_directory_structure(self):
        """Check that expected directories exist"""
        print("\n" + "="*70)
        print("VERIFYING DIRECTORY STRUCTURE")
        print("="*70)
        
        expected_dirs = ['zillow', 'census', 'bls', 'other']
        
        for dir_name in expected_dirs:
            dir_path = self.data_dir / dir_name
            if dir_path.exists():
                print(f"✓ {dir_name}/ exists")
            else:
                self.issues.append(f"Missing directory: {dir_name}/")
                print(f"✗ {dir_name}/ NOT FOUND")
    
    def verify_zillow_data(self):
        """Verify Zillow datasets"""
        print("\n" + "="*70)
        print("VERIFYING ZILLOW DATA")
        print("="*70)
        
        zillow_dir = self.data_dir / 'zillow'
        
        if not zillow_dir.exists():
            self.issues.append("Zillow directory not found")
            return
        
        expected_files = [
            'zhvi_metro.csv',
            'zhvi_county.csv',
            'zhvi_zip.csv',
            'zori_metro.csv',
            'inventory_metro.csv',
            'days_on_market_metro.csv',
            'sales_count_metro.csv',
            'median_list_price_metro.csv',
            'sales_count_metro.csv',
            'median_list_price_metro.csv'
        ]
        
        for filename in expected_files:
            filepath = zillow_dir / filename
            
            if filepath.exists():
                try:
                    df = pd.read_csv(filepath, nrows=5)
                    rows = pd.read_csv(filepath).shape[0]
                    cols = df.shape[1]
                    size_mb = filepath.stat().st_size / 1024 / 1024
                    
                    print(f"✓ {filename}")
                    print(f"  Rows: {rows:,}, Cols: {cols}, Size: {size_mb:.2f} MB")
                    
                    # Check for key columns
                    if 'RegionName' not in df.columns:
                        self.warnings.append(f"{filename}: Missing 'RegionName' column")
                    
                    # Check for time series data
                    date_cols = [col for col in df.columns if '-' in str(col)]
                    if len(date_cols) < 12:
                        self.warnings.append(f"{filename}: Less than 12 months of data")
                    
                    self.stats[filename] = {
                        'rows': rows,
                        'cols': cols,
                        'size_mb': round(size_mb, 2),
                        'date_columns': len(date_cols)
                    }
                    
                except Exception as e:
                    self.issues.append(f"Error reading {filename}: {e}")
                    print(f"✗ {filename} - Error: {e}")
            else:
                print(f"✗ {filename} NOT FOUND")
        
        # Check for optional/manual Zillow files
        manual_files = ['price_cuts_metro.csv']
        for filename in manual_files:
            filepath = zillow_dir / filename
            if not filepath.exists():
                self.warnings.append(f"Manual Zillow file missing: {filename}")
                print(f"⚠ {filename} NOT FOUND (requires manual download)")
            else:
                print(f"✓ {filename} (Manual download found)")
    
    def verify_census_data(self):
        """Verify Census Bureau datasets"""
        print("\n" + "="*70)
        print("VERIFYING CENSUS DATA")
        print("="*70)
        
        census_dir = self.data_dir / 'census'
        
        if not census_dir.exists():
            self.issues.append("Census directory not found")
            return
        
        # Check for expected files
        expected_files = [
            'population_estimates.csv',
            'building_permits.csv',
        ]
        
        for filename in expected_files:
            filepath = census_dir / filename
            
            if filepath.exists():
                try:
                    # Try default encoding (utf-8)
                    try:
                        df = pd.read_csv(filepath, nrows=5)
                        rows = pd.read_csv(filepath).shape[0]
                    except UnicodeDecodeError:
                        # Fallback to latin-1 for Census data
                        df = pd.read_csv(filepath, nrows=5, encoding='latin-1')
                        rows = pd.read_csv(filepath, encoding='latin-1').shape[0]
                        
                    size_mb = filepath.stat().st_size / 1024 / 1024
                    
                    print(f"✓ {filename}")
                    print(f"  Rows: {rows:,}, Size: {size_mb:.2f} MB")
                    
                    self.stats[filename] = {
                        'rows': rows,
                        'cols': df.shape[1],
                        'size_mb': round(size_mb, 2)
                    }
                    
                except Exception as e:
                    self.issues.append(f"Error reading {filename}: {e}")
                    print(f"✗ {filename} - Error: {e}")
            else:
                self.warnings.append(f"Optional Census file missing: {filename}")
                print(f"⚠ {filename} NOT FOUND (may require manual download)")
        
        # Check for migration data (manual download)
        migration_file = census_dir / 'migration_flows.csv'
        if not migration_file.exists():
            self.warnings.append("Migration flows data not found (requires manual download)")
            print("\n⚠ migration_flows.csv NOT FOUND")
            print("  This requires manual download from:")
            print("  https://www.census.gov/data/tables/time-series/demo/geographic-mobility/county-to-county-migration.html")
    
    def verify_bls_data(self):
        """Verify BLS datasets"""
        print("\n" + "="*70)
        print("VERIFYING BLS DATA")
        print("="*70)
        
        bls_dir = self.data_dir / 'bls'
        
        if not bls_dir.exists():
            self.issues.append("BLS directory not found")
            return
        
        # Check for API-downloaded files
        api_files = [
            'metro_employment.csv',
            'metro_wages.csv',
            'state_employment.csv'
        ]
        
        api_files_found = 0
        for filename in api_files:
            filepath = bls_dir / filename
            
            if filepath.exists():
                try:
                    df = pd.read_csv(filepath)
                    print(f"✓ {filename}")
                    print(f"  Rows: {df.shape[0]:,}, Size: {filepath.stat().st_size / 1024:.2f} KB")
                    api_files_found += 1
                    
                    self.stats[filename] = {
                        'rows': df.shape[0],
                        'cols': df.shape[1]
                    }
                    
                except Exception as e:
                    self.warnings.append(f"Error reading {filename}: {e}")
                    print(f"✗ {filename} - Error: {e}")
        
        if api_files_found == 0:
            print("\n⚠ No BLS API data found")
            print("  Options:")
            print("  1. Run: python bls_api_downloader.py (requires API key)")
            print("  2. Manual download from: https://www.bls.gov/data/")
        
        # Check for manual downloads
        qcew_dir = bls_dir / 'qcew'
        if qcew_dir.exists():
            qcew_files = list(qcew_dir.glob('*.csv'))
            if qcew_files:
                print(f"\n✓ Found {len(qcew_files)} QCEW files in qcew/")
            else:
                print("\n⚠ No QCEW files found in qcew/")
    
    def verify_other_data(self):
        """Verify FHFA and other datasets"""
        print("\n" + "="*70)
        print("VERIFYING OTHER DATA SOURCES")
        print("="*70)
        
        other_dir = self.data_dir / 'other'
        
        if not other_dir.exists():
            self.issues.append("Other directory not found")
            return
        
        expected_files = [
            'fhfa_hpi_metro.csv',
            'fhfa_hpi_metro.csv'
        ]
        
        for filename in expected_files:
            filepath = other_dir / filename
            
            if filepath.exists():
                try:
                    df = pd.read_csv(filepath, nrows=5)
                    rows = pd.read_csv(filepath).shape[0]
                    size_mb = filepath.stat().st_size / 1024 / 1024
                    
                    print(f"✓ {filename}")
                    print(f"  Rows: {rows:,}, Size: {size_mb:.2f} MB")
                    
                    self.stats[filename] = {
                        'rows': rows,
                        'cols': df.shape[1],
                        'size_mb': round(size_mb, 2)
                    }
                    
                except Exception as e:
                    self.issues.append(f"Error reading {filename}: {e}")
                    print(f"✗ {filename} - Error: {e}")
            else:
                self.warnings.append(f"Missing other file: {filename}")
                print(f"✗ {filename} NOT FOUND")
        
        # Check for manual Other files
        manual_files = ['freddie_mac_rates.csv']
        for filename in manual_files:
            filepath = other_dir / filename
            if not filepath.exists():
                self.warnings.append(f"Manual Other file missing: {filename}")
                print(f"⚠ {filename} NOT FOUND (requires manual download)")
            else:
                print(f"✓ {filename} (Manual download found)")
    
    def verify_metro_reference(self):
        """Verify metro reference file"""
        print("\n" + "="*70)
        print("VERIFYING METRO REFERENCE FILE")
        print("="*70)
        
        metro_file = self.data_dir / 'metro_reference.csv'
        
        if metro_file.exists():
            try:
                df = pd.read_csv(metro_file)
                print(f"✓ metro_reference.csv")
                print(f"  Metros: {df.shape[0]}")
                print(f"  Columns: {', '.join(df.columns.tolist())}")
                
                # Check key metros
                key_metros = ['Los Angeles', 'Dallas', 'Houston', 'Phoenix', 'Charlotte']
                for metro in key_metros:
                    if df['name'].str.contains(metro, case=False).any():
                        print(f"  ✓ Contains: {metro}")
                
                self.stats['metro_reference'] = {
                    'metros': df.shape[0]
                }
                
            except Exception as e:
                self.issues.append(f"Error reading metro_reference.csv: {e}")
                print(f"✗ Error: {e}")
        else:
            self.issues.append("metro_reference.csv not found")
            print("✗ metro_reference.csv NOT FOUND")
    
    def generate_report(self):
        """Generate verification report"""
        print("\n" + "="*70)
        print("VERIFICATION REPORT")
        print("="*70)
        
        # Count files
        total_files = sum(1 for _ in self.data_dir.rglob('*.csv'))
        total_size = sum(f.stat().st_size for f in self.data_dir.rglob('*.csv'))
        total_size_mb = total_size / 1024 / 1024
        
        print(f"\nTotal CSV files: {total_files}")
        print(f"Total size: {total_size_mb:.2f} MB")
        
        # Print issues
        if self.issues:
            print(f"\n❌ CRITICAL ISSUES ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  - {issue}")
        else:
            print("\n✓ No critical issues found")
        
        # Print warnings
        if self.warnings:
            print(f"\n⚠ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        else:
            print("\n✓ No warnings")
        
        # Data completeness
        print("\n" + "="*70)
        print("DATA COMPLETENESS")
        print("="*70)
        
        completeness = {
            'Zillow': len(list((self.data_dir / 'zillow').glob('*.csv'))) if (self.data_dir / 'zillow').exists() else 0,
            'Census': len(list((self.data_dir / 'census').glob('*.csv'))) if (self.data_dir / 'census').exists() else 0,
            'BLS': len(list((self.data_dir / 'bls').rglob('*.csv'))) if (self.data_dir / 'bls').exists() else 0,
            'Other': len(list((self.data_dir / 'other').glob('*.csv'))) if (self.data_dir / 'other').exists() else 0,
        }
        
        for source, count in completeness.items():
            status = "✓" if count > 0 else "✗"
            print(f"{status} {source}: {count} files")
        
        # Ready for analysis?
        print("\n" + "="*70)
        print("READY FOR ANALYSIS?")
        print("="*70)
        
        required_datasets = [
            (self.data_dir / 'zillow' / 'zhvi_metro.csv').exists(),
            (self.data_dir / 'zillow' / 'zori_metro.csv').exists(),
            (self.data_dir / 'other' / 'fhfa_hpi_metro.csv').exists(),
            (self.data_dir / 'metro_reference.csv').exists(),
        ]
        
        if all(required_datasets):
            print("✓ READY FOR BASIC ANALYSIS")
            print("\nYou have the minimum required datasets to begin analysis.")
            print("Next step: Run 'python data_cleaner.py' to standardize and merge data.")
        else:
            print("✗ NOT READY - Missing required datasets")
            print("\nMissing:")
            if not required_datasets[0]:
                print("  - Zillow ZHVI (home values)")
            if not required_datasets[1]:
                print("  - Zillow ZORI (rental index)")
            if not required_datasets[2]:
                print("  - FHFA HPI")
            if not required_datasets[3]:
                print("  - Metro reference file")
        
        # Optional but recommended
        print("\nOptional (Recommended):")
        
        optional_checks = [
            ((self.data_dir / 'census' / 'migration_flows.csv').exists(), "Census migration flows"),
            ((self.data_dir / 'bls' / 'metro_employment.csv').exists(), "BLS employment data"),
            ((self.data_dir / 'census' / 'building_permits.csv').exists(), "Building permits"),
        ]
        
        for exists, name in optional_checks:
            status = "✓" if exists else "✗"
            print(f"  {status} {name}")
        
        # Save report
        report = {
            'verification_date': datetime.now().isoformat(),
            'total_files': total_files,
            'total_size_mb': round(total_size_mb, 2),
            'issues': self.issues,
            'warnings': self.warnings,
            'completeness': completeness,
            'stats': self.stats
        }
        
        report_file = self.data_dir / 'verification_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✓ Verification report saved to: {report_file}")
    
    def run_verification(self):
        """Run complete verification"""
        print("\n" + "="*70)
        print("HOUSING MARKET DATA VERIFICATION")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        if not self.data_dir.exists():
            print(f"\n✗ Data directory not found: {self.data_dir}")
            print("\nRun the download script first:")
            print("  python housing_data_downloader.py")
            return
        
        # Run verifications
        self.verify_directory_structure()
        self.verify_zillow_data()
        self.verify_census_data()
        self.verify_bls_data()
        self.verify_other_data()
        self.verify_metro_reference()
        
        # Generate report
        self.generate_report()


def main():
    """Main execution"""
    verifier = DataVerifier()
    verifier.run_verification()


if __name__ == "__main__":
    main()
