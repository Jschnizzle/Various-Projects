# =============================================================================
# Homework 5 - Group-stage points models
# Builds a team-per-tournament modeling table from the World Cup CSVs using
# sqldf, then fits lm() for each of the five points-based options.
#
# Outcome variable: group-stage POINTS (0-9) per team per tournament.
# One row = one team's group-stage campaign in one men's World Cup.
# =============================================================================

# ---- Setup ------------------------------------------------------------------
library(sqldf)

# Folder holding the 38 CSVs. Adjust if you move the script.
data_dir <- "worldcup_data"
rd <- function(f) read.csv(file.path(data_dir, f), stringsAsFactors = FALSE)

group_standings     <- rd("group_standings.csv")
teams               <- rd("teams.csv")
tournaments         <- rd("tournaments.csv")
squads              <- rd("squads.csv")
players             <- rd("players.csv")
bookings            <- rd("bookings.csv")
host_countries      <- rd("host_countries.csv")
manager_appointments<- rd("manager_appointments.csv")

# =============================================================================
# 1. BASE TABLE: one row per team per group stage (men's tournaments only)
#    Filtered to the standard first/only group stage so `points` is comparable.
#    (Excludes second-group-stage / final-round round robins of 1974-1982.)
# =============================================================================
base <- sqldf("
  SELECT gs.tournament_id, gs.team_id, gs.team_name,
         gs.group_name, gs.played, gs.wins, gs.draws, gs.losses,
         gs.goals_for, gs.goals_against, gs.goal_difference, gs.points,
         gs.advanced,
         t.confederation_code, t.region_name,
         tp.year
  FROM group_standings gs
  LEFT JOIN teams       t  ON gs.team_id       = t.team_id
  LEFT JOIN tournaments tp ON gs.tournament_id = tp.tournament_id
  WHERE gs.tournament_name LIKE '%Men''s%'
    AND gs.stage_name IN ('group stage', 'first group stage')
")

# =============================================================================
# 2. PREDICTOR BLOCKS  (each aggregated to one row per tournament_id, team_id)
# =============================================================================

# --- Team experience: # of prior men's tournaments this team appeared in -----
#     Clean, non-leaky covariate (counts only tournaments before this year).
team_experience <- sqldf("
  SELECT DISTINCT gs.tournament_id, gs.team_id,
    (SELECT COUNT(DISTINCT g2.tournament_id)
       FROM group_standings g2
       JOIN tournaments t2 ON g2.tournament_id = t2.tournament_id
      WHERE g2.team_id = gs.team_id
        AND g2.tournament_name LIKE '%Men''s%'
        AND t2.year < tp.year) AS prior_tournaments
  FROM group_standings gs
  JOIN tournaments tp ON gs.tournament_id = tp.tournament_id
  WHERE gs.tournament_name LIKE '%Men''s%'
    AND gs.stage_name IN ('group stage', 'first group stage')
")

# --- Squad composition & age -------------------------------------------------
#     avg_age  = tournament year minus player birth year (approximate).
#       78 players have birth_date = 'not available'; the CASE/GLOB guard sets
#       those to NULL so AVG ignores them (otherwise avg_age blows up to ~1400).
#     *_share  = fraction of the squad at that position.
#     avg_career_tournaments = player-level career total from players.csv.
#       NOTE: this counts a player's WHOLE career (incl. future tournaments),
#       so it leaks information. Prefer prior_tournaments for clean inference;
#       included here only as an alternative experience proxy.
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
#     Per player, count prior men's World Cups they appeared in (squads table),
#     using t2.year < tp.year so only PAST tournaments count -> no leakage.
#     Then aggregate to the squad:
#       avg_prior_wc   = mean prior-WC appearances across the 23 players.
#       max_prior_wc   = experience of the most-capped player (veteran anchor).
#       debutant_share = fraction of the squad at their first World Cup.
#     This is the clean alternative to squad_stats$avg_career_tournaments.
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
          AND s2.tournament_name LIKE '%Men''s%'
          AND t2.year < tp.year) AS prior
    FROM squads s
    JOIN tournaments tp ON s.tournament_id = tp.tournament_id
    WHERE s.tournament_name LIKE '%Men''s%'
  ) s
  GROUP BY s.tournament_id, s.team_id
")

# --- Group-stage discipline (cards). Cards only recorded from 1970 on. --------
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

