rm( list = ls() )

# =============================================================================
# poisson_mens_groupstage_model.R
# -----------------------------------------------------------------------------
# MODEL-ONLY version. Loads the already-built modeling table from
# `mens_groupstage_1970on.csv` and runs the Poisson model selection, fit,
# overall-fit measures, clustered SEs, and diagnostics.
#
# The data-processing pipeline (reading the 8 raw worldcup_data/ CSVs, the
# men's/group-stage filters, all predictor aggregations, the points_std
# recompute, the 1970+ cut) lives in `poisson_mens_groupstage.R` and only needs
# to be re-run when the underlying data changes. This script assumes that table
# already exists and just does the modeling.
#
# OUTCOME:  points_std  (0-9 count, one row = one team's group-stage campaign)
# =============================================================================


# ---- Setup ------------------------------------------------------------------
# Optional packages for team-clustered SEs. The core fit and selection run
# without them; the clustered-SE block is skipped with a message if absent.
has_sandwich <- requireNamespace("sandwich", quietly = TRUE)   # clustered vcov
has_lmtest   <- requireNamespace("lmtest",   quietly = TRUE)   # coeftest


# =============================================================================
# 1. LOAD THE PRE-BUILT MODELING TABLE
# -----------------------------------------------------------------------------
#   Built by poisson_mens_groupstage.R: men's, group stage, 1970+, with
#   points_std already computed and predictors already aggregated.
# =============================================================================
model_df <- read.csv("mens_groupstage_1970on.csv", stringsAsFactors = FALSE)

# ---- Drop the OFC / confOTHER cell (perfect separation in the logit sibling) -
#   `conf == "OTHER"` is the collapsed OFC (Oceania) bucket: exactly 2 rows,
#   NEW ZEALAND 1982 and NEW ZEALAND 2010 -- the only Oceania entries in the
#   1970+ men's data, both with advanced = 0. That cell is perfectly separated
#   in the logistic model (confOTHER coefficient -> -Inf); we drop those 2 rows
#   here too (368 -> 366) so all sibling models share the SAME row set and no
#   near-empty confederation level is estimated. (Done across all model scripts.)
model_df <- subset(model_df, confederation_code != "OFC")

# ---- Restore factor structure that CSV storage flattens ---------------------
#   `conf` was written as plain text; re-establish it as a factor with UEFA as
#   the baseline so the coefficients read the same way as in the build script.
#   With the OFC rows gone, factor() no longer carries an "OTHER" level.
model_df$conf <- relevel(factor(model_df$conf), ref = "UEFA")

# ---- Sanity checks on the loaded table --------------------------------------
#   Same guardrail as the build script: from 1970 on every group campaign is
#   exactly 3 games (fixed denominator -> no Poisson offset needed).
stopifnot(all(model_df$year >= 1970))
stopifnot(all(model_df$played == 3))

cat(sprintf("Modeling table: %d rows x %d cols (men's, 1970+)\n",
            nrow(model_df), ncol(model_df)))
cat("points_std range:", range(model_df$points_std),
    "| mean:", round(mean(model_df$points_std), 2),
    "| var:",  round(var(model_df$points_std), 2), "\n")


# =============================================================================
# 2. CANDIDATE MODEL SPEC  (which variables, and why NOT the others)
# -----------------------------------------------------------------------------
# Many columns in the table are mechanically tied to the outcome or to each
# other, so a Poisson fit on ALL of them would be tautological and/or
# unidentifiable. Pruning rules applied:
#
#   EXCLUDED - deterministic functions of the result (would tautologically
#              predict points_std):
#       wins, draws, losses            (points_std = 3*wins + draws)
#       points_raw                     (old 2/3-pt version of the outcome)
#       advanced                       (derived from final group ranking)
#       goals_for, goals_against,      (downstream match results; and
#         goal_difference)               goal_difference = GF - GA exactly)
#
#   EXCLUDED - redundant / collinear with a kept predictor:
#       yellows, reds                  (total_cards ~ yellows+reds; y~tc r=.99)
#       max_prior_wc, debutant_share   (avg_prior_wc vs debutant_share r=-.95)
#       avg_career_tournaments         (LEAKY: counts future tournaments too)
#
#   KEPT - one clean representative per construct:
#       Experience :  prior_tournaments (team-level)  +  avg_prior_wc (squad)
#                     [moderately correlated, r~.49; keep both = different
#                      constructs. Drop one if VIF is uncomfortable.]
#       Squad shape:  avg_age, forward_share, defender_share, squad_size
#       Context    :  is_host, foreign_manager, conf (confederation), year_c
#       Discipline :  total_cards   (within-tournament covariate, not the score)
#
# NOTE on independence: the same nation recurs across tournaments, so rows are
# NOT independent. We report team-clustered SEs in section 4.
# =============================================================================

f_candidate <- points_std ~ prior_tournaments + avg_prior_wc +
                            avg_age + forward_share + defender_share + squad_size +
                            is_host + foreign_manager + conf + year_c +
                            total_cards

# A leaner "structural only" spec (drop discipline; keep pre-tournament vars),
# handy for a cleaner inference story if total_cards behaves oddly.
f_structural <- points_std ~ prior_tournaments + avg_prior_wc +
                            avg_age + forward_share + defender_share +
                            is_host + foreign_manager + conf + year_c


