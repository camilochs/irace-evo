#!/usr/bin/env Rscript

# Fix the performance history manually with data from the logs
library(irace)
source("../../R/code_evolution.R")

cat("=== MANUAL HISTORY FIX ===\n")

# Read current history
current_history <- jsonlite::fromJSON(readLines(".irace_evo_history.json"), simplifyDataFrame = FALSE)

cat("Current history has", length(current_history), "entries\n")

# From your logs, I can extract the performance data:
# Iteration 2 best: Configuration 10 with rank 22.5 (variant_2_iter1)
# Let's update the history with this information

if (length(current_history) >= 2) {
  # Update iteration 2 with the performance data from your logs
  current_history[[2]]$best_performance <- 21.5  # From your logs: best_cost_so_far: 21.5
  current_history[[2]]$best_configuration_id <- 10
  current_history[[2]]$winning_strategy <- "variant_2_iter1"
  
  cat("Updated iteration 2 with:\n")
  cat("  Best performance: 21.5\n")
  cat("  Best config ID: 10\n") 
  cat("  Winning strategy: variant_2_iter1\n")
}

# Save the updated history
updated_json <- jsonlite::toJSON(current_history, auto_unbox = TRUE, pretty = TRUE)
writeLines(updated_json, ".irace_evo_history.json")

cat("✓ History file updated successfully\n")

# Verify the update
updated_history <- jsonlite::fromJSON(readLines(".irace_evo_history.json"), simplifyDataFrame = FALSE)
if (length(updated_history) >= 2) {
  last_entry <- updated_history[[2]]
  cat("\nVerification - Latest entry:\n")
  cat("  Iteration:", last_entry$iteration, "\n")
  cat("  Best performance:", last_entry$best_performance, "\n")
  cat("  Winning strategy:", last_entry$winning_strategy, "\n")
}

cat("\n🎯 Now dynamic prompting should work with this performance data!\n")