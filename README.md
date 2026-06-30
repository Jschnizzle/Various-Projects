# California Housing Market & Migration Investment Analysis

STATS 421 final project on California county-level gentrification and migration
patterns, extended into a county investment-scoring pipeline. This repo
combines two related pieces of work:

1. **`analysis/`** — the original course notebooks: LODES worker/job data,
   IRS migration flows, and CAR housing-affordability indices, merged into a
   per-county dataset and analyzed for population/income migration trends.
2. **`investment-pipeline/`** — a follow-on Python toolkit that pulls Zillow,
   Census, BLS, and FHFA data to score and rank CA counties as investment
   opportunities, building on the same migration findings.

> [!NOTE]
> Large raw inputs have been replaced with small samples so the code is
> browsable and runnable end-to-end on a subset of data. See "Sampled /
> excluded data" below for what to download separately for full results.

## Structure

```
.
├── analysis/                  # Course notebooks + the data they read directly
│   ├── CollectionAndAnalysis.ipynb        # Main pipeline: LODES + migration + housing → results/ca_merged.csv
│   ├── Final Project Code.ipynb           # CAR housing-affordability regression → results/car_recent_dfs_master.csv
│   ├── Revised_migration_processing.ipynb # IRS inflow/outflow → results/{inflow,outflow}_total.csv, map
│   ├── ca_rac_S000_JT00_*.csv.gz          # SAMPLES (header + 1000 rows) of LODES residence-area data
│   ├── ca_wac_S000_JT00_*.csv.gz          # SAMPLES of LODES workplace-area data
│   ├── *HistoricalData*.csv, all-geocodes-v2020.xlsx, county{in,out}flow2122.csv
│   └── Data/                              # All 5 years of IRS county in/outflow CSVs
│       (CollectionAndAnalysis.ipynb expects this subfolder via `./Data`;
│        Revised_migration_processing.ipynb reads the 2122 pair bare from
│        the analysis/ folder itself — both layouts are kept so neither
│        notebook needs edits.)
├── investment-pipeline/       # Standalone scoring/cleaning toolkit
│   ├── *.py                   # Downloaders, cleaners, scorers, plotters (see docs/investment-pipeline-README.md)
│   ├── housing_market_prediction.ipynb
│   ├── california-counties.geojson
│   ├── requirements.txt, run.sh, setup.py
│   └── housing_market_data/   # Zillow/Census/BLS/FHFA inputs (SAMPLED — see below)
├── results/                   # Notebook outputs
│   ├── ca_merged.csv          # Final per-county merged dataset (output of CollectionAndAnalysis.ipynb)
│   ├── car_recent_dfs_master.csv
│   ├── inflow_total.csv / outflow_total.csv
│   ├── reduced_inflow.csv / reduced_outflow.csv   # earlier, superseded intermediate (kept for provenance)
│   └── visualizations/        # 15 PNGs from the investment-pipeline scoring/mapping scripts
└── docs/
    ├── STATS 421 Final - Gentrification.pptx / .pdf   # final presentation (two different exports)
    ├── Tables of Data.xlsx
    ├── housing_market_investment_analysis_2026.md     # write-up of investment-pipeline findings
    ├── DATA_RELATIONSHIPS.md, DEV_LOG.md, DIRECTORY_STRUCTURE.txt,
    │   PACKAGE_SUMMARY.md, QUICK_REFERENCE.md, MAC_INSTALLATION.md, START_HERE.md
    ├── investment-pipeline-README.md                   # original toolkit README (renamed to avoid clashing with this file)
    └── County Sales & Price Statistics (Public).xlsx, Historical Housing
        Affordability Index.xlsx, MedianTimeonMarket....xlsx,
        PercentChangeofSales....xlsx                    # raw source spreadsheets the analysis/ CSVs were exported from (not read by code directly)
```

## Sampled / excluded data

| What | Original size | What's here | Full source |
|---|---|---|---|
| `ca_rac_S000_JT00_*.csv` / `ca_wac_S000_JT00_*.csv` (LODES, 2018–2022) | ~370 MB total | header + 1000-row `.csv.gz` samples in `analysis/` | [LEHD LODES](https://lehd.ces.census.gov/data/lodes/LODES8/ca/) — residence (RAC) and workplace (WAC) area characteristics, CA, `S000_JT00`, 2018–2022 |
| `housing_market_data/zillow/zhvi_county.csv`, `zhvi_metro.csv` | 13 MB / 4.3 MB | 1000-row samples | [Zillow Research Data](https://www.zillow.com/research/data/) |
| `housing_market_data/other/fhfa_hpi_metro.csv` | 11.7 MB | 1000-row sample | [FHFA House Price Index](https://www.fhfa.gov/data/hpi) |
| `housing_market_data/census/population_estimates.csv` | 1.4 MB | 1000-row sample | U.S. Census Bureau population estimates |
| `housing_market_data/processed/zillow_debug.csv` | 14.9 MB | 1000-row sample | regenerable debug output of `data_cleaner.py` |
| `housing_market_data/bls/api_key.txt` | — | **excluded entirely** | this file held a real BLS API key; it is gitignored. Recreate it locally with your own key (`housing_market_data/bls/api_key.txt`, 32-char key, no newline) before running `bls_api_downloader.py` |
| `housing_market_data/census/migration_flows.csv` | — | not present in the source folder either (per `DEV_LOG.md`, requires manual download) | Census migration flows |

Everything else (the housing-affordability/median-price/DOM/UII CSVs, geocodes,
all 10 years of IRS county in/outflow data, BLS employment/wage CSVs, Zillow
ZORI/inventory/days-on-market/sales-count/median-list-price, metro reference,
metadata/verification JSON) is small enough (each well under 2 MB) to include
in full.

## Notes

- `Zipped Files/` (the original `.gz` archives of the rac/wac CSVs) was
  excluded — verified byte-for-byte identical to the decompressed CSVs once
  unzipped, so it added nothing but ~83 MB of duplication.
- The original top-level `ca_merged` / `ca_merged.txt` files were identical
  copies of `Data/ca_merged.csv`; only the one canonical copy is kept, in
  `results/ca_merged.csv`.
- `CollectionAndAnalysis.ipynb` also expects a `CENSUS_API_KEY` environment
  variable (loaded via `python-dotenv` from `~/Documents/.env` in the
  original) for its Census API calls.
- No file in this repo exceeds ~19 MB (the pptx); GitHub's hard limit is
  100 MB and it warns above 50 MB.
