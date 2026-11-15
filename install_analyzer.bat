@echo off
:: Install AbletonMCP Analyzer Max for Live Device
:: Run after main install.bat

echo =====================================================================
echo   🎛️  ABLETON BRAIN - Analyzer Device Installation
echo =====================================================================
echo.

:: Find Max for Live User Library presets folder
set M4L_PRESETS="%USERPROFILE%\Documents\Ableton\User Library\Presets\Audio Effects\Max Audio Effect"
if not exist "%M4L_PRESETS%" (
    echo Creating Max for Live presets folder...
    mkdir "%M4L_PRESETS%"
)

:: Copy analyzer device
echo Copying AbletonMCP_Analyzer.amxd...
copy /Y "%~dp0AbletonMCP_Analyzer.maxpat" "%M4L_PRESETS%\AbletonMCP_Analyzer.amxd"
if %ERRORLEVEL% EQU 0 (
    echo ✅ Analyzer device installed to %M4L_PRESETS%
) else (
    echo ❌ Failed to copy analyzer device
)

echo.
echo NEXT STEPS:
echo 1. Restart Ableton Live
echo 2. The device will appear in Browser > Audio Effects > Max Audio Effect > AbletonMCP_Analyzer
echo 3. Drag onto any track (recommended: Master track for full mix analysis)
echo 4. Run: python analyzer_bridge.py (to start OSC receiver on port 9878)
echo 5. Use MCP tools: install_analyzer, read_analyzer, mix_doctor, compare_to_reference
echo.
pause