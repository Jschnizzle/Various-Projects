rm( list = ls() )

# =============================================================================
# 02_model_fitting.R
# -----------------------------------------------------------------------------
# MODEL-FITTING STAGE for the men's World Cup group-stage analysis. Loads the
# already-built modeling table `mens_groupstage_1970on.csv` (produced by
# 01_data_transformation.R) and fits THREE models of the same group-stage
# campaign, side by side:
#
#   A. POISSON  -- points_std (0-9 count)            "HOW MANY points"
#   B. LOGISTIC -- advanced   (1 = qualified out)    "DID THEY QUALIFY"
#   C. ORDINAL  -- points_ord (points_std as ranks)  "WHERE ON THE SCALE"
#
# The three share the SAME rows and the SAME pre-pruned predictor pool by
# design, so their results are directly comparable. This file does NO data
# work: the raw worldcup_data/ CSVs, the sqldf joins, the men's/group-stage
# filters, the points_std recompute and the 1970+ cut all live in
# 01_data_transformation.R and only need re-running when the raw data changes.
#
# (Consolidated from poisson_mens_groupstage_model.R, logit_mens_groupstage_
#  advance.R, and ordinal_mens_groupstage_points.R.)
# =============================================================================


# =============================================================================
# SETUP: optional packages (each block below is skipped with a message if the
# package is absent -- the core fits all run on base R except the ordinal
# engine, which needs `ordinal` or `MASS`).
# =============================================================================
has_sandwich <- requireNamespace("sandwich",          quietly = TRUE)  # clustered vcov
has_lmtest   <- requireNamespace("lmtest",            quietly = TRUE)  # coeftest
has_pROC     <- requireNamespace("pROC",              quietly = TRUE)  # AUC (logistic)
has_resource <- requireNamespace("ResourceSelection", quietly = TRUE)  # Hosmer-Lemeshow
has_logistf  <- requireNamespace("logistf",           quietly = TRUE)  # Firth fallback
has_ordinal  <- requireNamespace("ordinal",           quietly = TRUE)  # clm, clmm, nominal_test
has_MASS     <- requireNamespace("MASS",              quietly = TRUE)  # polr fallback
has_brant    <- requireNamespace("brant",             quietly = TRUE)  # PO test for polr
has_VGAM     <- requireNamespace("VGAM",              quietly = TRUE)  # non-PO fallback

if (!has_ordinal && !has_MASS)
  stop("Need either `ordinal` or `MASS` for the ordinal model: install.packages(c('ordinal','MASS'))")

# Small helper reused by the Poisson and logistic stepwise sections.
show_terms <- function(lbl, m)
  cat(sprintf("%-12s: %s\n", lbl,
      paste(attr(terms(m), "term.labels"), collapse = " + ")))


# =============================================================================
# LOAD THE PRE-BUILT MODELING TABLE (shared by all three models)
# -----------------------------------------------------------------------------
#   Built by 01_data_transformation.R: men's, group stage, 1970+, with
#   points_std recomputed on the 3-1-0 scale and predictors already aggregated.
# =============================================================================
model_df <- read.csv("mens_groupstage_1970on.csv", stringsAsFactors = FALSE)

# ---- Drop the OFC / confOTHER cell (perfect separation in the logistic model) -
#   `conf == "OTHER"` is the collapsed OFC (Oceania) bucket: exactly 2 rows,
#   NEW ZEALAND 1982 and NEW ZEALAND 2010 -- the only Oceania entries in the
#   1970+ men's data, both with advanced = 0. In the logistic model (section B)
#   that cell is perfectly separated (confOTHER coefficient -> -Inf) with a
#   meaningless Wald CI. We drop those 2 rows for ALL three models here (368 ->
#   366) so they share one row set and no near-empty confederation level is
#   estimated; Oceania carried no advancement information anyway.
model_df <- subset(model_df, confederation_code != "OFC")

# ---- Restore factor structure that CSV storage flattens ---------------------
#   `conf` was written as plain text; re-establish it as a factor with UEFA as
#   the baseline so the coefficients read the same way across all three models.
#   With the OFC rows gone, factor() no longer carries an "OTHER" level.
model_df$conf <- relevel(factor(model_df$conf), ref = "UEFA")

# ---- Sanity checks on the loaded table --------------------------------------
#   Fixed 3-game denominator, 1970+ only, clean 0/1 `advanced`, and the outcome
#   confined to its 9 attainable point totals (guarantees no stray 8 appears).
stopifnot(all(model_df$played == 3))
stopifnot(all(model_df$year >= 1970))
stopifnot(all(model_df$advanced %in% c(0, 1)))
stopifnot(all(model_df$points_std %in% c(0, 1, 2, 3, 4, 5, 6, 7, 9)))

