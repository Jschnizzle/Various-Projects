rm( list = ls() )

# =============================================================================
# ordinal_mens_groupstage_points.R
# -----------------------------------------------------------------------------
# THIRD companion model. Loads the already-built modeling table from
# `mens_groupstage_1970on.csv` and fits an ORDINAL (proportional-odds)
# regression for a men's World Cup team's group-stage points, treating
# `points_std` as an ORDERED CATEGORICAL outcome rather than a count.
#
# Like `poisson_mens_groupstage_model.R` and `logit_mens_groupstage_advance.R`,
# this is the MODEL-ONLY script: the data-processing pipeline (raw
# worldcup_data/ CSVs, men's/group-stage filters, predictor aggregation, the
# points_std recompute, the 1970+ cut) lives in `poisson_mens_groupstage.R` and
# only needs re-running when the underlying data changes.
#
# OUTCOME:  points_ord  -- points_std as an ordered factor over {0..7, 9}
#
# WHY ORDINAL RATHER THAN POISSON:
#   The Poisson model treats points_std as an unbounded count. It isn't. Over
#   exactly 3 games, points_std = 3*wins + draws can only take the 9 values
#   {0,1,2,3,4,5,6,7,9}: 8 is STRUCTURALLY IMPOSSIBLE (there is no combination
#   of 3 results that sums to 8), and the gaps between adjacent attainable
#   values are not uniform in meaning. An ordinal model uses only the RANK
#   ORDER of the outcome, so it makes no spacing assumption, is untroubled by
#   the missing 8, and respects the hard ceiling at 9.
#   The tradeoff is interpretation: cumulative odds ratios instead of the
#   Poisson's rate ratios. Reporting both side by side is the point.
# =============================================================================


# =============================================================================
# CAVEATS TO CARRY INTO THE WRITEUP
# -----------------------------------------------------------------------------
# (a) THE OUTCOME'S SUPPORT IS IRREGULAR. `points_ord` has 9 levels, and 8 is
#     deliberately NOT among them -- it is unattainable, not merely unobserved,
#     so inserting it as an empty level would be wrong. Read the levels as
#     RANKS, not as evenly spaced scores: the step 7 -> 9 is one rank but two
#     points, and the model only ever uses the ordering.
#
# (b) ERA STABILITY. Post-1970 the meaning of a point total is fairly stable --
#     every team plays exactly 3 group games, and points_std restates all of
#     them under one recomputed 3-1-0 rule (the raw 2-1-0 era is already
#     converted upstream). `year_c` is retained anyway to absorb residual era
#     drift, consistent with the sibling models.
# =============================================================================


# ---- Setup ------------------------------------------------------------------
# `ordinal` is the primary engine (clm / clmm / nominal_test). MASS::polr is the
# fallback if it is absent. Each optional block is skipped with a message.
has_ordinal <- requireNamespace("ordinal", quietly = TRUE)  # clm, clmm, nominal_test
has_MASS    <- requireNamespace("MASS",    quietly = TRUE)  # polr fallback
has_brant   <- requireNamespace("brant",   quietly = TRUE)  # PO test for polr
has_VGAM    <- requireNamespace("VGAM",    quietly = TRUE)  # non-PO fallback

if (!has_ordinal && !has_MASS)
  stop("Need either `ordinal` or `MASS`: install.packages(c('ordinal','MASS'))")

engine <- if (has_ordinal) "ordinal::clm" else "MASS::polr"
cat(sprintf("Ordinal engine: %s\n", engine))


# =============================================================================
# 1. LOAD THE PRE-BUILT MODELING TABLE
# -----------------------------------------------------------------------------
#   Built by poisson_mens_groupstage.R: men's, group stage, 1970+, with
#   points_std already recomputed on the 3-1-0 scale.
# =============================================================================
model_df <- read.csv("mens_groupstage_1970on.csv", stringsAsFactors = FALSE)

# ---- Drop the OFC / confOTHER cell (perfect separation in the logit sibling) -
#   `conf == "OTHER"` is the collapsed OFC (Oceania) bucket: exactly 2 rows,
#   NEW ZEALAND 1982 and NEW ZEALAND 2010 -- the only Oceania entries in the
#   1970+ men's data, both with advanced = 0. In the logistic model this cell is
#   perfectly separated (confOTHER coefficient -> -Inf). We drop those 2 rows
#   here as well (368 -> 366) so every sibling model uses the SAME row set and no
#   near-empty confederation level is estimated. Oceania carried no advancement
#   information anyway. (Done consistently across all model scripts.)
model_df <- subset(model_df, confederation_code != "OFC")

# ---- Restore factor structure that CSV storage flattens ---------------------
#   `conf` was written as plain text; re-establish it as a factor with UEFA as
#   the baseline so the coefficients read the same way as in the sibling
#   scripts. With the OFC rows gone, factor() no longer carries an "OTHER" level.
#   Without this the baseline defaults to alphabetical (AFC).
model_df$conf <- relevel(factor(model_df$conf), ref = "UEFA")

