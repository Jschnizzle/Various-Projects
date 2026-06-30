
# wilcox_runlist_with_pctdiff.R (updated for pct_diff_mean compatibility)
# ------------------------------------------------------------------
# Accepts either a `pct_diff` column OR a `pct_diff_mean` column in RUNLIST.
# If only `pct_diff_mean` is present, the script copies it to `pct_diff`.
# Outputs remain the same:
#   - wilcox_results_min.csv (includes pct_diff)
#   - wilcox_results.png
# ------------------------------------------------------------------

suppressPackageStartupMessages({
  if (!requireNamespace("tibble", quietly = TRUE)) install.packages("tibble")
  if (!requireNamespace("dplyr", quietly = TRUE)) install.packages("dplyr")
  if (!requireNamespace("purrr", quietly = TRUE)) install.packages("purrr")
  if (!requireNamespace("ggplot2", quietly = TRUE)) install.packages("ggplot2")
  if (!requireNamespace("forcats", quietly = TRUE)) install.packages("forcats")
  if (!requireNamespace("readr", quietly = TRUE)) install.packages("readr")
})

library(tibble)
library(dplyr)
library(purrr)
library(ggplot2)
library(forcats)
library(readr)

# ------------------------------------------------------------------
# 1) EDIT THIS: Manual run list
#    You can use either `pct_diff` or `pct_diff_mean` here.
# ------------------------------------------------------------------
RUNLIST <- tibble::tribble(
  ~label, ~order, ~code, ~pct_diff_mean,
  # examples — replace with your actual tests and values:
#  "12am",  0, 'wilcox.test(subset12am_sb$`Avg Occupancy`, subset12am_regular$`Avg Occupancy`)',  (mean(subset12am_sb$`Avg Occupancy`) - mean(subset12am_regular$`Avg Occupancy`)) / mean(subset12am_regular$`Avg Occupancy`),
#  "1am",  1, 'wilcox.test(subset1am_sb$`Avg Occupancy`, subset1am_regular$`Avg Occupancy`)',  (mean(subset1am_sb$`Avg Occupancy`) - mean(subset1am_regular$`Avg Occupancy`)) / mean(subset1am_regular$`Avg Occupancy`),
#  "2am",  2, 'wilcox.test(subset2am_sb$`Avg Occupancy`, subset2am_regular$`Avg Occupancy`)',  (mean(subset2am_sb$`Avg Occupancy`) - mean(subset2am_regular$`Avg Occupancy`)) / mean(subset2am_regular$`Avg Occupancy`),
#  "3am",  3, 'wilcox.test(subset3am_sb$`Avg Occupancy`, subset3am_regular$`Avg Occupancy`)',  (mean(subset3am_sb$`Avg Occupancy`) - mean(subset3am_regular$`Avg Occupancy`)) / mean(subset3am_regular$`Avg Occupancy`),
#  "4am",  4, 'wilcox.test(subset4am_sb$`Avg Occupancy`, subset4am_regular$`Avg Occupancy`)',  (mean(subset4am_sb$`Avg Occupancy`) - mean(subset4am_regular$`Avg Occupancy`)) / mean(subset4am_regular$`Avg Occupancy`),
#  "5am",  5, 'wilcox.test(subset5am_sb$`Avg Occupancy`, subset5am_regular$`Avg Occupancy`)',  (mean(subset5am_sb$`Avg Occupancy`) - mean(subset5am_regular$`Avg Occupancy`)) / mean(subset5am_regular$`Avg Occupancy`),
#  "6am",  6, 'wilcox.test(subset6am_sb$`Avg Occupancy`, subset6am_regular$`Avg Occupancy`)',  (mean(subset6am_sb$`Avg Occupancy`) - mean(subset6am_regular$`Avg Occupancy`)) / mean(subset6am_regular$`Avg Occupancy`),
#  "7am",  7, 'wilcox.test(subset7am_sb$`Avg Occupancy`, subset7am_regular$`Avg Occupancy`)',  (mean(subset7am_sb$`Avg Occupancy`) - mean(subset7am_regular$`Avg Occupancy`)) / mean(subset7am_regular$`Avg Occupancy`),
  "8am",  8, 'wilcox.test(subset8am_sb$`Avg Occupancy`, subset8am_regular$`Avg Occupancy`)',  100*(mean(subset8am_sb$`Avg Occupancy`) - mean(subset8am_regular$`Avg Occupancy`)) / mean(subset8am_regular$`Avg Occupancy`),
  "9am",  9, 'wilcox.test(subset9am_sb$`Avg Occupancy`, subset9am_regular$`Avg Occupancy`)',  100*(mean(subset9am_sb$`Avg Occupancy`) - mean(subset9am_regular$`Avg Occupancy`)) / mean(subset9am_regular$`Avg Occupancy`),
  "10am",  10, 'wilcox.test(subset10am_sb$`Avg Occupancy`, subset10am_regular$`Avg Occupancy`)',  100*(mean(subset10am_sb$`Avg Occupancy`) - mean(subset10am_regular$`Avg Occupancy`)) / mean(subset10am_regular$`Avg Occupancy`),
#  "11am",  11, 'wilcox.test(subset11am_sb$`Avg Occupancy`, subset11am_regular$`Avg Occupancy`)',  (mean(subset11am_sb$`Avg Occupancy`) - mean(subset11am_regular$`Avg Occupancy`)) / mean(subset11am_regular$`Avg Occupancy`), 
#  "12pm",  12, 'wilcox.test(subset12pm_sb$`Avg Occupancy`, subset12pm_regular$`Avg Occupancy`)',  (mean(subset12pm_sb$`Avg Occupancy`) - mean(subset12pm_regular$`Avg Occupancy`)) / mean(subset12pm_regular$`Avg Occupancy`),
#  "1pm",  13, 'wilcox.test(subset1pm_sb$`Avg Occupancy`, subset1pm_regular$`Avg Occupancy`)',  (mean(subset1pm_sb$`Avg Occupancy`) - mean(subset1pm_regular$`Avg Occupancy`)) / mean(subset1pm_regular$`Avg Occupancy`),
#  "2pm",  14, 'wilcox.test(subset2pm_sb$`Avg Occupancy`, subset2pm_regular$`Avg Occupancy`)',  (mean(subset2pm_sb$`Avg Occupancy`) - mean(subset2pm_regular$`Avg Occupancy`)) / mean(subset2pm_regular$`Avg Occupancy`),
  "3pm",  15, 'wilcox.test(subset3pm_sb$`Avg Occupancy`, subset3pm_regular$`Avg Occupancy`)',  100*(mean(subset3pm_sb$`Avg Occupancy`) - mean(subset3pm_regular$`Avg Occupancy`)) / mean(subset3pm_regular$`Avg Occupancy`),
#  "4pm",  16, 'wilcox.test(subset4pm_sb$`Avg Occupancy`, subset4pm_regular$`Avg Occupancy`)',  (mean(subset4pm_sb$`Avg Occupancy`) - mean(subset4pm_regular$`Avg Occupancy`)) / mean(subset4pm_regular$`Avg Occupancy`),
  "5pm",  17, 'wilcox.test(subset5pm_sb$`Avg Occupancy`, subset5pm_regular$`Avg Occupancy`)',  100*(mean(subset5pm_sb$`Avg Occupancy`) - mean(subset5pm_regular$`Avg Occupancy`)) / mean(subset5pm_regular$`Avg Occupancy`),
  "6pm",  18, 'wilcox.test(subset6pm_sb$`Avg Occupancy`, subset6pm_regular$`Avg Occupancy`)',  100*(mean(subset6pm_sb$`Avg Occupancy`) - mean(subset6pm_regular$`Avg Occupancy`)) / mean(subset6pm_regular$`Avg Occupancy`),
  "7pm",  19, 'wilcox.test(subset7pm_sb$`Avg Occupancy`, subset7pm_regular$`Avg Occupancy`)',  100*(mean(subset7pm_sb$`Avg Occupancy`) - mean(subset7pm_regular$`Avg Occupancy`)) / mean(subset7pm_regular$`Avg Occupancy`),
  "8pm",  20, 'wilcox.test(subset8pm_sb$`Avg Occupancy`, subset8pm_regular$`Avg Occupancy`)',  100*(mean(subset8pm_sb$`Avg Occupancy`) - mean(subset8pm_regular$`Avg Occupancy`)) / mean(subset8pm_regular$`Avg Occupancy`),
  "9pm",  21, 'wilcox.test(subset9pm_sb$`Avg Occupancy`, subset9pm_regular$`Avg Occupancy`)',  100*(mean(subset9pm_sb$`Avg Occupancy`) - mean(subset9pm_regular$`Avg Occupancy`)) / mean(subset9pm_regular$`Avg Occupancy`),
#  "10pm",  22, 'wilcox.test(subset10pm_sb$`Avg Occupancy`, subset10pm_regular$`Avg Occupancy`)',  (mean(subset10pm_sb$`Avg Occupancy`) - mean(subset10pm_regular$`Avg Occupancy`)) / mean(subset10pm_regular$`Avg Occupancy`),
#  "11pm",  23, 'wilcox.test(subset11pm_sb$`Avg Occupancy`, subset11pm_regular$`Avg Occupancy`)',  (mean(subset11pm_sb$`Avg Occupancy`) - mean(subset11pm_regular$`Avg Occupancy`)) / mean(subset11pm_regular$`Avg Occupancy`),

)

