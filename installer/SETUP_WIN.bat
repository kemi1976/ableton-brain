@echo off
:: Ableton Brain Installer - Windows Batch Script
:: One-click installer for AI-powered Ableton Live automation

setlocal enabledelayedexpansion

:: Colors for output
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"

echo.
echo %BLUE%╔══════════════════════════════════════════════════════════╗
echo %BLUE%║           ABL TON BRAIN - INSTALLER                     ║
echo %BLUE%║          AI-Powered Ableton Live Automation              ║
echo %BLUE%╚══════════════════════════════════════════════════════════╝
echo.

:: Step 1: Detect Python
echo %YELLOW[Step 1] Checking Python 3.10+ availability...%RESET

set PYTHON_PATH=
for %%p in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "python"
) do (
    if exist %%p (
        for /f "tokens=2" %%v in ('%%p --version 2^>nul') do (
            set PYTHON_VER=%%v
        )
        if "!PYTHON_VER:~0,1!" geq "3" (
            set PYTHON_PATH=%%p
            goto :python_found
        )
    )
)

:: Try from PATH
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set PYTHON_PATH=python
    goto :python_found
)

echo %RED%ERROR: Python 3.10+ not found!%RESET
echo Please install Python 3.10+ from https://python.org
pause
exit /b 1

