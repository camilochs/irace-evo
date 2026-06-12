#!/bin/bash
# Post-installation script for irace
echo "🔧 irace post-install: Creating executable wrapper..."

IRACE_LIB_PATH="/home/camilocs/R/x86_64-pc-linux-gnu-library/4.1/irace"
IRACE_BIN_DIR="$IRACE_LIB_PATH/bin"
IRACE_EXECUTABLE="$IRACE_BIN_DIR/irace"

# Create the executable wrapper
cat > "$IRACE_EXECUTABLE" << 'EXEC_EOF'
#!/bin/sh
# irace executable wrapper
exec R --slave -e "library(irace); irace.cmdline()" --args "$@"
EXEC_EOF

chmod +x "$IRACE_EXECUTABLE"
echo "✅ irace executable created at: $IRACE_EXECUTABLE"
