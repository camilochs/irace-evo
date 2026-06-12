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
    # --- BEGIN: enhanced debugging block ---
  message("irace-evo: Searching for a valid Python interpreter...")

  # Force the Python configuration
  python_env_path <- Sys.getenv("RETICULATE_PYTHON")
  
  if (nzchar(python_env_path)) {
   message(paste("irace-evo: Found the RETICULATE_PYTHON environment variable. Trying to use:", python_env_path))
   if (file.exists(python_env_path)) {
    reticulate::use_python(python_env_path, required = TRUE)
   } else {
    message(paste("irace-evo: WARNING: The RETICULATE_PYTHON path does not exist:", python_env_path))
   }
  } else {
   message("irace-evo: RETICULATE_PYTHON is not set. Searching common paths...")
   python_paths <- c("/usr/bin/python3", "/usr/local/bin/python3", "/usr/bin/python")
   found <- FALSE
   for (py_path in python_paths) {
    message(paste("irace-evo: -> Comprobando si existe:", py_path))
    if (file.exists(py_path)) {
     message(paste("irace-evo:    ¡Encontrado! Intentando usar:", py_path))
     reticulate::use_python(py_path, required = TRUE)
     found <- TRUE
     break
    }
   }
   if (!found) message("irace-evo: No Python executable found in common paths.")
  }
  
  # --- PASO DE DIAGNÓSTICO MÁS IMPORTANTE ---
  # Print the configuration reticulate detected after the setup attempt.
  message("irace-evo: >>> reticulate configuration state BEFORE the final check:")
  py_config_output <- utils::capture.output(try(reticulate::py_config(), silent = TRUE))
  message(paste(py_config_output, collapse = "\n"))
  message("irace-evo: <<< End of configuration state.")
  
  # Final Python availability check
  message("irace-evo: Comprobando disponibilidad final con reticulate::py_available()...")
  if (!reticulate::py_available()) {
   message("irace-evo: ERROR: reticulate::py_available() ha devuelto FALSE.")
   irace_error("Python is not available. Code evolution requires Python 3.7+ bla bla")
  } else {
      message("irace-evo: ÉXITO: reticulate::py_available() ha devuelto TRUE.")
    }
    # --- END: debugging block ---
    
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
      }, error = function(e) FALSE)
      
      if (!result) {
        irace_error("Failed to import required Python module: ", module, 
                   ". Check Python dependencies in inst/python/")
      }
    }
    
    .irace_evo_env$python_initialized <- TRUE
    irace_note("irace-evo: Python backend initialized successfully")
    return(TRUE)
    
  }, error = function(e) {
    irace_error("Failed to initialize Python backend for code evolution. ",
               "Error2: ", e$message, 
               ". Ensure Python 3.7+ is available and required modules are installed.")
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
    irace_note("irace-evo: Worker node detected, skipping Python initialization")
    .irace_evo_env$python_initialized <- TRUE
    return(TRUE)
  }
  
  irace_note("irace-evo: Initializing Python backend on SLURM master node")
  
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
    irace_note("irace-evo: SLURM master node Python backend initialized successfully")
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
      irace_note("irace-evo: OpenAI API key configured from config file")
    } else if (api_provider == "anthropic") {
      # Set Anthropic API key as environment variable  
      Sys.setenv(ANTHROPIC_API_KEY = config_data$llm_config$api_key)
      irace_note("irace-evo: Anthropic API key configured from config file")
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
    irace_note("irace-evo: OpenAI API key detected")
  }
  
  if (anthropic_key != "") {
    irace_note("irace-evo: Anthropic API key detected")
  }
}

