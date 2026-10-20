@echo off
title UploadPost Master Fleet Control Panel
cd /d "%~dp0"
echo ========================================================
echo   UPLOADPOST FLEET - MASTER AUTOMATION CONTROL PANEL
echo   Opening: http://localhost:10000
echo ========================================================
echo.
timeout /t 2 >nul
start http://localhost:10000
python app.py
pause
