@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run INSTALL-WINDOWS.bat first.
    pause
    exit /b 1
)
echo Starting Granularity Analyser...
echo Close this window to stop the app.
".venv\Scripts\python.exe" -m granular_v2.gui
pause
