rm( list = ls() )

# =============================================================================
# logit_mens_groupstage_advance.R
# -----------------------------------------------------------------------------
# COMPANION to the Poisson points model. Loads the already-built modeling table
# from `mens_groupstage_1970on.csv` and fits a LOGISTIC regression for whether a
# men's World Cup team advanced out of the group stage.
#
# Like `poisson_mens_groupstage_model.R`, this is the MODEL-ONLY script: the
# data-processing pipeline (raw worldcup_data/ CSVs, men's/group-stage filters,
# predictor aggregation, the 1970+ cut) lives in `poisson_mens_groupstage.R` and
# only needs re-running when the underlying data changes.
#
# OUTCOME:  advanced  (1 = qualified out of the group, 0 = eliminated)
#
# TWO MODELS ARE REPORTED (this is deliberate -- see sections 4 and 5):
#   MODEL 1  INFERENTIAL, pre-specified spec `f_structural`. Because the terms
#            are fixed in advance, its p-values, Wald CIs and clustered SEs are
#            HONEST -- this is the model to interpret.
#   MODEL 2  VARIABLE-SELECTED via stepwise AIC. This answers the separate,
#            exploratory question "which predictors survive data-driven
#            selection?" Its post-selection p-values/CIs are optimistic and
#            should NOT be read as inference.
# Section 8 then does OUT-OF-SAMPLE validation (train <2010 / test >=2010), with
# the 2026 World Cup earmarked as the real forward benchmark.
#
# WHY THE DATASET'S OWN `advanced` FLAG:
#   We do NOT re-derive qualification from goal difference. Tie-breaks in this
#   data are genuinely nebulous -- early tournaments settled level teams by
#   PLAYOFFS, not GD (1954 West Germany advanced over Turkey with a worse GD;
#   1958 USSR beat England in a playoff). The stored `advanced` column records
#   the true historical outcome, including those cases, so it is the trustworthy
#   target; a GD rule would misclassify exactly those edge cases.
# =============================================================================


# =============================================================================
# CAVEAT: WHAT "ADVANCED" MEANS IS NOT PERFECTLY CONSTANT ACROSS ERAS
# -----------------------------------------------------------------------------
#   Group sizes, the number of qualifiers per group, and the tie-break
#   mechanics all changed over time:
#       - pre-1970 : level teams settled by PLAYOFF, not goal difference
#       - 1986-1994: the four best THIRD-PLACED teams also advanced, so a team
#                    could qualify without finishing top 2 of its group
#       - post-1994: the stable, familiar rule -- top 2 of 4 advance
#   Restricting to 1970+ removes most of this drift (and guarantees a fixed
#   3-game denominator), and `year_c` absorbs the residual era trend. But the
#   outcome is still not a perfectly homogeneous event across the whole window;
#   treat era-crossing comparisons with that in mind.
# =============================================================================


# ---- Setup ------------------------------------------------------------------
# Optional packages. The core fit, selection, calibration and classification all
# run on base R; each optional block is skipped with a message if absent.
has_sandwich <- requireNamespace("sandwich",          quietly = TRUE)  # clustered vcov
has_lmtest   <- requireNamespace("lmtest",            quietly = TRUE)  # coeftest
has_pROC     <- requireNamespace("pROC",              quietly = TRUE)  # AUC
has_resource <- requireNamespace("ResourceSelection", quietly = TRUE)  # Hosmer-Lemeshow
has_logistf  <- requireNamespace("logistf",           quietly = TRUE)  # Firth fallback


# =============================================================================
# 1. LOAD THE PRE-BUILT MODELING TABLE
# -----------------------------------------------------------------------------
#   Built by poisson_mens_groupstage.R: men's, group stage, 1970+, with the
#   `advanced` flag carried through and predictors already aggregated.
# =============================================================================
model_df <- read.csv("mens_groupstage_1970on.csv", stringsAsFactors = FALSE)

