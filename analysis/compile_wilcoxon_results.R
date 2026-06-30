
# compile_wilcoxon_results.R (patched)
# - Handles cases where broom::tidy(wilcox.test) does not include conf.low/conf.high
# - Ensures required packages are available (including purrr)
# - Produces wilcox_results.csv and wilcox_results.png

suppressPackageStartupMessages({
  if (!requireNamespace("broom", quietly = TRUE)) install.packages("broom")
  if (!requireNamespace("dplyr", quietly = TRUE)) install.packages("dplyr")
  if (!requireNamespace("readr", quietly = TRUE)) install.packages("readr")
  if (!requireNamespace("ggplot2", quietly = TRUE)) install.packages("ggplot2")
  if (!requireNamespace("forcats", quietly = TRUE)) install.packages("forcats")
  if (!requireNamespace("knitr", quietly = TRUE)) install.packages("knitr")
  if (!requireNamespace("purrr", quietly = TRUE)) install.packages("purrr")
})

library(broom)
library(dplyr)
library(readr)
library(ggplot2)
library(forcats)
library(knitr)
library(purrr)

calls_path <- "extracted_wilcox_calls.csv"
stopifnot(file.exists(calls_path))

calls <- readr::read_csv(calls_path, show_col_types = FALSE)

run_one <- function(label, call_str) {
  # Evaluate the call in the parent frame so it can see your objects
  expr <- tryCatch(parse(text = call_str)[[1]], error = function(e) e)
  if (inherits(expr, "error")) {
    return(tibble::tibble(
      label = label,
      method = NA_character_,
      alternative = NA_character_,
      p.value = NA_real_,
      statistic = NA_real_,
      conf.low = NA_real_,
      conf.high = NA_real_,
      error = paste("parse error:", conditionMessage(expr))
    ))
  }
  fit <- tryCatch(eval(expr, envir = parent.frame()), error = function(e) e)
  if (inherits(fit, "error")) {
    return(tibble::tibble(
      label = label,
      method = NA_character_,
      alternative = NA_character_,
      p.value = NA_real_,
      statistic = NA_real_,
      conf.low = NA_real_,
      conf.high = NA_real_,
      error = paste("eval error:", conditionMessage(fit))
    ))
  }
  td <- tryCatch(broom::tidy(fit), error = function(e) NULL)
  if (is.null(td)) {
    # Fallback: grab what we can
    pval <- tryCatch(fit$p.value, error = function(e) NA_real_)
    stat <- tryCatch(unname(fit$statistic), error = function(e) NA_real_)
    alt  <- tryCatch(as.character(fit$alternative), error = function(e) NA_character_)
    meth <- tryCatch(as.character(fit$method), error = function(e) NA_character_)
    out <- tibble::tibble(
      label = label,
      method = meth,
      alternative = alt,
      p.value = pval,
      statistic = as.numeric(stat),
      conf.low = NA_real_,
      conf.high = NA_real_,
      error = NA_character_
    )
  } else {
    # Ensure columns exist even if tidy() omitted them
    if (!"conf.low" %in% names(td)) td$conf.low <- NA_real_
    if (!"conf.high" %in% names(td)) td$conf.high <- NA_real_
    if (!"statistic" %in% names(td)) {
      # some broom versions may use "statistic" name, but just in case
      td$statistic <- NA_real_
    }
    if (!"method" %in% names(td)) td$method <- as.character(fit$method %||% NA_character_)
    if (!"alternative" %in% names(td)) td$alternative <- as.character(fit$alternative %||% NA_character_)

    out <- td |>
      mutate(label = label,
             statistic = suppressWarnings(as.numeric(statistic))) |>
      select(label, method, alternative, p.value, statistic, conf.low, conf.high) |>
      mutate(error = NA_character_)
  }
  out
}

# map over calls
results <- purrr::map2_dfr(calls$label, calls$call, run_one)

# Add significance stars
sig_star <- function(p) {
  if (is.na(p)) return(NA_character_)
  if (p < 0.001) return("***")
  if (p < 0.01)  return("**")
  if (p < 0.05)  return("*")
  if (p < 0.1)   return("·")
  ""
}

results <- results |>
  mutate(significance = vapply(p.value, sig_star, character(1)),
         neg_log10_p = ifelse(is.na(p.value), NA_real_, -log10(p.value)),
         label = as.character(label))

# Save CSV
readr::write_csv(results, "wilcox_results.csv")

# Print a nice table
print(knitr::kable(results, digits = 4,
                   caption = "Wilcoxon tests: tidy results with significance stars"))

# Plot -log10(p) bar chart
plot_df <- results |>
  filter(!is.na(neg_log10_p)) |>
  mutate(label = forcats::fct_reorder(label, neg_log10_p))

p <- ggplot(plot_df, aes(x = label, y = neg_log10_p)) +
  geom_col() +
  geom_hline(yintercept = -log10(0.05), linetype = "dashed") +
  geom_text(aes(label = significance), vjust = -0.5) +
  labs(x = NULL, y = "-log10(p)", title = "Wilcoxon tests: significance overview") +
  coord_flip() +
  theme_minimal(base_size = 12)

ggsave("wilcox_results.png", p, width = 7, height = 5, dpi = 150)

message('Done. Outputs written: "wilcox_results.csv" and "wilcox_results.png".')
