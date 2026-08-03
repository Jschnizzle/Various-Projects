# =============================================================================
# Filter transformed_data.csv down to MEN'S World Cups only
# -----------------------------------------------------------------------------
# Why this is needed:
#   transformed_data.csv currently holds BOTH men's and women's rows (581 total:
#   445 men's + 136 women's). The women's rows leaked in because the source
#   script (worldcupdata_processing.R) filters with SQLite's LIKE:
#       WHERE tournament_name LIKE '%Men''s%'
#   SQLite LIKE is CASE-INSENSITIVE, and "Women's" contains the substring
#   "men's", so women's tournaments match too. (The proper source-side fix is to
#   use LIKE '%FIFA Men''s%' or add AND tournament_name NOT LIKE '%Women''s%'.)
#
# This script fixes the EXPORT robustly: it reads the men's/women's label from
# the source group_standings table, keeps only men's tournament_ids, and writes
# the filtered result back. The original full table is backed up first.
# =============================================================================

# ---- Paths ------------------------------------------------------------------
transformed_path <- "transformed_data.csv"
standings_path   <- "worldcup_data/group_standings.csv"
backup_path      <- "transformed_data_all.csv"   # full (men's + women's) backup

transformed <- read.csv(transformed_path,   stringsAsFactors = FALSE)
standings   <- read.csv(standings_path,      stringsAsFactors = FALSE)

# =============================================================================
# 1. Identify men's tournament_ids from the SOURCE table
#    grepl() is case-SENSITIVE by default, so "Men's" does NOT match inside
#    "Women's" (capital M vs the lowercase m in Women's). Belt-and-suspenders:
#    also require it is NOT a Women's tournament.
# =============================================================================
tourneys <- unique(standings[, c("tournament_id", "tournament_name")])

is_mens  <- grepl("Men's", tourneys$tournament_name) &
           !grepl("Women's", tourneys$tournament_name)

mens_ids <- tourneys$tournament_id[is_mens]

cat("Men's tournaments found:", length(mens_ids), "\n")

# =============================================================================
# 2. Filter transformed_data to men's tournaments only
# =============================================================================
mens_only <- transformed[transformed$tournament_id %in% mens_ids, ]

cat(sprintf("Rows: %d total -> %d men's ( %d women's/other removed )\n",
            nrow(transformed), nrow(mens_only),
            nrow(transformed) - nrow(mens_only)))

# =============================================================================
# 3. Back up the full table (once) and overwrite transformed_data.csv
#    with the men's-only version so downstream code stays correct.
# =============================================================================
if (!file.exists(backup_path)) {
  write.csv(transformed, backup_path, row.names = FALSE)
  cat("Backed up full table to:", backup_path, "\n")
} else {
  cat("Backup already exists, leaving it untouched:", backup_path, "\n")
}

write.csv(mens_only, transformed_path, row.names = FALSE)
cat("Wrote men's-only table to:", transformed_path, "\n")

# ---- Sanity check -----------------------------------------------------------
cat("\nYears remaining (should be the 4-year men's cycle only):\n")
print(sort(unique(mens_only$year)))