# ---- Drop the OFC / confOTHER cell (perfect separation) ---------------------
#   `conf == "OTHER"` is the collapsed OFC (Oceania) bucket, and it is exactly
#   TWO rows: NEW ZEALAND 1982 and NEW ZEALAND 2010 -- the only Oceania entries
#   anywhere in the 1970+ men's data. Both had advanced = 0, so the cell is
#   PERFECTLY SEPARATED: the confOTHER logit coefficient runs off to -Inf and
#   its Wald CI is meaningless, contaminating the odds-ratio tables.
#   We remove those 2 rows here (368 -> 366) so no separated level enters any
#   model. The only cost is that Oceania drops out of the confederation
#   comparison -- and with 0 advancers in 2 games it carried no information
#   about advancement anyway. (Done consistently across every model script.)
model_df <- subset(model_df, confederation_code != "OFC")

# ---- Restore factor structure that CSV storage flattens ---------------------
#   `conf` was written as plain text; re-establish it as a factor with UEFA as
#   the baseline so the coefficients read the same way as in the Poisson script.
#   Because the OFC rows are already gone, factor() no longer carries an "OTHER"
#   level. Without the relevel the baseline would default to alphabetical (AFC).
model_df$conf <- relevel(factor(model_df$conf), ref = "UEFA")

# ---- Sanity checks on the loaded table --------------------------------------
#   From 1970 on every group campaign is exactly 3 games, every row is 1970+,
#   the outcome is a clean 0/1 flag, and the separated OFC cell is gone.
stopifnot(all(model_df$played == 3))
stopifnot(all(model_df$year >= 1970))
stopifnot(all(model_df$advanced %in% c(0, 1)))
stopifnot(!any(model_df$confederation_code == "OFC"))

base_rate <- mean(model_df$advanced)

cat(sprintf("Modeling table: %d rows x %d cols (men's, 1970+, OFC dropped)\n",
            nrow(model_df), ncol(model_df)))
cat(sprintf("advanced: %d ones / %d zeros | base rate = %.3f\n",
            sum(model_df$advanced == 1), sum(model_df$advanced == 0), base_rate))


# =============================================================================
# 2. CANDIDATE / PRE-SPECIFIED MODEL SPECS  (which variables, and why NOT others)
# -----------------------------------------------------------------------------
# Identical pre-pruned pool to the Poisson model -- deliberately so, because the
# two analyses are meant to be directly comparable (same data, same predictors,
# different question: HOW MANY points vs DID THEY QUALIFY).
#
#   EXCLUDED - deterministic functions of the result (they would trivially
#              predict qualification):
#       wins, draws, losses            (points = 3*wins + draws)
#       points_std, points_raw         (the Poisson model's outcome)
#       goals_for, goals_against,      (downstream match results; and
#         goal_difference)               goal_difference = GF - GA exactly)
#       position                       (the final group ranking itself)
#
#   EXCLUDED - redundant / collinear with a kept predictor:
#       yellows, reds                  (total_cards ~ yellows+reds; y~tc r=.99)
#       max_prior_wc, debutant_share   (avg_prior_wc vs debutant_share r=-.95)
#       avg_career_tournaments         (LEAKY: counts future tournaments too)
#
#   EXCLUDED - identifiers / context, not predictors:
#       row_id, campaign, team_name, team_id, tournament_id, group_name,
#       region_name, confederation_code (raw; `conf` is the modeled version)
#
#   KEPT - one clean representative per construct:
#       Experience :  prior_tournaments (team-level)  +  avg_prior_wc (squad)
#       Squad shape:  avg_age, forward_share, defender_share, squad_size
#       Context    :  is_host, foreign_manager, conf (confederation), year_c
#       Discipline :  total_cards   (within-tournament covariate, not the score)
#
# NOTE on independence: the same nation recurs across tournaments, so rows are
# NOT independent. We report team-clustered SEs for the inferential model.
# =============================================================================

# Full candidate pool (feeds the stepwise search in Model 2, section 5).
f_candidate <- advanced ~ prior_tournaments + avg_prior_wc +
                          avg_age + forward_share + defender_share + squad_size +
                          is_host + foreign_manager + conf + year_c +
                          total_cards

# Pre-specified "structural" spec -- pre-tournament variables only (drops
# total_cards, which is measured DURING the tournament). This is the INFERENTIAL
# model in section 4: the terms are fixed in advance, so its p-values / CIs are
# not post-selection-optimistic.
f_structural <- advanced ~ prior_tournaments + avg_prior_wc +
                           avg_age + forward_share + defender_share +
                           is_host + foreign_manager + conf + year_c