# ---- Ordered outcome for the ordinal model ----------------------------------
#   Levels are the OBSERVED values in ascending order. 8 is absent because it
#   cannot occur; do not pad the level set.
model_df$points_ord <- factor(model_df$points_std,
                              levels  = sort(unique(model_df$points_std)),
                              ordered = TRUE)

cat(sprintf("Modeling table: %d rows x %d cols (men's, 1970+)\n",
            nrow(model_df), ncol(model_df)))
cat("points_std range:", range(model_df$points_std),
    "| mean:", round(mean(model_df$points_std), 2),
    "| var:",  round(var(model_df$points_std), 2), "\n")


# #############################################################################
# ## A. POISSON MODEL  --  outcome: points_std (0-9 count)                    ##
# #############################################################################

# =============================================================================
# A2. CANDIDATE MODEL SPEC  (which variables, and why NOT the others)
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
# NOT independent. We report team-clustered SEs in section A4.
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
# A3. STEPWISE VARIABLE SELECTION (AIC & BIC), THEN FIT THE CHOSEN MODEL
# -----------------------------------------------------------------------------
#   Selection runs on the PRE-PRUNED candidate pool (section A2), so the leaky /
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

cat("\n---- [Poisson] Stepwise selection (terms retained) ----\n")
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
# A4. TEAM-CLUSTERED STANDARD ERRORS (honest variable significance)
# -----------------------------------------------------------------------------
#   The same nation recurs across tournaments, so rows are not independent.
#   Clustering the vcov by team_id keeps the significance tests from being
#   overconfident. (This addresses non-independence, not dispersion, and can be
#   dropped if you prefer the plain model-based SEs above.)
# =============================================================================
if (has_sandwich && has_lmtest) {
  cl_vcov <- sandwich::vcovCL(pois, cluster = model_df$team_id)
  cat("\n---- [Poisson] Coefficients with team-clustered SEs ----\n")
  print(lmtest::coeftest(pois, vcov. = cl_vcov))
} else {
  cat("\n[skip] install.packages(c('sandwich','lmtest')) for clustered SEs.\n")
}


# =============================================================================
# A5. RESIDUAL DIAGNOSTICS
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


# #############################################################################
# ## B. LOGISTIC MODEL  --  outcome: advanced (1 = qualified out of group)   ##
# #############################################################################
#
# WHY THE DATASET'S OWN `advanced` FLAG:
#   We do NOT re-derive qualification from goal difference. Tie-breaks in this
#   data are genuinely nebulous -- early tournaments settled level teams by
#   PLAYOFFS, not GD (1954 West Germany advanced over Turkey with a worse GD;
#   1958 USSR beat England in a playoff). The stored `advanced` column records
#   the true historical outcome, including those cases, so it is the trustworthy
#   target; a GD rule would misclassify exactly those edge cases.
#
# CAVEAT: what "advanced" means is not perfectly constant across eras (group
#   sizes, qualifiers per group, and tie-break mechanics all changed). The 1970+
#   cut removes most of that drift and `year_c` absorbs the residual era trend,
#   but treat era-crossing comparisons with that in mind.
# #############################################################################

base_rate <- mean(model_df$advanced)
cat(sprintf("\n[Logistic] advanced: %d ones / %d zeros | base rate = %.3f\n",
            sum(model_df$advanced == 1), sum(model_df$advanced == 0), base_rate))

# =============================================================================
# B2. CANDIDATE MODEL SPEC
# -----------------------------------------------------------------------------
# Identical pre-pruned pool to the Poisson model -- deliberately so, because the
# analyses are meant to be directly comparable (same data, same predictors,
# different question). Same exclusion rules as section A2, plus:
#       position                       (the final group ranking itself) EXCLUDED
# =============================================================================
f_candidate <- advanced ~ prior_tournaments + avg_prior_wc +
                          avg_age + forward_share + defender_share + squad_size +
                          is_host + foreign_manager + conf + year_c +
                          total_cards

f_structural <- advanced ~ prior_tournaments + avg_prior_wc +
                           avg_age + forward_share + defender_share +
                           is_host + foreign_manager + conf + year_c


# =============================================================================
# B3. STEPWISE VARIABLE SELECTION (AIC & BIC), THEN FIT THE CHOSEN MODEL
# =============================================================================
logit_full <- glm(f_candidate, family = binomial(link = "logit"), data = model_df)
null_mod   <- glm(advanced ~ 1, family = binomial(link = "logit"), data = model_df)
n_obs      <- nrow(model_df)

