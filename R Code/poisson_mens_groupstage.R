rm( list = ls() )

# =============================================================================
# poisson_mens_groupstage.R
# -----------------------------------------------------------------------------
# Builds a clean, Poisson-ready modeling table of MEN'S World Cup group-stage
# campaigns (1970 onward), uses stepwise AIC/BIC selection to choose predictors,
# fits the resulting Poisson GLM, and reports overall fit (pseudo-R^2) with
# team-clustered standard errors.
#
# WHY THIS SCRIPT EXISTS (design decisions baked in):
#   1. Men's-only, filter bug fixed at source.
#      The original pipeline used  LIKE '%Men''s%' , which SQLite matches
#      case-insensitively, so "FIFA WOmen's" also passed. We use
#      LIKE '%FIFA Men''s%'  instead, which cleanly excludes women's
#      tournaments (verified: 490 men's rows, 0 women's leakage).
#
#   2. 1970 onward only.
#      Booking (card) data begins in 1970, and from 1970 on EVERY team plays
#      exactly 3 group games -> the outcome denominator is fixed, so no
#      exposure offset is needed and points are directly comparable.
#
#   3. Single, era-invariant scoring rule:  points_std = 3*wins + draws.
#      The raw `points` column uses 2 points-for-a-win before 1994 and 3 after,
#      which changes BOTH the scale (max 6 vs 9) AND the value of a draw
#      relative to a win. Recomputing 3-1-0 for all years removes that artifact
#      entirely and gives a consistent 0-9 count that is a legitimate Poisson
#      response.
#
#   4. Predictors pruned to avoid tautology and collinearity (see section 4).
#
# OUTCOME:  points_std  (0-9 count, one row = one team's group-stage campaign)
# =============================================================================


# ---- Setup ------------------------------------------------------------------
library(sqldf)

# Optional packages for team-clustered SEs. The core fit and selection run
# without them; the clustered-SE block is skipped with a message if absent.
has_sandwich <- requireNamespace("sandwich", quietly = TRUE)   # clustered vcov
has_lmtest   <- requireNamespace("lmtest",   quietly = TRUE)   # coeftest

data_dir <- "worldcup_data"                       # adjust if you move the script
rd <- function(f) read.csv(file.path(data_dir, f), stringsAsFactors = FALSE)

group_standings      <- rd("group_standings.csv")
teams                <- rd("teams.csv")
tournaments          <- rd("tournaments.csv")
squads               <- rd("squads.csv")
players              <- rd("players.csv")
bookings             <- rd("bookings.csv")
host_countries       <- rd("host_countries.csv")
manager_appointments <- rd("manager_appointments.csv")


