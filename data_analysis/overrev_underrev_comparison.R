# Compare overrev/underrev balance per participant with and without haptic feedback.

script_dir <- getwd()
input_dir <- file.path(script_dir, "inputs")

# Hardcoded desired RPM range and source files.
desired_low_rpm <- 40
desired_high_rpm <- 55

input_files <- c(
  "session_20260423_114619_01_without.csv",
  "session_20260423_115614_01_with.csv",
  "session_20260423_120138_02_without.csv",
  "session_20260423_120158_02_with.csv",
  "session_20260423_121736_03_without.csv",
  "session_20260423_121300_03_with.csv",
  "session_20260423_122843_04_without.csv",
  "session_20260423_122549_04_with.csv",
  "session_20260407_131212_05_without.csv",
  "session_20260407_132101_05_with.csv"
)

parse_file_meta <- function(file_name) {
  m <- regexec(".*_([0-9]{2})_(with|without)\\.csv$", file_name)
  parts <- regmatches(file_name, m)[[1]]
  if (length(parts) != 3) {
    stop(paste("Unexpected file name format:", file_name))
  }
  list(participant = parts[2], condition = parts[3])
}

compute_ratio <- function(file_name) {
  path <- file.path(input_dir, file_name)
  data <- read.csv(path, stringsAsFactors = FALSE)

  race_window <- data[
    data$track_position_percent > 0.01 & data$track_position_percent <= 1.00,
  ]

  over_count <- sum(race_window$current_rpm > desired_high_rpm, na.rm = TRUE)
  under_count <- sum(race_window$current_rpm < desired_low_rpm, na.rm = TRUE)

  raw_ratio <- if (under_count == 0) {
    if (over_count == 0) 1.0 else Inf
  } else {
    over_count / under_count
  }

  # Keep plotted range aligned with the requested y-axis [0.5, 2.0].
  plotted_ratio <- min(2.0, max(0.5, raw_ratio))

  meta <- parse_file_meta(file_name)
  list(
    participant = meta$participant,
    condition = meta$condition,
    over_count = over_count,
    under_count = under_count,
    raw_ratio = raw_ratio,
    plotted_ratio = plotted_ratio
  )
}

results <- lapply(input_files, compute_ratio)
participants <- sort(unique(vapply(results, function(x) x$participant, character(1))))
conditions <- c("without", "with")

ratio_matrix <- matrix(
  NA_real_,
  nrow = length(conditions),
  ncol = length(participants),
  dimnames = list(conditions, participants)
)

for (item in results) {
  ratio_matrix[item$condition, item$participant] <- item$plotted_ratio
}

draw_plot <- function() {
  par(mar = c(5, 5, 4, 7) + 0.1, xaxs = "i", yaxs = "i")

  # Use a symmetric log2-ratio scale so 0.5 and 2.0 are equal distance from 1.0.
  ratio_ticks <- c(0.5, 1.0, 2.0)
  y_ticks <- log2(ratio_ticks)
  transformed_values <- log2(as.vector(ratio_matrix))

  mids <- barplot(
    ratio_matrix,
    beside = TRUE,
    col = NA,
    ylim = c(0.5, 2.0),
    ylab = "Overrev / Underrev Ratio",
    xlab = "Participant",
    names.arg = participants,
    main = "Overrev vs Underrev Balance by Participant",
    border = NA,
    axes = FALSE,
    plot = FALSE
  )

  plot.new()
  plot.window(
    xlim = range(mids) + c(-0.8, 0.8),
    ylim = c(-1.0, 1.0),
    xaxs = "i",
    yaxs = "i"
  )

  axis(2, at = y_ticks, labels = ratio_ticks)
  axis(1, at = colMeans(mids), labels = participants)
  box(bty = "l")
  title(xlab = "Participant ID", ylab = "Ratio of Overrev to Underrev")

  grid(nx = NULL, ny = NULL, col = "#dddddd", lty = "dotted")

  bar_half_width <- 0.32
  bar_cols <- c("#d62728", "#1f77b4")
  values <- as.vector(ratio_matrix)

  for (i in seq_along(transformed_values)) {
    x <- as.vector(mids)[i]
    y0 <- 0.0
    y1 <- transformed_values[i]
    rect(
      xleft = x - bar_half_width,
      ybottom = min(y0, y1),
      xright = x + bar_half_width,
      ytop = max(y0, y1),
      col = bar_cols[((i - 1) %% length(bar_cols)) + 1],
      border = NA
    )
  }

  abline(h = 0.0, col = "#2ca02c", lwd = 2, lty = 2)

  text(
    x = as.vector(mids),
    y = pmax(
      pmin(transformed_values + ifelse(transformed_values >= 0, 0.06, -0.06), 0.98),
      -0.98
    ),
    labels = sprintf("%.2f", values),
    cex = 0.8
  )

  legend(
    "top",
    legend = c("Without Haptic", "With Haptic", "Even (1.0)"),
    fill = c("#d62728", "#1f77b4", NA),
    border = c(NA, NA, NA),
    lty = c(NA, NA, 2),
    lwd = c(NA, NA, 2),
    col = c(NA, NA, "#2ca02c"),
    bg = "white"
  )
}

svg_output <- file.path(script_dir, "overrev_underrev_comparison.svg")
if (requireNamespace("svglite", quietly = TRUE)) {
  svglite::svglite(svg_output, width = 12, height = 7)
} else {
  svg(svg_output, width = 12, height = 7)
}
draw_plot()
dev.off()

pdf_output <- file.path(script_dir, "overrev_underrev_comparison.pdf")
pdf(pdf_output, width = 12, height = 7, useDingbats = FALSE)
draw_plot()
dev.off()

cat("Saved plot to:", svg_output, "\n")
cat("Saved plot to:", pdf_output, "\n")
cat("Race completion filter: track_position_percent > 0.01 and <= 1.00\n")
