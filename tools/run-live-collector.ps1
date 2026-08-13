$ErrorActionPreference = "Stop"
$Python = "C:\Users\drego\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
& $Python src\live_collector.py
