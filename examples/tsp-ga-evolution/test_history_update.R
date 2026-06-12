#!/usr/bin/env Rscript

library(irace)
source("../../R/code_evolution.R")

# Mock data similar to what irace would have
mock_elite_configs <- data.frame(
  .ID. = c(19, 6, 4),
  .RANK. = c(34.5, 41.2, 45.8),  # Lower rank = better
  .VARIANT. = c("variant_2_iter3", "original", "variant_1_iter3"),
  stringsAsFactors = FALSE
)

mock_scenario <- list(
  codeEvolution = TRUE,
  execDir = "."
)

cat("Testing performance history update with actual data...\n")

# Copy your actual history file for testing
file.copy(".irace_evo_history.json", "backup_history.json", overwrite = TRUE)

cat("Before update - last entry:\n")
history <- jsonlite::fromJSON(readLines(".irace_evo_history.json"))
print(history[[length(history)]])

# Test the update function
update_performance_history(mock_elite_configs, mock_scenario)

cat("\nAfter update - last entry:\n")
updated_history <- jsonlite::fromJSON(readLines(".irace_evo_history.json"))
print(updated_history[[length(updated_history)]])

# Restore backup
file.copy("backup_history.json", ".irace_evo_history.json", overwrite = TRUE)
file.remove("backup_history.json")