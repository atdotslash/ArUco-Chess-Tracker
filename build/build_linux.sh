#!/usr/bin/env bash
set -e

echo "======================================================="
echo "Building ArUco Chess Tracker for Linux with PyInstaller"
echo "======================================================="

pyinstaller --noconfirm --windowed --onefile \
--name ArUcoChessTracker \
--icon assets/icons/app.png \
--add-data "assets:assets" \
--add-data "calibration:calibration" \
--collect-all customtkinter \
--collect-all cv2 \
--collect-all numpy \
main.py

echo ""
echo "Build completed! Binary located in dist/ArUcoChessTracker"
