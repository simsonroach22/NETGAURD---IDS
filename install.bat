@echo off
REM ============================================================
REM  NETGUARD IDS — One-Time Setup Installer
REM ============================================================

title NETGUARD IDS - Setup

echo.
echo  ==========================================
echo   NETGUARD IDS - First Time Setup
echo  ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause & exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYVER=%%i
echo [OK] Found %PYVER%
echo.

echo [1/3] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo       Done.

echo [2/3] Installing dependencies...
pip install streamlit psutil --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install. Try running as Administrator.
    pause & exit /b 1
)
echo       Done.

echo [3/3] Setting up folders...
if not exist logs mkdir logs
if not exist mode.txt echo system> mode.txt
echo       Done.

echo.
echo  ==========================================
echo   SETUP COMPLETE!
echo   Double-click NETGUARD.bat to launch.
echo  ==========================================
echo.
pause