:python_found
echo %GREEN%Found Python: !PYTHON_PATH! (Version: !PYTHON_VER!%RESET%
echo.

:: Step 2: Detect Ableton
echo %YELLOW[Step 2] Detecting Ableton Live installation...%RESET

set ABLETON_PATH=
set ABLETON_VERSION=

:: Check Live 12 Suite first
if exist "%PROGRAMFILES%\Ableton\Live 12 Suite\Program\Ableton Live 12 Suite.exe" (
    set ABLETON_PATH=%PROGRAMFILES%\Ableton\Live 12 Suite\Program\Ableton Live 12 Suite.exe
    set ABLETON_VERSION=12
    goto :ableton_found
)

:: Check Live 11 Suite
if exist "%PROGRAMFILES%\Ableton\Live 11 Suite\Program\Ableton Live 11 Suite.exe" (
    set ABLETON_PATH=%PROGRAMFILES%\Ableton\Live 11 Suite\Program\Ableton Live 11 Suite.exe
    set ABLETON_VERSION=11
    goto :ableton_found
)

:: Check 32-bit Program Files
if exist "%PROGRAMFILES(X86)%\Ableton\Live 12 Suite\Program\Ableton Live 12 Suite.exe" (
    set ABLETON_PATH=%PROGRAMFILES(X86)%\Ableton\Live 12 Suite\Program\Ableton Live 12 Suite.exe
    set ABLETON_VERSION=12
    goto :ableton_found
)

if exist "%PROGRAMFILES(X86)%\Ableton\Live 11 Suite\Program\Ableton Live 11 Suite.exe" (
    set ABLETON_PATH=%PROGRAMFILES(X86)%\Ableton\Live 11 Suite\Program\Ableton Live 11 Suite.exe
    set ABLETON_VERSION=11
    goto :ableton_found
)

echo %YELLOW%Ableton Live not found in standard locations.%RESET%
set /p "CUSTOM_ABLETON=Enter path to Ableton executable (or press Enter to skip): "
if "!CUSTOM_ABLETON!" neq "" (
    if exist "!CUSTOM_ABLETON!" (
        set ABLETON_PATH=!CUSTOM_ABLETON!
        set ABLETON_VERSION=11
        goto :ableton_found
    )
)

echo %RED%ERROR: Ableton Live is required for this installer.%RESET%
pause
exit /b 1

:ableton_found
echo %GREEN%Found Ableton Live %ABLETON_VERSION%: !ABLETON_PATH!%RESET%
echo.

:: Step 3: Set up User Library path
echo %YELLOW[Step 3] Determining User Library path...%RESET

set USER_LIBRARY=%USERPROFILE%\Documents\Ableton\User Library

if not exist "!USER_LIBRARY!" (
    echo %YELLOW%Creating User Library folder...%RESET
    mkdir "!USER_LIBRARY!" 2>nul
)

echo %GREEN%User Library: !USER_LIBRARY!%RESET%
echo.

:: Step 4: Install Remote Script
echo %YELLOW[Step 4] Installing Remote Script...%RESET

set REMOTE_SCRIPT_DIR=!USER_LIBRARY!\Remote Scripts\AbletonBrain

if not exist "!REMOTE_SCRIPT_DIR!" (
    mkdir "!REMOTE_SCRIPT_DIR!"
    echo %GREEN%Created Remote Scripts folder%RESET%
) else (
    echo %GREEN%Remote Scripts folder already exists%RESET%
)

:: Get the directory where this script is located
set SCRIPT_DIR=%~dp0

:: Copy Remote Script if it exists
if exist "!SCRIPT_DIR!remote_script\*.py" (
    copy /Y "!SCRIPT_DIR!remote_script\*.py" "!REMOTE_SCRIPT_DIR!\" >nul
    echo %GREEN%Copied Remote Script files%RESET%
) else if exist "!SCRIPT_DIR!installer\resources\remote_script\*.py" (
    copy /Y "!SCRIPT_DIR!installer\resources\remote_script\*.py" "!REMOTE_SCRIPT_DIR!\" >nul
    echo %GREEN%Copied Remote Script files%RESET%
) else (
    echo %YELLOW%Warning: Remote Script files not found - please copy manually%RESET%
)

echo.

:: Step 5: Create Python Virtual Environment
echo %YELLOW[Step 5] Creating Python virtual environment...%RESET

set BRAIN_DIR=%SCRIPT_DIR%..
if exist "!BRAIN_DIR!**" (
    cd /d "!BRAIN_DIR!"
)

if not exist ".venv" (
    %PYTHON_PATH% -m venv .venv
    if !errorlevel! neq 0 (
        echo %RED%Failed to create virtual environment%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%Virtual environment created%RESET%
) else (
    echo %GREEN%Virtual environment already exists%RESET%
)

:: Step 6: Install Dependencies
echo %YELLOW[Step 6] Installing Python dependencies...%RESET

echo This will take a few minutes...
echo.

set VENV_PYTHON=.venv\Scripts\python.exe

:: Upgrade pip
%VENV_PYTHON% -m pip install --upgrade pip --quiet

:: Install core dependencies
%VENV_PYTHON% -m pip install mcp fastapi uvicorn librosa numpy scipy python-osc pyloudnorm soundfile mido requests websocket-client anyio rich qrcode Pillow pytest pytest-asyncio --quiet

if !errorlevel! equ 0 (
    echo %GREEN%Core dependencies installed%RESET%
) else (
    echo %YELLOW%Some dependencies may have failed - continuing...%RESET%
)

:: Try to install PyTorch CPU (optional)
echo %YELLOW%Installing PyTorch (CPU version, optional)...%RESET
%VENV_PYTHON% -m pip install torch --index-url https://download.pytorch.org/whl/cpu --quiet 2>nul

echo.

:: Step 7: Configure MCP Client
echo %YELLOW[Step 7] Configuring MCP client...%RESET

set MCP_CONFIG_DIR=%APPDATA%\Claude
if not exist "!MCP_CONFIG_DIR!" (
    mkdir "!MCP_CONFIG_DIR!"
)

set MCP_CONFIG_FILE=!MCP_CONFIG_DIR!\claude_desktop_config.json

:: Write MCP config
(
echo {
echo   "mcpServers": {
echo     "ableton-brain": {
echo       "command": "!CD!\.venv\Scripts\python.exe",
echo       "args": ["!CD!\mcp_server.py"]
echo     }
echo   }
echo }
) > temp_config.json

move /Y temp_config.json "!MCP_CONFIG_FILE!" >nul

echo %GREEN%MCP configuration created at:!MCP_CONFIG_FILE!%RESET%
echo.

:: Step 8: Create Start Script
echo %YELLOW[Step 8] Creating start script...%RESET

echo @echo off > start-brain.cmd
echo cd /d "!CD!" >> start-brain.cmd
echo .venv\Scripts\python.exe mcp_server.py --http >> start-brain.cmd
echo echo MCP Server started at http://localhost:8050 >> start-brain.cmd
echo echo Press Ctrl+C to stop >> start-brain.cmd

echo .venv\Scripts\python.exe analyzer_bridge.py >> start-brain.cmd
echo echo Analyzer Bridge started on port 9878 >> start-brain.cmd

echo .venv\Scripts\python.exe fleet_coordinator.py >> start-brain.cmd
echo echo Fleet Coordinator started on port 9880 >> start-brain.cmd

echo %GREEN%Created start-brain.cmd%RESET%
echo.

:: Step 9: Create Desktop Shortcut
echo %YELLOW[Step 9] Creating desktop shortcut...%RESET

set SHORTCUT_TARGET=%USERPROFILE%\Desktop\Ableton Brain - Dashboard.lnk
powershell -Command "New-Object -ComObject WScript.Shell; $s = (New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT_TARGET%'); $s.TargetPath = 'cmd.exe'; $s.Arguments = '/c start http://localhost:8050'; $s.WorkingDirectory = '%CD%'; $s.WindowStyle = 1; $s.Save()" 2>nul

echo %GREEN%Desktop shortcut created%RESET%
echo.

:: Complete
echo.
echo %GREEN%╔══════════════════════════════════════════════════════════╗
echo %GREEN%║              INSTALLATION COMPLETE!                   ║
echo %GREEN%╚══════════════════════════════════════════════════════════╝
echo.
echo Next steps:
echo 1. Enable AbletonBrain in Ableton Preferences ^> Link, Tempo ^& MIDI
echo 2. Run start-brain.cmd to launch services
echo 3. Open http://localhost:8050 in your browser
echo.
echo Features available:
echo   ^- Full MIDI/Audio track control (47 MCP tools)
echo   ^- Real-time audio analysis (LUFS, stereo, spectrum)
echo   ^- AI Mastering (Ozone-style EQ, comp, limiter)
echo   ^- Lyric Generation (template-based + LLM support)
echo   ^- Vocal Synthesis (ACE-Step / YuE - requires GPU)
echo   ^- Stem Separation (Demucs)
echo   ^- Sound Similarity Search (FAISS)
echo   ^- Distributed Compute (ThinkPad GPU offload)
echo.
pause
endlocal