sel_aic_both <- step(logit_full, direction = "both", trace = 0)
sel_aic_fwd  <- step(null_mod, scope = list(lower = ~1, upper = f_candidate),
                     direction = "forward", trace = 0)
sel_bic_both <- step(logit_full, direction = "both", k = log(n_obs), trace = 0)
sel_bic_fwd  <- step(null_mod, scope = list(lower = ~1, upper = f_candidate),
                     direction = "forward", k = log(n_obs), trace = 0)

cat("\n---- [Logistic] Stepwise selection (terms retained) ----\n")
show_terms("AIC both",    sel_aic_both)
show_terms("AIC forward", sel_aic_fwd)
show_terms("BIC both",    sel_bic_both)
show_terms("BIC forward", sel_bic_fwd)

# ---- Choose the model to report --------------------------------------------
#   Default: the AIC both-direction model, matching the Poisson script.
fit <- sel_aic_both

cat("\n================ CHOSEN LOGISTIC MODEL ================\n")
cat("Formula:", deparse(formula(fit)), "\n\n")
print(summary(fit))

# =============================================================================
# B4. ODDS RATIOS AND WALD CONFIDENCE INTERVALS
# -----------------------------------------------------------------------------
#   exp(beta) is the multiplicative change in the ODDS of advancing per one-unit
#   increase in the predictor (per level vs the UEFA baseline for `conf`).
#   OR > 1 pushes advancement up, OR < 1 pushes it down; a CI spanning 1 is the
#   "no detectable effect" case.
# =============================================================================
or_tab <- cbind(OR = exp(coef(fit)), exp(confint.default(fit)))
colnames(or_tab) <- c("OR", "CI 2.5%", "CI 97.5%")
cat("\n---- Odds ratios with Wald 95% CIs ----\n")
print(round(or_tab, 3))


# =============================================================================
# B5. OVERALL FIT
# -----------------------------------------------------------------------------
#   There is no true R^2 for a logistic GLM. McFadden's pseudo-R^2 compares the
#   fitted log-likelihood to the null model's; values of 0.2-0.4 already mean an
#   excellent fit by its own scale, so read it as "much lower than an OLS R^2".
#   NOTE: the deviance GOF test used in the Poisson section is NOT valid here --
#   with binary (ungrouped) responses the residual deviance does not have its
#   nominal chi-square distribution. Section B6 does calibration instead.
# =============================================================================
mcfadden <- 1 - as.numeric(logLik(fit) / logLik(null_mod))
lrt      <- anova(null_mod, fit, test = "Chisq")

cat("\n---- Overall fit ----\n")
cat(sprintf("McFadden pseudo-R^2      : %.3f\n", mcfadden))
cat(sprintf("AIC / BIC                : %.1f / %.1f\n", AIC(fit), BIC(fit)))
cat(sprintf("Null deviance            : %.1f on %d df\n",
            fit$null.deviance, fit$df.null))
cat(sprintf("Residual deviance        : %.1f on %d df\n",
            deviance(fit), df.residual(fit)))
cat("LRT vs null model:\n"); print(lrt)


# =============================================================================
# B6. CALIBRATION / GOODNESS OF FIT (Hosmer-Lemeshow)
# -----------------------------------------------------------------------------
#   Calibration asks a different question than discrimination: among the rows we
#   gave a ~70% chance, did about 70% actually advance? Hosmer-Lemeshow bins by
#   predicted-probability decile and chi-square tests observed vs expected.
#   A LARGE p-value means no evidence of miscalibration (here, "good").
# =============================================================================
p_hat <- fitted(fit)

if (has_resource) {
  hl <- ResourceSelection::hoslem.test(model_df$advanced, p_hat, g = 10)
  cat("\n---- Hosmer-Lemeshow goodness of fit ----\n")
  print(hl)
} else {
  cat("\n[skip] ResourceSelection not installed",
      "(install.packages('ResourceSelection')) -- manual decile table below.\n")
}

# ---- Manual decile calibration table (always printed) -----------------------
decile <- cut(p_hat,
              breaks = quantile(p_hat, probs = seq(0, 1, 0.1)),
              include.lowest = TRUE, labels = FALSE)
