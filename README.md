# Geostatistical Analysis of PM10 Air Pollution — Athens, Greece

Spatial-statistics project (UCLA STAT C173) modeling and interpolating **PM10
particulate-matter concentrations** across air-quality monitoring stations in
Athens, using classical geostatistics in R.

Author: Jeremy Shiu · March 2025

## Overview

Starting from ~1.7 million rows of hourly station readings, the data is reduced
to one record per monitoring station (65 stations) and analyzed to (1)
characterize the spatial correlation structure of PM10 and (2) predict PM10 at
unmonitored locations across the study area.

The workflow, in `stat_c173_project.Rmd`:

- **Data preparation** — deduplicate the raw hourly Athens dataset to one row per
  station and retain coordinates plus wind (U/V), temperature, relative humidity,
  PM10, and ozone.
- **Exploratory / non-spatial analysis** — summary statistics, histograms, ECDFs,
  a station-location scatter plot, and a PM10 bubble plot.
- **Spatial structure** — h-scatterplots at 5/10/20 km lag distances; empirical
  semivariograms (classical and robust Cressie–Hawkins estimators); fitting of
  exponential, spherical, and Gaussian models via ordinary and weighted least
  squares.
- **Interpolation & prediction** — inverse-distance weighting (IDW); ordinary,
  universal, and simple kriging; universal kriging with meteorological covariates
  (temperature, humidity, wind). Models are compared with leave-one-out
  cross-validation (ME / MSE / RMSE).

## Repository contents

```
.
├── stat_c173_project.Rmd        # full analysis (knits to PDF)
├── final_data.csv               # 65 monitoring stations — the working dataset
├── data/
│   └── sample/
│       └── athens_data.sample.csv  # header + 1000 rows of the raw hourly data
├── .gitignore
└── README.md
```

## Data note

The raw hourly datasets are too large for GitHub (Athens ~439 MB, Ancona
~108 MB, Zaragoza ~54 MB) and are **not stored in this repo**. Only Athens is
used in the analysis; the Ancona and Zaragoza files were alternate candidate
cities that the final analysis does not use.

`final_data.csv` (the deduplicated 65-station dataset) is committed in full, so
every analysis, plotting, semivariogram, and kriging step runs directly from the
repo. The first "Original data" chunk reads the included
`data/sample/athens_data.sample.csv` for demonstration; to regenerate the real
`final_data.csv` you need the full `athens_data.csv`.

## Running

Open `stat_c173_project.Rmd` in RStudio and knit, or run the chunks in order.
Required R packages: `dplyr`, `readr`, `ggplot2`, `tidyr`, `gridExtra`,
`geosphere`, `gstat`, `sp`, `scales`.
