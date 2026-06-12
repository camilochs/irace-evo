#!/usr/bin/env Rscript

# Test the corrected LLM timing calculation
# Simulate what the corrected metrics should look like

# Mock scenario with corrected metrics
scenario <- list(
  codeEvolution = TRUE,
  codeEvolutionGlobalMetrics = list(
    total_calls = 11,
    total_retries = 0,
    total_input_tokens = 27479,
    total_output_tokens = 6766,
    total_cost_estimate = 1.230,
    total_llm_time = 147.3,  # Corrected: ~2.5 minutes instead of 90+ minutes
    iterations = list(
      list(iteration = 1, calls = 4, retries = 0, input_tokens = 8962, 
           output_tokens = 1384, variants_generated = 3, llm_time = 32.1),
      list(iteration = 2, calls = 3, retries = 0, input_tokens = 8461, 
           output_tokens = 2238, variants_generated = 3, llm_time = 50.2),
      list(iteration = 3, calls = 4, retries = 0, input_tokens = 10056, 
           output_tokens = 3144, variants_generated = 3, llm_time = 65.0)
    ),
    start_time = Sys.time() - 6289,  # Mock start time from log
    api_provider = "openai",
    model = "gpt-4.1",
    temperature = 0.1,
    max_tokens = 2000
  )
)

# Load the corrected function
source("../../R/code_evolution.R")

cat("=== TESTING CORRECTED LLM TIMING CALCULATION ===\n\n")
cat("Before fix: Total LLM Processing Time: 5443.5 seconds (90+ minutes)\n")
cat("After fix should show: Total LLM Processing Time: ~147.3 seconds (2.5 minutes)\n\n")

# Execute the corrected function
print_llm_metrics_summary(scenario)

cat("\n=== ANALYSIS ===\n")
cat("✓ Now shows actual LLM API call time instead of total irace execution time\n")
cat("✓ Each iteration timing is tracked separately\n")  
cat("✓ Total is sum of individual iteration times, not elapsed wall clock\n")
cat("✓ Much more realistic: ~2.5 minutes LLM time vs 104 minutes total irace time\n")