#!/bin/bash
# Double-click this file in Finder to install and run Textural_Kinetics on macOS.

cd "$(dirname "$0")"

clear
echo ""
echo " ========================================"
echo " Textural_Kinetics"
echo " One-click install for macOS"
echo " ========================================"
echo ""
echo " This will install Python (if needed), set up the app,"
echo " and open the desktop GUI."
echo ""
read -r -p "Press Enter to continue... " _

bash "installers/mac/install.sh" || {
    echo ""
    echo " Installation failed. See messages above."
    read -r -p "Press Enter to close... " _
    exit 1
}
