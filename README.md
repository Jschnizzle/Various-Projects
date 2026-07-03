# Gridiron Football Analysis Project

A multiple linear regression study of what drives NFL regular-season wins. Using
four seasons of team data (2017–2020), the project models a team's win total as
a function of how it ranks league-wide in five performance categories, then
narrows that down to the factors that matter most.

## The question

Given where a team ranks (1 = best, 32 = worst) in a handful of offensive and
defensive efficiency categories, how well can we explain its number of regular
season wins, and which categories carry the most weight?

## Data

`football data.csv` contains one row per team-season across the 2017–2020 NFL
seasons (128 rows). Each row records the team's win total and its league ranking
in five categories:

| Column       | Meaning                                              |
|--------------|------------------------------------------------------|
| `wins`       | Regular-season wins (the response variable)          |
| `rypa`       | Rushing yards per attempt ranking (offense)          |
| `yppa`       | Passing yards per attempt ranking (offense)          |
| `t/o_margin` | Turnover margin ranking                              |
| `oppo.rypa`  | Opponent rushing yards per attempt ranking (defense) |
| `oppo.yppa`  | Opponent passing yards per attempt ranking (defense) |

Rankings run from 1 (best in the league) to 32 (worst), so a lower number is a
better result.

## Approach

The analysis fits a full linear model of wins on all five predictors, checks
regression diagnostics, and applies a power transformation to the response to
better satisfy the model assumptions. It then uses stepwise selection (forward
and backward, by both AIC and BIC), added-variable plots, and variance inflation
factors to assess each predictor's unique contribution and screen for
multicollinearity. A partial F-test compares the full model against a reduced
model built from the predictors that hold up across those checks — turnover
margin, passing offense, and passing defense.

## Files

- `nfl_wins_analysis.Rmd` — the full analysis, from data loading through final
  model diagnostics. Knit it to reproduce the report.
- `football data.csv` — the dataset the analysis reads.

## Running it

Open `nfl_wins_analysis.Rmd` in RStudio and knit, or run the chunks in order.
The code reads `football data.csv` from the working directory, so keep the two
files together. Two packages are required:

```r
install.packages(c("car", "MASS"))
```
