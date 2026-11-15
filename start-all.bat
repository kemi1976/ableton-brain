@echo off
:: ABLETON BRAIN - Quick Start Launcher
:: Run this after install.bat to start all services

echo =====================================================================
echo   🧠 ABLETON BRAIN - QUICK START
echo =====================================================================
echo.

cd /d "%~dp0"

echo Checking Python dependencies...
python -c "import mcp, fastapi, uvicorn, librosa, numpy, scipy, pythonosc, pyloudnorm, soundfile" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing missing dependencies...
    pip install mcp fastapi uvicorn librosa numpy scipy pythonosc pyloudnorm soundfile --quiet
)

echo.
echo Starting services...
echo.

echo [1/3] Starting MCP Server + HTTP Dashboard (port 8050)...
start "Ableton Brain MCP" cmd /k python mcp_server.py --http

echo [2/3] Starting Analyzer Bridge (OSC port 9878)...
timeout /t 2 >nul
start "Analyzer Bridge" cmd /k python analyzer_bridge.py

echo [3/3] Starting Fleet Coordinator (optional)...
timeout /t 2 >nul
start "Fleet Coordinator" cmd /k python fleet_coordinator.py

echo.
echo =====================================================================
echo   ✅ ALL SERVICES STARTED
echo =====================================================================
echo.
echo Dashboard: http://localhost:8050
echo.
echo Ableton Live Setup:
echo 1. Open Ableton Live
echo 2. Preferences > Link, Tempo & MIDI
echo 3. Control Surface: "AbletonBrain"
echo 4. Input: "None" | Output: "None"
echo 5. Restart Ableton Live
echo.
echo In Ableton:
echo - Drag "AbletonMCP_Analyzer" (Max Audio Effect) onto Master track
echo - Use dashboard to run Mix Doctor, AI Generation, etc.
echo.
echo Hermes Integration:
echo - Open plugin.json in Hermes to install as native widget
echo - Or embed dashboard.html in Messaging pane
echo.
pause