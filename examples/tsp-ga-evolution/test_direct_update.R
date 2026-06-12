#!/usr/bin/env Rscript

library(irace)
source("../../R/code_evolution.R")

# Mock data similar to what irace would have
mock_elite_configs <- data.frame(
  .ID. = c(19, 6, 4),
  .RANK. = c(34.5, 41.2, 45.8),
  .VARIANT. = c("variant_2_iter3", "original", "variant_1_iter3"),
  stringsAsFactors = FALSE
)

mock_scenario <- list(
  codeEvolution = TRUE,
  execDir = "."
)

cat("Before update:\n")
if (file.exists(".irace_evo_history.json")) {
  history <- jsonlite::fromJSON(readLines(".irace_evo_history.json"), simplifyDataFrame = FALSE)
  print(names(history[[length(history)]]))
} else {
  cat("No history file found\n")
}

# Test the update function directly
update_performance_history(mock_elite_configs, mock_scenario)

cat("\nAfter update:\n")
if (file.exists(".irace_evo_history.json")) {
  updated_history <- jsonlite::fromJSON(readLines(".irace_evo_history.json"), simplifyDataFrame = FALSE)
  last_entry <- updated_history[[length(updated_history)]]
  print(names(last_entry))
  cat("Best performance:", last_entry$best_performance, "\n")
  cat("Winning strategy:", last_entry$winning_strategy, "\n")
} else {
  cat("No history file found after update\n")
}