# =============================================================================
# 3. STEPWISE VARIABLE SELECTION  (exploratory -- feeds Model 2 only)
# -----------------------------------------------------------------------------
#   Selection runs on the PRE-PRUNED candidate pool (section 2), so the leaky /
#   tautological columns are never eligible -- stepwise only arbitrates among
#   legitimate predictors. Four searches: AIC vs BIC x forward vs both. BIC's
#   heavier penalty (k = log n) tends to return a smaller model.
#   IMPORTANT: this section only DISCOVERS a formula; the inference you can trust
#   comes from Model 1 (section 4), whose spec was fixed before seeing the data.
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

show_terms <- function(lbl, m)
  cat(sprintf("%-12s: %s\n", lbl,
      paste(attr(terms(m), "term.labels"), collapse = " + ")))
cat("\n---- Stepwise selection (terms retained) ----\n")
show_terms("AIC both",    sel_aic_both)
show_terms("AIC forward", sel_aic_fwd)
show_terms("BIC both",    sel_bic_both)
show_terms("BIC forward", sel_bic_fwd)

# 3b. Plotting the Odds Ratios
library(ggplot2)

# Your OR table -> tidy data frame
or_df <- data.frame(
  term = c("prior_tournaments","avg_prior_wc","avg_age","forward_share",
           "defender_share","is_host","foreign_manager","confAFC","confCAF",
           "confCONCACAF","confCONMEBOL","year_c"),
  OR   = c(1.221,1.331,0.837,0.075,0.369,8.229,1.616,0.182,0.217,0.350,1.000,0.945),
  lo   = c(1.121,0.457,0.658,0.001,0.001,1.558,0.876,0.073,0.088,0.150,0.477,0.878),
  hi   = c(1.330,3.877,1.066,9.600,128.517,43.456,2.980,0.454,0.537,0.818,2.096,1.017)
)

# Order by OR so the plot reads top-to-bottom; flag CIs that exclude 1
or_df$term <- factor(or_df$term, levels = or_df$term[order(or_df$OR)])
or_df$sig  <- with(or_df, lo > 1 | hi < 1)

ggplot(or_df, aes(x = OR, y = term, color = sig)) +
  geom_vline(xintercept = 1, linetype = "dashed", color = "grey40") +
  geom_errorbarh(aes(xmin = lo, xmax = hi), height = 0.25) +
  geom_point(size = 2.5) +
  scale_x_log10(breaks = c(0.01, 0.1, 0.5, 1, 2, 5, 10, 50)) +
  scale_color_manual(values = c(`TRUE` = "#2774AE", `FALSE` = "grey55"),
                     guide = "none") +
  labs(x = "Odds ratio (log scale, 95% Wald CI)", y = NULL,
       title = "Advancement odds ratios — logistic model") +
  theme_minimal(base_size = 12)

# #############################################################################
# ## MODEL 1 -- INFERENTIAL (pre-specified `f_structural`)                    ##
# #############################################################################
# =============================================================================
# 4. FIT + HONEST INFERENCE
# -----------------------------------------------------------------------------
#   This is the model to INTERPRET. The spec is fixed in advance (section 2), so
#   its coefficients, odds ratios and CIs are not inflated by a data-driven
#   search. We report Wald CIs and, because nations recur across tournaments,
#   team-clustered CIs for honest significance.
# =============================================================================
fit_infer <- glm(f_structural, family = binomial(link = "logit"), data = model_df)

cat("\n================ MODEL 1: INFERENTIAL (pre-specified) ================\n")
cat("Formula:", deparse(formula(fit_infer)), "\n\n")
print(summary(fit_infer))

# ---- 4a. Odds ratios and Wald confidence intervals --------------------------
#   exp(beta) is the multiplicative change in the ODDS of advancing per one-unit
#   increase in the predictor (per level vs the UEFA baseline for `conf`).
#   OR > 1 pushes advancement up, OR < 1 pushes it down; a CI spanning 1 is the
#   "no detectable effect" case.
or_infer <- cbind(OR = exp(coef(fit_infer)), exp(confint.default(fit_infer)))
colnames(or_infer) <- c("OR", "CI 2.5%", "CI 97.5%")
cat("\n---- [Model 1] Odds ratios with Wald 95% CIs ----\n")
print(round(or_infer, 3))

