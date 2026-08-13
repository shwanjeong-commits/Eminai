$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\drego\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$PowerShell = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$LogDir = Join-Path $Root "logs"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Test-ProcessCommand {
    param([string] $Needle)

    $processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
    foreach ($process in $processes) {
        if ($process.CommandLine -and $process.CommandLine.Contains($Needle)) {
            return $true
        }
    }
    return $false
}

if (-not (Test-ProcessCommand "src\api_server.py")) {
    Start-Process `
        -WindowStyle Hidden `
        -FilePath $Python `
        -WorkingDirectory $Root `
        -ArgumentList @("src\api_server.py") `
        -RedirectStandardOutput (Join-Path $LogDir "api-server.out.log") `
        -RedirectStandardError (Join-Path $LogDir "api-server.err.log")
}

if (
    -not (Test-ProcessCommand "src\live_collector.py") -and
    -not (Test-ProcessCommand "tools\run-worker-with-catchup.ps1")
) {
    Start-Process `
        -WindowStyle Hidden `
        -FilePath $PowerShell `
        -WorkingDirectory $Root `
        -ArgumentList @("-ExecutionPolicy", "Bypass", "-File", (Join-Path $Root "tools\run-worker-with-catchup.ps1")) `
        -RedirectStandardOutput (Join-Path $LogDir "worker.out.log") `
        -RedirectStandardError (Join-Path $LogDir "worker.err.log")
}

Write-Host "Local stack requested."
Write-Host "Dashboard: http://127.0.0.1:4173"
Write-Host "Logs: $LogDir"
