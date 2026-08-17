@echo off
echo.
echo ====================================================
echo   Mobile2Storage - Building .exe
echo ====================================================
echo.

echo [1/2] Installing dependencies...
pip install customtkinter Pillow qrcode pyinstaller >nul 2>&1

echo [2/2] Building executable...
echo.

python -m PyInstaller --name "Mobile2Storage" --onefile --windowed --clean --noconfirm ^
    --hidden-import=customtkinter ^
    --hidden-import=PIL ^
    --hidden-import=PIL._tkinter_finder ^
    --hidden-import=qrcode ^
    --hidden-import=qrcode.image.pil ^
    --hidden-import=src ^
    --hidden-import=src.core ^
    --hidden-import=src.core.receiver_server ^
    --hidden-import=src.core.mobile_page ^
    --hidden-import=src.core.qr_generator ^
    --hidden-import=src.ui ^
    --hidden-import=src.ui.dashboard ^
    --hidden-import=src.utils ^
    --hidden-import=src.utils.helpers ^
    --collect-data=customtkinter ^
    --paths=. ^
    main.py

if %errorlevel% equ 0 (
    echo.
    echo ====================================================
    echo   SUCCESS! Your exe is at: dist\Mobile2Storage.exe
    echo ====================================================
) else (
    echo.
    echo   BUILD FAILED - see errors above
)
echo.
pause
