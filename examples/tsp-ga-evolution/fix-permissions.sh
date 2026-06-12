#!/bin/bash
# Script para arreglar permisos del template después de reinstalar irace
echo "Fixing irace-evo template permissions..."
chmod +x /home/camilocs/R/x86_64-pc-linux-gnu-library/4.1/irace/templates/target-runner-evolution.tmpl
echo "Permissions fixed!"
ls -la /home/camilocs/R/x86_64-pc-linux-gnu-library/4.1/irace/templates/target-runner-evolution.tmpl