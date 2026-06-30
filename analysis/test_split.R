# split_cleaned_speed.R
# ---------------------------------------------------------------------------
# Splits Cleaned_speed.csv into multiple parts, each guaranteed to be under
# 25 MB. Output files are named Cleaned_speed1.csv, Cleaned_speed2.csv, ...
# The CSV header row is repeated at the top of every output file so each
# part is independently readable.
#
# Usage:
#   - Place this script anywhere and run it. By default it looks for
#     Cleaned_speed.csv in the Forecasting folder (the parent of this
#     script's folder), then in the current working directory.
#   - Or set the paths manually below / pass them on the command line:
#       Rscript split_cleaned_speed.R [input_csv] [output_dir]
# ---------------------------------------------------------------------------

# ---- Configuration --------------------------------------------------------
max_size_mb   <- 1            # hard ceiling per file (MB)
target_mb     <- 1            # we aim a bit under the ceiling for safety
output_prefix <- "Cleaned_speed"  # -> Cleaned_speed1.csv, Cleaned_speed2.csv

# ---- Resolve input / output paths ----------------------------------------
args <- commandArgs(trailingOnly = TRUE)

find_input <- function() {
  # 1) command-line argument
  if (length(args) >= 1 && nzchar(args[1])) return(args[1])
  # 2) parent of this script's directory (Forecasting/Cleaned_speed.csv)
  this_dir <- tryCatch({
    a <- commandArgs(FALSE)
    f <- sub("^--file=", "", a[grep("^--file=", a)])
    if (length(f)) dirname(normalizePath(f)) else NA_character_
  }, error = function(e) NA_character_)
  if (!is.na(this_dir)) {
    cand <- file.path(dirname(this_dir), "Cleaned_speed.csv")
    if (file.exists(cand)) return(cand)
  }
  # 3) current working directory
  if (file.exists("Cleaned_speed.csv")) return("Cleaned_speed.csv")
  stop("Could not find Cleaned_speed.csv. Pass its path as the first argument.")
}

input_file <- find_input()
output_dir <- if (length(args) >= 2 && nzchar(args[2])) args[2] else dirname(input_file)
if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)

cat(sprintf("Input : %s\n", normalizePath(input_file)))
cat(sprintf("Output: %s\n", normalizePath(output_dir)))

# ---- Stream the file line-by-line, flushing chunks under the size cap -----
target_bytes <- target_mb * 1024 * 1024

con <- file(input_file, "r", encoding = "UTF-8")
on.exit(close(con), add = TRUE)

header <- readLines(con, n = 1L, warn = FALSE)
if (length(header) == 0) stop("Input file appears to be empty.")
# bytes a line occupies on disk (content + newline)
line_bytes <- function(x) sum(nchar(x, type = "bytes")) + length(x)
header_bytes <- line_bytes(header)

part        <- 0L
buffer      <- character(0)
buffer_bytes <- 0L
total_rows  <- 0L

flush_buffer <- function() {
  if (length(buffer) == 0) return(invisible())
  part <<- part + 1L
  out_path <- file.path(output_dir, sprintf("%s%d.csv", output_prefix, part))
  writeLines(c(header, buffer), out_path, useBytes = TRUE)
  size_mb <- file.info(out_path)$size / (1024 * 1024)
  cat(sprintf("  wrote %s  (%d rows, %.2f MB)\n",
              basename(out_path), length(buffer), size_mb))
  buffer       <<- character(0)
  buffer_bytes <<- 0L
}

repeat {
  line <- readLines(con, n = 1L, warn = FALSE)
  if (length(line) == 0) break          # end of file
  lb <- line_bytes(line)

  # Guard: a single row larger than the cap can't be made to fit.
  if (header_bytes + lb > target_bytes) {
    warning(sprintf("A single data row exceeds the %d MB target; ",
                    target_mb),
            "it will be written in its own (oversized) file.")
  }

  # If adding this line would push the current chunk over target, flush first.
  if (length(buffer) > 0 &&
      header_bytes + buffer_bytes + lb > target_bytes) {
    flush_buffer()
  }

  buffer       <- c(buffer, line)
  buffer_bytes <- buffer_bytes + lb
  total_rows   <- total_rows + 1L
}
flush_buffer()  # write any remaining rows

cat(sprintf("\nDone. Split %d data rows into %d file(s), each < %d MB.\n",
            total_rows, part, max_size_mb))
