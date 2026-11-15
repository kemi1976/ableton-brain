@echo off
REM Windows setup script for ABLETON BRAIN
echo =================================
echo  ABLETON BRAIN Setup Script
echo =================================
echo.

REM Check Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.10+ from python.org
    exit /b 1
)

echo Using Python:
python --version
echo.

REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate and install
echo Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e ".[midi,dev]"

REM Run tests
echo.
echo Running tests...
python -m pytest tests -v

echo.
echo Setup complete!
echo.
echo Next steps:
echo   venv\Scripts\activate        - Activate environment
echo   python tests\run_tests.py  - Run tests
echo   python demo_quick.py       - Test the system
echo.
pause