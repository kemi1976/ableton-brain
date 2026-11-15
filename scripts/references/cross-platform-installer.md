# Cross-Platform Installer Pattern

## Overview
Create installers that work across Windows, macOS, and Linux with a single codebase structure.

## Structure
```
project/
├── scripts/
│   ├── install.bat          # Windows installer
│   └── install.sh           # Unix installer (macOS/Linux)
├── knowledge/
│   └── artist-database.json # Shared JSON database
└── README.md
```

## Windows Installer (.bat) Template

```batch
@echo off
setlocal enabledelayedexpansion

echo ================================================
echo PROJECT INSTALLER
echo ================================================

set "BASE_DIR=%USERPROFILE%\Documents\PROJECT"
set "PYTHON_EXE=python"

REM Check Python
%PYTHON_EXE% --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python not found! Please install Python 3.14+
    exit /b 1
)

REM Create directories
if not exist "%BASE_DIR%" mkdir "%BASE_DIR%"

REM Install dependencies
%PYTHON_EXE% -m pip install --upgrade pip -q
for %%p in (package1 package2 package3) do (
    %PYTHON_EXE% -m pip install %%p -q 2>nul || echo Warning: Could not install %%p
)

REM Create startup script
echo @echo off > "%BASE_DIR%\start.bat"
echo cd /d "%BASE_DIR%" >> "%BASE_DIR%\start.bat"
echo %PYTHON_EXE% main.py >> "%BASE_DIR%\start.bat"

echo.
echo Installation complete!
echo Run: %BASE_DIR%\start.bat
pause
```

## Unix Installer (.sh) Template

```bash
#!/bin/bash
set -e

echo "================================================"
echo "PROJECT INSTALLER"
echo "================================================"

BASE_DIR="$HOME/Documents/PROJECT"
PYTHON_EXE="python3"

# Check Python
if ! command -v $PYTHON_EXE &> /dev/null; then
    echo "Python not found! Please install Python 3.14+"
    exit 1
fi

# Create directories
mkdir -p "$BASE_DIR"

# Install dependencies
$PYTHON_EXE -m pip install --upgrade pip -q

# Install packages (with fallback handling)
PACKAGES=("package1" "package2" "package3")
for pkg in "${PACKAGES[@]}"; do
    echo "Installing $pkg..."
    $PYTHON_EXE -m pip install "$pkg" -q 2>/dev/null || \
    $PYTHON_EXE -m pip install "$pkg" --user -q 2>/dev/null || \
    echo "Warning: Could not install $pkg"
done

# Make scripts executable
chmod +x "$BASE_DIR/scripts/"*.sh 2>/dev/null || true

echo ""
echo "Installation complete!"
echo "Run: bash $BASE_DIR/scripts/start.sh"
```

## Key Principles

1. **Dual File Approach**: Always create both `.bat` and `.sh` files
2. **Cross-Platform Paths**: Use `os.path.join()` in Python, never hardcoded separators
3. **Graceful Degradation**: Install what you can, warn about failures, don't abort
4. **User Verification**: Always verify files were created with proper sizes
5. **Backwards Compatibility**: Check Python version, provide fallbacks for missing packages

## Verification Pattern

```python
from pathlib import Path
import json

# Verify database
db_path = Path(r'C:/Users/pc/Documents/PROJECT/database.json')
if db_path.exists():
    with open(db_path, 'r') as f:
        data = json.load(f)
    print(f"✅ Database verified: {len(data)} entries")
else:
    print("❌ Database not found")

# Verify script
script_path = Path(r'/c/Users/pc/Documents/PROJECT/scripts/install.sh')
if script_path.exists():
    size = script_path.stat().st_size
    print(f"✅ Script verified: {size} bytes")
else:
    print("❌ Script not found")
```

## Database Pattern

For JSON databases shared across platforms:
- Single source of truth
- Auto-backup before changes
- Schema versioning
- Genre-based organization
- No platform-specific formatting