# ------------------------------------------------------------------
# Backward/forward compatibility for pct_diff vs pct_diff_mean
# ------------------------------------------------------------------
if (!"pct_diff" %in% names(RUNLIST)) {
  if ("pct_diff_mean" %in% names(RUNLIST)) {
    RUNLIST <- RUNLIST %>% mutate(pct_diff = as.numeric(pct_diff_mean))
  } else {
    stop("RUNLIST must contain either `pct_diff` or `pct_diff_mean`.")
  }
}

stopifnot(all(c("label","order","code","pct_diff") %in% names(RUNLIST)))

# ------------------------------------------------------------------
# Helpers (unchanged)
# ------------------------------------------------------------------
eval_wilcox <- function(code_str) {
  expr <- tryCatch(parse(text = code_str)[[1]], error = function(e) e)
  if (inherits(expr, "error")) return(list(error = paste("parse error:", conditionMessage(expr))))
  fit <- tryCatch(eval(expr, envir = parent.frame()), error = function(e) e)
  if (inherits(fit, "error")) return(list(error = paste("eval error:", conditionMessage(fit))))
  list(fit = fit, expr = expr)
}

infer_ns <- function(expr) {
  n1 <- NA_real_; n2 <- NA_real_
  if (is.call(expr)) {
    args <- as.list(expr)[-1]
    pos_args <- args[which(names(args) %in% c("", "x", "y", NA))]
    if (length(pos_args) == 0) pos_args <- args
    get_len <- function(a) {
      v <- tryCatch(eval(a, envir = parent.frame()), error = function(e) NULL)
      if (is.null(v)) return(NA_real_)
      suppressWarnings(as.numeric(length(v)))
    }
    if (length(pos_args) >= 1) n1 <- get_len(pos_args[[1]])
    if (length(pos_args) >= 2) n2 <- get_len(pos_args[[2]])
  }
  c(n1 = n1, n2 = n2)
}

