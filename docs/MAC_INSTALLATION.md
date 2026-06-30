# 🍎 Mac Installation Guide - Housing Market Analysis

## 📥 Download the Files

You have **two options**:

### Option 1: Download Everything (Recommended)

Download this single file:

- [housing_market_analysis.tar.gz](computer:///mnt/user-data/outputs/housing_market_analysis.tar.gz) (33KB)

Then extract it:

```bash
cd ~/Downloads
tar -xzf housing_market_analysis.tar.gz
cd housing_market_analysis
```

### Option 2: Download Individual Files

Download each file separately from the outputs folder and put them in a directory.

## 🚀 Quick Setup on Mac

### Step 1: Create Project Directory

```bash
mkdir -p ~/housing-market-analysis
cd ~/housing-market-analysis
```

### Step 2: Extract Files (if using tar.gz)

```bash
# If you downloaded the tar.gz
tar -xzf ~/Downloads/housing_market_analysis.tar.gz
```

### Step 3: Check Python Version

```bash
python3 --version
```

You need Python 3.8 or higher. Most Macs with recent macOS have this.

### Step 4: Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 6: Make Scripts Executable

```bash
chmod +x run.sh
```

## ▶️ Start Downloading Data

### Quick Start (Guided Setup)

```bash
python setup.py
```

### Or Manual Steps

```bash
# Download data
python housing_data_downloader.py

# Verify quality
python verify_data.py

# Clean and Merge
python data_cleaner.py
python ca_county_cleaner.py
python tx_county_cleaner.py

# Feature Engineering
python feature_engineer.py
```

### Or Use the Bash Wrapper

```bash
./run.sh all
```

## 📁 Your Directory Structure

After setup, you'll have:

```text
~/housing-market-analysis/
├── Scripts
│   ├── housing_data_downloader.py
│   ├── bls_api_downloader.py
│   ├── verify_data.py
│   └── setup.py
├── run.sh
├── requirements.txt
├── Documentation
│   ├── START_HERE.md
│   ├── README.md
│   ├── QUICK_REFERENCE.md
│   └── PACKAGE_SUMMARY.md
└── housing_market_data/  (created after first download)
    ├── zillow/
    ├── census/
    ├── bls/
    └── other/
```

## 🔧 Troubleshooting

### "python: command not found"

Use `python3` instead:

```bash
python3 setup.py
```

### "pip: command not found"

```bash
python3 -m pip install -r requirements.txt
```

### Permission Issues

```bash
chmod +x run.sh
chmod +x *.py
```

### SSL Certificate Errors

```bash
# Install certificates (if needed)
/Applications/Python\ 3.*/Install\ Certificates.command
```

## 🎯 What to Run First

1. **Read the documentation:**

   ```bash
   cat START_HERE.md
   ```

2. **Run the setup wizard:**

   ```bash
   python3 setup.py
   ```

   This will guide you through everything!

3. **Or download data directly:**

   ```bash
   pip install -r requirements.txt
   python3 housing_data_downloader.py
   python3 verify_data.py
   ```

## 💡 Mac-Specific Tips

### Use Your Favorite Terminal

- Terminal.app (built-in)
- iTerm2 (popular alternative)
- VS Code integrated terminal

### Check What's Downloaded

```bash
# See all files
ls -lh housing_market_data/*/

# Check total size
du -sh housing_market_data/

# Count CSV files
find housing_market_data -name "*.csv" | wc -l
```

### Quick Commands (bash wrapper)

```bash
./run.sh status      # Check what you have
./run.sh download    # Download data
./run.sh verify      # Check quality
./run.sh all         # Download + verify
./run.sh help        # See all commands
```

## 📊 Expected Download Size

- Scripts: ~100KB
- Data: ~500MB - 1GB
- Total disk space needed: ~2GB (for processing)

## ⏱️ Expected Time

- Setup: 2-5 minutes
- Download: 5-15 minutes (depends on internet speed)
- Verification: 1-2 minutes

## 🔐 Optional: BLS API Key

For full employment/wage data:

1. Register (free): <https://www.bls.gov/developers/>
2. Get your API key
3. Set environment variable:

   ```bash
   export BLS_API_KEY='your-key-here'
   ```

4. Or save to file:

   ```bash
   echo 'your-key-here' > housing_market_data/bls/api_key.txt
   ```

## 📚 Next Steps After Installation

1. ✅ Install dependencies
2. ✅ Download data
3. ✅ Verify quality
4. 🔄 Read documentation
5. 🔄 Explore the data
6. 🔄 Start analysis!

## 🆘 Need Help?

Check these files in order:

1. `START_HERE.md` - Quick start
2. `QUICK_REFERENCE.md` - Command reference
3. `README.md` - Full documentation
4. `PACKAGE_SUMMARY.md` - Complete overview

Or run:

```bash
./run.sh help
python3 setup.py  # Interactive help
```

## 🎉 You're Ready

Once installed, your first command should be:

```bash
python3 housing_data_downloader.py
```

Then verify with:

```bash
python3 verify_data.py
```

Happy analyzing! 📊🏠

---

**Note:** All commands use `python3` for Mac compatibility. If `python` works on your system, you can use that instead.
