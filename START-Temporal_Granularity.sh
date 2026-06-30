#!/usr/bin/env bash
cd "$(dirname "$0")"
if [[ ! -x ".venv/bin/python" ]]; then
    echo "Run INSTALL-LINUX.sh first (or INSTALL-MAC.command on macOS)."
    read -r -p "Press Enter to close..."
    exit 1
fi
echo "Starting Temporal_Granularity..."
echo "Press Ctrl+C in this terminal to stop the app."
exec .venv/bin/python -m granular_v2.gui
