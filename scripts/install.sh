#!/bin/bash
# Install Script for Ableton Brain System
# Works on Windows, macOS, and Linux with backwards compatibility
# ================================================

set -e  # Exit on error

echo "🚀 ABLETON BRAIN INSTALLER"
echo "================================"
echo ""

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo "🖥️  Detected OS: $OS"

# Common paths
BASE_DIR="${HOME}/AI_PROJECTS_ANDROID"
if [ "$OS" = "windows" ]; then
    BASE_DIR="/c/Users/$(whoami)/Documents/AI PROJECTS ANDROID"
fi

# Check if base directory exists
if [ ! -d "$BASE_DIR" ]; then
    echo "⚠️  Creating base directory: $BASE_DIR"
    mkdir -p "$BASE_DIR"
fi

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
if [ "$OS" = "windows" ]; then
    PYTHON="python"
else
    PYTHON="python3"
fi

# Check Python installation
if ! command -v $PYTHON &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.14+ first."
    exit 1
fi

echo "✅ Python version: $($PYTHON --version)"

# Install required packages
echo "📥 Installing packages..."
pip install --upgrade pip -q

# Install core dependencies
DEPENDENCIES=(
    "keyboard"
    "python-rtmidi"
    "websocket-client"
    "pyaudio"
    "numpy"
    "Pillow"
    "qrcode"
    "requests"
)

for dep in "${DEPENDENCIES[@]}"; do
    echo "  Installing $dep..."
    pip install "$dep" -q 2>/dev/null || pip install "$dep" --user -q 2>/dev/null || true
done

# Create necessary directories
echo ""
echo "📁 Creating directory structure..."
mkdir -p "$BASE_DIR/knowledge/ableton-brain/presets"
mkdir -p "$BASE_DIR/knowledge/ableton-brain/controller-configs"
mkdir -p "$BASE_DIR/knowledge/ableton-brain/logs"

# Copy scripts to scripts directory
SCRIPTS_DIR="$BASE_DIR/knowledge/ableton-brain/scripts"
mkdir -p "$SCRIPTS_DIR"

if [ -f "scripts/manual-update.py" ]; then
    cp scripts/manual-update.py "$SCRIPTS_DIR/"
fi

# Make scripts executable (Unix only)
if [ "$OS" != "windows" ]; then
    chmod +x "$SCRIPTS_DIR"/*.sh 2>/dev/null || true
    chmod +x "$SCRIPTS_DIR"/*.py 2>/dev/null || true
fi

# Create desktop shortcut (Windows)
if [ "$OS" = "windows" ]; then
    echo ""
    echo "🖥️  Creating Windows shortcuts..."
    
    # Create batch file for quick start
    cat > "$BASE_DIR/knowledge/ableton-brain/start.bat" << 'EOF'
@echo off
title ABLETON BRAIN Controller
python main.py
pause
EOF
    
    # Create uninstall shortcut
    cat > "$BASE_DIR/knowledge/ableton-brain/uninstall.bat" << 'EOF'
@echo off
echo Uninstalling ABLETON BRAIN...
rmdir /s /q "knowledge\ableton-brain\presets" 2>nul
rmdir /s /q "knowledge\ableton-brain\controller-configs" 2>nul
rmdir /s /q "knowledge\ableton-brain\logs" 2>nul
echo Uninstall complete!
pause
EOF
fi

# Create Unix startup scripts
cat > "$SCRIPTS_DIR/start.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../../"
python3 main.py
EOF

cat > "$SCRIPTS_DIR/stop.sh" << 'EOF'
#!/bin/bash
pkill -f "main.py"
echo "Stopped ABLETON BRAIN"
EOF

chmod +x "$SCRIPTS_DIR"/*.sh

# Create systemd service file (Linux)
if [ "$OS" = "linux" ]; then
    echo ""
    echo "🐧 Creating systemd service..."
    
    cat > "$BASE_DIR/knowledge/ableton-brain/ableton-brain.service" << EOF
[Unit]
Description=ABLETON BRAIN Controller
After=network.target

[Service]
Type=simple
WorkingDirectory=$BASE_DIR/knowledge/ableton-brain
ExecStart=$PYTHON main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
fi

# Create launch scripts for different platforms
cat > "$SCRIPTS_DIR/launch.py" << 'EOF'
#!/usr/bin/env python3
"""Cross-platform launcher for ABLETON BRAIN."""
import sys
import os
import subprocess
from pathlib import Path

def main():
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    
    # Detect platform
    if sys.platform == "win32":
        main_script = base_dir / "main.py"
        python_exe = sys.executable
    else:
        main_script = base_dir / "main.py"
        python_exe = "python3" if sys.version_info[0] >= 3 else "python"
    
    print(f"🚀 Launching ABLETON BRAIN from: {base_dir}")
    print(f"🐍 Using Python: {python_exe}")
    
    try:
        subprocess.run([python_exe, str(main_script)], cwd=str(base_dir))
    except KeyboardInterrupt:
        print("\n👋 ABLETON BRAIN stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error launching: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

echo ""
echo "✅ Installation Complete!"
echo ""
echo "📂 Installation locations:"
echo "   Main app: $BASE_DIR/knowledge/ableton-brain/"
echo "   Scripts:  $BASE_DIR/knowledge/ableton-brain/scripts/"
echo "   Presets:  $BASE_DIR/knowledge/ableton-brain/presets/"
echo ""
echo "🚀 To start the system:"
if [ "$OS" = "windows" ]; then
    echo "   Double-click: $BASE_DIR/knowledge/ableton-brain/start.bat"
    echo "   Or run: cd \"$BASE_DIR/knowledge/ableton-brain\" && python main.py"
else
    echo "   Run: $SCRIPTS_DIR/start.sh"
    echo "   Or:  python3 $BASE_DIR/knowledge/ableton-brain/main.py"
fi
echo ""
echo "💡 Pro tip: Add the scripts folder to your PATH for quick access!"
echo ""
echo "🎉 Enjoy ABLETON BRAIN!"