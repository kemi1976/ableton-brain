@echo off
:: ABLETON BRAIN - Complete Installation Script
:: Run as Administrator for Remote Script installation

echo =====================================================================
echo   🧠 ABLETON BRAIN - Full Installation
echo =====================================================================
echo.

:: 1. Install Python dependencies
echo [1/8] Installing Python dependencies...
pip install mcp fastapi uvicorn librosa numpy scipy pythonosc pyloudnorm soundfile --quiet

:: 2. Find Ableton User Library
echo [2/8] Locating Ableton User Library...
set ABLETON_REMOTE="%USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\AbletonBrain"
if not exist "%ABLETON_REMOTE%" (
    mkdir "%ABLETON_REMOTE%"
)

:: 3. Copy Remote Script
echo [3/8] Installing Remote Script...
copy /Y "%~dp0ableton_remote\__init__.py" "%ABLETON_REMOTE%\__init__.py"
echo Remote Script installed to %ABLETON_REMOTE%

:: 4. Install Max for Live Analyzer Device
echo [4/8] Installing Max for Live Analyzer Device...
set M4L_PRESETS="%USERPROFILE%\Documents\Ableton\User Library\Presets\Audio Effects\Max Audio Effect"
if not exist "%M4L_PRESETS%" (
    mkdir "%M4L_PRESETS%"
)
copy /Y "%~dp0AbletonMCP_Analyzer.maxpat" "%M4L_PRESETS%\AbletonMCP_Analyzer.amxd"
if %ERRORLEVEL% EQU 0 (
    echo ✅ Analyzer device installed to %M4L_PRESETS%
) else (
    echo ⚠️  Analyzer device copy failed - run install_analyzer.bat manually
)

:: 5. Copy core Python modules
echo [5/8] Installing core modules...
copy /Y "%~dp0sample_scanner.py" "%~dp0"
copy /Y "%~dp0analyzer_bridge.py" "%~dp0"
copy /Y "%~dp0automation_recipes.py" "%~dp0"
copy /Y "%~dp0ai_generation.py" "%~dp0"
copy /Y "%~dp0plugin_corpus.py" "%~dp0"
copy /Y "%~dp0fleet_coordinator.py" "%~dp0"
copy /Y "%~dp0workflow_engine.py" "%~dp0"
echo Core modules ready

:: 6. Create sample folder
echo [6/8] Creating sample folder...
set SAMPLE_DIR="%~dp0samples"
if not exist "%SAMPLE_DIR%" mkdir "%SAMPLE_DIR%"

:: Create genre subfolders
for %%G in (drums bass loops melody pads fx vocals) do (
    if not exist "%SAMPLE_DIR%\%%G" mkdir "%SAMPLE_DIR%\%%G"
)

:: 7. Create plugin parameter maps folder
echo [7/8] Creating plugin corpus folder...
set PLUGIN_MAPS="%~dp0plugin_maps"
if not exist "%PLUGIN_MAPS%" mkdir "%PLUGIN_MAPS%"

:: 8. Install dashboard files
echo [8/8] Installing Dashboard & Hermes Plugin...
copy /Y "%~dp0ableton-brain-dashboard.html" "%~dp0"
copy /Y "%~dp0plugin.json" "%~dp0"
echo Dashboard & plugin installed

echo.
echo =====================================================================
echo   ✅ INSTALLATION COMPLETE
echo =====================================================================
echo.
echo NEXT STEPS:
echo 1. Open Ableton Live
echo 2. Go to Preferences > Link, Tempo & MIDI
echo 3. Set Control Surface: "AbletonBrain"
echo 4. Set Input: "None" | Output: "None"
echo 5. Restart Ableton Live
echo.
echo 6. Start ALL services (easy way):
echo    start-all.bat
echo.
echo    OR manually:
echo    python "%~dp0mcp_server.py" --http
echo    python "%~dp0analyzer_bridge.py"
echo    python "%~dp0fleet_coordinator.py"
echo.
echo 7. Open Dashboard: http://localhost:8050
echo.
echo 8. Configure Claude Desktop / Cursor with:
echo    {
echo      "mcpServers": {
echo        "ableton-brain": {
echo          "command": "python",
echo          "args": ["%~dp0mcp_server.py"]
echo        }
echo      }
echo    }
echo.
echo SAMPLE SCANNING:
echo   python "%~dp0sample_scanner.py" "C:\path\to\samples" "dnb"
echo.
echo ANALYZER USAGE:
echo   - Drag "AbletonMCP_Analyzer" (Max Audio Effect) onto any track
echo   - Use Dashboard: Mix Doctor, Compare to Reference, AI Generation
echo.
echo BLUETOOTH MIDI (Windows):
echo   - Download BlueMIDI from github.com/Armazi000/bluemidi/releases
echo   - Install teVirtualMIDI (loopMIDI or rtpMIDI)
echo   - Run bluemidi.exe --autostart
echo   - Enable "BlueMIDI - ROLI" in Ableton MIDI Preferences (check MPE)
echo.
echo HERMES INTEGRATION:
echo   - Open plugin.json in Hermes to install as native widget
echo   - Dashboard appears in Messaging pane
echo.
pause