# ---- Sanity checks on the loaded table --------------------------------------
#   Fixed 3-game denominator, 1970+ only, and the outcome confined to its 9
#   attainable values (the third check is what guarantees no stray 8 appears).
stopifnot(all(model_df$played == 3))
stopifnot(all(model_df$year >= 1970))
stopifnot(all(model_df$points_std %in% c(0, 1, 2, 3, 4, 5, 6, 7, 9)))

# ---- Build the ordered outcome ----------------------------------------------
#   Levels are the OBSERVED values in ascending order. 8 is absent because it
#   cannot occur; do not pad the level set.
model_df$points_ord <- factor(model_df$points_std,
                              levels  = sort(unique(model_df$points_std)),
                              ordered = TRUE)

cat(sprintf("Modeling table: %d rows x %d cols (men's, 1970+)\n",
            nrow(model_df), ncol(model_df)))
cat(sprintf("points_ord: %d ordered levels -> %s\n",
            nlevels(model_df$points_ord),
            paste(levels(model_df$points_ord), collapse = " < ")))
cat("Outcome distribution:\n")
print(table(model_df$points_ord))


# =============================================================================
# 2. CANDIDATE MODEL SPEC  (which variables, and why NOT the others)
# -----------------------------------------------------------------------------
# Identical pre-pruned pool to the Poisson and logistic models -- deliberately
# so, because the three analyses are meant to be directly comparable (same
# rows, same predictors, three different treatments of the same result:
# HOW MANY points as a count / DID THEY QUALIFY / WHERE ON THE ORDERED SCALE).
#
#   EXCLUDED - deterministic functions of the result (they would tautologically
#              predict points):
#       wins, draws, losses            (points_std = 3*wins + draws)
#       points_std                     (the numeric source of the outcome)
#       points_raw                     (old 2-1-0 version of the outcome)
#       advanced, position             (derived from the final group ranking)
#       goals_for, goals_against,      (downstream match results; and
#         goal_difference)               goal_difference = GF - GA exactly)
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
# NOT independent. Section 7 refits with a team random intercept.
# =============================================================================

f_candidate <- points_ord ~ prior_tournaments + avg_prior_wc +
                            avg_age + forward_share + defender_share + squad_size +
                            is_host + foreign_manager + conf + year_c +
                            total_cards

# A leaner "pre-tournament only" spec (drops discipline, which is measured
# DURING the tournament), for a cleaner inference story.
f_structural <- points_ord ~ prior_tournaments + avg_prior_wc +
                             avg_age + forward_share + defender_share +
                             is_host + foreign_manager + conf + year_c


# =============================================================================
# 3. FIT THE CUMULATIVE LINK (PROPORTIONAL-ODDS) MODEL
# -----------------------------------------------------------------------------
#   logit[ P(Y <= j) ] = theta_j - x'beta
#   One set of slopes beta shared across all 8 cutpoints (that IS the
#   proportional-odds assumption, tested in section 4); 8 thresholds theta_j
#   for the 9 levels. NOTE the minus sign in the parameterisation used by both
#   clm and polr: a POSITIVE beta pushes probability toward HIGHER categories.
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
#   clm reports cond.H ~ 1e7 and may warn "nearly unidentifiable: large
#   eigenvalue ratio". This is a SCALING artefact, not a real identification
#   problem: avg_age (~27), squad_size (~22) and year_c (~ -6..6) live on very
#   different scales from the share variables (0..1), so the Hessian is badly
#   conditioned. The fit itself converged cleanly (max.grad ~1e-12) and the
#   slopes are trustworthy; the visible symptom is that all 8 THRESHOLDS carry
#   a large common SE (~4.4), because they are estimated relative to a linear
#   predictor centred far from zero. Centring/scaling the continuous predictors
#   would fix the conditioning and shrink the threshold SEs WITHOUT changing
#   any slope, odds ratio, log-likelihood or p-value. We keep the raw scales so
#   the coefficients stay directly comparable to the Poisson and logistic
#   siblings; read the thresholds as nuisance parameters, not as estimates of
#   interest.
if (has_ordinal)
  cat(sprintf("cond.H = %.2g  (large = scaling artefact; see comment above -- slopes unaffected)\n",
              tryCatch(fit$cond.H, error = function(e) NA_real_)))

cat("\n---- Candidate vs structural spec ----\n")
cat(sprintf("f_candidate  (with total_cards): AIC %.1f | BIC %.1f\n",
            AIC(fit), BIC(fit)))
cat(sprintf("f_structural (pre-tournament)  : AIC %.1f | BIC %.1f\n",
            AIC(fit_struct), BIC(fit_struct)))


