@echo off
:: ABLETON BRAIN Launcher
title ABLETON BRAIN - Music Production AI
color 0E

echo.
echo ===================================================================
echo   🧠 ABLETON BRAIN - Intelligent Music Production Assistant
echo ===================================================================
echo.
echo Starting ABLETON BRAIN v3.0...
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH
    echo Please run from your Python environment
    pause
    exit /b 1
)

:: Run the ABLETON BRAIN interface
python /c/Users/pc/Documents/AI PROJECTS ANDROID/knowledge/ableton-brain/ableton_brain.py

pause