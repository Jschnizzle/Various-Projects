
# compile_wilcoxon_results_objectlabel_12h_ordered_v2.R
# Vectorized chronological ordering to avoid "condition has length > 1" in mutate()

suppressPackageStartupMessages({
  if (!requireNamespace("readr", quietly = TRUE)) install.packages("readr")
  if (!requireNamespace("dplyr", quietly = TRUE)) install.packages("dplyr")
  if (!requireNamespace("purrr", quietly = TRUE)) install.packages("purrr")
  if (!requireNamespace("stringr", quietly = TRUE)) install.packages("stringr")
  if (!requireNamespace("ggplot2", quietly = TRUE)) install.packages("ggplot2")
  if (!requireNamespace("forcats", quietly = TRUE)) install.packages("forcats")
})

library(readr)
library(dplyr)
library(purrr)
library(stringr)
library(ggplot2)
library(forcats)

calls_path <- "extracted_wilcox_calls.csv"
stopifnot(file.exists(calls_path))
calls <- readr::read_csv(calls_path, show_col_types = FALSE)

to_12h_label <- function(raw_label) {
  if (is.null(raw_label) || is.na(raw_label) || raw_label == "") return(NA_character_)
  lbl <- tolower(raw_label)
  m1 <- str_match(lbl, "(\\d{1,2})\\s*(am|pm)")
  if (!is.na(m1[1,1])) {
    h <- as.integer(m1[1,2]); ap <- m1[1,3]
    h12 <- h %% 12; if (h12 == 0) h12 <- 12
    return(paste0(h12, ap))
  }
  m2 <- str_match(lbl, "(\\d{1,2})")
  if (!is.na(m2[1,2])) {
    h <- as.integer(m2[1,2])
    ap <- if (h < 12) "am" else "pm"
    h12 <- h %% 12; if (h12 == 0) h12 <- 12
    return(paste0(h12, ap))
  }
  raw_label
}

# Vectorized hour order: returns 0..23 matching "12am,1am,..,11pm"
hour_order_vec <- function(lbls) {
  n <- length(lbls)
  res <- rep(NA_real_, n)
  m <- stringr::str_match(lbls, "(\\d{1,2})(am|pm)")
  h <- suppressWarnings(as.integer(m[,2]))
  ap <- m[,3]
  ok <- !is.na(h) & !is.na(ap)
  if (any(ok)) {
    h12 <- h[ok] %% 12; h12[h12 == 0] <- 12
    res[ok] <- ifelse(ap[ok] == "am", h12 %% 12, (h12 %% 12) + 12)
  }
  res
}

run_one <- function(label, call_str) {
  label <- to_12h_label(label)
  expr <- tryCatch(parse(text = call_str)[[1]], error = function(e) e)
  if (inherits(expr, "error")) {
    return(tibble(label = label, p.value = NA_real_, statistic_W = NA_real_,
                  n1 = NA_real_, n2 = NA_real_, U = NA_real_, z = NA_real_, r = NA_real_))
  }
  fit <- tryCatch(eval(expr, envir = parent.frame()), error = function(e) e)
  if (inherits(fit, "error")) {
    return(tibble(label = label, p.value = NA_real_, statistic_W = NA_real_,
                  n1 = NA_real_, n2 = NA_real_, U = NA_real_, z = NA_real_, r = NA_real_))
  }
  
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
  
  pval <- suppressWarnings(as.numeric(fit$p.value))
  W <- suppressWarnings(as.numeric(fit$statistic))
  U <- NA_real_; z <- NA_real_; r <- NA_real_
  if (!is.na(n1) && !is.na(n2) && n1 > 0 && n2 > 0) {
    U <- W - n1*(n1 + 1)/2
    sign_dir <- sign(U - (n1*n2/2))
    if (!is.na(pval)) {
      z <- qnorm(pval/2, lower.tail = FALSE) * sign_dir
      r <- z / sqrt(n1 + n2)
    }
  }
  tibble(label = label, p.value = pval, statistic_W = W, n1 = n1, n2 = n2, U = U, z = z, r = r)
}

results <- purrr::map2_dfr(calls$label, calls$call, run_one)

# Chronological sort
results <- results %>%
  mutate(hour24 = hour_order_vec(label)) %>%
  arrange(hour24, label)

# Save CSV without helper column
readr::write_csv(results %>% select(-hour24), "wilcox_results_min_objectlabel.csv")

# Plot -log10(p) in chronological order with fixed factor levels
plot_df <- results %>%
  filter(!is.na(p.value)) %>%
  mutate(neg_log10_p = -log10(p.value),
         label = factor(label, levels = unique(label)))

p <- ggplot(plot_df, aes(x = label, y = neg_log10_p)) +
  geom_col() +
  geom_hline(yintercept = -log10(0.05), linetype = "dashed") +
  labs(x = NULL, y = "-log10(p)", title = "Wilcoxon tests by time (chronological order)") +
  coord_flip() +
  theme_minimal(base_size = 12)

ggsave("wilcox_results.png", p, width = 7, height = 5, dpi = 150)
ggsave("wilcox_result.png", p, width = 7, height = 5, dpi = 150)

message('Done. Chronological ordering fixed and outputs saved.')