# ---- 4b. Team-clustered standard errors -------------------------------------
#   The same nation recurs across tournaments, so rows are not independent.
#   Clustering the vcov by team_id keeps the significance tests from being
#   overconfident. These are the numbers to report in the writeup.
if (has_sandwich && has_lmtest) {
  cl_vcov <- sandwich::vcovCL(fit_infer, cluster = model_df$team_id)
  cat("\n---- [Model 1] Coefficients with team-clustered SEs ----\n")
  print(lmtest::coeftest(fit_infer, vcov. = cl_vcov))

  cat("\n---- [Model 1] Odds ratios with team-clustered Wald 95% CIs ----\n")
  cl_se  <- sqrt(diag(cl_vcov))
  cl_tab <- cbind(OR       = exp(coef(fit_infer)),
                  `CI 2.5%`  = exp(coef(fit_infer) - 1.96 * cl_se),
                  `CI 97.5%` = exp(coef(fit_infer) + 1.96 * cl_se))
  print(round(cl_tab, 3))
} else {
  cat("\n[skip] install.packages(c('sandwich','lmtest')) for clustered SEs.\n")
}

# ---- 4c. Overall fit --------------------------------------------------------
#   No true R^2 for a logistic GLM. McFadden's pseudo-R^2 compares the fitted
#   log-likelihood to the null model's; 0.2-0.4 already means an excellent fit
#   on its own scale, so read it as "much lower than an OLS R^2". The LRT vs null
#   asks whether the predictors jointly beat an intercept.
mcfadden_infer <- 1 - as.numeric(logLik(fit_infer) / logLik(null_mod))
lrt_infer      <- anova(null_mod, fit_infer, test = "Chisq")
cat("\n---- [Model 1] Overall fit ----\n")
cat(sprintf("McFadden pseudo-R^2      : %.3f\n", mcfadden_infer))
cat(sprintf("AIC / BIC                : %.1f / %.1f\n", AIC(fit_infer), BIC(fit_infer)))
cat(sprintf("Null deviance            : %.1f on %d df\n",
            fit_infer$null.deviance, fit_infer$df.null))
cat(sprintf("Residual deviance        : %.1f on %d df\n",
            deviance(fit_infer), df.residual(fit_infer)))
cat("LRT vs null model:\n"); print(lrt_infer)


# #############################################################################
# ## MODEL 2 -- VARIABLE-SELECTED (stepwise AIC)                              ##
# #############################################################################
# =============================================================================
# 5. THE AIC-SELECTED MODEL  (exploratory: "which predictors survive selection")
# -----------------------------------------------------------------------------
#   Default reported selection = the AIC both-direction model (section 3). Swap
#   to sel_bic_both for the more parsimonious BIC choice, or to logit_full for
#   the full candidate spec.
#   READ THIS AS DESCRIPTIVE, NOT INFERENTIAL: because the terms were chosen by
#   looking at the data, the p-values and CIs below are optimistic. Use Model 1
#   for the inferential story; use Model 2 for prediction (sections 6-8).
# =============================================================================
fit_sel <- sel_aic_both

cat("\n================ MODEL 2: VARIABLE-SELECTED (AIC) ================\n")
cat("Formula:", deparse(formula(fit_sel)), "\n\n")
print(summary(fit_sel))

or_sel <- cbind(OR = exp(coef(fit_sel)), exp(confint.default(fit_sel)))
colnames(or_sel) <- c("OR", "CI 2.5%", "CI 97.5%")
cat("\n---- [Model 2] Odds ratios with Wald 95% CIs (post-selection -- optimistic) ----\n")
print(round(or_sel, 3))

mcfadden_sel <- 1 - as.numeric(logLik(fit_sel) / logLik(null_mod))
cat(sprintf("\n[Model 2] McFadden pseudo-R^2 : %.3f | AIC/BIC : %.1f / %.1f\n",
            mcfadden_sel, AIC(fit_sel), BIC(fit_sel)))
cat("[Model 2] Post-selection caveat: the CIs above do not account for the\n",
    "          search that produced this formula -- do not report them as\n",
    "          hypothesis tests. Model 1 is the pre-specified inferential fit.\n", sep = "")


