# Modeling Mega Events: Traffic During the 2028 Olympic Games

**UCLA STATS 421 midterm project — Group 6.** Chris, Nils, Sungjin, Jeremy Shiu, Dan, Hochan.

This repository analyzes Los Angeles freeway traffic around a real mega-event —
**Super Bowl LVI (Sunday, February 13, 2022, SoFi Stadium)** — and uses it as a proxy
to reason about traffic impacts of the upcoming **2028 Los Angeles Olympic Games**.
The core question: *does a major event measurably change freeway conditions, and at
which hours of the day?*

Sensor data comes from the **Caltrans Performance Measurement System (PeMS),
District 7 (Los Angeles)**.

> **What is actually measured: `Avg Occupancy`.** Every Wilcoxon / Mann-Whitney test in
> this repository compares **average detector occupancy** between event and baseline
> windows — not average speed. Speed is used for exploratory plots and for the
> interactive map, but no reported hypothesis test is a test of speed. (Earlier
> revisions of this README described the tests as comparing speed distributions. That
> was wrong; corrected 2026-08-04.)

## Design

**Event vs. baseline.** Super Bowl Sunday (02/13/2022) is compared against **two pooled
baseline Sundays** 2–3 weeks later (02/27 and 03/06).

**Friday as a placebo day.** The identical procedure is run on Friday 02/11/2022 — a
*non-event* day during Super Bowl week — against two pooled regular Fridays (02/25 and
03/04). This is a control on the method itself: a large effect on Sunday alongside a
small one on Friday is stronger evidence than Sunday alone.

**Spatial rings.** Stations are grouped by distance from SoFi Stadium — **R1 ≤ 3 miles,
R2 ≤ 5 miles, R3 ≤ 10 miles** — so the effect can be checked for decay with distance.

**Test.** Wilcoxon rank-sum (Mann-Whitney U), run per hour of day. Non-parametric
because the underlying distributions are not normal. Effect sizes (U, z, and r) are
reported alongside p-values, with results ordered chronologically (12am → 11pm), and
significance summarized both as a starred table and as a −log10(p) overview plot.

**Headline result.** A large **20–30%** effect on Sunday evening, during and after the
event; a smaller **3–7%** effect on ordinary rush-hour traffic.

**Forecasting extension.** Super Bowl LVI drew roughly 130k visitors; Paris 2024 drew an
estimated 300–400k daily. Against a baseline of ~100k normal tourism, that scales to
**30–75% more total visitors (1.5–2× event-specific)** for a 2028 Olympic scenario.
Host-city reference tables for past Olympics and World Cups are in `docs/`.

## Repository structure

```
.
├── README.md
├── .gitignore
├── analysis/                 # R analysis — the runnable bundle
│   ├── Traffic Presentation Code.Rmd      # main analysis (knit to PDF)
│   ├── compile_wilcoxon_results.R         # tidy p-value table + significance plot
│   ├── compile_wilcoxon_results_objectlabel_12h_ordered_v2.R  # effect sizes (U, z, r), chronological
│   ├── wilcox_runlist_template.R
│   ├── wilcox_runlist_with_pctdiff.R      # per-hour runlist + % difference in means
│   ├── split_cleaned_speed.R              # utility: split a large CSV into <25 MB parts
│   ├── test_split.R
│   ├── extracted_wilcox_calls.csv         # input for the compile_* scripts
│   ├── Forecasting Presentation Code.ipynb
│   ├── traffic.csv                        # small input (full)
│   ├── mann_whitney_results_min_friday.csv
│   └── mann_whitney_results_min_sunday.csv
├── results/                  # generated figures, result tables, result CSVs
│   ├── *.png
│   ├── wilcox_results*.csv
│   └── tables/*.html
├── python/
│   └── timeline_with_date_selector.py     # interactive Leaflet map (date + hour selector)
├── data/
│   ├── d07_text_meta_2023_12_22.txt       # PeMS District 7 sensor metadata (4,889 stations)
│   └── sample/                            # header + 1,000-row samples of the large CSVs
└── docs/
    ├── Modeling Mega Events_ Traffic During the 2028 Olymic Games.pptx
    ├── Documentation.xlsx                 # PeMS station-hour + metadata field definitions
    ├── Olympics City List.xlsx            # 18 past Olympic host cities
    └── World Cup City List.xlsx           # 89 past World Cup host cities
```

## Data

The full dataset is **not** included — raw and intermediate CSVs range from hundreds of
MB up to ~16 GB, well past GitHub's 100 MB per-file limit. Small samples (header +
1,000 rows) live in `data/sample/` so the schema of every pipeline stage can be
inspected.

Processing pipeline (each stage produced from the previous one):

```
merged_hour.csv   raw hourly PeMS export, headerless, many sparse columns
      ↓ (column naming)
Col_named.csv     same data with named columns
      ↓ (cleaning)
Cleaned.csv  →  Cleaned_speed.csv   analysis-ready
      ↓ (row slicing in the Rmd)
sb_week.csv (Super Bowl week)  +  after_sb.csv (baseline weeks)
```

To reproduce, download the station-hour export from Caltrans PeMS (District 7) for
February–March 2022 and regenerate `Cleaned_speed.csv`.

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

The Wilcoxon helper scripts (`compile_wilcoxon_results*.R`) are run *after* the Rmd has
built its hourly subset objects in the session — they evaluate the calls listed in
`extracted_wilcox_calls.csv` and write the result tables and plots.

## Known limitations

These are recorded so anyone reading the repo knows where the soft spots are. The
analysis is left as submitted.

- **`analysis/cleaned_speed.csv` is not in the repository.** The Rmd reads it by that
  name, and `.gitignore` whitelists it, but the file was never committed. Use
  `data/sample/Cleaned_speed.sample.csv` to inspect the schema, or supply the full file
  to reproduce results. Note the case difference (`cleaned_` vs `Cleaned_`) matters on
  case-sensitive filesystems.
- **Some chunks hard-code absolute row indices** against the full dataset (e.g.
  `sb_week <- df[401904:937775,]`). These will produce empty slices on any subset and
  break if the input changes.
- **`wilcox_runlist_with_pctdiff.R` always writes `mann_whitney_results_min_friday.csv`**
  and `mann_whitney_results_friday.png`, regardless of which day's subsets are in the
  session. The Rmd sources it a second time for the Sunday section and then reads
  `mann_whitney_results_min_sunday.csv`, which nothing in the repo writes. **Treat the
  checked-in Sunday CSV as unverified provenance** until the script is parameterized by
  day and re-run.
- **The runlist covers 9 of 24 hours** — 8am, 9am, 10am, 3pm, 5pm, 6pm, 7pm, 8pm, 9pm.
  The remaining hours are present but commented out.
- **Two parallel result sets exist** with different magnitudes: the 24-hour tables in
  `results/` and the 9-hour tables in `analysis/`. Which is canonical is not recorded.
- **No environment snapshot** (`renv.lock` / `sessionInfo()`) was captured.
