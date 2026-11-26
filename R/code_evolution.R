#' Code Evolution for irace-evo
#'
#' Implements automatic code generation and evolution using LLMs
#' integrated with the irace racing algorithm.
#'
#' @author Camilo Chacón Sartori
#' @keywords internal

# Initialize reticulate and Python backend
.irace_evo_env <- new.env(parent = emptyenv())
.irace_evo_env$python_initialized <- FALSE

# irace_note() prints its arguments as they are, so a message needs its own
# newline; without one the next message ran into it.
evo_note <- function(...) irace_note(sub("\n*$", "\n", paste0(..., collapse = "")))

initialize_python_backend <- function(scenario) {
  if (isTRUE(.irace_evo_env$python_initialized)) return(TRUE)
  
  # SLURM-specific initialization only on master node
  if (!is.null(scenario$batchmode) && scenario$batchmode == "slurm") {
    return(initialize_python_backend_slurm(scenario))
  }
  
  # Check for reticulate
  if (!requireNamespace("reticulate", quietly = TRUE)) {
    irace_error("Code evolution requires the 'reticulate' R package. Install with: install.packages('reticulate')")
  }
  
  # Check for jsonlite
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    irace_error("Code evolution requires the 'jsonlite' R package. Install with: install.packages('jsonlite')")
  }
  
  # Try to initialize Python backend
  tryCatch({
    # RETICULATE_PYTHON picks the interpreter; without it, the first of the
    # usual paths that exists.
    python_env_path <- Sys.getenv("RETICULATE_PYTHON")
    if (nzchar(python_env_path)) {
      if (!file.exists(python_env_path))
        irace_error("RETICULATE_PYTHON points to a file that does not exist: ", python_env_path)
      reticulate::use_python(python_env_path, required = TRUE)
    } else {
      for (py_path in c("/usr/bin/python3", "/usr/local/bin/python3", "/opt/homebrew/bin/python3", "/usr/bin/python")) {
        if (file.exists(py_path)) {
          reticulate::use_python(py_path, required = TRUE)
          break
        }
      }
    }
    if (!reticulate::py_available(initialize = TRUE)) {
      irace_error("Python is not available. Code evolution needs Python 3.9 or later; ",
                  "set RETICULATE_PYTHON to its path.")
    }
    evo_note("irace-evo: Python ", reticulate::py_config()$version, " at ", reticulate::py_config()$python)

    # Look for Python modules in inst/python/
    python_path <- system.file("python", package = "irace", mustWork = TRUE)
    if (!dir.exists(python_path)) {
      irace_error("Python modules directory not found: ", python_path)
    }
    
    reticulate::py_run_string(paste0("import sys; sys.path.append('", python_path, "')"))
    
    # Test required Python modules
    required_modules <- c("code_manager", "llm_service", "compilation", "strategies", "language_handlers")
    for (module in required_modules) {
      result <- tryCatch({
        reticulate::py_run_string(paste0("import ", module))
        TRUE
      }, error = function(e) conditionMessage(e))

      if (!isTRUE(result)) {
        irace_error("Failed to import the Python module '", module, "': ", result)
      }
    }
    
    .irace_evo_env$python_initialized <- TRUE
    evo_note("irace-evo: Python backend initialized successfully")
    return(TRUE)
    
  }, error = function(e) {
    irace_error("Failed to initialize the Python backend for code evolution: ", e$message,
                " (If a Python package is missing: pip install -r ",
                system.file("python", "requirements.txt", package = "irace"), ")")
  })
}

#' Initialize Python backend for SLURM environments
#'
#' @param scenario irace scenario
#' @return TRUE if successful
initialize_python_backend_slurm <- function(scenario) {
  
  # Only initialize on master node (rank 0)
  is_master_node <- Sys.getenv("SLURM_PROCID", "0") == "0"
  
  if (!is_master_node) {
    evo_note("irace-evo: Worker node detected, skipping Python initialization")
    .irace_evo_env$python_initialized <- TRUE
    return(TRUE)
  }
  
  evo_note("irace-evo: Initializing Python backend on SLURM master node")
  
  # Standard initialization for master node
  if (!requireNamespace("reticulate", quietly = TRUE)) {
    irace_error("Code evolution requires the 'reticulate' R package on master node. Install with: install.packages('reticulate')")
  }
  
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    irace_error("Code evolution requires the 'jsonlite' R package on master node. Install with: install.packages('jsonlite')")
  }
  
  tryCatch({
    if (!reticulate::py_available()) {
      irace_error("Python is not available on master node. Code evolution requires Python 3.7+")
    }
    
    python_path <- system.file("python", package = "irace", mustWork = TRUE)
    if (!dir.exists(python_path)) {
      irace_error("Python modules directory not found on master node: ", python_path)
    }
    
    reticulate::py_run_string(paste0("import sys; sys.path.append('", python_path, "')"))
    
    required_modules <- c("code_manager", "llm_service", "compilation", "strategies", "language_handlers")
    for (module in required_modules) {
      result <- tryCatch({
        reticulate::py_run_string(paste0("import ", module))
        TRUE
      }, error = function(e) FALSE)
      
      if (!result) {
        irace_error("Failed to import required Python module on master node: ", module)
      }
    }
    
    # Verify API keys are available
    check_llm_credentials_slurm()
    
    .irace_evo_env$python_initialized <- TRUE
    evo_note("irace-evo: SLURM master node Python backend initialized successfully")
    return(TRUE)
    
  }, error = function(e) {
    irace_error("Failed to initialize Python backend on SLURM master node. ",
               "Error1: ", e$message)
  })
}

#' Setup LLM credentials from configuration
#'
#' @param config_data Configuration data loaded from JSON
setup_llm_credentials <- function(config_data) {
  
  # Extract API key from config if available
  if (!is.null(config_data$llm_config$api_key) && nzchar(config_data$llm_config$api_key)) {
    api_provider <- if (is.null(config_data$llm_config$api_provider)) "openai" else config_data$llm_config$api_provider
    
    if (api_provider == "openai") {
      # Set OpenAI API key as environment variable
      Sys.setenv(OPENAI_API_KEY = config_data$llm_config$api_key)
      evo_note("irace-evo: OpenAI API key configured from config file")
    } else if (api_provider == "anthropic") {
      # Set Anthropic API key as environment variable  
      Sys.setenv(ANTHROPIC_API_KEY = config_data$llm_config$api_key)
      evo_note("irace-evo: Anthropic API key configured from config file")
    } else {
      irace_warning("irace-evo: Unknown API provider: ", api_provider)
    }
  } else {
    # Check if environment variables are already set
    openai_key <- Sys.getenv("OPENAI_API_KEY", "")
    anthropic_key <- Sys.getenv("ANTHROPIC_API_KEY", "")
    
    if (openai_key == "" && anthropic_key == "") {
      irace_error("No LLM API keys found. Either set api_key in config file or set OPENAI_API_KEY/ANTHROPIC_API_KEY environment variables.")
    }
  }
}

#' Check LLM credentials in SLURM environment
check_llm_credentials_slurm <- function() {
  
  openai_key <- Sys.getenv("OPENAI_API_KEY", "")
  anthropic_key <- Sys.getenv("ANTHROPIC_API_KEY", "")
  
  if (openai_key == "" && anthropic_key == "") {
    irace_error("No LLM API keys found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables in your SLURM job script.")
  }
  
  if (openai_key != "") {
    evo_note("irace-evo: OpenAI API key detected")
  }
  
  if (anthropic_key != "") {
    evo_note("irace-evo: Anthropic API key detected")
  }
}

