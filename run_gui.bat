@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m granular_v2.gui
) else (
    python -m granular_v2.gui
)
