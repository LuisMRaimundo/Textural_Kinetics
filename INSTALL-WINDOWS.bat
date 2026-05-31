@echo off
title Granularity Analyser - Install (Windows)
cd /d "%~dp0"

echo.
echo ========================================
echo Granularity Analyser
echo One-click install for Windows 10/11
echo ========================================
echo.
echo This will install Python (if needed), set up the app,
echo and open the desktop GUI.
echo.
pause

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installers\windows\Install-Granularity.ps1"
if errorlevel 1 (
    echo.
    echo Installation failed. Read the messages above.
    echo You can also install Python from https://www.python.org/downloads/
    echo then run this file again.
    echo.
    pause
    exit /b 1
)
