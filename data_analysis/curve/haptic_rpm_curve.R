# Plot haptic intensity and vibration gap over RPM using hardcoded parameters.
# These values mirror the current tuning in the adapter.

# RPM thresholds (Engine RPM)
idle_rpm <- 20
desired_low_rpm <- 40
desired_high_rpm <- 55
redline_rpm <- 60
max_rpm <- 80

# Haptic tuning parameters
min_gap <- 50
max_gap <- 1000
min_intensity <- 0.3
max_intensity <- 1.0

script_dir <- getwd()

if (redline_rpm <= idle_rpm) {
  stop("Invalid RPM thresholds: redline must be greater than idle.")
}

rpm <- seq(0, max_rpm, length.out = 800)

calc_curve <- function(current_rpm) {
  if (current_rpm < idle_rpm) {
    # Keep output constant below idle.
    intensity <- max_intensity
    gap <- as.integer(min_gap)
  } else if (current_rpm < desired_low_rpm) {
    position <- (current_rpm - idle_rpm) / (desired_low_rpm - idle_rpm)
    position <- max(0, min(1, position))

    intensity <- max_intensity + (min_intensity - max_intensity) * (position ^ 2)
    gap <- as.integer(min_gap + (max_gap - min_gap) * position)
  } else if (current_rpm < desired_high_rpm) {
    intensity <- min_intensity
    gap <- as.integer(max_gap)
  } else if (current_rpm <= max_rpm) {
    position <- (current_rpm - desired_high_rpm) / (redline_rpm - desired_high_rpm)
    position <- max(0, min(1, position))
    taper <- 1 - (1 - position) ^ 2

    intensity <- min_intensity + (max_intensity - min_intensity) * taper
    gap <- as.integer(max_gap - (max_gap - min_gap) * position)
  } else {
    # Keep output constant above max RPM.
    intensity <- max_intensity
    gap <- as.integer(min_gap)
  }

  intensity_255 <- as.integer(intensity * 255)
  intensity_255 <- max(0, min(255, intensity_255))

  c(intensity_255 = intensity_255, gap_ms = gap)
}

curves <- t(vapply(rpm, calc_curve, c(intensity_255 = 0, gap_ms = 0)))
intensity <- curves[, "intensity_255"]
gap_ms <- curves[, "gap_ms"]

draw_plot <- function() {
  par(mar = c(5, 5, 4, 7) + 0.1, xaxs = "i", yaxs = "i")
  plot(
    rpm,
    intensity,
    type = "l",
    col = "#1f77b4",
    lwd = 3,
    xlim = c(idle_rpm - 5, redline_rpm + 5),
    ylim = c(0, 260),
    xaxt = "n",
    xlab = "Engine RPM (x1000)",
    ylab = "Haptic Intensity (0-255)"
  )

  axis(side = 1, at = seq(idle_rpm, redline_rpm, by = 10), labels = seq(idle_rpm, redline_rpm, by = 10) / 10)

  right_axis_max <- max_gap
  scaled_gap <- gap_ms / right_axis_max * 255
  lines(rpm, scaled_gap, col = "#d62728", lwd = 3, lty = 2)

  thresholds <- c(idle_rpm, desired_low_rpm, desired_high_rpm, redline_rpm)
  threshold_names <- c("Idle", "Desired Low", "Desired High", "Redline")
  line_cols <- c("#2ca02c", "#17becf", "#9467bd", "#ff7f0e")

  abline(v = thresholds, col = line_cols, lty = 3, lwd = 2)

  for (i in seq_along(thresholds)) {
    text(
      x = thresholds[i],
      y = 250,
      labels = "",
      srt = 90,
      pos = 4,
      cex = 0.8,
      col = line_cols[i],
      xpd = NA
    )
  }

  axis(
    side = 4,
    at = seq(0, 255, by = 51),
    labels = round(seq(0, right_axis_max, length.out = 6), 0)
  )
  mtext("Time Gap Between Vibrations (ms)", side = 4, line = 3)

  legend(
    "left",
    legend = c("Intensity", "Time Gap", threshold_names),
    col = c("#1f77b4", "#d62728", line_cols),
    lty = c(1, 2, 3, 3, 3, 3),
    lwd = c(3, 3, 2, 2, 2, 2),
    bg = "white"
  )

  grid(nx = NULL, ny = NULL, col = "#dddddd", lty = "dotted")
}

svg_output_path <- file.path(script_dir, "haptic_rpm_curve.svg")
if (requireNamespace("svglite", quietly = TRUE)) {
  svglite::svglite(svg_output_path, width = 12, height = 7)
} else {
  svg(svg_output_path, width = 12, height = 7)
}
draw_plot()
dev.off()

pdf_output_path <- file.path(script_dir, "haptic_rpm_curve.pdf")
pdf(pdf_output_path, width = 12, height = 7, useDingbats = FALSE)
draw_plot()
dev.off()

cat("Saved plot to:", svg_output_path, "\n")
cat("Saved plot to:", pdf_output_path, "\n")
cat("Thresholds (RPM):\n")
cat("  Idle:", idle_rpm, "\n")
cat("  Desired Low:", desired_low_rpm, "\n")
cat("  Desired High:", desired_high_rpm, "\n")
cat("  Redline:", redline_rpm, "\n")
