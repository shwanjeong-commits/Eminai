$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\drego\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$LogDir = Join-Path $Root "logs"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Set-Location $Root

$env:PYTHONIOENCODING = "utf-8"

Write-Host "[catchup] collecting recent Telegram messages..."
& $Python src\collector.py --limit 500 --quiet

Write-Host "[catchup] reconciling known Telegram message gaps..."
& $Python src\reconcile_gaps.py --limit-gaps 1000

Write-Host "[catchup] analyzing queued news..."
& $Python src\ai_analyzer.py --limit 50

Write-Host "[catchup] rebuilding dashboard views..."
& $Python src\rebuild_views.py

Write-Host "[live] starting Telegram live collector..."
& $Python src\live_collector.py
