@echo off
echo.
echo  ╔═══════════════════════════════════════════════╗
echo  ║        🚀 agent2win — Installer               ║
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
if not exist "%APPDATA%\agent2win" mkdir "%APPDATA%\agent2win"

echo  ═══════════════════════════════════════════════
echo   ✅ Installation complete!
echo.
echo   To start:  agent2win  (or python main.py)
echo   Settings:  agent2win --settings
echo   Help:      agent2win --help
echo  ═══════════════════════════════════════════════
echo.
pause
