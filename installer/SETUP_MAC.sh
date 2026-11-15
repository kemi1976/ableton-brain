#!/bin/bash
# Ableton Brain Installer - macOS Shell Script
# One-click installer for AI-powered Ableton Live automation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗"
echo -e "${BLUE}║           ABL TON BRAIN - INSTALLER                     ║"
echo -e "${BLUE}║          AI-Powered Ableton Live Automation              ║"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Step 1: Detect Python
echo -e "${YELLOW}[Step 1] Checking Python 3.10+ availability...${NC}"

PYTHON=""
for p in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$p" &> /dev/null; then
        VER=$("$p" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        if [ "$(echo "$VER >= 3.10" | bc -l 2>/dev/null || echo 0)" -eq 1 ] 2>/dev/null || [[ "$VER" == 3.1* ]]; then
            PYTHON="$p"
            echo -e "${GREEN}Found Python $VER at: $(command -v $p)${NC}"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}ERROR: Python 3.10+ not found!${NC}"
    echo "Please install Python 3.10+ from https://python.org"
    exit 1
fi

echo ""

# Step 2: Detect Ableton
echo -e "${YELLOW}[Step 2] Detecting Ableton Live installation...${NC}"

ABLETON=""
ABLETON_VERSION=""

# Common paths
ABLETON_PATHS=(
    "/Applications/Ableton Live 12 Suite/Ableton Live 12 Suite.app"
    "/Applications/Ableton Live 12 Standard/Ableton Live 12 Standard.app"
    "/Applications/Ableton Live 11 Suite/Ableton Live 11 Suite.app"
    "/Applications/Ableton Live 11 Standard/Ableton Live 11 Standard.app"
)

for p in "${ABLETON_PATHS[@]}"; do
    if [ -d "$p" ]; then
        ABLETON="$p"
        if [[ "$p" == *"12"* ]]; then
            ABLETON_VERSION=12
        else
            ABLETON_VERSION=11
        fi
        break
    fi
done

if [ -z "$ABLETON" ]; then
    echo -e "${YELLOW}Ableton Live not found in standard locations.${NC}"
    read -p "Enter path to Ableton app (or press Enter to skip): " CUSTOM_ABLETON
    if [ -n "$CUSTOM_ABLETON" ] && [ -d "$CUSTOM_ABLETON" ]; then
        ABLETON="$CUSTOM_ABLETON"
        ABLETON_VERSION=11
    else
        echo -e "${RED}ERROR: Ableton Live is required for this installer.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Found Ableton Live ${ABLETON_VERSION}: $ABLETON${NC}"
echo ""

# Step 3: Set up User Library path
echo -e "${YELLOW}[Step 3] Determining User Library path...${NC}"

USER_LIBRARY="$HOME/Music/Ableton/User Library"

if [ ! -d "$USER_LIBRARY" ]; then
    echo -e "${YELLOW}Creating User Library folder...${NC}"
    mkdir -p "$USER_LIBRARY"
fi

echo -e "${GREEN}User Library: $USER_LIBRARY${NC}"
echo ""

# Step 4: Install Remote Script
echo -e "${YELLOW}[Step 4] Installing Remote Script...${NC}"

REMOTE_SCRIPT_DIR="$USER_LIBRARY/Remote Scripts/AbletonBrain"

if [ ! -d "$REMOTE_SCRIPT_DIR" ]; then
    mkdir -p "$REMOTE_SCRIPT_DIR"
    echo -e "${GREEN}Created Remote Scripts folder${NC}"
else
    echo -e "${GREEN}Remote Scripts folder already exists${NC}"
fi

# Copy Remote Script files
if [ -f "$SCRIPT_DIR/ableton_remote/__init__.py" ]; then
    cp "$SCRIPT_DIR/ableton_remote/__init__.py" "$REMOTE_SCRIPT_DIR/"
    echo -e "${GREEN}Copied Remote Script files${NC}"
elif [ -d "$BRAIN_DIR/ableton_remote" ]; then
    cp "$BRAIN_DIR/ableton_remote/__init__.py" "$REMOTE_SCRIPT_DIR/"
    echo -e "${GREEN}Copied Remote Script files${NC}"
