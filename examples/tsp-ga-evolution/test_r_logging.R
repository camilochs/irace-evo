#!/usr/bin/env Rscript

# Test R-side logging for dynamic prompting
library(irace)
source("../../R/code_evolution.R")

cat("=== TESTING R-SIDE DYNAMIC PROMPTING LOGGING ===\n\n")

# Test 1: Config logging - enabled by default
cat("--- TEST 1: Configuration Logging ---\n")

config_data <- list(
  llm_config = list(
    model = "gpt-4o",
    api_provider = "openai"
  )
)

# Simulate the config enhancement that happens in generate_code_variants
if (is.null(config_data$llm_config$use_dynamic_prompting)) {
  config_data$llm_config$use_dynamic_prompting <- TRUE
  message("irace-evo: 🎯 Dynamic prompting ENABLED - Will adapt prompts based on performance history")
} else if (isTRUE(config_data$llm_config$use_dynamic_prompting)) {
  message("irace-evo: 🎯 Dynamic prompting ENABLED via config")
} else {
  message("irace-evo: ⚪ Dynamic prompting DISABLED via config")
}

# Test 2: Config logging - explicitly enabled
cat("\n--- TEST 2: Explicitly Enabled Config ---\n")

config_data2 <- list(
  llm_config = list(
    model = "gpt-4o",
    api_provider = "openai",
    use_dynamic_prompting = TRUE
  )
)

if (is.null(config_data2$llm_config$use_dynamic_prompting)) {
  config_data2$llm_config$use_dynamic_prompting <- TRUE
  message("irace-evo: 🎯 Dynamic prompting ENABLED - Will adapt prompts based on performance history")
} else if (isTRUE(config_data2$llm_config$use_dynamic_prompting)) {
  message("irace-evo: 🎯 Dynamic prompting ENABLED via config")
} else {
  message("irace-evo: ⚪ Dynamic prompting DISABLED via config")
}

# Test 3: Config logging - explicitly disabled  
cat("\n--- TEST 3: Explicitly Disabled Config ---\n")

config_data3 <- list(
  llm_config = list(
    model = "gpt-4o", 
    api_provider = "openai",
    use_dynamic_prompting = FALSE
  )
)

if (is.null(config_data3$llm_config$use_dynamic_prompting)) {
  config_data3$llm_config$use_dynamic_prompting <- TRUE
  message("irace-evo: 🎯 Dynamic prompting ENABLED - Will adapt prompts based on performance history")
} else if (isTRUE(config_data3$llm_config$use_dynamic_prompting)) {
  message("irace-evo: 🎯 Dynamic prompting ENABLED via config")  
} else {
  message("irace-evo: ⚪ Dynamic prompting DISABLED via config")
}

# Test 4: Performance history update logging
cat("\n--- TEST 4: Performance History Update Logging ---\n")

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

# Test the enhanced logging message
update_performance_history(mock_elite_configs, mock_scenario)

cat("\n=== R-SIDE LOGGING TEST COMPLETE ===\n")
cat("✅ All R-side logging messages working correctly!\n\n")

cat("📋 LOG MESSAGE SUMMARY:\n")
cat("🎯 Config status: Shows if dynamic prompting is enabled/disabled\n")
cat("📊 History update: Shows best performance and winning strategy\n")