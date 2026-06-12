#!/bin/sh
#############################################################################
# Example SLURM job script for irace-evo (irace with code evolution)
# 
# This extends the basic irace SLURM example to support code evolution
# using LLMs for automatic algorithm generation.
#
# Launch this script with:
#   sbatch job-irace-evo.sh
#
# Requirements:
# - Python 3.7+ with openai/anthropic packages
# - R with reticulate and jsonlite packages
# - LLM API key (OpenAI or Anthropic)
#############################################################################
#SBATCH --account=user_account
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=30
#SBATCH --mem=0
#SBATCH --job-name=irace_evo_job
#SBATCH --mail-user=user@example.com
#SBATCH --time=12:00:00
#SBATCH --output=/mypath/irace-evo-%j.out
#SBATCH --error=/mypath/irace-evo-%j.err

# Load required modules
module load r
module load python/3.9
# Add other modules your algorithm requires

# Set LLM API key (choose one)
export OPENAI_API_KEY="your-openai-api-key-here"
# export ANTHROPIC_API_KEY="your-anthropic-api-key-here"

# Install Python dependencies (run once)
# pip install --user openai anthropic requests

# Create code evolution configuration
cat > code-evolution.json << 'EOF'
{
  "language_config": {
    "language": "cpp"
  },
  "source_config": {
    "source_file": "./src/algorithm.cpp",
    "function_name": "optimize"
  },
  "build_config": {
    "cpp": {
      "compiler": "g++",
      "flags": ["-O3", "-std=c++17"],
      "output_dir": "./bin"
    }
  },
  "llm_config": {
    "api_provider": "openai",
    "model": "gpt-4",
    "api_key_env": "OPENAI_API_KEY"
  },
  "cluster_config": {
    "enabled": true,
    "type": "slurm",
    "shared_filesystem": true,
    "distribute_variants": true
  }
}
EOF

# Create scenario file with code evolution enabled
cat > scenario-evo.txt << 'EOF'
execDir = "~/local/irace-execdir/"
logFile = "./irace-evo.Rdata"
parameterFile = "./parameters.txt"
targetRunner = "./target-runner"

# Code evolution settings
codeEvolution = TRUE
codeEvolutionConfig = "./code-evolution.json"
codeEvolutionVariants = 5

# Standard irace settings
maxExperiments = 1000
parallel = 30
EOF

echo "Starting irace-evo with SLURM distribution"
echo "Nodes: $SLURM_NNODES, Tasks per node: $SLURM_NTASKS_PER_NODE"
echo "Total parallel tasks: $SLURM_NTASKS"

# Option 1: Run irace-evo with automatic parallelization
~/bin/irace --scenario scenario-evo.txt --batchmode slurm --parallel $((SLURM_NTASKS_PER_NODE))

# Option 2: With MPI (if needed)
# mpirun -np 1 ~/bin/irace --scenario scenario-evo.txt --batchmode slurm --parallel $((SLURM_NTASKS-1)) --mpi 1

echo "irace-evo completed"
echo "Results in: irace-evo.Rdata"
echo "Generated variants in: ~/local/irace-execdir/.irace_evo_slurm/bin/"