#' Generate code variants using LLM
#'
#' @param elite_configs List of elite configurations from current iteration
#' @param iteration_stats Statistics from current iteration
#' @param scenario irace scenario with code evolution settings
#' @return List of generated code variants with their executables
generate_code_variants <- function(elite_configs, iteration_stats, scenario, num_variants = NULL) {
  config_data <- jsonlite::fromJSON(scenario$codeEvolutionConfig)
  # The keys go into the environment before Python starts, so its clients
  # find them there; they are never written into a command or a log.
  setup_llm_credentials(config_data)
  if (!initialize_python_backend(scenario)) {
    irace_error("Cannot initialize Python backend for code evolution")
  }

  # Ranks of the elites (lower is better). The first iteration has no race
  # yet, so it has no ranks.
  costs <- elite_configs$.RANK.
  if (is.null(costs) || !length(costs) || all(is.na(costs))) costs <- NA_real_
  best_cost_so_far <- suppressWarnings(min(costs, na.rm = TRUE))
  average_cost <- mean(costs, na.rm = TRUE)
  worst_cost <- suppressWarnings(max(costs, na.rm = TRUE))
  finite <- function(x) if (is.finite(x)) x else NA_real_

  context <- list(
    iteration_context = list(
      current_iteration = iteration_stats$iteration,
      max_iterations = iteration_stats$nb_iterations,
      elite_configurations = elite_configs
    ),
    performance_stats = list(
      best_cost_so_far = finite(best_cost_so_far),
      average_cost = finite(average_cost),
      worst_cost = finite(worst_cost),
      performance_range = finite(worst_cost - best_cost_so_far),
      convergence_trend = if (iteration_stats$iteration > 1) "improving" else "initial",
      elite_rankings = elite_configs$.RANK.,
      num_configurations_tested = nrow(elite_configs)
    ),
    improvement_guidance = list(
      performance_gap = finite(average_cost - best_cost_so_far),
      ranking_pressure = finite(best_cost_so_far / worst_cost)
    ),
    target_variants = if (!is.null(num_variants)) num_variants else scenario$codeEvolutionVariants,
    scenario_config = list(execDir = scenario$execDir),
    elite_configurations = elite_configs
  )

  # A single strategy must still reach Python as a list.
  if (!is.null(config_data$evolution_config$available_strategies)) {
    config_data$evolution_config$available_strategies <- as.list(config_data$evolution_config$available_strategies)
  }
  # Adapting the prompt to the performance history is not part of the
  # method described in the paper, so it is off unless the configuration
  # turns it on.
  if (is.null(config_data$llm_config$use_dynamic_prompting)) {
    config_data$llm_config$use_dynamic_prompting <- FALSE
  }
  config_data$llm_config$scenario_config <- list(execDir = scenario$execDir)
  # The key stays in the environment; the configuration handed to Python
  # (and printed in its logs) does not carry it.
  config_data$llm_config$api_key <- NULL

  tryCatch({
    # The data travels as Python objects, not spliced into code: nothing
    # needs escaping, and the command that is logged holds no data.
    reticulate::py_run_string("import json, os")
    py_os <- reticulate::import("os", convert = FALSE)
    for (key in c("OPENAI_API_KEY", "ANTHROPIC_API_KEY")) {
      value <- Sys.getenv(key, "")
      if (nzchar(value)) py_os$environ$`__setitem__`(key, value)
    }
    py_main <- reticulate::import_main(convert = FALSE)
    py_main$irace_evo_context_json <- as.character(jsonlite::toJSON(context, auto_unbox = TRUE, na = "null"))
    py_main$irace_evo_config_json <- as.character(jsonlite::toJSON(config_data, auto_unbox = TRUE, na = "null"))
    python_command <- paste0(
      "from logging_config import setup_logging\n",
      "setup_logging()\n",
      "import code_manager\n",
      "context = json.loads(irace_evo_context_json)\n",
      "config = json.loads(irace_evo_config_json)\n",
      "manager = code_manager.CodeEvolutionManager(config)\n",
      "variants = manager.generate_and_compile_variants(context)"
    )

    llm_start_time <- Sys.time()
    reticulate::py_run_string(python_command)
    llm_processing_time <- as.numeric(difftime(Sys.time(), llm_start_time, units = "secs"))
    python_result <- reticulate::py$variants

    llm_log_dir <- file.path(scenario$execDir, "irace-evo-llm-logs")
    dir.create(llm_log_dir, recursive = TRUE, showWarnings = FALSE)
    tryCatch(cat(
      "=== Python execution (iteration ", iteration_stats$iteration, ") ===\n",
      "Timestamp: ", format(Sys.time()), "\n\n",
      "=== Python command ===\n", python_command, "\n\n",
      "=== Result structure ===\n",
      paste(utils::capture.output(utils::str(python_result)), collapse = "\n"), "\n\n",
      sep = "", file = file.path(llm_log_dir, "python_execution.log"), append = TRUE),
      error = function(e) irace_warning("irace-evo: Failed to save execution log: ", e$message))

    if (is.null(python_result) || length(python_result) < 2) {
      irace_error("Invalid Python result format. Expected list with variants and metrics.")
    }
    variants <- python_result[[1]]
    metrics <- python_result[[2]]
    if (is.null(variants) || length(variants) == 0) {
      # The new configurations then take the surviving variants and the original.
      irace_warning("irace-evo: no code variant was generated in iteration ", iteration_stats$iteration)
      variants <- list()
    }
    metrics$llm_processing_time <- llm_processing_time
    processed_variants <- process_generated_variants(variants, scenario, iteration_stats$iteration)
    list(variants = processed_variants, metrics = metrics)
  }, error = function(e) {
    irace_error("Code variant generation failed: ", conditionMessage(e))
  })
}

