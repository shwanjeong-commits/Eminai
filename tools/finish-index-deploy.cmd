@echo off
chcp 65001 >nul
title EMINAI FINISH INDEX DEPLOY
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0finish-index-deploy.ps1"
echo.
echo Press any key to close this window.
pause >nul
