@echo off
chcp 65001 >nul
title EMINAI CHART UPGRADE DEPLOY
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy-chart-upgrade.ps1"
echo.
echo Press any key to close this window.
pause >nul
