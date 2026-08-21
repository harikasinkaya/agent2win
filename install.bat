@echo off
echo.
echo  ╔═══════════════════════════════════════════════╗
echo  ║     🪟 Windows Arena AI — Installer           ║
echo  ╚═══════════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ❌ Python not found! Install Python 3.9+ from https://python.org
    echo     Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo  ✅ Python found
echo.

:: Install dependencies
echo  📦 Installing dependencies...
pip install -r requirements.txt
echo.

:: Create config directory
if not exist "%APPDATA%\WindowsArenaAI" mkdir "%APPDATA%\WindowsArenaAI"

echo  ═══════════════════════════════════════════════
echo   ✅ Installation complete!
echo.
echo   To start:  python main.py
echo   Settings:  python main.py --settings
echo   Help:      python main.py --help
echo  ═══════════════════════════════════════════════
echo.
pause
