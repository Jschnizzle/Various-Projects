# Predicting Alcoholism Using Various Characteristics

STATS 101C final project (UCLA, Fall 2023). A Kaggle-style classification task:
predict whether a patient is an alcoholic from 26 vital-sign and lifestyle
predictors, training on a more complete labeled dataset.

**Team:** Nikita Park, Jeremy Shiu, Ian Turner, Mingchen Wang, Josh Xu
**Result:** 73.38% test accuracy — 5th place overall, 4th within the lecture.

## Approach

- **EDA** — the classes are ~50/50, and no single predictor is strong on its own
  (hemoglobin alone reaches only ~64%).
- **Missing data** — nearly every predictor had missing values scattered roughly
  at random, so list-wise deletion wasn't viable. We compared Amelia, Hmisc
  (`aregImpute`), mice, and missForest; models trained on `aregImpute`'s output
  scored highest.
- **Models** — logistic-regression baselines (with stepwise AIC/BIC selection),
  then tree ensembles. **XGBoost** was best; the final model was tuned via
  bootstrap resampling and pruned to `max_depth = 2`.
- **Variable selection** — dropping weak predictors always lowered leaderboard
  accuracy, so the final model kept all predictors (a leaderboard-chasing choice;
  see the report's Discussion for how a real study would differ).

## Files

| File | Description |
| --- | --- |
| `Project File Clean.Rmd` | Cleaned, annotated analysis code (start here). |
| `Project File.Rmd` | Original working code, kept for reference. |
| `Final Project.pdf` | Full written report. |
| `Stats 101C Final Project Slides.pdf` | Presentation slides. |
| `TrainSAData2.csv` | Raw training data (70,000 × 27). |
| `TestSAData2NoY.csv` | Raw test data (30,000 × 26, response withheld). |
| `aregimpute_kaggle_train.RData` | Cached `aregImpute` fit (imputation is slow). |
| `prototype2.csv` / `prototype3.csv` / `prototype4.csv` | Kaggle submissions (BIC GLM, AIC GLM, XGBoost). |

## Running the code

Open `Project File Clean.Rmd` in RStudio and knit, or run the chunks in order.
It reads the two raw CSVs and the cached imputation object, and regenerates the
intermediate imputed datasets itself, so no other files are needed.

Required packages: `ggplot2`, `dplyr`, `VIM`, `Hmisc`, `Amelia`, `missForest`,
`MASS`, `class`, `xgboost`, `caret`, `DiagrammeR`.

The multiple-imputation and bootstrap-tuning steps are computationally heavy.
They are wrapped in `if (file.exists(...))` guards so the code loads a saved
result when present and only recomputes when it is missing — delete the
corresponding cache file to force a fresh run.

## Data note

The data comes from the course's public Kaggle competition and is included here
only for reproducibility of this class project.
