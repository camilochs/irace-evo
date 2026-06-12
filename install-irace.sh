#!/bin/bash
# Complete irace installation with automatic executable creation

echo "📦 Installing irace package..."
R CMD INSTALL .

if [ $? -eq 0 ]; then
    echo "🔧 Creating irace executable..."
    ./post-install.sh
    echo "🎉 irace installation complete!"
else
    echo "❌ irace installation failed!"
    exit 1
fi
