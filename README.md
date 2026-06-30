# Modeling Mega Events: Traffic During the 2028 Olympic Games

Stat 421 midterm project. This repository analyzes Los Angeles freeway traffic
around a real mega-event — **Super Bowl LVI (February 2022, SoFi Stadium)** — and
uses it as a proxy to reason about traffic impacts of the upcoming **2028 Los
Angeles Olympic Games**. The core question: *does a major event measurably change
freeway speeds, and at which hours of the day?*

Sensor data comes from the **Caltrans Performance Measurement System (PeMS),
District 7 (Los Angeles)**. Speeds during Super Bowl week are compared against
regular weeks using non-parametric **Wilcoxon rank-sum / Mann–Whitney** tests,
broken out by hour of day and by day of week (Friday and Sunday).

## Repository structure

```
midterm-repo/
├── README.md
├── .gitignore
├── analysis/                 # R analysis — the runnable bundle
│   ├── Traffic Presentation Code.Rmd      # main analysis (knit to PDF)
│   ├── compile_wilcoxon_results.R         # tidy p-value table + significance plot
│   ├── compile_wilcoxon_results_objectlabel_12h_ordered_v2.R  # effect sizes (U, z, r), chronological
│   ├── wilcox_runlist_template.R
│   ├── wilcox_runlist_with_pctdiff.R
│   ├── split_cleaned_speed.R              # utility: split a large CSV into <25 MB parts
│   ├── test_split.R
│   ├── extracted_wilcox_calls.csv         # input for the compile_* scripts
│   ├── Forecasting Presentation Code.ipynb
│   ├── traffic.csv                        # small input (full)
│   ├── cleaned_speed.csv                  # 5,000-row SAMPLE (see "Data" below)
│   ├── mann_whitney_results_min_friday.csv
│   └── mann_whitney_results_min_sunday.csv
├── results/                  # generated figures, result tables, result CSVs
│   ├── *.png
│   ├── wilcox_results*.csv
│   └── tables/*.html
├── python/
│   └── timeline_with_date_selector.py     # interactive Leaflet map (date + hour selector)
├── data/
│   ├── d07_text_meta_2023_12_22.txt       # PeMS District 7 sensor metadata
│   └── sample/                            # header + 1,000-row samples of the large CSVs
└── docs/
    ├── Modeling Mega Events_ Traffic During the 2028 Olymic Games.pptx
    ├── Documentation.xlsx
    ├── Olympics City List.xlsx
    └── World Cup City List.xlsx
```

## Data

The full dataset is **not** included — the raw and intermediate CSVs range from
hundreds of MB up to ~16 GB, well past GitHub's 100 MB per-file limit. Instead,
small samples (header + 1,000 rows) live in `data/sample/` so you can inspect the
schema of every stage of the pipeline.

Processing pipeline (each stage produced from the previous one):

```
merged_hour.csv   raw hourly PeMS export, headerless, many sparse columns
      ↓ (column naming)
Col_named.csv     same data with named columns
      ↓ (cleaning)
Cleaned.csv  →  Cleaned_speed.csv   speed-focused, analysis-ready
      ↓ (row slicing in the Rmd)
sb_week.csv (Super Bowl week)  +  after_sb.csv (regular weeks)
```

To work with the full data, download the corresponding station-hour export from
Caltrans PeMS (District 7) for February 2022 and regenerate `Cleaned_speed.csv`.

## Running the analysis

The main artifact is `analysis/Traffic Presentation Code.Rmd`.

1. Open the project in RStudio and set the working directory to `analysis/`
   (the Rmd reads its inputs by relative filename).
2. Install dependencies:
   ```r
   install.packages(c("readr","dplyr","tidyr","tibble","purrr","stringr",
                      "ggplot2","forcats","broom","knitr","kableExtra",
                      "hms","caret","randomForest"))
   ```
3. Knit to PDF, or run chunk by chunk.

The Wilcoxon helper scripts (`compile_wilcoxon_results*.R`) are run *after* the
Rmd has built its hourly subset objects in the R session — they evaluate the
calls listed in `extracted_wilcox_calls.csv` and write the result tables/plots.

### Note on the sample data

`analysis/cleaned_speed.csv` is a **5,000-row sample**, enough to load the data
and run the early/exploratory chunks. A few later chunks hard-code absolute row
indices against the full dataset (e.g. `sb_week <- df[401904:937775,]`); those
require the complete `Cleaned_speed.csv` and will produce empty slices on the
sample. Replace the sample with the full file to reproduce every result.

(The Rmd references the file in lowercase, `cleaned_speed.csv`. On case-sensitive
filesystems such as Linux, make sure the filename casing matches.)

## Methods

Speed distributions during the event window are compared to baseline weeks with
the **Wilcoxon rank-sum (Mann–Whitney U)** test — a non-parametric choice that
does not assume normally distributed speeds. Tests are run per hour of day, with
effect sizes (U, z, and r) reported alongside p-values, and results ordered
chronologically (12am → 11pm). Significance is summarized both as a starred
table and as a −log10(p) overview plot.
