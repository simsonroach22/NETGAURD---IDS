@echo off
REM ============================================================
REM  NETGUARD IDS — App Launcher
REM  Double-click this every time to open NETGUARD
REM ============================================================

title NETGUARD IDS

python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [!] Run install.bat first, then try again.
    echo.
    pause & exit /b 1
)

if not exist app.py (
    echo.
    echo  [ERROR] app.py not found in this folder.
    echo.
    pause & exit /b 1
)

if not exist logs mkdir logs
if not exist mode.txt echo system> mode.txt

REM Kill any old Streamlit still running
taskkill /f /im streamlit.exe >nul 2>&1

echo.
echo  Starting NETGUARD IDS...
echo  Opening in your browser automatically.
echo  To stop the app, close this window.
echo.

python -m streamlit run app.py --server.headless true --browser.serverAddress localhost
