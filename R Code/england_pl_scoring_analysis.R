# =============================================================================
# England World Cup group-stage performance vs. Premier League scoring
# -----------------------------------------------------------------------------
# Question: does Premier League scoring being UP or DOWN in the years between
# World Cups relate to how England perform in the group stage of the following
# World Cup?
#
# This script explores TWO angles for "PL scoring", side by side:
#   (A) LEAGUE-WIDE : total goals per game across every match in the league.
#   (B) TOP CLUBS   : goals scored per game by the TOP_N (=6) clubs by points
#                     each season (a proxy for the England talent pool).
#
# Approach (applied to BOTH scoring measures):
#   1. Reduce each PL season to the two scoring numbers above.
#   2. For each men's World Cup year Y, summarise scoring over the
#      inter-tournament window (the four seasons ending in Y-3 .. Y):
#        - mean   : average level across the window
#        - slope  : within-window trend (lm of scoring on season year)
#        - delta  : last-season value minus first-season value
#        - change : this window's mean minus the PREVIOUS window's mean
#                   (the cleanest "scoring up or down between cups" measure)
#   3. Merge with England's group-stage row for that tournament and explore
#      each angle via correlations, simple lm, and scatterplots.
#
# CAVEATS (read before trusting anything):
#   * England has only SEVEN men's World Cups in the PL era (1998-2022), so
#     n = 7. Every correlation / model below is exploratory, not inferential;
#     a single tournament can swing the results.
#   * transformed_data.csv contains BOTH men's and women's England rows. The
#     Premier League is the men's domestic league, so we keep men's World Cups
#     only (the standard 4-year cycle from 1930). Women's WC years (1995, 2007,
#     2011, 2015, 2019) are deliberately excluded.
#   * PL match stats start in 1993/94, so windows before the 1998 WC are the
#     earliest we can build.
# =============================================================================

# ---- Setup ------------------------------------------------------------------
library(sqldf)

wc_data_dir <- "transformed_data.csv"   # England WC group-stage table (model_df export)
pl_data_dir <- "premierleague_data"     # folder of season-YYYY.csv files
TOP_N       <- 6                         # how many "top performing" clubs per season

transformed <- read.csv(wc_data_dir, stringsAsFactors = FALSE)

# =============================================================================
# 1. PREMIER LEAGUE SCORING PER SEASON  (both angles)
#    league_gpg : mean(FTHG + FTAG) over all matches   -> whole-league scoring
#    top_gpg    : goals scored per game by the top-N clubs (ranked by points)
#    Each season is keyed by its END year (season-9798.csv -> 1998), the spring
#    before a summer World Cup.
# =============================================================================

# --- Helper: top-N clubs' goals-scored-per-game for one season's match table --
season_top_scoring <- function(d, top_n = TOP_N) {
  home <- data.frame(club = d$HomeTeam, gf = d$FTHG,
                     pts = ifelse(d$FTR == "H", 3, ifelse(d$FTR == "D", 1, 0)))
  away <- data.frame(club = d$AwayTeam, gf = d$FTAG,
                     pts = ifelse(d$FTR == "A", 3, ifelse(d$FTR == "D", 1, 0)))
  long <- rbind(home, away)
  long$games <- 1
  tab  <- aggregate(cbind(gf, pts, games) ~ club, data = long, FUN = sum)
  tab  <- tab[order(-tab$pts), ]              # rank by league points
  top  <- head(tab, top_n)                    # keep the top performers
  sum(top$gf) / sum(top$games)                # their goals scored per game
}

season_files <- list.files(pl_data_dir, pattern = "^season-\\d{4}\\.csv$", full.names = TRUE)

pl_season <- do.call(rbind, lapply(season_files, function(f) {
  yy  <- regmatches(basename(f), regexec("season-(\\d{2})(\\d{2})", basename(f)))[[1]]
  end <- as.integer(yy[3])
  end <- ifelse(end >= 80, 1900 + end, 2000 + end)   # 94 -> 1994, 02 -> 2002
  d   <- read.csv(f, stringsAsFactors = FALSE)
  data.frame(season_end = end,
             league_gpg = mean(d$FTHG + d$FTAG, na.rm = TRUE),
             top_gpg    = season_top_scoring(d))
}))
pl_season <- pl_season[order(pl_season$season_end), ]

cat("PL seasons loaded:", nrow(pl_season),
    "( ", min(pl_season$season_end), "-", max(pl_season$season_end),
    ")  [top_gpg uses top", TOP_N, "clubs]\n")
print(pl_season, row.names = FALSE)

# =============================================================================
# 2. INTER-WORLD-CUP SCORING FEATURES  (generic over the chosen metric)
#    For a WC year Y, the window is PL seasons ending in (Y-4, Y].
#    Returns mean / slope / delta / change for whichever metric column is passed.
# =============================================================================
window_stats <- function(Y, metric) {
  w    <- pl_season[pl_season$season_end >  Y - 4 & pl_season$season_end <= Y, ]
  prev <- pl_season[pl_season$season_end >  Y - 8 & pl_season$season_end <= Y - 4, ]
  v    <- w[[metric]]
  slope <- if (nrow(w) >= 2) coef(lm(reformulate("season_end", metric), data = w))[2] else NA
  data.frame(
    mean   = mean(v),
    slope  = as.numeric(slope),
    delta  = v[length(v)] - v[1],
    change = mean(v) - mean(prev[[metric]])   # vs previous window
  )
}

