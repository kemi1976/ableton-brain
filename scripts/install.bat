@echo off
REM ABLETON BRAIN INSTALLER FOR WINDOWS
REM Works with backwards compatibility
REM ================================================

echo.
echo ================================================
echo 🚀 ABLETON BRAIN WINDOWS INSTALLER
echo ================================================
echo.

set "BASE_DIR=%USERPROFILE%\Documents\AI PROJECTS ANDROID"
set "SCRIPTS_DIR=%BASE_DIR%\knowledge\ableton-brain\scripts"
set "PYTHON_EXE=python"

REM Check Python installation
echo 🐍 Checking Python installation...
%PYTHON_EXE% --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Python not found!
    echo Please install Python 3.14+ from https://python.org
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYTHON_EXE% --version') do set PYTHON_VERSION=%%i
echo ✅ %PYTHON_VERSION%

REM Create base directory if it doesn't exist
if not exist "%BASE_DIR%" (
    echo.
    echo 📁 Creating base directory...
    mkdir "%BASE_DIR%"
)

REM Install Python dependencies
echo.
echo 📦 Installing Python dependencies...

%PYTHON_EXE% -m pip install --upgrade pip -q

REM List of required packages
set PACKAGES=keyboard python-rtmidi websocket-client numpy Pillow qrcode requests pyaudio

for %%p in (%PACKAGES%) do (
    echo   Installing %%p...
    %PYTHON_EXE% -m pip install %%p -q 2>nul
)

REM Create directories
echo.
echo 📂 Creating directory structure...
if not exist "%BASE_DIR%\knowledge\ableton-brain\presets" mkdir "%BASE_DIR%\knowledge\ableton-brain\presets"
if not exist "%BASE_DIR%\knowledge\ableton-brain\controller-configs" mkdir "%BASE_DIR%\knowledge\ableton-brain\controller-configs"
if not exist "%BASE_DIR%\knowledge\ableton-brain\logs" mkdir "%BASE_DIR%\knowledge\ableton-brain\logs"
if not exist "%SCRIPTS_DIR%" mkdir "%SCRIPTS_DIR%"

REM Copy scripts
echo.
echo 📄 Copying scripts...
copy /Y "scripts\manual-update.py" "%SCRIPTS_DIR%" >nul 2>&1
if exist "scripts\manual-update.py" (
    echo ✅ manual-update.py copied
)

REM Create startup scripts
echo.
echo 🖥️  Creating Windows startup scripts...

REM Main startup batch file
echo Creating start.bat...
(
echo @echo off
echo title ABLETON BRAIN Controller
echo color 0a
echo cd /d "%BASE_DIR%\knowledge\ableton-brain"
echo echo.
echo echo ================================================
echo echo 🎵 ABLETON BRAIN CONTROLLER
echo echo ================================================
echo echo.
echo %PYTHON_EXE% main.py
echo.
echo echo.
echo pause
) > "%BASE_DIR%\knowledge\ableton-brain\start.bat"

REM Manual update batch file
echo Creating update.bat...
(
echo @echo off
echo title ABLETON BRAIN Manual Update
echo color 0b
echo cd /d "%BASE_DIR%\knowledge\ableton-brain\scripts"
echo echo.
echo echo ================================================
echo echo 🔧 MANUAL UPDATE SYSTEM
echo echo ================================================
echo echo.
echo %PYTHON_EXE% manual-update.py
echo.
echo echo.
echo pause
) > "%BASE_DIR%\knowledge\ableton-brain\scripts\update.bat"

REM Stop script
echo Creating stop.bat...
(
echo @echo off
echo title Stop ABLETON BRAIN
echo color 0c
echo echo Stopping ABLETON BRAIN...
echo taskkill /f /im python.exe /fi "WINDOWTITLE eq ABLETON BRAIN Controller*" >nul 2^&1
echo taskkill /f /im python.exe /fi "WINDOWTITLE eq ABLETON BRAIN*" >nul 2^&1
echo echo ✅ Stopped!
echo pause
) > "%BASE_DIR%\knowledge\ableton-brain\stop.bat"

REM Desktop shortcuts
echo.
echo 📍 Creating desktop shortcuts...
set "DESKTOP=%USERPROFILE%\Desktop"
if exist "%DESKTOP%" (
    echo Creating shortcut...
    powershell -Command "$s = New-Object -ComObject WScript.Shell; $s.CreateShortcut('%DESKTOP%\ABLETON BRAIN.lnk').TargetPath = '%BASE_DIR%\knowledge\ableton-brain\start.bat'" >nul 2>&1
    if exist "%DESKTOP%\ABLETON BRAIN.lnk" echo ✅ Desktop shortcut created
)

REM Create quick launch scripts in the scripts directory
echo.
echo 🚀 Creating quick launch scripts...

REM launch.py
echo Creating launch.py...
(
echo #!/usr/bin/env python3
echo """Cross-platform launcher for ABLETON BRAIN."""
echo import sys, os, subprocess
echo from pathlib import Path
echo.
echo def main():
echo     script_dir = Path(__file__).parent
echo     base_dir = script_dir.parent
echo     main_script = base_dir / "main.py"
echo.
echo     print(f"🚀 Launching ABLETON BRAIN from: {base_dir}")
echo.
echo     try:
echo         subprocess.run([sys.executable, str(main_script)], cwd=str(base_dir))
echo     except KeyboardInterrupt:
echo         print(""^n👋 ABLETON BRAIN stopped by user"")
echo         sys.exit(0)
echo.
echo if __name__ == "__main__":
echo     main()
) > "%SCRIPTS_DIR%\launch.py"

echo.
echo ================================================
echo ✅ Installation Complete!
echo ================================================
echo.
echo 📂 Location: %BASE_DIR%\knowledge\ableton-brain\
echo.
echo 🚀 To start:
echo    Double-click start.bat on your desktop
echo    Or run: python main.py from the ABLETON BRAIN directory
echo.
echo 🔧 To update manually:
echo    Run: scripts\update.bat
echo.
echo 🎉 Enjoy ABLETON BRAIN!
echo.

pause