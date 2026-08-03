# =============================================================================
# fig_2026_ranked_cut.R -- cut-down version of fig_2026_ranked_probabilities.png
# -----------------------------------------------------------------------------
# The full figure has all 47 teams, which is unreadable at slide size. This makes
# a "head + tail" version: the top N and bottom M teams by predicted P(advance),
# same deck palette (green = actually advanced, slate = eliminated, dashed 0.5).
#
# Two variants are written:
#   fig_2026_ranked_cut_break.png  -- dotted break row labelling the omitted middle
#   fig_2026_ranked_cut_nogap.png  -- bars run continuously, no break
#
# Base R only. Run from the project root:  source("fig_2026_ranked_cut.R")
#
# NOTE ON THE CUT: the top 7 (not 6) is deliberate. Uruguay is rank 7 and is the
# model's biggest false positive (p = 0.889, eliminated). Stopping at 6 leaves
# every visible bar a correct call, so the slate colour -- and the whole
# "the upsets it missed" point -- disappears from the top block.
# =============================================================================

# ---- ranked table (from logit_mens_groupstage_advance.R section 8b) ----------
# If you have just run that script, `rank26` is already in memory and this block
# is skipped, so the figure always reflects the live model fit.
if (!exists("rank26")) {
  rank26 <- data.frame(
    team_name = c(
      "Mexico","Brazil","Argentina","United States","England","Spain","Uruguay",
      "France","Belgium","Sweden","Switzerland","Canada","Netherlands","Paraguay",
      "Germany","Portugal","Scotland","Colombia","Austria","Croatia","Ecuador",
      "South Korea","Norway","Turkey","Bosnia and Herzegovina","Czechia","Morocco",
      "Tunisia","Japan","Australia","Iran","Saudi Arabia","Algeria","Ghana",
      "Ivory Coast","Senegal","South Africa","Haiti","Panama","Egypt","Curacao",
      "DR Congo","Cape Verde","Iraq","Qatar","Jordan","Uzbekistan"),
    advanced = c(
      1,1,1,1,1,1,0, 1,1,1,1,1,1,1, 1,1,0,1,1,1,1,
      0,1,0,1,0,1, 0,1,1,0,0,1,1, 1,1,1,0,0,1,0,
      1,1,0,0,0,0),
    p_advance = c(
      0.980,0.962,0.935,0.928,0.910,0.893,0.889,
      0.873,0.824,0.761,0.761,0.734,0.724,0.717,
      0.684,0.684,0.684,0.633,0.596,0.596,0.540,
      0.480,0.406,0.406,0.361,0.361,0.313,
      0.313,0.299,0.260,0.260,0.260,0.237,0.237,
      0.204,0.204,0.204,0.184,0.184,0.174,0.156,
      0.148,0.125,0.119,0.119,0.100,0.100),
    stringsAsFactors = FALSE)
}

# ---- deck palette (see Context.md 12.7) -------------------------------------
NAVY  <- "#1F3864"; INK   <- "#1A2233"; GREEN <- "#2E9E6B"
SLATE <- "#5B6472"; GRID  <- "#C7D0E0"; LIGHT <- "#F4F6FA"

# ---- headline numbers (edit if the fit changes) ------------------------------
AUC26 <- if (exists("auc26")) auc26 else 0.757
ACC26 <- if (exists("acc26")) acc26 else 0.681
N26   <- nrow(rank26)