calib <- data.frame(
  decile    = seq_len(max(decile)),
  n         = as.vector(table(decile)),
  mean_pred = round(tapply(p_hat, decile, mean), 3),
  obs_rate  = round(tapply(model_df$advanced, decile, mean), 3),
  obs_adv   = as.vector(tapply(model_df$advanced, decile, sum)),
  exp_adv   = round(as.vector(tapply(p_hat, decile, sum)), 1)
)
cat("\n---- Decile calibration table (predicted vs observed) ----\n")
print(calib, row.names = FALSE)

# Hand-rolled Hosmer-Lemeshow statistic.
o1 <- calib$obs_adv;          e1 <- as.vector(tapply(p_hat, decile, sum))
o0 <- calib$n - o1;           e0 <- calib$n - e1
hl_stat <- sum((o1 - e1)^2 / e1) + sum((o0 - e0)^2 / e0)
hl_df   <- max(decile) - 2
cat(sprintf("Manual HL statistic: X2 = %.2f on %d df, p = %.3f",
            hl_stat, hl_df, pchisq(hl_stat, hl_df, lower.tail = FALSE)),
    " (large p = no evidence of miscalibration)\n")


# =============================================================================
# B7. CLASSIFICATION PERFORMANCE
# -----------------------------------------------------------------------------
#   Confusion matrix at the conventional 0.5 cut, plus AUC (threshold-free
#   discrimination). Accuracy must be judged against the NO-INFORMATION base
#   rate -- always guessing "advanced" already scores ~0.53 here, so only the
#   lift above that is real. And all of this is IN-SAMPLE (fit on these same
#   rows after a stepwise search), so the numbers are optimistic. For honest
#   predictive error, split train year < 2010 / test year >= 2010.
# =============================================================================
pred_class <- as.integer(p_hat >= 0.5)
cm <- table(Predicted = factor(pred_class, levels = c(0, 1)),
            Actual    = factor(model_df$advanced, levels = c(0, 1)))

accuracy <- sum(diag(cm)) / sum(cm)
sens     <- cm["1", "1"] / sum(cm[, "1"])   # of those who advanced, caught
spec     <- cm["0", "0"] / sum(cm[, "0"])   # of those who didn't, caught

cat("\n---- Confusion matrix (threshold 0.5) ----\n")
print(cm)
cat(sprintf("\nAccuracy      : %.3f  (no-information base rate = %.3f, lift = %+.3f)\n",
            accuracy, max(base_rate, 1 - base_rate),
            accuracy - max(base_rate, 1 - base_rate)))
cat(sprintf("Sensitivity   : %.3f  (advanced correctly identified)\n", sens))
cat(sprintf("Specificity   : %.3f  (eliminated correctly identified)\n", spec))

# ---- AUC --------------------------------------------------------------------
if (has_pROC) {
  auc_val <- as.numeric(pROC::auc(pROC::roc(model_df$advanced, p_hat,
                                            quiet = TRUE)))
  cat(sprintf("AUC (pROC)    : %.3f\n", auc_val))
} else {
  # Mann-Whitney equivalence (handles ties via rank averaging).
  r  <- rank(p_hat)
  n1 <- sum(model_df$advanced == 1); n0 <- sum(model_df$advanced == 0)
  auc_val <- (sum(r[model_df$advanced == 1]) - n1 * (n1 + 1) / 2) / (n0 * n1)
  cat(sprintf("AUC (manual)  : %.3f   [install pROC for the package version]\n",
              auc_val))
}
cat("NOTE: in-sample -- see the train-old/test-recent split suggested above.\n")


# =============================================================================
# B8. TEAM-CLUSTERED STANDARD ERRORS (honest variable significance)
# =============================================================================
if (has_sandwich && has_lmtest) {
  cl_vcov <- sandwich::vcovCL(fit, cluster = model_df$team_id)
  cat("\n---- [Logistic] Coefficients with team-clustered SEs ----\n")
  print(lmtest::coeftest(fit, vcov. = cl_vcov))

  cat("\n---- Odds ratios with team-clustered Wald 95% CIs ----\n")
  cl_se  <- sqrt(diag(cl_vcov))
  cl_tab <- cbind(OR       = exp(coef(fit)),
                  `CI 2.5%`  = exp(coef(fit) - 1.96 * cl_se),
                  `CI 97.5%` = exp(coef(fit) + 1.96 * cl_se))
  print(round(cl_tab, 3))
} else {
  cat("\n[skip] install.packages(c('sandwich','lmtest')) for clustered SEs.\n")
}


