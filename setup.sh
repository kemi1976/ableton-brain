#!/bin/bash
# Setup script for ABLETON BRAIN
# Run this script to install the package and its dependencies

set -e

echo "🚀 Setting up ABLETON BRAIN..."
echo "========================================"

# Detect Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "❌ Python not found. Please install Python 3.10+ first."
    exit 1
fi

echo "✓ Using Python: $("$PYTHON" --version)"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    "$PYTHON" -m venv venv
fi

# Activate and install
echo "🔧 Installing dependencies..."
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null || true

pip install --upgrade pip
pip install -e ".[midi,dev]"

# Run tests
echo "🧪 Running tests..."
pytest -v

# Generate config if needed
if [ ! -f ".abrain_config.json" ]; then
    echo "⚙️  Generating config file..."
    python -c "from core.universal_midi_translator import UniversalMIDITranslator; UniversalMIDITranslator().export_config()"
fi

echo ""
echo "✅ Setup complete!"
echo "   Run 'source venv/bin/activate' then 'pytest -v' to verify"
echo "   Run 'python demo_quick.py' to test the system"