draw_cut <- function(n_top = 7, n_bottom = 6, gap = TRUE,
                     file  = "figures/fig_2026_ranked_cut_break.png",
                     bg    = LIGHT,          # "#F4F6FA" deck tone, or "#FFFFFF"
                     width = 2000, height = 1300, res = 200) {

  d <- rbind(head(rank26, n_top), tail(rank26, n_bottom))
  n <- nrow(d)
  n_hidden <- N26 - n

  # y positions, top row first; insert one blank slot for the break if asked
  ypos <- seq_len(n) + c(rep(0, n_top), rep(if (gap) 1 else 0, n_bottom))
  ybrk <- n_top + 1                       # centre of the break band
  ymax <- max(ypos)

  dir.create(dirname(file), showWarnings = FALSE, recursive = TRUE)
  png(file, width = width, height = height, res = res, bg = bg)
  on.exit(dev.off())

  # xaxs = "i" pins the plot region to the data range, so a value label sitting
  # just past p = 0.98 (Mexico) would be clipped at the panel edge. Carry the
  # region a little past 1.0 and widen the right margin to make room; the axis
  # and gridlines are still drawn only out to 1.0.
  par(mar = c(4.4, 10.5, 4.6, 2.8), xaxs = "i", family = "sans", bg = bg)
  plot(NA, xlim = c(0, 1.07), ylim = c(ymax + 0.6, 0.4),
       axes = FALSE, xlab = "", ylab = "")

  # gridlines
  abline(v = seq(0, 1, 0.2), col = GRID, lwd = 1)

  # bars
  rect(0, ypos - 0.36, d$p_advance, ypos + 0.36,
       col = ifelse(d$advanced == 1, GREEN, SLATE), border = NA)

  # team names + value labels
  axis(2, at = ypos, labels = d$team_name, las = 1, tick = FALSE,
       line = -0.4, col.axis = INK, cex.axis = 0.92)
  # xpd = NA: belt-and-braces, lets a label spill into the right margin rather
  # than be silently cut off if the font metrics differ on another machine
  text(d$p_advance + 0.008, ypos, sprintf("%.2f", d$p_advance),
       adj = 0, cex = 0.72, col = SLATE, xpd = NA)

  # break row
  if (gap) {
    segments(0, ybrk, 1, ybrk, lty = 3, lwd = 1.6, col = "#9AA6BD")
    lab <- sprintf("%d teams omitted (ranks %d-%d)", n_hidden, n_top + 1, N26 - n_bottom)
    w   <- strwidth(lab, cex = 0.8)
    # sit the label to the RIGHT of the 0.5 line so the dashed threshold
    # doesn't cut through the text
    rect(0.515, ybrk - 0.30, 0.53 + w, ybrk + 0.30, col = bg, border = NA)
    text(0.525, ybrk, lab, adj = 0, cex = 0.8, font = 3, col = SLATE)
  }

  # 0.5 decision threshold. The label sits in the empty space to the RIGHT of
  # the dashed line, level with the first row of the bottom block (DR Congo),
  # on a background-filled patch so gridlines don't run through it -- same
  # treatment as the break-row label above.
  segments(0.5, 0.4, 0.5, ymax + 0.6, lty = 2, lwd = 2, col = INK)
  thr    <- "0.5 threshold"
  thr_y  <- ypos[min(n_top + 1, n)]
  thr_w  <- strwidth(thr, cex = 0.78)
  rect(0.515, thr_y - 0.30, 0.53 + thr_w, thr_y + 0.30, col = bg, border = NA)
  text(0.525, thr_y, thr, adj = 0, cex = 0.78, col = INK)

  # x axis
  axis(1, at = seq(0, 1, 0.2), col = SLATE, col.axis = INK, cex.axis = 0.95)
  mtext("Predicted probability of advancing", side = 1, line = 2.7,
        at = 0.5, cex = 1.05, col = NAVY)   # at = 0.5 keeps it centred on the
                                            # 0-1 axis, not the widened region

  # titles
  mtext(sprintf("2026 World Cup -- top %d and bottom %d by predicted advancement",
                n_top, n_bottom),
        side = 3, line = 2.0, cex = 1.35, font = 2, col = NAVY)
  mtext(sprintf("Forward out-of-sample  -  AUC %.3f  -  accuracy %.3f  -  n = %d (%d shown)",
                AUC26, ACC26, N26, n),
        side = 3, line = 0.6, cex = 0.92, col = SLATE)

  # legend, parked in the empty space beside the short bottom bars
  legend("bottomright", inset = c(0.02, 0.06), bg = bg, box.col = bg,
         legend = c("Actually advanced", "Actually eliminated", "0.5 decision threshold"),
         fill   = c(GREEN, SLATE, NA), border = c(NA, NA, NA),
         lty    = c(NA, NA, 2), lwd = c(NA, NA, 2), col = c(NA, NA, INK),
         cex = 0.88, text.col = INK)

  invisible(file)
}

# ---- build the two slide PNGs (break-row variant, two backgrounds) -----------
draw_cut(7, 6, gap = TRUE, bg = LIGHT,
         file = "figures/fig_2026_ranked_cut_break_light.png")   # #F4F6FA deck tone
draw_cut(7, 6, gap = TRUE, bg = "#FFFFFF",
         file = "figures/fig_2026_ranked_cut_break_white.png")   # pure white

cat("[fig] wrote figures/fig_2026_ranked_cut_break_light.png",
    "and ..._white.png\n")

# Optional extras:
#   no break row, bars continuous
#     draw_cut(7, 6, gap = FALSE, bg = "#FFFFFF",
#              file = "figures/fig_2026_ranked_cut_nogap_white.png")
#   a different cut, e.g. top 8 / bottom 8
#     draw_cut(8, 8, gap = TRUE, bg = "#FFFFFF",
#              file = "figures/fig_2026_ranked_cut_8_8_white.png")