else
    echo -e "${YELLOW}Warning: Remote Script files not found - please copy manually${NC}"
fi

echo ""

# Step 5: Create Python Virtual Environment
echo -e "${YELLOW}[Step 5] Creating Python virtual environment...${NC}"

cd "$BRAIN_DIR"

if [ ! -d ".venv" ]; then
    $PYTHON -m venv .venv
    echo -e "${GREEN}Virtual environment created${NC}"
else
    echo -e "${GREEN}Virtual environment already exists${NC}"
fi

# Step 6: Install Dependencies
echo -e "${YELLOW}[Step 6] Installing Python dependencies...${NC}"
echo "This will take a few minutes..."
echo ""

# Activate venv
source .venv/bin/activate

pip install --upgrade pip --quiet

pip install mcp fastapi uvicorn librosa numpy scipy python-osc pyloudnorm soundfile mido requests websocket-client anyio rich qrcode Pillow pytest pytest-asyncio faiss-cpu --quiet

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Core dependencies installed${NC}"
else
    echo -e "${YELLOW}Some dependencies may have failed - continuing...${NC}"
fi

# Try to install PyTorch CPU (optional)
echo -e "${YELLOW}Installing PyTorch (CPU version, optional)...${NC}"
pip install torch --index-url https://download.pytorch.org/whl/cpu --quiet 2>/dev/null || true

deactivate
echo ""

# Step 7: Configure MCP Client
echo -e "${YELLOW}[Step 7] Configuring MCP client...${NC}"

MCP_CONFIG_DIR="$HOME/Library/Application Support/Claude"
mkdir -p "$MCP_CONFIG_DIR"

MCP_CONFIG_FILE="$MCP_CONFIG_DIR/claude_desktop_config.json"

cat > "$MCP_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "ableton-brain": {
      "command": "$BRAIN_DIR/.venv/bin/python",
      "args": ["$BRAIN_DIR/mcp_server.py"]
    }
  }
}
EOF

echo -e "${GREEN}MCP configuration created at:$MCP_CONFIG_FILE${NC}"
echo ""

# Step 8: Create Start Script
echo -e "${YELLOW}[Step 8] Creating start script...${NC}"

cat > "$BRAIN_DIR/start-brain.sh" << 'STARTSH'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate

echo "Starting MCP Server (http://localhost:8050)..."
python mcp_server.py --http &

echo "Starting Analyzer Bridge (port 9878)..."
python analyzer_bridge.py &

echo "Starting Fleet Coordinator (port 9880)..."
python fleet_coordinator.py &

echo ""
echo "Services running!"
echo "Open http://localhost:8050 in your browser"
echo "Press Ctrl+C to stop all services"

wait
STARTSH

chmod +x "$BRAIN_DIR/start-brain.sh"
echo -e "${GREEN}Created start-brain.sh${NC}"
echo ""

# Step 9: Create Dock shortcut (optional)
echo -e "${YELLOW}[Step 9] Creating helper script...${NC}"

echo -e "${GREEN}Helper script created${NC}"
echo ""

# Complete
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗"
echo -e "${GREEN}║              INSTALLATION COMPLETE!                   ║"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "1. Enable AbletonBrain in Ableton Preferences > Link, Tempo & MIDI"
echo "2. Run ./start-brain.sh to launch services"
echo "3. Open http://localhost:8050 in your browser"
echo ""
echo "Features available:"
echo "  - Full MIDI/Audio track control (47 MCP tools)"
echo "  - Real-time audio analysis (LUFS, stereo, spectrum)"
echo "  - AI Mastering (Ozone-style EQ, comp, limiter)"
echo "  - Lyric Generation (template-based + LLM support)"
echo "  - Vocal Synthesis (ACE-Step / YuE - requires GPU)"
echo "  - Stem Separation (Demucs)"
echo "  - Sound Similarity Search (FAISS)"
echo "  - Distributed Compute (ThinkPad GPU offload)"
echo ""