# --- Build a prefixed feature block for a given metric across the WC years -----
build_features <- function(years, metric, prefix) {
  f <- do.call(rbind, lapply(years, window_stats, metric = metric))
  names(f) <- paste0(prefix, "_", names(f))
  f
}

# =============================================================================
# 3. ENGLAND MEN'S GROUP-STAGE ROWS  (PL era only)  + both feature blocks
#    Men's World Cups = the 4-year cycle from 1930; keep 1998 onward so a full
#    PL scoring window exists. (See caveats re: excluding women's rows.)
# =============================================================================
mens_wc_years <- seq(1930, 2022, by = 4)

england <- sqldf("
  SELECT year, points, goals_for, goals_against, wins, draws, losses, advanced
  FROM   transformed
  WHERE  team_name = 'England'
  ORDER BY year
")
england <- england[england$year %in% mens_wc_years & england$year >= 1998, ]

merged <- cbind(
  england,
  build_features(england$year, "league_gpg", "league"),   # angle A
  build_features(england$year, "top_gpg",    "top")       # angle B
)

cat("\nMerged England (men's) + PL scoring windows  ( n =", nrow(merged), "):\n")
print(data.frame(lapply(merged, function(x) if (is.numeric(x)) round(x, 3) else x)),
      row.names = FALSE)

# =============================================================================
# 4. EXPLORE THE RELATIONSHIP  (both angles)
#    With n = 7 these are descriptive. We report England group POINTS and
#    GOALS FOR against each scoring feature, for league-wide and top-club scoring.
# =============================================================================
report_angle <- function(prefix, label) {
  cat("\n===== Angle:", label, "=====\n")
  for (stat in c("mean", "slope", "delta", "change")) {
    v <- paste0(prefix, "_", stat)
    cat(sprintf("  points~%-14s r = %+0.3f   |   goals_for~%-14s r = %+0.3f\n",
                v, cor(merged$points,    merged[[v]]),
                v, cor(merged$goals_for, merged[[v]])))
  }
  # Headline model: does the between-period change matter for points?
  m <- lm(reformulate(paste0(prefix, "_change"), "points"), data = merged)
  cat("  -- lm( points ~ ", prefix, "_change ):  slope = ",
      round(coef(m)[2], 3), ",  R^2 = ", round(summary(m)$r.squared, 3), "\n", sep = "")
  invisible(m)
}

cat("\nPearson correlations (n =", nrow(merged), "):")
m_league <- report_angle("league", "LEAGUE-WIDE goals/game")
m_top    <- report_angle("top",    paste0("TOP-", TOP_N, " clubs goals/game"))

# Full model summaries for the two headline (change) models.
cat("\n--- lm( points ~ league_change ) ---\n"); print(summary(m_league))
cat("\n--- lm( points ~ top_change ) ---\n");    print(summary(m_top))

# =============================================================================
# 5. PLOTS  (2 x 2: rows = the two angles, saved next to this script)
#    Left column : between-cup scoring CHANGE vs England points.
#    Right column: window MEAN scoring vs England goals for.
# =============================================================================
png("england_pl_scoring_plots.png", width = 1100, height = 900)
par(mfrow = c(2, 2))

scatter_year <- function(x, y, xlab, ylab, main, fit = NULL) {
  plot(x, y, pch = 19, col = "#2774AE", cex = 1.4, xlab = xlab, ylab = ylab, main = main)
  text(x, y, labels = merged$year, pos = 3, cex = 0.8)
  if (!is.null(fit)) abline(fit, col = "#FFD100", lwd = 2)
}

# Row 1 - league-wide
scatter_year(merged$league_change, merged$points,
             "League goals/game: change vs previous period", "England group points",
             "A1. Points vs league scoring change", m_league)
scatter_year(merged$league_mean, merged$goals_for,
             "League goals/game: window mean", "England group goals for",
             "A2. Goals for vs league scoring level")

# Row 2 - top clubs
scatter_year(merged$top_change, merged$points,
             paste0("Top-", TOP_N, " goals/game: change vs previous period"), "England group points",
             "B1. Points vs top-club scoring change", m_top)
scatter_year(merged$top_mean, merged$goals_for,
             paste0("Top-", TOP_N, " goals/game: window mean"), "England group goals for",
             "B2. Goals for vs top-club scoring level")

par(mfrow = c(1, 1))
dev.off()

cat("\nSaved plot to:", normalizePath("england_pl_scoring_plots.png", mustWork = FALSE), "\n")

# =============================================================================
# NOTE / next steps:
#   * n = 7 means treat any signal as a hypothesis, not a finding.
#   * Two angles are compared: whole-league vs top-6 goals/game. Try TOP_N = 4
#     (Champions League places) or a fixed "big six" list for robustness, or
#     swap the outcome to 'advanced' / stage reached.
# =============================================================================