# --- Foreign manager flag ----------------------------------------------------
#     foreign_manager = 1 if manager nationality != team name.
#     Approximate: relies on string match between country_name and team_name.
manager <- sqldf("
  SELECT tournament_id, team_id,
         MAX(CASE WHEN country_name <> team_name THEN 1 ELSE 0 END) AS foreign_manager
  FROM manager_appointments
  GROUP BY tournament_id, team_id
")

# =============================================================================
# 3. ASSEMBLE THE MODELING TABLE (LEFT JOINs -> no row fan-out)
# =============================================================================
model_df <- sqldf("
  SELECT b.*,
         e.prior_tournaments,
         sq.squad_size, sq.avg_age, sq.forward_share, sq.defender_share,
         sq.avg_career_tournaments,
         xp.avg_prior_wc, xp.max_prior_wc, xp.debutant_share,
         COALESCE(c.yellows, 0)      AS yellows,
         COALESCE(c.reds, 0)         AS reds,
         COALESCE(c.total_cards, 0)  AS total_cards,
         COALESCE(h.is_host, 0)      AS is_host,
         COALESCE(m.foreign_manager, 0) AS foreign_manager
  FROM base b
  LEFT JOIN team_experience e ON b.tournament_id=e.tournament_id AND b.team_id=e.team_id
  LEFT JOIN squad_stats    sq ON b.tournament_id=sq.tournament_id AND b.team_id=sq.team_id
  LEFT JOIN squad_experience xp ON b.tournament_id=xp.tournament_id AND b.team_id=xp.team_id
  LEFT JOIN cards          c  ON b.tournament_id=c.tournament_id AND b.team_id=c.team_id
  LEFT JOIN host           h  ON b.tournament_id=h.tournament_id AND b.team_id=h.team_id
  LEFT JOIN manager        m  ON b.tournament_id=m.tournament_id AND b.team_id=m.team_id
")

cat("Modeling table:", nrow(model_df), "rows x", ncol(model_df), "cols\n")
summary(model_df[, c("points","goals_for","goals_against","prior_tournaments",
                     "avg_prior_wc","debutant_share",
                     "avg_age","forward_share","total_cards","is_host",
                     "foreign_manager")])

#write.csv(model_df, "transformed_data.csv")
# =============================================================================
# 4. MODELS  (each fits lm, prints summary + 95% CIs)
# =============================================================================

## ---- Option 1: direct goals model -----------------------------------------
## Caveat: points are mechanically driven by results, so goals_for/against
## are near-deterministic predictors. Good for discussing that limitation.
m1 <- lm(points ~ goals_for + goals_against, data = model_df)
summary(m1); confint(m1)

m1$coefficients[3]
## ---- Option 2: squad experience, age, and attacking shape -----------------
## Coefficient of interest: prior_tournaments (team experience),
## adjusting for squad age and forward share. Non-tautological.
m2 <- lm(points ~ prior_tournaments + avg_age + forward_share, data = model_df)
summary(m2); confint(m2)
## Alternative experience proxy (leaky - see note above):
## m2b <- lm(points ~ avg_career_tournaments + avg_age + forward_share, data = model_df)

## ---- Option 2c: CLEAN squad-level experience (recommended) -----------------
## Coefficient of interest: avg_prior_wc = mean prior-World-Cup appearances
## per player in the squad, adjusting for squad age and forward share.
## Unlike avg_career_tournaments this only looks backward, so it is non-leaky
## and directly comparable to the team-level prior_tournaments story.
m2c <- lm(points ~ avg_prior_wc + avg_age + forward_share + defender_share, data = model_df)
summary(m2c); confint(m2c)

## ---- Option 3: discipline (cards) -----------------------------------------
## Restrict to 1970+ since cards were not recorded before then.
## Coefficient of interest: total_cards, adjusting for scoring and era.
d3 <- subset(model_df, year >= 1970)
m3 <- lm(points ~ total_cards + goals_for + year, data = d3)
summary(m3); confint(m3)

## ---- Option 4: host advantage & region ------------------------------------
## Coefficient of interest: is_host, adjusting for confederation and era.
m4 <- lm(points ~ is_host + factor(confederation_code) + year, data = model_df)
summary(m4); confint(m4)

## ---- Option 5: experience & foreign manager -------------------------------
## Coefficient of interest: foreign_manager, adjusting for team experience & era.
m5 <- lm(points ~ prior_tournaments + foreign_manager + year, data = model_df)
summary(m5); confint(m5)

# =============================================================================
# 5. RESIDUAL DIAGNOSTICS (Question 2) - swap in whichever model you choose
# =============================================================================
par(mfrow = c(2, 2))
plot(m3)          # residuals vs fitted, Q-Q, scale-location, leverage
par(mfrow = c(1, 1))



# Try poisson models?
