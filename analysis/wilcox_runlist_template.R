
# wilcox_runlist_template.R
# ------------------------------------------------------------------
# Purpose:
# - Keep the same outputs as before (compact CSV + PNG)
# - BUT you manually control:
#   * the displayed label (e.g., "8am")
#   * the order in the chart/table
#   * the exact code that is run for each label (e.g., 'wilcox.test(...)')
#
# How to use:
# 1) Make sure your data & variables used by the tests are loaded.
# 2) Edit the RUNLIST below: one row per test, with `label`, `order`, and `code`.
# 3) source("wilcox_runlist_template.R")
# 4) Outputs:
#    - wilcox_results_min.csv (label, p.value, statistic_W, n1, n2, U, z, r)
#    - wilcox_results.png  (bar chart of -log10(p) in your specified order)
#
# Notes:
# - `order` controls both the table and the chart order. It can be any numeric ranking.
# - `code` must be a character string that evaluates to a wilcox.test(...) result.
# - Effect size r = Z / sqrt(n1 + n2), with Z from two-sided p and sign from U-midpoint.
# - The script evaluates code in the parent.frame() so it can see your objects.
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
# 1) EDIT THIS: Your manual run list
#    - Put your wilcox.test(...) expressions as strings in `code`
#    - Set `label` exactly as you want it to appear in the table/chart
#    - Set `order` (lower number appears earlier in the chart)
# ------------------------------------------------------------------
RUNLIST <- tibble::tribble(
  ~label, ~order, ~code,
  # examples — replace with your actual tests:
  "12am",    0,  'wilcox.test(subset12am_sb$`Avg Occupancy`, subset12am_regular$`Avg Occupancy`)',
  "1am",    1,  'wilcox.test(subset1am_sb$`Avg Occupancy`, subset1am_regular$`Avg Occupancy`)',
  "2am",    2,  'wilcox.test(subset2am_sb$`Avg Occupancy`, subset2am_regular$`Avg Occupancy`)',
  "3am",    3,  'wilcox.test(subset3am_sb$`Avg Occupancy`, subset3am_regular$`Avg Occupancy`)',
  "4am",    4,  'wilcox.test(subset4am_sb$`Avg Occupancy`, subset4am_regular$`Avg Occupancy`)',
  "5am",    5,  'wilcox.test(subset5am_sb$`Avg Occupancy`, subset5am_regular$`Avg Occupancy`)',
  "6am",    6,  'wilcox.test(subset6am_sb$`Avg Occupancy`, subset6am_regular$`Avg Occupancy`)',
  "7am",    7,  'wilcox.test(subset7am_sb$`Avg Occupancy`, subset7am_regular$`Avg Occupancy`)',
  "8am",    8,  'wilcox.test(subset8am_sb$`Avg Occupancy`, subset8am_regular$`Avg Occupancy`)',
  "9am",    9,  'wilcox.test(subset9am_sb$`Avg Occupancy`, subset9am_regular$`Avg Occupancy`)',
  # Add more rows below as needed:
  # "10am",  10, 'wilcox.test(subset10am_sb$Tickets, subset10am_regular$Tickets, alternative="two.sided")'
)

stopifnot(all(c("label","order","code") %in% names(RUNLIST)))

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
eval_wilcox <- function(code_str) {
  expr <- tryCatch(parse(text = code_str)[[1]], error = function(e) e)
  if (inherits(expr, "error")) return(list(error = paste("parse error:", conditionMessage(expr))))
  fit <- tryCatch(eval(expr, envir = parent.frame()), error = function(e) e)
  if (inherits(fit, "error")) return(list(error = paste("eval error:", conditionMessage(fit))))
  list(fit = fit, expr = expr)
}

# compute sample sizes n1,n2 by evaluating first two args of wilcox.test call, when present
infer_ns <- function(expr) {
  n1 <- NA_real_; n2 <- NA_real_
  if (is.call(expr)) {
    args <- as.list(expr)[-1]
    # Keep positional or named x,y
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

compute_row <- function(label, order, code_str) {
  out <- eval_wilcox(code_str)
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
    .order = order
  )
}

# ------------------------------------------------------------------
# 2) Run all rows
# ------------------------------------------------------------------
results <- purrr::pmap_dfr(RUNLIST, function(label, order, code) compute_row(label, order, code))

# ------------------------------------------------------------------
# 3) Save compact CSV (same columns/format as your minimal table, ordered)
# ------------------------------------------------------------------
results_out <- results %>%
  arrange(.order, label) %>%
  select(label, p.value, r)

readr::write_csv(results_out, "wilcox_results_min.csv")

# ------------------------------------------------------------------
# 4) Plot -log10(p) chart with your order + dashed line at p=0.05
# ------------------------------------------------------------------
plot_df <- results_out %>%
  mutate(neg_log10_p = ifelse(is.na(p.value), NA_real_, -log10(p.value)),
         label = factor(label, levels = results_out$label))

p <- ggplot(plot_df, aes(x = label, y = neg_log10_p)) +
  geom_col() +
  geom_hline(yintercept = -log10(0.05), linetype = "dashed") +
  labs(x = NULL, y = "-log10(p)", title = "Wilcoxon tests (manual labels & order)") +
  coord_flip() +
  theme_minimal(base_size = 12)

ggsave("wilcox_results.png", p, width = 7, height = 5, dpi = 150)

message('Done. Wrote "wilcox_results_min.csv" and "wilcox_results.png".')