# =============================================================================
# B9. SEPARATION CHECK
# -----------------------------------------------------------------------------
#   Logistic regression breaks down under perfect / quasi-separation. Flag any
#   |beta| or SE above ~10 and name the term rather than silently trusting the
#   fit. Firth's penalized likelihood (logistf) is the standard remedy.
#
#   KNOWN CASE IN THIS DATA: conf == "OTHER" (the collapsed OFC bucket) is
#   2 rows with 0 advancers -- a perfectly separated cell, so its beta runs to
#   -Inf. This is expected and does NOT affect the other coefficients, the
#   fitted probabilities, or the AUC. Read confOTHER as "no OFC team has ever
#   advanced in this window", not as a real estimate.
# =============================================================================
co  <- summary(fit)$coefficients
bad <- which(abs(co[, "Estimate"]) > 10 | co[, "Std. Error"] > 10)

cat("\n---- Separation check ----\n")
if (length(bad)) {
  cat("WARNING: possible separation -- these terms have |beta| or SE > 10:\n")
  print(round(co[bad, c("Estimate", "Std. Error"), drop = FALSE], 3))
  cat("Do NOT trust their Wald CIs. Refit with Firth's penalized logistic:\n")
  if (has_logistf) {
    cat("  logistf::logistf(formula(fit), data = model_df)\n")
  } else {
    cat("  install.packages('logistf'); logistf::logistf(formula(fit), data = model_df)\n")
  }
} else {
  cat("OK: all |beta| and SE < 10, and glm converged",
      sprintf("(%s).", ifelse(fit$converged, "converged = TRUE", "DID NOT CONVERGE")),
      "No sign of separation.\n")
}
cat(sprintf("Max |beta| = %.2f | Max SE = %.2f | fitted p range = [%.4f, %.4f]\n",
            max(abs(co[, "Estimate"])), max(co[, "Std. Error"]),
            min(p_hat), max(p_hat)))


# #############################################################################
# ## C. ORDINAL MODEL  --  outcome: points_ord (points_std as ordered ranks) ##
# #############################################################################
#
# WHY ORDINAL RATHER THAN POISSON:
#   The Poisson model treats points_std as an unbounded count. It isn't. Over
#   exactly 3 games, points_std = 3*wins + draws can only take the 9 values
#   {0,1,2,3,4,5,6,7,9}: 8 is STRUCTURALLY IMPOSSIBLE, and the gaps between
#   adjacent attainable values are not uniform in meaning. An ordinal model uses
#   only the RANK ORDER, so it makes no spacing assumption, is untroubled by the
#   missing 8, and respects the hard ceiling at 9. The tradeoff is
#   interpretation: cumulative odds ratios instead of the Poisson's rate ratios.
#   Reporting both side by side is the point.
# #############################################################################

engine <- if (has_ordinal) "ordinal::clm" else "MASS::polr"
cat(sprintf("\n[Ordinal] engine: %s\n", engine))
cat(sprintf("points_ord: %d ordered levels -> %s\n",
            nlevels(model_df$points_ord),
            paste(levels(model_df$points_ord), collapse = " < ")))
cat("Outcome distribution:\n")
print(table(model_df$points_ord))

# =============================================================================
# C2. CANDIDATE MODEL SPEC  (identical pre-pruned pool to the siblings)
# =============================================================================
f_candidate <- points_ord ~ prior_tournaments + avg_prior_wc +
                            avg_age + forward_share + defender_share + squad_size +
                            is_host + foreign_manager + conf + year_c +
                            total_cards

f_structural <- points_ord ~ prior_tournaments + avg_prior_wc +
                             avg_age + forward_share + defender_share +
                             is_host + foreign_manager + conf + year_c


# =============================================================================
# C3. FIT THE CUMULATIVE LINK (PROPORTIONAL-ODDS) MODEL
# -----------------------------------------------------------------------------
#   logit[ P(Y <= j) ] = theta_j - x'beta
#   One set of slopes beta shared across all 8 cutpoints (the proportional-odds
#   assumption, tested in section C4); 8 thresholds theta_j for the 9 levels.
#   NOTE the minus sign: a POSITIVE beta pushes probability toward HIGHER
#   categories (both clm and polr use this parameterisation).
# =============================================================================
if (has_ordinal) {
  fit        <- ordinal::clm(f_candidate,  data = model_df, link = "logit")
  fit_struct <- ordinal::clm(f_structural, data = model_df, link = "logit")
  null_mod   <- ordinal::clm(points_ord ~ 1, data = model_df, link = "logit")
} else {
  cat("\n[fallback] `ordinal` not installed -- using MASS::polr.\n")
  fit        <- MASS::polr(f_candidate,  data = model_df,
                           method = "logistic", Hess = TRUE)
  fit_struct <- MASS::polr(f_structural, data = model_df,
                           method = "logistic", Hess = TRUE)
  null_mod   <- MASS::polr(points_ord ~ 1, data = model_df,
                           method = "logistic", Hess = TRUE)
}