#' Process generated variants from Python backend
#'
#' @param variants Raw variants from Python
#' @param scenario irace scenario
#' @param current_iteration Current iteration number
#' @return Processed list of variants ready for racing
process_generated_variants <- function(variants, scenario, current_iteration = 1) {
  
  processed_variants <- list()
  
  # Create directory for saving source code files
  source_log_dir <- file.path(scenario$execDir, "irace-evo-sources")
  if (!dir.exists(source_log_dir)) {
    dir.create(source_log_dir, recursive = TRUE, showWarnings = FALSE)
  }
  
  # Create directory for detailed LLM logs
  llm_log_dir <- file.path(scenario$execDir, "irace-evo-llm-logs")
  if (!dir.exists(llm_log_dir)) {
    dir.create(llm_log_dir, recursive = TRUE, showWarnings = FALSE)
  }
  
  for (i in seq_along(variants)) {
    variant <- variants[[i]]
    
    # Handle special case for elite preserved variants
    if (!is.null(variant$strategy) && variant$strategy == "elite_preserved") {
      # For elite variants, maintain consistent naming but mark as preserved
      variant_id <- paste0("variant_", i-1, "_iter", current_iteration, "_elite")
      evo_note("irace-evo: Elite variant preserved as: ", variant_id)
    } else {
      # Save source code to file for logging with iteration number (0-indexed to match Python)
      variant_id <- paste0("variant_", i-1, "_iter", current_iteration)
    }
    source_file_path <- file.path(source_log_dir, paste0(variant_id, source_extension(scenario)))
    
    # Write source code to file
    if (!is.null(variant$code) && nzchar(variant$code)) {
      tryCatch({
        writeLines(variant$code, source_file_path)
        evo_note("irace-evo: Saved source code to ", source_file_path)
      }, error = function(e) {
        irace_warning("irace-evo: Failed to save source code for ", variant_id, ": ", e$message)
      })
    }
    
    # Save detailed variant information to log file
    variant_log_file <- file.path(llm_log_dir, paste0(variant_id, "_info.txt"))
    variant_strategy <- if (is.null(variant$strategy)) "unknown" else variant$strategy
    variant_parent <- if (is.null(variant$parent)) "initial" else variant$parent
    
    # Safe access to executable field
    variant_executable <- if (!is.null(variant$executable)) variant$executable else "not_set"
    compilation_success <- if (!is.null(variant$executable) && nzchar(variant$executable)) {
      file.exists(variant$executable)
    } else {
      "unknown"
    }
    
    variant_info <- paste0(
      "=== ", variant_id, " Information ===\n",
      "Strategy: ", variant_strategy, "\n",
      "Parent: ", variant_parent, "\n",
      "Executable: ", variant_executable, "\n",
      "Compilation Success: ", compilation_success, "\n",
      "Code Length: ", if (!is.null(variant$code)) nchar(variant$code) else 0, " characters\n",
      "Fingerprint: ", if (!is.null(variant$fingerprint)) variant$fingerprint else "unknown", "\n",
      "\n=== Generated Code Preview (First 500 chars) ===\n",
      if (!is.null(variant$code)) substr(variant$code, 1, 500) else "No code available", "\n",
      if (!is.null(variant$code) && nchar(variant$code) > 500) "... (truncated)" else "",
      "\n\n"
    )
    
    tryCatch({
      writeLines(variant_info, variant_log_file)
    }, error = function(e) {
      irace_warning("irace-evo: Failed to save variant info for ", variant_id, ": ", e$message)
    })
    
    # Python names each program after its iteration
    # (bin/algorithm_<variant>_iter<k>), so a later iteration never writes
    # over a program that configurations of an earlier one run.
    new_executable_path <- if (is.null(variant$executable) || !nzchar(variant$executable)) {
      irace_warning("irace-evo: Variant ", variant_id, " has no executable")
      NA_character_
    } else normalizePath(variant$executable, mustWork = FALSE)
    
    processed_variants[[i]] <- list(
      id = variant_id,
      executable_path = new_executable_path,
      source_code = variant$code,
      source_file_path = source_file_path,
      parent_id = if (is.null(variant$parent)) "initial" else variant$parent,
      compilation_success = !is.na(new_executable_path) && file.exists(new_executable_path),
      generation_strategy = if (is.null(variant$strategy)) "unknown" else variant$strategy
    )
  }
  
  # Only the variants that compiled race (Algorithm 1, line 6). None is not
  # an error: the new configurations then take the surviving variants and
  # the original.
  successful_variants <- Filter(function(x) isTRUE(x$compilation_success), processed_variants)
  if (length(successful_variants) < scenario$codeEvolutionVariants) {
    irace_warning("Only ", length(successful_variants), " out of ",
                  scenario$codeEvolutionVariants, " variants compiled successfully")
  }
  successful_variants
}

#' Pair the configurations of this iteration with code variants
#'
#' A configuration is a pair (theta, A) (paper, Sect. 2.2): once a
#' configuration has been given a variant it keeps it, on every instance and
#' in every later iteration. Only the configurations sampled in this
#' iteration get a variant here, chosen in turn from the pool of Algorithm 1,
#' line 7: the variants that passed validation in this iteration (A_valid),
#' the variants of the elite configurations (A_survived) and the original A0.
#' The new variants come first in the turn, so each gets a configuration
#' whenever there are as many new configurations as new variants.
#'
#' The pairing is written to `.irace_evo_variants.csv` in execDir
#' (config_id, executable_path, variant_id), which the target runner reads.
#'
#' @param variants List of new, validated variants (may be empty)
#' @param scenario irace scenario
#' @param elite_ids IDs of the elite configurations entering this race
#' @param new_ids IDs of the configurations sampled in this iteration
#' @return Updated scenario
setup_variant_target_runner <- function(variants, scenario, elite_ids = integer(0), new_ids = integer(0)) {
  config_data <- jsonlite::fromJSON(scenario$codeEvolutionConfig)
  base_name <- tools::file_path_sans_ext(basename(config_data$source_config$source_file))
  original_variant <- list(id = "original",
                           executable_path = file.path(scenario$execDir, "bin", base_name))

  variant_map_file <- file.path(scenario$execDir, ".irace_evo_variants.csv")
  old_map <- if (file.exists(variant_map_file))
               utils::read.csv(variant_map_file, stringsAsFactors = FALSE)
             else data.frame(config_id = integer(0), executable_path = character(0),
                             variant_id = character(0), stringsAsFactors = FALSE)

  # A_survived: the variants the elite configurations were paired with.
  survived_rows <- old_map[old_map$config_id %in% elite_ids, , drop = FALSE]
  survived_rows <- survived_rows[!duplicated(survived_rows$variant_id), , drop = FALSE]
  survived <- lapply(seq_len(nrow(survived_rows)), function(i)
    list(id = survived_rows$variant_id[i], executable_path = survived_rows$executable_path[i]))

  pool <- c(variants, survived, list(original_variant))
  pool <- pool[!duplicated(vapply(pool, function(v) v$id, ""))]

  # Configurations paired before this iteration keep their variant; the new
  # ones take the pool in turn.
  new_ids <- sort(setdiff(new_ids, old_map$config_id))
  turn <- rep_len(seq_along(pool), length(new_ids))
  new_rows <- data.frame(
    config_id = new_ids,
    executable_path = vapply(turn, function(i) pool[[i]]$executable_path, ""),
    variant_id = vapply(turn, function(i) pool[[i]]$id, ""),
    stringsAsFactors = FALSE)
  variant_map <- rbind(old_map[!(old_map$config_id %in% new_ids), , drop = FALSE], new_rows)
  variant_map <- variant_map[order(variant_map$config_id), , drop = FALSE]
  utils::write.csv(variant_map, variant_map_file, row.names = FALSE)

  evo_note("irace-evo: ", length(new_ids), " new configurations paired with ", length(pool),
             " code variants (", length(variants), " new, ", length(survived),
             " from the elites, and the original)\n")

  if (!is.null(scenario$batchmode) && scenario$batchmode == "slurm" && scenario$parallel > 1) {
    distribute_variants_slurm(pool, variant_map, scenario)
  }
  if (is.null(scenario$originalTargetRunner)) {
    scenario$originalTargetRunner <- scenario$targetRunner
  }
  scenario$targetRunnerData <- list(original_runner = scenario$originalTargetRunner,
                                    variant_map_file = variant_map_file,
                                    variants = pool)
  scenario$codeEvolutionVariantsReady <- TRUE
  scenario$codeEvolutionVariantMap <- variant_map
  scenario
}

