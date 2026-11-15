#!/bin/bash
# Startup script for Secondary Eliza on Lenovo Desktop
# This script starts the assistant instance on port 8000

echo "🚀 STARTING SECONDARY ELIZA ON LENOV0"
echo "========================================"

# Navigate to Eliza directory
cd ~/eliza-secondary

# Check if Python 3.14 is available
if command -v python3.14 &> /dev/null; then
    PYTHON=python3.14
elif command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "❌ Python not found!"
    exit 1
fi

# Stop any existing instance
echo "🔍 Checking for existing instance..."
pkill -f "eliza.*secondary" 2>/dev/null || true

# Start secondary Eliza
echo "✅ Starting Secondary Eliza..."
$PYTHON eliza.py --mode assistant --role secondary --port 8000

# Alternative startup commands:
# For Windows (PowerShell):
# python C:\Users\pc\Scripts\eliza.py --mode assistant --role secondary --port 8000

# For direct Python path:
# /c/Users/pc/AppData/Local/Programs/Python/Python314/python.exe eliza.py --mode assistant --port 8000

echo "🎧 Secondary Eliza is running on http://100.90.0.100:8000"