# Test script for LLM functionality without running full irace
library(irace)

test_llm_generation <- function() {
  cat("Testing LLM generation directly...\n")
  
  # Create a minimal scenario
  scenario <- list(
    codeEvolution = TRUE,
    codeEvolutionConfig = "./code-evolution.json",
    codeEvolutionVariants = 2,
    execDir = "./"
  )
  
  # Create test iteration stats (simulating iteration 2)
  iteration_stats <- list(
    iteration = 2,
    configurations_count = 8,
    experiments_used = 50,
    total_experiments = 100,
    time_used = 300,
    best_cost = 1500.0
  )
  
  # Create test performance stats
  performance_stats <- list(
    best_configuration_cost = 1500.0,
    worst_configuration_cost = 2000.0,
    median_cost = 1750.0,
    configurations = data.frame(
      .ID. = 1:3,
      cost = c(1500.0, 1600.0, 1700.0),
      population_size = c(100, 150, 200),
      elite_pro = c(0.15, 0.20, 0.18),
      mutation_pro = c(0.15, 0.12, 0.18),
      rhoe = c(0.65, 0.70, 0.60)
    )
  )
  
  cat("Configuration loaded:\n")
  cat("- Using strategy: innovate_heuristic_design\n")
  cat("- Target variants: 2\n")
  cat("- Simulating iteration 2\n\n")
  
  # Test the generation
  tryCatch({
    variants <- generate_code_variants(
      scenario = scenario,
      iteration_stats = iteration_stats,
      performance_stats = performance_stats
    )
    
    cat("SUCCESS! Generated variants:\n")
    for (i in seq_len(nrow(variants))) {
      cat(sprintf("  Variant %d: %s (strategy: %s)\n", 
                  i, variants$variant_id[i], variants$strategy[i]))
    }
    
  }, error = function(e) {
    cat("ERROR:", conditionMessage(e), "\n")
    traceback()
  })
}

# Run the test
test_llm_generation()