#!/usr/bin/env Rscript

# Load irace
library(irace)

# Mock the winning configuration based on the log
best_config <- data.frame(
  .ID. = 19,
  population_size = 284,
  elite_pro = 0.1846,
  mutation_pro = 0.1824,
  rhoe = 0.5694,
  .PARENT. = 6,
  .RANK. = 34.0,
  .WEIGHT. = 0.4,
  .VARIANT. = "variant_2_iter3",
  stringsAsFactors = FALSE
)

# Mock scenario
scenario <- list(
  codeEvolution = TRUE,
  sourceConfig = list(
    function_name = "order_chromosome"
  )
)

# Load the functions from code_evolution.R
source("../../R/code_evolution.R")

# Execute the winning variant function comparison
print_winning_variant_function(best_config, scenario)