# =============================================================================
# 6. CALIBRATION / GOODNESS OF FIT  (Hosmer-Lemeshow, on the selected model)
# -----------------------------------------------------------------------------
#   Calibration asks a different question than discrimination: among the rows we
#   gave a ~70% chance, did about 70% actually advance? Hosmer-Lemeshow bins by
#   predicted-probability decile and chi-square tests observed vs expected.
#   A LARGE p-value means no evidence of miscalibration (here, "good").
#   NOTE: the deviance GOF test used in the Poisson script is NOT valid here --
#   with binary (ungrouped) responses the residual deviance does not have its
#   nominal chi-square distribution, so we do calibration instead.
#   Run on the predictive model (Model 2); swap `p_hat <- fitted(fit_infer)` to
#   calibrate Model 1 instead.
# =============================================================================
p_hat <- fitted(fit_sel)

if (has_resource) {
  hl <- ResourceSelection::hoslem.test(model_df$advanced, p_hat, g = 10)
  cat("\n---- Hosmer-Lemeshow goodness of fit ----\n")
  print(hl)
} else {
  cat("\n[skip] ResourceSelection not installed",
      "(install.packages('ResourceSelection')) -- manual decile table below.\n")
}

# ---- Manual decile calibration table (always printed) -----------------------
#   Ten bins of equal size by predicted probability; compare the mean predicted
#   probability to the observed advancement rate within each bin. Close columns
#   = well calibrated. `unique()` guards the breakpoints in case fitted
#   probabilities ever pile up and make a quantile boundary non-unique.
qbreaks <- unique(quantile(p_hat, probs = seq(0, 1, 0.1)))
decile  <- cut(p_hat, breaks = qbreaks, include.lowest = TRUE, labels = FALSE)
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

# Hand-rolled Hosmer-Lemeshow statistic: sum over bins and both outcomes of
# (O - E)^2 / E, compared to chi-square with (#bins - 2) df.
o1 <- calib$obs_adv;          e1 <- as.vector(tapply(p_hat, decile, sum))
o0 <- calib$n - o1;           e0 <- calib$n - e1
hl_stat <- sum((o1 - e1)^2 / e1) + sum((o0 - e0)^2 / e0)
hl_df   <- max(decile) - 2
cat(sprintf("Manual HL statistic: X2 = %.2f on %d df, p = %.3f",
            hl_stat, hl_df, pchisq(hl_stat, hl_df, lower.tail = FALSE)),
    " (large p = no evidence of miscalibration)\n")


# =============================================================================
# 7. CLASSIFICATION PERFORMANCE  (in-sample, on the selected model)
# -----------------------------------------------------------------------------
#   Confusion matrix at the conventional 0.5 cut, plus AUC (threshold-free
#   discrimination: the probability a randomly chosen advancer gets a higher
#   predicted probability than a randomly chosen non-advancer; 0.5 = coin flip).
#
#   IMPORTANT: accuracy must be judged against the NO-INFORMATION base rate --
#   always guessing "advanced" already scores ~0.53 here, so only the lift above
#   that is real. And all of this is IN-SAMPLE: the model was fit on these same
#   rows (after a stepwise search, no less), so these numbers are optimistic.
#   Section 8 does the honest out-of-sample version.
# =============================================================================
pred_class <- as.integer(p_hat >= 0.5)
cm <- table(Predicted = factor(pred_class, levels = c(0, 1)),
            Actual    = factor(model_df$advanced, levels = c(0, 1)))

accuracy <- sum(diag(cm)) / sum(cm)
sens     <- cm["1", "1"] / sum(cm[, "1"])   # of those who advanced, caught
spec     <- cm["0", "0"] / sum(cm[, "0"])   # of those who didn't, caught

cat("\n---- Confusion matrix (threshold 0.5, in-sample) ----\n")
print(cm)
cat(sprintf("\nAccuracy      : %.3f  (no-information base rate = %.3f, lift = %+.3f)\n",
            accuracy, max(base_rate, 1 - base_rate),
            accuracy - max(base_rate, 1 - base_rate)))
cat(sprintf("Sensitivity   : %.3f  (advanced correctly identified)\n", sens))
cat(sprintf("Specificity   : %.3f  (eliminated correctly identified)\n", spec))

# ---- AUC --------------------------------------------------------------------
auc_insample <- function(y, p) {
  if (has_pROC) return(as.numeric(pROC::auc(pROC::roc(y, p, quiet = TRUE))))
  # Mann-Whitney equivalence (handles ties via rank averaging).
  r  <- rank(p); n1 <- sum(y == 1); n0 <- sum(y == 0)
  (sum(r[y == 1]) - n1 * (n1 + 1) / 2) / (n0 * n1)
}
cat(sprintf("AUC           : %.3f  %s\n", auc_insample(model_df$advanced, p_hat),
            if (has_pROC) "(pROC)" else "(manual; install pROC for the package version)"))
