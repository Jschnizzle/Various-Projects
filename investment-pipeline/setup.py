#!/usr/bin/env python3
"""
Master Setup Script for Housing Market Analysis
Handles environment setup, dependency installation, and initial data download
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def check_python_version():
    """Verify Python version is 3.8+"""
    print_header("Checking Python Version")
    
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("✗ Python 3.8 or higher is required")
        print("  Please upgrade Python and try again")
        return False
    
    print("✓ Python version is compatible")
    return True

def setup_virtual_environment():
    """Create and activate virtual environment"""
    print_header("Setting Up Virtual Environment")
    
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✓ Virtual environment already exists")
        return True
    
    try:
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✓ Virtual environment created")
        
        # Provide activation instructions
        if sys.platform == "win32":
            activate_cmd = "venv\\Scripts\\activate"
        else:
            activate_cmd = "source venv/bin/activate"
        
        print(f"\nTo activate the virtual environment, run:")
        print(f"  {activate_cmd}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create virtual environment: {e}")
        return False

def install_dependencies():
    """Install required Python packages"""
    print_header("Installing Dependencies")
    
    requirements_file = Path("requirements.txt")
    
    if not requirements_file.exists():
        print("✗ requirements.txt not found")
        return False
    
    try:
        print("Installing packages from requirements.txt...")
        print("This may take a few minutes...\n")
        
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        
        print("\n✓ All dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed to install dependencies: {e}")
        print("\nTry installing manually:")
        print(f"  {sys.executable} -m pip install -r requirements.txt")
        return False

def check_api_credentials():
    """Check for BLS API key"""
    print_header("Checking API Credentials")
    
    # Check environment variable
    api_key = os.getenv('BLS_API_KEY')
    
    # Check file
    key_file = Path('housing_market_data/bls/api_key.txt')
    
    if api_key:
        print("✓ BLS API key found in environment variable")
        return True
    elif key_file.exists():
        print(f"✓ BLS API key found in {key_file}")
        return True
    else:
        print("⚠ No BLS API key found (optional)")
        print("\nTo enable full BLS data access:")
        print("1. Register at: https://www.bls.gov/developers/home.htm")
        print("2. Set environment variable: export BLS_API_KEY='your-key'")
        print("   OR create file: housing_market_data/bls/api_key.txt")
        print("\nYou can still proceed with limited BLS access or manual downloads")
        return False

def run_data_download():
    """Execute the main data download script"""
    print_header("Starting Data Download")
    
    print("This will download housing market data from multiple sources.")
    print("Estimated download size: 500MB - 1GB")
    print("Estimated time: 5-15 minutes depending on connection")
    
    response = input("\nProceed with download? (y/n): ")
    
    if response.lower() != 'y':
        print("\nSkipping data download. You can run it later:")
        print("  python housing_data_downloader.py")
        return False
    
    try:
        print("\nStarting download...\n")
        subprocess.run([sys.executable, "housing_data_downloader.py"], check=True)
        print("\n✓ Data download completed")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Data download failed: {e}")
        return False
    except FileNotFoundError:
        print("\n✗ housing_data_downloader.py not found")
        return False

def run_bls_download():
    """Execute BLS API download if credentials available"""
    print_header("BLS Data Download (Optional)")
    
    api_key = os.getenv('BLS_API_KEY')
    key_file = Path('housing_market_data/bls/api_key.txt')
    
    if not api_key and not key_file.exists():
        print("Skipping BLS API download (no API key)")
        print("\nYou can:")
        print("1. Download BLS data manually (see README.md)")
        print("2. Get an API key and run: python bls_api_downloader.py")
        return False
    
    response = input("\nDownload BLS data via API? (y/n): ")
    
    if response.lower() != 'y':
        print("\nSkipping BLS download. You can run it later:")
        print("  python bls_api_downloader.py")
        return False
    
    try:
        print("\nStarting BLS download...\n")
        subprocess.run([sys.executable, "bls_api_downloader.py"], check=True)
        print("\n✓ BLS data download completed")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ BLS download failed: {e}")
        return False
    except FileNotFoundError:
        print("\n✗ bls_api_downloader.py not found")
        return False

def print_manual_steps():
    """Print remaining manual steps"""
    print_header("Manual Steps Required")
    
    print("""
1. CENSUS MIGRATION DATA (Required for full analysis)
   - Visit: https://www.census.gov/data/tables/time-series/demo/geographic-mobility/county-to-county-migration.html
   - Download: Most recent year's data
   - Save as: housing_market_data/census/migration_flows.csv

2. BLS DATA (If not using API)
   - Visit: https://www.bls.gov/cew/downloadable-data-files.htm
   - Download: County High-Level CSVs (recent quarters)
   - Save to: housing_market_data/bls/qcew/

3. VERIFY DOWNLOADS
   - Check: housing_market_data/ directory
   - Verify: download_metadata.json exists
   - Review: Any download errors in console output

4. NEXT STEPS
   - Data cleaning: python data_cleaner.py
   - Feature engineering: python feature_engineer.py
   - Analysis and modeling
    """)

def print_summary():
    """Print setup summary and next steps"""
    print_header("Setup Complete!")
    
    print("""
✓ Environment configured
✓ Dependencies installed
✓ Initial data downloaded

DIRECTORY STRUCTURE:
  housing_market_data/
  ├── zillow/          (Zillow Research data)
  ├── census/          (Census Bureau data)
  ├── bls/             (BLS employment/wage data)
  ├── other/           (FHFA, Freddie Mac data)
  └── metro_reference.csv

NEXT STEPS:

1. Complete manual downloads (see above)

2. Verify data quality:
   python -c "from pathlib import Path; print('Files:', len(list(Path('housing_market_data').rglob('*.csv'))))"

3. Run data cleaning script:
   python data_cleaner.py

4. Run feature engineering:
   python feature_engineer.py

5. Start analysis!

USEFUL COMMANDS:

  # Re-download specific data
  python housing_data_downloader.py
  
  # Download BLS data with API
  python bls_api_downloader.py
  
  # Check what's downloaded
  ls -lh housing_market_data/*/

DOCUMENTATION:
  
  See README.md for:
  - Detailed data source information
  - Metro area coverage
  - Analysis methodology
  - Troubleshooting guide

Happy analyzing! 🏠📊
    """)

def main():
    """Main setup workflow"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║        HOUSING MARKET INVESTMENT ANALYSIS - SETUP WIZARD            ║
║                                                                      ║
║  CA to TX Migration & Emerging Markets Analysis (2024-2025)         ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Step 1: Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Step 2: Setup virtual environment
    print("\nVirtual environment setup...")
    print("Note: If you're already in a virtual environment, this step will be skipped.")
    if not setup_virtual_environment():
        print("\nContinuing without virtual environment...")
    
    # Step 3: Install dependencies
    print("\nAttempting to install dependencies...")
    print("If this fails, activate your virtual environment and run:")
    print("  pip install -r requirements.txt")
    
    install_deps = input("\nInstall dependencies now? (y/n): ")
    if install_deps.lower() == 'y':
        install_dependencies()
    
    # Step 4: Check API credentials
    check_api_credentials()
    
    # Step 5: Download data
    run_data_download()
    
    # Step 6: Optional BLS download
    run_bls_download()
    
    # Step 7: Print manual steps
    print_manual_steps()
    
    # Step 8: Print summary
    print_summary()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)