#' Generate code variants using LLM
#'
#' @param elite_configs List of elite configurations from current iteration
#' @param iteration_stats Statistics from current iteration
#' @param scenario irace scenario with code evolution settings
#' @return List of generated code variants with their executables
generate_code_variants <- function(elite_configs, iteration_stats, scenario, num_variants = NULL) {
  
  # LOG: function entry point
  message("LOG: Entering generate_code_variants() for iteration ", iteration_stats$iteration)
  
  # Load code evolution configuration FIRST to get API keys
  config_data <- jsonlite::fromJSON(scenario$codeEvolutionConfig)
  
  # Configure API keys from config file BEFORE Python initialization
  setup_llm_credentials(config_data)
  
  if (!initialize_python_backend(scenario)) {
    irace_error("Cannot initialize Python backend for code evolution")
  }
  
# Extraemos los rangos directamente de la columna .RANK. del data.frame.
# A lower rank is better, so it acts as a "cost".
costs <- elite_configs$.RANK.

# Compute the statistics
best_cost_so_far <- min(costs)
average_cost <- mean(costs)

message("LOG: Performance statistics computed using the .RANK column.")

# Prepare enhanced context for LLM with ranking information
context <- list(
  iteration_context = list(
    current_iteration = iteration_stats$iteration,
    max_iterations = 4,  # Reasonable estimate based on typical irace runs
    elite_configurations = elite_configs
  ),
  performance_stats = list(
    best_cost_so_far = best_cost_so_far,
    average_cost = average_cost,
    worst_cost = max(costs),
    performance_range = max(costs) - min(costs),
    convergence_trend = if (iteration_stats$iteration > 1) "improving" else "initial",
    elite_rankings = elite_configs$.RANK.,
    num_configurations_tested = nrow(elite_configs)
  ),
  improvement_guidance = list(
    needs_aggressive_changes = (best_cost_so_far > average_cost * 0.8), # If best is close to average, need bigger changes
    performance_gap = average_cost - best_cost_so_far,
    ranking_pressure = best_cost_so_far / max(costs) # How much room for improvement
  ),
  target_variants = if (!is.null(num_variants)) num_variants else scenario$codeEvolutionVariants,
  # Add scenario config for dynamic prompting
  scenario_config = list(
    execDir = scenario$execDir
  ),
  elite_configurations = elite_configs  # For dynamic prompting performance analysis
)

message("LOG: 'context' object created successfully.")
  
  # Context structure validated
  
  # Call Python backend to generate variants
  tryCatch({
    # Convert R data to Python-compatible format
    context_json <- jsonlite::toJSON(context, auto_unbox = TRUE)
    
    # TEMPORAL DEBUG: Force available_strategies to be an array
    if (!is.null(config_data$evolution_config$available_strategies)) {
      # Ensure it's always treated as an array, even if single element
      config_data$evolution_config$available_strategies <- as.list(config_data$evolution_config$available_strategies)
    }
    
    # Enable dynamic prompting by default
    if (is.null(config_data$llm_config$use_dynamic_prompting)) {
      config_data$llm_config$use_dynamic_prompting <- TRUE
      message("irace-evo: 🎯 Dynamic prompting ENABLED - Will adapt prompts based on performance history")
    } else if (isTRUE(config_data$llm_config$use_dynamic_prompting)) {
      message("irace-evo: 🎯 Dynamic prompting ENABLED via config")
    } else {
      message("irace-evo: ⚪ Dynamic prompting DISABLED via config")
    }
    
    # Add scenario config to LLM config for dynamic prompting
    config_data$llm_config$scenario_config <- list(
      execDir = scenario$execDir
    )
    
    config_json <- jsonlite::toJSON(config_data, auto_unbox = TRUE)
    # --- INICIO: CÓDIGO CORREGIDO ---
    # To keep the string valid in Python we must escape TWO things:
    # 1. Las barras invertidas (\) deben convertirse en (\\)
    # 2. Las comillas simples (') deben convertirse en (\')
    
    escape_for_python <- function(json_string) {
      # OJO: En R, para representar una \ literal en un string, se escribe \\.
      # Por eso, para buscar una \ (\\) y reemplazarla por dos \\ (\\\\), la sintaxis es rara.
      json_string <- gsub('\\', '\\\\', json_string, fixed = TRUE)
      json_string <- gsub("'", "\\'", json_string, fixed = TRUE)
      return(json_string)
    }
    context_json_escaped <- escape_for_python(context_json)
    config_json_escaped <- escape_for_python(config_json)
    # Get API key for direct passing to Python
    api_key <- Sys.getenv("OPENAI_API_KEY", "")
    if (nzchar(api_key)) {
      api_key_escaped <- escape_for_python(api_key)
    } else {
      api_key_escaped <- ""
    }
    
    # Build the Python command as a string without leading indentation.
    # Every line starts flush at the left margin.
    python_command <- paste0(
      "import json\n",
      "import os\n",
      "from logging_config import setup_logging\n",
      "setup_logging()\n",
      if (nzchar(api_key_escaped)) paste0("os.environ['OPENAI_API_KEY'] = '", api_key_escaped, "'\n") else "",
      "context = json.loads('", context_json_escaped, "')\n",
      "config = json.loads('", config_json_escaped, "')\n",
      "manager = code_manager.CodeEvolutionManager(config)\n",
      "variants = manager.generate_and_compile_variants(context)"
    )
    
    message("LOG: Ejecutando el siguiente comando en Python:\n", python_command)
    
    # Verify Python can see the environment variable
    reticulate::py_run_string("import os; api_key = os.getenv('OPENAI_API_KEY'); print('Python sees OPENAI_API_KEY:', bool(api_key), '| Length:', len(api_key) if api_key else 0)")
    
    # Test basic OpenAI connectivity before proceeding
    message("LOG: Testing basic OpenAI connectivity...")
    test_result <- tryCatch({
      reticulate::py_run_string("
import openai
client = openai.OpenAI(timeout=30)
try:
    test_response = client.chat.completions.create(
        model='gpt-4o',
        messages=[{'role': 'user', 'content': 'Hello, respond with just OK'}],
        max_tokens=10,
        timeout=30
    )
    print('OpenAI test SUCCESS:', test_response.choices[0].message.content.strip())
except Exception as e:
    print('OpenAI test FAILED:', str(e))
      ")
      TRUE
    }, error = function(e) {
      message("LOG: OpenAI connectivity test failed: ", e$message)
      FALSE
    })
    
    if (test_result) {
      message("LOG: OpenAI connectivity test completed.")
    }
    
    # Execute Python code generation with timing
    llm_start_time <- Sys.time()
    reticulate::py_run_string(python_command)
    llm_end_time <- Sys.time()
    llm_processing_time <- as.numeric(difftime(llm_end_time, llm_start_time, units = "secs"))
    
    message("LOG: reticulate::py_run_string() execution finished.")
    
    python_result <- reticulate::py$variants
    
    # Save detailed Python execution log
    llm_log_dir <- file.path(scenario$execDir, "irace-evo-llm-logs")
    if (!dir.exists(llm_log_dir)) {
      dir.create(llm_log_dir, recursive = TRUE, showWarnings = FALSE)
    }
    
    execution_log_file <- file.path(llm_log_dir, "python_execution.log")
    execution_info <- paste0(
      "=== Python Execution Log (Iteration ", iteration_stats$iteration, ") ===\n",
      "Timestamp: ", Sys.time(), "\n\n",
      "=== Python Command Executed ===\n",
      python_command, "\n\n",
      "=== Python Result Structure ===\n",
      paste(capture.output(str(python_result)), collapse = "\n"), "\n\n"
    )
    
    tryCatch({
      cat(execution_info, file = execution_log_file, append = TRUE)
    }, error = function(e) {
      irace_warning("irace-evo: Failed to save execution log: ", e$message)
    })
    
    variants_test <- python_result[[1]]
    
    if (is.null(python_result) || length(python_result) < 2) {
      irace_error("Invalid Python result format. Expected list with variants and metrics.")
    }
    
    variants <- python_result[[1]]  # variants
    metrics <- python_result[[2]]   # metrics
    
    if (is.null(variants) || length(variants) == 0) {
      irace_error("No code variants returned from Python backend")
    }
    
    # Add actual LLM processing time to metrics
    metrics$llm_processing_time <- llm_processing_time
    
    # Convert to R format
    processed_variants <- process_generated_variants(variants, scenario, iteration_stats$iteration)
    
    # NUEVO LOG: Antes de devolver el resultado
    message("LOG: Variants processed. Exiting generate_code_variants() successfully.")
    
    return(list(
      variants = processed_variants,
      metrics = metrics
    ))
    
  }, error = function(e) { 
    
    # Print the detailed error BEFORE stopping execution
    message("\n\n--- ERROR DETALLADO DE PYTHON CAPTURADO ---\n")
    print(e)
    message("\n--- FIN DEL ERROR DETALLADO ---\n\n")
    
    irace_error("Code variant generation failed. See detailed error above.")
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
      irace_note("irace-evo: Elite variant preserved as: ", variant_id)
    } else {
      # Save source code to file for logging with iteration number (0-indexed to match Python)
      variant_id <- paste0("variant_", i-1, "_iter", current_iteration)
    }
    source_file_path <- file.path(source_log_dir, paste0(variant_id, ".cpp"))
    
    # Write source code to file
    if (!is.null(variant$code) && nzchar(variant$code)) {
      tryCatch({
        writeLines(variant$code, source_file_path)
        irace_note("irace-evo: Saved source code to ", source_file_path)
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
    
    # Handle executable path creation differently for elite vs new variants
    if (!is.null(variant$strategy) && variant$strategy == "elite_preserved") {
      # For elite variants, we need to compile from source or find existing executable
      irace_note("irace-evo: Processing elite preserved variant: ", variant_id)
      
      # Compile the preserved source code
      config_data <- jsonlite::fromJSON(scenario$codeEvolutionConfig)
      base_name <- tools::file_path_sans_ext(basename(config_data$source_config$source_file))
      
      # Extract clean variant name for consistent naming
      clean_variant_name <- gsub("_elite$", "", variant_id)  # Remove _elite suffix
      clean_variant_name <- gsub("^variant_", "algorithm_var_", clean_variant_name)  # Convert to standard format
      
      new_executable_path <- file.path(scenario$execDir, "bin", clean_variant_name)
      
      # Ensure bin directory exists
      bin_dir <- file.path(scenario$execDir, "bin")
      if (!dir.exists(bin_dir)) {
        dir.create(bin_dir, recursive = TRUE, showWarnings = FALSE)
      }
      
      # Compile the preserved variant
      compile_command <- paste("g++ -O3 -std=c++17 -Wall", 
                              shQuote(source_file_path), 
                              "-o", shQuote(new_executable_path),
                              "2>/dev/null")
      
      compile_result <- system(compile_command, ignore.stdout = TRUE, ignore.stderr = TRUE)
      
      if (compile_result == 0) {
        irace_note("irace-evo: Successfully compiled elite variant: ", new_executable_path)
      } else {
        irace_warning("irace-evo: Failed to compile elite variant: ", variant_id)
      }
      
    } else {
      # Create iteration-specific executable path for new variants
      original_exe_path <- variant$executable
      
      if (is.null(original_exe_path) || !nzchar(original_exe_path)) {
        irace_warning("irace-evo: Invalid executable path for variant ", variant_id)
        new_executable_path <- file.path(scenario$execDir, "bin", paste0("invalid_", variant_id))
      } else {
        exe_dir <- dirname(original_exe_path)
        exe_name <- basename(original_exe_path)
        exe_base <- tools::file_path_sans_ext(exe_name)
        exe_ext <- tools::file_ext(exe_name)
        
        # Add iteration number to executable name
        if (exe_ext != "") {
          new_exe_name <- paste0(exe_base, "_iter", current_iteration, ".", exe_ext)
        } else {
          new_exe_name <- paste0(exe_base, "_iter", current_iteration)
        }
        new_executable_path <- file.path(exe_dir, new_exe_name)
        
        # Copy or move the compiled executable to the iteration-specific name
        if (file.exists(original_exe_path)) {
          file.copy(original_exe_path, new_executable_path, overwrite = TRUE)
          # Keep the original for the Python backend's validation
        }
      }
    }
    
    processed_variants[[i]] <- list(
      id = variant_id,
      executable_path = new_executable_path,
      source_code = variant$code,
      source_file_path = source_file_path,
      parent_id = if (is.null(variant$parent)) "initial" else variant$parent,
      compilation_success = file.exists(new_executable_path),
      generation_strategy = if (is.null(variant$strategy)) "unknown" else variant$strategy
    )
  }
  
  # Filter only successful compilations
  successful_variants <- Filter(function(x) x$compilation_success, processed_variants)
  
  if (length(successful_variants) == 0) {
    irace_error("No code variants compiled successfully")
  }
  
  if (length(successful_variants) < scenario$codeEvolutionVariants) {
    irace_warning("Only ", length(successful_variants), " out of ", 
                  scenario$codeEvolutionVariants, " variants compiled successfully")
  }
  
  return(successful_variants)
}

#' Update target-runner to use code evolution
#'
#' @param variants List of generated code variants  
#' @param scenario irace scenario
#' @return Updated scenario with variant-aware target runner
setup_variant_target_runner <- function(variants, scenario) {
  
  # Load configuration to get correct executable name
  config_data <- jsonlite::fromJSON(scenario$codeEvolutionConfig)
  source_file <- config_data$source_config$source_file
  
  # Extract executable name from source file (remove path and .cpp extension)
  base_name <- tools::file_path_sans_ext(basename(source_file))
  executable_name <- base_name
  
  # Add the original algorithm as the first variant
  original_variant <- list(
    id = "original",
    executable_path = file.path(scenario$execDir, "bin", executable_name),  # Path to original algorithm
    strategy = "baseline",
    parent_id = "none"
  )
  
  # Load existing variants from previous iterations (if any)
  variant_map_file <- file.path(scenario$execDir, ".irace_evo_variants.csv")
  existing_variants <- list()
  existing_variant_map <- NULL
  
  if (file.exists(variant_map_file)) {
    tryCatch({
      existing_variant_map <- read.csv(variant_map_file, stringsAsFactors = FALSE)
      # Extract unique variants from existing mapping
      unique_existing <- unique(existing_variant_map[, c("executable_path", "variant_id")])
      for (i in 1:nrow(unique_existing)) {
        existing_variants[[length(existing_variants) + 1]] <- list(
          id = unique_existing$variant_id[i],
          executable_path = unique_existing$executable_path[i]
        )
      }
      irace_note("irace-evo: Loaded ", length(existing_variants), " variants from previous iterations")
    }, error = function(e) {
      irace_warning("irace-evo: Failed to load existing variants: ", e$message)
      existing_variants <- list()
    })
  }
  
  # Combine existing variants, original, and new generated variants
  all_variants <- c(existing_variants, list(original_variant), variants)
  
  # Remove duplicates based on variant ID
  unique_variants <- list()
  seen_ids <- character(0)
  
  for (variant in all_variants) {
    if (!(variant$id %in% seen_ids)) {
      unique_variants[[length(unique_variants) + 1]] <- variant
      seen_ids <- c(seen_ids, variant$id)
    }
  }
  
  all_variants <- unique_variants
  
  # Create mapping file for all accumulated variants with round-robin assignment
  num_variants <- length(all_variants)
  # Increase the upper bound to handle more configurations (e.g., 200 to accommodate accumulated variants)
  max_expected_configs <- max(200, num_variants * 20)  # Larger upper bound for accumulated variants
  
  config_ids <- 1:max_expected_configs
  variant_assignments <- rep(1:num_variants, length.out = max_expected_configs)
  
  variant_map <- data.frame(
    config_id = config_ids,
    executable_path = sapply(variant_assignments, function(idx) all_variants[[idx]]$executable_path),
    variant_id = sapply(variant_assignments, function(idx) all_variants[[idx]]$id),
    stringsAsFactors = FALSE
  )
  
  irace_note("irace-evo: Created accumulated variant mapping with round-robin assignment for ", max_expected_configs, 
             " configurations using ", num_variants, " total variants (", length(variants), " new + ", length(existing_variants) + 1, " existing)")
  
  # Save accumulated mapping to file
  write.csv(variant_map, variant_map_file, row.names = FALSE)
  
  # Handle SLURM distribution
  if (!is.null(scenario$batchmode) && scenario$batchmode == "slurm" && scenario$parallel > 1) {
    distribute_variants_slurm(all_variants, variant_map, scenario)
  }
  
  # Store original target runner only once
  if (is.null(scenario$originalTargetRunner)) {
    scenario$originalTargetRunner <- scenario$targetRunner
  }
  
  # Update target runner data to include variant mapping
  scenario$targetRunnerData <- list(
    original_runner = scenario$originalTargetRunner,
    variant_map_file = variant_map_file,
    variants = all_variants
  )
  
  # Mark that variants are now available for IMMEDIATE use
  scenario$codeEvolutionVariantsReady <- TRUE
  
  # Store variant mapping in scenario for access during result printing
  scenario$codeEvolutionVariantMap <- variant_map
  
  irace_note("irace-evo: Code variants prepared. Using evolution-aware target runner IMMEDIATELY.")
  
  return(scenario)
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
    csv_file <- ".irace_evo_variants.csv"
    if (file.exists(csv_file)) {
      tryCatch({
        variant_map <- read.csv(csv_file, stringsAsFactors = FALSE)
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
      # For configurations beyond our mapping, use round-robin
      num_variants <- length(unique(variant_map$variant_id))
      variant_idx <- ((id - 1) %% num_variants) + 1
      return(paste0("variant_", variant_idx))
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
  
  irace_note("irace-evo: Distributing variants for SLURM execution")
  
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
      
      # Update mapping with SLURM paths
      variant_map$executable_path[i] <- slurm_exec_path
      
      irace_note("irace-evo: Copied variant ", i, " to ", slurm_exec_path)
    }
  }
  
  # Save updated mapping
  slurm_variant_map_file <- file.path(slurm_dir, ".irace_evo_variants.csv")
  write.csv(variant_map, slurm_variant_map_file, row.names = FALSE)
  
  # Create distribution script for SLURM nodes
  create_slurm_distribution_script(slurm_dir, scenario)
  
  # Update main mapping to point to SLURM location
  main_variant_map_file <- file.path(scenario$execDir, ".irace_evo_variants.csv")
  write.csv(variant_map, main_variant_map_file, row.names = FALSE)
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
  
  irace_note("irace-evo: Created SLURM distribution script: ", script_path)
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
      irace_note("irace-evo: Interrupt detected, cleaning up processes...")
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
  
  irace_note("irace-evo: Signal handler setup for process cleanup")
}

#' Validate generated variants for obvious issues
#'
#' @param variants List of generated variants
#' @param scenario irace scenario
#' @return Filtered list of variants
validate_variants <- function(variants, scenario) {
  if (is.null(variants) || length(variants) == 0) {
    return(variants)
  }
  
  irace_note("irace-evo: Validating ", length(variants), " generated variants...")
  
  valid_variants <- list()
  
  for (i in seq_along(variants)) {
    variant <- variants[[i]]
    variant_id <- if ("variant_id" %in% names(variant)) variant$variant_id else paste0("variant_", i)
    
    tryCatch({
      # Check if executable exists
      if (!"executable_path" %in% names(variant) || is.null(variant$executable_path)) {
        irace_note("irace-evo: Warning: Variant ", variant_id, " has no executable path, skipping")
        next
      }
      
      executable_path <- file.path(scenario$execDir, variant$executable_path)
      if (!file.exists(executable_path)) {
        irace_note("irace-evo: Warning: Variant ", variant_id, " executable not found: ", executable_path)
        next
      }
      
      # Quick smoke test: run variant with minimal parameters and short timeout
      test_instance <- list.files(file.path(scenario$execDir, "instances"), pattern = "\\.tsp$", full.names = TRUE)[1]
      if (!is.null(test_instance) && file.exists(test_instance)) {
        cmd <- paste(executable_path, 
                    "--instance", test_instance,
                    "--population-size 10 --generations 5 --seed 12345",
                    "2>/dev/null")
        
        result <- tryCatch({
          system(paste("timeout 10", cmd), intern = TRUE, ignore.stderr = TRUE)
        }, error = function(e) NULL)
        
        if (is.null(result) || length(result) == 0) {
          irace_note("irace-evo: DISCARDING variant ", variant_id, " - failed smoke test (infinite loop or crash)")
          # Remove the problematic executable
          if (file.exists(executable_path)) {
            file.remove(executable_path)
          }
          next  # Skip this variant completely
        } else {
          irace_note("irace-evo: Variant ", variant_id, " passed smoke test")
        }
      }
      
      valid_variants[[length(valid_variants) + 1]] <- variant
      
    }, error = function(e) {
      irace_note("irace-evo: Warning: Error validating variant ", variant_id, ": ", e$message)
    })
  }
  
  discarded_count <- length(variants) - length(valid_variants)
  if (discarded_count > 0) {
    irace_note("irace-evo: Discarded ", discarded_count, " problematic variants")
    
    # If we have too few valid variants, try to generate replacements
    if (length(valid_variants) < max(1, scenario$codeEvolutionVariants * 0.5)) {
      irace_note("irace-evo: Too many variants discarded. Need to regenerate replacements...")
      # Return the valid variants we have - the calling function should handle regeneration
      attr(valid_variants, "needs_regeneration") <- TRUE
      attr(valid_variants, "discarded_count") <- discarded_count
    }
  }
  
  return(valid_variants)
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
    
    irace_note("irace-evo: Killed orphaned variant processes")
    
  }, error = function(e) {
    irace_note("irace-evo: Warning: Could not kill orphaned processes: ", e$message)
  })
}

#' Clean up files from previous irace-evo execution
#'
#' @param scenario irace scenario
cleanup_previous_execution <- function(scenario) {
  
  irace_note("irace-evo: Cleaning up files from previous execution...")
  
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
      irace_note("irace-evo: Removed previous variant mapping file")
    }
    
    # Remove previous source code files
    source_log_dir <- file.path(scenario$execDir, "irace-evo-sources")
    if (dir.exists(source_log_dir)) {
      unlink(source_log_dir, recursive = TRUE)
      irace_note("irace-evo: Removed previous source code directory")
    }
    
    # Remove previous LLM logs
    llm_log_dir <- file.path(scenario$execDir, "irace-evo-llm-logs")
    if (dir.exists(llm_log_dir)) {
      unlink(llm_log_dir, recursive = TRUE)
      irace_note("irace-evo: Removed previous LLM logs directory")
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
        irace_note("irace-evo: Removed ", length(all_variant_files), " previous variant executables")
      }
    }
  } else {
    irace_note("irace-evo: Skipping cleanup - active variants in use")
  }
  
  # Clean up any remaining temporary files from previous runs
  exec_dir <- scenario$execDir
  temp_patterns <- c("*.stdout", "*.stderr", "c[0-9]*-[0-9]*-[0-9]*.stdout", "c[0-9]*-[0-9]*-[0-9]*.stderr")
  
  for (pattern in temp_patterns) {
    temp_files <- list.files(exec_dir, pattern = glob2rx(pattern), full.names = TRUE)
    if (length(temp_files) > 0) {
      file.remove(temp_files)
      irace_note("irace-evo: Removed ", length(temp_files), " temporary output files")
    }
  }
  
  # Remove any duplicate source files that might exist in the main directory
  source_patterns <- c("variant_*.cpp", "algorithm_var_*.cpp", "*.cpp.bak")
  for (pattern in source_patterns) {
    source_files <- list.files(exec_dir, pattern = glob2rx(pattern), full.names = TRUE)
    # Exclude the original source file
    original_source <- file.path(exec_dir, dirname(source_file), basename(source_file))
    source_files <- source_files[source_files != original_source]
    
    if (length(source_files) > 0) {
      file.remove(source_files)
      irace_note("irace-evo: Removed ", length(source_files), " duplicate source files")
    }
  }
  
  # Kill any remaining variant processes
  kill_orphaned_processes(scenario)
  
  # Remove CSV mapping file from previous runs
  variant_csv_file <- file.path(exec_dir, ".irace_evo_variants.csv")
  if (file.exists(variant_csv_file)) {
    file.remove(variant_csv_file)
    irace_note("irace-evo: Removed previous variant mapping file")
  }
  
  # Reset scenario flags
  scenario$codeEvolutionVariantsReady <- NULL
  scenario$originalTargetRunner <- NULL
  scenario$targetRunnerData <- NULL
  
  irace_note("irace-evo: Complete cleanup finished - ready for fresh start")
}

