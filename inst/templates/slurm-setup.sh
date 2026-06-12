#!/bin/bash
###############################################################################
# SLURM Setup Script for irace-evo
#
# This script helps set up the SLURM environment for irace evolution runs.
# It distributes variant executables and sets up the necessary directory structure.
#
# Usage:
#   ./slurm-setup.sh [--distribute-variants] [--clean]
#
# Options:
#   --distribute-variants  Copy variant executables to all compute nodes
#   --clean               Clean up SLURM-specific directories
#   --help               Show this help message
#
###############################################################################

error() {
    echo "Error: $@" >&2
    exit 1
}

info() {
    echo "INFO: $@"
}

debug() {
    if [ "$DEBUG" = "1" ]; then
        echo "DEBUG: $@" >&2
    fi
}

show_help() {
    cat << EOF
SLURM Setup Script for irace-evo

Usage: $0 [OPTIONS]

OPTIONS:
    --distribute-variants    Copy variant executables to shared filesystem
    --clean                 Clean up SLURM-specific directories
    --setup-env             Set up SLURM environment variables
    --check-config          Validate SLURM configuration
    --help                  Show this help message

ENVIRONMENT VARIABLES:
    IRACE_SLURM_PARTITION   SLURM partition to use (default: defq)
    IRACE_SLURM_TIME        Time limit for jobs (default: 0-1:00:00)
    IRACE_SLURM_CPUS        CPUs per task (default: 1)
    IRACE_SLURM_MEM         Memory per CPU in MB (default: 8000)
    IRACE_SLURM_MODULES     Space-separated list of modules to load
    DEBUG                   Set to 1 for debug output

EXAMPLES:
    # Setup and distribute variants for SLURM
    $0 --distribute-variants
    
    # Check SLURM configuration
    $0 --check-config
    
    # Clean up after experiments
    $0 --clean

EOF
}

distribute_variants() {
    info "Distributing variant executables for SLURM..."
    
    # Create SLURM-specific directory
    SLURM_DIR=".irace_evo_slurm"
    mkdir -p "$SLURM_DIR"
    
    # Copy variant mapping file
    if [ -f ".irace_evo_variants.csv" ]; then
        cp ".irace_evo_variants.csv" "$SLURM_DIR/"
        info "Copied variant mapping to $SLURM_DIR/"
    else
        debug "No variant mapping file found (normal for first iteration)"
    fi
    
    # Copy all executables to SLURM directory
    if [ -d "bin" ]; then
        cp -r bin "$SLURM_DIR/"
        info "Copied executables to $SLURM_DIR/bin/"
    fi
    
    # Copy source directories for on-demand compilation
    if [ -d "src" ]; then
        cp -r src "$SLURM_DIR/"
        info "Copied source files to $SLURM_DIR/src/"
    fi
    
    if [ -d "irace-evo-sources" ]; then
        cp -r irace-evo-sources "$SLURM_DIR/"
        info "Copied evolved sources to $SLURM_DIR/irace-evo-sources/"
    fi
    
    # Copy configuration files
    for config_file in code-evolution.json *.json; do
        if [ -f "$config_file" ]; then
            cp "$config_file" "$SLURM_DIR/"
            debug "Copied $config_file to SLURM directory"
        fi
    done
    
    # Create distribution script
    cat > "$SLURM_DIR/distribute_variants.sh" << 'DIST_EOF'
#!/bin/bash
# This script is sourced by the target-runner on each SLURM node
# It ensures that all necessary files are available locally

debug() {
    if [ "$DEBUG" = "1" ]; then
        echo "DEBUG (SLURM node): $@" >&2
    fi
}

# Check if we're on a compute node
if [ -n "$SLURM_JOB_ID" ]; then
    debug "SLURM node setup: Job $SLURM_JOB_ID on node $SLURMD_NODENAME"
    
    # If using node-local storage, copy files there
    if [ -n "$SLURM_TMPDIR" ]; then
        debug "Using node-local storage: $SLURM_TMPDIR"
        # Implementation would go here for node-local copying
    fi
    
    debug "SLURM node setup completed"
fi
DIST_EOF
    
    chmod +x "$SLURM_DIR/distribute_variants.sh"
    info "Created distribution script"
    
    info "SLURM variant distribution completed"
}

setup_environment() {
    info "Setting up SLURM environment..."
    
    # Set default SLURM parameters if not already set
    export IRACE_SLURM_PARTITION=${IRACE_SLURM_PARTITION:-defq}
    export IRACE_SLURM_TIME=${IRACE_SLURM_TIME:-0-1:00:00}
    export IRACE_SLURM_CPUS=${IRACE_SLURM_CPUS:-1}
    export IRACE_SLURM_MEM=${IRACE_SLURM_MEM:-8000}
    
    info "SLURM environment configured:"
    info "  Partition: $IRACE_SLURM_PARTITION"
    info "  Time limit: $IRACE_SLURM_TIME"
    info "  CPUs per task: $IRACE_SLURM_CPUS"
    info "  Memory per CPU: ${IRACE_SLURM_MEM}MB"
    
    if [ -n "$IRACE_SLURM_MODULES" ]; then
        info "  Modules to load: $IRACE_SLURM_MODULES"
    fi
}

check_config() {
    info "Checking SLURM configuration..."
    
    # Check if SLURM is available
    if ! command -v sbatch >/dev/null 2>&1; then
        error "SLURM not found. Make sure SLURM is installed and in PATH."
    fi
    
    if ! command -v srun >/dev/null 2>&1; then
        error "srun not found. SLURM installation appears incomplete."
    fi
    
    info "✓ SLURM commands available"
    
    # Check partition
    PARTITION=${IRACE_SLURM_PARTITION:-defq}
    if ! sinfo -p "$PARTITION" >/dev/null 2>&1; then
        error "SLURM partition '$PARTITION' not found or not accessible"
    fi
    
    info "✓ SLURM partition '$PARTITION' is accessible"
    
    # Check for target runner
    if [ -f "target-runner-evolution-slurm.tmpl" ]; then
        info "✓ SLURM target runner template found"
    elif [ -f "target-runner" ] && grep -q "sbatch" "target-runner"; then
        info "✓ SLURM-enabled target runner found"
    else
        info "⚠ No SLURM target runner found. Consider using target-runner-evolution-slurm.tmpl"
    fi
    
    # Check for code evolution config
    if [ -f "code-evolution.json" ]; then
        info "✓ Code evolution configuration found"
        
        # Check if SLURM is enabled in config
        if grep -q '"cluster_config"' code-evolution.json && grep -q '"enabled".*true' code-evolution.json; then
            info "✓ SLURM cluster mode enabled in configuration"
        else
            info "⚠ SLURM cluster mode not enabled in code-evolution.json"
        fi
    else
        info "⚠ No code-evolution.json found"
    fi
    
    info "SLURM configuration check completed"
}

clean_slurm() {
    info "Cleaning SLURM-specific directories..."
    
    rm -rf ".irace_evo_slurm"
    info "Removed .irace_evo_slurm directory"
    
    # Clean up SLURM job output files (if any)
    rm -f slurm-*.out
    rm -f irace-evo-*.out
    info "Removed SLURM output files"
    
    info "SLURM cleanup completed"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --distribute-variants)
            distribute_variants
            shift
            ;;
        --setup-env)
            setup_environment
            shift
            ;;
        --check-config)
            check_config
            shift
            ;;
        --clean)
            clean_slurm
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            error "Unknown option: $1. Use --help for usage information."
            ;;
    esac
done

# If no arguments provided, show help
if [ $# -eq 0 ]; then
    show_help
fi