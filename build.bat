@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   Discord Process Spoofer & RPC Simulator Builder
echo ========================================================
echo.

:: Check for Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    echo Please install Python 3.10+ and add it to your PATH.
    pause
    exit /b 1
)

echo [1/3] Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Failed to install some requirements. Continuing anyway...
)

echo.
echo [2/3] Building standalone executable with PyInstaller...
python -m PyInstaller --clean --noconfirm --onedir --windowed --name "process_simulator" process_simulator.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo [SUCCESS] Build completed successfully!
    echo Output directory: dist\process_simulator\process_simulator.exe
    echo ========================================================
) else (
    echo.
    echo [ERROR] Build failed! Check the PyInstaller output above.
)

pause