cat("NOTE: in-sample -- see the out-of-sample split in section 8.\n")


# =============================================================================
# 7b. SEPARATION CHECK  (guard -- should now pass, OFC removed upstream)
# -----------------------------------------------------------------------------
#   Logistic regression breaks down under perfect / quasi-separation: if some
#   predictor (or combination) splits the outcome cleanly, the MLE runs off to
#   infinity and glm() reports a huge coefficient with an even huger SE while
#   still "converging". The one known separated cell -- confOTHER (the 2 OFC /
#   New Zealand rows with 0 advancers) -- is now dropped at load (section 1), so
#   this check is a guard that should report OK for BOTH models. If it ever fires
#   again, name the term and refit with Firth's penalized likelihood (logistf).
# =============================================================================
sep_check <- function(lbl, m) {
  co  <- summary(m)$coefficients
  bad <- which(abs(co[, "Estimate"]) > 10 | co[, "Std. Error"] > 10)
  cat(sprintf("[%s] ", lbl))
  if (length(bad)) {
    cat("WARNING: possible separation -- |beta| or SE > 10 for:",
        paste(rownames(co)[bad], collapse = ", "), "\n")
    cat("  Do NOT trust their Wald CIs. Refit with Firth:",
        if (has_logistf) "logistf::logistf(formula(m), data = model_df)\n"
        else "install.packages('logistf') then logistf::logistf(...)\n")
  } else {
    cat(sprintf("OK: all |beta| and SE < 10 (converged = %s). No separation.\n",
                m$converged))
  }
}
cat("\n---- Separation check ----\n")
sep_check("Model 1 inferential", fit_infer)
sep_check("Model 2 selected",    fit_sel)


# #############################################################################
# ## 8. OUT-OF-SAMPLE VALIDATION -- train (<2010) / test (>=2010)             ##
# #############################################################################
# =============================================================================
#   The honest read on predictive skill: fit on the OLDER tournaments and score
#   the HELD-OUT recent ones. We refit the PRE-SPECIFIED `f_structural` on the
#   training years (no stepwise here, so the test set never touches model
#   selection), then predict the test tournaments.
#
#   Split: train = 1970-2006 (n ~ 239), test = 2010, 2014, 2018, 2022 (n ~ 127).
#   All five confederations and both binary flags appear in each split, so the
#   refit sees no unseen factor level.
#
#   *** THE REAL BENCHMARK IS 2026. ***  This 2010 split is the in-data dry run.
#   The genuinely interesting test is scoring the model on the 2026 World Cup
#   group stage once those results exist -- a true forward, out-of-sample check
#   no part of this analysis has seen. Section 8b scaffolds that; fill it in when
#   the 2026 group-stage table is available.
# =============================================================================
train <- subset(model_df, year <  2010)
test  <- subset(model_df, year >= 2010)

# Keep the test set's `conf` on the SAME factor levels as training so predict()
# is well-defined even for a level that happens to be rare in one split.
train$conf <- factor(train$conf, levels = levels(model_df$conf))
test$conf  <- factor(test$conf,  levels = levels(model_df$conf))

fit_train <- glm(f_structural, family = binomial(link = "logit"), data = train)

p_test    <- predict(fit_train, newdata = test, type = "response")
test_base <- mean(test$advanced)
pred_test <- as.integer(p_test >= 0.5)

cm_test <- table(Predicted = factor(pred_test, levels = c(0, 1)),
                 Actual    = factor(test$advanced, levels = c(0, 1)))
acc_test <- sum(diag(cm_test)) / sum(cm_test)
auc_test <- auc_insample(test$advanced, p_test)   # here it is genuinely OOS

cat("\n================ OUT-OF-SAMPLE: train <2010 / test >=2010 ================\n")
cat(sprintf("train n = %d (base rate %.3f) | test n = %d (base rate %.3f)\n",
            nrow(train), mean(train$advanced), nrow(test), test_base))
