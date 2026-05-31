#!/usr/bin/env bash
# One-click install for Linux — run: ./INSTALL-LINUX.sh
# Or: bash INSTALL-LINUX.sh

cd "$(dirname "$0")"

clear
echo ""
echo " ========================================"
echo " Granularity Analyser"
echo " One-click install for Linux"
echo " ========================================"
echo ""
echo " This will install Python (if needed, may ask for sudo password),"
echo " set up the app, and open the desktop GUI."
echo ""
read -r -p "Press Enter to continue... " _

bash "installers/linux/install.sh" || {
    echo ""
    echo " Installation failed. See messages above."
    read -r -p "Press Enter to close... " _
    exit 1
}
