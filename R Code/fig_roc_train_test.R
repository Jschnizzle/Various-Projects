rm( list = ls() )

# =============================================================================
# fig_roc_train_test.R -- out-of-sample ROC curve, chronological train/test split
# -----------------------------------------------------------------------------
# Produces `figures/roc_train_test_split.png`, the ROC figure used on the deck's
# MODEL PERFORMANCE slide and as Figure 7 in main.tex.
#
# THE SPLIT: fit on the ten tournaments from 1970 through 2006 (239 campaigns),
# score the four most recent, 2010 through 2022 (127 campaigns). This is the
# same split as section 8 of logit_mens_groupstage_advance.R -- stated here as
# explicit year ranges rather than "< 2010 / >= 2010" because that is how the
# writeup and the slide describe it.
#
# WHY CHRONOLOGICAL, NOT RANDOM: it asks the question a forecaster actually
# faces -- predict the next tournament from the ones already played -- and it
# guarantees no test-year information reaches the fit. The model spec is
# PRE-SPECIFIED (f_structural), so the split arbitrates prediction only, never
# variable selection.
#
# WHY A SEPARATE FIGURE FROM section 8a's roc_test_2010.png: that one is drawn
# in UCLA blue for the R console workflow. This one uses the deck palette
# (navy/green on the light deck tone) so it sits natively in the PPTX and the
# LaTeX appendix. Same numbers, same curve.
#
# Base R only. Run from the PROJECT ROOT (not from R Code/), so the relative
# paths to the CSV and figures/ resolve:
#   setwd("<project root>"); source("R Code/fig_roc_train_test.R")
# =============================================================================


# ---- deck palette (see Context.md 12.7) -------------------------------------
NAVY  <- "#1F3864"; INK   <- "#1A2233"; GREEN <- "#2E9E6B"
SLATE <- "#5B6472"; GRID  <- "#C7D0E0"; LIGHT <- "#F4F6FA"

# Area under the curve is GREEN at 8% over white. WASH is the OPAQUE equivalent
# of that same washed-out green: the key panel is filled with it so the panel
# matches the shaded area exactly while still hiding the gridlines behind it
# (a translucent panel would let them show through).
FILL_ALPHA <- 0.08
WASH <- rgb(t(1 + (col2rgb(GREEN) / 255 - 1) * FILL_ALPHA))   # ~ #EEF7F3


# ---- data -------------------------------------------------------------------
model_df <- read.csv("mens_groupstage_1970on.csv", stringsAsFactors = FALSE)

# Match 02_model_fitting.R: drop the collapsed OFC cell (New Zealand 1982 &
# 2010). It is perfectly separated in the logistic model, and dropping it here
# keeps this figure on exactly the row set the reported model uses -> 366 rows.
model_df <- subset(model_df, conf != "OTHER")

# The CSV flattens `conf` to plain text, so the UEFA baseline must be re-applied
# after load -- otherwise the factor defaults to alphabetical (AFC) and the
# confederation coefficients read differently.
model_df$conf <- relevel(factor(model_df$conf), ref = "UEFA")

stopifnot(all(model_df$played == 3), all(model_df$year >= 1970))


# ---- pre-specified spec (Model 1) -------------------------------------------
f_structural <- advanced ~ prior_tournaments + avg_prior_wc +
                           avg_age + forward_share + defender_share +
                           is_host + foreign_manager + conf + year_c


# ---- chronological split -----------------------------------------------------
train <- subset(model_df, year <= 2006)   # 1970-2006
test  <- subset(model_df, year >= 2010)   # 2010-2022

# Keep the test set on the SAME factor levels as training so predict() does not
# error on an unseen level.
train$conf <- factor(train$conf, levels = levels(model_df$conf))
test$conf  <- factor(test$conf,  levels = levels(model_df$conf))

fit_train <- glm(f_structural, family = binomial(link = "logit"), data = train)
p_test    <- predict(fit_train, newdata = test, type = "response")


