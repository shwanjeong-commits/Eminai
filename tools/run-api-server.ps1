$ErrorActionPreference = "Stop"
$Python = "C:\Users\drego\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONIOENCODING = "utf-8"
$env:HOST = "127.0.0.1"
$env:PORT = "4173"
& $Python src\api_server.py
