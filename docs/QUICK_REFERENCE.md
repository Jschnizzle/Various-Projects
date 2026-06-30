# Housing Market Data Analysis - Quick Reference Guide

## 🚀 Quick Start (3 Commands)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download all data
python housing_data_downloader.py

# 3. Verify data quality
python verify_data.py
```

## 📋 All Available Scripts

### 1. `setup.py` - Complete Setup Wizard

**What it does:** Interactive setup - installs dependencies and downloads data

```bash
python setup.py
```

**Use when:**

- First time setup
- Want guided installation
- Setting up on new machine

---

### 2. `housing_data_downloader.py` - Main Data Downloader

**What it does:** Downloads Zillow, Census, FHFA, and Freddie Mac data automatically

```bash
python housing_data_downloader.py
```

**Downloads:**

- ✅ Zillow ZHVI (home values) - Metro, County, ZIP
- ✅ Zillow ZORI (rental index)
- ✅ Inventory metrics
- ✅ Days on market
- ✅ Sales counts
- ✅ FHFA House Price Index
- ✅ Freddie Mac mortgage rates
- ✅ Census population estimates
- ✅ Building permits

**Output:** `housing_market_data/` directory with organized subdirectories

---

### 3. `bls_api_downloader.py` - BLS Employment/Wage Data

**What it does:** Downloads Bureau of Labor Statistics data via API

```bash
# First, set your API key (get free at https://www.bls.gov/developers/)
export BLS_API_KEY='your-key-here'

# Then run
python bls_api_downloader.py
```

**Downloads:**

- Employment data by metro
- Wage data by metro
- State-level employment
- Unemployment rates

**Alternative:** Manual download from <https://www.bls.gov/data/>

---

### 4. `verify_data.py` - Data Quality Checker

**What it does:** Verifies all downloaded data for completeness and quality

```bash
python verify_data.py
```

**Checks:**

- File existence
- Data completeness
- Missing values
- Date ranges
- File sizes

**Output:**

- Console report
- `housing_market_data/verification_report.json`

---

### 5. `data_cleaner.py` - Data Standardization

**What it does:** Standardizes and merges raw data into a master dataset

```bash
python data_cleaner.py
```

### 6. `feature_engineer.py` - Investment Metrics

**What it does:** Calculates rental yields, price momentum, and other investment metrics

```bash
python feature_engineer.py
```

### 7. State Cleaners (`ca_county_cleaner.py`, `tx_county_cleaner.py`)

**What it does:** Creates state-specific county level master datasets

```bash
python ca_county_cleaner.py
python tx_county_cleaner.py
```

---

## 📂 Directory Structure

```
housing-market-analysis/
│
├── Scripts
│   ├── setup.py                      # Setup wizard
│   ├── housing_data_downloader.py    # Main downloader
│   ├── bls_api_downloader.py         # BLS API downloader
│   ├── verify_data.py                # Data verification
│   ├── data_cleaner.py               # Data standardization
│   ├── feature_engineer.py           # Feature engineering
│   ├── ca_county_cleaner.py          # CA county cleaner
│   └── tx_county_cleaner.py          # TX county cleaner
│
├── Documentation
│   ├── README.md                     # Full documentation
│   └── QUICK_REFERENCE.md            # This file
│
├── Configuration
│   └── requirements.txt              # Python dependencies
│
└── Data (created after download)
    └── housing_market_data/
        ├── zillow/                   # Zillow datasets
        ├── census/                   # Census Bureau data
        ├── bls/                      # BLS data
        ├── other/                    # FHFA, Freddie Mac
        ├── metro_reference.csv       # Metro area codes
        ├── download_metadata.json    # Download log
        └── verification_report.json  # Verification results
```

## 🎯 Common Workflows

### First-Time Setup

```bash
# Option 1: Guided setup (recommended)
python setup.py

# Option 2: Manual setup
pip install -r requirements.txt
python housing_data_downloader.py
python verify_data.py
```

### Update Existing Data

```bash
# Re-download everything
python housing_data_downloader.py

