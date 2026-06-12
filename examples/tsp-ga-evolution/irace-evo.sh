#!/bin/bash
# irace-evo wrapper script
# Configures Python environment before running irace

# Export Python configuration for reticulate
export RETICULATE_PYTHON="/usr/bin/python3"
export PYTHONPATH="/home/camilocs/.local/lib/python3.10/site-packages:$PYTHONPATH"

# Run irace with proper environment
exec irace "$@"