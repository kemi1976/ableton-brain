#!/bin/bash
# startup script for Secondary Eliza on Lenovo Desktop
# Generated: ELIZA Distributed Network Setup

echo "🚀 Starting Eliza Secondary Node on Lenovo..."
echo "=================================================="

# Change to script directory
cd "$(dirname "$0")/.."

# Display configuration
echo ""
echo "📋 Configuration:"
echo "   Primary Coordinator: 100.82.15.79"
echo "   Role: Assistant/Processing"
echo "   Features: ML Processing, File Backup, Database Sync"
echo "   Port: 8000"
echo ""

# Check dependencies
echo "🔍 Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "❌ Python not found!"
    exit 1
fi

echo "✅ Using: $PYTHON"
$PYTHON --version

# Check Tailscale
echo ""
echo "🔍 Checking Tailscale..."
if command -v tailscale &> /dev/null; then
    echo "✅ Tailscale available"
    tailscale status --json 2>/dev/null | $PYTHON -c "import sys,json; d=json.load(sys.stdin); print(f'   Connected: {len([n for n in d[\"Machine\"].values() if n[\"SeenAt\"]])} nodes')"
else
    echo "⚠️ Tailscale CLI not found"
fi

# Start Eliza
echo ""
echo "🎯 Launching Eliza Secondary Node..."
echo "=================================================="

# If eliza.py exists, run it
if [ -f "eliza.py" ]; then
    $PYTHON eliza.py --mode assistant --port 8000
# Otherwise just show ready message
else
    echo "✅ Eliza Secondary ready!"
    echo "   Configuration: knowledge/ableton-brain/secondary-config.json"
    echo "   Startup file: This script"
    echo ""
    echo "   To start: $PYTHON knowledge/ableton-brain/scripts/start-secondary.sh"
fi

echo ""
echo "✅ Eliza Secondary Node Complete"
echo "=================================================="