cat("\n================ CHOSEN ORDINAL MODEL (f_candidate) ================\n")
print(summary(fit))

cat("\n---- Threshold (cutpoint) estimates ----\n")
if (has_ordinal) print(round(fit$alpha, 3)) else print(round(fit$zeta, 3))

# ---- Note on the large condition number -------------------------------------
#   clm reports cond.H ~ 1e7 and may warn "nearly unidentifiable". This is a
#   SCALING artefact, not a real identification problem: avg_age (~27),
#   squad_size (~22) and year_c (~ -6..6) live on very different scales from the
#   share variables (0..1). The fit converged cleanly and the slopes are
#   trustworthy; centring/scaling the continuous predictors would fix the
#   conditioning without changing any slope, odds ratio, or p-value. We keep the
#   raw scales so the coefficients stay comparable to the siblings; read the
#   thresholds as nuisance parameters.
if (has_ordinal)
  cat(sprintf("cond.H = %.2g  (large = scaling artefact; slopes unaffected)\n",
              tryCatch(fit$cond.H, error = function(e) NA_real_)))

cat("\n---- Candidate vs structural spec ----\n")
cat(sprintf("f_candidate  (with total_cards): AIC %.1f | BIC %.1f\n",
            AIC(fit), BIC(fit)))
cat(sprintf("f_structural (pre-tournament)  : AIC %.1f | BIC %.1f\n",
            AIC(fit_struct), BIC(fit_struct)))


# =============================================================================
# C4. PROPORTIONAL-ODDS ASSUMPTION CHECK  (the key ordinal diagnostic)
# -----------------------------------------------------------------------------
#   The PO assumption says one slope per predictor works at EVERY cutpoint.
#   nominal_test() relaxes that one term at a time and runs an LRT: a SMALL
#   p-value means that term's effect genuinely differs across cutpoints, so the
#   shared-slope model is misspecified FOR THAT TERM. Remedy if violated: a
#   partial-PO model, clm(..., nominal = ~ <term>).
# =============================================================================
if (has_ordinal) {
  cat("\n---- nominal_test: proportional-odds assumption, per term ----\n")
  nt <- tryCatch(ordinal::nominal_test(fit),
                 error = function(e) { cat("  [error]", conditionMessage(e), "\n"); NULL })
  if (!is.null(nt)) {
    print(nt)
    pv  <- nt[["Pr(>Chi)"]]
    trm <- rownames(nt)
    bad <- trm[!is.na(pv) & pv < 0.05]
    na_terms <- trm[is.na(pv)][-1]   # drop the "<none>" row, which is always NA
    cat("\nRead: ")
    if (length(bad)) {
      cat("PO assumption VIOLATED (p < .05) for:", paste(bad, collapse = ", "), "\n")
      cat("  -> consider partial PO, e.g. clm(f_candidate, nominal = ~ ",
          paste(bad, collapse = " + "), ", data = model_df)\n", sep = "")
    } else {
      cat("no term violates PO at the .05 level -- the shared-slope model is defensible.\n")
    }
    if (length(na_terms))
      cat("  [note] no test available for:", paste(na_terms, collapse = ", "),
          "\n         (freeing these gives a non-identifiable fit; PO status",
          "UNTESTED, not confirmed.)\n")
    cat("  [note] 5 terms were testable, so treat borderline p-values (~.02) with",
        "a\n         multiple-comparison grain of salt.\n")

    # ---- Partial-PO refit, if any term violated ------------------------------
    if (length(bad)) {
      cat("\n---- Partial-PO refit: nominal = ~", paste(bad, collapse = " + "), "----\n")
      f_nom <- as.formula(paste("~", paste(bad, collapse = " + ")))
      fit_ppo <- tryCatch(
        suppressWarnings(ordinal::clm(f_candidate, nominal = f_nom,
                                      data = model_df, link = "logit")),
        error = function(e) { cat("  [error] partial-PO fit failed:",
                                  conditionMessage(e), "\n"); NULL })
      if (!is.null(fit_ppo)) {
        cat(sprintf("PO model      : AIC %.1f | logLik %.2f\n",
                    AIC(fit), as.numeric(logLik(fit))))
        cat(sprintf("Partial-PO    : AIC %.1f | logLik %.2f\n",
                    AIC(fit_ppo), as.numeric(logLik(fit_ppo))))
        print(anova(fit, fit_ppo))
        cat("Read: if partial-PO wins on AIC the violation is material; if the",
            "two are close,\n      the PO model is still the better story",
            "(far fewer parameters).\n")
      }
    }
  }

  cat("\n---- scale_test (secondary: latent-scale heterogeneity) ----\n")
  st <- tryCatch(ordinal::scale_test(fit),
                 error = function(e) { cat("  [error]", conditionMessage(e), "\n"); NULL })
  if (!is.null(st)) print(st)

} else if (has_brant) {
  cat("\n---- Brant test: proportional-odds assumption ----\n")
  print(brant::brant(fit))
} else {
  cat("\n[skip] PO assumption untested: install `ordinal` (nominal_test) or",
      "`brant` (install.packages('brant')) for the polr path.\n")
}
if (!has_VGAM)
  cat("[note] VGAM not installed; the fully non-proportional fallback",
      "(VGAM::vglm, cumulative(parallel = FALSE)) is unavailable.\n")