cat("\n---- Test-set confusion matrix (threshold 0.5) ----\n")
print(cm_test)
cat(sprintf("\nTest accuracy : %.3f  (test no-information rate = %.3f, lift = %+.3f)\n",
            acc_test, max(test_base, 1 - test_base),
            acc_test - max(test_base, 1 - test_base)))
cat(sprintf("Test AUC      : %.3f  (out-of-sample discrimination)\n", auc_test))
cat("Read: compare test AUC/accuracy to the in-sample numbers in section 7 --\n",
    "     a large drop means the in-sample fit was optimistic.\n", sep = "")


# =============================================================================
# 8a. ROC CURVE FOR THE TEST SPLIT  (>=2010, out-of-sample)
# -----------------------------------------------------------------------------
#   Visualises the same discrimination that `auc_test` summarises: sweeping the
#   classification threshold from 1 down to 0 traces true-positive rate (of the
#   teams that advanced, the share caught) against false-positive rate (of the
#   teams eliminated, the share wrongly flagged). The 45-degree line is the
#   no-skill baseline (AUC 0.5); the further the curve bows toward the top-left,
#   the better. AUC is the area under this curve. Fit on train (<2010), scored on
#   the held-out test tournaments (2010, 2014, 2018, 2022) -- honest OOS skill.
#
#   Base R always works; pROC (if installed) draws the same curve with CI bands.
#   Saved to roc_test_2010.png next to diagnostics.png.
# =============================================================================
# Manual ROC points: order by predicted prob (desc), accumulate TPR/FPR. Ties are
# order-dependent for the exact step path but do not affect the AUC value above.
roc_points <- function(y, p) {
  ord <- order(p, decreasing = TRUE)
  y   <- y[ord]
  n1  <- sum(y == 1); n0 <- sum(y == 0)
  data.frame(fpr = c(0, cumsum(y == 0) / n0),
             tpr = c(0, cumsum(y == 1) / n1))
}
roc_test <- roc_points(test$advanced, p_test)

png("roc_test_2010.png", width = 1500, height = 1500, res = 220)
plot(roc_test$fpr, roc_test$tpr, type = "s", lwd = 2.5, col = "#2774AE",
     xlim = c(0, 1), ylim = c(0, 1), asp = 1,
     xlab = "False positive rate (1 - specificity)",
     ylab = "True positive rate (sensitivity)",
     main = "ROC curve -- out-of-sample test (>=2010)")
abline(0, 1, lty = 2, col = "grey50")             # no-skill baseline
legend("bottomright", bty = "n",
       legend = sprintf("Test AUC = %.3f  (n = %d)", auc_test, nrow(test)),
       col = "#2774AE", lwd = 2.5)
dev.off()
cat("\n[ROC] wrote roc_test_2010.png (test-split ROC, AUC = ",
    sprintf("%.3f", auc_test), ")\n", sep = "")

# pROC alternative (nicer axes + optional CI band) if the package is available:
if (has_pROC) {
  roc_obj <- pROC::roc(test$advanced, p_test, quiet = TRUE)
  png("roc_test_2010_proc.png", width = 1500, height = 1500, res = 220)
  plot(roc_obj, col = "#2774AE", lwd = 2.5, legacy.axes = TRUE,
       main = sprintf("ROC curve -- test >=2010 (pROC, AUC = %.3f)",
                      as.numeric(pROC::auc(roc_obj))))
  dev.off()
  cat("[ROC] wrote roc_test_2010_proc.png (pROC version)\n")
}


# =============================================================================
# 8b. THE 2026 BENCHMARK  (real forward test -- 2026 field, actual outcomes)
# -----------------------------------------------------------------------------
#   The genuine out-of-sample check: fit on ALL historical data (1970-2022) and
#   predict the 2026 group stage, which no part of the training ever saw. The
#   2026 table is built by scrape_worldcup_2026.py.
#
#   REDUCED SPEC (why not f_structural): the scraped 2026 file currently carries
#   only the non-squad predictors -- prior_tournaments, is_host, conf, year_c
#   (the squad terms avg_prior_wc/avg_age/forward_share/defender_share/
#   foreign_manager need the 2026 rosters and are NA). So we fit and predict a
#   REDUCED model on exactly the predictors available for 2026. This still
#   contains every term that was significant in Model 1 (is_host,
#   prior_tournaments, the confederation contrasts). To use the full
#   f_structural instead, first fill the squad columns (see the hook in
#   scrape_worldcup_2026.py) and swap f_available -> f_structural below.
#
#   TWO STRUCTURAL CAVEATS for 2026, both widening the expected error:
#     - Format change: 48 teams / 12 groups, top 2 + 8 best thirds advance, so
#       the base rate jumps to ~2/3 (vs ~0.53 in training). Judge accuracy
#       against THIS base rate, not the historical one.
#     - year_c = 8 extrapolates the era trend one cycle beyond the training
#       range (2022 = 7), so the year term is doing out-of-range work.
# =============================================================================
new26 <- read.csv("mens_groupstage_2026.csv", stringsAsFactors = FALSE)