#' Add variant information to configurations
#'
#' @param configurations Data frame with configurations
#' @param scenario irace scenario with variant mapping
#' @return Configurations data frame with .VARIANT. column added
add_variant_information <- function(configurations, scenario) {
  if (is.null(scenario) || !isTRUE(scenario$codeEvolution) || nrow(configurations) == 0) {
    return(configurations)
  }
  
  # Remove any existing .VARIANT. column to ensure fresh mapping
  if (".VARIANT." %in% colnames(configurations)) {
    configurations$.VARIANT. <- NULL
  }
  
  # Try to load variant mapping from CSV if not in scenario
  if (is.null(scenario$codeEvolutionVariantMap)) {
    csv_file <- file.path(scenario$execDir, ".irace_evo_variants.csv")
    if (file.exists(csv_file)) {
      tryCatch({
        variant_map <- utils::read.csv(csv_file, stringsAsFactors = FALSE)
        if (nrow(variant_map) > 0 && "config_id" %in% colnames(variant_map) && 
            "variant_id" %in% colnames(variant_map)) {
          scenario$codeEvolutionVariantMap <- variant_map
        }
      }, error = function(e) {
        return(configurations)  # Return unchanged if loading fails
      })
    }
    
    # If still no variant map, return unchanged
    if (is.null(scenario$codeEvolutionVariantMap)) {
      return(configurations)
    }
  }
  
  # Add variant column to configurations
  variant_map <- scenario$codeEvolutionVariantMap
  
  # Create a copy of configurations to modify
  configs_with_variants <- configurations
  
  # Add variant information based on config ID with name normalization
  configs_with_variants$.VARIANT. <- sapply(configurations$.ID., function(id) {
    idx <- which(variant_map$config_id == id)
    if (length(idx) > 0) {
      # Get raw variant_id from CSV
      raw_variant_id <- variant_map$variant_id[idx[1]]
      
      # Normalize variant names for consistent display
      if (raw_variant_id == "original") {
        return("original")
      } else {
        # Extract variant number and iteration from various formats
        # Handles: "variant_1_iter1", "algorithm_var_000_inno_iter1", etc.
        variant_match <- regexpr("variant_([0-9]+)_iter([0-9]+)|var_([0-9]+).*iter([0-9]+)", raw_variant_id, perl = TRUE)
        if (variant_match > 0) {
          # Extract matched groups
          matches <- regmatches(raw_variant_id, variant_match)
          # Try to extract numbers from the match
          numbers <- regmatches(matches, gregexpr("[0-9]+", matches))[[1]]
          if (length(numbers) >= 2) {
            variant_num <- as.numeric(numbers[1])
            iter_num <- numbers[2]
            # Keep consistent 0-based indexing for both binaries and source files
            return(paste0("variant_", variant_num, "_iter", iter_num))
          }
        }
        # Fallback: return original if parsing fails
        return(raw_variant_id)
      }
    } else {
      # Not paired: the target runner runs the original for it.
      return("original")
    }
  })
  
  # Reorder columns to put variant after .ID.
  col_names <- colnames(configs_with_variants)
  id_idx <- which(col_names == ".ID.")
  variant_idx <- which(col_names == ".VARIANT.")
  
  # Create new column order
  if (id_idx > 0 && variant_idx > 0) {
    other_cols <- setdiff(seq_along(col_names), c(id_idx, variant_idx))
    new_order <- c(id_idx, variant_idx, other_cols)
    configs_with_variants <- configs_with_variants[, new_order]
  }
  
  return(configs_with_variants)
}

#' Print configurations with variant information for code evolution
#'
#' @param configurations Data frame with configurations
#' @param scenario irace scenario
#' @param metadata Whether to print metadata
configurations_print_with_variants <- function(configurations, scenario = NULL, metadata = FALSE) {
  if (is.null(scenario) || !isTRUE(scenario$codeEvolution)) {
    # Fall back to regular printing if not in code evolution mode
    configurations_print(configurations, metadata = metadata)
    return()
  }
  
  # Add variant information using the helper function
  configs_with_variants <- add_variant_information(configurations, scenario)
  
  # Print the enhanced configurations
  configurations_print(configs_with_variants, metadata = metadata)
}

#' Print best configurations as command lines with variant information
#'
#' @param configurations Configurations data.frame
#' @param parameters Parameters object
#' @param scenario irace scenario
configurations_print_command_with_variants <- function(configurations, parameters, scenario = NULL) {
  if (is.null(scenario) || !isTRUE(scenario$codeEvolution) || 
      is.null(scenario$codeEvolutionVariantMap)) {
    # Fall back to regular printing if not in code evolution mode
    configurations_print_command(configurations, parameters)
    return()
  }
  
  if (nrow(configurations) <= 0L) return(invisible())
  
  # Use the same variant information logic as the printing function
  configs_with_variants <- add_variant_information(configurations, scenario)
  variants <- configs_with_variants$.VARIANT.
  ids <- configurations$.ID.
  
  # Remove metadata for command line generation
  configs_clean <- removeConfigurationsMetaData(configurations)
  configs_clean <- configs_clean[, parameters$names, drop = FALSE]
  
  # Calculate spacing for alignment
  len <- nchar(max(ids))
  variant_len <- max(nchar(variants))
  
  # Print each configuration with variant information
  for (i in seq_nrow(configs_clean)) {
    cat(sprintf("%-*d %-*s %s\n", 
                len, ids[i],
                variant_len, variants[i],
                buildCommandLine(configs_clean[i, , drop=FALSE], parameters$switches)))
  }
}

#' Distribute code variants for SLURM execution
#'
#' @param variants List of generated code variants
#' @param variant_map Data frame with variant mapping
#' @param scenario irace scenario
distribute_variants_slurm <- function(variants, variant_map, scenario) {
  
  evo_note("irace-evo: Distributing variants for SLURM execution")
  
  # Create SLURM-specific directories and files
  slurm_dir <- file.path(scenario$execDir, ".irace_evo_slurm")
  dir.create(slurm_dir, showWarnings = FALSE, recursive = TRUE)
  
  # Copy executables to shared location
  variant_bin_dir <- file.path(slurm_dir, "bin")
  dir.create(variant_bin_dir, showWarnings = FALSE, recursive = TRUE)
  
  for (i in seq_along(variants)) {
    variant <- variants[[i]]
    if (!is.null(variant$executable_path) && file.exists(variant$executable_path)) {
      
      # Create unique executable name for SLURM
      exec_name <- paste0("variant_", i)
      slurm_exec_path <- file.path(variant_bin_dir, exec_name)
      
      # Copy executable
      file.copy(variant$executable_path, slurm_exec_path, overwrite = TRUE)
      
      # Make executable
      Sys.chmod(slurm_exec_path, mode = "0755")
      
      # Every configuration paired with this variant runs the copy
      variant_map$executable_path[variant_map$variant_id == variant$id] <- slurm_exec_path
      
      evo_note("irace-evo: Copied variant ", i, " to ", slurm_exec_path)
    }
  }
  
  # Save updated mapping
  slurm_variant_map_file <- file.path(slurm_dir, ".irace_evo_variants.csv")
  utils::write.csv(variant_map, slurm_variant_map_file, row.names = FALSE)
  
  # Create distribution script for SLURM nodes
  create_slurm_distribution_script(slurm_dir, scenario)
  
  # Update main mapping to point to SLURM location
  main_variant_map_file <- file.path(scenario$execDir, ".irace_evo_variants.csv")
  utils::write.csv(variant_map, main_variant_map_file, row.names = FALSE)
}

