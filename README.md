# Modeling Men's World Cup Group-Stage Performance

**STAT 418 — Tools in Data Science · UCLA, Summer 2026 · Jeremy Shiu**

Three regression models of the same outcome — a national team's men's World Cup
group-stage campaign — fit side by side on a table built entirely with SQL joins
against the [datahub FIFA World Cup relational dataset](https://datahub.io/core/world-cup).
The fitted logistic model is then used to make a genuine out-of-sample forecast for the
2026 tournament.

| Model | Outcome | Question |
|---|---|---|
| **Poisson** | `points_std` (0–9 count) | *How many* points did they take? |
| **Logistic** | `advanced` (1 = out of the group) | *Did they qualify?* |
| **Ordinal** | `points_ord` (points as ranks) | *Where on the scale* did they land? |

All three share the same rows and the same pre-pruned predictor pool by design, so
their results are directly comparable.

---

## Headline results

- **Modeling table:** one row per team per group-stage campaign, **men's only, 1970+**
  (366 campaigns across 14 tournaments), built via `sqldf` from 38 raw CSVs.
- **Out-of-sample validation:** chronological split — fit on 1970–2006 (239 campaigns),
  scored on 2010–2022 (127 campaigns). The split is chronological rather than random
  because that is the question a forecaster actually faces, and it guarantees no
  test-year information reaches the fit. The specification is *pre-specified*, so the
  split arbitrates prediction only, never variable selection.
- **2026 forward benchmark:** the model scores the 2026 field, which no part of the
  training data has seen. See `results/2026 FORWARD RESULTS.txt`.

Full writeup: **`paper/main.pdf`**. Presentation: **`slides/`**.

---

## Repository layout

```
.
├── R Code/                 # analysis pipeline (see below)
├── Python Code/            # data downloaders + 2026 field scraper, with their URL lists
├── worldcup_data/          # datahub World Cup relational dataset (38 CSVs) — primary source
├── premierleague_data/     # Football-Data (UK) season CSVs, 1993/94–2025/26
├── spanishlaliga_data/     #   "
├── germanbundesliga_data/  #   "
├── frenchligue1_data/      #   "
├── mens_groupstage_1970on.csv   # built modeling table (output of 01_data_transformation.R)
├── mens_groupstage_2026.csv     # 2026 field, for the forward benchmark
├── transformed_data.csv         # earlier export of the modeling table
├── transformed_data_all.csv     #   "  , men's + women's backup
├── figures/                # all generated figures (scripts write here)
├── paper/                  # main.tex + compiled main.pdf
├── slides/                 # presentation deck
├── tableau/                # Tableau workbooks used for EDA
├── results/                # model output logs
└── docs/                   # DATA_PIPELINE.md — how the raw data was assembled
```

**Working directory is the repository root.** Every script resolves its paths relative
to the repo root, not to `R Code/` — e.g. `read.csv("mens_groupstage_1970on.csv")`,
`data_dir <- "worldcup_data"`, and figures written to `figures/`. Run scripts as:

```r
setwd("<repo root>")
source("R Code/01_data_transformation.R")
```

---

## Pipeline

| Script | Role |
|---|---|
| `R Code/01_data_transformation.R` | **All data work, no modeling.** Reads the raw `worldcup_data/` CSVs, runs every `sqldf` join / aggregation / filter, assembles the modeling table, recomputes a consistent scoring rule, cuts to 1970+, writes `mens_groupstage_1970on.csv`. Only needs re-running when the raw data changes. |
| `R Code/02_model_fitting.R` | **All modeling, no data work.** Loads the built table and fits the Poisson, logistic, and ordinal models. |
| `R Code/logit_mens_groupstage_advance.R` | Standalone logistic model, carried further than the copy in `02`: adds the train/test split, the ROC, and the **2026 forward benchmark** (§8, §8b). |
| `R Code/poisson_mens_groupstage.R`, `poisson_mens_groupstage_model.R`, `ordinal_mens_groupstage_points.R` | The original single-model scripts that `01`/`02` were consolidated from. Kept because they carry the long-form derivations and commentary for each family. |
| `R Code/fig_roc_train_test.R` | Draws `figures/roc_train_test_split.png` (Figure 7 in the paper). |
| `R Code/fig_2026_ranked_cut.R` | Draws the 2026 ranked-probability figures. |
| `R Code/worldcupdata_processing.R`, `filter_transformed_mens.R` | Earlier processing pass; produced `transformed_data.csv`. Superseded by `01_data_transformation.R`. |
| `R Code/england_pl_scoring_analysis.R` | Side analysis: England's group-stage performance vs. Premier League scoring trends. |
| `Python Code/download_worldcup.py`, `download_premierleague.py`, `download_leagues.py` | Fetch the raw CSVs from the URL lists sitting alongside them. |
| `Python Code/scrape_worldcup_2026.py` | Builds `mens_groupstage_2026.csv` — the 2026 field. |

R packages: `sqldf` (required), plus optional `sandwich`, `lmtest`, `pROC`,
`ResourceSelection`, `logistf`, `ordinal` / `MASS`, `brant`, `VGAM` — each block is
skipped with a message if the package is absent, except the ordinal engine, which
needs `ordinal` or `MASS`.

---

## Three modeling decisions worth knowing

**1. Men's-only, with the filter bug fixed at the source.** An earlier pipeline filtered
with `LIKE '%Men''s%'`, which SQLite matches *case-insensitively* — so `"FIFA WOmen's"`
passed too, silently mixing women's tournaments into the table. The current filter is
`LIKE '%FIFA Men''s%'` (verified: 490 men's rows, zero women's leakage). `transformed_data.csv`
predates the fix; `mens_groupstage_1970on.csv` does not.

**2. 1970 onward only.** Booking data begins in 1970, and from 1970 on every team plays
exactly three group games — the outcome denominator is fixed, so no exposure offset is
needed and points are directly comparable across tournaments.

**3. A single era-invariant scoring rule: `points_std = 3·wins + draws`.** The raw
`points` column awards 2 for a win before 1994 and 3 after, which changes both the scale
(max 6 vs. 9) and the value of a draw relative to a win. Recomputing 3-1-0 for all years
removes the artifact.

The dataset's own `advanced` flag is used rather than re-deriving qualification from goal
difference: early tournaments settled level teams by **playoff**, not GD (1954 West Germany
advanced over Turkey on a worse GD; 1958 USSR beat England in a playoff), and later ones
advanced the best third-placed teams. The stored column records the true historical outcome
including those cases; a GD rule would misclassify exactly the interesting edges.

---

## Data sources

- **World Cup:** [datahub.io/core/world-cup](https://datahub.io/core/world-cup) — relational
  dataset of tournaments, teams, squads, players, matches, goals, bookings, managers, referees.
- **Domestic leagues:** [Football-Data.co.uk](https://www.football-data.co.uk/) via the
  datahub mirrors, one row per match, 1993/94–present.

Both are redistributed here in full; no file exceeds 5 MB.