# Match the training design: drop OFC (New Zealand) -- that level was removed
# from model_df for perfect separation, so the model has no confOFC coefficient
# and cannot score it. NZ finished bottom of Group G and did not advance.
new26 <- subset(new26, conf != "OFC")
new26$conf <- factor(new26$conf, levels = levels(model_df$conf))
stopifnot(!any(is.na(new26$conf)))   # every 2026 conf must be a trained level

# Reduced spec = the predictors present in the 2026 file (all Model-1-significant
# terms are here). Fit on the full 1970-2022 history, then predict 2026.
f_available <- advanced ~ prior_tournaments + is_host + conf + year_c
fit_hist  <- glm(f_available, family = binomial(link = "logit"), data = model_df)
p26       <- predict(fit_hist, newdata = new26, type = "response")

# ---- Score against the now-known 2026 outcomes ------------------------------
base26    <- mean(new26$advanced)
pred26    <- as.integer(p26 >= 0.5)
cm26      <- table(Predicted = factor(pred26, levels = c(0, 1)),
                   Actual    = factor(new26$advanced, levels = c(0, 1)))
acc26     <- sum(diag(cm26)) / sum(cm26)
auc26     <- auc_insample(new26$advanced, p26)   # genuinely out-of-sample

cat("\n================ 2026 FORWARD BENCHMARK (reduced spec) ================\n")
cat("Fit formula:", deparse(f_available), "\n")
cat(sprintf("2026 teams scored: %d (base rate advanced = %.3f)\n",
            nrow(new26), base26))
cat("\n---- 2026 confusion matrix (threshold 0.5) ----\n")
print(cm26)
cat(sprintf("\n2026 accuracy : %.3f  (no-information rate = %.3f, lift = %+.3f)\n",
            acc26, max(base26, 1 - base26), acc26 - max(base26, 1 - base26)))
cat(sprintf("2026 AUC      : %.3f  (forward out-of-sample discrimination)\n", auc26))

# ---- Ranked predicted probabilities (the payoff table / slide) --------------
rank26 <- new26[order(-p26), c("team_name", "group_name", "conf",
                               "prior_tournaments", "is_host", "advanced")]
rank26$p_advance <- round(p26[order(-p26)], 3)
cat("\n---- 2026 teams by predicted advancement probability ----\n")
print(rank26, row.names = FALSE)

# Optional: once the 2026 squad columns are populated, the FULL model is a
# one-line swap (drops nothing, adds the squad terms):
#   fit_hist_full <- glm(f_structural, family = binomial, data = model_df)
#   p26_full      <- predict(fit_hist_full, newdata = new26, type = "response")


# =============================================================================
# WHAT TO REPORT / NEXT STEPS
#   - INFERENCE: report Model 1 (pre-specified) odds ratios with the team-
#     clustered CIs, plus McFadden's pseudo-R^2 and the null LRT. These are the
#     honest significance numbers.
#   - SELECTION: report Model 2 as "which predictors AIC keeps", showing the
#     AIC vs BIC term sets; do NOT present its CIs as tests.
#   - PREDICTION: lead with the section-8 OUT-OF-SAMPLE test AUC/accuracy, not
#     the in-sample section-7 numbers, and judge both against the ~0.5 base rate.
#   - confOTHER (OFC / New Zealand 1982 & 2010, 2 rows, 0 advancers) is dropped
#     at load to remove perfect separation -- note this in the writeup.
#   - The 2026 World Cup is the real forward benchmark (section 8b).
#   - Companion scripts: poisson_mens_groupstage_model.R (points count) and
#     ordinal_mens_groupstage_points.R (points as ranks) -- same rows/predictors.
# =============================================================================