# =============================================================================
# 3. STEPWISE VARIABLE SELECTION (AIC & BIC), THEN FIT THE CHOSEN MODEL
# -----------------------------------------------------------------------------
#   Selection runs on the PRE-PRUNED candidate pool (section 2), so the leaky /
#   tautological columns are never eligible -- stepwise only arbitrates among
#   legitimate predictors (e.g. which experience term, whether cards help).
#   We report four searches: AIC vs BIC x forward vs backward/both. BIC's
#   heavier penalty (k = log n) tends to return a smaller model.
#   Caveat: post-selection p-values/CIs are optimistic; treat the chosen set as
#   a data-driven suggestion, not a hypothesis test.
# =============================================================================
pois_full <- glm(f_candidate, family = poisson(link = "log"), data = model_df)
null_mod  <- glm(points_std ~ 1, family = poisson(link = "log"), data = model_df)
n_obs     <- nrow(model_df)

sel_aic_both <- step(pois_full, direction = "both", trace = 0)
sel_aic_fwd  <- step(null_mod, scope = list(lower = ~1, upper = f_candidate),
                     direction = "forward", trace = 0)
sel_bic_both <- step(pois_full, direction = "both", k = log(n_obs), trace = 0)
sel_bic_fwd  <- step(null_mod, scope = list(lower = ~1, upper = f_candidate),
                     direction = "forward", k = log(n_obs), trace = 0)

show_terms <- function(lbl, m)
  cat(sprintf("%-12s: %s\n", lbl,
      paste(attr(terms(m), "term.labels"), collapse = " + ")))
cat("\n---- Stepwise selection (terms retained) ----\n")
show_terms("AIC both",    sel_aic_both)
show_terms("AIC forward", sel_aic_fwd)
show_terms("BIC both",    sel_bic_both)
show_terms("BIC forward", sel_bic_fwd)

# ---- Choose the model to report --------------------------------------------
#   Default: the AIC both-direction model. Swap to sel_bic_both for the more
#   parsimonious BIC choice, or back to pois_full to force the full spec.
pois <- sel_aic_both

cat("\n================ CHOSEN POISSON MODEL ================\n")
cat("Formula:", deparse(formula(pois)), "\n\n")
print(summary(pois))
cat("\n95% CIs (Wald):\n"); print(confint.default(pois))
cat("\nRate ratios exp(beta):\n"); print(round(exp(coef(pois)), 3))

# ---- Overall fit -----------------------------------------------------------
#   There is no true R^2 for a Poisson GLM (no least-squares variance to
#   partition). The analogues are PSEUDO-R^2 measures from the likelihood or
#   deviance, plus a deviance goodness-of-fit test and an LRT vs the null.
gof_p         <- pchisq(deviance(pois), df.residual(pois), lower.tail = FALSE)
mcfadden      <- 1 - as.numeric(logLik(pois) / logLik(null_mod))
pseudo_r2_dev <- 1 - deviance(pois) / deviance(null_mod)     # deviance-based R^2
lrt           <- anova(null_mod, pois, test = "Chisq")

cat("\n---- Overall fit ----\n")
cat(sprintf("McFadden pseudo-R^2      : %.3f\n", mcfadden))
cat(sprintf("Deviance pseudo-R^2      : %.3f\n", pseudo_r2_dev))
cat(sprintf("Deviance GOF p-value     : %.3f  (large p = no evidence of misfit)\n", gof_p))
cat(sprintf("AIC / BIC                : %.1f / %.1f\n", AIC(pois), BIC(pois)))
cat("LRT vs null model:\n"); print(lrt)


# =============================================================================
# 4. TEAM-CLUSTERED STANDARD ERRORS (honest variable significance)
# -----------------------------------------------------------------------------
#   The same nation recurs across tournaments, so rows are not independent.
#   Clustering the vcov by team_id keeps the significance tests from being
#   overconfident. (This addresses non-independence, not dispersion, and can be
#   dropped if you prefer the plain model-based SEs above.)
# =============================================================================
if (has_sandwich && has_lmtest) {
  cl_vcov <- sandwich::vcovCL(pois, cluster = model_df$team_id)
  cat("\n---- Coefficients with team-clustered SEs ----\n")
  print(lmtest::coeftest(pois, vcov. = cl_vcov))
} else {
  cat("\n[skip] install.packages(c('sandwich','lmtest')) for clustered SEs.\n")
}


# =============================================================================
# 5. RESIDUAL DIAGNOSTICS
# -----------------------------------------------------------------------------
#   The four standard glm plots (residuals vs fitted, Q-Q, scale-location,
#   leverage). Interactively these render to the plot pane. Under `Rscript`
#   there is no interactive device, so we ALSO save them to diagnostics.png so
#   the run works headless. Set save_plot <- FALSE to skip the file.
# =============================================================================
save_plot <- TRUE
if (save_plot) {
  png("diagnostics.png", width = 1000, height = 1000, res = 110)
  op <- par(mfrow = c(2, 2))
  plot(pois)
  par(op)
  dev.off()
  cat("\nSaved residual diagnostics to diagnostics.png\n")
}

# Also draw to the interactive device when one is available (RStudio / R GUI).
if (interactive()) {
  op <- par(mfrow = c(2, 2))
  plot(pois)        # residuals vs fitted, Q-Q, scale-location, leverage
  par(op)
}

# =============================================================================
# WHAT TO REPORT / NEXT STEPS
#   - Report the chosen model's rate ratios with the team-clustered SEs for
#     honest significance; cite the pseudo-R^2 and GOF p-value for overall fit.
#   - Show the AIC vs BIC selected term sets; if they disagree, BIC is the
#     parsimonious story and AIC the fuller one.
#   - Post-selection inference is optimistic -- if you want valid p-values,
#     pre-specify the model (e.g. f_structural) rather than lean on stepwise.
#   - Optionally check VIFs (car::vif) on prior_tournaments vs avg_prior_wc.
# =============================================================================