# Verify updates
python verify_data.py
```

### BLS Data Only

```bash
# Set API key
export BLS_API_KEY='your-key'

# Download
python bls_api_downloader.py
```

### Check Data Status

```bash
# Quick check
python verify_data.py

# Manual check
ls -lh housing_market_data/*/
```

## 🔧 Troubleshooting

### Download Failed

```bash
# Check internet connection
ping zillow.com

# Try specific dataset
# Edit housing_data_downloader.py and comment out other downloads

# Check disk space
df -h
```

### Missing Dependencies

```bash
# Reinstall
pip install -r requirements.txt --upgrade

# Install specific package
pip install pandas requests
```

### API Rate Limits (BLS)

- **Without API key:** 25 requests/day
- **With API key:** 500 requests/day
- **Solution:** Register at <https://www.bls.gov/developers/>

### Large File Downloads

- Expected total size: 500MB - 1GB
- Slow connection? Download overnight
- Use verification script to check what's missing

## 📊 Key Metros Included

### California (Outbound)

- Los Angeles (31080)
- San Francisco (41860)
- San Diego (41740)
- San Jose (41940)
- Sacramento (40900)

### Texas (Inbound)

- Dallas-Fort Worth (19100)
- Houston (26420)
- Austin (12420)
- San Antonio (41700)

### Emerging Hot Markets

- Phoenix, AZ (38060) - Only major metro with positive migration 2024
- Charlotte, NC (16740)
- Raleigh, NC (39580)
- Nashville, TN (34980)
- Greenville, SC (24860) - Highest migration rate +3.6%
- Charleston, SC (16700)
- Buffalo, NY (15380) - #1 Zillow hot market 2025
- Virginia Beach, VA (47260)

## 📈 Data Sources & Update Frequency

| Source | Frequency | Manual? |
|--------|-----------|---------|
| Zillow | Monthly | No - Automated |
| Census Population | Annual | No - Automated |
| Census Migration | Annual | Yes - Manual |
| BLS (API) | Monthly | No - With API key |
| BLS (Manual) | Quarterly | Yes - If no API |
| FHFA | Quarterly | No - Automated |
| Freddie Mac | Weekly | No - Automated |

## 🔄 Recommended Update Schedule

```bash
# Monthly (when Zillow updates)
python housing_data_downloader.py
python verify_data.py

# Quarterly (for BLS updates)
python bls_api_downloader.py

# Annually (for Census migration)
# Manual download from Census website
```

## 💾 Disk Space Requirements

- **Minimum (core datasets):** 200MB
- **Recommended (with BLS):** 500MB
- **Full (all optional data):** 1GB
- **Working space:** 2GB (for processing)

## 🆘 Getting Help

### Check Verification Report

```bash
python verify_data.py
cat housing_market_data/verification_report.json
```

### Check Download Log

```bash
cat housing_market_data/download_metadata.json
```

### List All Downloaded Files

```bash
find housing_market_data -name "*.csv" -type f | wc -l
```

### Check File Sizes

```bash
du -sh housing_market_data/*/
```

## 🎓 Next Steps After Data Download

1. **Data Cleaning** (Run `data_cleaner.py`)
   - Standardize metro codes
   - Handle missing values
   - Align time periods

2. **Feature Engineering** (Run `feature_engineer.py`)
   - Calculate migration rates
   - Compute affordability indices
   - Create momentum indicators

3. **Analysis**
   - Correlation analysis
   - Market scoring
   - ROI projections

4. **Visualization**
   - Interactive dashboards
   - Metro comparisons
   - Investment reports

## 📚 Resources

- **Full Documentation:** See README.md
- **Data Sources:**
  - Zillow: <https://www.zillow.com/research/data/>
  - Census: <https://www.census.gov/data.html>
  - BLS: <https://www.bls.gov/data/>
  - FHFA: <https://www.fhfa.gov/data>

- **API Documentation:**
  - BLS API: <https://www.bls.gov/developers/>

---

**Last Updated:** November 2025
**For:** 2026 Housing Investment Analysis
