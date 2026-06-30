#!/bin/bash
cd "$(dirname "$0")"
if [[ ! -x ".venv/bin/python" ]]; then
    echo "Run INSTALL-MAC.command first."
    read -r -p "Press Enter to close..."
    exit 1
fi
echo "Starting Temporal_Granularity..."
echo "Close this Terminal window to stop the app."
exec .venv/bin/python -m granular_v2.gui
