rm( list = ls() )

# =============================================================================
# 01_data_transformation.R
# -----------------------------------------------------------------------------
# EDA / DATA-TRANSFORMATION STAGE for the men's World Cup group-stage analysis.
#
# This script does ALL of the data work and NONE of the modeling: it reads the
# raw worldcup_data/ CSVs, runs every sqldf join / aggregation / filter, builds
# the predictor blocks, assembles the one-row-per-team-per-tournament modeling
# table, recomputes a consistent scoring rule, restricts to 1970+, and writes
# the finished table to `mens_groupstage_1970on.csv`.
#
# The companion script `02_model_fitting.R` loads that CSV and fits the Poisson,
# logistic, and ordinal models. This file only needs to be re-run when the
# underlying raw data changes.
#
# (Consolidated from the pipeline in poisson_mens_groupstage.R, sections 1-3.)
#
# WHY THE KEY TRANSFORMATION DECISIONS ARE MADE THE WAY THEY ARE:
#   1. Men's-only, filter bug fixed at source.
#      An earlier pipeline used  LIKE '%Men''s%' , which SQLite matches
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
#      entirely and gives a consistent 0-9 count.
#
#   4. Predictors pruned downstream to avoid tautology and collinearity. The
#      transformation keeps ALL candidate columns; the pruning rationale lives
#      with the model specs in 02_model_fitting.R.
#
# OUTPUT:  mens_groupstage_1970on.csv
#          (one row = one team's group-stage campaign; men's, 1970+)
# =============================================================================


# ---- Setup ------------------------------------------------------------------
library(sqldf)

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

# Export the clean table for reuse (LaTeX/Tableau/the model-fitting script).
write.csv(model_df, "mens_groupstage_1970on.csv", row.names = FALSE)
cat("Wrote modeling table to: mens_groupstage_1970on.csv\n")

# =============================================================================
# NEXT STEP
#   Run 02_model_fitting.R, which loads mens_groupstage_1970on.csv and fits the
#   Poisson (points_std), logistic (advanced), and ordinal (points_ord) models.
# =============================================================================
