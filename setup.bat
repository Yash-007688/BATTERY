@echo off
REM Battery Monitor - Quick Setup Script
REM This script installs dependencies and sets up the enhanced battery monitor

echo ========================================
echo Battery Monitor - Enhanced Edition
echo Quick Setup Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Python found!
python --version
echo.

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not available
    echo Please ensure pip is installed with Python
    pause
    exit /b 1
)

echo [2/4] Installing dependencies...
echo This may take a few minutes...
echo.

pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo WARNING: Some dependencies failed to install
    echo You can continue, but some features may not work
    echo.
    pause
) else (
    echo.
    echo [3/4] Dependencies installed successfully!
    echo.
)

REM Create necessary directories
echo [4/4] Creating directories...
if not exist "sounds" mkdir sounds
if not exist "static\css" mkdir static\css
if not exist "static\js" mkdir static\js
if not exist "templates" mkdir templates

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo You can now run Battery Monitor with:
echo.
echo   Console only:        python app_enhanced.py
echo   With web interface:  python app_enhanced.py --web
echo   With system tray:    python app_enhanced.py --web --tray
echo   Install auto-start:  python app_enhanced.py --install-startup
echo.
echo For phone monitoring, install Android SDK Platform Tools:
echo https://developer.android.com/tools/releases/platform-tools
echo.
echo Press any key to start Battery Monitor with web interface...
pause >nul

python app_enhanced.py --web
