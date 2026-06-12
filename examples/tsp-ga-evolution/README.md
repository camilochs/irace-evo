# TSP Genetic Algorithm with irace-evo

This example demonstrates how to use **irace-evo** to automatically evolve heuristics in a Genetic Algorithm for the Traveling Salesman Problem (TSP).

## 📁 Project Structure

```
tsp-ga-evolution/
├── src/
│   └── brkga.cpp               # BRKGA implementation with evolvable heuristics
├── instances/
│   └── att48.tsp               # TSP test instance (48 cities)
├── bin/                        # Compiled executables (created automatically)
├── logs/                       # irace-evo log files (created automatically)
├── parameters.txt              # Parameter space definition for irace
├── scenario.txt                # irace scenario configuration
├── code-evolution.json         # irace-evo evolution settings
├── target-runner              # Script that runs algorithm for irace
├── Makefile                   # Build automation
└── README.md                  # This file
```

## 🎯 What Gets Evolved

The GA has several **evolvable heuristics** that irace-evo can modify:

1. **`crossover_ox()`** - Order Crossover operator
2. **`mutate_swap()`** - Swap mutation operator  
3. **`tournament_selection()`** - Tournament selection
4. **`local_search_2opt()`** - 2-opt local search

The LLM will generate improved versions of these functions using domain-specific knowledge about TSP.

## 🔧 Requirements

### Software Dependencies
- **g++** with C++17 support
- **R** (≥ 4.0) with packages:
  - `irace-evo` (this modified version - install from source)
  - `reticulate` (≥ 1.20)
  - `jsonlite`
- **Python** (≥ 3.7) with packages:
  - `openai` (for GPT models)
  - `anthropic` (optional, for Claude models)

### API Access
- **OpenAI API key** (set `OPENAI_API_KEY` environment variable)
- OR **Anthropic API key** (set `ANTHROPIC_API_KEY` environment variable)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install base R packages (NOT irace - we'll install the modified version)
R -e "install.packages(c('reticulate', 'jsonlite'))"

# Install Python packages  
pip install openai anthropic requests

# Install irace-evo (from parent directory)
cd ../../  # Go to irace source directory
R CMD INSTALL .

# Verify irace-evo installation
R -e "library(irace); print(paste('irace version:', packageVersion('irace')))"

# Set API key
export OPENAI_API_KEY="your-api-key-here"

# Return to example directory
cd examples/tsp-ga-evolution/
```

### 2. Compile and Test

```bash
cd tsp-ga-evolution/

# Compile the algorithm
make

# Test basic functionality
make test
# Should output a number like: 12345.67
```

### 3. Run irace-evo

```bash
# Standard irace (parameter tuning only)
irace --scenario scenario.txt

# irace-evo (parameter tuning + code evolution)
irace --scenario scenario.txt --code-evolution
```

## 📊 Expected Results

### Standard irace Output
```
# Iteration 1: Configuration 23 (cost: 11542.3)
# Iteration 2: Configuration 45 (cost: 11234.1) 
# Iteration 3: Configuration 67 (cost: 10987.4)
# Final: Best parameters found with cost ~10900
```

### irace-evo Output  
```
# Iteration 1: Configuration 23 (cost: 11542.3)
# irace-evo: Generating 5 code variants for iteration 2
# irace-evo: Successfully generated 5 variants
# LLM Usage - Calls: 3, Tokens: 2847+1534, Est.Cost: $0.023
# Iteration 2: Configuration 34 (cost: 10876.2) ← Improved with evolved code!
# irace-evo: Generating 5 code variants for iteration 3
# Final: Evolved algorithm + parameters with cost ~10200
```

## ⚙️ Configuration Files

### `parameters.txt` - Parameter Space
```
population_size    "--population-size "    i    (50, 200)
crossover_rate     "--crossover-rate "     r    (0.5, 0.95)
mutation_rate      "--mutation-rate "      r    (0.01, 0.1)
tournament_size    "--tournament-size "    i    (2, 8)
local_search       "--local-search "       c    (true, false)
generations        "--generations "        i    (100, 1000)
```

### `code-evolution.json` - Evolution Settings
- **Target function**: `crossover_ox` (but can evolve others)
- **Strategies**: TSP-specific + general optimization
- **Validation**: Automatic compilation and testing
- **Fallback**: Keeps working variants if generation fails

### `scenario.txt` - Racing Configuration  
- **Budget**: 2000 evaluations, 2 hours max
- **Code evolution**: 5 variants per iteration
- **Instances**: All `.tsp` files in `instances/`

## 🔍 Monitoring Progress

### Log Files
```bash
# Main irace log
tail -f irace-evo.log

# Code evolution details  
tail -f logs/irace-evo.log

# LLM interactions (if enabled)
tail -f logs/irace-evo-llm.log
```

### Generated Code
```bash
# View evolved variants
ls -la .irace_evo_slurm/bin/    # In SLURM mode
ls -la bin/variant_*            # In local mode

# Compare original vs evolved
diff src/brkga.cpp bin/variant_1_source.cpp
```

## 🐛 Troubleshooting

### Common Issues

**1. "No API key found"**
```bash
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."
```

**2. "Python module not found"**
```bash
pip install --user openai anthropic requests
# Check Python path in R
R -e "reticulate::py_config()"
```

**3. "Compilation failed"**  
```bash
# Check g++ version
g++ --version  # Need C++17 support

# Manual compile test
g++ -O3 -std=c++17 -Wall src/brkga.cpp -o bin/brkga
```

**4. "No code variants generated"**
```bash
# Check evolution config
cat code-evolution.json | jq '.llm_config'

# Check logs
grep -i error logs/irace-evo.log
```

### Debug Mode
```bash
# Enable detailed logging
DEBUG=1 irace --scenario scenario.txt --code-evolution

# Enable LLM interaction logs
# Edit code-evolution.json: "log_llm_interactions": true
```

## 📈 Understanding Results

### Performance Comparison
```r
# Load results in R
load("irace-evo.Rdata")

# Best configuration found
print(getFinalElites(iraceResults))

# Compare with standard irace
# (run both versions and compare costs)
```

### Code Analysis
```bash
# View the best evolved heuristic
cat .irace_evo_slurm/bin/variant_best_source.cpp

# Common evolutions:
# - Better 2-opt implementation
# - Edge recombination crossover
# - Adaptive mutation rates
# - Problem-specific local search
```

## 🎯 Next Steps

1. **Add more instances**: Put more `.tsp` files in `instances/`
2. **Longer runs**: Increase `maxExperiments` in `scenario.txt`  
3. **More variants**: Increase `codeEvolutionVariants`
4. **Custom strategies**: Add domain-specific strategies in `code-evolution.json`
5. **SLURM**: Enable cluster execution for larger experiments

## 📚 References

- **irace**: López-Ibáñez et al. "The irace package: Iterated racing for automatic algorithm configuration"
- **TSP-GA**: Goldberg, D. "Genetic Algorithms in Search, Optimization and Machine Learning"
- **Instance**: ATT48 from TSPLIB (Reinelt, 1991)