# =============================================================================
# C5. CUMULATIVE ODDS RATIOS AND CONFIDENCE INTERVALS
# -----------------------------------------------------------------------------
#   exp(beta) is the multiplicative change in the odds of landing in a HIGHER
#   points category (vs all lower ones), the same at every cutpoint under
#   proportional odds. OR > 1 = shifts the team UP the points scale; OR < 1 =
#   down; a CI spanning 1 = no detectable shift. Thresholds are nuisance
#   parameters and are not exponentiated here.
# =============================================================================
beta <- if (has_ordinal) fit$beta else coef(fit)

# Profile-likelihood CIs are the clm default; fall back to Wald if they fail.
ci <- tryCatch(confint(fit),
               error   = function(e) { cat("[note] profile CI failed; using Wald.\n")
                                       confint.default(fit) },
               warning = function(w) { cat("[note] profile CI warned; using Wald.\n")
                                       suppressWarnings(confint.default(fit)) })
ci <- ci[names(beta), , drop = FALSE]

or_tab <- cbind(OR = exp(beta), exp(ci))
colnames(or_tab) <- c("OR", "CI 2.5%", "CI 97.5%")
cat("\n---- Cumulative odds ratios with 95% CIs ----\n")
print(round(or_tab, 3))
cat("(OR > 1 => shifts the team toward HIGHER points categories, under PO.)\n")


# =============================================================================
# C6. OVERALL FIT
# =============================================================================
mcfadden <- 1 - as.numeric(logLik(fit) / logLik(null_mod))
lrt      <- anova(null_mod, fit)

cat("\n---- Overall fit ----\n")
cat(sprintf("McFadden pseudo-R^2      : %.3f\n", mcfadden))
cat(sprintf("logLik null / fitted     : %.1f / %.1f\n",
            as.numeric(logLik(null_mod)), as.numeric(logLik(fit))))
cat(sprintf("AIC / BIC                : %.1f / %.1f\n", AIC(fit), BIC(fit)))
cat("LRT vs null model:\n"); print(lrt)


# =============================================================================
# C7. PREDICTIVE PERFORMANCE (ordinal-aware, IN-SAMPLE)
# -----------------------------------------------------------------------------
#   With 9 classes, exact accuracy is harsh and the no-information baseline is
#   low (always guess the modal class, points = 4, ~19%). Because the outcome is
#   ORDERED, WITHIN-ONE accuracy (predicted rank within +/-1 of observed) is the
#   more honest headline. Kendall's tau-b / Spearman on the ranks measure
#   ordinal association directly. NOTE the +/-1 is a RANK step, not a points
#   step: 7 -> 9 is adjacent in rank though 2 points apart. All IN-SAMPLE.
# =============================================================================
newx <- model_df[, setdiff(names(model_df), c("points_ord")), drop = FALSE]
pred_class <- if (has_ordinal) {
  predict(fit, newdata = newx, type = "class")$fit
} else {
  predict(fit, newdata = newx, type = "class")
}
pred_class <- factor(pred_class, levels = levels(model_df$points_ord),
                     ordered = TRUE)

obs_rank  <- as.integer(model_df$points_ord)
pred_rank <- as.integer(pred_class)

acc_exact  <- mean(pred_rank == obs_rank)
acc_within <- mean(abs(pred_rank - obs_rank) <= 1)
modal_rate <- max(table(model_df$points_ord)) / nrow(model_df)

cat("\n---- Confusion matrix (rows = predicted, cols = observed) ----\n")
print(table(Predicted = pred_class, Observed = model_df$points_ord))