#' Manual cleanup function for emergency cleanup
#' 
#' @param exec_dir Execution directory (default: current directory)
#' @export
clean_irace_evo_files <- function(exec_dir = ".") {
  message("Performing emergency cleanup of irace-evo files...")
  
  # Create a mock scenario for cleanup
  mock_scenario <- list(execDir = exec_dir)
  
  # Call the main cleanup function
  cleanup_previous_execution(mock_scenario)
  
  message("Emergency cleanup completed!")
}

#' Show the best heuristic code from elite configurations
#'
#' @param elite_configurations Elite configurations from current iteration
#' @param scenario irace scenario
show_best_heuristic <- function(elite_configurations, scenario) {
  if (!isTRUE(scenario$codeEvolution) || nrow(elite_configurations) == 0) {
    return()
  }
  
  irace_note("DEBUG: show_best_heuristic called with ", nrow(elite_configurations), " elite configurations")
  if (nrow(elite_configurations) > 0) {
    irace_note("DEBUG: Elite configs variants: ", paste(elite_configurations$.VARIANT., collapse = ", "))
    irace_note("DEBUG: Elite configs ranks: ", paste(elite_configurations$.RANK., collapse = ", "))
  }
  
  tryCatch({
    # Get the best configuration
    best_config <- elite_configurations[1, , drop = FALSE]
    best_variant <- best_config$.VARIANT.[1]
    
    irace_note("DEBUG: best_variant detected as: '", best_variant, "'")
    
    # Skip if it's the original algorithm
    if (is.null(best_variant) || best_variant == "original") {
      irace_note("Current best: Original algorithm (no heuristic modifications)")
      return()
    }
    
    irace_note("DEBUG: Proceeding to show variant: ", best_variant)
    
    # Find the source file for this variant
    sources_dir <- file.path(scenario$execDir, "irace-evo-sources")
    irace_note("DEBUG: Looking for sources in: ", sources_dir)
    
    if (!dir.exists(sources_dir)) {
      irace_note("DEBUG: Sources directory does not exist")
      return()
    }
    
    # Look for the variant source file (using escaped regex pattern)
    pattern <- paste0("^", gsub("([.|()\\^{}+$*?\\[\\]])", "\\\\\\1", best_variant), "\\.cpp$")
    irace_note("DEBUG: Searching with pattern: ", pattern)
    
    all_source_files <- list.files(sources_dir, pattern = "\\.cpp$", full.names = TRUE)
    irace_note("DEBUG: Available source files: ", paste(basename(all_source_files), collapse = ", "))
    
    source_files <- list.files(sources_dir, pattern = pattern, full.names = TRUE)
    irace_note("DEBUG: Matching source files: ", length(source_files))
    
    if (length(source_files) == 0) {
      irace_note("Source file not found for variant: ", best_variant)
      return()
    }
    
    source_file <- source_files[1]
    
    # Read and extract the order_chromosome function
    if (file.exists(source_file)) {
      source_lines <- readLines(source_file, warn = FALSE)
      
      # Find the order_chromosome function
      start_line <- which(grepl("vector<pair<int, double>> order_chromosome\\(", source_lines))[1]
      
      if (!is.na(start_line)) {
        # Find the end of the function by counting braces
        brace_count <- 0
        end_line <- start_line
        found_opening <- FALSE
        
        for (i in start_line:length(source_lines)) {
          line <- source_lines[i]
          if (grepl("\\{", line)) {
            brace_count <- brace_count + lengths(regmatches(line, gregexpr("\\{", line)))
            found_opening <- TRUE
          }
          if (grepl("\\}", line)) {
            brace_count <- brace_count - lengths(regmatches(line, gregexpr("\\}", line)))
          }
          
          if (found_opening && brace_count == 0) {
            end_line <- i
            break
          }
        }
        
        # Extract and display the function
        if (end_line > start_line) {
          cat("\n")
          irace_note("=== CURRENT BEST HEURISTIC (", best_variant, ") ===")
          function_lines <- source_lines[start_line:end_line]
          
          # Clean up and display the function
          for (line in function_lines) {
            cat(line, "\n")
          }
          cat("=== END HEURISTIC ===\n")
        }
      }
    }
  }, error = function(e) {
    # Silent failure - don't interrupt irace if something goes wrong
    return()
  })
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
evolve_code_iteration <- function(elite_configs, iteration_stats, scenario, budget_info = NULL) {
  
  if (!is_code_evolution_enabled(scenario)) {
    return(scenario)  # Return unchanged scenario
  }
  
  # Check if we have enough budget to justify LLM generation
  # Skip LLM generation if we're likely to stop soon due to budget constraints
  # BUT ALWAYS generate variants in the first iteration
  if (!is.null(budget_info) && iteration_stats$iteration > 1) {
    remaining_budget <- budget_info$remaining
    current_budget <- budget_info$current
    min_survival <- scenario$minNbSurvival
    
    # If remaining budget is very low or current budget is insufficient for minimum configs
    # Skip expensive LLM operations to avoid waste (except on first iteration)
    if (remaining_budget <= current_budget * 0.5 || current_budget <= min_survival * 2) {
      irace_note("irace-evo: Skipping LLM generation due to low remaining budget (",
                 remaining_budget, " remaining, ", current_budget, " current)")
      return(scenario)
    }
  }
  
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
  
  irace_note("irace-evo: Generating ", scenario$codeEvolutionVariants, 
             " code variants for iteration ", iteration_stats$iteration)
  
  # Generate new code variants
  variants_result <- generate_code_variants(elite_configs, iteration_stats, scenario)
  variants <- variants_result$variants
  llm_metrics <- variants_result$metrics
  
  # Validate generated variants for obvious issues
  variants <- validate_variants(variants, scenario)
  
  # Check if we need to regenerate discarded variants
  if (!is.null(attr(variants, "needs_regeneration")) && attr(variants, "needs_regeneration")) {
    discarded_count <- attr(variants, "discarded_count")
    irace_note("irace-evo: Regenerating ", discarded_count, " replacement variants...")
    
    tryCatch({
      # Generate replacement variants
      replacement_result <- generate_code_variants(elite_configs, iteration_stats, scenario, num_variants = discarded_count)
      replacement_variants <- replacement_result$variants
      
      # Validate the replacement variants (but don't recursively regenerate)
      replacement_variants <- validate_variants(replacement_variants, scenario)
      
      # Add the valid replacements to our variant list
      if (length(replacement_variants) > 0) {
        variants <- c(variants, replacement_variants)
        llm_metrics$total_calls <- llm_metrics$total_calls + replacement_result$metrics$total_calls
        llm_metrics$total_retries <- llm_metrics$total_retries + replacement_result$metrics$total_retries
        llm_metrics$total_input_tokens <- llm_metrics$total_input_tokens + replacement_result$metrics$total_input_tokens
        llm_metrics$total_output_tokens <- llm_metrics$total_output_tokens + replacement_result$metrics$total_output_tokens
        llm_metrics$estimated_cost <- llm_metrics$estimated_cost + replacement_result$metrics$estimated_cost
        
        irace_note("irace-evo: Successfully generated ", length(replacement_variants), " replacement variants")
      }
    }, error = function(e) {
      irace_note("irace-evo: Warning: Failed to generate replacement variants: ", e$message)
    })
  }
  
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
      saveRDS(scenario$codeEvolutionGlobalMetrics, ".irace_evo_metrics.rds")
    }, error = function(e) {
      # Silent fail - metrics persistence is nice-to-have
    })
  }
  
  # Display metrics in irace console output
  irace_note("irace-evo: Successfully generated ", length(variants), " variants")
  irace_note("LLM Usage - Calls: ", llm_metrics$total_calls, 
             ", Retries: ", llm_metrics$total_retries,
             ", Tokens: ", llm_metrics$total_input_tokens, "+", llm_metrics$total_output_tokens,
             ", Est.Cost: $", sprintf("%.3f", llm_metrics$total_cost_estimate))
  
  # Update scenario to use variants
  scenario <- setup_variant_target_runner(variants, scenario)
  
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
  cat("# ═══════════════════════════════════════════════════════════════════\n")
  
  # LLM Configuration
  cat("# LLM Configuration:\n")
  if (!is.null(metrics$api_provider)) {
    cat(sprintf("#   API Provider:             %s\n", metrics$api_provider))
  }
  if (!is.null(metrics$model)) {
    cat(sprintf("#   Model:                    %s\n", metrics$model))
  }
  if (!is.null(metrics$temperature)) {
    cat(sprintf("#   Temperature:              %.1f\n", metrics$temperature))
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
    cat("# ─────────────────────────────────────────────────────────────────────\n")
    
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
  
  cat("# ═══════════════════════════════════════════════════════════════════\n")
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
          
          message("irace-evo: 📊 PERFORMANCE UPDATE: Racing results added to history (best: ", best_rank, ", winner: ", updated_entry$winning_strategy, ")")
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
  cat("# ═══════════════════════════════════════════════════════════════════\n")
  cat(sprintf("# Winner: %s (Configuration ID: %d)\n", winning_variant, best_config$.ID.))
  performance_text <- if (!is.null(best_config$.RANK.) && !is.na(best_config$.RANK.)) {
    sprintf("%.1f", as.numeric(best_config$.RANK.))
  } else {
    "N/A"
  }
  cat(sprintf("# Performance: Rank %s\n", performance_text))
  cat("#\n")
  
  # Try to find and display the winning function
  source_file <- paste0("irace-evo-sources/", winning_variant, ".cpp")
  original_file <- "./src/brkga.cpp"
  
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
        cat("# ───────────────────────────────────────────────────────────────────\n")
        for (line in variant_function) {
          cat("#", line, "\n")
        }
        cat("#\n")
        
        cat("# ORIGINAL FUNCTION (for comparison):\n") 
        cat("# ───────────────────────────────────────────────────────────────────\n")
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
  
  cat("# ═══════════════════════════════════════════════════════════════════\n")
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

#' Get function name from configuration
#'
#' @param scenario irace scenario
#' @return Function name string
get_function_name_from_config <- function(scenario) {
  config_file <- "./code-evolution.json"
  if (file.exists(config_file)) {
    tryCatch({
      config <- jsonlite::fromJSON(config_file)
      if (!is.null(config$source_config$function_name)) {
        return(config$source_config$function_name)
      }
    }, error = function(e) {
      # Fall back to default if config reading fails
    })
  }
  # Default function name
  return("order_chromosome")
}