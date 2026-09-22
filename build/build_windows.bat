@echo off
echo =======================================================
echo Building ArUco Chess Tracker for Windows with PyInstaller
echo =======================================================

pyinstaller --noconfirm --windowed --onefile ^
--name ArUcoChessTracker ^
--icon assets\icons\app.ico ^
--add-data "assets;assets" ^
--add-data "calibration;calibration" ^
--collect-all customtkinter ^
--collect-all cv2 ^
--collect-all numpy ^
main.py

echo.
echo Build completed! Executable located in dist/ArUcoChessTracker.exe
