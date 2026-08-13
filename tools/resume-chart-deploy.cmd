@echo off
chcp 65001 >nul
title EMINAI RESUME DEPLOY
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0resume-chart-deploy.ps1"
echo.
echo Press any key to close this window.
pause >nul