# =============================================================================
# 1. BASE TABLE: one row per team per group stage (MEN'S tournaments only)
#    Fixed men's filter + standard first/only group stage so points compare.
# =============================================================================
base <- sqldf("
  SELECT gs.tournament_id, gs.team_id, gs.team_name,
         gs.group_name, gs.played, gs.wins, gs.draws, gs.losses,
         gs.goals_for, gs.goals_against, gs.goal_difference,
         gs.points AS points_raw, gs.advanced,
         t.confederation_code, t.region_name,
         tp.year
  FROM group_standings gs
  LEFT JOIN teams       t  ON gs.team_id       = t.team_id
  LEFT JOIN tournaments tp ON gs.tournament_id = tp.tournament_id
  WHERE gs.tournament_name LIKE '%FIFA Men''s%'          -- <- bug fix
    AND gs.stage_name IN ('group stage', 'first group stage')
")


# =============================================================================
# 2. PREDICTOR BLOCKS  (each aggregated to one row per tournament_id, team_id)
#    Men's filter fixed in every block that carries one.
# =============================================================================

# --- Team experience: # of prior men's tournaments this team appeared in -----
team_experience <- sqldf("
  SELECT DISTINCT gs.tournament_id, gs.team_id,
    (SELECT COUNT(DISTINCT g2.tournament_id)
       FROM group_standings g2
       JOIN tournaments t2 ON g2.tournament_id = t2.tournament_id
      WHERE g2.team_id = gs.team_id
        AND g2.tournament_name LIKE '%FIFA Men''s%'
        AND t2.year < tp.year) AS prior_tournaments
  FROM group_standings gs
  JOIN tournaments tp ON gs.tournament_id = tp.tournament_id
  WHERE gs.tournament_name LIKE '%FIFA Men''s%'
    AND gs.stage_name IN ('group stage', 'first group stage')
")

# --- Squad composition & age -------------------------------------------------
#     avg_age  = tournament year minus player birth year (approximate).
#       78 players have birth_date = 'not available'; the GLOB guard nulls them
#       so AVG ignores them (otherwise avg_age blows up to ~1400).
#     avg_career_tournaments is LEAKY (whole career incl. future) -> excluded
#       from the model spec; kept here only for reference.
squad_stats <- sqldf("
  SELECT s.tournament_id, s.team_id,
         COUNT(*)                                                           AS squad_size,
         AVG(CASE WHEN substr(p.birth_date, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'
                  THEN tp.year - CAST(substr(p.birth_date, 1, 4) AS INTEGER)
             END)                                                           AS avg_age,
         1.0*SUM(CASE WHEN s.position_code='FW' THEN 1 ELSE 0 END)/COUNT(*) AS forward_share,
         1.0*SUM(CASE WHEN s.position_code='DF' THEN 1 ELSE 0 END)/COUNT(*) AS defender_share,
         AVG(p.count_tournaments)                                           AS avg_career_tournaments
  FROM squads s
  JOIN players     p  ON s.player_id     = p.player_id
  JOIN tournaments tp ON s.tournament_id = tp.tournament_id
  GROUP BY s.tournament_id, s.team_id
")

# --- Squad World Cup experience (CLEAN, non-leaky) ---------------------------
#     Per player, count PRIOR men's World Cups (t2.year < tp.year) then
#     aggregate: avg_prior_wc / max_prior_wc / debutant_share.
squad_experience <- sqldf("
  SELECT s.tournament_id, s.team_id,
         AVG(prior)                                            AS avg_prior_wc,
         MAX(prior)                                            AS max_prior_wc,
         1.0*SUM(CASE WHEN prior=0 THEN 1 ELSE 0 END)/COUNT(*) AS debutant_share
  FROM (
    SELECT s.tournament_id, s.team_id, s.player_id,
      (SELECT COUNT(DISTINCT s2.tournament_id)
         FROM squads s2
         JOIN tournaments t2 ON s2.tournament_id = t2.tournament_id
        WHERE s2.player_id = s.player_id
          AND s2.tournament_name LIKE '%FIFA Men''s%'
          AND t2.year < tp.year) AS prior
    FROM squads s
    JOIN tournaments tp ON s.tournament_id = tp.tournament_id
    WHERE s.tournament_name LIKE '%FIFA Men''s%'
  ) s
  GROUP BY s.tournament_id, s.team_id
")

# --- Group-stage discipline (cards). Recorded from 1970 on. ------------------
cards <- sqldf("
  SELECT tournament_id, team_id,
         SUM(yellow_card)                     AS yellows,
         SUM(red_card + second_yellow_card)   AS reds,
         COUNT(*)                             AS total_cards
  FROM bookings
  WHERE stage_name = 'group stage'
  GROUP BY tournament_id, team_id
")

# --- Host nation flag --------------------------------------------------------
host <- sqldf("SELECT DISTINCT tournament_id, team_id, 1 AS is_host
               FROM host_countries")

# --- Foreign manager flag (approx: manager country != team name) -------------
manager <- sqldf("
  SELECT tournament_id, team_id,
         MAX(CASE WHEN country_name <> team_name THEN 1 ELSE 0 END) AS foreign_manager
  FROM manager_appointments
  GROUP BY tournament_id, team_id
")


# =============================================================================
# 3. ASSEMBLE, RECOMPUTE points_std, FILTER TO 1970+
# =============================================================================
model_full <- sqldf("
  SELECT b.*,
         e.prior_tournaments,
         sq.squad_size, sq.avg_age, sq.forward_share, sq.defender_share,
         sq.avg_career_tournaments,
         xp.avg_prior_wc, xp.max_prior_wc, xp.debutant_share,
         COALESCE(c.yellows, 0)         AS yellows,
         COALESCE(c.reds, 0)            AS reds,
         COALESCE(c.total_cards, 0)     AS total_cards,
         COALESCE(h.is_host, 0)         AS is_host,
         COALESCE(m.foreign_manager, 0) AS foreign_manager
  FROM base b
  LEFT JOIN team_experience  e  ON b.tournament_id=e.tournament_id  AND b.team_id=e.team_id
  LEFT JOIN squad_stats      sq ON b.tournament_id=sq.tournament_id AND b.team_id=sq.team_id
  LEFT JOIN squad_experience xp ON b.tournament_id=xp.tournament_id AND b.team_id=xp.team_id
  LEFT JOIN cards            c  ON b.tournament_id=c.tournament_id  AND b.team_id=c.team_id
  LEFT JOIN host             h  ON b.tournament_id=h.tournament_id  AND b.team_id=h.team_id
  LEFT JOIN manager          m  ON b.tournament_id=m.tournament_id  AND b.team_id=m.team_id
")

# ---- THE CLEANER FIX: single 3-1-0 rule for all years -----------------------
#   points_std removes the pre/post-1994 scoring-rule artifact (2 vs 3 pts for
#   a win) so the outcome is one consistent 0-9 count across the whole window.
model_full$points_std <- 3 * model_full$wins + model_full$draws

# ---- Restrict to 1970+ (cards exist; every team plays exactly 3 games) ------
model_df <- subset(model_full, year >= 1970)

# ---- Guardrail: from 1970 on, all group campaigns are exactly 3 games -------
#   If this ever fails, the fixed-denominator assumption is broken and you
#   would need an offset (log(played)) in the Poisson model.
stopifnot(all(model_df$played == 3))

# ---- Collapse the rare OFC confederation (only ~2 rows = New Zealand) --------
#   A 2-observation factor level is high-leverage / near-unidentifiable.
#   Default: lump into "OTHER". (Alternative: drop those rows -- see note.)
model_df$conf <- model_df$confederation_code
model_df$conf[model_df$conf %in% c("OFC")] <- "OTHER"
model_df$conf <- relevel(factor(model_df$conf), ref = "UEFA")   # UEFA = baseline

# ---- Era term: center year so the intercept is interpretable ----------------
#   year_c is in 4-year units centered on 1994 (the mid-era pivot).
model_df$year_c <- (model_df$year - 1994) / 4

# ---- Unique per-row identifier (for Tableau / disaggregated plotting) --------
#   row_id   = stable integer key, 1..N (guaranteed unique per campaign).
#   campaign = readable unique label, e.g. "Brazil 1970" (team_name + year).
#   Neither is a model predictor -- they exist so each row can be plotted as its
#   own mark in Tableau instead of being averaged by team_name / team_id.
model_df$row_id   <- seq_len(nrow(model_df))
model_df$campaign <- paste(model_df$team_name, model_df$year)
id_cols  <- c("row_id", "campaign")
model_df <- model_df[, c(id_cols, setdiff(names(model_df), id_cols))]

cat(sprintf("Modeling table: %d rows x %d cols (men's, 1970+)\n",
            nrow(model_df), ncol(model_df)))
cat("points_std range:", range(model_df$points_std),
    "| mean:", round(mean(model_df$points_std), 2),
    "| var:",  round(var(model_df$points_std), 2), "\n")

# Export the clean table for reuse (LaTeX/Tableau/other scripts).
write.csv(model_df, "mens_groupstage_1970on.csv", row.names = FALSE)


# =============================================================================
# 4. CANDIDATE MODEL SPEC  (which variables, and why NOT the others)
# -----------------------------------------------------------------------------
# The request was to use "most, if not all" variables. The binding constraint
# is that many columns are mechanically tied to the outcome or to each other,
# so a Poisson fit on ALL of them would be tautological and/or unidentifiable.
# Pruning rules applied:
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
# NOT independent. We report team-clustered SEs in section 6.
# =============================================================================
model_df <- read.csv("mens_groupstage_1970on.csv")

# ---- Drop the OFC / confOTHER cell (perfect separation in the logit sibling) -
#   `conf == "OTHER"` is the collapsed OFC (Oceania) bucket: exactly 2 rows,
#   NEW ZEALAND 1982 and NEW ZEALAND 2010 -- the only Oceania entries in the
#   1970+ men's data, both with advanced = 0. That cell is perfectly separated
#   in the logistic sibling (confOTHER coefficient -> -Inf). Dropping those 2
#   rows here too (368 -> 366) keeps this Poisson fit on the SAME row set as the
#   other model scripts. NOTE: this drop is applied to the MODELING step only --
#   the build/`write.csv` above still writes the full 368-row table, so the CSV
#   on disk is unchanged. (Done consistently across all model scripts.)
model_df <- subset(model_df, confederation_code != "OFC")

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
# 5. STEPWISE VARIABLE SELECTION (AIC & BIC), THEN FIT THE CHOSEN MODEL
# -----------------------------------------------------------------------------
#   Selection runs on the PRE-PRUNED candidate pool (section 4), so the leaky /
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
# 6. TEAM-CLUSTERED STANDARD ERRORS (honest variable significance)
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
# 7. RESIDUAL DIAGNOSTICS
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