#' Create distribution script for SLURM nodes
#'
#' @param slurm_dir SLURM directory path
#' @param scenario irace scenario
create_slurm_distribution_script <- function(slurm_dir, scenario) {
  
  script_path <- file.path(slurm_dir, "distribute_variants.sh")
  
  script_content <- paste0('#!/bin/bash
# irace-evo SLURM distribution script
# This script ensures variants are available on all SLURM nodes

SLURM_DIR="', slurm_dir, '"
EXEC_DIR="', scenario$execDir, '"
NODE_LOCAL_DIR="${SLURM_TMPDIR:-/tmp}/irace_evo_$$"

# Function to setup on worker node
setup_node() {
    echo "irace-evo: Setting up node $SLURMD_NODENAME"
    
    # Create local directory
    mkdir -p "$NODE_LOCAL_DIR"
    
    # Copy variant files to node-local storage
    if [ -d "$SLURM_DIR/bin" ]; then
        cp -r "$SLURM_DIR/bin" "$NODE_LOCAL_DIR/"
        chmod +x "$NODE_LOCAL_DIR/bin/"*
    fi
    
    # Copy variant mapping
    if [ -f "$SLURM_DIR/.irace_evo_variants.csv" ]; then
        cp "$SLURM_DIR/.irace_evo_variants.csv" "$NODE_LOCAL_DIR/"
        
        # Update paths in mapping to use node-local paths
        sed "s|', slurm_dir, '/bin/|$NODE_LOCAL_DIR/bin/|g" \\
            "$NODE_LOCAL_DIR/.irace_evo_variants.csv" > \\
            "$EXEC_DIR/.irace_evo_variants.csv"
    fi
    
    echo "irace-evo: Node setup complete on $SLURMD_NODENAME"
}

# Setup this node
setup_node

# Cleanup function
cleanup_node() {
    echo "irace-evo: Cleaning up node $SLURMD_NODENAME"
    rm -rf "$NODE_LOCAL_DIR"
}

# Register cleanup
trap cleanup_node EXIT
')
  
  writeLines(script_content, script_path)
  Sys.chmod(script_path, mode = "0755")
  
  evo_note("irace-evo: Created SLURM distribution script: ", script_path)
}

#' Check if code evolution is enabled and properly configured
#'
#' @param scenario irace scenario
#' @return TRUE if code evolution is enabled and valid
is_code_evolution_enabled <- function(scenario) {
  return(isTRUE(scenario$codeEvolution) && 
         !is.null.or.empty(scenario$codeEvolutionConfig) &&
         scenario$codeEvolutionVariants > 0)
}

#' Setup signal handler to clean up processes on interrupt
#'
#' @param scenario irace scenario
setup_code_evolution_signal_handler <- function(scenario) {
  # Store the scenario in the global environment for the signal handler
  assign(".irace_evo_scenario", scenario, envir = .GlobalEnv)
  
  # Setup signal handler for SIGINT (Ctrl+C)
  original_handler <- getOption("interrupt")
  
  interrupt_handler <- function() {
    tryCatch({
      scenario <- get(".irace_evo_scenario", envir = .GlobalEnv, inherits = FALSE)
      evo_note("irace-evo: Interrupt detected, cleaning up processes...")
      kill_orphaned_processes(scenario)
    }, error = function(e) {
      message("Error during interrupt cleanup: ", e$message)
    })
    
    # Call original handler or stop
    if (!is.null(original_handler)) {
      original_handler()
    } else {
      stop("Interrupted by user", call. = FALSE)
    }
  }
  
  # Set the interrupt handler
  options(interrupt = interrupt_handler)
  
  evo_note("irace-evo: Signal handler setup for process cleanup")
}

#' Validate generated variants for obvious issues
#'
#' @param variants List of generated variants
#' @param scenario irace scenario
#' @return Filtered list of variants
validate_variants <- function(variants, scenario) {
  if (is.null(variants) || length(variants) == 0) return(variants)
  # The test described by validation_config in the configuration file: run
  # the variant with test_arguments, within test_timeout seconds, and match
  # its output against expected_output_pattern. Without test_arguments (or
  # with basic_functionality_test = false), compiling is the validation.
  test <- jsonlite::fromJSON(scenario$codeEvolutionConfig)$validation_config
  if (is.null(test) || isFALSE(test$basic_functionality_test) || !length(test$test_arguments)) {
    return(variants)
  }
  timeout <- if (is.null(test$test_timeout)) 30 else test$test_timeout
  valid <- list()
  for (variant in variants) {
    output <- withr::with_dir(scenario$execDir, suppressWarnings(tryCatch(
      system2(variant$executable_path, args = shQuote(test$test_arguments),
              stdout = TRUE, stderr = FALSE, timeout = timeout),
      error = function(e) structure(character(0), status = 1L))))
    status <- attr(output, "status")
    ok <- is.null(status) || identical(as.integer(status), 0L)
    if (ok && !is.null(test$expected_output_pattern)) {
      ok <- any(grepl(test$expected_output_pattern, trimws(output), perl = TRUE))
    }
    if (ok) {
      valid[[length(valid) + 1L]] <- variant
    } else {
      evo_note("irace-evo: Discarding ", variant$id, ": it failed the validation test (exit status ",
                 if (is.null(status)) 0L else status, ", output '", paste(utils::head(output, 2), collapse = " "), "')\n")
    }
  }
  evo_note("irace-evo: ", length(valid), " of ", length(variants), " variants passed the validation test\n")
  valid
}

#' Kill orphaned variant processes that may be still running
#'
#' @param scenario irace scenario
kill_orphaned_processes <- function(scenario) {
  tryCatch({
    # Look for processes that contain our algorithm executable names
    bin_dir <- file.path(scenario$execDir, "bin")
    
    # Get original executable name from config
    config_data <- jsonlite::fromJSON(scenario$codeEvolutionConfig)
    source_file <- config_data$source_config$source_file
    base_name <- tools::file_path_sans_ext(basename(source_file))
    
    # Kill processes running variant executables
    variant_patterns <- c("algorithm_var_", "algorithm_fallback_", base_name)
    
    for (pattern in variant_patterns) {
      # Find processes matching the pattern
      cmd <- paste0("pkill -f '", file.path(bin_dir, pattern), "' 2>/dev/null || true")
      system(cmd, ignore.stdout = TRUE, ignore.stderr = TRUE)
    }
    
    # Also kill any processes that might be running in the execDir context
    exec_dir <- normalizePath(scenario$execDir, mustWork = FALSE)
    if (dir.exists(exec_dir)) {
      # Kill processes that have the execDir in their command line
      cmd <- paste0("pkill -f '", exec_dir, ".*algorithm' 2>/dev/null || true")
      system(cmd, ignore.stdout = TRUE, ignore.stderr = TRUE)
    }
    
    # Give processes time to terminate gracefully
    Sys.sleep(0.5)
    
    # Force kill if still running (SIGKILL)
    for (pattern in variant_patterns) {
      cmd <- paste0("pkill -9 -f '", file.path(bin_dir, pattern), "' 2>/dev/null || true")
      system(cmd, ignore.stdout = TRUE, ignore.stderr = TRUE)
    }
    
    evo_note("irace-evo: Killed orphaned variant processes")
    
  }, error = function(e) {
    evo_note("irace-evo: Warning: Could not kill orphaned processes: ", e$message)
  })
}

#' Clean up files from previous irace-evo execution
#'
#' @param scenario irace scenario
cleanup_previous_execution <- function(scenario) {
  
  evo_note("irace-evo: Cleaning up files from previous execution...")
  
  # Load configuration to get correct executable and source names
  config_data <- jsonlite::fromJSON(scenario$codeEvolutionConfig)
  source_file <- config_data$source_config$source_file
  base_name <- tools::file_path_sans_ext(basename(source_file))
  
  # Only clean up on the very first run (when starting fresh)
  # This is determined by checking if we're in iteration 1 and no variants exist yet
  variant_map_file <- file.path(scenario$execDir, ".irace_evo_variants.csv")
  
  # Check if this is a fresh start (no active variants)
  is_fresh_start <- !file.exists(variant_map_file) || file.size(variant_map_file) == 0
  
  if (is_fresh_start) {
    # Remove variant mapping file (should be empty or non-existent anyway)
    if (file.exists(variant_map_file)) {
      file.remove(variant_map_file)
      evo_note("irace-evo: Removed previous variant mapping file")
    }
    
    # Remove previous source code files
    source_log_dir <- file.path(scenario$execDir, "irace-evo-sources")
    if (dir.exists(source_log_dir)) {
      unlink(source_log_dir, recursive = TRUE)
      evo_note("irace-evo: Removed previous source code directory")
    }
    
    # Remove previous LLM logs
    llm_log_dir <- file.path(scenario$execDir, "irace-evo-llm-logs")
    if (dir.exists(llm_log_dir)) {
      unlink(llm_log_dir, recursive = TRUE)
      evo_note("irace-evo: Removed previous LLM logs directory")
    }
    
    # Remove previous variant executables (but keep the original algorithm)
    bin_dir <- file.path(scenario$execDir, "bin")
    if (dir.exists(bin_dir)) {
      # Remove ALL variant binaries including different naming patterns
      variant_patterns <- c(
        "^algorithm_var_.*",      # Standard variant naming
        "^algorithm_fallback_.*", # Fallback variants
        paste0("^", base_name, "_var.*"),  # Alternative naming based on actual executable
        "^variant_.*",           # Simple variant naming
        ".*_variant.*"           # Any file with "variant" in name
      )
      
      all_variant_files <- c()
      for (pattern in variant_patterns) {
        variant_files <- list.files(bin_dir, pattern = pattern, full.names = TRUE)
        all_variant_files <- c(all_variant_files, variant_files)
      }
      
      # Remove duplicates and exclude original algorithm
      all_variant_files <- unique(all_variant_files)
      original_algorithm <- file.path(bin_dir, base_name)
      all_variant_files <- all_variant_files[all_variant_files != original_algorithm]
      
      if (length(all_variant_files) > 0) {
        file.remove(all_variant_files)
        evo_note("irace-evo: Removed ", length(all_variant_files), " previous variant executables")
      }
    }
  } else {
    evo_note("irace-evo: Skipping cleanup - active variants in use")
  }
  
  # Clean up any remaining temporary files from previous runs
  exec_dir <- scenario$execDir
  temp_patterns <- c("*.stdout", "*.stderr", "c[0-9]*-[0-9]*-[0-9]*.stdout", "c[0-9]*-[0-9]*-[0-9]*.stderr")
  
  for (pattern in temp_patterns) {
    temp_files <- list.files(exec_dir, pattern = utils::glob2rx(pattern), full.names = TRUE)
    if (length(temp_files) > 0) {
      file.remove(temp_files)
      evo_note("irace-evo: Removed ", length(temp_files), " temporary output files")
    }
  }
  
  # Remove any duplicate source files that might exist in the main directory
  source_patterns <- c("variant_*.cpp", "algorithm_var_*.cpp", "*.cpp.bak")
  for (pattern in source_patterns) {
    source_files <- list.files(exec_dir, pattern = utils::glob2rx(pattern), full.names = TRUE)
    # Exclude the original source file
    original_source <- file.path(exec_dir, dirname(source_file), basename(source_file))
    source_files <- source_files[source_files != original_source]
    
    if (length(source_files) > 0) {
      file.remove(source_files)
      evo_note("irace-evo: Removed ", length(source_files), " duplicate source files")
    }
  }
  
  # Kill any remaining variant processes
  kill_orphaned_processes(scenario)
  
  # Remove CSV mapping file from previous runs
  variant_csv_file <- file.path(exec_dir, ".irace_evo_variants.csv")
  if (file.exists(variant_csv_file)) {
    file.remove(variant_csv_file)
    evo_note("irace-evo: Removed previous variant mapping file")
  }
  
  # Reset scenario flags
  scenario$codeEvolutionVariantsReady <- NULL
  scenario$originalTargetRunner <- NULL
  scenario$targetRunnerData <- NULL
  
  evo_note("irace-evo: Complete cleanup finished - ready for fresh start")
}

#' Remove the files a previous irace-evo run left in a directory
#'
#' Deletes the variant map, the generated sources and LLM logs, and the
#' variant programs in `bin/` (the original program is kept).
#'
#' @param exec_dir Execution directory (default: current directory)
#' @param config Code-evolution configuration file (default:
#'   `code-evolution.json` in `exec_dir`)
#' @keywords internal
clean_irace_evo_files <- function(exec_dir = ".", config = file.path(exec_dir, "code-evolution.json")) {
  if (!file.exists(config)) {
    stop("Configuration file not found: ", config, ". Pass it as 'config'.")
  }
  cleanup_previous_execution(list(execDir = exec_dir, codeEvolutionConfig = config))
  invisible(TRUE)
}

#' Show the best heuristic code from elite configurations
#'
#' @param elite_configurations Elite configurations from current iteration
#' @param scenario irace scenario
show_best_heuristic <- function(elite_configurations, scenario) {
  if (!isTRUE(scenario$codeEvolution) || nrow(elite_configurations) == 0) return(invisible())
  tryCatch({
    best_variant <- add_variant_information(elite_configurations[1, , drop = FALSE], scenario)$.VARIANT.[1]
    if (is.null(best_variant) || best_variant == "original") {
      evo_note("Current best: the original code\n")
      return(invisible())
    }
    source_file <- file.path(scenario$execDir, "irace-evo-sources",
                             paste0(best_variant, source_extension(scenario)))
    if (!file.exists(source_file)) return(invisible())
    lines <- extract_function_from_code(readLines(source_file, warn = FALSE),
                                        get_function_name_from_config(scenario))
    if (is.null(lines)) return(invisible())
    evo_note("=== CURRENT BEST FUNCTION (", best_variant, ") ===\n")
    cat(lines, sep = "\n")
    cat("=== END ===\n")
  }, error = function(e) invisible())
}

#' Main entry point for code evolution in irace
#'
#' Called from the main irace racing loop when code evolution is enabled
#'
#' @param elite_configs Elite configurations from current iteration
#' @param iteration_stats Current iteration statistics
#' @param scenario irace scenario
#' @param budget_info Optional list with budget information (remaining, current) to avoid wasteful LLM calls
#' @return Updated scenario with new code variants
evolve_code_iteration <- function(elite_configs, iteration_stats, scenario,
                                  elite_ids = integer(0), new_ids = integer(0)) {
  
  if (!is_code_evolution_enabled(scenario)) {
    return(scenario)  # Return unchanged scenario
  }
  # Every iteration generates variants (paper, Algorithm 1, line 5 and
  # Sect. 4.1); an earlier rule that skipped the LLM when the remaining
  # budget looked small is gone.
  
  # Clean up previous execution files on first iteration
  if (iteration_stats$iteration == 1) {
    cleanup_previous_execution(scenario)
    setup_code_evolution_signal_handler(scenario)
    
    # Initialize global LLM metrics tracking
    scenario$codeEvolutionGlobalMetrics <- list(
      total_calls = 0,
      total_retries = 0,
      total_input_tokens = 0,
      total_output_tokens = 0,
      total_cost_estimate = 0,
      total_llm_time = 0,  # Accumulated actual LLM processing time
      iterations = list(),
      start_time = Sys.time(),
      # Configuration will be set on first LLM call
      api_provider = NULL,
      model = NULL,
      temperature = NULL,
      max_tokens = NULL
    )
  }
  
  evo_note("irace-evo: Generating ", scenario$codeEvolutionVariants, 
             " code variants for iteration ", iteration_stats$iteration)
  
  # Generate new code variants
  variants_result <- generate_code_variants(elite_configs, iteration_stats, scenario)
  variants <- variants_result$variants
  llm_metrics <- variants_result$metrics
  
  # Validate generated variants for obvious issues
  variants <- validate_variants(variants, scenario)
  
  # Accumulate global LLM metrics
  if (!is.null(scenario$codeEvolutionGlobalMetrics)) {
    scenario$codeEvolutionGlobalMetrics$total_calls <- scenario$codeEvolutionGlobalMetrics$total_calls + llm_metrics$total_calls
    scenario$codeEvolutionGlobalMetrics$total_retries <- scenario$codeEvolutionGlobalMetrics$total_retries + llm_metrics$total_retries
    scenario$codeEvolutionGlobalMetrics$total_input_tokens <- scenario$codeEvolutionGlobalMetrics$total_input_tokens + llm_metrics$total_input_tokens
    scenario$codeEvolutionGlobalMetrics$total_output_tokens <- scenario$codeEvolutionGlobalMetrics$total_output_tokens + llm_metrics$total_output_tokens
    scenario$codeEvolutionGlobalMetrics$total_cost_estimate <- scenario$codeEvolutionGlobalMetrics$total_cost_estimate + llm_metrics$total_cost_estimate
    # Accumulate actual LLM processing time
    if (!is.null(llm_metrics$llm_processing_time)) {
      scenario$codeEvolutionGlobalMetrics$total_llm_time <- scenario$codeEvolutionGlobalMetrics$total_llm_time + llm_metrics$llm_processing_time
    }
    
    # Store LLM configuration on first iteration
    if (is.null(scenario$codeEvolutionGlobalMetrics$api_provider)) {
      scenario$codeEvolutionGlobalMetrics$api_provider <- llm_metrics$api_provider
      scenario$codeEvolutionGlobalMetrics$model <- llm_metrics$model
      scenario$codeEvolutionGlobalMetrics$temperature <- llm_metrics$temperature
      scenario$codeEvolutionGlobalMetrics$max_tokens <- llm_metrics$max_tokens
    }
    # Fields the model refused so far (e.g. temperature), so the summary
    # does not report a value that was never applied.
    scenario$codeEvolutionGlobalMetrics$refused_fields <-
      union(scenario$codeEvolutionGlobalMetrics$refused_fields, unlist(llm_metrics$refused_fields))
    
    # Store iteration-specific metrics
    iteration_metrics <- list(
      iteration = iteration_stats$iteration,
      calls = llm_metrics$total_calls,
      retries = llm_metrics$total_retries,
      input_tokens = llm_metrics$total_input_tokens,
      output_tokens = llm_metrics$total_output_tokens,
      cost_estimate = llm_metrics$total_cost_estimate,
      variants_generated = length(variants),
      llm_time = if (!is.null(llm_metrics$llm_processing_time)) llm_metrics$llm_processing_time else 0
    )
    scenario$codeEvolutionGlobalMetrics$iterations[[length(scenario$codeEvolutionGlobalMetrics$iterations) + 1]] <- iteration_metrics
    
    # Persist metrics to file for recovery in case scenario object is lost
    tryCatch({
      saveRDS(scenario$codeEvolutionGlobalMetrics, file.path(scenario$execDir, ".irace_evo_metrics.rds"))
    }, error = function(e) {
      # Silent fail - metrics persistence is nice-to-have
    })
  }
  
  # Display metrics in irace console output
  evo_note("irace-evo: Successfully generated ", length(variants), " variants")
  evo_note("LLM Usage - Calls: ", llm_metrics$total_calls, 
             ", Retries: ", llm_metrics$total_retries,
             ", Tokens: ", llm_metrics$total_input_tokens, "+", llm_metrics$total_output_tokens,
             ", Est.Cost: $", sprintf("%.3f", llm_metrics$total_cost_estimate))
  
  # Update scenario to use variants
  scenario <- setup_variant_target_runner(variants, scenario, elite_ids = elite_ids, new_ids = new_ids)
  
  return(scenario)
}

#' Print LLM metrics summary table
#'
#' @param scenario irace scenario with global LLM metrics
print_llm_metrics_summary <- function(scenario) {
  if (is.null(scenario$codeEvolutionGlobalMetrics) || 
      scenario$codeEvolutionGlobalMetrics$total_calls == 0) {
    return()
  }
  
  metrics <- scenario$codeEvolutionGlobalMetrics
  
  # Use accumulated LLM processing time instead of total execution time
  total_llm_time <- if (!is.null(metrics$total_llm_time)) {
    metrics$total_llm_time
  } else {
    NA
  }
  
  cat("\n")
  cat("# LLM Code Evolution Summary\n")
  cat("# ===================================================================\n")
  
  # LLM Configuration
  cat("# LLM Configuration:\n")
  if (!is.null(metrics$api_provider)) {
    cat(sprintf("#   API Provider:             %s\n", metrics$api_provider))
  }
  if (!is.null(metrics$model)) {
    cat(sprintf("#   Model:                    %s\n", metrics$model))
  }
  refused <- metrics$refused_fields
  if (!is.null(metrics$temperature)) {
    cat(sprintf("#   Temperature:              %s\n",
                if ("temperature" %in% refused) "not accepted by the model, not applied"
                else sprintf("%.1f", metrics$temperature)))
  }
  if (length(refused)) {
    cat(sprintf("#   Refused by the model:     %s\n", paste(refused, collapse = ", ")))
  }
  if (!is.null(metrics$max_tokens)) {
    cat(sprintf("#   Max Tokens:               %d\n", metrics$max_tokens))
  }
  cat("#\n")
  
  # Overall metrics
  cat("# Overall Metrics:\n")
  cat(sprintf("#   Total LLM API Calls:      %d\n", metrics$total_calls))
  cat(sprintf("#   Total Retry Attempts:     %d\n", metrics$total_retries))
  cat(sprintf("#   Input Tokens Used:        %s\n", format(metrics$total_input_tokens, big.mark=",")))
  cat(sprintf("#   Output Tokens Used:       %s\n", format(metrics$total_output_tokens, big.mark=",")))
  cat(sprintf("#   Total Tokens:             %s\n", format(metrics$total_input_tokens + metrics$total_output_tokens, big.mark=",")))
  if (!is.na(total_llm_time)) {
    cat(sprintf("#   Total LLM Processing Time: %.1f seconds\n", total_llm_time))
  }
  
  # Per-iteration breakdown
  if (length(metrics$iterations) > 0) {
    cat("#\n")
    cat("# Per-Iteration Breakdown:\n")
    cat(sprintf("# %8s %8s %8s %12s %12s %8s %8s\n", 
                "Iter", "Calls", "Retries", "Input", "Output", "Variants", "Time(s)"))
    cat("# ---------------------------------------------------------------------\n")
    
    for (iter_metrics in metrics$iterations) {
      llm_time_str <- if (!is.null(iter_metrics$llm_time)) sprintf("%.1f", iter_metrics$llm_time) else "N/A"
      cat(sprintf("# %8d %8d %8d %12s %12s %8d %8s\n",
                  iter_metrics$iteration,
                  iter_metrics$calls,
                  iter_metrics$retries,
                  format(iter_metrics$input_tokens, big.mark=","),
                  format(iter_metrics$output_tokens, big.mark=","),
                  iter_metrics$variants_generated,
                  llm_time_str))
    }
  }
  
  cat("# ===================================================================\n")
  cat("\n")
}

#' Update performance history with racing results for dynamic prompting
#'
#' @param elite_configurations Elite configurations data frame with racing results
#' @param scenario irace scenario
update_performance_history <- function(elite_configurations, scenario) {
  if (!isTRUE(scenario$codeEvolution) || nrow(elite_configurations) == 0) {
    return()
  }
  
  tryCatch({
    # Load existing history
    history_file <- file.path(scenario$execDir, ".irace_evo_history.json")
    
    if (file.exists(history_file)) {
      
      # More robust JSON reading
      history_raw <- tryCatch({
        paste(readLines(history_file, warn = FALSE), collapse = "\n")
      }, error = function(e) {
        return(NULL)
      })
      
      if (!is.null(history_raw) && nzchar(history_raw)) {
        history <- tryCatch({
          # Force to return a list, not a data frame
          jsonlite::fromJSON(history_raw, simplifyDataFrame = FALSE)
        }, error = function(e) {
          return(list())
        })
        
        if (length(history) > 0) {
          # Update the last entry with racing results
          last_entry <- history[[length(history)]]
          
          # Add performance information from racing results
          best_rank <- min(elite_configurations$.RANK.)
          
          # Create updated entry as a proper list
          updated_entry <- as.list(last_entry)
          updated_entry$best_performance <- best_rank
          updated_entry$best_configuration_id <- elite_configurations$.ID.[1]
          updated_entry$winning_strategy <- if (!is.null(elite_configurations$.VARIANT.[1])) {
            if (elite_configurations$.VARIANT.[1] != "original") elite_configurations$.VARIANT.[1] else "original"
          } else "original"
          
          # Update the entry in history  
          history[[length(history)]] <- updated_entry
          
          # Save updated history
          updated_json <- jsonlite::toJSON(history, auto_unbox = TRUE, pretty = TRUE)
          writeLines(updated_json, history_file)
          
          message("irace-evo: racing results added to the history (best: ", best_rank, ", winner: ", updated_entry$winning_strategy, ")")
        }
      }
    }
  }, error = function(e) {
    # Use message instead of irace_warning to avoid dependency issues
    message("irace-evo WARNING: Failed to update performance history: ", e$message)
  })
}

#' Print winning variant function comparison
#'
#' @param elite_configurations Elite configurations data frame
#' @param scenario irace scenario
print_winning_variant_function <- function(elite_configurations, scenario) {
  if (!isTRUE(scenario$codeEvolution) || nrow(elite_configurations) == 0) {
    return()
  }
  
  # Update performance history with racing results for dynamic prompting
  update_performance_history(elite_configurations, scenario)
  
  # Get the best configuration (first row)
  best_config <- elite_configurations[1, ]
  
  # Check if best configuration is a variant (not original)
  if (is.null(best_config$.VARIANT.) || best_config$.VARIANT. == "original") {
    return()  # Don't show if winner is original
  }
  
  winning_variant <- best_config$.VARIANT.
  
  cat("\n")
  cat("# Winning Variant Function Analysis\n")
  cat("# ===================================================================\n")
  cat(sprintf("# Winner: %s (Configuration ID: %d)\n", winning_variant, best_config$.ID.))
  performance_text <- if (!is.null(best_config$.RANK.) && !is.na(best_config$.RANK.)) {
    sprintf("%.1f", as.numeric(best_config$.RANK.))
  } else {
    "N/A"
  }
  cat(sprintf("# Performance: Rank %s\n", performance_text))
  cat("#\n")
  
  # Find the winning function and the original one
  source_file <- file.path(scenario$execDir, "irace-evo-sources",
                           paste0(winning_variant, source_extension(scenario)))
  original_file <- original_source_file(scenario)
  
  if (file.exists(source_file) && file.exists(original_file)) {
    # Read the winning variant source
    tryCatch({
      variant_code <- readLines(source_file)
      original_code <- readLines(original_file)
      
      # Extract function from variant
      function_name <- get_function_name_from_config(scenario)
      variant_function <- extract_function_from_code(variant_code, function_name)
      original_function <- extract_function_from_code(original_code, function_name)
      
      if (!is.null(variant_function) && !is.null(original_function)) {
        cat("# WINNING VARIANT FUNCTION:\n")
        cat("# -------------------------------------------------------------------\n")
        for (line in variant_function) {
          cat("#", line, "\n")
        }
        cat("#\n")
        
        cat("# ORIGINAL FUNCTION (for comparison):\n") 
        cat("# -------------------------------------------------------------------\n")
        for (line in original_function) {
          cat("#", line, "\n")
        }
        cat("#\n")
      } else {
        cat("# Could not extract function code for comparison\n")
      }
    }, error = function(e) {
      cat("# Error reading source files for function comparison\n")
    })
  } else {
    cat("# Source files not available for function comparison\n")
    if (!file.exists(source_file)) {
      cat(sprintf("# Missing: %s\n", source_file))
    }
    if (!file.exists(original_file)) {
      cat(sprintf("# Missing: %s\n", original_file))
    }
  }
  
  cat("# ===================================================================\n")
  cat("\n")
}

#' Extract function from source code lines
#'
#' @param code_lines Vector of code lines
#' @param function_name Name of function to extract
#' @return Vector of function lines or NULL if not found
extract_function_from_code <- function(code_lines, function_name) {
  tryCatch({
    # Look for function signature
    func_pattern <- paste0("\\b", function_name, "\\s*\\(")
    func_line <- -1
    
    for (i in seq_along(code_lines)) {
      if (grepl(func_pattern, code_lines[i])) {
        func_line <- i
        break
      }
    }
    
    if (func_line == -1) {
      return(NULL)
    }
    
    # Find opening brace
    brace_line <- func_line
    while (brace_line <= length(code_lines) && !grepl("\\{", code_lines[brace_line])) {
      brace_line <- brace_line + 1
    }
    
    if (brace_line > length(code_lines)) {
      return(NULL)
    }
    
    # Count braces to find function end
    brace_count <- 0
    start_line <- func_line
    end_line <- length(code_lines)
    
    for (i in brace_line:length(code_lines)) {
      line <- code_lines[i]
      # Count opening braces
      brace_count <- brace_count + lengths(regmatches(line, gregexpr("\\{", line)))
      # Count closing braces  
      brace_count <- brace_count - lengths(regmatches(line, gregexpr("\\}", line)))
      
      if (brace_count == 0) {
        end_line <- i
        break
      }
    }
    
    # Return function lines
    if (end_line >= start_line) {
      return(code_lines[start_line:end_line])
    } else {
      return(NULL)
    }
  }, error = function(e) {
    return(NULL)
  })
}

#' File extension of the language being evolved
#' @param scenario irace scenario
source_extension <- function(scenario) {
  language <- tryCatch(jsonlite::fromJSON(scenario$codeEvolutionConfig)$language_config$language,
                       error = function(e) NULL)
  switch(tolower(if (is.null(language)) "cpp" else language),
         python = , py = ".py", java = ".java", ".cpp")
}

#' Get function name from configuration
#'
#' @param scenario irace scenario
#' @return The name of the function the LLM may change
get_function_name_from_config <- function(scenario) {
  jsonlite::fromJSON(scenario$codeEvolutionConfig)$source_config$function_name
}

#' Path of the original source file, as given in the configuration
#'
#' @param scenario irace scenario
original_source_file <- function(scenario) {
  path <- jsonlite::fromJSON(scenario$codeEvolutionConfig)$source_config$source_file
  if (fs::is_absolute_path(path)) path else file.path(scenario$execDir, path)
}