# ---- AUC (Mann-Whitney, ties handled by rank averaging) ----------------------
auc_mw <- function(y, p) {
  r  <- rank(p)
  n1 <- sum(y == 1); n0 <- sum(y == 0)
  (sum(r[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}

auc_test  <- auc_mw(test$advanced, p_test)
acc_test  <- mean((p_test >= 0.5) == (test$advanced == 1))
base_test <- mean(test$advanced)

cat(sprintf("train n = %d (%d-%d) | test n = %d (%d-%d)\n",
            nrow(train), min(train$year), max(train$year),
            nrow(test),  min(test$year),  max(test$year)))
cat(sprintf("test accuracy = %.3f | naive baseline = %.3f | lift = %+.3f\n",
            acc_test, max(base_test, 1 - base_test),
            acc_test - max(base_test, 1 - base_test)))
cat(sprintf("test AUC      = %.3f  (out-of-sample discrimination)\n", auc_test))


# ---- ROC points --------------------------------------------------------------
# Sweep every threshold: sort descending by predicted probability, then each
# prefix of that ordering is one (FPR, TPR) pair. Prepend the origin.
roc_points <- function(y, p) {
  o  <- order(-p)
  ys <- y[o]
  list(fpr = c(0, cumsum(ys == 0) / sum(ys == 0)),
       tpr = c(0, cumsum(ys == 1) / sum(ys == 1)))
}
roc <- roc_points(test$advanced, p_test)


# ---- draw --------------------------------------------------------------------
draw_roc <- function(file = "figures/roc_train_test_split.png",
                     bg = "#FFFFFF", width = 1310, height = 1353, res = 300) {

  dir.create(dirname(file), showWarnings = FALSE, recursive = TRUE)
  png(file, width = width, height = height, res = res, bg = bg)
  on.exit(dev.off())

  par(mar = c(4.2, 4.4, 4.8, 1.6), family = "sans", bg = bg)
  plot(NA, xlim = c(-0.02, 1.02), ylim = c(-0.02, 1.02),
       axes = FALSE, xlab = "", ylab = "")

  # gridlines, then the no-skill diagonal
  abline(h = seq(0, 1, 0.2), v = seq(0, 1, 0.2), col = GRID, lwd = 0.6)
  segments(0, 0, 1, 1, col = GRID, lwd = 1.6, lty = 2)

  # shaded area under the curve, then the step curve itself
  polygon(c(roc$fpr, 1, 0), c(roc$tpr, 0, 0),
          col = adjustcolor(GREEN, alpha.f = FILL_ALPHA), border = NA)
  lines(roc$fpr, roc$tpr, type = "s", lwd = 2.6, col = GREEN)

  axis(1, at = seq(0, 1, 0.2), col = GRID, col.axis = SLATE, cex.axis = 0.85)
  axis(2, at = seq(0, 1, 0.2), col = GRID, col.axis = SLATE, cex.axis = 0.85, las = 1)
  mtext("1 - Specificity", side = 1, line = 2.6, col = INK, cex = 0.95)
  mtext("Sensitivity",     side = 2, line = 2.9, col = INK, cex = 0.95)

  # title + the split as a subtitle, so the figure is self-documenting when it
  # travels into the deck or the LaTeX appendix without its caption
  mtext("ROC Curve — Out-of-Sample Test", side = 3, line = 2.6,
        cex = 1.15, font = 2, col = NAVY)
  mtext(sprintf("Trained on %d–%d  ·  tested on %d–%d",
                min(train$year), max(train$year),
                min(test$year),  max(test$year)),
        side = 3, line = 1.1, cex = 0.8, col = SLATE)

  # Key panel, parked in the empty lower-right below the curve. Filled with the
  # opaque WASH so it is indistinguishable from the shaded area it sits on, but
  # opaque enough that no gridline runs through the text.
  rect(0.565, 0.112, 0.995, 0.345, col = WASH, border = NA)

  # headline AUC
  text(0.585, 0.30, sprintf("AUC: %.3f", auc_test),
       adj = 0, cex = 1.25, font = 2, col = GREEN)
  text(0.585, 0.225, sprintf("n = %d campaigns", nrow(test)),
       adj = 0, cex = 0.85, col = SLATE)
  text(0.585, 0.155, "0.50 = coin flip",
       adj = 0, cex = 0.8, font = 3, col = SLATE)

  invisible(file)
}

draw_roc("figures/roc_train_test_split.png", bg = "#FFFFFF")
cat("[fig] wrote figures/roc_train_test_split.png\n")

# Optional deck-tone variant, if the slide background is the light deck fill:
#   draw_roc("figures/roc_train_test_split_light.png", bg = LIGHT)