compute_row <- function(label, order, code, pct_diff) {
  out <- eval_wilcox(code)
  if (!is.null(out$error)) {
    return(tibble(
      label = label,
      p.value = NA_real_,
      statistic_W = NA_real_,
      n1 = NA_real_,
      n2 = NA_real_,
      U = NA_real_,
      z = NA_real_,
      r = NA_real_,
      pct_diff = suppressWarnings(as.numeric(pct_diff)),
      .order = order
    ))
  }
  fit <- out$fit
  expr <- out$expr
  pval <- suppressWarnings(as.numeric(fit$p.value))
  W <- suppressWarnings(as.numeric(fit$statistic))
  ns <- infer_ns(expr)
  n1 <- ns["n1"]; n2 <- ns["n2"]
  U <- NA_real_; z <- NA_real_; r <- NA_real_
  if (!is.na(n1) && !is.na(n2) && n1 > 0 && n2 > 0) {
    U <- W - n1*(n1 + 1)/2
    sign_dir <- sign(U - (n1*n2/2))
    if (!is.na(pval)) {
      z <- qnorm(pval/2, lower.tail = FALSE) * sign_dir
      r <- z / sqrt(n1 + n2)
    }
  }
  tibble(
    label = label,
    p.value = pval,
    statistic_W = W,
    n1 = as.numeric(n1),
    n2 = as.numeric(n2),
    U = as.numeric(U),
    z = as.numeric(z),
    r = as.numeric(r),
    pct_diff = suppressWarnings(as.numeric(pct_diff)),
    .order = order
  )
}

# ------------------------------------------------------------------
# Run and output
# ------------------------------------------------------------------
# Only pass the needed columns in the correct order to pmap
results <- purrr::pmap_dfr(RUNLIST[, c("label","order","code","pct_diff")],
                           function(label, order, code, pct_diff) compute_row(label, order, code, pct_diff))

results_out <- results %>%
  arrange(.order, label) %>%
  select(label, p.value, r, pct_diff)

#readr::write_csv(results_out, "wilcox_results_min.csv")
readr::write_csv(
  results_out %>%
    rename(
      Time = label,
      P_Value = p.value,
      Effect_Size = r,
      Pct_Diff_Mean = pct_diff
    ),
  "mann_whitney_results_min_friday.csv"
)


plot_df <- results_out %>%
  mutate(neg_log10_p = ifelse(is.na(p.value), NA_real_, -log10(p.value)),
         label = factor(label, levels = rev(results_out$label)))

p <- ggplot(plot_df, aes(x = label, y = neg_log10_p)) +
  geom_col() +
  geom_hline(yintercept = -log10(0.05), linetype = "dashed") +
  labs(x = NULL, y = "-log10(p)", title = "Degree of Significance") +
  coord_flip() +
  theme_minimal(base_size = 12)

ggsave("mann_whitney_results_friday.png", p, width = 7, height = 5, dpi = 150)

message('Done. Wrote "mann_whitney_results_min_friday.csv" (with pct_diff) and "mann_whitney_results.png".')