cat(sprintf("\nExact accuracy       : %.3f  (modal-class base rate = %.3f, lift = %+.3f)\n",
            acc_exact, modal_rate, acc_exact - modal_rate))
cat(sprintf("Within-one accuracy  : %.3f  (predicted rank within +/-1 of observed)\n",
            acc_within))
cat(sprintf("Mean |rank error|    : %.2f ranks\n", mean(abs(pred_rank - obs_rank))))

tau_b    <- cor(pred_rank, obs_rank, method = "kendall")
spearman <- cor(pred_rank, obs_rank, method = "spearman")
cat(sprintf("Kendall's tau-b      : %.3f\n", tau_b))
cat(sprintf("Spearman rho         : %.3f\n", spearman))
cat("NOTE: in-sample -- see the train-old/test-recent split described above.\n")


# =============================================================================
# C8. NON-INDEPENDENCE: TEAM RANDOM INTERCEPT (clmm robustness check)
# -----------------------------------------------------------------------------
#   The same nation recurs across tournaments (Brazil appears ~14 times), so the
#   model-based SEs above are optimistic. The cumulative-link analogue of
#   clustered SEs is a MIXED model: give each team its own random intercept on
#   the latent scale. The random-intercept variance is itself of interest -- a
#   large one says a lot of the signal is just "which country is this". clmm is
#   slow; if it fails to converge we report the caveat rather than a bad fit.
# =============================================================================
if (has_ordinal) {
  model_df$team_id <- factor(model_df$team_id)
  f_mixed <- update(f_candidate, . ~ . + (1 | team_id))

  cat("\n---- Mixed cumulative link model: (1 | team_id) ----\n")
  cat("(fitting clmm -- this is slower than clm)\n")
  fit_mixed <- tryCatch(
    ordinal::clmm(f_mixed, data = model_df, link = "logit", Hess = TRUE),
    error   = function(e) { cat("  [error] clmm failed:", conditionMessage(e), "\n"); NULL },
    warning = function(w) { cat("  [warn] clmm warned:", conditionMessage(w), "\n")
                            suppressWarnings(
                              ordinal::clmm(f_mixed, data = model_df,
                                            link = "logit", Hess = TRUE)) })

  if (!is.null(fit_mixed)) {
    print(summary(fit_mixed))
    vc <- as.numeric(ordinal::VarCorr(fit_mixed)$team_id)
    cat(sprintf("\nTeam random-intercept variance : %.3f  (SD = %.3f, latent logit scale)\n",
                vc, sqrt(vc)))
    # Ordinal analogue of an ICC, using the logistic residual variance pi^2/3.
    icc <- vc / (vc + pi^2 / 3)
    cat(sprintf("Implied team ICC               : %.3f  (share of latent variance that is nation-level)\n",
                icc))

    cat("\n---- Fixed effects: clm vs clmm ----\n")
    cmp <- cbind(clm  = beta,
                 clmm = fit_mixed$beta[names(beta)],
                 diff = fit_mixed$beta[names(beta)] - beta)
    print(round(cmp, 3))
    cat("(Large shifts flag effects that were partly picking up persistent",
        "nation quality.)\n")
  } else {
    cat("\n[skip] clmm unavailable/non-convergent -- CAVEAT: the clm SEs above",
        "are optimistic because the same nation recurs across tournaments.\n")
  }
} else {
  cat("\n[skip] `ordinal` not installed, so no clmm random-intercept check.",
      "CAVEAT: the polr SEs above are optimistic under team clustering.\n")
}


# =============================================================================
# WHAT TO REPORT / NEXT STEPS  (all three models)
#   - POISSON : rate ratios with team-clustered SEs; pseudo-R^2 and GOF p-value.
#   - LOGISTIC: odds ratios with team-clustered SEs; McFadden pseudo-R^2, the
#               null LRT, the decile/HL calibration table; judge accuracy vs the
#               ~0.53 base rate. Watch the confOTHER separation flag.
#   - ORDINAL : cumulative odds ratios + thresholds; lead the predictive block
#               with WITHIN-ONE accuracy and tau-b; nominal_test decides whether
#               the single-slope story holds; clmm gives the team-clustering
#               robustness check.
#   - Compare across models: same rows, same predictors, three treatments of the
#     result. Signs should agree; if one flips, that is worth explaining.
#   - Post-selection inference (Poisson/logistic stepwise) is optimistic -- for
#     valid p-values, pre-specify (f_structural). The ordinal spec is already
#     pre-specified, so it is not post-selection-optimistic.
#   - Data changes? Re-run 01_data_transformation.R first to rebuild the CSV.
# =============================================================================
