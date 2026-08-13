$ErrorActionPreference = "Stop"
$Python = "C:\Users\drego\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
& $Python src\login_telegram.py
Write-Host ""
Write-Host "Login finished. You can close this window."
Read-Host "Press Enter to close"