# =============================================================================
# 4. PROPORTIONAL-ODDS ASSUMPTION CHECK  (the key ordinal diagnostic)
# -----------------------------------------------------------------------------
#   The PO assumption says one slope per predictor works at EVERY cutpoint --
#   i.e. the effect of being host on "0 vs more than 0" is the same as on
#   "7 or less vs 9". nominal_test() relaxes that one term at a time and runs a
#   likelihood-ratio test: a SMALL p-value means that term's effect genuinely
#   differs across cutpoints, so the shared-slope model is misspecified FOR
#   THAT TERM.
#   Remedy if violated: a partial-PO model, `clm(..., nominal = ~ <term>)`,
#   which frees that one predictor to have its own slope per cutpoint while the
#   rest stay proportional. VGAM::vglm(family = cumulative(parallel = FALSE))
#   is the fully non-proportional alternative.
#   scale_test() is a different question (does the latent scale vary with x)
#   and is reported as a secondary check.
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
          "\n         (freeing these gives a non-identifiable fit -- with per-cutpoint",
          "slopes the\n         cumulative curves cross and the thresholds stop being",
          "monotone, so clm\n         cannot fit the alternative. Their PO status is",
          "UNTESTED, not confirmed.)\n")
    cat("  [note] 5 terms were testable, so treat borderline p-values (~.02) with",
        "a\n         multiple-comparison grain of salt.\n")

    # ---- Partial-PO refit, if any term violated ------------------------------
    #   Free ONLY the offending terms to have their own slope per cutpoint; all
    #   others stay proportional. If this beats the PO model on AIC/LRT, the
    #   violation is materially affecting the fit and should be reported.
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
# 5. CUMULATIVE ODDS RATIOS AND CONFIDENCE INTERVALS
# -----------------------------------------------------------------------------
#   INTERPRETATION: exp(beta) is the multiplicative change in the odds of
#   landing in a HIGHER points category (vs all lower ones), the same at every
#   cutpoint under proportional odds. OR > 1 = the predictor shifts a team
#   UP the points scale; OR < 1 = down; a CI spanning 1 = no detectable shift.
#   Thresholds are nuisance parameters and are not exponentiated here.
# =============================================================================
beta <- if (has_ordinal) fit$beta else coef(fit)

# Profile-likelihood CIs are the clm default and are better behaved than Wald;
# fall back to Wald if the profile fails to bracket.
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
# 6. OVERALL FIT
# -----------------------------------------------------------------------------
#   No true R^2 exists for a cumulative link model. McFadden compares the
#   fitted log-likelihood to the intercept-only ordinal model's; on its own
#   scale 0.2-0.4 is already an excellent fit, so it reads much lower than an
#   OLS R^2. The LRT asks whether the predictors jointly beat the thresholds
#   alone.
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
# 7. PREDICTIVE PERFORMANCE (ordinal-aware, IN-SAMPLE)
# -----------------------------------------------------------------------------
#   With 9 classes, exact accuracy is a harsh metric and the no-information
#   baseline is low (always guess the modal class, points = 4, ~19%). Because
#   the outcome is ORDERED, WITHIN-ONE accuracy (predicted rank within +/- 1 of
#   the observed rank) is the more honest headline: missing 4 with a 5 is a far
#   better error than missing it with a 0, and plain accuracy cannot see that.
#   Kendall's tau-b / Spearman on the ranks measure ordinal association
#   directly and are the cleanest single summary.
#
#   NOTE the +/- 1 rank step is a RANK step, not a points step: the 7 -> 9 pair
#   is adjacent in rank even though it is 2 points apart.
#
#   All of this is IN-SAMPLE -- the model was fit on these same rows, so the
#   numbers are optimistic. For honest predictive error, split train
#   year < 2010 / test year >= 2010, refit on the training rows and score the
#   held-out recent tournaments.
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
# 8. NON-INDEPENDENCE: TEAM RANDOM INTERCEPT (clmm robustness check)
# -----------------------------------------------------------------------------
#   The same nation recurs across tournaments (Brazil appears ~14 times), so
#   rows are not independent and the model-based SEs above are optimistic.
#   The cumulative-link analogue of clustered SEs is a MIXED model: give each
#   team its own random intercept on the latent scale, so persistent
#   nation-level quality is absorbed rather than being credited to the fixed
#   effects. The random-intercept variance is itself the quantity of interest --
#   a large one says a lot of the signal is just "which country is this".
#   clmm is slow (numerical integration over the random effects); if it fails
#   to converge we report the caveat rather than a bad fit.
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
    # Share of total latent variance attributable to team, using the logistic
    # residual variance pi^2/3 -- the ordinal analogue of an ICC.
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
# WHAT TO REPORT / NEXT STEPS
#   - Report the cumulative odds ratios with CIs and the threshold cutpoints;
#     cite McFadden's pseudo-R^2 and the null LRT for overall fit.
#   - Lead the predictive block with WITHIN-ONE accuracy and tau-b, not exact
#     accuracy -- 9 ordered classes make exact accuracy misleadingly harsh.
#   - The nominal_test result decides whether the single-slope story is
#     defensible; if a term violates PO, refit with `nominal = ~ that_term`
#     and report its per-cutpoint slopes instead.
#   - Compare against the siblings: the Poisson model (rate ratios on the same
#     outcome) and the logistic model (advanced yes/no). Signs should agree;
#     if one flips, that is worth explaining in the writeup.
#   - Post-hoc note: this script does NOT run stepwise selection -- the spec is
#     pre-specified, so the p-values here are not post-selection-optimistic the
#     way the Poisson/logistic stepwise ones are.
# =============================================================================
