@echo off
title Temporal_Granularity - Installer
cd /d "%~dp0\..\.." || (
    echo ERROR: Cannot find project root.
    pause
    exit /b 1
)

echo.
echo *** USE THIS FILE FOR NORMAL INSTALL ***
echo.
echo ========================================
echo Temporal_Granularity
echo One-click install for Windows 10/11
echo ========================================
echo.
echo GitHub: https://github.com/LuisMRaimundo/Temporal_Granularity
echo.
echo This installs Python if needed, sets up the app,
echo and opens the desktop GUI.
echo.
echo Do not close this window until finished.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Temporal_Granularity.ps1"
set ERR=%ERRORLEVEL%

echo.
if %ERR% NEQ 0 (
    echo Installation failed. See install.log in the project folder.
) else (
    echo Done.
)
echo.
pause
exit /b %ERR%
