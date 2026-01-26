@echo off
REM Quick wireless ADB connection script for Windows
REM Usage: connect_wireless.bat [IP:PORT] [PAIRING_CODE]

echo ============================================================
echo Wireless ADB Connection Helper
echo ============================================================

REM Check if ADB is available
adb version >nul 2>&1
if errorlevel 1 (
    echo ERROR: ADB not found in PATH!
    echo Please install Android SDK Platform Tools
    echo Download from: https://developer.android.com/tools/releases/platform-tools
    pause
    exit /b 1
)

echo.
echo Current connected devices:
adb devices

echo.
echo ============================================================
echo Instructions:
echo ============================================================
echo 1. On your phone: Settings ^> Developer Options ^> Wireless debugging
echo 2. Enable Wireless debugging
echo 3. Note the IP address and port shown
echo 4. For Android 11+: Use "Pair device with pairing code"
echo.

if "%1"=="" (
    set /p IP_PORT="Enter IP:Port (e.g., 192.168.1.100:5555): "
) else (
    set IP_PORT=%1
)

if "%2"=="" (
    echo.
    echo Do you need to pair first? (Android 11+)
    set /p NEED_PAIR="Enter pairing code (or press Enter to skip): "
    set PAIRING_CODE=%NEED_PAIR%
) else (
    set PAIRING_CODE=%2
)

if not "%PAIRING_CODE%"=="" (
    echo.
    echo Pairing device...
    adb pair %IP_PORT% %PAIRING_CODE%
    if errorlevel 1 (
        echo Pairing failed!
        pause
        exit /b 1
    )
    echo.
    echo Pairing successful! Now enter the connection port shown on your phone.
    set /p CONN_PORT="Enter connection port: "
    if not "%CONN_PORT%"=="" (
        for /f "tokens=1 delims=:" %%a in ("%IP_PORT%") do set IP=%%a
        set IP_PORT=%IP%:%CONN_PORT%
    )
)

echo.
echo Connecting to %IP_PORT%...
adb connect %IP_PORT%

if errorlevel 1 (
    echo Connection failed!
    pause
    exit /b 1
)

echo.
echo Checking connected devices:
adb devices

echo.
echo ============================================================
echo Connection complete! Your device should now be available.
echo ============================================================
pause
