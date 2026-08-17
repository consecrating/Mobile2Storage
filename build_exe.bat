@echo off
echo ============================================================
echo   Mobile2Storage - Building Executable
echo ============================================================
echo.
echo Installing dependencies...
pip install customtkinter Pillow pyinstaller
echo.
echo Building Mobile2Storage.exe...
python build_exe.py
echo.
echo Done! Check the dist\ folder for Mobile2Storage.exe
pause
